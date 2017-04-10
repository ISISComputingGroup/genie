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

    def test_GIVEN_end_without_brakets_WHEN_check_THEN_error_message(self):
        script_lines = [
            "def test():",
            "  begin()",
            "  end"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 3: 'end' command without brackets"])

    def test_GIVEN_end_as_start_of_another_word_WHEN_check_THEN_no_error_message(self):

        script_lines = [
            "def test():",
            "    endAngle = 1"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, [])

    def test_GIVEN_end_as_end_of_another_word_WHEN_check_THEN_no_error_message(self):

        script_lines = [
            "def test():",
            "    angle_end = 1"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, [])

    def test_GIVEN_end_without_brakets_at_start_of_line_WHEN_check_THEN_error_message(self):
        script_lines = [
            "end "]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 1: 'end' command without brackets"])

    def test_GIVEN_end_without_brackets_on_line_with_fn_with_brackets_WHEN_check_THEN_error_message(self):
        script_lines = [
            "begin(); end "]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 1: 'end' command without brackets"])

    def test_GIVEN_end_in_string_without_brakets_WHEN_check_THEN_no_message(self):
        script_lines = [
            "\" a string containing end \""]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, [])

    def test_GIVEN_end_between_strings_without_brakets_WHEN_check_THEN_error_message(self):
        script_lines = [
            "\" a string containing end \" end \" string in end\""]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, ["Line 1: 'end' command without brackets"])

    def test_GIVEN_end_in_comment_without_brakets_WHEN_check_THEN_no_message(self):
        script_lines = [
            "stuff # end \""]

        result = self.checker.check_script_lines(script_lines)

        self.assertEquals(result, [])

    def test_GIVEN_g_assignment_WHEN_check_THEN_warning_message(self):
        script_lines = ["g=1"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'g' assignment in line 1"])

    def test_GIVEN_g_assignment_after_whitespace_WHEN_check_THEN_warning_message(self):
        script_lines = ["  g=2"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'g' assignment in line 1"])

    def test_GIVEN_g_assignment_with_space_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["  g<= 3"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, [])

    def test_GIVEN_inst_assignment_with_point_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst.test=>4"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_with_space_between_assignment_and_value_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst = 5"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_with_2_symbols_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst+=6"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst=7"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_after_whitespace_WHEN_check_THEN_warning_message(self):
        script_lines = ["  inst=8"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_with_space_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["   inst= 9"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'inst' assignment in line 1"])

    def test_GIVEN_g_assignment_with_point_WHEN_check_THEN_warning_message(self):
        script_lines = ["g.test=10"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'g' assignment in line 1"])

    def test_GIVEN_g_assignment_with_space_between_assignment_and_value_WHEN_check_THEN_warning_message(self):
        script_lines = ["g = 11"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'g' assignment in line 1"])

    def test_GIVEN_g_assignment_with_2_symbols_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["g+=12"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'g' assignment in line 1"])

    def test_GIVEN_variable_assignment_with_g__WHEN_check_THEN_no_message(self):
        script_lines = ["going=13"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, [])

    def test_GIVEN_function_with_g_WHEN_check_THEN_no_message(self):
        script_lines = ["going()"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, [])

    def test_GIVEN_variable_assignment_with_inst__WHEN_check_THEN_no_message(self):
        script_lines = ["instrument=15"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, [])

    def test_GIVEN_function_with_inst_WHEN_check_THEN_no_message(self):
        script_lines = ["instrument()"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, [])

    def test_GIVEN_2_g_assignments_WHEN_check_THEN_warning_message(self):
        script_lines = ["g=16", "g=17"]

        result = self.checker.check_script_lines(script_lines, True)

        self.assertEquals(result, ["'g' assignment in line 1", "'g' assignment in line 2"])