"""Check five-room publication, observation and replay on Windows without IP listeners."""

import argparse
from contextlib import ExitStack, closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from uuid import uuid4

from local_api import api_command
from windows_ipc_api import UnixHttpConnection, unix_address
from world_test_socket import WebSocket


ROOMS = range(1, 6)


class Venue:
    def __init__(self, directory, args):
        self.socket_path = directory / 'api.sock'
        self.address = unix_address(self.socket_path)
        self.command, self.cwd, _ = api_command(args)
        self.tokens = {role: secrets.token_hex(32) for role in ('Master', 'GameServer', 'Room1', 'Room5')}
        keys = directory / 'keys.json'
        keys.write_text(json.dumps({'OperatorKeys': self.tokens}), encoding='utf-8')
        keep = {'systemroot', 'systemdrive', 'windir', 'temp', 'tmp', 'userprofile', 'localappdata'}
        self.env = {key: value for key, value in os.environ.items() if key.lower() in keep}
        self.env.update(DataDirectory=str(directory / 'missions'), SessionDataDirectory=str(directory / 'sessions'),
                        OperatorKeyFile=str(keys), ASPNETCORE_ENVIRONMENT='Production', VR_COMMAND_UNATTENDED='1')

    @contextmanager
    def response(self, route, method='GET', body=None, role='Master', status=200):
        headers = {'Authorization': 'Bearer ' + self.tokens[role]}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Idempotency-Key': str(uuid4())})
        with closing(UnixHttpConnection(self.address)) as connection:
            connection.request(method, route, None if body is None else json.dumps(body), headers)
            with connection.getresponse() as response:
                assert response.status == status, (method, route, response.status, response.read(800))
                yield response

    def request(self, route, **options):
        with self.response(route, **options) as response:
            return json.load(response)

    @contextmanager
    def start(self):
        self.socket_path.unlink(missing_ok=True)
        with tempfile.TemporaryFile() as log:
            command = [*self.command, '--urls', 'http://unix:/' + str(self.socket_path), '--preferHostingUrls', 'true']
            child = subprocess.Popen(command, cwd=self.cwd, env=self.env, stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                deadline = time.monotonic() + 25
                while child.poll() is None and time.monotonic() < deadline:
                    try:
                        with self.response('/health') as response:
                            response.read()
                    except OSError:
                        pass
                    else:
                        log.seek(0)
                        bindings = [line.split('Now listening on: ', 1)[1] for line in log.read().decode().splitlines()
                                    if 'Now listening on: ' in line]
                        if bindings:
                            assert bindings == ['http://unix:' + str(self.socket_path)], bindings
                            break
                    time.sleep(.1)
                else:
                    raise RuntimeError('Isolated API did not become ready')
                self.check_ip_endpoints(child.pid)
                yield
                self.check_ip_endpoints(child.pid)
            finally:
                if child.poll() is None:
                    child.terminate()
                child.wait(timeout=10)

    @staticmethod
    def check_ip_endpoints(pid):
        script = (f'@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object OwningProcess -EQ {pid}).Count; '
                  f'@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object OwningProcess -EQ {pid}).Count')
        counts = subprocess.check_output(['pwsh', '-NoProfile', '-NonInteractive', '-Command', script],
                                         text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        assert counts.split() == ['0', '0'], counts

    def phase(self, action, target, status=200, **fields):
        rows = self.request('/api/venue/phase')[target]
        targets = [{key: row[key] for key in ('sessionId', 'phaseSinceSequence', 'sessionSequence',
                   'environmentSinceSequence') if key in row} for row in rows]
        assert targets, action
        return self.request('/api/venue/phase', method='POST', body=dict(action=action, targets=targets, **fields), status=status)


class Publisher:
    def __init__(self, venue, session, stack):
        self.session = session
        self.route = '/api/sessions/' + session['id']
        self.world = self.route + '/world'
        self.venue = venue
        self.stream_id = str(uuid4())
        self.combat = 0
        self.damaged = set()
        self.enemies = {room: {'id': str(uuid4()), 'roomId': room, 'health': 100,
                               'feet': {'x': (room - 3) * 14, 'y': 0, 'z': 3}} for room in session['roomIds']}
        venue.request(self.route + '/combat-stream', method='POST', role='GameServer',
                      body={'streamId': self.stream_id, 'origin': 'GameServer'})
        self.socket = stack.enter_context(closing(WebSocket(None, self.world + '/publish', venue.tokens['GameServer'],
                                                          ipc_address=venue.address)))
        self.started = time.monotonic()
        self.sequence = 0
        self.tick = 0
        captured = datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', '0+00:00')
        header = {'sessionId': session['id'], 'streamId': self.stream_id, 'origin': 'GameServer',
                  'roomIds': session['roomIds'], 'captureStartedAtUtc': captured}
        if session['environment']['mode'] == 'MR':
            header['calibration'] = 'quest-room-mr-v1'
        self.send(type='header', payload=header)
        self.state = venue.request(self.route)

    def send(self, **message):
        reply = self.socket.send(message)
        assert reply['type'] == 'ack', reply
        return reply['info']

    def publish(self, drop_pose=False, damage=False):
        state = self.state
        if state['state'] == 'Running':
            self.tick += 1
        players, events = [], []
        for row in state['players']:
            room, seat, player_id = row['roomId'], row['seat'], row['id']
            head = {'x': (room - 3) * 14 + (seat - 2) * 1.5, 'y': 1.65, 'z': -3}
            connected = not (drop_pose and room == 5 and seat == 1)
            if damage and seat == 0:
                self.combat += 1
                self.damaged.add(player_id)
                event_id = str(uuid4())
                self.venue.request(self.route + '/combat-stream/reports', method='POST', role='GameServer',
                                   body={'streamId': self.stream_id, 'streamSequence': self.combat,
                                         'observedSequence': state['sequence'], 'report': {'reportId': event_id,
                                         'kind': 'PlayerDamaged', 'origin': 'GameServer', 'playerId': player_id, 'damage': 20}})
                events.append({'sequence': self.combat, 'tick': self.tick, 'eventId': event_id,
                               'kind': 'PlayerDamaged', 'playerId': player_id, 'damage': 20,
                               'enemyId': self.enemies[room]['id']})
            players.append({'id': player_id, 'roomId': room, 'head': head, 'muzzle': head, 'connected': connected,
                            'forward': {'x': 0, 'y': 0, 'z': 1}, 'health': 80 if player_id in self.damaged else 100,
                            'magazine': 30, 'reserve': 90, 'rig': {'kind': 'Tracked' if connected else 'None',
                                                                 'left': head, 'right': head}})
        self.sequence += 1
        environment = state['environment']
        packet = {'sequence': self.sequence, 'observedSequence': state['sequence'],
                  'elapsedMilliseconds': 0 if self.sequence == 1 else int((time.monotonic() - self.started) * 1000),
                  'weather': environment['weather'], 'lightning': environment['lightning'],
                  'throughCombatSequence': self.combat, 'events': events, 'frame': {'phase': state['state'],
                  'night': environment['timeOfDay'] == 'Night', 'visibility': environment['weather'], 'tick': self.tick,
                  'throughSequence': self.combat, 'players': players, 'enemies': list(self.enemies.values())}}
        assert self.send(type='frame', payload=packet)['acceptedSequence'] == self.sequence

    def seal(self):
        self.venue.request(self.route + '/combat-stream/seal', method='POST', role='GameServer',
                           body={'streamId': self.stream_id, 'finalSequence': self.combat})
        info = self.send(type='seal', finalSequence=self.sequence)
        assert info['complete'] and info['acceptedSequence'] == self.sequence, info
        return info


def next_event(response):
    for _ in range(16):
        line = response.readline()
        if not line:
            break
        if line.startswith(b'event: '):
            kind = line[7:].decode().strip()
            data = response.readline()
            assert data.startswith(b'data: ') and response.readline() in (b'\n', b'\r\n')
            if kind != 'status':
                return kind, json.loads(data[6:])
    raise AssertionError('Observation ended before the expected SSE event')


def check_mode(venue, mode):
    def mission(experience, enemies=1):
        return venue.request('/api/missions', method='POST', status=201, body={'name': f'{mode} {experience} IPC review',
            'briefing': '', 'durationSeconds': 180, 'props': [], 'environment': {'mode': experience, 'weather': 'Clear',
            'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': enemies, 'behavior': 'Hold', 'autoAttack': False}})['id']

    vr = mission('VR', len(ROOMS) if mode == 'Linked' else 1)
    if mode == 'Linked':
        sessions = [venue.request('/api/sessions', method='POST', status=201,
                                  body={'missionId': vr, 'mode': mode, 'roomIds': list(ROOMS)})]
    else:
        mr = mission('MR')
        sessions = venue.request('/api/sessions/independent-set', method='POST', status=201, body={
            'rooms': [{'roomId': room, 'missionId': mr if room in (2, 4) else vr} for room in ROOMS]})['sessions']
    for session in sessions:
        route = '/api/sessions/' + session['id']
        if session['environment']['mode'] == 'MR':
            room, = session['roomIds']
            venue.request(route + '/commands', method='POST', body={'action': 'SetRoomAlignment', 'commandId': str(uuid4()),
                          'expectedSequence': session['sequence'], 'roomAlignment': {f'room{room}': secrets.token_hex(32)}})
        for room in session['roomIds']:
            for seat in range(1, 6):
                venue.request(route + '/players', method='POST', body={'playerId': str(uuid4()), 'roomId': room,
                              'name': f'Room {room} seat {seat}', 'headset': 'Quest3'})
    with ExitStack() as stack:
        sources = [Publisher(venue, session, stack) for session in sessions]
        assert sum(len(source.state['players']) for source in sources) == 25
        for source in sources:
            source.publish(drop_pose=True)
        refused = venue.phase('Begin', 'begin', status=409, requireFullTracking=True)
        assert refused['code'] == 'venue-begin-not-ready' and refused['roomIds'] == [5], refused
        assert all(venue.request(source.route)['state'] == 'Preparing' for source in sources)
        for source in sources:
            source.publish()
        begun = venue.phase('Begin', 'begin', requireFullTracking=True)
        assert begun['requireFullTracking'] and {row['sessionId'] for row in begun['sessions']} == {s['id'] for s in sessions}
        venue.phase('SetEnvironment', 'environment', environment={'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True})
        for source in sources:
            source.state = venue.request(source.route)
            assert source.state['state'] == 'Running'
            source.publish(damage=True)

        observed = next(source for source in sources if 5 in source.session['roomIds'])
        with venue.response(observed.world + '/watch') as master:
            assert next_event(master)[0] == 'header'
            kind, overview = next_event(master)
            assert kind == 'frame' and overview['packet']['sequence'] == 3
            assert {actor['id'] for actor in overview['packet']['frame']['players']} == {
                player['id'] for player in observed.state['players']}
        scope = 'observerRoomId=5'
        with venue.response(observed.world + '/watch?' + scope, role='Room1', status=403):
            pass
        with venue.response(observed.world + '/watch?' + scope, role='Room5') as live:
            metadata = next_event(live)
            assert metadata[0] == 'header' and metadata[1]['observerRoomId'] == 5
            kind, visible = next_event(live)
            running = visible['packet']
            assert kind == 'frame' and running['sequence'] == 3 and running['frame']['phase'] == 'Running'
            assert running['weather'] == 'Storm' and running['lightning'] and running['frame']['night']
            assert len(running['frame']['players']) == 5 and {player['roomId'] for player in running['frame']['players']} == {5}
            assert {enemy['roomId'] for enemy in running['frame']['enemies']} == {5}
            assert len(running['events']) == 1 and running['events'][0]['damage'] == 20

            ended = venue.phase('End', 'end')
            closure_route = '/api/venue/closure/' + ended['requestId']
            assert all(row['world'] == 'Waiting' for row in venue.request(closure_route)['batch']['sessions'])
            for source in sources:
                source.state = venue.request(source.route)
                assert source.state['state'] == 'Ended'
                source.publish()
                source.seal()
            kind, terminal = next_event(live)
            assert kind == 'frame' and terminal['packet']['sequence'] == 4 and terminal['packet']['frame']['phase'] == 'Ended'
            kind, complete = next_event(live)
            assert kind == 'complete' and complete['complete'] and live.readline() == b''

        closure = venue.request(closure_route)
        assert {row['sessionId'] for row in closure['batch']['sessions']} == {s['id'] for s in sessions}
        saved = {}
        for row in closure['batch']['sessions']:
            original = next(source for source in sources if source.session['id'] == row['sessionId'])
            frame = row['trackingBegin']['frame']
            assert row['trackingBegin']['requestId'] == begun['requestId']
            assert frame['streamId'] == original.stream_id and frame['worldSequence'] == 2
            frames = [venue.request(original.world + f'/frames/{sequence}') for sequence in range(1, 5)]
            exact = frames[1]['packet']
            applied = next(entry['appliedAtSequence'] for entry in begun['sessions'] if entry['sessionId'] == row['sessionId'])
            assert row['trackingBegin']['appliedAtSequence'] == applied and exact['observedSequence'] == applied - 1
            assert exact['frame']['phase'] == 'Preparing' and frame['elapsedMilliseconds'] == exact['elapsedMilliseconds']
            assert len(exact['frame']['players']) == len(original.session['roomIds']) * 5
            assert all(player['connected'] and player['rig']['kind'] == 'Tracked' for player in exact['frame']['players'])
            stats = venue.request(original.route + '/statistics')['players']
            assert {player['playerId'] for player in stats if player['damageTaken'] == 20 and player['health'] == 80
                    and player['hitsReceived'] == 1} == original.damaged
            assert len([player for player in stats if player['damageTaken']]) == len(original.session['roomIds'])
            saved[original.world] = frames
        assert venue.request('/api/sessions') == []
        return {'mode': mode, 'seats': 25, 'recordings': len(sources), 'combatEvents': sum(source.combat for source in sources),
                'frames': sum(source.sequence for source in sources), 'closureRoute': closure_route, 'closure': closure,
                'roomFiveWorld': observed.world, 'roomFiveLive': visible, 'saved': saved}


def check_after_restart(venue, result):
    assert venue.request('/api/sessions') == []
    assert venue.request(result['closureRoute']) == result['closure']
    for world, frames in result['saved'].items():
        with venue.response(world + '/watch?mode=replay&fromFrame=1&throughFrame=latest&rate=4') as replay:
            kind, info = next_event(replay)
            assert kind == 'header' and info['complete'] and info['acceptedSequence'] == 4
            for sequence, frame in enumerate(frames, 1):
                assert next_event(replay) == ('frame', frame) and venue.request(world + f'/frames/{sequence}') == frame
            assert next_event(replay) == ('saved-end', info) and replay.readline() == b''
    with venue.response(result['roomFiveWorld'] + '/watch?mode=replay&fromFrame=3&throughFrame=3&observerRoomId=5', role='Room5') as replay:
        assert next_event(replay)[0] == 'header'
        assert next_event(replay) == ('frame', result['roomFiveLive'])
        assert next_event(replay)[0] == 'saved-end' and replay.readline() == b''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-exe', required=True, type=Path, help='Extracted management package Runtime/VrCommand.Api.exe')
    parser.add_argument('--work-root', required=True, type=Path, help='Short existing Windows folder for temporary isolated data')
    parser.add_argument('--report', type=Path, help='New path for a JSON verification report')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This fixture uses Windows AF_UNIX')
    root = args.work_root.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='venue-', dir=root) as directory:
        folder = Path(directory).resolve(strict=True)
        assert folder.parent == root
        venue = Venue(folder, args)
        with venue.start():
            results = [check_mode(venue, mode) for mode in ('Linked', 'Independent')]
        with venue.start():
            for result in results:
                check_after_restart(venue, result)
        summary = {'verified': [{field: result[field] for field in ('mode', 'seats', 'recordings', 'combatEvents', 'frames')}
                                for result in results], 'apiSha256': hashlib.sha256(args.api_exe.read_bytes()).hexdigest(),
                   'transport': 'Windows AF_UNIX', 'restarted': True, 'tcpListeners': 0, 'udpEndpoints': 0, 'activeSessions': 0,
                   'scope': 'Synthetic tracked poses and combat using packaged management API, real WebSocket and SSE'}
    if args.report:
        with args.report.open('x', encoding='utf-8') as output:
            json.dump(summary, output, indent=2)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
