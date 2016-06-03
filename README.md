# genie_python

The ISIS Python-based instrument control and scripting library.

## Instrument initialisation

By default when setting an instrument the init_default.py file is loaded. 
This file checks for the existence of a folder called C:\Instrument\Settings\config\NDX%INSTNAME%\Python and adds this to the sys path if it does.
If this path exists and contains a file called init_%INSTNAME%.py, it will load it too.

On the NDX any files in C:\Instrument\Settings\config\NDX%INSTNAME%\Python can be added to SVN for safe keeping.

Python modules can be imported directly from the C:\Instrument\Settings\config\NDX%INSTNAME%\Python directory. If running on a client it is necessary to have a copy of the Python directory for the instrument being connected to in the correct location.

Folders inside the Python directory must have a `__init__.py` file for them to be available to be imported.

## Start-up
The line "from genie_python import *" in genie_startup is responsible for loading all the genie_python stuff!
This file also contains code for disabling quickedit and for making genie_python guess the instrument name.

As genie_python is running inside IPython we use c.TerminalIPythonApp.exec_files to run genie_start.py, so everything is imported correctly.
