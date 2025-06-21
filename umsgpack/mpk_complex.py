# mpk_complex.py Extend MessagePack to support complex numbers.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.
# force_float_precision: on 32-bit platforms forcing double precision produces
# the correct output on dump. Load does not, because the complex object has native
# precision.

import umsgpack
import struct
from . import Packer, float_precision


@umsgpack.ext_serializable(0x50, complex)
class Complex(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)
        self.dp = options.get("force_float_precision", float_precision) == "double"
        self.fs = ">bdd" if self.dp else ">bff"

    def packb(self):
        return struct.pack(self.fs, self.dp, self.s.real, self.s.imag)

    @staticmethod
    def unpackb(data, options):
        dp = struct.unpack("b", data)[0]
        fs = ">dd" if dp else ">ff"
        return complex(*struct.unpack_from(fs, data, 1))
