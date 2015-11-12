"""Waits until motors complete their motion fully before proceeding."""
from time import sleep
from datetime import timedelta, datetime


class WaitForMoveController(object):
    def __init__(self, api):
        self._api = api
        self._motion_vi = "C:\\LabVIEW Modules\\Drivers\\Galil DMC2280\\Galil - System Functions.llb\\Galil - Table of motor details.vi"
        self._motion_indicator = "In Motion"
        self._polling_delay = 0.01
        self._wait_succeeded = False

    def wait(self, start_timeout=None, move_timeout=None):
        """Wait for motor motion to complete fully, with an optional starting timeout in seconds."""

        # Pause very briefly to avoid any "double move" that may occur when multiple motors are moved
        # and one of the motors is sent to its current position
        sleep(0.01)
        
        if start_timeout is not None and start_timeout <= 0:
            raise Exception("Start timeout must be greater than zero")
            
        if move_timeout is not None and move_timeout <= 0:
            raise Exception("Move timeout must be greater than zero")

        # If not already moving then wait for up to "timeout" seconds for a move to start
        self.wait_for_start(start_timeout)

        max_periods = self._get_timeout_periods(move_timeout)
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
        return self._api.blockserver.get_labview_var(self._motion_vi, self._motion_indicator)