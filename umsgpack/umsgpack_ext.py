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


class Packer:
    def __init__(self, s, options):
        self.s = s
        self.options = options

    def __call__(self, obj):
        self.s = obj
        return self


@umsgpack.ext_serializable(0x50, complex)
class Complex(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)

    def __str__(self):
        return f"Complex({self.s})"

    def packb(self):
        return struct.pack(">ff", self.s.real, self.s.imag)

    @staticmethod
    def unpackb(data):
        return complex(*struct.unpack(">ff", data))


@umsgpack.ext_serializable(0x51, set)
class Set(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)

    def __str__(self):
        return f"Set({self.s})"

    def packb(self):  # Must change to list otherwise get infinite recursion
        return umsgpack.dumps(list(self.s))

    @staticmethod
    def unpackb(data):
        return set(umsgpack.loads(data))


@umsgpack.ext_serializable(0x52, tuple)
class Tuple(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)

    def __str__(self):
        return f"Tuple({self.s})"

    def packb(self):
        return umsgpack.dumps(list(self.s))  # Infinite recursion

    @staticmethod
    def unpackb(data):
        return tuple(umsgpack.loads(data))


@umsgpack.ext_serializable(0x53, bytearray)
class ByteArray(Packer):
    def __init__(self, s):
        super().__init__(s, options)

    def __str__(self):
        return f"ByteArray({self.s})"

    def packb(self):
        return umsgpack.dumps(bytes(self.s))

    @staticmethod
    def unpackb(data):
        return bytearray(umsgpack.loads(data))
