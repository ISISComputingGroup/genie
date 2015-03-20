import types
import os
import imp
import sys
import readline
import glob
import re
from functools import wraps
from collections import OrderedDict
from genie_epics_api import *
from genie_script_checker import ScriptChecker

#Windows specific stuff
if os.name == 'nt':
    #Needed for correcting file paths
    import win32api

if 'SCISOFT_RPC_PORT' in os.environ:
    from genie_scisoft_plot import GeniePlot, SpectraPlot
else:
    from genie_plot import GeniePlot, SpectraPlot

#INITIALISATION CODE - DO NOT DELETE
try:
    #If __api does not exist or is None then we need to create it.
    if __api is None:
        raise Exception("API does not exist")
except:
    #This should only get called the first time genie is imported
    if 'MYPVPREFIX' in os.environ:
        MY_PV_PREFIX = os.environ['MYPVPREFIX']
        __api = API(MY_PV_PREFIX)
    else:
        print "No instrument specified - to set the instrument use the 'set_instrument' command"
        __api = API(None)
SCRIPT_DIR = "C:/scripts/"
_exceptions_raised = False
#END INITIALISATION CODE


#TAB COMPLETE FOR LOAD_SCRIPT
def complete(text, state):
    if text.startswith('load_script("') or text.startswith("load_script('"):
        temp = text[13:]
        ans = (glob.glob(temp+'*')+[None])[state]
        if ans is not None:
            return text[:13] + ans
    else:
        return __ipy_complete(text, state)

__ipy_complete = readline.get_completer()
readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(complete)
#END TAB COMPLETE


def _log_command(fn):
    #use wraps to make decorator propogate the docstring for the wrapped function
    @wraps(fn)
    def logged(*args, **kwargs):
        __api.log_entered_command()
        return fn(*args, **kwargs)
    return logged


def _print_error_message(message):
    """Print the error message to screen"""
    if os.name == 'nt':
        #Is windows
        from ctypes import windll
        std_output_handle = -11
        stdout_handle = windll.kernel32.GetStdHandle(std_output_handle)
        windll.kernel32.SetConsoleTextAttribute(stdout_handle, 12)
        print "ERROR: " + message
    else:
        #Non-windows
        print '\033[91m' + "ERROR: " + message
    #Log it
    __api.log_error_msg(message)


def _handle_exception(exception=None, message=None):
    """Handles any exception in the way we want"""
    if exception is not None:
        if message is not None:
            _print_error_message(message)
        else:
            _print_error_message(str(exception))
        if _exceptions_raised:
            raise exception
    elif message is not None:
        _print_error_message(message)
        if _exceptions_raised:
            raise Exception(message)
    else:
        _print_error_message("UNSPECIFIED")


@_log_command
def set_instrument(pv_prefix):
    """Sets the instrument this session is communicating with.
    Used for remote access.
    
    Parameters
    ----------
    pv_prefix : the PV prefix
    """
    try:
        __api.set_instrument(pv_prefix)
    except Exception as e:
        _handle_exception(e)


@_log_command
def get_blocks():
    """Returns a list of the blocknames.
    """
    try:
        return __api.get_blocks()
    except Exception as e:
        _handle_exception(e)


@_log_command
def cset(*args, **kwargs):
    """Sets the setpoint and runcontrol settings for blocks.
    
    Parameters
    ----------
    runcontrol : whether to set runcontrol for this block (True/False) [optional]
    wait : pause script/command line execution until setpoint reached (one block only) [optional]
    Note: cannot use wait and runcontrol in the same command
    lowlimit : the lower limit for runcontrol or waiting [optional]
    highlimit : the upper limit for runcontrol or waiting [optional]

    EXAMPLES
    --------
    
    Setting a value for a block:
    
    >>> cset(block1=100)
    
    Or:
    
    >>> cset("block1", 100)
    
    Setting values for more than one block:
    
    >>> cset(block1=100, block2=200, block3=300)
    
    NOTE: the order in which the values are set is random, e.g. block1 may or may not be set before block2 and block3
       
    Setting runcontrol values for a block:
    
    >>> cset(block1=100, runcontrol=True, lowlimit=99, highlimit=101)
    
    Changing runcontrol settings for a block without changing the setpoint:
    
    >>> cset("block1", runcontrol=False)    #Quotes round the block name
    >>> cset(block1=None, runcontrol=False)
    
    Wait for setpoint to be reached (one block only):
    
    >>> cset(block1=100, wait=True)
    
    Wait for limits to be reached - this does NOT change the runcontrol limits:
    
    >>> cset(block1=100, wait=True, lowlimit=99, highlimit=101)
    """

    #cset only works for blocks (currently)
    #block names contain alpha-numeric and underscores only
    #run-control not implemented yet!
    try:
        block = None
        blocks = []
        value = None
        values = []
        runcontrol = None
        lowlimit = None
        highlimit = None
        wait = None

        #See if single block name was entered, i.e. cset("block1", runcontrol=True)
        if len(args) > 0:
            if len(args) > 2:
                raise Exception('Too many arguments, please type: help(cset) for more information on the syntax')
            if not __api.block_exists(args[0]):
                raise Exception('No block with that name exists')
            else:
                block = args[0]
            if len(args) == 2:
                value = args[1]

        for k in kwargs:
            if k.lower() == 'runcontrol':
                runcontrol = kwargs['runcontrol']
            elif k.lower() == 'lowlimit':
                lowlimit = kwargs['lowlimit']
            elif k.lower() == 'highlimit':
                highlimit = kwargs['highlimit']
            elif k.lower() == 'wait':
                wait = kwargs['wait']
            else:
                #Perhaps it is a block?
                if __api.block_exists(k):
                    blocks.append(k)
                    values.append(kwargs[k])
                else:
                    raise Exception('No Block called ' + k + ' exists')

        if block is not None and len(blocks) > 0:
            raise Exception('Incorrect syntax, please type: help(cset) for more information on the syntax')

        if block is not None:
            #Something like cset("block1", runcontrol=True) or cset("block1", 10)
            if wait:
                raise Exception('Cannot wait as no setpoint specified. Please type: help(cset) for help')
            __api.set_block_value(block, value, runcontrol, lowlimit, highlimit, wait)
        elif len(blocks) == 1:
            #Something like cset(block1=123, runcontrol=True)
            if wait and runcontrol is not None:
                raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")
            else:
                __api.set_block_value(blocks[0], values[0], runcontrol, lowlimit, highlimit, wait)
        else:
            #Setting multiple blocks, so runcontrol and waiting are not allowed
            if runcontrol is not None or lowlimit is not None or highlimit is not None:
                raise Exception('Runcontrol settings can only be changed for one block at a time')
            if wait is not None:
                raise Exception('Cannot wait for more than one block')
            __api.set_multiple_blocks(blocks, values)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def cget(block):
    """Returns a dictionary of useful values associated with the block"""
    try: 
        if not __api.block_exists(block):
            raise Exception('No block with that name exists')
            
        ans = OrderedDict()
        ans['name'] = __api.correct_blockname(block)
        ans['value'] = __api.get_block_value(block)
        
        rc = __api.get_runcontrol_settings(block)
        
        if rc is not None:
            ans['runcontrol'] = rc["ENABLE"]
            ans['lowlimit'] = rc["LOW"]
            ans['highlimit'] = rc["HIGH"]       

        return ans
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def cshow(block=None):
    """Show the current settings for one block or for all blocks.
       
    EXAMPLES
    --------

    Showing all block values:
    
    >>> cshow()
    
    Showing values for one block only (name must be quoted):
    
    >>> cshow("block1")
    """
    try:
        if block:
            if __api.block_exists(block):
                output = block + ' = ' + str(__api.get_block_value(block))
                rc = __api.get_runcontrol_settings(block)
                if rc is not None:
                    output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (rc["ENABLE"], rc["LOW"], rc["HIGH"])
                
                #~ output = str(api.blocks[block].name) + ' = ' + str(api.blocks[block].value)
                #~ output += ' (setpoint = ' + str(api.blocks[block].setpoint)
                #~ output += ', runcontrol = ' + str(api.blocks[block].runcontrol)
                #~ output += ', lowlimit = '  + str(api.blocks[block].lowlimit)
                #~ output += ', highlimit = '  + str(api.blocks[block].highlimit)
                #~ output += ')'
                print output
            else:
                raise Exception('No block with that name exists')
        else:
            names = __api.get_blocks()
            if names is not None:
                for k in names:
                    cshow(k)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def waitfor(block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, 
            wait_all=False, seconds=None, minutes=None, hours=None, time=None, 
            frames=None, uamps=None, **pars):
    """Interrupts execution until certain conditions are met.
    
    Parameters
    ----------
    block : the name of the block to wait for [optional]
    value : the block value to wait for [optional]
    lowlimit : wait for the block to be >= this value [optional]
    highlimit : wait for the block to be <= this value [optional]
    maxwait : wait no longer that the specified number of seconds [optional]
    wait_all : wait for all conditions to be met (e.g. a number of frames and an amount of uamps) [optional]
    seconds : wait for a specified number of seconds [optional]
    minutes : wait for a specified number of minutes [optional]
    hours : wait for a specified number of hours [optional]
    time : a quicker way of setting hours, minutes and seconds (must be a string of format "HH:MM:SS") [optional]
    frames : wait for a total number of good frames to be collected [optional]
    uamps : wait for a total number of uamps to be received [optional]
        
    EXAMPLES
    --------
    
    Wait for a block to reach a specific value:
    
    >>> waitfor(myblock=123)
    >>> waitfor("myblock", 123)
    >>> waitfor("myblock", True)
    >>> waitfor("myblock", "OPEN")
    
    Wait for a block to be between limits:
    
    >>> waitfor("myblock", lowlimit=100, highlimit=110)
    
    Wait for a block to reach a specific value, but no longer than 60 seconds:
    
    >>> waitfor(myblock=123, maxwait=60)
    
    Wait for a specified time interval:
    
    >>> waitfor(seconds=10)
    >>> waitfor(hours=1, minutes=30, seconds=15)
    >>> waitfor(time="1:30:15")
    
    Wait for a data collection condition:
    
    >>> waitfor(frames=5000)
    >>> waitfor(uamps=200)
    
    Wait for either a number of frames OR a time interval to occur:
    
    >>> waitfor(frames=5000, hours=2)
    
    Wait for a number of frames AND a time interval to occur:
    
    >>> waitfor(frames=5000, hours=2, wait_all=True)    
    """
    try:
        if block is None:
            # Search through the params to see if there is a block there
            blks = __api.get_blocks()
            for k in pars:
                if k in blks:
                    if block is not None:
                        raise Exception('Can set waitfor for only one block at a time')
                    block = k
                    value = pars[k]
        # Check that wait_for object exists
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        # Start_waiting checks the block exists
        __api.waitfor.start_waiting(block, value, lowlimit, highlimit, maxwait, wait_all, seconds, minutes, hours, time,
                                    frames, uamps)
    except Exception as e:
        _handle_exception(e)


@_log_command
def waitfor_runstate(state, maxwaitsecs=60, onexit=False):
    """Wait for a particular instrument run state.
        
    Parameters
    ----------
    state : the state to wait for (e.g. "paused")
    maxwaitsecs : the maximum time to wait for the state before carrying on
    onexit : wait for runstate to change from the specified state
            
    EXAMPLES
    --------
    Wait for a run to enter the paused state:
    
    >>> waitfor_runstate("pause")
        
    Wait for a run to exit the paused state:
    
    >>> waitfor_runstate("pause", onexit=True)
    """
    try:
        # Check that wait_for object exists
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.wait_for_runstate(state, maxwaitsecs, onexit)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def waitfor_move(timeout=2):
    """ Wait for all motion to complete.

        Parameters
        ----------
        timeout : the number of seconds to wait for the movement to begin [optional]

    """
    try:
        #check that wait_for_move object exists
        if __api.wait_for_move is None:
            raise Exception("Cannot execute waitfor_move - try calling set_instrument first")
        __api.wait_for_move.wait(timeout)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_pv(name, to_string=False):
    """Get the value for the specified PV.
    
    PARAMETERS
    ----------
    name : the name of the PV to get the value for
    to_string : whether to get the value as a string
    """
    try:
        if not __api.pv_exists(name):
            raise Exception('PV does not exist')
        return __api.get_pv_value(name, to_string)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_pv(name, value, wait=False):
    """Set the value for the specified PV.
        
    Parameters
    ----------
    name : the PV name
    value : the new value to set
    wait : whether to wait for the value to be reached
    """
    try:
        return __api.set_pv_value(name, value, wait)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_messages_verbosity(verbose):
    """Set the global verbosity of messages
    
    Parameters
    ----------
    verbose : set the verbosity (True or False)
    """   
    __api.dae.set_verbose(verbose)    
        
        
@_log_command 
def begin(period=1, meas_id=None, meas_type="", meas_subid="", sample_id="", delayed=False, quiet=False, paused=False,
          verbose=False):
    """Starts a data collection run.
        
    Parameters
    ----------
    period : the period to begin data collection in [optional]
    meas_id : the measurement id [optional]
    meas_type : the type of measurement [optional]
    meas_subid : the measurement sub-id[optional]
    sample_id : the sample id [optional]
    delayed : puts the period card to into delayed start mode [optional]
    quiet : suppress the output to the screen [optional]
    paused : begin in the paused state [optional]
    """
    try:       
        __api.dae.begin_run(period, meas_id, meas_type, meas_subid, sample_id, delayed, quiet, paused, verbose)
        waitfor_runstate("SETUP", onexit=True)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def abort(verbose=False):
    """Abort the current run.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:        
        __api.dae.abort_run(verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def end():
    """End the current run.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:        
        __api.dae.end_run()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def pause(verbose=False):
    """Pause the current run.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:
        __api.dae.pause_run(verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def resume(verbose=False):
    """Resume the current run after it has been paused.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:
        __api.dae.resume_run(verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def recover(verbose=False):
    """Recovers the run if it has been aborted.
    The command should be run before the next run is started.
    
    Note: the run will be recovered in the paused state.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:
        __api.dae.recover_run(verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def updatestore(verbose=False):
    """Performs an update and a store operation in a combined operation.
    This is more efficient than doing the commands separately.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:
        __api.dae.update_store_run(verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def update(nopause=False, verbose=False):
    """Data is loaded from the DAE into the computer memory, but is not written to disk.
        
    Parameters
    ----------
    nopause : whether to pause data collection first [optional] [not implemented]
    verbose : show the messages from the DAE [optional]
    """
    try:
        __api.dae.update_run(not nopause, verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def store(verbose=False):
    """Data loaded into memory by a previous update command is now written to disk.
    
    Parameters
    ----------
    verbose : show the messages from the DAE [optional]
    """
    try:
        __api.dae.store_run(verbose)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_uamps(period=False):
    """Returns the current number of micro-amp hours.
        
    Parameters
    ----------
    period : whether to return the micro-amp hours for the current period [optional]
    """
    try:
        return __api.dae.get_uamps(period)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_frames(period=False):
    """Returns the current number of good frames.
        
    Parameters
    ----------
    period : whether to return the number of good frames for the current period [optional]
    """
    try:
        return __api.dae.get_good_frames(period)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_runstate():
    """Returns the current status of the instrument as a string.
    
    Note: this value can take a few seconds to update after a change of state."""
    try:
        return __api.dae.get_run_state()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_mevents():
    """Returns the total counts for all the detectors.
        
    Parameters
    ----------
    period : whether to return the total counts for the current period [optional]
    """
    try:
        return __api.dae.get_mevents()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_period():
    """Returns the current period number."""
    try:
        return __api.dae.get_period()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_number_periods():
    """Get the number of software periods."""
    try:
        return __api.dae.get_num_periods()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_period(period):
    """Sets the current period number."""
    try:
        return __api.dae.set_period(period)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_runnumber():
    """Get the current run number."""
    try:
        return __api.dae.get_run_number()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_totalcounts():
    """Get the total counts for the current run."""
    try:
        return __api.dae.get_total_counts()
    except Exception as e:
        _handle_exception(e)


# Commented out as not needed by users, rather they are for diagnostics
# Currently, does not work with the EPICS system
#~ def sum_all_dae_memory():
    #~ """Sum counts in all detector cards in the DAE."""
    #~ 
    #~ return __api.dae.sum_all_dae_memory()


#~ def sum_all_spectra():
    #~ """Get the sum of all the spectra in the DAE."""
    #~ 
    #~ return __api.dae.sum_all_spectra()

    
@_log_command
def get_title():
    """Returns the current title."""
    try:
        return __api.dae.get_title()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_title(title):
    """Sets the current title.
    
    PARAMETERS
    ----------
    title : the new title
    """
    try:
        __api.dae.set_title(title)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_rb():
    """Returns the current RB number."""
    try:
        return __api.dae.get_rb_number()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_dashboard():
    """Get the current experiment values.
    Returns a dictionary.
    """
    try:
        data = dict()
        data["status"] = __api.dae.get_run_state()
        data["run_number"] = __api.dae.get_run_number()
        data["rb_number"] = __api.dae.get_rb_number()
        data["user"] = __api.dae.get_users()
        data["title"] = __api.dae.get_title()
        data["run_time"] = __api.dae.get_run_duration()
        data["good_frames_total"] = __api.dae.get_good_frames()
        data["good_frames_period"] = __api.dae.get_good_frames(True)
        data["raw_frames_total"] = __api.dae.get_raw_frames()
        data["raw_frames_period"] = __api.dae.get_good_frames(True)
        data["beam_current"] = __api.dae.get_beam_current()
        data["total_current"] = __api.dae.get_total_uamps()
        data["spectra"] = __api.dae.get_num_spectra()
        #data["dae_memory_used"] = __api.dae.get_memory_used()         #Not implemented in EPICS system
        data["periods"] = __api.dae.get_num_periods()
        data["time_channels"] = __api.dae.get_num_timechannels()
        data["monitor_spectrum"] = __api.dae.get_monitor_spectrum()
        data["monitor_from"] = __api.dae.get_monitor_from()
        data["monitor_to"] = __api.dae.get_monitor_to()
        data["monitor_counts"] = __api.dae.get_monitor_counts()
        return data
    except Exception as e:
        _handle_exception(e)


def _correct_filepath(filepath):
    if os.name == 'nt':
        try:
            #correct path case for windows as Python needs correct casing
            return win32api.GetLongPathName(win32api.GetShortPathName(filepath))
        except Exception as err:
            raise Exception("Invalid file path entered: %s" % err)
    else:
        #Nothing to do for unix
        return filepath


def _convert_to_rawstring(data):
    escape_dict = {'\a': r'\a',
                   '\b': r'\b',
                   '\c': r'\c',
                   '\f': r'\f',
                   '\n': r'\n',
                   '\r': r'\r',
                   '\t': r'\t',
                   '\v': r'\v',
                   '\'': r'\'',
                   '\"': r'\"'}
    raw_string = ''
    for char in data:
        try: 
            raw_string += escape_dict[char]
        except KeyError: 
            raw_string += char
    return raw_string


def import_user_script_module(name, globs):
    """Loads user scripts from a module.
    This method should not be called directly instead use the load_script method.

    Parameters
    ----------
    name : the name of the file to load
    globs : the global settings dictionary of the caller
    """
    try:
        name = _convert_to_rawstring(name)
        name = name.__repr__().replace("\\", "/").replace("'", "").replace("//", "/")

        try:
            if "/" in name:
                #Probably a fullpath name
                name = _correct_filepath(name)
            else:
                #May be a file in the SCRIPT_DIR
                name = _correct_filepath(SCRIPT_DIR + name)
            directory, filename = os.path.split(os.path.abspath(name))
            directory += '\\'
        except:
            raise Exception("Script file was not found")

        mod = __load_module(filename[0:-3], directory)
        #If we get this far then the script is syntactically correct as far as Python is concerned
        #Now check the script details manually
        sc = ScriptChecker(__file__)
        errs = sc.check_script(name)
        if len(errs) > 0:
            combined = "script not loaded as errors found in script: "
            for e in errs:
                combined += "\n\t" + e
            raise Exception(combined)

        #Safe to load
        #Read the file to get the name of the functions
        funcs = []
        f = open(directory + filename, "r")
        for l in f.readlines():
            m = re.match("^def\s+(.+)\(", l)
            if m is not None:
                funcs.append(m.group(1))
        f.close()
        scripts = []
        for att in dir(mod):
            if isinstance(mod.__dict__.get(att), types.FunctionType):
                #Check function comes from script file not an import
                if att in funcs:
                    scripts.append(att)
        if len(scripts) > 0:
            #This is where the script file is actually loaded
            execfile(directory + filename, globs)
            msg = "Loaded the following script(s): "
            for script in scripts:
                msg += script + ", "
            print msg[0:-2]
            print "From: %s%s" % (directory, filename)
        else:
            raise Exception("No script found")
    except Exception as e:
        _handle_exception(e)


def __load_module(name, directory):
    """This will reload the module if it has already been loaded."""
    fpath = None
    try:
        fpath, pathname, description = imp.find_module(name, [directory])
        return imp.load_module(name, fpath, pathname, description)
    except Exception as e:
        raise Exception(e)
    finally:
        # Since we may exit via an exception, close fpath explicitly.
        if fpath is not None:
            fpath.close()


@_log_command
def get_script_dir():
    """Get the current script directory."""
    return SCRIPT_DIR

    
@_log_command
def set_script_dir(directory):
    """Set the directory for loading scripts from.
    
    Parameters
    ----------
    directory : the directory to load scripts from
    """
    try:
        directory = _convert_to_rawstring(directory)
        directory = _correct_filepath(directory.replace("\\", "/").replace("'", "").replace("//", "/"))
        if os.path.exists(directory):
            global SCRIPT_DIR
            if directory[-1] == "/":
                SCRIPT_DIR = directory
            else:
                SCRIPT_DIR = directory + "/"
        else:
            raise Exception("Directory does not exist")
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_start():
    """Start a change operation.
    The operaton is finished when change_finish is called.
    
    Between these two calls a sequence of other change commands can be called. 
    For example: change_tables, change_tcb etc.
    """
    try:
        
        __api.dae.change_start()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_finish():
    """End a change operation.
    The operaton is begun when change_start is called.
    
    Between these two calls a sequence of other change commands can be called. 
    For example: change_tables, change_tcb etc.
    """
    try:
        __api.dae.change_finish()
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_monitor(spec, low, high):
    """Change the monitor to a specified spectrum and range.
        
    Parameters
    ----------
    spectrum : the spectrum number (integer)
    low : the low end of the integral (float)
    high : the high end of the integral (float)
    """
    try:
        __api.dae.change_monitor(spec, low, high)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_tables(wiring=None, detector=None, spectra=None):
    """Load the wiring, detector and/or spectra tables.
        
    Parameters
    ----------
    wiring : the filename of the wiring table file [optional]
    detector : the filename of the detector table file [optional]
    spectra : the filename of the spectra table file [optional]
    """
    try:
        __api.dae.change_tables(wiring, detector, spectra)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_sync(source):
    """Change the source the DAE using for synchronisation.
        
    Parameters
    ----------
    source : the source to use ('isis', 'internal', 'smp', 'muon cerenkov', 'muon ms', 'isis (first ts1)')
    """
    try:
        __api.dae.change_sync(source)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_tcb_file(tcbfile=None, default=False):
    """Change the time channel boundaries.
        
    Parameters
    ----------
    tcbfile : the file to load [optional]
    default : load the default file "c:\\labview modules\\dae\\tcb.dat" [optional]
    """
    try:
        __api.dae.change_tcb_file(tcbfile, default)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_tcb(low, high, step, trange, log=False, regime=1):
    """Change the time channel boundaries.
        
    Parameters
    ----------
    low : the lower limit
    high : the upper limit
    step : the step size
    trange : the time range (1 to 5)
    log : whether to use LOG binning [optional]  
    regime : the time regime to set (1 or 2)[optional]        
    """
    try:
        __api.dae.change_tcb(low, high, step, trange, log, regime)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change_vetos(**params):
    """Change the DAE veto settings.
        
    Parameters
    ----------
    clearall : remove all vetos [optional]
    smp : set SMP veto [optional]
    ts2 : set TS2 veto [optional]
    hz50 : set 50 hz veto [optional]
    ext0 : set external veto 0 [optional]
    ext1 : set external veto 1 [optional]
    ext2 : set external veto 2 [optional]
    ext3 : set external veto 3 [optional]
    
    EXAMPLES
    --------
    
    If clearall is specified then all vetos are turned off, but it is possible to turn other vetoes 
    back on at the same time:
        
    >>> change_vetos(clearall=True, smp=True)    #Turns all vetoes off then turns the SMP veto back on
    """
    try:
        __api.dae.change_vetos(**params)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_fermi_veto(enable=None, delay=1.0, width=1.0):
    """Configure the fermi chopper veto.
        
    Parameters
    ----------
    enable : enable the fermi veto
    delay : the veto delay
    width : the veto width
    """
    try:
        __api.dae.set_fermi_veto(enable, delay, width)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def enable_soft_periods(nperiods=None):
    """Switch the DAE to software periods mode.
        
    Parameters
    ----------
    nperiods : the number of software periods [optional]
    """
    try:
        __api.dae.set_period_mode('soft')
        __api.dae.set_num_soft_periods(nperiods)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_number_soft_periods(number, enable=None):
    """Sets the number of software periods for the DAE.
        
    Parameters
    ----------
    number : the number of periods to create
    enable : switch to soft period mode [optional]
    """
    try:
        if enable:
            __api.dae.set_period_mode('soft')
        __api.dae.set_num_soft_periods(number)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def enable_hard_periods(mode, period_file=None, sequences=None, output_delay=None, period=None, daq=False, dwell=False,
                        unused=False, frames=None, output=None, label=None):
    """Sets the DAE to use hardware periods.
        
    Parameters
    ----------
    mode : set the mode to internal ('int') or external ('ext')
    period_file : the file containing the internal period settings (ignores any other settings) [optional]
    sequences : the number of times to repeat the period loop (0 = infinite loop) [optional]
    output_delay : the output delay in microseconds  [optional]
    period : the number of the period to set the following parameters for [optional]
    Note: if the period number is unspecified then the settings will be applied to all periods
    daq :  the specified period is a acquisition period [optional]
    dwell : the specified period is a dwell period [optional]
    unused : the specified period is a unused period [optional]
    frames : the number of frames to count for the specified period [optional]
    output : the binary output the specified period [optional]
    label : the label for the period the specified period [optional]
                 
    EXAMPLES
    --------

    Setting external periods:
    
    >>> enable_hard_periods('ext')
        
    Setting internal periods from a file:
    
    >>> enable_hard_periods('int', 'c:\\myperiods.txt')
    """
    try:
        __api.dae.configure_hard_periods(mode, period_file, sequences, output_delay, period, daq, dwell, unused, frames,
                                         output, label)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def configure_internal_periods(sequences=None, output_delay=None, period=None, daq=False, dwell=False, unused=False,
                               frames=None, output=None, label=None):
    """Configure the internal periods without switching to internal period mode.
        
    Parameters
    ----------
    file : the file containing the internal period settings (ignores any other settings) [optional]
    sequences : the number of times to repeat the period loop (0 = infinite loop) [optional]
    output_delay : the output delay in microseconds [optional]
    period : the number of the period to set the following parameters for [optional]
    Note: if the period number is unspecified then the settings will be applied to all periods
    daq :  the specified period is a acquisition period [optional]
    dwell : the specified period is a dwell period [optional]
    unused : the specified period is a unused period [optional]
    frames : the number of frames to count for the specified period [optional]
    output : the binary output the specified period [optional]
    label : the label for the period the specified period [optional]
    """
    try:
        __api.dae.configure_internal_periods(sequences, output_delay, period, daq, dwell, unused, frames, output, label)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def define_hard_period(period=None, daq=False, dwell=False, unused=False, frames=None, output=None, label=None):
    """Define the internal hardware periods.
        
    Parameters
    ----------
    period : the number of the period to set the following parameters for [optional]
    Note: if the period number is unspecified then the settings will be applied to all periods
    daq :  the specified period is a acquisition period [optional]
    dwell : the specified period is a dwell period [optional]
    unused : the specified period is a unused period [optional]
    frames : the number of frames to count for the specified period [optional]
    output : the binary output the specified period [optional]
    label : the label for the period the specified period [optional]
    """
    try:
        configure_internal_periods(None, None, period, daq, dwell, unused, frames, output, label)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def change(**params):
    """Change experiment parameters.

    Note: it is possible to change more than one item at a time.

    Parameters
    ----------
    title : change the current title
    period : change to a different period (must be in a non-running state)
    nperiods : change the number of software periods (must be in a non-running state)
    user : change the user(s) (not implemented)
    sample_name : change the sample name (not implemented)
    rbno : change the RB number (not implemented)
    aoi : change the angle of incidence (reflectometers only) (not implemented)
    phi : change the sample angle PHI (reflectometers only) (not implemented)

    EXAMPLE
    -------

    Change the title:

    >>> change(title="The new title")

    Change the RB number and the users:

    >>> change(rbno=123456, user="A. User and Ann Other")
    """
    try:
        for k in params:
            key = k.lower().strip()
            if key == 'title':
                set_title(params[k])
            elif key == 'period':
                set_period(params[k])
            elif key == 'nperiods':
                set_number_soft_periods(params[k])
            elif key == 'user' or key == 'users':
                __api.dae.set_users(params[k])
            #~ elif key == 'sample_name':
                #~ api.set_sample_name(params[k])
            #~ elif key == 'thickness':
                #~ api.set_sample_par('thickness', params[k])
            #~ elif key == 'rb' or key == 'rbno':
                #~ api.set_rb_number(params[k])
            #~ elif key == 'aoi':
                #~ api.change_vars(aoi=params[k])
            #~ elif key == 'phi':
                #~ api.change_vars(phi=params[k])
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_spectrum(spectrum, period=1, dist=False):
    """Get the specified spectrum from the DAE.
        
    Parameters
    ----------
    spectrum : the spectrum number
    period : the period [optional]
    dist : whether to get the spectrum as a distribution [optional]
    """
    try:
        return __api.dae.get_spectrum(spectrum, period, dist)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def plot_spectrum(spectrum, period=1, dist=False):
    """Get the specified spectrum from the DAE and plot it.
    Returns a GeniePlot object.
        
    Parameters
    ----------
    spectrum : the spectrum number
    period : the period [optional]
    dist : whether to get the spectrum as a distribution [optional]
    """
    try:
        graph = SpectraPlot(__api, spectrum, period, dist)
        return graph
    except Exception as e:
        _handle_exception(e)


@_log_command
def get_sample_pars():
    """Get the current sample parameter values."""
    try:
        names = __api.get_sample_pars()
        return names
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_sample_par(name, value):
    """Set a new value for a sample parameter

    Parameters
    ----------
        name : the name of the parameter to change
        value : the new value
    """
    try:
        __api.set_sample_par(name, value)
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def get_beamline_pars():
    """Get the current beamline parameter values."""
    try:
        names = __api.get_beamline_pars()
        return names
    except Exception as e:
        _handle_exception(e)

        
@_log_command
def set_beamline_par(name, value):
    """Set a new value for a beamline parameter

    Parameters
    ----------
        name : the name of the parameter to change
        value : the new value
    """
    try:
        __api.set_beamline_par(name, value)
    except Exception as e:
        _handle_exception(e)


@_log_command
def add_block(blockname, pvname, **kwargs):
    """Adds a block to Blockserver.

    Parameters
    ----------
    blockname : the name for the block (don't include prefix)
    pvname : the associated PV's name (include prefix)
    group : the group to put the block in [optional]
    local : is the PV local to the machine [optional, default=True]
    visible : is the block visible on the GUI [optional, default=True]
    save_rc : should the run-control settings be saved to the configuration [optional, default=False]

    Examples
    --------

    Add a block called SAMPLE_TEMP and put it in the TEMPERATURE group:

    >>> add_block("SAMPLE_TEMP", "IN:YOUR_INST:TEMP_CONTROL:TEMP_1", group="TEMPERATURE")
    """
    try:
        __api.log_entered_command()
        __api.blockserver.add_block(blockname, pvname, **kwargs)
        print "Block added - type action_block_changes() to update blocks"
    except Exception as e:
        _handle_exception(e)


@_log_command
def remove_block(blockname):
    """Removes a block from Blockserver.

    Parameters
    ----------
    blockname : the name of the block (don't include prefix)
    """
    try:
        __api.blockserver.remove_block(blockname)
        print "Block removed - type action_block_changes() to update blocks"
    except Exception as e:
        _handle_exception(e)


@_log_command
def action_block_changes():
    try:
        __api.blockserver.action_block_changes()
    except Exception as e:
        _handle_exception(e)


@_log_command
def get_config():
    """Get the name of the current configuration."""
    try:
        return __api.blockserver.get_config_name()
    except Exception as e:
        _handle_exception(e)
        
        
@_log_command
def get_configs():
    """Get the names of the available configurations."""
    try:
        return __api.blockserver.get_configs()
    except Exception as e:
        _handle_exception(e)


@_log_command
def load_config(name):
    """Load a configuration.

    Parameters
    ----------
    name : the name of the configuration to load
    """
    try:
        __api.blockserver.load_config(name)
    except Exception as e:
        _handle_exception(e)
        

@_log_command
def get_block_groups():
    """Get the block groups"""
    try:
        return __api.blockserver.get_block_groups()
    except Exception as e:
        _handle_exception(e)
        
        
@_log_command
def get_iocs():
    """Get the IOCs"""
    try:
        return __api.blockserver.get_iocs()
    except Exception as e:
        _handle_exception(e)
        
        
@_log_command
def get_config_iocs():
    """Get the IOCs in the configuration"""
    try:
        return __api.blockserver.get_config_iocs()
    except Exception as e:
        _handle_exception(e)

@_log_command
def send_sms(phone_num, message):
    """Send a text message to a mobile phone

    Parameters
    ----------
    phone_num : the mobile number to send to
    message : the message to send
    """
    try:
        from smslib.sms import send_sms
        send_sms(phone_num, message)
    except Exception as e:
        _handle_exception(e)


if __name__ == "__main__":
    #Put quick tests here, but delete them or make them into full tests when done.
    #~ set_beamline_par(aperture=123, aperture2=321)
    cshow()