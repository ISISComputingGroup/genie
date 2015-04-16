# encoding: UTF-8

"""Waits until the supplied process variable returns 'done'.
Allows motors to complete their motion fully before proceeding."""

# If you include db/motorUtil.db and call motorUtilInit(“pv prefix”) from your IOC you get 3 PVs defined:
# $(P)alldone, $(P)allstop, $(P)moving which cover all motors in that IOC.
# The “allstop” PV is automatically reset after the stop command has been issued to all motors,
# “alldone” indicates when any motion has completed and “moving” gives a count of moving motors.

from time import sleep
from datetime import timedelta, datetime


class WaitForMoveController(object):
    def __init__(self, api, motion_pv):
        self._api = api
        self._motion_pv = motion_pv
        self._polling_delay = 0.01
        self._wait_succeeded = False

    def wait(self, timeout=None):
        """Wait for motor motion to complete fully, with an optional starting timeout in seconds.
        If the motion does not start within the specified timeout then an error is thrown"""

        # Pause very briefly to avoid any "double move" that may occur when multiple motors are moved
        # and one of the motors is sent to its current position
        sleep(0.01)

        # If not already moving then wait for up to "timeout" seconds for a move to start
        self.wait_for_start(timeout)
        start_time = datetime.now()

        max_periods = self._get_timeout_periods(timeout)
        period = 0

        while self.moving():
            sleep(self._polling_delay)
            period += 1
            if max_periods is not None and period >= max_periods:
                self._api.log_info_msg("WAITFOR_MOVE TIMED OUT")
                return
        self._api.log_info_msg("WAITFOR_MOVE MOVE FINISHED")

    def wait_for_start(self, timeout):
        if timeout is None:
            return

        if timeout < 0:
            raise Exception("Timeout must not be negative")

        max_periods = self._get_timeout_periods(timeout)
        period = 0

        while not self.moving():
            sleep(self._polling_delay)
            period += 1
            if max_periods is not None and period >= max_periods:
                self._api.log_info_msg("WAITFOR_START TIMED OUT")
                return
        self._api.log_info_msg("WAITFOR_START FINISHED")

    def _get_timeout_periods(self, timeout):
        if timeout is None:
            return None
        polling_delay = min(timeout, self._polling_delay)
        return timeout/polling_delay

    def moving(self):
        return self._api.get_pv_value(self._motion_pv) != 0