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
# Provide uasyncio StreamReader support.
# Exported functions now match ujson: dump, dumps, load, loads (only).
# Many functions refactored to save bytes, especially replace function
# dispatch table with code.
# Further refactoring to reduce allocations.
# InvalidString class removed because it is a subclass of a native type.
# Method of detecting platform's float size changed.
# Version reset to (0.1.0).

__version__ = (0, 1, 1)


##############################################################################
# Ext Class
##############################################################################

# Extension type for application-defined types and data
class Ext:
    """
    The Ext class facilitates creating a serializable extension object to store
    an application-defined type and data byte array.
    """

    def __init__(self, type, data):
        """
        Construct a new Ext object.

        Args:
            type: application-defined type integer
            data: application-defined data byte array

        TypeError:
            Type is not an integer.
        ValueError:
            Type is out of range of -128 to 127.
        TypeError:
            Data is not type 'bytes'.

        Example:
        >>> foo = umsgpack.Ext(0x05, b"\x01\x02\x03")
        >>> umsgpack.dumps({u"special stuff": foo, u"awesome": True})
        '\x82\xa7awesome\xc3\xadspecial stuff\xc7\x03\x05\x01\x02\x03'
        >>> bar = umsgpack.loads(_)
        >>> print(bar["special stuff"])
        Ext Object (Type: 0x05, Data: 01 02 03)
        >>>
        """
        # Check type is type int
        if not isinstance(type, int):
            raise TypeError("ext type is not type integer")
        if not (-128 <= type <= 127):
            raise ValueError("ext type value {:d} is out of range (-128 to 127)".format(type))
        # Check data is type bytes
        elif not isinstance(data, bytes):
            raise TypeError("ext data is not type \'bytes\'")
        self.type = type
        self.data = data

    def __eq__(self, other):
        """
        Compare this Ext object with another for equality.
        """
        return (isinstance(other, self.__class__) and
                self.type == other.type and
                self.data == other.data)

    def __ne__(self, other):
        """
        Compare this Ext object with another for inequality.
        """
        return not self.__eq__(other)

    def __str__(self):
        """
        String representation of this Ext object.
        """
        s = "Ext Object (Type: {:d}, Data: ".format(self.type)
        s += " ".join(["0x{:02}".format(ord(self.data[i:i + 1]))
                       for i in xrange(min(len(self.data), 8))])
        if len(self.data) > 8:
            s += " ..."
        s += ")"
        return s

    def __hash__(self):
        """
        Provide a hash of this Ext object.
        """
        return hash((self.type, self.data))


##############################################################################
# Ext Serializable Decorator
##############################################################################

ext_class_to_type = {}
ext_type_to_class = {}


def ext_serializable(ext_type):
    """
    Return a decorator to register a class for automatic packing and unpacking
    with the specified Ext type code. The application class should implement a
    `packb()` method that returns serialized bytes, and an `unpackb()` class
    method or static method that accepts serialized bytes and returns an
    instance of the application class.
    Args:
        ext_type: application-defined Ext type code
    Raises:
        TypeError:
            Ext type is not an integer.
        ValueError:
            Ext type is out of range of -128 to 127.
        ValueError:
            Ext type or class already registered.
    """
    def wrapper(cls):
        if not isinstance(ext_type, int):
            raise TypeError("Ext type is not type integer")
        elif not (-128 <= ext_type <= 127):
            raise ValueError("Ext type value {:d} is out of range of -128 to 127".format(ext_type))
        elif ext_type in ext_type_to_class:
            raise ValueError("Ext type {:d} already registered with class {:s}".format(ext_type, repr(ext_type_to_class[ext_type])))
        elif cls in ext_class_to_type:
            raise ValueError("Class {:s} already registered with Ext type {:d}".format(repr(cls), ext_type))

        ext_type_to_class[ext_type] = cls
        ext_class_to_type[cls] = ext_type

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

# Lazy module load to save RAM: takes about 20μs on Pyboard 1.x after initial load

def load(fp, **options):
    """
    Deserialize MessagePack bytes into a Python object.

    Args:
        fp: a .read()-supporting file-like object

    Kwargs:
        ext_handlers (dict): dictionary of Ext handlers, mapping integer Ext
                             type to a callable that unpacks an instance of
                             Ext into an object
        use_ordered_dict (bool): unpack maps into OrderedDict, instead of
                                 unordered dict (default False)
        use_tuple (bool): unpacks arrays into tuples, instead of lists
                                 (default False)
        allow_invalid_utf8 (bool): unpack invalid strings into bytes
                                 (default False)

    Returns:
        A Python object.

    Raises:
        InsufficientDataException(UnpackException):
            Insufficient data to unpack the serialized object.
        InvalidStringException(UnpackException):
            Invalid UTF-8 string encountered during unpacking.
        ReservedCodeException(UnpackException):
            Reserved code encountered during unpacking.
        UnhashableKeyException(UnpackException):
            Unhashable key encountered during map unpacking.
            The serialized map cannot be deserialized into a Python dictionary.
        DuplicateKeyException(UnpackException):
            Duplicate key encountered during map unpacking.

    Example:
    >>> f = open('test.bin', 'rb')
    >>> umsgpack.loads(f)
    {'compact': True, 'schema': 0}
    >>>
    """
    from . import mp_load
    return mp_load.load(fp, options)

def loads(s, **options):
    """
    Deserialize MessagePack bytes into a Python object.

    Args:
        s: a 'bytes' or 'bytearray' containing serialized MessagePack bytes

    Kwargs:
        ext_handlers (dict): dictionary of Ext handlers, mapping integer Ext
                             type to a callable that unpacks an instance of
                             Ext into an object
        use_ordered_dict (bool): unpack maps into OrderedDict, instead of
                                 unordered dict (default False)
        use_tuple (bool): unpacks arrays into tuples, instead of lists
                                 (default False)
        allow_invalid_utf8 (bool): unpack invalid strings into bytes
                                 (default False)

    Returns:
        A Python object.

    Raises:
        TypeError:
            Packed data type is neither 'bytes' nor 'bytearray'.
        InsufficientDataException(UnpackException):
            Insufficient data to unpack the serialized object.
        InvalidStringException(UnpackException):
            Invalid UTF-8 string encountered during unpacking.
        ReservedCodeException(UnpackException):
            Reserved code encountered during unpacking.
        UnhashableKeyException(UnpackException):
            Unhashable key encountered during map unpacking.
            The serialized map cannot be deserialized into a Python dictionary.
        DuplicateKeyException(UnpackException):
            Duplicate key encountered during map unpacking.

    Example:
    >>> umsgpack.loads(b'\x82\xa7compact\xc3\xa6schema\x00')
    {'compact': True, 'schema': 0}
    >>>
    """
    from . import mp_load
    return mp_load.loads(s, options)

def dump(obj, fp, **options):
    """
    Serialize a Python object into MessagePack bytes.

    Args:
        obj: a Python object
        fp: a .write()-supporting file-like object

    Kwargs:
        ext_handlers (dict): dictionary of Ext handlers, mapping a custom type
                             to a callable that packs an instance of the type
                             into an Ext object
        force_float_precision (str): "single" to force packing floats as
                                     IEEE-754 single-precision floats,
                                     "double" to force packing floats as
                                     IEEE-754 double-precision floats.

    Returns:
        None.

    Raises:
        UnsupportedType(PackException):
            Object type not supported for packing.

    Example:
    >>> f = open('test.bin', 'wb')
    >>> umsgpack.dump({u"compact": True, u"schema": 0}, f)
    >>>
    """
    from . import mp_dump
    mp_dump.dump(obj, fp, options)

def dumps(obj, **options):
    """
    Serialize a Python object into MessagePack bytes.

    Args:
        obj: a Python object

    Kwargs:
        ext_handlers (dict): dictionary of Ext handlers, mapping a custom type
                             to a callable that packs an instance of the type
                             into an Ext object
        force_float_precision (str): "single" to force packing floats as
                                     IEEE-754 single-precision floats,
                                     "double" to force packing floats as
                                     IEEE-754 double-precision floats.

    Returns:
        A 'bytes' containing serialized MessagePack bytes.

    Raises:
        UnsupportedType(PackException):
            Object type not supported for packing.

    Example:
    >>> umsgpack.dumps({u"compact": True, u"schema": 0})
    b'\x82\xa7compact\xc3\xa6schema\x00'
    >>>
    """
    from . import mp_dump
    return mp_dump.dumps(obj, options)

async def aload(fp, **options):
    """
    Deserialize MessagePack bytes from a StreamReader into a Python object.

    Args:
        fp: a uasyncio StreamReader object

    Kwargs:
        ext_handlers (dict): dictionary of Ext handlers, mapping integer Ext
                             type to a callable that unpacks an instance of
                             Ext into an object
        use_ordered_dict (bool): unpack maps into OrderedDict, instead of
                                 unordered dict (default False)
        use_tuple (bool): unpacks arrays into tuples, instead of lists
                                 (default False)
        allow_invalid_utf8 (bool): unpack invalid strings into bytes
                                 (default False)

    Returns:
        A Python object.

    Raises:
        InsufficientDataException(UnpackException):
            Insufficient data to unpack the serialized object.
        InvalidStringException(UnpackException):
            Invalid UTF-8 string encountered during unpacking.
        ReservedCodeException(UnpackException):
            Reserved code encountered during unpacking.
        UnhashableKeyException(UnpackException):
            Unhashable key encountered during map unpacking.
            The serialized map cannot be deserialized into a Python dictionary.
        DuplicateKeyException(UnpackException):
            Duplicate key encountered during map unpacking.

    Example:
    >>> f = open('test.bin', 'rb')
    >>> umsgpack.loads(f)
    {'compact': True, 'schema': 0}
    >>>
    """
    from . import as_load
    return await as_load.aload(fp, options)
