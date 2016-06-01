import types
import os
import imp
import sys
import glob
import re
import ctypes
from functools import wraps
from collections import OrderedDict
from genie_script_checker import ScriptChecker
from utilities import waveform_to_string

# Determine whether to start in simulation mode
if 'GENIE_SIMULATE' in os.environ and os.environ['GENIE_SIMULATE'] == '1':
    print "\n=========== RUNNING IN SIMULATION MODE ===========\n"
    from genie_simulate import API
else:
    from genie_epics_api import API

# Windows specific stuff
if os.name == 'nt':
    # Needed for correcting file paths
    import win32api

if 'SCISOFT_RPC_PORT' in os.environ:
    from genie_scisoft_plot import GeniePlot, SpectraPlot
else:
    from genie_plot import GeniePlot, SpectraPlot
  

# INITIALISATION CODE - DO NOT DELETE
try:
    # If __api does not exist or is None then we need to create it.
    if __api is None:
        raise Exception("API does not exist")
except:
    # This should only get called the first time genie is imported
    my_pv_prefix = None
    if 'MYPVPREFIX' in os.environ:
        my_pv_prefix = os.environ['MYPVPREFIX']
        __api = API(my_pv_prefix, globals())
    else:
        print "No instrument specified - loading local instrument"
        __api = API(None, globals())

SCRIPT_DIR = "C:/scripts/"
_exceptions_raised = False
# END INITIALISATION CODE


# TAB COMPLETE FOR LOAD_SCRIPT
try:
    import readline

    def complete(text, state):
        if text.startswith('load_script("') or text.startswith("load_script('"):
            temp = text[13:]
            ans = (glob.glob(temp+'*')+[None])[state]
            if ans is not None:
                # return / to avoid a quoting issue with \ in paths
                return (text[:13] + ans).replace('\\', '/')
        else:
            return __ipy_complete(text, state)

    __ipy_complete = readline.get_completer()
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
except:
    pass
# END TAB COMPLETE


def usercommand(func):
    """Decorator that marks a function as a user command (e.g. for NICOS)."""
    func.is_usercommand = True
    func.is_hidden = False
    return func


def helparglist(args):
    """Decorator that supplies a custom argument list to be displayed by
    a help (e.g. for NICOS).
    """
    def deco(func):
        func.help_arglist = args
        return func
    return deco


if os.name == 'nt':
    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ('dwSize', ctypes.wintypes._COORD),
            ('dwCursorPosition', ctypes.wintypes._COORD),
            ('wAttributes', ctypes.c_ushort),
            ('srWindow', ctypes.wintypes._SMALL_RECT),
            ('dwMaximumWindowSize', ctypes.wintypes._COORD)
        ]


def _print_error_message(message):
    """Print the error message to screen"""
    # Look at using colorama?
    if os.name == 'nt':
        # Is windows
        std_output_handle = -11
        stdout_handle = ctypes.windll.kernel32.GetStdHandle(std_output_handle)
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, ctypes.byref(csbi))
        old_attrs = csbi.wAttributes
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, 12)
        print "ERROR: " + message
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, old_attrs)
    else:
        # Non-windows
        print '\033[91m' + "ERROR: " + message + '\033[0m'
    # Log it
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


def set_instrument(pv_prefix):
    """Sets the instrument this session is communicating with.
    Used for remote access - do not delete.

    Args:
        pv_prefix (string) : the PV prefix
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        globs = _get_correct_globals()
        __api.set_instrument(pv_prefix, globs)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_blocks():
    """Get the names of the blocks.

    Returns:
        list : the blocknames
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.get_blocks()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('...')
def cset(*args, **kwargs):
    """Sets the setpoint and runcontrol settings for blocks.
    
    Args:
        runcontrol (bool, optional) : whether to set runcontrol for this block
        wait (string, optional) : pause execution until setpoint isreached (one block only)
        lowlimit (float, optional) : the lower limit for runcontrol or waiting
        highlimit (float, optional): the upper limit for runcontrol or waiting

    Note: cannot use wait and runcontrol in the same command

    Examples:
        Setting a value for a block:

        >>> cset(block1=100)

        Or:

        >>> cset("block1", 100)

        Setting values for more than one block:

        >>> cset(block1=100, block2=200, block3=300)

        NOTE: the order in which the values are set is random,
        e.g. block1 may or may not be set before block2 and block3

        Setting runcontrol values for a block:

        >>> cset(block1=100, runcontrol=True, lowlimit=99, highlimit=101)

        Changing runcontrol settings for a block without changing the setpoint:

        >>> cset("block1", runcontrol=False)
        >>> cset(block1=None, runcontrol=False)

        Wait for setpoint to be reached (one block only):

        >>> cset(block1=100, wait=True)

        Wait for limits to be reached - this does NOT change the runcontrol limits:

        >>> cset(block1=100, wait=True, lowlimit=99, highlimit=101)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    # cset only works for blocks (currently)
    # Block names contain alpha-numeric and underscores only
    # Run-control not implemented yet!
    try:
        block = None
        blocks = []
        value = None
        values = []
        runcontrol = None
        lowlimit = None
        highlimit = None
        wait = None

        # See if single block name was entered, i.e. cset("block1", runcontrol=True)
        if len(args) > 0:
            if len(args) > 2:
                raise Exception('Too many arguments, please type: help(cset) for more information on the syntax')
            if not __api.block_exists(args[0]):
                raise Exception('No block with the name "%s" exists' % args[0])
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
                # Perhaps it is a block?
                if __api.block_exists(k):
                    blocks.append(k)
                    values.append(kwargs[k])
                else:
                    raise Exception('No block with the name "%s" exists' % k)

        if block is not None and len(blocks) > 0:
            raise Exception('Incorrect syntax, please type: help(cset) for more information on the syntax')

        if block is not None:
            # Something like cset("block1", runcontrol=True) or cset("block1", 10)
            if wait:
                raise Exception('Cannot wait as no setpoint specified. Please type: help(cset) for help')
            __api.set_block_value(block, value, runcontrol, lowlimit, highlimit, wait)
        elif len(blocks) == 1:
            # Something like cset(block1=123, runcontrol=True)
            if wait and runcontrol is not None:
                raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")
            else:
                __api.set_block_value(blocks[0], values[0], runcontrol, lowlimit, highlimit, wait)
        else:
            # Setting multiple blocks, so runcontrol and waiting are not allowed
            if runcontrol is not None or lowlimit is not None or highlimit is not None:
                raise Exception('Runcontrol settings can only be changed for one block at a time')
            if wait is not None:
                raise Exception('Cannot wait for more than one block')
            __api.set_multiple_blocks(blocks, values)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('block')
def cget(block):
    """Gets the useful values associated with a block.

    Args:
        block (string) : the name of the block

    Returns
        dict : details about about the block
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if not __api.block_exists(block):
            raise Exception('No block with the name "%s" exists' % block)
            
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


def _cshow_all():
    blks = __api.get_current_block_values()
    for bn, bv in blks.iteritems():
        if bv[0] == "*** disconnected" or bv[0] is None:
            _print_cshow(bn, connected=False)
        else:
            _print_cshow(bn, bv[0], bv[1], bv[2], bv[3])


def _print_cshow(name, value=None, rc_enabled=None, rc_low=None, rc_high=None, connected=True):
    if connected:
        print '%s = %s (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (name, value, rc_enabled, rc_low, rc_high)
    else:
        print "%s = *** disconnected ***" % name


def cshow(block=None):
    """Show the current settings for one block or for all blocks.

    Args:
        block (string, optional) : the name of the block

    Examples:
        Showing all block values:
        >>> cshow()

        Showing values for one block only (name must be quoted):
        >>> cshow("block1")
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if block:
            # Show only one block
            if __api.block_exists(block):
                rc = __api.get_runcontrol_settings(block)
                _print_cshow(block, __api.get_block_value(block, attempts=1), rc["ENABLE"], rc["LOW"],rc["HIGH"])
            else:
                raise Exception('No block with the name "%s" exists' % block)
        else:
            # Show all blocks
            _cshow_all()
    except Exception as e:
        _handle_exception(e)


def waitfor(block=None, value=None, lowlimit=None, highlimit=None, maxwait=None,
            wait_all=False, seconds=None, minutes=None, hours=None, time=None,
            frames=None, uamps=None, **pars):
    """Interrupts execution until certain conditions are met.
    
    Args:
        block (string, optional) : the name of the block to wait for
        value (float, optional) : the block value to wait for
        lowlimit (float, optional): wait for the block to be >= this value
        highlimit (float, optional) : wait for the block to be <= this value
        maxwait (float, optional) : wait no longer that the specified number of seconds
        wait_all (bool, optional) : wait for all conditions to be met (e.g. a number of frames and an amount of uamps)
        seconds (float, optional) : wait for a specified number of seconds
        minutes (float, optional) : wait for a specified number of minutes
        hours (float, optional) : wait for a specified number of hours
        time (string, optional) : a quicker way of setting hours, minutes and seconds (must be of format "HH:MM:SS")
        frames (int, optional) : wait for a total number of good frames to be collected
        uamps (float, optional) : wait for a total number of uamps to be received
        
    Examples:
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
    __api.log_command(sys._getframe().f_code.co_name, locals())
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


@usercommand
@helparglist('...')
def waitfor_value(block, value, maxwait=None):
    """Interrupts execution until block reaches specific value

    Args:
        block: the name of the block to wait for
        value: the target block value
        maxwait: wait no longer that the specified number of seconds

    Examples:
        >>> waitfor("myblock", 123)
        >>> waitfor("myblock", True)
        >>> waitfor("myblock", "OPEN", maxwait=15)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.start_waiting(block=block, value=value, maxwait=maxwait)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('...')
def waitfor_limit(block, lowlimit=None, highlimit=None, maxwait=None):
    """Interrupts execution until block value within between specified limit(s)

    Args:
        block: the name of the block to wait for
        lowlimit: waits for the block to be >= this value
        highlimit: waits for the block to be <= this value
        maxwait: wait no longer that the specified number of seconds

    Examples:
        >>> waitfor("myblock", lowlimit=100, highlimit=110)
        >>> waitfor("myblock", highlimit=1.0, maxwait=60)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if lowlimit is None and highlimit is None:
            raise Exception("Cannot execute waitfor_limit - need to set at least one limit. Type help(waitfor_limit) to"
                            " see guidelines")
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.start_waiting(block=block, lowlimit=lowlimit, highlimit=highlimit, maxwait=maxwait)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('...')
def waitfor_time(seconds=None, minutes=None, hours=None, time=None):
    """Interrupts execution for a specified amount of time

    Args:
        seconds (float, optional) : wait for a specified number of seconds
        minutes (float, optional) : wait for a specified number of minutes
        hours (float, optional) : wait for a specified number of hours
        time (string, optional) : a quicker way of setting hours, minutes and seconds (must be of format "HH:MM:SS")

    Examples:
        >>> waitfor(seconds=10)
        >>> waitfor(hours=1, minutes=30, seconds=15)
        >>> waitfor(time="1:30:15")
    """
    try:
        if seconds is None and minutes is None and hours is None and time is None:
            raise Exception("Cannot execute waitfor_time - need to set at least one parameter. Type help(waitfor_time) "
                            "to see guidelines")
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.start_waiting(seconds=seconds, minutes=minutes, hours=hours, time=time)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('...')
def waitfor_frame(frame):
    """Interrupts execution to wait for a specific frame

    Args:
        frame: the frame to wait for

    Example:
        >>> waitfor_frame(50000)
    """
    try:
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.start_waiting(frames=frames)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('...')
def waitfor_uamps(uamps):
    """Interrupts execution to wait for a specific total charge

    Args:
        uamps: the charge to wait for

    Example:
        >>> waitfor_uamps(35000)
    """
    try:
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.start_waiting(uamps=uamps)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('state[, maxwaitsecs][, onexit]')
def waitfor_runstate(state, maxwaitsecs=3600, onexit=False):
    """Wait for a particular instrument run state.
        
    Args:
        state (string) : the state to wait for (e.g. "paused")
        maxwaitsecs (int, optional) : the maximum time to wait for the state before carrying on
        onexit (bool, optional) : wait for runstate to change from the specified state
            
    Examples:
        Wait for a run to enter the paused state:
        >>> waitfor_runstate("pause")

        Wait for a run to exit the paused state:
        >>> waitfor_runstate("pause", onexit=True)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        # Check that wait_for object exists
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.wait_for_runstate(state, maxwaitsecs, onexit)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[block, ...][, start_timeout][, move_timeout]')
def waitfor_move(*blocks, **kwargs):
    """ Wait for all motion or specific motion to complete.

    If block names are supplied then it will only wait for those to stop moving. Otherwise, it will wait for all motion
    to stop.

    Args:
        blocks (string, multiple, optional) : the names of specific blocks to wait for
        start_timeout (int, optional) : the number of seconds to wait for the movement to begin (default = 2 seconds)
        move_timeout (int, optional) : the maximum number of seconds to wait for motion to stop

    Examples:
        Wait for all motors to stop moving:
        >>> waitfor_move()

        Wait for all motors to stop moving with a timeout of 30 seconds:
        >>> waitfor_move(move_timeout=30)

        Wait for only slit1 and slit2 motors to stop moving:
        >>> waitfor_move("slit1", "slit2")
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())

    # Sort out the parameters
    # Standard parameters
    if 'start_timeout' in kwargs:
        start_timeout = kwargs['start_timeout']
    else:
        start_timeout = 2
    if 'move_timeout' in kwargs:
        move_timeout = kwargs['move_timeout']
    else:
        move_timeout = None

    try:
        # Check that wait_for_move object exists
        if __api.wait_for_move is None:
            raise Exception("Cannot execute waitfor_move - try calling set_instrument first")

        if len(blocks) > 0:
            # Specified blocks waitfor_move
            move_blocks = list()
            # Check blocks exist
            for b in blocks:
                if __api.block_exists(b):
                    move_blocks.append(b)
                else:
                    print "Block %s does not exist, so ignoring it" % b
            __api.wait_for_move.wait_specific(move_blocks, start_timeout, move_timeout)
        else:
            # Standard waitfor_move
            __api.wait_for_move.wait(start_timeout, move_timeout)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('name[, to_string]')
def get_pv(name, to_string=False):
    """Get the value for the specified PV.
    
    Args:
        name (string) : the name of the PV to get the value for
        to_string (bool, optional) : whether to get the value as a string

    Returns:
        the current PV value
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if not __api.pv_exists(name):
            raise Exception('PV %s does not exist' % name)
        return __api.get_pv_value(name, to_string)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('name, value[, wait]')
def set_pv(name, value, wait=False):
    """Set the value for the specified PV.
        
    Args:
        name (string) : the PV name
        value : the new value to set
        wait (bool, optional) : whether to wait until the value has been received by the hardware
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.set_pv_value(name, value, wait)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('verbose')
def set_messages_verbosity(verbose):
    """Set the global verbosity of messages.
    
    Args:
        verbose (bool): set the verbosity
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    __api.dae.set_verbose(verbose)    


@usercommand
@helparglist('...')
def begin(period=1, meas_id=None, meas_type="", meas_subid="", sample_id="", delayed=False, quiet=False, paused=False,
          verbose=False):
    """Starts a data collection run.
        
    Args:
        period (int, optional) : the period to begin data collection in
        meas_id (string, optional) : the measurement id
        meas_type (string, optional) : the type of measurement
        meas_subid (string, optional) : the measurement sub-id
        sample_id (string, optional) : the sample id
        delayed (bool, optional) : puts the period card to into delayed start mode
        quiet (bool, optional) : suppress the output to the screen
        paused (bool, optional) : begin in the paused state
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.run_pre_post_cmd("begin_precmd", quiet=quiet)
        __api.dae.begin_run(period, meas_id, meas_type, meas_subid, sample_id, delayed, quiet, paused)
        waitfor_runstate("SETUP", onexit=True)
        __api.dae.post_begin_check(verbose)
        __api.run_pre_post_cmd("begin_postcmd", run_num=__api.dae.get_run_number(), quiet=quiet)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def abort(verbose=False):
    """Abort the current run.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.run_pre_post_cmd("abort_precmd")
        __api.dae.abort_run()
        waitfor_runstate("SETUP")
        __api.dae.post_abort_check(verbose)
        __api.run_pre_post_cmd("abort_postcmd")
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def end(verbose=False):
    """End the current run.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.run_pre_post_cmd("end_precmd")
        __api.dae.end_run()
        waitfor_runstate("SETUP")
        __api.dae.post_end_check(verbose)
        __api.run_pre_post_cmd("end_postcmd")
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def pause(verbose=False):
    """Pause the current run.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.run_pre_post_cmd("pause_precmd")
        __api.dae.pause_run()
        waitfor_runstate("PAUSED")
        __api.dae.post_pause_check(verbose)
        __api.run_pre_post_cmd("pause_postcmd")
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def resume(verbose=False):
    """Resume the current run after it has been paused.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.run_pre_post_cmd("resume_precmd")
        __api.dae.resume_run()
        waitfor_runstate("PAUSED", onexit=True)
        __api.dae.post_resume_check(verbose)
        __api.run_pre_post_cmd("resume_postcmd")
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def recover(verbose=False):
    """Recovers the run if it has been aborted.
    The command should be run before the next run is started.
    
    Note: the run will be recovered in the paused state.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.recover_run()
        waitfor_runstate("SETUP", onexit=True)
        __api.dae.post_recover_check(verbose)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def updatestore(verbose=False):
    """Performs an update and a store operation in a combined operation.
    This is more efficient than doing the commands separately.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.update_store_run()
        waitfor_runstate("SAVING", onexit=True)
        __api.dae.post_update_store_check(verbose)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[pause_run], [verbose]')
def update(pause_run=True, verbose=False):
    """Data is loaded from the DAE into the computer memory, but is not written to disk.
        
    Args:
        pause_run (bool, optional) : whether to pause data collection first [optional]
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if pause_run:
            # Pause
            pause(verbose=verbose)

        # Update
        __api.dae.update_run()
        waitfor_runstate("UPDATING", onexit=True)
        __api.dae.post_update_check(verbose)

        if pause_run:
            # Resume
            resume(verbose=verbose)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[verbose]')
def store(verbose=False):
    """Data loaded into memory by a previous update command is now written to disk.
    
    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.store_run()
        waitfor_runstate("STORING", onexit=True)
        __api.dae.post_store_check(verbose)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[filename], [verbose]')
def snapshot_crpt(filename="c:\\Data\snapshot_crpt.tmp", verbose=False):
    """Create a snapshot of the current data.

    Args:
        filename (string, optional) : where to write the data file(s)
        verbose (bool, optional) : show the messages from the DAE

    Examples:
        Snapshot to a file called my_snapshot:

        >>> snapshot_crpt("c:\\Data\my_snapshot")
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        name = _correct_filepath(filename)
        __api.dae.snapshot_crpt(name)
        waitfor_runstate("STORING", onexit=True)
        __api.dae.post_snapshot_check(verbose)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[period]')
def get_uamps(period=False):
    """Get the current number of micro-amp hours.
        
    Args:
        period (bool, optional) : whether to return the value for the current period only

    Returns:
        float : the number of uamps
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_uamps(period)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[period]')
def get_frames(period=False):
    """Gets the current number of good frames.
        
    Args:
        period (bool, optional) : whether to return the value for the current period only

    Returns:
        int : the number of frames
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_good_frames(period)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_runstate():
    """Get the current status of the instrument as a string.
    
    Note: this value can take a few seconds to update after a change of state.

    Returns:
        string : the current run state
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_run_state()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_mevents():
    """Gets the total counts for all the detectors.

    Returns:
        float : the number of mevents
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_mevents()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_period():
    """Gets the current period number.

    Returns:
        int : the current period
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_period()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_number_periods():
    """Get the number of software periods.

    Returns:
        int : the number of periods
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_num_periods()
    except Exception as e:
        _handle_exception(e)


def set_period(period):
    """Sets the current period number.

    Deprecated - use change_period

    Args:
        period (int) : the period to switch to
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    print "set_period is deprecated - use change_period"
    change_period(period)



@usercommand
@helparglist('')
def get_runnumber():
    """Get the current run-number.

    Returns:
        string : the run-number
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_run_number()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_totalcounts():
    """Get the total counts for the current run.

    Returns:
        int : the total counts
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_total_counts()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_title():
    """Returns the current title.

    Returns:
        string : the title
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_title()
    except Exception as e:
        _handle_exception(e)


def set_title(title):
    """Sets the current title.

    Deprecated - use change_title

    Args:
        title : the new title
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    print "set_title is deprecated - use change_title"
    change_title(title)


@usercommand
@helparglist('')
def get_rb():
    """Returns the current RB number.

    Returns:
        string : the RB number
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_rb_number()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_dashboard():
    """Get the current experiment values.

    Returns:
        dict : the experiment values
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
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
        # data["dae_memory_used"] = __api.dae.get_memory_used()         #Not implemented in EPICS system
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
    """Corrects the slashes"""
    return filepath.__repr__().replace("\\", "/").replace("'", "").replace("//", "/")


def _correct_filepath_existing(filepath):
    """If the file exists it get the correct path with the correct casing"""
    filepath = _correct_filepath(filepath)
    if os.name == 'nt':
        try:
            # Correct path case for windows as Python needs correct casing
            return win32api.GetLongPathName(win32api.GetShortPathName(filepath))
        except Exception as err:
            raise Exception("Invalid file path entered: %s" % err)
    else:
        # Nothing to do for unix
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


def _get_correct_globals():
    """This is a hack to find the frame in which to add the script function(s).

    The frame we want is the outermost one that contains a reference to cshow().
    """
    import inspect

    globs = dict()

    for i in inspect.stack():
        if "cshow" in i[0].f_globals:
            globs = i[0].f_globals
    return globs


def load_script(name, dummy=None):
    """Loads a user script.
    Args:
        name (string) : the name of the file to load
        dummy (object) : This is a dummy parameter just so the GUI does not complain once the GUI is updated we can
        remove this
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    # This check can be removed once the GUI is updated to no longer use the second parameter
    if name is None:
        return

    try:
        globs = _get_correct_globals()

        name = _convert_to_rawstring(name)

        try:
            if "/" in name:
                # Probably a fullpath name
                name = _correct_filepath_existing(name)
            else:
                # May be a file in the SCRIPT_DIR
                name = _correct_filepath_existing(SCRIPT_DIR + name)
            directory, filename = os.path.split(os.path.abspath(name))
            directory += '\\'
        except:
            raise Exception("Script file was not found")

        mod = __load_module(filename[0:-3], directory)
        # If we get this far then the script is syntactically correct as far as Python is concerned
        # Now check the script details manually
        sc = ScriptChecker(__file__)
        errs = sc.check_script(name)
        if len(errs) > 0:
            combined = "script not loaded as errors found in script: "
            for e in errs:
                combined += "\n\t" + e
            raise Exception(combined)

        # Safe to load
        # Read the file to get the name of the functions
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
                # Check function comes from script file not an import
                if att in funcs:
                    scripts.append(att)
        if len(scripts) > 0:
            # This is where the script file is actually loaded
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


def get_script_dir():
    """Get the current script directory.

    Returns:
        string : the directory
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    return SCRIPT_DIR


def set_script_dir(directory):
    """Set the directory for loading scripts from.

    Deprecated - use change_script_dir.

    Args:
        string : the directory to load scripts from
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    print "set_script_dir is deprecated - use change_script_dir"
    change_script_dir(directory)


def change_script_dir(directory):
    """Set the directory for loading scripts from.
    
    Args:
        string : the directory to load scripts from
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        directory = _convert_to_rawstring(directory)
        directory = _correct_filepath_existing(directory)
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


@usercommand
@helparglist('')
def change_start():
    """Start a change operation.
    The operation is finished when change_finish is called.
    
    Between these two calls a sequence of other change commands can be called. 
    For example: change_tables, change_tcb etc.
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        
        __api.dae.change_start()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def change_finish():
    """End a change operation.
    The operation is begun when change_start is called.
    
    Between these two calls a sequence of other change commands can be called. 
    For example: change_tables, change_tcb etc.
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_finish()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('spec, low, high')
def change_monitor(spec, low, high):
    """Change the monitor to a specified spectrum and range.
        
    Args:
        spectrum (int) : the spectrum number
        low (float) : the low end of the integral
        high (float) : the high end of the integral
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_monitor(spec, low, high)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[wiring], [detector], [spectra]')
def change_tables(wiring=None, detector=None, spectra=None):
    """Load the wiring, detector and/or spectra tables.
        
    Args:
        wiring (string, optional) : the filename of the wiring table file
        detector (string, optional) : the filename of the detector table file
        spectra (string, optional) : the filename of the spectra table file
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_tables(wiring, detector, spectra)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('source')
def change_sync(source):
    """Change the source the DAE using for synchronisation.
        
    Args:
        source (string) : the source to use ('isis', 'internal', 'smp', 'muon cerenkov', 'muon ms', 'isis (first ts1)')
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_sync(source)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[tcbfile], [default]')
def change_tcb_file(tcbfile=None, default=False):
    """Change the time channel boundaries.
        
    Args:
        tcbfile (string, optional) : the file to load
        default (bool, optional): load the default file
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_tcb_file(tcbfile, default)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('low, high, step, trange[, log][, regime]')
def change_tcb(low, high, step, trange, log=False, regime=1):
    """Change the time channel boundaries.
        
    Args
        low (float) : the lower limit
        high (float) : the upper limit
        step (float) : the step size
        trange (int) : the time range (1 to 5)
        log (bool, optional) : whether to use LOG binning
        regime (int, optional) : the time regime to set (1 to 6)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_tcb(low, high, step, trange, log, regime)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[...]')
def change_vetos(**params):
    """Change the DAE veto settings.
        
    Args:
        clearall (bool, optional) : remove all vetos
        smp (bool, optional) : set SMP veto
        ts2 (bool, optional) : set TS2 veto
        hz50 (bool, optional) : set 50 hz veto
        ext0  (bool, optional): set external veto 0
        ext1  (bool, optional): set external veto 1
        ext2 (bool, optional) : set external veto 2
        ext3 (bool, optional) : set external veto 3

    Note: If clearall is specified then all vetos are turned off,
    but it is possible to turn other vetoes back on at the same time:
    
    Examples:
        Turns all vetoes off then turns the SMP veto back on:
        >>> change_vetos(clearall=True, smp=True)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.change_vetos(**params)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[enable], [delay], [width]')
def change_fermi_veto(enable=None, delay=1.0, width=1.0):
    """Configure the fermi chopper veto.
        
    Args:
        enable (bool, optional) : enable the fermi veto
        delay (float, optional) : the veto delay
        width (float, optional) : the veto width
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.set_fermi_veto(enable, delay, width)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[nperiods]')
def enable_soft_periods(nperiods=None):
    """Switch the DAE to software periods mode.
        
    Args:
        nperiods (int, optional) : the number of software periods
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.set_period_mode('soft')
        if nperiods is not None:
            __api.dae.set_num_soft_periods(nperiods)
    except Exception as e:
        _handle_exception(e)


def set_number_soft_periods(number, enable=None):
    """Sets the number of software periods for the DAE.

    Deprecated - use change_number_soft_periods

    Args:
        number (int) : the number of periods to create
        enable (bool, optional) : switch to soft period mode
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    print "set_number_soft_periods is deprecated - use change_number_soft_periods"
    change_number_soft_periods(number, enable)


@usercommand
@helparglist('mode[, ...]')
def enable_hard_periods(mode, period_file=None, sequences=None, output_delay=None, period=None, daq=False, dwell=False,
                        unused=False, frames=None, output=None, label=None):
    """Sets the DAE to use hardware periods.
        
    Args:
        mode (string) : set the mode to internal ('int') or external ('ext')
        period_file (string, optional) : the file containing the internal period settings (ignores any other settings)
        sequences (int, optional) : the number of times to repeat the period loop (0 = infinite loop)
        output_delay (int, optional) : the output delay in microseconds
        period (int, optional) : the number of the period to set the following parameters for
        daq (bool, optional) :  the specified period is a acquisition period
        dwell (bool, optional) : the specified period is a dwell period
        unused (bool, optional) : the specified period is a unused period
        frames (int, optional) : the number of frames to count for the specified period
        output (int, optional) : the binary output the specified period
        label (string, optional) : the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods

    Examples:
        Setting external periods:
        >>> enable_hard_periods('ext')

        Setting internal periods from a file:
        >>> enable_hard_periods('int', 'c:\\myperiods.txt')
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.configure_hard_periods(mode, period_file, sequences, output_delay, period, daq, dwell, unused, frames,
                                         output, label)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[...]')
def configure_internal_periods(sequences=None, output_delay=None, period=None, daq=False, dwell=False, unused=False,
                               frames=None, output=None, label=None):
    """Configure the internal periods without switching to internal period mode.

    Args:
        sequences (int, optional) : the number of times to repeat the period loop (0 = infinite loop)
        output_delay (int, optional) : the output delay in microseconds
        period (int, optional) : the number of the period to set the following parameters for
        daq (bool, optional) :  the specified period is a acquisition period
        dwell (bool, optional) : the specified period is a dwell period
        unused (bool, optional) : the specified period is a unused period
        frames (int, optional) : the number of frames to count for the specified period
        output (int, optional) : the binary output the specified period
        label (string, optional) : the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.configure_internal_periods(sequences, output_delay, period, daq, dwell, unused, frames, output, label)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('[...]')
def define_hard_period(period=None, daq=False, dwell=False, unused=False, frames=None, output=None, label=None):
    """Define the internal hardware periods.
        
    Args:
        period (int, optional) : the number of the period to set the following parameters for
        daq (bool, optional) :  the specified period is a acquisition period
        dwell (bool, optional) : the specified period is a dwell period
        unused (bool, optional) : the specified period is a unused period
        frames (int, optional) : the number of frames to count for the specified period
        output (int, optional) : the binary output the specified period
        label (string, optional) : the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        configure_internal_periods(None, None, period, daq, dwell, unused, frames, output, label)
    except Exception as e:
        _handle_exception(e)



def change(**params):
    """Change experiment parameters.

    Note: it is possible to change more than one item at a time.

    Args:
        title (string, optional) : change the current title
        period (int, optional) : change to a different period (must be in a non-running state)
        nperiods (int, optional) : change the number of software periods (must be in a non-running state)
        user (string, optional) : change the user(s)

    Examples:
        Change the title:
        >>> change(title="The new title")

        Change the RB number and the users:
        >>> change(rbno=123456, user="A. User and Ann Other")
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        for k in params:
            key = k.lower().strip()
            if key == 'title':
                change_title(params[k])
            elif key == 'period':
                change_period(params[k])
            elif key == 'nperiods':
                change_number_soft_periods(params[k])
            elif key == 'user' or key == 'users':
                change_users(params[k])
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('title')
def change_title(title):
    """Sets the current title.

    Args:
        title : the new title
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.set_title(title)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('period')
def change_period(period):
    """Changes the current period number.

    Args:
        period (int) : the period to switch to
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.set_period(period)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('number[, enable]')
def change_number_soft_periods(number, enable=None):
    """Sets the number of software periods for the DAE.

    Args:
        number (int) : the number of periods to create
        enable (bool, optional) : switch to soft period mode
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        if enable:
            __api.dae.set_period_mode('soft')
        __api.dae.set_num_soft_periods(number)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('number[, enable]')
def change_users(users):
    """Changes the users of the DAE

    Args:
        users: a string containing the user name(s)
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.dae.set_users(users)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('spectrum[, period][, dist]')
def get_spectrum(spectrum, period=1, dist=False):
    """Get the specified spectrum from the DAE.
        
    Args:
        spectrum (int) : the spectrum number
        period (int, optional) : the period
        dist (bool, optional) : whether to get the spectrum as a distribution

    Returns:
        dict : dictionary of values
    """
    try:
        return __api.dae.get_spectrum(spectrum, period, dist)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('spectrum[, period][, dist]')
def plot_spectrum(spectrum, period=1, dist=False):
    """Get the specified spectrum from the DAE and plot it.
        
    Args:
        spectrum (int) : the spectrum number
        period (int, optional) : the period. Default is 1
        dist (bool, optional) : whether to get the spectrum as a distribution. Default is False

    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    __api.plots.remove_closed()
    try:
        graph = SpectraPlot(__api, spectrum, period, dist)
        __api.plots.add_plot(graph)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('spectrum[, period][, dist]')
def add_spectrum(spectrum, period=1, dist=False, figure=None):
    """Add a spectrum graph to an existing plot

    Args:
        spectrum (int) : the spectrum number
        period (int, optional) : the period. Default is 1
        dist (bool, optional) : whether to get the spectrum as a distribution. Default is False
        figure (int, optional) : specifies which figure to plot the spectrum in. Default is last active plot

    Examples:
        Add Spectrum 2 to last active plot window
        >>> add_spectrum(2)

        Add Spectrum 1 to Figure 3
        >>> add_spectrum(2, figure=3)

        Add Spectrum 1 with period=2 to last active plot window as distribution
        >>> add_spectrum(1, period=2, dist=True)

        Add Spectrum 4 to Figure 1 as distribution
        >>> add_spectrum(4, dist=True, figure=1)
    """
    __api.plots.remove_closed()
    try:
        if figure is None:
            __api.plots.has_last_changed()
            figure = __api.plots.get_last_plot()
        else:
            figure = __api.plots.get_plot(figure)
            __api.plots.set_last_plot(figure)
        figure.add_spectrum(spectrum, period, dist)
    except Exception:
        if figure is None:
            print "Plotting failed: Create a plot first using plot_spectrum(<number>)"
        else:
            print "Plotting failed: Figure " + repr(figure) + " not found."


@usercommand
@helparglist('')
def get_sample_pars():
    """Get the current sample parameter values.

    Returns:
        dict : the sample parameters
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        names = __api.get_sample_pars()
        return names
    except Exception as e:
        _handle_exception(e)


def set_sample_par(name, value):
    """Set a new value for a sample parameter

    Deprecated - use change_sample_par

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    print "set_sample_par is deprecated - use change_sample_par"
    change_sample_par(name, value)


@usercommand
@helparglist('name, value')
def change_sample_par(name, value):
    """Set a new value for a sample parameter

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.set_sample_par(name, value)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_beamline_pars():
    """Get the current beamline parameter values.

    Returns:
        dict : the beamline parameters
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        names = __api.get_beamline_pars()
        return names
    except Exception as e:
        _handle_exception(e)


def set_beamline_par(name, value):
    """Set a new value for a beamline parameter

    Deprecated - use change_beamline_par

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    print "set_beamline_par is deprecated - use change_beamline_par"
    change_beamline_par(name, value)


@usercommand
@helparglist('name, value')
def change_beamline_par(name, value):
    """Set a new value for a beamline parameter

    Args:
        name (string, optional) : the name of the parameter to change
        value (optional) : the new value
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        __api.set_beamline_par(name, value)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('phone_num, message')
def send_sms(phone_num, message):
    """Send a text message to a mobile phone

    Args:
        phone_num (string) : the mobile number to send to
        message (string) : the message to send
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        from smslib.sms import send_sms
        send_sms(phone_num, message)
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_wiring_tables():
    """Gets a list of possible wiring table choices.

    Returns:
        list : the files
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_wiring_tables()
    except Exception as e:
        _handle_exception(e)
        

@usercommand
@helparglist('')
def get_spectra_tables():
    """Gets a list of possible spectra table choices.

    Returns:
        list : the files
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_spectra_tables()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_detector_tables():
    """Gets a list of possible detector table choices.

    Returns:
        list : the files
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_detector_tables()
    except Exception as e:
        _handle_exception(e)


@usercommand
@helparglist('')
def get_period_files():
    """Gets a list of possible period file choices.

    Returns:
        list : the files
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    try:
        return __api.dae.get_period_files()
    except Exception as e:
        _handle_exception(e)


def check_alarms(*blocks):
    """Checks whether the specified blocks are in alarm.

    Args:
        blocks (string, multiple) : the block(s) to check

    Returns:
        list, list : the blocks in minor alarm and major alarm respectively

    Example:
        Check alarm state for block1 and block2:
        >>> check_alarms("block1", "block2")
    """
    __api.log_command(sys._getframe().f_code.co_name, locals())
    return __api.check_alarms(blocks)
