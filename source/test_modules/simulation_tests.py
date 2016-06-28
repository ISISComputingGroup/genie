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
        try:
            genie.abort()
        except:
            pass

    def tearDown(self):
        pass

    def test_multiple_blocks_can_be_created_simultaneously(self):
        # Arrange
        genie.cset(a=100, b=200, c=300)

        # Act
        a = genie.cget("a")
        b = genie.cget("b")
        c = genie.cget("c")

        # Assert
        self.assertEquals(100, a["value"])
        self.assertEquals(200, b["value"])
        self.assertEquals(300, c["value"])

    def test_runcontrol_and_wait_cannot_be_set_true_simultaneously(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Cannot enable or disable runcontrol at the same time as setting a wait'):
            genie.cset(a=1, runcontrol=True, wait=True)

    def test_runcontrol_cannot_be_set_for_more_than_one_block_simultaneously(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Runcontrol settings can only be changed for one block at a time'):
            genie.cset(a=1, b=2, runcontrol=True)

    def test_wait_cannot_be_set_for_more_than_one_block_at_a_time(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Cannot wait for more than one block'):
            genie.cset(a=1, b=2, wait=True)

    ###################
    def test_GIVEN_runcontrol_values_WHEN_change_setpoint_values_THEN_retain_runcontrol_limits(self):
        # Arrange
        genie.cset(a=98, runcontrol=True, lowlimit=97, highlimit=99)

        # Act
        genie.cset(a=2, wait=True, lowlimit=1, highlimit=3)
        a = genie.cget("a")

        # Assert
        self.assertEquals(1, a["lowlimit"])
        self.assertEquals(3, a["highlimit"])

    def test_GIVEN_running_state_WHEN_begin_run_THEN_exception(self):
        # Arrange
        genie.begin()

        # Assert
        with self.assertRaisesRegexp(Exception, 'Can only begin run from SETUP'):
            genie.begin()

    def test_GIVEN_ended_state_WHEN_pause_run_THEN_exception(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Can only pause when RUNNING'):
            genie.pause()

    def test_GIVEN_ended_state_WHEN_end_run_THEN_exception(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Can only end when RUNNING or PAUSED'):
            genie.end()

    def test_GIVEN_ended_state_WHEN_abort_run_THEN_exception(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Can only abort when RUNNING or PAUSED'):
            genie.abort()

    def test_GIVEN_ended_state_WHEN_update_store_THEN_exception(self):
        # Assert
        with self.assertRaisesRegexp(Exception, 'Can only be called when RUNNING or PAUSED'):
            genie.updatestore()

    def test_GIVEN_period_WHEN_change_period_to_higher_value_THEN_exception(self):
        # Arrange
        period = genie.get_period()

        # Assert
        with self.assertRaisesRegexp(Exception, 'Cannot set period as it is higher than the number of periods'):
            genie.change_period(period + 1)