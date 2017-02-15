from genie_python.genie import *
# Second import is required for user scripts.
from genie_python import genie as g
import ctypes
import os


if os.name == "nt":
    # Disable Windows console quick edit mode
    win32 = ctypes.windll.kernel32
    hin = win32.GetStdHandle(-10)
    mode = ctypes.c_ulong(0)
    win32.GetConsoleMode(hin, ctypes.byref(mode))
    # To disable quick edit need to disable the 7th bit and enable the 8th
    new_mode = mode.value & ~(0x0040) | (0x0080)
    win32.SetConsoleMode(hin, new_mode)

# Call set_instrument with None to force it to try to guess the instrument
set_instrument(None)