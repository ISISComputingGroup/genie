class UnableToConnectToPVException(Exception):
    def __init__(self, pv_name, err):
        super(UnableToConnectToPVException, self).__init__("Unable to connect to PV {0}: {1}".format(pv_name, err))
