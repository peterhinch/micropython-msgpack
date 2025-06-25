# mpk_complex.py Extend MessagePack to support complex numbers.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.
# force_float_precision: on 32-bit platforms forcing double precision produces
# the correct output on dump. Load does not, because the complex object has native
# precision.

import umsgpack
import struct
from . import float_precision


@umsgpack.ext_serializable(0x50, complex)
class Complex:
    @staticmethod
    def packb(obj, options):
        dp = options.get("force_float_precision", float_precision) == "double"
        fs = ">bdd" if dp else ">bff"
        return struct.pack(fs, dp, obj.real, obj.imag)

    @staticmethod
    def unpackb(data, options):
        dp = struct.unpack("b", data)[0]
        fs = ">dd" if dp else ">ff"
        return complex(*struct.unpack_from(fs, data, 1))
