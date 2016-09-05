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

import imp

##import genie
from genie_script_checker import ScriptChecker


class TestScriptChecker(unittest.TestCase):
    def setUp(self):
        self.checker = ScriptChecker(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir, "genie.py"))
        ##TODO uncomment self.checker = ScriptChecker(genie.__file__)

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





#TODO delete
        # fpath = None
        # try:
        #     name = "example"
        #     directory = "C:\\temp"
        #     fpath, pathname, description = imp.find_module(name, [directory])
        #     imp.load_module(name, fpath, pathname, description)
        # except Exception as e:
        #     raise Exception(e)
        # finally:
        #     # Since we may exit via an exception, close fpath explicitly.
        #     if fpath is not None:
        #         fpath.close()
