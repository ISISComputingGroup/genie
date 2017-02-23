class UnableToConnectToPVException(Exception):
    def __init__(self, pv_name):
        super(UnableToConnectToPVException, self).__init__("Unable to find PV %s" % pv_name)
