"""Read a CLOSED VRWORLD1 file without opening SQLite or acquiring a writer.

Checks binary envelope / SHA256 / sequence boundaries, not full gameplay validation.
Outputs bounded metadata only. Never repairs, truncates, acknowledges or publishes.
"""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import struct


def utc(value):
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None: raise ValueError('Capture / response timestamp needs an explicit UTC offset')
    return result


def analyze(path, accepted_sequence=None, response_utc=None, *, expected_session=None, expected_header=None, on_running_frame=None,
            on_packet=None):
    if accepted_sequence is not None and (type(accepted_sequence) is not int or accepted_sequence < 1): raise ValueError('Positive accepted Begin sequence required')
    if response_utc and accepted_sequence is None: raise ValueError('Response timing requires a known accepted Begin boundary')
    response = utc(response_utc) if response_utc else None
    digest = hashlib.sha256(); counts = {}; header = None; capture_start = None
    last = None; first = None; acknowledged = 0; complete = sealed = False
    last_combat = None; running_frames = 0
    transitions = []; transition_count = 0; previous_state = None
    peak_unacknowledged = 0; peak_boundary = None
    with Path(path).open('rb') as source:
        before = os.fstat(source.fileno())
        def read(count):
            data = source.read(count); digest.update(data)
            if len(data) != count: raise ValueError('Torn world journal; no bytes discarded')
            return data
        if read(8) != b'VRWORLD1': raise ValueError('Unknown world journal format')
        while source.tell() < before.st_size:
            record_offset = source.tell()
            count, = struct.unpack('<i', read(4))
            if not 1 <= count <= 1024 * 1024 - 128: raise ValueError('Invalid world record length')
            payload = read(count)
            if hashlib.sha256(payload).digest() != read(32): raise ValueError('World journal checksum mismatch')
            tag = payload[0]; counts[str(tag)] = counts.get(str(tag), 0) + 1
            if header is None and tag != 0: raise ValueError('Header must be first')
            if tag == 0:
                if header is not None: raise ValueError('Duplicate world header')
                header = json.loads(payload[1:]); capture_start = utc(header['captureStartedAtUtc']) if header.get('captureStartedAtUtc') else None
                if expected_session is not None and header.get('sessionId') != expected_session: raise ValueError('Journal belongs to a different session')
                if expected_header is not None:
                    observed_header = {key: header.get(key) for key in expected_header}
                    if json.dumps(observed_header, sort_keys=True) != json.dumps(expected_header, sort_keys=True):
                        raise ValueError('Journal header differs from the expected source')
            elif tag == 1:
                packet = json.loads(payload[1:]); frame = packet['frame']
                if complete or last and last['phase'] == 'Ended': raise ValueError('Frame after terminal boundary')
                if packet['sequence'] != (last['worldSequence'] + 1 if last else 1): raise ValueError('Noncontiguous world sequence')
                if last and (packet['observedSequence'] < last['observedSequence'] or packet['elapsedMilliseconds'] < last['elapsedMilliseconds']): raise ValueError('World observation rewound')
                if packet['sequence'] > 1000000: raise ValueError('World frame limit exceeded')
                captured = capture_start + timedelta(milliseconds=packet['elapsedMilliseconds']) if capture_start else None
                row = {'worldSequence': packet['sequence'], 'observedSequence': packet['observedSequence'],
                    'phase': frame['phase'], 'tick': frame['tick'], 'suspended': packet['suspended'],
                    'elapsedMilliseconds': packet['elapsedMilliseconds'], 'capturedAtUtc': captured.isoformat() if captured else None}
                state = (row['phase'], row['observedSequence'], row['suspended'])
                if state != previous_state:
                    transition_count += 1
                    if len(transitions) < 256: transitions.append(row)
                    previous_state = state
                if accepted_sequence is not None and first is None and row['observedSequence'] >= accepted_sequence and row['phase'] == 'Running' and row['tick'] > 0 and not row['suspended']:
                    first = row
                if on_packet is not None:
                    on_packet(packet)
                if row['phase'] == 'Running' and row['tick'] > 0 and row['suspended'] is False:
                    running_frames += 1
                    if on_running_frame is not None:
                        on_running_frame(frame)
                last = row
                last_combat = packet.get('throughCombatSequence')
            elif tag in (2, 3, 4):
                if len(payload) != 9 or last is None: raise ValueError('Invalid receipt size / boundary')
                sequence, = struct.unpack('<q', payload[1:])
                if tag == 2:
                    if sealed or sequence != acknowledged + 1 or sequence > last['worldSequence']: raise ValueError('Invalid durable receipt sequence')
                    acknowledged = sequence
                elif tag == 3:
                    if complete or last['phase'] != 'Ended' or sequence != last['worldSequence']: raise ValueError('Invalid completion intent')
                    complete = True
                else:
                    if not complete or sealed or sequence != acknowledged or sequence != last['worldSequence']: raise ValueError('Invalid final receipt')
                    sealed = True
            else: raise ValueError('Unknown world record tag')
            pending = (last['worldSequence'] if last else 0) - acknowledged
            if pending > peak_unacknowledged:
                peak_unacknowledged = pending
                peak_boundary = {'worldSequence': last['worldSequence'], 'acknowledgedSequence': acknowledged,
                    'afterRecordTag': tag, 'recordOffsetBytes': record_offset}
        after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns): raise ValueError('Journal changed during read; stop its writer first')
    if header is None: raise ValueError('Missing world header')
    return {'version': 1, 'bytes': before.st_size, 'sha256': digest.hexdigest(), 'records': counts,
        'acceptedSequence': accepted_sequence, 'applicationBoundaryKnown': accepted_sequence is not None,
        'captureStartedAtUtc': capture_start.isoformat() if capture_start else None,
        'responseObservedAtUtc': response_utc, 'firstApplied': first, 'lastFrame': last, 'acknowledgedSequence': acknowledged,
        'lastCombatSequence': last_combat, 'runningFrames': running_frames,
        'unacknowledgedFrames': (last['worldSequence'] if last else 0) - acknowledged, 'complete': complete, 'sealed': sealed,
        'peakUnacknowledgedFrames': peak_unacknowledged, 'firstPeakBoundary': peak_boundary,
        'firstAppliedCaptureSecondsAfterResponse': (utc(first['capturedAtUtc']) - response).total_seconds() if first and first['capturedAtUtc'] and response else None,
        'transitions': transitions, 'transitionCount': transition_count, 'transitionsTruncated': transition_count > len(transitions),
        'scope': 'Closed journal binary checksum / sequence metadata only. Backlog counts persisted frames without local durable receipts; not buffered writer queue depth, wall-clock duration, API rejection or network latency. Unknown Begin stays unknown. Not full gameplay validation or a storage root-cause verdict.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path); parser.add_argument('--accepted-sequence', type=int, help='Exact accepted Begin sequence; omit for persistence-only analysis without inferred application timing')
    parser.add_argument('--response-utc'); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); report = analyze(args.journal, args.accepted_sequence, args.response_utc)
    if args.output:
        with args.output.open('x', encoding='utf-8') as target: target.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
