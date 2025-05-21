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

import builtins
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

import astroid

from genie_python.genie_epics_api import API
from genie_python.genie_script_checker import ScriptChecker
from genie_python.testing_utils.script_checker import (
    CreateTempScriptAndReturnErrors,
    write_to_temp_file,
)


class TestScriptChecker(unittest.TestCase):
    def setUp(self):
        self.checker = ScriptChecker()
        self.api = API("", None)
        self.instrument, self.machine, self.pv_prefix = (
            self.api._get_machine_details_from_identifier(None)
        )
        file_path = os.path.join("C:\\", "Instrument", "Settings", "config", self.machine, "Python")
        sys.path.append(file_path)

    def tearDown(self):
        pass

    def assertSymbolsDefined(self, script_lines, expected_symbols):
        dir_path = tempfile.mkdtemp()
        write_to_temp_file(script_lines, suffix=".py", dir=dir_path)
        result = self.checker.get_inst_attributes(dir_path)
        shutil.rmtree(dir_path)
        self.assertEqual(result, expected_symbols)

    def test_GIVEN_end_without_brackets_WHEN_check_THEN_error_message(self):
        script_lines = [
            "from genie_python import genie as g\ndef test():\n",
            "   g.begin()\n",
            "   g.end\n",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(
                errors, ["W:  4: Statement seems to have no effect (pointless-statement)"]
            )

    def test_GIVEN_end_as_start_of_another_word_WHEN_check_THEN_no_error_message(self):
        script_lines = ["from genie_python import genie as g\ndef test():\n", "    endAngle = 1"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_end_as_end_of_another_word_WHEN_check_THEN_no_error_message(self):
        script_lines = [
            "from genie_python import genie as g\ndef test():\n",
            "    angle_end = 1",
        ]

        with CreateTempScriptAndReturnErrors(
            self.checker, self.machine, script_lines, no_pyright=True
        ) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_end_without_brackets_at_start_of_line_WHEN_check_THEN_error_message(self):
        script_lines = ["from genie_python import genie as g\ndef test():\n   g.end"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(
                errors, ["W:  3: Statement seems to have no effect (pointless-statement)"]
            )

    def test_GIVEN_end_without_brackets_on_line_with_fn_with_brackets_WHEN_check_THEN_error_message(
        self,
    ):
        script_lines = ["from genie_python import genie as g\ng.begin(); g.end "]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(
                errors, ["W:  2: Statement seems to have no effect (pointless-statement)"]
            )

    def test_GIVEN_end_in_string_without_brackets_WHEN_check_THEN_no_message(self):
        script_lines = ['def test():\n   " a string containing end "']

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_end_in_comment_without_brackets_WHEN_check_THEN_no_message(self):
        script_lines = ["def test():\n", '   "stuff" # end "']

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_g_assignment_WHEN_check_THEN_warning_message(self):
        script_lines = ["from genie_python import genie as g", "g=1"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  2: 'g' assignment in line 2"])

    def test_GIVEN_g_assignment_after_whitespace_WHEN_check_THEN_warning_message(self):
        script_lines = ["g=2"]
        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'g' assignment in line 1"])

    def test_GIVEN_g_assignment_with_space_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["g<= 3"]
        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, [])

    def test_GIVEN_inst_assignment_with_point_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst.test=>4"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_with_space_between_assignment_and_value_WHEN_check_THEN_warning_message(
        self,
    ):
        script_lines = ["inst = 5"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_with_2_symbols_before_number_WHEN_check_THEN_warning_message(
        self,
    ):
        script_lines = ["inst+=6"]
        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst=7"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_after_whitespace_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst=8"]

        result = self.checker.check_script_lines(script_lines)
        self.assertEqual(result, ["W:  1: 'inst' assignment in line 1"])

    def test_GIVEN_inst_assignment_with_space_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["inst= 9"]
        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'inst' assignment in line 1"])

    def test_GIVEN_g_assignment_with_point_WHEN_check_THEN_warning_message(self):
        script_lines = ["g.cset=10"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'g' assignment in line 1"])

    def test_GIVEN_g_assignment_with_space_between_assignment_and_value_WHEN_check_THEN_warning_message(
        self,
    ):
        script_lines = ["g = 11"]

        result = self.checker.check_script_lines(script_lines)

        self.assertEqual(result, ["W:  1: 'g' assignment in line 1"])

    def test_GIVEN_g_assignment_with_2_symbols_before_number_WHEN_check_THEN_warning_message(self):
        script_lines = ["from genie_python import genie as g\n", "def test():\n", "   g+=12"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, ["W:  3: 'g' assignment in line 3"])

    def test_GIVEN_variable_assignment_with_g__WHEN_check_THEN_no_message(self):
        script_lines = ["going=13"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_function_with_g_WHEN_check_THEN_warn_user(self):
        script_lines = ["from genie_python import genie as g\ndef test():\n   g.test_function()\n"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(
                errors,
                ["E:  3: Module 'genie_python.genie' has no 'test_function' member (no-member)"],
            )

    def test_GIVEN_2_g_assignments_WHEN_check_THEN_warning_message(self):
        script_lines = [
            "from genie_python import genie as g\ndef test():\n    g=16\n",
            "    g=17",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(
                errors, ["W:  3: 'g' assignment in line 3", "W:  4: 'g' assignment in line 4"]
            )

    def test_GIVEN_g_non_existing_command_WHEN_call_THEN_error_message(self):
        script_lines = ["from genie_python import genie as g\ndef test():\n  g.aitfor_time(10)"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(
                errors,
                [
                    "E:  3: Module 'genie_python.genie' has no "
                    "'aitfor_time' member; maybe 'waitfor_time'? (no-member)"
                ],
            )

    def test_GIVEN_class_definition_WHEN_get_inst_attributes_THEN_class_name_and_attributes_defined(
        self,
    ):
        script_lines = [
            "class TestClass(Object):\n",
            "    def __init__(self):\n",
            "        self.a = 10",
        ]

        self.assertSymbolsDefined(script_lines, "inst.TestClass,inst.TestClass.a")

    def test_GIVEN_method_definition_WHEN_get_inst_attributes_THEN_only_method_name_defined(self):
        script_lines = ["def testMethod():\n", "    b = 10"]

        self.assertSymbolsDefined(script_lines, "inst.testMethod")

    def test_GIVEN_variable_assignment_WHEN_get_inst_attributes_THEN_variable_defined(self):
        script_lines = ["a = 10"]

        self.assertSymbolsDefined(script_lines, "inst.a")

    def test_GIVEN_nested_variable_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(self):
        script_lines = ["a = b = 10"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b")

    @unittest.skipIf(sys.version_info[0] < 3, "Starred assignments are not supported in Python 2")
    def test_GIVEN_starred_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(self):
        script_lines = ["a, *b, c = range(5)"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b,inst.c")

    def test_GIVEN_unparenthesized_tuple_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(
        self,
    ):
        script_lines = ["a,b = 1,2"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b")

    def test_GIVEN_parenthesized_tuple_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(
        self,
    ):
        script_lines = ["(a,b) = (1,2)"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b")

    def test_GIVEN_nested_tuple_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(self):
        script_lines = ["((a,b),c) = ((1,2),3)"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b,inst.c")

    def test_GIVEN_list_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(self):
        script_lines = ["[a,b] = [1,2]"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b")

    def test_GIVEN_nested_list_assignment_WHEN_get_inst_attributes_THEN_all_vars_defined(self):
        script_lines = ["[[a,b],c] = [[1,2],3]"]

        self.assertSymbolsDefined(script_lines, "inst.a,inst.b,inst.c")

    def test_GIVEN_index_subscript_assignment_WHEN_get_inst_attributes_THEN_no_symbols_defined(
        self,
    ):
        script_lines = ["list[0] = 1"]

        self.assertSymbolsDefined(script_lines, "")

    def test_GIVEN_list_definition_and_index_subscript_assignment_WHEN_get_inst_attributes_THEN_only_list_defined(
        self,
    ):
        script_lines = ["list = []\n", "list[0] = 1"]

        self.assertSymbolsDefined(script_lines, "inst.list")

    def test_GIVEN_key_subscript_assignment_WHEN_get_inst_attributes_THEN_no_symbols_defined(self):
        script_lines = ["dict['a'] = 1"]

        self.assertSymbolsDefined(script_lines, "")

    def test_GIVEN_dict_definition_and_subscript_assignment_WHEN_get_inst_attributes_THEN_only_dict_defined(
        self,
    ):
        script_lines = ["dict = {}\n", "dict['a'] = 1"]

        self.assertSymbolsDefined(script_lines, "inst.dict")

    def test_GIVEN_slice_subscript_assignment_WHEN_get_inst_attributes_THEN_no_symbols_defined(
        self,
    ):
        script_lines = ["list[0:2] = [8,9]"]

        self.assertSymbolsDefined(script_lines, "")

    def test_GIVEN_list_definition_and_slice_subscript_assignment_WHEN_get_inst_attributes_THEN_only_list_defined(
        self,
    ):
        script_lines = ["list = []\n", "list[0:2] = [8,9]"]

        self.assertSymbolsDefined(script_lines, "inst.list")

    def test_GIVEN_attribute_assignment_WHEN_get_inst_attributes_THEN_attribute_defined(self):
        script_lines = ["test.a = 1"]

        self.assertSymbolsDefined(script_lines, "inst.test.a")

    def test_GIVEN_nested_attribute_assignment_WHEN_get_inst_attributes_THEN_attribute_defined(
        self,
    ):
        script_lines = ["test1.test2.a = 1"]

        self.assertSymbolsDefined(script_lines, "inst.test1.test2.a")

    def test_GIVEN_complex_assignment_WHEN_get_inst_attributes_THEN_all_symbols_defined(self):
        script_lines = ["[[dict['a'], test1.test2.b], c], test1.d = [[1,2], 3], 4"]

        self.assertSymbolsDefined(script_lines, "inst.test1.test2.b,inst.c,inst.test1.d")

    @unittest.skipIf(sys.version_info[0] < 3, "Starred assignments are not supported in Python 2")
    def test_GIVEN_starred_complex_assignment_WHEN_get_inst_attributes_THEN_all_symbols_defined(
        self,
    ):
        script_lines = ["[[dict['a'], *test1.test2.b], c], test1.d = [range(5), 6], 7"]

        self.assertSymbolsDefined(script_lines, "inst.test1.test2.b,inst.c,inst.test1.d")

    def test_GIVEN_inst_script_wrong_path_WHEN_call_THEN_give_empty_error(self):
        dir_path = os.path.join("C:\\", "this", "path", "does", "not", "exist")
        result = self.checker.get_inst_attributes(dir_path)
        self.assertEqual(result, "")

    def test_GIVEN_invalid_python_expr_WHEN_call_check_THEN_error(self):
        script_lines = ["my_expr ="]
        expected = "E:  1: Parsing failed: 'invalid syntax"

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertTrue(
                errors[0].startswith(expected),
                f"Result was {errors}, expected first line to start with {expected}",
            )

    def test_GIVEN_valid_python_expr_WHEN_call_check_THEN_no_error(self):
        script_lines = ["my_expr = {}"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_valid_python_class_WHEN_call_check_THEN_no_error(self):
        script_lines = ["class MyClass():", "pass"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_invalid_python_class_WHEN_call_check_THEN_error(self):
        script_lines = ["class MyClass():"]
        expected = "E:  1: Parsing failed: 'expected an indented block"

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertTrue(
                errors[0].startswith(expected),
                f'Result was "{errors[0]}", expected first line to start with "{expected}"',
            )

    def test_GIVEN_builtin_module_THEN_it_can_safely_be_cached(self):
        # The module itself is irrelevant for this check so we can pass None as the module.
        self.assertTrue(self.checker._can_cache_module(builtins.__name__, None))

    def test_GIVEN_site_packages_module_THEN_it_can_safely_be_cached(self):
        import numpy

        mod = astroid.Module(numpy.__name__, numpy.__file__)
        self.assertTrue(self.checker._can_cache_module("numpy", mod))

    def test_GIVEN_user_script_THEN_it_should_not_be_cached(self):
        name = "my_user_script"
        mod = astroid.Module(name, os.path.join("C:\\", "scripts", "my_user_script.py"))
        self.assertFalse(self.checker._can_cache_module(name, mod))

    def test_GIVEN_instrument_script_THEN_it_should_not_be_cached(self):
        name = "my_inst_script"
        mod = astroid.Module(
            name,
            os.path.join(
                "C:\\",
                "Instrument",
                "Settings",
                "config",
                "UNITTEST",
                "Python",
                "inst",
                "my_inst_script.py",
            ),
        )
        self.assertFalse(self.checker._can_cache_module(name, mod))

    ### Start of pyright tests

    def test_GIVEN_invalid_range_THEN_pyright_throws_exception(self):
        script_lines = ["def wrong():\n", "    for i in range(1, 3.5):\n", "        print(i)\n"]

        expected = "E: 2: Argument of type"

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertTrue(errors[0].startswith(expected))

    def test_GIVEN_invalid_var_type_THEN_pyright_throws_exception(self):
        script_lines = ["c: int | float = 3.4\n", "c = None\n"]

        expected = "not assignable"

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertTrue(expected in errors[0])

    def test_GIVEN_two_get_pv_calls_with_arithmetic_operators_THEN_no_error(self):
        script_lines = [
            "from genie_python import genie as g\n",
            "a = g.get_pv('...')\n",
            "b = g.get_pv('...')\n",
            "added = a + b\n",
            "subtracted = a - b\n",
            "multiplied = a * b\n",
            "divided = a / b\n",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertListEqual(errors, [])

    def test_GIVEN_new_directory_WHEN_pyright_script_checker_called_THEN_pyright_json_created_then_destroyed_after_use(
        self,
    ):
        temp_dir = tempfile.mkdtemp()

        json_file = os.path.join(temp_dir, "pyrightconfig.json")

        with self.checker._TemporaryPyrightConfig(temp_dir, self.instrument):
            self.assertTrue(os.path.exists(json_file))

        self.assertFalse(os.path.exists(json_file))

        shutil.rmtree(temp_dir)

    def test_GIVEN_invalid_genie_script_WHEN_pyright_script_checker_called_THEN_pyright_throws_exception(
        self,
    ):
        script_lines = [
            "from genie_python import genie as g\n",
            "def test_genie():\n",
            "   g.begin(1,2,3,4,5,6,7,8,9)\n",
        ]

        expected = "E: 3: Argument of type"

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertTrue(errors[0].startswith(expected))

    # Test that if linter fails then pyright does not run
    # Supply a script that fails in both pylint and pyright but for different reasons
    def test_GIVEN_that_pylint_fails_THEN_pyright_is_not_ran(self):
        script_lines = [
            "class Example:",
            "   def __init__(self, value):",
            "       self.value = value",
            "   def add(self, x):",
            "       return self.value + x",
            "   def example_usage():",
            "       example = Example(42)",
            "       example.add('10')",
        ]
        expected = "E:  1: Parsing failed: 'invalid syntax"

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertTrue(
                errors[0].startswith(expected) and len(errors) == 1
            )  # Will be count of 2 if pyright still runs

    # Test that if no_pyright is true when calling check_script then pyright will not run
    # Passes a script that will usually fail for pyright but not for pylint
    def test_GIVEN_invalid_genie_script_WHEN_pyright_script_checker_called_with_no_pyiright_as_true_THEN_no_error(
        self,
    ):
        script_lines = [
            "from genie_python import genie as g\n",
            "def test_genie():\n",
            "   g.begin(1,2,3,4,5,6,7,8,9)\n",
        ]

        with CreateTempScriptAndReturnErrors(
            self.checker, self.machine, script_lines, no_pyright=True
        ) as errors:
            self.assertEqual(errors, [])

    # Pyright config checks

    def test_GIVEN_unused_variable_in_script_WHEN_pyright_script_checker_called_THEN_no_error(self):
        script_lines = ["a = 10\n"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_access_member_of_optional_type_var_WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = [
            "from typing import Optional\n",
            "def up(a: Optional[str]):\n",
            "   a.upper()\n",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_index_var_of_optional_type_WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = [
            "from typing import Optional, List\n",
            "def get_first_element(elements: Optional[List[int]]) -> int:\n   return elements[0]\n",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_call_var_of_optional_type_WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = [
            "from typing import Optional, Callable\n",
            "def execute_callback(callback: Optional[Callable[[], None]]) -> None:\n"
            "   callback()\n",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_iterate_over_var_of_optional_type_WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = [
            "from typing import Optional, List\n",
            "def iter_elements(elements: Optional[List[int]]):\n   for element in elements:\n",
            "       pass\n",
        ]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_define_function_with_none_type_args_type_WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = ["def none_func(arg: int = None):\n   print(arg)\n"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_use_optional_operand__WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = ["def none_func(arg1: int, arg2: int = None):\n   print(arg2 + arg1)\n"]

        with CreateTempScriptAndReturnErrors(self.checker, self.machine, script_lines) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_trying_to_use_undefined_variable_WHEN_pyright_script_checker_called_THEN_no_error(
        self,
    ):
        script_lines = ["def func():\n   print(arg)\n"]

        with CreateTempScriptAndReturnErrors(
            self.checker, self.machine, script_lines, no_pylint=True
        ) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_unused_import_WHEN_pyright_script_checker_called_THEN_no_error(self):
        script_lines = ["import genie\n"]

        with CreateTempScriptAndReturnErrors(
            self.checker, self.machine, script_lines, no_pylint=True
        ) as errors:
            self.assertEqual(errors, [])

    def test_GIVEN_scanning_instrument_WHEN_calling_pylint_THEN_pylint_does_not_crash(self):
        # Pylint should not complain about this as the method from a class
        # deriving from "ScanningInstrument" should get added to it's parents'
        # locals by the scanning_instrument_pylint_plugin.
        script_lines = [
            "class ScanningInstrument(): pass\n",
            "class Larmor(ScanningInstrument):\n",
            "    def foo(self): pass\n",
        ]

        captured_stderr = io.StringIO()
        with contextlib.redirect_stderr(captured_stderr):
            with CreateTempScriptAndReturnErrors(
                self.checker, self.machine, script_lines
            ) as errors:
                self.assertEqual(errors, [])

        self.assertEqual(captured_stderr.getvalue(), "")
