import zlib
import os
import re

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
    return  _correct_path_casing_existing(name)


