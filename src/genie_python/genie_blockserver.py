from __future__ import absolute_import, print_function

import time
from builtins import object

from genie_python.utilities import compress_and_hex, dehex_decompress_and_dejson

# Prefix for block server pvs
PV_BLOCK_NAMES = "BLOCKNAMES"
BLOCK_SERVER_PREFIX = "CS:BLOCKSERVER:"


def _blockserver_retry(func):
    def wrapper(*args, **kwargs):
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
    def __init__(self, api):
        self.api = api

    def _get_pv_value(self, pv, as_string=False):
        """Just a convenient wrapper for calling the api's get_pv_value method"""
        return self.api.get_pv_value(self.api.prefix_pv_name(pv), as_string)

    def _set_pv_value(self, pv, value, wait=False):
        """Just a convenient wrapper for calling the api's set_pv_value method"""
        return self.api.set_pv_value(self.api.prefix_pv_name(pv), value, wait)

    @_blockserver_retry
    def get_sample_par_names(self):
        """Get the current sample parameter names as a list."""
        # Get the names from the blockserver
        raw = self._get_pv_value(BLOCK_SERVER_PREFIX + "SAMPLE_PARS", True)
        return dehex_decompress_and_dejson(raw)

    @_blockserver_retry
    def get_beamline_par_names(self):
        """Get the current beamline parameter names as a list."""
        # Get the names from the blockserver
        raw = self._get_pv_value(BLOCK_SERVER_PREFIX + "BEAMLINE_PARS", True)
        return dehex_decompress_and_dejson(raw)

    @_blockserver_retry
    def get_runcontrol_settings(self):
        """Get the current run-control settings."""
        raw = self._get_pv_value(BLOCK_SERVER_PREFIX + "GET_RC_PARS", True)
        return dehex_decompress_and_dejson(raw)

    def reload_current_config(self):
        """Reload the current configuration."""
        raw = compress_and_hex("1")
        self._set_pv_value(BLOCK_SERVER_PREFIX + "RELOAD_CURRENT_CONFIG", raw, True)
