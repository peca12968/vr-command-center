"""Read closed sparse long-run diagnostics. No SQLite, credentials or pose data.

Same-host UTC joins require stable clocks. CPU is the sampled Unity calling
thread over a whole Update-to-Update bracket, not a selected engine node.
"""
import argparse
from datetime import datetime
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('continuity_loop_analysis', ROOT / 'scripts/analyze-pose-input.py')
legacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
SCALE = 10_000_000
EPOCH = 621355968000000000


def number(value, minimum=0):
    if type(value) not in (float, int) or not math.isfinite(value) or value < minimum: raise ValueError('Invalid diagnostic number')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum: raise ValueError('Invalid diagnostic integer')
    return value


def validate(report, role, loop_expected):
    if report['version'] != 1 or report['source'] != 'NativeWindowsSparsePoseContinuity' or report['role'] != role \
        or report['complete'] is not True or report['truncated'] is not False or report['error'] or report['stopReason'] != 'Explicit local diagnostic stop':
        raise ValueError('Incomplete sparse continuity report')
    if report['maximumSeconds'] != 1200 or report['streamCapacity'] != 256 or report['gapCapacity'] != 4096 \
        or not 0 < number(report['endedSeconds']) < 1200 or integer(report['mainThreadSamples']) < 1 or integer(report['mainThreadId']) < 1:
        raise ValueError('Invalid sparse diagnostic bounds')
    for key, bound in [('streams', 256), ('gaps', 4096), ('bodies', 4096), ('threadWindows', 4096)]:
        if not isinstance(report[key], list) or len(report[key]) > bound: raise ValueError('Diagnostic array exceeds its declared bound')
    clocks = [number(report['maximumClockStepSeconds'])]; identities = set(); streams = {}
    for stream in report['streams']:
        key = (stream['point'], integer(stream['connection']), integer(stream['source']))
        if key in identities or not isinstance(key[0], str) or not 0 < len(key[0]) <= 40 or key[2] > 255 or integer(stream['count']) < 1:
            raise ValueError('Invalid or repeated diagnostic stream')
        identities.add(key)
        streams[key] = stream
        a, b = number(stream['firstSeconds']), number(stream['lastSeconds'])
        if not a <= b <= report['endedSeconds'] or integer(stream['firstUtcTicks']) < 1 or integer(stream['lastUtcTicks']) < stream['firstUtcTicks']:
            raise ValueError('Invalid stream clock coverage')
        clocks.append(abs((stream['lastUtcTicks'] - stream['firstUtcTicks']) / SCALE - (b - a)))
        number(stream['maximumGapSeconds']); number(stream['maximumDurationSeconds'])
    for gap in report['gaps']:
        key = (gap['point'], integer(gap['connection']), integer(gap['source']))
        if key not in identities: raise ValueError('Gap has no aggregate stream')
        a, b = number(gap['fromSeconds']), number(gap['toSeconds'])
        stream = streams[key]
        if not stream['firstSeconds'] <= a <= b <= stream['lastSeconds'] or b - a > stream['maximumGapSeconds'] + 1e-8 or number(gap['durationSeconds']) > stream['maximumDurationSeconds'] + 1e-8:
            raise ValueError('Gap disagrees with aggregate bounds')
        if not a <= b <= report['endedSeconds'] or integer(gap['fromFrame']) > integer(gap['toFrame']) or not (b - a > .2 or number(gap['durationSeconds']) > .2):
            raise ValueError('Invalid sparse gap')
        if integer(gap['fromUtcTicks']) > integer(gap['toUtcTicks']): raise ValueError('UTC gap rewound')
        clocks.append(abs((gap['toUtcTicks'] - gap['fromUtcTicks']) / SCALE - (b - a)))
    for body in report['bodies']:
        integer(body['connection']); integer(body['frame']); integer(body['utcTicks'], 1)
        if type(body['connected']) is not bool or not 0 <= number(body['seconds']) <= report['endedSeconds'] or not (number(body['poseAgeSeconds'], -1) == -1 or body['poseAgeSeconds'] >= 0):
            raise ValueError('Invalid body change')
    windows = []
    for window in report['threadWindows']:
        before, after = window['before'], window['after']
        for sample in (before, after):
            if integer(sample['threadId'], 1) != report['mainThreadId'] or not 0 <= number(sample['fromSeconds']) <= number(sample['toSeconds']) <= report['endedSeconds']:
                raise ValueError('Main-thread sample identity / bracket differs')
            if integer(sample['fromUtcTicks'], 1) > integer(sample['toUtcTicks'], 1): raise ValueError('Thread query UTC rewound')
            integer(sample['creationTime'], 1)
            for key in ('kernel100ns', 'user100ns', 'cycles'): integer(sample[key])
        if before['creationTime'] != after['creationTime'] or after['fromSeconds'] < before['toSeconds'] or after['fromSeconds'] - before['toSeconds'] <= .2 \
            or any(after[k] < before[k] for k in ('kernel100ns', 'user100ns', 'cycles')): raise ValueError('Thread counter identity / monotonicity differs')
        clocks.append(abs((after['fromUtcTicks'] - before['toUtcTicks']) / SCALE - (after['fromSeconds'] - before['toSeconds'])))
        windows.append({'fromUtcTicks': before['fromUtcTicks'], 'toUtcTicks': after['toUtcTicks'],
            'wallSecondsIncludingQueries': after['toSeconds'] - before['fromSeconds'],
            'mainThreadCpuSeconds': (after['kernel100ns'] - before['kernel100ns'] + after['user100ns'] - before['user100ns']) / SCALE,
            'mainThreadCycleDelta': after['cycles'] - before['cycles'], 'threadId': after['threadId']})
    valid = max(clocks, default=0) < .05
    loop = None
    if loop_expected:
        native = {'endedSeconds': report['endedSeconds']}
        start = min(s['firstUtcTicks'] for s in report['streams']); end = max(s['lastUtcTicks'] for s in report['streams'])
        loop = legacy.loop_analysis(report['playerLoop'], native, {'observation': (start, end)}, [], valid)
        valid = valid and loop['clockJoinValid']
    elif report.get('playerLoop'):
        # JsonUtility emits an unused class with its field initializers.
        # Only this exact empty shape is absence; nonempty evidence is rejected.
        empty = {'version': 1, 'capacity': 4096, 'maximumNodes': 512, 'source': 'NativeWindowsPlayerLoopBoundaries',
            'complete': False, 'truncated': False, 'detached': False, 'callbacks': 0, 'firstUtcTicks': 0, 'lastUtcTicks': 0,
            'firstSeconds': 0, 'lastSeconds': 0, 'maximumClockStepSeconds': 0, 'boundaries': [], 'gaps': []}
        if report['playerLoop'] != empty: raise ValueError('Undeclared PlayerLoop diagnostic')
    return {'clockJoinValid': valid, 'maximumClockStepSeconds': max(clocks, default=0), 'mainThreadWindows': windows, 'playerLoop': loop}


def overlap(row, start, end):
    return row['fromUtcTicks'] <= end and row['toUtcTicks'] >= start


def analyze(directory):
    def read(path): return json.loads(path.read_text(encoding='utf-8'))
    cleanup = read(directory / 'cleanup.json'); mission = read(directory / 'multiplayer-checks.json'); manifest = read(directory / 'multiplayer-continuity.json')
    if cleanup['errors'] or cleanup['remainingTrackedChildren'] or not mission['executionFinished'] or manifest['complete'] is not True:
        raise ValueError('Close the actual fixture and complete diagnostics before analysis; mission acceptance may still be false')
    header = mission['sealed']['world']['header']; captured = datetime.fromisoformat(header['captureStartedAtUtc'])
    base_ticks = EPOCH + round(captured.timestamp() * SCALE)
    start = base_ticks + round(mission['replay']['runningCaptureFromMs'] * 10000); end = base_ticks + round(mission['replay']['runningCaptureToMs'] * 10000)
    reports = []
    for entry in manifest['programs']:
        path = Path(entry['directory']); report = read(path / 'report.json'); result = validate(report, entry['role'], entry['loop'])
        active_bodies = [body for body in report['bodies'] if not body['connected'] and start <= body['utcTicks'] <= end]
        windows = [row for row in result['mainThreadWindows'] if overlap(row, start, end)]
        gaps = [row for row in report['gaps'] if overlap(row, start, end)]
        loop_gaps = [row for row in result['playerLoop']['gaps'] if overlap(row, start, end)] if result['playerLoop'] else []
        reports.append({'name': entry['name'], 'role': entry['role'], 'connection': entry.get('connection'), 'clockJoinValid': result['clockJoinValid'],
            'streamCount': len(report['streams']), 'mainThreadSamples': report['mainThreadSamples'], 'activeBodyLosses': active_bodies if result['clockJoinValid'] else None,
            'activeGaps': gaps if result['clockJoinValid'] else None, 'activeMainThreadWindows': windows if result['clockJoinValid'] else None,
            'activePlayerLoopGaps': loop_gaps if result['clockJoinValid'] else None,
            'maximumClockStepSeconds': result['maximumClockStepSeconds']})
    return {'version': 1, 'complete': all(row['clockJoinValid'] for row in reports), 'missionAcceptancePassed': mission['acceptancePassed'],
        'programs': reports, 'scope': 'Same-host diagnostic overlap; send is an RPC call, not packet transmission; CPU windows are whole Update-to-Update brackets, not individual engine nodes; cycles are not seconds',
        'causalRootProven': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory', type=Path); args = parser.parse_args()
    result = analyze(args.directory); output = args.directory / 'pose-continuity-analysis.json'
    if output.exists(): raise FileExistsError('Preserve previous analysis outputs')
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': result['complete'], 'missionAcceptancePassed': result['missionAcceptancePassed'], 'programs': len(result['programs']),
        'activeBodyLosses': sum(len(p['activeBodyLosses'] or []) for p in result['programs']), 'causalRootProven': False, 'output': str(output)}))
    if not result['complete']: raise SystemExit(1)


if __name__ == '__main__': main()
