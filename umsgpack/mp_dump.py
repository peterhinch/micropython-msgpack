# mp_dump.py A lightweight MessagePack serializer and deserializer module.

# Adapted for MicroPython by Peter Hinch
# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE

# Original source: https://github.com/vsergeev/u-msgpack-python
# See __init__.py for details of changes made for MicroPython.

import struct
from collections import OrderedDict
import io
from . import *

# Auto-detect system float precision
_float_precision = "single" if len(str(1 / 3)) < 13 else "double"


def _fail():  # Debug code should never be called.
    raise Exception("Logic error")


# struct.pack returns a bytes object


def _pack_integer(obj, fp, _):
    if obj < 0:
        if obj >= -32:
            fp.write(struct.pack("b", obj))
        elif obj >= -(2 ** (8 - 1)):
            fp.write(b"\xd0")
            fp.write(struct.pack("b", obj))
        elif obj >= -(2 ** (16 - 1)):
            fp.write(b"\xd1")
            fp.write(struct.pack(">h", obj))
        elif obj >= -(2 ** (32 - 1)):
            fp.write(b"\xd2")
            fp.write(struct.pack(">i", obj))
        elif obj >= -(2 ** (64 - 1)):
            fp.write(b"\xd3")
            fp.write(struct.pack(">q", obj))
        else:
            raise UnsupportedTypeException("huge signed int")
    else:
        if obj < 128:
            fp.write(struct.pack("B", obj))
        elif obj < 2 ** 8:
            fp.write(b"\xcc")
            fp.write(struct.pack("B", obj))
        elif obj < 2 ** 16:
            fp.write(b"\xcd")
            fp.write(struct.pack(">H", obj))
        elif obj < 2 ** 32:
            fp.write(b"\xce")
            fp.write(struct.pack(">I", obj))
        elif obj < 2 ** 64:
            fp.write(b"\xcf")
            fp.write(struct.pack(">Q", obj))
        else:
            raise UnsupportedTypeException("huge unsigned int")


def _pack_boolean(obj, fp, _):
    fp.write(b"\xc3" if obj else b"\xc2")


def _pack_float(obj, fp, options):
    fpr = options.get("force_float_precision", _float_precision)
    if fpr == "double":
        fp.write(b"\xcb")
        fp.write(struct.pack(">d", obj))
    elif fpr == "single":
        fp.write(b"\xca")
        fp.write(struct.pack(">f", obj))
    else:
        raise ValueError("invalid float precision")


def _pack_string(obj, fp, _):
    obj = bytes(obj, "utf-8")  # Preferred MP encode method
    obj_len = len(obj)
    if obj_len < 32:
        fp.write(struct.pack("B", 0xA0 | obj_len))
    elif obj_len < 2 ** 8:
        fp.write(b"\xd9")
        fp.write(struct.pack("B", obj_len))
    elif obj_len < 2 ** 16:
        fp.write(b"\xda")
        fp.write(struct.pack(">H", obj_len))
    elif obj_len < 2 ** 32:
        fp.write(b"\xdb")
        fp.write(struct.pack(">I", obj_len))
    else:
        raise UnsupportedTypeException("huge string")
    fp.write(obj)


def _pack_binary(obj, fp, _):
    obj_len = len(obj)
    if obj_len < 2 ** 8:
        fp.write(b"\xc4")
        fp.write(struct.pack("B", obj_len))
    elif obj_len < 2 ** 16:
        fp.write(b"\xc5")
        fp.write(struct.pack(">H", obj_len))
    elif obj_len < 2 ** 32:
        fp.write(b"\xc6")
        fp.write(struct.pack(">I", obj_len))
    else:
        raise UnsupportedTypeException("huge binary string")
    fp.write(obj)


# Pack an externally handled data type.
def _pack_ext(
    otype, odata, fp, tb=b"\x00\xd4\xd5\x00\xd6\x00\x00\x00\xd7\x00\x00\x00\x00\x00\x00\x00\xd8"
):
    obj_len = len(odata)  # Packed data
    ot = otype & 0xFF  # Type code
    code = tb[obj_len] if obj_len <= 16 else 0
    if code:
        fp.write(int.to_bytes(code, 1, "big"))
        fp.write(struct.pack("B", ot))
    elif obj_len < 2 ** 8:
        fp.write(b"\xc7")
        fp.write(struct.pack("BB", obj_len, ot))
    elif obj_len < 2 ** 16:
        fp.write(b"\xc8")
        fp.write(struct.pack(">HB", obj_len, ot))
    elif obj_len < 2 ** 32:
        fp.write(b"\xc9")
        fp.write(struct.pack(">IB", obj_len, ot))
    else:
        raise UnsupportedTypeException("huge ext data")
    fp.write(odata)


def _pack_array(obj, fp, options):
    obj_len = len(obj)
    if obj_len < 16:
        fp.write(struct.pack("B", 0x90 | obj_len))
    elif obj_len < 2 ** 16:
        fp.write(b"\xdc")
        fp.write(struct.pack(">H", obj_len))
    elif obj_len < 2 ** 32:
        fp.write(b"\xdd")
        fp.write(struct.pack(">I", obj_len))
    else:
        raise UnsupportedTypeException("huge array")

    for e in obj:
        mpdump(e, fp, options)


def _pack_map(obj, fp, options):
    obj_len = len(obj)
    if obj_len < 16:
        fp.write(struct.pack("B", 0x80 | obj_len))
    elif obj_len < 2 ** 16:
        fp.write(b"\xde")
        fp.write(struct.pack(">H", obj_len))
    elif obj_len < 2 ** 32:
        fp.write(b"\xdf")
        fp.write(struct.pack(">I", obj_len))
    else:
        raise UnsupportedTypeException("huge array")

    for k, v in obj.items():
        mpdump(k, fp, options)
        mpdump(v, fp, options)


def _utype(obj):
    raise UnsupportedTypeException(f"{type(obj)}")


# ***** Interface to __init__.py *****

# Despatch table
_dtable = {
    bool: _pack_boolean,
    int: _pack_integer,
    float: _pack_float,
    str: _pack_string,
    bytes: _pack_binary,
    bytearray: _pack_binary,
    list: _pack_array,
    tuple: _pack_array,
    dict: _pack_map,
    OrderedDict: _pack_map,  # Should not be necessary: OrderedDict is a dict
}
# Pack with unicode 'str' type, 'bytes' type
# options is a dict (from __init__.dump())
def mpdump(obj, fp, options):
    if obj is None:
        fp.write(b"\xc0")
        return
    # Try extension types before native types. This because extension can override
    # native (tuple)
    t = next((t for t in types if isinstance(obj, t)), None)
    if t is not None:
        ex, v = types[t]  # Instance or class, ext_type
        if isinstance(ex, type):  # Class: must instantiate
            obj = ex(obj, options)
            types[t] = obj, v
        else:
            obj = ex(obj)  # Assign the object to the Packer
        try:
            _pack_ext(v, obj.packb(), fp)
        except AttributeError:
            raise NotImplementedError("Class {:s} lacks packb()".format(repr(obj.__class__)))
        return

    # Is obj a native built-in type?
    func = _dtable.get(obj.__class__, None)
    if func is not None:
        func(obj, fp, options)
        return

    if not custom:  # Custom class is last chance saloon.
        return _utype(obj)

    # Look for custom class
    # custom dict: key is class, value is ext_type
    t = next((t for t in custom if isinstance(obj, t)), None)
    if t:
        try:
            _pack_ext(custom[t], obj.packb(), fp)
            return
        except AttributeError:
            pass
    _utype(obj)


def mpdumps(obj, options):
    fp = io.BytesIO()
    mpdump(obj, fp, options)
    return fp.getvalue()
