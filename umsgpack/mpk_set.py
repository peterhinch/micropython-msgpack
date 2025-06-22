# mpk_set.py Extend MessagePack to support set objects.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct


@umsgpack.ext_serializable(0x51, set)
class Set:
    def packb(self, s, options):  # Must change to list otherwise get infinite recursion
        return umsgpack.dumps(list(s))

    @staticmethod
    def unpackb(data, options):
        return set(umsgpack.loads(data))
