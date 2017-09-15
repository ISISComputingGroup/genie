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
from genie_epics_api import API


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
        self.api = API("", None)
        self.mock_wrapper.get_pv_value = MagicMock(return_value=self.mock_pv_value)
        API.blockserver = MagicMock()

    def tearDown(self):
        pass

    def _increase_counter(self):
        self.counter += 1

    def test_WHEN_reloading_current_config_THEN_command_is_delegated_to_blockserver(self):

        # Arrange
        API.blockserver.reload_current_config = MagicMock(side_effect=self._increase_counter)
        # Act
        self.api.reload_current_config()

        # Assert
        self.assertEquals(self.counter, 1)

    def test_GIVEN_list_of_one_element_with_PV_prefix_sample_WHEN_get_sample_pars_is_called_THEN_returns_a_one_element_dictionary_containing_the_PV_suffix_and_mock_value(self):
        # Arrange
        pv_prefix = u'PARS:SAMPLE:'
        pv_suffix = u'AOI'
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_sample_par_names = MagicMock(return_value=[pv_name])

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
        self.api.blockserver.get_sample_par_names = MagicMock(return_value=[pv_name])

        # Act
        val = self.api.get_sample_pars()

        # Assert
        self.assertEquals(len(val), 0)

    def test_GIVEN_list_of_one_element_with_PV_prefix_bl_WHEN_get_beamline_pars_is_called_THEN_returns_a_one_element_dictionary_containing_the_PV_suffix_and_mock_value(self):
        # Arrange
        pv_prefix = u'PARS:BL:'
        pv_suffix = u'JOURNAL:BLOCKS'
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_beamline_par_names = MagicMock(return_value=[pv_name])

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
        self.assertEquals(len(val), 0)


class TestEpicsApiSetInstrumentName(unittest.TestCase):
    def setUp(self):
        self.api = API("", None)

    def test_WHEN_machine_identifier_begins_ndx_THEN_instrument_is_name_without_ndx(self):
        # Act
        expected = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("NDX" + expected)

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_ndx_THEN_machine_name_is_machine_identifier(self):
        # Act
        expected = "NDXNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, machine)

    def test_WHEN_machine_identifier_begins_ndx_THEN_pv_prefix_begins_with_in_colon(self):
        # Act
        name = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("NDX" + name)
        expected = "IN:" + name + ":"

        # Assert
        self.assertEqual(expected, pv_prefix)

    def test_WHEN_machine_identifier_begins_ndw_THEN_instrument_is_same_as_name(self):
        # Act
        expected = "NDWNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_ndw_THEN_machine_name_is_machine_identifier(self):
        # Act
        expected = "NDWNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, machine)

    def test_WHEN_machine_identifier_begins_ndw_THEN_pv_prefix_begins_with_the_colon(self):
        # Act
        machine = "NDWname"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(machine)
        expected = "TE:" + machine + ":"

        # Assert
        self.assertEqual(expected, pv_prefix)

    def test_WHEN_machine_identifier_begins_nde_THEN_instrument_is_name_without_nde(self):
        # Act
        expected = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("NDE"+expected)

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_nde_THEN_machine_name_is_machine_identifier(self):
        # Act
        expected = "NDENAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, machine)

    def test_WHEN_machine_identifier_begins_nde_THEN_pv_prefix_begins_with_in_colon(self):
        # Act
        name = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("NDE" + name)
        expected = "IN:" + name + ":"

        # Assert
        self.assertEqual(expected, pv_prefix)

    def test_WHEN_machine_identifier_begins_ndlt_THEN_instrument_is_same_as_machine_name(self):
        # Act
        expected = "NDLTNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_ndlt_THEN_machine_name_is_machine_identifier(self):
        # Act
        expected = "NDLTNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, machine)

    def test_WHEN_machine_identifier_begins_in_colon_THEN_instrument_is_name_without_prefix(self):
        # Act
        expected = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("IN:" + expected + ":")

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_in_colon_THEN_machine_name_is_machine_identifier(self):
        # Act
        name = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("IN:" + name + ":")

        # Assert
        self.assertEqual("NDX" + name, machine)

    def test_WHEN_machine_identifier_begins_with_instrument_prefix_THEN_pv_prefix_begins_with_the_colon(self):
        # Act
        expected = "IN:NAME:"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, pv_prefix)

    def test_WHEN_machine_identifier_begins_ndlt_THEN_pv_prefix_begins_with_the_colon(self):
        # Act
        machine = "NDLTNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(machine)
        expected = "TE:" + machine + ":"

        # Assert
        self.assertEqual(expected, pv_prefix)
