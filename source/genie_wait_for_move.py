# encoding: UTF-8

"""Waits until the supplied process variable returns 'done'.
Allows motors to complete their motion fully before proceeding."""

# If you include db/motorUtil.db and call motorUtilInit(“pv prefix”) from your IOC you get 3 PVs defined:
# $(P)alldone, $(P)allstop, $(P)moving which cover all motors in that IOC.
# The “allstop” PV is automatically reset after the stop command has been issued to all motors,
# “alldone” indicates when any motion has completed and “moving” gives a count of moving motors.

import time


class WaitForMoveController(object):
    def __init__(self, api, motion_pv):
        self._api = api
        self._motion_pv = motion_pv
        self._polling_delay = 0.02
        self._wait_succeeded = False
        self._missing_blocks = list()

    def wait(self, start_timeout=None, move_timeout=None):
        """Wait for motor motion to complete.

        Args:
            start_timeout (int, optional) : the number of seconds to wait for the movement to begin
            move_timeout (int, optional) : the maximum number of seconds to wait for motion to stop

        If the motion does not start within the specified start_timeout then it will continue as if it did.
        """
        self._do_wait(start_timeout, move_timeout, self._any_motion)

    def wait_specific(self, blocks, start_timeout=None, move_timeout=None):
        """Wait for motor motion to complete on the specified blocks only.

        Args:
            blocks (list) : the names of the blocks to wait for
            start_timeout (int, optional) : the number of seconds to wait for the movement to begin
            move_timeout (int, optional) : the maximum number of seconds to wait for motion to stop

        If the motion does not start within the specified start_timeout then it will continue as if it did
        """
        def check_blocks():
            return self._check_specific_motion(blocks)

        self._do_wait(start_timeout, move_timeout, check_blocks)

        # Check alarms
        minor, major = self._check_alarms(blocks)
        for i in major:
            self._api.log_info_msg("WAITFOR_MOVE BLOCK %s IN MAJOR ALARM" % i)
            print "Block %s is in alarm: MAJOR" % i
        for i in minor:
            self._api.log_info_msg("WAITFOR_MOVE BLOCK %s IN MINOR ALARM" % i)
            print "Block %s is in alarm state: MINOR" % i
        for i in self._missing_blocks:
            self._api.log_info_msg("WAITFOR_MOVE BLOCK %s COULD NOT BE FOUND" % i)
            print "Block %s could not be found" % i

        return minor, major

    def _do_wait(self, start_timeout, move_timeout, check_for_move):
        # Pause very briefly to avoid any "double move" that may occur when multiple motors are moved
        # and one of the motors is sent to its current position
        time.sleep(0.01)

        self._missing_blocks = list()

        start_timeout, move_timeout = self._check_timeouts_valid(start_timeout, move_timeout)

        # If not already moving then wait for up to "timeout" seconds for a move to start
        self.wait_for_start(start_timeout, check_for_move)

        start = time.time()
        while check_for_move():
            time.sleep(self._polling_delay)
            if move_timeout is not None and time.time() - start >= move_timeout:
                self._api.log_info_msg("WAITFOR_MOVE TIMED OUT")
                return
        self._api.log_info_msg("WAITFOR_MOVE MOVE FINISHED")

    def _check_timeouts_valid(self, start_timeout, move_timeout):
        if start_timeout is not None and start_timeout <= 0:
            self._api.log_info_msg("Start time out cannot be less than zero - using default value")
            start_timeout = 0
        if move_timeout is not None and move_timeout <= 0:
            self._api.log_info_msg("Move time out cannot be less than zero - using default value")
            move_timeout = None
        return start_timeout, move_timeout

    def wait_for_start(self, timeout, check_for_move):
        if timeout is None:
            return

        start = time.time()

        while not check_for_move():
            time.sleep(self._polling_delay)
            if time.time() - start >= timeout:
                self._api.log_info_msg("WAITFOR_MOVE START TIMED OUT")
                return
        self._api.log_info_msg("WAITFOR_MOVE START FINISHED")

    def _any_motion(self):
        return self._api.get_pv_value(self._motion_pv) != 0

    def _check_specific_motion(self, blocks):
        for b in blocks:
            if b in self._missing_blocks:
                # Skip any missing blocks
                continue
            name = self._api.correct_blockname(b)
            # DMOV = 0 when moving
            try:
                moving = self._api.get_pv_value(name + ".DMOV", attempts=1) == 0
            except:
                # Could not find block so don't try it again
                self._api.log_info_msg("WAITFOR_MOVE DISCONNECTED BLOCK: %s" % b)
                print "\nCould not connect to block %s so ignoring it" % b
                self._missing_blocks.append(b)
                moving = False
            if moving:
                return True

        return False

    def _check_alarms(self, blocks):
        minor = list()
        major = list()
        for b in blocks:
            if b in self._missing_blocks:
                # Skip any missing blocks
                continue
            name = self._api.correct_blockname(b)
            # Alarm states are: NO_ALARM, MINOR, MAJOR
            try:
                alarm_state = self._api.get_pv_value(name + ".SEVR", attempts=1)
                if alarm_state == "MINOR":
                    minor.append(b)
                elif alarm_state == "MAJOR":
                    major.append(b)
            except:
                # Could not get value
                self._api.log_info_msg("WAITFOR_MOVE COULD NOT GET ALARM STATE FOR BLOCK: %s" % b)
                print "\nCould not get alarm state for block %s" % b
        return minor, major
