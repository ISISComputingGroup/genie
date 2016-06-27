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

os.environ['GENIE_SIMULATE'] = '1'

from genie import *


class TestSimulationSequence(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_original_block_values_are_remembered_when_changing_other_values(self):
        # Arrange
        cset(HCENTRE=2, runcontrol=True, lowlimit=2.5, highlimit=3)

        # Act
        cset(HCENTRE=2.6, wait=True)

        # Assert
        a = cget("HCENTRE")
        self.assertEquals(2.5, a["lowlimit"])
        self.assertEquals(3, a["highlimit"])
        self.assertEquals(True, a["runcontrol"])