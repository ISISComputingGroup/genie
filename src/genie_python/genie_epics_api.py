from __future__ import absolute_import, print_function

import contextlib
import os
import re
import sys
import typing
import urllib.parse
import urllib.request
from builtins import str
from collections import OrderedDict
from io import open
from typing import TYPE_CHECKING, Callable

from genie_python.block_names import BlockNames, BlockNamesManager
from genie_python.channel_access_exceptions import UnableToConnectToPVException
from genie_python.genie_blockserver import BlockServer
from genie_python.genie_cachannel_wrapper import CaChannelWrapper as Wrapper
from genie_python.genie_dae import Dae
from genie_python.genie_experimental_data import GetExperimentData
from genie_python.genie_logging import GenieLogger
from genie_python.genie_logging import filter as logging_filter
from genie_python.genie_pre_post_cmd_manager import PrePostCmdManager
from genie_python.genie_wait_for_move import WaitForMoveController
from genie_python.genie_waitfor import WaitForController
from genie_python.utilities import (
    EnvironmentDetails,
    crc8,
    dehex_decompress_and_dejson,
    remove_field_from_pv,
)

if TYPE_CHECKING:
    from genie_python.genie import PVValue

RC_ENABLE = ":RC:ENABLE"
RC_LOW = ":RC:LOW"
RC_HIGH = ":RC:HIGH"


# Block names and its manager which automatically gets populated
# with the names of the current blocks
BLOCK_NAMES = BlockNames()
BLOCK_NAMES_MANAGER = BlockNamesManager(BLOCK_NAMES)


class API(object):
    def __init__(
        self, pv_prefix: str, globs: dict, environment_details: EnvironmentDetails | None = None
    ) -> None:
        """
        Constructor for the EPICS enabled API.

        Args:
            pv_prefix: used for prefixing the PV and block names
            globs: globals
            environment_details: details of the computer environment
        """
        self.waitfor = None  # type: WaitForController
        self.wait_for_move = None
        self.dae = None  # type: Dae
        self.blockserver = None  # type: BlockServer
        self.exp_data = None  # type: GetExperimentData
        self.inst_prefix = ""
        self.instrument_name = ""
        self.machine_name = ""
        self.localmod = None
        self.block_prefix = "CS:SB:"
        self.motion_suffix = "CS:MOT:MOVING"
        self.pre_post_cmd_manager = PrePostCmdManager()
        self.logger = GenieLogger()

        if environment_details is None:
            self._environment_details = EnvironmentDetails()
        else:
            self._environment_details = environment_details

        Wrapper.error_log_func = self.logger.log_ca_msg

        # disable CA error messages to console from disconnected PVs
        import ctypes

        if os.name == "nt":
            comdll = "COM.DLL"
        else:
            comdll = "libCom.so"
        try:
            hcom = ctypes.cdll.LoadLibrary(comdll)
            hcom.eltc(ctypes.c_int(0))
        except Exception as e:
            print("Unable to disable CA console errors from {}: {}".format(comdll, e))

    def get_instrument(self) -> str:
        """
        Gets the name of the local instrument (e.g. NDW1234, DEMO, EMMA-A)

        Returns:
            the name of the local instrument
        """
        return self.instrument_name

    def get_instrument_py_name(self) -> str:
        """
        Gets the name of the local instrument in lowercase and with "-" replaced with "_"

        Returns:
            the name of the local instrument in a python-friendly format
        """
        return self.instrument_name.lower().replace("-", "_")

    def _get_machine_details_from_identifier(self, machine_identifier: str) -> tuple[str, str, str]:
        """
        Gets the details of a machine by looking it up in the instrument list first.
        If there is no match it calculates the details as usual.

        Args:
            machine_identifier: should be the pv prefix but also accepts instrument name;
            if none defaults to computer host name

        Returns:
            The instrument name, machine name and pv_prefix based in the machine identifier
        """
        instrument_pv_prefix = "IN:"
        test_machine_pv_prefix = "TE:"

        instrument_machine_prefixes = ["NDX", "NDE"]
        test_machine_prefixes = ["NDH"]

        if machine_identifier is None:
            machine_identifier = self._environment_details.get_host_name()

        # machine_identifier needs to be uppercase for both 'NDXALF' and 'ndxalf' to be valid
        machine_identifier = machine_identifier.upper()

        # get the dehexed, decompressed list of instruments from the PV INSTLIST
        # then find the first match where pvPrefix equals the machine identifier
        # that's been passed to this function if it is not found instrument_details will be None
        instrument_details = None
        try:
            instrument_list = dehex_decompress_and_dejson(self.get_pv_value("CS:INSTLIST"))
            instrument_details = next(
                (inst for inst in instrument_list if inst["pvPrefix"] == machine_identifier), None
            )
        except UnableToConnectToPVException as error:
            print(
                "An exception occured while loading genie python:",
                error,
                "\nContinuing execution...",
            )

        if instrument_details is not None:
            instrument = instrument_details["name"]
        else:
            instrument = machine_identifier.upper()
            for p in (
                [instrument_pv_prefix, test_machine_pv_prefix]
                + instrument_machine_prefixes
                + test_machine_prefixes
            ):
                if machine_identifier.startswith(p):
                    instrument = machine_identifier.upper()[len(p) :].rstrip(":")
                    break

        if instrument_details is not None:
            machine = instrument_details["hostName"]
        elif machine_identifier.startswith(instrument_pv_prefix):
            machine = "NDX{0}".format(instrument)
        elif machine_identifier.startswith(test_machine_pv_prefix):
            machine = instrument
        else:
            machine = machine_identifier.upper()

        is_instrument = any(
            machine_identifier.startswith(p)
            for p in instrument_machine_prefixes + [instrument_pv_prefix]
        )
        pv_prefix = self._get_pv_prefix(instrument, is_instrument)

        return instrument, machine, pv_prefix

    def get_instrument_full_name(self) -> str:
        return self.machine_name

    def set_instrument(
        self, machine_identifier: str, globs: dict, import_instrument_init: bool = True
    ) -> None:
        """
        Set the instrument being used by setting the PV prefix or by the
        hostname if no prefix was passed.

        Will do some checking to allow you to pass instrument names in so.

        Args:
            machine_identifier: should be the pv prefix but also accepts
            instrument name; if none defaults to computer host name
            globs: globals
            import_instrument_init (bool): if True import the instrument init
                                           from the config area; otherwise don't
        """
        instrument, machine, pv_prefix = self._get_machine_details_from_identifier(
            machine_identifier
        )

        print("PV prefix is " + pv_prefix)
        self.inst_prefix = pv_prefix
        self.instrument_name = instrument
        self.machine_name = machine
        self.dae = Dae(self, pv_prefix)

        try:
            self.exp_data = GetExperimentData(machine)
        except Exception as e:
            error_message = (
                "Could not connect to database, RB numbers will not be accessible: {}".format(e)
            )
            self.logger.log_error_msg(error_message)
            print(error_message)
            self.exp_data = None

        self.wait_for_move = WaitForMoveController(self, pv_prefix + self.motion_suffix)
        self.waitfor = WaitForController(self)
        self.blockserver = BlockServer(self)
        BLOCK_NAMES_MANAGER.update_prefix(pv_prefix)

        # Set instrument for logging purposes
        logging_filter.instrument = instrument

        # Whatever machine we're on, try to initialize and fall back if unsuccessful
        self.init_instrument(instrument, machine, globs, import_instrument_init)

    def _get_pv_prefix(self, instrument: str, is_instrument: bool) -> str:
        """
        Create the pv prefix based on instrument name and whether it is an
        instrument or a dev machine

        Args:
            instrument: instrument name
            is_instrument: True is an instrument; False not an instrument

        Returns:
            string: the PV prefix
        """
        clean_instrument = instrument
        if clean_instrument.endswith(":"):
            clean_instrument = clean_instrument[:-1]
        if len(clean_instrument) > 8:
            clean_instrument = clean_instrument[0:6] + crc8(clean_instrument)

        self.instrument_name = clean_instrument

        if is_instrument:
            pv_prefix_prefix = "IN"
            print("THIS IS %s!" % self.instrument_name.upper())
        else:
            pv_prefix_prefix = "TE"
            print("THIS IS %s! (test machine)" % self.instrument_name.upper())
        return "{prefix}:{instrument}:".format(
            prefix=pv_prefix_prefix, instrument=self.instrument_name
        )

    def prefix_pv_name(self, name: str) -> str:
        """
        Adds the instrument prefix to the specified PV.
        """
        if self.inst_prefix is not None:
            return self.inst_prefix + name
        return name

    def init_instrument(
        self, instrument: str, machine_name: str, globs: dict, import_instrument_init: bool
    ) -> None:
        """
        Initialise an instrument using the default init file followed by the machine specific init.
        Args:
            instrument: instrument name to load from
            machine_name: machine name
            globs: current globals
            import_instrument_init: if True import the instrument init from the config area;
                                    otherwise don't
        """
        if import_instrument_init:
            instrument = instrument.lower().replace("-", "_")
            python_config_area = os.path.join(
                "C:" + os.sep, "Instrument", "Settings", "config", machine_name, "Python"
            )
            print(
                "Loading instrument scripts from: {}".format(
                    os.path.join(python_config_area, "inst")
                )
            )

            # Check instrument specific folder exists, if so add to sys path
            if os.path.isdir(python_config_area):
                sys.path.append(python_config_area)

            import importlib

            # Load the instrument init file
            self.localmod = importlib.import_module("init_{}".format(instrument))

            if self.localmod.__file__.endswith(".pyc"):
                file_loc = self.localmod.__file__[:-1]
            else:
                file_loc = self.localmod.__file__
            # execfile - this puts any imports in the init file into the globals namespace
            # Note: Anything loose in the module like print statements will be run twice
            exec(compile(open(file_loc).read(), file_loc, "exec"), globs)
            # Call the init command
            init_func = getattr(self.localmod, "init")
            init_func(machine_name)

    def set_pv_value(
        self,
        name: str,
        value: "PVValue",
        wait: bool = False,
        attempts: int = 3,
        is_local: bool = False,
    ) -> None:
        """
        Set the PV to a value.

        When setting a PV value this call should be used unless there is a special requirement.

        Args:
            name: the PV name
            value: the value to set. If this is None, do nothing.
            wait: wait for the value to be set before returning
            is_local (bool, optional): whether to automatically prepend the
                                       local inst prefix to the PV name
            attempts: number of attempts to try to set the pv value
        """
        if value is None:
            self.logger.log_info_msg(
                f"set_pv_value called with name={name} value={value} wait={wait}"
                f" is_local={is_local} attempts={attempts} ignoring because value is None"
            )
            return
        if is_local:
            if not name.startswith(self.inst_prefix):
                name = self.prefix_pv_name(name)
        self.logger.log_info_msg("set_pv_value %s %s" % (name, str(value)))

        while True:
            try:
                Wrapper.set_pv_value(name, value, wait=wait)
                return
            except Exception as e:
                attempts -= 1
                if attempts < 1:
                    self.logger.log_error_msg("set_pv_value exception {!r}".format(e))
                    raise e

    def get_pv_value(
        self,
        name: str,
        to_string: bool = False,
        attempts: int = 3,
        is_local: bool = False,
        use_numpy: bool | None = None,
    ) -> "PVValue":
        """
        Get the current value of the PV.

        When getting a PV value this call should be used unless there is a special requirement.

        Args:
            name: the PV name
            to_string (bool, optional): whether to cast it to a string
            attempts (int, optional): the number of times it tries to read the pv before
                                      throwing an exception if it
            can not
            is_local (bool, optional): whether to automatically prepend the local inst prefix
                                       to the PV name
            use_numpy (None|boolean): True use numpy to return arrays, False return a list;
                                      None for use the default
        """
        if is_local:
            if not name.startswith(self.inst_prefix):
                name = self.prefix_pv_name(name)

        if not self.pv_exists(name):
            raise UnableToConnectToPVException(name, "does not exist")

        while True:
            try:
                return Wrapper.get_pv_value(name, to_string, use_numpy=use_numpy)
            except Exception as e:
                attempts -= 1
                if attempts < 1:
                    raise e

    def pv_exists(self, name: str, fail_fast: bool = False, is_local: bool = False) -> bool:
        """
        See if the PV exists.

        Args:
            name (string): the name of the block
            fail_fast (bool, optional): if True the function will not attempt to wait for
                                        a disconnected PV
            is_local (bool, optional): whether to automatically prepend the local inst prefix
                                       to the PV name

        Returns:
            bool: True if the block exists
        """
        if is_local:
            if not name.startswith(self.inst_prefix):
                name = self.prefix_pv_name(name)
        if fail_fast:
            return Wrapper.pv_exists(name, 0)
        else:
            return Wrapper.pv_exists(name)

    def connected_pvs_in_list(self, pv_list: list[str], is_local: bool = False) -> list[str]:
        """
        Checks whether the specified PVs are connected.

        Args:
            pv_list (list): the list of PVs to check
            is_local (bool, optional): whether to automatically prepend the
                                       local inst prefix to the PV names

        Returns:
            bool: True if all PVs are connected
        """

        # do this with multiprocessing to speed up
        import multiprocessing.dummy as multiprocessing

        pool = multiprocessing.Pool()

        # make the mapping work with correct params for
        # def pv_exists(self, name, fail_fast=False, is_local=False):
        # to avoid this eror: def pv_exists(self, name, fail_fast=False, is_local=False):
        def pv_exists_wrapper(name: str) -> str | None:
            if self.pv_exists(name, fail_fast=False, is_local=is_local):
                return name
            else:
                return None

        connected_pv_list = [pv for pv in pool.map(pv_exists_wrapper, pv_list) if pv is not None]
        pool.close()
        pool.join()
        return connected_pv_list

    def reload_current_config(self) -> None:
        """
        Reload the current configuration.
        """
        self.blockserver.reload_current_config()

    def correct_blockname(self, name: str, add_prefix: bool = True) -> str:
        """
        Corrects the casing of the block.
        """
        for true_block_name in self.get_block_names():
            if name.lower() == true_block_name.lower():
                if add_prefix:
                    return self.inst_prefix + self.block_prefix + true_block_name
                else:
                    return true_block_name
        # If we get here then the block does not exist
        # but this should be picked up elsewhere
        return name

    def get_block_names(self) -> list[str]:
        """
        Gets a list of block names from the block name monitor.

        Note: does not include the prefix
        """
        return [name for name in BLOCK_NAMES.__dict__.keys()]

    def block_exists(self, name: str, fail_fast: bool = False) -> str | None:
        """
        Checks whether the block exists.

        Args:
            name (string): the name of the block
            fail_fast (bool): if True the function will not attempt to wait for a disconnected PV

        Note: this is case insensitive
        """
        return self.pv_exists(self.get_pv_from_block(name), fail_fast)

    def set_block_value(
        self,
        name: str,
        value: "PVValue" = None,
        runcontrol: bool | None = None,
        lowlimit: int | float | None = None,
        highlimit: int | float | None = None,
        wait: bool | None = False,
    ) -> None:
        """
        Sets a range of block values.
        """
        # Run pre-command
        if wait is not None and runcontrol is not None:
            # Cannot set both at the same time
            raise Exception(
                "Cannot enable or disable runcontrol at the same time as setting a wait"
            )

        if not self.pre_post_cmd_manager.cset_precmd(runcontrol=runcontrol, wait=wait):
            print("cset cancelled by pre-command")
            return

        full_name = self.get_pv_from_block(name)

        if lowlimit is not None and highlimit is not None:
            if lowlimit > highlimit:
                print(
                    "Low limit ({}) higher than high limit ({}), "
                    "swapping them around for you".format(lowlimit, highlimit)
                )
                lowlimit, highlimit = highlimit, lowlimit
            if wait and not lowlimit < value < highlimit:
                # Can only warn as may move through this range whilst changing
                print(
                    "Warning the range {} to {} does not cover setpoint of {}, "
                    "may wait forever".format(lowlimit, highlimit, value)
                )

        if value is not None:
            # Write to SP if it exists
            if self.pv_exists(full_name + ":SP"):
                self.set_pv_value(full_name + ":SP", value)
            else:
                self.set_pv_value(full_name, value)

        if wait:
            self.waitfor.start_waiting(name, value, lowlimit, highlimit)
            return

        if runcontrol is not None:
            enable = 1 if runcontrol else 0
            self.set_pv_value(full_name + RC_ENABLE, enable)

        # Set limits
        if lowlimit is not None:
            self.set_pv_value(full_name + RC_LOW, lowlimit)
        if highlimit is not None:
            self.set_pv_value(full_name + RC_HIGH, highlimit)

    def get_block_value(self, name: str, to_string: bool = False, attempts: int = 3) -> "PVValue":
        """
        Gets the current value for the block.
        """
        return self.get_pv_value(self.get_pv_from_block(name), to_string, attempts)

    def set_multiple_blocks(self, names: list[str], values: list["PVValue"]) -> None:
        """
        Sets values for multiple blocks.
        """
        # With LabVIEW we could set values then press go after all values are set
        # Not sure we are going to do something similar for EPICS
        temp = list(zip(names, values))
        # Set the values
        for name, value in temp:
            self.set_block_value(name, value)

    def get_block_units(self, block_name: str) -> str | None:
        """
        Get the physical measurement units associated with a block name.

        Parameters
        ----------
        block_name: name of the block

        Returns
        -------
        units of the block
        """

        pv_name = self.get_pv_from_block(block_name)
        if "." in pv_name:
            # Remove any headers
            pv_name = pv_name.split(".")[0]
        unit_name = pv_name + ".EGU"
        # pylint: disable=protected-access
        if not self.block_exists(block_name) and block_name.upper() not in (
            existing_block.upper() for existing_block in self.get_block_names()
        ):
            # If block doesn't exist, not found even in some form on the block server
            raise Exception(
                "No block with the name '{}' exists\nCurrent blocks are {}".format(
                    block_name, self.get_block_names()
                )
            )

        field_type = Wrapper.dbf_type_to_string(Wrapper.get_chan(pv_name).field_type())

        if field_type in ["DBF_STRING", "DBF_CHAR", "DBF_UCHAR", "DBF_ENUM"]:
            return None
        # Only return block units if PV field type is _not_ STRING, CHAR, UCHAR or ENUM
        # as they're unlikely to have .EGU fields
        return typing.cast(str | None, Wrapper.get_pv_value(unit_name))

    def _get_pars(
        self, pv_prefix_identifier: str, get_names_from_blockserver: Callable[[], list[str]]
    ) -> dict:
        """
        Get the current parameter values for a given pv subset as a dictionary.
        """
        names = get_names_from_blockserver()
        ans = {}
        if names is not None:
            for n in names:
                val = self.get_pv_value(self.prefix_pv_name(n))
                m = re.match(".+:" + pv_prefix_identifier + ":(.+)", n)
                if m is not None:
                    ans[m.groups()[0]] = val
                else:
                    self.logger.log_error_msg(
                        "Unexpected PV found whilst retrieving parameters: {0}".format(n)
                    )
        return ans

    def get_sample_pars(self) -> dict:
        """
        Get the current sample parameter values as a dictionary.
        """
        return self._get_pars("SAMPLE", self.blockserver.get_sample_par_names)

    def set_sample_par(self, name: str, value: "PVValue") -> None:
        """
        Set a new value for a sample parameter.

        Args:
            name: the name of the parameter to change
            value: the new value
        """
        names = self.blockserver.get_sample_par_names()
        if names is not None:
            for n in names:
                m = re.match(".+:SAMPLE:%s" % name.upper(), n)
                if m is not None:
                    # Found it!
                    self.set_pv_value(self.prefix_pv_name(n), value)
                    return
        raise Exception("Sample parameter %s does not exist" % name)

    def get_beamline_pars(self) -> dict:
        """
        Get the current beamline parameter values as a dictionary.
        """
        return self._get_pars("BL", self.blockserver.get_beamline_par_names)

    def set_beamline_par(self, name: str, value: "PVValue") -> None:
        """
        Set a new value for a beamline parameter.

        Args:
            name: the name of the parameter to change
            value: the new value
        """
        names = self.blockserver.get_beamline_par_names()
        if names is not None:
            for n in names:
                m = re.match(".+:BL:%s" % name.upper(), n)
                if m is not None:
                    self.set_pv_value(self.prefix_pv_name(n), value)
                    return
        raise Exception("Beamline parameter %s does not exist" % name)

    def get_runcontrol_settings(self, block_name: str) -> tuple[bool, float, float]:
        """
        Gets the current run-control settings for a block.

        Args:
            block_name: the full pv of the block

        Returns:
            tuple: (enabled, low_limit, high_limit)
        """
        try:
            block_pv = self.get_pv_from_block(block_name)
            enabled = self.get_pv_value(block_pv + RC_ENABLE) == "YES"
            low_limit = self.get_pv_value(block_pv + RC_LOW)
            high_limit = self.get_pv_value(block_pv + RC_HIGH)
            return enabled, low_limit, high_limit
        except UnableToConnectToPVException:
            return "UNKNOWN", "UNKNOWN", "UNKNOWN"

    def check_alarms(self, blocks: list[str]) -> tuple[list[str], list[str], list[str]]:
        """
        Checks whether the specified blocks are in alarm.

        Args:
            blocks (list): the blocks to check

        Returns:
            list, list, list: the blocks in minor, major and invalid alarm
        """
        alarm_states = self._get_fields_from_blocks(blocks, "SEVR", "alarm state")
        minor = [t[0] for t in alarm_states if t[1] == "MINOR"]
        major = [t[0] for t in alarm_states if t[1] == "MAJOR"]
        invalid = [t[0] for t in alarm_states if t[1] == "INVALID"]
        return minor, major, invalid

    def check_limit_violations(self, blocks: list[str]) -> list[str]:
        """
        Checks whether the specified blocks have soft limit violations.

        Args:
            blocks (list): the blocks to check

        Returns:
            list: the blocks which have soft limit violations
        """
        violation_states = self._get_fields_from_blocks(blocks, "LVIO", "limit violation")
        return [t[0] for t in violation_states if t[1] == 1]

    def _get_fields_from_blocks(
        self, blocks: list[str], field_name: str, field_description: str
    ) -> list["PVValue"]:
        field_values = list()
        for block in blocks:
            if self.block_exists(block):
                block_name = self.correct_blockname(block, False)
                full_block_pv = self.get_pv_from_block(block)
                try:
                    field_value = self.get_pv_value(full_block_pv + "." + field_name, attempts=1)
                    field_values.append([block_name, field_value])
                except IOError:
                    # Could not get value
                    print("Could not get {} for block: {}".format(field_description, block))
            else:
                print("Block {} does not exist, so ignoring it".format(block))

        return field_values

    def get_pv_from_block(self, block_name: str) -> str:
        """
        Get the full gateway level PV name for a given block.

        Args:
        block_name (str): The name of a block

        Returns:
            pv_name (str): The pv name as a string

        """
        return self.inst_prefix + self.block_prefix + block_name.upper()

    def _alert_http_request(
        self,
        message: str,
        emails: str | None = None,
        mobiles: str | None = None,
        inst: str | None = None,
    ) -> None:
        if emails is None and mobiles is None and inst is None:
            self.logger.log_info_msg(
                "_alert_http_request called with no destinations, doing nothing."
            )
            return

        pw = self.get_pv_value("CS:AC:ALERTS:PW:SP", to_string=True, is_local=True)
        if not pw:
            raise ValueError(
                "Unable to send sms as cannot get ALERTS password. "
                "Contact ISIS experiment controls for assistance."
            )
        assert isinstance(pw, str)
        req = {
            "message": message,
            "source": "GENIE",
            "type": "ALERT",
            "pw": pw,
        }

        if emails is not None:
            req["emails"] = emails
        if mobiles is not None:
            req["mobiles"] = mobiles
        if inst is not None:
            req["inst"] = inst

        address = self.get_pv_value("CS:AC:ALERTS:URL:SP", to_string=True, is_local=True)
        if not address:
            raise ValueError(
                "Unable to send sms as cannot get ALERTS http url. "
                "Contact ISIS experiment controls for assistance."
            )
        assert isinstance(address, str)

        req = urllib.request.Request(url=address, data=urllib.parse.urlencode(req).encode("utf-8"))
        with contextlib.closing(urllib.request.urlopen(req)) as f:
            print(f.read())

    def send_sms(self, phone_num: str, message: str) -> None:
        """
        Sends an SMS message to a phone number.

        Args:
            phone_num (string): The phone number to send the SMS to.
            message (string): The message to send.
        """
        try:
            self._alert_http_request(mobiles=phone_num, message=message)
        except Exception as e:
            raise Exception("Could not send SMS: {}".format(e))

    def send_email(self, address: str, message: str) -> None:
        """
        Sends an email to a given address.

        Args:
            address (string): The email address to use.
            message (string): The message to send.
        """
        try:
            self._alert_http_request(emails=address, message=message)
        except Exception as e:
            raise Exception("Could not send email: {}".format(e))

    def send_alert(self, message: str, inst: str) -> None:
        """
        Sends an alert message for a specified instrument.

        Args:
            message (string): The message to send.
            inst (string): The instrument to generate an alert for.
        """
        if inst is None:
            inst = self.instrument_name
        try:
            self._alert_http_request(inst=inst, message=message)
        except Exception as e:
            raise Exception("Could not send alert: {}".format(e))

    def get_alarm_from_block(self, block: str) -> str:
        """
        Gets the alarm status from a single block

        args:
            block (str): the name of the block to get the alarm status of

        returns:
            (str) the alarm status as a string.
            One of "NO_ALARM", "MINOR", "MAJOR", "INVALID", or "UNKNOWN" if the
            alarm status could not be determined
        """

        return self.get_pv_alarm(self.get_pv_from_block(block))

    def get_pv_alarm(self, pv_name: str) -> str:
        """
        Gets the alarm status of a pv.

        args:
            pv_name (str): the name of the pv to get the alarm status of

        returns:
            (str) the alarm status as a string.
            One of "NO_ALARM", "MINOR", "MAJOR", "INVALID", or "UNKNOWN" if the
            alarm status could not be determined
        """
        try:
            return self.get_pv_value(
                "{}.SEVR".format(remove_field_from_pv(pv_name)), to_string=True
            )
        except Exception:
            return "UNKNOWN"

    def get_block_data(self, block: str, fail_fast: bool = False) -> dict:
        """
        Gets the useful values associated with a block.

        The value will be None if the block is not "connected".

        Args:
            block (string): the name of the block
            fail_fast (bool): if True the function will not attempt to wait for a disconnected PV

        Returns
            dict: details about about the block. Contains:
                name - name of the block
                value - value of the block
                unit - physical units of the block
                connected - True if connected; False otherwise
                runcontrol - NO not in runcontrol, YES otherwise
                lowlimit - run control low limit set
                highlimit - run control high limit set
                alarm - the alarm status of the block
        """
        ans = OrderedDict()
        ans["connected"] = True

        if not self.block_exists(block, fail_fast):
            # Check if block exists in some form in the block server
            if block.upper() in (
                existing_block.upper() for existing_block in self.get_block_names()
            ):
                ans["connected"] = False
            else:
                # Can't find block at all
                raise Exception(
                    "No block with the name '{}' exists\nCurrent blocks are {}".format(
                        block, self.get_block_names()
                    )
                )

        ans["name"] = block
        ans["value"] = self.get_block_value(block) if ans["connected"] else None

        try:
            ans["unit"] = self.get_block_units(block) if ans["connected"] else None
        except UnableToConnectToPVException:
            ans["unit"] = "Unable to connect to .EGU PV"

        ans["runcontrol"], ans["lowlimit"], ans["highlimit"] = self.get_runcontrol_settings(block)

        fail_fast_and_disconnected = fail_fast and not ans["connected"]
        ans["alarm"] = "UNKNOWN" if fail_fast_and_disconnected else self.get_alarm_from_block(block)

        return ans
