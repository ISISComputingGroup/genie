"""
Wrapping of p4p in genie_python
"""

from __future__ import absolute_import, print_function

import threading
from builtins import object
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional, Tuple

from p4p import Value
from p4p.client.thread import Context, Subscription

from .channel_access_exceptions import WriteAccessException
from .utilities import waveform_to_string

if TYPE_CHECKING:
    from genie_python.genie import PVValue

TIMEOUT = 15  # Default timeout for PV set/get
EXIST_TIMEOUT = 3  # Separate smaller timeout for pv_exists() and searchw() operations
CACHE = threading.local()
CACHE_LOCK = threading.local()


class P4PWrapper(object):
    context: Optional[Context] = None
    error_log_function: Optional[Callable[[str], None]] = None

    # noinspection PyPep8Naming
    @staticmethod
    def _log_error(message: str) -> None:
        """
        Log an error
        Args:
            message: message to log
        """
        if P4PWrapper.error_log_function is not None:
            try:
                P4PWrapper.error_log_function(message)
            except Exception:
                pass
        else:
            print("PVERROR: {}".format(message))

    @staticmethod
    def set_pv_value(
        name: str,
        value: "PVValue",
        wait: bool = False,
        timeout: float = TIMEOUT,
        safe_not_quick: bool = True,
    ) -> None:
        if safe_not_quick:
            P4PWrapper._check_for_disp(name)
        context = P4PWrapper.get_context()
        context.put(name, value, timeout=timeout, wait=wait)

    @staticmethod
    def clear_monitor(name: str, timeout: float) -> None:
        try:
            lock = CACHE_LOCK.lock
        except AttributeError:
            lock = CACHE_LOCK.lock = threading.RLock()
        with lock:
            try:
                subscriptions = CACHE.subscriptions
                if name in subscriptions:
                    subscriptions.pop(name).close()
            except AttributeError:
                return

    @staticmethod
    def get_pv_value(
        name: str,
        to_string: bool = False,
        timeout: float = TIMEOUT,
        use_numpy: Optional[bool] = None,
    ) -> "PVValue":
        context = P4PWrapper.get_context()
        output = context.get(name, timeout=timeout)
        if isinstance(output, Exception):
            raise output

        # Required to convince pyright the type won't be [Exception] which is only a valid response
        # to a list of names. This should be replaced by proper handling for [Value] and [Exception]
        # In a non-minimal/equivalent to CaChannel implementation.
        assert isinstance(output, Value)

        val = output.value

        # If it's still a Value type then it's an Enum, so get the index or choice.
        if isinstance(val, Value):
            return val.choices[val.index]

        if to_string:
            val = str(val)
        return val

    @staticmethod
    def get_pv_timestamp(name: str, timeout: float = TIMEOUT) -> Tuple[int, int]:
        context = P4PWrapper.get_context()
        output = context.get(name, timeout=timeout)
        if isinstance(output, Exception):
            raise output

        # Required to convince pyright the type won't be [Exception] which is only a valid response
        # to a list of names. This should be replaced by proper handling for [Value] and [Exception]
        # In a non-minimal/equivalent to CaChannel implementation.
        assert isinstance(output, Value)

        time = output.timeStamp
        return time.get("secondsPastEpoch"), time.get("nanoseconds")

    @staticmethod
    def pv_exists(name: str, timeout: float) -> bool:
        try:
            P4PWrapper.get_pv_value(name, timeout=timeout)
            return True
        except TimeoutError:
            return False

    @staticmethod
    def add_monitor(
        name: str,
        call_back_function: "Callable[[PVValue, str, str], None]",
        link_alarm_on_disconnect: bool = True,
        to_string: bool = False,
        use_numpy: Optional[bool] = None,
    ) -> Subscription:
        def _process_call_back(response: Value | Exception) -> None:
            if isinstance(response, Exception):
                P4PWrapper._log_error(str(response))
                return
            value = response.get("value")
            if isinstance(value, Value):
                value = value.choices[value.index]
            if to_string:
                # Could see if the element count is > 1 instead
                if isinstance(value, list):
                    value = waveform_to_string(value)
                else:
                    value = str(value)
            elif isinstance(value, Value):
                value = value.index

            call_back_function(
                value,
                response.get("alarm").get("severity"),
                response.get("alarm").get("status"),
            )

        context = P4PWrapper.get_context()
        subscription = context.monitor(name, _process_call_back, notify_disconnect=True)

        # Add to a dict of subscriptions to reproduce ability to close a monitor by its name.
        try:
            lock = CACHE_LOCK.lock
        except AttributeError:
            lock = CACHE_LOCK.lock = threading.RLock()
        with lock:
            try:
                subscriptions = CACHE.subscriptions
                subscriptions.update({name: subscription})
            except AttributeError:
                CACHE.subscriptions = {name: Subscription}
        return subscription

    @staticmethod
    def get_context(autowrap: bool = False) -> Context:
        try:
            lock = CACHE_LOCK.lock
        except AttributeError:
            lock = CACHE_LOCK.lock = threading.RLock()

        with lock:
            try:
                thread_context = CACHE.context
            except AttributeError:
                thread_context = CACHE.context = Context("pva", nt=autowrap)
            if thread_context is None:
                thread_context = Context("pva", nt=autowrap)
        return thread_context

    @staticmethod
    def _check_for_disp(name: str) -> None:
        """
        Check if DISP is set on a PV. If passed a field instead of a PV, do nothing.
        Only check DISP if it exists.
        """
        if (
            ".DISP" not in name
        ):  # Do not check for DISP if it's already in the name of the PV to check
            if "." in name:  # If given a field on a PV, check the PV itself if DISP is set
                name = name.split(".")[0]
            _disp_name = "{}.DISP".format(name)
            if P4PWrapper.pv_exists(_disp_name, 0) and P4PWrapper.get_pv_value(_disp_name) != "0":
                raise WriteAccessException("{} (DISP is set)".format(name))

    @staticmethod
    def close_context() -> None:
        P4PWrapper.get_context().close()
