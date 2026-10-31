"""A genuine 15-minute Windows mission, with full recorded continuity and final ledger audit."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('long_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)
vm = debrief.venue_module


def fingerprint():
    digest = hashlib.sha256()
    for name in ['check-desktop-long.py', 'check-desktop-debrief.py', 'start-desktop-venue.py']:
        digest.update(name.encode()); digest.update((ROOT / 'scripts' / name).read_bytes())
    return digest.hexdigest()


def active_fault(row, player, stable_sequence, health):
    packet = row['packet']; frame = packet['frame']
    if frame['phase'] != 'Running': return 'unexpectedSuspension' if frame['phase'] == 'Paused' else None
    own = next((value for value in frame['players'] if value['id'] == player), None)
    if own is None or not own['connected'] or own['rig']['kind'] != 'Simulated': return 'inactiveBody'
    if packet['observedSequence'] >= stable_sequence and own['health'] != health: return 'changedHealth'
    return None


def audit_replay(venue, entry, sealed, stable_sequence, health, limit):
    expected = venue.frame(entry); previous, last, tick, running, gaps, faults = 0, None, 0, 0, 0, []
    elapsed = None; maximum_gap = 0; bad_count = 0
    request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    deadline = time.monotonic() + sealed['world']['durationMilliseconds'] / 4000 + 30
    venue.stage('full-replay', frames=sealed['world']['acceptedSequence'])
    with urllib.request.urlopen(request, timeout=10) as response:
        kind = ''
        for raw in response:
            if time.monotonic() > deadline: raise RuntimeError('Full replay exceeded its bound')
            line = raw.decode().strip()
            if line.startswith('event: '): kind = line[7:]
            if kind != 'frame' or not line.startswith('data: '): continue
            row = json.loads(line[6:]); packet = row['packet']; frame = packet['frame']
            if packet['sequence'] != previous + 1 or not tick <= frame['tick'] <= limit: raise RuntimeError('Recorded clock / sequence rewound or exceeded limit')
            if elapsed is not None:
                maximum_gap = max(maximum_gap, packet['elapsedMilliseconds'] - elapsed)
                gaps += packet['elapsedMilliseconds'] - elapsed >= 1500
            elapsed = packet['elapsedMilliseconds']; previous, tick, last = packet['sequence'], frame['tick'], row
            running += frame['phase'] == 'Running'
            fault = active_fault(row, entry['players'][0]['id'], stable_sequence, health)
            if fault:
                bad_count += 1
                if len(faults) < 200: faults.append({'sequence': previous, 'tick': tick, 'reason': fault})
    if previous != sealed['world']['acceptedSequence'] or last != expected or tick != limit or last['packet']['frame']['phase'] != 'Ended': raise RuntimeError('Replay final boundary differs from exact sealed world')
    return {'frames': previous, 'runningFrames': running, 'maximumCaptureGapMilliseconds': maximum_gap, 'captureGapsAtLeast1500ms': gaps,
        'badRunningFrames': bad_count, 'badFrameSamples': faults, 'finalPacketAndStatisticsMatch': True, 'passed': running > 0 and bad_count == 0 and gaps == 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args(); args.duration = 900; args.job_workers = 2; args.visible_room = 0; args.check = True
    vm.verify_player(args); tool = fingerprint(); venue = vm.Venue(args, artifact_family='desktop-long'); report = None
    live = {'frames': 0, 'heartbeatSamples': 0, 'maximumSourceAgeSeconds': -1, 'badAgeSamples': 0, 'badActiveFrames': 0, 'skippedLiveSequences': 0, 'faultSamples': []}
    try:
        venue.start()
        mission = venue.request('/api/missions', {'name': '15 minute native PC mission', 'briefing': 'Long countdown / original admission / damage ledger', 'durationSeconds': 900,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        entry = venue.create(mission, [3], 'long'); venue.clients([entry]); player = entry['players'][0]
        expires = datetime.fromisoformat(player['ticketExpiresAtUtc']); venue.command(entry, 'SetMissionClock', missionClock={'autoEnd': True}); venue.command(entry, 'Begin')
        venue.command(entry, 'SetEnemies', enemies={'count': 1, 'behavior': 'Hold', 'autoAttack': True})
        venue.wait(lambda: any(p['damageTaken'] > 0 for p in venue.frame(entry)['statistics']), 20, 'real AI damage')
        off = venue.command(entry, 'SetEnemies', enemies={'count': 1, 'behavior': 'Hold', 'autoAttack': False})
        stable_sequence = off['session']['sequence']
        stable = venue.wait(lambda: (f if not (f := venue.frame(entry))['packet']['frame']['autoAttack'] and f['packet']['observedSequence'] >= stable_sequence else None), 10, 'AI hold applied')
        health = stable['packet']['frame']['players'][0]['health']
        if not 0 < health < 100: raise RuntimeError('Long-lived participant must be alive with actual recorded damage')
        captured_start = None; last_sequence = 0; after_expiry = None; deadline = time.monotonic() + 990; next_progress = 0
        request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=live', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
        with urllib.request.urlopen(request, timeout=5) as response:
            kind = ''
            for raw in response:
                if time.monotonic() > deadline: raise RuntimeError('Long source did not finish within its observation bound')
                if any(process.poll() is not None for process in venue.processes.values()): raise RuntimeError('An owned native process exited during the long run')
                line = raw.decode().strip()
                if line.startswith('event: '): kind = line[7:]
                if not line.startswith('data: '): continue
                data = json.loads(line[6:]); now = datetime.now(timezone.utc)
                if kind == 'header': captured_start = datetime.fromisoformat(data['header']['captureStartedAtUtc']); continue
                if kind == 'frame':
                    packet = data['packet']; number = packet['sequence']; live['frames'] += 1
                    if last_sequence: live['skippedLiveSequences'] += number - last_sequence - 1
                    last_sequence = number
                    age = (now - captured_start).total_seconds() - packet['elapsedMilliseconds'] / 1000
                    fault = active_fault(data, player['id'], stable_sequence, health)
                    if fault:
                        live['badActiveFrames'] += 1
                        if len(live['faultSamples']) < 200: live['faultSamples'].append({'sequence': number, 'tick': packet['frame']['tick'], 'reason': fault})
                    if now > expires and after_expiry is None and packet['frame']['phase'] == 'Running' and not fault:
                        state = venue.state(entry)
                        if state['players'][0]['admissionId'] != player['admissionId']: raise RuntimeError('Original admission changed after ticket expiry')
                        after_expiry = {'utc': now.isoformat(), 'tick': packet['frame']['tick'], 'playerId': player['id'], 'admissionId': player['admissionId'], 'health': health}
                    if time.monotonic() >= next_progress:
                        next_progress = time.monotonic() + 30; venue.save('live-observations.json', live)
                        venue.stage('long-running', tick=packet['frame']['tick'], targetTick=18000, liveFrames=live['frames'], badActiveFrames=live['badActiveFrames'], badAgeSamples=live['badAgeSamples'])
                elif kind == 'status':
                    live['heartbeatSamples'] += 1; age = (now - datetime.fromisoformat(data['capturedAtUtc'])).total_seconds()
                    if data['complete']: break
                else: continue
                live['maximumSourceAgeSeconds'] = max(live['maximumSourceAgeSeconds'], age)
                if not -1 <= age < 1.5: live['badAgeSamples'] += 1
        sealed = venue.seal(entry)
        if not venue.wait_for_player_results(entry)['allAcknowledged']: raise RuntimeError('Long result was not acknowledged')
        result = debrief.final_result(venue, 'long-client-3'); debrief.validate_result(result, entry, player, sealed)
        if debrief.log_text(venue, 'long-client-3').count('VR_CLIENT_CONNECTED id=') != 1 or after_expiry is None: raise RuntimeError('Ticket-expiry continuity was not observed on one original connection')
        replay = audit_replay(venue, entry, sealed, stable_sequence, health, 18000)
        events = venue.request(f'/api/sessions/{entry["id"]}/events?after=0&limit=500')
        expiry = [e for e in events if e['kind'] == 'ControlApplied' and e['payload'].get('clockExpiration')]
        if len(expiry) != 1 or expiry[0]['payload']['clockExpiration']['tick'] != 18000: raise RuntimeError('Long mission did not produce one exact deadline End')
        passed = replay['passed'] and live['badActiveFrames'] == 0 and live['badAgeSamples'] == 0
        report = {'complete': False, 'executionFinished': True, 'acceptancePassed': passed, 'headsets': 0, 'source': 'Actual Windows Unity; stationary Simulation rig',
            'durationSeconds': 900, 'toolFingerprint': tool, 'playerBuildReceipt': venue.receipt, 'stableHealth': health, 'stableSequence': stable_sequence,
            'ticketExpiresAtUtc': player['ticketExpiresAtUtc'], 'originalConnectionAfterExpiry': after_expiry, 'live': live, 'replay': replay,
            'sealed': sealed, 'clientResult': result, 'automaticEnd': expiry[0]}
    except BaseException as error:
        venue.save('live-observations.json', live); venue.stage('failed', errorType=type(error).__name__); raise
    finally:
        cleanup = venue.cleanup()
        if report is not None:
            if fingerprint() != tool: raise RuntimeError('Long-run tool sources changed during execution')
            report['complete'] = cleanup and report['acceptancePassed']; venue.save('checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Long-run cleanup failed')
    if not report or not report['complete']: raise RuntimeError('Long-run continuity acceptance failed; exact seals / failures retained')
    print('PASS: 15-minute native mission / original admission / full continuity / exact seals', flush=True)


if __name__ == '__main__': main()
