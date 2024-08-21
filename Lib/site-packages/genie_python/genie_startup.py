from __future__ import absolute_import

import ctypes
import os
import sys
from importlib import reload  # noqa F401

from genie_python import BLOCK_NAMES as b  # noqa F401
from genie_python import genie as g  # noqa F401

# Required so that scientists can just call reload(inst) in the python console.
# Importing genie and block names is required for user scripts.
from genie_python.genie import *  # noqa F403

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
set_instrument(None)  # noqa F405 (defined from star import)

# Add shared instrument scripts to the PYTHONPATH
sys.path.append("C:\\Instrument\\scripts")
