"""Actual two-client participation, owned peer exit and replacement admission; Simulation only."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)
vm = debrief.venue_module

def fingerprint():
    result = hashlib.sha256()
    for name in ['scripts/check-desktop-readiness.py', 'scripts/start-desktop-venue.py', 'scripts/check-desktop-debrief.py', 'tests/browser/check-readiness-native.cjs']:
        result.update(name.encode()); result.update((ROOT / name).read_bytes())
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args(); args.duration = 300; args.job_workers = 2; args.visible_room = 0; args.check = True
    vm.verify_player(args); source = fingerprint(); venue = vm.Venue(args, artifact_family='desktop-readiness'); report = None
    venue.save('tool-source.json', {'fingerprint': source, 'apiBuildPath': str(args.api_dll.resolve())})
    try:
        venue.start()
        mission = venue.request('/api/missions', {'name': '雙玩家參戰狀態', 'briefing': 'Native Simulation, no injected poses', 'durationSeconds': 300,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        entry = venue.create(mission, [3], 'readiness'); entry['dynamicRoster'] = True
        identity = str(uuid.uuid4())
        state = venue.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': 3, 'name': 'Readiness peer', 'headset': 'Quest3'}, role='Room3')
        peer = next(player for player in state['players'] if player['id'] == identity); entry['players'].append(peer)
        venue.wait(lambda: venue.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'world initialization')
        path = f'/api/sessions/{entry["id"]}/readiness'
        captures = {'beforeClients': venue.request(path, role='Room3')}
        if any(row['canParticipate'] for row in captures['beforeClients']['players']): raise RuntimeError('Roster appeared online before clients started')
        for name, player in [('readiness-primary', entry['players'][0]), ('readiness-peer', peer)]:
            venue.launch(name, venue.client_config(entry, venue.ticket(entry, player)))
        def expected_ready(count):
            value = venue.request(path, role='Room3')
            return value if value['sourceState'] == 'Fresh' and sum(row['canParticipate'] for row in value['players']) == count else None
        captures['connected'] = venue.wait(lambda: expected_ready(2), 40, 'two real participating clients')
        venue.save('ready.json', {'source': 'Simulation', 'headsets': 0, 'baseUrl': venue.base, 'directory': str(venue.directory), 'runtimeDirectory': str(venue.runtime_directory),
            'sessionId': entry['id'], 'primaryId': entry['players'][0]['id'], 'peerId': identity, 'oldAdmission': peer['admissionId'], 'playerBuildReceipt': venue.receipt})
        venue.stage('native-ready', sessionId=entry['id'])
        venue.wait(lambda: (venue.directory / 'connected-seen.done').exists(), 80, 'browser connected state')
        venue.stop('readiness-peer')
        captures['disconnected'] = venue.wait(lambda: expected_ready(1), 20, 'peer exit reaches accepted world')
        if next(row for row in captures['disconnected']['players'] if row['playerId'] == identity)['state'] != 'PoseUnavailable': raise RuntimeError('Disconnected peer status differs')
        venue.stage('native-peer-offline')
        venue.wait(lambda: (venue.directory / 'disconnected-seen.done').exists(), 50, 'browser disconnected state')
        venue.request(f'/api/sessions/{entry["id"]}/players/{identity}', role='Room3', method='DELETE', expected=204, admission=peer['admissionId'])
        state = venue.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': 3, 'name': 'Readmitted peer', 'headset': 'Quest3'}, role='Room3')
        replacement = next(player for player in state['players'] if player['id'] == identity)
        if replacement['admissionId'] == peer['admissionId']: raise RuntimeError('Replacement reused an admission')
        entry['players'] = [entry['players'][0], replacement]
        captures['readmitted'] = venue.request(path, role='Room3')
        if next(row for row in captures['readmitted']['players'] if row['playerId'] == identity)['canParticipate']: raise RuntimeError('New admission inherited an old pose')
        venue.stage('native-readmitted', admissionId=replacement['admissionId'])
        venue.wait(lambda: (venue.directory / 'readmitted-seen.done').exists(), 50, 'browser replacement is not ready')
        venue.launch('readiness-replacement', venue.client_config(entry, venue.ticket(entry, replacement)))
        captures['reconnected'] = venue.wait(lambda: expected_ready(2), 40, 'replacement real client')
        venue.stage('native-reconnected')
        venue.wait(lambda: (venue.directory / 'ended-seen.done').exists(), 60, 'browser Begin / Pause / End and final status')
        if venue.state(entry)['state'] != 'Ended': raise RuntimeError('Browser did not end its owned session')
        captures['ended'] = venue.request(path, role='Room3')
        if captures['ended']['sourceState'] != 'Ended' or any(row['canParticipate'] for row in captures['ended']['players']): raise RuntimeError('Ended displayed as participating')
        sealed = venue.seal(entry)
        if not venue.wait_for_player_results(entry)['allAcknowledged']: raise RuntimeError('Player results not acknowledged')
        results = [debrief.validate_result(debrief.final_result(venue, process), entry, player, sealed)
                   for process, player in [('readiness-primary', entry['players'][0]), ('readiness-replacement', replacement)]]
        report = {'complete': False, 'source': 'Actual Windows Unity headless Simulation / real API / Chromium control UI', 'headsets': 0,
            'toolFingerprint': source, 'playerBuildReceipt': venue.receipt, 'captures': captures, 'sealed': sealed, 'results': results,
            'checks': ['roster is not device presence', 'two actual accepted native rigs', 'owned peer exit reflected', 'replacement admission cannot inherit old pose',
                       'new client restores only its own admission', 'browser Begin/Pause/End and source freshness', 'Ended never participating', 'both original-current results match exact seals']}
    finally:
        clean = venue.cleanup()
        if report is not None:
            if fingerprint() != source: raise RuntimeError('Native readiness tool source changed during the run')
            report['complete'] = clean; venue.save('checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not clean: raise RuntimeError('Native readiness fixture cleanup failed')
    if not report or not report['complete']: raise RuntimeError('Readiness acceptance incomplete')
    print('PASS: 8 native participation / admission / sealed-result checks; no headsets', flush=True)


if __name__ == '__main__': main()
