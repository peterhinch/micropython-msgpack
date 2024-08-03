# asyntest_py3_serial.py Test/demo of asychronous use of MessagePack under full python3 with pyserial

# Configured for pyserial. Link RX and TX pins.

# Copyright (c) 2024 Peter Hinch Released under the MIT License see LICENSE

import asyncio
import umsgpack
import serial_asyncio

async def sender(swriter):
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

async def receiver(sreader):
    recv_observer = stream_observer()
    while True:
        res = await umsgpack.aload(sreader, observer=recv_observer)
        print('Received:', res)

async def receiver_using_aloader(sreader):
    uart_aloader = umsgpack.aloader(sreader, observer=stream_observer())
    while True:
        res = await uart_aloader.load()
        print('Received (aloader):', res)

async def main():
    reader, writer = await serial_asyncio.open_serial_connection(url='/dev/ttyUSB0', baudrate=9600)
    asyncio.create_task(sender(writer))
    # asyncio.create_task(receiver(reader))
    asyncio.create_task(receiver_using_aloader(reader))
    while True:
        print('running...')
        await asyncio.sleep(20)

def test():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')

test()
