"""Real Windows player mission-end receipt / admission / sealed-ledger check. Simulation only."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('debrief_venue', ROOT / 'scripts/start-desktop-venue.py')
venue_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(venue_module)


class DebriefVenue(venue_module.Venue):
    def launch(self, name, config, visible=False, *, extra_args=()):
        if self.args.host and config['role'] == 'Server':
            entry = next(e for e in self.rounds if name == e['name'] + '-server')
            config = {**config, 'role': 'Host', 'joinTicket': self.ticket(entry, entry['players'][0])}
            visible = self.args.interactive
        super().launch(name, config, visible, extra_args=extra_args)


def log_text(venue, name):
    path = venue.directory / (name + '.log')
    return path.read_text(encoding='utf-8', errors='replace') if path.exists() else ''


def final_result(venue, name):
    lines = [line.split('VR_CLIENT_DEBRIEF_FINAL ', 1)[1] for line in log_text(venue, name).splitlines() if 'VR_CLIENT_DEBRIEF_FINAL ' in line]
    if len(lines) > 1: raise ValueError('Client accepted more than one final result')
    return json.loads(lines[0]) if lines else None


def validate_result(result, entry, player, sealed):
    if not sealed['world']['complete'] or sealed['statistics']['pendingTelemetry']:
        raise ValueError('Result is not backed by both final seals')
    expected = next(p for p in sealed['statistics']['players'] if p['playerId'] == player['id'])
    if result['version'] != 1 or result['sessionId'] != entry['id'] or result['playerId'] != player['id'] or result['admissionId'] != player['admissionId']:
        raise ValueError('Debrief identity is not the original admission')
    if result['origin'] != 'Simulation' or result['roomId'] != player['roomId'] or result['throughSequence'] != sealed['statistics']['throughSequence']:
        raise ValueError('Debrief source / room / ledger sequence differs')
    for field in ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent']:
        if result[field] != expected[field]: raise ValueError('Debrief / sealed statistics differ: ' + field)
    if result['worldSequence'] != sealed['world']['acceptedSequence'] or result['streamId'] != sealed['world']['header']['streamId']:
        raise ValueError('Debrief world seal differs')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--runtime-root', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--interactive', action='store_true', help='Require one real Space shot before End')
    mode.add_argument('--cancel-preparing', action='store_true', help='End before Begin; verify the zero-event sealed ledger result')
    parser.add_argument('--host', action='store_true', help='First player is the native host; verify it waits for the peer result before shutdown')
    parser.add_argument('--inspect-seconds', type=int, default=0, choices=range(0, 301), metavar='0..300')
    args = parser.parse_args(); args.duration = 300; args.job_workers = 2; args.visible_room = 3; args.check = True
    if os.name != 'nt' or not args.player_exe.is_file() or not args.api_dll.is_file(): parser.error('Build Windows and API first')
    venue_module.verify_player(args)
    venue = DebriefVenue(args, artifact_family='desktop-debrief')
    try:
        venue.start()
        mission = venue.request('/api/missions', {'name': 'PC mission end debrief', 'briefing': 'Native Simulation receipt check', 'durationSeconds': 300,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False},
            'props': [{'assetId': 'barrel', 'position': {'x': -4.125, 'y': 0, 'z': -1}, 'yawDegrees': 0}]}, expected=201)
        entry = venue.create(mission, [3], 'debrief'); entry['dynamicRoster'] = True
        for index in range(2):
            identity = str(uuid.uuid4())
            state = venue.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': 3, 'name': 'Debrief peer ' + str(index), 'headset': 'Quest3'}, role='Room3')
            entry['players'].append(next(p for p in state['players'] if p['id'] == identity))
        venue.wait(lambda: venue.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'world initialization')
        tickets = []
        for index, player in enumerate(entry['players']):
            ticket = venue.ticket(entry, player); tickets.append(ticket)
            if not args.host or index != 0:
                venue.launch('debrief-player-' + str(index), venue.client_config(entry, ticket), visible=args.interactive and index == 0)
        venue.wait(lambda: venue.connected(entry), 90, 'three accepted rigs')
        removed = entry['players'].pop()
        venue.request(f'/api/sessions/{entry["id"]}/players/{removed["id"]}', role='Room3', admission=removed['admissionId'], method='DELETE', expected=204)
        venue.wait(lambda: 'VR_CLIENT_DISCONNECTED' in log_text(venue, 'debrief-player-2'), 15, 'removed admission disconnect')
        if not args.cancel_preparing: venue.command(entry, 'Begin')
        if args.cancel_preparing:
            pass
        elif args.interactive:
            venue.stage('awaiting-shot', instruction='Press Space once in the visible native player')
            venue.wait(lambda: next(p for p in venue.frame(entry)['statistics'] if p['playerId'] == entry['players'][0]['id'])['ammoUsed'] >= 1, 120, 'real Space shot')
            venue.command(entry, 'Pause')
        else:
            venue.command(entry, 'SetEnemies', enemies={'count': 1, 'behavior': 'Hold', 'autoAttack': True})
            venue.wait(lambda: any(p['damageTaken'] > 0 for p in venue.frame(entry)['statistics']), 20, 'real AI damage')
        sealed = venue.seal(entry)
        results = []
        for index, player in enumerate(entry['players']):
            name = 'debrief-server' if args.host and index == 0 else 'debrief-player-' + str(index)
            result = venue.wait(lambda n=name: final_result(venue, n), 30, name + ' final receipt')
            results.append(validate_result(result, entry, player, sealed))
            venue.wait(lambda n=name: ('VR_SERVER_STOPPED host=True' if args.host and index == 0 else 'VR_CLIENT_DISCONNECTED') in log_text(venue, n), 15, name + ' acknowledged disconnect')
        server = log_text(venue, 'debrief-server')
        if server.count('VR_SERVER_DEBRIEF_ACK ') != 2 or 'VR_SERVER_DEBRIEF_TIMEOUT ' in server:
            raise ValueError('Results were not acknowledged by exactly the two remaining admissions')
        if 'VR_CLIENT_DEBRIEF_' in log_text(venue, 'debrief-player-2'): raise ValueError('Removed admission received debrief data')
        stream = venue.state(entry)['combatStream']
        if not stream['sealed'] or any(r['streamId'] != stream['streamId'] or r['finalStreamSequence'] != stream['acceptedSequence'] for r in results):
            raise ValueError('Debrief final combat stream seal differs')
        if not args.host:
            venue.launch('debrief-ended-ticket', venue.client_config(entry, tickets[0]))
            venue.wait(lambda: 'VR_CLIENT_ADMISSION_REJECTED' in log_text(venue, 'debrief-ended-ticket'), 20, 'ended ticket rejection')
            if 'VR_CLIENT_DEBRIEF_' in log_text(venue, 'debrief-ended-ticket'): raise ValueError('Ended ticket received debrief data')
        if venue.request(f'/api/sessions/{entry["id"]}/statistics') != sealed['statistics']: raise ValueError('Final ledger changed after result / rejection')
        report = {'complete': False, 'source': 'Actual Windows Unity UDP; Simulation rigs', 'headsets': 0,
            'results': results, 'sealed': sealed, 'removedPlayer': removed['id'], 'acknowledgedResults': 2, 'interactive': args.interactive,
            'host': args.host, 'cancelPreparing': args.cancel_preparing,
            'checks': ['two targeted final results match sealed statistics and replay', 'removed admission received no result',
                       'acknowledged delivery precedes disconnect',
                       'host shutdown waits for peer ack' if args.host else 'ended ticket rejected without result or ledger mutation']}
        venue.save('debrief-result.json', report)
        if args.inspect_seconds:
            venue.stage('inspect-result', inspectSeconds=args.inspect_seconds)
            deadline = time.monotonic() + args.inspect_seconds
            while time.monotonic() < deadline and not (venue.directory / 'inspected.done').exists(): time.sleep(.25)
        venue.evidence.extend(report['checks'])
        args.check = False; venue.summary()
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__); raise
    finally:
        if not venue.cleanup() and sys.exc_info()[0] is None: raise RuntimeError('Debrief fixture cleanup failed')
    report['complete'] = True; venue.save('debrief-result.json', report); venue.stage('passed', checks=len(report['checks']))


if __name__ == '__main__': main()
