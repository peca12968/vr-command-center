"""Minimal loopback WebSocket client for real world-publisher fixtures."""
import base64
import hashlib
import json
import secrets
import socket
import struct
import sys


class WebSocket:
    def __init__(self, port, route, token):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.file = self.sock.makefile("rb")
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        self.sock.sendall((f"GET {route} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nAuthorization: Bearer {token}\r\n\r\n").encode())
        status = self.file.readline().decode()
        headers = {}
        while (line := self.file.readline()) not in (b"\r\n", b""):
            name, value = line.decode().split(":", 1)
            headers[name.lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        if " 101 " not in status or headers.get("sec-websocket-accept") != expected:
            self.close()
            raise AssertionError("WebSocket handshake rejected: " + status.strip())

    def send(self, value, opcode=1):
        data = json.dumps(value, separators=(",", ":")).encode()
        size = len(data)
        head = bytes([0x80 | opcode, 0x80 | size]) if size < 126 else bytes([0x80 | opcode, 0x80 | 126]) + struct.pack("!H", size) if size < 65536 else bytes([0x80 | opcode, 0x80 | 127]) + struct.pack("!Q", size)
        mask = secrets.token_bytes(4)
        self.sock.sendall(head + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(data)))
        body = b""
        while True:
            header = self.file.read(2)
            if len(header) != 2 or header[0] & 15 == 8:
                raise AssertionError("World publisher closed without an acknowledgment")
            size = header[1] & 127
            if size == 126:
                size = struct.unpack("!H", self.file.read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.file.read(8))[0]
            if size > 1024 * 1024:
                raise AssertionError("Unbounded WebSocket response")
            body += self.file.read(size)
            if header[0] & 0x80:
                return json.loads(body)

    def close(self):
        self.file.close()
        self.sock.close()


if __name__ == "__main__":
    request = json.load(sys.stdin)
    publisher = WebSocket(request["port"], request["route"], request["token"])
    try:
        for message in request["messages"]:
            reply = publisher.send(message)
            if reply["type"] != "ack":
                raise RuntimeError(reply.get("error", "World fixture publication was rejected"))
        print(json.dumps(reply["info"]))
    finally:
        publisher.close()
