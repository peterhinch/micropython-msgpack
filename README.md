# 0. Contents

1. [Introduction](./README.md#1-micropython-messagepack-introduction)  
 1.1 [Supported Types](./README.md#11-supported-types) List of supported data types.  
 1.2 [Library update](./README.md#12-library-update) Changes in release 0.2.0.  
 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.1 [Extended built-in classes](./README.md#121-extended-built-in-classes)  
 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.2 [Asynchronous unpacking](./README.md#122-asynchronous-unpacking) Use with streaming data.  
 1.3 [Comprssion performance](./README.md#13-compression-performance)  
2. [The MicroPython implementation](./README.md#2-the-micropython-implementation)  
 2.1 [Inter-operation](./README.md#21-inter-operation) Standard compliance: data exchange with other systems.  
3. [Installation](./README.md#3-installation)  
 3.1 [Quick install](./README.md#31-quick-install)  
 3.2 [Files](./README.md#32-files) List of installed files.  
 3.3 [Manual install](./README.md#33-manual-install) Doing it the hard way.  
4. [API](./README.md#4-api) User interface.  
 4.1 [Load options](./README.md#41-load-options) Specialist options.  
 4.2 [Dump options](./README.md#42-dump-options)  
5. [Extension modules](./README.md#5-extension-modules:-additional-built-in-types) Using extension modules.  
6. [Extending umsgpack](./README.md#6-extending-umsgpack) Writing extensions.  
 6.1 [Serialisable user classes](./README.md#61-serialisable-user-classes)  
 6.2 [Adding built-in types](./README.md#62-adding-built-in-types)  
7. [Asynchronous use](./README.md#7-asynchronous-use) Use with streaming I/O.  
 7.1 [Serialisation](./README.md#71-serialisation)  
 7.2 [De-serialisation](./README.md#72-de-serialisation)  
 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7.2.1 [The Observer object](./README.md#721-the-observer-object) Optionally observe the data stream.  
8. [Exceptions](./README.md#8-exceptions)  
9. [Test suite](./README.md#9-test-suite)  
10. [Changes for MicroPython](./README.md#10-changes-for-micropython) Brief summary of changes for microcontroller use.  
11. [Notes on extension classes](./README.md#11-notes-on-extension-classes) Detailed "how it works" notes.  
12. [Measurement of RAM usage](./README.md#12-measurement-of-ram-usage)  
13. [Acknowledgements](./README.md#13-acknowledgements)  
14. [References](./README.md#14-References)  
15. [Licence](./README.md#15-licence)

# 1. MicroPython MessagePack Introduction

[MessagePack](http://msgpack.org/) is a serialization protocol similar to JSON.
Where JSON produces human readable strings, MessagePack produces binary `bytes`
data. The protocol achieves a substantial reduction in data volume. Its
combination of ease of use, extensibility, and packing performance makes it
worth considering in any application where these capabilities are of use.

This MicroPython implementation has usage identical to that of the `json`
library:
```python
import umsgpack
obj = [1, 2, 3.14159]
s = umsgpack.dumps(obj)  # s is a bytes object
print(umsgpack.loads(s))  # Outcome [1, 2, 3.14159]
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
The protocol is self describing even when extended. Extended usage is simply a
matter of importing the relevant library:
```python
import umsgpack, umsgpack.mpk_complex  # Add complex support
s = umsgpack.dumps([1, "abc", 1+9j])
print(umsgpack.loads(s))  # Outcome [1, 'abc', (1+9j)]
```
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
 overridden by a load option. An extension module provides proper support
 whereby `list` and `tuple` objects unpack unchanged.
 * `list` Termed "array" in MessagePack documentation.
 * `dict` Termed "map" in MessagePack docs.

The `list` and `dict` types may contain any supported type including `list` and
`dict` instances (ad nauseam).

Extended support currently adds the following options:
 * `tuple` Provides an explicit distinction between `tuple` and `list` types:
 if it is encoded as a `tuple` it will be decoded as one.
 * `complex`
 * `set`
 * `bytearray` Provides an explicit distinction between `bytes` and `byterray`.

This document details how to support further built-in types and/or user-defined
classes.

## 1.2 Library Update

A substantial update has been undertaken to V0.2.0. For users of "advanced"
features (extension and asynchronous use) this is a breaking change. Objectives
were to save RAM by removing unnecessary features and simplifying code. PEP5
compliance has been improved. To eliminate duplication the `as_load` module has
been abandoned in favour of `as_loader`.

### 1.2.1 Extended built-in classes

The ext handler approach (formerly an option) has been discarded. Extension is
exclusively via an enhanced `ext_serializable` decorator. The `mpext` function
has been discarded. This enables each extension class to be handled by a separate
Python file, improving modularity, reducing RAM use, and easing the addition of
new classes. In consequence the old `umsgpack_ext.py` is replaced by individual
files such as `umsgpack.mpk_set.py`. Other improvements minimise object creation
when packing extended built-ins.

### 1.2.2 Asynchronous unpacking

Unpacking is now via an asynchronous iterator. The `observer` object can now be
any callable (a callback function/method or a class).

## 1.3 Compression performance

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

#### [Contents](./README.md#0-contents)  

# 2. The MicroPython implementation

This implementation is based on the following well proven MessagePack repo
[u-msgpack-python](https://github.com/vsergeev/u-msgpack-python). This runs
under Python 2 and Python 3. With trivial adaptations it will run under
[MicroPython](https://micropython.org/) but at a high cost in RAM consumption.
This version was adapted from that codebase and optimised to minimise RAM usage
when run on microcontrollers. When using frozen bytecode or romfs RAM use can be
as low as 2192 bytes for `dumps` and 1008 bytes for `loads` - see
[section 12](./README.md#12-measurement-of-ram-usage).

This version is a subset of the original. Support was removed for features
thought problematic for microcontroller use. The principal example is that of
timestamps. MicroPython does not support the `datetime` module. There are also
issues with platforms differing in their time handling, notably the epoch. On a
microcontroller it is simple to send the integer result from `time.time()` or
even `time.time_ns()`. Python 2 support is removed. The code will run under
Python 3.

Supported types are fully compliant with a subset of the latest
[MessagePack specification](https://github.com/msgpack/msgpack/blob/master/spec.md).
In particular, it supports the new binary, UTF-8 string and application-defined
ext types. As stated above, timestamps are unsupported.

This MicroPython version uses various techniques to minimise RAM use including
"lazy imports": a module is only imported on first usage. For example an
application that only de-serialises data using synchronous code will not import
code to dump data or that to support asynchronous programming.

# 2.1 Inter-operation

The un-extended module conforms to the MessagePack specification. Consequently
messages may be exchanged between systems using different MessagePack modules
including applications written in non-Python languages. If extension modules are
to be used in such applications, a matching extension will be required by the
foreign language party.

The MessagePack specification does not distinguish between mutable and
immutable types. Consequently the non-extended module will be unable to
distinguish `tuple` and `list` items, also `bytes` and `bytearray`. The
extension modules address this.

#### [Contents](./README.md#0-contents)  

# 3. Installation

## 3.1 Quick install

The library may be installed using the official `mpremote`:
```bash
$ mpremote mip install "github:peterhinch/micropython-msgpack"
```

## 3.2 Files

The following files are installed by `mpremote`:  
1. `umsgpack/__init__.py` Necessary library support.  
2. `umsgpack/mp_dump.py` Supports `dump` and `dumps` commands.  
3. `umsgpack/mp_load.py` Supports `load` and `loads` commands.  
4. `umsgpack/as_loader.py` Supports `ALoader` asynchronous loader class.  
5. `umsgpack/mpk_bytearray.py` Extends support to `bytearray`.  
6. `umsgpack/mpk_complex.py` Extends support to `complex`.  
7. `umsgpack/mpk_set.py` Extends support to `set`.  
8. `umsgpack/mpk_tuple.py` Extends support to `tuple`.  
9. `asyntest.py` Demo of asynchronous use of MessagePack.  
10. `user_class.py` Demo of a user defined class that is serialisable by MessagePack.  

In a minimal installation only items 1-3 are required.

Additional files:
1. `asyntest_py3_serial` Demo of running the library on a PC.
2. `test_umsgpack.py` The full test suite.

See [section 9](./README.md#9-test-suite) for details of the test suite.

## 3.3 Manual install

Clone the repo by moving to a directory on your PC and issuing
```bash
$ git clone https://github.com/peterhinch/micropython-msgpack
```
Copy the directory `umsgpack` and its contents to your target hardware.

The following optional files may also be copied to the target:
 * `user_class.py` A serialisable user class.
 * `asyntest.py` Demo of asynchronous use. See [section 7](./README.md#7-asynchronous-use).

The file `test_umsgpack.py` is the test suite which runs on a PC. See
[section 9](./README.md#9-test-suite).

#### [Contents](./README.md#0-contents)  

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
 5. `ALoader(fp, **options)` Asynchronous unpack of data from a `StreamReader`.
 See [section 7](./README.md#7-asynchronous-use).

The options are discussed below. Most are rather specialised - the principal use
case being exchanging data with non-Python targets.

## 4.1 Load options

`load`, `loads` and `ALoader` support the following options as keyword args:  
 1. `allow_invalid_utf8` (bool): unpack invalid strings into bytes (default
 `False` which causes an exception to be raised).
 2. `use_ordered_dict` (bool): unpack dicts into `OrderedDict`, instead of
 `dict`. (default `False`).
 3. `use_tuple` (bool): unpacks arrays into tuples, instead of lists (default
 `False`). The `mpk_tuple` module (if used) makes this redundant.
 4. `observer` (ALoader only): a `callable` (a function or an object with a
 `__call()__` method) which is called with the results of each `readexactly(n)`
 call. This could be used, for example, to calculate a CRC value on the received
 message data.

Work is in progress to make `dict` instances ordered by default, so option 2
may become pointless.

## 4.2 Dump options

`dump` and `dumps` support the following option as a keyword arg:  

 1. `force_float_precision` (str): `"single"` to force packing floats as
 IEEE-754 single-precision floats, `"double"` to force packing floats as
 IEEE-754 double-precision floats. By default the precision of the target's
 firmware is detected and used.

At risk of stating the obvious, on a 32-bit platform there is little point in
packing to 64-bit precision as the platform's underlying precision is only 32
bits. However packing as single on a 64-bit platform saves a lot of space. The
supplied `mpk_complex.py` honours the `force_float_precision` arg.

#### [Contents](./README.md#0-contents)  

# 5. Extension modules: additional built-in types

These extend MessagePack to handle further built-in data types. Each module
supports one data type; importing a module enables that support. Currently the
following types are supported:
* `set`
* `complex`
* `tuple` Natively `tuple` instances unpack as `list` objects. This module enables
`tuple` and `list` data types to be preserved.
* `bytearray` By default a `bytearray` decodes as a `bytes` object. This module
remedies this.

The following enables support for `byterray`, `set`, `complex` and `tuple` and
illustrates saving and restoring a `set`.
```py
import umsgpack
import umsgpack.mpk_bytearray, umsgpack.mpk_set, umsgpack.mpk_complex, umsgpack.mpk_tuple
umsgpack.dumps({1,2,3})
# Outcome: b'\xd6Q\x93\x03\x01\x02'
umsgpack.loads(b'\xd6Q\x93\x03\x01\x02')
# Outcome {1, 2, 3}
```
The following examples may be pasted at the REPL:
```python
import umsgpack
import umsgpack.mpk_complex
with open('data', 'wb') as f:
   umsgpack.dump(1 + 4j, f)
```
Reading back:
```python
import umsgpack
import umsgpack.mpk_complex
with open('data', 'rb') as f:
    z = umsgpack.load(f)
print(z)
# Outcome (1+4j)
```
#### [Contents](./README.md#0-contents)  

# 6 Extending umsgpack

This is done via the `ext_serializable` decorator which is used in two ways: to
create serialisable user classes and to support additional built-in types.

## 6.1 Serialisable user classes

This example of a serialisable user class may be found in `user_class.py`. It
provides a `Point3d` class representing a point in 3D space stored as three
`float` values.
```python
import umsgpack
import struct

@umsgpack.ext_serializable(0x10)
class Point3d:
    def __init__(self, x, y, z):
        self.v = (float(x), float(y), float(z))

    def __str__(self):
        return "Point3d({:5.2f} {:5.2f} {:5.2f})".format(*self.v)

    def packb(self):
        return struct.pack(">fff", *self.v)

    @staticmethod
    def unpackb(data, options):
        return Point3d(*struct.unpack(">fff", data))
```
The single arg to `ext_serializable` is the extension type: this is an arbitrary
byte value which must be unique to the application. The `packb` and `unpackb`
methods specify how the object is to be packed by `struct`. The `packb` method
must return a `bytes` object and `unpackb` returns a new instance of the class.

It may be run as follows (paste at the REPL):
```python
import umsgpack
from user_class import Point3d
p = Point3d(1.0, 2.1, 3)
s = umsgpack.dumps(p)
print(umsgpack.loads(s))  # Outcome Point3d( 1.00  2.10  3.00)
```

## 6.2 Adding built-in types

The following is a simplified version of the contents of `mpk_complex.py` (the
actual module includes code to define the float precision):
```python
import umsgpack
import struct

@umsgpack.ext_serializable(0x49, complex)
class Complex:
    @staticmethod
    def packb(s, options):  # s is a complex instance
        return struct.pack(">ff", s.real, s.imag)

    @staticmethod
    def unpackb(data, options):
        return complex(*struct.unpack(">ff", data))
```
The decorator takes two args, the extension type and the type to be handled.
A class defined with the two-arg decorator must provide the following static
methods:

 * `packb` Takes two args, an instance of the type to be serialised and a
 `dict` of pack options. Returns a `bytes` instance containing the serialised
 object. The method can optionally access `.options`.
 * `unpackb` This accepts a `bytes` instance of packed data and a `dict` of
 unpack options. Returns a new instance of the unpacked data type.

The options comprise the keyword args supplied to `dump(s)` and `load(s)`
respectively.

Typically packing and unpacking is done using the `struct` module, but in some
simple cases it may be done by `umsgpack` itself. For example `mpk_set.py`:
```py
@umsgpack.ext_serializable(0x51, set)
class Set:
    @staticmethod
    def packb(s, options):  # Pack as a list
        return umsgpack.dumps(list(s))

    @staticmethod
    def unpackb(data, options):
        return set(umsgpack.loads(data))  # Cast to set
```
Contributions of new built-in serialisers are welcome.

#### [Contents](./README.md#0-contents)  

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
receiver. Further, in many cases a substantial amount of the message must be
read before the total length can be deduced. The `ALoader` class is
instantiated with a `StreamReader`: incoming data is unpacked and objects
retrieved using an asynchronous iterator:
```python
async def receiver():
    uart_aloader = umsgpack.ALoader(asyncio.StreamReader(uart))
    async for item in uart_aloader:
        print('Received', item)
```

The demo `asyntest.py` runs on a Pyboard with pins X1 and X2 linked. See code
comments for connections with other platforms. The code includes notes regarding
RAM overhead.

### 7.2.1 The Observer object

This enables the incoming data stream to be monitored. An observer can be any
callable - typically an instance of a user class with an `__call__` method. This
is called whenever data is read from the stream: it receives a `bytes` instance
with the latest data or `b""` when a decode is complete. The following (from
`asyntest.py`) illustrates an example which displays a buffer full of data for
each decode.
```py
class StreamObserver:
    def __init__(self, size=100):
        self.buf = bytearray(size)
        self.n = 0

    def __call__(self, data: bytes) -> None:
        if l := len(data):
            self.buf[self.n : self.n + l] = data
            self.n += l
        else:  # End of data
            print(f"{self.buf[:self.n]}")
            self.n = 0

async def receiver():
    uart_aloader = umsgpack.ALoader(asyncio.StreamReader(uart), observer=StreamObserver())
    async for res in uart_aloader:
        print("Received:", res)
```
#### [Contents](./README.md#0-contents)  

# 8. Exceptions

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
#### [Contents](./README.md#0-contents)  

# 9. Test suite

This is mainly of interest to those wanting to modify the code.

The repo includes the test suite `test_umsgpack.py` which must be run under
Python 3 in a directory containing the `umsgpack` tree. It will not run under
MicroPython because it tests large data types: the test suite causes memory
errors when run under even the Unix build of MicroPython. To run the test suite
issue:
```bash
$ python3 test_umsgpack.py
```
#### [Contents](./README.md#0-contents)  

# 10. Changes for MicroPython

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
Many functions refactored to save bytes.  
`InvalidString` class removed because it is a subclass of a native type.  
Method of detecting platform's float size changed (MicroPython does not support
the original method).  

#### [Contents](./README.md#0-contents)  

# 11. Notes on extension classes

These notes are for those wishing to understand how this works, perhaps to add
support for further types. Consider this code which adds support for complex
numbers:
```py
import umsgpack
import umsgpack.mpk_complex
```
The `mpk_complex` module contains this code
```py
@umsgpack.ext_serializable(0x50, complex)
class Complex:
    @staticmethod
    def packb(obj, options):
      # Code omitted
    @staticmethod
    def unpackb(data, options):
      # code omitted
```
Classes decorated with `ext_serializable` are known as "packers" and must have
static methods `packb` and `unpackb`.

For builtins the `ext_serializable` decorator takes two args, the `ext_type`
integer value which represents the record type, and the class to be encoded. The
`ext_type` value should be a byte unique to this class. The decorator
(in `__init__.py`) runs when the module is imported. Because there are two args
it populates a global `builtins` dictionary. The key is the target class
(`complex`) and the value is a 2-tuple `(0x50, Complex)` i.e. the unique
`ext_type` byte and the packer class.

In the case of user classes the decorator receives only one arg being the
`ext_type` value. A global dictionary `custom` is populated: the key is the
user class and the value is the `ext_type`. (No instance of the user class is
created). The user class must have a `packb` method and an `unpackb` static
method.

On packing the `builtins` and `custom` dictionaries are used to locate the
appropriate packer with its `packb` method. Packers are never instantiated.

In both type of extensions the decorator populates a global `packers`
dictionary: the key is the `ext_type` and the value is the packer class or user
class. This class is used on unpacking to run the `unpackb` static method.

This mechanism implies that the names of a packer class and the module
containing it are arbitrary.

The `packb` method of a packer or use class converts the data, returning a
`bytes` instance. It receives the object to be packed and a dict of `.options`,
being the keyword args passed to `dump(s)`.

The `unpackb` static method accepts a `bytes` instance as created by `packb` and
an `options` dict containing any options passed to `load(s)`. It returns an
instance of the supported class.

Typically `packb` and `unpackb` use the `struct` module, but in simple cases
they can convert between the supported data type and one natively supported,
and use `umsgpack` itself. See `mpk_set.py` which converts a `set` to a `list`
and _vice versa_.

#### [Contents](./README.md#0-contents)  

# 12. Measurement of RAM usage

This test used an RP2040 with precompiled code in romfs. In each case the code
below was placed in `main.py`, the board re-booted, and the result observed.

Pack:
```py
import gc, umsgpack
gc.collect()
a = gc.mem_free()
umsgpack.dumps(1)
gc.collect()
b = gc.mem_free()
print(a-b)
```
Unpack:
```py
import gc, umsgpack
gc.collect()
a = gc.mem_free()
umsgpack.loads(b'\x01')
gc.collect()
b = gc.mem_free()
print(a-b)
```
Results were pack: 2192 bytes, unpack 1008 bytes.

#### [Contents](./README.md#0-contents)  

# 13. Acknowledgements

This project was inspired by
[this forum thread](https://forum.micropython.org/viewtopic.php?f=15&t=10827)
where user WZab performed an initial port of the source library. See also
[this GitHub issue](https://github.com/micropython/micropython/issues/4241).

# 14. References

MessagePack main site:  
[MessagePack](http://msgpack.org/)  
MessagePack spec:  
[the MessagePack spec](https://github.com/msgpack/msgpack/blob/master/spec.md).  
Code on which this repo is based:  
[u-msgpack-python](https://github.com/vsergeev/u-msgpack-python).

# 16. Licence

micropython-msgpack is MIT licenced. See the included `LICENSE` file for more
details.
