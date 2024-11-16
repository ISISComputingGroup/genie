from __future__ import print_function

import ctypes
import functools
import glob
import inspect
import os
import re
import sys
import time
import traceback
from typing import Any, Callable, ParamSpec, TypeVar

import IPython
from decorator import getfullargspec
from IPython.core.completer import IPCompleter

from genie_python.utilities import get_correct_filepath_existing

P = ParamSpec("P")
T = TypeVar("T")

# Determine whether to start in simulation mode

if "GENIE_SIMULATE" not in os.environ or os.environ["GENIE_SIMULATE"] != "1":
    from genie_python.genie_epics_api import API
else:
    print("\n=========== RUNNING IN SIMULATION MODE ===========\n")
    from genie_python.genie_simulate_impl import API


# Windows specific stuff
if os.name == "nt":
    # Needed for correcting file paths
    pass

# INITIALISATION CODE - DO NOT DELETE
try:
    # If __api does not exist or is None then we need to create it.
    if __api is None:  # noqa: F821 __api currently gets added to globals which is bad.
        raise Exception("API does not exist")
except Exception:
    # This should only get called the first time genie is imported
    my_pv_prefix = None
    if "MYPVPREFIX" in os.environ:
        my_pv_prefix = os.environ["MYPVPREFIX"]
        __api = API(my_pv_prefix, globals())
    else:
        print("No instrument specified - loading local instrument")
        __api = API(None, globals())


# END INITIALISATION CODE


def set_user_script_dir(*directory: str | list[str]) -> None:
    """
    Set the user script directory, ensuring it ends in a slash
    Args:
        directory: directory to set it to, or list of directories

    """
    global USER_SCRIPT_DIR

    requested_dir = os.path.join(*directory)
    directory_name = requested_dir
    dirs_to_create = []

    base_name = None
    while base_name != "":
        try:
            directory_name = get_correct_filepath_existing(directory_name)
            break
        except OSError:
            directory_name, base_name = os.path.split(directory_name.strip(r"\\/"))
            dirs_to_create.append(base_name)

    # Got to a single directory which does not exist
    if base_name == "":
        raise OSError("Script dir does not exist and can not be created: {}".format(requested_dir))

    for dir_to_create in reversed(dirs_to_create):
        directory_name = os.path.join(directory_name, dir_to_create)
        os.mkdir(directory_name)
        directory_name = get_correct_filepath_existing(directory_name)

    if len(directory_name) > 1 and directory_name[-1] != "/":
        directory_name += "/"
    USER_SCRIPT_DIR = directory_name


def get_user_script_dir() -> str:
    """
    Returns: the user script directory
    """
    global USER_SCRIPT_DIR
    return USER_SCRIPT_DIR


try:
    set_user_script_dir("C:/scripts/")
except Exception:
    USER_SCRIPT_DIR = ""


# TAB COMPLETE CODE

LOAD_SCRIPT_COMMAND = "load_script("


class LoadScriptCompleter:
    """
    A class holding a custom complete function which replaces the normal completion
    function of the ipython completer. We are replacing it and not just adding it
    as a custom completer because it allows us to return just paths after
    load_script and no other completions from the IPython backend. If this
    does not have load script in it will return what the original one did.
    """

    def __init__(self, original_complete_fn: Callable) -> None:
        """
        Initialise.
        Args:
            original_complete_fn: function which was originally used to complete
        """
        self._original_complete = original_complete_fn
        self.is_pydev = False

    def _get_completion_paths(self, line_buffer: str) -> tuple[list[str], str, bool, bool]:
        """
        Given a line buffer, get the relevant filename completions for a g.load_script command

        Args:
            line_buffer: the line to complete
        Returns:
            tuple (list[str], str, bool, bool) - a list of the completions,
                the search path which was used, whether the path was already quoted,
                whether the path was absolute (e.g. c:/scripts/myscript.py)
                or relative (e.g. myscript.py)
        """
        # cope with None as search path
        if line_buffer is None:
            line_buffer = ""

        # get file path
        search_path = line_buffer.split(LOAD_SCRIPT_COMMAND)[-1]

        had_quotes = search_path.startswith("'") or search_path.startswith('"')
        if had_quotes:
            search_path = search_path[1:]

        is_absolute = os.path.isabs(search_path)
        if not is_absolute:
            search_path = "{}{}".format(get_user_script_dir(), search_path)

        # search and return results
        paths = glob.glob("{}*".format(search_path))

        return paths, search_path, had_quotes, is_absolute

    def standalone_complete(self, completer: IPCompleter, text: str | None = None) -> list[str]:
        """
        Find completions for the given text and line context.

        Parameters
        ----------
          completer : IPyCompleter
            The IPython completer instance being used to perform this completion.

          text : string, optional
            Text to perform the completion on.  Line buffer
            is always used except when using the default completer.

        Returns
        -------
        completion : list
          A list of completion matches.
        """
        line_buffer = completer.line_buffer
        if LOAD_SCRIPT_COMMAND not in line_buffer:
            return []
        else:
            paths, search_path, had_quotes, was_absolute = self._get_completion_paths(line_buffer)

            # add quote if it is missing
            if had_quotes:
                quote = ""
            else:
                quote = '"'

            # if the path isn't absolute it should refer to script dir
            if was_absolute:
                len_added_user_script = 0
            else:
                len_added_user_script = len(get_user_script_dir())

            # Console expects the whole path
            # return / to avoid a quoting issue with \ in paths and do not include the script dir
            completion = [
                "{}{}".format(quote, path.replace("\\", "/")[len_added_user_script:])
                for path in paths
            ]

        return completion

    def pydev_complete(
        self, text: str | None = None, line_buffer: str | None = None, cursor_pos: int | None = None
    ) -> tuple[str, list[str]]:
        """
        Find completions for the given text and line context.
        Note that both the text and the line_buffer are optional, but at least
        one of them must be given.
        Parameters
        ----------
          text : string, optional
            Text to perform the completion on.  Line buffer
            is always used except when using the default completer.
          line_buffer : string, optional
            line to match
          cursor_pos : int, optional
            Index of the cursor in the full line buffer.  Should be provided by
            remote frontends where kernel has no access to frontend state.
        Returns
        -------
        text : str
          Text that was actually used in the completion.
        matches : list
          A list of completion matches.
        """

        if LOAD_SCRIPT_COMMAND not in line_buffer:
            match, completion = self._original_complete(text, line_buffer, cursor_pos)
        else:
            paths, search_path, _, _ = self._get_completion_paths(line_buffer)
            match = search_path

            # PyDev expects just the end part of the expression back broken at the last punctuation
            completion = []
            for path in paths:
                # py dev replaces back to the last splitting character.
                # Find that in the line buffer. E.g.
                # I have a script called play.py
                # I type C:/script/pl
                # This function will add only play.py to the list
                # (back to the last splitting character, i.e. /)
                # There is a special case when it is just load_script(
                if line_buffer.endswith("load_script("):
                    line_buffer_back_to_last_splitting_character = '"'
                else:
                    line_buffer_back_to_last_splitting_character = re.split(
                        r"[/:\\ .-]", line_buffer
                    )[-1]

                # find extra path to add
                len_of_overlap = len(search_path)
                completion_path = path[len_of_overlap:].replace("\\", "/")

                # assemble the auto replace
                completion.append(
                    "{}{}".format(line_buffer_back_to_last_splitting_character, completion_path)
                )

        return match, completion


class PyDevComplete:
    """
    In PyDev the completer is at a higher level, it uses the ipython
    completer above and adds extra completion
    we need to override this to return just the paths and
    not the other possible completions.
    This is not nice code because I am manipulating
    private methods but there is no other way to do this.
    """

    def __init__(self, original_function: Callable) -> None:
        """
        Initialise
        Args:
            original_function: the original completion function that we will call
        """
        self.original_function = original_function

    def just_path_on_load(self, text: str, act_tok: Any) -> list[str]:
        """
        Returns completions for load on a path if load_script in path otherwise returns as before.
        Will replace .metadata\.plugins\org.eclipse.pde.core\.bundle_pool\plugins\
        org.python.pydev_5.9.2.201708151115\pysrc\_pydev_bundle\pydev_ipython_console_011.py

        This functions will filter out the pydev completions if the line contains load_script. 
        It know which are the pydev ones because they are marked with the type '11'.

        Args:
            text: text to complete
            act_tok: token, used only in original completion

        Returns:
            pydev completions

        """
        # This is the completion type assigned to all ipython completions in pydev
        ipython_completer_completion_type = "11"
        ans = self.original_function(text, act_tok)
        # returns list of tuples (completion, py doc, ?, type)
        if LOAD_SCRIPT_COMMAND in text:
            ans = [an for an in ans if an[3] == ipython_completer_completion_type]
        return ans


try:
    # replace the original completer in ipython with the one above
    ipy_completer = IPython.get_ipython().Completer.complete
    _load_script_completer = LoadScriptCompleter(ipy_completer)
    IPython.get_ipython().set_custom_completer(_load_script_completer.standalone_complete, 0)

    try:
        # Replace the old completer in pydev with the new completer above and turns on pydev
        from _pydev_bundle.pydev_ipython_console_011 import _PyDevFrontEndContainer

        _PyDevFrontEndContainer._instance.getCompletions = PyDevComplete(
            _PyDevFrontEndContainer._instance.getCompletions
        ).just_path_on_load
        _load_script_completer.is_pydev = True
        # Pydev does not honor IPython custom_completer, so use an old-style function replace
        # (this no longer works in standalone python window so cannot use same style for both cases)
        IPython.get_ipython().Completer.complete = _load_script_completer.pydev_complete
    except ImportError:
        pass
        # this means we are not in pydev
except AttributeError:
    print("ERROR: IPython does not exist, auto complete not installed")

# END TAB COMPLETE


def usercommand(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that marks a function as a user command (e.g. for NICOS).
    """
    func.is_usercommand = True
    func.is_hidden = False
    return func


def helparglist(args: Any) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that supplies a custom argument list to be displayed by
    a help (e.g. for NICOS).
    """

    def deco(func: Callable[P, T]) -> Callable[P, T]:
        func.help_arglist = args  # type: ignore
        return func

    return deco


def log_command_and_handle_exception(f: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that will log the command when run and will
    catch all exceptions to be handled by genie.

    Note: _func_name_unlikely_to_be_reused must be called something that a user will not
    accidentally put into a genie function
    """

    @functools.wraps(f)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        log_args = {"kwargs": kwargs}
        arg_names = getfullargspec(f).args
        # If we can get the argument names the include them in the log
        if len(arg_names) >= len(args):
            log_args["args"] = dict(zip(arg_names, args))
        else:
            log_args["args"] = args

        command_exception = None
        start = time.time()
        try:
            return_value = f(*args, **kwargs)
            return return_value
        except Exception as e:
            command_exception = traceback.format_exc()
            _handle_exception(e)
            return None  # type: ignore
        finally:
            end = time.time()
            time_taken = end - start
            # hack to allow tests to pass. linux has microsecond resolution,
            # Windows only as millisecond but can be >1ms occasionaly and
            # mock is expecting 0.0
            if time_taken < 0.002:
                time_taken = 0.0
            __api.logger.log_command(f.__name__, log_args, command_exception, time_taken=time_taken)
            if command_exception is not None:
                __api.logger.log_command_error_msg(f.__name__, command_exception)

    decorator.__signature__ = inspect.signature(f)  # type: ignore
    return decorator


def _print_error_message(message: str) -> None:
    """
    Print the error message to screen.
    """
    if os.name == "nt":
        # Is windows
        class ConsoleScreenBufferInfo(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.wintypes._COORD),  # type: ignore
                ("dwCursorPosition", ctypes.wintypes._COORD),  # type: ignore
                ("wAttributes", ctypes.c_ushort),  # type: ignore
                ("srWindow", ctypes.wintypes._SMALL_RECT),  # type: ignore
                ("dwMaximumWindowSize", ctypes.wintypes._COORD),  # type: ignore
            ]

        std_output_handle = -11
        stdout_handle = ctypes.windll.kernel32.GetStdHandle(std_output_handle)
        csbi = ConsoleScreenBufferInfo()
        ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, ctypes.byref(csbi))
        old_attrs = csbi.wAttributes
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, 12)
        print("ERROR: " + message)
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, old_attrs)
    else:
        # Non-windows
        print("\033[91m" + "ERROR: " + message + "\033[0m")
    # Log it
    __api.logger.log_error_msg(message)


_exceptions_raised = False


def _handle_exception(exception: Exception | None = None, message: str | None = None) -> None:
    """
    Handles any exception in the way we want.
    """
    if exception is not None:
        if _exceptions_raised:
            raise exception
        if message is not None:
            _print_error_message(message)
        else:
            traceback.print_exc(file=sys.stderr)
    elif message is not None:
        _print_error_message(message)
        if _exceptions_raised:
            raise Exception(message)
    else:
        _print_error_message("UNSPECIFIED")
