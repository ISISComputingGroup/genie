from __future__ import absolute_import, print_function

import json
import os
import re
import xml.etree.ElementTree as ET
import zlib
from binascii import hexlify
from builtins import str
from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime, timedelta
from io import open
from stat import S_IREAD, S_IWUSR
from time import sleep, strftime
from typing import TYPE_CHECKING, cast

import numpy as np
import numpy.typing as npt
import psutil

try:
    from CaChannel._ca import AlarmCondition, AlarmSeverity
except ImportError:
    # Note: caffi dynamically added to dependencies by CaChannel if not using built backend.
    from caffi.ca import AlarmCondition, AlarmSeverity  # type: ignore[reportMissingImports]

from genie_python.genie_cachannel_wrapper import CaChannelWrapper
from genie_python.genie_change_cache import ChangeCache
from genie_python.utilities import (
    compress_and_hex,
    dehex_and_decompress,
    get_correct_path,
    require_runstate,
    waveform_to_string,
)

if TYPE_CHECKING:
    from genie_python.genie import PVValue
    from genie_python.genie_epics_api import API

## for beginrun etc. there exists both the PV specified here and also a PV with
## an '_' appended that skips the additional pre/post commands defined in
## the IOC write and is used for when prepost=False is specified for command
DAE_PVS_LOOKUP = {
    "runstate": "DAE:RUNSTATE",
    "runstate_str": "DAE:RUNSTATE_STR",
    "beginrun": "DAE:BEGINRUNEX",
    "abortrun": "DAE:ABORTRUN",
    "pauserun": "DAE:PAUSERUN",
    "resumerun": "DAE:RESUMERUN",
    "endrun": "DAE:ENDRUN",
    "recoverrun": "DAE:RECOVERRUN",
    "saverun": "DAE:SAVERUN",
    "updaterun": "DAE:UPDATERUN",
    "storerun": "DAE:STORERUN",
    "snapshot": "DAE:SNAPSHOTCRPT",
    "period_rbv": "DAE:PERIOD:RBV",
    "period": "DAE:PERIOD",
    "runnumber": "DAE:RUNNUMBER",
    "numperiods": "DAE:NUMPERIODS",
    "events": "DAE:EVENTS",
    "mevents": "DAE:MEVENTS",
    "totalcounts": "DAE:TOTALCOUNTS",
    "goodframes": "DAE:GOODFRAMES",
    "goodframesperiod": "DAE:GOODFRAMES_PD",
    "rawframes": "DAE:RAWFRAMES",
    "uamps": "DAE:GOODUAH",
    "histmemory": "DAE:HISTMEMORY",
    "spectrasum": "DAE:SPECTRASUM",
    "uampsperiod": "DAE:GOODUAH_PD",
    "title": "DAE:TITLE",
    "title_sp": "DAE:TITLE:SP",
    "display_title": "DAE:TITLE:DISPLAY",
    "rbnum": "ED:RBNUMBER",
    "rbnum_sp": "ED:RBNUMBER:SP",
    "period_sp": "DAE:PERIOD:SP",
    "users": "ED:SURNAME",
    "users_table_sp": "ED:USERNAME:SP",
    "users_dae_sp": "ED:USERNAME:DAE:SP",
    "users_surname_sp": "ED:SURNAME",
    "starttime": "DAE:STARTTIME",
    "npratio": "DAE:NPRATIO",
    "timingsource": "DAE:DAETIMINGSOURCE",
    "periodtype": "DAE:PERIODTYPE",
    "isiscycle": "DAE:ISISCYCLE",
    "rawframesperiod": "DAE:RAWFRAMES_PD",
    "runduration": "DAE:RUNDURATION",
    "rundurationperiod": "DAE:RUNDURATION_PD",
    "numtimechannels": "DAE:NUMTIMECHANNELS",
    "memoryused": "DAE:DAEMEMORYUSED",
    "numspectra": "DAE:NUMSPECTRA",
    "monitorcounts": "DAE:MONITORCOUNTS",
    "monitorspectrum": "DAE:MONITORSPECTRUM",
    "periodseq": "DAE:PERIODSEQ",
    "beamcurrent": "DAE:BEAMCURRENT",
    "totaluamps": "DAE:TOTALUAMPS",
    "totaldaecounts": "DAE:TOTALDAECOUNTS",
    "monitorto": "DAE:MONITORTO",
    "monitorfrom": "DAE:MONITORFROM",
    "countrate": "DAE:COUNTRATE",
    "eventmodefraction": "DAE:EVENTMODEFRACTION",
    "daesettings": "DAE:DAESETTINGS",
    "daesettings_sp": "DAE:DAESETTINGS:SP",
    "tcbsettings": "DAE:TCBSETTINGS",
    "tcbsettings_sp": "DAE:TCBSETTINGS:SP",
    "periodsettings": "DAE:HARDWAREPERIODS",
    "periodsettings_sp": "DAE:HARDWAREPERIODS:SP",
    "getspectrum_x": "DAE:SPEC:{:d}:{:d}:X",
    "getspectrum_x_size": "DAE:SPEC:{:d}:{:d}:X.NORD",
    "getspectrum_y": "DAE:SPEC:{:d}:{:d}:Y",
    "getspectrum_y_size": "DAE:SPEC:{:d}:{:d}:Y.NORD",
    "getspectrum_yc": "DAE:SPEC:{:d}:{:d}:YC",
    "getspectrum_yc_size": "DAE:SPEC:{:d}:{:d}:YC.NORD",
    "errormessage": "DAE:ERRMSGS",
    "allmessages": "DAE:ALLMSGS",
    "statetrans": "DAE:STATETRANS",
    "wiringtables": "DAE:WIRINGTABLES",
    "spectratables": "DAE:SPECTRATABLES",
    "detectortables": "DAE:DETECTORTABLES",
    "periodfiles": "DAE:PERIODFILES",
    "set_veto_true": "DAE:VETO:ENABLE:SP",
    "set_veto_false": "DAE:VETO:DISABLE:SP",
    "simulation_mode": "DAE:SIM_MODE",
    "state_changing": "DAE:STATE:CHANGING",
    "specintegrals": "DAE:SPECINTEGRALS",
    "specintegrals_size": "DAE:SPECINTEGRALS.NORD",
    "specdata": "DAE:SPECDATA",
    "specdata_size": "DAE:SPECDATA.NORD",
}

DAE_CONFIG_FILE_PATHS = [
    r"C:\Labview modules\dae\icp_config.xml",
    r"C:\Instrument\Apps\EPICS\ICP_Binaries\icp_config.xml",
]

END_NOW_FILE_PATH = "C:\\data\\end_now.dae"

CLEAR_VETO = "clearall"
SMP_VETO = "smp"
TS2_VETO = "ts2"
HZ50_VETO = "hz50"
EXT0_VETO = "ext0"
EXT1_VETO = "ext1"
EXT2_VETO = "ext2"
EXT3_VETO = "ext3"
FIFO_VETO = "fifo"


class Dae(object):
    """
    Communications with the DAE pvs.
    """

    def __init__(self, api: "API", prefix: str = "") -> None:
        """
        The constructor.

        Args:
            api(genie_python.genie_epics_api.API): the API used for communication
            prefix: the PV prefix
        """
        self.api = api
        self.inst_prefix = prefix
        self.in_change = False
        self.change_cache = ChangeCache()
        self.verbose = False

        # this is the default value to ensure dae settings are
        # written before returning, only changed for testing
        self.wait_for_completion_callback_dae_settings = True

    def _prefix_pv_name(self, name: str) -> str:
        """
        Adds the prefix to the PV name.

        Args:
            name: the name to be prefixed

        Returns:
            string: the full PV name
        """
        if self.inst_prefix is not None:
            name = self.inst_prefix + name
        return name

    def _get_dae_pv_name(self, name: str, base: bool = False) -> str:
        """
        Retrieves the full pv name of a DAE variable.

        Args:
            name: the short name for the DAE variable
            base: return the underlying action PV name

        Returns:
            string: the full PV name
        """
        if base:
            return self._prefix_pv_name(DAE_PVS_LOOKUP[name.lower()]) + "_"
        else:
            return self._prefix_pv_name(DAE_PVS_LOOKUP[name.lower()])

    def _get_pv_value(
        self, name: str, to_string: bool = False, use_numpy: bool | None = None
    ) -> "PVValue":
        """
        Gets a PV's value.

        Args:
            name: the PV name
            to_string: whether to convert the value to a string
            use_numpy (None|boolean): True use numpy to return arrays, False return a list;
                                      None for use the default

        Returns:
            object: the PV's value
        """
        return self.api.get_pv_value(name, to_string, use_numpy=use_numpy)

    def _set_pv_value(self, name: str, value: "PVValue", wait: bool = False) -> None:
        """
        Sets a PV value via the API.

        Args:
            name: the PV name
            value: the value to set
            wait: whether to wait for it to be set before returning
        """
        self.api.set_pv_value(name, value, wait)

    def _check_for_runstate_error(self, pv: str, header: str = "") -> None:
        """
        Check for errors on the run state PV.

        Args:
            pv: the PV name
            header: information to include in the exception raised.

        Raises:
            Exception: if there is an error on the specified PV

        """
        status = self._get_pv_value(pv + ".STAT", to_string=True)
        if status != "NO_ALARM":
            raise Exception(
                "{} {}".format(
                    header.strip(),
                    self._get_pv_value(self._get_dae_pv_name("errormessage"), to_string=True),
                )
            )

    def _print_verbose_messages(self) -> None:
        """
        Prints all the messages.
        """
        msgs = self._get_pv_value(self._get_dae_pv_name("allmessages"), to_string=True)
        print(msgs)

    def _write_to_end_now_file(self, file_content: str) -> None:
        """
        Creates the end_now file if it doesn't exist and writes text to it, overwriting
        any existing content

        Args:
            file_content: the new file content
        """
        with open(END_NOW_FILE_PATH, "w+") as f:
            f.write(file_content)

    def set_verbose(self, verbose: bool) -> None:
        """
        Sets the verbosity of the DAE messages printed

        Args:
            verbose: bool setting

        Raise:
            Exception: if the supplied value is not a bool
        """
        if isinstance(verbose, bool):
            self.verbose = verbose
            if verbose:
                print("Setting DAE messages to verbose mode")
            else:
                print("Setting DAE messages to non-verbose mode")
        else:
            raise Exception("Value must be boolean")

    @require_runstate(["SETUP"])
    def begin_run(
        self,
        period: int | None = None,
        meas_id: str | None = None,
        meas_type: str | None = None,
        meas_subid: str | None = None,
        sample_id: str | None = None,
        delayed: bool = False,
        quiet: bool = False,
        paused: bool = False,
        prepost: bool = True,
    ) -> None:
        """Starts a data collection run.

        Args:
            period - the period to begin data collection in [optional]
            meas_id - the measurement id [optional]
            meas_type - the type of measurement [optional]
            meas_subid - the measurement sub-id[optional]
            sample_id - the sample id [optional]
            delayed - puts the period card to into delayed start mode [optional]
            quiet - suppress the output to the screen [optional]
            paused - begin in the paused state [optional]
            prepost - run pre and post commands [optional]
        """
        if self.in_change:
            raise Exception("Cannot start in CHANGE mode, type change_finish()")

        # Set sample parameters
        sample_pars = {
            "MEAS:ID": meas_id,
            "MEAS:TYPE": meas_type,
            "MEAS:SUBID": meas_subid,
            "ID": sample_id,
        }
        for pv, value in sample_pars.items():
            if value is not None:
                self.api.set_sample_par(pv, str(value))

        # Check PV exists
        val = self._get_pv_value(self._get_dae_pv_name("beginrun"))
        if val is None:
            raise Exception("begin_run: could not connect to DAE")

        if period is not None:
            # Set the period before starting the run
            self.set_period(period)

        run_number = self.get_run_number()
        if not quiet:
            if self.get_simulation_mode():
                self.simulation_mode_warning()
            print("** Beginning Run {} at {}".format(run_number, strftime("%H:%M:%S %d/%m/%y ")))
            ## don't fail begin() if we are unabel to print rb/user details
            try:
                print(
                    "The following details will currently be used to determine"
                    "ownership of the data file"
                )
                print("*  Proposal Number: {}".format(self.get_rb_number()))
                print("*  Experiment Team: {}".format(self.get_users()))
                print("If this is incorrect, you can change it any time before the run is ENDed\n")
            except Exception as e:
                print(f"WARNING: Unable to read RB/Users from service: {e}")
        self.api.logger.log_info_msg(f"BEGIN: run number: {run_number}")
        try:
            self.api.logger.log_info_msg(
                f"BEGIN: Proposal number: {self.get_rb_number()} Team: {self.get_users()}"
            )
        except Exception as e:
            self.api.logger.log_error_msg(f"BEGIN: Unable to read RB/Users from service: {e}")

        # By choosing the value sent to the begin PV it can set pause and/or delayed
        options = 0
        if paused:
            options += 1
        if delayed:
            options += 2

        _cancel_monitor_fn = None
        try:

            def callback_function(
                message: str, severity: AlarmSeverity, status: AlarmCondition
            ) -> None:
                """
                Args:
                    message: the error message from the DAE as character waveform
                    severity: required by the CaChannelWrapper.add_monitor
                    status: required by the CaChannelWrapper.add_monitor
                """
                message = waveform_to_string(message)
                if message:
                    print("ISISICP error: {}".format(message))

            _cancel_monitor_fn = CaChannelWrapper.add_monitor(
                self._get_dae_pv_name("errormessage"), callback_function
            )
            # actually do begin
            self._set_pv_value(
                self._get_dae_pv_name("beginrun", base=not prepost), options, wait=True
            )
        finally:
            if _cancel_monitor_fn is not None:
                _cancel_monitor_fn()

    def simulation_mode_warning(self) -> None:
        """
        Warn user they are in simulation mode.
        """
        print("\n=========== RUNNING IN SIMULATION MODE ===========\n")
        print("Simulation mode can be stopped using:               \n")
        print("         >>>set_dae_simulation_mode(False)          \n")
        print("==================================================\n")

    def post_begin_check(self, verbose: bool = False) -> None:
        """
        Checks the BEGIN PV for errors after beginning a run.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("beginrun", base=True), "BEGIN")
        if verbose or self.verbose:
            self._print_verbose_messages()

    @require_runstate(["RUNNING", "VETOING", "WAITING", "PAUSED"])
    def abort_run(self, prepost: bool = True) -> None:
        """
        Abort the current run.
            prepost - run pre and post commands [optional]
        """
        print(
            (
                "** Aborting Run {} at {} "
                "(the run will not be saved, call g.recover() to undo this)".format(
                    self.get_run_number(), strftime("%H:%M:%S %d/%m/%y ")
                )
            )
        )
        self._set_pv_value(self._get_dae_pv_name("abortrun", base=not prepost), 1, wait=True)

    def post_abort_check(self, verbose: bool = False) -> None:
        """
        Checks the ABORT PV for errors after aborting a run.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("abortrun", base=True), "ABORT")
        if verbose or self.verbose:
            self._print_verbose_messages()

    @require_runstate(["RUNNING", "VETOING", "WAITING", "PAUSED", "ENDING"])
    def end_run(
        self,
        verbose: bool = False,
        quiet: bool = False,
        immediate: bool = False,
        prepost: bool = True,
    ) -> None:
        """
        End the current run.

        Args:
            verbose: whether to print verbosely
            quiet: suppress the output to the screen [optional]
            immediate: end immediately, without waiting for a period sequence to finish [optional]
            prepost: run pre and post commands [optional]
        """
        if self.get_run_state() == "ENDING" and not immediate:
            print("Please specify the 'immediate=True' flag to end a run while in the ENDING state")
            return

        run_number = self.get_run_number()
        if not quiet:
            print(("** Ending Run {} at {}".format(run_number, strftime("%H:%M:%S %d/%m/%y "))))

        self.api.logger.log_info_msg(f"END: run number: {run_number}")
        try:
            self.api.logger.log_info_msg(
                f"END: Proposal number: {self.get_rb_number()} Team: {self.get_users()}"
            )
        except Exception as e:
            self.api.logger.log_error_msg(f"END: Unable to read RB/Users from service: {e}")

        if immediate:
            self._write_to_end_now_file("1")

        self._set_pv_value(self._get_dae_pv_name("endrun", base=not prepost), 1, wait=True)
        if verbose or self.verbose:
            self._print_verbose_messages()

    def post_end_check(self, verbose: bool = False) -> None:
        """
        Checks the END PV for errors after ending a run.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("endrun", base=True), "END")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def recover_run(self) -> None:
        """
        Recovers the run if it has been aborted.

        The command should be run before the next run is started.
        Note: the run will be recovered in the paused state.
        """
        self._set_pv_value(self._get_dae_pv_name("recoverrun"), 1, wait=True)

    def post_recover_check(self, verbose: bool = False) -> None:
        """
        Checks the RECOVER PV for errors after recovering a run.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("recoverrun"), "RECOVER")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def update_store_run(self) -> None:
        """
        Performs an update and a store operation in a combined operation.

        This is more efficient than doing the commands separately.
        """
        print(
            ("** Saving Run {} at {}".format(self.get_run_number(), strftime("%H:%M:%S %d/%m/%y ")))
        )
        self._set_pv_value(self._get_dae_pv_name("saverun"), 1, wait=True)

    def post_update_store_check(self, verbose: bool = False) -> None:
        """
        Checks the associated PV for errors after an update store.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("saverun"), "SAVE")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def update_run(self) -> None:
        """
        Data is loaded from the DAE into the computer memory, but is not written to disk.
        """
        self._set_pv_value(self._get_dae_pv_name("updaterun"), 1, wait=True)

    def post_update_check(self, verbose: bool = False) -> None:
        """
        Checks the associated PV for errors after an update.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("updaterun"), "UPDATE")
        if verbose or self.verbose:
            self._print_verbose_messages()

    @require_runstate(["RUNNING", "VETOING", "WAITING", "PAUSED"])
    def store_run(self) -> None:
        """
        Data loaded into memory by a previous update_run command is now written to disk.
        """
        self._set_pv_value(self._get_dae_pv_name("storerun"), 1, wait=True)

    def post_store_check(self, verbose: bool = False) -> None:
        """
        Checks the associated PV for errors after a store.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("storerun"), "STORE")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def snapshot_crpt(self, filename: str) -> None:
        """
        Save a snapshot of the CRPT.

        Args:
            filename - the name and location to save the file(s) to
        """
        self._set_pv_value(self._get_dae_pv_name("snapshot"), filename, wait=True)

    def post_snapshot_check(self, verbose: bool = False) -> None:
        """
        Checks the associated PV for errors after a snapshot.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("snapshot"), "SNAPSHOTCRPT")
        if verbose or self.verbose:
            self._print_verbose_messages()

    @require_runstate(["RUNNING", "VETOING", "WAITING", "PAUSING"])
    def pause_run(self, immediate: bool = False, prepost: bool = True) -> None:
        """
        Pause the current run.

        Args:
            immediate: pause immediately, without waiting for a period sequence to complete
            prepost: run pre and post commands
        """
        if self.get_run_state() == "PAUSING" and not immediate:
            print(
                "Please specify the 'immediate=True' flag to pause a run while in the PAUSING state"
            )
            return

        print(
            (
                "** Pausing Run {} at {}".format(
                    self.get_run_number(), strftime("%H:%M:%S %d/%m/%y ")
                )
            )
        )

        if immediate:
            self._write_to_end_now_file("1")

        self._set_pv_value(self._get_dae_pv_name("pauserun", base=not prepost), 1, wait=True)

    def post_pause_check(self, verbose: bool = False) -> None:
        """
        Checks the PAUSE PV for errors after pausing.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("pauserun", base=True), "PAUSE")
        if verbose or self.verbose:
            self._print_verbose_messages()

    @require_runstate(["PAUSED"])
    def resume_run(self, prepost: bool = True) -> None:
        """
        Resume the current run after it has been paused.
            prepost - run pre and post commands [optional]
        """
        print(
            (
                "** Resuming Run {} at {}".format(
                    self.get_run_number(), strftime("%H:%M:%S %d/%m/%y ")
                )
            )
        )
        self._set_pv_value(self._get_dae_pv_name("resumerun", base=not prepost), 1, wait=True)

    def post_resume_check(self, verbose: bool = False) -> None:
        """
        Checks the RESUME PV for errors after resuming.

        Args:
            verbose: whether to print verbosely
        """
        self._check_for_runstate_error(self._get_dae_pv_name("resumerun", base=True), "RESUME")
        if verbose or self.verbose:
            self._print_verbose_messages()

    def get_run_state(self) -> str:
        """
        Gets the current state of the DAE.

        Note: this value can take a few seconds to update after a change of state.

        Returns:
            string: the current run state

        Raises:
            Exception: if cannot retrieve value
        """
        try:
            return self._get_pv_value(self._get_dae_pv_name("runstate"), to_string=True)
        except IOError:
            raise IOError("get_run_state: could not get run state")

    def get_run_number(self) -> str:
        """
        Gets the current run number.

        Returns:
            string: the current run number
        """
        return self._get_pv_value(self._get_dae_pv_name("runnumber"))

    def get_period_type(self) -> str:
        """
        Gets the period type.

        Returns:
            string: the period type
        """
        return self._get_pv_value(self._get_dae_pv_name("periodtype"))

    def get_period_seq(self) -> int:
        """
        Gets the period sequence.

        Returns:
            object: the period sequence
        """
        return self._get_pv_value(self._get_dae_pv_name("periodseq"))

    def get_period(self) -> int:
        """
        Gets  the current period number.

        Returns:
            int: the current period
        """
        return self._get_pv_value(self._get_dae_pv_name("period"))

    def get_num_periods(self) -> int:
        """
        Gets the number of periods.

        Returns:
            int: the number of periods
        """
        return cast(int, self._get_pv_value(self._get_dae_pv_name("numperiods")))

    def set_period(self, period: int) -> None:
        """
        Change to the specified period.

        Args:
            period: the number of the period to change to

        Raises:
            IOError: if the DAE can not set the period to the given number.
        """
        run_state = self.get_run_state()
        if run_state == "SETUP" or run_state == "PAUSED":
            self._set_pv_value(self._get_dae_pv_name("period_sp"), period, wait=True)

            if self.api.get_pv_alarm(self._get_dae_pv_name("period_sp")) == "INVALID":
                raise IOError(
                    f"You are trying to set an invalid period number {period}! "
                    f"The number must be between 1 and {self.get_num_periods()}."
                )
        else:
            raise ValueError("Cannot change period whilst running")

    def get_uamps(self, period: bool = False) -> float:
        """
        Returns the current number of micro-amp hours.

        Args:
            period: whether to return the micro-amp hours for the current period [optional]
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("uampsperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("uamps"))

    def get_events(self) -> int:
        """
        Gets the total number of events for all the detectors.

        Returns:
            int: the total number of events
        """
        return self._get_pv_value(self._get_dae_pv_name("events"))

    def get_mevents(self) -> float:
        """
        Gets the total number of millions of events for all the detectors.

        Returns:
            float: the total number of millions of events
        """
        return self._get_pv_value(self._get_dae_pv_name("mevents"))

    def get_total_counts(self) -> int:
        """
        Gets the total counts for the current run.

        Returns:
            int: the total counts
        """
        return self._get_pv_value(self._get_dae_pv_name("totalcounts"))

    def get_good_frames(self, period: bool = False) -> int:
        """
        Gets the current number of good frames.

        Args:
            period: whether to get for the current period only [optional]

        Returns:
            int: the number of good frames
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("goodframesperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("goodframes"))

    def get_raw_frames(self, period: bool = False) -> int:
        """
        Gets the current number of raw frames.

        Args:
            period: whether to get for the current period only [optional]

        Returns:
            int: the number of raw frames
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("rawframesperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("rawframes"))

    def sum_all_dae_memory(self) -> int:
        """
        Gets the sum of the counts in the DAE.

        Returns:
            int: the sum
        """
        return self._get_pv_value(self._get_dae_pv_name("histmemory"))

    def get_memory_used(self) -> int:
        """
        Gets the DAE memory used.

        Returns:
            int: the memory used
        """
        return self._get_pv_value(self._get_dae_pv_name("memoryused"))

    def sum_all_spectra(self) -> int:
        """
        Returns the sum of all the spectra in the DAE.

        Returns:
            int: the sum of spectra
        """
        return self._get_pv_value(self._get_dae_pv_name("spectrasum"))

    def get_num_spectra(self) -> int:
        """
        Gets the number of spectra.

        Returns:
            int: the number of spectra
        """
        return cast(int, self._get_pv_value(self._get_dae_pv_name("numspectra")))

    def get_rb_number(self) -> str:
        """
        Gets the RB number for the current run.

        Returns:
            string: the current RB number
        """
        return self._get_pv_value(self._get_dae_pv_name("rbnum"))

    def set_rb_number(self, rbno: str) -> None:
        """
        Set the RB number for the current run.

        Args:
            rbno (str): the new RB number
        """
        self._set_pv_value(self._get_dae_pv_name("rbnum_sp"), rbno)
        self.api.logger.log_info_msg(f"Proposal number changed to: {rbno}")

    def get_title(self) -> str:
        """
        Gets the title for the current run.

        Returns
            string: the current title
        """
        return self._get_pv_value(self._get_dae_pv_name("title"), to_string=True)

    def set_title(self, title: str) -> None:
        """
        Set the title for the current/next run.

        Args:
            title: the title to set
        """
        self._set_pv_value(self._get_dae_pv_name("title_sp"), title, wait=True)
        self.api.logger.log_info_msg(f"Title changed to: {title}")

    def get_display_title(self) -> bool:
        """
        Gets the display title status for the current run.

        Returns
            boolean: the current display title status
        """
        return self._get_pv_value(self._get_dae_pv_name("display_title"))

    def set_display_title(self, display_title: bool) -> None:
        """
        Set the display title status for the current/next run.

        Args:
            display_title: the display title status to set
        """
        self._set_pv_value(self._get_dae_pv_name("display_title"), display_title, wait=True)

    def get_users(self) -> str:
        """
        Gets the users for the current run.

        Returns:
            string: the names
        """
        try:
            # Data comes as comma separated list
            raw = str(self._get_pv_value(self._get_dae_pv_name("users_dae_sp"), to_string=True))
            names_list = [x.strip() for x in raw.split(",")]
            if len(names_list) > 1:
                last = names_list.pop(-1)
                names = ", ".join(names_list)
                names += " and " + last
                return names
            else:
                # Will throw if empty - that is okay
                return names_list[0]
        except Exception:
            return ""

    def set_users(self, users: str) -> None:
        """
        Set the users for the current run.

        Args:
            users: the users as a comma-separated string
        """
        split_users = users.split(",") if users else []
        table_data = json.dumps([{"name": user.strip()} for user in split_users])
        # Send just the username and database server will clear the table if only user is set
        self._set_pv_value(
            self._get_dae_pv_name("users_table_sp"), compress_and_hex(table_data), True
        )
        self.api.logger.log_info_msg(f"Users set to: {users}")

    def get_starttime(self) -> str:
        """
        Gets the start time for the current run.

        Returns
            string: the start time
        """
        return self._get_pv_value(self._get_dae_pv_name("starttime"))

    @require_runstate(
        ["PAUSING", "BEGINNING", "ABORTING", "RESUMING", "RUNNING", "VETOING", "WAITING", "PAUSED"]
    )
    def get_time_since_begin(self, get_timedelta: bool) -> float | timedelta:
        """
        Gets the time since start of the current run in seconds or in datetime
        Args:
            get_timedelta (bool): If true return the value as a datetime object,
                                  otherwise return seconds (defaults to false)
        Returns
            integer: the time since start in seconds if get_datetime is False
            datetime: the time since start in (Year-Month-Day  Hour:Minute:Second)
                      format if get_datetime is True
        """

        current_time = datetime.now()
        # Casting get_startime string to datetime object
        datetime_object = datetime.strptime(self.get_starttime(), "%a %d-%b-%Y %H:%M:%S")
        # Difference between current time and start time gives time since start
        time_since_start = current_time - datetime_object

        if get_timedelta:
            return time_since_start
        else:
            return time_since_start.total_seconds()

    def get_npratio(self) -> float:
        """
        Gets the n/p ratio for the current run.

        Returns:
            float: the ratio
        """
        return self._get_pv_value(self._get_dae_pv_name("npratio"))

    def get_timing_source(self) -> str:
        """
        Gets the DAE timing source.

        Returns:
            string: the current timing source being used
        """
        return self._get_pv_value(self._get_dae_pv_name("timingsource"))

    def get_run_duration(self, period: bool = False) -> int:
        """
        Gets either the total run duration or the period duration

        Args:
            period: whether to return the duration for the current period [optional]

        Returns:
            int: the run duration in seconds
        """
        if period:
            return self._get_pv_value(self._get_dae_pv_name("rundurationperiod"))
        else:
            return self._get_pv_value(self._get_dae_pv_name("runduration"))

    def get_num_timechannels(self) -> int:
        """
        Gets the number of time channels.

        Returns:
            int: the number of time channels
        """
        return cast(int, self._get_pv_value(self._get_dae_pv_name("numtimechannels")))

    def get_monitor_counts(self) -> int:
        """
        Gets the number of monitor counts.

        Returns:
            int: the number of monitor counts
        """
        return self._get_pv_value(self._get_dae_pv_name("monitorcounts"))

    def get_monitor_spectrum(self) -> int:
        """
        Gets the monitor spectrum.

        Returns:
            int: the detector number of the monitor
        """
        return self._get_pv_value(self._get_dae_pv_name("monitorspectrum"))

    def get_monitor_to(self) -> float:
        """
        Gets the monitor 'to' limit.

        Returns:
            float: the 'to' time for the monitor
        """
        return self._get_pv_value(self._get_dae_pv_name("monitorto"))

    def get_monitor_from(self) -> float:
        """
        Gets the monitor 'from' limit.

        Returns:
            float: the 'from' time for the monitor
        """
        return self._get_pv_value(self._get_dae_pv_name("monitorfrom"))

    def get_beam_current(self) -> float:
        """
        Gets the beam current.

        Returns:
            float: the current value
        """
        return self._get_pv_value(self._get_dae_pv_name("beamcurrent"))

    def get_total_uamps(self) -> float:
        """
        Gets the total microamp hours for the current run.

        Returns:
            float: the total micro-amp hours.
        """
        return self._get_pv_value(self._get_dae_pv_name("totaluamps"))

    def get_total_dae_counts(self) -> int:
        """
        Gets the total DAE counts for the current run.

        Returns:
            int: the total count
        """
        return self._get_pv_value(self._get_dae_pv_name("totaldaecounts"))

    def get_countrate(self) -> float:
        """
        Gets the count rate.

        Returns:
            float: the count rate
        """
        return self._get_pv_value(self._get_dae_pv_name("countrate"))

    def get_eventmode_fraction(self) -> float:
        """
        Gets the event mode fraction.

        Returns:
            float: the fraction
        """
        return self._get_pv_value(self._get_dae_pv_name("eventmodefraction"))

    def get_spec_integrals(self) -> npt.NDArray:
        """
        Gets the event mode spectrum integrals.
        This includes spectrum 0

        Returns:
            numpy int array: the spectrum integrals
        """
        # this return waveform NELM elements, but only NORD are valid
        data = cast(
            npt.NDArray, self._get_pv_value(self._get_dae_pv_name("specintegrals"), use_numpy=True)
        )
        spec_size = self._get_pv_value(self._get_dae_pv_name("specintegrals_size"))
        assert isinstance(spec_size, (int, float))
        size = int(spec_size)
        # this is an EPICS waveform so NORD <= NELM
        if size < data.size:
            data.resize(size)
        return data

    def get_spec_data(self) -> npt.NDArray:
        """
        Gets the event mode spectrum data.
        This includes spectrum 0 and time bin 0

        Returns:
            numpy int array: the spectrum data
        """
        self._set_pv_value(self._get_dae_pv_name("specdata") + ".PROC", 1, wait=True)
        # this return waveform NELM elements, but only NORD are valid
        data = cast(
            npt.NDArray, self._get_pv_value(self._get_dae_pv_name("specdata"), use_numpy=True)
        )
        spec_size = self._get_pv_value(self._get_dae_pv_name("specdata_size"))
        assert isinstance(spec_size, (int, float))
        size = int(spec_size)
        # this is an EPICS waveform so NORD <= NELM
        if size < data.size:
            data.resize(size)
        return data

    def change_start(self) -> None:
        """
        Start a change operation.

        The operation is finished when change_finish is called.
        Between these two calls a sequence of other change commands can be called.
        For example: change_tables, change_tcb etc.

        Raises:
            ValueError: if the run state is not SETUP or change already started
        """
        # Check if we are in transition e.g. wiring tables being changed from GUI
        # because it can go in and out of transition 3 times very quickly during a
        # change we do a nested check
        if self.in_transition():
            print("Another DAE change operation is currently in progress, waiting...")
            while self.in_transition():
                while self.in_transition():
                    sleep(1)
                sleep(0.1)
            print("Previous DAE change operation has now completed")

        # Check in SETUP
        if self.get_run_state() != "SETUP":
            raise ValueError("Instrument must be in SETUP when changing settings!")
        if self.in_change:
            raise ValueError("Already in change - previous cached values will be used")
        else:
            self.in_change = True
            self.change_cache = ChangeCache()

    def change_finish(self) -> None:
        """
        End a change operation.

        The operation is begun when change_start is called.
        Between these two calls a sequence of other change commands can be called.
        For example: change_tables, change_tcb etc.

        Raises:
            ValueError: if the change has already finished
        """
        if not self.in_change:
            raise ValueError("Change has already finished")
        if self.in_transition():
            raise ValueError(
                "Another DAE change operation is currently in progress - "
                "values will be inconsistent"
            )
        if self.get_run_state() != "SETUP":
            raise ValueError("Instrument must be in SETUP when changing settings!")
        if self.in_change:
            self.in_change = False
            self._change_dae_settings()
            self._change_tcb_settings()
            self._change_period_settings()
            self.change_cache = ChangeCache()

    def change_tables(
        self, wiring: str | None = None, detector: str | None = None, spectra: str | None = None
    ) -> None:
        """
        Load the wiring, detector and/or spectra tables.

        Args:
            wiring: the filename of the wiring table file [optional]
            detector: the filename of the detector table file [optional]
            spectra: the filename of the spectra table file [optional]
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if wiring is not None:
            self.change_cache.wiring = wiring
        if detector is not None:
            self.change_cache.detector = detector
        if spectra is not None:
            self.change_cache.spectra = spectra
        if did_change:
            self.change_finish()

    def change_monitor(self, spec: int, low: float, high: float) -> None:
        """
        Change the monitor to a specified spectrum and range.

        Args:
            spec: the spectrum number (integer)
            low: the low end of the integral (float)
            high: the high end of the integral (float)

        Raises:
            TypeError: if a value supplied is not correctly typed
        """
        try:
            spec = int(spec)
        except ValueError:
            raise TypeError("Spectrum number must be an integer")
        try:
            low = float(low)
        except ValueError:
            raise TypeError("Low must be a float")
        try:
            high = float(high)
        except ValueError:
            raise TypeError("High must be a float")
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        self.change_cache.set_monitor(spec, low, high)
        if did_change:
            self.change_finish()

    def change_sync(self, source: str) -> None:
        """
        Change the source the DAE using for synchronisation.

        Args:
            source: the source to use ('isis', 'internal', 'smp', 'muon cerenkov',
                                       'muon ms', 'isis (first ts1)', 'isis (ts1 only)')

        Raises:
            Exception: if an invalid source is entered
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        source = source.strip().lower()
        if source == "isis":
            value = 0
        elif source == "internal":
            value = 1
        elif source == "smp":
            value = 2
        elif source == "muon cerenkov":
            value = 3
        elif source == "muon ms":
            value = 4
        elif source == "isis (first ts1)":
            value = 5
        elif source == "isis (ts1 only)":
            value = 6
        else:
            raise Exception("Invalid timing source entered, try help(change_sync)!")
        self.change_cache.dae_sync = value
        if did_change:
            self.change_finish()

    def change_tcb_file(self, tcb_file: str | None = None, default: bool = False) -> None:
        """
        Change the time channel boundaries.

        Args:
            tcb_file: the file to load [optional]
            default: load the default file "c:\\labview modules\\dae\\tcb.dat" [optional]

        Raises:
            Exception: if the TCB file is not specified or not found
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if tcb_file is not None:
            tcb_file = get_correct_path(tcb_file)
            print(("Reading TCB boundaries from {}".format(tcb_file)))
        elif default:
            tcb_file = "c:\\labview modules\\dae\\tcb.dat"
        else:
            raise Exception("No tcb file specified")
        if not os.path.exists(tcb_file):
            raise Exception("Tcb file could not be found")
        self.change_cache.tcb_file = tcb_file
        self.change_cache.tcb_calculation_method = 1
        if did_change:
            self.change_finish()

    def _create_tcb_return_string(self, low: float, high: float, step: float, log: bool) -> str:
        """
        Creates a human readable string when the tcb is changed.

        Args:
            low: the lower limit
            high: the upper limit
            step: the step size
            log: whether to use LOG binning [optional]

        Returns:
            str: The human readable string
        """
        out = "Setting TCB "
        binning = "LOG binning" if log else "LINEAR binning"

        low_changed, high_changed, step_changed = (c is not None for c in [low, high, step])

        if low_changed and high_changed:
            out += "range {} to {} ".format(low, high)
        elif low_changed:
            out += "low limit to {} ".format(low)
        elif high_changed:
            out += "high limit to {} ".format(high)

        if step_changed:
            out += "step {} ".format(step)

        if not any([low_changed, high_changed, step_changed]):
            out += "to {}".format(binning)
        else:
            out += "({})".format(binning)

        return out

    def change_tcb(
        self, low: float, high: float, step: float, trange: int, log: bool = False, regime: int = 1
    ) -> None:
        """
        Change the time channel boundaries.

        Args:
            low: the lower limit
            high: the upper limit
            step: the step size
            trange: the time range (1 to 5)
            log: whether to use LOG binning [optional]
            regime: the time regime to set (1 to 6)[optional]
        """
        print((self._create_tcb_return_string(low, high, step, log)))
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if log:
            self.change_cache.tcb_tables.append((regime, trange, low, high, step, 2))
        else:
            self.change_cache.tcb_tables.append((regime, trange, low, high, step, 1))

        self.change_cache.tcb_calculation_method = 0

        if did_change:
            self.change_finish()

    def change_vetos(self, **params: bool) -> None:
        """
        Change the DAE veto settings.

        Args:
            clearall: remove all vetoes [optional]
            smp: set SMP veto [optional]
            ts2: set TS2 veto [optional]
            hz50: set 50 hz veto [optional]
            ext0: set external veto 0 [optional]
            ext1: set external veto 1 [optional]
            ext2: set external veto 2 [optional]
            ext3: set external veto 3 [optional]

        If clearall is specified then all vetoes are turned off,
        but it is possible to turn other vetoes back on at the same time.

        Example:
            Turns all vetoes off then turns the SMP veto back on
            >>> change_vetos(clearall=True, smp=True)
        """
        valid_vetoes = [
            CLEAR_VETO,
            SMP_VETO,
            TS2_VETO,
            HZ50_VETO,
            EXT0_VETO,
            EXT1_VETO,
            EXT2_VETO,
            EXT3_VETO,
            FIFO_VETO,
        ]

        # Change keys to be case insensitive
        params = dict((k.lower(), v) for k, v in params.items())

        # Check for invalid veto names and invalid (non-boolean) values
        not_bool = []
        for k, v in params.items():
            if k not in valid_vetoes:
                raise Exception("Invalid veto name: {}".format(k))
            if not isinstance(v, bool):
                not_bool.append(k)
        if len(not_bool) > 0:
            raise Exception(
                "Vetoes must be set to True or False, "
                "the following vetoes were incorrect: {}".format(" ".join(not_bool))
            )

        # Set any runtime vetoes
        params = self._change_runtime_vetos(params)
        if len(params) == 0:
            return

        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True

        # Clearall must be done first.
        if CLEAR_VETO in params:
            if isinstance(params[CLEAR_VETO], bool) and params[CLEAR_VETO]:
                self.change_cache.clear_vetos()
        if SMP_VETO in params:
            if isinstance(params[SMP_VETO], bool):
                self.change_cache.smp_veto = int(params[SMP_VETO])
        if TS2_VETO in params:
            if isinstance(params[TS2_VETO], bool):
                self.change_cache.ts2_veto = int(params[TS2_VETO])
        if HZ50_VETO in params:
            if isinstance(params[HZ50_VETO], bool):
                self.change_cache.hz50_veto = int(params[HZ50_VETO])
        if EXT0_VETO in params:
            if isinstance(params[EXT0_VETO], bool):
                self.change_cache.ext0_veto = int(params[EXT0_VETO])
        if EXT1_VETO in params:
            if isinstance(params[EXT1_VETO], bool):
                self.change_cache.ext1_veto = int(params[EXT1_VETO])
        if EXT2_VETO in params:
            if isinstance(params[EXT2_VETO], bool):
                self.change_cache.ext2_veto = int(params[EXT2_VETO])
        if EXT3_VETO in params:
            if isinstance(params[EXT3_VETO], bool):
                self.change_cache.ext3_veto = int(params[EXT3_VETO])

        if did_change:
            self.change_finish()

    def _change_runtime_vetos(self, params: dict) -> None:
        """
        Change the DAE veto settings whilst the DAE is running.

        Args:
            params (dict): The vetoes to be set.

        Returns:
            dict : The params passed in minus the ones set in this method.
        """
        if FIFO_VETO in params:
            if isinstance(params[FIFO_VETO], bool):
                self._set_pv_value(
                    self._get_dae_pv_name("set_veto_" + ("true" if params[FIFO_VETO] else "false")),
                    "FIFO",
                )

                # Check if in SETUP, if not SETUP warn the user that the setting will be set
                # to True automatically when a run begins.
                if self.get_run_state() == "SETUP" and not params[FIFO_VETO]:
                    print(
                        "FIFO veto will automatically revert to ENABLED when next run begins.\n"
                        "Run this command again during the run to disable FIFO vetos."
                    )
                del params[FIFO_VETO]
            else:
                raise Exception("FIFO veto must be set to True or False")
        return params

    def set_fermi_veto(
        self, enable: bool | None = None, delay: float = 1.0, width: float = 1.0
    ) -> None:
        """
        Configure the fermi chopper veto.

        Args:
            enable: enable the fermi veto
            delay: the veto delay
            width: the veto width

        Raises:
            Exception: if invalid typed value supplied.
        """
        if not isinstance(enable, bool):
            raise Exception("Fermi veto: enable must be a boolean value")
        if not isinstance(delay, float) and not isinstance(delay, int):
            raise Exception("Fermi veto: delay must be a numeric value")
        if not isinstance(width, float) and not isinstance(width, int):
            raise Exception("Fermi veto: width must be a numeric value")
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if enable:
            self.change_cache.set_fermi(1, delay, width)
            print(
                ("SET_FERMI_VETO: requested status is ON, delay: {} width: {}".format(delay, width))
            )
        else:
            self.change_cache.set_fermi(0)
            print("SET_FERMI_VETO: requested status is OFF")
        if did_change:
            self.change_finish()

    def set_num_soft_periods(self, number: int) -> None:
        """
        Sets the number of software periods for the DAE.

        Args:
            number: the number of periods to create

        Raises:
            Exception: if wrongly typed value supplied
        """
        if not isinstance(number, float) and not isinstance(number, int):
            raise Exception("Number of soft periods must be a numeric value")
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if number >= 0:
            self.change_cache.periods_soft_num = number
        if did_change:
            self.change_finish()

    def set_period_mode(self, mode: str) -> None:
        """
        Sets the period mode for the DAE.

        Args:
            mode: the mode to switch to ('soft', 'int', 'ext')
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if mode.strip().lower() == "soft":
            self.change_cache.periods_type = 0
        else:
            self.configure_hard_periods(mode)
        if did_change:
            self.change_finish()

    def configure_hard_periods(
        self,
        mode: str,
        period_file: str | None = None,
        sequences: int | None = None,
        output_delay: int | None = None,
        period: int | None = None,
        daq: bool = False,
        dwell: bool = False,
        unused: bool = False,
        frames: int | None = None,
        output: int | None = None,
        label: str | None = None,
    ) -> None:
        """
        Configures the DAE's hardware periods.

        Args:
            mode: set the mode to internal ('int') or external ('ext')

            Internal periods parameters [optional]:
                period_file: the file containing the internal period settings (ignores any
                             other settings)
                sequences: the number of period sequences
                output_delay: the output delay in microseconds
                period: the number of the period to set the following for:
                daq: period is an acquisition; if period is not set then applies for all periods
                dwell: period is a dwell; if period is not set then applies for all periods
                unused: period is a unused; if period is not set then applies for all periods
                frames: the number of frames to count for the period; if period is not set then
                        applies for all periods
                output: the binary output for the period; if period is not set then applies for
                        all periods
                label: the label for the period; if period is not set then applies for all periods

        Raises:
            Exception: if mode is not 'int' or 'ext'

        Examples:
            Setting external periods
            >>> enable_hardware_periods("ext")

            Setting internal periods from a file
            >>> enable_hardware_periods("int", "myperiods.txt")
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        # Set the source to 'Use Parameters Below' by default
        self.change_cache.periods_src = 0
        if mode.strip().lower() == "int":
            self.change_cache.periods_type = 1
            if period_file is not None:
                period_file = get_correct_path(period_file)
                if not os.path.exists(period_file):
                    raise Exception("Period file could not be found")
                self.change_cache.periods_src = 1
                self.change_cache.periods_file = period_file
            else:
                self.configure_internal_periods(
                    sequences, output_delay, period, daq, dwell, unused, frames, output, label
                )
        elif mode.strip().lower() == "ext":
            self.change_cache.periods_type = 2
        else:
            raise Exception('Period mode invalid, it should be "int" or "ext"')
        if did_change:
            self.change_finish()

    def configure_internal_periods(
        self,
        sequences: int | None = None,
        output_delay: int | None = None,
        period: int | None = None,
        daq: bool = False,
        dwell: bool = False,
        unused: bool = False,
        frames: int | None = None,
        output: int | None = None,
        label: str | None = None,
    ) -> None:
        """
        Configure the internal periods without switching to internal period mode.

        Args:
            sequences: the number of period sequences [optional]
            output_delay: the output delay in microseconds [optional]
            period: the number of the period to set values for [optional]
            daq:  the specified period is a aquisition period [optional]
            dwell: the specified period is a dwell period [optional]
            unused: the specified period is a unused period [optional]
            frames: the number of frames to count for the specified period [optional]
            output: the binary output the specified period [optional]
            label: the label for the period the specified period [optional]

        Note: if the period number is unspecified then the settings will be applied to all periods.

        Raises:
            Exception: if wrongly typed value supplied
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if sequences is not None:
            if isinstance(sequences, int):
                self.change_cache.periods_seq = sequences
            else:
                raise Exception("Number of period sequences must be an integer")
        if output_delay is not None:
            if isinstance(output_delay, int):
                self.change_cache.periods_delay = output_delay
            else:
                raise Exception("Output delay of periods must be an integer (microseconds)")
        self.define_hard_period(period, daq, dwell, unused, frames, output, label)
        if did_change:
            self.change_finish()

    def define_hard_period(
        self,
        period: int | None = None,
        daq: bool = False,
        dwell: bool = False,
        unused: bool = False,
        frames: int | None = None,
        output: int | None = None,
        label: str | None = None,
    ) -> None:
        """
        Define the hardware periods.

        Args:
            period: the number of the period to set values for [optional]
            daq:  the specified period is a aquisition period [optional]
            dwell: the specified period is a dwell period [optional]
            unused: the specified period is a unused period [optional]
            frames: the number of frames to count for the specified period [optional]
            output: the binary output the specified period [optional]
            label: the label for the period the specified period [optional]

        Note: if the period number is unspecified then the settings will be applied to all periods.

        Raises:
            Exception: if supplied period is not a integer between 0 and 9
        """
        did_change = False
        if not self.in_change:
            self.change_start()
            did_change = True
        if period is None:
            # Do for all periods (1 to 8)
            for i in range(1, 9):
                self.define_hard_period(i, daq, dwell, unused, frames, output, label)
        else:
            if isinstance(period, int) and 0 < period < 9:
                p_type = None  # unchanged
                if unused:
                    p_type = 0
                elif daq:
                    p_type = 1
                elif dwell:
                    p_type = 2
                p_frames = None  # unchanged
                if frames is not None and isinstance(frames, int):
                    p_frames = frames
                p_output = None  # unchanged
                if output is not None and isinstance(output, int):
                    p_output = output
                p_label = None  # unchanged
                if label is not None:
                    p_label = label
                self.change_cache.periods_settings.append(
                    (period, p_type, p_frames, p_output, p_label)
                )
            else:
                raise Exception("Period number must be an integer from 1 to 8")
        if did_change:
            self.change_finish()

    def _change_dae_settings(self) -> None:
        """
        Changes the DAE settings.
        """
        root = ET.fromstring(
            self._get_pv_value(self._get_dae_pv_name("daesettings"), to_string=True)
        )
        changed = self.change_cache.change_dae_settings(root)
        if changed:
            self._set_pv_value(
                self._get_dae_pv_name("daesettings_sp"),
                ET.tostring(root),
                wait=self.wait_for_completion_callback_dae_settings,
            )

        """confirm that the wiring tables for the dae_setting complete, 
        must be done here due to equate for mulitiple change requests.
        """
        tables_to_check = self._check_tables_not_empty()

        if tables_to_check:  # if there's nothing in the change cache we don't want to change tables
            if self._check_table_file_paths_correct(tables_to_check):
                print("All tables successfully changed.")

            else:  # there were some errors, report which tables failed to write.
                errors = " "
                for item in tables_to_check:
                    if item.correctly_written is False:
                        errors = "{}{} : {}, ".format(errors, item.table_type, item.cache_value)
                raise ValueError("{} table(s) failed to write.".format(errors))

    def _check_table_file_paths_correct(self, tables_to_check: list[str]) -> None:
        """Checks the wiring, detector and spectra tables in
        the dae settings against those provided in tables_to_check

        @param tables_to_check : list containing the change_cache
        values for Wiring, Detector and Spectra tables.
        @returns written: boolean value True when all tables are correct.
        """

        written = True

        for item in tables_to_check:
            if self.get_table_path(item.table_type) == item.cache_value:
                item = item._replace(correctly_written=True)
                written = written & item.correctly_written
            else:
                written = False
        return written

    def _check_tables_not_empty(self) -> list[str]:
        """Checks the wiring, detector and spectra tables in change_cache
        are not empty.

        @returns tables_to_check: a list containing the change_cache
        values for Wiring, Detector and Spectra tables and a boolean state, used to
        indicate whether the file is correct in the dae settings.
        """
        tables_to_check = []
        table_path = namedtuple("table_path", "table_type cache_value correctly_written")

        if self.change_cache.wiring is not None:
            wiring = table_path("Wiring", self.change_cache.wiring, False)
            tables_to_check.append(wiring)
        if self.change_cache.detector is not None:
            detector = table_path("Detector", self.change_cache.detector, False)
            tables_to_check.append(detector)
        if self.change_cache.spectra is not None:
            spectra = table_path("Spectra", self.change_cache.spectra, False)
            tables_to_check.append(spectra)

        return tables_to_check

    def _get_tcb_xml(self) -> ET.Element:
        """
        Reads the hexed and zipped TCB data.

        Returns:
            The root of the xml.
        """
        value = self._get_pv_value(self._get_dae_pv_name("tcbsettings"), to_string=True)
        xml = dehex_and_decompress(value)
        # Strip off any zlib checksum stuff at end of the string
        last = xml.rfind(">") + 1
        return ET.fromstring(xml[0:last].strip())

    def _change_tcb_settings(self) -> None:
        """
        Changes the TCB settings.
        """
        root = self._get_tcb_xml()
        changed = self.change_cache.change_tcb_settings(root)
        if changed:
            ans = zlib.compress(ET.tostring(root))
            self._set_pv_value(self._get_dae_pv_name("tcbsettings_sp"), hexlify(ans), wait=True)

    def _change_period_settings(self) -> None:
        """
        Changes the period settings.

        Raises:
            IOError: if the DAE could not set the number of periods.
        """
        root = ET.fromstring(
            self._get_pv_value(self._get_dae_pv_name("periodsettings"), to_string=True)
        )
        changed = self.change_cache.change_period_settings(root)
        if changed:
            self._set_pv_value(
                self._get_dae_pv_name("periodsettings_sp"), ET.tostring(root).strip(), wait=True
            )

            if self.api.get_pv_alarm(self._get_dae_pv_name("periodsettings_sp")) == "INVALID":
                raise IOError(
                    "The DAE could not set the number of periods! "
                    "This may be because you are trying to "
                    "set a number that is too large for the DAE memory. Try a smaller number!"
                )

    def get_spectrum(
        self, spectrum: int, period: int = 1, dist: bool = True, use_numpy: bool | None = None
    ) -> dict:
        """
        Gets a spectrum from the DAE via a PV.

        Args:
            spectrum: the spectrum number
            period: the period number
            dist: True to return as a distribution (default), False to return as a histogram
            use_numpy (None|boolean): True use numpy to return arrays, False return a list;
                                      None for use the default

        Returns:
            dict: all the spectrum data
        """
        if dist:
            y_data = self._get_pv_value(
                self._get_dae_pv_name("getspectrum_y").format(period, spectrum), use_numpy=use_numpy
            )
            y_size = self._get_pv_value(
                self._get_dae_pv_name("getspectrum_y_size").format(period, spectrum)
            )
            y_data = y_data[:y_size]
            mode = "distribution"
            x_size = y_size
        else:
            y_data = self._get_pv_value(
                self._get_dae_pv_name("getspectrum_yc").format(period, spectrum),
                use_numpy=use_numpy,
            )
            y_size = self._get_pv_value(
                self._get_dae_pv_name("getspectrum_yc_size").format(period, spectrum)
            )
            y_data = y_data[:y_size]
            mode = "non-distribution"
            x_size = y_size + 1
        x_data = self._get_pv_value(
            self._get_dae_pv_name("getspectrum_x").format(period, spectrum), use_numpy=use_numpy
        )
        x_data = x_data[:x_size]

        return {"time": x_data, "signal": y_data, "sum": None, "mode": mode}

    def in_transition(self) -> bool:
        """
        Checks whether the DAE is in transition.

        Returns:
            bool: is the DAE in transition
        """
        transition = self._get_pv_value(self._get_dae_pv_name("statetrans"))
        if transition == "Yes":
            return True
        else:
            return False

    def get_wiring_tables(self) -> str:
        """
        Gets a list of wiring table choices.

        Returns:
            list: the table choices
        """
        raw = dehex_and_decompress(
            self._get_pv_value(self._get_dae_pv_name("wiringtables"), to_string=True)
        )
        return json.loads(raw)

    def get_spectra_tables(self) -> list[str]:
        """
        Gets a list of spectra table choices.

        Returns:
            list: the table choices
        """
        raw = dehex_and_decompress(
            self._get_pv_value(self._get_dae_pv_name("spectratables"), to_string=True)
        )
        return json.loads(raw)

    def get_detector_tables(self) -> list[str]:
        """
        Gets a list of detector table choices.

        Returns:
            list: the table choices
        """
        raw = dehex_and_decompress(
            self._get_pv_value(self._get_dae_pv_name("detectortables"), to_string=True)
        )
        return json.loads(raw)

    def get_period_files(self) -> list[str]:
        """
        Gets a list of period file choices.

        Returns:
            list: the table choices
        """
        raw = dehex_and_decompress(
            self._get_pv_value(self._get_dae_pv_name("periodfiles"), to_string=True)
        )
        return json.loads(raw)

    def get_tcb_settings(self, trange: int, regime: int = 1) -> dict:
        """
        Gets a dictionary of the time channel settings.

        Args:
            regime: the regime to read (1 to 6)
            trange: the time range to read (1 to 5) [optional]

        Returns:
            dict: the low, high and step for the supplied range and regime
        """
        root = self._get_tcb_xml()
        search_text = r"TR{} (\w+) {}".format(regime, trange)
        regex = re.compile(search_text)
        out = {}

        for top in root.iter("DBL"):
            n = top.find("Name")
            match = regex.search(n.text)
            if match is not None:
                v = top.find("Val")
                out[match.group(1)] = v.text

        return out

    def get_table_path(self, table_type: str) -> str:
        dae_xml = self._get_dae_settings_xml()
        for top in dae_xml.iter("String"):
            n = top.find("Name")
            if n.text == "{} Table".format(table_type):
                val = top.find("Val")
                return val.text

    def _get_dae_settings_xml(self) -> ET.Element:
        xml_value = self._get_pv_value(self._get_dae_pv_name("daesettings"))
        assert isinstance(xml_value, str)
        return ET.fromstring(xml_value)

    def _wait_for_isis_dae_state(self, state: str, timeout: int) -> tuple[bool, str]:
        """
        Wait for the isis dae to get to a state.
        :param state: state to reach
        :param timeout: timeout before reporting state wasn't reached
        :return: True if state was reached; False otherwise
        """
        state_attained = False
        current_state = ""
        for _ in range(timeout):
            current_state = self._get_pv_value(self._prefix_pv_name("CS:PS:ISISDAE_01:STATUS"))
            if current_state == state:
                state_attained = True
                break
            else:
                sleep(1)
        return state_attained, current_state

    def _isis_dae_triggered_state_was_reached(
        self,
        trigger_pv: str,
        state: str,
        timeout_per_trigger: int = 20,
        max_number_of_triggers: int = 5,
    ) -> str:
        """
        Trigger a state and wait for the state to be reached. For example stop the
        ISIS DAE and wait for it to be
        stopped. If the state isn't reached re-trigger the state
        :param trigger_pv: pv to trigger the state
        :param state: the state to reach
        :param timeout_per_trigger: timeout to wait to reach the state before retriggering
        :param max_number_of_triggers: The maximum number if triggers to do before exiting
        :return: True if state was reached; False otherwise
        """
        self.api.logger.log_info_msg(
            "Trying to reach state '{}' using trigger pv '{}'".format(state, trigger_pv)
        )
        state_attained = False
        current_state = "Not set"
        for _ in range(max_number_of_triggers):
            self._set_pv_value(self._prefix_pv_name(trigger_pv), 1)
            state_attained, current_state = self._wait_for_isis_dae_state(
                state, timeout_per_trigger
            )
            if state_attained:
                break
        else:
            self.api.logger.log_error_msg(
                "Failed to get to state '{}' using trigger pv '{}' was in state '{}'".format(
                    state, trigger_pv, current_state
                )
            )
        return state_attained

    @contextmanager
    def temporarily_kill_icp(self) -> None:
        """
        Context manager to temporarily kill ICP.
        """
        try:
            if not self._isis_dae_triggered_state_was_reached("CS:PS:ISISDAE_01:STOP", "Shutdown"):
                raise IOError("Could not stop ISISDAE!")
            for p in psutil.process_iter():
                if p.name().lower() == "isisicp.exe":
                    p.kill()
            yield
        finally:
            if not self._isis_dae_triggered_state_was_reached("CS:PS:ISISDAE_01:START", "Running"):
                raise IOError("Could not restart ISISDAE!")

            if self._get_pv_value(self._prefix_pv_name("CS:PS:ISISDAE_01:AUTORESTART")) != "On":
                self._set_pv_value(self._prefix_pv_name("CS:PS:ISISDAE_01:TOGGLE"), 1)

    @require_runstate(["SETUP", "PROCESSING"])
    def set_simulation_mode(self, mode: bool) -> None:
        """
        Sets the DAE simulation mode by writing to ICP_config.xml and restarting the
        DAE IOC and ISISICP
        Args:
            mode (bool): True to simulate the DAE, False otherwise
        """

        existent_config_files = [p for p in DAE_CONFIG_FILE_PATHS if os.path.exists(p)]

        if not len(existent_config_files) > 0:
            raise IOError("Could not find ICP configuration file")

        with self.temporarily_kill_icp():
            for path in existent_config_files:
                xml = ET.parse(path).getroot()

                node = xml.find(r"I32/[Name='Simulate']/Val")
                if node is None:
                    raise ValueError("No 'simulate' tag in ISISICP config file.")
                node.text = "1" if mode else "0"

                os.chmod(path, S_IWUSR | S_IREAD)

                with open(path, "wb") as f:
                    f.write(ET.tostring(xml))

    def get_simulation_mode(self) -> bool:
        """
        Gets the DAE simulation mode.
        Returns:
            True if the DAE is in simulation mode, False otherwise.
        """
        return self._get_pv_value(self._prefix_pv_name(DAE_PVS_LOOKUP["simulation_mode"])) == "Yes"

    def is_changing(self) -> bool:
        """
        Gets whether the DAE is in state changing mode.
        Returns:
            True if the DAE is in state changing mode, False otherwise.
        """
        return self._get_pv_value(self._prefix_pv_name(DAE_PVS_LOOKUP["state_changing"])) == "Yes"

    def integrate_spectrum(
        self, spectrum: int, period: int = 1, t_min: float | None = None, t_max: float | None = None
    ) -> float:
        """
        Integrates the spectrum within the time period and returns neutron counts.

        The underlying algorithm sums the counts from each bin, if a bin is split by the
        time region then a proportional fraction of the count for that bin is used.

        Args:
            spectrum (int): the spectrum number
            period (int, optional): the period
            t_min (float, optional): time of flight to start from
            t_max (float, optional): time of flight to finish at

        Returns:
            float: integral of the spectrum (neutron counts)
        """
        spectrum = self.get_spectrum(spectrum, period, False, use_numpy=True)
        time = spectrum["time"]
        count = spectrum["signal"]

        if time is None or count is None:
            return None

        # Get index for first bin with data in (partial or not)
        if t_min is None:
            first_bin_included = 0
            t_min = time[first_bin_included]
        else:
            if t_min < time[0]:
                raise ValueError(
                    "Argument from_time, {}, is less than lowest bin time, {}.".format(
                        t_min, time[0]
                    )
                )
            first_bin_included = time.searchsorted(t_min, side="left")

        # Get index of highest bin from which all data is included
        if t_max is None:
            last_complete_bin = len(time) - 1
            t_max = time[last_complete_bin]
        else:
            if t_max > time[-1]:
                raise ValueError(
                    "Argument to_time, {}, is greater than highest bin time, {}.".format(
                        t_max, time[-1]
                    )
                )
            last_complete_bin = time.searchsorted(t_max, side="left")

        # Error check
        if t_max < t_min:
            raise ValueError("Time range is not valid, to_time is less than from_time.")

        # Calculate extra counts from top bin if it is only a partial bin
        if t_max != time[last_complete_bin]:
            last_complete_bin -= 1

            width = time[last_complete_bin + 1] - time[last_complete_bin]

            partial_count_high = count[last_complete_bin]
            partial_count_high *= (t_max - time[last_complete_bin]) / width

        else:
            partial_count_high = 0.0

        # Calculate missing counts from the lowest bin that needs to be subtracted
        # if this is a partial bin
        if t_min != time[first_bin_included]:
            first_bin_included -= 1
            partial_count_low = count[first_bin_included]

            width = time[first_bin_included + 1] - time[first_bin_included]
            partial_count_low *= (t_min - time[first_bin_included]) / width

        else:
            partial_count_low = 0.0

        # calculate sum from lowest bin with any counts in to hightest bin
        # that is completely included
        full_count = np.sum(count[first_bin_included:last_complete_bin])

        # run sum of terms, note in the case that the high and low partials
        # are in the same bin this still works
        return full_count + partial_count_high - partial_count_low
