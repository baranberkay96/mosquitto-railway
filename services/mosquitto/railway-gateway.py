#!/usr/bin/env python3
"""Small HTTP front for Mosquitto on Railway's public domain (port $PORT).

- WebSocket upgrade requests (any path, e.g. /mqtt) are passed through
  byte for byte to Mosquitto's built-in WebSockets listener on
  127.0.0.1:9001. Mosquitto's own listener closes plain HTTP requests
  without an answer, which Railway's edge turns into a 502.
- GET /healthz logs in to the broker over MQTT 3.1.1 with the generated
  user (Railway's healthcheck, STANDARD 8.34): 200 on CONNACK 0, else 503.
- GET / answers with a short text page; anything else is 404.
Nothing secret is served or logged. Listens on all IPv4 and IPv6 addresses.
"""
import asyncio
import os
import struct

CREDENTIALS = "/run/railway-mqtt-health"
MQTT = ("127.0.0.1", 1883)
WEBSOCKETS = ("127.0.0.1", 9001)
MAX_HEAD = 16384


def port() -> int:
    value = os.environ.get("PORT", "")
    return int(value) if value.isdigit() and 1 <= int(value) <= 65535 else 8080


def utf8(value: str) -> bytes:
    data = value.encode()
    return struct.pack("!H", len(data)) + data


def remaining_length(length: int) -> bytes:
    out = bytearray()
    while True:
        byte, length = length % 128, length // 128
        out.append(byte | (0x80 if length else 0))
        if not length:
            return bytes(out)


async def mqtt_login() -> str:
    with open(CREDENTIALS, encoding="utf-8") as handle:
        user, _, password = handle.read().partition("\n")
    variable = utf8("MQTT") + bytes([4, 0xC2]) + struct.pack("!H", 10)
    payload = utf8("railway-healthz") + utf8(user) + utf8(password.rstrip("\n"))
    packet = bytes([0x10]) + remaining_length(len(variable) + len(payload)) + variable + payload
    reader, writer = await asyncio.wait_for(asyncio.open_connection(*MQTT), 3)
    try:
        writer.write(packet)
        await writer.drain()
        reply = await asyncio.wait_for(reader.readexactly(4), 3)
        writer.write(b"\xe0\x00")
        await writer.drain()
    finally:
        writer.close()
    if reply[0] == 0x20:
        return "ok" if reply[3] == 0 else f"login refused (code {reply[3]})"
    return "unexpected reply"


async def respond(writer: asyncio.StreamWriter, status: str, body: str) -> None:
    data = body.encode()
    writer.write(f"HTTP/1.1 {status}\r\nContent-Type: text/plain; charset=utf-8\r\n"
                 f"Content-Length: {len(data)}\r\nConnection: close\r\n\r\n".encode() + data)
    await writer.drain()


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        writer.close()


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 30)
    except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
        writer.close()
        return
    lines = head.decode("latin-1").split("\r\n")
    parts = lines[0].split(" ")
    path = parts[1].split("?", 1)[0] if len(parts) > 1 else "/"
    headers = {k.strip().lower(): v.strip() for k, _, v in (line.partition(":") for line in lines[1:] if ":" in line)}
    try:
        if headers.get("upgrade", "").lower() == "websocket":
            up_reader, up_writer = await asyncio.wait_for(asyncio.open_connection(*WEBSOCKETS), 5)
            up_writer.write(head)
            await up_writer.drain()
            await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))
            return
        if path == "/healthz":
            try:
                result = await mqtt_login()
            except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
                result = f"broker unreachable ({type(err).__name__})"
            await respond(writer, "200 OK" if result == "ok" else "503 Service Unavailable", result + "\n")
        elif path == "/":
            await respond(writer, "200 OK", "Eclipse Mosquitto MQTT broker. Connect with an MQTT client over "
                                            "WebSockets (wss://this-host/mqtt) or MQTT over the TCP proxy.\n")
        else:
            await respond(writer, "404 Not Found", "not found\n")
    except (OSError, asyncio.TimeoutError):
        pass
    finally:
        writer.close()


async def main() -> None:
    # The public domain targets 8080; Railway's healthcheck probes $PORT. Serve both
    # when they differ (e.g. an older template configuration with PORT=8081).
    servers = [await asyncio.start_server(handle, host=None, port=p, limit=MAX_HEAD) for p in sorted({port(), 8080})]
    await asyncio.gather(*(s.serve_forever() for s in servers))


if __name__ == "__main__":
    asyncio.run(main())
