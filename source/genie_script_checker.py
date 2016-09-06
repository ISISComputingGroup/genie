import re
import ast


class ScriptChecker(object):
    """
    Check scripts for common errors
    """

    def __init__(self, genie_path):
        """
        Constructor
        Args:
            genie_path: path to a file containing python for gennie commands
        Returns:
        """
        self.genie_functions = self._get_genie_functions(genie_path)
        # regular experssion to find one of the genie commands ({0} bit) within a word boundary (\b before and after)
        # also capture any cahracter after this e.g. opening bracket
        self._find_gennie_fn_pattern = re.compile(r"\b({0})\b(.?)".format("|".join(self.genie_functions)))

    def _get_genie_functions(self, genie_path):
        # Get genie methods
        # __file__ gives the location of the .pyc if it exists otherwise it gives the .py
        if genie_path.endswith(".pyc"):
            genie_path = genie_path[:-1]
        try:
            f = open(genie_path, 'r')
            src = f.read()
        except:
            raise
        else:
            f.close()
        try:
            tree = ast.parse(src)
            functions = list()
            for item in tree.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                    functions.append(item.name)
            functions.sort()
            return functions
        except:
            raise

    def check_script(self, name, warning_as_error=False):
        """
        Check a script for common errors
        Args:
            name: filename of the script
            warning_as_error: True treat warnings as errors; False otherwise

        Returns: error messages list; empty list if there are no errors
        """

        f = open(name, 'r')
        return self.check_script_lines(f, warning_as_error)

    def check_script_lines(self, lines, warning_as_error=False):
        """
        Check the lines of the script for possible errors
        Args:
            lines: iterable of lines to check
            warning_as_error: True treat warnings as errors; False otherwise

        Returns: error in the script; empty list if none

        """
        errors = []
        warnings = []
        line_no = 0
        commands_count = {}
        for line in lines:
            line_no += 1
            # Look for genie commands missing brackets, e.g. begin, end, cshow etc.
            error, warning = self._check_genie_commands_has_brackets(line, line_no)
            errors.extend(error)
            errors.extend(warning)

            self._add_command_counts(commands_count, line)

        error, warning = self._check_command_counts(commands_count)
        errors.extend(error)
        errors.extend(warning)
        return errors

    def _check_genie_commands_has_brackets(self, line, line_no):
        """
        Check the line for a gennie command with no opening brackets
        Args:
            line: the line to check
            line_no: the line number

        Returns: list of error and a list or warnings;  Empty lists for no error or warnings
        """
        for function_name, possible_bracket in self._get_possible_commands(line):
            if possible_bracket != "(":
                return ["Line %s: '%s' command without brackets" % (line_no, function_name)], []

        return [], []

    def _get_possible_commands(self, line):
        line = re.sub(r"'[^']*'", "", line)
        line = re.sub(r'"[^"]*"', "", line)
        line = re.sub(r"#.*", "", line)
        matches = self._find_gennie_fn_pattern.findall(line)
        return matches

    def _add_command_counts(self, commands_count, line):
        for function_name, possible_bracket in self._get_possible_commands(line):
            if possible_bracket == "(":
                commands_count[function_name] = commands_count.get(function_name, 0) + 1

    def _check_command_counts(self, commands_count):
        end_count = commands_count.get("end", 0)
        begin_count = commands_count.get("begin", 0)
        if end_count == begin_count:
            return [], []
        elif end_count > begin_count:
            return [], ["'end' command without 'begin' in script is begin missing?"]

