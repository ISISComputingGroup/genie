import json
from utilities import compress_and_hex, dehex_and_decompress


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
        raw = self._get_pv_value(self.__blockserver_prefix + "BLOCKNAMES", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def get_block_groups(self):
        raw = self._get_pv_value(self.__blockserver_prefix + "GROUPS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def get_iocs(self):
        raw = self._get_pv_value(self.__blockserver_prefix + "IOCS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)
        
    def get_config_iocs(self):
        raw = self._get_pv_value(self.__blockserver_prefix + "CONFIG_IOCS", True)
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
        raw = self._get_pv_value(self.__blockserver_prefix + "GET_RC_PARS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)
        
    def add_block(self, blockname, pvname, **kwargs):
        """Adds a block to BlockServer.

        Parameters:
            blockname - the name for the block (don't include prefix)
            pvname - the associated PV's name (include prefix)
            group - the group to put the block in [optional]
            local - is the PV local to the machine [optional]
            visible - whether the block should be visible in the GUI [optional]
            save_rc - whether the run-control settings are saved to the configuration [optional]
        """
        data = {"name": blockname, 'read_pv': pvname}
        # The blockserver expects a list
        data = [dict(data.items() + kwargs.items())]
        self._set_pv_value(self.__blockserver_prefix + "ADD_BLOCKS", compress_and_hex(json.dumps(data)), True)        
        # Check for an error
        res = self._get_pv_value(self.__blockserver_prefix + "ADD_BLOCKS", True)
        res = json.loads(dehex_and_decompress(res))
        if res != "OK":
            raise Exception(res)
            
    def remove_block(self, blockname):
        """Removes a block from Blockserver.
        
        Parameters:
            blockname - the name of the block (don't include prefix)
        """
        # The blockserver expects a list 
        data = compress_and_hex(json.dumps([blockname]))
        self._set_pv_value(self.__blockserver_prefix + "REMOVE_BLOCKS", data, True) 
        # Check for an error
        res = self._get_pv_value(self.__blockserver_prefix + "REMOVE_BLOCKS", True)
        res = json.loads(dehex_and_decompress(res))
        if res != "OK":
            raise Exception(res)
            
    def action_block_changes(self):
        """Restarts the blocks gateway and block archive"""
        self._set_pv_value(self.__blockserver_prefix + "ACTION_CHANGES", compress_and_hex(json.dumps("action")), True) 
        # Check for an error
        res = self._get_pv_value(self.__blockserver_prefix + "ACTION_CHANGES", True)
        res = json.loads(dehex_and_decompress(res))
        if res != "OK":
            raise Exception(res)
            
    def get_config_name(self):
        """Get the name of the current configuration."""
        raw = self._get_pv_value(self.__blockserver_prefix + "CONFIG", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)

    def load_config(self, name):
        """Load a configuration.
        
        Parameters:
            name - the name of the configuration to load
        """
        data = compress_and_hex(json.dumps(name))
        self._set_pv_value(self.__blockserver_prefix + "LOAD_CONFIG", data, True)
        # Check for an error
        res = self._get_pv_value(self.__blockserver_prefix + "LOAD_CONFIG", True)
        res = json.loads(dehex_and_decompress(res))
        if res != "OK":
            raise Exception(res)

    def get_configs(self):
        raw = self._get_pv_value(self.__blockserver_prefix + "CONFIGS", True)
        raw = dehex_and_decompress(raw)
        return json.loads(raw)