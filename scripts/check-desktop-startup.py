"""Witness accepted Begin versus actual native world application. No gameplay injection."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import urllib.request
import uuid
from venue_http_gate import VenueHttpGate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief); vm = debrief.venue_module


def applied(packet, sequence):
    return packet['observedSequence'] >= sequence and packet['frame']['phase'] == 'Running' and packet['frame']['tick'] > 0 and not packet['suspended']


def witness(packet):
    return {key: packet[key] for key in ('sequence', 'observedSequence', 'elapsedMilliseconds', 'suspended')} | {'phase': packet['frame']['phase'], 'tick': packet['frame']['tick']}


class StartupVenue(vm.Venue):
    def __init__(self, args):
        super().__init__(args, artifact_family='desktop-clock-faults'); self.use_gate = False; self.proxy = None; self.gates = []
    def launch(self, name, config, visible=False, *, extra_args=()):
        if config['role'] == 'Server' and self.use_gate:
            self.proxy = VenueHttpGate(self.base, config['sessionId']).start(); self.gates.append(self.proxy)
            config = {**config, 'managementApiUrl': self.proxy.base}
        super().launch(name, config, visible, extra_args=extra_args)


def replay(v, entry, sealed, sequence, controlled):
    request = urllib.request.Request(v.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4', headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    previous = 0; first = None; suspended = 0; last = None
    with urllib.request.urlopen(request, timeout=10) as response:
        kind = ''
        for raw in response:
            line = raw.decode('utf-8').strip()
            if line.startswith('event: '): kind = line[7:]
            if kind != 'frame' or not line.startswith('data: '): continue
            row = json.loads(line[6:]); packet = row['packet']
            if packet['sequence'] != previous + 1: raise ValueError('Startup full replay skipped a saved frame')
            previous = packet['sequence']; last = row
            suspended += packet['suspended'] and packet['frame']['phase'] == 'Preparing' and packet['frame']['tick'] == 0
            if first is None and applied(packet, sequence): first = witness(packet)
    if previous != sealed['world']['acceptedSequence'] or first is None or last != v.frame(entry) or controlled and suspended == 0:
        raise ValueError('Startup replay / Begin witness / controlled suspension differs')
    return {'frames': previous, 'firstApplied': first, 'suspendedPreparingFrames': suspended, 'finalPacketAndStatisticsMatch': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--trials', type=int, choices=range(1, 6), default=3)
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    args = parser.parse_args(); args.duration = 180; args.visible_room = 0; args.job_workers = 2; args.check = True
    vm.verify_player(args); v = StartupVenue(args); report = None
    tool = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        v.start(); results = []
        for trial in range(args.trials + 1):
            controlled = trial == args.trials; v.use_gate = controlled
            mission = v.request('/api/missions', {'name': 'Begin witness - Simulation', 'briefing': 'Accepted policy / real world / controlled management calibration', 'durationSeconds': 1800,
                'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 2, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
            entry = v.create(mission, [5], 'startup-' + str(trial)); identity = str(uuid.uuid4())
            state = v.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'name': 'Startup peer', 'roomId': 5, 'headset': 'Quest3'}, role='Room5')
            entry['players'].append(next(p for p in state['players'] if p['id'] == identity))
            v.wait(lambda: v.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'startup recording')
            names = {}
            for player in entry['players']:
                name = entry['name'] + '-client-' + player['admissionId']; names[player['id']] = name
                v.launch(name, v.client_config(entry, v.ticket(entry, player)))
            v.wait(lambda: v.connected(entry), 90, 'two original startup clients')
            observations = []; before = v.frame(entry, measure=True)
            if controlled:
                v.proxy.block('management')
                v.wait(lambda: v.proxy.snapshot()['counts']['managementBlocked'] > 0, 5, 'known management block')
            command = v.command(entry, 'Begin'); accepted = time.monotonic(); sequence = command['session']['sequence']
            v.save(entry['name'] + '-begin.json', {'acceptedAtUtc': datetime.now(timezone.utc).isoformat(), 'response': command, 'before': witness(before['packet']), 'controlled': controlled})
            if controlled:
                value = v.wait(lambda: (f if (f := v.frame(entry))['packet']['suspended'] else None), 8, 'known Preparing suspension')
                packet = value['packet']; observations.append(witness(packet))
                if applied(packet, sequence) or packet['frame']['tick'] != 0 or packet['frame']['phase'] != 'Preparing' or v.state(entry)['state'] != 'Running':
                    raise ValueError('Accepted Begin was confused with source application')
                v.proxy.release()
            release = time.monotonic(); deadline = release + 15; first = None
            while time.monotonic() < deadline:
                row = v.frame(entry, measure=True); packet = row['packet']; observations.append(witness(packet))
                v.save(entry['name'] + '-observations.json', observations)
                if applied(packet, sequence): first = witness(packet); break
                time.sleep(.1)
            first_observed = time.monotonic()
            if first is None: raise RuntimeError('Native Begin application exceeded original 15 second observation bound')
            if not all(p['connected'] and p['rig']['kind'] == 'Simulated' for p in row['packet']['frame']['players']) or len(row['packet']['frame']['players']) != 2:
                raise ValueError('Startup world lost its original native rigs')
            sealed = v.seal(entry); delivery = v.wait_for_player_results(entry)
            if not delivery['allAcknowledged'] or len(delivery['phases']) != 2: raise ValueError('Startup final receipts incomplete')
            for player in entry['players']:
                debrief.validate_result(debrief.final_result(v, names[player['id']]), entry, player, sealed)
            recorded = replay(v, entry, sealed, sequence, controlled)
            results.append({'controlled': controlled, 'sessionId': entry['id'], 'acceptedSequence': sequence, 'firstApplied': first,
                'secondsAfterResponse': first_observed - accepted, 'secondsAfterRelease': first_observed - release,
                'observedBeforeEnd': observations, 'replay': recorded, 'sealed': sealed})
            v.stop_round(entry)
            if controlled: v.save('startup-gate.json', v.proxy.snapshot())
            v.stage('startup-trial-complete', trial=trial + 1, controlled=controlled, firstApplied=first)
        report = {'complete': False, 'executionFinished': True, 'source': 'Actual same-host Windows UDP / NGO; Simulation', 'headsets': 0, 'networkCapacityAccepted': False,
            'toolFingerprint': tool, 'playerBuildReceipt': v.receipt, 'trials': results, 'causalRootProven': False}
    except BaseException as error:
        v.stage('failed', errorType=type(error).__name__); raise
    finally:
        cleaned = v.cleanup(); gates_closed = True
        for gate in v.gates:
            try: gate.close()
            except Exception: gates_closed = False
        if report is not None:
            report['complete'] = cleaned and gates_closed; v.save('startup-checks.json', report)
        if not cleaned or not gates_closed: raise RuntimeError('Startup actor / proxy cleanup incomplete')
    print('PASS: direct native startup witnesses and controlled accepted-but-not-applied Begin', flush=True)


if __name__ == '__main__': main()
