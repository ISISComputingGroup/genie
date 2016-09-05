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

from genie_script_checker import ScriptChecker

try:
    import genie
    GENIE_FILENAME = genie.__file__
except ImportError:
    # if matplotlib is not installed just use a straight path
    GENIE_FILENAME = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir, "genie.py")


class TestScriptChecker(unittest.TestCase):
    def setUp(self):
        self.checker = ScriptChecker(GENIE_FILENAME)

    def tearDown(self):
        pass

    def test_GIVEN_script_containing_end_function_without_brakets_WHEN_check_THEN_error_message(self):
        script_lines = [
            "def test():",
            "  begin()",
            "  end"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 3: 'end' command without brackets"])

    def test_GIVEN_script_containing_end_not_as_a_function_WHEN_check_THEN_no_error_message(self):

        script_lines = [
            "def test():",
            "    endAngle = 1"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, [])

    def test_GIVEN_script_containing_end_without_brakets_at_start_of_line_WHEN_check_THEN_error_message(self):
        script_lines = [
            "end "]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 1: 'end' command without brackets"])

    def test_GIVEN_script_containing_end_without_brakets_on_line_with_good_command_WHEN_check_THEN_error_message(self):
        script_lines = [
            "begin(); end "]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 1: 'end' command without brackets"])

