# mp_load.py A lightweight MessagePack serializer and deserializer module.

# Adapted for MicroPython by Peter Hinch

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE

# Original source: https://github.com/vsergeev/u-msgpack-python
# See __init__.py for details of changes made for MicroPython.

import struct
import collections
import io
from . import *


def _fail():  # Debug code should never be called.
    raise Exception("Logic error")


def _read_except(fp, n):
    if n == 0:
        return b""

    data = fp.read(n)
    if len(data) == 0:
        raise InsufficientDataException

    while len(data) < n:
        chunk = fp.read(n - len(data))
        if len(chunk) == 0:
            raise InsufficientDataException

        data += chunk

    return data


def _re0(s, fp, n):
    return struct.unpack(s, _read_except(fp, n))[0]


def _unpack_integer(code, fp):
    ic = ord(code)
    if (ic & 0xE0) == 0xE0:
        return struct.unpack("b", code)[0]
    if (ic & 0x80) == 0x00:
        return struct.unpack("B", code)[0]
    ic -= 0xCC
    off = ic << 1
    try:
        s = "B >H>I>Qb >h>i>q"[off : off + 2]
    except IndexError:
        _fail()
    return _re0(s.strip(), fp, 1 << (ic & 3))


def _unpack_float(code, fp):
    ic = ord(code)
    if ic == 0xCA:
        return _re0(">f", fp, 4)
    if ic == 0xCB:
        return _re0(">d", fp, 8)
    _fail()


def _unpack_string(code, fp, options):
    ic = ord(code)
    if (ic & 0xE0) == 0xA0:
        length = ic & ~0xE0
    elif ic == 0xD9:
        length = _re0("B", fp, 1)
    elif ic == 0xDA:
        length = _re0(">H", fp, 2)
    elif ic == 0xDB:
        length = _re0(">I", fp, 4)
    else:
        _fail()

    data = _read_except(fp, length)
    try:
        return str(data, "utf-8")  # Preferred MP way to decode
    except:  # MP does not have UnicodeDecodeError
        if options.get("allow_invalid_utf8"):
            return data  # MP Remove InvalidString class: subclass of built-in class
        raise InvalidStringException("unpacked string is invalid utf-8")


def _unpack_binary(code, fp):
    ic = ord(code)
    if ic == 0xC4:
        length = _re0("B", fp, 1)
    elif ic == 0xC5:
        length = _re0(">H", fp, 2)
    elif ic == 0xC6:
        length = _re0(">I", fp, 4)
    else:
        _fail()

    return _read_except(fp, length)


def _unpack_ext(code, fp, options):
    ic = ord(code)
    n = b"\xd4\xd5\xd6\xd7\xd8".find(code)
    length = 0 if n < 0 else 1 << n
    if not length:
        if ic == 0xC7:
            length = _re0("B", fp, 1)
        elif ic == 0xC8:
            length = _re0(">H", fp, 2)
        elif ic == 0xC9:
            length = _re0(">I", fp, 4)
        else:
            _fail()

    ext_type = _re0("b", fp, 1)
    ext_data = _read_except(fp, length)

    # Unpack with ext classes, if type is registered
    if ext_type in packers:
        cls = packers[ext_type]
        try:
            return cls.unpackb(ext_data, options)
        except AttributeError:
            raise NotImplementedError(f"Ext class {repr(cls)} lacks unpackb()")
    raise UnsupportedTypeException(f"ext_type: 0x{ext_type:0X}")


def _unpack_array(code, fp, options):
    ic = ord(code)
    if (ic & 0xF0) == 0x90:
        length = ic & ~0xF0
    elif ic == 0xDC:
        length = _re0(">H", fp, 2)
    elif ic == 0xDD:
        length = _re0(">I", fp, 4)
    else:
        _fail()
    g = (mpload(fp, options) for i in range(length))  # generator
    return tuple(g) if options.get("use_tuple") else list(g)


def _deep_list_to_tuple(obj):
    if isinstance(obj, list):
        return tuple([_deep_list_to_tuple(e) for e in obj])
    return obj


def _unpack_map(code, fp, options):
    ic = ord(code)
    if (ic & 0xF0) == 0x80:
        length = ic & ~0xF0
    elif ic == 0xDE:
        length = _re0(">H", fp, 2)
    elif ic == 0xDF:
        length = _re0(">I", fp, 4)
    else:
        _fail()

    d = {} if not options.get("use_ordered_dict") else collections.OrderedDict()
    for _ in range(length):
        # Unpack key
        k = mpload(fp, options)

        if isinstance(k, list):
            # Attempt to convert list into a hashable tuple
            k = _deep_list_to_tuple(k)
        try:
            hash(k)
        except:
            raise UnhashableKeyException(f'"{str(k)}"')
        if k in d:
            raise DuplicateKeyException(f'"{str(k)}" ({type(k)})')

        # Unpack value
        v = mpload(fp, options)

        try:
            d[k] = v
        except TypeError:
            raise UnhashableKeyException(f'"{str(k)}"')
    return d


def mpload(fp, options):
    code = _read_except(fp, 1)
    ic = ord(code)
    if (ic <= 0x7F) or (0xCC <= ic <= 0xD3) or (0xE0 <= ic <= 0xFF):
        return _unpack_integer(code, fp)
    if ic <= 0xC9:
        if ic <= 0xC3:
            if ic <= 0x8F:
                return _unpack_map(code, fp, options)
            if ic <= 0x9F:
                return _unpack_array(code, fp, options)
            if ic <= 0xBF:
                return _unpack_string(code, fp, options)
            if ic == 0xC1:
                raise ReservedCodeException("got 0xc1")
            return (None, 0, False, True)[ic - 0xC0]
        if ic <= 0xC6:
            return _unpack_binary(code, fp)
        return _unpack_ext(code, fp, options)
    if ic <= 0xCB:
        return _unpack_float(code, fp)
    if ic <= 0xD8:
        return _unpack_ext(code, fp, options)
    if ic <= 0xDB:
        return _unpack_string(code, fp, options)
    if ic <= 0xDD:
        return _unpack_array(code, fp, options)
    return _unpack_map(code, fp, options)


# API


def load(fp, **options):
    return mpload(fp, options)


def loads(s, **options):
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("Need 'bytes' or 'bytearray'")
    return mpload(io.BytesIO(s), options)
