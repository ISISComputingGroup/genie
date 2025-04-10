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

from hamcrest import assert_that, calling, is_, raises
from mock import MagicMock, patch
from parameterized import parameterized

from genie_python.channel_access_exceptions import UnableToConnectToPVException
from genie_python.genie_cachannel_wrapper import CaChannelWrapper as Wrapper
from genie_python.genie_epics_api import API


class TestEpicsApiSequence(unittest.TestCase):
    def setUp(self):
        # Patch the Wrapper used by the api
        wrapper_patch = patch("genie_python.genie_epics_api.Wrapper")
        # Make sure the patch is destroyed on teardown
        self.addCleanup(wrapper_patch.stop)
        # Create a mock from the patch
        self.mock_wrapper = wrapper_patch.start()

        self.counter = 0
        self.mock_pv_value = "Mock PV value"
        self.api = API("", None)
        self.mock_wrapper.get_pv_value = MagicMock(return_value=self.mock_pv_value)
        self.api.blockserver = MagicMock()

    def tearDown(self):
        pass

    def _increase_counter(self):
        self.counter += 1

    @staticmethod
    def mock_get_pv_value(pv_name, to_string):
        """
        Mock method for testing reading the alarm status of a PV.
        Args:
            pv_name: the name of the pv
            to_string: whether to convert the value to a string. Not used in this method, but included since the method
            it is mocking is called with this keyword argument.

        Returns:
            - A string saying "INVALID" if the pv name argument is ALARM_PV.SEVR.
            - A mock list of instruments if the pv name argument is CS:INSTLIST.
            - Otherwise it returns an exception.
        """
        if pv_name == "ALARM_PV.SEVR":
            return "INVALID"
        elif pv_name == "CS:INSTLIST":
            return [
                {
                    "name": "TEST1",
                    "hostName": "NDXTEST1",
                    "pvPrefix": "IN:TEST1:",
                    "isScheduled": True,
                    "groups": ["GROUP1"],
                },
                {
                    "name": "TEST2",
                    "hostName": "NDXTEST2",
                    "pvPrefix": "IN:TEST2:",
                    "isScheduled": True,
                    "groups": ["GROUP2"],
                },
                {
                    "name": "TEST3",
                    "hostName": "NDXTEST3",
                    "pvPrefix": "IN:TEST3:",
                    "isScheduled": False,
                    "groups": ["GROUP3"],
                },
            ]
        else:
            raise Exception

    def test_WHEN_reloading_current_config_THEN_command_is_delegated_to_blockserver(self):
        # Arrange
        self.api.blockserver.reload_current_config = MagicMock(side_effect=self._increase_counter)
        # Act
        self.api.reload_current_config()

        # Assert
        self.assertEqual(self.counter, 1)

    def test_GIVEN_list_of_one_element_with_PV_prefix_sample_WHEN_get_sample_pars_is_called_THEN_returns_a_one_element_dictionary_containing_the_PV_suffix_and_mock_value(
        self,
    ):
        # Arrange
        pv_prefix = "PARS:SAMPLE:"
        pv_suffix = "AOI"
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_sample_par_names = MagicMock(return_value=[pv_name])

        # Act
        val = self.api.get_sample_pars()

        # Assert
        self.assertEqual(len(val), 1)
        self.assertEqual(list(val.keys())[0], pv_suffix)
        self.assertEqual(val[pv_suffix], self.mock_pv_value)

    def test_GIVEN_list_of_one_element_with_PV_prefix_not_sample_WHEN_get_sample_pars_is_called_THEN_returns_an_empty_dictionary(
        self,
    ):
        # Arrange
        pv_prefix = "PARS:BL:"
        pv_suffix = "BEAMSTOP:POS"
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_sample_par_names = MagicMock(return_value=[pv_name])

        # Act
        val = self.api.get_sample_pars()

        # Assert
        self.assertEqual(len(val), 0)

    def test_GIVEN_list_of_one_element_with_PV_prefix_bl_WHEN_get_beamline_pars_is_called_THEN_returns_a_one_element_dictionary_containing_the_PV_suffix_and_mock_value(
        self,
    ):
        # Arrange
        pv_prefix = "PARS:BL:"
        pv_suffix = "JOURNAL:BLOCKS"
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_beamline_par_names = MagicMock(return_value=[pv_name])

        # Act
        val = self.api.get_beamline_pars()

        # Assert
        self.assertEqual(len(val), 1)
        self.assertEqual(list(val.keys())[0], pv_suffix)
        self.assertEqual(val[pv_suffix], self.mock_pv_value)

    def test_GIVEN_list_of_one_element_with_PV_prefix_not_bl_WHEN_get_beamline_pars_is_called_THEN_returns_an_empty_dictionary(
        self,
    ):
        # Arrange
        pv_prefix = "PARS:SAMPLE:"
        pv_suffix = "HEIGHT"
        pv_name = pv_prefix + pv_suffix
        self.api.blockserver.get_beamline_par_names = MagicMock(return_value=[pv_name])

        # Act
        val = self.api.get_beamline_pars()

        # Assert
        self.assertEqual(len(val), 0)

    def test_GIVEN_pv_name_WHEN_pv_connected_THEN_get_pv_alarm(self):
        self.api.get_pv_value = TestEpicsApiSequence.mock_get_pv_value

        self.assertEqual(self.api.get_pv_alarm("ALARM_PV"), "INVALID")

    def test_GIVEN_pv_name_WHEN_pv_not_connected_THEN_get_pv_alarm(self):
        self.api.get_pv_value = TestEpicsApiSequence.mock_get_pv_value

        self.assertEqual(self.api.get_pv_alarm("DISCONNECTED_PV"), "UNKNOWN")

    def test_GIVEN_api_is_imported_THEN_error_log_func_overwritten_on_wrapper(self):
        self.assertEqual(self.mock_wrapper.error_log_func, self.api.logger.log_ca_msg)


class TestEpicsApiSetInstrumentName(unittest.TestCase):
    def setUp(self):
        self.api = API("", None)

    def test_WHEN_machine_identifier_begins_ndx_THEN_instrument_is_name_without_ndx(self):
        # Act
        expected = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(
            "NDX" + expected
        )

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
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(
            "NDE" + expected
        )

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
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(
            "IN:" + expected + ":"
        )

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_in_colon_THEN_machine_name_is_machine_identifier(self):
        # Act
        name = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(
            "IN:" + name + ":"
        )

        # Assert
        self.assertEqual("NDX" + name, machine)

    def test_WHEN_machine_identifier_begins_with_instrument_prefix_THEN_pv_prefix_begins_with_the_colon(
        self,
    ):
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

    def test_WHEN_machine_identifier_begins_ndh_THEN_instrument_is_name_without_ndh(self):
        # Act
        expected = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(
            "NDH" + expected
        )

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_begins_ndh_THEN_machine_name_is_machine_identifier(self):
        # Act
        expected = "NDHNAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, machine)

    def test_WHEN_machine_identifier_begins_ndh_THEN_pv_prefix_begins_with_te_colon(self):
        # Act
        name = "NAME"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier("NDH" + name)
        expected = "TE:" + name + ":"

        # Assert
        self.assertEqual(expected, pv_prefix)

    def test_WHEN_machine_identifier_is_in_instrument_list_THEN_instrument_name_is_corrent(self):
        # Act
        name = "IN:TEST2:"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(name)
        expected = "TEST2"

        # Assert
        self.assertEqual(expected, instrument)

    def test_WHEN_machine_identifier_is_in_instrument_list_THEN_machine_name_is_corrent(self):
        # Act
        name = "IN:TEST2:"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(name)
        expected = "NDXTEST2"

        # Assert
        self.assertEqual(expected, machine)

    def test_WHEN_machine_identifier_is_in_instrument_list_THEN_pv_prefix_is_corrent(self):
        # Act
        expected = "IN:TEST2:"
        instrument, machine, pv_prefix = self.api._get_machine_details_from_identifier(expected)

        # Assert
        self.assertEqual(expected, pv_prefix)


class TestEpicsApiSMS(unittest.TestCase):
    def setUp(self):
        self.api = API("", None)

    def tearDown(self):
        pass

    def test_GIVEN_phone_number_WHEN_send_sms_THEN_requests_api_send_sms(self):
        # Arrange
        self.api._alert_http_request = MagicMock(return_value="OK")

        # Act
        self.api.send_sms("123", "test")

        # Assert
        self.api._alert_http_request.assert_called_once_with(mobiles="123", message="test")

    def test_GIVEN_email_address_WHEN_send_email_THEN_requests_api_send_email(self):
        # Arrange
        self.api._alert_http_request = MagicMock(return_value="OK")

        # Act
        self.api.send_email("a@b", "message")

        # Assert
        self.api._alert_http_request.assert_called_once_with(emails="a@b", message="message")

    def test_GIVEN_message_WHEN_send_alert_THEN_requests_api_send_alert(self):
        # Arrange
        self.api._alert_http_request = MagicMock(return_value="OK")

        # Act
        self.api.send_alert("message", "inst")

        # Assert
        self.api._alert_http_request.assert_called_once_with(inst="inst", message="message")


class TestPvMethods(unittest.TestCase):
    @patch("genie_python.genie_epics_api.GetExperimentData")
    def setUp(self, mock_sql):
        self.api = API(None, None)
        try:
            self.instrument_prefix = "TE:TEST:"
            self.api.set_instrument("TEST", globals())
        except Exception as e:
            if "init_test" not in str(e):
                raise

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_local_pv_value_THEN_pv_is_returned(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_wrapper_mock.pv_exists.return_value = True
        pv_wrapper_mock.get_pv_value.return_value = expected_value
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        result = self.api.get_pv_value(pv_name, is_local=True)

        assert_that(result, is_(expected_value))
        pv_wrapper_mock.get_pv_value.assert_called_with(expected_pv_name, False, use_numpy=None)

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_value_of_local_pv_with_local_prefix_on_start_THEN_pv_is_returned_and_pv_asked_for_has_only_one_prefix(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_wrapper_mock.pv_exists.return_value = True
        pv_wrapper_mock.get_pv_value.return_value = expected_value
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        result = self.api.get_pv_value(expected_pv_name, is_local=True)

        assert_that(result, is_(expected_value))
        pv_wrapper_mock.get_pv_value.assert_called_with(expected_pv_name, False, use_numpy=None)

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_global_pv_value_THEN_pv_is_returned(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_wrapper_mock.pv_exists.return_value = True
        pv_wrapper_mock.get_pv_value.return_value = expected_value
        expected_pv_name = "PV"

        result = self.api.get_pv_value(expected_pv_name)

        assert_that(result, is_(expected_value))
        pv_wrapper_mock.get_pv_value.assert_called_with(expected_pv_name, False, use_numpy=None)

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_pv_value_but_pv_does_not_exist_THEN_exception(
        self, pv_wrapper_mock: MagicMock
    ):
        pv_wrapper_mock.pv_exists.return_value = False

        assert_that(
            calling(self.api.get_pv_value).with_args("PV"), raises(UnableToConnectToPVException)
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_pv_value_but_wrapper_exception_THEN_exception_thrown(
        self, pv_wrapper_mock: MagicMock
    ):
        pv_wrapper_mock.get_pv_value.side_effect = ValueError()

        assert_that(calling(self.api.get_pv_value).with_args("PV"), raises(ValueError))
        assert_that(
            pv_wrapper_mock.get_pv_value.call_count,
            is_(3),
            "get pv call count, one for each attempt",
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_pv_value_wrapper_exception_on_first_trial_and_ok_on_second_THEN_value_returned(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_wrapper_mock.pv_exists.return_value = True
        pv_wrapper_mock.get_pv_value.side_effect = [ValueError(), expected_value]
        expected_pv_name = "PV"

        result = self.api.get_pv_value(expected_pv_name)

        assert_that(result, is_(expected_value))
        pv_wrapper_mock.get_pv_value.assert_called_with(expected_pv_name, False, use_numpy=None)
        assert_that(
            pv_wrapper_mock.get_pv_value.call_count,
            is_(2),
            "get pv call count, once for raise once for ok",
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_get_pv_value_raises_exception_except_on_last_trial_THEN_value_returned(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_wrapper_mock.pv_exists.return_value = True
        pv_wrapper_mock.get_pv_value.side_effect = [
            ValueError(),
            ValueError(),
            ValueError(),
            expected_value,
        ]
        expected_pv_name = "PV"

        result = self.api.get_pv_value(expected_pv_name, attempts=4)

        assert_that(result, is_(expected_value))
        pv_wrapper_mock.get_pv_value.assert_called_with(expected_pv_name, False, use_numpy=None)
        assert_that(
            pv_wrapper_mock.get_pv_value.call_count,
            is_(4),
            "get pv call count, once for raise once for ok",
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_set_local_pv_value_THEN_pv_is_set(self, pv_wrapper_mock: MagicMock):
        expected_value = 10
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        self.api.set_pv_value(pv_name, expected_value, is_local=True)

        pv_wrapper_mock.set_pv_value.assert_called_with(
            expected_pv_name, expected_value, wait=False
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_set_local_pv_value_with_inst_prefix_THEN_pv_is_set_pv_does_not_have_extra_prefix(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        self.api.set_pv_value(expected_pv_name, expected_value, is_local=True)

        pv_wrapper_mock.set_pv_value.assert_called_with(
            expected_pv_name, expected_value, wait=False
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_set_global_pv_value_THEN_pv_is_set(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        expected_pv_name = "PV"

        self.api.set_pv_value(expected_pv_name, expected_value, is_local=False)

        pv_wrapper_mock.set_pv_value.assert_called_with(
            expected_pv_name, expected_value, wait=False
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_set_local_pv_value_but_wrapper_exceptions_THEN_exception_thrown(
        self, pv_wrapper_mock: MagicMock
    ):
        pv_wrapper_mock.set_pv_value.side_effect = ValueError()
        expected_value = 10
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        assert_that(
            calling(self.api.set_pv_value).with_args(
                expected_pv_name, expected_value, is_local=True
            ),
            raises(ValueError),
        )
        assert_that(
            pv_wrapper_mock.set_pv_value.call_count,
            is_(3),
            "set pv call count, once for raise once for ok",
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_set_local_pv_value_but_wrapper_exception_on_first_trial_and_ok_on_second_THEN_pv_value_set(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        pv_wrapper_mock.set_pv_value.side_effect = [ValueError(), expected_value]

        self.api.set_pv_value(expected_pv_name, expected_value, is_local=True)

        pv_wrapper_mock.set_pv_value.assert_called_with(
            expected_pv_name, expected_value, wait=False
        )
        assert_that(
            pv_wrapper_mock.set_pv_value.call_count,
            is_(2),
            "set pv call count, once for raise once for ok",
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_mock_pv_WHEN_set_local_pv_value_raises_exception_except_on_last_trial_THEN_pv_value_set_called_attempt_times(
        self, pv_wrapper_mock: MagicMock
    ):
        expected_value = 10
        pv_name = "PV"
        expected_pv_name = "{}{}".format(self.instrument_prefix, pv_name)

        pv_wrapper_mock.set_pv_value.side_effect = [
            ValueError(),
            ValueError(),
            ValueError(),
            expected_value,
        ]

        self.api.set_pv_value(expected_pv_name, expected_value, is_local=True, attempts=4)

        pv_wrapper_mock.set_pv_value.assert_called_with(
            expected_pv_name, expected_value, wait=False
        )
        assert_that(
            pv_wrapper_mock.set_pv_value.call_count,
            is_(4),
            "set pv call count, once for raise once for ok",
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_block_pointing_at_field_WHEN_get_block_units_THEN_units_field_is_called(
        self, pv_wrapper_mock: MagicMock
    ):
        # Mock get_pv_from_block to return something with .SOMETHING on the end
        self.api.get_pv_from_block = MagicMock(return_value="PVNAME.SOMETHING")

        # Call get_block_units
        self.api.get_block_names = MagicMock(return_value=["TEST"])
        self.api.get_block_units("TEST")

        # Assert get_pv_value is called without the .SOMETHING
        pv_wrapper_mock.get_pv_value.assert_called_with("PVNAME.EGU")

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_block_already_pointing_at_unit_field_WHEN_get_block_units_THEN_units_field_is_called(
        self, pv_wrapper_mock: MagicMock
    ):
        # Mock get_pv_from_block to return something with .EGU at the end
        self.api.get_pv_from_block = MagicMock(return_value="PVNAME.EGU")

        # Call get_block_units
        self.api.get_block_names = MagicMock(return_value=["BLOCK_NAME"])
        self.api.get_block_units("BLOCK_NAME")

        # Assert get_pv_value is called without the extra .EGU (PVNAME.EGU and not PVNAME.EGU.EGU)
        pv_wrapper_mock.get_pv_value.assert_called_with("PVNAME.EGU")

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_block_not_pointing_at_field_WHEN_get_block_units_THEN_units_field_is_called(
        self, pv_wrapper_mock: MagicMock
    ):
        # Mock get_pv_from_block to return something without .SOMETHING at the end
        self.api.get_pv_from_block = MagicMock(return_value="PVNAME")

        # Call get_block_units
        self.api.get_block_names = MagicMock(return_value=["BLOCK_NAME"])
        self.api.get_block_units("BLOCK_NAME")

        # Assert get_pv_value is called with the .EGU
        pv_wrapper_mock.get_pv_value.assert_called_with("PVNAME.EGU")

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_block_not_found_WHEN_get_block_units_THEN_exception_is_raised(
        self, pv_wrapper_mock: MagicMock
    ):
        # Mock get_pv_from_block to return something without .SOMETHING at the end
        self.api.get_pv_from_block = MagicMock(return_value="PVNAME")

        # Set a different name than the one being called to existing block
        self.api.get_block_names = MagicMock(return_value=["DIFF_BLOCK_NAME"])
        self.api.block_exists = MagicMock(return_value=0)

        # Assert get_pv_value is called with the .EGU
        assert_that(calling(self.api.get_block_units).with_args("BLOCK_NAME"), raises(Exception))

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_pv_not_found_WHEN_get_block_units_THEN_exception_is_raised(
        self, pv_wrapper_mock: MagicMock
    ):
        # Mock get_pv_from_block to return something without .SOMETHING at the end
        self.api.get_pv_from_block = MagicMock(return_value="PVNAME")
        pv_name = self.api.get_pv_from_block

        # Set call to mock get_pv_value to raise an exception
        pv_wrapper_mock.get_pv_value.side_effect = UnableToConnectToPVException(pv_name, "err")

        # Set block names to avoid block not found exception
        self.api.get_block_names = MagicMock(return_value=["BLOCK_NAME"])

        # Assert get_pv_value is called with the .EGU
        assert_that(
            calling(self.api.get_block_units).with_args("BLOCK_NAME"),
            raises(UnableToConnectToPVException),
        )

    # Test that when units of char-type PV (STRING, CHAR, UCHAR, ENUM) requested, None is returned
    # (as these PVs don't usually have .EGU fields).
    @parameterized.expand(
        [
            "DBF_STRING",
            "DBF_CHAR",
            "DBF_UCHAR",
            "DBF_ENUM",
        ]
    )
    @patch("genie_python.genie_epics_api.Wrapper")
    def test_GIVEN_chartype_pv_WHEN_get_block_units_called_THEN_None_returned(
        self, field_type: str, pv_wrapper_mock: MagicMock
    ):
        # Mock get_pv_from_block to return something with .SOMETHING on the end
        self.api.get_pv_from_block = MagicMock(return_value="PVNAME.SOMETHING")

        # Mock return value for DBF type (integer) to string from genie api
        pv_wrapper_mock.dbf_type_to_string.return_value = field_type

        # Call get_block_units
        self.api.get_block_names = MagicMock(return_value=["TEST"])
        test_units = self.api.get_block_units("TEST")

        # Assert that returned units value is None
        self.assertEqual(test_units, None)


class TestSetBlockMethod(unittest.TestCase):
    @patch("genie_python.genie_epics_api.GetExperimentData")
    def setUp(self, sql_mock):
        self.api = API(None, None)
        try:
            self.instrument_prefix = "TE:TEST:"
            self.api.set_instrument("TEST", globals())
        except Exception as e:
            if "init_test" not in str(e):
                raise

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_WHEN_set_block_value_called_with_wait_THEN_setpoint_set_and_wait_for_called(
        self, pv_wrapper: Wrapper
    ):
        self.api.waitfor = MagicMock()

        self.api.set_block_value("TEST_BLOCK", 10, wait=True)
        pv_wrapper.set_pv_value.assert_called_with(
            self.api.get_pv_from_block("TEST_BLOCK") + ":SP", 10, wait=False
        )
        self.api.waitfor.start_waiting.assert_called()

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_WHEN_set_block_value_called_with_wait_and_high_low_THEN_wait_for_called_with_high_low(
        self, pv_wrapper: Wrapper
    ):
        self.api.waitfor = MagicMock()
        block_name, set_point = "TEST_BLOCK", 10
        lowlimit, highlimit = 8, 12

        self.api.set_block_value(
            block_name, set_point, wait=True, lowlimit=lowlimit, highlimit=highlimit
        )
        self.api.waitfor.start_waiting.assert_called_with(
            block_name, set_point, lowlimit, highlimit
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_WHEN_set_block_value_called_with_wait_and_high_low_incorrect_order_THEN_wait_for_called_with_high_low_correct_order(
        self, pv_wrapper: Wrapper
    ):
        self.api.waitfor = MagicMock()
        block_name, set_point = "TEST_BLOCK", 10
        lowlimit, highlimit = 12, 8

        self.api.set_block_value(
            block_name, set_point, wait=True, lowlimit=lowlimit, highlimit=highlimit
        )
        self.api.waitfor.start_waiting.assert_called_with(
            block_name, set_point, highlimit, lowlimit
        )

    @patch("genie_python.genie_epics_api.Wrapper")
    def test_WHEN_set_block_value_called_with_wait_and_high_low_THEN_wait_for_called_with_high_low_correct_order(
        self, pv_wrapper: Wrapper
    ):
        self.api.waitfor = MagicMock()
        block_name, set_point = "TEST_BLOCK", 10
        lowlimit, highlimit = 12, 8

        self.api.set_block_value(
            block_name, set_point, wait=True, lowlimit=lowlimit, highlimit=highlimit
        )
        self.api.waitfor.start_waiting.assert_called_with(
            block_name, set_point, highlimit, lowlimit
        )

    @parameterized.expand(
        [
            ("area_of_limits_above_sp", 12, 14, 10, True),
            ("area_of_limits_covers_sp", 8, 12, 10, False),
            ("area_of_limits_below_sp", 5, 7, 10, True),
        ]
    )
    @patch("genie_python.genie_epics_api.Wrapper")
    @patch("genie_python.genie_epics_api.print")
    def test_WHEN_set_block_value_called_with_wait_and_various_odd_high_lows_THEN_message_printed(
        self,
        _,
        low: int,
        high: int,
        val: int,
        should_warn: bool,
        mock_print: MagicMock,
        pv_wrapper: Wrapper,
    ):
        self.api.waitfor = MagicMock()
        block_name, set_point = "TEST_BLOCK", 10

        self.api.set_block_value(block_name, val, wait=True, lowlimit=low, highlimit=high)
        if should_warn:
            mock_print.assert_called_with(
                "Warning the range {} to {} does not cover setpoint of {}, may wait forever".format(
                    low, high, val
                )
            )
        else:
            mock_print.assert_not_called()
        pv_wrapper.set_pv_value.assert_called_with(
            self.api.get_pv_from_block("TEST_BLOCK") + ":SP", 10, wait=False
        )
        self.api.waitfor.start_waiting.assert_called_with(block_name, set_point, low, high)

    def test_GIVEN_non_existent_block_WHEN_get_block_data_called_THEN_raises(self):
        self.api.block_exists = MagicMock(return_value=False)
        self.assertRaises(Exception, self.api.get_block_data, "my_block")

    def test_GIVEN_non_existent_block_but_in_blockserver_names_WHEN_cget_called_THEN_returns_disconnected(
        self,
    ):
        test_block = "my_block"
        self.api.block_exists = MagicMock(return_value=False)
        self.api.get_block_names = MagicMock(return_value=[test_block])
        block_data = self.api.get_block_data("my_block")
        self.assertEqual(block_data["connected"], False)
        self.assertEqual(block_data["value"], None)

    def test_GIVEN_disconnected_block_WHEN_cget_called_THEN_still_tries_to_get_runcontrol_and_alarms(
        self,
    ):
        test_block = "my_block"
        expected_run_control = "YES", "0", "10"
        expected_alarm = "HIGH"
        self.api.block_exists = MagicMock(return_value=False)
        self.api.get_block_names = MagicMock(return_value=[test_block])
        self.api.get_runcontrol_settings = MagicMock(return_value=expected_run_control)
        self.api.get_alarm_from_block = MagicMock(return_value=expected_alarm)
        block_data = self.api.get_block_data("my_block")
        self.assertEqual(block_data["connected"], False)
        self.assertEqual(block_data["value"], None)
        self.assertEqual(block_data["alarm"], expected_alarm)
        self.assertEqual(block_data["runcontrol"], expected_run_control[0])
        self.assertEqual(block_data["lowlimit"], expected_run_control[1])
        self.assertEqual(block_data["highlimit"], expected_run_control[2])

    def test_GIVEN_disconnected_block_WHEN_cget_called_with_fail_fast_THEN_still_tries_to_get_runcontrol_but_not_alarms(
        self,
    ):
        test_block = "my_block"
        expected_run_control = "YES", "0", "10"
        self.api.block_exists = MagicMock(return_value=False)
        self.api.get_block_names = MagicMock(return_value=[test_block])
        self.api.get_runcontrol_settings = MagicMock(return_value=expected_run_control)
        self.api.get_alarm_from_block = MagicMock(return_value="HIGH")
        block_data = self.api.get_block_data("my_block", True)
        self.assertEqual(block_data["connected"], False)
        self.assertEqual(block_data["value"], None)
        self.assertEqual(block_data["alarm"], "UNKNOWN")
        self.assertFalse(self.api.get_alarm_from_block.called)
        self.assertEqual(block_data["runcontrol"], expected_run_control[0])
        self.assertEqual(block_data["lowlimit"], expected_run_control[1])
        self.assertEqual(block_data["highlimit"], expected_run_control[2])
