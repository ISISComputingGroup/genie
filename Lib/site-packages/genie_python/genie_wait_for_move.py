# encoding: UTF-8

"""Waits until the supplied process variable returns 'done'.
Allows motors to complete their motion fully before proceeding."""

# If you include db/motorUtil.db and call motorUtilInit(“pv prefix”) from your IOC you get 3 PVs defined:
# $(P)alldone, $(P)allstop, $(P)moving which cover all motors in that IOC.
# The “allstop” PV is automatically reset after the stop command has been issued to all motors,
# “alldone” indicates when any motion has completed and “moving” gives a count of moving motors.

from __future__ import absolute_import, print_function

import time
from builtins import object

from genie_python.utilities import check_break


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
        self._flag_error_conditions(blocks)

    def _do_wait(self, start_timeout, move_timeout, check_for_move):
        # Pause very briefly to avoid any "double move" that may occur when multiple motors are moved
        # and one of the motors is sent to its current position
        time.sleep(0.01)

        self._missing_blocks = []

        start_timeout, move_timeout = self._check_timeouts_valid(start_timeout, move_timeout)

        # If not already moving then wait for up to "timeout" seconds for a move to start
        self.wait_for_start(start_timeout, check_for_move)

        start = time.time()
        while check_for_move():
            check_break(2)
            time.sleep(self._polling_delay)
            if move_timeout is not None and time.time() - start >= move_timeout:
                self._api.logger.log_info_msg("WAITFOR_MOVE TIMED OUT")
                return
        self._api.logger.log_info_msg("WAITFOR_MOVE MOVE FINISHED")

    def _check_timeouts_valid(self, start_timeout, move_timeout):
        if start_timeout is not None and start_timeout <= 0:
            self._api.logger.log_info_msg(
                "Start time out cannot be less than zero - using default value"
            )
            start_timeout = 0
        if move_timeout is not None and move_timeout <= 0:
            self._api.logger.log_info_msg(
                "Move time out cannot be less than zero - using default value"
            )
            move_timeout = None
        return start_timeout, move_timeout

    def wait_for_start(self, timeout, check_for_move):
        if timeout is not None:
            start = time.time()

            while not check_for_move():
                check_break(2)
                time.sleep(self._polling_delay)
                if time.time() - start >= timeout:
                    self._api.logger.log_info_msg("WAITFOR_MOVE START TIMED OUT")
                    return
            self._api.logger.log_info_msg("WAITFOR_MOVE START FINISHED")

    def _any_motion(self):
        return self._api.get_pv_value(self._motion_pv) != 0

    def _check_specific_motion(self, blocks):
        for block in blocks:
            if block in self._missing_blocks:
                # Skip any missing blocks
                continue
            block_pv = self._api.get_pv_from_block(block)
            # DMOV = 0 when moving
            try:
                moving = self._api.get_pv_value(block_pv + ":DMOV", attempts=1) == 0
            except IOError:
                # Could not find block so don't try it again
                self._api.logger.log_info_msg("WAITFOR_MOVE DISCONNECTED BLOCK: {}".format(block))
                print("Could not connect to block {} so ignoring it".format(block))
                self._missing_blocks.append(block)
                moving = False
            if moving:
                return True

        return False

    def _flag_error_conditions(self, blocks):
        time.sleep(0.5)
        filtered_blocks = self._filter_out_missing_blocks(blocks)

        # Check alarms
        minor, major, invalid = self._api.check_alarms(filtered_blocks)
        for i in major:
            self._api.logger.log_info_msg("WAITFOR_MOVE BLOCK %s IN MAJOR ALARM" % i)
            print("Block %s is in alarm: MAJOR" % i)
        for i in minor:
            self._api.logger.log_info_msg("WAITFOR_MOVE BLOCK %s IN MINOR ALARM" % i)
            print("Block %s is in alarm state: MINOR" % i)

        # Check soft limit violations
        violations = self._api.check_limit_violations(filtered_blocks)
        for i in violations:
            self._api.logger.log_info_msg("WAITFOR_MOVE BLOCK %s HAS SOFT LIMIT VIOLATIONS" % i)
            print("Block %s has soft limit violations" % i)

        # Print missing blocks
        for i in self._missing_blocks:
            self._api.logger.log_info_msg("WAITFOR_MOVE BLOCK %s COULD NOT BE FOUND" % i)
            print("Block %s could not be found" % i)

    def _filter_out_missing_blocks(self, blocks):
        filtered_blocks = []
        for b in blocks:
            if b in self._missing_blocks:
                continue
            filtered_blocks.append(b)
        return filtered_blocks
