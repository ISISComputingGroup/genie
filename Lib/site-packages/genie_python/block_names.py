import zlib
from keyword import iskeyword
from threading import RLock, Timer

from .channel_access_exceptions import UnableToConnectToPVException
from .genie_blockserver import BLOCK_SERVER_PREFIX, PV_BLOCK_NAMES
from .genie_cachannel_wrapper import CaChannelWrapper
from .utilities import dehex_decompress_and_dejson

DELAY_BEFORE_RETRYING_BLOCK_NAMES_PV_ON_FAIL = 30.0


class BlockNamesManager:
    """
    Manager for a blocks name object. It makes sure that the blocks it contains are updated
    """

    def __init__(
        self,
        block_names,
        delay_before_retry_add_monitor=DELAY_BEFORE_RETRYING_BLOCK_NAMES_PV_ON_FAIL,
    ):
        """
        Constructor.
        :param block_names: the block name instance that this manger is managing
        :param delay_before_retry_add_monitor: if the block names pv doesn't exist on start the delay before retrying
        """
        self._block_names = block_names
        self._cancel_monitor_fn = None
        self._delay_before_retry_add_monitor = delay_before_retry_add_monitor
        self._timer = None
        self._pv_name = None
        # lock used to access _timer or _pv_name
        self.pv_name_lock = RLock()

    def update_prefix(self, pv_prefix):
        """
        Update the instrument prefix that the manager is using if it has changed
        :param pv_prefix: new pv prefix
        """

        with self.pv_name_lock:
            new_name = "{}{}{}".format(pv_prefix, BLOCK_SERVER_PREFIX, PV_BLOCK_NAMES)
            if new_name != self._pv_name:
                self._pv_name = new_name
                if self._timer is None:
                    self._timer = Timer(0, self._add_monitor)
                    self._timer.setDaemon(True)
                    self._timer.start()

    def _add_monitor(self):
        """
        Add a monitor to the block names pv if it is not already monitored, then reschedule task to add monitor. If the
        pv is monitored don't run.
        """

        # Get PV we should monitor and check whether we need to add new monitor if so cancel old monitor
        with self.pv_name_lock:
            self._timer = None
            # not monitoring the correct pv
            if self._cancel_monitor_fn is not None:
                self._cancel_monitor_fn()

            # Add new monitor if successful then record monitored pv and pull first value, otherwise do nothing
            try:
                self._cancel_monitor_fn = CaChannelWrapper.add_monitor(
                    self._pv_name, self._update_block_names, to_string=True
                )
                self._update_block_names(
                    CaChannelWrapper.get_pv_value(self._pv_name, to_string=True), None, None
                )
            except UnableToConnectToPVException:
                # Schedule next add monitor if needed; i.e. a old pv-prefix change was slower the the last pv-prefix
                # and so we are monitoring the wrong pv.
                self._timer = Timer(self._delay_before_retry_add_monitor, self._add_monitor)
                self._timer.setDaemon(True)
                self._timer.start()

    def _update_block_names(self, value, _, _1):
        """
        Update the block names from a pv
        Args:
            :param value: new value of block names pv
            :param _(CaChannel._ca.AlarmSeverity): severity of any alarm (not used but passed in by monitor)
            :param _1(CaChannel._ca.AlarmCondition): status of the alarm (not used but passed in by monitor)
        """
        # remove old blocks
        for block_name in list(self._block_names.__dict__.keys()):
            delattr(self._block_names, block_name)

        # add new block as attributes to class
        try:
            block_names = dehex_decompress_and_dejson(value)
            for name in block_names:
                attribute_name = name
                if iskeyword(attribute_name):
                    attribute_name = "{}__".format(attribute_name)
                setattr(self._block_names, attribute_name, name)
        except (zlib.error, ValueError, TypeError):
            # if we can not decode the blocks then just pass
            pass


class BlockNames:
    """
    Hold names of the current blocks in config. If block is requested which does not appear in the current config
    block name returned but message printed about it.
    """

    def __getattr__(self, attr):
        """
        If an attribute is not set then return name requested
        :param attr: attribute name
        :return: block name, which is the same as the attribute
        """
        # don't mask not having methods starting with underscore all blocks start with a
        # letter, e.g. ipython console calls __wrapper__ to check it is not a wrapper
        if attr.startswith("_"):
            raise AttributeError()
        print("WARNING: Block name {} not found, it may not exist".format(attr))
        if attr.endswith("__") and iskeyword(attr[:-2]):
            return str(attr[:-2])
        return attr
