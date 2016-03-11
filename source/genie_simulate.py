import os

global block_dict
block_dict = dict()
_exceptions_raised = False
global run_state
run_state = "SETUP"
global period
period = 1
global num_periods
num_periods = 1
global run_number
run_number = 123456

def cshow(block=None):
    """

    Args:
        block: Block name

    Examples:
        Show one block
        >>>cshow_sim("x")

        Show all blocks
        >>>cshow_sim()
    """
    try:
        if block:
            # Show only one block
            if block in block_dict.keys():
                print block_dict[block]
                output = block + ' = ' + str(block_dict[block][0])
                output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)\n' % (block_dict[block][1], block_dict[block][2], block_dict[block][3])
                print output
            else:
                raise Exception('No block with the name "%s" exists' % block)
        else:
            # Show all blocks
            for block in block_dict.keys():
                print block_dict[block]
                output = block + ' = ' + str(block_dict[block][0])
                output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)\n' % (block_dict[block][1], block_dict[block][2], block_dict[block][3])
                print output
    except Exception as e:
        _handle_exception(e)


def cset(*args, **kwargs):
    """

    Args:
        *args: block name and value
        **kwargs: other values (runcontrol, wait, highlimit, lowlimit)


    """
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
            # if not __api.block_exists(args[0]):
            #     raise Exception('No block with the name "%s" exists' % args[0])
            # else:
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
                blocks.append(k)
                values.append(kwargs[k])

        if block is not None and len(blocks) > 0:
            raise Exception('Incorrect syntax, please type: help(cset) for more information on the syntax')

        if block is not None:
            # Something like cset("block1", runcontrol=True) or cset("block1", 10)
            if wait:
                raise Exception('Cannot wait as no setpoint specified. Please type: help(cset) for help')
            set_block_value(block, value, runcontrol, lowlimit, highlimit, wait)
        elif len(blocks) == 1:
            # Something like cset(block1=123, runcontrol=True)
            if wait and runcontrol is not None:
                raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")
            else:
                set_block_value(blocks[0], values[0], runcontrol, lowlimit, highlimit, wait)
        else:
            # Setting multiple blocks, so runcontrol and waiting are not allowed
            if runcontrol is not None or lowlimit is not None or highlimit is not None:
                raise Exception('Runcontrol settings can only be changed for one block at a time')
            if wait is not None:
                raise Exception('Cannot wait for more than one block')
            set_multiple_blocks(blocks, values)
    except Exception as e:
        _handle_exception(e)


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


def _print_error_message(message):
    """Print the error message to screen"""
    # Look at using colorama?
    if os.name == 'nt':
        # Is windows
        print "ERROR: " + message
    else:
        # Non-windows
        print '\033[91m' + "ERROR: " + message + '\033[0m'


def set_block_value(name, value=None, runcontrol=None, lowlimit=None, highlimit=None, wait=False):
    try:
        block_values = [value, runcontrol, lowlimit, highlimit, wait]
        block_dict[name] = block_values
    except Exception as e:
        _handle_exception(e)


def set_multiple_blocks(names, values):
    """

    Args:
        names: list of block names
        values: list of block values (nested if multiple)

    Examples:
        Setting multiple blocks
        >>>set_multiple_blocks(["x","y"], [ [1, 2, 3, True], [1, 2, 3, False] ])

    """
    try:
        temp = zip(names, values)
        for name, value in temp:
            if name in block_dict:
                block_dict[name][0] = value
            else:
                block_dict[name] = [value, False, None, None, None]
    except Exception as e:
        _handle_exception(e)


def waitfor(block=None, value=None, lowlimit=None, highlimit=None, maxwait=None,
            wait_all=False, seconds=None, minutes=None, hours=None, time=None,
            frames=None, uamps=None, **pars):
    try:
        if block is None:
            # Search through the params to see if there is a block there
            blks = block_dict.keys()
            for k in pars:
                if k in blks:
                    if block is not None:
                        raise Exception('Can set waitfor for only one block at a time')
                    block = k
                    value = pars[k]
        # Check that wait_for object exists
        if waitfor_sim is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        # Start_waiting checks the block exists
        waitfor_start_waiting(block, value, lowlimit, highlimit, maxwait, wait_all, seconds, minutes, hours, time,
                              frames, uamps)
    except Exception as e:
        _handle_exception(e)


def waitfor_sim():
    pass


def waitfor_start_waiting(block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, wait_all=False,
                      seconds=None, minutes=None, hours=None, time=None, frames=None, uamps=None):
        pass


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
    global run_state
    try:
        if run_state == "SETUP":

            run_state = "RUNNING"
        else:
            raise Exception("Can only begin run from SETUP")
    except Exception as e:
        _handle_exception(e)


def abort(verbose=False):
    """Abort the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    global run_state

    try:
        if run_state == "RUNNING" or run_state == "PAUSED":
            run_state = "SETUP"
        else:
            raise Exception("Can only abort when RUNNING or PAUSED")
    except Exception as e:
        _handle_exception(e)


def end(verbose=False):
    """End the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    global run_state

    try:
        if run_state == "RUNNING" or run_state == "PAUSED":
            run_state = "SETUP"
        else:
            raise Exception("Can only abort when RUNNING or PAUSED")
    except Exception as e:
        _handle_exception(e)


def pause(verbose=False):
    """Pause the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    global run_state

    try:
        if run_state == "RUNNING":
            run_state = "PAUSED"
        else:
            raise Exception("Can only pause when state is RUNNING")
    except Exception as e:
        _handle_exception(e)


def resume(verbose=False):
    """Resume the current run after it has been paused.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    global run_state

    try:
        if run_state == "PAUSED":
            run_state = "RUNNING"
        else:
            raise Exception("Can only resume when state is PAUSED")
    except Exception as e:
        _handle_exception(e)


def updatestore(verbose=False):
    """Performs an update and a store operation in a combined operation.
    This is more efficient than doing the commands separately.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    try:
        if run_state == "RUNNING" or run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run in RUNNING or PAUSED")
    except Exception as e:
        _handle_exception(e)


def update(pause_run=True, verbose=False):
    """Data is loaded from the DAE into the computer memory, but is not written to disk.

    Args:
        pause_run (bool, optional) : whether to pause data collection first [optional]
        verbose (bool, optional) : show the messages from the DAE
    """
    try:
        if run_state == "RUNNING" or run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run in RUNNING or PAUSED")
    except Exception as e:
        _handle_exception(e)


def store(verbose=False):
    """Data loaded into memory by a previous update command is now written to disk.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    try:
        if run_state == "RUNNING" or run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run in RUNNING or PAUSED")
    except Exception as e:
        _handle_exception(e)


def get_runstate():
    return run_state


def get_period():
    """Gets the current period number.

    Returns:
        int : the current period
    """
    return period


def get_number_periods():
    """Get the number of software periods.

    Returns:
        int : the number of periods
    """
    return num_periods


def set_period(number):
    """Changes the current period number.

    Deprecated - use change_period

    Args:
        number (int) : the period to switch to
    """
    global period
    try:
        print "set_period is deprecated - use change_period"
        if period > num_periods:
            raise Exception("Number of periods is less than " + number)
        else:
            period = number
    except Exception as e:
        _handle_exception(e)


def change_period(number):
    """Changes the current period number.

    Args:
        number (int) : the period to switch to
    """
    global period
    try:
        if period > num_periods:
            raise Exception("Number of periods is less than " + number)
        else:
            period = number
    except Exception as e:
        _handle_exception(e)


def get_blocks():
    """Get the names of the blocks.

    Returns:
        list : the blocknames
    """
    return block_dict.keys()


def cget(block):
    """Gets the useful values associated with a block.

    Args:
        block (string) : the name of the block

    Returns
        dict : details about about the block
    """
    try:
        if block not in block_dict.keys():
            raise Exception('No block with the name "%s" exists' % block)

        ans = dict()
        ans['name'] = block
        ans['value'] = block_dict[block][0]

        rc = block_dict[block][1:]

        if rc is not None:
            ans['runcontrol'] = rc[1]
            ans['lowlimit'] = rc[2]
            ans['highlimit'] = rc[3]

        return ans
    except Exception as e:
        _handle_exception(e)


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
    try:
        None
    except Exception as e:
        _handle_exception(e)


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
    try:
        None
    except Exception as e:
        _handle_exception(e)


def get_runnumber():
    """Get the current run-number.

    Returns:
        string : the run-number
    """
    try:
        return run_number
    except Exception as e:
        _handle_exception(e)


def snapshot_crpt(filename="c:\\Data\snapshot_crpt.tmp", verbose=False):
    """Create a snapshot of the current data.

    Args:
        filename (string, optional) : where to write the data file(s)
        verbose (bool, optional) : show the messages from the DAE

    Examples:
        Snapshot to a file called my_snapshot:

        >>> snapshot_crpt("c:\\Data\my_snapshot")
    """
    try:
        None
    except Exception as e:
        _handle_exception(e)