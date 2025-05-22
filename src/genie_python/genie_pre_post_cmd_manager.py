from builtins import object
from typing import Any


class PrePostCmdManager(object):
    """
    A class to manager the precmd and postcmd commands such as used in begin, end, abort, resume,
     pause.
    """

    def begin_precmd(self, **kwargs: Any) -> str | None:
        return

    def begin_postcmd(self, **kwargs: Any) -> str | None:
        return

    def abort_precmd(self, **kwargs: Any) -> str | None:
        return

    def abort_postcmd(self, **kwargs: Any) -> str | None:
        return

    def end_precmd(self, **kwargs: Any) -> str | None:
        return

    def end_postcmd(self, **kwargs: Any) -> str | None:
        return

    def pause_precmd(self, **kwargs: Any) -> str | None:
        return

    def pause_postcmd(self, **kwargs: Any) -> str | None:
        return

    def resume_precmd(self, **kwargs: Any) -> str | None:
        return

    def resume_postcmd(self, **kwargs: Any) -> str | None:
        return

    def cset_precmd(self, **kwargs: Any) -> bool:
        return True

    def cset_postcmd(self, **kwargs: Any) -> str | None:
        return
