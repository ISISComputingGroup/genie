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

from parameterized import parameterized

from genie_python.genie_simulate_impl import API
from genie_python.genie_wait_for_move import WaitForMoveController


class TestGenieWaitForMove(unittest.TestCase):
    def setUp(self):
        motion_pv = "MOTOR"
        self.genie_wait_for_move = WaitForMoveController(API(), motion_pv)

    def test_GIVEN_method_flag_error_conditions_WHEN_method_called_THEN_method_doesnt_error(self):
        blocks = []
        self.genie_wait_for_move._flag_error_conditions(blocks)

    def test_GIVEN_method_flag_error_conditions_WHEN_method_called_THEN_method_doesnt_error_A(self):
        blocks = ["BLOCK"]
        self.genie_wait_for_move._flag_error_conditions(blocks)

    def test_GIVEN_method_filter_out_missing_blocks_WHEN_method_called_THEN_method_doesnt_error(
        self,
    ):
        blocks = []
        self.genie_wait_for_move._filter_out_missing_blocks(blocks)

    def test_GIVEN_method_wait_specific_WHEN_method_called_THEN_method_doesnt_error(self):
        blocks = []
        self.genie_wait_for_move.wait_specific(blocks)

    def test_GIVEN_method_any_motion_WHEN_method_called_THEN_method_doesnt_error(self):
        self.genie_wait_for_move._any_motion()

    def test_GIVEN_method_check_timeouts_valid_WHEN_method_called_THEN_method_doesnt_error(self):
        start_timeout, move_timeout = 10.0, 10.0
        self.genie_wait_for_move._check_timeouts_valid(start_timeout, move_timeout)

    @parameterized.expand([("start_invalid_move_none", -10.0, None), ("both_valid", 12.0, 30.0)])
    def test_GIVEN_method_check_timeouts_valid_WHEN_check_timeouts_THEN_returns_valid_values(
        self, _, start_input, move_input
    ):
        start_timeout = start_input
        move_timeout = move_input
        start_input, move_input = self.genie_wait_for_move._check_timeouts_valid(
            start_timeout, move_timeout
        )

        self.assertGreaterEqual(start_input, 0)

    @parameterized.expand(
        [("start_valid_move_none", 10.0, None), ("start_valid_move_invalid", 12.0, -30.0)]
    )
    def test_GIVEN_method_check_timeouts_valid_WHEN_check_timeouts_THEN_returns_valid_values(
        self, _, start_input, move_input
    ):
        start_timeout = start_input
        move_timeout = move_input
        start_input, move_input = self.genie_wait_for_move._check_timeouts_valid(
            start_timeout, move_timeout
        )

        self.assertIsNone(move_input)
