import os
import tempfile
from types import TracebackType
from typing import IO

from genie_python.genie_script_checker import ScriptChecker


def write_to_temp_file(message: list[str], suffix: str = "", dir: str = "") -> IO[bytes]:
    """
    write to temporary file for test check_script

    Args:
        message: message to write to file
        suffix: filename suffix
        dir: directory to write into

    Returns:
        temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=dir)
    for line in message:
        temp_file.write(line.encode("utf-8"))
    temp_file.close()
    return temp_file


class CreateTempScriptAndReturnErrors:
    def __init__(
        self,
        script_checker: ScriptChecker,
        machine: str,
        script: list[str],
        warnings_as_error: bool = True,
        no_pyright: bool = False,
        no_pylint: bool = False,
        dir: str = "",
    ) -> None:
        self.script = script
        self.machine = machine
        self.dir = dir
        self.warnings_as_error = warnings_as_error
        self.no_pyright = no_pyright
        self.no_pylint = no_pylint
        self.script_checker = script_checker

    def __enter__(self) -> list[str]:
        self.temp_script_file = write_to_temp_file(self.script, dir=self.dir)
        return self.script_checker.check_script(
            self.temp_script_file.name,
            self.machine,
            warnings_as_error=self.warnings_as_error,
            no_pyright=self.no_pyright,
            no_pylint=self.no_pylint,
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType,
    ) -> None:
        os.unlink(self.temp_script_file.name)
