"""
Useful and slightly more explicit exceptions that can be thrown.
In general catch the super class of these.
"""


class UnableToConnectToPVException(IOError):
    """
    The system is unable to connect to a PV for some reason.
    """

    def __init__(self, pv_name: str, err: str) -> None:
        super(UnableToConnectToPVException, self).__init__(
            f"Unable to connect to PV {pv_name}: {err}"
        )


class InvalidEnumStringException(KeyError):
    """
    The enum string that is trying to be set is not listed in the pv.
    """

    def __init__(self, pv_name: str, valid_states: str) -> None:
        super(InvalidEnumStringException, self).__init__(
            f"Invalid string value entered for {pv_name}. Valid strings are {valid_states}"
        )


class ReadAccessException(IOError):
    """
    PV exists but its value is unavailable to read.
    """

    def __init__(self, pv_name: str) -> None:
        super(ReadAccessException, self).__init__(f"Read access denied for PV {pv_name}")


class WriteAccessException(IOError):
    """
    PV was written to but does not allow writes.
    """

    def __init__(self, pv_name: str) -> None:
        super(WriteAccessException, self).__init__(f"Write access denied for PV {pv_name}")
