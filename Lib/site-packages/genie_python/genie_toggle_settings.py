"""
Genie Toggle Settings module.

This module is used for storing and updating user preferences and settings.
"""

from __future__ import absolute_import, print_function

import genie_python.genie_api_setup  # for _exceptions_raised
from genie_python.genie_api_setup import helparglist, log_command_and_handle_exception, usercommand


class ToggleSettings:
    cset_verbose = False


@usercommand
@helparglist("")
@log_command_and_handle_exception
def exceptions_raised(toggle_on):
    """
    Set whether to allow exceptions to propagate (True) or let genie handle any exceptions (False).
    By default (False), genie_python will handle any exceptions by printing the error message and carrying on.

    Args:
        toggle_on (bool): Allow exceptions if True, let genie handle exceptions if False.

    Examples:
        Set genie_python not to handle exceptions:

        >>> exceptions_raised(True)
    """
    if not isinstance(toggle_on, bool):
        raise ValueError("Exceptions raised setting needs to be True or False.")
    genie_python.genie_api_setup._exceptions_raised = toggle_on
    # noinspection PyProtectedMember
    print("Raise exceptions set to {}.".format(genie_python.genie_api_setup._exceptions_raised))


@usercommand
@helparglist("")
@log_command_and_handle_exception
def cset_verbose(verbose):
    """
    Set the default verbosity of cset.

    Args:
        verbose (bool): The cset verbose flag.

    Examples:
        Setting up all cset calls to be verbose:

        >>> cset_verbose(True)
    """
    if not isinstance(verbose, bool):
        raise ValueError("Default verbosity needs to be True or False.")
    ToggleSettings.cset_verbose = verbose
    print("Default cset verbosity set to {}.".format(ToggleSettings.cset_verbose))
