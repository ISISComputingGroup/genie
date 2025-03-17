from __future__ import absolute_import, print_function

import datetime
import importlib
import importlib.util
import os
import re
import sys
import types
from builtins import FileNotFoundError, str
from io import open
from typing import Any, Callable, TypedDict

import numpy.typing as npt

from genie_python.genie_api_setup import __api as _genie_api

os.environ["FROM_IBEX"] = str(False)

# for user import this functionality so they can do g.adv and g.sim
import genie_python.genie_advanced as adv  # noqa F401
import genie_python.genie_alerts as alerts  # noqa F401
import genie_python.genie_simulate as sim  # noqa F401
import genie_python.genie_toggle_settings as toggle  # noqa F401

# Import required for g.my_pv_prefix
from genie_python.genie_api_setup import (  # noqa E402
    get_user_script_dir,
    helparglist,
    log_command_and_handle_exception,
    my_pv_prefix,  # noqa F401
    set_user_script_dir,
    usercommand,
)
from genie_python.genie_script_checker import ScriptChecker  # noqa E402
from genie_python.genie_toggle_settings import ToggleSettings  # noqa E402
from genie_python.utilities import (  # noqa E402
    EnvironmentDetails,
    check_lowlimit_against_highlimit,
    get_correct_filepath_existing,
    get_correct_path,
)
from genie_python.version import VERSION  # noqa E402

PVBaseValue = bool | int | float | str
PVValue = PVBaseValue | list[PVBaseValue] | npt.NDArray | None

print("\ngenie_python version " + VERSION)

MIN_SUPPORTED_PYTHON_VERSION = (3, 11, 0)
MAX_SUPPORTED_PYTHON_VERSION = (3, 12, 999)

if not (MIN_SUPPORTED_PYTHON_VERSION <= sys.version_info[0:3] <= MAX_SUPPORTED_PYTHON_VERSION):
    message = (
        "WARNING: genie_python only supports "
        "python versions {0[0]}.{0[1]}.{0[2]} to {1[0]}.{1[1]}.{1[2]}, you are running {2}".format(
            MIN_SUPPORTED_PYTHON_VERSION, MAX_SUPPORTED_PYTHON_VERSION, sys.version
        )
    )
    print(message, file=sys.stderr)


@log_command_and_handle_exception
def set_instrument(pv_prefix: str, import_instrument_init: bool = True) -> None:
    """
    Sets the instrument this session is communicating with.
    Used for remote access - do not delete.

    Args:
        pv_prefix (string): the PV prefix
        import_instrument_init (bool): if True import the instrument init
        from the config area; otherwise don't
    """
    globs = _get_correct_globals()
    _genie_api.set_instrument(pv_prefix, globs, import_instrument_init)


@log_command_and_handle_exception
def reload_current_config() -> None:
    """
    Reload the current configuration.
    """
    _genie_api.reload_current_config()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_blocks() -> list[str]:
    """
    Get the names of the blocks.

    Returns:
        list: the blocknames
    """
    return _genie_api.get_block_names()


@usercommand
@helparglist("block")
@log_command_and_handle_exception
def get_block_units(block_name: str) -> str | dict | None:
    """
    Get the physical measurement units associated with a block name.

    Args:
        block_name: name of the block

    Returns
        string: units of the block
    """
    return _genie_api.get_block_units(block_name)


@usercommand
@helparglist("...")
@log_command_and_handle_exception
def cset(
    *args: PVValue,
    runcontrol: bool | None = None,
    lowlimit: float | None = None,
    highlimit: float | None = None,
    wait: bool | None = None,
    verbose: bool | None = None,
    **kwargs: PVValue,
) -> None:
    """
    Sets the setpoint and runcontrol settings for blocks.

    Args:
        runcontrol (bool, optional): whether to set runcontrol for this block
        wait (bool, optional): pause execution until setpoint is reached (one block only)
        lowlimit (float, optional): the lower limit for runcontrol or waiting
        highlimit (float, optional): the upper limit for runcontrol or waiting
        verbose (bool, optional): report what the new block state is as a result of the command

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
    # Block names contain alpha-numeric and underscores only

    # See if single block name was entered, i.e. cset("block1", runcontrol=True)
    if len(args) > 0:
        if len(args) > 2:
            raise Exception(
                "Too many arguments, please type: help(g.cset) for more information on the syntax"
            )
        blocks = [args[0]]
        values = [args[1]] if len(args) == 2 else [None]
    elif len(kwargs) > 0:
        # Check for specifying blocks via the cset(block=value) syntax
        blocks, values = zip(*kwargs.items())
    else:
        raise Exception(
            "Incorrect syntax, please type: help(g.cset) for more information on the syntax"
        )

    for block in blocks:
        if not _genie_api.block_exists(block):
            raise Exception('No block with the name "{}" exists'.format(block))

    if wait and runcontrol is not None:
        raise Exception("Cannot enable or disable runcontrol at the same time as setting a wait")
    if wait and values[0] is None:
        raise Exception("Cannot wait as no setpoint specified. Please type: help(g.cset) for help")

    # Warn if highlimit and lowlimit are round the incorrect way
    check_lowlimit_against_highlimit(lowlimit, highlimit)

    if len(blocks) > 1:
        # Setting multiple blocks, so other settings not allowed
        if not all(argument is None for argument in [runcontrol, lowlimit, highlimit, wait]):
            raise Exception("Runcontrol and wait can only be changed for one block at a time")

    for block, value in list(zip(blocks, values)):
        # If there are multiple blocks then runcontrol etc.
        # should be None anyway so pass them through

        _genie_api.set_block_value(block, value, runcontrol, lowlimit, highlimit, wait)
        _warn_if_block_alarm(block)

    # Display what the new block state is as a result of the command if
    # cset verbosity is toggled on, or the command
    # was specifically called with 'verbose=True'.
    # If default verbosity is True, but the command was specifically
    # called with no verbose, do not display new state.
    if verbose is not False and (verbose or ToggleSettings.cset_verbose):
        for block, value in list(zip(blocks, values)):
            waitfor_block(block=block, value=value, maxwait=5)
            print("Result: ", end="")
            cshow(block)


class _CgetReturn(TypedDict):
    name: str
    value: Any
    unit: str
    connected: bool
    runcontrol: bool
    lowlimit: Any
    highlimit: Any
    alarm: str


@usercommand
@helparglist("block")
@log_command_and_handle_exception
def cget(block: str) -> _CgetReturn:
    """
    Gets the useful values associated with a block.

    The value will be None if the block is not "connected".

    Args:
        block (string): the name of the block

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
    ans = _genie_api.get_block_data(block)
    if ans["alarm"] != "NO_ALARM":
        _log_alarmed_block(block, ans["alarm"])
    return ans


def _log_alarmed_block(block_name: str, alarm_state: str) -> None:
    _genie_api.logger.log_info_msg("BLOCK {} IN {} ALARM".format(block_name, alarm_state))
    print("Block {} is in alarm: {}".format(block_name, alarm_state), file=sys.stdout)


def _warn_if_block_alarm(block: object) -> None:
    """
    Checks whether a block is in an alarmed state and warn user (inc log)

    Args:
        block (object): The block to be checked
    """
    minor, major, invalid = check_alarms(block)
    alarms = {"MINOR": minor, "MAJOR": major, "INVALID": invalid}
    for alarm_type, alarm in alarms.items():
        if alarm:
            _log_alarmed_block(alarm[0], alarm_type)


def _print_from_cget(block_details: dict[str, str]) -> None:
    """
    Prints the values obtained through cget into a
    human readable format, used for cshow.

    Args:
        block_details (dict): dict containing information on the block
        (see return of cget)
    """
    format_string = (
        "{name} = {value} (runcontrol = {runcontrol}, "
        "lowlimit = {lowlimit}, highlimit = {highlimit}, "
        "alarm = {alarm})"
    )
    if not block_details["connected"]:
        block_details["value"] = "*** disconnected ***"
    print(format_string.format(**block_details))


@log_command_and_handle_exception
def cshow(block: str | None = None) -> None:
    """
    Show the current settings for one block or for all blocks.

    Args:
        block (string, optional): the name of the block

    Examples:
        Showing all block values:

        >>> cshow()

        Showing values for one block only (name must be quoted):

        >>> cshow("block1")
    """
    blocks_to_get = [block] if block is not None else _genie_api.get_block_names()
    for block in blocks_to_get:
        _print_from_cget(_genie_api.get_block_data(block, True))


@log_command_and_handle_exception
def waitfor(
    block: str | None = None,
    value: float | None = None,
    lowlimit: float | None = None,
    highlimit: float | None = None,
    maxwait: float | None = None,
    wait_all: bool = False,
    seconds: float | None = None,
    minutes: float | None = None,
    hours: float | None = None,
    time: str | None = None,
    frames: int | None = None,
    raw_frames: int | None = None,
    uamps: float | None = None,
    mevents: float | None = None,
    early_exit: Callable[[], bool] = lambda: False,
    quiet: bool = False,
    **pars: bool | int | float | str | Callable[[None], bool] | None,
) -> None:
    """
    Interrupts execution until certain conditions are met.

    Args:
        block (string, optional): the name of the block to wait for
        value (float, optional): the block value to wait for
        lowlimit (float, optional): wait for the block to be >= this value (numeric only)
        highlimit (float, optional): wait for the block to be <= this value (numeric only)
        maxwait (float, optional): wait no longer that the specified number of seconds
        wait_all (bool, optional): wait for all conditions to be met
            (e.g. a number of frames and an amount of uamps)
        seconds (float, optional): wait for a specified number of seconds
        minutes (float, optional): wait for a specified number of minutes
        hours (float, optional): wait for a specified number of hours
        time (string, optional): a quicker way of setting hours, minutes and seconds
            (must be of format "HH:MM:SS")
        frames (int, optional): wait for a total number of good frames to be collected
        raw_frames (int, optional): wait for a total number of raw frames to be collected
        uamps (float, optional): wait for a total number of uamps to be received
        mevents (float, optional): wait for a total number of millions of events to be collected
        early_exit (lambda, optional): stop waiting if the function evaluates to True
        quiet (bool, optional): suppress normal output messages to the console

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

        Wait for either the block to reach a value or a condition to be met:

        >>> waitfor(myblock=123, early_exit=lambda:
            some_function(cget("another_block")["value"]) > 123)
    """
    if block is None:
        # Search through the params to see if there is a block there
        blks = _genie_api.get_block_names()
        for k in pars:
            if k in blks:
                if block is not None:
                    raise Exception("Can set waitfor for only one block at a time")
                block = k
                value = pars[k]
            else:
                raise ValueError("Block named '{}' did not exist.".format(k))
    # Check that wait_for object exists
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor - try calling set_instrument first")
    # Warn if highlimit and lowlimit are round correct way
    check_lowlimit_against_highlimit(lowlimit, highlimit)
    # Start_waiting checks the block exists
    _genie_api.waitfor.start_waiting(
        block,
        value,
        lowlimit,
        highlimit,
        maxwait,
        wait_all,
        seconds,
        minutes,
        hours,
        time,
        frames,
        raw_frames,
        uamps,
        mevents,
        early_exit,
        quiet,
    )


@usercommand
@helparglist("block[, value][, lowlimit][, highlimit][, maxwait]")
@log_command_and_handle_exception
def waitfor_block(
    block: str,
    value: bool | int | float | str | None = None,
    lowlimit: float | None = None,
    highlimit: float | None = None,
    maxwait: float | None = None,
    early_exit: Callable[[], bool] = lambda: False,
    quiet: bool = False,
) -> None:
    """
    Interrupts execution until block reaches specific value

    Args:
        block: the name of the block to wait for
        value: the target block value
        lowlimit: waits for the block to be >= this value (numeric only)
        highlimit: waits for the block to be <= this value (numeric only)
        maxwait: wait no longer that the specified number of seconds
        early_exit: stop waiting if the exception evaluates to True
        quiet (bool, optional): suppress normal output messages to the console

    Examples:

        >>> waitfor_block("myblock", value=123)
        >>> waitfor_block("myblock", value=True, maxwait=15)
        >>> waitfor_block("myblock", lowlimit=100, highlimit=110)
        >>> waitfor_block("myblock", highlimit=1.0, maxwait=60)
        >>> waitfor_block(
        ...     "myblock", value=123, early_exit=lambda: cget("myblock_limit_reached")["value"] != 0
        ... )
    """
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor_block - try calling set_instrument first")
    # Warn if highlimit and lowlimit are round correct way
    check_lowlimit_against_highlimit(lowlimit, highlimit)
    _genie_api.waitfor.start_waiting(
        block=block,
        value=value,
        lowlimit=lowlimit,
        highlimit=highlimit,
        maxwait=maxwait,
        early_exit=early_exit,
        quiet=quiet,
    )


@usercommand
@helparglist("[seconds][, minutes][, hours][, time]")
@log_command_and_handle_exception
def waitfor_time(
    seconds: float | None = None,
    minutes: float | None = None,
    hours: float | None = None,
    time: str | None = None,
    quiet: bool = False,
) -> None:
    """
    Interrupts execution for a specified amount of time

    Args:
        seconds (float, optional): wait for a specified number of seconds
        minutes (float, optional): wait for a specified number of minutes
        hours (float, optional): wait for a specified number of hours
        time (string, optional): a quicker way of setting hours,
            minutes and seconds (must be of format "HH:MM:SS")
        quiet (bool, optional): suppress normal output messages to the console

    Examples:

        >>> waitfor_time(seconds=10)
        >>> waitfor_time(hours=1, minutes=30, seconds=15)
        >>> waitfor_time(time="1:30:15")
    """
    if all(t is None for t in (seconds, minutes, hours, time)):
        raise TypeError(
            "Cannot execute waitfor_time - need to set at least one parameter. "
            "Type help(waitfor_time) "
            "to see guidelines"
        )
    if any(t is not None and t < 0 for t in (seconds, minutes, hours)):
        raise ValueError("Cannot execute waitfor_time - Time parameters cannot be negative")
    if _genie_api.waitfor is None:
        raise TypeError("Cannot execute waitfor_time - try calling set_instrument first")
    _genie_api.waitfor.start_waiting(
        seconds=seconds, minutes=minutes, hours=hours, time=time, quiet=quiet
    )


@usercommand
@helparglist("frames")
@log_command_and_handle_exception
def waitfor_frames(frames: int, quiet: bool = False) -> None:
    """
    Interrupts execution to wait for number of total good frames to reach parameter value

    Args:
        frames (int): the number of frames to wait for
        quiet (bool, optional): suppress normal output messages to the console

    Example:

        >>> waitfor_frames(4000)
    """
    if frames is None:
        raise TypeError(
            "Cannot execute waitfor_frames - need to set frames parameter. Type help(waitfor_frames"
        )
    if frames < 0:
        raise ValueError("Cannot execute waitfor_frames - frames parameter cannot be negative")
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor_frames - try calling set_instrument first")
    _genie_api.waitfor.start_waiting(frames=frames, quiet=quiet)


@usercommand
@helparglist("raw_frames")
@log_command_and_handle_exception
def waitfor_raw_frames(raw_frames: int, quiet: bool = False) -> None:
    """
    Interrupts execution to wait for number of total raw frames to reach parameter value

    Args:
        raw frames (int): the number of raw frames to wait for
        quiet (bool, optional): suppress normal output messages to the console

    Example:

        >>> waitfor_raw_frames(4000)
    """
    if raw_frames is None:
        raise TypeError(
            "Cannot execute waitfor_raw_frames - need to set raw_frames parameter. "
            "Type help(waitfor_raw_frames"
        )
    if raw_frames < 0:
        raise ValueError(
            "Cannot execute waitfor_raw_frames - raw_frames parameter cannot be negative"
        )
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor_raw_frames - try calling set_instrument first")
    _genie_api.waitfor.start_waiting(raw_frames=raw_frames, quiet=quiet)


@usercommand
@helparglist("uamps")
@log_command_and_handle_exception
def waitfor_uamps(uamps: float, quiet: bool = False) -> None:
    """
    Interrupts execution to wait for a specific total charge

    Args:
        uamps: the charge to wait for
        quiet (bool, optional): suppress normal output messages to the console

    Example:

        >>> waitfor_uamps(115.5)
    """
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor_uamps - try calling set_instrument first")
    _genie_api.waitfor.start_waiting(uamps=uamps, quiet=quiet)


@usercommand
@helparglist("mevents")
@log_command_and_handle_exception
def waitfor_mevents(mevents: float, quiet: bool = False) -> None:
    """
    Interrupts execution to wait for number of millions of events to reach parameter value

    Args:
        mevents (float): the number of millions of events to wait for
        quiet (bool, optional): suppress normal output messages to the console

    Example:

        >>> waitfor_mevents(0.0004)
    """
    if mevents is None:
        raise TypeError(
            "Cannot execute waitfor_mevents - need to set mevents parameter. "
            "Type help(waitfor_mevents)"
        )
    if mevents < 0:
        raise ValueError("Cannot execute waitfor_mevents - mevents parameter cannot be negative")
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor_mevents - try calling set_instrument first")
    _genie_api.waitfor.start_waiting(mevents=mevents, quiet=quiet)


@usercommand
@helparglist("state[, maxwaitsecs][, onexit]")
@log_command_and_handle_exception
def waitfor_runstate(
    state: str, maxwaitsecs: int = 3600, onexit: bool = False, quiet: bool = False
) -> None:
    """
    Wait for a particular instrument run state.

    Args:
        state (string): the state to wait for (e.g. "paused")
        maxwaitsecs (int, optional): the maximum time to wait for the state before carrying on
        onexit (bool, optional): wait for runstate to change from the specified state
        quiet (bool, optional): suppress normal output messages to the console

    Examples:
        Wait for a run to enter the paused state:

        >>> waitfor_runstate("paused")

        Wait for a run to exit the paused state:

        >>> waitfor_runstate("paused", onexit=True)
    """
    # Check that wait_for object exists
    if _genie_api.waitfor is None:
        raise Exception("Cannot execute waitfor_runstate - try calling set_instrument first")
    _genie_api.waitfor.wait_for_runstate(state, maxwaitsecs, onexit, quiet)


@usercommand
@helparglist("[block, ...][, start_timeout][, move_timeout]")
@log_command_and_handle_exception
def waitfor_move(*blocks: str | None, **kwargs: int | None) -> None:
    """
    Wait for all motion or specific motion to complete.

    If block names are supplied then it will only wait for those to stop moving.
    Otherwise, it will wait for all motion
    to stop.

    Args:
        blocks (string, multiple, optional): the names of specific blocks to wait for
        start_timeout (int, optional): the number of seconds to wait for the
            movement to begin (default = 2 seconds)
        move_timeout (int, optional): the maximum number of seconds to wait for motion to stop

    Examples:
        Wait for all motors to stop moving:

        >>> waitfor_move()

        Wait for all motors to stop moving with a timeout of 30 seconds:

        >>> waitfor_move(move_timeout=30)

        Wait for only slit1 and slit2 motors to stop moving:

        >>> waitfor_move("slit1", "slit2")
    """
    # Sort out the parameters
    # Standard parameters
    if "start_timeout" in kwargs:
        start_timeout = kwargs["start_timeout"]
    else:
        start_timeout = 2
    if "move_timeout" in kwargs:
        move_timeout = kwargs["move_timeout"]
    else:
        move_timeout = None

    # Check that wait_for_move object exists
    if _genie_api.wait_for_move is None:
        raise Exception("Cannot execute waitfor_move - try calling set_instrument first")

    if len(blocks) > 0:
        # Specified blocks waitfor_move
        move_blocks = list()
        # Check blocks exist
        for b in blocks:
            if _genie_api.block_exists(b):
                move_blocks.append(b)
            else:
                print("Block %s does not exist, so ignoring it" % b)
        _genie_api.wait_for_move.wait_specific(move_blocks, start_timeout, move_timeout)
    else:
        # Standard waitfor_move
        _genie_api.wait_for_move.wait(start_timeout, move_timeout)


@usercommand
@helparglist("name[, to_string][, is_local][, use_numpy]")
@log_command_and_handle_exception
def get_pv(
    name: str, to_string: bool = False, is_local: bool = False, use_numpy: bool = False
) -> Any:
    """
    Get the value for the specified PV.

    Args:
        name (string): the name of the PV to get the value for
        to_string (bool, optional): whether to get the value as a string
        is_local (bool, optional): whether to automatically prepend the
            local inst prefix to the PV name
        use_numpy (bool, optional): True use numpy to return arrays,
            False return a list; None for use the default

    Returns:
        the current PV value
    """
    return _genie_api.get_pv_value(name, to_string, is_local=is_local, use_numpy=use_numpy)


@usercommand
@helparglist("name, value[, wait][, is_local]")
@log_command_and_handle_exception
def set_pv(name: str, value: PVValue, wait: bool = False, is_local: bool = False) -> None:
    """
    Set the value for the specified PV.

    Args:
        name (string): the PV name
        value: the new value to set
        wait (bool, optional): whether to wait until the value
            has been received by the hardware
        is_local (bool, optional): whether to automatically
            prepend the local inst prefix to the PV name
    """
    _genie_api.set_pv_value(name, value, wait, is_local=is_local)


@usercommand
@helparglist("pv_list, [, is_local]")
@log_command_and_handle_exception
def connected_pvs_in_list(pv_list: list[str], is_local: bool = False) -> list[str]:
    """
    Check if the specified PVs are connected.

    Args:
        pv_list (list): the PV names
        is_local (bool, optional): whether to automatically prepend the
            local inst prefix to the PV names

    Returns:
        list: the PV names that are connected
    """
    return _genie_api.connected_pvs_in_list(pv_list, is_local=is_local)


@usercommand
@helparglist("...")
@log_command_and_handle_exception
def begin(
    period: int = 1,
    meas_id: str | None = None,
    meas_type: str = "",
    meas_subid: str = "",
    sample_id: str = "",
    delayed: bool = False,
    quiet: bool = False,
    paused: bool = False,
    verbose: bool = False,
    prepost: bool = True,
) -> None:
    """
    Starts a data collection run.

    Args:
        period (int, optional): the period to begin data collection in
        meas_id (string, optional): the measurement id
        meas_type (string, optional): the type of measurement
        meas_subid (string, optional): the measurement sub-id
        sample_id (string, optional): the sample id
        delayed (bool, optional): puts the period card to into delayed start mode
        quiet (bool, optional): suppress the output to the screen
        paused (bool, optional): begin in the paused state
        verbose (bool, optional): show the messages from the DAE
        prepost (bool, optional): run pre and post commands (default: True)
    Returns:
        Any: return what the begin_postcmd method returns
    """
    # Returns None if we should start the run or the reason why if not
    pre_post_cmd_return = _genie_api.pre_post_cmd_manager.begin_precmd(quiet=quiet, prepost=prepost)
    if pre_post_cmd_return is None:
        _genie_api.dae.begin_run(
            period, meas_id, meas_type, meas_subid, sample_id, delayed, quiet, paused, prepost
        )

        waitfor_runstate("SETUP", onexit=True)

        _genie_api.dae.post_begin_check(verbose)
        _genie_api.pre_post_cmd_manager.begin_postcmd(
            run_num=_genie_api.dae.get_run_number(), quiet=quiet, prepost=prepost
        )
    else:
        print(str(pre_post_cmd_return))


@usercommand
@helparglist("[verbose], [prepost]")
@log_command_and_handle_exception
def abort(verbose: bool = False, prepost: bool = True) -> None:
    """
    Abort the current run.

    Args:
        verbose (bool, optional): show the messages from the DAE
        prepost (bool, optional): run pre and post commands (default: True)
    """
    _genie_api.pre_post_cmd_manager.abort_precmd(prepost=prepost)
    _genie_api.dae.abort_run(prepost)
    _genie_api.dae.post_abort_check(verbose)
    _genie_api.pre_post_cmd_manager.abort_postcmd(prepost=prepost)


@usercommand
@helparglist("[verbose], [quiet], [immediate], [prepost]")
@log_command_and_handle_exception
def end(
    verbose: bool = False, quiet: bool = False, immediate: bool = False, prepost: bool = False
) -> None:
    """
    End the current run.

    Args:
        verbose (bool, optional): show the messages from the DAE
        quiet (bool, optional): suppress the end_precmd output to the screen
        immediate (bool, optional): end immediately, without waiting for
            a period sequence to complete
        prepost (bool, optional): run pre and post commands (default: True)
    """
    _genie_api.pre_post_cmd_manager.end_precmd(quiet=quiet, prepost=prepost)
    _genie_api.dae.end_run(verbose=verbose, quiet=quiet, immediate=immediate, prepost=prepost)
    waitfor_runstate("SETUP")
    _genie_api.dae.post_end_check(verbose)
    _genie_api.pre_post_cmd_manager.end_postcmd(quiet=quiet, prepost=prepost)


@usercommand
@helparglist("[verbose], [immediate], [prepost]")
@log_command_and_handle_exception
def pause(verbose: bool = False, immediate: bool = False, prepost: bool = True) -> None:
    """
    Pause the current run.

    Args:
        verbose (bool, optional): show the messages from the DAE
        immediate (bool, optional): pause immediately,
            without waiting for a period sequence to complete
        prepost (bool, optional): run pre and post commands (default: True)
    """
    _genie_api.pre_post_cmd_manager.pause_precmd(prepost=prepost)
    _genie_api.dae.pause_run(immediate=immediate, prepost=prepost)
    _genie_api.dae.post_pause_check(verbose)
    _genie_api.pre_post_cmd_manager.pause_postcmd(prepost=prepost)


@usercommand
@helparglist("[verbose], [prepost]")
@log_command_and_handle_exception
def resume(verbose: bool = False, prepost: bool = False) -> None:
    """
    Resume the current run after it has been paused.

    Args:
        verbose (bool, optional): show the messages from the DAE
        prepost (bool, optional): run pre and post commands (default: True)
    """
    _genie_api.pre_post_cmd_manager.resume_precmd(prepost=prepost)
    _genie_api.dae.resume_run(prepost)
    _genie_api.dae.post_resume_check(verbose)
    _genie_api.pre_post_cmd_manager.resume_postcmd(prepost=prepost)


@usercommand
@helparglist("[verbose]")
@log_command_and_handle_exception
def recover(verbose: bool = False) -> None:
    """
    Recovers the run if it has been aborted.
    The command should be run before the next run is started.

    Note: the run will be recovered in the paused state.

    Args:
        verbose (bool, optional): show the messages from the DAE
    """
    _genie_api.dae.recover_run()
    waitfor_runstate("SETUP", onexit=True)
    _genie_api.dae.post_recover_check(verbose)


@usercommand
@helparglist("[verbose]")
@log_command_and_handle_exception
def updatestore(verbose: bool = False) -> None:
    """
    Performs an update and a store operation in a combined operation.
    This is more efficient than doing the commands separately.

    Args:
        verbose (bool, optional): show the messages from the DAE
    """
    _genie_api.dae.update_store_run()
    waitfor_runstate("SAVING", onexit=True)
    _genie_api.dae.post_update_store_check(verbose)


@usercommand
@helparglist("[pause_run], [verbose]")
@log_command_and_handle_exception
def update(pause_run: bool = True, verbose: bool = False) -> None:
    """
    Data is loaded from the DAE into the computer memory, but is not written to disk.

    Args:
        pause_run (bool, optional): whether to pause data collection first [optional]
        verbose (bool, optional): show the messages from the DAE
    """
    if pause_run:
        # Pause
        pause(verbose=verbose)

    # Update
    _genie_api.dae.update_run()
    waitfor_runstate("UPDATING", onexit=True)
    _genie_api.dae.post_update_check(verbose)

    if pause_run:
        # Resume
        resume(verbose=verbose)


@usercommand
@helparglist("[verbose]")
@log_command_and_handle_exception
def store(verbose: bool = False) -> None:
    """
    Data loaded into memory by a previous update command is now written to disk.

    Args:
        verbose (bool, optional): show the messages from the DAE
    """
    _genie_api.dae.store_run()
    waitfor_runstate("STORING", onexit=True)
    _genie_api.dae.post_store_check(verbose)


@usercommand
@helparglist("[filename], [verbose]")
@log_command_and_handle_exception
def snapshot_crpt(filename: str = "c:\\Data\\snapshot_crpt.tmp", verbose: bool = False) -> None:
    """
    Create a snapshot of the current data.

    Args:
        filename (string, optional): where to write the data file(s)
        verbose (bool, optional): show the messages from the DAE

    Examples:
        Snapshot to a file called my_snapshot:

        >>> snapshot_crpt("c:\\Data\\my_snapshot")
    """
    name = get_correct_path(filename)
    _genie_api.dae.snapshot_crpt(name)
    waitfor_runstate("STORING", onexit=True)
    _genie_api.dae.post_snapshot_check(verbose)


@usercommand
@helparglist("[period]")
@log_command_and_handle_exception
def get_uamps(period: bool = False) -> float:
    """
    Get the current number of micro-amp hours.

    Args:
        period (bool, optional): whether to return the value for the current period only

    Returns:
        float: the number of uamps
    """
    return _genie_api.dae.get_uamps(period)


@usercommand
@helparglist("[period]")
@log_command_and_handle_exception
def get_frames(period: bool = False) -> int:
    """
    Gets the current number of good frames.

    Args:
        period (bool, optional): whether to return the value for the current period only

    Returns:
        int: the number of frames
    """
    return _genie_api.dae.get_good_frames(period)


@usercommand
@helparglist("[period]")
@log_command_and_handle_exception
def get_raw_frames(period: bool = False) -> int:
    """
    Gets the current number of raw frames.

    Args:
        period (bool, optional): whether to return the value for the current period only

    Returns:
        int: the number of raw frames
    """
    return _genie_api.dae.get_raw_frames(period)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_runstate() -> str:
    """
    Get the current status of the instrument as a string.

    Note: this value can take a few seconds to update after a change of state.

    Returns:
        string: the current run state
    """
    return _genie_api.dae.get_run_state()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_time_since_begin(get_timedelta: bool = False) -> float | datetime.timedelta:
    """
    Gets the time since start of the current run in seconds or in datetime

    Args:
        get_timedelta (bool): If true return the value as a datetime object,
            otherwise return seconds (defaults to false)

    Returns
        integer: the time since start in seconds if get_datetime is False,
            or timedelta, the time since begin as a datetime.timedelta object
            (Year-Month-Day  Hour:Minute:Second) if get_datetime is True
    """

    return _genie_api.dae.get_time_since_begin(get_timedelta)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_events() -> int:
    """
    Gets the total events for all the detectors.

    Returns:
        int: the number of events
    """
    return _genie_api.dae.get_events()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_mevents() -> float:
    """
    Gets the total millions of events for all the detectors.

    Returns:
        float: the number of millions of events
    """
    return _genie_api.dae.get_mevents()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_period() -> int:
    """
    Gets the current period number.

    Returns:
        int: the current period
    """
    return _genie_api.dae.get_period()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_number_periods() -> int:
    """
    Get the number of software periods.

    Returns:
        int: the number of periods
    """
    return _genie_api.dae.get_num_periods()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_number_timechannels() -> int:
    """
    Get the number of time channels. This is the number of bins used
    to map the time region of interest, it does not include the
    special diagnostic "bin zero" in this count but this fact is not
    normally of interest to most users.

    Returns:
        int: the number of time channels
    """
    return _genie_api.dae.get_num_timechannels()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_number_spectra() -> int:
    """
    Get the number of spectra. The diagnostic spectrum zero
    is not included in the count, so valid spectrum numbers
    are 0 to get_number_spectra()

    Returns:
        int: the number of spectra
    """
    return _genie_api.dae.get_num_spectra()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_spectrum_integrals(with_spec_zero: bool = True) -> npt.NDArray:
    """
    Get the event mode spectrum integrals as numpy ND array.

    Args:
        with_spec_zero (bool, optional):  Include or exclude diagnostic spectrum 0
            if you have 10 spectra and include spectrum zero, your array will be
            of size 11 and spectrum 5 will be at array[5]. If you exclude spectrum zero
            then spectrum 5 would be at array[4]

    Returns:
        numpy int array: spectrum integrals numpy ND array
            this is of dimensions [periods, spectra]
    """
    data = _genie_api.dae.get_spec_integrals()
    nper = get_number_periods()
    nsp = get_number_spectra()
    # original array is nsp + 1 as has spectrum 0
    data_reshaped = data.reshape((nper, nsp + 1))
    return data_reshaped if with_spec_zero else data_reshaped[:, 1:]


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_spectrum_data(with_spec_zero: bool = True) -> npt.NDArray:
    """
    Get the event mode spectrum data as numpy ND array.

    Args:
        with_spec_zero (bool, optional):  Include or exclude diagnostic spectrum 0
            if you have 10 spectra and include spectrum zero, you array will be
            of size 11 and spectrum 5 will be at array[5]. If you exclude spectrum zero
            then spectrum 5 would be at array[4]

    Returns:
        numpy int array: spectrum data ND array
            this is of dimensions [periods, spectra, time_bins]
    """

    return adv.get_spectrum_data(with_spec_zero=with_spec_zero)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_runnumber() -> str:
    """
    Get the current run-number.

    Returns:
        string: the run-number
    """
    return _genie_api.dae.get_run_number()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_totalcounts() -> int:
    """
    Get the total counts for the current run.

    Returns:
        int: the total counts
    """
    return _genie_api.dae.get_total_counts()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_title() -> str:
    """
    Returns the current title.

    Returns:
        string: the title
    """
    return _genie_api.dae.get_title()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_display_title() -> bool:
    """
    Returns the current display title status.

    Returns:
        boolean: the display title status
    """
    return _genie_api.dae.get_display_title()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_rb() -> str:
    """
    Returns the current RB number.

    Returns:
        string: the RB number
    """
    return _genie_api.dae.get_rb_number()


class _GetdashboardReturn(TypedDict):
    status: str
    run_number: str
    rb_number: str
    user: str
    title: str
    display_title: str
    run_time: int
    good_frames_total: int
    good_frames_period: int
    raw_frames_total: int
    raw_frames_period: int
    beam_current: float
    total_current: float
    spectra: int
    periods: int
    time_channels: int
    monitor_spectrum: int
    monitor_from: float
    monitor_to: float
    monitor_counts: int


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_dashboard() -> _GetdashboardReturn:
    """
    Get the current experiment values.

    Returns:
        dict: the experiment values
    """
    data = dict()
    data["status"] = _genie_api.dae.get_run_state()
    data["run_number"] = _genie_api.dae.get_run_number()
    data["rb_number"] = _genie_api.dae.get_rb_number()
    data["user"] = _genie_api.dae.get_users()
    data["title"] = _genie_api.dae.get_title()
    data["display_title"] = _genie_api.dae.get_display_title()
    data["run_time"] = _genie_api.dae.get_run_duration()
    data["good_frames_total"] = _genie_api.dae.get_good_frames()
    data["good_frames_period"] = _genie_api.dae.get_good_frames(True)
    data["raw_frames_total"] = _genie_api.dae.get_raw_frames()
    data["raw_frames_period"] = _genie_api.dae.get_raw_frames(True)
    data["beam_current"] = _genie_api.dae.get_beam_current()
    data["total_current"] = _genie_api.dae.get_total_uamps()
    data["spectra"] = _genie_api.dae.get_num_spectra()
    # data["dae_memory_used"] = genie_api.dae.get_memory_used()
    # Not implemented in EPICS system
    data["periods"] = _genie_api.dae.get_num_periods()
    data["time_channels"] = _genie_api.dae.get_num_timechannels()
    data["monitor_spectrum"] = _genie_api.dae.get_monitor_spectrum()
    data["monitor_from"] = _genie_api.dae.get_monitor_from()
    data["monitor_to"] = _genie_api.dae.get_monitor_to()
    data["monitor_counts"] = _genie_api.dae.get_monitor_counts()
    return data


def _get_correct_globals() -> dict[types.FrameType, int]:
    """
    This is a hack to find the frame in which to add the script function(s).

    The frame we want is the outermost one that contains a reference to cshow().
    """
    import inspect

    globs = dict()

    for i in inspect.stack():
        if "cshow" in i[0].f_globals:
            globs = i[0].f_globals
    return globs


def load_script(name: str, check_script: bool = True, warnings_as_error: bool = False) -> None:
    """
    Loads a user script.

    Args:
        name (string): the name of the file to load. If this is not a
            full path the file is assumed to be in C:\\scripts
        check_script: When True run the script checker on the script;
            False otherwise (default True)
        warnings_as_error: When true throw an exception on a warning;
            False otherwise (default False)
    """

    globs = _get_correct_globals()

    _genie_api.logger.log_info_msg("Trying to resolve full filename for %s" % name)

    try:
        try:
            full_name = get_correct_filepath_existing(name)
        except Exception:
            # Try with default script directory prepended

            full_name = get_correct_filepath_existing(os.path.join(get_user_script_dir(), name))
    except Exception:
        raise Exception("Script file was not found (%s)" % get_correct_path(name))

    _genie_api.logger.log_info_msg("Trying to load script from: %s" % full_name)

    directory, filename = os.path.split(os.path.abspath(full_name))

    # Add the directory to the path in case there are relative imports
    if directory not in sys.path:
        sys.path.append(directory)

    try:
        # Now check the script details with a linter
        if check_script:
            instrument_full_name = _genie_api.get_instrument_full_name()
            sc = ScriptChecker()
            errs = sc.check_script(
                full_name, instrument_full_name, warnings_as_error=warnings_as_error
            )
            if len(errs) > 0:
                combined = "script not loaded as errors found in script: "
                for e in errs:
                    combined += "\n\t" + e
                raise Exception(combined)

        mod = __load_module(filename[0:-3], directory)
        # Safe to load
        # Read the file to get the name of the functions
        funcs = []
        file_path = os.path.join(directory, filename)
        with open(file_path) as f:
            for line in f.readlines():
                m = re.match(r"^def\s+(.+)\(", line)
                if m is not None:
                    funcs.append(m.group(1))

        scripts = []
        for att in dir(mod):
            if isinstance(mod.__dict__.get(att), types.FunctionType):
                # Check function comes from script file not an import
                if att in funcs:
                    scripts.append(att)

        if len(scripts) > 0:
            # This is where the script file is actually loaded
            with open(file_path) as f:
                file_contents = f.read()

            # dont_inherit=True so that __future__
            # statements in this file are not propagated to user scripts
            code = compile(file_contents, file_path, "exec", dont_inherit=True)
            exec(code, globs)

            msg = "Loaded the following script(s): "
            for script in scripts:
                msg += script + ", "
            print(msg[0:-2])
            print("From: %s" % file_path)

            print(
                "File last modified: %s"
                % datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        else:
            raise Exception(
                "No scripts found in {} - please ensure all your code is"
                " contained within functions.".format(file_path)
            )
    except Exception as e:
        if directory in sys.path:
            sys.path.remove(directory)
        raise


def __load_module(name: str, directory: str) -> types.ModuleType:
    """
    This will reload the module if it has already been loaded.
    """
    spec = importlib.util.find_spec(name, directory)
    if spec is None:
        raise ValueError(f"Cannot find spec for module {name} in {directory}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader = spec.loader
    if loader is None:
        raise ValueError("Module spec has no loader")
    loader.exec_module(module)
    return module


@log_command_and_handle_exception
def get_script_dir() -> str:
    """
    Get the current script directory.

    Returns:
        string: the directory
    """
    return get_user_script_dir()


@log_command_and_handle_exception
def change_script_dir(*directory: str) -> None:
    """
    Set the directory for loading user scripts from.

    Args:
        directory (string|List(string)): the directory to load user scripts from,
            either as a single entry or as multiple arguments
    Example:
        g.change_script_dir(r"c/scrips/mydir")
        g.change_script_dir(r"c/scrips", "mydir")


    """
    set_user_script_dir(*directory)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def change_start() -> None:
    """
    Start a change operation.

    The operation is finished when change_finish is called.

    Between these two calls a sequence of other change commands can be called.
    For example: change_tables, change_tcb etc.
    """
    _genie_api.dae.change_start()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def change_finish() -> None:
    """
    End a change operation.

    The operation is begun when change_start is called.

    Between these two calls a sequence of other change commands can be called.
    For example: change_tables, change_tcb etc.
    """
    _genie_api.dae.change_finish()


@usercommand
@helparglist("spec, low, high")
@log_command_and_handle_exception
def change_monitor(spec: int, low: float, high: float) -> None:
    """
    Change the monitor to a specified spectrum and range.

    Args:
        spec (int): the spectrum number
        low (float): the low end of the integral
        high (float): the high end of the integral
    """
    _genie_api.dae.change_monitor(spec, low, high)


@usercommand
@helparglist("[wiring], [detector], [spectra]")
@log_command_and_handle_exception
def change_tables(
    wiring: str | None = None, detector: str | None = None, spectra: str | None = None
) -> None:
    """
    Load the wiring, detector and/or spectra tables.
    Checks that the file paths are valid, throws exception if not.
    Args:
        wiring (string, optional): the filename of the wiring table file
        detector (string, optional): the filename of the detector table file
        spectra (string, optional): the filename of the spectra table file
    """

    def get_table_file(path: str) -> str:
        """Assume the path is a correct path, if not try it relative to tables directory"""
        try:
            return get_correct_filepath_existing(path)
        except Exception:
            env_details = EnvironmentDetails()
            tables_dir = os.path.join(env_details.get_settings_directory(), "tables")
            return get_correct_filepath_existing(os.path.join(tables_dir, path))

    errors = []
    if wiring is not None:
        try:
            wiring = get_table_file(wiring)
        except Exception:
            errors.append(
                "Could not find wiring table. Did you type the file name correctly? %s" % wiring
            )
    if spectra is not None:
        try:
            spectra = get_table_file(spectra)
        except Exception:
            errors.append(
                "Could not find spectra table. Did you type the file name correctly? %s" % spectra
            )
    if detector is not None:
        try:
            detector = get_table_file(detector)
        except Exception:
            errors.append(
                "Could not find detector table. Did you type the file name correctly? %s" % detector
            )

    if errors:
        raise FileNotFoundError(" ".join(errors))
    elif not all(path is None for path in (wiring, detector, spectra)):
        _genie_api.dae.change_tables(wiring, detector, spectra)
    else:
        raise ValueError("No file paths were provided.")


@usercommand
@helparglist("source")
@log_command_and_handle_exception
def change_sync(source: str) -> None:
    """
    Change the source the DAE using for synchronisation.

    Args:
        source (string): the source to use (
         'isis',
         'internal',
         'smp',
         'muon cerenkov',
         'muon ms',
         'isis (first ts1)'
    )
    """
    _genie_api.dae.change_sync(source)


@usercommand
@helparglist("[tcbfile], [default]")
@log_command_and_handle_exception
def change_tcb_file(tcbfile: str | None = None, default: bool = False) -> None:
    """
    Change the time channel boundaries.

    Args:
        tcbfile (string, optional): the file to load
        default (bool, optional): load the default file
    """
    _genie_api.dae.change_tcb_file(tcbfile, default)


@usercommand
@helparglist("[low], [high], [step], [trange], [log], [regime]")
@log_command_and_handle_exception
def change_tcb(
    low: float | None = None,
    high: float | None = None,
    step: float | None = None,
    trange: int = 1,
    log: bool = False,
    regime: int = 1,
) -> None:
    """
    Change the time channel boundaries.
    If None is specified for low, high or step then the values are left unchanged.

    Args
        low (float, optional): the lower limit. Default is no change from the current value.
        high (float, optional): the upper limit. Default is no change from the current value.
        step (float,optional): the step size. Default is no change from the current value.
        trange (int, optional): the time range (1 to 5). Default is 1.
        log (bool, optional): whether to use LOG binning. Default is no.
        regime (int, optional): the time regime to set (1 to 6). Default is 1.

    Examples:
        Changes the from, to and step of the 1st range to 0, 10 and 5 respectively.

        >>> change_tcb(0, 10, 5)

        Changes the step size of the 2nd range to 2, leaving other parameters unchanged.

        >>> change_tcb(step=2, trange=2)
    """
    _genie_api.dae.change_tcb(low, high, step, trange, log, regime)


@usercommand
@helparglist("trange, [regime]")
@log_command_and_handle_exception
def get_tcb_settings(trange: int, regime: int = 1) -> dict[str, int]:
    """
    Gets a dictionary of the time channel settings.

    Args:
        trange (int): the time range to read (1 to 5)
        regime (int, optional): the regime to read (1 to 6). Default is 1.

    Returns:
        dict: the low, high and step for the supplied range and regime

    Examples:
        Get the step size for the 2nd range in the 3rd regime:

        >>> get_tcb_settings(2, 3)["Steps"]

        Get the step size for the 2nd range in the 3rd regime:

        >>> get_tcb_settings(2, 3)["Steps"]
    """
    return _genie_api.dae.get_tcb_settings(trange, regime)


@usercommand
@helparglist("[...]")
@log_command_and_handle_exception
def change_vetos(**params: bool | None) -> None:
    """
    Change the DAE veto settings.

    Args:
        clearall (bool, optional): remove all vetos
        smp (bool, optional): set SMP veto
        ts2 (bool, optional): set TS2 veto
        hz50 (bool, optional): set 50 hz veto
        ext0  (bool, optional): set external veto 0
        ext1  (bool, optional): set external veto 1
        ext2 (bool, optional): set external veto 2
        ext3 (bool, optional): set external veto 3
        fifo (bool, optional): set FIFO veto

    Note: If clearall is specified then all vetos (excluding the FIFO veto) are turned off,
    but it is possible to turn other vetoes back on at the same time.

    Note: FIFO veto is automatically enabled on run begin, but can be changed whilst running.

    Examples:
        Turns all vetoes off then turns the SMP veto back on:

        >>> change_vetos(clearall=True, smp=True)

        Turn off FIFO:

        >>> change_vetos(fifo=False)
    """
    _genie_api.dae.change_vetos(**params)


@usercommand
@helparglist("[enable], [delay], [width]")
@log_command_and_handle_exception
def change_fermi_veto(enable: bool | None = None, delay: float = 1.0, width: float = 1.0) -> None:
    """
    Configure the fermi chopper veto.

    Args:
        enable (bool, optional): enable the fermi veto
        delay (float, optional): the veto delay
        width (float, optional): the veto width
    """
    _genie_api.dae.set_fermi_veto(enable, delay, width)


@usercommand
@helparglist("[nperiods]")
@log_command_and_handle_exception
def enable_soft_periods(nperiods: int | None = None) -> None:
    """
    Switch the DAE to software periods mode.

    Args:
        nperiods (int, optional): the number of software periods
    """
    _genie_api.dae.set_period_mode("soft")
    if nperiods is not None:
        _genie_api.dae.set_num_soft_periods(nperiods)


@usercommand
@helparglist("mode[, ...]")
@log_command_and_handle_exception
def enable_hard_periods(
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
    Sets the DAE to use hardware periods.

    Args:
        mode (string): set the mode to internal ('int') or external ('ext')
        period_file (string, optional): the file containing the internal period settings
            (ignores any other settings)
        sequences (int, optional): the number of times to repeat the period loop (0 = infinite loop)
        output_delay (int, optional): the output delay in microseconds
        period (int, optional): the number of the period to set the following parameters for
        daq (bool, optional):  the specified period is a acquisition period
        dwell (bool, optional): the specified period is a dwell period
        unused (bool, optional): the specified period is a unused period
        frames (int, optional): the number of frames to count for the specified period
        output (int, optional): the binary output the specified period
        label (string, optional): the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods

    Examples:
        Setting external periods:

        >>> enable_hard_periods("ext")

        Setting internal periods from a file:

        >>> enable_hard_periods("int", "c:\\myperiods.txt")
    """
    _genie_api.dae.configure_hard_periods(
        mode,
        period_file,
        sequences,
        output_delay,
        period,
        daq,
        dwell,
        unused,
        frames,
        output,
        label,
    )


@usercommand
@helparglist("[...]")
@log_command_and_handle_exception
def configure_internal_periods(
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
        sequences (int, optional): the number of times to repeat the period loop (0 = infinite loop)
        output_delay (int, optional): the output delay in microseconds
        period (int, optional): the number of the period to set the following parameters for
        daq (bool, optional):  the specified period is a acquisition period
        dwell (bool, optional): the specified period is a dwell period
        unused (bool, optional): the specified period is a unused period
        frames (int, optional): the number of frames to count for the specified period
        output (int, optional): the binary output the specified period
        label (string, optional): the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods
    """
    _genie_api.dae.configure_internal_periods(
        sequences, output_delay, period, daq, dwell, unused, frames, output, label
    )


@usercommand
@helparglist("[...]")
@log_command_and_handle_exception
def define_hard_period(
    period: int | None = None,
    daq: bool = False,
    dwell: bool = False,
    unused: bool = False,
    frames: int | None = None,
    output: int | None = None,
    label: str | None = None,
) -> None:
    """
    Define the internal hardware periods.

    Args:
        period (int, optional): the number of the period to set the following parameters for
        daq (bool, optional):  the specified period is a acquisition period
        dwell (bool, optional): the specified period is a dwell period
        unused (bool, optional): the specified period is a unused period
        frames (int, optional): the number of frames to count for the specified period
        output (int, optional): the binary output the specified period
        label (string, optional): the label for the period the specified period

    Note: if the period number is unspecified then the settings will be applied to all periods
    """
    configure_internal_periods(None, None, period, daq, dwell, unused, frames, output, label)


@log_command_and_handle_exception
def change(**params: str | int) -> None:
    """
    Change experiment parameters.

    Note: it is possible to change more than one item at a time.

    Args:
        title (string, optional): the new title
        period (int, optional): the new period (must be in a non-running state)
        nperiods (int, optional): the new number of software periods
            (must be in a non-running state)
        user (string, optional): the new user(s) as a comma-separated list
        rb (int, optional): the new RB number

    Examples:
        Change the title:

        >>> change(title="The new title")

        Change the user:

        >>> change(user="Instrument Team")

        Set multiple users:

        >>> change(user="Thouless, Haldane, Kosterlitz")

        Change the RB number and the users:

        >>> change(rb=123456, user="Smith, Jones")
    """
    for k in params:
        key = k.lower().strip()
        if key == "title":
            change_title(params[k])
        elif key == "period":
            change_period(params[k])
        elif key == "nperiods":
            change_number_soft_periods(params[k])
        elif key == "user" or key == "users":
            change_users(params[k])
        elif key == "rb":
            change_rb(params[k])
        else:
            raise KeyError("Unknown parameter supplied. Type help(change) for more information")


@usercommand
@helparglist("title")
@log_command_and_handle_exception
def change_title(title: str) -> None:
    """
    Sets the current title.

    Args:
        title: the new title
    """
    _genie_api.dae.set_title(title)


@usercommand
@helparglist("display_title")
@log_command_and_handle_exception
def set_display_title(display_title: bool) -> None:
    """
    Sets the current display title status.

    Args:
        display_title: the new display title status
    """
    _genie_api.dae.set_display_title(display_title)


@usercommand
@helparglist("period")
@log_command_and_handle_exception
def change_period(period: int) -> None:
    """
    Changes the current period number.

    Args:
        period (int): the period to switch to
    """
    _genie_api.dae.set_period(period)


@usercommand
@helparglist("number[, enable]")
@log_command_and_handle_exception
def change_number_soft_periods(number: int, enable: bool = False) -> None:
    """
    Sets the number of software periods for the DAE.

    Args:
        number (int): the number of periods to create
        enable (bool, optional): switch to soft period mode
    """
    if enable:
        _genie_api.dae.set_period_mode("soft")
    _genie_api.dae.set_num_soft_periods(number)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_users() -> str:
    """
    Get the users.

    Returns:
        str: the users.
    """
    return _genie_api.dae.get_users()


@usercommand
@helparglist("users")
@log_command_and_handle_exception
def change_users(users: str) -> None:
    """
    Changes the users.

    Args:
        users: a string containing the user name(s)

    Example:

        >>> change_users("Emerson, Lake, Palmer")
    """
    _genie_api.dae.set_users(users)


@usercommand
@helparglist("rb")
@log_command_and_handle_exception
def change_rb(rb: int | str) -> None:
    """
    Changes the RB number.

    Args:
        rb (int or string): the new RB number
    """
    if isinstance(rb, int):
        # If it is an int then that is fine, just cast to str as the PV is a string
        rb = str(rb)
    elif isinstance(rb, str):
        # Let's be kind in case they enter a string.
        # Check string contains only digits though
        if not rb.isdigit():
            raise TypeError("RB number must be a number.")
    else:
        raise TypeError("RB number must be a number.")
    _genie_api.dae.set_rb_number(rb)


class _GetspectrumReturn(TypedDict):
    time: list[float]
    signal: list[float]
    sum: None
    mode: str


@usercommand
@helparglist("spectrum[, period][, dist]")
@log_command_and_handle_exception
def get_spectrum(spectrum: int, period: int = 1, dist: bool = True) -> _GetspectrumReturn:
    """
    Get the specified spectrum from the DAE.

    Args:
        spectrum (int): the spectrum number
        period (int, optional): the period
        dist (bool, optional): whether to get the spectrum as a distribution. Default is True.

    Returns:
        dict: dictionary of values
    """
    return _genie_api.dae.get_spectrum(spectrum, period, dist)


@usercommand
@helparglist("spectrum[, period][, dist]")
@log_command_and_handle_exception
def plot_spectrum(spectrum: int, period: int = 1, dist: bool = True) -> object:
    """
    Get the specified spectrum from the DAE and plot it. Returns the plot that was created.

    Note: this will replace any other plots which are open.

    Args:
        spectrum (int): the spectrum number
        period (int, optional): the period. Default is 1
        dist (bool, optional): whether to get the spectrum as a distribution. Default is True

    Returns:
        The created plot

    """
    # Import SpectraPlot locally as it uses matplotlib, and the user may want to change
    # some matplotlib config parameters before it is used for the first time.
    from genie_python.genie_plot import SpectraPlot

    return SpectraPlot(_genie_api, spectrum, period, dist)


@usercommand
@helparglist("spectrum[, period][, t_min][, t_max]")
@log_command_and_handle_exception
def integrate_spectrum(
    spectrum: int, period: int = 1, t_min: float | None = None, t_max: float | None = None
) -> float | None:
    """
    Integrates the spectrum within the time period and returns neutron counts.

    The underlying algorithm sums the counts from each bin, if a bin is split by
    the time region then a proportional fraction of the count for that bin is used.

    Args:
        spectrum (int): the spectrum number
        period (int, optional): the period
        t_min (float, optional): time of flight to start from
        t_max (float, optional): time of flight to finish at

    Returns:
        float: integral of the spectrum (neutron counts); None spectrum can not be read
    """
    return _genie_api.dae.integrate_spectrum(spectrum, period, t_min, t_max)


class GetSampleParsReturnMEAS(TypedDict):
    ID: int
    LABEL: str
    SUBID: int
    TYPE: int


class GetSampleParsReturnSCRIPT(TypedDict):
    NAME: str


class _GetSampleParsReturn(TypedDict):
    AOI: float
    COMMENTS: str
    FIELD_LABEL: str
    GEOMETRY: str
    HEIGHT: float
    ID: int
    MEAS: GetSampleParsReturnMEAS
    NAME: str
    PHI: float
    SCRIPT: GetSampleParsReturnSCRIPT
    TEMP_LABEL: str
    THICK: float
    TYPE: str
    WIDTH: float


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_sample_pars() -> _GetSampleParsReturn:
    """
    Get the current sample parameter values.

    Returns:
        dict: the sample parameters
    """
    names = _genie_api.get_sample_pars()
    return names


@usercommand
@helparglist("name, value")
@log_command_and_handle_exception
def change_sample_par(name: str, value: bool | int | float | str | None) -> None:
    """
    Set a new value for a sample parameter.

    Args:
        name (string): the name of the parameter to change
        value: the new value
    """
    _genie_api.set_sample_par(name, value)


class _GetbeamlineparsReturnBEAMSTOP(TypedDict):
    POS: str


class _GetbeamlineparsReturnCHOPEN(TypedDict):
    ANG: float


class _GetbeamlineparsReturnJOURNAL(TypedDict):
    BLOCKS: str


class _GetbeamlineparsReturn(TypedDict):
    A1: float
    A2: float
    A3: float
    BCX: float
    BCY: float
    BEAMSTOP: _GetbeamlineparsReturnBEAMSTOP
    CHOPEN: _GetbeamlineparsReturnCHOPEN
    CURR_CONFIG: str
    FOEMIRROR: float
    GEOMETRY: str
    JOURNAL: _GetbeamlineparsReturnJOURNAL
    L1: float
    SDD: float


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_beamline_pars() -> _GetbeamlineparsReturn:
    """
    Get the current beamline parameter values.

    Returns:
        dict: the beamline parameters
    """
    names = _genie_api.get_beamline_pars()
    return names


@usercommand
@helparglist("name, value")
@log_command_and_handle_exception
def change_beamline_par(name: str, value: bool | int | float | str | None) -> None:
    """
    Set a new value for a beamline parameter

    Args:
        name (string): the name of the parameter to change
        value: the new value
    """
    _genie_api.set_beamline_par(name, value)


@usercommand
@helparglist("phone_num, message")
@log_command_and_handle_exception
def send_sms(phone_num: str, message: str) -> None:
    """
    Sends an SMS message to a phone number.
    If you are sending to messages to the same number often consider using g.alerts.send()

    Args:
        phone_num (string): the phone number to send the SMS to
        message (string): the message to send
    """
    _genie_api.send_sms(phone_num, message)


@usercommand
@helparglist("message, inst")
@log_command_and_handle_exception
def send_alert(message: str, inst: str | None = None) -> None:
    """
    Sends an alert message for the specified instrument.

    Args:
        message (string): the message to send
        inst (string, optional): the instrument to generate the alert for.
            Defaults to current instrument.
    """
    _genie_api.send_alert(message, inst)


@usercommand
@helparglist("address, message")
@log_command_and_handle_exception
def send_email(address: str, message: str) -> None:
    """
    Sends a message to an email address.

    Args:
        address (string): the email address to use
        message (string): the message to send
    """
    _genie_api.send_email(address, message)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_wiring_tables() -> list[str]:
    """
    Gets a list of possible wiring table choices.

    Returns:
        list: the files
    """
    return _genie_api.dae.get_wiring_tables()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_spectra_tables() -> list[str]:
    """
    Gets a list of possible spectra table choices.

    Returns:
        list: the files
    """
    return _genie_api.dae.get_spectra_tables()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_detector_tables() -> list[str]:
    """
    Gets a list of possible detector table choices.

    Returns:
        list: the files
    """
    return _genie_api.dae.get_detector_tables()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_period_files() -> list[str]:
    """
    Gets a list of possible period file choices.

    Returns:
        list: the files
    """
    return _genie_api.dae.get_period_files()


@log_command_and_handle_exception
def check_alarms(*blocks: str) -> tuple[list[str], list[str], list[str]]:
    """
    Checks whether the specified blocks are in alarm.

    Args:
        blocks (string, multiple): the block(s) to check

    Returns:
        list, list: the blocks in minor alarm and major alarm respectively

    Example:
        Check alarm state for block1 and block2:

        >>> check_alarms("block1", "block2")
    """
    return _genie_api.check_alarms(blocks)


@log_command_and_handle_exception
def check_limit_violations(*blocks: str) -> list[str]:
    """
    Checks whether the specified blocks have soft limit violations.

    Args:
        blocks (string, multiple): the block(s) to check

    Returns:
        list: the blocks that have soft limit violations

    Example:
        Check soft limit violations for block1 and block2:

        >>> check_limit_violations("block1", "block2")
    """
    return _genie_api.check_limit_violations(blocks)


@usercommand
@helparglist("name")
@log_command_and_handle_exception
def prefix_pv_name(name: str) -> str:
    """
    Prepends the instrument PV prefix on to the supplied PV name

    Args:
        name (string): The PV without the prefix.

    Returns:
        string: The PV with the instrument prefix prepended
    """
    return _genie_api.prefix_pv_name(name)


@usercommand
@helparglist("")
def get_version() -> str:
    """
    Tells you the version of genie_python that is used.

    Returns:
        string: The current version number of genie python
    """
    return VERSION


@usercommand
@helparglist("mode")
@log_command_and_handle_exception
def set_dae_simulation_mode(mode: bool, skip_required_runstates: bool = False) -> None:
    """
    Sets the DAE into simulation mode.

    Args:
         mode: True to set the DAE into simulated mode, False to set the DAE into
            non-simulated (hardware) mode
         skip_required_runstates: Ignore all checks, use with caution
    """
    # skip_required_runstates must be passed as a keyword argument for wrapper to catch it.
    _genie_api.dae.set_simulation_mode(mode, skip_required_runstates=skip_required_runstates)


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_dae_simulation_mode() -> bool:
    """
    Gets the DAE simulation mode.
    Returns:
        True if the DAE is in simulation mode, False otherwise.
    """
    return _genie_api.dae.get_simulation_mode()


def load(name: str) -> None:
    """
    Informs the user that load may not be the function they want.
    Prints a message telling the user about g.loadscript and numpy.load.

    Args:
        name (string): The script the user is trying to load.
    """
    print(
        'This function does not load a script; you probably wanted g.load_script("{0}").'
        "If you wanted numpy load please call it directly with import numpy as numpy; "
        'numpy.load("{0}")'.format(get_correct_path(name))
    )
    return


@usercommand
@log_command_and_handle_exception
def get_wiring_table() -> str | None:
    """Gets the current wiring table path"

    Returns:
            The file path of the current wiring table.
    """
    return _genie_api.dae.get_table_path("Wiring")


@usercommand
@log_command_and_handle_exception
def get_spectra_table() -> str | None:
    """Gets the current spectra table path"

    Returns:
            The file path of the current spectra table.
    """
    return _genie_api.dae.get_table_path("Spectra")


@usercommand
@log_command_and_handle_exception
def get_detector_table() -> str | None:
    """Gets the current detector table path"

    Returns:
            The file path of the current detector table.
    """
    return _genie_api.dae.get_table_path("Detector")
