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

import numpy as np
from hamcrest import assert_that, calling, close_to, is_, raises
from mock import MagicMock, patch
from parameterized import parameterized_class

from genie_python.genie_change_cache import ChangeCache
from genie_python.genie_dae import Dae
from genie_python.genie_simulate_impl import ChangeCache as SimChangeCache
from genie_python.genie_simulate_impl import Dae as SimDae
from genie_python.utilities import compress_and_hex, dehex_and_decompress

WIRING_PATH = "path/to/wiring.dat"
SPECTRA_PATH = "path/to/spectra.dat"
DETECTOR_PATH = "path/to/detector.dat"

DAE_SETTINGS_XML = """<Cluster>
    <Name>Data Acquisition</Name>
    <NumElts>4</NumElts>
    <I32>
        <Name>Monitor Spectrum</Name>
        <Val>5</Val>
    </I32>
    <DBL>
        <Name>from</Name>
        <Val>12000</Val>
    </DBL>
    <String>
        <Name>Wiring Table</Name>
        <Val>{wiring_path}</Val>
    </String>
    <String>
        <Name>Detector Table</Name>
        <Val>{detector_path}</Val>
    </String>
        <String>
        <Name>Spectra Table</Name>
        <Val>{spectra_path}</Val>
    </String>
    <EW>
        <Name>DAETimingSource</Name>
        <Choice>ISIS</Choice>
        <Choice>Internal Test Clock</Choice>
        <Choice>SMP</Choice>
        <Choice>Muon Cerenkov</Choice>
        <Choice>Muon MS</Choice>
        <Choice>ISIS (first TS1)</Choice>
        <Choice>TS1 Only</Choice>
        <Val>2</Val>
    </EW>
</Cluster>""".format(
    wiring_path=WIRING_PATH, detector_path=DETECTOR_PATH, spectra_path=SPECTRA_PATH
)

TCB_SETTINGS_XML = """<Cluster>
        <Name>Time Channels</Name>
        <NumElts>3</NumElts>
        <DBL>
                <Name>TR1 From 1</Name>
                <Val>0</Val>
        </DBL>
        <U16>
                <Name>TR1 In Mode 2</Name>
                <Val>0</Val>
        </U16>
        <String>
                <Name>Time Channel File</Name>
                <Val>C:/Instrument/Settings/config/NDW1801/configurations/tcb/RCPTT_TCB_1.dat</Val>
        </String>
</Cluster>"""

PERIOD_SETTINGS_XML = """<Cluster>
    <Name>Hardware Periods</Name>
    <NumElts>38</NumElts>
    <EW>
        <Name>Period Setup Source</Name>
        <Choice>Use Parameters Below</Choice>
        <Choice>Read from file</Choice>
        <Val>0</Val>
    </EW>
    <String>
        <Name>Period File</Name>
        <Val></Val>
    </String>
    <I32>
        <Name>Number Of Software Periods</Name>
        <Val>1000</Val>
    </I32>
    <DBL>
        <Name>Hardware Period Sequences</Name>
        <Val>0</Val>
    </DBL>
</Cluster>"""

YC_RETURN = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
Y_RETURN = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
YC_NORD_RETURN = 4
Y_NORD_RETURN = 5
WIDTHS = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
X_RETURN = [10.0 + sum(WIDTHS[0:i]) for i in range(len(WIDTHS) + 1)]

SPECINT = [1.0, 2.0]
SPECDATA = [1.0, 2.0, 3.0, 4.0]


def get_mock_pv_value(pv_name, to_string, use_numpy):
    """
    Mock method for testing changes to DAE settings. It returns example XML data if the pv name is one of
    DAESETTINGS, TCBSETTINGS or HARDWAREPERIODS.
    Args:
        pv_name: the name of the pv
        to_string: whether to convert the value to a string. Not used in this method, but included since the method
        it is mocking is called with this keyword argument.

    Returns:
        String representing XML data similar to the one in the actual PV, or a hex string for TCB settings.
    """
    mock_data = {
        "DAE:DAESETTINGS": DAE_SETTINGS_XML,
        "DAE:TCBSETTINGS": compress_and_hex(TCB_SETTINGS_XML),
        "DAE:HARDWAREPERIODS": PERIOD_SETTINGS_XML,
    }
    return mock_data[pv_name]


class TestGenieDAE(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.dae = Dae(self.api, "")

        self.change_cache = ChangeCache()
        self.dae.change_cache = self.change_cache

    @patch.dict("genie_python.genie_dae.DAE_PVS_LOOKUP", {"period_rbv": "DAE:PERIOD:RBV"})
    def test_GIVEN_lower_case_DAE_name_WHEN_get_dae_pv_name_THEN_get_correct_pv_name(self):
        self.assertEqual(self.dae._get_dae_pv_name("period_rbv"), "DAE:PERIOD:RBV")

    @patch.dict("genie_python.genie_dae.DAE_PVS_LOOKUP", {"period_rbv": "DAE:PERIOD:RBV"})
    def test_GIVEN_sentence_case_DAE_name_WHEN_get_dae_pv_name_THEN_get_correct_pv_name(self):
        self.assertEqual(self.dae._get_dae_pv_name("Period_Rbv"), "DAE:PERIOD:RBV")

    def test_GIVEN_pv_name_WHEN_no_inst_prefix_THEN_get_get_unchanged_pv_name(self):
        self.dae.inst_prefix = None
        self.assertEqual(self.dae._prefix_pv_name("DAE:PERIOD:SP"), "DAE:PERIOD:SP")

    def test_GIVEN_pv_name_WHEN_has_inst_prefix_THEN_get_get_full_pv_name(self):
        self.dae.inst_prefix = "TE:NDW1801:"
        self.assertEqual(self.dae._prefix_pv_name("DAE:PERIOD:SP"), "TE:NDW1801:DAE:PERIOD:SP")

    def test_WHEN_create_tcb_string_with_no_changes_and_log_binning_THEN_bin_setting_string_returned(
        self,
    ):
        self.dae.in_change = True
        ans = self.dae._create_tcb_return_string(None, None, None, True)

        self.assertEqual(ans, "Setting TCB to LOG binning")

    def test_WHEN_create_tcb_string_with_no_changes_and_not_log_binning_THEN_bin_setting_string_returned(
        self,
    ):
        self.dae.in_change = True
        ans = self.dae._create_tcb_return_string(None, None, None, False)

        self.assertEqual(ans, "Setting TCB to LINEAR binning")

    def test_WHEN_create_tcb_string_with_low_and_high_changed_THEN_range_changed_string_returned(
        self,
    ):
        self.dae.in_change = True
        new_low = 0
        new_high = 10
        ans = self.dae._create_tcb_return_string(new_low, new_high, None, True)

        self.assertEqual(ans, "Setting TCB range {} to {} (LOG binning)".format(new_low, new_high))

    def test_WHEN_create_tcb_string_with_only_low_changed_THEN_low_limit_changed_string_returned(
        self,
    ):
        self.dae.in_change = True
        new_low = 0
        ans = self.dae._create_tcb_return_string(new_low, None, None, True)

        self.assertEqual(ans, "Setting TCB low limit to {} (LOG binning)".format(new_low))

    def test_WHEN_create_tcb_string_with_only_high_changed_THEN_high_limit_changed_string_returned(
        self,
    ):
        self.dae.in_change = True
        new_high = 10
        ans = self.dae._create_tcb_return_string(None, new_high, None, True)

        self.assertEqual(ans, "Setting TCB high limit to {} (LOG binning)".format(new_high))

    def test_WHEN_create_tcb_string_with_only_step_changed_THEN_step_changed_string_returned(self):
        self.dae.in_change = True
        new_step = 10
        ans = self.dae._create_tcb_return_string(None, None, new_step, False)

        self.assertEqual(ans, "Setting TCB step {} (LINEAR binning)".format(new_step))

    def test_WHEN_create_tcb_string_with_all_changed_THEN_all_changed_string_returned(self):
        self.dae.in_change = True
        new_low = 0
        new_high = 10
        new_step = 2
        ans = self.dae._create_tcb_return_string(new_low, new_high, new_step, True)

        self.assertEqual(
            ans,
            "Setting TCB range {} to {} step {} (LOG binning)".format(new_low, new_high, new_step),
        )

    def test_WHEN_create_tcb_string_with_low_and_step_changed_THEN_low_limit_and_step_string_returned(
        self,
    ):
        self.dae.in_change = True
        new_low = 0
        new_step = 2
        ans = self.dae._create_tcb_return_string(new_low, None, new_step, True)

        self.assertEqual(
            ans, "Setting TCB low limit to {} step {} (LOG binning)".format(new_low, new_step)
        )

    def test_WHEN_create_tcb_string_with_high_and_step_changed_THEN_high_limit_and_step_string_returned(
        self,
    ):
        self.dae.in_change = True
        new_high = 10
        new_step = 2
        ans = self.dae._create_tcb_return_string(None, new_high, new_step, True)

        self.assertEqual(
            ans, "Setting TCB high limit to {} step {} (LOG binning)".format(new_high, new_step)
        )

    def test_GIVEN_change_not_started_WHEN_change_finished_called_THEN_exception_thrown(self):
        self.assertRaises(Exception, self.dae.change_finish)

    def test_GIVEN_in_running_state_and_period_pv_no_alarm_WHEN_set_period_called_THEN_value_error_thrown(
        self,
    ):
        self.dae.api.get_pv_value = MagicMock(return_value="RUNNING")
        self.dae.api.get_pv_alarm = MagicMock(return_value="NO_ALARM")

        self.assertRaises(ValueError, self.dae.set_period, 1)

    def test_GIVEN_in_paused_state_and_period_pv_no_alarm_WHEN_set_period_called_THEN_no_exception_thrown(
        self,
    ):
        self.dae.api.get_pv_value = MagicMock(return_value="PAUSED")
        self.dae.api.get_pv_alarm = MagicMock(return_value="NO_ALARM")

        self.dae.set_period(1)

    def test_GIVEN_in_setup_state_and_period_pv_invalid_alarm_WHEN_set_period_called_THEN_io_error_thrown(
        self,
    ):
        self.dae.api.get_pv_value = MagicMock(return_value="SETUP")
        self.dae.api.get_pv_alarm = MagicMock(return_value="INVALID")

        self.assertRaises(IOError, self.dae.set_period, -1)

    def test_GIVEN_not_in_change_WHEN_change_finish_called_THEN_value_error_with_correct_message_thrown(
        self,
    ):
        self.dae.in_change = False

        self.assertRaisesRegex(ValueError, "Change has already finished", self.dae.change_finish)

    def test_GIVEN_in_transition_WHEN_change_finish_called_THEN_value_error_with_correct_message_thrown(
        self,
    ):
        self.dae.in_change = True
        self.dae.in_transition = MagicMock(return_value=True)

        self.assertRaisesRegex(
            ValueError,
            "Another DAE change operation is currently in progress - values will be inconsistent",
            self.dae.change_finish,
        )

    def test_GIVEN_instrument_not_in_setup_WHEN_change_finish_called_THEN_value_error_with_correct_message_thrown(
        self,
    ):
        self.dae.in_change = True
        self.dae.get_run_state = MagicMock(return_value="RUNNING")

        self.assertRaisesRegex(
            ValueError,
            "Instrument must be in SETUP when changing settings!",
            self.dae.change_finish,
        )

    def test_GIVEN_instrument_in_setup_and_in_change_and_not_in_transition_WHEN_change_finish_called_THEN_no_exception_thrown_and_not_in_change(
        self,
    ):
        self.dae.in_change = True
        self.dae.get_run_state = MagicMock(return_value="SETUP")
        self.dae.in_transition = MagicMock(return_value=False)
        self.dae.api.get_pv_value = get_mock_pv_value

        self.dae.change_finish()
        self.assertEqual(self.dae.in_change, False)
        self.assertEqual(self.dae.in_change, False)

    def test_GIVEN_number_of_periods_pv_in_invalid_alarm_WHEN_change_period_settings_called_THEN_exception_thrown(
        self,
    ):
        self.dae.api.get_pv_value = MagicMock(return_value=PERIOD_SETTINGS_XML)
        self.dae.api.set_pv_value = MagicMock(return_value=None)
        self.dae.change_cache.change_period_settings = MagicMock(return_value=True)
        self.dae.api.get_pv_alarm = MagicMock(return_value="INVALID")

        self.assertRaises(IOError, self.dae._change_period_settings)

    def test_GIVEN_number_of_periods_pv_no_alarm_WHEN_change_finish_called_THEN_no_exception_thrown(
        self,
    ):
        self.dae.api.get_pv_value = MagicMock(return_value=PERIOD_SETTINGS_XML)
        self.dae.api.set_pv_value = MagicMock(return_value=None)
        self.dae.change_cache.change_period_settings = MagicMock(return_value=True)
        self.dae.api.get_pv_alarm = MagicMock(return_value="NO_ALARM")

        self.dae._change_period_settings()

    def check_all_vetos(self, set):
        """
        Helper function to check that all vetos are set or not.
        """
        for k, d in self.change_cache.__dict__.items():
            if k.endswith("veto") and "fermi" not in k:
                self.assertEqual(set, d, "{} incorrect".format(k))

    def set_all_vetos(self, set):
        """
        Helper function to set all vetos to a value by the 'backdoor'.
        """
        for k in self.change_cache.__dict__.keys():
            if k.endswith("veto") and "fermi" not in k:
                self.change_cache.__dict__[k] = set

    def test_WHEN_change_vetos_called_with_no_arguments_THEN_nothing_happens(self):
        self.dae.change_vetos()

        self.check_all_vetos(None)

    def test_WHEN_change_vetos_called_with_smp_true_THEN_smp_veto_set_to_1(self):
        self.dae.in_change = True
        self.dae.change_vetos(smp=True)
        self.assertEqual(1, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_smp_true_incorrect_case_THEN_smp_veto_set_to_1(self):
        self.dae.in_change = True
        self.dae.change_vetos(sMP=True)
        self.assertEqual(1, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_smp_false_THEN_smp_veto_set_to_0(self):
        self.dae.in_change = True
        self.dae.change_vetos(smp=False)
        self.assertEqual(0, self.change_cache.smp_veto)

    def test_WHEN_change_vetos_called_with_non_boolean_value_THEN_exception_raised_and_veto_not_set(
        self,
    ):
        self.assertRaises(Exception, self.dae.change_vetos, smp="test")
        self.assertEqual(None, self.change_cache.smp_veto)

        self.assertRaises(Exception, self.dae.change_vetos, hz50="test")
        self.assertEqual(None, self.change_cache.hz50_veto)

    def test_WHEN_change_vetos_called_with_clearall_true_THEN_all_vetos_cleared(self):
        self.dae.in_change = True
        self.set_all_vetos(1)
        self.check_all_vetos(1)

        self.dae.change_vetos(clearall=True)
        self.check_all_vetos(0)

    def test_WHEN_change_vetos_called_with_clearall_false_THEN_nothing_happens(self):
        self.dae.in_change = True
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
        self.dae.in_change = True
        self.dae.change_vetos(clearall=True)

        func = self.api.set_pv_value
        # clearall should not affect FIFO so none of the PVs should be set.
        func.assert_not_called()

    @patch("genie_python.genie_cachannel_wrapper.CaChannelWrapper.add_monitor")
    def test_GIVEN_simulation_mode_WHEN_begin_run_THEN_user_is_warned(self, mock_monitor):
        mock_monitor.return_value = None
        self.dae.api.get_pv_value = MagicMock(return_value="SETUP")
        self.dae.get_simulation_mode = MagicMock(return_value=True)
        mock_warning = MagicMock()
        self.dae.simulation_mode_warning = mock_warning
        self.dae.begin_run()

        mock_warning.assert_called_once()

    @patch("genie_python.genie_cachannel_wrapper.CaChannelWrapper.add_monitor")
    def test_GIVEN_not_in_simulation_mode_WHEN_begin_run_THEN_user_is_warned(self, mock_monitor):
        mock_monitor.return_value = None
        self.dae.api.get_pv_value = MagicMock(return_value="SETUP")
        self.dae.get_simulation_mode = MagicMock(return_value=False)
        mock_warning = MagicMock()
        self.dae.simulation_mode_warning = mock_warning
        self.dae.begin_run()

        mock_warning.assert_not_called()

    def get_y_or_yc_pv_value(self, pv, _, use_numpy=False):
        if "X" in pv:
            result = X_RETURN
        elif "YC.NORD" in pv:
            result = YC_NORD_RETURN
        elif "Y.NORD" in pv:
            result = Y_NORD_RETURN
        elif "YC" in pv:
            result = YC_RETURN
        else:
            result = Y_RETURN

        if use_numpy:
            return np.array(result)
        else:
            return result

    def test_WHEN_get_spectrum_dist_true_THEN_default_returns_regular_counts(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)
        spectrum = self.dae.get_spectrum(1, 1, True)
        self.assertEqual(
            spectrum["signal"], Y_RETURN[:Y_NORD_RETURN], "Should return value of get_spectrum_y"
        )
        self.assertEqual(
            len(spectrum["signal"]), len(spectrum["time"]), "Should be the same length"
        )
        self.assertEqual(spectrum["mode"], "distribution", "Should return 'distribution'")

    def test_WHEN_get_spectrum_dist_false_THEN_default_returns_pure_counts(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)
        spectrum = self.dae.get_spectrum(1, 1, False)
        self.assertEqual(
            spectrum["signal"], YC_RETURN[:YC_NORD_RETURN], "Should return value of get_spectrum_yc"
        )
        self.assertEqual(
            len(spectrum["signal"]) + 1,
            len(spectrum["time"]),
            "x_size should be one larger than y_size",
        )
        self.assertEqual(spectrum["mode"], "non-distribution", "should return 'non-distribution'")

    def test_WHEN_get_spectrum_integrate_for_whole_range_THEN_whole_integrated_range(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(1, 1, X_RETURN[0], X_RETURN[YC_NORD_RETURN])

        expected_result = sum(YC_RETURN[0:YC_NORD_RETURN])
        assert_that(result, is_(expected_result))

    def test_WHEN_get_spectrum_integrate_for_unspecified_range_THEN_get_whole_range(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(1, 1)

        expected_result = sum(YC_RETURN[0:YC_NORD_RETURN])
        assert_that(result, is_(expected_result))

    def test_WHEN_get_spectrum_integrate_for_one_count_THEN_get_just_that_count(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(1, 1, X_RETURN[1], X_RETURN[2])

        assert_that(result, is_(YC_RETURN[1]))

    def test_WHEN_get_spectrum_integrate_for_count_partial_first_bin_top_limit_not_on_boundry_THEN_get_part_of_count(
        self,
    ):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(1, 1, X_RETURN[1], X_RETURN[1] + WIDTHS[1] * 0.25)

        assert_that(result, is_(YC_RETURN[1] * 0.25))

    def test_WHEN_get_spectrum_integrate_for_count_partial_first_bin_lower_limit_no_on_boundryTHEN_get_part_of_count(
        self,
    ):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(1, 1, X_RETURN[1] + WIDTHS[1] * 0.25, X_RETURN[2])

        assert_that(result, is_(YC_RETURN[1] * 0.75))

    def test_WHEN_get_spectrum_integrate_for_count_partial_of_two_different_bins_none_apart_THEN_get_part_of_count(
        self,
    ):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(
            1, 1, X_RETURN[1] + WIDTHS[1] * 0.25, X_RETURN[2] + WIDTHS[2] * 0.4
        )

        expected_from_low_bin = YC_RETURN[1] * 0.75
        expected_from_high_bin = YC_RETURN[2] * 0.4
        assert_that(result, is_(close_to(expected_from_high_bin + expected_from_low_bin, 1e-6)))

    def test_WHEN_get_spectrum_integrate_for_count_partial_of_two_different_bins_one_apart_THEN_get_part_of_count(
        self,
    ):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(
            1, 1, X_RETURN[1] + WIDTHS[1] * 0.25, X_RETURN[3] + WIDTHS[3] * 0.4
        )

        expected_from_low_bin = YC_RETURN[1] * 0.75
        expected_from_middle_bin = YC_RETURN[2]
        expected_from_high_bin = YC_RETURN[3] * 0.4
        assert_that(
            result,
            is_(
                close_to(
                    expected_from_high_bin + expected_from_middle_bin + expected_from_low_bin, 1e-6
                )
            ),
        )

    def test_WHEN_get_spectrum_integrate_for_count_partial_of_one_bins_THEN_get_part_of_count(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        result = self.dae.integrate_spectrum(
            1, 1, X_RETURN[1] + WIDTHS[1] * 0.25, X_RETURN[1] + WIDTHS[1] * 0.4
        )

        expected = YC_RETURN[1] * (0.4 - 0.25)
        assert_that(result, is_(close_to(expected, 1e-6)))

    def test_WHEN_get_spectrum_integrate_and_low_limit_is_below_lowest_bin_THEN_error(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        assert_that(
            calling(self.dae.integrate_spectrum).with_args(1, 1, X_RETURN[0] - 0.01, X_RETURN[1]),
            raises(ValueError),
        )

    def test_WHEN_get_spectrum_integrate_and_upper_limit_is_above_highest_bin_THEN_error(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        assert_that(
            calling(self.dae.integrate_spectrum).with_args(
                1, 1, X_RETURN[0], X_RETURN[YC_NORD_RETURN] + 0.1
            ),
            raises(ValueError),
        )

    def test_WHEN_get_spectrum_integrate_and_upper_limit_is_below_lower_limit_THEN_error(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_y_or_yc_pv_value)

        assert_that(calling(self.dae.integrate_spectrum).with_args(1, 1, 10, 9), raises(ValueError))

    def test_WHEN_users_set_with_empty_string_THEN_new_users_sent_to_db_server(self):
        self.api.set_pv_value = MagicMock()

        self.dae.set_users("")

        set_pv_arguments = self.api.set_pv_value.call_args_list[0][0]

        self.assertEqual("ED:USERNAME:SP", set_pv_arguments[0])
        self.assertEqual("[]", dehex_and_decompress(set_pv_arguments[1]))
        self.assertEqual(True, set_pv_arguments[2])

    def test_WHEN_users_set_with_single_user_THEN_new_users_sent_to_db_server(self):
        self.api.set_pv_value = MagicMock()

        self.dae.set_users("Smith")

        set_pv_arguments = self.api.set_pv_value.call_args_list[0][0]

        self.assertEqual("ED:USERNAME:SP", set_pv_arguments[0])
        self.assertEqual('[{"name": "Smith"}]', dehex_and_decompress(set_pv_arguments[1]))
        self.assertEqual(True, set_pv_arguments[2])

    def test_WHEN_users_set_with_multiple_users_THEN_new_users_sent_to_db_server(self):
        self.api.set_pv_value = MagicMock()

        self.dae.set_users("Smith, Jones")

        set_pv_arguments = self.api.set_pv_value.call_args_list[0][0]

        self.assertEqual("ED:USERNAME:SP", set_pv_arguments[0])
        self.assertEqual(
            '[{"name": "Smith"}, {"name": "Jones"}]', dehex_and_decompress(set_pv_arguments[1])
        )
        self.assertEqual(True, set_pv_arguments[2])

    def get_integrals_or_specdata_pv_value(self, pv, _, use_numpy=False):
        if "DAE:SPECINTEGRALS.NORD" in pv:
            result = len(SPECINT)
        elif "DAE:SPECINTEGRALS" in pv:
            result = SPECINT
        elif "DAE:SPECDATA.NORD" in pv:
            result = len(SPECDATA)
        elif "DAE:SPECDATA" in pv:
            result = SPECDATA
        else:
            result = []
        if use_numpy:
            return np.array(result)
        else:
            return result

    def test_WHEN_get_specint_called_THEN_expected_values(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_integrals_or_specdata_pv_value)
        data = self.dae.get_spec_integrals()
        self.assertTrue((data == SPECINT).all())

    def test_WHEN_get_specdata_called_THEN_expected_values(self):
        self.api.get_pv_value = MagicMock(side_effect=self.get_integrals_or_specdata_pv_value)
        data = self.dae.get_spec_data()
        self.assertTrue((data == SPECDATA).all())


@parameterized_class(
    [
        {"simulation": True},
        {"simulation": False},
    ]
)
class TestGenieAndSimulateDAEParity(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        if self.simulation:
            self.dae = SimDae()
            self.change_cache = SimChangeCache()
            self.change_cache.wiring = WIRING_PATH
            self.change_cache.spectra = SPECTRA_PATH
            self.change_cache.detector = DETECTOR_PATH
        else:
            self.dae = Dae(self.api, "")
            self.change_cache = ChangeCache()
            self.dae.api.get_pv_value = get_mock_pv_value
        self.dae.change_cache = self.change_cache

    def set_run_state(self, new_runstate):
        if self.simulation:
            self.dae.run_state = new_runstate
        else:
            self.dae.api.get_pv_value = MagicMock(return_value=new_runstate)

    @patch("genie_python.genie_cachannel_wrapper.CaChannelWrapper.add_monitor")
    def test_GIVEN_in_setup_state_WHEN_begin_run_called_THEN_no_exception_thrown(
        self, mock_monitor
    ):
        mock_monitor.return_value = None
        self.set_run_state("SETUP")
        self.dae.begin_run()

    def test_GIVEN_in_setup_state_WHEN_abort_run_called_THEN_exception_thrown(self):
        self.set_run_state("SETUP")

        with self.assertRaises(Exception):
            self.dae.abort_run()

    def test_GIVEN_in_setup_state_WHEN_end_run_called_THEN_exception_thrown(self):
        self.set_run_state("SETUP")

        with self.assertRaises(Exception):
            self.dae.end_run()

    def test_GIVEN_in_setup_state_WHEN_store_run_called_THEN_exception_thrown(self):
        self.set_run_state("SETUP")

        with self.assertRaises(Exception):
            self.dae.store_run()

    def test_GIVEN_in_setup_state_WHEN_pause_run_called_THEN__exception_thrown(self):
        self.set_run_state("SETUP")

        with self.assertRaises(Exception):
            self.dae.pause_run()

    def test_GIVEN_in_setup_state_WHEN_resume_run_called_THEN_exception_thrown(self):
        self.set_run_state("SETUP")

        with self.assertRaises(Exception):
            self.dae.resume_run()

    def test_GIVEN_in_running_state_WHEN_begin_run_called_THEN_exception_thrown(self):
        self.set_run_state("RUNNING")

        with self.assertRaises(Exception):
            self.dae.begin_run()

    def test_GIVEN_in_running_state_WHEN_abort_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("RUNNING")

        self.dae.abort_run()

    def test_GIVEN_in_running_state_WHEN_end_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("RUNNING")

        self.dae.end_run()

    def test_GIVEN_in_running_state_WHEN_store_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("RUNNING")

        self.dae.store_run()

    def test_GIVEN_in_running_state_WHEN_pause_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("RUNNING")

        self.dae.pause_run()

    def test_GIVEN_in_running_state_WHEN_resume_run_called_THEN_exception_thrown(self):
        self.set_run_state("RUNNING")

        with self.assertRaises(Exception):
            self.dae.resume_run()

    def test_GIVEN_in_paused_state_WHEN_begin_run_called_THEN_exception_thrown(self):
        self.set_run_state("PAUSED")

        with self.assertRaises(Exception):
            self.dae.begin_run()

    def test_GIVEN_in_paused_state_WHEN_abort_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("PAUSED")

        self.dae.abort_run()

    def test_GIVEN_in_paused_state_WHEN_end_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("PAUSED")

        self.dae.end_run()

    def test_GIVEN_in_paused_state_WHEN_store_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("PAUSED")

        self.dae.store_run()

    def test_GIVEN_in_paused_state_WHEN_pause_run_called_THEN_exception_thrown(self):
        self.set_run_state("PAUSED")

        with self.assertRaises(Exception):
            self.dae.pause_run()

    def test_GIVEN_in_ending_state_WHEN_end_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("ENDING")

        self.dae.end_run()

    def test_GIVEN_in_pausing_state_WHEN_pause_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("PAUSING")

        self.dae.pause_run()

    def test_GIVEN_in_paused_state_WHEN_resume_run_called_THEN_no_exception_thrown(self):
        self.set_run_state("PAUSED")

        self.dae.resume_run()

    def test_WHEN_get_detector_table_called_THEN_table_retrieved_from_xml(self):
        table = self.dae.get_table_path("Detector")

        self.assertEqual(table, DETECTOR_PATH)

    def test_WHEN_get_spectra_table_called_THEN_table_retrieved_from_xml(self):
        table = self.dae.get_table_path("Spectra")

        self.assertEqual(table, SPECTRA_PATH)

    def test_WHEN_get_wiring_table_called_THEN_table_retrieved_from_xml(self):
        table = self.dae.get_table_path("Wiring")

        self.assertEqual(table, WIRING_PATH)
