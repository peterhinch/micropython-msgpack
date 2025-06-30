# mpk_odict.py Extend MessagePack to support OrderedDict objects.

# Copyright (c) 2025 Peter Hinch Released under the MIT License see LICENSE.
# See https://github.com/micropython/micropython/issues/6170 for work on making
# all dicts ordered.

import umsgpack
import struct
from collections import OrderedDict


@umsgpack.ext_serializable(0x54, OrderedDict)
class Tuple:
    @staticmethod
    def packb(s, options):
        return umsgpack.dumps(dict(s))  # Avoid recursion

    @staticmethod
    def unpackb(data, options):
        return OrderedDict(umsgpack.loads(data))
