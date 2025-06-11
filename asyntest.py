# asyntest.py Test/demo of asychronous use of MessagePack

# Copyright (c) 2021-5 Peter Hinch Released under the MIT License see LICENSE

# From testing on a pyboard:
#   Free RAM after reset 101504 bytes. Free RAM while running 82944 bytes
#   Usage 18560 bytes i.e. ~18.1KiB
#   This compares with 5312 bytes for a similar script sending plain text.
#   The MessagePack overhead is thus 13,248 bytes (12.9KiB).

from sys import platform
import asyncio
import umsgpack
from machine import UART, Pin
import gc


if platform == "pyboard":
    uart = UART(4, 9600)  # Pyboard (link pins X1 and X2)
elif platform == "rp2":
    uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))  # Pi Pico (link pins 0 and 1)
elif platform == "esp32":
    uart = UART(2, baudrate=9600, tx=17, rx=16)  # Adafruit Huzzah32 (link pins TX and RX)
else:
    raise OSError(f"Unknown platform {platform}")


async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    obj = [
        1,
        True,
        False,
        0xFFFFFFFF,
        {"foo": b"\x80\x01\x02", "bar": [1, 2, 3, {"a": [1, 2, 3, {}]}]},
        -1,
        2.12345,
    ]

    while True:
        s = umsgpack.dumps(obj)
        swriter.write(s)
        await swriter.drain()
        await asyncio.sleep(5)
        obj[0] += 1


# Obsever may be a class with __call__ or a simple callback function
class StreamObserver:
    def __call__(self, data: bytes) -> None:
        print(f"{data}")


# def stream_observer(data: bytes):
#   print(f"{data}")


async def receiver():
    uart_aloader = umsgpack.aloader(asyncio.StreamReader(uart), observer=StreamObserver())
    async for res in uart_aloader:
        print("Received (aloader):", res)


async def main():
    asyncio.create_task(sender())
    asyncio.create_task(receiver())
    while True:
        gc.collect()
        print("mem free", gc.mem_free())
        await asyncio.sleep(20)


def test():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        asyncio.new_event_loop()
        print("asyntest.test() to run again.")


test()
