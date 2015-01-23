import socket

#This loads everything if using "from genie import *"
#If starting via IPython this is not called
name = socket.gethostname()

if name.startswith("NDX"):
    #Try loading an instrument specific script
    name = name[3:].lower()
    try:
        exec "from %s import *" % ('init_' + name)
    except Exception as err:
        print err
        #Try loading in non-specific instrument mode
        exec "from init_default import *"
else:
    #Non-specific instrument mode
    exec "from init_default import *"
