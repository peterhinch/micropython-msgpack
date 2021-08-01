# user_class.py Instances of Point3d may be serialised with umsgpack as if
# they were natively supported.

# Copyright (c) 2021 Peter Hinch Released under the MIT License see LICENSE.

import umsgpack
import struct

@umsgpack.ext_serializable(0x10)
class Point3d:
    def __init__(self, x, y, z):
        self.v = (float(x), float(y), float(z))

    def __str__(self):
        return "Point3d({} {} {})".format(*self.v)

    def packb(self):
        return struct.pack("fff", *self.v)

    @staticmethod
    def unpackb(data):
        return Point3d(*struct.unpack("fff", data))
