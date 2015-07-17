from genie_python.genie import *
import ctypes
import os


if os.name == "nt":
    # Disable Windows console quick edit mode
    win32 = ctypes.windll.kernel32
    handle = win32.GetStdHandle(-10)
    win32.SetConsoleMode(handle, 0x0080)
    

def load_script(script_file, globs=None, globs_holder=[]):
    """Load a script file

    Parameters:
        file - the file to load.

    EXAMPLE:
        load_script("C:\\myscripts.py")
    """
    # This is a workaround to get it to work correctly from the PyDev GUI
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


def set_instrument(pv_prefix, globs=None, globs_holder=[]):
    """Sets the instrument this session is communicating with.
    Used for remote access.

    Parameters
    ----------
    pv_prefix : the PV prefix
    """
    # This is a workaround to get it to work correctly from the PyDev GUI
    if globs is not None and len(globs_holder) == 0:
        globs_holder.append(globs)
    if pv_prefix is None:
        return
    if len(globs_holder) > 0:
        # This is used by the GUI to set the globals correctly
        set_instrument_internal(pv_prefix, globs_holder[0])
    else:
        # This is used by the command line IPython-based genie_python
        set_instrument_internal(pv_prefix, globals())