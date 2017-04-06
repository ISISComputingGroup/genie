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
            genie_path: path to a file containing python for genie commands
        Returns:
        """
        self.genie_functions = self._get_genie_functions(genie_path)
        # regular expression to find one of the genie commands ({0} bit) within a word boundary (\b before and after)
        # also capture any character after this e.g. opening bracket
        self._find_genie_fn_pattern = re.compile(r"\b({0})\b(.?)".format("|".join(self.genie_functions)))

    def _get_genie_functions(self, genie_path):
        """"
            Get genie methods
            Args:
                genie_path: path to a file containing python for genie commands, uses .py rather than .pyc
        # __file__ gives the location of the
        """
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

        with file(name, mode="r") as f:
            return self.check_script_lines(f, warnings_as_error)

    def _set_regex(self, variable):
        """
        Sets the function to find any of the symbols listed below
        Args:
            variable: the assigned string from the search function
        Return:
            the string to be used in the regex search function
        """
        assignment_regex = "[\|\&\^\/\+\-\*\%]?=[^=]"
        regex = r'\b{0}[.][\w\s]*' + assignment_regex + r'|\b{0}[\s]*' + assignment_regex
        return regex.format(variable)

    def _check_g_inst_name(self, line, line_no):
        """
        Checks a line of a script for assignments of variables named g or inst
        Args:
            line: the line to check
            line_no: the line number

        Return:
            list of warnings: contains tuple of 2 lists, 1 which contains an empty list with no warnings,
                              the other containing the list of warnings
        """
        g_error = re.search(self._set_regex('g'), line)
        if g_error:
            return [], ["'g' assignment in line " + str(line_no)]
        inst_error = re.search(self._set_regex('inst'), line)
        if inst_error:
            return [], ["'inst' assignment in line " + str(line_no)]
        return [], []


    def check_script_lines(self, lines, warning_as_error=False):
        """
        Check the lines of the script for possible errors
        Args:
            lines: iterable of lines to check
            warning_as_error: True treat warnings as errors; False otherwise

        Returns: error in the script; empty list if none

        """
        name_errors = []
        bracket_errors = []
        line_no = 0
        for line in lines:
            line_no += 1
            # Look for genie code with 'g' or 'inst', g = 1.
            name_error, name_warnings = self._check_g_inst_name(line, line_no)
            name_errors.extend(name_error)
            name_errors.extend(self._process_warnings(warning_as_error, name_warnings))

            # Look for genie commands missing brackets, e.g. begin, end, cshow etc.
            bracket_error, bracket_warnings = self._check_genie_commands_has_brackets(line, line_no)
            bracket_errors.extend(bracket_error)
            bracket_errors.extend(self._process_warnings(warning_as_error, bracket_warnings))

        errors = name_errors + bracket_errors

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
        Check the line for a genie command with no opening brackets
        Args:
            line: the line to check
            line_no: the line number

        Returns: list of error and a list of warnings;  Empty lists for no error or warnings
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
        matches = self._find_genie_fn_pattern.findall(line)
        return matches
