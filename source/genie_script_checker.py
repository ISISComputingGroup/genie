import re
import ast


class ScriptChecker(object):

    def __init__(self, genie_path):
        self.genie_functions = self._get_genie_functions(genie_path)

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

    def check_script(self, name):
        errors = list()
        f = open(name, 'r')
        line_no = 0
        for line in f:
            line_no += 1
            # Look for genie commands missing brackets, e.g. begin, end, cshow etc.
            error = self.check_genie_commands_has_brackets(line, line_no)
            if error is not None:
                errors.append(error)
        return errors

    def check_genie_commands_has_brackets(self, line, line_no):
        msg = None
        for f in self.genie_functions:
            # A good match
            m = re.match("\s*" + f + "\(", line)
            if m is not None:
                # It is okay
                return None
            # A bad match
            nm1 = re.match("\s*" + f + "$", line)
            nm2 = re.match("\s*" + f + "[^(]", line)
            if nm1 is not None or nm2 is not None:
                # Might be a mistake
                msg =  "Line %s: '%s' command without brackets" % (line_no, f)
        return msg