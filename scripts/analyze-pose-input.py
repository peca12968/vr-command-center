"""Join closed same-host input traces by connection, without reading SQLite.

Reports overlapping observations, never an OS / driver / audio / transport
root-cause verdict. RPC calls have no packet correlation. Unstable UTC disables
cross-process joins instead of treating a clock step as a shared stall.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('timing_common', ROOT / 'scripts/analyze-pose-trace.py')
common = importlib.util.module_from_spec(spec); spec.loader.exec_module(common)
cpu_spec=importlib.util.spec_from_file_location('process_timing_analysis',ROOT/'scripts/analyze-process-timing.py')
process_cpu=importlib.util.module_from_spec(cpu_spec);cpu_spec.loader.exec_module(process_cpu)
SCALE = 10_000_000
UNIX_TICKS = 621355968000000000


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


def loop_analysis(report, native, periods, shared, native_clock_valid):
    if report['version'] != 1 or report['source'] != 'NativeWindowsPlayerLoopBoundaries' \
        or not report['complete'] or report['truncated'] or not report['detached']:
        raise ValueError('Incomplete or attached PlayerLoop diagnostic')
    boundaries=report['boundaries']; gaps=report['gaps']
    if not 0 < len(boundaries) <= 1024 or report['maximumNodes'] != 512 or report['capacity'] != 4096 or len(gaps)>4096:
        raise ValueError('Invalid PlayerLoop bounds')
    for b in boundaries:
        if not re.fullmatch(r'(?:/\d+)+',b['path']) or not b['system'] or b['side'] not in ('before','after') \
            or type(b['calls']) is not int or b['calls']<0 or not math.isfinite(b['maximumIncomingGapSeconds']) or b['maximumIncomingGapSeconds']<0:
            raise ValueError('Invalid PlayerLoop boundary')
    identities={(b['path'],b['side']) for b in boundaries}
    if len(identities)!=len(boundaries) or any((b['path'],'after' if b['side']=='before' else 'before') not in identities for b in boundaries):
        raise ValueError('Incomplete PlayerLoop boundary pairs')
    if any(len({b['system'] for b in boundaries if b['path']==path})!=1 for path,_ in identities):
        raise ValueError('Inconsistent PlayerLoop system pair')
    if type(report['callbacks']) is not int or report['callbacks'] <= 0 or sum(b['calls'] for b in boundaries)!=report['callbacks']:
        raise ValueError('Invalid PlayerLoop callback count')
    for k in ('firstSeconds','lastSeconds','maximumClockStepSeconds'):
        if not math.isfinite(report[k]) or report[k]<0: raise ValueError('Invalid PlayerLoop time')
    if not report['firstSeconds'] <= report['lastSeconds'] <= native['endedSeconds'] \
        or any(type(report[k]) is not int or report[k]<=0 for k in ('firstUtcTicks','lastUtcTicks')) \
        or report['firstUtcTicks']>=report['lastUtcTicks']:
        raise ValueError('Invalid PlayerLoop coverage')
    clock_error=max(report['maximumClockStepSeconds'], abs((report['lastUtcTicks']-report['firstUtcTicks'])/SCALE-(report['lastSeconds']-report['firstSeconds'])))
    previous=report['firstSeconds']; observations=[]
    for g in gaps:
        if any(type(g[k]) is not int for k in ('fromBoundary','toBoundary','fromUtcTicks','toUtcTicks','fromFrame','toFrame')) \
            or not 0<=g['fromBoundary']<len(boundaries) or not 0<=g['toBoundary']<len(boundaries) \
            or not 0<=g['fromFrame']<=g['toFrame'] or not all(math.isfinite(g[k]) for k in ('fromSeconds','toSeconds')) \
            or not previous<=g['fromSeconds']<g['toSeconds']<=report['lastSeconds']:
            raise ValueError('Invalid PlayerLoop gap')
        a=boundaries[g['fromBoundary']];b=boundaries[g['toBoundary']];duration=g['toSeconds']-g['fromSeconds']
        if duration<=.1 or b['maximumIncomingGapSeconds']+1e-9<duration: raise ValueError('Inconsistent PlayerLoop gap')
        previous=g['toSeconds']
        clock_error=max(clock_error,abs((g['toUtcTicks']-g['fromUtcTicks'])/SCALE-duration),
            abs((g['fromUtcTicks']-report['firstUtcTicks'])/SCALE-(g['fromSeconds']-report['firstSeconds'])),
            abs((g['toUtcTicks']-report['firstUtcTicks'])/SCALE-(g['toSeconds']-report['firstSeconds'])))
        inside=a['path']==b['path'] and a['system']==b['system'] and a['side']=='before' and b['side']=='after'
        observations.append({**g,'seconds':duration,'from':{k:a[k] for k in ('path','system','side')},
            'to':{k:b[k] for k in ('path','system','side')},'location':'inside observed system' if inside else 'between observers'})
    for index,b in enumerate(boundaries):
        if b['maximumIncomingGapSeconds']>.1 and abs(max((g['seconds'] for g in observations if g['toBoundary']==index),default=0)-b['maximumIncomingGapSeconds'])>1e-9:
            raise ValueError('PlayerLoop maximum gap is missing from complete evidence')
    valid=native_clock_valid and clock_error<.05
    covered=[r for r in shared or [] if report['firstUtcTicks']<=r['fromUtcTicks'] and r['toUtcTicks']<=report['lastUtcTicks']]
    def in_period(g,p):return g['fromUtcTicks']<=p[1] and g['toUtcTicks']>=p[0]
    return {'clockJoinValid':valid,'maximumClockStepSeconds':clock_error,'callbacks':report['callbacks'],'boundaryCount':len(boundaries),
        'observationFullyCovered':report['firstUtcTicks']<=periods['observation'][0] and report['lastUtcTicks']>=periods['observation'][1] if valid else None,
        'maximumAdjacentBoundaryGapSeconds':max(b['maximumIncomingGapSeconds'] for b in boundaries),
        'fullyCoveredNativeTripleGaps':len(covered) if valid else None,
        'uncoveredNativeTripleGaps':len(shared or [])-len(covered) if valid else None,
        'gaps':observations,'phaseGaps':{name:[g for g in observations if in_period(g,p)] for name,p in periods.items()} if valid else None,
        'nativeTripleIntersections':[{'seconds':(end-start)/SCALE,'fromUtcTicks':start,'toUtcTicks':end,'boundaryGap':index}
            for index,g in enumerate(observations) for start,end in intersection([(g['fromUtcTicks'],g['toUtcTicks'])],
                [(r['fromUtcTicks'],r['toUtcTicks']) for r in shared or []])] if valid else None,
        'limits':['Intervals between inserted observers are wall time, not native system CPU duration',
            'An inside-system interval includes waiting, scheduling and instrumentation; it does not prove that system caused it',
            'A between-observer gap may cross frame boundaries or engine work outside the instrumented tree',
            'Observer overhead / perturbation and external-tool influence are not excluded']}


def heartbeat_analysis(report, shared, periods, native_clock_valid):
    if report['schemaVersion'] != 1 or report['source'] != 'IndependentPythonWakeTiming' or not report['complete'] or report['truncated']:
        raise ValueError('Incomplete independent heartbeat')
    if report['sampleSeconds'] != .01 or report['maximumGapRows'] != 4096 or len(report['gaps']) > 4096:
        raise ValueError('Unsupported heartbeat bounds')
    for key in ('startedCounterNs', 'endedCounterNs', 'durationNs', 'wakes', 'maximumGapNs', 'maximumClockStepNs'):
        if type(report[key]) is not int or report[key] < 0: raise ValueError('Invalid heartbeat counter')
    if report['wakes'] == 0 or report['durationNs'] != report['endedCounterNs'] - report['startedCounterNs']:
        raise ValueError('Incomplete heartbeat duration')
    previous = report['startedCounterNs']; gaps = []; gap_clock_error = 0
    for row in report['gaps']:
        for key in ('fromCounterNs','toCounterNs','fromUnixNs','toUnixNs','durationNs','processCpuNs'):
            if type(row[key]) is not int or row[key] < 0: raise ValueError('Invalid heartbeat gap')
        if not previous <= row['fromCounterNs'] < row['toCounterNs'] <= report['endedCounterNs'] \
            or row['durationNs'] != row['toCounterNs'] - row['fromCounterNs'] or row['durationNs'] <= 100_000_000 \
            or report['maximumGapNs'] < row['durationNs']:
            raise ValueError('Inconsistent heartbeat gap')
        previous = row['toCounterNs']
        gap_clock_error = max(gap_clock_error, abs((row['toUnixNs'] - row['fromUnixNs']) - row['durationNs']))
        if row['durationNs'] > 500_000_000:
            gaps.append((UNIX_TICKS + row['fromUnixNs'] // 100, UNIX_TICKS + row['toUnixNs'] // 100))
    anchors = report['anchors']; anchor_error = 0
    if not anchors or len(anchors) > 256: raise ValueError('Missing heartbeat clock anchors')
    for row in anchors:
        if any(type(row[key]) is not int or row[key] < 0 for key in ('counterNs','unixNs')) \
            or not report['startedCounterNs'] <= row['counterNs'] <= report['endedCounterNs']: raise ValueError('Invalid heartbeat anchor')
    for a, b in zip(anchors, anchors[1:]):
        if b['counterNs'] <= a['counterNs']: raise ValueError('Heartbeat anchor counter moved backwards')
        anchor_error = max(anchor_error, abs((b['unixNs'] - a['unixNs']) - (b['counterNs'] - a['counterNs'])))
    native = [(row['fromUtcTicks'], row['toUtcTicks']) for row in shared] if shared is not None else []
    explicit = 'startedUnixNs' in report and 'endedUnixNs' in report
    start_ns = report['startedUnixNs'] if explicit else anchors[0]['unixNs']
    end_ns = report['endedUnixNs'] if explicit else anchors[-1]['unixNs']
    if type(start_ns) is not int or type(end_ns) is not int or start_ns < 0 or end_ns <= start_ns:
        raise ValueError('Invalid heartbeat UTC coverage')
    coverage_error = abs(end_ns-start_ns-report['durationNs']) if explicit else 0
    if explicit:
        coverage_error = max(coverage_error, max(abs(row['unixNs']-start_ns-(row['counterNs']-report['startedCounterNs'])) for row in anchors))
    clock_error = max(anchor_error, gap_clock_error, coverage_error, report['maximumClockStepNs'])
    valid = native_clock_valid and clock_error < 50_000_000
    coverage = (UNIX_TICKS + start_ns // 100, UNIX_TICKS + end_ns // 100)
    covered = [(a,b) for a,b in native if coverage[0] <= a and b <= coverage[1]]
    joined = intersection(native, sorted(gaps)) if valid else None
    return {'source': report['source'], 'wakes': report['wakes'], 'durationSeconds': report['durationNs'] / 1e9,
        'maximumWakeGapSeconds': report['maximumGapNs'] / 1e9, 'clockJoinValid': valid,
        'maximumClockStepSeconds': clock_error / 1e9, 'gapRecordingThresholdSeconds': .1,
        'coverageFromUtcTicks': coverage[0], 'coverageToUtcTicks': coverage[1], 'coverageSource': 'explicit' if explicit else 'conservative clock anchors',
        'fullyCoveredNativeTripleGaps': len(covered) if valid else None, 'uncoveredNativeTripleGaps': len(native)-len(covered) if valid else None,
        'gapsOverHalfSecond': [{'fromUtcTicks': a, 'toUtcTicks': b} for a, b in gaps],
        'nativeTripleGapIntersections': [{'fromUtcTicks': a, 'toUtcTicks': b, 'seconds': (b-a) / SCALE} for a,b in joined] if joined is not None else None,
        'phaseLongGaps': {name: len(intersection(sorted(gaps), [period])) for name, period in periods.items()} if valid else None,
        'limits': ['Normal-priority independent process on the same host and execution environment; not an independent machine',
                   'Wake gaps include requested sleep, scheduling, blocking and other causes; no OS or native-thread CPU attribution',
                   'No gaps over 100ms retained does not mean a zero timer delta; use maximumWakeGapSeconds',
                   'A clean control does not prove historical stalls were fixed or exclude external-tool influence']}


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
    for phase in marks:
        if phase.endswith('-start') and phase != 'baseline-start':
            name = phase[:-6]; periods[name] = (marks[phase], marks[name + '-end'])
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
    heartbeat_path = root / 'pose-input-heartbeat/report.json'
    heartbeat = heartbeat_analysis(json.loads(heartbeat_path.read_text()), overlap, periods, join_valid) if heartbeat_path.exists() else None
    result_path = directory / 'input-timing-result.json'
    fixture=json.loads(result_path.read_text()) if result_path.exists() else {}
    loop_reports={}
    for role,report in reports.items():
        raw=report.get('playerLoop')
        if not raw:continue
        if fixture.get('playerLoop') is False:
            # Actual JsonUtility output materializes an unrequested null class.
            # Ignore ONLY its exact empty default, with explicit fixture mode.
            empty={'version':1,'capacity':4096,'maximumNodes':512,'source':'NativeWindowsPlayerLoopBoundaries',
                'complete':False,'truncated':False,'detached':False,'callbacks':0,'firstUtcTicks':0,'lastUtcTicks':0,
                'firstSeconds':0,'lastSeconds':0,'maximumClockStepSeconds':0,'boundaries':[],'gaps':[]}
            if raw!=empty:raise ValueError('Unexpected PlayerLoop evidence in a disabled fixture')
            continue
        loop_reports[role]=loop_analysis(raw,report,periods,overlap,join_valid)
    if loop_reports and len(loop_reports)!=3: raise ValueError('Partial three-process PlayerLoop evidence')
    if fixture.get('independentHeartbeat') and heartbeat is None:
        raise ValueError('Declared independent heartbeat report is missing')
    if fixture.get('playerLoop') and len(loop_reports)!=3:
        raise ValueError('Declared PlayerLoop reports are missing')
    cpu_path=root/'pose-process-timing/report.json';cpu=None
    if cpu_path.exists():
        if fixture.get('processTiming') is False:raise ValueError('Unexpected CPU timing in disabled fixture')
        manifest=json.loads((root/'pose-process-targets.json').read_text())
        if manifest['schemaVersion']!=1 or manifest['source']!='OwnedProcessTimingTargets' or {t['role'] for t in manifest['targets']}!={'Visible','Peer','Server'}:
            raise ValueError('Invalid three-process ownership manifest')
        cpu_intervals=[dict(kind='sharedUpdate',**r) for r in overlap or []]
        loop_valid=all(r['clockJoinValid'] for r in loop_reports.values())
        if loop_reports and loop_valid:
            shared_loop=None
            for r in loop_reports.values():
                values=[(g['fromUtcTicks'],g['toUtcTicks']) for g in r['gaps'] if g['seconds']>.5]
                shared_loop=values if shared_loop is None else intersection(shared_loop,values)
            cpu_intervals.extend({'kind':'sharedLoop','fromUtcTicks':a,'toUtcTicks':b,'seconds':(b-a)/SCALE}
                for a,b in intersection(shared_loop,[periods['observation']]))
        cpu=process_cpu.analyze(json.loads(cpu_path.read_text()),manifest['targets'],cpu_intervals,join_valid and loop_valid)
    if fixture.get('processTiming') and cpu is None:raise ValueError('Declared process timing is missing')
    return {'source': 'Actual native same-host timing; individual connections; no per-packet correlation', 'independentHeartbeat': heartbeat,'playerLoop':loop_reports or None,'processTiming':cpu,
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
    heartbeat_cleanup = directory / 'heartbeat-cleanup.json'
    if heartbeat_cleanup.exists() and json.loads(heartbeat_cleanup.read_text()) != {'errors': [], 'remaining': []}:
        raise ValueError('Heartbeat writer did not stop cleanly')
    if not (directory/'input-timing-result.json').exists():raise ValueError('Completed native input fixture metadata is missing')
    fixture=json.loads((directory/'input-timing-result.json').read_text())
    cpu_cleanup=directory/'process-timing-cleanup.json'
    if fixture.get('processTiming') and not cpu_cleanup.exists():raise ValueError('Process timing cleanup is missing')
    if cpu_cleanup.exists() and json.loads(cpu_cleanup.read_text())!={'errors':[],'remaining':[]}:
        raise ValueError('Process timing writer did not stop cleanly')
    result = analyze(directory)
    (directory / 'input-timing-analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not result['clockJoinValid']: raise SystemExit('Unstable UTC: cross-process joins withheld')
    if result['independentHeartbeat'] is not None and not result['independentHeartbeat']['clockJoinValid']:
        raise SystemExit('Unstable heartbeat clock: independent joins withheld')
    if result['playerLoop'] is not None and not all(r['clockJoinValid'] for r in result['playerLoop'].values()):
        raise SystemExit('Unstable PlayerLoop clock: boundary joins withheld')
    if result['playerLoop'] is not None and not all(r['observationFullyCovered'] for r in result['playerLoop'].values()):
        raise SystemExit('PlayerLoop boundary observations did not cover the full observation period')
    if result['processTiming'] is not None and not result['processTiming']['clockJoinValid']:
        raise SystemExit('Unstable CPU timing clock: process joins withheld')


if __name__ == '__main__': main()
