import os


class BlockServer(object):    
    def __init__(self, session):
        self.session = session

    def get_block_names(self):
        blocks = self.get_dae_mon_data()
        names = []
        for b in blocks:
            names.append(b[0])
        return names

    def get_dae_mon_data(self):
        """Gets the raw data from the DAE Monitor VI."""
        return self.session.getLabviewVar("C:\LabVIEW Modules\dae\monitor\dae_monitor.vi", "Parameter details")

    def get_sample_par_names(self):
        """Get the current sample parameter names as a list."""
        return self.session.getSampleParameterNames()

    def get_beamline_par_names(self):
        """Get the current beamline parameter names as a list."""
        return self.session.getBeamlineParameterNames()

    def get_runcontrol_settings(self, name):
        raw = self.get_raw_block_details(name)
        if raw is not None:
            rc_vals = dict()
            if raw[7] == 1:
                rc_vals["ENABLE"] = True
            else:
                rc_vals["ENABLE"] = False
            rc_vals["LOW"] = raw[8]
            rc_vals["HIGH"] = raw[9]
            return rc_vals
        
    def get_raw_block_details(self, name):
        """Gets the raw data for a specified block from the DAE Monitor VI."""
        blocks = self.get_dae_mon_data()
        for b in blocks:
            # Ignore case
            if b[0].lower() == name.lower():
                return b
        return None
        
    def set_raw_block_details(self, data):
        """Sets the raw data for a specified block in the DAE Monitor VI."""
        blocks = self.get_dae_mon_data()
        newdata = []
        for b in blocks:
            # Ignore case
            if b[0] == data[0]:
                newdata.append(data)
            else:
                newdata.append(b)
        self.session.setLabviewVar("C:\LabVIEW Modules\dae\monitor\dae_monitor.vi", "Parameter details", newdata)
        
    def get_labview_var(self, vi, control):
        """Get the value of a control on a LabVIEW VI.
        
        Parameters:
            vi - the name of VI (path optional)
            control - the control to read
    
        EXAMPLE: getting the synchrotron beam current from the beam logger VI
        ans = getlabviewvar("c:\\Labview modules\\Beam Logger\\beam logger.vi", "Beam Current")
        """
        vi = self._fix_filepath(vi)
        if not "\\" in vi:
            # Not using fullpath
            vi = self._get_vi_fullpath(vi)
        result = self.session.getLabviewVar(vi, control)
        if result is None:
            raise NameError("Could not get value. Are the VI and control names correct?")
        else:
            return result
            
    def set_labview_var(self, vi, control, value):
        """Set the value of a control on a LabVIEW VI.
        
        Parameters:
            vi - the name of VI (path optional)
            control - the control to set
            value - the new value
        
        EXAMPLE: setting a control on a generic VI
        setlabviewvar("c:\\Labview modules\\generic.vi", "Numeric Control", 123)
        """
        vi = self._fix_filepath(vi)
        if not "\\" in vi:
            # Not using fullpath
            vi = self._get_vi_fullpath(vi)
        try:
            self.session.setLabviewVar(vi, control, value)
        except:
            raise NameError("Could not set value. Are the VI and control names correct?")
            
    def _fix_filepath(self, path):
        """Replaces any escaped characters and any backslashes"""
        path = path.replace('\t', '\\t')
        path = path.replace('\a', '\\a')
        path = path.replace('\n', '\\n')
        path = path.replace('\r', '\\r')
        path = path.replace('\b', '\\b')
        path = path.replace('\\\\', '\\')
        return path    
        
    def _get_all_vi_fullnames(self):
        """Gets the fullpaths of all the VIs currently loaded."""
        return self.session.getViNames()
        
    def _get_vi_fullpath(self, vi):
        """Get the fullpath from just the VI name."""
        viname = os.path.basename(vi).lower()
        names = self._get_all_vi_fullnames()
        for name in names:
            if os.path.basename(name).lower() == viname:
                return name
        return None
        
    def set_runcontrol(self, name, value):
        if value != 0:
            value = 1
        else:
            value = 0       
        settings = self.get_raw_block_details(name)
        newsettings = []
        for s in settings:
            newsettings.append(s)
        newsettings[7] = value
        self.set_raw_block_details(newsettings)
        
    def set_runcontrol_low(self, name, value):
        settings = self.get_raw_block_details(name)
        newsettings = []
        for s in settings:
            newsettings.append(s)
        newsettings[8] = value
        self.set_raw_block_details(newsettings)
        
    def set_runcontrol_high(self, name, value):
        settings = self.get_raw_block_details(name)
        newsettings = []
        for s in settings:
            newsettings.append(s)
        newsettings[9] = value
        self.set_raw_block_details(newsettings)

