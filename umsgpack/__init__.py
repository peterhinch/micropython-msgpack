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

__version__ = (0, 1, 3)

# ABC for classes which handle extended Python built-in classes.
class Packer:
    def __init__(self, s: object, options: dict):
        self.s = s
        self.options = options

    def __call__(self, obj):
        self.s = obj
        return self


##############################################################################
# Ext Serializable Decorator
##############################################################################

custom = {}  # Pack. Key: Custom class. Value: ext_type integer.
ext_type_to_class = {}  # Unpack. Key: ext_type integer Value: Packer subclass.
types = {}  # Pack. Key: data type to pack Value: ext_type integer.

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
        elif ext_type in ext_type_to_class:
            raise ValueError(
                "Ext type {:d} already registered with class {:s}".format(
                    ext_type, repr(ext_type_to_class[ext_type])
                )
            )
        elif cls in custom:
            raise ValueError(
                "Class {:s} already registered with Ext type {:d}".format(repr(cls), ext_type)
            )

        ext_type_to_class[ext_type] = cls  # For unpack
        if example is None:  # Custom class
            custom[cls] = ext_type
        else:  # Extension type having a Packer class
            types[example] = (cls, ext_type)
        return cls

    return wrapper


##############################################################################
# Exceptions
##############################################################################

# Base Exception classes
class PackException(Exception):
    "Base class for exceptions encountered during packing."


class UnpackException(Exception):
    "Base class for exceptions encountered during unpacking."


# Packing error
class UnsupportedTypeException(PackException):
    "Object type not supported for packing."


# Unpacking error
class InsufficientDataException(UnpackException):
    "Insufficient data to unpack the serialized object."


class InvalidStringException(UnpackException):
    "Invalid UTF-8 string encountered during unpacking."


class ReservedCodeException(UnpackException):
    "Reserved code encountered during unpacking."


class UnhashableKeyException(UnpackException):
    """
    Unhashable key encountered during map unpacking.
    The serialized map cannot be deserialized into a Python dictionary.
    """


class DuplicateKeyException(UnpackException):
    "Duplicate key encountered during map unpacking."


##############################################################################
# Lazy module load to save RAM: takes about 20μs on Pyboard 1.x after initial load
##############################################################################


def load(fp, **options):
    from . import mp_load

    return mp_load.mpload(fp, options)


def loads(s, **options):
    from . import mp_load

    return mp_load.mploads(s, options)


def dump(obj, fp, **options):
    from . import mp_dump

    mp_dump.mpdump(obj, fp, options)


def dumps(obj, **options):
    from . import mp_dump

    return mp_dump.mpdumps(obj, options)


def aloader(fp, **options):
    from . import as_loader

    return as_loader.asloader(fp, options)
