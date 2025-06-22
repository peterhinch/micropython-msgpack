# mpk_tuple.py Extend MessagePack to support tuple objects.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct


@umsgpack.ext_serializable(0x52, tuple)
class Tuple:
    def packb(self, s, options):
        return umsgpack.dumps(list(s))  # Infinite recursion

    @staticmethod
    def unpackb(data, options):
        return tuple(umsgpack.loads(data))
