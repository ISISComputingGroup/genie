from CaChannel import ca, CaChannel, CaChannelException
from threading import Event
from utilities import waveform_to_string

TIMEOUT = 15         # default timeout for PV set/get
EXIST_TIMEOUT = 3    # separate smaller timeout for pv_exists() and searchw() operations 
CACHE = dict()


class CaChannelWrapper(object):
    @staticmethod
    def putCB(epics_args, user_args):
        user_args[0].set()

    @staticmethod
    def set_pv_value(name, value, wait=False, timeout=TIMEOUT):
        """Set the PV to a value.
           When getting a PV value this call should be used, unless there is a special requirement.

        Args:
            name - the PV name
            value - the value to set
            wait - wait for the value to be set before returning
        """
        if name in CACHE.keys() and CACHE[name].state() == ca.ch_state.cs_conn:
            chan = CACHE[name]
        else:
            chan = CaChannel(name)
            chan.setTimeout(EXIST_TIMEOUT)
            # Try to connect - throws if cannot
            try:
                CaChannelWrapper.connect_to_pv(chan)
            except Exception as e:
                raise e
            CACHE[name] = chan
        chan.setTimeout(timeout)
        if not chan.write_access():
            raise Exception("Write access denied for PV %s" % name)
        if wait:
            ftype = chan.field_type()
            ecount = chan.element_count()
            event = Event()
            chan.array_put_callback(value, ftype, ecount, CaChannelWrapper.putCB, event)
            # Wait in a loop so keyboard interrupt is possible.
            # Should use overall timeout somehow? need to make sure it is long enough for all requests to complete
            # though did try flush_io() followed by event.wait(1.0) inside the loop, but a send got missed.
            # Looks like pend_event() / poll() is needed
            while not event.isSet():
                chan.pend_event(0.1)
        else:
            # putw() flushes send buffer, but doesn't wait for a CA completion callback
            chan.putw(value)

    @staticmethod
    def get_pv_value(name, to_string=False, timeout=TIMEOUT):
        """Get the current value of the PV"""
        if name in CACHE.keys() and CACHE[name].state() == ca.ch_state.cs_conn:
            chan = CACHE[name]
        else:
            chan = CaChannel(name)
            chan.setTimeout(EXIST_TIMEOUT)
            # Try to connect - throws if cannot
            try:
                CaChannelWrapper.connect_to_pv(chan)
            except Exception as e:
                raise e
            CACHE[name] = chan
        chan.setTimeout(timeout)
        if not chan.read_access():
            raise Exception("Read access denied for PV %s" % name)
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
                return waveform_to_string(value)
            else:
                return str(value)
        else:
            return chan.getw()

    @staticmethod
    def pv_exists(name, timeout=EXIST_TIMEOUT):
        """See if the PV exists"""
        if name in CACHE.keys() and CACHE[name].state() == ca.ch_state.cs_conn:
            return True
        else:
            chan = CaChannel(name)
            chan.setTimeout(timeout)
            try:
                CaChannelWrapper.connect_to_pv(chan)
            except Exception as e:
                print e.message
                return False
            CACHE[name] = chan
            return True

    @staticmethod
    def connect_to_pv(ca_channel):
        event = Event()
        try:
            ca_channel.search_and_connect(None, CaChannelWrapper.putCB, event)

            interval = 0.1
            time_elapsed = 0.0
            timeout = ca_channel.getTimeout()

            while not event.is_set() and time_elapsed <= timeout:
                ca_channel.pend_event(interval)
                time_elapsed += interval
            if not event.is_set():
                raise Exception()
        except:
            raise Exception("Unable to find PV %s" % ca_channel.pvname)
