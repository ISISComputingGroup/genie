import os


class Waitfor(object):
    def __init__(self):
        pass

    def start_waiting(self, block=None, value=None, lowlimit=None, highlimit=None, maxwait=None, wait_all=False,
                      seconds=None, minutes=None, hours=None, time=None, frames=None, uamps=None):
        pass

    def wait_for_runstate(self, state, maxwaitsecs=3600, onexit=False):
        pass


class Dae(object):
    def __init__(self):
        self.run_state = "SETUP"
        self.run_number = 123456
        self.period_current = 1
        self.num_periods = 1

    def begin_run(self, period=None, meas_id=None, meas_type=None, meas_subid=None,
                  sample_id=None, delayed=False, quiet=False, paused=False):
        if self.run_state == "SETUP":
            self.run_state = "RUNNING"
        else:
            raise Exception("Can only begin run from SETUP")

    def post_begin_check(self, verbose=False):
        pass

    def post_end_check(self, verbose=False):
        pass

    def post_abort_check(self, verbose=False):
        pass

    def post_pause_check(self, verbose=False):
        pass

    def post_resume_check(self, verbose=False):
        pass

    def post_update_store_check(self, verbose=False):
        pass

    def post_update_check(self, verbose=False):
        pass

    def post_store_check(self, verbose=False):
        pass

    def abort_run(self):
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            self.run_state = "SETUP"
        else:
            raise Exception("Can only abort when RUNNING or PAUSED")

    def get_run_state(self):
        return self.run_state

    def get_run_number(self):
        return self.run_number

    def end_run(self):
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            self.run_state = "SETUP"
        else:
            raise Exception("Can only end when RUNNING or PAUSED")

    def pause_run(self):
        if self.run_state == "RUNNING":
            self.run_state = "PAUSED"
        else:
            raise Exception("Can only pause when RUNNING")

    def resume_run(self):
        if self.run_state == "PAUSED":
            self.run_state = "RUNNING"
        else:
            raise Exception("Can only resume when PAUSED")

    def update_store_run(self):
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run when RUNNING or PAUSED")

    def update_run(self):
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run when RUNNING or PAUSED")

    def store_run(self):
        if self.run_state == "RUNNING" or self.run_state == "PAUSED":
            pass
        else:
            raise Exception("Can only be run when RUNNING or PAUSED")

    def get_period(self):
        return self.period_current

    def get_num_periods(self):
        return self.num_periods

    def set_period(self, period):
        if period <= self.num_periods:
            self.period_current = period
        else:
            raise Exception("Cannot set period as it is higher than the number of periods")


class SimulationAPI(object):

    def __init__(self):
        self.block_dict = dict()
        self.num_periods = 1
        self.run_number = 123456
        self.waitfor = Waitfor()
        self.dae = Dae()

    def log_info_msg(self, *args, **kwargs):
        pass

    def block_exists(self, name):
        # Create an entry for it and return True
        if name not in self.block_dict:
            self.set_block_value(name)
        return True

    def get_blocks(self):
        return self.block_dict.keys()

    def get_block_value(self, name, to_string=False, attempts=3):
        if to_string:
            return str(self.block_dict[name][0])
        return self.block_dict[name][0]

    def get_run_control_settings(self, name):
        rc = dict()
        rc["ENABLE"] = self.block_dict[name][1]
        rc["LOW"] = self.block_dict[name][2]
        rc["HIGH"] = self.block_dict[name][3]
        return rc

    def get_current_block_values(self):
        return self.block_dict

    def set_block_value(self, name, value=None, runcontrol=None, lowlimit=None, highlimit=None, wait=False):
        try:
            # Final value in list is the EPICS record type
            self.block_dict[name] = [value, runcontrol, lowlimit, highlimit, ""]
        except Exception as e:
            _handle_exception(e)

    def set_multiple_blocks(self, names, values):
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
                if name in self.block_dict:
                    self.block_dict[name][0] = value
                else:
                    self.block_dict[name] = [value, False, None, None, None]
        except Exception as e:
            _handle_exception(e)

    def run_pre_post_cmd(self, command, **pars):
        pass

    def get_blocks(self):
        return self.block_dict.keys()


__api = SimulationAPI()


def _handle_exception(e):
    print e


def waveform_to_string():
    pass


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
    try:
        if block:
            # Show only one block
            if __api.block_exists(block):
                output = block + ' = ' + str(__api.get_block_value(block, attempts=1))
                rc = __api.get_run_control_settings(block)
                if rc:
                    output += ' (runcontrol = %s, lowlimit = %s, highlimit = %s)' % (rc["ENABLE"], rc["LOW"],
                                                                                     rc["HIGH"])
                print output
            else:
                raise Exception('No block with the name "%s" exists' % block)
        else:
            # Show all blocks
            _cshow_all()
    except Exception as e:
        _handle_exception(e)


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
    __api.log_info_msg("CSET %s" % (locals(),))
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
    __api.log_info_msg("WAITFOR %s" % (locals(),))
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
    __api.log_info_msg("BEGIN %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("begin_precmd", quiet=quiet)
        __api.dae.begin_run(period, meas_id, meas_type, meas_subid, sample_id, delayed, quiet, paused)
        waitfor_runstate("SETUP", onexit=True)
        __api.dae.post_begin_check(verbose)
        __api.run_pre_post_cmd("begin_postcmd", run_num=__api.dae.get_run_number(), quiet=quiet)
    except Exception as e:
        _handle_exception(e)


def abort(verbose=False):
    """Abort the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("ABORT %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("abort_precmd")
        __api.dae.abort_run()
        waitfor_runstate("SETUP")
        __api.dae.post_abort_check(verbose)
        __api.run_pre_post_cmd("abort_postcmd")
    except Exception as e:
        _handle_exception(e)


def end(verbose=False):
    """End the current run.

        Args:
            verbose (bool, optional) : show the messages from the DAE
        """
    __api.log_info_msg("END %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("end_precmd")
        __api.dae.end_run()
        waitfor_runstate("SETUP")
        __api.dae.post_end_check(verbose)
        __api.run_pre_post_cmd("end_postcmd")
    except Exception as e:
        _handle_exception(e)


def pause(verbose=False):
    """Pause the current run.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("PAUSE %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("pause_precmd")
        __api.dae.pause_run()
        waitfor_runstate("PAUSED")
        __api.dae.post_pause_check(verbose)
        __api.run_pre_post_cmd("pause_postcmd")
    except Exception as e:
        _handle_exception(e)


def resume(verbose=False):
    """Resume the current run after it has been paused.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("RESUME %s" % (locals(),))
    try:
        __api.run_pre_post_cmd("resume_precmd")
        __api.dae.resume_run()
        waitfor_runstate("PAUSED", onexit=True)
        __api.dae.post_resume_check(verbose)
        __api.run_pre_post_cmd("resume_postcmd")
    except Exception as e:
        _handle_exception(e)


def updatestore(verbose=False):
    """Performs an update and a store operation in a combined operation.
    This is more efficient than doing the commands separately.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("SAVING %s" % (locals(),))
    try:
        __api.dae.update_store_run()
        waitfor_runstate("SAVING", onexit=True)
        __api.dae.post_update_store_check(verbose)
    except Exception as e:
        _handle_exception(e)


def update(pause_run=True, verbose=False):
    """Data is loaded from the DAE into the computer memory, but is not written to disk.

    Args:
        pause_run (bool, optional) : whether to pause data collection first [optional]
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("UPDATE %s" % (locals(),))
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


def store(verbose=False):
    """Data loaded into memory by a previous update command is now written to disk.

    Args:
        verbose (bool, optional) : show the messages from the DAE
    """
    __api.log_info_msg("STORING %s" % (locals(),))
    try:
        __api.dae.store_run()
        waitfor_runstate("STORING", onexit=True)
        __api.dae.post_store_check(verbose)
    except Exception as e:
        _handle_exception(e)


def get_runstate():
    """Get the current status of the instrument as a string.

    Note: this value can take a few seconds to update after a change of state.

    Returns:
        string : the current run state
    """
    try:
        return __api.dae.get_run_state()
    except Exception as e:
        _handle_exception(e)


def get_period():
    """Gets the current period number.

    Returns:
        int : the current period
    """
    try:
        return __api.dae.get_period()
    except Exception as e:
        _handle_exception(e)


def get_number_periods():
    """Get the number of software periods.

    Returns:
        int : the number of periods
    """
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
    print "set_period is deprecated - use change_period"
    change_period(period)


def change_period(period):
    """Changes the current period number.

    Args:
        period (int) : the period to switch to
    """
    try:
        __api.dae.set_period(period)
    except Exception as e:
        _handle_exception(e)


def get_blocks():
    """Get the names of the blocks.

    Returns:
        list : the blocknames
    """
    try:
        return __api.get_blocks()
    except Exception as e:
        _handle_exception(e)



def cget(block):
    """Gets the useful values associated with a block.

    Args:
        block (string) : the name of the block

    Returns
        dict : details about about the block
    """
    try:
        if block not in __api.block_dict.keys():
            raise Exception('No block with the name "%s" exists' % block)

        ans = dict()
        ans['name'] = block
        ans['value'] = __api.block_dict[block][0]

        rc = __api.block_dict[block][1:]

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
    __api.log_info_msg("WAITFOR_RUNSTATE %s" % (locals(),))
    try:
        # Check that wait_for object exists
        if __api.waitfor is None:
            raise Exception("Cannot execute waitfor - try calling set_instrument first")
        __api.waitfor.wait_for_runstate(state, maxwaitsecs, onexit)
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
        return __api.run_number
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
