import six
from CaChannel import ca, CaChannel, CaChannelException
from threading import Event
from utilities import waveform_to_string
from channel_access_exceptions import UnableToConnectToPVException, InvalidEnumStringException, ReadAccessException, \
    WriteAccessException

TIMEOUT = 15         # Default timeout for PV set/get
EXIST_TIMEOUT = 3    # Separate smaller timeout for pv_exists() and searchw() operations
CACHE = {}


class CaChannelWrapper(object):
    @staticmethod
    def putCB(epics_args, user_args):
        """
        Callback used for setting PV values.

        Args:
            epics_args (tuple): Contains the results of the action.
            user_args (tuple): Contains any extra arguments supplied to the call.

        Returns:
            None.
        """
        user_args[0].set()

    @staticmethod
    def set_pv_value(name, value, wait=False, timeout=TIMEOUT):
        """
        Set the PV to a value.

        When getting a PV value this call should be used, unless there is a special requirement.

        Args:
            name (string): The PV name.
            value: The value to set.
            wait (bool, optional): Wait for the value to be set before returning.
            timeout (optional): How long to wait for the PV to connect etc.

        Returns:
            None.

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
            WriteAccessException: If write access is denied.
            InvalidEnumStringException: If the PV is an enum and the string value supplied is not a valid enum value.
        """
        if name in CACHE.keys() and CACHE[name].state() == ca.cs_conn:
            chan = CACHE[name]
        else:
            chan = CaChannel(name)
            chan.setTimeout(EXIST_TIMEOUT)
            # Try to connect - throws if cannot
            try:
                CaChannelWrapper.connect_to_pv(chan)
            except UnableToConnectToPVException as e:
                raise e
            CACHE[name] = chan
        chan.setTimeout(timeout)

        # Validate user input and format accordingly for mbbi/bi records
        value = CaChannelWrapper.check_for_enum_value(value, chan, name)

        if not chan.write_access():
            raise WriteAccessException(name)
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
            # Write value to PV, or produce error
            chan.putw(value)

    @staticmethod
    def get_pv_value(name, to_string=False, timeout=TIMEOUT):
        """
        Get the current value of the PV.

        Args:
            name (name): The PV.
            to_string (bool, optional): Whether to convert the value to a string.
            timeout (optional): How long to wait for the PV to connect etc.

        Returns:
            The PV value.

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
            ReadAccessException: If read access is denied.
        """
        if name in CACHE.keys() and CACHE[name].state() == ca.cs_conn:
            chan = CACHE[name]
        else:
            chan = CaChannel(name)
            chan.setTimeout(EXIST_TIMEOUT)
            # Try to connect - throws if cannot
            try:
                CaChannelWrapper.connect_to_pv(chan)
            except UnableToConnectToPVException as e:
                raise e
            CACHE[name] = chan
        chan.setTimeout(timeout)
        if not chan.read_access():
            raise ReadAccessException(name)
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
        """
        See if the PV exists.

        Args:
            name (string): The PV name.
            timeout(optional): How long to wait for the PV to "appear".

        Returns:
            True if exists, otherwise False.
        """
        if name in CACHE.keys() and CACHE[name].state() == ca.cs_conn:
            return True
        else:
            chan = CaChannel(name)
            chan.setTimeout(timeout)
            try:
                CaChannelWrapper.connect_to_pv(chan)
            except UnableToConnectToPVException:
                return False
            CACHE[name] = chan
            return True

    @staticmethod
    def connect_to_pv(ca_channel):
        """
        Connects to the PV.

        Args:
            ca_channel (CaChannel): The channel to connect to.

        Returns:
            None.

        Raises:
            UnableToConnectToPVException: If cannot connect to PV.
        """
        event = Event()
        try:
            ca_channel.search_and_connect(None, CaChannelWrapper.putCB, event)
        except CaChannelException as e:
            raise UnableToConnectToPVException(ca_channel.name(), e)

        interval = 0.1
        time_elapsed = 0.0
        timeout = ca_channel.getTimeout()

        while not event.is_set() and time_elapsed <= timeout:
            ca_channel.pend_event(interval)
            time_elapsed += interval
        if not event.is_set():
            raise UnableToConnectToPVException(ca_channel.name(), "Connection timeout")

    @staticmethod
    def check_for_enum_value(value, chan, name):
        """
        Check for string input for MBBI/BI records and replace with the equivalent index value.

        Args:
            value: The PV value.
            chan (CaChannel): The channel access channel.
            name (string): The name of the channel.

        Returns:
            Index value of enum, if the record is mbbi/bi. Otherwise, returns unmodified value.

        Raises:
            InvalidEnumStringException: If the string supplied is not a valid enum value.
        """
        # If PV is MBBI/BI type, search list of enum values and iterate to find a match
        # Use six to check string type as it works for Python 2 and 3.
        if ca.dbr_type_is_ENUM(chan.field_type()) and isinstance(value, six.string_types):
            chan.array_get(ca.DBR_CTRL_ENUM)
            chan.pend_io()
            channel_properties = chan.getValue()
            for index, enum_value in enumerate(channel_properties["pv_statestrings"]):
                if enum_value.lower() == value.lower():
                    # Replace user input with enum index value
                    return index
            # If the string entered isn't valid then throw
            raise InvalidEnumStringException(name, channel_properties["pv_statestrings"])

        return value
