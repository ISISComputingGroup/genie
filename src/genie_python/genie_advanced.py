"""
Genie Advanced module:

This module is used for advanced commands that are for expert users.
"""

import contextlib
from datetime import datetime, timedelta
from time import sleep
from typing import Any, Callable, Iterator, TypedDict

import numpy.typing as npt

from genie_python.genie_api_setup import (
    __api,
    helparglist,
    log_command_and_handle_exception,
    usercommand,
)
from genie_python.genie_waitfor import DELAY_IN_WAIT_FOR_SLEEP_LOOP
from genie_python.utilities import check_break


@usercommand
@helparglist("")
def get_manager_mode() -> bool:
    """
    Returns whether you are in manager mode or not.

    Returns:
        manager_mode (Bool): Manager mode on or off.

    """

    return __api.get_pv_value("CS:MANAGER", True, 3, True) == "Yes"


@usercommand
@helparglist("")
def assert_in_manager_mode() -> None:
    """
    Checks that the user is in manager mode so can use advanced functions.

    Args:

    Returns:

    """

    if not get_manager_mode():
        raise RuntimeError("You need to be in Manager mode to complete this action.")


@contextlib.contextmanager
def motor_in_set_mode(pv_name: str) -> Iterator:
    """
    Uses a context to place motor into set mode and ensure that it leaves
    set mode after context has ended. If it can not set the mode correctly
    will not run the yield.

    Args:
        pv_name: pv of motor on which to set the mode

    Returns:
    """

    if not __api.pv_exists(pv_name):
        raise ValueError("Cannot find pv " + pv_name)

    try:
        __api.set_pv_value(pv_name + ".SET", 1, True)
        offset_freeze_switch = __api.get_pv_value(pv_name + ".FOFF")
        __api.set_pv_value(pv_name + ".FOFF", "Frozen", True)
    except IOError as ex:
        raise ValueError("Can not set motor set and frozen offset mode: {}".format(ex))

    try:
        yield
    finally:
        try:
            __api.set_pv_value(pv_name + ".SET", 0, True)
            __api.set_pv_value(pv_name + ".FOFF", offset_freeze_switch, True)
        except IOError as ex:
            raise ValueError("Can not reset motor set and frozen offset mode: {}".format(ex))


@usercommand
@helparglist("name str, value flt")
def redefine_motor_position(name: str, value: float | int) -> None:
    """

    Change the motor Move Abs value.

    Args:
        name: Name of the motor. e.g MTR0101
        value: The new value of Move Abs.

    Returns:

    """

    assert_in_manager_mode()

    pv_name = f"{__api.inst_prefix}MOT:{name}"

    with motor_in_set_mode(pv_name):
        if __api.get_pv_value(pv_name + ".MOVN") == 1:
            raise RuntimeError("Cannot change motor " + name + " position while it is moving.")

        try:
            __api.set_pv_value(pv_name + ".VAL", value, True)
        except IOError as ex:
            raise ValueError("Can not set new motor position: {}".format(ex))


@usercommand
@helparglist("block str")
@log_command_and_handle_exception
def get_pv_from_block(block: str) -> str:
    """
    Get the full PV name for a given block.
    This is an advanced function because of the need to use the pv name correctly.

    Args:
        block (str): A block object

    Returns:
        pv_name (Str): The pv name as a string

    """
    return __api.get_pv_from_block(block)


@usercommand
@helparglist("pv str")
@log_command_and_handle_exception
def pv_exists(pv: str, is_local: bool = False) -> None:
    """
    Check if PV exists.

    Params:
        pv (str): The address of the PV
        is_local (bool, optional): is it a local PV i.e. needs prefix adding
    """
    return __api.pv_exists(pv, is_local=is_local)


@usercommand
@helparglist("pv str, value[, maxwait]")
@log_command_and_handle_exception
def wait_for_pv(
    pv: str, value: bool | int | float | str | None, maxwait: int | None = None
) -> None:
    """
    Wait until a PV has reached a given value.

    Params:
        pv (str): The address of the PV
        value: The value to wait for
        maxwait (int, optional): The maximum time to wait for in seconds
    """
    start_time = datetime.utcnow()
    while True:
        curr_value = __api.get_pv_value(pv)
        if curr_value == value:
            break
        if maxwait is not None:
            if timedelta(seconds=maxwait) < datetime.utcnow() - start_time:
                break
        sleep(DELAY_IN_WAIT_FOR_SLEEP_LOOP)
        check_break(2)


@usercommand
@helparglist("")
def set_begin_precmd(begin_precmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call before the begin command.

    Args:
        begin_precmd (function): The function to call (which should return
        None if it wants the run to start, or a string with the reason why not to start run).
    """
    __api.pre_post_cmd_manager.begin_precmd = begin_precmd


@usercommand
@helparglist("")
def set_begin_postcmd(begin_postcmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call after the begin command.

    Args:
        begin_postcmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.begin_postcmd = begin_postcmd


@usercommand
@helparglist("")
def set_abort_precmd(abort_precmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call before the abort command.

    Args:
        abort_precmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.abort_precmd = abort_precmd


@usercommand
@helparglist("")
def set_abort_postcmd(abort_postcmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call after the abort command.

    Args:
        abort_postcmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.abort_postcmd = abort_postcmd


@usercommand
@helparglist("")
def set_end_precmd(end_precmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call before the end command.

    Args:
        end_precmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.end_precmd = end_precmd


@usercommand
@helparglist("")
def set_end_postcmd(end_postcmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call after the end command.

    Args:
        end_postcmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.end_postcmd = end_postcmd


@usercommand
@helparglist("")
def set_pause_precmd(pause_precmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call before the pause command.

    Args:
        pause_precmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.pause_precmd = pause_precmd


@usercommand
@helparglist("")
def set_pause_postcmd(pause_postcmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call after the pause command.

    Args:
        pause_postcmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.pause_postcmd = pause_postcmd


@usercommand
@helparglist("")
def set_resume_precmd(resume_precmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call before the resume command.

    Args:
        resume_precmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.resume_precmd = resume_precmd


@usercommand
@helparglist("")
def set_resume_postcmd(resume_postcmd: Callable[[Any], str | None]) -> None:
    """
    Set the function to call after the resume command.

    Args:
        resume_postcmd (function): The function to call.
    """
    __api.pre_post_cmd_manager.resume_postcmd = resume_postcmd


@usercommand
@helparglist("")
def open_plot_window(
    is_primary: bool = True, host: str | int | None = None, figures: list[int] | None = None
) -> None:
    """
    Open the plot window in a locally running client
    (even if this is called in a standalone genie_python)
    Args:
        is_primary: True to open primary plotting window; False open secondaty window
        host: host to open plot from; Default None is localhost
        figures: List of figures to open; Default opens all figures
    """
    from genie_python.matplotlib_backend.ibex_websocket_backend import (
        figure_numbers,
        ibex_open_plot_window,
    )

    ibex_open_plot_window(
        figures=figure_numbers if figures is None else figures, is_primary=is_primary, host=host
    )


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_instrument() -> str | None:
    """
    Gets the name of the local instrument (e.g. NDW1234, DEMO, EMMA-A)

    Returns:
        the name of the local instrument
    """
    return __api.get_instrument()


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_instrument_full_name() -> str | None:
    """
    Gets the full name of the local instrument

    Returns:
        the full name of the machine
    """
    return __api.get_instrument_full_name()


@usercommand
@helparglist("verbose")
@log_command_and_handle_exception
def set_dae_message_verbosity(verbose: bool) -> None:
    """
    Set the verbosity of messages coming from the DAE.

    Args:
        verbose (bool): set the verbosity, True to be more verbose
    """
    __api.dae.set_verbose(verbose)


class _GetExpDataReturn(TypedDict):
    rb_number: int | str
    user: str
    role: str
    start_date: str
    duration: float


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_exp_data(
    rb: int | str = "%", user: str = "%", role: str = "%", verbose: bool = False
) -> list[_GetExpDataReturn]:
    """
    Returns the data of experiments that match the given criteria,
    or all if none is given, from the exp_data
    database. If verbose is enabled, only pretty-print the data.

    Args:
        rb (int, optional): The RB number of the experiment to look for, Defaults to Any.
        user (str, optional): The name of the user who is running/has
            run the experiment, Defaults to Any.
        role (str, optional): The user role, Defaults to Any.
        verbose (bool, optional): Pretty-print the data, Defaults to False.

    Returns:
        exp_data (list): The experiment(s) data as a list of dicts.

    Raises:
        NotFoundError: Thrown if a parameter's value was not found in the database.

    """
    try:
        if __api.exp_data is None:
            raise EnvironmentError("Could not connect to instrument database")
        return __api.exp_data.get_exp_data(rb, user, role, verbose)
    except AttributeError as e:
        raise NotImplementedError(
            "get_exp_data is not implemented for this genie type. {}".format(e)
        )


@usercommand
@helparglist("")
@log_command_and_handle_exception
def get_spectrum_data(with_spec_zero: bool = True, with_time_bin_zero: bool = False) -> npt.NDArray:
    """
    Get the event mode spectrum data as ND array.

    Args:
        with_spec_zero (bool, optional):  Include or exclude diagnostic spectrum 0
            if you have 10 spectra and include spectrum zero, your array will be
            of size 11 and spectrum 5 will be at array[5]. If you exclude spectrum zero
            then spectrum 5 would be at array[4]
        with_time_bin_zero (bool, optional):  Include or exclude diagnostic bin 0
            if you have 1000 time channels and include time bin 0, your array will be
            of size 1001 and data for your defined time bins will start at array[1]
            rather than array[0]. This bin contents is only of use for diagnostic
            issues, it contains data that does not fit into the defined time range
    Returns:
        numpy int array: spectrum data ND array
            this is of dimensions [periods, spectra, time_bins]
    """
    data = __api.dae.get_spec_data()
    nper = __api.dae.get_num_periods()
    nsp = __api.dae.get_num_spectra()
    ntc = __api.dae.get_num_timechannels()
    # this is (nsp + 1) and (ntc + 1) for spectrum 0 and time channel 0
    data_reshaped = data.reshape((nper, nsp + 1, ntc + 1))
    return data_reshaped[
        slice(None),
        slice(None) if with_spec_zero else slice(1, None),
        slice(None) if with_time_bin_zero else slice(1, None),
    ]
