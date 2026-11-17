"""Connect to a Windows process's local Kestrel socket."""

import ctypes
from http.client import HTTPConnection
import os
import select
import socket
from socketserver import BaseRequestHandler, ThreadingTCPServer
import struct
import threading

from windows_firewall import require_silent_windows_launch


def unix_address(path):
    # Windows socket.py may omit AF_UNIX even when Winsock supports sockaddr_un.
    encoded = os.fsencode(path)
    if not path.is_absolute() or len(encoded) > 107 or b'\0' in encoded:
        raise ValueError('Use an absolute Windows IPC path of at most 107 bytes')
    return struct.pack('<H', 1) + encoded.ljust(108, b'\0')


def connect_unix(address):
    winsock = ctypes.WinDLL('Ws2_32')
    winsock.connect.argtypes = (ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int)
    sock = socket.socket(1, socket.SOCK_STREAM)
    try:
        if winsock.connect(sock.fileno(), ctypes.c_char_p(address), len(address)):
            raise OSError(winsock.WSAGetLastError(), 'Could not connect to the owned Windows IPC socket')
        sock.settimeout(5)
        return sock
    except BaseException:
        sock.close()
        raise


class UnixHttpConnection(HTTPConnection):
    def __init__(self, address):
        super().__init__('localhost')
        self.address = address

    def connect(self):
        self.sock = connect_unix(self.address)


class RelayHandler(BaseRequestHandler):
    def handle(self):
        try:
            with connect_unix(self.server.address) as upstream:
                self.request.settimeout(5)
                readers = {self.request: upstream, upstream: self.request}
                while readers and not self.server.ending.is_set():
                    readable, _, _ = select.select(list(readers), [], [], .25)
                    for source in readable:
                        chunk = source.recv(65536)
                        if chunk:
                            readers[source].sendall(chunk)
                        else:
                            readers.pop(source).shutdown(socket.SHUT_WR)
        except OSError:
            pass  # The original connection closes when a client or the owned API stops.


class LoopbackIpcRelay(ThreadingTCPServer):
    request_queue_size = 16

    def __init__(self, address, executable):
        require_silent_windows_launch(executable)
        self.address = address
        self.ending = threading.Event()
        super().__init__(('127.0.0.1', 0), RelayHandler)
        self.thread = threading.Thread(target=self.serve_forever, name='Windows IPC loopback', daemon=True)
        self.thread.start()

    def close(self):
        self.ending.set()
        self.shutdown()
        self.server_close()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError('Windows IPC loopback relay did not stop')
