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

try:
    from machine import Pin
except ImportError:
    pass

# Inject Pin's id type for easier configuration.
#
# Class Pin's first argument `id` is specific to the Micropython port. Set the
# correct value with `umsgpack.PIN_TYPE = x`, here or somewhere else where this
# module is used.
#
# Valid values:
# * `0` no Pin handling
# * `1` integer, i.e., `Pin(0)`
# * `2` string, i.e., `Pin('LED1')`
# * `3` tuple, i.e., `Pin(('GPIO_1', 1))`
umsgpack.PIN_TYPE = 0

# Entries in mpext are required where types are to be handled without declaring
# an ext_serializable class in the application. This example enables complex,
# tuple, set and Pin types to be packed as if they were native to umsgpack.
# Options (kwargs to dump and dumps) may be passed to constructor including new
# type-specific options
def mpext(obj, options):
    if isinstance(obj, complex):
        return Complex(obj)
    if isinstance(obj, set):
        return Set(obj)
    if isinstance(obj, tuple):
        return Tuple(obj)
    if umsgpack.PIN_TYPE and isinstance(obj, Pin):
        if umsgpack.PIN_TYPE == 1:
            return PinInt(obj)
        elif umsgpack.PIN_TYPE == 2:
            return PinStr(obj)
        elif umsgpack.PIN_TYPE == 3:
            return PinTuple(obj)
        else:
            raise umsgpack.UnsupportedTypeException
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

@umsgpack.ext_serializable(0x53)
class PinInt:
    def __init__(self, p):
        self.pin = p.pin()

    def __str__(self):
        return "Pin({})".format(self.pin)

    def packb(self):
        return self.pin.to_bytes(1, "big")

    @staticmethod
    def unpackb(data):
        return Pin(int.from_bytes(data, "big"))

@umsgpack.ext_serializable(0x54)
class PinStr:
    def __init__(self, p):
        self.name = p.name()

    def __str__(self):
        return "Pin('{}')".format(self.name)

    def packb(self):
        return self.name.encode()

    @staticmethod
    def unpackb(data):
        return Pin(data.decode())

@umsgpack.ext_serializable(0x55)
class PinTuple:
    def __init__(self, p):
        self.port = p.port()
        self.pin = p.pin()

    def __str__(self):
        return "Pin(('{}', {}))".format(self.port, self.pin)

    def packb(self):
        lp = len(self.port)
        return struct.pack("B{}s".format(lp), self.pin, self.port.encode())

    @staticmethod
    def unpackb(data):
        lp = len(data) - 1
        pin, port = struct.unpack("B{}s".format(lp), data)
        return Pin((port.decode(), pin))
