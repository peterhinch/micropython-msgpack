# mpk_bytearray.py Extend MessagePack to support bytearray objects.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct
from . import Packer


@umsgpack.ext_serializable(0x53, bytearray)
class ByteArray(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)

    def packb(self):
        return umsgpack.dumps(bytes(self.s))

    @staticmethod
    def unpackb(data, options):
        return bytearray(umsgpack.loads(data))
