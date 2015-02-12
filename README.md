# genie_python

The ISIS Python-based instrument control and scripting library.

## Initialisation

Ny default when setting an instrument the init_INSTNAME.py file is loaded. This file checks for the existance of a
folder called C:\Instrument\Settings\config\NDXINSTNAME\Python and adds this to the sys path.
This means that Python modules can be imported directly from that directory. If running on a client it is necessary to
have a copy of the Python directory for the instrument being connected to in the correct location.

Folders inside the Python directory must have a __init__.py file for them to be available to be imported.

## The load_script workaround

To enable the load_script command to put loaded scripts into the globals()
for the interactive session, it is necessary to define load_script at the command-line and not inside a module.
To do this, we need to set the PYTHONSTARTUP environment variable to point at genie_start.py. This can be done in a BAT.

The line "from genie_python import *" in genie_startup is responsible for loading all the genie_python stuff!

Alternatively, if we are using IPython we can use c.TerminalIPythonApp.exec_files to run genie_start.py.
This has the advantage of only making IPython automatically genie_python aware.