"""Bounded loopback-only fault proxy for one owned Unity server / session.

HTTP bodies and credentials are forwarded in memory, never recorded. WebSocket
bytes are opaque. Only explicitly selected session routes / publication are blocked.
"""
import http.client
from contextlib import closing
import http.server
import select
import socket
import threading
import time
from urllib.parse import urlsplit
from uuid import UUID


class _Server(http.server.ThreadingHTTPServer):
    # ThreadingMixIn.server_close joins every request handler before evidence is final.
    daemon_threads = False
    block_on_close = True
    def process_request(self, request, address):
        if not self.owner.slots.acquire(False):
            request.close(); self.owner.bump('capacityRejected'); return
        try: super().process_request(request, address)
        except BaseException: self.owner.slots.release(); raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.owner.slots.release()

    def handle_error(self, request, address):
        self.owner.bump('handlerErrors')  # Never log request / auth / body.


class VenueHttpGate:
    def __init__(self, upstream, session, *, max_block_seconds=20, maximum_seconds=240):
        target = urlsplit(upstream)
        if target.scheme != 'http' or target.hostname != '127.0.0.1' or not target.port or target.port == 5080 or target.path not in ('', '/') or target.query or target.fragment or target.username or target.password:
            raise ValueError('Gate requires its own plain loopback upstream, never preview 5080')
        self.session = str(UUID(session)); self.prefix = '/api/sessions/' + self.session
        if not 0 < max_block_seconds <= 20 or not 0 < maximum_seconds <= 240:
            raise ValueError('Fault duration must be bounded')
        self.upstream = ('127.0.0.1', target.port); self.max_block_seconds = max_block_seconds
        self.maximum_seconds = maximum_seconds; self.lock = threading.RLock(); self.slots = threading.BoundedSemaphore(8)
        self.mode = None; self.block_started = None; self.block_history = []; self.tunnels = set(); self.stop = threading.Event()
        self.counts = dict.fromkeys(['managementBlocked', 'publicationBlocked', 'combatSealBlocked', 'statisticsBlocked', 'tunnelsClosed', 'httpForwarded', 'webSockets', 'capacityRejected', 'handlerErrors', 'routeRejected'], 0)
        self.limits_triggered = []; self.server = _Server(('127.0.0.1', 0), _Handler); self.server.owner = self
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        self.watchdog = threading.Thread(target=self._watch, daemon=True)

    def bump(self, key):
        with self.lock: self.counts[key] += 1

    def start(self):
        self.started = time.monotonic(); self.thread.start(); self.watchdog.start(); return self

    def block(self, mode):
        if mode not in ('management', 'publication', 'combat-seal', 'statistics'): raise ValueError('Unknown fault mode')
        with self.lock:
            if self.mode is not None: raise ValueError('Release the current fault first')
            self.mode = mode; self.block_started = time.monotonic()
            tunnels = list(self.tunnels) if mode == 'publication' else []
        for pair in tunnels:
            self.bump('tunnelsClosed')
            for stream in pair:
                try: stream.shutdown(socket.SHUT_RDWR)
                except OSError: pass

    def release(self, reason='requested'):
        with self.lock:
            if self.mode is None: return
            self.block_history.append({'mode': self.mode, 'seconds': time.monotonic() - self.block_started, 'releaseReason': reason})
            self.mode = None; self.block_started = None

    def blocked(self, mode):
        with self.lock: return self.mode == mode

    def allowed(self, method, path):
        return (method == 'GET' and path in (self.prefix, self.prefix + '/statistics')) or (method == 'POST' and path in (
            '/api/player-tickets/validate', self.prefix + '/combat-stream', self.prefix + '/combat-stream/batch', self.prefix + '/combat-stream/seal'))

    def blocked_http(self, method, path):
        if method == 'GET' and path == self.prefix and self.blocked('management'): return 'managementBlocked'
        if method == 'POST' and path == self.prefix + '/combat-stream/seal' and self.blocked('combat-seal'): return 'combatSealBlocked'
        if method == 'GET' and path == self.prefix + '/statistics' and self.blocked('statistics'): return 'statisticsBlocked'
        return None

    def _watch(self):
        while not self.stop.wait(.02):
            with self.lock:
                if self.block_started is not None and time.monotonic() - self.block_started >= self.max_block_seconds:
                    self.limits_triggered.append('blockLimit'); self.release('blockLimit')
            if time.monotonic() - self.started >= self.maximum_seconds:
                with self.lock: self.limits_triggered.append('lifetimeLimit')
                self.release('lifetimeLimit'); self.server.shutdown(); return

    def snapshot(self):
        with self.lock: return {'counts': dict(self.counts), 'faults': list(self.block_history), 'limitsTriggered': list(self.limits_triggered), 'mode': self.mode, 'activeTunnels': len(self.tunnels)}

    def close(self):
        self.release('cleanup'); self.stop.set()
        with self.lock: tunnels = list(self.tunnels)
        for pair in tunnels:
            for stream in pair:
                try: stream.shutdown(socket.SHUT_RDWR)
                except OSError: pass
        self.server.shutdown(); self.server.server_close(); self.thread.join(2); self.watchdog.join(2)
        if self.thread.is_alive() or self.watchdog.is_alive(): raise RuntimeError('Owned fault proxy did not stop')


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args): pass
    def do_GET(self): self.forward()
    def do_POST(self): self.forward()

    def reject(self, status):
        self.send_response(status); self.send_header('Content-Length', '0'); self.send_header('Connection', 'close'); self.end_headers(); self.close_connection = True

    def forward(self):
        gate = self.server.owner
        self.connection.settimeout(6)
        if self.path == gate.prefix + '/world/publish' and self.command == 'GET' and self.headers.get('Upgrade', '').lower() == 'websocket':
            if gate.blocked('publication'):
                gate.bump('publicationBlocked'); return self.reject(503)
            return self.tunnel()
        if not gate.allowed(self.command, self.path):
            gate.bump('routeRejected'); return self.reject(403)
        blocked = gate.blocked_http(self.command, self.path)
        if blocked:
            gate.bump(blocked); return self.reject(503)
        if self.headers.get('Transfer-Encoding'): return self.reject(400)
        try: size = int(self.headers.get('Content-Length', '0'))
        except ValueError: return self.reject(400)
        if not 0 <= size <= 1024 * 1024: return self.reject(413)
        body = self.rfile.read(size)
        if len(body) != size: return self.reject(400)
        headers = {key: value for key, value in self.headers.items() if key.lower() not in ('host', 'connection', 'proxy-connection')}
        headers['Connection'] = 'close'
        try:
            with closing(http.client.HTTPConnection(*gate.upstream, timeout=5)) as upstream:
                upstream.request(self.command, self.path, body=body or None, headers=headers)
                response = upstream.getresponse(); payload = response.read(2 * 1024 * 1024 + 1)
                if len(payload) > 2 * 1024 * 1024: return self.reject(502)
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in ('content-length', 'transfer-encoding', 'connection', 'server', 'date'): self.send_header(key, value)
                self.send_header('Content-Length', str(len(payload))); self.send_header('Connection', 'close'); self.end_headers()
                self.wfile.write(payload); gate.bump('httpForwarded')
        except (OSError, http.client.HTTPException): self.reject(502)
        finally: self.close_connection = True

    def tunnel(self):
        gate = self.server.owner; self.close_connection = True
        try:
            with socket.create_connection(gate.upstream, timeout=5) as upstream:
                pair = (self.connection, upstream)
                with gate.lock:
                    if gate.mode == 'publication': gate.bump('publicationBlocked'); return self.reject(503)
                    gate.tunnels.add(pair)
                try:
                    header = self.command + ' ' + self.path + ' HTTP/1.1\r\n' + ''.join(key + ': ' + value + '\r\n' for key, value in self.headers.items()) + '\r\n'
                    upstream.sendall(header.encode('latin-1')); gate.bump('webSockets')
                    deadline = gate.started + gate.maximum_seconds
                    while not gate.stop.is_set() and not gate.blocked('publication') and time.monotonic() < deadline:
                        ready, _, _ = select.select(pair, [], [], .05)
                        for source in ready:
                            data = source.recv(65536)
                            if not data: return
                            (upstream if source is self.connection else self.connection).sendall(data)
                finally:
                    with gate.lock: gate.tunnels.discard(pair)
        except OSError: pass
