"""Read closed sparse long-run diagnostics. No SQLite, credentials or pose data.

Same-host UTC joins require stable clocks. CPU is the sampled Unity calling
thread over a whole Update-to-Update bracket, not a selected engine node.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path, PureWindowsPath
import re
from uuid import UUID

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


def exercise_incidents(packets, owners):
    incidents, active = [], {}
    previous, longest_gap = None, None

    def observe(packet):
        nonlocal previous, longest_gap
        frame = packet['frame']
        if frame['phase'] != 'Running' or packet['suspended']:
            active.clear()
            previous = None
            return
        point = {'frame': integer(packet['sequence'], 1), 'elapsedMilliseconds': integer(packet['elapsedMilliseconds']),
                 'tick': integer(frame['tick'])}
        if previous:
            gap = point['elapsedMilliseconds'] - previous['elapsedMilliseconds']
            if longest_gap is None or gap > longest_gap['milliseconds']:
                longest_gap = {'from': previous, 'to': point, 'milliseconds': gap}
        players = {row['id']: row for row in frame['players']}
        if len(players) != len(frame['players']) or not players.keys() <= owners.keys():
            raise ValueError('Exercise journal contains an unexpected or repeated player')
        for player, owner in owners.items():
            body = players.get(player)
            if body is not None and body['roomId'] != owner['roomId']:
                raise ValueError('Exercise journal player belongs to another room')
            if body and body['connected'] is True and body['rig']['kind'] == 'Simulated':
                if player in active:
                    active.pop(player)['recovered'] = point
                continue
            if player not in active:
                if len(incidents) >= 4096:
                    raise ValueError('Too many pose interruption windows for one report')
                incident = {'roomId': owner['roomId'], 'seat': owner['seat'] + 1, 'connection': owner['nativeConnectionId'],
                    'preceding': previous, 'firstInactive': point, 'lastInactive': point, 'recovered': None}
                active[player] = incident
                incidents.append(incident)
            else:
                active[player]['lastInactive'] = point
        previous = point

    journal = packets(observe)
    return journal, incidents, longest_gap


def exercise_observations(report, validated, connection, start, end, points):
    if not validated['clockJoinValid']:
        return None
    # Sparse evidence has gaps only above its threshold. Empty matches never imply continuous sampling.
    return {'poseGaps': {point: max((row for row in report['gaps'] if row['point'] == point
                and row['connection'] == connection and overlap(row, start, end)),
                key=lambda row: row['toUtcTicks'] - row['fromUtcTicks'], default=None) for point in points},
        'mainThreadWindow': max((row for row in validated['mainThreadWindows'] if overlap(row, start, end)),
            key=lambda row: row['wallSecondsIncludingQueries'], default=None),
        'playerLoopGap': max((row for row in validated['playerLoop']['gaps'] if overlap(row, start, end)),
            key=lambda row: row['seconds'], default=None) if validated['playerLoop'] else None,
        'bodyLoss': next((row for row in report['bodies'] if row['connection'] == connection and not row['connected']
            and start <= row['utcTicks'] <= end), None)}


def analyze_exercise(directory):
    def read(name): return json.loads((directory / name).read_text(encoding='utf-8'))
    cleanup = read('cleanup.json')
    manifest = read('multiplayer-continuity.json')
    if cleanup['errors'] or cleanup['remainingTrackedChildren'] or manifest['version'] != 1 or manifest['complete'] is not True:
        raise ValueError('Close the actual exercise and complete its diagnostics before analysis')
    world = read('linked-1-sealed.json')['world']
    header = world['header']
    session_id = str(UUID(header['sessionId']))
    if session_id != header['sessionId'] or world['complete'] is not True:
        raise ValueError('Exercise world is not sealed')
    replay = read('linked-1-replay-checks.json')
    if (directory / 'failure-forensics.json').exists():
        failure = read('failure-forensics.json')
        if failure['acceptancePassed'] is not False or failure['rounds'] != [
            {'sessionId': session_id, 'replayRead': True, 'replayContinuityPassed': replay['complete'], 'acceptancePassed': False}]:
            raise ValueError('Failed exercise has no complete matching forensic replay')
        passed = False
    else:
        run = read('exercise-result.json')
        if run['complete'] is not True or replay['complete'] is not True or len(run['modes']) != 1 \
                or run['modes'][0]['mode'] != 'linked' or run['modes'][0]['endurance'] is not True:
            raise ValueError('Exercise has no completed Linked endurance replay')
        passed = True
    clients = read('linked-native-clients.json')
    owners = {row['playerId']: row for row in clients}
    names = {row['name']: integer(row['nativeConnectionId'], 1) for row in clients}
    if not 1 <= len(owners) == len(names) == len(clients) == len(set(names.values())) <= 25 \
            or any(row['sessionId'] != session_id or row['name'] != 'linked-1-client-' + row['admissionId']
                   or integer(row['seat']) >= 5
                   or row['roomId'] not in header['roomIds'] for row in clients):
        raise ValueError('Exercise diagnostic manifest has no unique original connections')
    programs = manifest['programs']
    if len(programs) != len(clients) + 1 or {row['name'] for row in programs} != {'linked-1-server', *names}:
        raise ValueError('Exercise diagnostics do not cover the original processes')
    snapshot = directory / 'runtime-snapshot'
    reports, seen = {}, set()
    for entry in programs:
        server = entry['name'] == 'linked-1-server'
        path = PureWindowsPath(entry['directory'])
        role = 'Server' if server else 'Client'
        connection = names.get(entry['name'])
        if entry['role'] != role or entry['loop'] is not server or entry.get('connection') != connection \
                or path.parent.name != 'continuity' or not re.fullmatch(r'p[0-9]{3}', path.name) or path.name in seen:
            raise ValueError('Exercise diagnostic report does not match its original process')
        seen.add(path.name)
        report = read(Path('runtime-snapshot') / 'continuity' / path.name / 'report.json')
        if not server and not any(row['point'] == 'PoseSend' and row['connection'] == connection for row in report['streams']):
            raise ValueError('Exercise client report has no original pose send stream')
        reports[connection] = (report, validate(report, role, server))

    world_spec = importlib.util.spec_from_file_location('exercise_world_analysis', ROOT / 'scripts/analyze-world-journal.py')
    world_reader = importlib.util.module_from_spec(world_spec)
    world_spec.loader.exec_module(world_reader)
    journal_path = snapshot / 'linked-1-telemetry' / (session_id + '.worldlog')
    expected_header = {key: header[key] for key in ('sessionId', 'streamId', 'captureStartedAtUtc', 'origin', 'roomIds')}
    journal, incidents, longest_gap = exercise_incidents(
        lambda observe: world_reader.analyze(journal_path, expected_header=expected_header, on_packet=observe), owners)
    if not journal['sealed'] or journal['runningFrames'] < 1 \
            or not journal['acknowledgedSequence'] == world['acceptedSequence'] == replay['frames'] \
            or journal['lastFrame']['elapsedMilliseconds'] != world['durationMilliseconds']:
        raise ValueError('Exercise world journal differs from the original sealed replay')
    capture = world_reader.utc(journal['captureStartedAtUtc'])
    offset = capture - datetime(1970, 1, 1, tzinfo=timezone.utc)
    base = EPOCH + (offset.days * 86400 + offset.seconds) * SCALE + offset.microseconds * 10
    for incident in incidents:
        start = base + (incident['preceding'] or incident['firstInactive'])['elapsedMilliseconds'] * 10000
        end = base + (incident['recovered'] or incident['lastInactive'])['elapsedMilliseconds'] * 10000
        connection = incident['connection']
        incident['client'] = exercise_observations(*reports[connection], connection, start, end, ('PoseSend',))
        incident['server'] = exercise_observations(*reports[None], connection, start, end, ('PoseReceive', 'PoseAccepted'))
    return {'version': 1, 'complete': all(row['clockJoinValid'] for _, row in reports.values()),
        'missionAcceptancePassed': passed, 'worldJournalSha256': journal['sha256'], 'sealedFrames': journal['acknowledgedSequence'],
        'programs': len(reports), 'interruptions': incidents, 'longestRunningCaptureGap': longest_gap, 'causalRootProven': False,
        'scope': 'Overlap of sparse same-host observations. A pose send records an RPC call. Loop and thread gaps measure wall time.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--exercise', action='store_true', help='Match original Linked exercise interruptions to per-connection diagnostics')
    args = parser.parse_args()
    if args.exercise:
        result = analyze_exercise(args.directory)
        output = args.directory / 'exercise-pose-continuity-analysis.json'
        with output.open('x', encoding='utf-8') as file:
            file.write(json.dumps(result, indent=2) + '\n')
        print(json.dumps({key: result[key] for key in ('complete', 'missionAcceptancePassed', 'programs', 'sealedFrames', 'causalRootProven')}
                         | {'interruptions': len(result['interruptions']), 'output': str(output)}))
        if not result['complete']:
            raise SystemExit(1)
        return
    result = analyze(args.directory); output = args.directory / 'pose-continuity-analysis.json'
    if output.exists(): raise FileExistsError('Preserve previous analysis outputs')
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': result['complete'], 'missionAcceptancePassed': result['missionAcceptancePassed'], 'programs': len(result['programs']),
        'activeBodyLosses': sum(len(p['activeBodyLosses'] or []) for p in result['programs']), 'causalRootProven': False, 'output': str(output)}))
    if not result['complete']: raise SystemExit(1)


if __name__ == '__main__': main()
