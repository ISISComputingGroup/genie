"""
Wrapping of pvAccess (p4p) in genie_python
"""

from __future__ import absolute_import, print_function

import os
import threading
from builtins import object
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import TYPE_CHECKING, NoReturn, Optional, Tuple, TypeVar

import numpy as np
from p4p import Value
from p4p._p4p import RemoteError
from p4p.client.thread import Context

if TYPE_CHECKING:
    from genie_python.genie import PVValue

from .channel_access_exceptions import (
    InvalidEnumStringException,
    ReadAccessException,
    UnableToConnectToPVException,
    WriteAccessException,
)
from .utilities import waveform_to_string

TIMEOUT = 10  # Default timeout for PV set/get
EXIST_TIMEOUT = 3  # Separate smaller timeout for pv_exists() operations
T = TypeVar("T")

# Name of the p4p provider to use. 'pva' is the standard pvAccess provider;
# this mirrors how CaChannel implicitly uses the 'ca' provider throughout
# the CA wrapper.
PROVIDER = "pva"

_CONTEXT_LOCK = threading.Lock()
_CONTEXT: Optional[Context] = None


@dataclass(frozen=True, slots=True)
class PvaChannel:
    """
    Thin wrapper bundling a shared p4p context with a PV name.
    """

    context: Context
    name: str


def _removed(what: str, reason: str) -> NoReturn:
    raise NotImplementedError(f"{what} is not available on the pvAccess wrapper: {reason}")


class PVAccessWrapper(object):
    """
    Wrap pvAccess channel access to give utility methods for access in one place
    """

    error_log_func: Optional[Callable[[str], None]] = None

    # noinspection PyPep8Naming
    @staticmethod
    def logError(message: str):  # noqa N802
        ...

    # noinspection PyPep8Naming
    @staticmethod
    def printfHandler(message: str, user_args: Tuple[T, ...]) -> None:  # noqa N802
        _removed(
            "printfHandler",
            "Not supported by PVA/P4P.",
        )

    # noinspection PyPep8Naming
    @staticmethod
    def CAExceptionHandler(epics_args: dict[str, str], user_args: Tuple[None]) -> None:  # noqa N802
        _removed(
            "CAExceptionHandler",
            "Not supported by PVA/P4P.",
        )

    # noinspection PyPep8Naming
    @staticmethod
    def installHandlers(chan: PvaChannel) -> None:  # noqa N802
        _removed(
            "installHandlers",
            "Not supported by PVA/P4P.",
        )

    # noinspection PyPep8Naming
    @staticmethod
    def putCB(epics_args: Tuple[str, int, int, int], user_args: Tuple[Event, ...]) -> None:  # noqa N802
        _removed(
            "putCB",
            "Not supported by PVA/P4P.",
        )

    @staticmethod
    def set_pv_value(
        name: str,
        value: "PVValue|bytes",
        wait: bool = False,
        timeout: float = TIMEOUT,
        safe_not_quick: bool = True,
    ) -> None:
        ...

    @staticmethod
    def _check_for_disp(name: str) -> None:
        ...

    @staticmethod
    def get_chan(name: str, timeout: float = EXIST_TIMEOUT) -> PvaChannel:
        channel = PvaChannel(context=PVAccessWrapper._get_context(), name=name)
        PVAccessWrapper.connect_to_pv(channel)
        return channel

    @staticmethod
    def clear_monitor(name: str, timeout: float = EXIST_TIMEOUT) -> None:
        ...

    @staticmethod
    def get_pv_value(
            name: str, to_string: bool = False, timeout: float = TIMEOUT, use_numpy: bool | None = None
    ) -> "PVValue":
        chan = PVAccessWrapper.get_chan(name=name, timeout=timeout)
        try:
            value: Value = chan.context.get(name, timeout=timeout)
        except RemoteError as e:
            raise ReadAccessException(name) from e

        match value.getID():
            case "epics:nt/NTEnum:1.0":
                # CA forces to_string=True for ENUM fields unconditionally, so
                # the caller's to_string argument is not consulted here either.
                index = value["value.index"]
                choices = value["value.choices"]
                return choices[index]

            case "epics:nt/NTScalar:1.0":
                raw = value["value"]
                element_type = value.type()["value"]
                # 's' is already a string; 'b'/'B' (byte) mirrors CA's
                # dbr_type_is_CHAR forcing to_string regardless of the flag.
                is_text = element_type in ("s", "b", "B")
                if to_string or is_text:
                    return str(raw)
                return raw

            case "epics:nt/NTScalarArray:1.0":
                raw = value["value"]
                element_type = value.type()["value"][1:]  # strip leading 'a'
                is_char_waveform = element_type in ("b", "B")
                if to_string or is_char_waveform:
                    elements = raw.tolist() if isinstance(raw, np.ndarray) else list(raw)
                    return waveform_to_string(elements)
                if use_numpy is False and isinstance(raw, np.ndarray):
                    return raw.tolist()
                return raw

            case "epics:nt/NTTable:1.0":
                labels = value["labels"]
                return {label: value[f"value.{label}"] for label in labels}

            case _:
                if value.has("value"):
                    return value["value"]
                return value.tostr()

    @staticmethod
    def get_pv_timestamp(name: str, timeout: float = TIMEOUT) -> Tuple[int, int]:
        ...

    @staticmethod
    def pv_exists(name: str, timeout: float = EXIST_TIMEOUT) -> bool:
        ...

    @staticmethod
    def connect_to_pv(channel: PvaChannel) -> None:
        if os.getenv("GITHUB_ACTIONS"):
            # genie_python does some PV accesses on import. To avoid them timing out and making CI
            # builds really slow, shortcut every PV to "non-existent" here.
            raise UnableToConnectToPVException("", "In CI")

        try:
            channel.context.get(channel.name, timeout=EXIST_TIMEOUT)
        except TimeoutError as e:
            raise UnableToConnectToPVException(channel.name, str(e))

    @staticmethod
    def check_for_enum_value(value: "PVValue|bytes", chan: PvaChannel, name: str) -> "PVValue|bytes":
        ...

    @staticmethod
    def add_monitor(
        name: str,
        call_back_function: "Callable[[PVValue, Optional[str], Optional[str]], None]",
        link_alarm_on_disconnect: bool = True,
        to_string: bool = False,
        use_numpy: bool | None = None,
    ) -> Callable[[], None]:
        ...

    @staticmethod
    def poll() -> None:
        _removed(
            "poll",
            "Not supported by PVA/P4P.",
        )

    @staticmethod
    def _wait_for_pend_event(
        chan: PvaChannel, event: Event, timeout: Optional[float] = None, interval: float = 0.1
    ) -> None:
        _removed(
            "_wait_for_pend_event",
            "Not supported by PVA/P4P.",
        )

    @staticmethod
    def dbf_type_to_string(typ: str) -> str:
        ...

    @staticmethod
    def _get_context() -> Context:
        global _CONTEXT

        if _CONTEXT is None:
            with _CONTEXT_LOCK:
                if _CONTEXT is None:
                    _CONTEXT = Context(PROVIDER)

        assert _CONTEXT is not None
        return _CONTEXT