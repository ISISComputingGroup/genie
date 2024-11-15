from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:
    from genie_python.genie import PVValue


@runtime_checkable
class GeniePvConnectionProtocol(Protocol):
    @staticmethod
    def set_pv_value(
        name: str, value: "PVValue", wait: bool, timeout: float, safe_not_quick: bool
    ) -> None: ...

    @staticmethod
    def clear_monitor(name: str, timeout: float) -> None: ...

    @staticmethod
    def get_pv_value(
        name: str, to_string: bool, timeout: float, use_numpy: bool | None
    ) -> "PVValue": ...

    @staticmethod
    def get_pv_timestamp(name: str, timeout: float) -> Tuple[int, int]: ...

    @staticmethod
    def pv_exists(name: str, timeout: float) -> bool: ...

    @staticmethod
    def add_monitor(
        name: str,
        call_back_function: "Callable[[PVValue, str, str], None]",
        link_alarm_on_disconnect: bool = True,
        to_string: bool = False,
        use_numpy: bool | None = None,
    ) -> Callable[[], None]: ...
