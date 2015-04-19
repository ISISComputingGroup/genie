from CaChannel import ca, CaChannel, CaChannelException
from threading import Event

TIMEOUT = 15
CACHE = dict()


class CaChannelWrapper(object):
    @staticmethod
    def _waveform2string(data):
        output = ""
        for i in data:
            if i == 0:
                break
            output += str(unichr(i))
        return output

    @staticmethod
    def set_pv_value(name, value, wait=False, timeout=TIMEOUT):
        """Set the PV to a value.
           When getting a PV value this call should be used, unless there is a special requirement.

        Parameters:
            name - the PV name
            value - the value to set
            wait - wait for the value to be set before returning
        """
        if name not in CACHE.keys():
            chan = CaChannel(name)
            chan.setTimeout(timeout)
            # Try to connect - throws if cannot
            chan.searchw()
            CACHE[name] = chan
        else:
            chan = CACHE[name]
        if wait:
            def putCB(epics_args, user_args):
                user_args[0].set()
            ftype = chan.field_type()
            ecount = chan.element_count()
            event = Event()
            chan.array_put_callback(value, ftype, ecount, putCB, event)
            chan.flush_io()
            # wait in a loop so keyboard interrupt is possible
            while not event.isSet():
                event.wait(1.0)  # use overall timeout somehow? need to make sure it is long enough
        else:
            chan.putw(value)  # putw() flushes send buffer, but doesn't wait for a CA completion callback
                
    @staticmethod
    def get_pv_value(name, to_string=False, timeout=TIMEOUT):
        """Get the current value of the PV"""
        if name not in CACHE.keys():
            chan = CaChannel(name)
            chan.setTimeout(timeout)
            # Try to connect - throws if cannot
            chan.searchw()
            CACHE[name] = chan
        else:
            chan = CACHE[name]
        ftype = chan.field_type()
        if ca.dbr_type_is_ENUM(ftype) or ca.dbr_type_is_CHAR(ftype) or ca.dbr_type_is_STRING(ftype):
            to_string = True
        if to_string:
            if ca.dbr_type_is_ENUM(ftype) or ca.dbr_type_is_STRING(ftype):
                value = chan.getw(ca.DBR_STRING)
            else:
                # If we get a numeric using ca.DBR_CHAR the value still comes back as a numeric
                # In other words, it does not get cast to char
                value = chan.getw(ca.DBR_CHAR)
            # Could see if the element count is > 1 instead
            if isinstance(value, list):
                return CaChannelWrapper._waveform2string(value)
            else:
                return str(value)
        else:
            return chan.getw()

    @staticmethod
    def pv_exists(name):
        """See if the PV exists"""
        try:
            chan = CaChannel(name)
            # Try to connect - throws if cannot
            chan.searchw()
            return True
        except:
            return False
