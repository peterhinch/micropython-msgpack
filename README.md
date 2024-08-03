# 1. MicroPython MessagePack Introduction

[MessagePack](http://msgpack.org/) is a serialization protocol similar to JSON.
Where JSON produces human readable strings, MessagePack produces binary `bytes`
data. The protocol achieves a substantial reduction in data volume. Its
combination of ease of use, extensibility, and packing performance makes it
worth considering in any application where data volume is an issue.

This MicroPython implementation has usage identical to that of the `ujson`
library:
```python
import umsgpack
obj = [1, 2, 3.14159]
s = umsgpack.dumps(obj)  # s is a bytes object
```
MessagePack efficiently serialises a range of Python built-in types, a range
that can readily be extended to support further Python types or instances of
user defined classes. A key feature of the protocol is that, like JSON, it is
self describing: the receiver gets all the information needed to decode the
stream from the stream itself. This example assumes a file whose contents were
encoded with MessagePack.
```python
import umsgpack
with open('data', 'rb') as f:
    z = umsgpack.load(f)
print(z)  # z might be a wide range of Python objects
```
The protocol is self describing even when extended. The file
`umsgpack/umsgpack_ext.py` extends support to `complex`, `tuple` and `set`
built-in types. Provided that file exists on the target, the code above will
work even if the data includes such objects. Extension can be provided in a way
that is transparent to the application.

This document focuses on usage with MicroPython and skips most of the detail on
how MessagePack works. The
[source document](https://github.com/vsergeev/u-msgpack-python) provides a lot
of useful information for those wishing to understand the protocol. Also see
[the MessagePack spec](https://github.com/msgpack/msgpack/blob/master/spec.md).

## 1.1 Supported types

The following types are natively supported.
 * `int` In range `-2**63` to `2**64 - 1`.
 * `True`, `False` and `None`.
 * `str` Unicode string.
 * `bytes` Binary data.
 * `float` IEEE-754 single or double precision controlled by a dump option.
 * `tuple` By default tuples are de-serialised as lists, but this can be
 overridden by a load option. The extension module provides proper support
 wherby `list` and `tuple` objects unpack unchanged.
 * `list` Termed "array" in MessagePack documentation.
 * `dict` Termed "map" in MessagePack docs.

The `list` and `dict` types may contain any supported type including `list` and
`dict` instances (ad nauseam).

The file `umsgpack_ext.py` (in `umsgpack` directory) extends this to add the
following:
 * `tuple` Provides an explicit distinction between `tuple` and `list` types:
 if it is encoded as a `tuple` it will be decoded as one.
 * `complex`
 * `set`



## 1.2 Performance

The degree of compression compared to UJSON depends on the object being
serialised. The following gives an example:
```python
import umsgpack
import ujson
obj = [1, True, False, 0xffffffff, {u"foo": b"\x80\x01\x02", u"bar": [1,2,3, {u"a": [1,2,3,{}]}]}, -1, 2.12345]
lj = len(ujson.dumps(obj))
lm = len(umsgpack.dumps(obj, force_float_precision = "single"))
print(lj, lm, lj/lm)
```
Outcome: `lj` == 106 bytes, `lm` == 41 bytes corresponding to a transmission
speedup factor of 2.6. The `force_float_precision` option ensures the same
result on 32 bit and 64 bit platforms.

If large quantities of text are to be transmitted, a greater gain could be
achieved by compressing the text with a `gzip` style compressor and serialising
the resultant `bytes` object with MessagePack.

# 2. The MicroPython implementation

This implementation is based on the following well proven MessagePack repo
[u-msgpack-python](https://github.com/vsergeev/u-msgpack-python). This runs
under Python 2 and Python 3. With trivial adaptations it will run under
[MicroPython](https://micropython.org/) but at a high cost in RAM consumption.
This version was adapted from that codebase and optimised to minimise RAM usage
when run on microcontrollers. Consumption is about 12KiB measured on STM32.
Using frozen bytecode this reduces to about 3.5KiB. This was tested with the
`asyntest.py` demo, comparing the free RAM with that available running a
similar script which exchanges uncompressed data. The difference was taken to
be the library overhead of running compression and asynchronous decompression.

This version is a subset of the original. Support was removed for features
thought unnecessary for microcontroller use. The principal example is that of
timestamps. MicroPython does not support the `datetime` module. There are also
issues with platforms differing in their time handling, notably the epoch. On a
microcontroller it is simple to send the integer result from `time.time()` or
even `time.time_ns()`. Python 2 support is removed. The code will run under
Python 3.

Supported types are fully compliant with a subset of the latest
[MessagePack specification](https://github.com/msgpack/msgpack/blob/master/spec.md).
In particular, it supports the new binary, UTF-8 string and application-defined
ext types. As stated above, timestamps are unsupported.

The repository includes `umsgpack/umsgpack_ext.py` which optionally extends the
library to support Python `set`, `complex` and `tuple` objects. The aim is to
show how this can easily be extended to include further types.

This MicroPython version uses various techniques to minimise RAM use including
"lazy imports": a module is only imported on first usage. For example an
application that only de-serialises data using synchronous code will not import
code to dump data or that to support asynchronous programming.

# 3. Installation

Clone the repo by moving to a directory on your PC and issuing
```bash
$ git clone https://github.com/peterhinch/micropython-msgpack
```
Copy the directory `umsgpack` and its contents to your target hardware.

The following optional files may also be copied to the target:
 * `user_class.py` A serialisable user class.
 * `asyntest.py` Demo of asynchronous use. See [section 7](./README.md#7-asynchronous-use).

The files `run_test_suite` and `test_umsgpack.py` comprise the test suite which
runs on a PC. See [section 9](./README.md#9-test-suite).

If RAM usage is to be minimised, the file `umsgpack/umsgpack_ext.py` may be
deleted from the target with loss of its additional type support. Its overhead
is about 2KiB measured on a Pyboard with no frozen bytecode.

# 4. API

In applications using `ujson`, MessagePack provides a drop-in replacement with
the same API. The human readable (but large) strings are replaced by compact
binary `bytes` objects.

The API supports the following methods:
 1. `dumps(obj, **options)` Pack an arbitrary Python object. Returns a `bytes`
 instance.
 2. `dump(obj, fp, **options)` Pack a Python object to a stream or file.
 3. `loads(s, **options)` Deserialise a `bytes` object. Returns a Python
 object.
 4. `load(fp, **options)` Unpack data from a stream or file.
 5. `aload(fp, **options)` Asynchronous unpack of data from a `StreamReader`.
 See [section 7](./README.md#7-asynchronous-use).

The options are discussed below. Most are rather specialised. I am unsure if
there is a practical use case for `ext_handlers`: an easier way is to use
[the ext_serializable decorator](./README.md#61-the-ext_serializable-decorator).

## 4.1 Load options

`load`, `loads` and `aload` support the following options as keyword args:  
 1. `allow_invalid_utf8` (bool): unpack invalid strings into bytes (default
 `False` which causes an exception to be raised).
 2. `use_ordered_dict` (bool): unpack dicts into `OrderedDict`, instead of
 `dict`. (default `False`).
 3. `use_tuple` (bool): unpacks arrays into tuples, instead of lists (default
 `False`). The extension module (if used) makes this redundant.
 4. `ext_handlers`: a dictionary of Ext handlers, mapping integer Ext type to a
 callable that unpacks an instance of Ext into an object. See
 [section 8](./README.md#8-ext-handlers).
 5. `observer` (aload only): an object with an update() method, which is
 called with the results of each readexactly(n) call. This could be used, for
 example, to calculate a CRC value on the received message data.
 
Work is in progress to make `dict` instances ordered by default, so option 3
may become pointless. The `umsgpack_ext` module enables tuples to be encoded in
a different format to lists which is more flexible than the global `use_tuple`
arg.

## 4.2 Dump options

`dump` and `dumps` support the following options as keyword args:  

 1. `force_float_precision` (str): `"single"` to force packing floats as
 IEEE-754 single-precision floats, `"double"` to force packing floats as
 IEEE-754 double-precision floats. By default the precision of the target's
 firmware is detected and used.
 2. `ext_handlers` (dict): dictionary of Ext handlers, mapping a custom type
 to a callable that packs an instance of the type into an Ext object. See
 [section 8](./README.md#8-ext-handlers).

# 5. Extension module

The `umsgpack_ext` module extends `umsgpack` to support `complex`, `set` and
`tuple` types, but its design facilitates adding further Python built-in types
or types supported by other libraries. Support is entirely transparent to the
application: the added types behave in the same way as native types.

The following examples may be pasted at the REPL:
```python
import umsgpack
with open('data', 'wb') as f:
   umsgpack.dump(1 + 4j, f)  # mpext() handles extension type
```
Reading back:
```python
import umsgpack
with open('data', 'rb') as f:
    z = umsgpack.load(f)
print(z)  # z is complex
```
 The file `umsgpack_ext.py` may be found in the `umsgpack` directory. To extend
 it to support additional types, see
[section 11](./README.md#11-notes-on-the-extension-module).

# 6. Serialisable user classes

An example of a serialisable user class may be found in `user_class.py`. It
provides a `Point3d` class representing a point in 3D space stored as three
`float` values. It may be run as follows (paste at the REPL):
```python
import umsgpack
from user_class import Point3d
p = Point3d(1.0, 2.1, 3)
s = umsgpack.dumps(p)
print(umsgpack.loads(s))
```

## 6.1 The ext_serializable decorator

This provides a simple way of extending MessagePack to include additional
types. The following is the contents of `user_class.py`:
```python
import umsgpack
import struct

@umsgpack.ext_serializable(0x10)
class Point3d:
    def __init__(self, x, y, z):
        self.v = (float(x), float(y), float(z))

    def __str__(self):
        return "Point3d({} {} {})".format(*self.v)

    def packb(self):
        return struct.pack(">fff", *self.v)

    @staticmethod
    def unpackb(data):
        return Point3d(*struct.unpack(">fff", data))
```
A class defined with the decorator must provide the following methods:
 * Constructor: stores the object to be serialised.
 * `packb` This returns a `bytes` instance containing the serialised object.
 * `unpackb` Defined as a static method, this accepts a `bytes` instance of
 packed data and returns a new instance of the unpacked data type.

Typically this packing and unpacking is done using the `struct` module, but in
the some simple cases it may be done by umsgpack itself. The following, taken
from the extension module, illustrates support for `complex`:
```python
@umsgpack.ext_serializable(0x50)
class Complex:
    def __init__(self, c):
        self.c = c

    def __str__(self):
        return "Complex({})".format(self.c)

    def packb(self):
        return struct.pack(">ff", self.c.real, self.c.imag)

    @staticmethod
    def unpackb(data):
        return complex(*struct.unpack(">ff", data))
```

# 7. Asynchronous use

## 7.1 Serialisation

Serialisation presents no problem in asynchronous code. The following example
serialises the data using the normal synchronous `dumps` method then sends it
asynchronously:
```python
async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    obj = [1, 2, 3.14159]
    while True:
        s = umsgpack.dumps(obj)  # Synchronous serialisation
        swriter.write(s)
        await swriter.drain()  # Asynchonous transmission
        await asyncio.sleep(5)
        obj[0] += 1
```

## 7.2 De-serialisation

This is potentially difficult. In the case of ASCII protocols like JSON and
Pickle it is possible to append a `b'\n'` delimiter to each message, then use
`StreamReader.readline()` to perform an asynchronous read of an entire message.
This works because the messages themselves cannot contain that character.
MessagePack is a binary protocol so the data may include all possible byte
values. Consequently a unique delimiter is unavailable.

MessagePack messages are binary sequences whose length is unknown to the
receiver. Further, in many case a substantial amount of the message must be
read before the total length can be deduced. The solution adopted is to add an
`aload()` method that accepts data from a `StreamReader`, decoding it as it
arrives. The following is an example of an asynchronous reader:
```python
async def receiver():
    sreader = asyncio.StreamReader(uart)
    while True:
        res = await umsgpack.aload(sreader)
        print('Recieved', res)
```
The demo `asyntest.py` runs on a Pyboard (or Pi Pico) with pins X1 and X2 linked. The code includes notes regarding RAM overhead.

The demo `asyntest_py3_serial.py` is similar, but meant to run on a computer with full python3.

# 8. Ext Handlers

This is an alternative to the `ext_serializable` decorator and provides another
option for extending MessagePack. In my view it is rather clunky and I struggle
to envisage a use case. It is included for completeness.

The packing functions accept an optional `ext_handlers` dictionary that maps
custom types to callables that pack the type into an Ext object. The callable
should accept the custom type object as an argument and return a packed
`umsgpack.Ext` object.

Example for packing `set` and `complex` types into Ext objects with type codes
0x20 and 0x30:

```python
umsgpack.dumps([1, True, {"foo", 2}, complex(3, 4)],
    ext_handlers = {
       set: lambda obj: umsgpack.Ext(0x20, umsgpack.dumps(list(obj))),
       complex: lambda obj: umsgpack.Ext(0x30, struct.pack("ff", obj.real, obj.imag))
       })
```

Similarly, the unpacking functions accept an optional `ext_handlers` dictionary
that maps Ext type codes to callables that unpack the Ext into a custom object.
The callable should accept a `umsgpack.Ext` object as an argument and return an
unpacked custom type object.

Example for unpacking Ext objects with type codes 0x20, and 0x30 into `set` and
`complex` objects:

``` python
umsgpack.loads(s,
    ext_handlers = {
      0x20: lambda ext: set(umsgpack.loads(ext.data)),
      0x30: lambda ext: complex(*struct.unpack("ff", ext.data)),
    })
```

Example for packing and unpacking a custom class:

``` python
class Point(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return "Point({}, {}, {})".format(self.x, self.y, self.z)

    def pack(self):
        return struct.pack(">iii", self.x, self.y, self.z)

    @staticmethod
    def unpack(data):
        return Point(*struct.unpack(">iii", data))

# Pack
obj = Point(1,2,3)
data = umsgpack.dumps(obj, ext_handlers = {Point: lambda obj: umsgpack.Ext(0x10, obj.pack())})

# Unpack
obj = umsgpack.loads(data, ext_handlers = {0x10: lambda ext: Point.unpack(ext.data)})
```
# 9. Exceptions

These are defined in `umsgpack/__init__.py`.

The `dump` and `dumps` methods can throw the following:
```python
# Packing error
class UnsupportedTypeException(PackException):
    "Object type not supported for packing."
```
The `load` and `loads` methods can throw the following. In practice these are
only likely to occur if data has been corrupted, for example if transmitted via
an unreliable medium:
```python
class InsufficientDataException(UnpackException):
    "Insufficient data to unpack the serialized object."

class InvalidStringException(UnpackException):
    "Invalid UTF-8 string encountered during unpacking."

class ReservedCodeException(UnpackException):
    "Reserved code encountered during unpacking."

class UnhashableKeyException(UnpackException):
    """
    Unhashable key encountered during map unpacking.
    The serialized map cannot be deserialized into a Python dictionary.
    """

class DuplicateKeyException(UnpackException):
    "Duplicate key encountered during map unpacking."
```

# 10. Test suite

This is mainly of interest to those wanting to modify the code.

The repo includes the test suite `test_umsgpack.py` which must be run under
Python 3 in a directory containing the `umsgpack` tree. It will not run under
MicroPython because it tests large data types: the test suite causes memory
errors when compiled under even the Unix build of MicroPython. The file
`umsgpack_ext.py` should not be present: this is because the test suite assumes
that `complex` and `set` are not supported. The script `run_test_suite` renames
`umsgpack_ext.py`, runs the tests and restores the file. 

# 11. Changes for MicroPython

Code in this repo is based on
[this implementation](https://github.com/vsergeev/u-msgpack-python), whose code
is of high quality. It required minimal changes to run under MicroPython.

Hosted on a microcontroller its RAM consumption was high; most changes were to
reduce this. Further, the nature of the protocol results in an issue when using
asynchronous code to de-serialise data which arrives slowly or sporadically.
This is handled by adding an asynchronous de-serialiser.

These can be summarised as follows:  
Python2 code removed.  
Compatibility mode removed.  
Timestamps removed.  
Converted to Python package with lazy import to save RAM.  
Provide asyncio StreamReader support.
Exported functions now match ujson: dump, dumps, load, loads (only).  
Many functions refactored to save bytes, e.g. replacing the function dispatch
table with code.  
Further refactoring to reduce allocations.  
`InvalidString` class removed because it is a subclass of a native type.  
Method of detecting platform's float size changed (MicroPython does not support
the original method).  
Version reset to (0.1.0).

# 12. Notes on the extension module

These notes are for those wishing to understand how this works, perhaps to add
support for further types.

The `mp_dump.py` attempts to load a function `mpext` from the module. If this
fails (becuase the module is missing) it creates a dummy function. When the
`dump` method runs, it executes `mpext` passing the object to be encoded. If
the type of the object matches one support by the extension, it returns an
instance of a serialisable class created with the passed object. If the type
does not match, the passed object is returned for `dump` to inspect.

Supporting additional types therefore comprises the following:
 1. Create an `ext_serializable` class for the new type as per
 [section 6.1](./README.md#61-the-ext_serializable-decorator).
 2. Change the function `mpext` to check for the new type and, if found, return
 an instance of the above class.

## Acknowledgements

This project was inspired by
[this forum thread](https://forum.micropython.org/viewtopic.php?f=15&t=10827)
where user WZab performed an initial port of the source library. See also
[this GitHub issue](https://github.com/micropython/micropython/issues/4241).

## Summary of references

MessagePack main site:  
[MessagePack](http://msgpack.org/)  
MessagePack spec:  
[the MessagePack spec](https://github.com/msgpack/msgpack/blob/master/spec.md).  
Code on which this repo is based:  
[u-msgpack-python](https://github.com/vsergeev/u-msgpack-python).

## License

micropython-msgpack is MIT licensed. See the included `LICENSE` file for more
details.
