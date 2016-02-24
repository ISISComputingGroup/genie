import zlib


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
