"""Calibrate sparse diagnostics with two real PC clients and owned upstream loss.

No graphics, input / pose injection, security settings or external network.
Does not claim to reproduce or solve the natural 25-client intermittent fault.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
multi = load('calibration_multi', 'check-desktop-multiplayer-long.py')
loss = load('calibration_gate', 'check-desktop-pose.py')
analysis = load('calibration_analysis', 'analyze-pose-continuity.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args(); args.pose_continuity = True; args.duration = 120; args.job_workers = 2; args.visible_room = 0; args.check = False
    try:
        multi.vm.verify_player(args, python_listener=True)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    venue = multi.DiagnosticVenue(args, artifact_family='desktop-long'); gate = None; report = None
    try:
        venue.start()
        mission = venue.request('/api/missions', {'name': 'Sparse continuity controlled-loss calibration', 'briefing': 'Two native stationary Simulation clients; one deliberate upstream dropout', 'durationSeconds': 120,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        entry = venue.create(mission, [3], 'continuity'); primary = entry['players'][0]
        identity = str(uuid.uuid4()); state = venue.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': 3, 'name': 'Calibration peer', 'headset': 'Quest3'}, role='Room3')
        entry['players'].append(next(p for p in state['players'] if p['id'] == identity))
        venue.wait(lambda: venue.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'recording')
        gate = loss.LossGate(entry['port'])
        for index, player in enumerate(entry['players']):
            config = venue.client_config(entry, venue.ticket(entry, player))
            if index == 0: config['port'] = gate.port
            venue.launch('continuity-player-' + str(index), config)
        venue.wait(lambda: venue.connected(entry), 45, 'two original native clients'); venue.command(entry, 'Begin')
        start = venue.frame(entry)['packet']['elapsedMilliseconds']; venue.stage('sparse-calibration-baseline', seconds=15)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if not venue.connected(entry): raise RuntimeError('Calibration baseline lost a native body')
            time.sleep(.15)
        mark = datetime.now(timezone.utc).isoformat(); gate.until = time.monotonic() + 1.2
        venue.stage('sparse-calibration-loss', seconds=1.2)
        def stale():
            value = venue.frame(entry, measure=True); players = value['packet']['frame']['players']
            own = next(p for p in players if p['id'] == primary['id']); peer = next(p for p in players if p['id'] != primary['id'])
            return value if not own['connected'] and own['rig']['kind'] == 'None' and peer['connected'] else None
        inactive = venue.wait(stale, 5, 'controlled primary pose expiry while peer remains active')
        recovered = venue.wait(lambda: venue.connected(entry), 10, 'same original admission recovery')
        finish_mark = datetime.now(timezone.utc).isoformat()
        if not gate.dropped or gate.error or not multi.same_admissions(venue.state(entry)['players'], entry['players']): raise ValueError('Controlled gate / admission identity differs')
        end = recovered['packet']['elapsedMilliseconds']; sealed = venue.seal(entry)
        if not venue.wait_for_player_results(entry)['allAcknowledged']: raise ValueError('Calibration results not acknowledged')
        results = []
        for index, player in enumerate(entry['players']):
            result = multi.debrief.final_result(venue, 'continuity-player-' + str(index)); multi.debrief.validate_result(result, entry, player, sealed); results.append(result)
        diagnostics = venue.finish_continuity()
        report = {'version': 1, 'complete': False, 'executionFinished': True, 'acceptancePassed': False, 'fixtureKind': 'ControlledUpstreamLossCalibration',
            'headsets': 0, 'hosts': 1, 'participants': 2, 'sealed': sealed, 'clientResults': results, 'poseContinuity': diagnostics,
            'replay': {'runningCaptureFromMs': start, 'runningCaptureToMs': end},
            'controlledLoss': {'startedAtUtc': mark, 'recoveredAtUtc': finish_mark, 'requestedSeconds': 1.2, 'droppedDatagrams': gate.dropped,
                'staleSequence': inactive['packet']['sequence'], 'recoveredSequence': recovered['packet']['sequence']}}
    finally:
        if gate: gate.close()
        cleanup = venue.cleanup()
        if report is not None: venue.save('multiplayer-checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Calibration cleanup failed')
    result = analysis.analyze(venue.directory)
    if not result['complete']: raise ValueError('Diagnostic clocks do not permit a calibrated join')
    server = next(p for p in result['programs'] if p['role'] == 'Server'); primary_connection = next(p['connection'] for p in result['programs'] if p['name'] == 'continuity-player-0')
    if not any(g['point'] == 'PoseReceive' and g['connection'] == primary_connection and g['toSeconds'] - g['fromSeconds'] > .8 for g in server['activeGaps']):
        raise ValueError('Controlled receive gap missing from sparse evidence')
    if not any(b['connection'] == primary_connection and b['poseAgeSeconds'] > .5 for b in server['activeBodyLosses']): raise ValueError('Controlled body expiry missing')
    primary_report = next(p for p in result['programs'] if p['name'] == 'continuity-player-0')
    if any(g['point'] == 'PoseSend' and g['toSeconds'] - g['fromSeconds'] > .2 for g in primary_report['activeGaps']): raise ValueError('Calibration confounded by client send gaps')
    report['complete'] = True; report['calibrationPassed'] = True; venue.save('multiplayer-checks.json', report)
    venue.save('pose-continuity-analysis.json', result)
    print('PASS: real sparse reports / controlled upstream receive gap / peer continuity / original admissions / exact results; natural root remains unproven', flush=True)


if __name__ == '__main__': main()
