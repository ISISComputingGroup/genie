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
import genie
import sys


class TestGenie(unittest.TestCase):
    def setUp(self):
        genie._exceptions_raised = True

    def tearDown(self):
        pass

    def test_GIVEN_no_script_WHEN_load_script_THEN_return_None(self):
        # Arrange

        # Act
        result = genie.load_script(None)

        # Assert
        self.assertIsNone(result)

    def test_GIVEN_error_script_WHEN_load_script_THEN_error(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error.py")

        # Act
        self.assertRaises(Exception, genie.load_script, script)

    def test_GIVEN_valid_script_WHEN_load_script_THEN_can_call_script(self):
        #Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "valid.py")

        # Act
        genie.load_script(script)

        #Assert
        self.assertTrue(genie.valid())

    def test_GIVEN_error_script_WHEN_load_script_THEN_script_folder_not_added_to_path(self):
        #Arrange
        directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts")
        script = os.path.join(directory, "error.py")

        # Act
        self.assertRaises(Exception, genie.load_script, script)

        #Assert
        self.assertTrue(directory not in sys.path)

    def test_GIVEN_valid_script_WHEN_load_script_THEN_script_folder_added_to_path(self):
        #Arrange
        directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts")
        script = os.path.join(directory, "valid.py")

        # Act
        genie.load_script(script)

        #Assert
        print "dir is: " + str(sys.path)
        self.assertTrue(directory in sys.path)


    def test_GIVEN_script_checker_error_WHEN_load_script_THEN_error(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error_for_script_checker.py")

        # Act
        self.assertRaises(Exception, genie.load_script, script)

    def test_GIVEN_script_checker_error_WHEN_load_script_without_script_checker_THEN_ok(self):
        # Arrange
        script = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_scripts", "error_for_script_checker.py")

        # Act
        genie.load_script(script, check_script=False)


