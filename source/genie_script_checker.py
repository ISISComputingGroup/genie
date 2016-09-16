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
        # regular expression to find one of the genie commands ({0} bit) within a word boundary (\b before and after)
        # also capture any character after this e.g. opening bracket
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

    def check_script(self, name, warnings_as_error=False):
        """
        Check a script for common errors
        Args:
            name: filename of the script
            warnings_as_error: True treat warnings as errors; False otherwise

        Returns: error messages list; empty list if there are no errors
        """

        f = open(name, 'r')
        return self.check_script_lines(f, warnings_as_error)

    def check_script_lines(self, lines, warning_as_error=False):
        """
        Check the lines of the script for possible errors
        Args:
            lines: iterable of lines to check
            warning_as_error: True treat warnings as errors; False otherwise

        Returns: error in the script; empty list if none

        """
        errors = []
        line_no = 0
        state_changes = {}
        for line in lines:
            line_no += 1
            # Look for genie commands missing brackets, e.g. begin, end, cshow etc.
            error, warnings = self._check_genie_commands_has_brackets(line, line_no)
            errors.extend(error)
            errors.extend(self._process_warnings(warning_as_error, warnings))

        return errors

    def _process_warnings(self, warning_as_error, warnings):
        """
        Process the warnings
        :param warning_as_error: True if warning should be errors; False if they should be printed
        :param warnings: list of warnings
        :return: errors list
        """
        if warning_as_error:
            return warnings
        for warning in warnings:
            print "Warning: " + warning
        return []

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
        """
        Get a list of possible command on the current line. Ignores comments and strings.
        :param line: line to get commands from
        :return: list of function names and following character
        """
        line = re.sub(r"'[^']*'", "", line)
        line = re.sub(r'"[^"]*"', "", line)
        line = re.sub(r"#.*", "", line)
        matches = self._find_gennie_fn_pattern.findall(line)
        return matches

