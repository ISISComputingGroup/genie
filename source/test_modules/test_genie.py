# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
from __future__ import absolute_import
import os
import unittest
from genie_python import genie
from genie_python import genie_simulate
from genie_python.genie_waitfor import WaitForController
from mock import MagicMock
from contextlib import contextmanager

import genie
from mock import MagicMock

class TestGenie(unittest.TestCase):
    def setUp(self):
        genie._exceptions_raised = True

    def tearDown(self):
        pass

    def test_GIVEN_no_script_WHEN_load_script_THEN_return_None(self):
        # Arrange

        # Act
        result = genie.load_script(None)

        # Assert
        self.assertIsNone(result)

    def test_GIVEN_error_script_WHEN_load_script_THEN_error(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error.py")

        # Act
        self.assertRaises(Exception, genie.load_script, script)

    def test_GIVEN_valid_script_WHEN_load_script_THEN_can_call_script(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "valid.py")

        # Act
        genie.load_script(script)

        # Assert
        self.assertTrue(genie.valid())

    def test_GIVEN_valid_script_WHEN_load_script_THEN_can_import_from_script_directory(self):
        # Arrange
        script = os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts"), "valid.py")

        # Act
        genie.load_script(script)

        # Assert
        self.assertTrue(genie.check_import())

    def test_GIVEN_script_checker_error_WHEN_load_script_THEN_error(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error_for_script_checker.py")

        # Act
        self.assertRaises(Exception, genie.load_script, script)

    def test_GIVEN_script_checker_error_WHEN_load_script_without_script_checker_THEN_ok(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error_for_script_checker.py")

        # Act
        genie.load_script(script, check_script=False)

    def test_WHEN_seconds_negative_THEN_waitfor_time_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_time(seconds=-1)

    def test_WHEN_minutes_negative_THEN_waitfor_time_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_time(minutes=-1)

    def test_WHEN_hours_negative_THEN_waitfor_time_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_time(hours=-1)

    def test_WHEN_time_is_0_seconds_THEN_waitfor_time_returns(self):
        genie.waitfor_time(seconds=0)

    def test_WHEN_time_is_0_minutes_THEN_waitfor_time_returns(self):
        genie.waitfor_time(minutes=0)

    def test_WHEN_time_is_0_hours_THEN_waitfor_time_returns(self):
        genie.waitfor_time(hours=0)

    def test_WHEN_time_is_0_string_THEN_waitfor_time_returns(self):
        genie.waitfor_time(time="00:00:00")

    def test_WHEN_raw_frames_negative_THEN_waitfor_raw_frames_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_raw_frames(raw_frames=-1)

    def test_WHEN_raw_frames_is_0_THEN_waitfor_raw_frames_returns(self):
        genie.waitfor_raw_frames(raw_frames=0)

    def test_WHEN_frames_negative_THEN_waitfor_frames_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_frames(frames=-1)

    def test_WHEN_frames_is_0_THEN_waitfor_frames_returns(self):
        genie.waitfor_frames(frames=0)


    def test_WHEN_raw_frames_is_0_THEN_waitfor_returns(self):
        genie.waitfor(raw_frames=0)


    def test_WHEN_frames_is_0_THEN_waitfor_returns(self):
        genie.waitfor(frames=0)

    def test_WHEN_input_None_THEN_waitfor_uamps_returns(self):
        genie.waitfor_uamps(None)

    def test_GIVEN_frames_less_than_2_power_31_WHEN_reported_frames_increasing_THEN_waitfor_frames_waits_until_reported_frames_equals_requested_frames(self):
        frames = 5000
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(side_effect=[frames - 1, frames, frames + 1])
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 2)

    def test_GIVEN_frames_greater_than_2_power_31_WHEN_reported_frames_increasing_THEN_waitfor_frames_waits_until_reported_frames_equals_requested_frames(self):
        frames = 2 ** 31
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(side_effect=[frames - 1, frames, frames + 1])
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 2)

    def test_GIVEN_frames_less_than_2_power_31_WHEN_reported_frames_increasing_skips_requested_THEN_waitfor_frames_waits_until_next_reported_frames_equals_above_requested_frames(self):
        frames = 5000
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(side_effect=[frames - 2, frames - 1, frames + 1, frames + 2])
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 3)

    def test_GIVEN_frames_greater_than_2_power_31_WHEN_reported_frames_increasing_skips_requested_THEN_waitfor_frames_waits_until_next_reported_frames_equals_above_requested_frames(self):
        frames = 2 ** 31
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(side_effect=[frames - 2, frames - 1, frames + 1, frames + 2])
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 3)

    @contextmanager
    def _mock_get_blocks(self, blocks):
        oldapi = getattr(genie, "__api")  # Have to use getattr and setattr because of the name mangling
        setattr(genie, "__api", MagicMock(get_blocks=lambda: blocks))
        yield
        setattr(genie, "__api", oldapi)

    def test_WHEN_waitfor_is_given_a_valid_block_as_a_keyword_argument_THEN_no_exception_raised(self):
        with self._mock_get_blocks(["blockname"]):
            genie.waitfor(blockname=5)

    def test_WHEN_waitfor_is_given_a_non_existent_block_as_a_keyword_argument_THEN_exception_raised(self):
        with self._mock_get_blocks([]), self.assertRaises(ValueError):
            genie.waitfor(blockname=5)
