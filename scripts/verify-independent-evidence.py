"""Read back CLOSED IndependentFiveRoomLong JSON / CSV evidence, never SQLite.

The caller must first observe the original tool handle terminal and clean up all
writers. This checks cross-file consistency, not historical process execution,
raw replay gameplay, root cause, rendering, active users or network capacity.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
METRICS = ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent')


def require(value, message):
    if not value: raise ValueError(message)


def count(value):
    require(type(value) is int and value >= 0, 'Expected a nonnegative integer')
    return value


def audit_counters(row, size, final_sequence, *, replay, room):
    frames, running = count(row['frames']), count(row['runningFrames'])
    require(0 < running <= frames and count(row['expectedParticipantObservations']) == running * size, 'Running observation accounting differs')
    if replay:
        require(count(row['finalSequence']) == final_sequence and count(row['finalTick']) == 18000, 'Replay terminal boundary differs')
        require(frames == final_sequence and count(row['skippedLiveSequences']) == 0 and row['finalPacketAndStatisticsMatch'] is True, 'Incomplete declared full replay')
    else:
        require(frames <= count(row['finalSequence']) <= final_sequence and count(row['finalTick']) <= 18000, 'Live observation exceeds the sealed world')
    bad = count(row['badFrames']); require(bad <= frames, 'Invalid bad-frame count')
    require(all(0 < count(v) <= bad for v in row['perPlayerBadFrames'].values()), 'Per-player failure counts differ')
    paused = count(row['pausedFrames'])
    require(paused > 0 if room == 1 else paused == 0, 'Planned Pause must belong only to room 1')
    require(running + paused <= frames, 'Running and Paused frame counts overlap')
    gaps = count(row['captureGapsAtLeast1500ms'])
    paused_bad, environment_bad = count(row['badPausedFrames']), count(row['badEnvironmentFrames'])
    require(paused_bad <= paused and environment_bad <= frames, 'Invalid Pause / environment failure counts')
    passed = bad == 0 and (not replay or gaps == 0) and paused_bad == 0 and environment_bad == 0
    require(type(row['passed']) is bool and row['passed'] is passed, 'Audit pass flag disagrees with recorded counters')
    return passed


def verify(directory):
    directory = directory.resolve(strict=True)
    require(directory.parent == (ROOT / 'artifacts/desktop-long').resolve() and re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}', directory.name), 'Use an explicit owned desktop-long directory')
    evidence = {}
    def content(name):
        value = (directory / name).read_bytes(); evidence[name] = hashlib.sha256(value).hexdigest(); return value
    def read(name): return json.loads(content(name))
    checks, cleanup = read('independent-checks.json'), read('cleanup.json')
    require(checks['version'] == 1 and checks['fixtureKind'] == 'IndependentFiveRoomLong' and checks['executionFinished'] is True, 'Not finished independent evidence')
    require(cleanup['errors'] == [] and cleanup['remainingTrackedChildren'] == [], 'Cleanup has errors, unknown state or remaining children')
    require(type(checks['acceptancePassed']) is bool and checks['complete'] is checks['acceptancePassed'], 'Completion and acceptance differ after cleanup')
    require(checks['headsets'] == 0 and checks['hosts'] == 1 and checks['networkCapacityAccepted'] is False and checks['durationSecondsPerRoom'] == 900, 'Unsupported evidence scope')
    require('poseContinuity' in checks and checks['poseContinuity'] is None and not (directory / 'multiplayer-continuity.json').exists(), 'Unexpected diagnostic mode')
    receipt = checks['playerBuildReceipt']; fingerprint = receipt['sourceFingerprint']
    require(receipt['target'] == 'StandaloneWindows64' and re.fullmatch('[a-f0-9]{64}', fingerprint), 'Missing Windows source receipt')
    total = count(checks['participants']); require(total in (5, 10, 15, 20, 25), 'Invalid five-room participant count'); size = total // 5
    roster = read('independent-native-clients.json'); require(len(roster) == total, 'Native roster size differs')
    for key in ('playerId', 'admissionId', 'name', 'processId'):
        require(len({p[key] for p in roster}) == total, 'Native identities alias: ' + key)
    require(all(type(p['processId']) is int and p['processId'] > 0 for p in roster), 'Invalid native process identity')
    rooms = checks['rooms']; headers = read('independent-world-headers.json')
    require(len(rooms) == len(headers) == 5 and {tuple(r['roomIds']) for r in rooms} == {(i,) for i in range(1, 6)}, 'Five independent rooms required')
    require(len({r['sessionId'] for r in rooms}) == len({h['streamId'] for h in headers}) == 5, 'World identities alias')
    pause = checks['pauseIsolation']; require(read('independent-pause-isolation.json') == pause, 'Independent Pause witness differs')
    require(count(pause['pauseSequence']) < count(pause['resumeSequence']) and 0 < count(pause['tick']) < 18000, 'Invalid Pause fence')
    require(type(pause['secondsObserved']) in (int, float) and math.isfinite(pause['secondsObserved']) and pause['secondsObserved'] >= 3, 'Pause observation is too short')
    others = pause['otherRooms']; require(len(others) == 4 and {r['roomId'] for r in others} == {2, 3, 4, 5}, 'Pause isolation witness has the wrong rooms')
    require(all(count(r['beforeTick']) < count(r['afterTick']) <= 18000 for r in others), 'Another room did not advance during Pause')
    require(type(checks['nativeLogFindings']) is list, 'Native log findings are unknown')
    summaries = []; expected_pass = not checks['nativeLogFindings']
    for room in sorted(rooms, key=lambda r: r['roomIds'][0]):
        number = room['roomIds'][0]; prefix = 'independent-long-' + str(number)
        own = [p for p in roster if p['roomId'] == number]
        require(len(own) == size and {p['seat'] for p in own} == set(range(size)) and all(p['sessionId'] == room['sessionId'] for p in own), 'Original room / seat assignments differ')
        sealed = room['sealed']; require(read(prefix + '-sealed.json') == sealed, 'Independent seal artifact differs')
        world, stats = sealed['world'], sealed['statistics']; header = world['header']; final = count(world['acceptedSequence'])
        require(final > 0 and world['complete'] is True and stats['pendingTelemetry'] is False, 'Exact dual seals are not declared complete')
        require(header in headers and sum(h == header for h in headers) == 1 and header['sessionId'] == stats['sessionId'] == room['sessionId'] and header['roomIds'] == [number], 'World / ledger belongs to another room')
        require(header['origin'] == stats['origin'] == 'Simulation' and header['rulesVersion'] == '0.8.0' and header['missionDurationSeconds'] == 900, 'World source / mission clock differs')
        require(len(header['props']) == 1 and header['props'][0]['roomId'] == number, 'Geometry crossed room scope')
        latest = read(prefix + '-latest-frame.json'); packet = latest['packet']
        require(packet['sequence'] == final and packet['frame']['phase'] == 'Ended' and packet['frame']['tick'] == 18000 and packet['elapsedMilliseconds'] == world['durationMilliseconds'], 'Saved final frame differs from exact seal')
        require(sorted(latest['statistics'], key=lambda p: p['playerId']) == sorted(stats['players'], key=lambda p: p['playerId']), 'Saved final frame ledger differs')
        end = room['automaticEnd']; clock = end['payload']['clockExpiration']
        require(end['sessionId'] == room['sessionId'] and end['kind'] == 'ControlApplied' and clock['tick'] == 18000 and clock['streamId'] == header['streamId'] and clock['observedSequence'] < end['sequence'] <= packet['observedSequence'], 'Automatic End witness differs')
        expiry = room['originalConnectionsAfterExpiry']; require(expiry['allOriginalAdmissions'] is True and 0 < count(expiry['tick']) <= 18000, 'Original expired-ticket admission witness is absent')
        results = room['clientResults']; require(len(results) == size and len({p['playerId'] for p in results}) == size, 'Individual results incomplete or duplicated')
        owners = {p['playerId']: p for p in own}; ledger = {p['playerId']: p for p in stats['players']}
        require(len(ledger) == size and set(ledger) == set(owners) == {p['playerId'] for p in results}, 'Sealed / result roster differs from native roster')
        require(all(p['roomId'] == number for p in ledger.values()), 'Sealed ledger crossed room scope')
        for result in results:
            owner = owners[result['playerId']]
            require(result['version'] == 1 and result['admissionId'] == owner['admissionId'] and result['sessionId'] == room['sessionId'] and result['roomId'] == number, 'Result is not the original admission')
            require(result['origin'] == 'Simulation' and result['streamId'] == header['streamId'] and result['worldSequence'] == final and result['throughSequence'] == stats['throughSequence'] and count(result['finalStreamSequence']) == packet['throughCombatSequence'], 'Individual world / combat boundary differs')
            require(all(result[k] == ledger[result['playerId']][k] for k in METRICS), 'Result statistics differ from sealed ledger')
        delivery = read(prefix + '-player-results.json')
        require(delivery['allAcknowledged'] is True and delivery['timedOut'] == [] and set(delivery['phases']) == {p['name'] for p in own} and all(v == 'acknowledged' for v in delivery['phases'].values()), 'Original result acknowledgment witness differs')
        csv_name = prefix + '-report.csv'; raw = content(csv_name); record = room['finalReportCsv']
        require(record['verified'] is True and record['players'] == size and record['sha256'] == evidence[csv_name] and Path(record['path']).resolve() == (directory / csv_name).resolve(), 'CSV metadata differs')
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline='')))
        require(len(rows) == size and {p['playerId'] for p in rows} == set(owners), 'CSV original roster differs')
        result_by_id = {p['playerId']: p for p in results}
        for row in rows:
            result = result_by_id[row['playerId']]
            require(row['reportVersion'] == '1' and row['rowType'] == 'Player' and row['sessionMode'] == 'Independent' and row['sessionId'] == room['sessionId']
                and row['roomIds'] == str(number) and row['playerRoomId'] == str(number) and row['origin'] == 'Simulation' and row['plannedDurationSeconds'] == '900', 'CSV session / room / source differs')
            require(row['streamId'] == result['streamId'] and int(row['finalStreamSequence']) == result['finalStreamSequence'] and int(row['throughSequence']) == result['throughSequence'], 'CSV tail boundary differs')
            require(all(Decimal(row[k]).is_finite() and Decimal(row[k]) == Decimal(str(result[k])) for k in METRICS), 'CSV statistics differ')
        live_pass = audit_counters(room['live'], size, final, replay=False, room=number)
        replay_pass = audit_counters(room['replay'], size, final, replay=True, room=number)
        require(set(room['live']['perPlayerBadFrames']) <= set(owners) and set(room['replay']['perPlayerBadFrames']) <= set(owners), 'Audit names another player')
        age = room['sourceAge']; require(count(age['frames']) == room['live']['frames'] and count(age['heartbeats']) > 0 and type(age['maximumSeconds']) in (int, float) and math.isfinite(age['maximumSeconds']), 'Source-age observation metadata differs')
        age_pass = count(age['badSamples']) == 0
        if age_pass: require(-1 <= age['maximumSeconds'] < 1.5, 'Accepted source age exceeds the unchanged boundary')
        expected_pass = expected_pass and live_pass and replay_pass and age_pass
        summaries.append({'roomId': number, 'participants': size, 'worldFrames': final, 'runningFrames': room['replay']['runningFrames'], 'participantObservations': room['replay']['expectedParticipantObservations'], 'pausedFrames': room['replay']['pausedFrames'], 'badFrames': room['replay']['badFrames'], 'badSourceAges': age['badSamples']})
    require(checks['acceptancePassed'] is expected_pass, 'Reported acceptance disagrees with recorded evidence')
    for name, digest in evidence.items():
        require(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, 'Evidence changed during readback')
    return {'run': directory.name, 'sourceFingerprint': fingerprint, 'acceptancePassed': expected_pass, 'participants': total, 'rooms': summaries, 'evidenceHashes': evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directories', nargs='+', type=Path); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    output = args.output.resolve(); require(output.is_relative_to((ROOT / 'artifacts').resolve()) and not output.exists(), 'Use a new output under artifacts')
    require(not any(output.is_relative_to(p.resolve()) for p in args.directories), 'Output must not enter preserved input evidence')
    require(len({p.resolve() for p in args.directories}) == len(args.directories), 'Duplicate input run')
    runs = [verify(p) for p in args.directories]
    report = {'version': 1, 'complete': True, 'networkCapacityAccepted': False, 'causalRootProven': False, 'runs': runs, 'scope': __doc__}
    with output.open('x', encoding='utf-8') as target: json.dump(report, target, indent=2); target.write('\n')
    print(json.dumps({'complete': True, 'runs': len(runs), 'acceptancePassed': [r['acceptancePassed'] for r in runs], 'output': str(output)}))


if __name__ == '__main__': main()
