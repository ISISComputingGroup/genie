from builtins import object
from typing import Any, Callable


class PrePostCmdManager(object):
    """
    A class to manager the precmd and postcmd commands such as used in begin, end, abort, resume,
     pause.
    """

    def __init__(self) -> None:
        self.begin_precmd: Callable[[Any], str | None] = lambda **pars: None
        self.begin_postcmd: Callable[[Any], str | None] = lambda **pars: None
        self.abort_precmd: Callable[[Any], str | None] = lambda **pars: None
        self.abort_postcmd: Callable[[Any], str | None] = lambda **pars: None
        self.end_precmd: Callable[[Any], str | None] = lambda **pars: None
        self.end_postcmd: Callable[[Any], str | None] = lambda **pars: None
        self.pause_precmd: Callable[[Any], str | None] = lambda **pars: None
        self.pause_postcmd: Callable[[Any], str | None] = lambda **pars: None
        self.resume_precmd: Callable[[Any], str | None] = lambda **pars: None
        self.resume_postcmd: Callable[[Any], str | None] = lambda **pars: None
        self.cset_precmd: Callable[[Any], str | bool | None] = lambda **pars: True
        self.cset_postcmd: Callable[[Any], str | None] = lambda **pars: None
