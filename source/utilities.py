import json
import zlib
import os
import re


class PVReadException(Exception):
    """
    Exception to throw when there is a problem reading a pv
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def compress_and_hex(value):
    compr = zlib.compress(value)
    return compr.encode('hex')


def dehex_and_decompress(value):
    return zlib.decompress(value.decode("hex"))


def waveform_to_string(data):
    output = ""
    for i in data:
        if i == 0:
            break
        output += str(unichr(i))
    return output


def get_correct_path(path):
    """Corrects the slashes and escapes any slash characters.

    Note: does not check whether the file exists.

    Args:
        path (string): the file path to correct

    Returns:
         string : the corrected file path
    """
    # Remove any unescaped chars
    path = _convert_to_rawstring(path)
    # Replace '\' with '/'
    path = path.__repr__().replace("\\", "/").replace("'", "")
    # Remove multiple slashes
    return re.sub('/+', '/', path)


def _correct_path_casing_existing(path):
    """If the file exists it get the correct path with the correct casing"""
    if os.name == 'nt':
        try:
            # Correct path case for windows as Python needs correct casing
            # Windows specific stuff
            import win32api
            return win32api.GetLongPathName(win32api.GetShortPathName(path))
        except Exception as err:
            raise Exception("Invalid file path entered: %s" % err)
    else:
        # Nothing to do for unix
        return path


def _convert_to_rawstring(data):
    escape_dict = {'\a': r'\a',
                   '\b': r'\b',
                   '\c': r'\c',
                   '\f': r'\f',
                   '\n': r'\n',
                   '\r': r'\r',
                   '\t': r'\t',
                   '\v': r'\v',
                   '\'': r'\'',
                   '\"': r'\"'}
    raw_string = ''
    for char in data:
        try:
            raw_string += escape_dict[char]
        except KeyError:
            raw_string += char
    return raw_string


def get_correct_filepath_existing(path):
    """Corrects the file path to make it OS independent.

    Raises if the file does not exist.

    Args:
        path (string): the file path to correct

    Returns:
         string : the corrected file path
    """
    path = get_correct_path(path)
    return _correct_path_casing_existing(path)


def get_correct_directory_path_existing(path):
    """Corrects the directory path to make it OS independent.

        Raises if the directory does not exist.

        Args:
            path (string): the directory path to correct

        Returns:
             string : the corrected directory path
        """
    name = get_correct_path(path)
    return _correct_path_casing_existing(name)


def crc8(value):
    """
    Generate a CRC 8 from the value (See EPICS\utils_win32\master\src\crc8.c)
    Args:
        value: the value to generate a CRC from

    Returns: a string representation of the CRC8 of the value; two characters

    """
    if value == "":
        return ""

    crc_size = 8
    maximum_crc_value = 255
    generator = 0x07

    bytes = bytearray()
    bytes.extend(value)

    crc = 0  # start with 0 so first byte can be 'xored' in

    for byte in bytes:
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
    Get the pv value decompress and convert from json
    Args:
        pv_name: name of the pv to read
        api: the api to use to read it
        attempts: number of attempts to try to read PV

    Returns: pv value as python objects
    Raises PVReadException: if value can not be read

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


class EnvironmentDetails(object):
    """
    Details of the computer environment the code is running in.
    """

    # PV which holds the live instrument list
    INSTRUMENT_LIST_PV = "CS:INSTLISTa"

    # List of instruments dictionary similar to CS:INSTLIST
    DEFAULT_INST_LIST = [
        {"name": "LARMOR"},
        {"name": "ALF"},
        {"name": "DEMO"},
        {"name": "IMAT"},
        {"name": "MUONFE"},
        {"name": "ZOOM"},
        {"name": "IRIS"}]

    def __init__(self, host_name=None):
        """
        Consturctor
        Args:
            host_name: computer host name to use; None to get it from the system
        Returns:

        """
        import socket

        if host_name is None:
            self._host_name = socket.gethostname()
        else:
            self._host_name = host_name

    def host_name(self):
        """

        Returns: the host name of the computer

        """

        return self._host_name

    def get_instrument_list(self, api):
        """
        Get the instrument list
        Args:
            api: api to use to get a pv value
        Returns: the current instrument list
        """
        try:
            return get_json_pv_value(self.INSTRUMENT_LIST_PV, api, attempts=1)
        except PVReadException as ex:
            print "Error: {0}. Using internal instrument list.".format(ex.message)
            return self.DEFAULT_INST_LIST
