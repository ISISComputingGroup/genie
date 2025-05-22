from __future__ import absolute_import, print_function

import time
from builtins import object
from typing import TYPE_CHECKING, Any, Callable, ParamSpec, TypeVar

from genie_python.utilities import compress_and_hex, dehex_decompress_and_dejson

if TYPE_CHECKING:
    from genie_python.genie import PVValue
    from genie_python.genie_epics_api import API

Param = ParamSpec("Param")
RetType = TypeVar("RetType")

# Prefix for block server pvs
PV_BLOCK_NAMES = "BLOCKNAMES"
BLOCK_SERVER_PREFIX = "CS:BLOCKSERVER:"


def _blockserver_retry(func: Callable[Param, RetType]) -> Callable[Param, RetType]:
    def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RetType:
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(
                    "Exception thrown from {}: {}, will retry in 15 seconds".format(
                        func.__name__, e.__class__.__name__
                    )
                )
                time.sleep(15)

    return wrapper


class BlockServer(object):
    def __init__(self, api: "API") -> None:
        self.api: "API" = api

    def _get_pv_value(self, pv: str, as_string: bool = False) -> "PVValue":
        """Just a convenient wrapper for calling the api's get_pv_value method"""
        return self.api.get_pv_value(self.api.prefix_pv_name(pv), as_string)

    def _set_pv_value(self, pv: str, value: "PVValue | bytes", wait: bool = False) -> None:
        """Just a convenient wrapper for calling the api's set_pv_value method"""
        return self.api.set_pv_value(self.api.prefix_pv_name(pv), value, wait)

    @_blockserver_retry
    def get_sample_par_names(self) -> Any:  # noqa: ANN401
        """Get the current sample parameter names as a list."""
        # Get the names from the blockserver
        raw = self._get_pv_value(BLOCK_SERVER_PREFIX + "SAMPLE_PARS", True)
        return dehex_decompress_and_dejson(raw)

    @_blockserver_retry
    def get_beamline_par_names(self) -> Any:  # noqa: ANN401
        """Get the current beamline parameter names as a list."""
        # Get the names from the blockserver
        raw = self._get_pv_value(BLOCK_SERVER_PREFIX + "BEAMLINE_PARS", True)
        return dehex_decompress_and_dejson(raw)

    @_blockserver_retry
    def get_runcontrol_settings(self) -> Any:  # noqa: ANN401
        """Get the current run-control settings."""
        raw = self._get_pv_value(BLOCK_SERVER_PREFIX + "GET_RC_PARS", True)
        return dehex_decompress_and_dejson(raw)

    def reload_current_config(self) -> None:
        """Reload the current configuration."""
        raw = compress_and_hex("1")
        self._set_pv_value(BLOCK_SERVER_PREFIX + "RELOAD_CURRENT_CONFIG", raw, True)
