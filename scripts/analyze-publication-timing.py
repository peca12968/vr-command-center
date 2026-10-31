"""Correlate an owned CLOSED admission run with the existing native timing trace.

No gameplay changes, SQLite, payload output, inferred fsync / WS / API timing.
Nested WorldCapture / WorldJournal spans are reported separately, never added.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path

SCALE = 10000000
EPOCH = datetime(1, 1, 1, tzinfo=timezone.utc)


def ticks(value):
    date = datetime.fromisoformat(value)
    if date.utcoffset() is None: raise ValueError('UTC offset required')
    delta = date - EPOCH
    return (delta.days * 86400 + delta.seconds) * SCALE + delta.microseconds * 10


def finite(value): return type(value) in (int, float) and math.isfinite(value)


def union_seconds(intervals):
    merged = []
    for start, end in sorted(intervals):
        if end <= start: continue
        if merged and start <= merged[-1][1]: merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else: merged.append((start, end))
    return sum(end - start for start, end in merged) / SCALE


def correlate(trace, witness):
    if trace.get('schemaVersion') != 1 or trace.get('source') != 'NativeWindowsMonotonicTiming' or trace.get('role') != 'Server' \
        or trace.get('complete') is not True or trace.get('truncated') is not False or trace.get('error') \
        or trace.get('maximumSeconds') != 240 or trace.get('capacity') != 32768:
        raise ValueError('Need complete bounded native server timing evidence')
    rows = trace['rows']; samples = witness['samples']
    if not 0 < len(rows) <= 32768 or witness.get('version') != 1 or witness.get('truncated') is not False \
        or not 0 < len(samples) <= 256 or witness.get('totalSamples') != len(samples): raise ValueError('Incomplete / truncated timing window')
    if type(witness.get('acceptedSequence')) is not int or witness['acceptedSequence'] < 1: raise ValueError('Invalid accepted boundary')
    if not finite(trace['endedSeconds']) or not 0 < trace['endedSeconds'] <= 240: raise ValueError('Invalid trace lifetime')
    start = ticks(witness['responseObservedAtUtc']); end = ticks(samples[-1]['receivedAtUtc'])
    if end < start: raise ValueError('Receiver window rewound')
    clock_error = 0.; previous = -1.; previous_receive = start
    for sample in samples:
        receive = ticks(sample['receivedAtUtc'])
        if receive < previous_receive or not finite(sample['secondsAfterResponse']) or sample['secondsAfterResponse'] < 0: raise ValueError('Invalid receiver clock')
        clock_error = max(clock_error, abs((receive - start) / SCALE - sample['secondsAfterResponse']))
        previous_receive = receive
    first = rows[0]
    for row in rows:
        if not finite(row['seconds']) or not previous <= row['seconds'] <= trace['endedSeconds'] \
            or type(row['utcTicks']) is not int or row['utcTicks'] <= 0 or not finite(row['durationSeconds']) \
            or not 0 <= row['durationSeconds'] <= row['seconds'] + .005 or not isinstance(row['point'], str) or not 0 < len(row['point']) <= 40:
            raise ValueError('Invalid native trace row')
        clock_error = max(clock_error, abs((row['utcTicks'] - first['utcTicks']) / SCALE - (row['seconds'] - first['seconds'])))
        previous = row['seconds']
    coverage = first['utcTicks'] <= start <= end <= rows[-1]['utcTicks']
    usable = coverage and clock_error <= .05
    points = {}
    for point in ('WorldJournal', 'WorldCapture', 'MainThreadGap'):
        selected = [r for r in rows if r['point'] == point]
        overlapping = [r for r in selected if r['utcTicks'] >= start and r['utcTicks'] - round(r['durationSeconds'] * SCALE) <= end]
        slow = [r for r in overlapping if r['durationSeconds'] >= .1]
        points[point] = {'totalSamples': len(selected), 'windowSamples': len(overlapping) if usable else None,
            'maximumSeconds': max((r['durationSeconds'] for r in selected), default=0),
            'windowMaximumSeconds': max((r['durationSeconds'] for r in overlapping), default=0) if usable else None,
            'windowUnionSeconds': union_seconds((max(start, r['utcTicks'] - round(r['durationSeconds'] * SCALE)), min(end, r['utcTicks'])) for r in overlapping) if usable else None,
            'slowWindowCount': len(slow) if usable else None,
            'earliestSlowWindow': [{'endUtcTicks': r['utcTicks'], 'durationSeconds': r['durationSeconds']} for r in slow[:64]] if usable else [],
            'slowWindowTruncated': len(slow) > 64 if usable else None}
    if not points['WorldJournal']['totalSamples']: raise ValueError('No measured world journal spans')
    return {'version': 1, 'acceptedSequence': witness['acceptedSequence'], 'applicationObservedLive': witness['applicationObserved'],
        'windowStartUtc': witness['responseObservedAtUtc'], 'windowEndUtc': samples[-1]['receivedAtUtc'],
        'windowSeconds': (end - start) / SCALE, 'receiverSamples': len(samples),
        'traceSamples': len(rows), 'traceEndedSeconds': trace['endedSeconds'], 'windowCovered': coverage,
        'maximumClockDisagreementSeconds': clock_error, 'clockToleranceSeconds': .05, 'utcCorrelationUsable': usable,
        'points': points, 'causalRootProven': False,
        'unmeasured': ['Background world ack journal lock / append / flush', 'WebSocket exchange', 'API validation / SQLite / durable receipt'],
        'scope': 'Existing main-thread elapsed spans include lock / serialization / append / flush, not fsync-only or CPU. WorldCapture includes WorldJournal; never sum them. No span-to-world-sequence mapping or original-fault causal verdict.'}


def read(path, limit=1024 * 1024):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit: raise ValueError('Diagnostic JSON exceeds its bound')
    return json.loads(raw)


def analyze(directory):
    directory = Path(directory).resolve(); stage = read(directory / 'stage.json'); cleanup = read(directory / 'cleanup.json')
    if cleanup['remainingTrackedChildren'] or any(p['exitCode'] is None for p in cleanup['processes']): raise ValueError('Stop owned writers before analysis')
    runtime = Path(stage['runtimeDirectory']).resolve(); trace_path = Path(stage['serverTraceDirectory']).resolve()
    if trace_path != runtime / 'server-trace': raise ValueError('Trace is outside this runtime')
    witness = read(directory / 'begin-witness.json'); command = read(directory / 'control-Begin.json')
    if command['session']['sequence'] != witness['acceptedSequence']: raise ValueError('Begin boundary differs')
    trace = read(trace_path / 'report.json', 16 * 1024 * 1024); result = correlate(trace, witness)
    spec = importlib.util.spec_from_file_location('publication_journal', Path(__file__).with_name('analyze-world-journal.py'))
    journal = importlib.util.module_from_spec(spec); spec.loader.exec_module(journal)
    paths = list((runtime / 'telemetry').glob('*.worldlog'))
    if len(paths) != 1: raise ValueError('Need exactly one source journal')
    result['closedJournal'] = journal.analyze(paths[0], witness['acceptedSequence'], witness['responseObservedAtUtc'], expected_session=command['session']['id'])
    result['evidenceSha256'] = {}
    for name, path in [('trace', trace_path / 'report.json'), ('beginWitness', directory / 'begin-witness.json'), ('command', directory / 'control-Begin.json')]:
        with path.open('rb') as source: result['evidenceSha256'][name] = hashlib.file_digest(source, 'sha256').hexdigest()
    digest = hashlib.sha256()
    for name in ('analyze-publication-timing.py', 'analyze-world-journal.py'):
        digest.update(name.encode()); digest.update(Path(__file__).with_name(name).read_bytes())
    result['analysisFingerprint'] = digest.hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run_directory', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); report = analyze(args.run_directory)
    if args.output:
        with args.output.open('x', encoding='utf-8') as target: target.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
