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

from mock import MagicMock, Mock

from genie_python.genie_blockserver import BlockServer
from genie_python.utilities import compress_and_hex


class TestGenieBlockserver(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_api.return_value.prefix_pv_name = Mock(side_effect=self._add_prefix)

        self.blockserver = BlockServer(self.mock_api.return_value)

    def test_WHEN_reloading_current_config_THEN_correct_pv_is_set(self):
        # Arrange
        expected_pv_name = self._add_prefix(self._add_blockserver_prefix("RELOAD_CURRENT_CONFIG"))
        expected_pv_value = compress_and_hex("1")
        expected_wait = True

        self.mock_api.return_value.set_pv_value.assert_not_called()

        # Act
        self.blockserver.reload_current_config()

        # Assert
        self.mock_api.return_value.set_pv_value.assert_called_once_with(
            expected_pv_name, expected_pv_value, expected_wait
        )

    def _add_prefix(self, name):
        return "TEST123" + name

    def _add_blockserver_prefix(self, name):
        return "CS:BLOCKSERVER:" + name
