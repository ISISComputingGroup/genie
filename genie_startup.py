from genie_python.genie import *


def load_script(script_file):
    """Load a script file

    Parameters:
        file - the file to load.

    EXAMPLE:
        load_script("C:\\myscripts.py")
    """
    import_user_script_module(script_file, globals())