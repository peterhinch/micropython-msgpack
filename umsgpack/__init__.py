# __init__.py A lightweight MessagePack serializer and deserializer module.

# Adapted for MicroPython by Peter Hinch
# Copyright (c) 2021 Peter Hinch Released under the MIT License see LICENSE

# This is a port of the version at
# https://github.com/vsergeev/u-msgpack-python
# refactored to reduce RAM consumption and trimmed to remove functionality
# irrelevant to MicroPython. It is compliant with a subset of the latest
# MessagePack specification at
# https://github.com/msgpack/msgpack/blob/master/spec.md
# In particular, it supports the new binary, UTF-8 string, and application ext
# types. It does not support timestamps.

# Principal changes.
# Python2 code removed.
# Compatibility mode removed.
# Timestamps removed.
# Converted to Python package with lazy import to save RAM.
# Provide asyncio StreamReader support.
# Exported functions now match ujson: dump, dumps, load, loads (only).
# Further refactoring to reduce allocations.
# InvalidString class removed because it is a subclass of a native type.
# Method of detecting platform's float size changed.
# Version reset to (0.1.0).

__version__ = (0, 2, 0)

# Auto-detect system float precision
float_precision = "single" if len(str(1 / 3)) < 13 else "double"

##############################################################################
# Ext Serializable Decorator
##############################################################################

# Global dicts
# Packer
custom = {}  # Pack custom. Key: Custom class. Value: ext_type integer.
builtins = {}  # Pack built-in. Key: data type to pack
# Value: (ext_type byte, Packer class).
# The second item is replaced with Packer instance once one exists.

# Unpacker
packers = {}  # Key: ext_type integer Value: Packer subclass.

# Decorator. Args:
# ext_type: An integer identifying the packed record.
# example: None in the case of a custom class. Where a Python built-in is handled
# by a Packer subclass, the class to be (un)packed is passed.
def ext_serializable(ext_type: int, example=None):
    def wrapper(cls):
        if not isinstance(ext_type, int):
            raise TypeError("Ext type is not type integer")
        elif not (-128 <= ext_type <= 127):
            raise ValueError("Ext type value {:d} is out of range of -128 to 127".format(ext_type))
        elif ext_type in packers:
            raise ValueError(
                "Ext type {:d} already registered with class {:s}".format(
                    ext_type, repr(packers[ext_type])
                )
            )
        elif cls in custom:
            raise ValueError(
                "Class {:s} already registered with Ext type {:d}".format(repr(cls), ext_type)
            )

        packers[ext_type] = cls  # For unpack
        if example is None:  # Custom class
            custom[cls] = ext_type
        else:  # Extension type having a Packer class
            builtins[example] = (cls, ext_type)
        return cls

    return wrapper


# Exceptions

# Base Exception classes
class PackException(Exception):
    pass


class UnpackException(Exception):
    pass


# Packing error
class UnsupportedTypeException(PackException):
    pass


# Unpacking error
class InsufficientDataException(UnpackException):
    pass


class InvalidStringException(UnpackException):
    pass


class ReservedCodeException(UnpackException):
    pass


class UnhashableKeyException(UnpackException):
    pass


class DuplicateKeyException(UnpackException):
    pass


# Lazy loader

_attrs = {
    "load": "mp_load",
    "loads": "mp_load",
    "dump": "mp_dump",
    "dumps": "mp_dump",
    "ALoader": "as_loader",
}

# Copied from asyncio.__init__.py
# Lazy loader, effectively does:
#   global attr
#   from .mod import attr
def __getattr__(attr):
    mod = _attrs.get(attr, None)
    if mod is None:
        raise AttributeError(attr)
    value = getattr(__import__(mod, globals(), None, True, 1), attr)
    globals()[attr] = value
    return value
