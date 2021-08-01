# as_load.py A lightweight asynchronous MessagePack deserializer module.

# Adapted for MicroPython by Peter Hinch
# Copyright (c) 2021 Peter Hinch

# Original source: https://github.com/vsergeev/u-msgpack-python
# See __init__.py for details of changes made for MicroPython.

import struct
import collections
import io
from uasyncio import StreamReader
from . import *
try:
    from . import umsgpack_ext
except ImportError:
    pass


async def _re0(s, fp, n):
    d = await fp.readexactly(n)
    return struct.unpack(s, d)[0]

async def _unpack_integer(code, fp):
    ic = ord(code)
    if (ic & 0xe0) == 0xe0:
        return struct.unpack("b", code)[0]
    if (ic & 0x80) == 0x00:
        return struct.unpack("B", code)[0]
    ic -= 0xcc
    off = ic << 1
    try:
        s = "B >H>I>Qb >h>i>q"[off : off + 2]
    except IndexError:
        _fail()
    return await _re0(s.strip(), fp, 1 << (ic & 3))


async def _unpack_float(code, fp):
    ic = ord(code)
    if ic == 0xca:
        return await _re0(">f", fp, 4)
    if ic == 0xcb:
        return await _re0(">d", fp, 8)
    _fail()


async def _unpack_string(code, fp, options):
    ic = ord(code)
    if (ic & 0xe0) == 0xa0:
        length = ic & ~0xe0
    elif ic == 0xd9:
        length = await _re0("B", fp, 1)
    elif ic == 0xda:
        length = await _re0(">H", fp, 2)
    elif ic == 0xdb:
        length = await _re0(">I", fp, 4)
    else:
        _fail()

    data = await fp.readexactly(length)
    try:
        return str(data, 'utf-8')  # Preferred MP way to decode
    except:  # MP does not have UnicodeDecodeError
        if options.get("allow_invalid_utf8"):
            return data  # MP Remove InvalidString class: subclass of built-in class
        raise InvalidStringException("unpacked string is invalid utf-8")


async def _unpack_binary(code, fp):
    ic = ord(code)
    if ic == 0xc4:
        length = await _re0("B", fp, 1)
    elif ic == 0xc5:
        length = await _re0(">H", fp, 2)
    elif ic == 0xc6:
        length = await _re0(">I", fp, 4)
    else:
        _fail()

    return await fp.readexactly(length)


async def _unpack_ext(code, fp, options):
    ic = ord(code)
    n = b'\xd4\xd5\xd6\xd7\xd8'.find(code)
    length = 0 if n < 0 else 1 << n
    if not length:
        if ic == 0xc7:
            length = await _re0("B", fp, 1)
        elif ic == 0xc8:
            length = await _re0(">H", fp, 2)
        elif ic == 0xc9:
            length = await _re0(">I", fp, 4)
        else:
            _fail()

    ext_type = await _re0("b", fp, 1)
    ext_data = await fp.readexactly(length)

    # Create extension object
    ext = Ext(ext_type, ext_data)

    # Unpack with ext handler, if we have one
    ext_handlers = options.get("ext_handlers")
    if ext_handlers and ext.type in ext_handlers:
        return ext_handlers[ext.type](ext)
    # Unpack with ext classes, if type is registered
    if ext_type in _ext_type_to_class:
        try:
            return _ext_type_to_class[ext_type].unpackb(ext_data)
        except AttributeError:
            raise NotImplementedError("Ext class {:s} lacks unpackb()".format(repr(_ext_type_to_class[ext_type])))

    return ext

async def _unpack_array(code, fp, options):
    ic = ord(code)
    if (ic & 0xf0) == 0x90:
        length = (ic & ~0xf0)
    elif ic == 0xdc:
        length = await _re0(">H", fp, 2)
    elif ic == 0xdd:
        length = await _re0(">I", fp, 4)
    else:
        _fail()
    l = []
    for i in range(length):
        l.append(await _unpack(fp, options))
    return tuple(l) if options.get('use_tuple') else l


def _deep_list_to_tuple(obj):
    if isinstance(obj, list):
        return tuple([_deep_list_to_tuple(e) for e in obj])
    return obj


async def _unpack_map(code, fp, options):
    ic = ord(code)
    if (ic & 0xf0) == 0x80:
        length = (ic & ~0xf0)
    elif ic == 0xde:
        length = await _re0(">H", fp, 2)
    elif ic == 0xdf:
        length = await _re0(">I", fp, 4)
    else:
        _fail()

    d = {} if not options.get('use_ordered_dict') \
        else collections.OrderedDict()
    for _ in range(length):
        # Unpack key
        k = await _unpack(fp, options)

        if isinstance(k, list):
            # Attempt to convert list into a hashable tuple
            k = _deep_list_to_tuple(k)
        try:
            hash(k)
        except:
            raise UnhashableKeyException(
                "unhashable key: \"{:s}\"".format(str(k)))
        if k in d:
            raise DuplicateKeyException(
                "duplicate key: \"{:s}\" ({:s})".format(str(k), str(type(k))))

        # Unpack value
        v = await _unpack(fp, options)

        try:
            d[k] = v
        except TypeError:
            raise UnhashableKeyException(
                "unhashable key: \"{:s}\"".format(str(k)))
    return d


async def _unpack(fp, options):
    code = await fp.readexactly(1)
    ic = ord(code)
    if (ic <= 0x7f) or (0xcc <= ic <= 0xd3) or (0xe0 <= ic <= 0xff):
        return await _unpack_integer(code, fp)
    if ic <= 0xc9:
        if ic <= 0xc3:
            if ic <= 0x8f:
                return await _unpack_map(code, fp, options)
            if ic <= 0x9f:
                return await _unpack_array(code, fp, options)
            if ic <= 0xbf:
                return await _unpack_string(code, fp, options)
            if ic == 0xc1:
                raise ReservedCodeException("got reserved code: 0xc1")
            return (None, 0, False, True)[ic - 0xc0]
        if ic <= 0xc6:
            return await _unpack_binary(code, fp)
        return _unpack_ext(code, fp, options)
    if ic <= 0xcb:
        return await _unpack_float(code, fp)
    if ic <= 0xd8:
        return await _unpack_ext(code, fp, options)
    if ic <= 0xdb:
        return await _unpack_string(code, fp, options)
    if ic <= 0xdd:
        return await _unpack_array(code, fp, options)
    return await _unpack_map(code, fp, options)

# Interface to __init__.py

async def aload(fp, options):
    return await _unpack(fp, options)
