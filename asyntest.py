# asyntest.py Test/demo of asychronous use of MessagePack

# Configured for a Pyboard. Link pins X1 and X2.

# Copyright (c) 2021 Peter Hinch Released under the MIT License see LICENSE

# Free RAM after reset 101504 bytes. Free RAM while running 82944 bytes
# Usage 18560 bytes i.e. ~18.1KiB
# This compares with 5312 bytes for a similar script sending plain text.
# The MessagePack overhead is thus 13,248 bytes (12.9KiB).

import asyncio
import umsgpack
from machine import UART, Pin
import gc

try:
    uart = UART(4, 9600)  # Pyboard (link pins X1 and X2)
except ValueError:
    uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))  # Pi Pico (link pins 0 and 1)

async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    obj = [1, True, False, 0xffffffff, {u"foo": b"\x80\x01\x02", \
                  u"bar": [1,2,3, {u"a": [1,2,3,{}]}]}, -1, 2.12345]

    while True:
        s = umsgpack.dumps(obj)
        swriter.write(s)
        await swriter.drain()
        await asyncio.sleep(5)
        obj[0] += 1

class stream_observer:
    def update(self, data: bytes) -> None:
        print(f'{data}')

async def receiver():
    sreader = asyncio.StreamReader(uart)
    recv_observer = stream_observer()
    while True:
        res = await umsgpack.aload(sreader, observer=recv_observer)
        print('Recieved', res)

async def receiver_using_aloader():
    uart_aloader = umsgpack.aloader(asyncio.StreamReader(uart), observer=stream_observer())
    while True:
        res = await uart_aloader.load()
        print('Received (aloader):', res)

async def main():
    asyncio.create_task(sender())
    # asyncio.create_task(receiver())
    asyncio.create_task(receiver_using_aloader())
    while True:
        gc.collect()
        print('mem free', gc.mem_free())
        await asyncio.sleep(20)

def test():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print('asyntest.test() to run again.')

test()
