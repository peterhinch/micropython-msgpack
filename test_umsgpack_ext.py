# -*- coding: utf-8 -*-
# Run test_umsgpack.py with Python3 to test the correctness of umsgpack_ext.py:
#
#   $ python3 test_umsgpack_ext.py
#   $ micropython test_umsgpack_ext.py

import unittest

import umsgpack

def roundtrip (obj):
    return umsgpack.loads(umsgpack.dumps(obj))


class TestUmsgpackExt(unittest.TestCase):

    def test_complex(self):
        obj = complex(1, 2)
        ext = umsgpack_ext.Complex(obj)
        self.assertEqual(str(ext), "Complex((1+2j))")
        self.assertEqual(obj, roundtrip(obj))

    def test_set(self):
        obj = set([1, 2, 3])
        ext = umsgpack_ext.Set(obj)
        self.assertEqual(str(ext), "Set({1, 2, 3})")
        self.assertEqual(obj, roundtrip(obj))

    def test_tuple(self):
        obj = tuple([1, 2, 3])
        ext = umsgpack_ext.Tuple(obj)
        self.assertEqual(str(ext), "Tuple((1, 2, 3))")
        self.assertEqual(obj, roundtrip(obj))


if __name__ == '__main__':
    unittest.main()
