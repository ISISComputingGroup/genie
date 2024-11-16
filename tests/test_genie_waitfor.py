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

import sys
import unittest
from io import StringIO

from genie_python.genie_simulate_impl import API
from genie_python.genie_waitfor import WaitForController


class TestGenieWaitFor(unittest.TestCase):
    def setUp(self):
        self.genie_waitfor = WaitForController(API())

    def test_GIVEN_silent_waitfor_time_WHEN_waitfor_time_THEN_no_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(seconds=0, quiet=True)
        sys.stdout = sys.__stdout__
        self.assertIs("", capturedOutput.getvalue())

    def test_GIVEN_waitfor_time_WHEN_waitfor_time_THEN_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(seconds=0, quiet=False)
        sys.stdout = sys.__stdout__
        self.assertIsNot("", capturedOutput.getvalue())

    def test_GIVEN_silent_waitfor_uamps_WHEN_waitfor_uamps_THEN_no_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(uamps=0, quiet=True)
        sys.stdout = sys.__stdout__
        self.assertIs("", capturedOutput.getvalue())

    def test_GIVEN_waitfor_uamps_WHEN_waitfor_uamps_THEN_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(uamps=0, quiet=False)
        sys.stdout = sys.__stdout__
        self.assertIsNot("", capturedOutput.getvalue())

    def test_GIVEN_silent_waitfor_raw_frames_WHEN_waitfor_raw_frames_THEN_no_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(raw_frames=0, quiet=True)
        sys.stdout = sys.__stdout__
        self.assertIs("", capturedOutput.getvalue())

    def test_GIVEN_waitfor_raw_frames_WHEN_waitfor_raw_frames_THEN_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(raw_frames=0, quiet=False)
        sys.stdout = sys.__stdout__
        self.assertIsNot("", capturedOutput.getvalue())

    def test_GIVEN_silent_waitfor_mevents_WHEN_waitfor_mevents_THEN_no_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(mevents=0, quiet=True)
        sys.stdout = sys.__stdout__
        self.assertIs("", capturedOutput.getvalue())

    def test_GIVEN_waitfor_mevents_WHEN_waitfor_mevents_THEN_output(self):
        capturedOutput = StringIO()
        sys.stdout = capturedOutput
        self.genie_waitfor.start_waiting(mevents=0, quiet=False)
        sys.stdout = sys.__stdout__
        self.assertIsNot("", capturedOutput.getvalue())
