import os
import re
from time import strftime, localtime

from genie_blockserver import BlockServer
from genie_cachannel_wrapper import CaChannelWrapper as Wrapper
from genie_dae import Dae
from genie_plot import PlotController
from genie_wait_for_move import WaitForMoveController
from genie_waitfor import WaitForController
from utilities import crc8, EnvironmentDetails


class API(object):
    waitfor = None
    wait_for_move = None
    dae = None
    blockserver = None
    __inst_prefix = ""
    __mod = None
    __localmod = None
    __data_dir = "C:\\Data"
    __log_dir = "C:\\Instrument\\Var\\logs\\genie_python\\"
    __blockserver_prefix = "CS:BLOCKSERVER:"
    __block_prefix = "CS:SB:"
    __motion_suffix = "CS:MOT:MOVING"
    plots = PlotController()

    def __init__(self, pv_prefix, globs, environment_details=None):
        """
        Constructor for the EPICS enabled API.

        Args:
            pv_prefix: used for prefixing the PV and block names
            globs: globals
            computer_details: details of the computer environment
        """
        if environment_details is None:
            self._environment_details = EnvironmentDetails()
        else:
            self._environment_details = environment_details

    def _get_machine_details_from_identifier(self, machine_identifier):
        instrument_pv_prefix = "IN:"
        test_machine_pv_prefix = "TE:"

        instrument_machine_prefixes = ["NDX", "NDE"]

        # machine_identifier needs to be uppercase for both 'NDXALF' and 'ndxalf' to be valid
        if machine_identifier is None:
            machine_identifier = self._environment_details.get_host_name().upper()
        else:
            machine_identifier = machine_identifier.upper()

        instrument = machine_identifier.upper()
        for p in [instrument_pv_prefix, test_machine_pv_prefix] + instrument_machine_prefixes:
            if machine_identifier.startswith(p):
                instrument = machine_identifier.upper()[len(p):].rstrip(":")
                break

        if machine_identifier.startswith(instrument_pv_prefix):
            machine = "NDX{0}".format(instrument)
        elif machine_identifier.startswith(test_machine_pv_prefix):
            machine = "NDW{0}".format(instrument)
        else:
            machine = machine_identifier.upper()

        is_instrument = any(machine_identifier.startswith(p)
                            for p in instrument_machine_prefixes + [instrument_pv_prefix])
        pv_prefix = self._get_pv_prefix(instrument, is_instrument)

        return instrument, machine, pv_prefix

    def set_instrument(self, machine_identifier, globs):
        """
        Set the instrument being used by setting the PV prefix or by the hostname if no prefix was passed.

        Will do some checking to allow you to pass instrument names in so.

        Args:
            machine_identifier: should be the pv prefix but also accepts instrument name; if none defaults to computer
            host name
            globs: globals
        """
        API.__mod = __import__('init_default', globals(), locals(), [], -1)

        instrument, machine, pv_prefix = self._get_machine_details_from_identifier(machine_identifier)

        # Whatever machine we're on, try to initialize and fall back if unsuccessful
        try:
            self.init_instrument(instrument, machine, globs)
        except Exception as e:
            print e.message

        print "PV prefix is " + pv_prefix
        API.__inst_prefix = pv_prefix
        API.dae = Dae(self, pv_prefix)
        API.wait_for_move = WaitForMoveController(self, pv_prefix + API.__motion_suffix)
        API.waitfor = WaitForController(self)
        API.blockserver = BlockServer(self)

    def _get_pv_prefix(self, instrument, is_instrument):
        """
        Create the pv prefix based on instrument name and whether it is an instrument or a dev machine

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

        if is_instrument:
            pv_prefix_prefix = "IN"
            print "THIS IS %s!" % clean_instrument.upper()
        else:
            pv_prefix_prefix = "TE"
            print "THIS IS %s! (test machine)" % clean_instrument.upper()
        return "{prefix}:{instrument}:".format(prefix=pv_prefix_prefix, instrument=clean_instrument)

    def prefix_pv_name(self, name):
        """
        Adds the instrument prefix to the specified PV.
        """
        if API.__inst_prefix is not None:
            return API.__inst_prefix + name
        return name

    def init_instrument(self, instrument, machine_name, globs):
        try:
            # Try to call init on init_default to add the path for the instrument specific python files
            init_func = getattr(API.__mod, "init")
            init_func(machine_name)

            # Load it
            instrument = instrument.lower()
            API.__localmod = __import__('init_' + instrument, globals(), locals(), ['init_' + instrument], -1)
            if API.__localmod.__file__.endswith('.pyc'):
                file_loc = API.__localmod.__file__[:-1]
            else:
                file_loc = API.__localmod.__file__
            # execfile - this puts any imports in the init file into the globals namespace
            # Note: Anything loose in the module like print statements will be run twice
            execfile(file_loc, globs)
            # Call the init command
            init_func = getattr(API.__localmod, "init")
            init_func(machine_name)
        except Exception as err:
            raise Exception("There was a problem with loading init_{0} so will use default.\nError was {1}"
                            .format(instrument.lower(), err))

    def set_pv_value(self, name, value, wait=False, is_local=False):
        """
        Set the PV to a value.

        When setting a PV value this call should be used unless there is a special requirement.

        Args:
            name: the PV name
            value: the value to set
            wait: wait for the value to be set before returning
            is_local (bool, optional): whether to automatically prepend the local inst prefix to the PV name
        """
        if is_local:
            if not str.startswith(name, API.__inst_prefix):
                name = self.prefix_pv_name(name)
        self.log_info_msg("set_pv_value %s %s" % (name, str(value)))
        attempts = 3
        while True:
            try:
                Wrapper.set_pv_value(name, value, wait=wait)
                return
            except Exception as e:
                attempts -= 1
                if attempts < 1:
                    self.log_info_msg("set_pv_value exception %s" % e.message)
                    raise e

    def get_pv_value(self, name, to_string=False, attempts=3, is_local=False):
        """
        Get the current value of the PV.

        When getting a PV value this call should be used unless there is a special requirement.

        Args:
            name: the PV name
            to_string: whether to cast it to a string
            is_local (bool, optional): whether to automatically prepend the local inst prefix to the PV name
        """
        if is_local:
            if not str.startswith(name, API.__inst_prefix):
                name = self.prefix_pv_name(name)

        if not self.pv_exists(name):
            raise Exception('PV %s does not exist' % name)

        while True:
            try:
                return Wrapper.get_pv_value(name, to_string)
            except Exception as e:
                attempts -= 1
                if attempts < 1:
                    raise e

    def pv_exists(self, name):
        """
        See if the PV exists.
        """
        return Wrapper.pv_exists(name)

    def reload_current_config(self):
        """
        Reload the current configuration.
        """
        API.blockserver.reload_current_config()

    def correct_blockname(self, name, add_prefix=True):
        """
        Corrects the casing of the block.
        """
        blocks = self.get_blocks()
        for i in range(len(blocks)):
            if name.lower() == blocks[i].lower():
                if add_prefix:
                    return self.__inst_prefix + API.__block_prefix + blocks[i]
                else:
                    return blocks[i]
        # If we get here then the block does not exist
        # but this should be picked up elsewhere
        return name

    def get_blocks(self):
        """
        Gets a list of block names from the blockserver.

        Note: does not include the prefix
        """
        # Get blocks from block server
        return API.blockserver.get_block_names()

    def block_exists(self, name):
        """
        Checks whether the block exists.

        Note: this is case insensitive
        """
        blks = self.get_blocks()
        blks = [x.lower() for x in blks]
        if name.lower() in blks:
            return True
        return False

    def set_block_value(self, name, value=None, runcontrol=None, lowlimit=None, highlimit=None, wait=False):
        """
        Sets a range of block values.
        """
        # Run pre-command
        if wait is not None and runcontrol is not None:
            # Cannot set both at the same time
            raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")

        if not self.run_pre_post_cmd('cset_precmd', runcontrol=runcontrol, wait=wait):
            print 'cset cancelled by pre-command'
            return

        full_name = self.correct_blockname(name)

        if lowlimit is not None and highlimit is not None:
            if lowlimit > highlimit:
                temp = highlimit
                highlimit = lowlimit
                lowlimit = temp

                # if lowlimit is not None:
                # if lowlimit == float("inf"):
                # lowlimit = 'Infinity'
                # elif lowlimit == float("-inf"):
                # lowlimit = '-Infinity'
                # if highlimit is not None:
                # if highlimit == float("inf"):
                # highlimit = 'Infinity'
                # elif highlimit == float("-inf"):
                # highlimit = '-Infinity'
        if value is not None:
            # Need to append :SP to the blockname: this is NOT a long term solution!
            # If a field is included then strip it off
            if "." in name:
                name = name[:name.index('s')]
                name = self.correct_blockname(name)
                if self.pv_exists(name + ":SP"):
                    self.set_pv_value(name + ":SP", value)
                else:
                    # Try the unmodified name
                    self.set_pv_value(full_name, value)
            else:
                # Default case
                if self.pv_exists(full_name + ":SP"):
                    self.set_pv_value(full_name + ":SP", value)
                else:
                    self.set_pv_value(full_name, value)
        if wait:
            self.waitfor.start_waiting(name, value, lowlimit, highlimit)
            return
        if runcontrol is not None:
            if runcontrol:
                # Turn on
                self.set_pv_value(full_name + ":RC:ENABLE", 1)
            else:
                # Turn off
                self.set_pv_value(full_name + ":RC:ENABLE", 0)
        # Set limits
        if lowlimit is not None:
            self.set_pv_value(full_name + ":RC:LOW", lowlimit)
        if highlimit is not None:
            self.set_pv_value(full_name + ":RC:HIGH", highlimit)

    def get_block_value(self, name, to_string=False, attempts=3):
        """
        Gets the current value for the block.
        """
        return self.get_pv_value(self.correct_blockname(name), to_string, attempts)

    def set_multiple_blocks(self, names, values):
        """
        Sets values for multiple blocks.
        """
        # With LabVIEW we could set values then press go after all values are set
        # Not sure we are going to do something similar for EPICS
        temp = zip(names, values)
        # Set the values
        for name, value in temp:
            self.set_block_value(name, value)

    def run_pre_post_cmd(self, command, **pars):
        """
        Runs a pre or post command.

        Args:
            command: the command name as a string
            pars: the parameters to pass to the command
        """
        try:
            # Try getting the instrument specific version
            func = getattr(API.__localmod, command)
            return func(**pars)
        except:
            pass
        try:
            # Try getting the default
            func = getattr(API.__mod, command)
            return func(**pars)
        except Exception as msg:
            print msg

    def log_info_msg(self, message):
        self.write_to_log(message, 'CMD')

    def log_command(self, function_name, arguments):
        self.write_to_log("%s %s" % (function_name, arguments), 'CMD')

    def log_error_msg(self, error_msg):
        """Log the error to the log file"""
        self.write_to_log("ERROR: " + error_msg, 'CMD')

    def write_to_log(self, message, source):
        """
        Writes a message to the default log file.

        Can be used for error logging and logging commands sent.

        Args:
            message: the message to log
            source: the source of the message
        """
        try:
            curr_time = localtime()
            if not os.path.exists(API.__log_dir):
                os.makedirs(API.__log_dir)
            f_name = API.__log_dir + 'genie-' + strftime("%Y-%m-%d-%a", curr_time) + '.log'
            t_stamp = strftime("%Y-%m-%dT%H:%M:%S", curr_time)
            f = open(f_name, 'a')
            message = "%s\t(%s)\t(%s)\t%s\n" % (t_stamp, source, os.getpid(), message)
            f.write(message)
            f.close()
        except:
            pass

    def _get_pars(self, pv_prefix_identifier, get_names_from_blockserver):
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
                    self.log_error_msg("Unexpected PV found whilst retrieving parameters: {0}".format(n))
        return ans

    def get_sample_pars(self):
        """
        Get the current sample parameter values as a dictionary.
        """
        return self._get_pars("SAMPLE", API.blockserver.get_sample_par_names)

    def set_sample_par(self, name, value):
        """
        Set a new value for a sample parameter.

        Args:
            name: the name of the parameter to change
            value: the new value
        """
        names = API.blockserver.get_sample_par_names()
        if names is not None:
            for n in names:
                m = re.match(".+:SAMPLE:%s" % name.upper(), n)
                if m is not None:
                    # Found it!
                    self.set_pv_value(self.prefix_pv_name(n), value)
                    return
        raise Exception("Sample parameter %s does not exist" % name)

    def get_beamline_pars(self):
        """
        Get the current beamline parameter values as a dictionary.
        """
        return self._get_pars("BL", API.blockserver.get_beamline_par_names)

    def set_beamline_par(self, name, value):
        """
        Set a new value for a beamline parameter.

        Args:
            name: the name of the parameter to change
            value: the new value
        """
        names = API.blockserver.get_beamline_par_names()
        if names is not None:
            for n in names:
                m = re.match(".+:BL:%s" % name.upper(), n)
                if m is not None:
                    # Found it!
                    self.set_pv_value(self.prefix_pv_name(n), value)
                    return
        raise Exception("Beamline parameter %s does not exist" % name)

    def get_runcontrol_settings(self, name):
        """
        Gets the current run-control settings for a block.

        Args:
            name: the name of the block

        Returns:
            dict: the run-control settings
        """
        name = self.correct_blockname(name)
        name = name[name.rfind(':') + 1:]
        ans = API.blockserver.get_runcontrol_settings()
        if name in ans:
            return ans[name]

        return dict()

    def check_alarms(self, blocks):
        """
        Checks whether the specified blocks are in alarm.

        Args:
            blocks (list): the blocks to check

        Returns:
            list, list: the blocks in minor alarm and major alarm respectively
        """
        alarm_states = self._get_fields_from_blocks(blocks, "SEVR", "alarm state")
        minor = [t[0] for t in alarm_states if t[1] == "MINOR"]
        major = [t[0] for t in alarm_states if t[1] == "MAJOR"]
        return minor, major

    def check_limit_violations(self, blocks):
        """
        Checks whether the specified blocks have soft limit violations.

        Args:
            blocks (list): the blocks to check

        Returns:
            list: the blocks which have soft limit violations
            """
        violation_states = self._get_fields_from_blocks(blocks, "LVIO", "limit violation")
        return [t[0] for t in violation_states if t[1] == 1]

    def _get_fields_from_blocks(self, blocks, field_name, field_description):
        field_values = list()
        for b in blocks:
            if self.block_exists(b):
                block_name = self.correct_blockname(b, False)
                full_name = self.correct_blockname(b)
                try:
                    field_value = self.get_pv_value(full_name + "." + field_name, attempts=1)
                    field_values.append([block_name, field_value])
                except:
                    # Could not get value
                    print "\nCould not get " + field_description + " for block %s" % b
            else:
                print "Block %s does not exist, so ignoring it" % b

        return field_values

    def get_current_block_values(self):
        """
        Gets the current block values including the run-control settings.

        Returns:
            dict: contains a tuple for each block containing the value and the run-control settings
        """
        return API.blockserver.get_current_block_values()

    def send_sms(self, phone_num, message):
        """
        Sends an SMS message to a phone number.

        Args:
            phone_num (string): the phone number to send the SMS to
            message (string): the message to send in the SMS
        """
        try:
            from smslib.sms import send_sms
            send_sms(phone_num, message)
        except Exception as e:
            raise Exception("Could not send SMS\n" + str(e))
