# This doc is incomplete and under development.

# 1. MessagePack Introduction

[MessagePack](http://msgpack.org/) is a serialization protocol similar to JSON.
Where JSON produces human readable strings, MessagePack produces binary `bytes`
data. The protocol achieves a substantial reduction in data volume. This
MicroPython implementation has usage identical to that of the `ujson` library:
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
Where the protocol is extended it is still self describing. If the extension
module is available to the receiver, code as above will work. For example the
following might retrieve a `dict` containing, amongst other data, a `tuple` of
`complex` values:
```python
import umsgpack
import umsgpack_ext  # Extension module can encode tuple, set and complex
with open('data', 'rb') as f:
    z = umsgpack.load(f)
```
This document focuses on usage with MicroPython. The
[source document](https://github.com/vsergeev/u-msgpack-python) provides a lot
of useful information for those wishing to understand the protocol.

## 1.1 Supported types

The following types are natively supported.
 * `int` In range `-2**63` to `2**64 - 1`.
 * `bool`
 * `None`
 * `str` Unicode string.
 * `bytes` Binary data.
 * `float` IEEE-754 single or double precision controlled by a dump option.
 * `tuple` By default tuples are de-serialised as lists, but this can be
 overridden by a load option.
 * `list` Termed "array" in MessagePack documentation.
 * `dict` Termed "map" in MessagePack docs.

The `list` and `dict` types may contain any supported type including `list` and
`dict` instances.

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
speedup factor of 2.6. The `force_float_precision` arg ensures the same result
on 32 bit and 64 bit platforms.

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

This version is a subset of the original with support for features alien to
MicroPython removed. The principal example is that of timestamps which do not
exist in MicroPython. Python 2 support is removed. The code will run under
Python 3 but in practice there is little reason to do so.

Supported types are fully compliant with a subset of the latest
[MessagePack specification](https://github.com/msgpack/msgpack/blob/master/spec.md).
In particular, it supports the new binary, UTF-8 string and application-defined
ext types. As stated above, timestamps are unsupported.

The repository includes `umsgpack_ext.py` which optionally extends the library
to support Python `set`, `complex` and `tuple` objects. The aim is to show how
this can easily be extended to include further types.

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

The file `umsgpack_ext.py` simplifies the extension of MessagePack to support
extra Python native types. By default it supports `set`, `complex` and `tuple`
objects but this can readily be extended. To use this, copy it to the target
hardware.

The file `asyntest.py` demonstrates asynchronous use on a Pyboard. It can be
adapted to support any target with a UART.

## 3.1 Test suite

The repo includes the test suite `test_umsgpack.py` which must be run under
Python 3. This is because it tests large data types: the test suite causes
memory errors when compiled under even the Unix build of MicroPython. To run,
move to the location of the the `umsgpack` directory on your PC and issue:
```bash
$ python3 test_umsgpack.py
```

# 4. API

In applications using `ujson`, MessagePack provides a dop-in replacement with
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

## 4.1 Load options

`load`, `loads` and `aload` support the following options as keyword args:  
 1. `ext_handlers` a dictionary of Ext handlers, mapping integer Ext type to a
 callable that unpacks an instance of Ext into an object.
 2. `allow_invalid_utf8` (bool): unpack invalid strings into bytes (default
 `False` which causes an exception to be raised).
 3. `use_ordered_dict` (bool): unpack dicts into `OrderedDict`, instead of
 `dict`. (default `False`).
 4. `use_tuple` (bool): unpacks arrays into tuples, instead of lists (default
 `False`).

Work is in progress to make `dict` instances ordered by default, so option 3
may become pointless. The `umsgpack_ext` module enables tuples to be encoded in
a different format to lists which is more flexible than the global `use_tuple`
arg.

## 4.2 Dump options

`dump` and `dumps` support the following options as keyword args:  

 1. `ext_handlers` (dict): dictionary of Ext handlers, mapping a custom type
 to a callable that packs an instance of the type into an Ext object
 2. `force_float_precision` (str): `"single"` to force packing floats as
 IEEE-754 single-precision floats, `"double"` to force packing floats as
 IEEE-754 double-precision floats. By default the precision of the target's
 firmware is detected and used.

# 5. Extension module

The `umsgpack_ext` module simplifies the extension of `umsgpack` to support
additional Python built-in types or types supported by other libraries. By
default it supports `complex`, `set` and `tuple` types but it can readily
be extended to support further types. The following examples may be pasted at
the REPL:
```python
import umsgpack
from umsgpack_ext import mpext
with open('data', 'wb') as f:
   umsgpack.dump(mpext(1 + 4j), f)  # mpext() handles extension type
```
Reading back:
```python
import umsgpack, umsgpack_ext
with open('data', 'rb') as f:
    z = umsgpack.load(f)
print(z)  # z is complex
```
A type supported by `umsgpack_ext` is serialised using `mpext(obj)` which
returns an instance of a serialisable extension class.

# 6. Asynchronous use

TODO

# N. Changes for MicroPython

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
Provide uasyncio StreamReader support.  
Exported functions now match ujson: dump, dumps, load, loads (only).  
Many functions refactored to save bytes, e.g. replacing the function dispatch
table with code.  
Further refactoring to reduce allocations.  
`InvalidString` class removed because it is a subclass of a native type.  
Method of detecting platform's float size changed (MicroPython does not support
the original method).  
Version reset to (0.1.0).

## License

micropython-msgpack is MIT licensed. See the included `LICENSE` file for more details.
