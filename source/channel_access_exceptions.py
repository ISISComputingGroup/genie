class UnableToConnectToPVException(Exception):
    def __init__(self, pv_name, err):
        super(UnableToConnectToPVException, self).__init__("Unable to connect to PV {0}: {1}".format(pv_name, err))


class InvalidEnumStringException(Exception):
    def __init__(self, pv_name, valid_states):
        super(InvalidEnumStringException, self).__init__(
            "Invalid string value entered for {}. Valid strings are {}".format(pv_name, valid_states))


class ReadAccessException(Exception):
    def __init__(self, pv_name):
        super(ReadAccessException, self).__init__("Read access denied for PV {}".format(pv_name))


class WriteAccessException(Exception):
    def __init__(self, pv_name):
        super(WriteAccessException, self).__init__("Write access denied for PV {}".format(pv_name))