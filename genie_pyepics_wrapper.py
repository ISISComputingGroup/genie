from epics import caput, ca, dbr


class PyEpicsWrapper(object):

    @staticmethod
    def set_pv_value(name, value, wait=False):
        """Set the PV to a value.
           When getting a PV value this call should be used, unless there is a special requirement.

        Parameters:
            name - the PV name
            value - the value to set
            wait - wait for the value to be set before returning
        """
        caput(name, value, wait=wait)

    @staticmethod
    def get_pv_value(name, to_string=False):
        """Get the current value of the PV"""

        #Use the lowest level ca commands otherwise PyEpics tries to be clever.
        #which slows the "get" down and also creates a subscription that can cause the CPU
        #to max out if it is a fast changing PV such as a spectrum
        chid = ca.create_channel(name)
        connected = ca.connect_channel(chid)
        if not connected:
            raise Exception("Could not connect to channel %s" % name)
        ftype = ca.field_type(chid)
        if ftype == dbr.ENUM or ftype == dbr.CHAR or ftype == dbr.STRING:
            to_string = True
        return ca.get(chid, as_string=to_string)

    @staticmethod
    def pv_exists(name):
        """See if the PV exists"""
        chid = ca.create_channel(name)
        connected = ca.connect_channel(chid)
        return connected