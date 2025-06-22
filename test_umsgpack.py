# -*- coding: utf-8 -*-
# Adapted for MicroPython version of umsgpack.
# Test suite requires python3 because of its use of large structures unsupported
# even on Unix build.
# Run test_umsgpack.py with Python3 to test the correctness of u-msgpack-python!
#
#   $ python3 test_umsgpack.py
#
# Remove tests for unsupported code:
# Compatibility mode.
# Aliases .pack, .packb, .unpack, .unpackb
# InvalidString class: MP version returns a string
# Timestamp support.

import sys
import struct
import unittest
import io
from collections import OrderedDict, namedtuple

import umsgpack

single_test_vectors = [
    # None
    ["nil", None, b"\xc0"],
    # Booleans
    ["bool false", False, b"\xc2"],
    ["bool true", True, b"\xc3"],
    # + 7-bit uint
    ["7-bit uint", 0x00, b"\x00"],
    ["7-bit uint", 0x10, b"\x10"],
    ["7-bit uint", 0x7F, b"\x7f"],
    # - 5-bit int
    ["5-bit sint", -1, b"\xff"],
    ["5-bit sint", -16, b"\xf0"],
    ["5-bit sint", -32, b"\xe0"],
    # 8-bit uint
    ["8-bit uint", 0x80, b"\xcc\x80"],
    ["8-bit uint", 0xF0, b"\xcc\xf0"],
    ["8-bit uint", 0xFF, b"\xcc\xff"],
    # 16-bit uint
    ["16-bit uint", 0x100, b"\xcd\x01\x00"],
    ["16-bit uint", 0x2000, b"\xcd\x20\x00"],
    ["16-bit uint", 0xFFFF, b"\xcd\xff\xff"],
    # 32-bit uint
    ["32-bit uint", 0x10000, b"\xce\x00\x01\x00\x00"],
    ["32-bit uint", 0x200000, b"\xce\x00\x20\x00\x00"],
    ["32-bit uint", 0xFFFFFFFF, b"\xce\xff\xff\xff\xff"],
    # 64-bit uint
    ["64-bit uint", 0x100000000, b"\xcf\x00\x00\x00\x01\x00\x00\x00\x00"],
    ["64-bit uint", 0x200000000000, b"\xcf\x00\x00\x20\x00\x00\x00\x00\x00"],
    ["64-bit uint", 0xFFFFFFFFFFFFFFFF, b"\xcf\xff\xff\xff\xff\xff\xff\xff\xff"],
    # 8-bit int
    ["8-bit int", -33, b"\xd0\xdf"],
    ["8-bit int", -100, b"\xd0\x9c"],
    ["8-bit int", -128, b"\xd0\x80"],
    # 16-bit int
    ["16-bit int", -129, b"\xd1\xff\x7f"],
    ["16-bit int", -2000, b"\xd1\xf8\x30"],
    ["16-bit int", -32768, b"\xd1\x80\x00"],
    # 32-bit int
    ["32-bit int", -32769, b"\xd2\xff\xff\x7f\xff"],
    ["32-bit int", -1000000000, b"\xd2\xc4\x65\x36\x00"],
    ["32-bit int", -2147483648, b"\xd2\x80\x00\x00\x00"],
    # 64-bit int
    ["64-bit int", -2147483649, b"\xd3\xff\xff\xff\xff\x7f\xff\xff\xff"],
    ["64-bit int", -1000000000000000002, b"\xd3\xf2\x1f\x49\x4c\x58\x9b\xff\xfe"],
    ["64-bit int", -9223372036854775808, b"\xd3\x80\x00\x00\x00\x00\x00\x00\x00"],
    # 64-bit float
    ["64-bit float", 0.0, b"\xcb\x00\x00\x00\x00\x00\x00\x00\x00"],
    ["64-bit float", 2.5, b"\xcb\x40\x04\x00\x00\x00\x00\x00\x00"],
    ["64-bit float", float(10 ** 35), b"\xcb\x47\x33\x42\x61\x72\xc7\x4d\x82"],
    # Fixstr String
    ["fix string", "", b"\xa0"],
    ["fix string", "a", b"\xa1\x61"],
    ["fix string", "abc", b"\xa3\x61\x62\x63"],
    ["fix string", "a" * 31, b"\xbf" + b"\x61" * 31],
    # 8-bit String
    ["8-bit string", "b" * 32, b"\xd9\x20" + b"b" * 32],
    ["8-bit string", "c" * 100, b"\xd9\x64" + b"c" * 100],
    ["8-bit string", "d" * 255, b"\xd9\xff" + b"d" * 255],
    # 16-bit String
    ["16-bit string", "b" * 256, b"\xda\x01\x00" + b"b" * 256],
    ["16-bit string", "c" * 65535, b"\xda\xff\xff" + b"c" * 65535],
    # 32-bit String
    ["32-bit string", "b" * 65536, b"\xdb\x00\x01\x00\x00" + b"b" * 65536],
    # Wide character String
    ["wide char string", "Allagbé", b"\xa8Allagb\xc3\xa9"],
    [
        "wide char string",
        "По оживлённым берегам",
        b"\xd9\x28\xd0\x9f\xd0\xbe\x20\xd0\xbe\xd0\xb6\xd0\xb8\xd0\xb2\xd0\xbb\xd1\x91\xd0\xbd\xd0\xbd\xd1\x8b\xd0\xbc\x20\xd0\xb1\xd0\xb5\xd1\x80\xd0\xb5\xd0\xb3\xd0\xb0\xd0\xbc",
    ],
    # 8-bit Binary
    ["8-bit binary", b"\x80" * 1, b"\xc4\x01" + b"\x80" * 1],
    ["8-bit binary", b"\x80" * 32, b"\xc4\x20" + b"\x80" * 32],
    ["8-bit binary", b"\x80" * 255, b"\xc4\xff" + b"\x80" * 255],
    # 16-bit Binary
    ["16-bit binary", b"\x80" * 256, b"\xc5\x01\x00" + b"\x80" * 256],
    # 32-bit Binary
    ["32-bit binary", b"\x80" * 65536, b"\xc6\x00\x01\x00\x00" + b"\x80" * 65536],
    # Empty Array
    ["empty array", [], b"\x90"],
    # Empty Map
    ["empty map", {}, b"\x80"],
]

composite_test_vectors = [
    # Fix Array
    ["fix array", [5, "abc", True], b"\x93\x05\xa3\x61\x62\x63\xc3"],
    # 16-bit Array
    ["16-bit array", [0x05] * 16, b"\xdc\x00\x10" + b"\x05" * 16],
    ["16-bit array", [0x05] * 65535, b"\xdc\xff\xff" + b"\x05" * 65535],
    # 32-bit Array
    ["32-bit array", [0x05] * 65536, b"\xdd\x00\x01\x00\x00" + b"\x05" * 65536],
    # Fix Map
    [
        "fix map",
        OrderedDict([(1, True), (2, "abc"), (3, b"\x80")]),
        b"\x83\x01\xc3\x02\xa3\x61\x62\x63\x03\xc4\x01\x80",
    ],
    ["fix map", {"abc": 5}, b"\x81\xa3\x61\x62\x63\x05"],
    ["fix map", {b"\x80": 0xFFFF}, b"\x81\xc4\x01\x80\xcd\xff\xff"],
    ["fix map", {True: None}, b"\x81\xc3\xc0"],
    # 16-bit Map
    [
        "16-bit map",
        OrderedDict([(k, 0x05) for k in range(16)]),
        b"\xde\x00\x10" + b"".join([struct.pack("B", i) + b"\x05" for i in range(16)]),
    ],
    [
        "16-bit map",
        OrderedDict([(k, 0x05) for k in range(6000)]),
        b"\xde\x17\x70"
        + b"".join([struct.pack("B", i) + b"\x05" for i in range(128)])
        + b"".join([b"\xcc" + struct.pack("B", i) + b"\x05" for i in range(128, 256)])
        + b"".join([b"\xcd" + struct.pack(">H", i) + b"\x05" for i in range(256, 6000)]),
    ],
    # Complex Map
    [
        "complex map",
        OrderedDict(
            [
                (1, [OrderedDict([(1, 2), (3, 4)]), {}]),
                (2, 1),
                (3, [False, "def"]),
                (4, OrderedDict([(0x100000000, "a"), (0xFFFFFFFF, "b")])),
            ]
        ),
        b"\x84\x01\x92\x82\x01\x02\x03\x04\x80\x02\x01\x03\x92\xc2\xa3\x64\x65\x66\x04\x82\xcf\x00\x00\x00\x01\x00\x00\x00\x00\xa1\x61\xce\xff\xff\xff\xff\xa1\x62",
    ],
    # Map with Tuple Keys
    [
        "map with tuple keys",
        OrderedDict([(("foo", False, 3), True), ((3e6, -5), "def")]),
        b"\x82\x93\xa3\x66\x6f\x6f\xc2\x03\xc3\x92\xcb\x41\x46\xe3\x60\x00\x00\x00\x00\xfb\xa3\x64\x65\x66",
    ],
    # Map with Complex Tuple Keys
    [
        "map with complex tuple keys",
        {("foo", (1, 2, 3), 3): -5},
        b"\x81\x93\xa3\x66\x6f\x6f\x93\x01\x02\x03\x03\xfb",
    ],
]

pack_exception_test_vectors = [
    # Unsupported type exception.
    ["unsupported type", -(2 ** (64 - 1)) - 1, umsgpack.UnsupportedTypeException],
    ["unsupported type", 2 ** 64, umsgpack.UnsupportedTypeException],
]

unpack_exception_test_vectors = [
    # Type errors
    ["type error unpack unicode string", "\x01", TypeError],
    ["type error unpack boolean", True, TypeError],
    # Insufficient data to unpack object
    ["insufficient data 8-bit uint", b"\xcc", umsgpack.InsufficientDataException],
    ["insufficient data 16-bit uint", b"\xcd\xff", umsgpack.InsufficientDataException],
    ["insufficient data 32-bit uint", b"\xce\xff", umsgpack.InsufficientDataException],
    ["insufficient data 64-bit uint", b"\xcf\xff", umsgpack.InsufficientDataException],
    ["insufficient data 8-bit int", b"\xd0", umsgpack.InsufficientDataException],
    ["insufficient data 16-bit int", b"\xd1\xff", umsgpack.InsufficientDataException],
    ["insufficient data 32-bit int", b"\xd2\xff", umsgpack.InsufficientDataException],
    ["insufficient data 64-bit int", b"\xd3\xff", umsgpack.InsufficientDataException],
    ["insufficient data 32-bit float", b"\xca\xff", umsgpack.InsufficientDataException],
    ["insufficient data 64-bit float", b"\xcb\xff", umsgpack.InsufficientDataException],
    ["insufficient data fixstr", b"\xa1", umsgpack.InsufficientDataException],
    ["insufficient data 8-bit string", b"\xd9", umsgpack.InsufficientDataException],
    ["insufficient data 8-bit string", b"\xd9\x01", umsgpack.InsufficientDataException],
    ["insufficient data 16-bit string", b"\xda\x01\x00", umsgpack.InsufficientDataException],
    [
        "insufficient data 32-bit string",
        b"\xdb\x00\x01\x00\x00",
        umsgpack.InsufficientDataException,
    ],
    ["insufficient data 8-bit binary", b"\xc4", umsgpack.InsufficientDataException],
    ["insufficient data 8-bit binary", b"\xc4\x01", umsgpack.InsufficientDataException],
    ["insufficient data 16-bit binary", b"\xc5\x01\x00", umsgpack.InsufficientDataException],
    [
        "insufficient data 32-bit binary",
        b"\xc6\x00\x01\x00\x00",
        umsgpack.InsufficientDataException,
    ],
    ["insufficient data fixarray", b"\x91", umsgpack.InsufficientDataException],
    ["insufficient data fixarray", b"\x92\xc2", umsgpack.InsufficientDataException],
    [
        "insufficient data 16-bit array",
        b"\xdc\x00\xf0\xc2\xc3",
        umsgpack.InsufficientDataException,
    ],
    [
        "insufficient data 32-bit array",
        b"\xdd\x00\x01\x00\x00\xc2\xc3",
        umsgpack.InsufficientDataException,
    ],
    ["insufficient data fixmap", b"\x81", umsgpack.InsufficientDataException],
    ["insufficient data fixmap", b"\x82\xc2\xc3", umsgpack.InsufficientDataException],
    ["insufficient data 16-bit map", b"\xde\x00\xf0\xc2\xc3", umsgpack.InsufficientDataException],
    [
        "insufficient data 32-bit map",
        b"\xdf\x00\x01\x00\x00\xc2\xc3",
        umsgpack.InsufficientDataException,
    ],
    ["insufficient data fixext 1", b"\xd4", umsgpack.InsufficientDataException],
    ["insufficient data fixext 1", b"\xd4\x05", umsgpack.InsufficientDataException],
    ["insufficient data fixext 2", b"\xd5\x05\x01", umsgpack.InsufficientDataException],
    ["insufficient data fixext 4", b"\xd6\x05\x01\x02\x03", umsgpack.InsufficientDataException],
    ["insufficient data fixext 8", b"\xd7\x05\x01\x02\x03", umsgpack.InsufficientDataException],
    ["insufficient data fixext 16", b"\xd8\x05\x01\x02\x03", umsgpack.InsufficientDataException],
    [
        "insufficient data ext 8-bit",
        b"\xc7\x05\x05\x01\x02\x03",
        umsgpack.InsufficientDataException,
    ],
    [
        "insufficient data ext 16-bit",
        b"\xc8\x01\x00\x05\x01\x02\x03",
        umsgpack.InsufficientDataException,
    ],
    [
        "insufficient data ext 32-bit",
        b"\xc9\x00\x01\x00\x00\x05\x01\x02\x03",
        umsgpack.InsufficientDataException,
    ],
    # Unhashable key { 1 : True, { 1 : 1 } : False }
    ["unhashable key", b"\x82\x01\xc3\x81\x01\x01\xc2", umsgpack.UnhashableKeyException],
    # Unhashable key { [ 1, 2, {} ] : True }
    ["unhashable key", b"\x81\x93\x01\x02\x80\xc3", umsgpack.UnhashableKeyException],
    # Key duplicate { 1 : True, 1 : False }
    ["duplicate key", b"\x82\x01\xc3\x01\xc2", umsgpack.DuplicateKeyException],
    # Reserved code (0xc1)
    ["reserved code", b"\xc1", umsgpack.ReservedCodeException],
    # Invalid string (non utf-8)
    ["invalid string", b"\xa1\x80", umsgpack.InvalidStringException],
]

compatibility_test_vectors = [
    # Fix Raw
    ["fix raw", b"", b"\xa0"],
    ["fix raw", "", b"\xa0"],
    ["fix raw", b"a", b"\xa1\x61"],
    ["fix raw", "a", b"\xa1\x61"],
    ["fix raw", b"abc", b"\xa3\x61\x62\x63"],
    ["fix raw", "abc", b"\xa3\x61\x62\x63"],
    ["fix raw", b"a" * 31, b"\xbf" + b"\x61" * 31],
    ["fix raw", "a" * 31, b"\xbf" + b"\x61" * 31],
    # 16-bit Raw
    ["16-bit raw", "b" * 32, b"\xda\x00\x20" + b"b" * 32],
    ["16-bit raw", b"b" * 32, b"\xda\x00\x20" + b"b" * 32],
    ["16-bit raw", "b" * 256, b"\xda\x01\x00" + b"b" * 256],
    ["16-bit raw", b"b" * 256, b"\xda\x01\x00" + b"b" * 256],
    ["16-bit raw", "c" * 65535, b"\xda\xff\xff" + b"c" * 65535],
    ["16-bit raw", b"c" * 65535, b"\xda\xff\xff" + b"c" * 65535],
    # 32-bit Raw
    ["32-bit raw", "b" * 65536, b"\xdb\x00\x01\x00\x00" + b"b" * 65536],
    ["32-bit raw", b"b" * 65536, b"\xdb\x00\x01\x00\x00" + b"b" * 65536],
]

float_precision_test_vectors = [
    ["float precision single", 2.5, b"\xca\x40\x20\x00\x00"],
    ["float precision double", 2.5, b"\xcb\x40\x04\x00\x00\x00\x00\x00\x00"],
]

tuple_test_vectors = [
    [
        "nested array",
        [0x01, [b"\x80", [["a", "b", "c"], True]]],
        b"\x92\x01\x92\xc4\x01\x80\x92\x93\xa1a\xa1b\xa1c\xc3",
        (0x01, (b"\x80", (("a", "b", "c"), True))),
    ],
]

# Dynamic loader prevents this test from working
# These are the only global variables that should be exported by umsgpack
# exported_vars_test_vector = [
#     "dump",
#     "dumps",
#     "load",
#     "loads",
#     "custom",
#     "ext_type_to_class",
#     "types",
#     "ext_serializable",
#     "PackException",
#     "UnpackException",
#     "UnsupportedTypeException",
#     "InsufficientDataException",
#     "InvalidStringException",
#     "ReservedCodeException",
#     "UnhashableKeyException",
#     "DuplicateKeyException",
#     "mp_load",
#     "mp_dump",
#     "ALoader",
#     "as_loader",
# ]

##########################################################################


class TestUmsgpack(unittest.TestCase):
    def test_pack_single(self):
        for (name, obj, data) in single_test_vectors:
            obj_repr = repr(obj)
            print(
                "\tTesting {:s}: object {:s}".format(
                    name, obj_repr if len(obj_repr) < 24 else obj_repr[0:24] + "..."
                )
            )

            self.assertEqual(umsgpack.dumps(obj), data)

    def test_pack_composite(self):
        for (name, obj, data) in composite_test_vectors:
            obj_repr = repr(obj)
            print(
                "\tTesting {:s}: object {:s}".format(
                    name, obj_repr if len(obj_repr) < 24 else obj_repr[0:24] + "..."
                )
            )

            self.assertEqual(umsgpack.dumps(obj), data)

    def test_pack_exceptions(self):
        for (name, obj, exception) in pack_exception_test_vectors:
            obj_repr = repr(obj)
            print(
                "\tTesting {:s}: object {:s}".format(
                    name, obj_repr if len(obj_repr) < 24 else obj_repr[0:24] + "..."
                )
            )

            with self.assertRaises(exception):
                umsgpack.dumps(obj)

    def test_unpack_single(self):
        for (name, obj, data) in single_test_vectors:
            obj_repr = repr(obj)
            print(
                "\tTesting {:s}: object {:s}".format(
                    name, obj_repr if len(obj_repr) < 24 else obj_repr[0:24] + "..."
                )
            )

            unpacked = umsgpack.loads(data)

            # In Python2, we have both int and long integer types, but which
            # one we end up with depends on the architecture (32-bit/64-bit)
            if sys.version_info[0] == 2:
                # Allow both {int,long} -> unpackb -> {int,long}
                if isinstance(obj, int) or isinstance(obj, long):
                    self.assertTrue(isinstance(unpacked, int) or isinstance(unpacked, long))
                else:
                    self.assertTrue(isinstance(unpacked, type(obj)))
            # In Python3, we only have the int integer type
            else:
                self.assertTrue(isinstance(unpacked, type(obj)))

            self.assertEqual(unpacked, obj)

    def test_unpack_composite(self):
        for (name, obj, data) in composite_test_vectors:
            obj_repr = repr(obj)
            print(
                "\tTesting {:s}: object {:s}".format(
                    name, obj_repr if len(obj_repr) < 24 else obj_repr[0:24] + "..."
                )
            )

            self.assertEqual(umsgpack.loads(data), obj)

    def test_unpack_exceptions(self):
        for (name, data, exception) in unpack_exception_test_vectors:
            print("\tTesting {:s}".format(name))

            with self.assertRaises(exception):
                umsgpack.loads(data)

    def test_unpack_ordered_dict(self):
        # Use last composite test vector (a map)
        (_, obj, data) = composite_test_vectors[-1]

        # Unpack with default options (unordered dict)
        unpacked = umsgpack.loads(data)
        self.assertTrue(isinstance(unpacked, dict))

        # Unpack with unordered dict
        unpacked = umsgpack.loads(data, use_ordered_dict=False)
        self.assertTrue(isinstance(unpacked, dict))

        # Unpack with ordered dict
        unpacked = umsgpack.loads(data, use_ordered_dict=True)
        self.assertTrue(isinstance(unpacked, OrderedDict))
        self.assertEqual(unpacked, obj)

    def test_unpack_tuple(self):
        # Use tuple test vector
        (_, obj, data, obj_tuple) = tuple_test_vectors[0]

        # Unpack with default options (list)
        self.assertEqual(umsgpack.loads(data), obj)

        # Unpack with use_tuple=False (list)
        self.assertEqual(umsgpack.loads(data, use_tuple=False), obj)

        # Unpack with use_tuple=True (tuple)
        self.assertEqual(umsgpack.loads(data, use_tuple=True), obj_tuple)

    def test_pack_force_float_precision(self):
        for ((name, obj, data), precision) in zip(
            float_precision_test_vectors, ["single", "double"]
        ):
            obj_repr = repr(obj)
            print(
                "\tTesting {:s}: object {:s}".format(
                    name, obj_repr if len(obj_repr) < 24 else obj_repr[0:24] + "..."
                )
            )

            packed = umsgpack.dumps(obj, force_float_precision=precision)
            self.assertEqual(packed, data)

    def test_ext_serializable(self):

        # Register test class
        @umsgpack.ext_serializable(0x20)
        class CustomComplex:
            def __init__(self, real, imag):
                self.real = real
                self.imag = imag

            def __eq__(self, other):
                return self.real == other.real and self.imag == other.imag

            def packb(self):
                return struct.pack("<II", self.real, self.imag)

            @classmethod
            def unpackb(cls, data, options):
                return cls(*struct.unpack("<II", data))

        obj, data = CustomComplex(123, 456), b"\xd7\x20\x7b\x00\x00\x00\xc8\x01\x00\x00"

        # Test pack
        packed = umsgpack.dumps(obj)
        self.assertEqual(packed, data)

        # Test unpack
        unpacked = umsgpack.loads(packed)
        self.assertTrue(isinstance(unpacked, CustomComplex))
        self.assertEqual(unpacked, obj)

        # Test registration collision
        with self.assertRaises(ValueError):

            @umsgpack.ext_serializable(0x20)
            class DummyClass:
                pass

        # Test out of range Ext type value
        with self.assertRaises(ValueError):

            @umsgpack.ext_serializable(-129)
            class DummyClass2:
                pass

        with self.assertRaises(ValueError):

            @umsgpack.ext_serializable(128)
            class DummyClass3:
                pass

        # Register class with missing packb() and unpackb()
        @umsgpack.ext_serializable(0x21)
        class IncompleteClass:
            pass

        # Test unimplemented packb()
        with self.assertRaises(umsgpack.UnsupportedTypeException):
            umsgpack.dumps(IncompleteClass())

        # Test unimplemented unpackb()
        with self.assertRaises(NotImplementedError):
            umsgpack.loads(b"\xd4\x21\x00")

        # Test extension classes for builtins
        @umsgpack.ext_serializable(0x51, set)
        class Set:
            def packb(self, s, _):  # Must change to list otherwise get infinite recursion
                return umsgpack.dumps(list(s))

            @staticmethod
            def unpackb(data, options):
                return set(umsgpack.loads(data))

        packed = umsgpack.dumps({1, 2, 3})
        data = umsgpack.loads(packed)
        self.assertEqual({1, 2, 3}, data)

        # Unregister Ext serializable classes to prevent interference with
        # subsequent tests
        umsgpack._ext_classes_to_code = {}
        umsgpack._ext_code_to_classes = {}

    def test_ext_serializable_subclass(self):
        @umsgpack.ext_serializable(0x10)
        class Rectangle:
            def __init__(self, length, width):
                self.length = length
                self.width = width

            def __eq__(self, other):
                return self.length == other.length and self.width == other.width

            def packb(self):
                return umsgpack.dumps([self.length, self.width])

            @classmethod
            def unpackb(cls, data, options):
                return cls(*umsgpack.loads(data))

        class Square(Rectangle):
            def __init__(self, width):
                Rectangle.__init__(self, width, width)

        # Test pack (packs base class)
        packed = umsgpack.dumps(Square(5))
        self.assertEqual(packed, b"\xc7\x03\x10\x92\x05\x05")

        # Test unpack (unpacks base class)
        unpacked = umsgpack.loads(packed)
        self.assertEqual(unpacked, Rectangle(5, 5))

        # Unregister Ext serializable classes to prevent interference with
        # subsequent tests
        umsgpack._ext_classes_to_code = {}
        umsgpack._ext_code_to_classes = {}

    def test_streaming_writer(self):
        # Try first composite test vector
        (_, obj, data) = composite_test_vectors[0]
        writer = io.BytesIO()
        umsgpack.dump(obj, writer)
        self.assertTrue(writer.getvalue(), data)

    def test_streaming_reader(self):
        # Try first composite test vector
        (_, obj, data) = composite_test_vectors[0]
        reader = io.BytesIO(data)
        self.assertEqual(umsgpack.load(reader), obj)

    # Dynamic loader prevents this test from working
    # def test_namespacing(self):
    #     # Get a list of global variables from umsgpack module
    #     exported_vars = list([x for x in dir(umsgpack) if not x.startswith("_")])
    #
    #     self.assertEqual(len(exported_vars), len(exported_vars_test_vector))
    #     print("###")
    #     print("Test namespace")
    #     for var in exported_vars_test_vector:
    #         self.assertTrue(var in exported_vars)

    def test_load_short_read(self):
        # When reading from files, the network, etc. there's no guarantee that
        # read(n) returns n bytes. Simulate this with a file-like object that
        # returns 1 byte at a time.

        class SlowFile(object):
            def __init__(self, data):
                self._data = data

            def read(self, n=None):
                if n is None or len(self._data) == 0:
                    data, self._data = self._data, b""
                    return data

                chunk = self._data[0:1]
                self._data = self._data[1:]
                return chunk

        obj = {"hello": "world"}
        f = SlowFile(umsgpack.dumps(obj))
        unpacked = umsgpack.load(f)

        self.assertEqual(unpacked, obj)


if __name__ == "__main__":
    unittest.main()
