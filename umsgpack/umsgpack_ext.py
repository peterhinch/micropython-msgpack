# umsgpack_ext.py Demo of extending MessagePack to support additional Python
# built-in types.

# Copyright (c) 2021 Peter Hinch Released under the MIT License see LICENSE.

# Each supported type has a class defined with the umsgpack.ext_serializable
# decorator and assigned a unique integer in range 0-127. I arbitrarily chose
# a range starting at 0x50.
# The mpext method accepts an instance of a supported class and returns an
# instance of the appropriate ext_serializable class.

import umsgpack
import struct

# Entries in mpext are required where types are to be handled without declaring
# an ext_serializable class in the application. This example enables complex,
# tuple and set types to be packed as if they were native to umsgpack.
# Options (kwargs to dump and dumps) may be passed to constructor including new
# type-specific options
def mpext(obj, options):
    if isinstance(obj, complex):
        return Complex(obj)
    if isinstance(obj, set):
        return Set(obj)
    if isinstance(obj, tuple):
        return Tuple(obj)
    return obj

@umsgpack.ext_serializable(0x50)
class Complex:
    def __init__(self, c):
        self.c = c

    def __str__(self):
        return "Complex({})".format(self.c)

    def packb(self):
        return struct.pack(">ff", self.c.real, self.c.imag)

    @staticmethod
    def unpackb(data):
        return complex(*struct.unpack(">ff", data))

@umsgpack.ext_serializable(0x51)
class Set:
    def __init__(self, s):
        self.s = s

    def __str__(self):
        return "Set({})".format(self.s)

    def packb(self):  # Must change to list otherwise get infinite recursion
        return umsgpack.dumps(list(self.s))

    @staticmethod
    def unpackb(data):
        return set(umsgpack.loads(data))

@umsgpack.ext_serializable(0x52)
class Tuple:
    def __init__(self, s):
        self.s = s

    def __str__(self):
        return "Tuple({})".format(self.s)

    def packb(self):
        return umsgpack.dumps(list(self.s))  # Infinite recursion

    @staticmethod
    def unpackb(data):
        return tuple(umsgpack.loads(data))
