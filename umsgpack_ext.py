import umsgpack
import struct

def mpext(obj):
    if isinstance(obj, complex):
        return Complex(obj)
    if isinstance(obj, set):
        return Set(obj)
    if isinstance(obj, tuple):
        return Tuple(obj)
    raise umsgpack.UnsupportedTypeException("unsupported type: {:s}".format(str(type(obj))))

@umsgpack.ext_serializable(0x50)
class Complex:
    def __init__(self, c):
        self.c = c

    def __str__(self):
        return "Complex({})".format(self.c)

    def packb(self):
        return struct.pack("ff", self.c.real, self.c.imag)

    @staticmethod
    def unpackb(data):
        return complex(*struct.unpack("ff", data))

@umsgpack.ext_serializable(0x51)
class Set:
    def __init__(self, s):
        self.s = s

    def __str__(self):
        return "Set({})".format(self.s)

    def packb(self):
        return umsgpack.dumps(list(self.s))

    @staticmethod
    def unpackb(data):
        return set(umsgpack.loads(data))

@umsgpack.ext_serializable(0x52)
class Tuple:
    def __init__(self, s):
        self.s = s

    def __str__(self):
        return "Tuple({})".format(self.s)

    def packb(self):
        return umsgpack.dumps(self.s)

    @staticmethod
    def unpackb(data):
        return tuple(umsgpack.loads(data))
