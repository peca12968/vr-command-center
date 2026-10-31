"""Five owned 15-minute native Windows worlds, five stationary Simulation clients each.

Full saved-frame audits and separate exact seals; no device or LAN capacity claim.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import threading
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('independent_multi', ROOT / 'scripts/check-desktop-multiplayer-long.py')
multi = importlib.util.module_from_spec(spec); spec.loader.exec_module(multi)
vm, capacity, debrief = multi.vm, multi.capacity, multi.debrief


def fingerprint():
    return hashlib.sha256((ROOT / 'scripts/check-desktop-independent-long.py').read_bytes() + multi.fingerprint().encode()).hexdigest()


class RoomAudit(multi.Continuity):
    def __init__(self, entry, *, replay=False):
        super().__init__(entry['players'], entry['stableSequence'], entry['health'], replay=replay)
        self.entry = entry; self.pauses = []; self.pause_bad = 0; self.environment_bad = 0

    def observe(self, row):
        packet, frame = row['packet'], row['packet']['frame']
        environment = self.entry['mission']['definition']['environment']
        if frame['phase'] in ('Running', 'Paused'):
            self.environment_bad += bool(packet.get('suspended') or packet['weather'] != environment['weather']
                or packet['lightning'] != environment['lightning'] or frame['night'] != (environment['timeOfDay'] == 'Night')
                or len(frame['enemies']) != 1 or any(p['roomId'] != self.entry['roomIds'][0] for p in frame['enemies']))
        if frame['phase'] == 'Paused' and self.entry['roomIds'] == [1]:
            if len(self.pauses) >= 512: raise ValueError('Planned pause observation bound exceeded')
            self.pauses.append({'sequence': packet['sequence'], 'tick': frame['tick'], 'observedSequence': packet['observedSequence']})
            running = {**row, 'packet': {**packet, 'frame': {**frame, 'phase': 'Running'}}}
            self.pause_bad += bool(multi.roster_faults(running, self.players, self.stable_sequence, self.health))
            # Keep every saved sequence / gap without counting a deliberate Pause as activity.
            row = {**row, 'packet': {**packet, 'frame': {**frame, 'phase': 'Preparing'}}}
        super().observe(row)

    def finish(self, pause):
        if self.entry['roomIds'] == [1]:
            if not pause or not self.pauses or any(p['tick'] != pause['tick'] or not pause['pauseSequence'] <= p['observedSequence'] < pause['resumeSequence'] for p in self.pauses):
                raise ValueError('Paused frames do not belong to the accepted room-1 Pause / Resume fence')
        elif self.pauses: raise ValueError('Another room acquired the planned pause')
        result = self.result()
        return {**result, 'pausedFrames': len(self.pauses), 'badPausedFrames': self.pause_bad, 'badEnvironmentFrames': self.environment_bad,
            'passed': result['passed'] and self.pause_bad == 0 and self.environment_bad == 0}


def verify_worlds(entries, headers):
    if len(entries) != 5 or len({e['id'] for e in entries}) != 5 or len({e['port'] for e in entries}) != 5:
        raise ValueError('Five distinct sessions and native UDP ports required')
    if len({h['streamId'] for h in headers}) != 5: raise ValueError('World stream identities alias')
    for entry, header in zip(entries, headers):
        if header['sessionId'] != entry['id'] or header['roomIds'] != entry['roomIds'] or header['missionDurationSeconds'] != 900 or header['origin'] != 'Simulation':
            raise ValueError('World header belongs to another room / source / clock')
        if len(header['props']) != 1 or header['props'][0]['roomId'] != entry['roomIds'][0]: raise ValueError('Geometry crossed room scope')


def live_room(v, entry, stop):
    audit = RoomAudit(entry); age = {'frames': 0, 'heartbeats': 0, 'maximumSeconds': -1, 'badSamples': 0}; expiry = None
    entry['liveAudit'] = audit; entry['sourceAge'] = age
    request = urllib.request.Request(v.base + f'/api/sessions/{entry["id"]}/world/watch?mode=live', headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    latest = max(datetime.fromisoformat(p['ticketExpiresAtUtc']) for p in entry['players']); deadline = time.monotonic() + 1010
    with urllib.request.urlopen(request, timeout=5) as response:
        kind = ''; captured = None
        for raw in response:
            if stop.is_set(): return None
            if time.monotonic() > deadline: raise RuntimeError('Independent room observation exceeded bound')
            line = raw.decode('utf-8').strip()
            if line.startswith('event: '): kind = line[7:]
            if not line.startswith('data: '): continue
            row = json.loads(line[6:]); now = datetime.now(timezone.utc)
            if kind == 'header': captured = datetime.fromisoformat(row['header']['captureStartedAtUtc']); continue
            if kind == 'frame':
                audit.observe(row); age['frames'] += 1; seconds = (now - captured).total_seconds() - row['packet']['elapsedMilliseconds'] / 1000
                if expiry is None and now > latest and row['packet']['frame']['phase'] == 'Running':
                    if not multi.same_admissions(v.state(entry)['players'], entry['players']): raise ValueError('Original admission changed after expiry')
                    expiry = {'utc': now.isoformat(), 'tick': row['packet']['frame']['tick'], 'allOriginalAdmissions': True}
            elif kind == 'status':
                age['heartbeats'] += 1; seconds = (now - datetime.fromisoformat(row['capturedAtUtc'])).total_seconds()
                if row['complete']: break
            else: continue
            age['maximumSeconds'] = max(age['maximumSeconds'], seconds); age['badSamples'] += not -1 <= seconds < 1.5
    if expiry is None: raise ValueError('No original-admission observation after ticket expiry')
    return expiry


def replay_room(v, entry, sealed, pause):
    audit = RoomAudit(entry, replay=True); expected = v.frame(entry)
    request = urllib.request.Request(v.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4', headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    deadline = time.monotonic() + sealed['world']['durationMilliseconds'] / 4000 + 30
    with urllib.request.urlopen(request, timeout=10) as response:
        for row in capacity.sse_frames(response):
            if time.monotonic() > deadline: raise RuntimeError('Independent full replay exceeded bound')
            audit.observe(row)
    if audit.previous != sealed['world']['acceptedSequence'] or audit.last != expected or audit.tick != 18000 or audit.last['packet']['frame']['phase'] != 'Ended':
        raise ValueError('Independent full replay differs from exact seal / mission limit')
    return {**audit.finish(pause), 'finalPacketAndStatisticsMatch': True}


def run(v, args, tool):
    v.start(); entries = []; native = []; resources = []
    def memory(label):
        value = capacity.memory_status(); capacity.require_memory(value); resources.append({'stage': label, **value}); v.save('independent-resources.json', resources)
    for room in range(1, 6):
        weather, night = [('Clear', False), ('Fog', False), ('Rain', True), ('Storm', True), ('Clear', True)][room - 1]
        mission = v.request('/api/missions', {'name': f'Independent R{room} 15-minute Simulation', 'briefing': 'Separate native world / original admissions / exact separate seals',
            'durationSeconds': 900, 'environment': {'mode': 'VR', 'weather': weather, 'timeOfDay': 'Night' if night else 'Day', 'lightning': weather == 'Storm'},
            'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False},
            'props': [{'assetId': 'barrel' if room % 2 else 'sandbag', 'position': {'x': 4, 'y': 0, 'z': 1}, 'yawDegrees': room * 15}]}, expected=201)
        memory('server-' + str(room)); entry = v.create(mission, [room], 'independent-long-' + str(room)); entries.append(entry)
        for _ in range(args.players_per_room - 1):
            identity = str(uuid.uuid4()); state = v.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': room, 'name': f'Independent R{room}', 'headset': 'Quest3'}, role='Room' + str(room))
            entry['players'].append(next(p for p in state['players'] if p['id'] == identity))
        capacity.validate_roster(entry['players'], [room], args.players_per_room)
    for entry in entries:
        v.wait(lambda e=entry: v.request(f'/api/sessions/{e["id"]}/world', optional=True), 90, 'independent source ready')
        for player in entry['players']:
            memory('client-' + str(len(native) + 1)); name = entry['name'] + '-client-' + player['admissionId']
            v.launch(name, v.client_config(entry, v.ticket(entry, player)))
            native.append({'name': name, 'sessionId': entry['id'], 'playerId': player['id'], 'admissionId': player['admissionId'], 'roomId': player['roomId'], 'seat': player['seat'], 'processId': v.processes[name].pid})
        capacity.validate_frame(v.wait(lambda e=entry: v.connected(e), 100, 'independent original rigs'), entry['players'])
        v.stage('independent-admitting', rooms=len({p['roomId'] for p in native}), participants=len(native))
    v.save('independent-native-clients.json', native)
    headers = [v.request(f'/api/sessions/{e["id"]}/world')['header'] for e in entries]; verify_worlds(entries, headers)
    v.save('independent-world-headers.json', headers)
    for entry in entries:
        room = entry['roomIds'][0]; wrong = 'Room' + str(room % 5 + 1)
        v.command(entry, 'Begin', role=wrong, expected=403); v.request(f'/api/sessions/{entry["id"]}/world/watch?mode=live', role=wrong, expected=403)
        v.command(entry, 'SetMissionClock', missionClock={'autoEnd': True}); v.command(entry, 'Begin')
        v.command(entry, 'SetEnemies', enemies={'count': 1, 'behavior': 'Hold', 'autoAttack': True})
        v.wait(lambda e=entry: any(p['damageTaken'] > 0 for p in v.frame(e)['statistics']), 25, 'independent AI damage')
        off = v.command(entry, 'SetEnemies', enemies={'count': 1, 'behavior': 'Hold', 'autoAttack': False}); entry['stableSequence'] = off['session']['sequence']
        stable = v.wait(lambda e=entry: (f if not (f := v.frame(e))['packet']['frame']['autoAttack'] and f['packet']['observedSequence'] >= e['stableSequence'] else None), 10, 'independent AI hold')
        entry['health'] = {p['id']: p['health'] for p in stable['packet']['frame']['players']}
        if any(not 0 < h <= 100 for h in entry['health'].values()): raise ValueError('Independent participants must survive AI damage')
    stop = threading.Event(); pause = None; next_progress = 0
    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(live_room, v, e, stop) for e in entries]
            try:
                while not all(f.done() for f in futures):
                    for f in futures:
                        if f.done(): f.result()
                    if any(p.poll() is not None for p in v.processes.values()): raise RuntimeError('An owned actor exited before all five worlds completed')
                    first = entries[0].get('liveAudit')
                    if pause is None and first and first.tick >= 2400:
                        command = v.command(entries[0], 'Pause'); paused = v.wait(lambda: (f if (f := v.frame(entries[0]))['packet']['frame']['phase'] == 'Paused' else None), 10, 'room-1 deliberate Pause')
                        before = [v.frame(e) for e in entries[1:]]; begin = time.monotonic(); time.sleep(3)
                        still = v.frame(entries[0]); after = [v.frame(e) for e in entries[1:]]
                        tick = paused['packet']['frame']['tick']
                        if still['packet']['frame']['tick'] != tick or any(b['packet']['frame']['tick'] >= a['packet']['frame']['tick'] or a['packet']['frame']['phase'] != 'Running' for b, a in zip(before, after)):
                            raise ValueError('Target Pause leaked to another room or failed to freeze own tick')
                        resume = v.command(entries[0], 'Resume')
                        pause = {'tick': tick, 'pauseSequence': command['session']['sequence'], 'resumeSequence': resume['session']['sequence'], 'secondsObserved': time.monotonic() - begin,
                            'otherRooms': [{'roomId': e['roomIds'][0], 'beforeTick': b['packet']['frame']['tick'], 'afterTick': a['packet']['frame']['tick']} for e, b, a in zip(entries[1:], before, after)]}
                        v.save('independent-pause-isolation.json', pause)
                    if time.monotonic() >= next_progress:
                        next_progress = time.monotonic() + 30; memory('running')
                        status = [{'roomId': e['roomIds'][0], 'tick': e['liveAudit'].tick, 'badFrames': e['liveAudit'].bad, 'badSourceAges': e['sourceAge']['badSamples']} for e in entries if 'liveAudit' in e]
                        v.save('independent-live.json', status); v.stage('independent-running', rooms=status, participants=len(native))
                    time.sleep(.2)
            except BaseException:
                stop.set(); raise
            expiry = [f.result() for f in futures]
    finally: stop.set()
    results = []
    for entry, after in zip(entries, expiry):
        sealed = v.seal(entry); delivery = v.wait_for_player_results(entry)
        own = [p for p in native if p['sessionId'] == entry['id']]; state = v.state(entry); receipts = []
        if not delivery['allAcknowledged'] or len(delivery['phases']) != len(own) or not multi.same_admissions(state['players'], entry['players']): raise ValueError('Original results / admissions incomplete')
        for row in own:
            player = next(p for p in entry['players'] if p['id'] == row['playerId']); result = debrief.final_result(v, row['name']); debrief.validate_result(result, entry, player, sealed)
            if result['finalStreamSequence'] != state['combatStream']['acceptedSequence'] or debrief.log_text(v, row['name']).count('VR_CLIENT_CONNECTED id=') != 1: raise ValueError('Original connection or combat boundary changed')
            receipts.append(result)
        events = v.request(f'/api/sessions/{entry["id"]}/events?after=0&limit=500'); ends = [e for e in events if e['kind'] == 'ControlApplied' and e['payload'].get('clockExpiration')]
        if len(ends) != 1 or ends[0]['payload']['clockExpiration']['tick'] != 18000: raise ValueError('Expected one tick18000 automatic End per room')
        results.append({'sessionId': entry['id'], 'roomIds': entry['roomIds'], 'originalConnectionsAfterExpiry': after, 'stableSequence': entry['stableSequence'], 'stableHealthByPlayer': entry['health'],
            'live': entry['liveAudit'].finish(pause), 'sourceAge': entry['sourceAge'], 'sealed': sealed, 'clientResults': receipts, 'automaticEnd': ends[0],
            'finalReportCsv': capacity.practice.save_report(v, entry, sealed['statistics'], filename=entry['name'] + '-report.csv')})
    v.stage('independent-full-replay', rooms=5, frames=sum(r['sealed']['world']['acceptedSequence'] for r in results))
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(replay_room, v, e, r['sealed'], pause) for e, r in zip(entries, results)]
        for result, future in zip(results, futures): result['replay'] = future.result()
    findings = capacity.native_log_findings(v.directory)
    passed = all(r['live']['passed'] and r['replay']['passed'] and r['sourceAge']['badSamples'] == 0 for r in results) and not findings
    return {'version': 1, 'fixtureKind': 'IndependentFiveRoomLong', 'executionFinished': True, 'acceptancePassed': passed, 'complete': False,
        'source': 'Actual Windows UDP / NGO; stationary Simulation', 'headsets': 0, 'hosts': 1, 'networkCapacityAccepted': False,
        'participants': len(native), 'durationSecondsPerRoom': 900, 'playerBuildReceipt': v.receipt, 'toolFingerprint': tool, 'poseContinuity': None,
        'pauseIsolation': pause, 'rooms': results, 'nativeLogFindings': findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--players-per-room', type=int, choices=range(1, 6), default=5)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args(); args.duration = 900; args.job_workers = 2; args.visible_room = 0; args.check = True
    vm.verify_player(args); tool = fingerprint(); v = vm.Venue(args, artifact_family='desktop-long'); report = None
    try: report = run(v, args, tool)
    except BaseException as error: v.stage('failed', errorType=type(error).__name__); raise
    finally:
        cleaned = v.cleanup()
        if report is not None:
            if fingerprint() != tool: raise RuntimeError('Independent long tool sources changed during execution')
            report['complete'] = cleaned and report['acceptancePassed']; v.save('independent-checks.json', report)
        print('Artifacts:', v.directory, flush=True)
        if not cleaned: raise RuntimeError('Independent cleanup / snapshot failed')
    if not report or not report['complete']: raise RuntimeError('Independent continuity failed; sealed evidence retained')
    print('PASS: five independent original-admission worlds / 15 minutes each / full replay / individual results', flush=True)


if __name__ == '__main__': main()
