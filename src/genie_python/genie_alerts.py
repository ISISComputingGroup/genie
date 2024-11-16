"""
Genie Alerts module:

This module is used for setting alerts on blocks.
"""

from __future__ import absolute_import, print_function

from genie_python.genie_api_setup import (
    __api,
    helparglist,
    log_command_and_handle_exception,
    usercommand,
)

_ALERT_ENABLE = "CS:SB:{}:AC:ENABLE"
_ALERT_LOW = "CS:SB:{}:AC:LOW"
_ALERT_HIGH = "CS:SB:{}:AC:HIGH"
_ALERT_DELAY_OUT = "CS:SB:{}:AC:OUT:DELAY"
_ALERT_DELAY_IN = "CS:SB:{}:AC:IN:DELAY"

_ALERT_MOBILES = "CS:AC:ALERTS:MOBILES:SP"
_ALERT_EMAILS = "CS:AC:ALERTS:EMAILS:SP"
_ALERT_MESSAGE = "CS:AC:ALERTS:MESSAGE:SP"


@usercommand
@helparglist("block, lowlimit, highlimit, [delay_in, delay_out]")
@log_command_and_handle_exception
def set_range(block, lowlimit, highlimit, set_enable=True, delay_in=None, delay_out=None):
    """
    Sets alert range on block.

    Args:
        block (str): Block name
        lowlimit (float): low limit
        highlimit (float): high limit
        set_enable (bool): (optional setting True will enable alerts on the block. Defaults to True.
        delay_in (float): (optional) delay /s before triggering in range. If not specified the delay remains unchanged.
        delay_out (float): (optional) delay /s before triggering out of range. If not specified the delay remains unchanged.

    """
    if not __api.block_exists(block):
        raise Exception('No block with the name "{}" exists'.format(block))

    __api.set_pv_value(_ALERT_LOW.format(block), lowlimit, wait=False, is_local=True)
    __api.set_pv_value(_ALERT_HIGH.format(block), highlimit, wait=False, is_local=True)
    if delay_in is not None:
        __api.set_pv_value(_ALERT_DELAY_IN.format(block), delay_in, wait=False, is_local=True)
    if delay_out is not None:
        __api.set_pv_value(_ALERT_DELAY_OUT.format(block), delay_out, wait=False, is_local=True)
    if set_enable:
        enable(block)


@usercommand
@helparglist("block [, is_enabled]")
@log_command_and_handle_exception
def enable(block, set_enabled=True):
    """
    Enable alerts on a block.

    Args:
        block (str): Block name
        set_enabled (bool): whether to enable

    """
    if not __api.block_exists(block):
        raise Exception('No block with the name "{}" exists'.format(block))
    __api.set_pv_value(_ALERT_ENABLE.format(block), set_enabled, wait=False, is_local=True)


@usercommand
@helparglist("message")
@log_command_and_handle_exception
def send(message):
    """
    Send a message to all alert recipients.

    Args:
        message (str): message to send

    """
    __api.set_pv_value(_ALERT_MESSAGE, message, wait=False, is_local=True)


## no log decorator so mobile numbers not sent to log file
@usercommand
@helparglist("numbers")
def set_sms(numbers):
    """
    Set SMS text numbers for alerts on blocks.

    Args:
        numbers (list): list of strings giving phone numbers

    """
    try:
        if isinstance(numbers, list):
            __api.set_pv_value(_ALERT_MOBILES, ";".join(numbers), wait=False, is_local=True)
        else:
            __api.set_pv_value(_ALERT_MOBILES, numbers, wait=False, is_local=True)
    except Exception as e:
        print("Unable to set alert SMS numbers: {}".format(e))


## no log decorator so email addresses not sent to log file
@usercommand
@helparglist("emails")
def set_email(emails):
    """
    Set email addresses for alerts on blocks.

    Args:
        emails (list): list of strings giving email addresses

    """
    try:
        if isinstance(emails, list):
            __api.set_pv_value(_ALERT_EMAILS, ";".join(emails), wait=False, is_local=True)
        else:
            __api.set_pv_value(_ALERT_EMAILS, emails, wait=False, is_local=True)
    except Exception as e:
        print("Unable to set alert email addresses: {}".format(e))


def _print_block(block, only_if_enabled=False):
    enabled = (
        __api.get_pv_value(_ALERT_ENABLE.format(block), to_string=True, is_local=True) == "YES"
    )
    if only_if_enabled and not enabled:
        return
    print("Block: {}".format(block))
    print("  Enabled:   {}".format(enabled))
    print(
        "  Low:       {}".format(
            __api.get_pv_value(_ALERT_LOW.format(block), to_string=False, is_local=True)
        )
    )
    print(
        "  High:      {}".format(
            __api.get_pv_value(_ALERT_HIGH.format(block), to_string=False, is_local=True)
        )
    )
    print(
        "  Delay In:  {}".format(
            __api.get_pv_value(_ALERT_DELAY_IN.format(block), to_string=False, is_local=True)
        )
    )
    print(
        "  Delay Out: {}".format(
            __api.get_pv_value(_ALERT_DELAY_OUT.format(block), to_string=False, is_local=True)
        )
    )


@usercommand
@helparglist("[block, all]")
@log_command_and_handle_exception
def status(block=None, all=False):
    """
    Prints the emails and mobiles used for alerts and the current status of specified block.
    Args:
        block (string): The block to print information about
        all (bool): If True information about all the blocks is printed
    """
    print("Emails: {}".format(__api.get_pv_value(_ALERT_EMAILS, to_string=False, is_local=True)))
    print("Mobiles: {}".format(__api.get_pv_value(_ALERT_MOBILES, to_string=True, is_local=True)))
    if block is not None:
        if not __api.block_exists(block):
            raise Exception('No block with the name "{}" exists'.format(block))
        _print_block(block)
    else:
        blocks = __api.get_block_names()
        for block in blocks:
            _print_block(block, not all)


# used as part of tests, returns a dictionary of details
def _dump(block):
    if not __api.block_exists(block):
        raise Exception('No block with the name "{}" exists'.format(block))
    res = {}
    res["emails"] = __api.get_pv_value(_ALERT_EMAILS, to_string=True, is_local=True).split(";")
    res["mobiles"] = __api.get_pv_value(_ALERT_MOBILES, to_string=True, is_local=True).split(";")
    res["enabled"] = __api.get_pv_value(_ALERT_ENABLE.format(block), to_string=False, is_local=True)
    res["lowlimit"] = __api.get_pv_value(_ALERT_LOW.format(block), to_string=False, is_local=True)
    res["highlimit"] = __api.get_pv_value(_ALERT_HIGH.format(block), to_string=False, is_local=True)
    res["delay_in"] = __api.get_pv_value(
        _ALERT_DELAY_IN.format(block), to_string=False, is_local=True
    )
    res["delay_out"] = __api.get_pv_value(
        _ALERT_DELAY_OUT.format(block), to_string=False, is_local=True
    )
    return res
