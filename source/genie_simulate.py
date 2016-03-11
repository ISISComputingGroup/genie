import os

global block_dict
block_dict = dict()
_exceptions_raised = False
global run_state
run_state = "SETUP"

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