"""Check five-room publication, observation and replay on Windows without IP listeners."""

import argparse
from collections import Counter
from contextlib import ExitStack, closing, contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
import zipfile
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
        self.tokens = {role: secrets.token_hex(32) for role in ('Master', 'GameServer', *(f'Room{room}' for room in ROOMS))}
        keys = directory / 'keys.json'
        keys.write_text(json.dumps({'OperatorKeys': self.tokens}), encoding='utf-8')
        keep = {'systemroot', 'systemdrive', 'windir', 'temp', 'tmp', 'userprofile', 'localappdata'}
        self.env = {key: value for key, value in os.environ.items() if key.lower() in keep}
        self.env.update(DataDirectory=str(directory / 'missions'), SessionDataDirectory=str(directory / 'sessions'),
                        OperatorKeyFile=str(keys), ASPNETCORE_ENVIRONMENT='Production', VR_COMMAND_UNATTENDED='1')

    @contextmanager
    def response(self, route, method='GET', body=None, role='Master', status=200, admission=None):
        headers = {'Authorization': 'Bearer ' + self.tokens[role]}
        if admission:
            headers.update({'If-Match-Admission': admission, 'Idempotency-Key': str(uuid4())})
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
        log_path = self.socket_path.with_suffix('.log')
        with log_path.open('wb') as log:
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
                        # Read with a separate handle so startup checks cannot move the child's output cursor.
                        lines = log_path.read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)
                        bindings = [line.split('Now listening on: ', 1)[1].rstrip('\r\n') for line in lines
                                    if line.endswith('\n') and 'Now listening on: ' in line]
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
        if 'roomIds' in fields:
            rows = [row for row in rows if set(row['roomIds']).intersection(fields['roomIds'])]
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
                  'roomIds': session['roomIds'], 'captureStartedAtUtc': captured, 'environmentVersion': 1}
        if session['environment']['mode'] == 'MR':
            header['calibration'] = 'quest-room-mr-v1'
        self.send(type='header', payload=header)
        self.state = venue.request(self.route)

    def send(self, **message):
        reply = self.socket.send(message)
        assert reply['type'] == 'ack', reply
        return reply['info']

    def publish(self, drop_pose=False, damage=False, departing=None):
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
                if player_id == departing:
                    with self.venue.response(self.route + '/players/' + player_id, method='DELETE',
                                             admission=row['admissionId'], status=204):
                        pass
                    continue
            players.append({'id': player_id, 'roomId': room, 'head': head, 'muzzle': head, 'connected': connected,
                            'forward': {'x': 0, 'y': 0, 'z': 1}, 'health': 80 if player_id in self.damaged else 100,
                            'magazine': 30, 'reserve': 90, 'rig': {'kind': 'Tracked' if connected else 'None',
                                                                 'left': head, 'right': head}})
        if departing:
            self.state = state = self.venue.request(self.route)
            assert all(row['id'] != departing for row in state['players'])
        self.sequence += 1
        environment = state['environment']
        packet = {'sequence': self.sequence, 'observedSequence': state['sequence'],
                  'elapsedMilliseconds': 0 if self.sequence == 1 else int((time.monotonic() - self.started) * 1000),
                  'weather': environment['weather'], 'lightning': environment['lightning'],
                  'throughCombatSequence': self.combat, 'events': events, 'frame': {'phase': state['state'],
                  'night': environment['timeOfDay'] == 'Night',
                  'visibility': environment['weather'] if environment['weather'] in ('Fog', 'Storm') else 'Clear', 'tick': self.tick,
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


def publish_destinations(venue, sources, mode):
    targets = [{'sessionId': source.session['id'], 'endpoint': {
        'address': '127.0.0.1', 'port': 17770 + min(source.session['roomIds']),
        'streamId': source.stream_id, 'version': 1}} for source in sources]
    receipt = venue.request('/api/venue/connection-endpoints', method='PUT', role='GameServer',
                            body={'version': 1, 'topology': mode, 'servers': targets})
    expected = {t['sessionId']: (t['endpoint']['address'], t['endpoint']['port']) for t in targets}
    assert {row['sessionId']: (row['address'], row['port']) for row in receipt['servers']} == expected
    return expected


def check_ticket(venue, session, player, ticket):
    approved = venue.request('/api/player-tickets/validate', method='POST', role='GameServer',
                             body={'sessionId': session['id'], 'ticket': ticket, 'protocolVersion': 2})
    assert approved['sessionId'] == session['id'] and approved['playerId'] == player['id']
    assert approved['throughSequence'] == session['sequence']
    assert all(approved[key] == player[key] for key in ('roomId', 'seat', 'admissionId'))


def replace_headset_before_start(venue, route, old, headset):
    player_route = route + '/players/' + old['id']
    session = venue.request(route)
    invitation = venue.request(player_route + '/join-ticket', method='POST', admission=old['admissionId'])
    check_ticket(venue, session, old, invitation['ticket'])
    with venue.response(player_route, method='DELETE', admission=old['admissionId'], status=204):
        pass
    rejoined = venue.request(route + '/players', method='POST', body={
        'playerId': old['id'], 'name': old['name'], 'roomId': old['roomId'], 'headset': headset})
    current, = [p for p in rejoined['players'] if p['id'] == old['id']]
    assert current['admissionId'] != old['admissionId']
    assert (current['roomId'], current['seat'], current['headset']) == (old['roomId'], old['seat'], headset)
    with venue.response('/api/player-tickets/validate', method='POST', role='GameServer', status=403,
                        body={'sessionId': session['id'], 'ticket': invitation['ticket'], 'protocolVersion': 2}):
        pass
    with venue.response(player_route + '/join-ticket', method='POST', admission=old['admissionId'], status=409):
        pass
    return current


def configure_weather(venue, sources, mode):
    storm = {'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True}
    receipt = venue.phase('SetEnvironment', 'environment', environment=storm)
    expected = {source.session['id']: storm for source in sources}
    sequences = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
    if mode == 'Independent':
        for rooms, weather in [([1, 2], {'weather': 'Rain', 'timeOfDay': 'Day', 'lightning': False}),
                               ([4], {'weather': 'Fog', 'timeOfDay': 'Night', 'lightning': False})]:
            receipt = venue.phase('SetEnvironment', 'environment', roomIds=rooms, environment=weather)
            selected = {source.session['id'] for source in sources if source.session['roomIds'][0] in rooms}
            assert {row['sessionId'] for row in receipt['sessions']} == selected
            for row in receipt['sessions']:
                expected[row['sessionId']] = weather
                sequences[row['sessionId']] = row['appliedAtSequence']
    for source in sources:
        source.state = venue.request(source.route)
        key = source.session['id']
        assert source.state['sequence'] == sequences[key]
        assert all(source.state['environment'][field] == value for field, value in expected[key].items())
    return expected


def check_current_environment(venue, room, expected):
    route = f'/api/rooms/{room}/hardware-environment'
    for role in ('Master', f'Room{room}'):
        with venue.response(route, role=role) as response:
            assert response.getheader('Cache-Control') == 'no-store'
            assert json.load(response) == {'version': 1, 'roomId': room, 'session': expected}
    for denied in (f'Room{room % 5 + 1}', 'GameServer'):
        with venue.response(route, role=denied, status=403):
            pass


def check_room_environment(venue, session, room, phase_sequence, environment_sequence):
    route = f"/api/sessions/{session['id']}/rooms/{room}/hardware-environment"
    with venue.response(route, role=f'Room{room}') as response:
        assert response.getheader('Cache-Control') == 'no-store'
        snapshot = json.load(response)
    assert snapshot == {'version': 1, 'sessionId': session['id'], 'roomId': room, 'state': session['state'],
                        'throughSequence': session['sequence'], 'phaseSinceSequence': phase_sequence,
                        'environmentSinceSequence': environment_sequence,
                        'environment': session['environment'] if session['state'] == 'Running' else None}
    assert venue.request(route) == snapshot
    check_current_environment(venue, room, None if session['state'] == 'Ended' else snapshot)
    return snapshot


def recorded_weather(packet):
    return {'weather': packet['weather'], 'timeOfDay': 'Night' if packet['frame']['night'] else 'Day',
            'lightning': packet['lightning']}


def check_mode(venue, mode):
    for room in ROOMS:
        check_current_environment(venue, room, None)
    for invalid in (0, 6):
        with venue.response(f'/api/rooms/{invalid}/hardware-environment', status=400):
            pass

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
    rosters = {}
    headsets = Counter()
    tickets = {}
    for session in sessions:
        route = '/api/sessions/' + session['id']
        expected = rosters[route] = {}
        if session['environment']['mode'] == 'MR':
            room, = session['roomIds']
            with venue.response(route + '/players', method='POST', status=409, body={
                    'playerId': str(uuid4()), 'roomId': room, 'name': 'MR device check', 'headset': 'ViveXr'}):
                pass
            assert venue.request(route) == session
            venue.request(route + '/commands', method='POST', body={'action': 'SetRoomAlignment', 'commandId': str(uuid4()),
                          'expectedSequence': session['sequence'], 'roomAlignment': {f'room{room}': secrets.token_hex(32)}})
        for room in session['roomIds']:
            for seat in range(1, 6):
                if (room, seat) == (1, 4):
                    prior = venue.request(route + '/players', method='POST', body={'playerId': str(uuid4()),
                        'roomId': room, 'name': f'Room {room} seat {seat}', 'headset': 'Quest3'})
                    prior_seat = next(p for p in prior['players'] if p['roomId'] == room and p['seat'] == seat - 1)
                    with venue.response(route + '/players/' + prior_seat['id'], method='DELETE',
                                        admission=prior_seat['admissionId'], status=204):
                        pass
                headset = 'ViveXr' if session['environment']['mode'] == 'VR' and seat % 2 == 0 else 'Quest3'
                if (room, seat) == (5, 2):
                    headset = 'Quest3'  # This attendee switches devices after the room is full.
                player_id = str(uuid4())
                joined = venue.request(route + '/players', method='POST', body={'playerId': player_id, 'roomId': room,
                                       'name': f'Room {room} seat {seat}', 'headset': headset})
                player, = [p for p in joined['players'] if p['id'] == player_id]
                assert (player['roomId'], player['seat'], player['headset']) == (room, seat - 1, headset)
                expected[player_id] = player
        if 5 in session['roomIds']:
            old, = [p for p in expected.values() if p['roomId'] == 5 and p['seat'] == 1]
            replacement = replace_headset_before_start(venue, route, old, 'ViveXr')
            expected[old['id']] = replacement
            device_change = {'room': old['roomId'], 'seatNumber': old['seat'] + 1, 'from': old['headset'],
                             'to': replacement['headset'], 'oldTicketRejected': True}
        headsets.update(p['headset'] for p in expected.values())
    with ExitStack() as stack:
        sources = [Publisher(venue, session, stack) for session in sessions]
        assert sum(len(source.state['players']) for source in sources) == 25
        destinations = publish_destinations(venue, sources, mode)
        for source in sources:
            source.publish(drop_pose=True)
            assert {p['id']: p for p in source.state['players']} == rosters[source.route]
            for player in source.state['players']:
                invitation = venue.request(source.route + '/players/' + player['id'] + '/join-ticket',
                                           method='POST', admission=player['admissionId'])
                endpoint = invitation['endpoint']
                assert (endpoint['address'], endpoint['port']) == destinations[source.session['id']]
                assert invitation.get('roomAlignmentSha256') == (source.state.get('roomAlignment') or {}).get(
                    'room' + str(player['roomId']))
                tickets[player['id']] = invitation['ticket']
                check_ticket(venue, source.state, player, invitation['ticket'])
        refused = venue.phase('Begin', 'begin', status=409, requireFullTracking=True)
        assert refused['code'] == 'venue-begin-not-ready' and refused['roomIds'] == [5], refused
        assert all(venue.request(source.route)['state'] == 'Preparing' for source in sources)
        for source in sources:
            source.publish()
        begun = venue.phase('Begin', 'begin', requireFullTracking=True)
        assert begun['requireFullTracking'] and {row['sessionId'] for row in begun['sessions']} == {s['id'] for s in sessions}
        weather = configure_weather(venue, sources, mode)
        live_weather = {}
        hardware = {}
        for source in sources:
            assert source.state['state'] == 'Running'
            phase = next(row['appliedAtSequence'] for row in begun['sessions'] if row['sessionId'] == source.state['id'])
            for room in source.session['roomIds']:
                hardware[room] = check_room_environment(venue, source.state, room, phase, source.state['sequence'])
                route = source.route + f'/rooms/{room}/hardware-environment'
                for denied in (f'Room{room % 5 + 1}', 'GameServer'):
                    with venue.response(route, role=denied, status=403):
                        pass
            for player in source.state['players']:
                check_ticket(venue, source.state, player, tickets[player['id']])
            source.publish(damage=True)
            with venue.response(source.world + '/watch') as observer:
                assert next_event(observer)[0] == 'header'
                kind, snapshot = next_event(observer)
                assert kind == 'frame' and snapshot['packet']['sequence'] == 3
                actual = recorded_weather(snapshot['packet'])
                assert actual == weather[source.session['id']]
                for room in source.session['roomIds']:
                    assert all(hardware[room]['environment'][key] == value for key, value in actual.items())
                live_weather.update({room: actual for room in source.session['roomIds']})

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
        first_session = next(s for s in sessions if 1 in s['roomIds'])
        left = venue.request(f"/api/venue/closure/{closure['batch']['requestId']}/sessions/{first_session['id']}/departed-players")
        occupant, = left['players']
        assert occupant['seat'] == prior_seat['seat'] == 3 and occupant['admissionId'] == prior_seat['admissionId']
        assert occupant['statistics']['playerId'] == prior_seat['id'] and occupant['statistics']['name'] == prior_seat['name']
        assert {row['sessionId'] for row in closure['batch']['sessions']} == {s['id'] for s in sessions}
        saved = {}
        for row in closure['batch']['sessions']:
            original = next(source for source in sources if source.session['id'] == row['sessionId'])
            frame = row['trackingBegin']['frame']
            assert row['trackingBegin']['requestId'] == begun['requestId']
            assert frame['streamId'] == original.stream_id and frame['worldSequence'] == 2
            frames = [venue.request(original.world + f'/frames/{sequence}') for sequence in range(1, 5)]
            initial = {'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}
            assert [recorded_weather(item['packet']) for item in frames] == [initial] * 2 + [weather[row['sessionId']]] * 2
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
                'roomFiveWorld': observed.world, 'roomFiveLive': visible, 'saved': saved, 'rosters': rosters,
                'headsetRoster': dict(headsets), 'ticketsRevalidatedInRunning': len(tickets),
                'deviceChange': device_change, 'roomWeather': live_weather, 'hardwareEnvironment': hardware}


def check_departed_clip(venue):
    mission = venue.request('/api/missions', method='POST', status=201, body={'name': 'Delayed event review',
        'briefing': '', 'durationSeconds': 180, 'props': [], 'environment': {'mode': 'VR', 'weather': 'Clear',
        'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 5, 'behavior': 'Hold', 'autoAttack': False}})
    session = venue.request('/api/sessions', method='POST', status=201, body={
        'missionId': mission['id'], 'mode': 'Linked', 'roomIds': list(ROOMS)})
    route = '/api/sessions/' + session['id']
    departed = str(uuid4())
    earlier = str(uuid4())
    name = '=同名,"甲"'
    joined = venue.request(route + '/players', method='POST', body={'playerId': earlier, 'roomId': 1, 'name': name, 'headset': 'Quest3'})
    admissions = {earlier: (joined['players'][0]['admissionId'], joined['sequence'])}
    with venue.response(route + '/players/' + earlier, method='DELETE', admission=admissions[earlier][0], status=204):
        pass
    for room in (1, 5):
        joined = venue.request(route + '/players', method='POST', body={'playerId': departed if room == 1 else str(uuid4()),
                               'roomId': room, 'name': name if room == 1 else f'Seat {room}', 'headset': 'Quest3'})
        if room == 1:
            admissions[departed] = (joined['players'][0]['admissionId'], joined['sequence'])
    with ExitStack() as stack:
        source = Publisher(venue, session, stack)
        publish_destinations(venue, [source], 'Linked')
        source.state = venue.request(route)
        source.publish()
        venue.phase('Begin', 'begin')
        source.state = venue.request(route)
        source.publish(damage=True, departing=departed)
        end = venue.phase('End', 'end')
        source.state = venue.request(route)
        source.publish()
        source.seal()
    departures_path = f"/api/venue/closure/{end['requestId']}/sessions/{session['id']}/departed-players"
    for role in ('Room1', 'GameServer'):
        with venue.response(departures_path, role=role, status=403):
            pass
    report = venue.request(departures_path)
    assert {row['statistics']['playerId'] for row in report['players']} == set(admissions)
    for row in report['players']:
        score = row['statistics']
        assert (row['admissionId'], row['joinedAtSequence']) == admissions[score['playerId']]
        assert row['seat'] == 0 and score['roomId'] == 1 and score['name'] == name
        assert row['joinedAtSequence'] < row['leftAtSequence'] < report['endedAtSequence']
        assert (score['hitsReceived'], score['damageTaken'], score['health']) == ((1, 20, 80) if score['playerId'] == departed else (0, 0, 100))
    clip = source.world + '/clips/' + str(uuid4())
    venue.request(clip, method='PUT', body={'name': 'After departure', 'streamId': source.stream_id, 'startFrame': 2, 'endFrame': 3})
    export = clip + '/player-replay.json'
    full = venue.request(export)
    assert all(body['id'] != departed for packet in full['packets'] for body in packet['frame']['players'])
    event, = [event for packet in full['packets'] for event in packet['events'] if event['playerId'] == departed]
    assert full['eventRooms'] == {event['eventId']: 1}
    originals = [venue.request(source.world + f'/frames/{seq}')['packet'] for seq in (2, 3)]
    assert full['packets'] == originals
    room = venue.request(export + '?roomId=1')
    assert 'eventRooms' not in room and [e['eventId'] for p in room['packets'] for e in p['events']] == [event['eventId']]
    return full


def check_after_restart(venue, result):
    clips = {}
    assert venue.request('/api/sessions') == []
    assert venue.request(result['closureRoute']) == result['closure']
    for route, expected in result['rosters'].items():
        assert {row['id']: row for row in venue.request(route)['players']} == expected
    for world, frames in result['saved'].items():
        with venue.response(world + '/watch?mode=replay&fromFrame=1&throughFrame=latest&rate=4') as replay:
            kind, info = next_event(replay)
            assert kind == 'header' and info['complete'] and info['acceptedSequence'] == 4
            for sequence, frame in enumerate(frames, 1):
                assert next_event(replay) == ('frame', frame) and venue.request(world + f'/frames/{sequence}') == frame
            assert next_event(replay) == ('saved-end', info) and replay.readline() == b''
        header = info['header']
        rooms = header['roomIds']
        name = 'linked' if len(rooms) == 5 else f'room-{rooms[0]}'
        clip = world + '/clips/' + str(uuid4())
        venue.request(clip, method='PUT', body={'name': name, 'streamId': header['streamId'], 'startFrame': 1, 'endFrame': 4})
        exported = venue.request(clip + '/player-replay.json')
        assert exported['header']['roomIds'] == rooms and exported['header']['environmentVersion'] == 1
        assert exported['packets'] == [frame['packet'] for frame in frames]
        clips[name] = exported
    with venue.response(result['roomFiveWorld'] + '/watch?mode=replay&fromFrame=3&throughFrame=3&observerRoomId=5', role='Room5') as replay:
        assert next_event(replay)[0] == 'header'
        assert next_event(replay) == ('frame', result['roomFiveLive'])
        assert next_event(replay)[0] == 'saved-end' and replay.readline() == b''
    return clips


def check_environment_pause(venue, previous):
    mission = venue.request(previous['roomFiveWorld'].removesuffix('/world'))['mission']
    session = venue.request('/api/sessions', method='POST', status=201,
                            body={'missionId': mission['id'], 'mode': 'Independent', 'roomIds': [1]})
    route = '/api/sessions/' + session['id']
    check_room_environment(venue, session, 1, 1, 1)
    with venue.response(route + '/rooms/2/hardware-environment', status=400):
        pass
    venue.request(route + '/players', method='POST', body={'playerId': str(uuid4()), 'roomId': 1,
                                                          'name': 'Room receiver rehearsal', 'headset': 'Quest3'})
    def command(action, **fields):
        return venue.request(route + '/commands', method='POST',
                             body=dict(action=action, commandId=str(uuid4()), **fields))['appliedAtSequence']
    begun = command('Begin')
    check_room_environment(venue, venue.request(route), 1, begun, 1)
    climate = dict(mission['definition']['environment'], weather='Rain', timeOfDay='Night', lightning=False)
    changed = command('SetEnvironment', environment=climate)
    check_room_environment(venue, venue.request(route), 1, begun, changed)
    paused = command('Pause')
    return check_room_environment(venue, venue.request(route), 1, paused, changed), climate


def check_environment_resume(venue, paused, climate):
    route = '/api/sessions/' + paused['sessionId']
    changed = paused['environmentSinceSequence']
    assert check_room_environment(venue, venue.request(route), 1, paused['phaseSinceSequence'], changed) == paused
    for action, state in [('Resume', 'Running'), ('End', 'Ended')]:
        receipt = venue.request(route + '/commands', method='POST', body={'action': action, 'commandId': str(uuid4())})
        snapshot = check_room_environment(venue, venue.request(route), 1, receipt['appliedAtSequence'], changed)
        assert snapshot['state'] == state and snapshot['environment'] == (climate if state == 'Running' else None)
    assert venue.request('/api/sessions') == []


def check_segmented_exports(venue, directory):
    directory.mkdir()
    mission = venue.request('/api/missions', method='POST', status=201, body={'name': 'Segmented replay',
        'briefing': '', 'durationSeconds': 600, 'props': [], 'environment': {'mode': 'VR', 'weather': 'Clear',
        'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 100, 'behavior': 'Hold', 'autoAttack': False}})
    session = venue.request('/api/sessions', method='POST', status=201, body={
        'missionId': mission['id'], 'mode': 'Linked', 'roomIds': list(ROOMS)})
    route = '/api/sessions/' + session['id']
    for room in ROOMS:
        for seat in range(1, 6):
            venue.request(route + '/players', method='POST', body={'playerId': str(uuid4()), 'roomId': room,
                          'name': f'Seat {room}-{seat}', 'headset': 'Quest3'})
    with ExitStack() as stack:
        source = Publisher(venue, session, stack)
        for i in range(95):
            room = i % 5 + 1
            source.enemies[i + 6] = {**source.enemies[room], 'id': str(uuid4())}
        source.publish()
        venue.phase('Begin', 'begin')
        source.state = venue.request(route)
        for _ in range(299):
            source.publish()
        venue.phase('End', 'end')
        source.state = venue.request(route)
        source.publish()
        source.seal()

    def save(first, last):
        clip = source.world + '/clips/' + str(uuid4())
        venue.request(clip, method='PUT', body={'name': 'Whole mission <五房> & "回看"', 'streamId': source.stream_id,
                                               'startFrame': first, 'endFrame': last})
        return clip

    clip = save(1, 301)
    with venue.response(clip + '/player-replay.json', status=409):
        pass
    for extension in ('zip', 'html'):
        with venue.response(clip + '/player-replay.' + extension, role='Room1', status=403):
            pass
    summary = {}
    for scope, query in [('full', ''), ('room-5', '?roomId=5')]:
        checkpoint = venue.request(source.world + '/clips')
        with venue.response(clip + '/player-replay.zip' + query) as response:
            assert response.headers['Cache-Control'] == 'no-store'
            raw = response.read()
        assert venue.request(source.world + '/clips') == checkpoint
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            assert names[0] == 'VRCommand-Player-Replay.html' and len(names) == len(set(names))
            ranges = []
            embedded = []
            for name in names[1:]:
                payload = archive.read(name)
                part = json.loads(payload)
                assert part['clipName'] == 'Whole mission <五房> & "回看"'
                embedded.append(b'<script type="application/json" data-player-replay-part>' + payload + b'</script>')
                first, last = part['startFrame'], part['endFrame']
                assert first == (ranges[-1][1] + 1 if ranges else 1) and 2 <= last - first + 1 <= 300
                assert name.endswith(f'-frames-{first:06}-{last:06}.json') and len(payload) <= 8 * 1024 * 1024
                assert part['header']['roomIds'] == ([5] if query else list(ROOMS))
                assert [p['sequence'] for p in part['packets']] == list(range(first, last + 1))
                # Compare the exact original single-file export for this range and scope.
                single = save(first, last)
                with venue.response(single + '/player-replay.json' + query) as original:
                    assert original.read() == payload
                ranges.append([first, last])
            assert ranges[-1][1] == 301
            if query:
                assert ranges == [[1, 299], [300, 301]]
            else:
                assert len(ranges) > 2 or ranges[0][1] < 299, 'Dense full-venue clip must exercise the byte limit'
            template = archive.read(names[0])
            assert template.count(b'<!--player-replay-data-->') == 1
            expected = template.replace(b'<!--player-replay-data-->', b''.join(embedded))
        with venue.response(clip + '/player-replay.html' + query) as response:
            assert response.headers['Cache-Control'] == 'no-store' and response.headers.get_content_type() == 'text/html'
            assert response.headers.get_filename() == 'vr-command-replay-' + clip.split('/')[-1] + ('-room-05' if query else '') + '.html'
            html = response.read()
            assert html == expected
            (directory / (scope + '.html')).write_bytes(html)
        (directory / (scope + '.zip')).write_bytes(raw)
        summary[scope] = ranges
    return {'sessionId': session['id'], 'clip': clip, 'ranges': summary}


def check_volume_exports(venue, directory):
    directory.mkdir()
    results = {}
    for label, frames, seats, enemies in [('long', 7201, 1, 5), ('dense', 1501, 5, 100)]:
        mission = venue.request('/api/missions', method='POST', status=201, body={'name': label,
            'briefing': '', 'durationSeconds': 900, 'props': [], 'environment': {'mode': 'VR', 'weather': 'Clear',
            'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': enemies, 'behavior': 'Hold', 'autoAttack': False}})
        session = venue.request('/api/sessions', method='POST', status=201, body={
            'missionId': mission['id'], 'mode': 'Linked', 'roomIds': list(ROOMS)})
        route = '/api/sessions/' + session['id']
        for room in ROOMS:
            for seat in range(1, seats + 1):
                venue.request(route + '/players', method='POST', body={'playerId': str(uuid4()), 'roomId': room,
                              'name': f'Seat {room}-{seat}', 'headset': 'Quest3'})
        with ExitStack() as stack:
            source = Publisher(venue, session, stack)
            for i in range(enemies - 5):
                source.enemies[i + 6] = {**source.enemies[i % 5 + 1], 'id': str(uuid4())}
            source.publish()
            venue.phase('Begin', 'begin')
            source.state = venue.request(route)
            for sequence in range(2, frames):
                if label == 'long' and sequence == 7200:
                    configure_weather(venue, [source], 'Linked')
                source.publish()
            venue.phase('End', 'end')
            source.state = venue.request(route)
            source.publish()
            source.seal()
        clip_id = str(uuid4())
        clip = source.world + '/clips/' + clip_id
        venue.request(clip, method='PUT', body={'name': label, 'streamId': source.stream_id,
                                               'startFrame': 1, 'endFrame': frames})
        url = clip + '/player-replay.html'
        for query, role, status in [('', 'Master', 409), ('?fromFrame=1', 'Room1', 403),
                                    ('?fromFrame=0', 'Master', 400), (f'?fromFrame={frames}', 'Master', 400)]:
            with venue.response(url + query, role=role, status=status):
                pass
        ranges = []
        first = 1
        room_query = '&roomId=5' if label == 'long' else ''
        before = venue.request(source.world + '/clips')
        while first <= frames:
            with venue.response(url + f'?fromFrame={first}' + room_query) as response:
                last = int(response.headers['X-Replay-Last-Frame'])
                suffix = '-room-05' if room_query else ''
                assert response.headers.get_filename() == f'vr-command-replay-{clip_id}{suffix}-frames-{first:06}-{last:06}.html'
                assert first < last <= frames and last != frames - 1 and response.headers['Cache-Control'] == 'no-store'
                html = response.read()
            next_frame = first
            count = size = 0
            for match in re.finditer(rb'<script type="application/json" data-player-replay-part>([^<]+)</script>', html):
                part = json.loads(match[1])
                count += 1
                size += len(match[1])
                assert part['header']['sessionId'] == session['id'] and part['header']['streamId'] == source.stream_id
                assert part['header']['roomIds'] == ([5] if room_query else list(ROOMS))
                assert part['startFrame'] == next_frame
                assert [p['sequence'] for p in part['packets']] == list(range(next_frame, part['endFrame'] + 1))
                next_frame = part['endFrame'] + 1
            assert next_frame == last + 1 and 1 <= count <= 24 and size <= 64 * 1024 * 1024
            (directory / f'{label}-{first}-{last}.html').write_bytes(html)
            ranges.append([first, last, count, size])
            first = next_frame
        assert len(ranges) > 1 and venue.request(source.world + '/clips') == before
        if label == 'long':
            assert ranges[0][:3] == [1, 7199, 24] and ranges[1][:2] == [7200, 7201]
            with venue.response(url + f'?fromFrame={ranges[1][0]}&roomId=4') as response:
                (directory / 'room4.html').write_bytes(response.read())
        else:
            assert ranges[0][2] < 24, 'Dense recording must split on bytes before the file count'
        results[label] = {'sessionId': session['id'], 'clip': clip, 'ranges': ranges}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-exe', required=True, type=Path, help='Extracted management package Runtime/VrCommand.Api.exe')
    parser.add_argument('--work-root', required=True, type=Path, help='Short existing Windows folder for temporary isolated data')
    parser.add_argument('--report', type=Path, help='New path for a JSON verification report')
    parser.add_argument('--departed-clip', type=Path, help='New output file for the verified synthetic player clip')
    parser.add_argument('--environment-clips', type=Path, help='New directory for the six verified replay exports')
    parser.add_argument('--segmented-replay-exports', type=Path, help='Also export and verify a dense 301-frame player ZIP for two scopes')
    parser.add_argument('--volume-exports', type=Path, help='Verify full coverage beyond player frame and byte limits')
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
            departed_clip = check_departed_clip(venue)
        with venue.start():
            clips = {}
            for result in results:
                clips.update(check_after_restart(venue, result))
            assert set(clips) == {'linked', *(f'room-{room}' for room in ROOMS)}
            paused, climate = check_environment_pause(venue, results[0])
        with venue.start():
            check_environment_resume(venue, paused, climate)
            segmented = check_segmented_exports(venue, args.segmented_replay_exports) if args.segmented_replay_exports else None
            volumes = check_volume_exports(venue, args.volume_exports) if args.volume_exports else None
        summary = {'verified': [{field: result[field] for field in ('mode', 'seats', 'recordings', 'combatEvents', 'frames',
                                                                     'headsetRoster', 'ticketsRevalidatedInRunning', 'deviceChange',
                                                                     'roomWeather', 'hardwareEnvironment')}
                                for result in results], 'apiSha256': hashlib.sha256(args.api_exe.read_bytes()).hexdigest(),
                   'transport': 'Windows AF_UNIX', 'restarted': True, 'tcpListeners': 0, 'udpEndpoints': 0, 'activeSessions': 0,
                   'scope': 'Synthetic tracked poses and combat using packaged management API, real WebSocket and SSE'}
    summary['verifiedDepartedEventRooms'] = len(departed_clip['eventRooms'])
    if segmented:
        summary['segmentedReplay'] = segmented
    if volumes:
        summary['replayVolumes'] = volumes
    summary['assemblySha256'] = {name: hashlib.sha256(args.api_exe.with_name(name).read_bytes()).hexdigest()
                                 for name in ('VrCommand.Api.dll', 'VrCommand.Core.dll')}
    summary['environmentExports'] = sorted(clips)
    summary['roomEnvironmentRestartedWhilePaused'] = True
    if args.environment_clips:
        args.environment_clips.mkdir()
        for name, clip in clips.items():
            (args.environment_clips / (name + '.json')).write_text(json.dumps(clip), encoding='utf-8')
    if args.departed_clip:
        with args.departed_clip.open('x', encoding='utf-8') as output:
            json.dump(departed_clip, output)
    if args.report:
        with args.report.open('x', encoding='utf-8') as output:
            json.dump(summary, output, indent=2)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
