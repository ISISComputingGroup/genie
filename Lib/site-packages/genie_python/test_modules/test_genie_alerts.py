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

import unittest

from mock import patch

import genie_python.genie_alerts
import genie_python.genie_api_setup
from genie_python import genie


class TestGenieAlerts(unittest.TestCase):
    def setUp(self):
        genie.set_instrument(None, import_instrument_init=False)
        genie_python.genie_api_setup._exceptions_raised = True

    @patch("genie_python.genie_alerts.__api.block_exists")
    @patch("genie_python.genie_alerts.__api.set_pv_value")
    def test_GIVEN_block_name_and_alert_range_THEN_alert_set(self, set_pv, block_exists):
        # Arrange
        block_exists.return_value = True
        genie_python.genie_alerts.set_range("block1", -5.0, 10.0)

        # Act
        block_exists.assert_called_with("block1")
        set_pv.assert_called()
        self.assertEqual(set_pv.call_args_list[0].args[1], -5.0)  # check value passed to PV
        self.assertEqual(set_pv.call_args_list[1].args[1], 10.0)  # check value passed to PV

    @patch("genie_python.genie_alerts.__api.set_pv_value")
    def test_GIVEN_emails_and_numbers_WHEN_details_set_THEN_details_set(self, set_pv):
        # Arrange
        genie_python.genie_alerts.set_sms(["123", "456"])
        genie_python.genie_alerts.set_email(["a@b", "c@d"])

        # Act
        set_pv.assert_called()
        self.assertEqual(set_pv.call_args_list[0].args[1], "123;456")  # check value passed to PV
        self.assertEqual(set_pv.call_args_list[1].args[1], "a@b;c@d")  # check value passed to PV

    @patch("genie_python.genie_alerts.__api.block_exists")
    @patch("genie_python.genie_alerts.__api.set_pv_value")
    def test_GIVEN_block_WHEN_set_enable_THEN_enabled(self, set_pv, block_exists):
        # Arrange
        block_exists.return_value = True
        genie_python.genie_alerts.enable("block1", True)

        # Act
        block_exists.assert_called_with("block1")
        set_pv.assert_called()
        self.assertEqual(set_pv.call_args_list[0].args[1], True)  # check value passed to PV

    @patch("genie_python.genie_alerts.__api.set_pv_value")
    def test_GIVEN_message_WHEN_details_set_THEN_message_send(self, set_pv):
        # Arrange
        genie_python.genie_alerts.send("hello")

        # Act
        set_pv.assert_called()
        self.assertEqual(set_pv.call_args_list[0].args[1], "hello")  # check value passed to PV
