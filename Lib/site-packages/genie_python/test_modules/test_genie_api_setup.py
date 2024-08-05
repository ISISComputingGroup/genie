"""
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
"""

from __future__ import absolute_import

import os
import unittest

from hamcrest import assert_that, is_
from mock import patch
from parameterized import parameterized

import genie_python.genie_api_setup
from genie_python.genie_api_setup import LoadScriptCompleter, log_command_and_handle_exception
from genie_python.utilities import get_correct_path

if os.name == "nt":
    DRIVE_ROOT_PREFIX = "c:"
else:
    DRIVE_ROOT_PREFIX = "/c"

SCRIPT_DIR = DRIVE_ROOT_PREFIX + "/scripts/"
DRIVE_ROOT = DRIVE_ROOT_PREFIX + os.sep


class TestGenieAutoCompletePyConsole(unittest.TestCase):
    RETURN_FROM_COMPLETER = ("", ["result"])

    def setUp(self):
        self.load_script = LoadScriptCompleter(self._completer_stub)
        genie_python.genie_api_setup._exceptions_raised = True
        # You can not use set script dir because it relies on the path existing
        genie_python.genie_api_setup.USER_SCRIPT_DIR = get_correct_path(SCRIPT_DIR)

    def tearDown(self):
        pass

    def _completer_stub(self, text=None, line_buffer=None, cursor_pos=None):
        return self.RETURN_FROM_COMPLETER

    def test_GIVEN_no_text_WHEN_auto_complete_THEN_return_contents_of_given_completer(self):
        # Arrange

        # Act
        result = self.load_script.pydev_complete(line_buffer="")

        # Assert

        assert_that(result, is_(self.RETURN_FROM_COMPLETER))

    def test_GIVEN_text_no_load_script_WHEN_auto_complete_THEN_return_contents_of_given_completer(
        self,
    ):
        # Arrange

        # Act
        result = self.load_script.pydev_complete(line_buffer="stuff is here")

        # Assert

        assert_that(result, is_(self.RETURN_FROM_COMPLETER))

    @parameterized.expand(
        [
            (os.path.join(DRIVE_ROOT, "scri"), DRIVE_ROOT_PREFIX + "/scripts", "scripts"),
            (os.path.join(DRIVE_ROOT, "scripts"), DRIVE_ROOT_PREFIX + "/scripts", "scripts"),
            (
                os.path.join(DRIVE_ROOT, "scripts"),
                DRIVE_ROOT_PREFIX + "/scripts/play.com",
                "scripts/play.com",
            ),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play."),
                DRIVE_ROOT_PREFIX + "/scripts/play.py",
                "py",
            ),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play.p"),
                DRIVE_ROOT_PREFIX + "/scripts/play.py",
                "py",
            ),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play "),
                DRIVE_ROOT_PREFIX + "/scripts/play - a.py",
                "- a.py",
            ),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play -"),
                DRIVE_ROOT_PREFIX + "/scripts/play - a.py",
                " a.py",
            ),
        ]
    )
    @patch("glob.glob")
    def test_GIVEN_line_starts_load_script_with_various_partial_paths_WHEN_auto_complete_THEN_return_contents_of_path_before_dot(
        self, search_path, filename_from_glob, expected_result, mock_glob
    ):
        # Arrange
        mock_glob.return_value = [filename_from_glob]
        expected_completer = (search_path, [expected_result])

        # Act
        result = self.load_script.pydev_complete(line_buffer=r'load_script("{}'.format(search_path))

        # Assert
        assert_that(result, is_(expected_completer))

    @patch("glob.glob")
    def test_GIVEN_line_with_g_dot_load_script_with_partial_path_WHEN_auto_complete_THEN_return_contents_of_path(
        self, mock_glob
    ):
        # Arrange
        search_path = DRIVE_ROOT_PREFIX + r"/scri"
        filenames = [r"scripts"]
        mock_glob.return_value = [DRIVE_ROOT_PREFIX + "/" + f for f in filenames]
        expected_completer = (search_path, [str(filename) for filename in filenames])

        # Act
        result = self.load_script.pydev_complete(
            line_buffer=r'g.load_script("{}'.format(search_path)
        )

        # Assert
        assert_that(result, is_(expected_completer))

    @patch("glob.glob")
    def test_GIVEN_line_with_load_script_with_no_matching_paths_WHEN_auto_complete_THEN_no_matches(
        self, mock_glob
    ):
        # Arrange
        search_path = os.path.join(DRIVE_ROOT, "scri")
        mock_glob.return_value = []
        expected_completer = (search_path, [])

        # Act
        result = self.load_script.pydev_complete(
            line_buffer=r'g.load_script("{}'.format(search_path)
        )

        # Assert
        assert_that(result, is_(expected_completer))

    @patch("glob.glob")
    def test_GIVEN_line_with_load_script_with_quote_WHEN_auto_complete_THEN_show_matches_with_quote(
        self, mock_glob
    ):
        # Arrange
        search_path = DRIVE_ROOT_PREFIX + "/scripts/"
        mock_glob.return_value = ["{}filename.py".format(SCRIPT_DIR)]
        expected_completer = (search_path, ["filename.py"])

        # Act
        result = self.load_script.pydev_complete(
            line_buffer=r"g.load_script({}".format(search_path)
        )

        # Assert
        assert_that(result, is_(expected_completer))


class TestGenieAutoCompletePyDev(unittest.TestCase):
    RETURN_FROM_COMPLETER = ("", ["result"])

    def setUp(self):
        self.load_script = LoadScriptCompleter(self._completer_stub)
        self.load_script.is_pydev = True
        genie_python.genie_api_setup._exceptions_raised = True

    def tearDown(self):
        pass

    def _completer_stub(self, text=None, line_buffer=None, cursor_pos=None):
        return self.RETURN_FROM_COMPLETER

    def test_GIVEN_no_text_WHEN_auto_complete_THEN_return_contents_of_given_completer(self):
        # Arrange

        # Act
        result = self.load_script.pydev_complete(line_buffer="")

        # Assert

        assert_that(result, is_(self.RETURN_FROM_COMPLETER))

    def test_GIVEN_text_no_load_script_WHEN_auto_complete_THEN_return_contents_of_given_completer(
        self,
    ):
        # Arrange

        # Act
        result = self.load_script.pydev_complete(line_buffer="stuff is here")

        # Assert

        assert_that(result, is_(self.RETURN_FROM_COMPLETER))

    @patch("glob.glob")
    def test_GIVEN_line_with_load_script_with_no_matching_paths_WHEN_auto_complete_THEN_no_matches(
        self, mock_glob
    ):
        # Arrange
        search_path = os.path.join(DRIVE_ROOT, "scri")
        mock_glob.return_value = []
        expected_completer = (search_path, [])

        # Act
        result = self.load_script.pydev_complete(
            line_buffer=r'g.load_script("{}'.format(search_path)
        )

        # Assert
        assert_that(result, is_(expected_completer))

    @parameterized.expand(
        [
            (
                os.path.join(DRIVE_ROOT, "scripts", "play."),
                DRIVE_ROOT_PREFIX + r"/scripts/play.py",
                "py",
            ),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play.p"),
                DRIVE_ROOT_PREFIX + r"/scripts/play.py",
                "py",
            ),
            (os.path.join(DRIVE_ROOT, "scri"), DRIVE_ROOT_PREFIX + r"/scripts", "scripts"),
            (os.path.join(DRIVE_ROOT, "scripts"), DRIVE_ROOT_PREFIX + r"/scripts", "scripts"),
            (os.path.join(DRIVE_ROOT, "scri"), DRIVE_ROOT_PREFIX + r"/scripts", "scripts"),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play "),
                os.path.join(DRIVE_ROOT, "scripts", "play - a.py"),
                "- a.py",
            ),
            (
                os.path.join(DRIVE_ROOT, "scripts", "play -"),
                os.path.join(DRIVE_ROOT, "scripts", "play - a.py"),
                " a.py",
            ),
        ]
    )
    @patch("glob.glob")
    def test_GIVEN_line_starts_load_script_with_various_partial_paths_WHEN_auto_complete_THEN_return_contents_of_path_from_dot(
        self, search_path, filename_from_glob, expected_result, mock_glob
    ):
        # Arrange
        mock_glob.return_value = [filename_from_glob]
        expected_completer = (search_path, [expected_result])

        # Act
        result = self.load_script.pydev_complete(line_buffer=r'load_script("{}'.format(search_path))

        # Assert
        assert_that(result, is_(expected_completer))

    @parameterized.expand(
        [
            ("", SCRIPT_DIR + "scripts.py", 'load_script("scripts.py'),
            ("sc", SCRIPT_DIR + "scripts.py", 'load_script("scripts.py'),
            ("scripts.py", SCRIPT_DIR + "scripts.py", "py"),
        ]
    )
    @patch("glob.glob")
    def test_GIVEN_line_starts_load_script_with_non_absolute_path_THEN_return_contents_of_scripting_dir(
        self, search_path, filename_from_glob, expected_result, mock_glob
    ):
        # Arrange
        mock_glob.return_value = [filename_from_glob]
        expected_completer = (DRIVE_ROOT_PREFIX + "/scripts/" + search_path, [expected_result])

        # Act
        result = self.load_script.pydev_complete(line_buffer=r'load_script("{}'.format(search_path))

        # Assert
        mock_glob.assert_called_with("{}{}*".format(SCRIPT_DIR, search_path))
        assert_that(result, is_(expected_completer))

    @patch("glob.glob")
    def test_GIVEN_line_starts_load_script_with_nothing_else_THEN_return_contents_of_scripting_dir_with_load_script(
        self, mock_glob
    ):
        # Arrange
        expected_result = '"play.py'
        mock_glob.return_value = ["{}play.py".format(SCRIPT_DIR)]
        expected_completer = (DRIVE_ROOT_PREFIX + "/scripts/", [expected_result])

        # Act
        result = self.load_script.pydev_complete(line_buffer=r"load_script(")

        # Assert
        mock_glob.assert_called_with("{}*".format(SCRIPT_DIR))
        assert_that(result, is_(expected_completer))


class TestLogAndExceptionDecorator(unittest.TestCase):
    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_that_raises_and_squshed_exceptions_WHEN_called_THEN_exception_squashed(
        self, logger
    ):
        genie_python.genie_api_setup._exceptions_raised = False

        @log_command_and_handle_exception
        def test_func():
            raise Exception()

        test_func()
        self.assertTrue(True)

    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_that_raises_and_no_squashed_exception_WHEN_called_THEN_exception_raised(
        self, logger
    ):
        genie_python.genie_api_setup._exceptions_raised = True

        @log_command_and_handle_exception
        def test_func():
            raise Exception()

        # self.assertRaises(Exception, test_func, ()) doesn't seem to work here?
        try:
            test_func()
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_WHEN_call_with_no_args_THEN_logs_name(self, logger):
        @log_command_and_handle_exception
        def test_func():
            pass

        test_func()
        logger.assert_called_with("test_func", {"kwargs": {}, "args": {}}, None, time_taken=0.0)

    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_WHEN_call_with_named_args_THEN_logs_name_and_args(self, logger):
        @log_command_and_handle_exception
        def test_func(arg_one, arg_two, arg_three):
            pass

        test_func(1, 2, 3)
        logger.assert_called_with(
            "test_func",
            {"kwargs": {}, "args": {"arg_one": 1, "arg_two": 2, "arg_three": 3}},
            None,
            time_taken=0.0,
        )

    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_WHEN_call_with_kwargs_THEN_logs_name_and_kwargs(self, logger):
        @log_command_and_handle_exception
        def test_func(**kwargs):
            pass

        test_func(kwarg_one=1, kwarg_two=2)
        logger.assert_called_with(
            "test_func",
            {"kwargs": {"kwarg_one": 1, "kwarg_two": 2}, "args": {}},
            None,
            time_taken=0.0,
        )

    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_WHEN_call_with_mixed_args_and_kwargs_THEN_logs_name_args_and_kwargs(
        self, logger
    ):
        @log_command_and_handle_exception
        def test_func(arg_one, **kwargs):
            pass

        test_func(1, kwarg_one=1, kwarg_two=2)
        logger.assert_called_with(
            "test_func",
            {"kwargs": {"kwarg_one": 1, "kwarg_two": 2}, "args": {"arg_one": 1}},
            None,
            time_taken=0.0,
        )

    @patch("genie_python.genie_api_setup.__api.logger.log_command")
    def test_GIVEN_decorated_method_WHEN_call_with_mixed_named_args_and_args_THEN_logs_args_without_name(
        self, logger
    ):
        @log_command_and_handle_exception
        def test_func(arg_one, *args):
            pass

        test_func(1, 2, 3)
        logger.assert_called_with(
            "test_func", {"kwargs": {}, "args": (1, 2, 3)}, None, time_taken=0.0
        )
