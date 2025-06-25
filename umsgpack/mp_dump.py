# mp_dump.py A lightweight MessagePack serializer and deserializer module.

# Adapted for MicroPython by Peter Hinch
# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE

# Original source: https://github.com/vsergeev/u-msgpack-python
# See __init__.py for details of changes made for MicroPython.

import struct
from collections import OrderedDict
import io
from . import *


def _fail():  # Debug code should never be called.
    raise Exception("Logic error")


# struct.pack returns a bytes object


def _pack_integer(obj, fp):
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


def _pack_boolean(obj, fp):
    fp.write(b"\xc3" if obj else b"\xc2")


def _pack_float(obj, fp, options):
    fpr = options.get("force_float_precision", float_precision)
    if fpr == "double":
        fp.write(b"\xcb")
        fp.write(struct.pack(">d", obj))
    elif fpr == "single":
        fp.write(b"\xca")
        fp.write(struct.pack(">f", obj))
    else:
        raise ValueError("invalid float precision")


def _pack_string(obj, fp):
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


def _pack_binary(obj, fp):
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


# Pack an externally handled data type. Args:
# otype ext_type byte
# odata Raw packed data from user class or extended built-in
# fp Destination stream.
# Sends MessagePack header followed by raw data.
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

# Pack with unicode 'str' type, 'bytes' type
# options is a dict (from dump())
def mpdump(obj, fp, options):
    if obj is None:
        fp.write(b"\xc0")
        return
    # Try extension builtin types before native types. This because extension can override
    # native (tuple)
    try:
        t = next((t for t in builtins if isinstance(obj, t)))  # Retrieve matching type
        # If there is a matching built-in, dict holds Packer class, ext_type byte
        pk, v = builtins[t]  # pk: Packer class, v: ext_type
        try:
            # Run the Packer and prepend MessagePack header
            _pack_ext(v, pk.packb(obj, options), fp)
        except AttributeError:
            raise NotImplementedError(f"Class {repr(obj.__class__)} invalid packb()")
        return
    except StopIteration:
        pass
    # Is obj a built-in type?
    # NOTE: using a depatch table consumed 1800 bytes more than code below.
    if isinstance(obj, bool):
        _pack_boolean(obj, fp)
        return
    if isinstance(obj, int):
        _pack_integer(obj, fp)
        return
    if isinstance(obj, float):
        _pack_float(obj, fp, options)
        return
    if isinstance(obj, str):
        _pack_string(obj, fp)
        return
    if isinstance(obj, (bytes, bytearray)):
        _pack_binary(obj, fp)
        return
    if isinstance(obj, (list, tuple)):
        _pack_array(obj, fp, options)
        return
    if isinstance(obj, (dict, OrderedDict)):
        _pack_map(obj, fp, options)
        return

    if not custom:  # Custom class is last chance saloon.
        return _utype(obj)

    # Look for custom class
    # custom dict: key is class, value is ext_type
    try:
        t = next((t for t in custom if isinstance(obj, t)))
    except StopIteration:
        _utype(obj)  # FAIL: unknown data type
    try:
        _pack_ext(custom[t], obj.packb(), fp)
    except AttributeError:
        _utype(obj)  # Fail


# ***** API *****
def dump(obj, fp, **options):
    mpdump(obj, fp, options)


def dumps(obj, **options):
    fp = io.BytesIO()
    mpdump(obj, fp, options)
    return fp.getvalue()
