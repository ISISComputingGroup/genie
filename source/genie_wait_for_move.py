# encoding: UTF-8

"""Waits until the supplied process variable returns 'done'.
Allows motors to complete their motion fully before proceeding."""

# If you include db/motorUtil.db and call motorUtilInit(“pv prefix”) from your IOC you get 3 PVs defined:
# $(P)alldone, $(P)allstop, $(P)moving which cover all motors in that IOC.
# The “allstop” PV is automatically reset after the stop command has been issued to all motors,
# “alldone” indicates when any motion has completed and “moving” gives a count of moving motors.

from time import sleep


class WaitForMoveController(object):
    def __init__(self, api, motion_pv):
        self._api = api
        self._motion_pv = motion_pv
        self.__polling_delay = 0.01
        self.__wait_succeeded = False

    def wait(self, timeout=None):
        """Wait for motor motion to complete fully, with an optional starting timeout in seconds.
        If the motion does not start within the specified timeout then an error is thrown"""

        #Pause very briefly to avoid any "double move" that may occur when multiple motors are moved 
        # and one of the motors is sent to its current position
        sleep(0.01)

        # If not already moving then wait for up to "timeout" seconds for a move to start
        self.wait_for_start(timeout)

        while self.moving():
            sleep(0.01)

    def wait_for_start(self, timeout):
        if timeout is None:
            return

        if timeout < 0:
            raise Exception("Timeout must not be negative")

        polling_delay = min(timeout, self.__polling_delay)
        max_periods = timeout/polling_delay
        period = 0
        while not self.moving():
            sleep(polling_delay)
            period += 1
            if period >= max_periods:
                break

    def moving(self):
        return self._api.get_pv_value(self._motion_pv) != 0