"""Open an isolated control desk and run the VR missions its operator creates.

The helper owns this API only. It starts native Simulation servers and short-ticket
clients from its live roster; it never launches programs against the preview API.
"""
import argparse
import importlib.util
import ipaddress
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_venue', ROOT / 'scripts/start-desktop-venue.py')
venue_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(venue_module)

def configure_network(args):
    external = args.client_mode == 'external'
    if external and not args.advertise_address:
        raise ValueError('External mode requires --advertise-address; the helper does not guess a reachable LAN address')
    args.advertise_address = args.advertise_address or '127.0.0.1'
    args.listen_address = args.listen_address or ('0.0.0.0' if external else '127.0.0.1')
    advertised = ipaddress.IPv4Address(args.advertise_address); listen = ipaddress.IPv4Address(args.listen_address)
    if str(advertised) != args.advertise_address or advertised.packed[0] == 0 or advertised.packed[0] >= 224:
        raise ValueError('Advertise a canonical unicast IPv4 address, not a bind wildcard')
    if str(listen) != args.listen_address or listen.packed[0] >= 224:
        raise ValueError('Listen on a canonical IPv4 bind address')
    if not external and (args.advertise_address != '127.0.0.1' or args.listen_address not in ('127.0.0.1', '0.0.0.0')):
        raise ValueError('Local clients use loopback; use external mode for another address')
    if external and args.listen_address != '0.0.0.0' and args.listen_address != args.advertise_address:
        raise ValueError('A specific bind address must match the advertised endpoint')
    if external: args.visible_room = 0

def retain_results(venue, entry):
    if getattr(venue.args, 'client_mode', 'local') != 'external':
        venue.wait_for_player_results(entry)
        return time.monotonic() + getattr(venue.args, 'results_seconds', 30)
    if 'externalGraceUntil' not in entry:
        seconds = max(36, getattr(venue.args, 'results_seconds', 30))
        entry['externalGraceUntil'] = time.monotonic() + seconds
        entry['playerResults'] = {'phases': {}, 'allAcknowledged': None, 'scope': 'External client delivery is not observed by this launcher', 'serverRetentionSeconds': seconds}
        venue.save(entry['name'] + '-player-results.json', entry['playerResults'])
    return entry['externalGraceUntil']


def run(venue):
    venue.start()
    external = getattr(venue.args, 'client_mode', 'local') == 'external'
    ready = {'source': 'Simulation', 'headsets': None if external else 0, 'clientMode': 'External' if external else 'Local',
             'advertiseAddress': venue.args.advertise_address, 'listenAddress': venue.args.listen_address, 'baseUrl': venue.base, 'consoleUrl': venue.base + '/console/',
             'directory': str(venue.directory), 'runtimeDirectory': str(venue.runtime_directory), 'playerBuildReceipt': venue.receipt}
    venue.save('ready.json', ready)
    venue.stage('waiting_for_operator', consoleUrl=ready['consoleUrl'], source='Simulation', headsets=ready['headsets'], clientMode=ready['clientMode'])
    print('Use the temporary Master / RoomN credential from this run\'s keys.json. Create a VR mission, Preparing session and roster in the console.', flush=True)
    print('External mode starts servers only; download each player connection file in the control desk.' if external else 'The first admitted player in --visible-room gets a native window. Begin / environment / AI / End stay under operator control.', flush=True)
    print('End rounds in the control desk, create end.request, press Ctrl+C or wait for duration to finish owned rounds.' if external else 'Close that player, create end.request, press Ctrl+C or wait for duration to finish all owned rounds.', flush=True)
    entries, clients = {}, {}
    visible = None
    deadline = time.monotonic() + venue.args.duration
    try:
        while time.monotonic() < deadline and not (venue.directory / 'end.request').exists():
            # Retain Ended result windows without blocking other rooms or new admissions.
            for entry in entries.values():
                if entry.get('resultsUntil') is not None and (time.monotonic() >= entry['resultsUntil'] or (venue.directory / 'dismiss-results.request').exists()):
                    venue.stop_round(entry); del entry['resultsUntil']
                    for identity, name in list(clients.items()):
                        if identity[0] == entry['id']:
                            del clients[identity]
                            if visible == name: visible = None
            if visible in venue.processes and venue.processes[visible].poll() is not None:
                ended = any(e['sealed'] and visible.startswith(e['name'] + '-') for e in entries.values())
                venue.stop(visible)
                if ended: visible = None
                else: break
            states = venue.request('/api/sessions?includeEnded=true')
            for state in states:
                if state['id'] not in entries:
                    if state['state'] == 'Ended': continue
                    # Create the initial recording while the roster may still be empty.
                    entry = venue.adopt(state, 'operator-' + state['id'])
                    entry['dynamicRoster'] = True
                    entry['recordingDeadline'] = time.monotonic() + 90
                    entries[state['id']] = entry
                    venue.stage('server_starting', sessionId=entry['id'], roomIds=entry['roomIds'])
                entry = entries[state['id']]
                if entry['sealed']: continue
                recording = venue.request('/api/sessions/' + entry['id'] + '/world', optional=True)
                if recording is None:
                    if venue.processes[entry['name'] + '-server'].poll() is not None: raise RuntimeError('Native operator server stopped before recording')
                    if time.monotonic() >= entry['recordingDeadline'] or state['state'] != 'Preparing':
                        raise RuntimeError('Native recording is not ready. Keep the round Preparing until clients are connected; inspect the native server log for unsupported mission geometry')
                    continue
                # Keep the real latest roster, including new admissions; no client chooses
                # its own room, seat, epoch or Master/GameServer identity.
                entry['players'] = state['players']
                if 'connectionEndpoint' not in entry:
                    endpoint = venue.request('/api/sessions/' + entry['id'] + '/connection-endpoint',
                        {'version': 1, 'streamId': recording['header']['streamId'], 'address': venue.args.advertise_address, 'port': entry['port']}, method='PUT', role='GameServer')
                    entry['connectionEndpoint'] = endpoint
                    venue.save('connection-endpoints.json', {identity: value['connectionEndpoint'] for identity, value in entries.items() if 'connectionEndpoint' in value})
                    venue.save('server-processes.json', {identity: {'processId': venue.processes[value['name'] + '-server'].pid,
                        'port': value['port'], 'listenAddress': venue.args.listen_address} for identity, value in entries.items() if 'connectionEndpoint' in value and value['name'] + '-server' in venue.processes})
                if state['state'] == 'Ended':
                    venue.seal(entry); entry['resultsUntil'] = retain_results(venue, entry)
                    venue.stage('operator_round_sealed', sessionId=entry['id'], frames=entry['sealed']['world']['acceptedSequence'])
                    continue
                wanted = {(entry['id'], p['id'], p['admissionId']) for p in state['players']}
                for identity, name in list(clients.items()):
                    if identity[0] == entry['id'] and identity not in wanted:
                        venue.stop(name); del clients[identity]
                        if name == visible: visible = None
                for player in ([] if external else state['players']):
                    identity = (entry['id'], player['id'], player['admissionId'])
                    if identity in clients: continue
                    ticket = venue.ticket(entry, player)
                    if visible and player['roomId'] == venue.args.visible_room and any(e['sealed'] and visible.startswith(e['name'] + '-') for e in entries.values()):
                        venue.stop(visible)
                        for old_identity, old_name in list(clients.items()):
                            if old_name == visible: del clients[old_identity]
                        visible = None  # A new playable admission takes precedence over an old result window.
                    show = visible is None and player['roomId'] == venue.args.visible_room
                    name = entry['name'] + '-client-' + player['admissionId']
                    venue.launch(name, venue.client_config(entry, ticket), show)
                    clients[identity] = name
                    if show: visible = name
                    venue.stage('player_starting', sessionId=entry['id'], playerId=player['id'], roomId=player['roomId'], visible=show)
                failed = [name for name, child in venue.processes.items() if child.poll() is not None
                          and not any(e['sealed'] and name.startswith(e['name'] + '-') for e in entries.values())]
                if failed: raise RuntimeError('An owned native process exited; preserve journals and inspect the run logs')
                frame = venue.frame(entry, measure=True)
                venue.save('operator-status.json', {'sessionId': entry['id'], 'phase': frame['packet']['frame']['phase'], 'frame': frame['packet']['sequence'],
                    'connectedPlayers': [p['id'] for p in frame['packet']['frame']['players'] if p['connected']],
                    'roomIds': entry['roomIds'], 'source': 'Simulation', 'tick': frame['packet']['frame']['tick'],
                    'weather': frame['packet']['weather'], 'night': frame['packet']['frame']['night'], 'lightning': frame['packet']['lightning'],
                    'enemyCount': len(frame['packet']['frame']['enemies']), 'behavior': frame['packet']['frame']['behavior'], 'autoAttack': frame['packet']['frame']['autoAttack']})
            time.sleep(.25)
    except KeyboardInterrupt:
        pass
    # Explicit operator End is already honored; only still-active owned rounds need End.
    for entry in venue.rounds:
        venue.seal(entry)
        if external:
            retain_results(venue, entry)
            continue
        if not entry.get('resultsUntil'):
            venue.wait_for_player_results(entry)
            if visible and visible.startswith(entry['name'] + '-'):
                venue.inspect_player_results(entry, visible, getattr(venue.args, 'results_seconds', 30))
    if external:
        deadline = max((entry.get('externalGraceUntil', 0) for entry in venue.rounds), default=0)
        while time.monotonic() < deadline: time.sleep(max(0, min(.1, deadline - time.monotonic())))
    venue.summary()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    venue_module.add_api_arguments(parser)
    parser.add_argument('--duration', type=int, choices=range(60,1801), default=900, metavar='60..1800')
    parser.add_argument('--visible-room', type=int, choices=range(0,6), default=1)
    parser.add_argument('--job-workers', type=int, choices=range(1,17), default=2)
    parser.add_argument('--runtime-root', type=Path)
    parser.add_argument('--results-seconds', type=int, choices=range(0,301), default=30, metavar='0..300')
    parser.add_argument('--client-mode', choices=['local', 'external'], default='local', help='external starts servers only, without claiming player admissions locally')
    parser.add_argument('--advertise-address', help='Explicit player-facing unicast IPv4; required for external mode')
    parser.add_argument('--listen-address', help='Server IPv4 binding; external defaults to 0.0.0.0, local to 127.0.0.1')
    args = parser.parse_args(); args.check = False
    try: configure_network(args)
    except ValueError as error: parser.error(str(error))
    try: venue_module.verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: parser.error(str(error))
    venue = venue_module.Venue(args)
    try: run(venue)
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__)
        raise
    finally:
        cleaned = venue.cleanup()
        if not cleaned and sys.exc_info()[0] is None:
            venue.stage('failed', errorType='CleanupError')
            raise RuntimeError('Operator helper cleanup failed; inspect cleanup.json')


if __name__ == '__main__': main()
