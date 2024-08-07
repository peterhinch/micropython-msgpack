# as_loader.py Defines the aloader class, which performs lightweight
#              asynchronous MessagePack deserialization.
#              It's the same deserialization logic as what's in as_load.py, but
#              using an object-oriented implementation.

# Copyright (c) 2024 Peter Hinch
# Refactored as_load contributed by @bapowell

import struct
import collections
from . import *

try:
    from . import umsgpack_ext
except ImportError:
    pass


class aloader:
    """Deserialize MessagePack bytes from a StreamReader into a Python object."""

    def __init__(self, fp, options):
        self.fp = fp
        self.allow_invalid_utf8 = options.get("allow_invalid_utf8")
        self.use_ordered_dict = options.get("use_ordered_dict")
        self.use_tuple = options.get("use_tuple")
        self.ext_handlers = options.get("ext_handlers")
        self.observer = options.get("observer")

    @staticmethod
    def _fail():  # Debug code should never be called.
        raise Exception("Logic error")

    async def _re(self, n):
        d = await self.fp.readexactly(n)
        if self.observer:
            self.observer.update(d)
        return d

    async def _re0(self, s, n):
        d = await self._re(n)
        return struct.unpack(s, d)[0]

    async def _unpack_integer(self, code):
        ic = ord(code)
        if (ic & 0xE0) == 0xE0:
            return struct.unpack("b", code)[0]
        if (ic & 0x80) == 0x00:
            return struct.unpack("B", code)[0]
        ic -= 0xCC
        off = ic << 1
        try:
            s = "B >H>I>Qb >h>i>q"[off : off + 2]
        except IndexError:
            aloader._fail()
        return await self._re0(s.strip(), 1 << (ic & 3))

    async def _unpack_float(self, code):
        ic = ord(code)
        if ic == 0xCA:
            return await self._re0(">f", 4)
        if ic == 0xCB:
            return await self._re0(">d", 8)
        aloader._fail()

    async def _unpack_string(self, code):
        ic = ord(code)
        if (ic & 0xE0) == 0xA0:
            length = ic & ~0xE0
        elif ic == 0xD9:
            length = await self._re0("B", 1)
        elif ic == 0xDA:
            length = await self._re0(">H", 2)
        elif ic == 0xDB:
            length = await self._re0(">I", 4)
        else:
            aloader._fail()

        data = await self._re(length)
        try:
            return str(data, "utf-8")  # Preferred MP way to decode
        except:  # MP does not have UnicodeDecodeError
            if self.allow_invalid_utf8:
                return data  # MP Remove InvalidString class: subclass of built-in class
            raise InvalidStringException("unpacked string is invalid utf-8")

    async def _unpack_binary(self, code):
        ic = ord(code)
        if ic == 0xC4:
            length = await self._re0("B", 1)
        elif ic == 0xC5:
            length = await self._re0(">H", 2)
        elif ic == 0xC6:
            length = await self._re0(">I", 4)
        else:
            aloader._fail()

        return await self._re(length)

    async def _unpack_ext(self, code):
        ic = ord(code)
        n = b"\xd4\xd5\xd6\xd7\xd8".find(code)
        length = 0 if n < 0 else 1 << n
        if not length:
            if ic == 0xC7:
                length = await self._re0("B", 1)
            elif ic == 0xC8:
                length = await self._re0(">H", 2)
            elif ic == 0xC9:
                length = await self._re0(">I", 4)
            else:
                aloader._fail()

        ext_type = await self._re0("b", 1)
        ext_data = await self._re(length)

        # Create extension object
        ext = Ext(ext_type, ext_data)

        # Unpack with ext handler, if we have one
        if self.ext_handlers and ext.type in self.ext_handlers:
            return self.ext_handlers[ext.type](ext)
        # Unpack with ext classes, if type is registered
        if ext_type in ext_type_to_class:
            try:
                return ext_type_to_class[ext_type].unpackb(ext_data)
            except AttributeError:
                raise NotImplementedError(
                    "Ext class {:s} lacks unpackb()".format(repr(ext_type_to_class[ext_type]))
                )

        return ext

    async def _unpack_array(self, code):
        ic = ord(code)
        if (ic & 0xF0) == 0x90:
            length = ic & ~0xF0
        elif ic == 0xDC:
            length = await self._re0(">H", 2)
        elif ic == 0xDD:
            length = await self._re0(">I", 4)
        else:
            aloader._fail()
        l = []
        for i in range(length):
            l.append(await self._unpack())
        return tuple(l) if self.use_tuple else l

    @staticmethod
    def _deep_list_to_tuple(obj):
        if isinstance(obj, list):
            return tuple([aloader._deep_list_to_tuple(e) for e in obj])
        return obj

    async def _unpack_map(self, code):
        ic = ord(code)
        if (ic & 0xF0) == 0x80:
            length = ic & ~0xF0
        elif ic == 0xDE:
            length = await self._re0(">H", 2)
        elif ic == 0xDF:
            length = await self._re0(">I", 4)
        else:
            aloader._fail()

        d = {} if not self.use_ordered_dict else collections.OrderedDict()
        for _ in range(length):
            # Unpack key
            k = await self._unpack()

            if isinstance(k, list):
                # Attempt to convert list into a hashable tuple
                k = aloader._deep_list_to_tuple(k)
            try:
                hash(k)
            except:
                raise UnhashableKeyException('unhashable key: "{:s}"'.format(str(k)))
            if k in d:
                raise DuplicateKeyException(
                    'duplicate key: "{:s}" ({:s})'.format(str(k), str(type(k)))
                )

            # Unpack value
            v = await self._unpack()

            try:
                d[k] = v
            except TypeError:
                raise UnhashableKeyException('unhashable key: "{:s}"'.format(str(k)))
        return d

    async def _unpack(self):
        code = await self._re(1)
        ic = ord(code)
        if (ic <= 0x7F) or (0xCC <= ic <= 0xD3) or (0xE0 <= ic <= 0xFF):
            return await self._unpack_integer(code)
        if ic <= 0xC9:
            if ic <= 0xC3:
                if ic <= 0x8F:
                    return await self._unpack_map(code)
                if ic <= 0x9F:
                    return await self._unpack_array(code)
                if ic <= 0xBF:
                    return await self._unpack_string(code)
                if ic == 0xC1:
                    raise ReservedCodeException("got reserved code: 0xc1")
                return (None, 0, False, True)[ic - 0xC0]
            if ic <= 0xC6:
                return await self._unpack_binary(code)
            return self._unpack_ext(code)
        if ic <= 0xCB:
            return await self._unpack_float(code)
        if ic <= 0xD8:
            return await self._unpack_ext(code)
        if ic <= 0xDB:
            return await self._unpack_string(code)
        if ic <= 0xDD:
            return await self._unpack_array(code)
        return await self._unpack_map(code)

    async def load(self):
        return await self._unpack()
