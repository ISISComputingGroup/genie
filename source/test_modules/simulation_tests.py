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

import genie


class TestSimulationSequence(unittest.TestCase):
    def setUp(self):
        genie._exceptions_raised = True

    def tearDown(self):
        pass

    def test_multiple_blocks_can_be_created_simultaneously(self):
        # Arrange
        genie.cset(block_a=100, block_b=200, block_c=300)

        # Act
        a = genie.cget("block_a")
        b = genie.cget("block_b")
        c = genie.cget("block_c")

        #Assert
        self.assertEquals(100, a["value"])
        self.assertEquals(200, b["value"])
        self.assertEquals(300, c["value"])

    def test_runcontrol_and_wait_cannot_be_set_true_simultaneously(self):
        pass

    def test_runcontrol_cannot_be_set_for_more_than_one_block_simultaneously(self):
        pass

    def test_begin_can_only_be_used_when_running_or_paused(self):
        pass

    def test_pause_can_only_be_used_when_running(self):
        pass

    def test_end_can_only_be_used_when_running_or_paused(self):
        #with self.assertRaisesRegexp(Exception, '.*only.*'):
            genie.end()

    def test_abort_can_only_be_used_when_running_or_paused(self):
        pass

