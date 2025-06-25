# mpk_bytearray.py Extend MessagePack to support bytearray objects.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct


@umsgpack.ext_serializable(0x53, bytearray)
class ByteArray:
    @staticmethod
    def packb(s, options):
        # Convert to bytes to avoid infinite recursion
        return umsgpack.dumps(bytes(s))

    @staticmethod
    def unpackb(data, options):
        return bytearray(umsgpack.loads(data))
