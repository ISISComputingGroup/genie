import sys
import os

print("This is init_default!")

def init(inst):
    # Check instrument specific folder exists, if so add to sys path
    path = "C:\\Instrument\\Settings\\config\\%s\\Python" % inst
    if os.path.isdir(path):
        sys.path.append(path)
    print("hullo from init")


def abort_precmd(**pars):
    pass


def abort_postcmd(**pars):
    pass


def begin_precmd(**pars):
    if 'quiet' in pars:
        pass


def begin_postcmd(**pars):
    if 'quiet' in pars:
        pass
    if 'run_num' in pars:
        pass


def end_precmd(**pars):
    if 'quiet' in pars:
        pass
    if 'immediate' in pars:
        pass


def end_postcmd(**pars):
    if 'quiet' in pars:
        pass
    if 'run_num' in pars:
        pass
    if 'immediate' in pars:
        pass


def pause_precmd(**pars):
    if 'quiet' in pars:
        pass


def pause_postcmd(**pars):
    if 'quiet' in pars:
        pass


def resume_precmd(**pars):
    if 'quiet' in pars:
        pass


def resume_postcmd(**pars):
    if 'quiet' in pars:
        pass


def cset_precmd(**pars):
    #Return False to cancel cset
    if 'runcontrol' in pars:
        pass
    if 'wait' in pars:
        pass
    return True