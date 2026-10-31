"""Bounded opaque UDP gate for one owned loopback client; never records payloads."""
from collections import deque
import socket
import threading
import time


class LoopbackGate:
    def __init__(self, server_port, should_hold, *, mode='delay', pass_small_bytes=0, max_hold_seconds=8, max_packets=1024, max_bytes=2 * 1024 * 1024):
        if mode not in ('delay', 'drop') or not 0 <= pass_small_bytes <= 64 or not 0 < server_port < 65536 or not 0 < max_hold_seconds <= 40 or not 0 < max_packets <= 1024 or not 0 < max_bytes <= 2 * 1024 * 1024:
            raise ValueError('Gate bounds are invalid')
        self.server = ('127.0.0.1', server_port); self.client = None; self.should_hold = should_hold
        self.mode = mode; self.pass_small_bytes = pass_small_bytes; self.max_hold_seconds = max_hold_seconds; self.max_packets = max_packets; self.max_bytes = max_bytes
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1', 0)); self.port = self.socket.getsockname()[1]; self.socket.settimeout(.02)
        self.stop_event = threading.Event(); self.release_event = threading.Event(); self.held = threading.Event()
        self.queue = deque(); self.queued_bytes = 0; self.started = None; self.released_at = None; self.release_reason = None; self.error = None
        self.counts = {'upstream': 0, 'downstream': 0, 'held': 0, 'released': 0, 'dropped': 0, 'smallPassed':0, 'foreignDropped': 0, 'connectionResets':0, 'peakPackets': 0, 'peakBytes': 0}
        self.thread = threading.Thread(target=self._run, name='owned-loopback-gate', daemon=True)
    def start(self): self.thread.start(); return self
    def release(self): self.release_event.set()
    def _flush(self, reason):
        self.release_reason = reason
        self.released_at = time.monotonic()
        while self.queue:
            data = self.queue.popleft(); self.queued_bytes -= len(data)
            self.socket.sendto(data, self.client); self.counts['released'] += 1
    def _run(self):
        deadline = time.monotonic() + 90
        try:
            while not self.stop_event.is_set() and time.monotonic() < deadline:
                if self.started is not None and self.release_reason is None:
                    if self.release_event.is_set(): self._flush('requested')
                    elif time.monotonic() - self.started >= self.max_hold_seconds: self._flush('holdLimit')
                try: data, sender = self.socket.recvfrom(65536)
                except socket.timeout: continue
                except ConnectionResetError: self.counts['connectionResets'] += 1; continue
                if sender != self.server:
                    if sender[0] != '127.0.0.1' or (self.client is not None and sender != self.client):
                        self.counts['foreignDropped'] += 1; continue
                    self.client = sender; self.socket.sendto(data, self.server); self.counts['upstream'] += 1; continue
                if self.client is None: self.counts['foreignDropped'] += 1; continue
                if self.started is None and not self.release_event.is_set() and self.should_hold():
                    self.started = time.monotonic(); self.held.set()
                if self.started is not None and self.release_reason is None:
                    if self.mode == 'drop':
                        if self.pass_small_bytes and len(data)<=self.pass_small_bytes:
                            self.socket.sendto(data,self.client); self.counts['smallPassed']+=1; continue
                        self.counts['dropped'] += 1; continue
                    if len(self.queue) >= self.max_packets or self.queued_bytes + len(data) > self.max_bytes:
                        self._flush('queueLimit')
                    else:
                        self.queue.append(data); self.queued_bytes += len(data); self.counts['held'] += 1
                        self.counts['peakPackets'] = max(self.counts['peakPackets'], len(self.queue))
                        self.counts['peakBytes'] = max(self.counts['peakBytes'], self.queued_bytes); continue
                self.socket.sendto(data, self.client); self.counts['downstream'] += 1
        except OSError as error:
            if not self.stop_event.is_set(): self.error = repr(error)
        except Exception as error: self.error = repr(error)
        finally: self.socket.close()
    def close(self):
        self.stop_event.set(); self.thread.join(timeout=2)
        if self.thread.is_alive(): raise RuntimeError('Owned UDP gate did not stop')
        if self.started is not None and self.released_at is None:
            self.release_reason='stopped'; self.released_at=time.monotonic()
        self.queue.clear(); self.queued_bytes=0
    def report(self):
        return {**self.counts, 'mode':self.mode, 'passSmallBytes':self.pass_small_bytes, 'releaseReason': self.release_reason, 'holdSeconds': None if self.started is None else (self.released_at if self.released_at is not None else time.monotonic()) - self.started,
                'error': self.error, 'threadStopped': not self.thread.is_alive(), 'payloadsRecorded': False}
