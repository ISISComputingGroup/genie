#print "loading init_larmor"
#from .genie import *
import urllib2

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
    #Set to ignore proxy for localhost
    print "Restarting archiver"
    proxy_handler = urllib2.ProxyHandler({})
    opener = urllib2.build_opener(proxy_handler)
    urllib2.install_opener(opener)
    urllib2.urlopen("http://localhost:4813/restart")
    
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