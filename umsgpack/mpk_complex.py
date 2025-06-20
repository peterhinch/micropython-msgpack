# mpk_complex.py Extend MessagePack to support complex numbers.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct
from . import Packer


@umsgpack.ext_serializable(0x50, complex)
class Complex(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)

    def packb(self):
        return struct.pack(">ff", self.s.real, self.s.imag)

    @staticmethod
    def unpackb(data, options):
        return complex(*struct.unpack(">ff", data))
