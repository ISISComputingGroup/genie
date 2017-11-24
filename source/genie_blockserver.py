from __future__ import absolute_import
import json
from .utilities import compress_and_hex, dehex_and_decompress, waveform_to_string
import six


class BlockServer(object):
    __blockserver_prefix = "CS:BLOCKSERVER:"
    
    def __init__(self, api):
        self.api = api
        
    def _get_pv_value(self, pv, as_string=False):
        """Just a convenient wrapper for calling the api's get_pv_value method"""
        return self.api.get_pv_value(self.api.prefix_pv_name(pv), as_string)
        
    def _set_pv_value(self, pv, value, wait=False):
        """Just a convenient wrapper for calling the api's set_pv_value method"""
        return self.api.set_pv_value(self.api.prefix_pv_name(pv), value, wait)
        
    def get_block_names(self):
        """Get the names of all the blocks."""
        raw = self._get_pv_value(self.__blockserver_prefix + "BLOCKNAMES", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def get_sample_par_names(self):
        """Get the current sample parameter names as a list."""
        # Get the names from the blockserver
        raw = self._get_pv_value(self.__blockserver_prefix + "SAMPLE_PARS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def get_beamline_par_names(self):
        """Get the current beamline parameter names as a list."""
        # Get the names from the blockserver
        raw = self._get_pv_value(self.__blockserver_prefix + "BEAMLINE_PARS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def get_runcontrol_settings(self):
        """Get the current run-control settings."""
        raw = self._get_pv_value(self.__blockserver_prefix + "GET_RC_PARS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def get_current_block_values(self):
        """Get the cache values for the blocks."""
        raw = self._get_pv_value(self.__blockserver_prefix + "BLOCKVALUES", True)
        raw = dehex_and_decompress(raw)
        blks = json.loads(raw)
        # Convert any char waveforms into correct format
        for bn, bv in six.iteritems(blks):
            if isinstance(bv[0], list) and bv[4] == "CHAR":
                bv[0] = waveform_to_string(bv[0])
        return blks

    def reload_current_config(self):
        """Reload the current configuration."""
        raw = compress_and_hex("1")
        self._set_pv_value(self.__blockserver_prefix + "RELOAD_CURRENT_CONFIG", raw, True)