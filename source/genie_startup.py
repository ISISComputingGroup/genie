from genie_python.genie import *


def load_script(script_file, globs=None, globs_holder=[]):
    """Load a script file

    Parameters:
        file - the file to load.

    EXAMPLE:
        load_script("C:\\myscripts.py")
    """
    # This is a workaround to get load_script to work correctly from the PyDev GUI
    if globs is not None and len(globs_holder) == 0:
        globs_holder.append(globs)
    if script_file is None:
        return
    if len(globs_holder) > 0:
        # This is used by the GUI to set the globals correctly
        import_user_script_module(script_file, globs_holder[0])
    else:
        # This is used by the command line IPython-based genie_python
        import_user_script_module(script_file, globals())