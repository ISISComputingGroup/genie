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
import os
import unittest
from genie_simulate import API

os.environ['GENIE_SIMULATE'] = '1'


class TestSimulationSequence(unittest.TestCase):
    def setUp(self):
        self.api = API()
        pass

    def tearDown(self):
        pass

    def test_GIVEN_preexisting_block_WHEN_updating_values_THEN_update_values_and_retain_non_specified_values(self):
        # Arrange
        self.api.set_block_value('block', 2, True, 2.5, 3)

        # Act
        self.api.set_block_value('block', 2.6, None, None, None, True)
        rc = self.api.get_runcontrol_settings('block')

        # Assert
        self.assertEquals(2.5, rc['LOW'])
        self.assertEquals(3, rc["HIGH"])
        self.assertEquals(True, rc["ENABLE"])

    def test_GIVEN_preexisting_block_WHEN_set_no_values_THEN_retain_original_values(self):
        # Arrange
        self.api.set_block_value('block', 3, False, 1.5, 6)

        # Act
        self.api.set_block_value('block')
        rc = self.api.get_runcontrol_settings('block')

        # Assert
        self.assertEquals(1.5, rc['LOW'])
        self.assertEquals(6, rc["HIGH"])
        self.assertEquals(False, rc["ENABLE"])

    def test_GIVEN_no_preexisting_blocks_WHEN_set_values_for_a_block_THEN_set_values(self):
        # Arrange
        self.api.set_block_value('block', 1, False, 0.5)

        # Act
        rc = self.api.get_runcontrol_settings('block')

        # Assert
        self.assertEquals(0.5, rc['LOW'])
        self.assertEquals(None, rc["HIGH"])
        self.assertEquals(False, rc["ENABLE"])