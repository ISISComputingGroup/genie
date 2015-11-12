import win32com.client
from time import strftime, localtime
from genie_python.seci.genie_seci_dae import Dae
from genie_python.genie_waitfor import WaitForController
from genie_python.seci.genie_seci_wait_for_move import WaitForMoveController
from genie_python.seci.genie_seci_blockserver import BlockServer
import os
import re
from genie_python.genie_cachannel_wrapper import CaChannelWrapper as Wrapper
import socket


class API(object):
    waitfor = None
    wait_for_move = None
    dae = None
    blockserver = None
    dcom_api = None
    dcom_session = None
    __inst_prefix = ""
    __mod = None
    __localmod = None
    __data_dir = "C:\\Data"
    __log_dir = "C:\\Instrument\\Var\\logs\\genie_python\\"
    __blockserver_prefix = "CS:BLOCKSERVER:"
    __block_prefix = "CS:SB:"
    __motion_suffix = "CS:MOT:MOVING"

    def __init__(self, pv_prefix, globs):
        """Constructor for the EPICS enabled API
        
        Parameters:
            pv_prefix - used for prefixing the PV and block names
        """
        self.set_instrument(socket.gethostname(), globs)

    def set_instrument(self, pv_prefix, globs):
        """Set the instrument being used by setting the PV prefix"""
        API.__mod = __import__('init_default', globals(), locals(), [], -1)
        if pv_prefix.startswith("NDX"):
            instrument = pv_prefix[3:]
            if instrument.endswith(":"):
                instrument = instrument[:-1]
            print "THIS IS %s!" % instrument.upper()
            try:
                name = instrument.lower()
                # Load it
                API.__localmod = __import__('genie_python.init_' + name, globals(), locals(), ['init_' + name], -1)
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
            pv_prefix = "IN:" + instrument + ":"
        if not pv_prefix.endswith(":"):
            pv_prefix += ":"
        API.__inst_prefix = pv_prefix
        self.dcom_api = win32com.client.Dispatch("instapi.api")
        self.dcom_session = self.dcom_api.create("", "", "")
        API.dae = Dae(self, pv_prefix, self.dcom_session)
        API.wait_for_move = WaitForMoveController(self)
        API.waitfor = WaitForController(self)
        API.blockserver = BlockServer(self.dcom_session)
        
    def prefix_pv_name(self, name):
        """Adds the instrument prefix to the specified PV"""
        if API.__inst_prefix is not None:
            return API.__inst_prefix + name
        return name

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

    def correct_blockname(self, name):
        """Corrects the casing of the block."""
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
        # TODO:

        if wait is not None and runcontrol is not None:
            # Cannot set both at the same time
            raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")

        # Run pre-command
        if not self.run_pre_post_cmd('cset_precmd', runcontrol=runcontrol, wait=wait):
            print 'cset cancelled by pre-command'
            return

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
            settings = self.blockserver.get_raw_block_details(name)
            self.blockserver.set_labview_var(settings[1], settings[3], value)
            # Might need to push a button
            if settings[4] != 'none':
                self.blockserver.set_labview_var(settings[1], settings[4], True)
        if wait:
            self.waitfor.start_waiting(name, value, lowlimit, highlimit)
            return
        if runcontrol is not None:
            if runcontrol:
                # Turn on
                self.blockserver.set_runcontrol(name, 1)
            else:
                # Turn off
                self.blockserver.set_runcontrol(name, 0)
        # Set limits
        if lowlimit is not None:
            self.blockserver.set_runcontrol_low(name, lowlimit)
        if highlimit is not None:
            self.blockserver.set_runcontrol_high(name, highlimit)

    def get_block_value(self, name, to_string=False, attempts=3):
        """Gets the current value for the block"""
        settings = self.blockserver.get_raw_block_details(name)
        return self.blockserver.get_labview_var(settings[1], settings[2])

    def set_multiple_blocks(self, names, values):
        """Sets values for multiple blocks"""
        # With the old system we could set values then press go after all values are set
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

    def log_entered_command(self):
        """Write the command to a log file"""
        try:
            import readline
            self.write_to_log(readline.get_line_buffer(), 'CMD')
        except:
            pass

    def log_info_msg(self, message):
        self.write_to_log(message, 'CMD')

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
            message = t_stamp + '\t(' + str(source) + ')\t' + str(message) + '\n'
            f.write(message)
            f.close()
        except:
            pass

    def get_sample_pars(self):
        """Get the current sample parameter values as a dictionary"""
        pars = dict()
        names = self.blockserver.get_sample_par_names()
        for name in names:
            vals = self.dcom_session.getSampleParameter(name)
            pars[name] = vals[0]
        return pars

    def set_sample_par(self, name, value):
        """Set a new value for a sample parameter

        Parameters:
            name - the name of the parameter to change
            value - the new value
        """
        names = self.blockserver.get_sample_par_names()
        for n in names:
            if n.lower() == name.lower():
                # Found it!
                self.dcom_session.setSampleParameter(n, value, "")
                return
        raise Exception("Sample parameter %s does not exist" % name)

    def get_beamline_pars(self):
        """Get the current beamline parameter values as a dictionary"""
        pars = dict()
        names = self.blockserver.get_beamline_par_names()
        for name in names:
            vals = self.dcom_session.getBeamlineParameter(name)
            pars[name] = vals[0]
        return pars

    def set_beamline_par(self, name, value):
        """Set a new value for a beamline parameter

        Parameters:
            name - the name of the parameter to change
            value - the new value
        """
        names = self.blockserver.get_beamline_par_names()
        for n in names:
            if n.lower() == name.lower():
                # Found it!
                self.dcom_session.setBeamlineParameter(n, value, "")
                return
        raise Exception("Beamline parameter %s does not exist" % name)

    def get_runcontrol_settings(self, name):
        name = self.correct_blockname(name)
        name = name[name.rfind(':') + 1:]
        ans = self.blockserver.get_runcontrol_settings(name)
        return ans