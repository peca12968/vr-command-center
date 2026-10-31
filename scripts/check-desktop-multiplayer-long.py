"""One real 15-minute Linked Windows world, up to 25 stationary PC clients.

Every saved Running frame and original admission is audited. This is one host,
headless Simulation, not active input, device, LAN or full network-capacity proof.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


long = load('multiplayer_single_long', 'check-desktop-long.py')
capacity = load('multiplayer_capacity', 'check-desktop-capacity.py')
debrief = long.debrief
vm = long.vm


class DiagnosticVenue(vm.Venue):
    def __init__(self, args, **options):
        self.continuity_programs = []
        super().__init__(args, **options)

    def launch(self, name, config, visible=False, *, extra_args=()):
        if getattr(self.args, 'pose_continuity', False):
            directory = self.runtime_directory / 'continuity' / f'p{len(self.continuity_programs) + 1:03d}'
            directory.parent.mkdir(exist_ok=True)
            loop = config['role'] == 'Server'
            self.continuity_programs.append({'name': name, 'role': config['role'], 'directory': str(directory), 'loop': loop})
            extra_args = (*extra_args, '--vr-pose-continuity', str(directory), *(['--vr-pose-continuity-loop'] if loop else []))
        return super().launch(name, config, visible, extra_args=extra_args)

    def finish_continuity(self):
        if not self.continuity_programs: return None
        for program in self.continuity_programs: (Path(program['directory']) / 'finish.request').write_text('stop collection after all sealed individual receipts\n')
        self.wait(lambda: all((Path(p['directory']) / 'report.json').is_file() for p in self.continuity_programs), 20, 'sparse continuity reports')
        analyzer = load('finish_sparse_validation', 'analyze-pose-continuity.py')
        for program in self.continuity_programs:
            report = vm.read_json(Path(program['directory']) / 'report.json')
            analyzer.validate(report, program['role'], program['loop'])
            if program['role'] == 'Client':
                import re
                ids = re.findall(r'VR_CLIENT_CONNECTED id=(\d+)', debrief.log_text(self, program['name']))
                if len(ids) != 1: raise ValueError('Diagnostic client did not retain one original native connection')
                program['connection'] = int(ids[0])
                if not any(s['point'] == 'PoseSend' and s['connection'] == program['connection'] and s['count'] > 0 for s in report['streams']):
                    raise ValueError('Client diagnostic has no original pose sends')
        result = {'version': 1, 'complete': True, 'programs': self.continuity_programs}
        self.save('multiplayer-continuity.json', result); return result


def fingerprint():
    digest = hashlib.sha256()
    for name in ['check-desktop-multiplayer-long.py', 'check-desktop-long.py', 'check-desktop-capacity.py',
                 'check-desktop-debrief.py', 'start-desktop-venue.py', 'start-desktop-demo.py', 'analyze-pose-continuity.py', 'analyze-pose-input.py']:
        digest.update(name.encode()); digest.update((ROOT / 'scripts' / name).read_bytes())
    return digest.hexdigest()


def roster_faults(row, players, stable_sequence, health):
    frame = row['packet']['frame']; actual = frame['players']
    if frame['phase'] != 'Running': return [{'playerId': None, 'reason': 'unexpectedSuspension'}] if frame['phase'] == 'Paused' else []
    expected = {p['id']: p for p in players}; faults = []
    if len(actual) != len(expected) or {p['id'] for p in actual} != set(expected):
        faults.append({'playerId': None, 'reason': 'rosterMismatch'})
    for identity, player in expected.items():
        own = next((p for p in actual if p['id'] == identity), None)
        reason = long.active_fault(row, identity, stable_sequence, health[identity])
        if reason is None and own['roomId'] != player['roomId']: reason = 'wrongRoom'
        if reason is None and own['health'] <= 0: reason = 'eliminatedBody'
        if reason: faults.append({'playerId': identity, 'reason': reason})
    return faults


class Continuity:
    def __init__(self, players, stable_sequence, health, *, replay=False):
        self.players, self.stable_sequence, self.health, self.replay = players, stable_sequence, health, replay
        self.frames = self.running = self.player_rows = self.bad = self.skipped = self.gaps = 0
        self.previous = self.tick = 0; self.elapsed = None; self.last = None; self.maximum_gap = 0
        self.reasons = Counter(); self.player_faults = Counter(); self.samples = []
        self.running_from = self.running_to = None

    def observe(self, row):
        packet = row['packet']; frame = packet['frame']; sequence = packet['sequence']
        if sequence <= self.previous or not self.tick <= frame['tick'] <= 18000: raise ValueError('World sequence or clock rewound / exceeded mission limit')
        if self.replay and sequence != self.previous + 1: raise ValueError('Full replay skipped a stored frame')
        if self.previous: self.skipped += sequence - self.previous - 1
        if self.elapsed is not None:
            gap = packet['elapsedMilliseconds'] - self.elapsed
            if gap < 0: raise ValueError('Capture elapsed time rewound')
            self.maximum_gap = max(self.maximum_gap, gap); self.gaps += gap >= 1500
        self.frames += 1; self.running += frame['phase'] == 'Running'
        if frame['phase'] == 'Running':
            self.player_rows += len(self.players)
            if self.running_from is None: self.running_from = packet['elapsedMilliseconds']
            self.running_to = packet['elapsedMilliseconds']
        faults = roster_faults(row, self.players, self.stable_sequence, self.health)
        self.bad += bool(faults)
        for fault in faults:
            self.reasons[fault['reason']] += 1
            if fault['playerId'] is not None: self.player_faults[fault['playerId']] += 1
            if len(self.samples) < 200: self.samples.append({'sequence': sequence, 'tick': frame['tick'], **fault})
        self.previous, self.tick, self.elapsed, self.last = sequence, frame['tick'], packet['elapsedMilliseconds'], row

    def result(self):
        return {'frames': self.frames, 'runningFrames': self.running, 'expectedParticipantObservations': self.player_rows,
                'badFrames': self.bad, 'reasonCounts': dict(self.reasons), 'perPlayerBadFrames': dict(self.player_faults), 'faultSamples': self.samples,
                'skippedLiveSequences': self.skipped, 'maximumCaptureGapMilliseconds': self.maximum_gap,
                'captureGapsAtLeast1500ms': self.gaps, 'finalSequence': self.previous, 'finalTick': self.tick,
                'runningCaptureFromMs': self.running_from, 'runningCaptureToMs': self.running_to,
                'passed': self.running > 0 and self.bad == 0 and (not self.replay or self.gaps == 0)}


def same_admissions(current, original):
    fields = ('id', 'admissionId', 'roomId', 'seat')
    return len(current) == len(original) and {tuple(p[f] for f in fields) for p in current} == {tuple(p[f] for f in fields) for p in original}


def replay(venue, entry, sealed, audit):
    expected = venue.frame(entry)
    request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    deadline = time.monotonic() + sealed['world']['durationMilliseconds'] / 4000 + 30
    venue.stage('multiplayer-full-replay', frames=sealed['world']['acceptedSequence'], participants=len(entry['players']))
    with urllib.request.urlopen(request, timeout=10) as response:
        for row in capacity.sse_frames(response):
            if time.monotonic() > deadline: raise RuntimeError('Full multiplayer replay exceeded its bound')
            audit.observe(row)
    if audit.previous != sealed['world']['acceptedSequence'] or audit.last != expected or audit.tick != 18000 or audit.last['packet']['frame']['phase'] != 'Ended':
        raise ValueError('Full replay final packet differs from the sealed world / deadline')
    return {**audit.result(), 'finalPacketAndStatisticsMatch': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--players-per-room', type=int, choices=range(1, 6), default=5)
    parser.add_argument('--pose-continuity', action='store_true', help='Explicit sparse 1200s diagnostic in all processes, server PlayerLoop only; no gameplay changes')
    args = parser.parse_args(); args.duration = 900; args.job_workers = 2; args.visible_room = 0; args.check = True
    vm.verify_player(args); tool = fingerprint(); venue = DiagnosticVenue(args, artifact_family='desktop-long'); report = None; live = None
    age = {'frameSamples': 0, 'heartbeatSamples': 0, 'maximumSourceAgeSeconds': -1, 'badSamples': 0}
    native, resources = [], []
    def memory(stage):
        value = capacity.memory_status(); capacity.require_memory(value)
        resources.append({'stage': stage, 'utc': datetime.now(timezone.utc).isoformat(), **value}); venue.save('multiplayer-resources.json', resources)
    try:
        venue.start(); memory('before-native')
        mission = venue.request('/api/missions', {'name': '25 PC 15-minute Linked mission', 'briefing': 'Stationary Simulation / original admissions / all saved frames', 'durationSeconds': 900,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 5, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        entry = venue.create(mission, [1, 2, 3, 4, 5], 'long-multi')
        for room in entry['roomIds']:
            for _ in range(args.players_per_room - 1):
                identity = str(uuid.uuid4()); state = venue.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': room, 'name': f'Long PC R{room}', 'headset': 'Quest3'}, role='Room' + str(room))
                entry['players'].append(next(p for p in state['players'] if p['id'] == identity))
        capacity.validate_roster(entry['players'], entry['roomIds'], args.players_per_room)
        venue.wait(lambda: venue.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'multiplayer world initialization')
        started = set()
        for index, player in enumerate(sorted(entry['players'], key=lambda p: (p['seat'], p['roomId'])), 1):
            memory('client-' + str(index)); name = entry['name'] + '-client-' + player['admissionId']
            ticket = venue.ticket(entry, player); venue.launch(name, venue.client_config(entry, ticket)); started.add(player['id'])
            native.append({'name': name, 'playerId': player['id'], 'admissionId': player['admissionId'], 'roomId': player['roomId'], 'seat': player['seat'], 'processId': venue.processes[name].pid})
            if index % 5 == 0:
                venue.wait(lambda: {p['id'] for p in venue.frame(entry)['packet']['frame']['players'] if p['connected'] and p['rig']['kind'] == 'Simulated'} == started, 100, 'native admission batch')
                venue.stage('multiplayer-admitting', participants=index, target=len(entry['players']))
        capacity.validate_frame(venue.wait(lambda: venue.connected(entry), 100, 'all original rigs'), entry['players'])
        venue.save('multiplayer-native-clients.json', native)
        venue.command(entry, 'SetMissionClock', missionClock={'autoEnd': True}); venue.command(entry, 'Begin')
        venue.command(entry, 'SetEnemies', enemies={'count': 5, 'behavior': 'Hold', 'autoAttack': True})
        venue.wait(lambda: {p['roomId'] for p in venue.frame(entry)['statistics'] if p['damageTaken'] > 0} == set(entry['roomIds']), 25, 'AI damage in all five rooms')
        off = venue.command(entry, 'SetEnemies', enemies={'count': 5, 'behavior': 'Hold', 'autoAttack': False}); stable_sequence = off['session']['sequence']
        stable = venue.wait(lambda: (f if not (f := venue.frame(entry))['packet']['frame']['autoAttack'] and f['packet']['observedSequence'] >= stable_sequence else None), 10, 'stable damage policy')
        health = {p['id']: p['health'] for p in stable['packet']['frame']['players']}
        if set(health) != {p['id'] for p in entry['players']} or any(not 0 < h <= 100 for h in health.values()): raise RuntimeError('All original participants must survive initial AI damage')
        latest_expiry = max(datetime.fromisoformat(p['ticketExpiresAtUtc']) for p in entry['players'])
        live = Continuity(entry['players'], stable_sequence, health); after_expiry = None; captured_start = None
        deadline = time.monotonic() + 990; next_progress = 0
        request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=live', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
        with urllib.request.urlopen(request, timeout=5) as response:
            kind = ''
            for raw in response:
                if time.monotonic() > deadline: raise RuntimeError('Multiplayer mission did not finish within its observation bound')
                if any(p.poll() is not None for p in venue.processes.values()): raise RuntimeError('An owned native process exited during the mission')
                line = raw.decode('utf-8').strip()
                if line.startswith('event: '): kind = line[7:]
                if not line.startswith('data: '): continue
                data = json.loads(line[6:]); now = datetime.now(timezone.utc)
                if kind == 'header': captured_start = datetime.fromisoformat(data['header']['captureStartedAtUtc']); continue
                if kind == 'frame':
                    live.observe(data); packet = data['packet']; age['frameSamples'] += 1
                    seconds = (now - captured_start).total_seconds() - packet['elapsedMilliseconds'] / 1000
                    if after_expiry is None and now > latest_expiry and packet['frame']['phase'] == 'Running' and not roster_faults(data, entry['players'], stable_sequence, health):
                        if not same_admissions(venue.state(entry)['players'], entry['players']): raise RuntimeError('An original admission / room / seat changed after ticket expiry')
                        after_expiry = {'utc': now.isoformat(), 'tick': packet['frame']['tick'], 'participants': len(entry['players']), 'allOriginalAdmissions': True}
                    if time.monotonic() >= next_progress:
                        next_progress = time.monotonic() + 30; memory('running-' + str(packet['frame']['tick']))
                        venue.save('multiplayer-live.json', {'continuity': live.result(), 'sourceAge': age, 'afterTicketExpiry': after_expiry})
                        venue.stage('multiplayer-running', tick=packet['frame']['tick'], targetTick=18000, participants=len(entry['players']), badFrames=live.bad, badSourceAges=age['badSamples'])
                elif kind == 'status':
                    age['heartbeatSamples'] += 1; seconds = (now - datetime.fromisoformat(data['capturedAtUtc'])).total_seconds()
                    if data['complete']: break
                else: continue
                age['maximumSourceAgeSeconds'] = max(age['maximumSourceAgeSeconds'], seconds)
                age['badSamples'] += not -1 <= seconds < 1.5
        sealed = venue.seal(entry)
        delivery = venue.wait_for_player_results(entry)
        if not delivery['allAcknowledged'] or len(delivery['phases']) != len(native): raise RuntimeError('Not every original player acknowledged the sealed result')
        final_state = venue.state(entry); results = []
        for row in native:
            player = next(p for p in entry['players'] if p['id'] == row['playerId']); result = debrief.final_result(venue, row['name'])
            debrief.validate_result(result, entry, player, sealed)
            if result['finalStreamSequence'] != final_state['combatStream']['acceptedSequence']: raise ValueError('Player combat seal differs')
            if debrief.log_text(venue, row['name']).count('VR_CLIENT_CONNECTED id=') != 1: raise ValueError('An original player reconnected during continuity check')
            results.append(result)
        if after_expiry is None or not same_admissions(final_state['players'], entry['players']): raise ValueError('Original expired-ticket connections / admissions not retained')
        csv = capacity.practice.save_report(venue, entry, sealed['statistics'])
        diagnostics = venue.finish_continuity()
        recorded = replay(venue, entry, sealed, Continuity(entry['players'], stable_sequence, health, replay=True))
        events = venue.request(f'/api/sessions/{entry["id"]}/events?after=0&limit=500')
        expiry = [e for e in events if e['kind'] == 'ControlApplied' and e['payload'].get('clockExpiration')]
        if len(expiry) != 1 or expiry[0]['payload']['clockExpiration']['tick'] != 18000: raise ValueError('Expected one exact tick18000 automatic End')
        findings = capacity.native_log_findings(venue.directory)
        passed = live.result()['passed'] and age['badSamples'] == 0 and recorded['passed'] and not findings
        report = {'version': 1, 'complete': False, 'executionFinished': True, 'acceptancePassed': passed, 'headsets': 0, 'hosts': 1,
            'source': 'Actual Windows UDP / NGO; stationary headless Simulation', 'networkCapacityAccepted': False,
            'participants': len(native), 'durationSeconds': 900, 'toolFingerprint': tool, 'playerBuildReceipt': venue.receipt,
            'stableSequence': stable_sequence, 'stableHealthByPlayer': health, 'latestTicketExpiryUtc': latest_expiry.isoformat(),
            'originalConnectionsAfterExpiry': after_expiry, 'live': live.result(), 'sourceAge': age, 'replay': recorded,
            'nativeLogFindings': findings, 'clientResults': results, 'sealed': sealed, 'finalReportCsv': csv, 'automaticEnd': expiry[0], 'poseContinuity': diagnostics}
    except BaseException as error:
        venue.save('multiplayer-live.json', {'continuity': live.result() if live else None, 'sourceAge': age}); venue.stage('failed', errorType=type(error).__name__); raise
    finally:
        cleanup = venue.cleanup()
        if report is not None:
            if fingerprint() != tool: raise RuntimeError('Multiplayer tool sources changed during execution')
            report['complete'] = cleanup and report['acceptancePassed']; venue.save('multiplayer-checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Multiplayer cleanup failed')
    if not report or not report['complete']: raise RuntimeError('Multiplayer continuity acceptance failed; sealed counterexamples retained')
    print('PASS: all original PC participants / 15 minutes / full replay / exact individual results', flush=True)


if __name__ == '__main__': main()
