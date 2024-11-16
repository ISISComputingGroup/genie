from builtins import object


class PrePostCmdManager(object):
    """
    A class to manager the precmd and postcmd commands such as used in begin, end, abort, resume, pause.
    """

    def __init__(self):
        self.begin_precmd = lambda **pars: None
        self.begin_postcmd = lambda **pars: None
        self.abort_precmd = lambda **pars: None
        self.abort_postcmd = lambda **pars: None
        self.end_precmd = lambda **pars: None
        self.end_postcmd = lambda **pars: None
        self.pause_precmd = lambda **pars: None
        self.pause_postcmd = lambda **pars: None
        self.resume_precmd = lambda **pars: None
        self.resume_postcmd = lambda **pars: None
        self.cset_precmd = lambda **pars: True
        self.cset_postcmd = lambda **pars: None
