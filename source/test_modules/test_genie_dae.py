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
from mock import MagicMock, call
from genie_dae import Dae
from genie_change_cache import ChangeCache


class TestGenieDAE(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.dae = Dae(self.api, "")

        self.dae.in_change = True
        self.change_cache = ChangeCache()
        self.dae.change_cache = self.change_cache

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

    def check_all_vetos(self, set):
        """
        Helper function to check that all vetos are set or not.
        """
        for k, d in self.change_cache.__dict__.iteritems():
            if k.endswith('veto') and 'fermi' not in k:
                self.assertEqual(set, d, "{} incorrect".format(k))

    def set_all_vetos(self, set):
        """
        Helper function to set all vetos to a value by the 'backdoor'.
        """
        for k in self.change_cache.__dict__.keys():
            if k.endswith('veto') and 'fermi' not in k:
                self.change_cache.__dict__[k] = set

    def test_WHEN_change_vetos_called_with_no_arguments_THEN_nothing_happens(self):
        self.dae.change_vetos()

        self.check_all_vetos(None)

    def test_WHEN_change_vetos_called_with_smp_true_THEN_smp_veto_set_to_1(self):
        self.dae.change_vetos(smp=True)
        self.assertEqual(1, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_smp_true_incorrect_case_THEN_smp_veto_set_to_1(self):
        self.dae.change_vetos(sMP=True)
        self.assertEqual(1, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_smp_false_THEN_smp_veto_set_to_0(self):
        self.dae.change_vetos(smp=False)
        self.assertEqual(0, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_smp_false_THEN_smp_veto_set_to_0(self):
        self.dae.change_vetos(smp=False)
        self.assertEqual(0, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_non_boolean_value_THEN_exception_raised_and_veto_not_set(self):
        self.assertRaises(Exception, self.dae.change_vetos, smp="test")
        self.assertEqual(None, self.change_cache.smp_veto)

        self.assertRaises(Exception, self.dae.change_vetos, hz50="test")
        self.assertEqual(None, self.change_cache.hz50_veto)

    def test_WHEN_change_vetos_called_with_clearall_true_THEN_all_vetos_cleared(self):
        self.set_all_vetos(1)
        self.check_all_vetos(1)

        self.dae.change_vetos(clearall=True)
        self.check_all_vetos(0)

    def test_WHEN_change_vetos_called_with_clearall_false_THEN_nothing_happens(self):
        self.set_all_vetos(1)
        self.check_all_vetos(1)

        self.dae.change_vetos(clearall=False)
        self.check_all_vetos(1)

    def test_WHEN_change_vetos_called_with_unknown_veto_THEN_exception_thrown(self):
        self.assertRaises(Exception, self.dae.change_vetos, bad_veto=True)

    def test_WHEN_fifo_veto_enabled_at_runtime_THEN_correct_PV_set_with_correct_value(self):
        self.dae.change_vetos(fifo=True)

        func = self.api.set_pv_value
        self.assertTrue(func.called)
        func.assert_called_with("DAE:VETO:ENABLE:SP", "FIFO", False)

    def test_WHEN_fifo_veto_disabled_at_runtime_THEN_correct_PV_set_with_correct_value(self):
        self.dae.change_vetos(fifo=False)

        func = self.api.set_pv_value
        self.assertTrue(func.called)
        func.assert_called_with("DAE:VETO:DISABLE:SP", "FIFO", False)

    def test_WHEN_clearing_all_vetoes_THEN_fifo_is_unaffected(self):
        self.dae.change_vetos(clearall=True)

        func = self.api.set_pv_value
        # clearall should not affect FIFO so none of the PVs should be set.
        func.assert_not_called()
