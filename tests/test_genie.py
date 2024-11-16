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
from __future__ import absolute_import, print_function

import os
import unittest
from datetime import datetime, timedelta
from io import StringIO

from hamcrest import assert_that, contains_exactly, has_length, is_
from mock import MagicMock, call, patch

import genie_python.genie_api_setup
from genie_python import genie
from genie_python.channel_access_exceptions import ReadAccessException, UnableToConnectToPVException
from genie_python.genie_waitfor import (
    WaitForController,
    WaitForControllerConnectedState,
    WaitForControllerExceptionContext,
)


class TestGenie(unittest.TestCase):
    def setUp(self):
        genie.set_instrument(None, import_instrument_init=False)
        genie_python.genie_api_setup._exceptions_raised = True

    def test_GIVEN_error_script_WHEN_load_script_THEN_error(self):
        # Arrange
        script = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error.py"
        )

        # Act
        self.assertRaises(Exception, genie.load_script, script)

    def test_GIVEN_valid_script_WHEN_load_script_THEN_can_call_script(self):
        # Arrange
        script = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "test_scripts", "valid.py"
        )

        # Act
        genie.load_script(script)

        # Assert
        self.assertTrue(genie.valid())

    def test_GIVEN_valid_script_WHEN_load_script_THEN_can_import_from_script_directory(self):
        # Arrange
        script = os.path.join(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts"), "valid.py"
        )

        # Act
        genie.load_script(script)

        # Assert
        self.assertTrue(genie.check_import())

    def test_GIVEN_script_checker_error_WHEN_load_script_THEN_error(self):
        # Arrange
        script = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "test_scripts",
            "error_for_script_checker.py",
        )

        # Act
        self.assertRaises(Exception, genie.load_script, script)

    def test_GIVEN_script_checker_error_WHEN_load_script_without_script_checker_THEN_ok(self):
        # Arrange
        script = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "test_scripts",
            "error_for_script_checker.py",
        )

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

    def test_WHEN_time_is_float_THEN_waitfor_time_returns(self):
        genie.waitfor_time(minutes=0.0000001)

    def test_WHEN_time_is_float_and_negative_THEN_waitfor_time_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_time(minutes=-0.000001)

    def test_WHEN_raw_frames_negative_THEN_waitfor_raw_frames_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_raw_frames(raw_frames=-1)

    @patch("genie_python.genie._genie_api.get_block_names")
    @patch("genie_python.genie._genie_api.waitfor.api.dae.get_raw_frames")
    def test_WHEN_raw_frames_is_0_THEN_waitfor_raw_frames_returns(self, raw_frames, blocks):
        blocks.return_value = []
        raw_frames.return_value = 0.1
        genie.waitfor_raw_frames(raw_frames=0)

    def test_WHEN_frames_negative_THEN_waitfor_frames_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_frames(frames=-1)

    @patch("genie_python.genie._genie_api.get_block_names")
    @patch("genie_python.genie._genie_api.waitfor.api.dae.get_good_frames")
    def test_WHEN_frames_is_0_THEN_waitfor_frames_returns(self, good_frames, blocks):
        blocks.return_value = []
        good_frames.return_value = 0.1
        genie.waitfor_frames(frames=0)

    @patch("genie_python.genie._genie_api.get_block_names")
    @patch("genie_python.genie._genie_api.waitfor.api.dae.get_raw_frames")
    def test_WHEN_raw_frames_is_0_THEN_waitfor_returns(self, raw_frames, blocks):
        blocks.return_value = []
        raw_frames.return_value = 0.1
        genie.waitfor(raw_frames=0)

    @patch("genie_python.genie._genie_api.get_block_names")
    @patch("genie_python.genie._genie_api.waitfor.api.dae.get_good_frames")
    def test_WHEN_frames_is_0_THEN_waitfor_returns(self, good_frames, blocks):
        blocks.return_value = []
        good_frames.return_value = 0.1
        genie.waitfor(frames=0)

    def test_WHEN_input_None_THEN_waitfor_uamps_returns(self):
        genie.waitfor_uamps(None)

    def test_GIVEN_frames_less_than_2_power_31_WHEN_reported_frames_increasing_THEN_waitfor_frames_waits_until_reported_frames_equals_requested_frames(
        self,
    ):
        frames = 5000
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(side_effect=[frames - 1, frames, frames + 1])
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 2)

    def test_GIVEN_frames_greater_than_2_power_31_WHEN_reported_frames_increasing_THEN_waitfor_frames_waits_until_reported_frames_equals_requested_frames(
        self,
    ):
        frames = 2**31
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(side_effect=[frames - 1, frames, frames + 1])
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 2)

    def test_GIVEN_frames_less_than_2_power_31_WHEN_reported_frames_increasing_skips_requested_THEN_waitfor_frames_waits_until_next_reported_frames_equals_above_requested_frames(
        self,
    ):
        frames = 5000
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(
            side_effect=[frames - 2, frames - 1, frames + 1, frames + 2]
        )
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 3)

    def test_GIVEN_frames_greater_than_2_power_31_WHEN_reported_frames_increasing_skips_requested_THEN_waitfor_frames_waits_until_next_reported_frames_equals_above_requested_frames(
        self,
    ):
        frames = 2**31
        self.api = MagicMock()
        self.api.dae.get_good_frames = MagicMock(
            side_effect=[frames - 2, frames - 1, frames + 1, frames + 2]
        )
        controller = WaitForController(self.api)
        controller.start_waiting(frames=frames)
        self.assertEqual(self.api.dae.get_good_frames.call_count, 3)

    def test_WHEN_mevents_negative_THEN_waitfor_mevents_raises_error(self):
        with self.assertRaises(ValueError):
            genie.waitfor_mevents(mevents=-1)

    @patch("genie_python.genie._genie_api.get_block_names")
    @patch("genie_python.genie._genie_api.waitfor.api.dae.get_mevents")
    def test_WHEN_mevents_is_0_THEN_waitfor_mevents_returns(self, mevents, blocks):
        blocks.return_value = []
        mevents.return_value = 1
        genie.waitfor_mevents(mevents=0)

    def test_GIVEN_mevents_less_than_2_power_31_WHEN_reported_mevents_increasing_THEN_waitfor_mevents_waits_until_reported_mevents_equals_requested_mevents(
        self,
    ):
        mevents = 5000
        self.api = MagicMock()
        self.api.dae.get_mevents = MagicMock(side_effect=[mevents - 1, mevents, mevents + 1])
        controller = WaitForController(self.api)
        controller.start_waiting(mevents=mevents)
        self.assertEqual(self.api.dae.get_mevents.call_count, 2)

    def test_GIVEN_mevents_greater_than_2_power_31_WHEN_reported_mevents_increasing_THEN_waitfor_mevents_waits_until_reported_mevents_equals_requested_mevents(
        self,
    ):
        mevents = 2**31
        self.api = MagicMock()
        self.api.dae.get_mevents = MagicMock(side_effect=[mevents - 1, mevents, mevents + 1])
        controller = WaitForController(self.api)
        controller.start_waiting(mevents=mevents)
        self.assertEqual(self.api.dae.get_mevents.call_count, 2)

    def test_GIVEN_mevents_less_than_2_power_31_WHEN_reported_mevents_increasing_skips_requested_THEN_waitfor_mevents_waits_until_next_reported_mevents_equals_above_requested_mevents(
        self,
    ):
        mevents = 5000
        self.api = MagicMock()
        self.api.dae.get_mevents = MagicMock(
            side_effect=[mevents - 2, mevents - 1, mevents + 1, mevents + 2]
        )
        controller = WaitForController(self.api)
        controller.start_waiting(mevents=mevents)
        self.assertEqual(self.api.dae.get_mevents.call_count, 3)

    def test_GIVEN_mevents_greater_than_2_power_31_WHEN_reported_mevents_increasing_skips_requested_THEN_waitfor_mevents_waits_until_next_reported_mevents_equals_above_requested_mevents(
        self,
    ):
        mevents = 2**31
        self.api = MagicMock()
        self.api.dae.get_mevents = MagicMock(
            side_effect=[mevents - 2, mevents - 1, mevents + 1, mevents + 2]
        )
        controller = WaitForController(self.api)
        controller.start_waiting(mevents=mevents)
        self.assertEqual(self.api.dae.get_mevents.call_count, 3)

    @patch("genie_python.genie._genie_api.waitfor.start_waiting")
    @patch("genie_python.genie._genie_api.get_block_names")
    def test_WHEN_waitfor_is_given_a_valid_block_as_a_keyword_argument_THEN_no_exception_raised_and_waitfor_called(
        self, block_names, start_waiting
    ):
        block_names.return_value = ["blockname"]
        genie.waitfor(blockname=5)
        start_waiting.assert_called_once()

    @patch("genie_python.genie._genie_api.waitfor.start_waiting")
    @patch("genie_python.genie._genie_api.get_block_names")
    def test_WHEN_waitfor_is_given_a_non_existent_block_as_a_keyword_argument_THEN_exception_raised_and_start_waiting_not_called(
        self, block_names, start_waiting
    ):
        block_names.return_value = []
        with self.assertRaises(ValueError):
            genie.waitfor(blockname=5)

    def test_WHEN_change_tables_is_called_with_no_file_paths_THEN_exception_thrown(self):
        self.assertRaises(ValueError, genie.change_tables)

    @patch("sys.stdout", new_callable=StringIO)
    def test_WHEN_waitfor_given_maxwait_and_frames_not_reached_THEN_times_out(self, std_fake_out):
        # Mock pv as disconnected
        api = MagicMock()
        api.dae.get_good_frames.side_effect = UnableToConnectToPVException(
            err="mocked err", pv_name="mocked pv"
        )
        # Set up controller
        controller = WaitForController(api)

        try:
            controller.start_waiting(frames=5000, maxwait=0.1)

            # Check output (get rid of last line as split causes empty string at end)
            output = std_fake_out.getvalue().split("\n")[:-1]

            # One line for waiting for frames, another for the exception and another to say the waitfor has timed out
            self.assertEqual(len(output), 5)
            self.assertEqual("Waiting for 5000 frames [timeout=0.1]", output[1])
            self.assertIn(
                "Exception in waitfor loop: {}".format(UnableToConnectToPVException.__name__),
                output[2],
            )
            self.assertIn("Waitfor timed out", output[3])
        except Exception as e:
            self.fail(
                "start_waiting should catch the exception and continue. Exception: {}".format(e)
            )

    @patch("sys.stdout", new_callable=StringIO)
    def test_WHEN_context_starts_THEN_state_is_connected_and_no_output(self, std_fake_out):
        context = WaitForControllerExceptionContext(None)

        self.assertIsInstance(context._state, WaitForControllerConnectedState)
        # When no output is made StringIO returns empty string
        self.assertEqual(std_fake_out.getvalue(), "")

    @patch("sys.stdout", new_callable=StringIO)
    def test_WHEN_exception_occurs_then_clears_THEN_exception_and_clearance_printed(
        self, std_fake_out
    ):
        context = WaitForControllerExceptionContext(MagicMock())

        context.process_exception(
            UnableToConnectToPVException(err="mocked err", pv_name="mocked pv")
        )
        context.process_exception(None)

        # Check output (get rid of last line as split causes empty string at end)
        output_lines = std_fake_out.getvalue().split("\n")[:-1]

        # One line for exception occurring, one for clearing
        self.assertEqual(len(output_lines), 2)
        # First line should be occurrence of exception
        self.assertIn(
            "Exception in waitfor loop: {}".format(UnableToConnectToPVException.__name__),
            output_lines[0],
        )
        self.assertNotIn("Exception cleared", output_lines[0])
        # Second line should be exception clearing
        self.assertIn("Exception cleared", output_lines[1])
        self.assertNotIn(
            "Exception in waitfor loop: {}".format(UnableToConnectToPVException.__name__),
            output_lines[1],
        )

    @patch("sys.stdout", new_callable=StringIO)
    def test_WHEN_exception_continuously_occurs_for_more_than_15_minutes_THEN_exception_printed_three_times(
        self, std_fake_out
    ):
        number_of_5_minutes = 3
        context = WaitForControllerExceptionContext(MagicMock())

        # Simulate first disconnection
        context.process_exception(
            UnableToConnectToPVException(err="mocked err", pv_name="mocked pv")
        )
        # Simulate 5 minutes passing 3 times
        for i in range(number_of_5_minutes):
            context._state._last_notification_time = datetime.now() - timedelta(minutes=5)
            context.process_exception(
                UnableToConnectToPVException(err="mocked err", pv_name="mocked pv")
            )

        # Check lines contain exception (get rid of last line as split causes empty string at end)
        output_lines = std_fake_out.getvalue().split("\n")[:-1]
        self.assertEqual(len(output_lines), number_of_5_minutes + 1)
        for i in range(len(output_lines)):
            self.assertIn(
                "Exception in waitfor loop: {}".format(UnableToConnectToPVException.__name__),
                output_lines[i],
            )

    @patch("sys.stdout", new_callable=StringIO)
    def test_WHEN_exception_changes_THEN_new_exception_printed(self, std_fake_out):
        context = WaitForControllerExceptionContext(MagicMock())

        # Simulate first disconnection
        context.process_exception(
            UnableToConnectToPVException(err="mocked err", pv_name="mocked pv")
        )
        # Simulate change of exception
        context.process_exception(ReadAccessException(pv_name="mocked pv"))

        # Check lines contain exception (get rid of last line as split causes empty string at end)
        output_lines = std_fake_out.getvalue().split("\n")[:-1]
        # One line for each exception
        self.assertEqual(len(output_lines), 2)
        self.assertIn(
            "Exception in waitfor loop: {}".format(UnableToConnectToPVException.__name__),
            output_lines[0],
        )
        self.assertIn(
            "Exception in waitfor loop: {}".format(ReadAccessException.__name__), output_lines[1]
        )


class TestGenieMockedAPI(unittest.TestCase):
    def setUp(self):
        genie.set_instrument(None, import_instrument_init=False)
        genie_python.genie_api_setup._exceptions_raised = True
        self.old_api = genie._genie_api

        mocked_check_alarms = MagicMock(return_value=([], [], []))
        self.mocked_api = MagicMock(check_alarms=mocked_check_alarms)

        genie._genie_api = self.mocked_api

    def tearDown(self):
        genie._genie_api = self.old_api

    def test_WHEN_cset_is_called_with_string_blockname_THEN_exactly_one_call_to_set_pv_value(self):
        block_name, value = "MY_BLOCK_NAME", 3
        genie.cset(block_name, value)
        self.mocked_api.set_block_value.assert_called_with(
            block_name, value, None, None, None, None
        )

    def test_WHEN_cset_is_called_with_kwarg_syntax_THEN_exactly_one_call_to_set_pv_value(self):
        block_name, value = "MY_BLOCK_NAME", 3
        genie.cset(**{block_name: value})

        self.mocked_api.set_block_value.assert_called_with(
            block_name, value, None, None, None, None
        )

    def test_WHEN_cset_is_called_with_kwarg_syntax_with_multiple_blocks_THEN_exactly_one_call_to_set_multiple_blocks_which_contains_the_blocknames_and_values(
        self,
    ):
        blocks = {
            "MY_BLOCK_NAME": "abc123",
            "ANOTHER_BLOCK": 42,
            "THE_LAST_BLOCK": True,
        }

        genie.cset(**blocks)
        for block_name, value in blocks.items():
            self.mocked_api.set_block_value.assert_any_call(
                block_name, value, None, None, None, None
            )

    def test_WHEN_cset_is_called_with_string_blockname_THEN_exactly_one_call_to_get_alarms(self):
        block_name, value = "MY_BLOCK_NAME", 3
        genie.cset(block_name, value)
        self.mocked_api.check_alarms.assert_called_with((block_name,))

    def test_WHEN_cset_is_called_with_kwarg_syntax_THEN_exactly_one_call_to_get_alarms(self):
        block_name, value = "MY_BLOCK_NAME", 3
        genie.cset(**{block_name: value})
        self.mocked_api.check_alarms.assert_called_with((block_name,))

    def test_WHEN_cset_is_called_with_kwarg_syntax_with_multiple_blocks_THEN_each_block_is_sent_to_check_alarms(
        self,
    ):
        blocks = {
            "MY_BLOCK_NAME": "abc123",
            "ANOTHER_BLOCK": 42,
            "THE_LAST_BLOCK": True,
        }

        genie.cset(**blocks)
        self.assertEqual(self.mocked_api.check_alarms.call_count, len(blocks))
        self.mocked_api.check_alarms.assert_has_calls(
            [call((x,)) for x in list(blocks.keys())], any_order=True
        )

    def test_WHEN_cset_called_with_too_many_arguments_THEN_raises(self):
        self.assertRaises(Exception, genie.cset, 1, 2, 3)

    def test_WHEN_cset_called_with_no_arguments_THEN_raises(self):
        self.assertRaises(Exception, genie.cset)

    def test_WHEN_cset_called_with_run_control_but_no_block_THEN_raises(self):
        self.assertRaises(Exception, genie.cset, runcontrol=True, lowlimit=0, highlimit=1)

    def test_WHEN_cset_called_with_wait_but_no_block_THEN_raises(self):
        self.assertRaises(Exception, genie.cset, wait=True)

    def test_WHEN_cset_called_with_single_non_existant_block_THEN_raises(self):
        self.mocked_api.block_exists = MagicMock(return_value=False)
        self.assertRaises(Exception, genie.cset, "my_block", 1)

    def test_WHEN_cset_called_with_runcontrol_limits_THEN_limits_passed_to_API(self):
        low_limit, high_limit = 3, 10
        genie.cset("my_block", 1, runcontrol=True, lowlimit=low_limit, highlimit=high_limit)
        self.mocked_api.set_block_value.assert_called_with(
            "my_block", 1, True, low_limit, high_limit, None
        )

    def test_WHEN_cset_called_with_wait_THEN_passed_to_API(self):
        genie.cset("my_block", 1, wait=True)
        self.mocked_api.set_block_value.assert_called_with("my_block", 1, None, None, None, True)

    def test_WHEN_cset_called_with_wait_limits_THEN_passed_to_API(self):
        low_limit, high_limit = 3, 10
        genie.cset("my_block", 1, wait=True, lowlimit=low_limit, highlimit=high_limit)
        self.mocked_api.set_block_value.assert_called_with(
            "my_block", 1, None, low_limit, high_limit, True
        )

    def test_WHEN_cset_called_with_wait_and_runcontrol_THEN_raises(self):
        self.assertRaises(Exception, genie.cset, "my_block", 1, wait=True, runcontrol=True)

    def test_WHEN_cset_called_as_dict_with_wait_and_runcontrol_THEN_raises(self):
        self.assertRaises(Exception, genie.cset, block=1, wait=True, runcontrol=False)

    def test_WHEN_cset_called_with_runcontrol_and_no_value_THEN_passed_to_API(self):
        low_limit, high_limit = 3, 10
        genie.cset("my_block", runcontrol=True, lowlimit=low_limit, highlimit=high_limit)
        self.mocked_api.set_block_value.assert_called_with(
            "my_block", None, True, low_limit, high_limit, None
        )

    def test_WHEN_cset_called_with_wait_and_no_value_THEN_raises(self):
        self.assertRaises(Exception, genie.cset, "my_block", wait=True)

    @patch("genie_python.utilities._correct_path_casing_existing")
    def test_WHEN_change_tables_is_called_with_absolute_path_THEN_path_not_changed(
        self, correct_casing
    ):
        correct_casing.side_effect = lambda x: x

        test_table = r"C:/abs_path"

        genie.change_tables(wiring=test_table)

        self.mocked_api.dae.change_tables.assert_called_with(test_table, None, None)


class TestChangeScriptDir(unittest.TestCase):
    def setUp(self):
        self.default_dir = r"C:/scripts/"
        genie.change_script_dir(self.default_dir)
        genie_python.genie_api_setup._exceptions_raised = True

    @patch("genie_python.utilities._correct_path_casing_existing")
    def test_GIVEN_defaults_set_WHEN_get_path_THEN_path_is_default(self, correct_casing):
        correct_casing.side_effect = lambda x: x
        result = genie.get_script_dir()

        assert_that(result, is_(self.default_dir))

    @patch("genie_python.utilities._correct_path_casing_existing")
    @patch("os.mkdir")
    def test_GIVEN_defaults_WHEN_change_dir_to_existing_dir_using_forward_slashes_THEN_path_is_as_set(
        self, make_dirs_mock, correct_casing
    ):
        expected_dir = r"c:/scripts/test/"
        self.setup_mocks(expected_dir, correct_casing, make_dirs_mock)

        genie.change_script_dir(expected_dir)
        result = genie.get_script_dir()

        assert_that(result, is_(expected_dir))
        assert_that(self.created_paths, has_length(0), "no paths created")

    @patch("genie_python.utilities._correct_path_casing_existing")
    @patch("os.mkdir")
    def test_GIVEN_defaults_WHEN_change_dir_to_existing_dir_using_multiple_arguments_THEN_path_is_all_arguments_joined(
        self, make_dirs_mock, correct_casing
    ):
        root = r"c:/scripts"
        dir = r"test"
        subdir = r"test_sub"
        expected_dir = "{}/{}/{}/".format(root, dir, subdir)

        self.setup_mocks(expected_dir, correct_casing, make_dirs_mock)

        genie.change_script_dir(root, dir, subdir)
        result = genie.get_script_dir()

        assert_that(result, is_(expected_dir))
        assert_that(self.created_paths, has_length(0), "no paths created")

    @patch("genie_python.utilities._correct_path_casing_existing")
    @patch("os.mkdir")
    def test_GIVEN_defaults_WHEN_change_dir_but_top_dir_does_not_exist_THEN_path_created(
        self, make_dirs_mock, correct_casing
    ):
        self.setup_mocks(r"c:/scripts", correct_casing, make_dirs_mock)

        expected_dir = r"c:/scripts/test"

        genie.change_script_dir(expected_dir)
        result = genie.get_script_dir()

        assert_that(self.created_paths, contains_exactly(os.path.abspath(expected_dir)))
        assert_that(result, is_(expected_dir + "/"))

    @patch("genie_python.utilities._correct_path_casing_existing")
    @patch("os.mkdir")
    def test_GIVEN_defaults_WHEN_change_dir_but_top_three_dirs_do_not_exist_THEN_path_created(
        self, make_dirs_mock, correct_casing
    ):
        existing_dir = r"c:/scripts"
        self.setup_mocks(existing_dir, correct_casing, make_dirs_mock)

        subdir = "test"
        subdir1 = "subdir1"
        subdir2 = "subdir2"
        expected_dir = "{}/{}/{}/{}/".format(existing_dir, subdir, subdir1, subdir2)

        genie.change_script_dir(os.path.join(existing_dir, subdir, subdir1, subdir2) + "/")
        result = genie.get_script_dir()

        assert_that(
            self.created_paths,
            contains_exactly(
                os.path.abspath(os.path.join(existing_dir, subdir)),
                os.path.abspath(os.path.join(existing_dir, subdir, subdir1)),
                os.path.abspath(os.path.join(existing_dir, subdir, subdir1, subdir2)),
            ),
        )
        assert_that(result, is_(expected_dir))

    @patch("genie_python.utilities._correct_path_casing_existing")
    @patch("os.mkdir")
    def test_GIVEN_defaults_WHEN_change_dir_but_root_dir_does_not_exist_THEN_script_dir_not_changed(
        self, make_dirs_mock, correct_casing
    ):
        self.setup_mocks(r"c:/scripts", correct_casing, make_dirs_mock)

        with self.assertRaises(OSError):
            genie.change_script_dir(r"D:/scripts/test")
        result = genie.get_script_dir()

        assert_that(result, is_(r"C:/scripts/"))

    def setup_mocks(self, initial_dir, correct_casing, make_dirs_mock):
        self.created_paths = []
        self.paths = [os.path.abspath(initial_dir)]

        def stub(path):
            if os.path.abspath(path) in self.paths:
                return path
            raise OSError("No such file")

        def create_dir(path):
            self.paths.append(os.path.abspath(path))
            self.created_paths.append(os.path.abspath(path))

        correct_casing.side_effect = stub
        make_dirs_mock.side_effect = create_dir
