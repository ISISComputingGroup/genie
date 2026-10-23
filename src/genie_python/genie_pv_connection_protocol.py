from collections.abc import Callable
from typing import Protocol, runtime_checkable

from ibex_non_ca_helpers import PVValue


@runtime_checkable
class GeniePvConnectionProtocol(Protocol):
    @staticmethod
    def set_pv_value(
        name: str, value: "PVValue|bytes", wait: bool, timeout: float, safe_not_quick: bool
    ) -> None: ...

    @staticmethod
    def clear_monitor(name: str, timeout: float) -> None: ...

    @staticmethod
    def get_pv_value(
        name: str, to_string: bool, timeout: float, use_numpy: bool | None
    ) -> "PVValue": ...

    @staticmethod
    def get_pv_timestamp(name: str, timeout: float) -> tuple[int, int]: ...

    @staticmethod
    def pv_exists(name: str, timeout: float) -> bool: ...

    @staticmethod
    def add_monitor(
        name: str,
        call_back_function: "Callable[[PVValue, str | None, str | None], None]",
        link_alarm_on_disconnect: bool = True,
        to_string: bool = False,
        use_numpy: bool | None = None,
    ) -> Callable[[], None]: ...
