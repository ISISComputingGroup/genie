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

import unittest
from collections import OrderedDict
from datetime import datetime

from mock import patch
from parameterized import parameterized

from genie_python import genie


def create_dummy_blocks(block_names, values=None):
    if values is None:
        values = ["INIT_VALUE"] * len(block_names)
    genie._genie_api.set_multiple_blocks(block_names, values)


class TestSimulationSetup(unittest.TestCase):
    @patch("genie_python.genie._genie_api.get_block_names")
    def test_GIVEN_existing_blocks_WHEN_simulate_with_populate_blocks_THEN_blocks_populated(
        self, block_names
    ):
        block_names.return_value = ["TEST_BLOCK"]
        with genie.sim.Simulate(True):
            test_block_data = genie.cget("TEST_BLOCK")
            self.assertEqual("TEST_BLOCK", test_block_data["name"])
            self.assertEqual("INITIAL_VALUE", test_block_data["value"])

    @patch("genie_python.genie._genie_api.get_block_names")
    def test_GIVEN_existing_blocks_WHEN_simulate_with_populate_blocks_and_get_non_existent_block_THEN_exception_thrown(
        self, block_names
    ):
        block_names.return_value = ["TEST_BLOCK"]
        with genie.sim.Simulate(True):
            self.assertRaises(Exception, genie.cget, "BAD_BLOCK")

    @patch("genie_python.genie._genie_api.get_block_names")
    def test_GIVEN_existing_blocks_WHEN_simulate_with_populate_blocks_and_set_non_existent_block_THEN_exception_thrown(
        self, block_names
    ):
        block_names.return_value = ["TEST_BLOCK"]
        with genie.sim.Simulate(True):
            self.assertRaises(Exception, genie.cset, "BAD_BLOCK", 10)

    @patch("genie_python.genie._genie_api.get_block_names")
    def test_GIVEN_existing_blocks_WHEN_simulate_without_populate_blocks_and_get_existing_block_THEN_exception_thrown(
        self, block_names
    ):
        block_names.return_value = ["TEST_BLOCK"]
        with genie.sim.Simulate(False):
            self.assertRaises(Exception, genie.cget, "TEST_BLOCK")

    @patch("genie_python.genie._genie_api.get_block_names")
    def test_WHEN_simulate_without_populate_blocks_and_set_block_THEN_block_is_set(
        self, block_names
    ):
        with genie.sim.Simulate(False):
            genie.cset("TEST_BLOCK", 10)
            test_block_data = genie.cget("TEST_BLOCK")
            self.assertEqual("TEST_BLOCK", test_block_data["name"])
            self.assertEqual(10, test_block_data["value"])

    @patch("genie_python.genie._genie_api.get_block_names")
    def test_WHEN_simulate_with_populate_blocks_and_initial_block_value_is_set(self, block_names):
        with genie.sim.Simulate(True, {"TEST_BLOCK": 42.42}):
            test_block_data = genie.cget("TEST_BLOCK")
            self.assertEqual("TEST_BLOCK", test_block_data["name"])
            self.assertEqual(42.42, test_block_data["value"])

    @patch("genie_python.genie._genie_api.get_block_names")
    def test_WHEN_simulate_with_populate_blocks_and_initial_block_is_set_as_dictionary(
        self, block_names
    ):
        block_info = OrderedDict()
        block_info["name"] = "TEST_BLOCK"
        block_info["value"] = 42.42
        block_info["runcontrol"] = True
        block_info["lowlimit"] = 40
        block_info["highlimit"] = 45
        with genie.sim.Simulate(True, {"TEST_BLOCK": block_info}):
            test_block_data = genie.cget("TEST_BLOCK")
            self.assertEqual("TEST_BLOCK", test_block_data["name"])
            self.assertEqual(42.42, test_block_data["value"])
            self.assertTrue(test_block_data["runcontrol"])
            self.assertEqual(40, test_block_data["lowlimit"])
            self.assertEqual(45, test_block_data["highlimit"])


class TestSimulationSequence(unittest.TestCase):
    def setUp(self):
        self.sim = genie.sim.Simulate(False)
        self.sim.__enter__()
        genie.set_instrument(None, import_instrument_init=False)

    def tearDown(self):
        self.sim.__exit__()

    def test_GIVEN_one_block_WHEN_cset_value_for_block_THEN_set_correct_value(self):
        create_dummy_blocks(["a"])
        genie.cset(a=125)

        a = genie.cget("a")

        self.assertEqual(125, a["value"])

    def test_GIVEN_one_block_WHEN_cset_value_for_block_in_alternate_way_THEN_set_correct_value(
        self,
    ):
        create_dummy_blocks(["a"])
        genie.cset("a", 60)

        a = genie.cget("a")

        self.assertEqual(60, a["value"])

    def test_GIVEN_three_blocks_WHEN_cset_values_for_each_block_THEN_set_correct_values(self):
        create_dummy_blocks(["a", "b", "c"])
        genie.cset(a=100, b=200, c=300)

        # Act
        a = genie.cget("a")
        b = genie.cget("b")
        c = genie.cget("c")

        # Assert
        self.assertEqual(100, a["value"])
        self.assertEqual(200, b["value"])
        self.assertEqual(300, c["value"])

    def test_GIVEN_one_block_WHEN_cset_runcontrol_limits_THEN_set_runcontrol_limits(self):
        create_dummy_blocks(["a"])
        genie.cset(a=45, runcontrol=True, lowlimit=40, highlimit=50)

        a = genie.cget("a")

        self.assertEqual(40, a["lowlimit"])
        self.assertEqual(50, a["highlimit"])

    def test_GIVEN_one_block_WHEN_cset_change_wait_limits_THEN_retain_runcontrol_limits(self):
        create_dummy_blocks(["a"])
        genie.cset(a=90, runcontrol=True, lowlimit=95, highlimit=99)

        genie.cset(a=1, wait=True, lowlimit=4, highlimit=6)
        a = genie.cget("a")

        self.assertEqual(95, a["lowlimit"])
        self.assertEqual(99, a["highlimit"])

    def test_GIVEN_one_period_WHEN_change_number_of_soft_periods_THEN_set_number_of_periods(self):
        genie.change_number_soft_periods(42)

        self.assertEqual(42, genie.get_number_periods())

    def test_GIVEN_one_block_WHEN_cset_period_THEN_update_period(self):
        genie.change_number_soft_periods(15)

        genie.change_period(5)

        self.assertEqual(5, genie.get_period())

    def test_GIVEN_aborted_state_WHEN_begin_run_THEN_begin_run(self):
        genie.begin()

        rs = genie.get_runstate()

        self.assertEqual("RUNNING", rs)

    def test_GIVEN_running_state_WHEN_abort_run_THEN_abort_run(self):
        # Arrange
        genie.begin()

        # Act
        genie.abort()
        rs = genie.get_runstate()

        # Assert
        self.assertEqual("SETUP", rs)

    def test_GIVEN_running_state_WHEN_end_run_THEN_end_run(self):
        # Arrange
        genie.begin()

        # Act
        genie.end()
        rs = genie.get_runstate()

        # Assert
        self.assertEqual("SETUP", rs)

    def test_GIVEN_running_state_WHEN_pause_run_THEN_pause_run(self):
        # Arrange
        genie.begin()

        # Act
        genie.pause()
        rs = genie.get_runstate()

        # Assert
        self.assertEqual("PAUSED", rs)

    def test_GIVEN_one_block_WHEN_cset_runcontrol_and_wait__true_THEN_exception(self):
        create_dummy_blocks(["a"])
        with self.assertRaisesRegex(
            Exception, "Cannot enable or disable runcontrol at the same time as setting a wait"
        ):
            genie.cset(a=1, runcontrol=True, wait=True)

    def test_GIVEN_multiple_blocks_WHEN_cset_runcontrol_THEN_exception(self):
        create_dummy_blocks(["a", "b"])
        with self.assertRaisesRegex(
            Exception, "Runcontrol and wait can only be changed for one block at a time"
        ):
            genie.cset(a=1, b=2, runcontrol=True)

    def test_GIVEN_multiple_blocks_WHEN_cset_wait_THEN_exception(self):
        create_dummy_blocks(["a", "b"])
        with self.assertRaisesRegex(
            Exception, "Runcontrol and wait can only be changed for one block at a time"
        ):
            genie.cset(a=1, b=2, wait=True)

    def test_GIVEN_period_WHEN_set_period_to_higher_value_THEN_exception(self):
        # Arrange
        period = genie.get_number_periods()

        # Assert
        with self.assertRaisesRegex(
            Exception, "Cannot set period as it is higher than the number of periods"
        ):
            genie.change_period(period + 1)

    def test_GIVEN_preexisting_block_WHEN_updating_values_with_cset_THEN_update_values_and_remember_non_specified_values(
        self,
    ):
        create_dummy_blocks(["HCENTRE"])
        genie.cset(HCENTRE=2, runcontrol=True, lowlimit=2.5, highlimit=3)

        genie.cset(HCENTRE=2.6, wait=True)

        a = genie.cget("HCENTRE")
        self.assertEqual(2.5, a["lowlimit"])
        self.assertEqual(3, a["highlimit"])
        self.assertEqual(True, a["runcontrol"])

    @parameterized.expand([(123456,), (654321,), (234175,)])
    def test_GIVEN_change_rb_WHEN_get_rb_THEN_values_match(self, rb):
        # Act
        genie.change_rb(rb)

        # Assert
        self.assertEqual(str(rb), genie.get_rb())

    def test_GIVEN_changed_user_WHEN_getting_user_THEN_values_match(self):
        # Arrange
        users = "Adam, Dave, John"

        # Act
        genie.change_users(users)

        # Assert
        self.assertEqual(users, genie.get_dashboard()["user"])

    def test_WHEN_wait_for_called_THEN_does_not_wait_long(self):
        start_time = datetime.now()
        genie.waitfor_time(seconds=10)
        elapsed_time = (datetime.now() - start_time).seconds

        self.assertLess(elapsed_time, 2)

    def test_WHEN_default_setup_THEN_num_spectra_as_expected(self):
        self.assertEqual(1, genie.get_number_spectra())

    def test_WHEN_default_setup_THEN_num_time_channels_as_expected(self):
        self.assertEqual(1, genie.get_number_timechannels())
