import http.client
from contextlib import closing
import http.server
import importlib.util
from pathlib import Path
import socket
import threading
import time
import unittest
import uuid

spec = importlib.util.spec_from_file_location('venue_http_gate', Path(__file__).resolve().parents[1] / 'scripts/venue_http_gate.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class Upstream(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path.endswith('/statistics') and hasattr(self.server, 'entered'):
            self.server.entered.set(); self.server.release.wait(2)
        if self.headers.get('Upgrade') == 'websocket':
            self.send_response(101); self.send_header('Upgrade', 'websocket'); self.send_header('Connection', 'Upgrade'); self.end_headers()
            self.connection.settimeout(3)
            try:
                while data := self.connection.recv(128): self.connection.sendall(data)
            except OSError: pass
        else: self.reply(b'ordinary response')
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.reply(body + b'|' + self.headers.get('Authorization', '').encode())
    def reply(self, body):
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)


class VenueHttpGateTests(unittest.TestCase):
    def setUp(self):
        self.session = str(uuid.uuid4()); self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        self.server.daemon_threads = True; self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port); self.gates = []
    def tearDown(self):
        for gate in self.gates: gate.close()
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
    def gate(self, **kwargs):
        gate = m.VenueHttpGate(self.base, self.session, **kwargs).start(); self.gates.append(gate); return gate
    def request(self, gate, path='', method='GET', body=None, headers=None):
        with closing(http.client.HTTPConnection('127.0.0.1', gate.server.server_port, timeout=2)) as connection:
            connection.request(method, gate.prefix + path, body, headers or {})
            response = connection.getresponse(); return response.status, response.read()
    def tunnel(self, gate):
        client = socket.create_connection(('127.0.0.1', gate.server.server_port), timeout=2)
        client.sendall(f'GET {gate.prefix}/world/publish HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n'.encode())
        header = b''
        while not header.endswith(b'\r\n\r\n'): header += client.recv(1)
        self.assertIn(b'101', header); return client
    def test_only_owned_plain_loopback_upstream_and_bounded_duration(self):
        for address in ['http://example.com:1234', 'http://127.0.0.1:5080', 'https://127.0.0.1:1234', self.base + '/other', self.base + '?query=1', 'http://u:p@127.0.0.1:1234']:
            with self.assertRaises(ValueError): m.VenueHttpGate(address, self.session)
        for kwargs in [{'max_block_seconds': 21}, {'maximum_seconds': 241}]:
            with self.assertRaises(ValueError): m.VenueHttpGate(self.base, self.session, **kwargs)
    def test_management_fault_does_not_block_other_http_or_lose_auth_body(self):
        gate = self.gate(); self.assertEqual((200, b'ordinary response'), self.request(gate))
        gate.block('management'); self.assertEqual(503, self.request(gate)[0])
        self.assertEqual((200, b'own fixture body|Bearer unit-test-only'), self.request(gate, '/combat-stream/batch', 'POST', b'own fixture body', {'Authorization': 'Bearer unit-test-only'}))
        gate.release(); self.assertEqual(200, self.request(gate)[0]); self.assertEqual(1, gate.snapshot()['counts']['managementBlocked'])
    def test_publication_fault_closes_opaque_tunnel_and_reconnects_after_release(self):
        gate = self.gate()
        with self.tunnel(gate) as client:
            client.sendall(b'opaque bytes'); self.assertEqual(b'opaque bytes', client.recv(128))
            gate.block('publication')
            try: self.assertEqual(b'', client.recv(128))
            except ConnectionResetError: pass
        self.assertEqual(200, self.request(gate)[0])
        self.assertEqual(503, self.request(gate, '/world/publish', headers={'Upgrade': 'websocket'})[0])
        gate.release()
        with self.tunnel(gate) as client:
            client.sendall(b'new bytes'); self.assertEqual(b'new bytes', client.recv(128))
        self.assertEqual(2, gate.snapshot()['counts']['webSockets'])
    def test_other_session_and_unbounded_http_bodies_are_rejected(self):
        gate = self.gate()
        self.assertEqual(403, self.request(gate, '/../' + str(uuid.uuid4()))[0])
        self.assertEqual(413, self.request(gate, '/combat-stream', 'POST', headers={'Content-Length': str(1024 * 1024 + 1)})[0])
        self.assertEqual(400, self.request(gate, '/combat-stream', 'POST', headers={'Transfer-Encoding': 'chunked'})[0])
    def test_automatic_release_is_reported_and_cannot_be_a_successful_fault(self):
        gate = self.gate(max_block_seconds=.06); gate.block('management'); deadline = time.monotonic() + 2
        while not gate.snapshot()['limitsTriggered'] and time.monotonic() < deadline: time.sleep(.01)
        self.assertEqual(['blockLimit'], gate.snapshot()['limitsTriggered']); self.assertIsNone(gate.snapshot()['mode'])
        self.assertEqual('blockLimit', gate.snapshot()['faults'][0]['releaseReason'])
    def test_connection_capacity_is_bounded(self):
        gate = self.gate(); clients = []
        try:
            clients = [self.tunnel(gate) for _ in range(8)]
            with socket.create_connection(('127.0.0.1', gate.server.server_port), timeout=2) as ninth:
                ninth.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
                try: self.assertEqual(b'', ninth.recv(1))
                except ConnectionResetError: pass
            deadline = time.monotonic() + 2
            while not gate.snapshot()['counts']['capacityRejected'] and time.monotonic() < deadline: time.sleep(.005)
            self.assertEqual(1, gate.snapshot()['counts']['capacityRejected'])
        finally:
            for client in clients: client.close()

    def test_lifetime_cap_stops_the_listener_and_marks_the_run_invalid(self):
        gate = self.gate(maximum_seconds=.08); deadline = time.monotonic() + 2
        while gate.thread.is_alive() and time.monotonic() < deadline: time.sleep(.01)
        self.assertFalse(gate.thread.is_alive()); self.assertEqual(['lifetimeLimit'], gate.snapshot()['limitsTriggered'])

    def test_close_waits_for_an_inflight_http_handler(self):
        gate = self.gate(); self.server.entered = threading.Event(); self.server.release = threading.Event(); results = []
        requester = threading.Thread(target=lambda: results.append(self.request(gate, '/statistics')))
        closer = threading.Thread(target=gate.close)
        requester.start(); self.assertTrue(self.server.entered.wait(2)); closer.start()
        try:
            time.sleep(.15); self.assertTrue(closer.is_alive())
        finally: self.server.release.set()
        closer.join(2); requester.join(2)
        self.assertFalse(closer.is_alive()); self.assertFalse(requester.is_alive()); self.assertEqual(200, results[0][0])
        self.gates.remove(gate)  # Already closed and all handlers joined.


if __name__ == '__main__': unittest.main()
