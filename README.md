# genie_python

The ISIS Python-based instrument control and scripting library. 

## The load_script workaround

To enable the load_script command to put loaded scripts into the globals()
for the interactive session, it is necessary to define load_script at the command-line and not inside a module.
To do this, we need to set the PYTHONSTARTUP environment variable to point at genie_start.py. This can be done in a BAT.

The line "from genie_python import *" in genie_startup is responsible for loading all the genie_python stuff!

Alternatively, if we are using IPython we can use c.TerminalIPythonApp.exec_files to run genie_start.py.
This has the advantage of only making IPython automatically genie_python aware.