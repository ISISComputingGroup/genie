from __future__ import absolute_import, print_function

import ast
import json
import os
import re
import site
import subprocess
import sys
import sysconfig
import unicodedata
from builtins import object
from io import StringIO, open
from typing import Iterable

from astroid import MANAGER, nodes
from pylint.lint import Run
from pylint.reporters.text import TextReporter


class ScriptChecker(object):
    """
    Check Scripts for common errors
    """

    def _find_regex(self, variable: str) -> str:
        """
        Sets the function to find any of the symbols listed below
        Args:
            variable: the assigned string from the search function
        Return:
            the string to be used in the regex search function
        """
        assignment_regex = "[\|\&\^\/\+\-\*\%]?=[^=]"
        regex = r"\b{0}[.][\w\s]*" + assignment_regex + r"|\b{0}[\s]*" + assignment_regex
        return regex.format(variable)

    def _check_g_inst_name(self, line: str, line_no: int) -> str:
        """
        Checks a line of a script for assignments of variables named g or inst
        Args:
            line: the line to check
            line_no: the line number
        Return:
            If an error is found appropriate warning string else
            if no error found an empty string
        """
        g_error = re.search(self._find_regex("g"), line)
        if g_error:
            return "W:  {line_no}: 'g' assignment in line {line_no}".format(line_no=line_no)

        inst_error = re.search(self._find_regex("inst"), line)
        if inst_error:
            return "W:  {line_no}: 'inst' assignment in line {line_no}".format(line_no=line_no)

        return ""

    def check_script_lines(self, lines: Iterable[str]) -> list[str]:
        """
        Check the lines of the script for possible errors
        Args:
            lines: iterable of lines to check
        Returns: error in the script; empty list if none
        """
        reassignment_warnings = []
        line_no = 0
        for line in lines:
            line_no += 1
            warning = self._check_g_inst_name(line, line_no)
            if len(warning) != 0:
                reassignment_warnings.append(warning)

        return reassignment_warnings

    def _can_cache_module(self, module_name: str, module: nodes.Module) -> bool:
        """
        Determines whether a module can be cached or whether the linter
        should re-examine it's contents each time.

        Args:
            module_name: the name of the module
            module: the astroid module object

        Returns:
            True if the module can safely be cached, False otherwise
        """
        # Always allow builtin modules to be cached.
        if module_name in sys.builtin_module_names:
            return True

        # Allow modules defined in the site packages directories to be cached as
        # they are unlikely to change at runtime
        if module.file is not None and any(
            module.file.startswith(site_package_dir) for site_package_dir in site.getsitepackages()
        ):
            return True

        # Other modules are probably user-defined e.g. inst scripts,
        # shared scripts, user scripts. Don't cache these.
        return False

    def _clean_astroid_cache(self) -> None:
        """
        Cleans user-defined scripts out of the astroid cache.
        """
        new_cache = {}

        for module_name, module in MANAGER.astroid_cache.items():
            if self._can_cache_module(module_name, module):
                new_cache[module_name] = module

        MANAGER.astroid_cache = new_cache

    class _TemporaryPyrightConfig:
        def __init__(
            self,
            config_path: str,
            instrument_name: str,
            additional_include_paths: list[str] | None = None,
        ) -> None:
            if additional_include_paths is None:
                additional_include_paths = []

            self.config_path = config_path
            self.config_name = "pyrightconfig.json"
            self.json_write = {
                "include": [
                    ".",
                ],
                "extraPaths": [
                    os.path.join(sysconfig.get_paths()["purelib"]),
                    os.path.join(sysconfig.get_paths()["platlib"]),
                    os.path.join("C:\\", "Instrument", "scripts"),
                    os.path.join(
                        "C:\\", "Instrument", "settings", "config", instrument_name, "Python"
                    ),
                    os.path.join("U:\\", "scripts"),
                    os.path.join("U:\\"),
                ],
                "exclude": [
                    "**/node_modules",
                    "**/__pycache__",
                ],
                "typeCheckingMode": "basic",
                "reportUnusedVariable": False,
                "reportOptionalMemberAccess": False,
                "reportOptionalSubscript": False,
                "reportOptionalCall": False,
                "reportOptionalIterable": False,
                "reportUnboundVariable": False,
                "reportUndefinedVariable ": False,
                # Errors such as these will be caught by pylint before pyright, so no need to report
                "reportMissingImports": False,
                # Errors such as these will be caught by pylint before pyright, so no need to report
                "strictParameterNoneValue": False,
                "reportOptionalOperand": False,
                "pythonPlatform": "Windows",
            }

            for path in additional_include_paths:
                self.json_write["extraPaths"].append(path)

        def __enter__(self) -> None:
            self._filename = os.path.join(self.config_path, self.config_name)
            with open(self._filename, "w") as f:
                f.write(json.dumps(self.json_write))

        def __exit__(self, exc_type: None, exc_value: None, exc_traceback: None) -> None:
            os.unlink(self._filename)

    def pyright_script_checker(
        self, script_path: str, instrument_name: str, pyright_additional_include: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        Makes a call to pyright to do a static analyis of the script.

        Args:
            script_name: The path to the selected user script
            instrument_name: The instrument name in
                C:\\Instrument\\Settings\\config\\[instrument_name]\\Python
        Returns:
            A list of warnings and a list of errors.
        """

        script_dir = os.path.dirname(script_path)
        errors = []
        warnings = []

        # 1 - Checks to see if pyrightconfig.json is present
        #   under the same directory as the selected script
        # 2 - if not then copy json into dir
        # 3 - Run pyright --project C:/[path_to_script_dir] C:/[path_to_script_dir]/[script].py
        # 4 - reads from json output and returns appropriate errors/warnings/nothing if OK

        with self._TemporaryPyrightConfig(script_dir, instrument_name, pyright_additional_include):
            cmd = [
                sys.executable,
                "-m",
                "pyright",
                "--project",
                script_dir,
                "--outputjson",
                script_path,
            ]

            pr_result = subprocess.run(args=cmd, capture_output=True, text=True, encoding="utf-8")
            json_out = unicodedata.normalize("NFKD", pr_result.stdout)

            json_data = json.loads(json_out)

            # for each diagnostic, if severity is error then
            # add message to error array else add to warning array
            for diagnostic in json_data["generalDiagnostics"]:
                start = diagnostic["range"]["start"]
                if not diagnostic["rule"] == "reportUndefinedVariable":  ### CHANGE
                    if diagnostic["severity"] == "error":
                        errors += [
                            f"E: {start['line'] + 1}: "
                            f"{diagnostic['message']} [{diagnostic['rule']}]"
                        ]
                    else:
                        warnings += [
                            f"W: {start['line'] + 1}: "
                            f"{diagnostic['message']} [{diagnostic['rule']}]"
                        ]

        return warnings, errors

    def check_for_tabs(
        self,
        lines_list: list[str],
        error_line_numbers: list[int],
        lines_containing_errors: list[str],
    ) -> None:
        """
        Searches for tabs in script file. Tells user to convert tabs to 4 space characters.

        Args:
            lines_list: List of all lines in script.
            error_line_numbers: List of line numbers which have errors.
            lines_containing_errors: List of lines that contain errors.
        """

        tab_found = False
        for i, line in enumerate(lines_list, start=1):
            if i in error_line_numbers:
                lines_containing_errors.append(line.strip())

            tab_line = re.search(r"\t", line)
            if tab_line:
                tab_found = True

        if tab_found:
            print(
                "Tab characters found in file, for portability convert tabs to 4 space characters."
            )

    def check_script(
        self,
        script_name: str,
        instrument_name: str,
        warnings_as_error: bool = False,
        no_pyright: bool = False,
        no_pylint: bool = False,
        pyright_additional_include: list[str] | None = None,
    ) -> list[str]:
        """
        Check a script for common errors.
        Args:
            script_name: filename of the script
            instrument_name: Full instrument name
            warnings_as_error: True treat warnings as errors; False otherwise

        Returns: error messages list; empty list if there are no errors
        """
        errors_output = StringIO()

        # We need to clean the cache so that we pick up changes in instrument scripts
        self._clean_astroid_cache()

        warnings = []
        errors = []

        dir_path = os.path.dirname(os.path.realpath(__file__))

        if no_pylint and no_pyright:
            return []

        elif not no_pylint:
            pylint_path = os.path.join(dir_path, ".pylintrc")

            with open(script_name) as f:
                reassignment_warnings = self.check_script_lines(f)
                warnings.extend(reassignment_warnings)

            inst_file_path = os.path.join(
                "C:\\", "Instrument", "Settings", "config", instrument_name, "Python"
            )
            init_hook = (
                "import sys;"
                'sys.path.append("{}");'
                'sys.path.append("U:\\scripts");'
                'sys.path.append("C:\\Instrument\\scripts");'.format(inst_file_path)
            )
            init_hook = init_hook.replace("\\", "\\\\")
            inst_scripts_file_path = os.path.join(inst_file_path, "inst")

            try:
                functions = self.get_inst_attributes(inst_scripts_file_path)
            except Exception as e:
                match = re.search(r"\((.*?),", str(e))
                assert match is not None, "Regex searching for expression failed."
                e_filename = match.group(1)
                return [
                    "Error while getting attributes of instrument scripts. Please check "
                    + os.path.join(inst_scripts_file_path, e_filename)
                    + ": {}".format(e)
                ]

            # C = Convention related checks,
            # R = Refactoring Related Checks,
            # W = various warnings,
            # E = Errors,
            # F = fatal
            # --msg-template={msg_id}:{line:3d},{column}: {obj}: {msg} for more specific message
            Run(
                [
                    "--rcfile={}".format(pylint_path),
                    "--init-hook={}".format(init_hook),
                    "--msg-template={C}:{line:3d}: {msg} ({symbol})",
                    "--generated-members={}".format(functions),
                    "--score=n",
                    script_name,
                ],
                reporter=TextReporter(errors_output),
                exit=False,
            )

            new_warnings, errors = self.split_warning_errors(errors_output)
            warnings += new_warnings

        if errors == [] and not no_pyright:  # Don't run pryight if pylint goes wrong
            pyright_warnings, pyright_errors = self.pyright_script_checker(
                script_name, instrument_name, pyright_additional_include or []
            )

            errors += pyright_errors
            warnings += pyright_warnings

        error_line_numbers = []

        if warnings_as_error:
            errors += warnings
        else:
            for warning in warnings:
                print(warning)

                error_line = re.search(r"W:\s+(\d+):", warning)
                if error_line:
                    selected_number = error_line.group(1)
                    error_line_numbers.append(int(selected_number))

        lines_containing_errors = []
        with open(script_name) as f:
            content = f.read()

        lines_list = content.splitlines()

        self.check_for_tabs(lines_list, error_line_numbers, lines_containing_errors)

        line_numbers_position = 0

        for line in lines_containing_errors:
            g_error_line = re.search(r"g\.", line)
            if g_error_line:
                errors.append(
                    f"An error has been found on line {error_line_numbers[line_numbers_position]} "
                    f"within the file {script_name}"
                )
                errors.append(
                    'Please check the "g." statement and ensure that the brackets are not missing.'
                )

        return errors

    def split_warning_errors(self, errors_outputs: Iterable[str]) -> tuple[list[str], list[str]]:
        """
        takes in errors and warning lists and split in two separate list i.e.
        (errors and warnings)
        :param errors_outputs: list of errors and warnings
        :return: two separate lists for errors and warnings
        """
        warnings = []
        errors = []
        errors_outputs = errors_outputs.getvalue().split("\n")
        verbose_warning = [
            "Redefining name 'g' from outer scope",
            "Redefining name 'inst' from outer scope",
        ]
        verbose_warning = [
            error
            for error in errors_outputs
            if any(warning in error for warning in verbose_warning)
        ]

        for message in errors_outputs:
            if message.startswith("W") and (message not in verbose_warning):
                warnings.append(message)
            elif message.startswith("E"):
                errors.append(message)

        return warnings, errors

    def get_inst_attributes(self, instrument_scripts_paths: str) -> str | list[str]:
        """
        gets attributes such as Global variables, Functions, Classes defined
        in instrument scripts
        :param instrument_scripts_paths: path to instrument scripts
        :return: string representation of attributes present in
        instrument scripts with comma separated
        """
        try:
            attributes = ""
            for filename in os.listdir(instrument_scripts_paths):
                if filename.endswith(".py") and not filename.startswith("__"):
                    with open(os.path.join(instrument_scripts_paths, filename)) as f:
                        src = f.read()
                        tree = ast.parse(src, filename)
                    attributes += self.get_all_attributes(tree)
            attributes = attributes[:-1]
            return attributes
        except OSError:
            return ""

    def get_all_attributes(self, tree: nodes.Module) -> str | list[str]:
        """
        gets all the attributes of instrument scripts
        :param tree: abstract syntax tree representation of instrument script
        :return: string of all the useful attributes
        """
        attributes = self.get_names_of_functions_classes_global_variables(tree.body)
        return attributes

    def get_names_of_functions_classes_global_variables(self, body: Iterable) -> str | list[str]:
        """
        gets the name of function, class and global variable names
        :param body: body to iterate through
        :return: string of function names, class, global variables (comma separated)
        """
        attributes = ""
        for item in body:
            # getting functions in global scope
            if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                attributes += "inst.{function_name},".format(function_name=item.name)
            # getting class and its attributes
            elif isinstance(item, ast.ClassDef):
                class_name = "inst.{class_name}".format(class_name=item.name)
                attributes += "{class_name},".format(class_name=class_name)
                attributes += self.get_class_member_names(item.body, class_name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    attributes += self.parse_assignment_target(target)

        return attributes

    def parse_assignment_target(self, target: ast.AST, descendants: str = "") -> list[str]:
        if isinstance(target, ast.Name):
            return "inst.{}{},".format(target.id, descendants)

        if sys.version_info[0] >= 3 and isinstance(target, ast.Starred):
            return self.parse_assignment_target(target.value, descendants=descendants)

        if isinstance(target, ast.Attribute):
            descendants = ".{}{}".format(target.attr, descendants)
            return self.parse_assignment_target(target.value, descendants=descendants)

        if isinstance(target, (ast.List, ast.Tuple)):
            attributes = ""
            for nested_target in target.elts:
                attributes += self.parse_assignment_target(nested_target)
            return attributes

        # Ignore all other nodes
        return ""

    def get_class_member_names(self, body: Iterable, class_name: str) -> list[str]:
        """
        gets the name of all the class members
        :param body: body to iterate through
        :param class_name: name of class to prepend
        :return: string of class member names (comma separated)
        """
        attributes = ""
        for function_body in body:
            if isinstance(function_body, ast.FunctionDef):
                if "__" not in function_body.name:
                    attributes += "{class_name}.{function_name},".format(
                        class_name=class_name, function_name=function_body.name
                    )
                else:
                    # variables defined inside __init__
                    for variables in function_body.body:
                        if isinstance(variables, ast.Assign):
                            attributes += "{class_name}.{variable_name},".format(
                                class_name=class_name, variable_name=variables.targets[0].attr
                            )
        return attributes
