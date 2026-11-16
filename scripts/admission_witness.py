"""Bounded metadata-only Begin application window; never a network-latency verdict."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import time
import hashlib
from pathlib import Path


def observer_fingerprint():
    digest = hashlib.sha256()
    for name in ('check-unity-admission.py', 'admission_witness.py', 'start-desktop-venue.py', 'live_world_frame.py'):
        digest.update(name.encode()); digest.update((Path(__file__).parent / name).read_bytes())
    return digest.hexdigest()


class BeginWitness:
    def __init__(self, sequence, *, limit=256):
        if type(sequence) is not int or sequence < 1 or type(limit) is not int or not 1 <= limit <= 256:
            raise ValueError('Invalid accepted Begin boundary')
        self.sequence = sequence; self.limit = limit; self.started = time.monotonic()
        self.accepted_at = datetime.now(timezone.utc).isoformat(); self.rows = []; self.phases = Counter()
        self.total = 0; self.applied = False; self.truncated = False; self.first = None

    def observe(self, packet, capture_start=None):
        if self.applied: return
        now = datetime.now(timezone.utc); frame = packet['frame']; self.total += 1; self.phases[frame['phase']] += 1
        captured = None if not capture_start else datetime.fromisoformat(capture_start) + timedelta(milliseconds=packet['elapsedMilliseconds'])
        ready = packet['observedSequence'] >= self.sequence and frame['phase'] == 'Running' and frame['tick'] > 0 and not packet['suspended']
        row = {'worldSequence': packet['sequence'], 'observedSequence': packet['observedSequence'], 'phase': frame['phase'], 'tick': frame['tick'],
            'suspended': packet['suspended'], 'elapsedMilliseconds': packet['elapsedMilliseconds'], 'receivedAtUtc': now.isoformat(),
            'capturedAtUtc': captured.isoformat() if captured else None, 'sourceAgeSeconds': (now - captured).total_seconds() if captured else None,
            'secondsAfterResponse': time.monotonic() - self.started, 'applied': ready}
        if len(self.rows) < self.limit: self.rows.append(row)
        else: self.truncated = True
        if ready: self.applied = True; self.first = row

    def snapshot(self):
        return {'version': 1, 'acceptedSequence': self.sequence, 'responseObservedAtUtc': self.accepted_at,
            'applicationObserved': self.applied, 'firstApplied': self.first, 'totalSamples': self.total, 'phaseCounts': dict(self.phases),
            'truncated': self.truncated, 'samples': self.rows, 'scope': 'Receiver observation after Begin response; includes polling / persistence / publication, not RTT or source internal timing'}
