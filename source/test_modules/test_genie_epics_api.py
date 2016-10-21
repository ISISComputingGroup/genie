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
from mock import MagicMock, patch
from genie_epics_api import API, ComputerDetails


class TestEpicsApiSequence(unittest.TestCase):
    def setUp(self):
        # Patch the Wrapper used by the api
        wrapper_patch = patch("genie_epics_api.Wrapper")
        # Make sure the patch is destroyed on teardown
        self.addCleanup(wrapper_patch.stop)
        # Create a mock from the patch
        self.mock_wrapper = wrapper_patch.start()

        self.counter = 0
        self.mock_pv_value = "Mock PV value"
        self.api = API("",None)
        self.mock_wrapper.get_pv_value = MagicMock(return_value = self.mock_pv_value)
        API.blockserver = MagicMock()


    def tearDown(self):
        pass

    def _increase_counter(self):
        self.counter += 1

    def test_WHEN_reloading_current_config_THEN_command_is_delegated_to_blockserver(self):

        # Arrange
        API.blockserver.reload_current_config = MagicMock(side_effect = self._increase_counter)

        # Act
        self.api.reload_current_config()

        # Assert
        self.assertEquals(self.counter, 1)

    def test_GIVEN_list_of_one_element_with_PV_prefix_sample_WHEN_get_sample_pars_is_called_THEN_returns_a_one_element_dictionary_containing_the_PV_suffix_and_mock_value(self):

        # Arrange
        pv_prefix = u'PARS:SAMPLE:'
        pv_suffix = u'AOI'
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_sample_par_names = MagicMock(return_value = [pv_name])

        # Act
        val = self.api.get_sample_pars()

        # Assert
        self.assertEquals(len(val), 1)
        self.assertEquals(val.keys()[0], pv_suffix)
        self.assertEquals(val[pv_suffix], self.mock_pv_value)

    def test_GIVEN_list_of_one_element_with_PV_prefix_not_sample_WHEN_get_sample_pars_is_called_THEN_returns_an_empty_dictionary(self):

        # Arrange
        pv_prefix = u'PARS:BL:'
        pv_suffix = u'BEAMSTOP:POS'
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_sample_par_names = MagicMock(return_value = [pv_name])

        # Act
        val = self.api.get_sample_pars()

        # Assert
        self.assertEquals(len(val),0)

    def test_GIVEN_list_of_one_element_with_PV_prefix_bl_WHEN_get_beamline_pars_is_called_THEN_returns_a_one_element_dictionary_containing_the_PV_suffix_and_mock_value(self):

        # Arrange
        pv_prefix = u'PARS:BL:'
        pv_suffix = u'JOURNAL:BLOCKS'
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_beamline_par_names = MagicMock(return_value = [pv_name])

        # Act
        val = self.api.get_beamline_pars()

        # Assert
        self.assertEquals(len(val), 1)
        self.assertEquals(val.keys()[0], pv_suffix)
        self.assertEquals(val[pv_suffix], self.mock_pv_value)

    def test_GIVEN_list_of_one_element_with_PV_prefix_not_bl_WHEN_get_beamline_pars_is_called_THEN_returns_an_empty_dictionary(self):

        # Arrange
        pv_prefix = u'PARS:SAMPLE:'
        pv_suffix = u'HEIGHT'
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_beamline_par_names = MagicMock(return_value=[pv_name])

        # Act
        val = self.api.get_beamline_pars()

        # Assert
        self.assertEquals(len(val),0)


class TestEpicsApiSetInstrumentName(unittest.TestCase):

    def prefix_set_and_check(self, pv_prefix_to_set, expected_pv_prefix, host_name="host"):

        computer_details = ComputerDetails(host_name)
        api = API(None, None, computer_details=computer_details)
        api.set_instrument(pv_prefix_to_set, None)
        result = api.prefix_pv_name("")
        self.assertEqual(result,
                         expected_pv_prefix,
                         'Expected "{expected}" was "{actual}"'.format(expected=expected_pv_prefix, actual=result))

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_WHEN_standard_instrument_WHEN_inst_set_THEN_name_recognised(self):
        pv_prefix_to_set = "LARMOR"
        expected_pv_prefix = "IN:{0}:".format(pv_prefix_to_set)
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_in_WHEN_inst_set_THEN_instrument_set_as_expected(self):
        pv_prefix_to_set = "IN:LARMOR:"
        expected_pv_prefix = "IN:LARMOR:"
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_in_lower_case_WHEN_inst_set_THEN_instrument_prefix_is_capitalised(self):
        pv_prefix_to_set = "in:larmor:"
        expected_pv_prefix = "IN:LARMOR:"
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_doesnt_end_in_colon_WHEN_inst_set_THEN_extra_colon_added_to_prefix(self):
        pv_prefix_to_set = "In:Larmor"
        expected_pv_prefix = "IN:LARMOR:"
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_ndx_WHEN_inst_set_THEN_instrument_set_as_expected(self):
        pv_prefix_to_set = "NDXLARMOR:"
        expected_pv_prefix = "IN:LARMOR:"
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_is_not_recognised_WHEN_inst_set_THEN_prefix_is_unaltered(self):
        pv_prefix_to_set = "unrecognised:pvprefix:"
        expected_pv_prefix = pv_prefix_to_set
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_ndw_with_short_name_WHEN_inst_set_THEN_instrument_set_as_NDW_in_TE(self):

        pv_prefix_to_set = "NDWBLAH"
        expected_pv_prefix = "TE:{0}:".format(pv_prefix_to_set)

        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_ndw_with_long_name_WHEN_inst_set_THEN_instrument_set_as_NDW_with_CRC_in_TE(self):

        pv_prefix_to_set = "NDWBLAH_REALLY_LONG"
        expected_pv_prefix = "TE:NDWBLA3C:"

        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_ndx_with_long_name_WHEN_inst_set_THEN_instrument_set_as_NDW_with_CRC_in_IN(self):

        pv_prefix_to_set = "NDXBLAH_REALLY_LONG"
        expected_pv_prefix = "IN:BLAH_R32:"

        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_nde_WHEN_inst_set_THEN_instrument_set_as_expected(self):
        pv_prefix_to_set = "NDELARMOR"
        expected_pv_prefix = "IN:LARMOR:"
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)

    def test_WHEN_prefix_starts_with_te_WHEN_inst_set_THEN_instrument_set_as_expected(self):
        pv_prefix_to_set = "TE:TESTNAME:"
        expected_pv_prefix = "TE:TESTNAME:"
        self.prefix_set_and_check(pv_prefix_to_set, expected_pv_prefix)
