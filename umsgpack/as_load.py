# as_load.py A lightweight asynchronous MessagePack deserializer module.

# Adapted for MicroPython by Peter Hinch
# Copyright (c) 2021 Peter Hinch

# Original source: https://github.com/vsergeev/u-msgpack-python
# See __init__.py for details of changes made for MicroPython.

import struct
import collections
from . import *

try:
    from . import umsgpack_ext
except ImportError:
    pass


def _fail():  # Debug code should never be called.
    raise Exception("Logic error")


async def _re(fp, n, options):
    d = await fp.readexactly(n)
    observer = options.get("observer")
    if observer:
        observer.update(d)
    return d


async def _re0(s, fp, n, options):
    d = await _re(fp, n, options)
    return struct.unpack(s, d)[0]


async def _unpack_integer(code, fp, options):
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
    return await _re0(s.strip(), fp, 1 << (ic & 3), options)


async def _unpack_float(code, fp, options):
    ic = ord(code)
    if ic == 0xCA:
        return await _re0(">f", fp, 4, options)
    if ic == 0xCB:
        return await _re0(">d", fp, 8, options)
    _fail()


async def _unpack_string(code, fp, options):
    ic = ord(code)
    if (ic & 0xE0) == 0xA0:
        length = ic & ~0xE0
    elif ic == 0xD9:
        length = await _re0("B", fp, 1, options)
    elif ic == 0xDA:
        length = await _re0(">H", fp, 2, options)
    elif ic == 0xDB:
        length = await _re0(">I", fp, 4, options)
    else:
        _fail()

    data = await _re(fp, length, options)
    try:
        return str(data, "utf-8")  # Preferred MP way to decode
    except:  # MP does not have UnicodeDecodeError
        if options.get("allow_invalid_utf8"):
            return data  # MP Remove InvalidString class: subclass of built-in class
        raise InvalidStringException("unpacked string is invalid utf-8")


async def _unpack_binary(code, fp, options):
    ic = ord(code)
    if ic == 0xC4:
        length = await _re0("B", fp, 1, options)
    elif ic == 0xC5:
        length = await _re0(">H", fp, 2, options)
    elif ic == 0xC6:
        length = await _re0(">I", fp, 4, options)
    else:
        _fail()

    return await _re(fp, length, options)


async def _unpack_ext(code, fp, options):
    ic = ord(code)
    n = b"\xd4\xd5\xd6\xd7\xd8".find(code)
    length = 0 if n < 0 else 1 << n
    if not length:
        if ic == 0xC7:
            length = await _re0("B", fp, 1, options)
        elif ic == 0xC8:
            length = await _re0(">H", fp, 2, options)
        elif ic == 0xC9:
            length = await _re0(">I", fp, 4, options)
        else:
            _fail()

    ext_type = await _re0("b", fp, 1, options)
    ext_data = await _re(fp, length, options)

    # Create extension object
    ext = Ext(ext_type, ext_data)

    # Unpack with ext handler, if we have one
    ext_handlers = options.get("ext_handlers")
    if ext_handlers and ext.type in ext_handlers:
        return ext_handlers[ext.type](ext)
    # Unpack with ext classes, if type is registered
    if ext_type in ext_type_to_class:
        try:
            return ext_type_to_class[ext_type].unpackb(ext_data)
        except AttributeError:
            raise NotImplementedError(
                "Ext class {:s} lacks unpackb()".format(repr(ext_type_to_class[ext_type]))
            )

    return ext


async def _unpack_array(code, fp, options):
    ic = ord(code)
    if (ic & 0xF0) == 0x90:
        length = ic & ~0xF0
    elif ic == 0xDC:
        length = await _re0(">H", fp, 2, options)
    elif ic == 0xDD:
        length = await _re0(">I", fp, 4, options)
    else:
        _fail()
    l = []
    for i in range(length):
        l.append(await _unpack(fp, options))
    return tuple(l) if options.get("use_tuple") else l


def _deep_list_to_tuple(obj):
    if isinstance(obj, list):
        return tuple([_deep_list_to_tuple(e) for e in obj])
    return obj


async def _unpack_map(code, fp, options):
    ic = ord(code)
    if (ic & 0xF0) == 0x80:
        length = ic & ~0xF0
    elif ic == 0xDE:
        length = await _re0(">H", fp, 2, options)
    elif ic == 0xDF:
        length = await _re0(">I", fp, 4, options)
    else:
        _fail()

    d = {} if not options.get("use_ordered_dict") else collections.OrderedDict()
    for _ in range(length):
        # Unpack key
        k = await _unpack(fp, options)

        if isinstance(k, list):
            # Attempt to convert list into a hashable tuple
            k = _deep_list_to_tuple(k)
        try:
            hash(k)
        except:
            raise UnhashableKeyException('unhashable key: "{:s}"'.format(str(k)))
        if k in d:
            raise DuplicateKeyException(
                'duplicate key: "{:s}" ({:s})'.format(str(k), str(type(k)))
            )

        # Unpack value
        v = await _unpack(fp, options)

        try:
            d[k] = v
        except TypeError:
            raise UnhashableKeyException('unhashable key: "{:s}"'.format(str(k)))
    return d


async def _unpack(fp, options):
    code = await _re(fp, 1, options)
    ic = ord(code)
    if (ic <= 0x7F) or (0xCC <= ic <= 0xD3) or (0xE0 <= ic <= 0xFF):
        return await _unpack_integer(code, fp, options)
    if ic <= 0xC9:
        if ic <= 0xC3:
            if ic <= 0x8F:
                return await _unpack_map(code, fp, options)
            if ic <= 0x9F:
                return await _unpack_array(code, fp, options)
            if ic <= 0xBF:
                return await _unpack_string(code, fp, options)
            if ic == 0xC1:
                raise ReservedCodeException("got reserved code: 0xc1")
            return (None, 0, False, True)[ic - 0xC0]
        if ic <= 0xC6:
            return await _unpack_binary(code, fp, options)
        return _unpack_ext(code, fp, options)
    if ic <= 0xCB:
        return await _unpack_float(code, fp, options)
    if ic <= 0xD8:
        return await _unpack_ext(code, fp, options)
    if ic <= 0xDB:
        return await _unpack_string(code, fp, options)
    if ic <= 0xDD:
        return await _unpack_array(code, fp, options)
    return await _unpack_map(code, fp, options)


# Interface to __init__.py


async def aload(fp, options):
    return await _unpack(fp, options)
