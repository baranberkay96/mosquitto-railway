#!/usr/bin/env python3
"""Private /healthz on $PORT for Railway's healthcheck (STANDARD 8.34).

Each request opens an MQTT 3.1.1 connection to the local broker, logs in
with the generated user and returns 200 only on a successful CONNACK. The
credentials come from a root-written file readable only by this process;
nothing secret is served or logged.
"""
import http.server
import os
import socket
import struct

CREDENTIALS = "/run/railway-mqtt-health"
BROKER = ("127.0.0.1", 1883)


def port() -> int:
    value = os.environ.get("PORT", "")
    return int(value) if value.isdigit() and 1 <= int(value) <= 65535 else 8081


def credentials() -> tuple[str, str]:
    with open(CREDENTIALS, encoding="utf-8") as handle:
        user, _, password = handle.read().partition("\n")
    return user, password.rstrip("\n")


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


def mqtt_login() -> str:
    user, password = credentials()
    variable = utf8("MQTT") + bytes([4, 0xC2]) + struct.pack("!H", 10)  # v3.1.1, user+pass+clean session
    payload = utf8("railway-healthz") + utf8(user) + utf8(password)
    packet = bytes([0x10]) + remaining_length(len(variable) + len(payload)) + variable + payload
    with socket.create_connection(BROKER, timeout=3) as sock:
        sock.sendall(packet)
        reply = sock.recv(4)
        sock.sendall(b"\xe0\x00")  # DISCONNECT
    if len(reply) == 4 and reply[0] == 0x20:
        return "ok" if reply[3] == 0 else f"login refused (code {reply[3]})"
    return "unexpected reply"


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "railway-mqtt-healthz"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] not in ("/healthz", "/"):
            self.send_error(404)
            return
        try:
            result = mqtt_login()
        except OSError as err:
            result = f"broker unreachable ({type(err).__name__})"
        body = f"{result}\n".encode()
        self.send_response(200 if result == "ok" else 503)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_HEAD = do_GET

    def log_message(self, *args) -> None:
        return


class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def server_bind(self) -> None:
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def main() -> None:
    try:
        server = DualStackServer(("::", port()), Handler)
    except OSError:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port()), Handler)
        server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
