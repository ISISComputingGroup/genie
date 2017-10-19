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

import unittest
from mock import MagicMock
from genie_dae import Dae


class TestGenieDAE(unittest.TestCase):
    def setUp(self):
        self.dae = Dae(MagicMock(), "")

    def test_WHEN_create_tcb_string_with_no_changes_and_log_binning_THEN_bin_setting_string_returned(self):
        ans = self.dae._create_tcb_return_string(None, None, None, True)

        self.assertEqual(ans, "Setting TCB to LOG binning")

    def test_WHEN_create_tcb_string_with_no_changes_and_not_log_binning_THEN_bin_setting_string_returned(self):
        ans = self.dae._create_tcb_return_string(None, None, None, False)

        self.assertEqual(ans, "Setting TCB to LINEAR binning")

    def test_WHEN_create_tcb_string_with_low_and_high_changed_THEN_range_changed_string_returned(self):
        new_low = 0
        new_high = 10
        ans = self.dae._create_tcb_return_string(new_low, new_high, None, True)

        self.assertEqual(ans, "Setting TCB range {} to {} (LOG binning)".format(new_low, new_high))

    def test_WHEN_create_tcb_string_with_only_low_changed_THEN_low_limit_changed_string_returned(self):
        new_low = 0
        ans = self.dae._create_tcb_return_string(new_low, None, None, True)

        self.assertEqual(ans, "Setting TCB low limit to {} (LOG binning)".format(new_low))

    def test_WHEN_create_tcb_string_with_only_high_changed_THEN_high_limit_changed_string_returned(self):
        new_high = 10
        ans = self.dae._create_tcb_return_string(None, new_high, None, True)

        self.assertEqual(ans, "Setting TCB high limit to {} (LOG binning)".format(new_high))

    def test_WHEN_create_tcb_string_with_only_step_changed_THEN_step_changed_string_returned(self):
        new_step = 10
        ans = self.dae._create_tcb_return_string(None, None, new_step, False)

        self.assertEqual(ans, "Setting TCB step {} (LINEAR binning)".format(new_step))

    def test_WHEN_create_tcb_string_with_all_changed_THEN_all_changed_string_returned(self):
        new_low = 0
        new_high = 10
        new_step = 2
        ans = self.dae._create_tcb_return_string(new_low, new_high, new_step, True)

        self.assertEqual(ans, "Setting TCB range {} to {} step {} (LOG binning)".format(new_low, new_high, new_step))

    def test_WHEN_create_tcb_string_with_low_and_step_changed_THEN_low_limit_and_step_string_returned(self):
        new_low = 0
        new_step = 2
        ans = self.dae._create_tcb_return_string(new_low, None, new_step, True)

        self.assertEqual(ans, "Setting TCB low limit to {} step {} (LOG binning)".format(new_low, new_step))

    def test_WHEN_create_tcb_string_with_high_and_step_changed_THEN_high_limit_and_step_string_returned(self):
        new_high = 10
        new_step = 2
        ans = self.dae._create_tcb_return_string(None, new_high, new_step, True)

        self.assertEqual(ans, "Setting TCB high limit to {} step {} (LOG binning)".format(new_high, new_step))

    def test_GIVEN_change_not_started_WHEN_change_finished_called_THEN_exception_thrown(self):
        self.dae.in_change = False

        self.assertRaises(Exception, self.dae.change_finish)

    def test_GIVEN_in_running_state_WHEN_set_period_called_THEN_exception_thrown(self):
        self.dae.api.get_pv_value = MagicMock(return_value="RUNNING")

        self.assertRaises(Exception, self.dae.set_period, 1)

    def test_GIVEN_in_paused_state_WHEN_set_period_called_THEN_no_exception_thrown(self):
        self.dae.api.get_pv_value = MagicMock(return_value="PAUSED")

        self.dae.set_period(1)
        self.assertTrue(True)

    def test_GIVEN_in_setup_state_WHEN_set_period_called_THEN_no_exception_thrown(self):
        self.dae.api.get_pv_value = MagicMock(return_value="SETUP")

        self.dae.set_period(1)
        self.assertTrue(True)
