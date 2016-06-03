import getpass
import socket
from time import strftime, localtime
import os
import re
from genie_dae import Dae
from genie_plot import PlotController
from genie_waitfor import WaitForController
from genie_wait_for_move import WaitForMoveController
from genie_blockserver import BlockServer
from genie_cachannel_wrapper import CaChannelWrapper as Wrapper


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
    valid_instruments = ["DEMO", "LARMOR", "IMAT"]
    plots = PlotController()

    def __init__(self, pv_prefix, globs):
        """Constructor for the EPICS enabled API.
        
        Parameters:
            pv_prefix - used for prefixing the PV and block names
        """
        pass

    def set_instrument(self, pv_prefix, globs):
        """Set the instrument being used by setting the PV prefix or by the hostname if no prefix was passed"""
        API.__mod = __import__('init_default', globals(), locals(), [], -1)

        if pv_prefix is None:
            pv_prefix = socket.gethostname()
        instrument = pv_prefix.upper()
        if instrument.endswith(":"):
            instrument = instrument[:-1]

        if instrument.startswith("NDX") or instrument.startswith("IN:") or instrument in self.valid_instruments:
            if instrument.startswith("NDX") or instrument.startswith("IN:"):
                instrument = instrument[3:]
            self.init_instrument(instrument, globs)
            pv_prefix = "IN:" + instrument + ":"

        elif instrument.startswith("NDW") or instrument.startswith("NDLT"):
            print "THIS IS %s!" % instrument.upper()
            print instrument.lower() + " will use init_default "
            if not pv_prefix.startswith(socket.gethostname() + ":" + getpass.getuser().upper()):
                pv_prefix = pv_prefix + ":" + getpass.getuser().upper()

        if not pv_prefix.endswith(":"):
            pv_prefix += ":"
        print "PV prefix is " + pv_prefix
        API.__inst_prefix = pv_prefix
        API.dae = Dae(self, pv_prefix)
        API.wait_for_move = WaitForMoveController(self, pv_prefix + API.__motion_suffix)
        API.waitfor = WaitForController(self)
        API.blockserver = BlockServer(self)
        
    def prefix_pv_name(self, name):
        """Adds the instrument prefix to the specified PV"""
        if API.__inst_prefix is not None:
            return API.__inst_prefix + name
        return name

    def init_instrument(self, instrument, globs):
        print "THIS IS %s!" % instrument.upper()
        try:
            name = instrument.lower()

            # Try to call init on init_default to add the path for the instrument specific python files
            init_func = getattr(API.__mod , "init")
            init_func(name)

            # Load it
            API.__localmod = __import__('init_' + name, globals(), locals(), ['init_' + name], -1)
            if API.__localmod.__file__.endswith('.pyc'):
                file_loc = API.__localmod.__file__[:-1]
            else:
                file_loc = API.__localmod.__file__
            # execfile - this puts any imports in the init file into the globals namespace
            # Note: Anything loose in the module like print statements will be run twice
            execfile(file_loc, globs)
            # Call the init command
            init_func = getattr(API.__localmod, "init")
            init_func(name)
        except Exception as err:
            print "There was a problem with loading init_" + instrument.lower() + " so will use default"
            print "Error was: %s" % err

    def set_pv_value(self, name, value, wait=False):
        """Set the PV to a value.
           When setting a PV value this call should be used unless there is a special requirement.

        Parameters:
            name - the PV name
            value - the value to set
            wait - wait for the value to be set before returning
        """
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

    def get_pv_value(self, name, to_string=False, attempts=3):
        """Get the current value of the PV.
            When getting a PV value this call should be used unless there is a special requirement.

        Parameters:
            name - the PV name
            to_string - whether to cast it to a string
        """
        while True:
            try:
                return Wrapper.get_pv_value(name, to_string)
            except Exception as e:
                attempts -= 1
                if attempts < 1:
                    raise e

    def pv_exists(self, name):
        """See if the PV exists"""
        return Wrapper.pv_exists(name)
        
    def correct_blockname(self, name, add_prefix=True):
        """Corrects the casing of the block."""
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
        """Gets a list of block names from the blockserver
        Note: does not include the prefix"""
        # Get blocks from block server
        return API.blockserver.get_block_names()
        
    def block_exists(self, name):
        """Checks whether the block exists.
        Note: this is case insensitive"""
        blks = self.get_blocks()
        blks = [x.lower() for x in blks]
        if name.lower() in blks:
            return True
        return False

    def set_block_value(self, name, value=None, runcontrol=None, lowlimit=None, highlimit=None, wait=False):
        """Sets a range of block values"""
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
            # Need to append :SP to the blockname - this is NOT a long term solution!
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
        """Gets the current value for the block"""
        return self.get_pv_value(self.correct_blockname(name), to_string, attempts)
            
    def set_multiple_blocks(self, names, values):
        """Sets values for multiple blocks"""
        # With LabVIEW we could set values then press go after all values are set
        # Not sure we are going to do something similar for EPICS
        temp = zip(names, values)
        # Set the values
        for name, value in temp:
            self.set_block_value(name, value)        
            
    def run_pre_post_cmd(self, command, **pars):
        """Runs a pre or post command.
        
        Parameters:
            command - the command name as a string
            pars - the parameters to pass to the command
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
        """Writes a message to the default log file.
        Can be used for error logging and logging commands sent.
        
        Parameters:
            message - the message to log
            source - the source of the message
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
        
    def get_sample_pars(self):
        """Get the current sample parameter values as a dictionary"""
        names = self.blockserver.get_sample_par_names()
        ans = {}
        if names is not None:
            for n in names:
                val = self.get_pv_value(self.prefix_pv_name(n))
                m = re.match(".+:SAMPLE:(.+)", n)
                ans[m.groups()[0]] = val
        return ans
        
    def set_sample_par(self, name, value):
        """Set a new value for a sample parameter
        
        Parameters:
            name - the name of the parameter to change
            value - the new value
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
        
    def get_beamline_pars(self):
        """Get the current beamline parameter values as a dictionary"""
        names = self.blockserver.get_beamline_par_names()
        ans = {}
        if names is not None:
            for n in names:
                val = self.get_pv_value(self.prefix_pv_name(n))
                m = re.match(".+:BL:(.+)", n)
                ans[m.groups()[0]] = val
        return ans
        
    def set_beamline_par(self, name, value):
        """Set a new value for a beamline parameter
        
        Parameters:
            name - the name of the parameter to change
            value - the new value
        """
        names = self.blockserver.get_beamline_par_names()
        if names is not None:
            for n in names:
                m = re.match(".+:BL:%s" % name.upper(), n)
                if m is not None:
                    # Found it!
                    self.set_pv_value(self.prefix_pv_name(n), value)
                    return
        raise Exception("Beamline parameter %s does not exist" % name)
        
    def get_runcontrol_settings(self, name):
        """Gets the current run-control settings for a block.

        Parameters:
            name - the name of the block

        Returns:
            dict - the run-control settings
        """
        name = self.correct_blockname(name)
        name = name[name.rfind(':') + 1:]
        ans = self.blockserver.get_runcontrol_settings()
        if name in ans:
            return ans[name]

        return dict()
        
    def check_alarms(self, blocks):
        """Checks whether the specified blocks are in alarm.

        Args:
            blocks (list) : the blocks to check

        Returns:
            list, list : the blocks in minor alarm and major alarm respectively
        """
        minor = list()
        major = list()
        for b in blocks:
            if self.block_exists(b):
                name = self.correct_blockname(b, False)
                full_name = self.correct_blockname(b)
                # Alarm states are: NO_ALARM, MINOR, MAJOR
                try:
                    alarm_state = self.get_pv_value(full_name + ".SEVR", attempts=1)
                    if alarm_state == "MINOR":
                        minor.append(name)
                    elif alarm_state == "MAJOR":
                        major.append(name)
                except:
                    # Could not get value
                    print "\nCould not get alarm state for block %s" % b
            else:
                print "Block %s does not exist, so ignoring it" % b
        return minor, major

    def get_current_block_values(self):
        """Gets the current block values including the run-control settings.

        Returns:
            dict - contains a tuple for each block containing the value and the run-control settings
        """
        return self.blockserver.get_current_block_values()
