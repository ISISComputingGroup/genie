from __future__ import absolute_import, print_function

import codecs
import json
import os
import re
import unicodedata
import zlib
from builtins import object
from datetime import timedelta
from functools import wraps

try:
    from nicos import session

    def check_break(level):
        session.breakpoint(level)
except ImportError:

    def check_break(level):
        pass


## call to make sure we cleanup any subprocesses on process termination
## useful to call from e.g. ioc test framework
## it creates windows job object with kill on close property, which will be inherited by sub processes
## when returned handle is closed, all processes will die
## we make sure we detach the Py_HANDLE object from the underlying WIN32 handle
## so termination is done by windows and not when pythion obecjt goes out of scope
def cleanup_subprocs_on_process_exit():
    if os.name == "nt":
        try:
            import win32api
            import win32job

            h = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(h, win32job.JobObjectExtendedLimitInformation)
            info["BasicLimitInformation"]["LimitFlags"] |= (
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            win32job.SetInformationJobObject(h, win32job.JobObjectExtendedLimitInformation, info)
            win32job.AssignProcessToJobObject(h, win32api.GetCurrentProcess())
            h.Detach()
        except Exception as err:
            raise OSError(f"cleanup_subprocs_on_process_exit() failed: {err}")


class PVReadException(Exception):
    """
    Exception to throw when there is a problem reading a PV.
    """

    def __init__(self, message):
        super(PVReadException, self).__init__(message)


def compress_and_hex(value):
    compr = zlib.compress(bytearray(value, "utf-8"))
    return codecs.encode(compr, "hex_codec")


def dehex_and_decompress(value):
    """
    Dehex and decompress a string and return it
    :param value: compressed hexed string
    :return: value as a strinnng
    """
    try:
        # If it comes as bytes then cast to string
        value = value.decode("utf-8")
    except AttributeError:
        pass

    return zlib.decompress(bytes.fromhex(value)).decode("utf-8")


def dehex_decompress_and_dejson(value):
    """
    Convert string from zipped hexed json to a python representation
    :param value: value to convert
    :return: python representation of json
    """
    return json.loads(dehex_and_decompress(value))


def waveform_to_string(data):
    output = ""
    for i in data:
        if i == 0:
            break
        if isinstance(i, str):
            output += i
        else:
            output += str(chr(i))
    return output


def convert_string_to_ascii(data):
    """
    Converts a string to be ascii.

    Args:
        data: the string to convert

    Returns:
        string: the ascii equivalent
    """

    def _make_ascii_mappings():
        """
        Create mapping for characters not converted to 7-bit by NFKD.
        """
        mappings_in = [ord(char) for char in "\xd0\xd7\xd8\xde\xdf\xf0\xf8\xfe"]
        mappings_out = "DXOPBoop"
        d = dict(list(zip(mappings_in, mappings_out)))
        d[ord("\xc6")] = "AE"
        d[ord("\xe6")] = "ae"
        return d

    # Replace all compatibility characters with their equivalents
    normalised = unicodedata.normalize("NFKD", data)
    # Keep non-combining chars only
    extracted = "".join([c for c in normalised if not unicodedata.combining(c)])
    # Finally translate to ascii
    return extracted.translate(_make_ascii_mappings()).encode("ascii", "ignore").decode("utf-8")


def get_correct_path(path):
    """
    Corrects the slashes and escapes any slash characters.

    Note: does not check whether the file exists.

    Args:
        path (string): the file path to correct

    Returns:
         string : the corrected file path
    """
    # Remove any unescaped chars
    path = _convert_to_rawstring(path)
    # Replace '\' with '/'
    path = path.replace("\\", "/").replace("'", "")
    # Remove multiple slashes
    return re.sub("/+", "/", path)


def get_time_delta(seconds, minutes, hours):
    """
    Returns a timedelta representation of the input seconds, minutes and hours. If all parameters are None, then
    None returned, else None parameters are interpreted as 0
    """
    if all(t is None for t in (seconds, minutes, hours)):
        return None
    else:
        num_seconds, num_minutes, num_hours = (
            0 if t is None else t for t in (seconds, minutes, hours)
        )
        return timedelta(hours=num_hours, minutes=num_minutes, seconds=num_seconds)


def _correct_path_casing_existing(path):
    """
    If the file exists it get the correct path with the correct casing.
    """
    if os.name == "nt":
        try:
            # Correct path case for windows as Python needs correct casing
            # Windows specific stuff
            import win32api

            return win32api.GetLongPathName(win32api.GetShortPathName(path))
        except Exception as err:
            raise OSError("Invalid file path entered: %s" % err)
    else:
        # Nothing to do for unix
        return path


def _convert_to_rawstring(data):
    escape_dict = {
        "\a": r"\a",
        "\b": r"\b",
        "\c": r"\c",
        "\f": r"\f",
        "\n": r"\n",
        "\r": r"\r",
        "\t": r"\t",
        "\v": r"\v",
        "'": r"\'",
        '"': r"\"",
    }
    raw_string = ""
    for char in data:
        try:
            raw_string += escape_dict[char]
        except KeyError:
            raw_string += char
    return raw_string


def get_correct_filepath_existing(path):
    """
    Corrects the file path to make it OS independent.

    Args:
        path (string): the file path to correct

    Returns:
         string : the corrected file path

    Raises:
         if the directory does not exist.
    """
    path = get_correct_path(path)
    return _correct_path_casing_existing(path)


def crc8(value):
    """
    Generate a CRC 8 from the value (See EPICS\\utils_win32\\master\\src\\crc8.c).

    Args:
        value: the value to generate a CRC from

    Returns:
        string: representation of the CRC8 of the value; two characters

    """
    if value == "":
        return ""

    crc_size = 8
    maximum_crc_value = 255
    generator = 0x07

    as_bytes = value.encode("utf-8")

    crc = 0  # start with 0 so first byte can be 'xored' in

    for byte in as_bytes:
        crc ^= byte  # XOR-in the next input byte

        for i in range(8):
            # unlike the c code we have to artifically restrict the maximum value wherever it is caluclated
            if (crc >> (crc_size - 1)) & maximum_crc_value != 0:
                crc = ((crc << 1 & maximum_crc_value) ^ generator) & maximum_crc_value
            else:
                crc <<= 1

    return "{0:02X}".format(crc)


def get_json_pv_value(pv_name, api, attempts=3):
    """
    Get the pv value decompress and convert from JSON.

    Args:
        pv_name: name of the pv to read
        api: the api to use to read it
        attempts: number of attempts to try to read PV

    Returns:
        pv value as python objects

    Raises:
         PVReadException: if value can not be read

    """
    try:
        raw = api.get_pv_value(pv_name, to_string=True, attempts=attempts)
    except Exception:
        raise PVReadException("Can not read '{0}'".format(pv_name))

    try:
        raw = dehex_and_decompress(raw)
    except Exception:
        raise PVReadException("Can not decompress '{0}'".format(pv_name))

    try:
        result = json.loads(raw)
    except Exception:
        raise PVReadException("Can not unmarshal '{0}'".format(pv_name))

    return result


def remove_field_from_pv(pv):
    """
    Given a PV, return it with any field postfixes removed.

    examples:
        IN:TEST:FIELD.RVAL -> IN:TEST:FIELD
        IN:TEST:NOFIELD -> IN:TEST:NOFIELD

    args:
        pv (str): the pv to remove the field from

    returns:
        (str) the pv name with the field postfix removed
    """
    return pv.split(".")[0] if "." in pv else pv


def check_lowlimit_against_highlimit(lowlimit, highlimit):
    """
    Check the lowlimit is below the highlimit, and warns if this is the case
    """
    if lowlimit is not None and highlimit is not None and lowlimit > highlimit:
        print(
            "WARNING: You have set the lowlimit({}) above the highlimit({})".format(
                lowlimit, highlimit
            )
        )


def require_runstate(runstates):
    """
    Decorator that checks for needed runstates.
    If skip_required_runstates is passed in as a keyword argument to the underlying function then it will be ignore this
    check
    """
    runstates_string = ", ".join(runstates)

    def _check_runstate(func):
        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            if not kwargs.pop("skip_required_runstates", False):
                run_state = self.get_run_state()
                if run_state not in set(runstates):
                    e_string = "{} can only be run in the following runstates: {}".format(
                        func.__name__, runstates_string
                    )
                    raise ValueError(e_string)
            return func(self, *args, **kwargs)

        return _wrapper

    return _check_runstate


class EnvironmentDetails(object):
    """
    Details of the computer environment the code is running in.
    """

    # PV which holds the live instrument list
    INSTRUMENT_LIST_PV = "CS:INSTLIST"

    # List of instruments dictionary similar to CS:INSTLIST
    DEFAULT_INST_LIST = [
        {"name": "LARMOR"},
        {"name": "ALF"},
        {"name": "DEMO"},
        {"name": "IMAT"},
        {"name": "MUONFE"},
        {"name": "ZOOM"},
        {"name": "IRIS"},
    ]

    def __init__(self, host_name=None):
        """
        Consturctor.

        Args:
            host_name: computer host name to use; None to get it from the system
        Returns:

        """
        import socket

        if host_name is None:
            self._host_name = socket.gethostname()
        else:
            self._host_name = host_name

    def get_host_name(self):
        """
        Gets the name of the computer.

        Returns:
            the host name of the computer
        """
        return self._host_name

    def get_instrument_list(self, api):
        """
        Get the instrument list.

        Args:
            api: api to use to get a pv value

        Returns:
            the current instrument list
        """
        try:
            return get_json_pv_value(self.INSTRUMENT_LIST_PV, api, attempts=1)
        except PVReadException as ex:
            print("Error: {!r}. Using internal instrument list.".format(ex))
            return self.DEFAULT_INST_LIST

    def get_settings_directory(self):
        default_directory = "C:/Instrument/Settings/config/{}/configurations".format(
            self._host_name
        )
        return os.environ.get("ICPCONFIGROOT", default_directory)
