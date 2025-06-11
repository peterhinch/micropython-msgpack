# mpk_set.py Extend MessagePack to support set objects.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct
from . import Packer


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
