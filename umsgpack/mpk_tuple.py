# mpk_tuple.py Extend MessagePack to support tuple objects.

# Copyright (c) 2021-2025 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct
from . import Packer


@umsgpack.ext_serializable(0x52, tuple)
class Tuple(Packer):
    def __init__(self, s, options):
        super().__init__(s, options)

    def packb(self):
        return umsgpack.dumps(list(self.s))  # Infinite recursion

    @staticmethod
    def unpackb(data, options):
        return tuple(umsgpack.loads(data))
