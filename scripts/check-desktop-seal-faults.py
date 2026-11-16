"""Real PC pending-result safety while combat seal or final statistics delivery is unavailable."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import time
import urllib.request
from venue_http_gate import VenueHttpGate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('seal_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)
vm = debrief.venue_module


def fingerprint():
    digest = hashlib.sha256()
    for name in ['check-desktop-seal-faults.py', 'venue_http_gate.py', 'check-desktop-debrief.py', 'start-desktop-venue.py']:
        digest.update(name.encode()); digest.update((ROOT / 'scripts' / name).read_bytes())
    return digest.hexdigest()


class SealVenue(vm.Venue):
    proxy = None
    def launch(self, name, config, visible=False, *, extra_args=()):
        if config['role'] == 'Server':
            self.proxy = VenueHttpGate(self.base, config['sessionId'],
                                      allow_recovery_reads=bool(getattr(self.args, 'recovery_exe', None))).start()
            config = {**config, 'managementApiUrl': self.proxy.base}
        super().launch(name, config, visible, extra_args=extra_args)


def replay(venue, entry, sealed):
    expected = venue.frame(entry); previous, last = 0, None
    request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    deadline = time.monotonic() + sealed['world']['durationMilliseconds'] / 4000 + 15
    with urllib.request.urlopen(request, timeout=5) as response:
        kind = ''
        for raw in response:
            if time.monotonic() > deadline: raise RuntimeError('Replay observation exceeded its bound')
            line = raw.decode().strip()
            if line.startswith('event: '): kind = line[7:]
            if kind == 'frame' and line.startswith('data: '):
                row = json.loads(line[6:])
                if row['packet']['sequence'] != previous + 1: raise RuntimeError('Replay lost a source frame')
                previous, last = row['packet']['sequence'], row
    if previous != sealed['world']['acceptedSequence'] or last != expected: raise RuntimeError('Replay and exact final boundary differ')
    return {'frames': previous, 'finalPacketAndStatisticsMatch': True}


def csv_export(venue, entry):
    request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/report.csv', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read().decode('utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--mode', choices=['combat-seal', 'statistics'], default='combat-seal')
    args = parser.parse_args(); args.duration = 120; args.job_workers = 2; args.visible_room = 0; args.check = True
    vm.verify_player(args, python_listener=True); tool = fingerprint(); venue = SealVenue(args, artifact_family='desktop-seal-faults'); report = None; closed = False
    try:
        venue.start()
        mission = venue.request('/api/missions', {'name': 'PC final result outage', 'briefing': 'No final data before exact seals and server confirmation', 'durationSeconds': 60,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': True}, 'props': []}, expected=201)
        entry = venue.create(mission, [3], 'seal'); venue.clients([entry]); venue.command(entry, 'Begin')
        venue.wait(lambda: any(p['damageTaken'] > 0 for p in venue.frame(entry)['statistics']), 20, 'actual AI damage')
        venue.command(entry, 'Pause')
        venue.wait(lambda: venue.frame(entry)['packet']['frame']['phase'] == 'Paused', 10, 'accepted pause')
        venue.proxy.block(args.mode); venue.command(entry, 'End'); client = 'seal-client-3'
        blocked_key = 'combatSealBlocked' if args.mode == 'combat-seal' else 'statisticsBlocked'
        venue.wait(lambda: venue.proxy.snapshot()['counts'][blocked_key] > 0 and 'VR_CLIENT_DEBRIEF_PENDING ' in debrief.log_text(venue, client), 10, 'pending / selected unavailable route')
        observations = []; started = time.monotonic(); venue.stage('pending-without-confirmation', mode=args.mode)
        while time.monotonic() - started < 8:
            state = venue.state(entry); statistics = venue.request(f'/api/sessions/{entry["id"]}/statistics'); world = venue.request(f'/api/sessions/{entry["id"]}/world')
            if state['state'] != 'Ended' or debrief.final_result(venue, client) is not None or 'VR_CLIENT_DISCONNECTED' in debrief.log_text(venue, client):
                raise RuntimeError('Pending client ended early or received unconfirmed final data')
            if args.mode == 'combat-seal':
                if state['combatStream']['sealed'] or not statistics['pendingTelemetry'] or world['complete']: raise RuntimeError('Unavailable combat seal was incorrectly considered final')
                venue.request(f'/api/sessions/{entry["id"]}/report.csv', expected=409)
            else:
                if not state['combatStream']['sealed'] or statistics['pendingTelemetry'] or not world['complete']: raise RuntimeError('Statistics delivery fault must leave both real seals intact')
                if not csv_export(venue, entry).startswith('"reportVersion"'): raise RuntimeError('Sealed operator report was incorrectly withheld by a GameServer delivery outage')
            observations.append({'seconds': time.monotonic() - started, 'combatSealed': state['combatStream']['sealed'], 'pendingTelemetry': statistics['pendingTelemetry'], 'worldComplete': world['complete'], 'acceptedWorldSequence': world['acceptedSequence'], 'csvAvailable': args.mode == 'statistics'})
            time.sleep(.4)
        held = time.monotonic() - started; venue.proxy.release(); sealed = venue.seal(entry)
        if not venue.wait_for_player_results(entry)['allAcknowledged']: raise RuntimeError('Recovered result was not acknowledged')
        result = debrief.final_result(venue, client); debrief.validate_result(result, entry, entry['players'][0], sealed)
        if result['damageTaken'] <= 0 or result['health'] >= 100: raise RuntimeError('Actual damage was lost from the result')
        raw_csv = csv_export(venue, entry)
        rows = list(csv.DictReader(io.StringIO(raw_csv)))
        if len(rows) != 1 or rows[0]['sessionId'] != result['sessionId'] or rows[0]['origin'] != 'Simulation' or int(rows[0]['playerRoomId']) != result['roomId'] or rows[0]['playerId'] != result['playerId'] or rows[0]['streamId'] != result['streamId'] or int(rows[0]['throughSequence']) != result['throughSequence'] or int(rows[0]['finalStreamSequence']) != result['finalStreamSequence']:
            raise RuntimeError('Final CSV identity / boundaries differ from the targeted result')
        for field in ['ammoUsed', 'shotsHit', 'kills', 'damageTaken', 'hitsReceived', 'health']:
            if int(rows[0][field]) != result[field]: raise RuntimeError('Final CSV lost accepted combat data')
        if float(rows[0]['accuracyPercent']) != result['accuracyPercent']: raise RuntimeError('Final CSV accuracy differs from the accepted result')
        if 'VR_SERVER_DEBRIEF_TIMEOUT ' in debrief.log_text(venue, 'seal-server'): raise RuntimeError('Pending delivery hit its original application deadline')
        venue.proxy.close(); closed = True; gate = venue.proxy.snapshot()
        if gate['limitsTriggered'] or gate['activeTunnels'] or any(gate['counts'][key] for key in ['handlerErrors', 'routeRejected', 'capacityRejected']): raise RuntimeError('Fault proxy cleanup / scope invalid')
        report = {'complete': False, 'source': 'Actual Windows Unity; Simulation rig', 'headsets': 0, 'mode': args.mode, 'toolFingerprint': tool,
            'playerBuildReceipt': venue.receipt, 'heldSeconds': held, 'pendingSamples': observations, 'proxy': gate,
            'sealed': sealed, 'clientResult': result, 'finalCsvMatchesResult': True, 'replay': replay(venue, entry, sealed),
            'checks': ['real AI damage precedes End', 'selected route unavailable while management continues', 'pending client receives no final and stays connected during the outage',
                       'API combat/world finality distinguishes unavailable seal from unavailable statistics delivery', 'recovery seals exact boundaries and preserves original-admission result',
                       'acknowledgment occurs within the unchanged result deadline', 'entire replay / final CSV / ledger match', 'proxy and all owned writers stop before runtime snapshot']}
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__); raise
    finally:
        if venue.proxy: venue.proxy.release()
        cleanup = venue.cleanup()
        if venue.proxy and not closed: venue.proxy.close()
        if report is not None:
            if fingerprint() != tool: raise RuntimeError('Seal tool sources changed during the native run')
            report['complete'] = cleanup; venue.save('checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Seal outage cleanup failed')
    if not report or not report['complete']: raise RuntimeError('Seal outage incomplete')
    print('PASS: 8 native pending-result / seal checks; Simulation only', flush=True)


if __name__ == '__main__': main()
