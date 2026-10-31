"""Join closed same-host input traces by connection, without reading SQLite.

Reports overlapping observations, never an OS / driver / audio / transport
root-cause verdict. RPC calls have no packet correlation. Unstable UTC disables
cross-process joins instead of treating a clock step as a shared stall.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('timing_common', ROOT / 'scripts/analyze-pose-trace.py')
common = importlib.util.module_from_spec(spec); spec.loader.exec_module(common)
SCALE = 10_000_000


def intersection(left, right):
    result = []; i = j = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0]); end = min(left[i][1], right[j][1])
        if start < end: result.append((start, end))
        if left[i][1] < right[j][1]: i += 1
        else: j += 1
    return result


def intervals(report):
    # MainThreadGap is time between Update observations, not measured CPU time.
    values = sorted((row['utcTicks'] - round(row['durationSeconds'] * SCALE), row['utcTicks'])
                    for row in report['rows'] if row['point'] == 'MainThreadGap' and row['durationSeconds'] > .5)
    merged = []
    for start, end in values:
        if merged and start <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else: merged.append((start, end))
    return merged


def analyze(directory):
    root = directory / 'runtime-snapshot'
    reports = {label: common.load_report(root / f'pose-input-{name}-trace/report.json', role)
               for label, name, role in [('Visible','player','Client'), ('Peer','peer','Client'), ('Server','server','Server')]}
    connections = {}
    for role in ('Visible', 'Peer'):
        ids = {row['connection'] for row in reports[role]['rows'] if row['point'] == 'PoseSend'}
        if len(ids) != 1: raise ValueError('Each client must retain exactly one sending connection')
        connections[role] = ids.pop()
    if connections['Visible'] == connections['Peer']: raise ValueError('Clients cannot share a connection identity')
    marks = {row['phase']: common.ticks(row['utc']) for row in json.loads((directory / 'input-stages.json').read_text())}
    periods = {'baseline': (marks['baseline-start'], marks['baseline-end']),
               'observation': (marks['baseline-start'], marks['observation-end'])}
    for index in range(1, 4): periods[f'shot-{index}'] = (marks[f'shot-{index}-start'], marks[f'shot-{index}-end'])
    if any(start >= end for start, end in periods.values()): raise ValueError('Invalid observation window')
    clock_steps = {role: max((abs((b['utcTicks'] - a['utcTicks']) / SCALE - (b['seconds'] - a['seconds']))
                             for a, b in zip(report['rows'], report['rows'][1:])), default=0) for role, report in reports.items()}
    join_valid = all(value < .05 for value in clock_steps.values())

    def gap_summary(role, point, connection, period):
        rows = [row for row in reports[role]['rows'] if row['point'] == point and row['connection'] == connection]
        gaps = [{'seconds': b['seconds'] - a['seconds'], 'fromUtcTicks': a['utcTicks'], 'toUtcTicks': b['utcTicks']}
                for a, b in zip(rows, rows[1:]) if a['utcTicks'] <= period[1] and b['utcTicks'] >= period[0]]
        return {'intervals': len(gaps), 'maximumGapSeconds': max((g['seconds'] for g in gaps), default=None),
                'gapsOverHalfSecond': [g for g in gaps if g['seconds'] > .5]}

    def phase_summary(period):
        result = {}
        for client, connection in connections.items():
            result[client] = {'connection': connection, 'rpcCall': gap_summary(client, 'PoseSend', connection, period),
                'serverReceive': gap_summary('Server', 'PoseReceive', connection, period),
                'serverAccept': gap_summary('Server', 'PoseAccepted', connection, period),
                'publishedStale': [{'utcTicks': row['utcTicks'], 'ageSeconds': row['poseAgeSeconds']}
                    for row in reports['Server']['rows'] if row['point'] == 'BodyConnection' and row['connection'] == connection
                    and not row['connected'] and period[0] <= row['utcTicks'] <= period[1]]}
        for role, report in reports.items():
            rows = [row for row in report['rows'] if row['utcTicks'] >= period[0] and row['utcTicks'] - round(row['durationSeconds'] * SCALE) <= period[1]]
            result.setdefault(role, {})['maximumMainThreadGapSeconds'] = max((row['durationSeconds'] for row in rows if row['point'] == 'MainThreadGap'), default=0)
            result[role]['maximumMeasuredSpans'] = {point: max(row['durationSeconds'] for row in rows if row['point'] == point)
                for point in sorted({row['point'] for row in rows if row['durationSeconds'] > 0 and row['point'] != 'MainThreadGap'})}
        return result

    overlap = None
    if join_valid:
        shared = intersection(intersection(intervals(reports['Visible']), intervals(reports['Peer'])), intervals(reports['Server']))
        shared = intersection(shared, [periods['observation']])
        overlap = [{'fromUtcTicks': start, 'toUtcTicks': end, 'seconds': (end - start) / SCALE} for start, end in shared]
    hud = json.loads((root / 'pose-input-hud/report.json').read_text(encoding='utf-8-sig'))
    if not hud['complete'] or hud['error'] or hud['hudTransitionsTruncated'] or hud['mode'] != 'hud-trace': raise ValueError('Incomplete HUD trace')
    if hud['captures'] or hud['audioSamples'] or hud['callbackCount']: raise ValueError('Expected no native GPU readback / PCM')
    hud_start = common.ticks(hud['startedAtUtc'])
    stale_hud = []
    transitions = hud['hudTransitions']
    for index, row in enumerate(transitions):
        if row['hud']['status'] != 'POSE STREAM STALE': continue
        following = transitions[index + 1] if index + 1 < len(transitions) else None
        observed_at = hud_start + round(row['seconds'] * SCALE)
        stale_hud.append({'utcTicks': observed_at, 'poseAccepted': row['hud']['poseAccepted'], 'connected': row['hud']['connected'],
            'withinPoseObservation': periods['observation'][0] <= observed_at <= periods['observation'][1] if join_valid else None,
            'durationSeconds': following['seconds'] - row['seconds'] if following else None,
            'nextStatus': following['hud']['status'] if following else None, 'rightCensored': following is None})
    return {'source': 'Actual native same-host timing; individual connections; no per-packet correlation',
        'connectionIds': connections, 'clockStepMaximumSeconds': clock_steps, 'clockJoinValid': join_valid,
        'phases': {name: phase_summary(period) for name, period in periods.items()} if join_valid else None, 'hudStaleTransitions': stale_hud,
        'overlappingThreeProcessMainThreadGaps': overlap,
        'limits': ['MainThreadGap measures the interval between Update observations, not CPU execution or an OS-wide suspension',
                   'Shared intervals are observations, not an audio, GPU, scheduler, I/O or transport root-cause verdict',
                   'External window observation / input tools were present and their influence has not been excluded',
                   'Diagnostic instrumentation overhead has not been excluded as a contributor',
                   'RPC call / receive intervals cannot pair individual packets and include phase-boundary gaps',
                   'Shot-stage windows include operator inspection and acknowledgement waits, not weapon-processing duration',
                   'Published body changes are sampled at 10Hz; HUD UTC uses its own report start and relative clock',
                   'Empty shared intervals do not prove absence of stalls; invalid clocks disable cross-process joins',
                   'Diagnostic final serialization and file writes happen after pose observation ends']}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory', type=Path); args = parser.parse_args()
    directory = args.directory.resolve()
    if directory.parent != ROOT / 'artifacts/desktop-venue' or not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}', directory.name):
        parser.error('Pass this repository own closed desktop-venue run')
    if json.loads((directory / 'cleanup.json').read_text()) != {'errors': [], 'remainingTrackedChildren': []}: raise ValueError('Writers did not stop cleanly')
    result = analyze(directory)
    (directory / 'input-timing-analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not result['clockJoinValid']: raise SystemExit('Unstable UTC: cross-process joins withheld')


if __name__ == '__main__': main()
