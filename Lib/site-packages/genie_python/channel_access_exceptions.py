"""
Useful and slightly more explit exceptions that can be thrown. In general catch the super class of these.
"""


class UnableToConnectToPVException(IOError):
    """
    The system is unable to connect to a PV for some reason.
    """

    def __init__(self, pv_name, err):
        super(UnableToConnectToPVException, self).__init__(
            "Unable to connect to PV {0}: {1}".format(pv_name, err)
        )


class InvalidEnumStringException(KeyError):
    """
    The enum string that is trying to be set is not listed in the pv.
    """

    def __init__(self, pv_name, valid_states):
        super(InvalidEnumStringException, self).__init__(
            "Invalid string value entered for {}. Valid strings are {}".format(
                pv_name, valid_states
            )
        )


class ReadAccessException(IOError):
    """
    PV exists but its value is unavailable to read.
    """

    def __init__(self, pv_name):
        super(ReadAccessException, self).__init__("Read access denied for PV {}".format(pv_name))


class WriteAccessException(IOError):
    """
    PV was written to but does not allow writes.
    """

    def __init__(self, pv_name):
        super(WriteAccessException, self).__init__("Write access denied for PV {}".format(pv_name))
