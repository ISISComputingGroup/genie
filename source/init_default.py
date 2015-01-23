#print "loading init_default"
#from genie_python.genie import *


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