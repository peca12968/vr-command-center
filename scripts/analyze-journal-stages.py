"""Read-only detailed native journal stages for one closed admission fixture."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
publication = load('journal_publication', 'analyze-publication-timing.py')
OPERATIONS = ('Header', 'Frame', 'Ack', 'Complete', 'Seal', 'Pending', 'LastSequence', 'ThroughWorldSequence', 'AcknowledgedSequence', 'CompleteState', 'SealedState', 'Dispose')
STAGES = ('GateEnter', 'Write', 'DurableFlush')


def merged(intervals):
    result = []
    for start, end in sorted(intervals):
        if end <= start: continue
        if result and start <= result[-1][1]: result[-1] = (result[-1][0], max(end, result[-1][1]))
        else: result.append((start, end))
    return result


def intersection_seconds(left, right):
    left, right = merged(left), merged(right); i = j = 0; count = 0
    while i < len(left) and j < len(right):
        count += max(0, min(left[i][1], right[j][1]) - max(left[i][0], right[j][0]))
        if left[i][1] < right[j][1]: i += 1
        else: j += 1
    return count / publication.SCALE


def correlate(report, parent):
    if report.get('version') != 1 or report.get('source') != 'NativeWindowsWorldJournalStages' or report.get('role') != 'Server' \
        or report.get('complete') is not True or report.get('truncated') is not False or report.get('inFlight') != 0 or report.get('error') \
        or report.get('maximumSeconds') != 90 or report.get('capacity') != 32768:
        raise ValueError('Need complete drained bounded detailed trace')
    frequency = report['frequency']; main = report['mainManagedThreadId']; rows = report['rows']
    if type(frequency) is not int or frequency <= 0 or type(main) is not int or main <= 0 or not 0 < len(rows) <= 32768:
        raise ValueError('Invalid trace counters')
    for key in ('startedTimestamp', 'startedUtcTicks', 'stoppedTimestamp', 'stoppedUtcTicks'):
        if type(report[key]) is not int or report[key] <= 0: raise ValueError('Missing native clock anchor')
    if report['stoppedTimestamp'] < report['startedTimestamp']: raise ValueError('Native clock rewound')
    start, end = publication.ticks(parent['windowStartUtc']), publication.ticks(parent['windowEndUtc'])
    groups = {}; all_rows = []; clock_error = 0.; failed = 0
    for row in rows:
        for key in ('stage', 'operation', 'managedThreadId', 'sequence', 'startedTimestamp', 'endedTimestamp', 'startedUtcTicks', 'endedUtcTicks'):
            if type(row[key]) is not int: raise ValueError('Invalid detailed row integer')
        if not 0 <= row['stage'] <= 2 or not 0 <= row['operation'] < len(OPERATIONS) or row['managedThreadId'] <= 0 or row['sequence'] < 0 \
            or not report['startedTimestamp'] <= row['startedTimestamp'] <= row['endedTimestamp'] or row['startedTimestamp'] > report['stoppedTimestamp'] \
            or row['startedUtcTicks'] <= 0 or row['endedUtcTicks'] <= 0 or type(row['succeeded']) is not bool:
            raise ValueError('Invalid detailed timing boundary')
        duration = (row['endedTimestamp'] - row['startedTimestamp']) / frequency
        for prefix in ('started', 'ended'):
            clock_error = max(clock_error, abs((row[prefix + 'UtcTicks'] - report['startedUtcTicks']) / publication.SCALE - (row[prefix + 'Timestamp'] - report['startedTimestamp']) / frequency))
        failed += not row['succeeded']; role = 'Main' if row['managedThreadId'] == main else 'Background'
        key = role + '/' + OPERATIONS[row['operation']] + '/' + STAGES[row['stage']]
        group = groups.setdefault(key, {'count': 0, 'maximumSeconds': 0., 'failed': 0, 'intervals': [], 'windowSamples': 0})
        group['count'] += 1; group['maximumSeconds'] = max(group['maximumSeconds'], duration); group['failed'] += not row['succeeded']
        # UTC locates the endpoint; Stopwatch measures duration. Raw UTC pairs
        # can quantize a sub-millisecond call to zero or an entire clock step.
        projected_start = row['endedUtcTicks'] - round(duration * publication.SCALE)
        interval = (max(start, projected_start), min(end, row['endedUtcTicks']))
        if projected_start <= end and row['endedUtcTicks'] >= start: group['windowSamples'] += 1
        if interval[1] > interval[0]: group['intervals'].append(interval)
        all_rows.append((role, row['stage'], row['operation'], interval))
    clock_error = max(clock_error, abs((report['stoppedUtcTicks'] - report['startedUtcTicks']) / publication.SCALE - (report['stoppedTimestamp'] - report['startedTimestamp']) / frequency))
    covered = report['startedUtcTicks'] <= start <= end <= report['stoppedUtcTicks']
    usable = covered and clock_error <= .05 and parent['utcCorrelationUsable']
    waits = [i for role, stage, operation, i in all_rows if role == 'Main' and stage == 0]
    acks = [i for role, stage, operation, i in all_rows if role == 'Background' and stage == 2 and operation == 2]
    frames = [i for role, stage, operation, i in all_rows if role == 'Main' and stage == 2 and operation == 1]
    for group in groups.values():
        intervals = group.pop('intervals'); group['windowSamples'] = group['windowSamples'] if usable else None
        group['windowUnionSeconds'] = publication.union_seconds(intervals) if usable else None
    return {'version': 1, 'rows': len(rows), 'failedOperations': failed, 'windowCovered': covered,
        'maximumClockDisagreementSeconds': clock_error, 'clockToleranceSeconds': .05, 'utcCorrelationUsable': usable,
        'mainGateEnterWindowSeconds': publication.union_seconds(waits) if usable else None,
        'backgroundAckFlushWindowSeconds': publication.union_seconds(acks) if usable else None,
        'mainFrameFlushWindowSeconds': publication.union_seconds(frames) if usable else None,
        'mainWaitOverlapsBackgroundAckFlushSeconds': intersection_seconds(waits, acks) if usable else None,
        'groups': groups, 'causalRootProven': False,
        'scope': 'UTC endpoint minus Stopwatch duration locates intervals; raw UTC pairs are not durations. GateEnter brackets Monitor.Enter including instrumentation overhead. Write includes hashing / BinaryWriter.Flush; DurableFlush brackets FileStream.Flush(true), not physical-drive-only time. Managed thread IDs, not OS IDs. Frame file rows have sequence 0 (unknown). Overlapping roles / stages are not additive; no WS or API timing.'}


def analyze(directory):
    directory = Path(directory).resolve(); parent = publication.analyze(directory); stage = publication.read(directory / 'stage.json')
    path = Path(stage['journalTraceDirectory']).resolve()
    if path != Path(stage['runtimeDirectory']).resolve() / 'journal-trace': raise ValueError('Detailed trace outside this runtime')
    report = publication.read(path / 'report.json', 32 * 1024 * 1024); result = correlate(report, parent)
    result['publication'] = parent
    with (path / 'report.json').open('rb') as source: result['traceSha256'] = hashlib.file_digest(source, 'sha256').hexdigest()
    digest = hashlib.sha256()
    for name in ('analyze-journal-stages.py', 'analyze-publication-timing.py', 'analyze-world-journal.py'):
        digest.update(name.encode()); digest.update((ROOT / name).read_bytes())
    result['analysisFingerprint'] = digest.hexdigest(); return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run_directory', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = analyze(args.run_directory)
    if args.output:
        with args.output.open('x', encoding='utf-8') as output: output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
