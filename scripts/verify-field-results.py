"""Check sealed Windows server results against Windows player logs or Quest logcat."""
import argparse
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import importlib.util
import ipaddress
import io
from itertools import chain
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import uuid
import zipfile
import zlib


COMBAT = ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken')
# TelemetryOutbox version 1 uses the WorldEventKind byte and .NET Guid byte order.
COMBAT_EVENT = struct.Struct('<qq16sB16s16s16si')
SHOT_FIRED, SHOT_HIT, ENEMY_ELIMINATED, PLAYER_DAMAGED = 0, 1, 2, 4
WORLD_COMBAT_KINDS = ('ShotFired', 'ShotHit', 'EnemyEliminated', 'PlayerDamaged')
EMPTY_GUID = bytes(16)
LAN = tuple(map(ipaddress.IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
SERVER_MARKER = re.compile(r'VR_SERVER_(ADMISSION_APPROVED|PEER|CLIENT_LEFT|DEBRIEF_ACK|DEBRIEF_TIMEOUT) id=(0|[1-9][0-9]{0,19})(?: endpoint=(\S+))?')
CONNECT = re.compile(r'VR_CLIENT_CONNECTED id=(0|[1-9][0-9]{0,19})')
LOGCAT_UNITY = re.compile(r'[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3} +'
                          r'([1-9][0-9]{0,9}) +[1-9][0-9]{0,9} I Unity *: (.*)')
OPENXR_RUNTIME = re.compile(r'\[XR\] .* Runtime Name: (\S.{0,127})')
PLAYER_MARKERS = ('VR_CLIENT_CONNECTED', 'VR_CLIENT_DISCONNECTED', 'VR_CLIENT_DEBRIEF_FINAL')
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_WINDOWS_LINK_BYTES = 64 * 1024
MAX_ALIGNMENT_BYTES = 16 * 1024
QUEST_ROOMS = (1, 2, 3, 4, 5)
MAX_QUEST_PLAN_BYTES = 32768
MAX_CONCURRENT_FRAME_GAP_MS = 500


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def limited_read(stream):
    data = stream.read(MAX_FILE_BYTES + 1)
    require(len(data) <= MAX_FILE_BYTES, 'Evidence exceeds the per-file size limit')
    return data


def content(path):
    with path.open('rb') as stream:
        return limited_read(stream).decode('utf-8-sig')


def read_json(text):
    def fields(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), 'Duplicate JSON field')
        return result

    return json.loads(text, parse_float=Decimal, object_pairs_hook=fields)


def integer(value, lower=0, upper=2**63 - 1):
    require(type(value) is int and lower <= value <= upper, 'Invalid numeric evidence')
    return value


def identity(value):
    require(type(value) is str, 'Invalid evidence identity')
    parsed = uuid.UUID(value)
    require(parsed.int and str(parsed) == value, 'Invalid evidence identity')
    return value


def ipv4(value):
    address = ipaddress.IPv4Address(value)
    require(not (address.is_unspecified or address.is_multicast or address.is_reserved), 'Invalid IPv4 evidence address')
    return address


def read_quest_document(path):
    with path.open('rb') as source:
        raw = source.read(MAX_QUEST_PLAN_BYTES + 1)
    require(len(raw) <= MAX_QUEST_PLAN_BYTES, 'Quest plan or report is too large')
    value = read_json(raw.decode('utf-8-sig'))
    require(type(value) is dict, 'Expected a Quest JSON object')
    return value, raw


def read_quest_json(path):
    return read_quest_document(path)[0]


def read_quest_plan_file(path):
    value = read_quest_json(path)
    require(type(value.get('version')) is int and value['version'] == 1,
            'Expected a version 1 Quest plan or report')
    return value


def quest_seats(rows, field):
    require(type(rows) is list and 1 <= len(rows) <= 25, 'Expected 1 to 25 mapped Quest seats')
    seats = {}
    for row in rows:
        require(type(row) is dict and set(row) == {'roomId', 'seat', field}, 'Unexpected Quest seat mapping fields')
        room, seat = integer(row['roomId'], 1, 5), integer(row['seat'], 1, 5)
        require(type(row[field]) is str and (room, seat) not in seats, 'Invalid or repeated Quest seat mapping')
        seats[room, seat] = row[field]
    return seats


def read_quest_device_map(path):
    value = read_quest_plan_file(path)
    require(set(value) == {'version', 'seats'}, 'Unexpected Quest device map fields')
    serials = quest_seats(value['seats'], 'serial')
    require(len(set(serials.values())) == len(serials) and all(re.fullmatch(r'[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}', serial)
            for serial in serials.values()), 'Use distinct explicit ADB serials')
    return serials


def quest_network_address(value):
    require(type(value) is str, 'Expected a Quest plan IPv4 address')
    parsed = ipv4(value)
    require(str(parsed) == value and (parsed.is_loopback or any(parsed in network for network in LAN)),
            'Use a canonical private or loopback IPv4 address')
    return value


def read_quest_network_plan(path, *, allow_shared_sources=False):
    plan = read_quest_plan_file(path)
    require(set(plan) == {'version', 'mode', 'endpoints', 'sources'}, 'Unexpected Quest network plan fields')
    sources = {seat: quest_network_address(value) for seat, value in quest_seats(plan['sources'], 'address').items()}
    if not allow_shared_sources:
        require(len(set(sources.values())) == len(sources), 'Use a distinct IPv4 for each mapped Quest')
    mode = plan['mode']
    require(mode in ('Independent', 'Linked'), 'Expected Independent or Linked venue mode')
    expected = {QUEST_ROOMS} if mode == 'Linked' else {(room,) for room in QUEST_ROOMS}
    endpoints = plan['endpoints']
    require(type(endpoints) is list and len(endpoints) == len(expected), 'Provide every game endpoint for the venue mode')
    groups = {}
    for row in endpoints:
        require(type(row) is dict and set(row) == {'roomIds', 'address', 'port'}, 'Unexpected game endpoint fields')
        rooms = row['roomIds']
        require(type(rooms) is list and all(type(room) is int for room in rooms)
                and tuple(rooms) in expected and tuple(rooms) not in groups, 'Invalid or repeated game endpoint')
        groups[tuple(rooms)] = quest_network_address(row['address']), integer(row['port'], 1024, 65535)
    require(len(set(groups.values())) == len(groups), 'A game binding is used by more than one endpoint')
    return mode, groups, sources


def peer_address(endpoint):
    host, separator, port = endpoint.rpartition(':')
    require(separator and re.fullmatch(r'[1-9][0-9]{0,4}', port), 'Missing or invalid UDP peer endpoint')
    integer(int(port), 1, 65535)
    if host.startswith('[') and host.endswith(']'):
        mapped = ipaddress.IPv6Address(host[1:-1]).ipv4_mapped
        require(mapped is not None, 'Expected an IPv4 UDP peer')
        host = str(mapped)
    return ipv4(host), int(port)


def server_connections(log, port, *, verify_history=False, allow_timeout=False):
    approved, peers, released, acknowledged = {}, {}, {}, set()
    started = 0
    for order, line in enumerate(log.splitlines()):
        if line.startswith('VR_NETWORK_STARTED '):
            require(line == f'VR_NETWORK_STARTED role=Server started=True background=True port={port}',
                    'Server log startup differs from the reported UDP binding')
            started += 1
        if line.startswith('VR_SERVER_PEER_LIMIT'):
            raise EvidenceError('UDP peer log reached its recording limit')
        if not (line.startswith(('VR_SERVER_ADMISSION_APPROVED ', 'VR_SERVER_PEER ', 'VR_SERVER_DEBRIEF_ACK ', 'VR_SERVER_DEBRIEF_TIMEOUT '))
                or (verify_history and line.startswith('VR_SERVER_CLIENT_LEFT '))):
            continue
        require(started == 1, 'Server connection marker precedes startup')
        match = SERVER_MARKER.fullmatch(line)
        require(match is not None, 'Malformed server connection marker')
        kind, connection, endpoint = match.groups()
        require(bool(endpoint) == (kind == 'PEER'), 'Unexpected server marker format')
        if kind == 'ADMISSION_APPROVED':
            require(connection not in approved, 'Duplicate server admission marker')
            approved[connection] = order
        elif kind == 'PEER':
            require(connection in approved and connection not in peers and connection not in released, 'Missing approval or duplicate UDP peer marker')
            peers[connection] = endpoint
        elif kind == 'CLIENT_LEFT':
            if connection in approved:
                require(connection not in released, 'Duplicate server release marker')
                released[connection] = order
        elif kind == 'DEBRIEF_ACK':
            require(connection in peers and connection not in acknowledged, 'Missing UDP peer or duplicate server acknowledgement')
            require(connection not in released, 'Server acknowledgement follows server release')
            acknowledged.add(connection)
        elif not allow_timeout:
            raise EvidenceError('Server recorded a player result timeout')
    require(started == 1, 'Expected one original server startup in the log')
    return peers, acknowledged, approved, released


def client_result(log, *, connections=None, require_startup=False, startup_port=None):
    connection = None
    final = None
    seen = set()
    started = not require_startup
    for line in log.splitlines():
        if require_startup and line.startswith('VR_NETWORK_STARTED '):
            require(not started and client_startup_on_port(line, startup_port), 'Expected one original Windows client startup')
            started = True
        if line.startswith(PLAYER_MARKERS):
            require(started, 'Windows player marker precedes the original client startup')
        if line.startswith('VR_CLIENT_CONNECTED '):
            match = CONNECT.fullmatch(line)
            require(match is not None and connection is None and final is None, 'Unexpected player connection marker')
            connection = match.group(1)
            require(connection not in seen, 'Player connection number reused')
            seen.add(connection)
            if connections is not None:
                connections.append(connection)
        elif line == 'VR_CLIENT_DISCONNECTED':
            connection = None
        elif line.startswith('VR_CLIENT_DEBRIEF_FINAL '):
            require(connection is not None and final is None, 'Player final result lacks a unique live connection')
            final = (connection, read_json(line.removeprefix('VR_CLIENT_DEBRIEF_FINAL ')))
    require(final is not None and connection is None, 'Missing player final result or terminal disconnect')
    return final


def client_startup_on_port(message, port=None):
    match = re.fullmatch(r'VR_NETWORK_STARTED role=Client started=True background=(True|False) port=([1-9][0-9]{0,4})', message)
    return match is not None and int(match[2]) <= 65535 and (port is None or int(match[2]) == port)


def quest_client_result(log, pid, port, *, connections=None):
    pid = str(integer(pid, 1, 2**31 - 1))
    started = False
    markers = []
    for line in log.splitlines():
        entry = LOGCAT_UNITY.fullmatch(line)
        if entry is None:
            continue
        process, message = entry.groups()
        if message.startswith('VR_NETWORK_STARTED '):
            require(process == pid and not started and client_startup_on_port(message, port),
                'Quest logcat does not contain one original client startup on the game port')
            started = True
        elif message.startswith(PLAYER_MARKERS):
            require(process == pid and started, 'Quest logcat player marker is outside the original client process or startup')
            markers.append(message)
    require(started, 'Missing original Quest client startup in logcat')
    return client_result('\n'.join(markers), connections=connections)


def verify_reconnect_chain(connections, used, peers, acknowledged, approved, released, expected_ip):
    require(not used.intersection(connections), 'A connection was reused across player logs')
    for previous, following in zip(connections, connections[1:]):
        require(previous in peers and previous not in acknowledged and following in approved
                and previous in released and released[previous] < approved[following],
                'Missing server release before the next approved connection')
        require(peer_address(peers[previous])[0] == expected_ip, 'Historical UDP peer differs from the declared source')
    used.update(connections)


def windows_player_source(log, port):
    startup = []
    for line in log.splitlines():
        if line.startswith(('VR_OPENXR_STARTUP ', 'VR_NETWORK_STARTED ', 'VR_CLIENT_CONNECTED ')):
            if line.startswith('VR_CLIENT_CONNECTED '):
                startup.append(('connected', None))
                break
            startup.append((line, None))
        elif line.startswith('[XR] ') and ' Runtime Name:' in line:
            runtime = OPENXR_RUNTIME.fullmatch(line)
            require(runtime is not None, 'Windows OpenXR runtime record is malformed')
            startup.append(('runtime', runtime.group(1).strip()))
    if len(startup) == 2 and client_startup_on_port(startup[0][0], port):
        return 'windows-desktop-simulated', 'Simulated'
    require(len(startup) == 5 and startup[0][0] == 'VR_OPENXR_STARTUP status=requested'
            and startup[1][0] == 'runtime' and startup[2][0] == 'VR_OPENXR_STARTUP status=active'
            and client_startup_on_port(startup[3][0], port),
            'Windows player lacks an original desktop or OpenXR startup on the game port')
    if startup[1][1].casefold() == 'unity mock runtime':
        return 'windows-openxr-mock-tracked', 'Tracked'
    return 'windows-openxr-tracked', 'Tracked'


def roster(rows, key, size):
    require(type(rows) is list and len(rows) == size, 'Player count differs from the final roster')
    indexed = {identity(row[key]): row for row in rows}
    require(len(indexed) == size, 'Duplicate player identity')
    return indexed


def scores(row):
    values = tuple(integer(row[field]) for field in COMBAT) + (integer(row['health'], upper=100),)
    accuracy = row['accuracyPercent']
    require(type(accuracy) in (int, Decimal) and 0 <= accuracy <= 100, 'Invalid player accuracy')
    return values + (accuracy,)


def verify_combat_journal(path, session_id, stream_id, origin, final_sequence, authority_end, ledger, *, fired=None):
    digest = hashlib.sha256()
    projected = {uuid.UUID(pid).bytes_le: dict.fromkeys(COMBAT, 0) | {'health': 100} for pid in ledger}
    reports, shots, eliminated = {}, {}, set()
    acknowledged = 0
    complete = sealed = False

    def apply(record):
        sequence, observed, report, kind, player, shot, enemy, damage = record
        require(sequence == len(reports) + 1 <= final_sequence and 1 <= observed < authority_end
                and report != EMPTY_GUID and report not in reports and player in projected,
                'Invalid combat journal event sequence, identity or player')
        totals = projected[player]
        if kind == PLAYER_DAMAGED:
            require(shot == enemy == EMPTY_GUID and 1 <= damage <= 1000 and totals['health'] > 0,
                    'Invalid combat journal damage')
            actual = min(damage, totals['health'])
            totals['hitsReceived'] += 1
            totals['damageTaken'] += actual
            totals['health'] -= actual
        else:
            require(shot != EMPTY_GUID and damage == 0, 'Invalid combat journal shot')
            if kind == SHOT_FIRED:
                require(enemy == EMPTY_GUID and shot not in shots and totals['health'] > 0, 'Invalid combat journal fire')
                shots[shot] = (player, EMPTY_GUID)
                totals['ammoUsed'] += 1
                if fired is not None:
                    fired[sequence] = (report, player, shot, observed)
            else:
                require(enemy != EMPTY_GUID and enemy not in eliminated, 'Invalid combat journal target')
                if kind == SHOT_HIT:
                    require(shots.get(shot) == (player, EMPTY_GUID), 'Combat journal hit needs the original unscored shot')
                    shots[shot] = (player, enemy)
                    totals['shotsHit'] += 1
                else:
                    require(kind == ENEMY_ELIMINATED and shots.get(shot) == (player, enemy),
                            'Combat journal elimination needs the original confirmed hit')
                    eliminated.add(enemy)
                    totals['kills'] += 1
        reports[report] = sequence

    with path.open('rb') as source:
        before = os.fstat(source.fileno())

        def read(length):
            raw = source.read(length)
            require(len(raw) == length, 'Torn combat journal record')
            digest.update(raw)
            return raw

        def frame():
            length, = struct.unpack('<i', read(4))
            require(1 <= length <= 65536, 'Invalid combat journal record length')
            payload = read(length)
            require(hashlib.sha256(payload).digest() == read(32), 'Combat journal checksum mismatch')
            return payload

        origin_bytes = origin.encode('ascii')
        header = (struct.pack('<Bi', 1, 1) + uuid.UUID(session_id).bytes_le + uuid.UUID(stream_id).bytes_le
                  + bytes([len(origin_bytes)]) + origin_bytes)
        require(frame() == header, 'Combat journal header differs from the original session, stream or origin')
        while source.tell() < before.st_size:
            payload = frame()
            tag, body = payload[0], payload[1:]
            require(not sealed, 'Combat journal contains records after its seal')
            if tag == 2:
                require(not complete and len(body) >= 4, 'Invalid combat journal batch boundary')
                count, = struct.unpack_from('<i', body)
                require(1 <= count <= 500 and len(body) == 4 + count * COMBAT_EVENT.size, 'Invalid combat journal batch size')
                for record in COMBAT_EVENT.iter_unpack(body[4:]):
                    apply(record)
            elif tag == 3:
                require(not complete and body == struct.pack('<q', len(reports)), 'Invalid combat journal completion boundary')
                complete = True
            elif tag == 4:
                require(len(body) == 24, 'Invalid combat journal acknowledgement size')
                sequence, report = struct.unpack('<q16s', body)
                require(sequence > acknowledged and reports.get(report) == sequence, 'Invalid combat journal acknowledgement')
                acknowledged = sequence
            else:
                require(tag == 5 and not body and complete and acknowledged == len(reports), 'Invalid combat journal seal')
                sealed = True
        after = os.fstat(source.fileno())
        require(source.tell() == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
                'Combat journal changed during verification')

    require(sealed and acknowledged == final_sequence, 'Missing combat journal seal or exact acknowledged event sequence')
    for pid, row in ledger.items():
        totals = projected[uuid.UUID(pid).bytes_le]
        ammo, hits = totals['ammoUsed'], totals['shotsHit']
        totals['accuracyPercent'] = (Decimal(100 * hits) / ammo).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN) if ammo else 0
        require(scores(totals) == scores(row), 'Combat journal replay differs from sealed player statistics')
    return {'sha256': digest.hexdigest(), 'events': final_sequence, 'players': len(projected)}


def roster_periods(players, minimum_ms, applied_end, *, require_tracked=False, sealed_fires=None, require_living=False):
    expected = {pid: player['roomId'] for pid, player in players.items()}
    periods, fires, pending_fires = [], [], []
    start = previous = previous_tick = None
    combat_sequence = 0

    def match_fires(packet):
        nonlocal combat_sequence
        matched = []
        for event in packet['events']:
            if event['kind'] not in WORLD_COMBAT_KINDS:
                continue
            combat_sequence += 1
            if event['kind'] == 'ShotFired':
                source = sealed_fires.pop(combat_sequence, None)
                identities = tuple(uuid.UUID(identity(event[key])).bytes_le for key in ('eventId', 'playerId', 'shotId'))
                require(source is not None and source[:3] == identities and source[3] <= packet['observedSequence'],
                        'World fire differs from its original sealed combat event')
                matched.append((identity(event['playerId']), integer(event['tick'])))
        require(combat_sequence == packet['throughCombatSequence'], 'World packet has a different combat boundary')
        return matched

    def observe(packet):
        nonlocal start, previous, previous_tick
        matched = match_fires(packet) if sealed_fires is not None else ()
        frame = packet['frame']
        if frame['phase'] != 'Running' or packet['suspended'] is not False or packet['observedSequence'] >= applied_end:
            previous = None
            previous_tick = None
            pending_fires.clear()
            return
        rows = frame['players']
        require(type(rows) is list and len(rows) <= 25, 'Invalid player rows in the concurrent roster evidence')
        connected = {row['id']: integer(row['roomId'], 1, 5) for row in rows
                     if row['connected'] is True and (not require_tracked or row['rig']['kind'] == 'Tracked')
                     and (not require_living or (integer(row['health'], 0, 100) > 0
                                                 and row['rig']['kind'] in ('Tracked', 'Simulated')))}
        tick = integer(frame['tick'])
        if len(rows) != len(expected) or connected != expected or not tick:
            previous = None
            previous_tick = None
            pending_fires.clear()
            return
        elapsed = integer(packet['elapsedMilliseconds'])
        if (sealed_fires is not None or require_living) and tick == previous_tick:
            # Several packets may share a tick. Wait for actual advancement
            # before crediting any fire or extending the window.
            if previous is not None and elapsed - previous <= MAX_CONCURRENT_FRAME_GAP_MS:
                pending_fires.extend(pid for pid, event_tick in matched if event_tick == tick)
            else:
                previous = None
                pending_fires.clear()
            return
        if previous is None or elapsed - previous > MAX_CONCURRENT_FRAME_GAP_MS or tick <= previous_tick:
            start = elapsed
        else:
            fires.extend((previous, elapsed, pid) for pid in pending_fires)
            fires.extend((previous, elapsed, pid) for pid, event_tick in matched if previous_tick <= event_tick <= tick)
        pending_fires.clear()
        previous, previous_tick = elapsed, tick
        if elapsed - start >= minimum_ms:
            if periods and periods[-1][0] == start:
                periods[-1] = (start, elapsed)
            else:
                periods.append((start, elapsed))

    return observe, periods, fires


class VenueRosterOverlap:
    def __init__(self, minimum_ms, *, require_tracked=False, require_fire=False):
        self.minimum_ms = minimum_ms
        self.minimum = timedelta(milliseconds=minimum_ms)
        self.require_tracked = require_tracked
        self.require_fire = require_fire
        self.fires = []
        self.intervals = None

    def add(self, capture_started_at, periods, fires):
        require(capture_started_at is not None, 'Concurrent roster verification requires an original UTC capture clock')
        capture = datetime.fromisoformat(capture_started_at).astimezone(timezone.utc)
        self.fires.extend((capture + timedelta(milliseconds=before), capture + timedelta(milliseconds=after), pid)
                          for before, after, pid in fires)
        right = [(capture + timedelta(milliseconds=start), capture + timedelta(milliseconds=end)) for start, end in periods]
        if self.intervals is None:
            self.intervals = right
            return
        left, intersection = self.intervals, []
        i = j = 0
        while i < len(left) and j < len(right):
            a, b = left[i], right[j]
            start, end = max(a[0], b[0]), min(a[1], b[1])
            if end - start >= self.minimum:
                intersection.append((start, end))
            if a[1] <= b[1]:
                i += 1
            if b[1] <= a[1]:
                j += 1
        self.intervals = intersection

    def summary(self, players):
        require(self.intervals, 'Original recordings do not show the required continuous concurrent roster')
        candidates = self.intervals
        if self.require_fire:
            # A world event only gives a tick. Both samples bracketing it must
            # fit inside the common UTC window to count it for the original seat.
            fires = sorted(self.fires)
            candidates = []
            for start, end in self.intervals:
                seats = set()
                index = bisect_left(fires, start, key=lambda fire: fire[0])
                while index < len(fires) and fires[index][0] <= end:
                    _, after, player = fires[index]
                    if after <= end:
                        seats.add(player)
                    index += 1
                if len(seats) == players:
                    candidates.append((start, end))
            require(candidates, 'No continuous concurrent roster interval contains a sealed shot from every original seat')
        start, end = max(candidates, key=lambda pair: pair[1] - pair[0])
        return {'players': players, 'minimumMilliseconds': self.minimum_ms,
                'longestMilliseconds': (end - start) // timedelta(milliseconds=1),
                'maxFrameGapMilliseconds': MAX_CONCURRENT_FRAME_GAP_MS,
                'fromUtc': start.isoformat(), 'throughUtc': end.isoformat(),
                **({'playersWithConfirmedFire': players} if self.require_fire else {}),
                **({'rigKind': 'Tracked'} if self.require_tracked else {})}


class VenueReconnectWindow:
    def __init__(self, selection):
        require(type(selection) is dict and set(selection) == {'roomId', 'seat', 'firstUnavailableSequence', 'recoveredSequence'},
                'Select one original seat and the unavailable and recovered world sequences')
        self.room = integer(selection['roomId'], 1, 5)
        self.seat = integer(selection['seat'], 1, 5)
        self.first = integer(selection['firstUnavailableSequence'], 2)
        self.recovered = integer(selection['recoveredSequence'], self.first + 2)
        self.coverage = []
        self.target_window = None

    def watch(self, players, applied_end, final_sequence, *, tracked_only):
        target = next((pid for pid, player in players.items()
                       if (player['roomId'], player['seat'] + 1) == (self.room, self.seat)), None)
        if target is None:
            observe, periods, _ = roster_periods(players, 1, applied_end, require_tracked=tracked_only, require_living=True)

            def finish(capture):
                self.coverage.append([(capture + timedelta(milliseconds=first), capture + timedelta(milliseconds=last))
                                      for first, last in periods])
            return observe, finish

        require(self.recovered < final_sequence, 'Reconnect window boundary is outside the original Running recording')
        previous_tick = advancing_elapsed = first_tick = None
        boundaries = {}
        before = self.first - 1
        rigs = ('Tracked',) if tracked_only else ('Tracked', 'Simulated')

        def observe(packet):
            nonlocal previous_tick, advancing_elapsed, first_tick
            sequence = packet['sequence']
            if not before <= sequence <= self.recovered:
                return
            frame = packet['frame']
            require(frame['phase'] == 'Running' and packet['suspended'] is False and packet['observedSequence'] < applied_end,
                    'Reconnect window leaves the original Running phase')
            elapsed, tick = integer(packet['elapsedMilliseconds']), integer(frame['tick'], 1)
            if previous_tick is not None:
                require(tick >= previous_tick and elapsed - advancing_elapsed <= MAX_CONCURRENT_FRAME_GAP_MS,
                        'Reconnect window has a capture gap or stalled tick')
            if tick != previous_tick:
                advancing_elapsed = elapsed
            previous_tick = tick
            if sequence in (before, self.first, self.recovered):
                boundaries[sequence] = elapsed
            if sequence == self.first:
                first_tick = tick
            if sequence == self.recovered:
                require(first_tick is not None and tick > first_tick, 'Reconnect window does not advance beyond the unavailable pose')
            rows = roster(frame['players'], 'id', len(players))
            require(rows.keys() == players.keys() and all(integer(row['roomId'], 1, 5) == players[pid]['roomId']
                    and integer(row['health'], 0, 100) > 0 for pid, row in rows.items()),
                    'Reconnect window does not contain the original living room roster')
            available = {pid for pid, row in rows.items() if row['connected'] is True and row['rig']['kind'] in rigs}
            expected = players.keys() - ({target} if self.first <= sequence < self.recovered else set())
            require(available == expected and (target in expected or rows[target]['connected'] is False),
                    'Reconnect window does not isolate the selected seat or restore its pose')

        def finish(capture):
            require(boundaries.keys() == {before, self.first, self.recovered}, 'Missing reconnect window boundary frames')
            require(boundaries[self.recovered] > boundaries[self.first], 'Reconnect window capture clock does not advance')
            self.target_window = {sequence: capture + timedelta(milliseconds=elapsed) for sequence, elapsed in boundaries.items()}
        return observe, finish

    def summary(self, histories, players):
        require(any((row['roomId'], row['seat']) == (self.room, self.seat) for row in histories),
                'Selected reconnect seat has no verified retired connection')
        require(self.target_window is not None, 'Selected reconnect seat is missing from the original recording')
        before, first, recovered = (self.target_window[seq] for seq in (self.first - 1, self.first, self.recovered))
        require(all(any(start <= before and recovered <= end for start, end in intervals) for intervals in self.coverage),
                'Other rooms do not cover the reconnect window with continuous original poses')
        return {'roomId': self.room, 'seat': self.seat, 'unaffectedSeats': players - 1,
                'beforeSequence': self.first - 1, 'firstUnavailableSequence': self.first, 'recoveredSequence': self.recovered,
                'unavailableFrames': self.recovered - self.first, 'maxFrameGapMilliseconds': MAX_CONCURRENT_FRAME_GAP_MS,
                'observedUnavailableMilliseconds': (recovered - first) // timedelta(milliseconds=1),
                'beforeUtc': before.isoformat(), 'firstUnavailableUtc': first.isoformat(), 'recoveredUtc': recovered.isoformat()}


def verify_world_journal(path, world, combat_sequence, through, applied_end, *, player_sources=None, guarded_begin=None,
                         players=None, concurrency=None, sealed_fires=None, reconnect_window=None, on_packet=None,
                         control_batches=()):
    spec = importlib.util.spec_from_file_location('field_world_journal', Path(__file__).with_name('analyze-world-journal.py'))
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    expected = world['header']
    quest_mr = expected.get('calibration') == 'quest-room-mr-v1'
    begin_kind, begin = guarded_begin if guarded_begin is not None else (None, None)
    tracked_only = begin_kind == 'trackingBegin' or quest_mr
    allowed_rigs = ('Tracked',) if tracked_only else ('Tracked', 'Simulated')
    roster_label = 'tracked' if begin_kind == 'trackingBegin' else 'participating'
    begin_roster = None
    controls = {batch['appliedAtSequence']: batch for batch in control_batches}
    control_frames = {}
    if concurrency is not None:
        observe_roster, periods, fires = roster_periods(players, concurrency.minimum_ms, applied_end,
                                                       require_tracked=concurrency.require_tracked, sealed_fires=sealed_fires)
    if reconnect_window is not None:
        observe_reconnect, finish_reconnect = reconnect_window.watch(players, applied_end, world['acceptedSequence'],
            tracked_only=quest_mr)

    def observe_packet(packet):
        if begin is not None:
            check_begin_frame(packet)
        if concurrency is not None:
            observe_roster(packet)
        if reconnect_window is not None:
            observe_reconnect(packet)
        observed = packet['observedSequence']
        if observed in controls and packet['frame']['phase'] == 'Running' and packet['suspended'] is False and packet['frame']['tick'] > 0:
            batch = controls[observed]
            frame = packet['frame']
            if batch['action'] == 'SetEnvironment':
                require(packet['weather'] == batch['weather'] and packet['lightning'] is batch['lightning']
                        and frame['night'] is (batch['timeOfDay'] == 'Night'),
                        'Original Running frame disagrees with the venue environment batch')
            else:
                require(frame['behavior'] == batch['behavior'] and frame['autoAttack'] is batch['autoAttack']
                        and frame.get('roomEnemyPolicies') in (None, []),
                        'Original Running frame disagrees with the venue enemy policy batch')
            control_frames.setdefault(observed, {**batch, 'worldSequence': packet['sequence']})
        if on_packet is not None:
            on_packet(packet)

    def check_begin_frame(packet):
        nonlocal begin_roster
        if packet['sequence'] != begin['frame']['worldSequence']:
            return
        frame = packet['frame']
        require(integer(packet['elapsedMilliseconds']) == begin['frame']['elapsedMilliseconds']
                and integer(packet['observedSequence'], 1) == begin['appliedAtSequence'] - 1
                and packet['suspended'] is False and frame['phase'] == 'Preparing' and integer(frame['tick'], 0, 0) == 0,
                'Guarded Begin frame differs from the original Preparing boundary')
        rows = roster(frame['players'], 'id', len(players))
        require(set(rows) == set(players) and all(row['connected'] is True and row['rig']['kind'] in allowed_rigs
                    and integer(row['health'], 1, 100) and integer(row['roomId'], 1, 5) == players[pid]['roomId']
                    for pid, row in rows.items()), f'Guarded Begin frame does not contain the original {roster_label} roster')
        tracked = sum(row['rig']['kind'] == 'Tracked' for row in rows.values())
        begin_roster = {'trackedPlayers': tracked}
        if begin_kind == 'participationBegin':
            begin_roster.update(participants=len(rows), simulatedPlayers=len(rows) - tracked)

    def count_player_rigs(frame):
        rows = frame['players']
        require(type(rows) is list and len(rows) <= 25, 'Invalid player rows in the world journal')
        seen = set()
        for row in rows:
            require(type(row['connected']) is bool, 'Invalid player connection state in the world journal')
            if not row['connected']:
                continue
            pid = row['id']
            require(pid in player_sources and pid not in seen, 'World journal contains an unexpected connected player')
            source = player_sources[pid]
            require(integer(row['roomId'], 1, 5) == source['roomId'] and row['rig']['kind'] == source['rigKind'],
                    'World journal player room or rig differs from the original player log')
            source['runningFrames'] += 1
            seen.add(pid)

    try:
        journal = analyzer.analyze(path, accepted_sequence=begin['appliedAtSequence'] if begin is not None else None,
                                   expected_full_header=expected, on_running_frame=count_player_rigs if player_sources is not None else None,
                                   on_packet=observe_packet if controls or any(item is not None for item in (begin, concurrency, reconnect_window, on_packet)) else None)
    except EvidenceError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ArithmeticError, RecursionError) as error:
        raise EvidenceError('World journal failed source or record integrity verification') from error
    tail = journal['lastFrame']
    sequence = world['acceptedSequence']
    require(journal['complete'] is journal['sealed'] is True and journal['unacknowledgedFrames'] == 0
            and journal['acknowledgedSequence'] == sequence and journal['runningFrames'] > 0
            and tail['phase'] == 'Ended' and tail['suspended'] is False and tail['worldSequence'] == sequence
            and integer(journal['lastCombatSequence']) == combat_sequence,
            'World journal must contain active play and the exact durable world and combat seals')
    require(integer(tail['elapsedMilliseconds']) == integer(world['durationMilliseconds'])
            and integer(tail['observedSequence'], 1, through) >= (applied_end or 1)
            and datetime.fromisoformat(tail['capturedAtUtc']) == datetime.fromisoformat(world['capturedAtUtc']),
            'World journal terminal capture or management boundary differs from the sealed session')
    if player_sources is not None:
        require(all(source['runningFrames'] > 0 for source in player_sources.values()),
                'World journal lacks an active accepted pose for an original seat')
    if concurrency is not None:
        require(not sealed_fires, 'Original sealed combat fire is missing from the world journal')
        concurrency.add(journal['captureStartedAtUtc'], periods, fires)
    if reconnect_window is not None:
        capture = journal['captureStartedAtUtc']
        require(capture is not None, 'Reconnect window requires an original UTC capture clock')
        finish_reconnect(datetime.fromisoformat(capture).astimezone(timezone.utc))
    result = {'sha256': journal['sha256'], 'frames': sequence, 'runningFrames': journal['runningFrames']}
    if controls:
        require(control_frames.keys() == controls.keys(), 'World journal lacks an exact Running frame for a venue control batch')
        result['venueControlFrames'] = [control_frames[observed] for observed in sorted(control_frames)]
    if begin is not None:
        first = journal['firstApplied']
        require(begin_roster is not None and first is not None
                and first['worldSequence'] > begin['frame']['worldSequence'] and first['observedSequence'] < applied_end,
                'World journal lacks the guarded Begin witness or its subsequent application')
        result[begin_kind] = {'requestId': begin['requestId'], 'appliedAtSequence': begin['appliedAtSequence'],
                              'preparingFrame': begin['frame']['worldSequence'],
                              'firstRunningFrame': first['worldSequence'], **begin_roster}
    return result


def verify_experience(session, header):
    mode = session['environment']['mode']
    require(mode in ('VR', 'MR') and session['mission']['definition']['environment']['mode'] == mode,
            'Experience mode differs from the original mission')
    if mode == 'MR':
        require(header['origin'] == 'GameServer' and header.get('calibration') == 'quest-room-mr-v1',
                'MR alignment evidence requires the original calibrated game source')
    else:
        require(header.get('calibration') == 'uncalibrated-vr', 'VR world profile differs from the session mode')
    return mode


def verify_room_alignments(session, header, alignments):
    require(verify_experience(session, header) == 'MR', 'Room alignment evidence is only for MR sessions')
    rooms = session['roomIds']
    pins = session.get('roomAlignment')
    require(type(pins) is dict and {key for key, value in pins.items() if value is not None} == {f'room{room}' for room in rooms}
            and set(alignments) == set(rooms), 'Provide the locked alignment file for every original MR room')
    evidence = []
    for room in sorted(rooms):
        with alignments[room].open('rb') as source:
            raw = source.read(MAX_ALIGNMENT_BYTES + 1)
        require(0 < len(raw) <= MAX_ALIGNMENT_BYTES, 'Invalid room alignment file size')
        digest = hashlib.sha256(raw).hexdigest()
        require(pins[f'room{room}'] == digest, 'Room alignment bytes differ from the sealed session lock')
        exported = read_json(raw.decode('utf-8-sig'))
        require(integer(exported['version'], 1, 1) and exported['profile'] == 'room-floor-alignment-v1'
                and integer(exported['roomId'], 1, 5) == room and exported['withinTolerance'] is True,
                'Locked alignment export does not identify the original MR room')
        evidence.append({'roomId': room, 'sha256': digest})
    return evidence


def verify_udp_preflight(paths, binding, addresses):
    require(bool(addresses), 'UDP preflight needs an observed peer for this game binding')
    powershell = (shutil.which('powershell.exe') if os.name == 'nt' else None) or shutil.which('pwsh')
    require(powershell is not None, 'PowerShell is required to verify the original UDP reports')
    script = Path(__file__).with_name('check-lan-udp.ps1')
    command = [powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned', '-File', str(script),
               '-ListenerReport', str(paths[0]), '-ProbeReport', str(paths[1]), '-ExpectedServerAddress', binding['address'],
               '-ExpectedGamePort', str(binding['port']), '-ExpectedPeerAddresses', ','.join(map(str, sorted(addresses))),
               '-BindingObservedAtUtc', binding['observedAtUtc']]
    try:
        response = subprocess.run(command, capture_output=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        raise EvidenceError('UDP preflight report verification timed out') from None
    require(response.returncode == 0, 'UDP preflight differs from the game binding, accepted peer or preflight window')
    receipt = read_json(response.stdout.decode('utf-8-sig'))
    require(receipt.get('complete') is True and receipt.get('endpointVerified') is True and receipt.get('stage') == 'pair-verified',
            'UDP preflight pair has no binding confirmation')
    exchange = receipt['exchangeSha256']
    require(type(exchange) is str and re.fullmatch(r'[0-9a-f]{64}', exchange), 'Invalid UDP exchange digest')
    summary = {'samples': integer(receipt['matched'], 1, 20), 'exchangeSha256': exchange}
    return summary, integer(receipt['verifiedPeerIndex'], 0, len(addresses) - 1)


def verify_udp_source_preflights(pairs, binding, addresses):
    require(1 <= len(pairs) == len(addresses) <= 25, 'Provide one UDP preflight pair for each acknowledged source address at this binding')
    sources, exchanges, summaries = set(), set(), []
    for pair in pairs:
        summary, source = verify_udp_preflight(pair, binding, addresses)
        exchange = summary['exchangeSha256']
        require(source not in sources, 'UDP source preflights cover the same source more than once')
        require(exchange not in exchanges, 'UDP source preflights reused an exchange')
        sources.add(source)
        exchanges.add(exchange)
        summaries.append(summary)
    return {'observedSourceAddresses': len(addresses), 'verifiedSourceAddresses': len(sources),
            'pairs': sorted(summaries, key=lambda summary: summary['exchangeSha256'])}


def require_terminal_launcher(launcher):
    require(type(launcher) is dict and integer(launcher['schemaVersion'], 1, 1) and launcher['status'] == 'sealed-stopped'
            and launcher['complete'] is launcher['childExited'] is launcher['cleanupCompleted'] is True
            and integer(launcher['exitCode'], 0, 0) == 0, 'Launcher lacks terminal evidence')


def sealed_result_boundary(session, statistics, world, combat, stream_id):
    header, origin = world['header'], combat['origin']
    require(world['complete'] is combat['sealed'] is True and statistics['pendingTelemetry'] is False
            and header['streamId'] == combat['streamId'] == stream_id and header['origin'] == origin
            and origin in ('Simulation', 'GameServer') and session['combatStream'] == combat,
            'World and combat seals disagree')
    through = integer(session['sequence'], 1)
    require(integer(statistics['throughSequence'], 1) == through, 'Statistics do not match the terminal session sequence')
    return {'sessionId': session['id'], 'streamId': stream_id, 'origin': origin,
            'worldSequence': integer(world['acceptedSequence'], 1), 'throughSequence': through,
            'finalStreamSequence': integer(combat['acceptedSequence'])}


def verify_player_terminal_result(result, owner, stats, boundary):
    room = integer(owner['roomId'], 1, 5)
    require(integer(result['roomId'], 1, 5) == integer(stats['roomId'], 1, 5) == room
            and result['admissionId'] == owner['admissionId'], 'Player result admission or room differs')
    require(integer(result['version'], 1, 1)
            and all(type(result[key]) is type(value) and result[key] == value for key, value in boundary.items())
            and scores(result) == scores(stats), 'Player result differs from the final seals or statistics')
    return room


def verify(topology, server_ips, launcher, session, statistics, endpoint, server_log, player_logs, *, quest_player_logs=(),
           world_journal=None, combat_journal=None, room_alignments=None, udp_preflight=None, udp_source_preflights=None,
           verify_player_sources=False, verify_reconnect_history=False):
    report, _ = verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log,
                               len(player_logs) + len(quest_player_logs), player_logs, quest_player_logs=quest_player_logs,
                               world_journal=world_journal, combat_journal=combat_journal, room_alignments=room_alignments, udp_preflight=udp_preflight,
                               udp_source_preflights=udp_source_preflights, verify_player_sources=verify_player_sources,
                               verify_reconnect_history=verify_reconnect_history)
    return report


def verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log, size, player_logs, *,
                   require_remote=True, quest_player_logs=(), world_journal=None, combat_journal=None, applied_end=None, room_alignments=None,
                   udp_preflight=None, udp_source_preflights=None, verify_player_sources=False, quest_capture_logs=(),
                   guarded_begin=None, concurrency=None, verify_reconnect_history=False, reconnect_window=None,
                   quest_deployments=None, require_distinct_remote_roster=False, control_batches=(),
                   observed_quest_addresses=None):
    integer(size, 1, 25)
    require(topology in ('same-host', 'direct-lan') and server_ips, 'Missing topology or server addresses')
    require(not verify_player_sources or world_journal is not None, 'Player source verification requires the original closed world journal')
    require(udp_preflight is None or udp_source_preflights is None, 'Use either single-pair or all-source UDP preflight verification')
    require_terminal_launcher(launcher)
    binding = launcher['udpBinding']
    bound = ipv4(binding['address'])
    require(bound in server_ips and integer(binding['processId'], 1) == integer(launcher['childPid'], 1), 'UDP binding differs from the server interface or process')
    port = integer(binding['port'], 1024, 65535)
    world, combat = launcher['finalWorld'], launcher['finalCombatStream']
    header = world['header']
    session_id, stream_id = identity(launcher['sessionId']), identity(launcher['streamId'])
    require(integer(endpoint['version'], 1, 1) and endpoint['sessionEnded'] is True
            and endpoint['sessionId'] == session_id and endpoint['streamId'] == stream_id
            and ipv4(endpoint['address']) == bound and integer(endpoint['port'], 1024, 65535) == port,
            'Published endpoint differs from the observed server binding or terminal session')
    rooms = session['roomIds']
    require(type(rooms) is list and len(rooms) in (1, 5), 'Unsupported room scope')
    require(all(integer(room, 1, 5) for room in rooms) and len(set(rooms)) == len(rooms), 'Invalid room scope')
    mode = 'Linked' if len(rooms) == 5 else 'Independent'
    require(session['id'] == header['sessionId'] == statistics['sessionId'] == session_id
            and session['state'] == 'Ended' and session['mode'] == mode and header['roomIds'] == rooms,
            'Session identity, room scope or terminal state differs')
    started, ended = (datetime.fromisoformat(session[field]) for field in ('startedAtUtc', 'endedAtUtc'))
    require(started.utcoffset() is not None and ended.utcoffset() is not None and started <= ended,
            'Invalid session start or end time')
    boundary = sealed_result_boundary(session, statistics, world, combat, stream_id)
    origin = boundary['origin']
    world_sequence, through, combat_sequence = (boundary[key] for key in ('worldSequence', 'throughSequence', 'finalStreamSequence'))
    players = roster(session['players'], 'id', size)
    ledger = roster(statistics['players'], 'playerId', size)
    require(set(players) == set(ledger), 'Final roster and statistics disagree')
    require(len({identity(p['admissionId']) for p in players.values()}) == size, 'Duplicate admission identity')
    if statistics['origin'] is None:
        require(combat_sequence == 0 and all(scores(p) == (0, 0, 0, 0, 0, 100, 0) for p in ledger.values()), 'Missing statistics origin for nonempty combat')
    else:
        require(statistics['origin'] == origin, 'Statistics source differs from the seals')

    peers, acknowledged, approved, released = server_connections(server_log, port, verify_history=verify_reconnect_history)
    used_players, used_connections, endpoints = set(), set(), set()
    verified_history, reconnected_seats = set(), []
    room_sources = {}
    player_sources = {} if verify_player_sources else None
    source_seats = set()
    quest_players = 0
    windows_logs = ((address, log, None, None) for address, log in player_logs)
    quest_logs = ((address, log, pid, None) for address, log, pid in quest_player_logs)
    for expected_ip, log, pid, capture_seat in chain(windows_logs, quest_logs, quest_capture_logs):
        history = [] if verify_reconnect_history else None
        connection, result = (client_result(log, connections=history, require_startup=verify_reconnect_history,
                                            startup_port=port if require_distinct_remote_roster else None) if pid is None
                              else quest_client_result(log, pid, port, connections=history))
        require(connection in acknowledged and connection not in used_connections, 'Missing or reused server acknowledgement')
        observed = peer_address(peers[connection])
        if expected_ip is None:
            require(capture_seat is not None and observed_quest_addresses is not None,
                    'Server-observed addresses require original mapped Quest capture evidence')
            expected_ip = observed[0]
            require(expected_ip not in observed_quest_addresses, 'Use a distinct observed IPv4 for each mapped Quest')
            observed_quest_addresses.add(expected_ip)
        require(observed[0] == expected_ip and observed not in endpoints, 'UDP peer differs from the declared source or is reused')
        player_id = identity(result['playerId'])
        require(player_id in players and player_id not in used_players, 'Unexpected or duplicated result player')
        owner, stats = players[player_id], ledger[player_id]
        if pid is not None:
            require(owner.get('headset') == 'Quest3' and topology == 'direct-lan' and expected_ip not in server_ips,
                    'Quest logcat requires a Quest 3 admission and its own direct LAN address')
            quest_players += 1
        room = verify_player_terminal_result(result, owner, stats, boundary)
        require(room in rooms, 'Player result admission or room differs')
        if capture_seat is not None:
            require((room, integer(owner['seat'], 0, 4) + 1) == capture_seat,
                    'Quest capture room or seat differs from the original admission')
        if pid is not None and quest_deployments is not None:
            seat = integer(owner['seat'], 0, 4) + 1
            require(quest_deployments.pop((room, seat), None) == (session_id, player_id, owner['admissionId'], port),
                    f'Quest deployment does not match the original admission and endpoint for room {room} seat {seat}')
        if player_sources is not None or verify_reconnect_history:
            seat = integer(owner['seat'], 0, 4) + 1
            require((room, seat) not in source_seats, 'Duplicate seat in the player source evidence')
            source_seats.add((room, seat))
        if verify_reconnect_history:
            verify_reconnect_chain(history, verified_history, peers, acknowledged, approved, released, expected_ip)
            if len(history) > 1:
                reconnected_seats.append({'roomId': room, 'seat': seat, 'retiredConnections': len(history) - 1})
        if player_sources is not None:
            source, rig = windows_player_source(log, port) if pid is None else ('quest-logcat-tracked', 'Tracked')
            if concurrency is not None and concurrency.require_tracked:
                require(source in ('quest-logcat-tracked', 'windows-openxr-tracked'),
                        f'Concurrent tracked roster requires original Quest or non-mock Windows OpenXR player logs; '
                        f'room {room} seat {seat} uses {source}')
            player_sources[player_id] = {'roomId': room, 'seat': seat, 'source': source, 'rigKind': rig, 'runningFrames': 0}
        used_players.add(player_id)
        used_connections.add(connection)
        endpoints.add(observed)
        room_sources.setdefault(room, []).append(observed[0])
    require(used_connections == acknowledged and used_players == set(players), 'Extra acknowledgement or missing result')
    if verify_reconnect_history:
        require(verified_history == peers.keys(), 'Server log contains unmatched UDP peer records')
    if require_distinct_remote_roster:
        require(verified_history == approved.keys(), 'Distinct remote roster requires a matched UDP source for every approved connection')
    require(all(len(sources) <= 5 for sources in room_sources.values()), 'Room participant limit exceeded')

    peer_ips = {address for address, _ in endpoints}
    remote = peer_ips - server_ips
    if topology == 'direct-lan':
        require((remote or not require_remote) and all(any(address in network for network in LAN) for address in peer_ips | {bound}),
                'Direct LAN needs private addresses and a peer outside the declared server addresses')
    else:
        require(not remote, 'A peer is outside the declared same-host addresses')
    preflight = verify_udp_preflight(udp_preflight, binding, peer_ips)[0] if udp_preflight else None
    source_preflight = verify_udp_source_preflights(udp_source_preflights, binding, peer_ips) if udp_source_preflights is not None else None
    sealed_fires = {} if concurrency is not None and concurrency.require_fire else None
    combat_evidence = verify_combat_journal(combat_journal, session_id, stream_id, origin, combat_sequence,
                                            applied_end if applied_end is not None else through, ledger,
                                            fired=sealed_fires) if combat_journal is not None else None
    journal = verify_world_journal(world_journal, world, combat_sequence, through, applied_end,
                                   player_sources=player_sources, guarded_begin=guarded_begin, players=players,
                                   concurrency=concurrency, sealed_fires=sealed_fires,
                                   reconnect_window=reconnect_window, control_batches=control_batches) if world_journal is not None else None
    alignments = None
    if room_alignments is not None:
        require(journal is not None and quest_players == size, 'MR alignment evidence requires the closed world journal and all original Quest logs')
        alignments = verify_room_alignments(session, header, room_alignments)
    return {'version': 1, 'consistent': True, 'declaredTopology': topology, 'mode': mode,
            'players': size, 'playersPerRoom': {room: len(room_sources[room]) for room in sorted(room_sources)}, 'distinctPeerAddresses': len(peer_ips),
            'distinctAddressesOutsideDeclaredServer': len(remote), 'serverAcknowledgements': len(acknowledged),
            'worldSequence': world_sequence, 'combatSequence': combat_sequence, 'physicalHostsVerified': False,
            'networkCapacityAccepted': False,
            **({'questLogcatPlayers': quest_players} if quest_players else {}),
            **({'udpPreflight': preflight} if preflight is not None else {}),
            **({'udpSourcePreflight': source_preflight} if source_preflight is not None else {}),
            **({'worldJournal': journal} if journal else {}),
            **({'combatJournal': combat_evidence} if combat_evidence else {}),
            **({'playerSources': sorted(player_sources.values(), key=lambda row: (row['roomId'], row['seat']))}
               if player_sources is not None else {}),
            **({'reconnectHistory': {'observedConnections': len(verified_history),
                                     'retiredConnections': len(verified_history) - len(used_connections),
                                     'reconnectedSeats': sorted(reconnected_seats, key=lambda row: (row['roomId'], row['seat']))}}
               if verify_reconnect_history else {}),
            **({'roomAlignments': alignments} if alignments is not None else {})}, room_sources


def evidence_zip_entry(archive, name):
    info = archive.getinfo(name)
    require(info.orig_filename == name and info.file_size <= MAX_FILE_BYTES
            and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and not (info.flag_bits & 1),
            'Unsupported or oversized evidence ZIP entry')
    with archive.open(info) as entry:
        return limited_read(entry)


def management_zip_records(data):
    names = ('session.json', 'statistics.json', 'endpoint.json')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(sorted(archive.namelist()) == sorted(names), 'Management ZIP must contain exactly the three original JSON records')
        return [read_json(evidence_zip_entry(archive, name)) for name in names]


def management_zip(path):
    with path.open('rb') as source:
        return management_zip_records(limited_read(source))


def venue_bundle(path, mode):
    names = ['linked.zip'] if mode == 'Linked' else [f'room-{room:02}.zip' for room in QUEST_ROOMS]
    with path.open('rb') as source, zipfile.ZipFile(io.BytesIO(limited_read(source))) as archive:
        require(sorted(archive.namelist()) == sorted(['closure.json', *names]),
                'Venue ZIP must contain only the original closure and exact session ZIPs for this mode')
        require(sum(info.file_size for info in archive.infolist()) <= MAX_FILE_BYTES, 'Venue ZIP exceeds the expanded size limit')
        closure = read_json(evidence_zip_entry(archive, 'closure.json'))['batch']
        return closure, {name: evidence_zip_entry(archive, name) for name in names}


def venue_windows_logs(rows, expected, evidence_path, players_per_room):
    require(type(rows) is list and 1 <= len(rows) <= 25, 'Provide one to 25 original Windows logs in windowsPlayers')
    groups = {}
    for row in rows:
        files = windows_log_paths(row, evidence_path)
        _, path, launch, _, bundle = files
        raw_log, _, _ = read_windows_evidence(path, launch, bundle)
        _, result = client_result(raw_log.decode('utf-8-sig'))
        session_id = identity(result['sessionId'])
        require(session_id in expected, 'Windows log belongs to a different venue session')
        group = groups.setdefault(session_id, [])
        group.append(files)
        require(len(group) <= len(expected[session_id]['roomIds']) * players_per_room,
                'Too many Windows logs for an original venue session')
    return groups


def windows_log_paths(row, evidence_path):
    base = {'address', 'log'}
    launcher = base | {'launcherReport'}
    bundled = {'address', 'evidenceZip'}
    require(type(row) is dict and set(row) in (base, launcher, launcher | {'linkMetrics'}, bundled, bundled | {'linkMetrics'}),
            'Provide either the original Windows files or the player evidence ZIP for one address')
    launch = evidence_path(row['launcherReport']) if 'launcherReport' in row else None
    metrics = evidence_path(row['linkMetrics']) if 'linkMetrics' in row else None
    log = evidence_path(row['log']) if 'log' in row else None
    bundle = evidence_path(row['evidenceZip']) if 'evidenceZip' in row else None
    return ipv4(row['address']), log, launch, metrics, bundle


def read_windows_evidence(log, launcher, bundle):
    if bundle is not None:
        with bundle.open('rb') as source:
            require(os.fstat(source.fileno()).st_size <= MAX_FILE_BYTES + MAX_WINDOWS_LINK_BYTES + 65536,
                    'Windows evidence ZIP exceeds its file limit')
            with zipfile.ZipFile(source) as archive:
                names = sorted(archive.namelist())
                require(names in (['launch-report.json', 'player.log'], ['launch-report.json', 'link-metrics.json', 'player.log']),
                        'Windows evidence ZIP must contain the original player log and launcher report, with optional link metrics')
                require(archive.getinfo('launch-report.json').file_size <= 4096, 'Windows launcher report exceeds its ZIP entry limit')
                metrics = None
                if 'link-metrics.json' in names:
                    require(0 < archive.getinfo('link-metrics.json').file_size <= MAX_WINDOWS_LINK_BYTES,
                            'Windows link report exceeds its file limit')
                    metrics = evidence_zip_entry(archive, 'link-metrics.json')
                return (evidence_zip_entry(archive, 'player.log'),
                        evidence_zip_entry(archive, 'launch-report.json').decode('utf-8-sig'), metrics)
    with log.open('rb') as source:
        raw_log = limited_read(source)
    return raw_log, content(launcher) if launcher is not None else None, None


def verify_windows_release(log_hash, launch, windows_hash, *, has_link_metrics=False):
    require(launch.get('status') == 'exited' and integer(launch.get('exitCode'), 0, 0) == 0
            and integer(launch.get('processId'), 1, 2**31 - 1) and launch.get('playerManifestSha256') == windows_hash,
            'Windows launcher did not exit with the original venue release manifest')
    require(launch.get('playerLogSha256') == log_hash if 'playerLogSha256' in launch else has_link_metrics,
            'Windows release evidence does not match the original player log bytes')


def read_windows_seat_map(path):
    value = read_json(content(path))
    require(type(value) is dict and set(value) == {'version', 'seats'}, 'Invalid Windows seat map')
    integer(value['version'], 1, 1)
    rows = value['seats']
    require(type(rows) is list and 1 <= len(rows) <= 25, 'Expected 1 to 25 Windows seats')
    seats, stations = {}, set()
    for row in rows:
        require(type(row) is dict and set(row) == {'roomId', 'seat', 'station'}, 'Invalid Windows seat map row')
        seat = integer(row['roomId'], 1, 5), integer(row['seat'], 1, 5)
        station = row['station']
        require(type(station) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,31}', station), 'Invalid Windows station label')
        require(seat not in seats and station.lower() not in stations, 'Windows seat map repeats a seat or station')
        seats[seat] = station
        stations.add(station.lower())
    return seats


def read_windows_station_addresses(path, seat_map):
    with path.open('rb') as source:
        raw = source.read(8193)
    require(len(raw) <= 8192, 'Windows station address map exceeds its file limit')
    value = read_json(raw.decode('utf-8-sig'))
    require(type(value) is dict and set(value) == {'version', 'stations'}, 'Invalid Windows station address map')
    integer(value['version'], 1, 1)
    rows = value['stations']
    require(type(rows) is list and len(rows) == len(seat_map), 'Provide an address for every mapped Windows station')
    expected = {station.lower(): seat for seat, station in seat_map.items()}
    addresses = {}
    for row in rows:
        require(type(row) is dict and set(row) == {'station', 'address'}
                and type(row['station']) is str and type(row['address']) is str, 'Invalid Windows station address row')
        seat = expected.get(row['station'].lower())
        require(seat is not None and seat not in addresses, 'Windows station address map names an unknown or repeated station')
        addresses[seat] = ipv4(row['address'])
    return addresses, hashlib.sha256(raw).hexdigest()


def windows_inbox(directory, inputs, expected, players_per_room, windows_hash, seat_map, evidence_path, link_criteria,
                  station_addresses=None):
    require(directory.is_dir(), 'Windows evidence inbox must be a directory')
    require(type(windows_hash) is str and re.fullmatch(r'[0-9a-f]{64}', windows_hash),
            'Windows evidence inbox requires the original Windows release report')
    files = sorted(path for path in directory.iterdir() if path.suffix.lower() == '.zip' and path.is_file())
    require(len(files) <= 50, 'Windows evidence inbox contains more than 50 ZIPs')
    batches, roster_seats = {}, {}
    for _, launcher, session, statistics, endpoint, server_log in inputs:
        session_id = identity(session['id'])
        original = expected.get(session_id)
        require_terminal_launcher(launcher)
        require(original is not None and session_id not in batches and session['state'] == 'Ended'
                and original['world'] == original['combat'] == 'Sealed'
                and endpoint['sessionEnded'] is True
                and launcher['sessionId'] == endpoint['sessionId'] == session_id and session['roomIds'] == original['roomIds']
                and launcher['streamId'] == endpoint['streamId'] == original['replay']['streamId'],
                'Windows inbox roster or endpoint differs from the original sealed batch')
        world, combat = launcher['finalWorld'], launcher['finalCombatStream']
        header = world['header']
        boundary = sealed_result_boundary(session, statistics, world, combat, launcher['streamId'])
        require(header['sessionId'] == statistics['sessionId'] == session_id and header['roomIds'] == session['roomIds']
                and boundary['worldSequence'] == integer(original['replay']['throughSequence'], 1),
                'Windows inbox statistics or seals differ from the original closure')
        port = integer(endpoint['port'], 1024, 65535)
        peers, acknowledgements, _, _ = server_connections(server_log, port, allow_timeout=True)
        size = len(session['roomIds']) * players_per_room
        owners, ledger = roster(session['players'], 'id', size), roster(statistics['players'], 'playerId', size)
        require(owners.keys() == ledger.keys(), 'Final roster and statistics disagree')
        for player_id, owner in owners.items():
            room, seat = integer(owner['roomId'], 1, 5), integer(owner['seat'], 0, 4) + 1
            require(room in original['roomIds'] and (room, seat) not in roster_seats, 'Windows inbox roster repeats or misplaces a seat')
            roster_seats[room, seat] = (session_id, player_id)
        batches[session_id] = (boundary, owners, ledger, peers, acknowledgements)
    require(all(sum(seat[0] == room for seat in roster_seats) == players_per_room for room in range(1, 6)),
            'Windows inbox original roster has an unexpected room size')
    if seat_map is not None:
        require(seat_map.keys() <= roster_seats.keys(), 'Windows seat map names a seat outside the original batch roster')
    selected = {owner: seat for seat, owner in roster_seats.items() if seat_map is None or seat in seat_map}
    received, groups, issues, connections, measured = {}, {}, [], set(), {}
    for file in files:
        try:
            path = evidence_path(str(file))
            raw_log, raw_launch, raw_metrics = read_windows_evidence(None, None, path)
            connection, result = client_result(raw_log.decode('utf-8-sig'))
            session_id, player_id = identity(result['sessionId']), identity(result['playerId'])
            require(session_id in batches, 'Player ZIP belongs to another venue batch')
            boundary, owners, ledger, peers, acknowledgements = batches[session_id]
            seat = selected.get((session_id, player_id))
            require(seat is not None, 'Player ZIP does not match an expected Windows seat')
            log_hash, launch = hashlib.sha256(raw_log).hexdigest(), read_json(raw_launch)
            require(raw_metrics is not None or 'linkMetrics' not in launch, 'Player ZIP lacks its recorded Windows link report')
            metrics = verify_windows_link(log_hash, connection, launch, raw_metrics, link_criteria) if raw_metrics is not None else None
            verify_windows_release(log_hash, launch, windows_hash, has_link_metrics=raw_metrics is not None)
            require(connection in acknowledgements, 'Player ZIP lacks an original server acknowledgement')
            verify_player_terminal_result(result, owners[player_id], ledger[player_id], boundary)
            require(seat not in received and (session_id, connection) not in connections, 'Player ZIP repeats a seat or acknowledged connection')
            address, _ = peer_address(peers[connection])
            if station_addresses is not None:
                require(address == station_addresses[seat], f'Server-observed IPv4 differs from the address assigned to Windows station {seat_map[seat]}')
        except EvidenceError as error:
            issues.append({'file': file.name, 'reason': str(error)})
            continue
        except (OSError, UnicodeError, ArithmeticError, AttributeError, KeyError, TypeError, ValueError,
                RecursionError, zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError):
            issues.append({'file': file.name, 'reason': 'Player ZIP cannot be read as original Windows evidence'})
            continue
        received[seat] = file.name
        if metrics is not None:
            measured[seat] = metrics
        connections.add((session_id, connection))
        groups.setdefault(session_id, []).append((address, None, None, None, path))

    def seat_row(seat):
        return {'roomId': seat[0], 'seat': seat[1], **({'station': seat_map[seat]} if seat_map is not None else {})}

    missing = sorted(set(selected.values()) - received.keys())
    if measured:
        issues.extend({'file': received[seat], 'reason': 'Windows link evidence must cover every Windows seat in the venue'}
                      for seat in sorted(received.keys() - measured.keys()))
    link_report = {}
    if measured or link_criteria is not None:
        missing_metrics = sorted(set(selected.values()) - measured.keys())
        metrics_summary = {
            'verifiedSeats': len(measured),
            'missingSeats': [seat_row(seat) for seat in missing_metrics],
            'seats': [dict(seat_row(seat), file=received[seat], **measured[seat]) for seat in sorted(measured)],
        }
        if link_criteria is not None:
            metrics_summary['criteria'] = link_criteria
            metrics_summary['meetsCriteria'] = not missing_metrics and all(
                not row.get('criteriaFailures') for row in measured.values())
        link_report['windowsLinkMetrics'] = metrics_summary
    return groups, {'complete': not missing and not issues, 'expectedWindowsSeats': len(selected),
                    'receivedWindowsSeats': len(received), 'missingSeats': [seat_row(seat) for seat in missing],
                    'receivedSeats': [dict(seat_row(seat), file=received[seat]) for seat in sorted(received)], 'issues': issues,
                    **link_report}


def verify_windows_link(log_hash, connection, launch, raw_metrics, criteria=None):
    require(0 < len(raw_metrics) <= MAX_WINDOWS_LINK_BYTES, 'Windows link report exceeds its file limit')
    metrics = read_json(raw_metrics.decode('utf-8-sig'))
    proof = launch.get('linkMetrics')
    require(launch.get('status') == 'exited' and integer(launch.get('exitCode'), 0, 0) == 0
            and type(proof) is dict and set(proof) == {'logSha256', 'metricsSha256'}
            and proof['logSha256'] == log_hash
            and proof['metricsSha256'] == hashlib.sha256(raw_metrics).hexdigest(),
            'Windows launcher did not record these original link and player log bytes')
    require(integer(metrics.get('version'), 1, 1) and metrics.get('complete') is True and metrics.get('reason') == 'Limit'
            and integer(metrics.get('processId'), 1, 2**31 - 1) == integer(launch.get('processId'), 1, 2**31 - 1)
            and integer(metrics.get('connection'), 1, 2**64 - 1) == int(connection)
            and type(metrics.get('batchMode')) is bool and type(metrics.get('graphicsDeviceActive')) is bool,
            'Windows link report does not belong to the original process and final acknowledged connection')
    samples = metrics['samples']
    require(type(samples) is list and len(samples) == 30, 'Windows link report lacks the complete 30 samples')
    tick, timeouts, interrupted, replies = 0, 0, 0, []
    for sequence, row in enumerate(samples, 1):
        integer(row['sequence'], sequence, sequence)
        tick = integer(row['tick'], tick)
        integer(row['playerLoopFrames'], 1)
        window, rtt = row['windowSeconds'], row['roundTripMilliseconds']
        require(type(window) in (int, Decimal) and Decimal(window).is_finite() and window >= 1
                and type(rtt) in (int, Decimal) and Decimal(rtt).is_finite() and 0 <= rtt < 900,
                'Invalid Windows link sample timing')
        outcome = row['result']
        if outcome == 'Reply':
            replies.append(rtt)
        else:
            require(outcome in ('Timeout', 'Interrupted') and rtt == 0, 'Invalid Windows link sample outcome')
            timeouts += outcome == 'Timeout'
            interrupted += outcome == 'Interrupted'
    replies.sort()
    p95 = replies[(95 * len(replies) + 99) // 100 - 1] if replies else None
    failures = []
    if criteria is not None:
        if len(replies) < criteria['minimumReplies']:
            failures.append('minimumReplies')
        if p95 is None or p95 > criteria['maximumP95RoundTripMs']:
            failures.append('maximumP95RoundTripMs')
    return {'attempts': len(samples), 'replies': len(replies), 'timeouts': timeouts, 'interrupted': interrupted,
            'p95RoundTripMs': float(p95) if p95 is not None else None,
            'batchMode': metrics['batchMode'], 'graphicsDeviceActive': metrics['graphicsDeviceActive'],
            **({'criteriaFailures': failures} if failures else {})}


def read_udp_launcher_document(path, *, preview):
    value, raw = read_quest_document(path)
    if preview:
        require(integer(value['schemaVersion'], 1, 1) and value['status'] == 'venue-checked' and value['complete'] is True,
                'Provide the original successful Windows launcher preview')
    else:
        require(set(value) == {'version', 'controlInstance', 'topology', 'address', 'listenAddress', 'servers'}
                and integer(value['version'], 2, 4) and type(value['controlInstance']) is str and value['controlInstance'],
                'Provide a revision-guarded Windows launch plan')
    mode, rows = value['topology'], value['servers']
    require(mode in ('Independent', 'Linked'), 'Invalid Windows launcher topology')
    rooms = {QUEST_ROOMS} if mode == 'Linked' else {(room,) for room in QUEST_ROOMS}
    require(type(rows) is list and len(rows) == len(rooms), 'Incomplete Windows launcher room list')
    bindings, sessions = {}, set()
    for row in rows:
        require(type(row) is dict and type(row['sessionId']) is str and type(row['roomIds']) is list
                and all(type(room) is int for room in row['roomIds']) and ('missionId' not in row or type(row['missionId']) is str),
                'Invalid Windows launcher room group')
        if not preview:
            require(set(row) == {'roomIds', 'sessionId', 'missionId', 'sessionSequence', 'port'}, 'Invalid Windows launch plan entry')
        group = tuple(row['roomIds'])
        session = identity(row['sessionId'])
        require(group in rooms and group not in bindings and session not in sessions, 'Repeated launcher room or session')
        endpoint = row if preview else value
        listen = endpoint['listenAddress']
        bindings[group] = {'sessionId': session, 'missionId': identity(row['missionId']) if 'missionId' in row else None,
                           'sessionSequence': integer(row['sessionSequence'], 1) if 'sessionSequence' in row else None,
                           'port': integer(row['port'], 1024, 65535), 'address': quest_network_address(endpoint['address']),
                           'listenAddress': '0.0.0.0' if listen == '0.0.0.0' else quest_network_address(listen)}
        sessions.add(session)
    require(len({row['port'] for row in bindings.values()}) == len(bindings), 'Repeated launcher port')
    return hashlib.sha256(raw).hexdigest(), mode, bindings


def compare_udp_launch_documents(plan, preview):
    plan_sha, mode, planned = plan
    preview_sha, preview_mode, observed = preview
    groups = []
    fields = {'sessionId': 'session-mismatch', 'missionId': 'mission-mismatch', 'sessionSequence': 'session-sequence-mismatch',
              'port': 'port-mismatch', 'address': 'advertised-address-mismatch', 'listenAddress': 'listen-address-mismatch'}
    for rooms in sorted(planned.keys() | observed.keys()):
        wanted, got = planned.get(rooms), observed.get(rooms)
        if wanted is None:
            issues = ['unexpected-launch-group']
        elif got is None:
            issues = ['missing-launch-group']
        else:
            issues = [issue for field, issue in fields.items() if wanted[field] != got[field]]
        groups.append({'roomIds': list(rooms), 'issues': issues})
    return {'planSha256': plan_sha, 'previewSha256': preview_sha, 'mode': mode,
            'complete': mode == preview_mode and not any(group['issues'] for group in groups), 'groups': groups}


def read_udp_preflight_batch(path, mode, expected_rooms, *, expected_sessions=None):
    batch = read_json(content(path))
    require(integer(batch['version'], 1, 1) and batch.get('scope') in ('quest-udp-preflight-only', 'venue-udp-preflight-only')
            and batch.get('mode') == mode and batch.get('complete') is True,
            'Provide a complete UDP preflight batch for the original mode')
    launch = None
    if 'launchBinding' in batch:
        proof = batch['launchBinding']
        require(batch['scope'] == 'venue-udp-preflight-only' and type(proof) is dict
                and all(type(proof.get(name)) is str and proof[name] for name in ('plan', 'preview')),
                'Missing original Windows launch plan and preview paths')
        paths = {name: proof[name] for name in ('plan', 'preview')}
        plan = read_udp_launcher_document(path.parent / paths['plan'], preview=False)
        preview = read_udp_launcher_document(path.parent / paths['preview'], preview=True)
        checked = compare_udp_launch_documents(plan, preview)
        summary = batch.get('launcherPreview')
        require(proof == {**paths, **checked} and checked['complete'] and checked['mode'] == mode
                and type(summary) is dict and summary.get('sha256') == checked['previewSha256'] and summary.get('complete') is True,
                'Original Windows launch plan or preview differs from the UDP readiness proof')
        if expected_sessions is not None:
            require({rooms: row['sessionId'] for rooms, row in plan[2].items()} == expected_sessions,
                    'UDP launch plan sessions differ from the original sealed batch')
        launch = checked, plan[2]
    groups = batch['groups']
    require(type(groups) is list and 1 <= len(groups) <= len(expected_rooms), 'Invalid UDP endpoint groups')
    sources = {}
    for group in groups:
        room_ids = group['roomIds']
        require(type(room_ids) is list and all(type(room) is int for room in room_ids) and room_ids in expected_rooms
                and tuple(room_ids) not in sources and group.get('complete') is True,
                'Invalid or repeated UDP endpoint group')
        pairs = group['udpSourcePreflights']
        require(type(pairs) is list and 1 <= len(pairs) <= len(room_ids) * 5, 'Invalid all-source UDP preflight list')
        sources[tuple(room_ids)] = [(pair, path.parent) for pair in pairs]
    return sources, launch


def read_quest_capture_report(path, mode):
    report = read_quest_plan_file(path)
    fields = {'version', 'complete', 'topology', 'expectedSeats', 'capturedSeats', 'scope', 'seats'}
    require(set(report) in (fields, fields | {'deploymentSha256'})
            and type(report['complete']) is bool and report['topology'] == mode and report['scope'] == 'quest-logcat-only',
            'Quest capture report has an invalid format or the wrong topology')
    if 'deploymentSha256' in report:
        digest = report['deploymentSha256']
        require(type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'Invalid original Quest deployment digest in capture report')
    count = integer(report['expectedSeats'], 1, 25)
    captured = integer(report['capturedSeats'], 0, count)
    rows = report['seats']
    require(type(rows) is list and len(rows) == count, 'Quest capture report seat totals differ')
    seen = set()
    common = {'roomId', 'seat', 'sessionId', 'port', 'complete'}
    successful = common | {'log', 'logcatPid', 'bytes', 'sha256'}
    failed = common | {'reason'}
    for row in rows:
        require(type(row) is dict and common <= row.keys() and type(row.get('complete')) is bool, 'Invalid Quest capture seat outcome')
        seat = integer(row['roomId'], 1, 5), integer(row['seat'], 1, 5)
        require(seat not in seen, 'Quest capture report repeats a seat')
        seen.add(seat)
        identity(row['sessionId'])
        integer(row['port'], 1024, 65535)
        log_name = f'room-{seat[0]:02}-seat-{seat[1]:02}-logcat.txt'
        if row['complete']:
            require(set(row) == successful and row['log'] == log_name, 'Expected the original Quest capture log name and metadata')
            require(type(row['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['sha256']),
                    'Invalid original Quest capture digest')
            integer(row['logcatPid'], 1, 2**31 - 1)
            integer(row['bytes'], 1, MAX_FILE_BYTES)
        else:
            require(set(row) in (failed, failed | {'partial'}) and type(row['reason']) is str and bool(row['reason'])
                    and row.get('partial', log_name + '.partial') == log_name + '.partial', 'Invalid failed Quest capture row')
    require(sum(row['complete'] for row in rows) == captured and report['complete'] == (captured == count),
            'Quest capture report completeness differs from its seat totals')
    return report


def read_quest_capture_batches(spec, mode, expected, evidence_path):
    require(type(spec) is dict and set(spec) in ({'networkPlan', 'reports'}, {'deviceMap', 'reports'}),
            'Provide capture reports and either a Quest network plan or the original device map')
    observed = 'deviceMap' in spec
    if observed:
        sources = dict.fromkeys(read_quest_device_map(evidence_path(spec['deviceMap'])))
        endpoints = {}
    else:
        plan_mode, endpoints, plan_sources = read_quest_network_plan(evidence_path(spec['networkPlan']))
        require(plan_mode == mode, 'Quest network plan differs from the venue mode')
        sources = {seat: ipv4(address) for seat, address in plan_sources.items()}
    reports = spec['reports']
    require(type(reports) is list and 1 <= len(reports) <= 25, 'Provide 1 to 25 Quest capture reports')
    captures, used_seats, deployments = {}, set(), []
    incomplete_reports = failed_attempts = 0
    for name in reports:
        path = evidence_path(name)
        report = read_quest_capture_report(path, mode)
        if 'deploymentSha256' in report:
            deployments.append((report['deploymentSha256'], report['seats']))
        incomplete_reports += not report['complete']
        failed_attempts += report['expectedSeats'] - report['capturedSeats']
        for row in report['seats']:
            seat = row['roomId'], row['seat']
            require(seat in sources, 'Quest capture names an unplanned seat')
            session_id = row['sessionId']
            session = expected.get(session_id)
            require(session is not None and seat[0] in session['roomIds'], 'Quest capture does not match an original session and room')
            rooms = tuple(session['roomIds'])
            if observed:
                _, port = endpoints.setdefault(rooms, (None, row['port']))
                require(row['port'] == port, 'Quest capture reports disagree on the original game port')
            else:
                require(row['port'] == endpoints[rooms][1], 'Quest capture port differs from the network plan')
            if not row['complete']:
                continue
            require(seat not in used_seats, 'Quest capture repeats a completed seat')
            log = evidence_path(row['log'], path.parent)
            require(log.parent == path.parent and log.name == row['log'], 'Quest capture log must be next to its report')
            captures.setdefault(session_id, []).append((sources[seat], log, row['logcatPid'], seat, row['bytes'], row['sha256']))
            used_seats.add(seat)
    require(used_seats == sources.keys(), 'Quest capture reports must cover the planned Quest seats exactly')
    summary = {'questCaptureBatchesVerified': len(reports)}
    if observed:
        summary['questCaptureAddressSource'] = 'server-observed'
    if incomplete_reports:
        summary.update(questCaptureIncompleteReports=incomplete_reports, questCaptureFailedAttempts=failed_attempts)
    return captures, endpoints, summary, deployments


def quest_capture_log(address, path, pid, seat, size, digest):
    with path.open('rb') as source:
        raw = limited_read(source)
    require(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, 'Original Quest capture log size or digest differs')
    return address, raw.decode('utf-8-sig'), pid, seat


def quest_deployment_retry_proof(report, count):
    def hex_field(value, length):
        return type(value) is str and len(value) == length and re.fullmatch(r'[0-9a-f]+', value) is not None

    proof, previous = report.get('retry'), report.get('previousDeploymentSha256')
    if 'retry' not in report:
        require('previousDeploymentSha256' not in report, 'Quest deployment predecessor lacks original retry proof')
        return None, None
    require(type(proof) is dict and set(proof) == {'version', 'venueSha256', 'mapSha256', 'salt', 'devices'}
            and integer(proof['version'], 1, 1) and hex_field(proof['salt'], 32)
            and all(hex_field(proof[key], 64) for key in ('venueSha256', 'mapSha256'))
            and type(proof['devices']) is list and len(proof['devices']) == count
            and all(hex_field(device, 64) for device in proof['devices']) and len(set(proof['devices'])) == count,
            'Invalid Quest deployment retry proof')
    require('previousDeploymentSha256' not in report or hex_field(previous, 64), 'Invalid Quest deployment predecessor digest')
    return proof, previous


def quest_deployment_leaves(attempts):
    has_successor = set()
    for digest, attempt in attempts.items():
        parent_digest = attempt['previous']
        if parent_digest is None:
            continue
        require(parent_digest != digest and parent_digest not in has_successor, 'Conflicting Quest deployment retry branches')
        has_successor.add(parent_digest)
        if parent_digest in attempts:
            parent = attempts[parent_digest]
            require(not parent['complete'] and parent['proof'] == attempt['proof'] and parent['seats'] == attempt['seats']
                    and attempt['launched'][:len(parent['launched'])] == parent['launched'],
                    'Quest deployment retry changes its original proof, seats or completed prefix')

    leaves = [attempt for digest, attempt in attempts.items() if digest not in has_successor]
    salts = [attempt['proof']['salt'] for attempt in leaves if attempt['proof'] is not None]
    require(len(salts) == len(set(salts)), 'Quest deployment retry history is disconnected; provide the linked reports or the latest report alone')
    linked = len(attempts.keys() & has_successor)
    visited = set()
    for leaf in leaves:
        digest = leaf['previous']
        while digest in attempts:
            require(digest not in visited, 'Cyclic Quest deployment retry history')
            visited.add(digest)
            digest = attempts[digest]['previous']
    require(len(visited) == linked, 'Cyclic Quest deployment retry history')
    return leaves, linked


def read_quest_deployments(spec, mode, evidence_path, release=None, *, capture_reports=()):
    expected = {'releaseReport', 'reports'} if release is None else {'reports'}
    require(type(spec) is dict and set(spec) == expected,
            'Provide the original Quest deployment reports and exactly one release report for the selected mode')
    if release is None:
        release = read_quest_json(evidence_path(spec['releaseReport']))
    quest = release.get('quest')
    require(release.get('verified') is True and release.get('scope') == 'offline-package-consistency'
            and type(quest) is dict and quest.get('applicationId') == 'com.vrcommand.quest'
            and quest.get('architecture') == 'arm64-v8a' and quest.get('signatureV2') is True,
            'Quest release report was not verified for the original application')
    version = integer(quest.get('versionCode'), 1, 2**31 - 1)
    digest = quest.get('sha256')
    require(type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'Invalid Quest release APK digest')
    reports = spec['reports']
    require(type(reports) is list and 1 <= len(reports) <= 25, 'Provide 1 to 25 Quest deployment reports')
    attempts = {}
    for name in reports:
        report, raw = read_quest_document(evidence_path(name))
        report_hash = hashlib.sha256(raw).hexdigest()
        require(report_hash not in attempts, 'Quest deployment repeats a successful seat or the same original report')
        require(report.get('phase') == 'deployment' and report.get('managementVerified') is True
                and report.get('topology') == mode and integer(report.get('apkVerificationVersion'), 1, 1),
                'Quest deployment report lacks verified deployment or uses another topology')
        require(report.get('expectedApkSha256') == digest and integer(report.get('expectedVersionCode'), 1) == version,
                'Quest deployment report differs from the original release APK')
        devices = report.get('devices')
        require(type(devices) is list and 1 <= len(devices) <= 25
                and all(type(row) is dict and type(row.get('status')) is str for row in devices),
                'Invalid Quest deployment device list')
        launched = [row for row in devices if row.get('status') == 'launch-requested']
        require(report.get('complete') is (len(launched) == len(devices))
                and devices[:len(launched)] == launched, 'Quest deployment report lacks a consistent successful prefix')
        proof, previous = quest_deployment_retry_proof(report, len(devices))
        seats, confirmed = {}, {}
        for row in devices:
            room, seat = integer(row.get('roomId'), 1, 5), integer(row.get('seat'), 1, 5)
            require((room, seat) not in seats, 'Quest deployment report repeats a device seat')
            seats[room, seat] = None
            if row['status'] != 'launch-requested':
                continue
            require(row.get('apkVerified') is True and row.get('filesVerified') is True
                    and integer(row.get('versionCode'), 1) == version,
                    'Quest deployment lacks verified APK and configuration')
            confirmed[room, seat] = (identity(row['sessionId']), identity(row['playerId']), identity(row['admissionId']),
                                     integer(row.get('port'), 1024, 65535))
        attempts[report_hash] = dict(proof=proof, previous=previous, complete=report['complete'], seats=tuple(seats),
                                     launched=launched, confirmed=confirmed)

    for digest, seats in capture_reports:
        deployment = attempts.get(digest)
        require(deployment is not None and deployment['complete'] and deployment['proof'] is not None,
                'Provide the exact completed Quest deployment report referenced by the capture')
        for row in seats:
            original = deployment['confirmed'].get((row['roomId'], row['seat']))
            require(original is not None and original[0] == row['sessionId'] and original[3] == row['port'],
                    'Quest capture seat does not match its referenced deployment')
    leaves, linked = quest_deployment_leaves(attempts)
    deployed = {}
    for attempt in leaves:
        confirmed = attempt['confirmed']
        require(confirmed, 'Quest deployment report lacks a consistent successful prefix')
        require(deployed.keys().isdisjoint(confirmed), 'Quest deployment repeats a successful seat')
        deployed.update(confirmed)
    summary = {'versionCode': version, 'apkSha256': digest, 'reportsVerified': len(reports), 'seatsVerified': len(deployed)}
    if linked:
        summary['retryReportsLinked'] = linked
    return deployed, summary


def read_venue_release(path):
    with path.open('rb') as file:
        raw = file.read(8193)
    require(0 < len(raw) <= 8192, 'Venue release report exceeds its file limit')
    release = read_json(raw.decode('utf-8-sig'))
    require(type(release) is dict and release.get('verified') is True and release.get('scope') == 'offline-package-consistency',
            'Provide a verified offline venue release report')
    return release, hashlib.sha256(raw).hexdigest()


def read_venue_debrief_receipts(path, request_id, session_count):
    with path.open('rb') as source:
        raw = source.read(16385)
    require(len(raw) <= 16384, 'Management debrief receipt export is too large')
    value = read_json(raw.decode('utf-8-sig'))
    require(type(value) is dict and set(value) == {'version', 'requestId', 'sessions'}
            and integer(value['version'], 1, 1) == 1 and identity(value['requestId']) == request_id,
            'Management debrief receipts identify another End batch or invalid export')
    require(type(value['sessions']) is list and len(value['sessions']) == session_count,
            'Management debrief receipts must cover every original venue session')
    sessions = {}
    for row in value['sessions']:
        require(type(row) is dict and set(row) == {'sessionId', 'streamId', 'throughSequence', 'finalStreamSequence',
                                                  'worldSequence', 'players'}, 'Invalid management debrief receipt session')
        session_id = identity(row['sessionId'])
        require(session_id not in sessions, 'Management debrief receipts repeat a venue session')
        sessions[session_id] = row
    return sessions, hashlib.sha256(raw).hexdigest()


def verify_venue_debrief_session(receipts, session, stream, report):
    require(receipts is not None and identity(receipts['streamId']) == stream
            and integer(receipts['throughSequence'], 1) == session['sequence']
            and integer(receipts['finalStreamSequence']) == report['combatSequence']
            and integer(receipts['worldSequence'], 1) == report['worldSequence'],
            'Management debrief receipt boundaries differ from the original sealed session')
    roster = {(player['id'], player['admissionId'], player['roomId']) for player in session['players']}
    players = receipts['players']
    require(type(players) is list and len(players) == len(roster) == report['serverAcknowledgements'],
            'Management debrief receipts must cover every acknowledged original player')
    confirmed = set()
    for row in players:
        require(type(row) is dict and set(row) == {'playerId', 'admissionId', 'roomId', 'acknowledged'}
                and row['acknowledged'] is True, 'Management debrief receipt is missing or unconfirmed')
        confirmed.add((identity(row['playerId']), identity(row['admissionId']), integer(row['roomId'], 1, 5)))
    require(confirmed == roster, 'Management debrief receipts differ from the original admissions')


def read_venue_control_batches(references, expected, closure, recorded_at, evidence_path):
    require(type(references) is list and 1 <= len(references) <= 32,
            'Provide 1 to 32 original venue phase reports')
    batches = {}
    by_session = {sid: {} for sid in expected}
    for reference in references:
        require(type(reference) is dict and set(reference) == {'action', 'phaseReport'}
                and reference['action'] in ('SetEnvironment', 'SetEnemies'), 'Invalid venue control batch reference')
        action = reference['action']
        phase = read_json(content(evidence_path(reference['phaseReport'])))
        require(type(phase) is dict, 'Invalid venue phase report')
        batch = phase.get('latestEnvironment' if action == 'SetEnvironment' else 'latestEnemies')
        require(type(batch) is dict, 'Venue phase report lacks the selected original control batch')
        request = identity(batch['requestId'])
        when = datetime.fromisoformat(batch['recordedAtUtc'])
        require(request != closure['requestId'] and request not in batches and when.utcoffset() is not None
                and when <= recorded_at, 'Venue control batch identity or time differs from the original closure')
        if action == 'SetEnvironment':
            policy = {name: batch[name] for name in ('weather', 'timeOfDay', 'lightning')}
            require(policy['weather'] in ('Clear', 'Rain', 'Fog', 'Storm') and policy['timeOfDay'] in ('Day', 'Night')
                    and type(policy['lightning']) is bool, 'Invalid venue environment batch policy')
        else:
            policy = {name: batch[name] for name in ('behavior', 'autoAttack')}
            require(policy['behavior'] in ('Hold', 'Patrol', 'Advance') and type(policy['autoAttack']) is bool,
                    'Invalid venue enemy batch policy')
        targets = batch['sessions']
        require(type(targets) is list and len(targets) == len(expected), 'Venue control batch must cover every original session')
        seen = set()
        for target in targets:
            sid = identity(target['sessionId'])
            require(sid in expected and sid not in seen and target['roomIds'] == expected[sid]['roomIds']
                    and all(type(room) is int for room in target['roomIds'])
                    and target['state'] in ('Current', 'Superseded', 'Ended'), 'Venue control target differs from the original room or session')
            sequence = integer(target['appliedAtSequence'], 1, expected[sid]['appliedAtSequence'] - 1)
            require(sequence not in by_session[sid], 'Venue control batches reuse an applied sequence')
            seen.add(sid)
            by_session[sid][sequence] = {'requestId': request, 'action': action, 'appliedAtSequence': sequence, **policy}
        batches[request] = {'requestId': request, 'action': action, 'sessionsVerified': len(expected), **policy}
    return list(batches.values()), {sid: targets.values() for sid, targets in by_session.items()}


def read_terminal_venue_launcher(path, mode, expected):
    with path.open('rb') as stream:
        raw = limited_read(stream)
    report = read_json(raw.decode('utf-8-sig'))
    require(type(report) is dict and integer(report['schemaVersion'], 1, 1)
            and report['status'] == 'venue-sealed-stopped' and report['complete'] is report['readyPublished'] is True
            and report['topology'] == mode and report['sourceAttachment'] == report['endpointPublication'] == 'confirmed',
            'Provide the original terminal Windows venue launch report')
    identity(report['instanceId'])
    launch_id = identity(report['venueLaunchId'])
    rows = report['servers']
    require(type(rows) is list and len(rows) == len(expected), 'Venue launcher report must cover every original venue session')
    results, child_pids = {}, set()
    for row in rows:
        result = row['result']
        require_terminal_launcher(result)
        sid = identity(result['sessionId'])
        original = expected.get(sid)
        rooms = row['roomIds']
        require(original is not None and sid not in results and type(rooms) is list
                and all(type(room) is int for room in rooms) and rooms == original['roomIds']
                and result['streamId'] == original['replay']['streamId'],
                'Venue launcher result differs from the original closure room or stream')
        pid = integer(result['childPid'], 1)
        require(pid not in child_pids, 'Venue launcher repeats an original child process')
        child_pids.add(pid)
        results[sid] = result
    return {'launchId': launch_id, 'sha256': hashlib.sha256(raw).hexdigest(), 'sessions': len(results)}, results


def venue_closure_sessions(mode, rows):
    rooms = list(QUEST_ROOMS)
    groups = [rooms] if mode == 'Linked' else [[room] for room in rooms]
    require(type(rows) is list and len(rows) == len(groups),
            'Venue must contain the original five independent sessions or one linked session')
    expected = {identity(row['sessionId']): row for row in rows}
    require(len(expected) == len(rows) and all(type(row['roomIds']) is list and row['roomIds']
            and all(integer(room, 1, 5) for room in row['roomIds']) for row in rows)
            and sorted(row['roomIds'] for row in rows) == groups, 'Closure does not cover exactly the five original rooms')
    return groups, expected


def require_venue_launcher_source(session, launch_id, session_id, original):
    source = session['combatStream']
    require(session['id'] == session_id and type(source) is dict and source.get('venueLaunchId') == launch_id,
            'Original management source belongs to a different venue launch or session')
    integer(source['expectedSequence'], 1, original['appliedAtSequence'] - 1)


def verify_venue(manifest_path):
    report, _ = verify_venue_batch(manifest_path)
    return report


def verify_venue_batch(manifest_path, *, inspect_windows=False):
    manifest_path = manifest_path.resolve(strict=True)
    with manifest_path.open('rb') as stream:
        raw_manifest = limited_read(stream)
    manifest = read_json(raw_manifest.decode('utf-8-sig'))
    integer(manifest['version'], 1, 1)
    link_criteria = None
    if 'windowsLinkCriteria' in manifest:
        link_criteria = manifest['windowsLinkCriteria']
        require(type(link_criteria) is dict and set(link_criteria) == {'minimumReplies', 'maximumP95RoundTripMs'},
                'Windows link criteria require minimumReplies and maximumP95RoundTripMs')
        integer(link_criteria['minimumReplies'], 1, 30)
        integer(link_criteria['maximumP95RoundTripMs'], 0, 900)
    players_per_room = integer(manifest.get('expectedPlayersPerRoom', 5), 1, 5)
    topology, mode = manifest['topology'], manifest['mode']
    require(topology in ('same-host', 'direct-lan') and mode in ('Independent', 'Linked'), 'Invalid venue topology or mode')
    addresses = manifest['serverIps']
    require(type(addresses) is list and 1 <= len(addresses) <= 128, 'Provide the server IPv4 inventory as a list')
    server_ips = {ipv4(value) for value in addresses}
    require(len(server_ips) == len(addresses), 'Duplicate server address')
    seen_paths = {manifest_path}

    def evidence_path(value, base=manifest_path.parent):
        require(type(value) is str and bool(value), 'Evidence path is missing')
        path = (base / value).resolve(strict=True)
        require(path not in seen_paths, 'Evidence paths must be distinct across the venue')
        seen_paths.add(path)
        return path

    release, release_hash = (read_venue_release(evidence_path(manifest['venueReleaseReport']))
                             if 'venueReleaseReport' in manifest else (None, None))
    windows_release = release.get('windows') if release is not None else None
    windows_hash = windows_release.get('playerManifestSha256') if type(windows_release) is dict else None

    packed = 'venueBundle' in manifest
    require(packed != ('closure' in manifest), 'Provide either venueBundle or the original closure and per-session ZIPs')
    if packed:
        closure, archives = venue_bundle(evidence_path(manifest['venueBundle']), mode)
    else:
        closure = read_json(content(evidence_path(manifest['closure'])))['batch']
    closure_id = identity(closure['requestId'])
    recorded_at = datetime.fromisoformat(closure['recordedAtUtc'])
    require(recorded_at.utcoffset() is not None, 'Closure time must specify a time zone')
    all_rooms = list(range(1, 6))
    entries = manifest['sessions']
    rows = closure['sessions']
    expected_rooms, expected = venue_closure_sessions(mode, rows)
    require(type(entries) is list and len(entries) == len(rows),
            'Venue must contain the original five independent sessions or one linked session')
    debrief_receipts, debrief_hash = (read_venue_debrief_receipts(evidence_path(manifest['venueDebriefReceipts']),
                                                               closure['requestId'], len(rows))
                                    if 'venueDebriefReceipts' in manifest and not inspect_windows else (None, None))
    journals = any('worldJournal' in entry for entry in entries)
    require(not journals or all('worldJournal' in entry for entry in entries), 'Provide a world journal for every session in this batch')
    combat_journals = any('combatJournal' in entry for entry in entries)
    require(not combat_journals or all('combatJournal' in entry for entry in entries),
            'Provide a combat journal for every session in this batch')
    require_tracked = manifest.get('requireTrackedRoster', False)
    require(type(require_tracked) is bool, 'requireTrackedRoster must be a boolean')
    require(not require_tracked or 'minimumConcurrentMilliseconds' in manifest,
            'requireTrackedRoster requires minimumConcurrentMilliseconds')
    require_fire = manifest.get('requireConcurrentFire', False)
    require(type(require_fire) is bool, 'requireConcurrentFire must be a boolean')
    require(not require_fire or ('minimumConcurrentMilliseconds' in manifest and combat_journals),
            'requireConcurrentFire requires minimumConcurrentMilliseconds and the original combat journals for the full batch')
    concurrency = None
    if 'minimumConcurrentMilliseconds' in manifest:
        require(journals, 'Concurrent roster verification requires the original world journals for the full batch')
        concurrency = VenueRosterOverlap(integer(manifest['minimumConcurrentMilliseconds'], 1000, 900000),
                                         require_tracked=require_tracked, require_fire=require_fire)
    require_distinct_remote_roster = manifest.get('requireDistinctRemoteRoster', False)
    require(type(require_distinct_remote_roster) is bool, 'requireDistinctRemoteRoster must be a boolean')
    require(not require_distinct_remote_roster or (topology == 'direct-lan' and concurrency is not None),
            'requireDistinctRemoteRoster requires direct-lan and minimumConcurrentMilliseconds')
    verify_player_sources = manifest.get('verifyPlayerSources', False)
    require(type(verify_player_sources) is bool and (not verify_player_sources or journals),
            'Player source verification requires a boolean option and the original world journals for the full batch')
    verify_player_sources = verify_player_sources or require_tracked
    verify_reconnect_history = manifest.get('verifyReconnectHistory', False)
    require(type(verify_reconnect_history) is bool, 'verifyReconnectHistory must be a boolean')
    verify_reconnect_history = verify_reconnect_history or require_distinct_remote_roster
    reconnect_window = None
    if 'reconnectWindow' in manifest:
        require(verify_reconnect_history and journals, 'reconnectWindow requires verified reconnect history and the original world journals')
        reconnect_window = VenueReconnectWindow(manifest['reconnectWindow'])
    verify_tracking_begin = manifest.get('verifyTrackingBegin', False)
    verify_participation_begin = manifest.get('verifyParticipationBegin', False)
    require(type(verify_tracking_begin) is bool and type(verify_participation_begin) is bool
            and (not (verify_tracking_begin or verify_participation_begin) or journals),
            'Guarded Begin verification requires a boolean option and the original world journals for the full batch')
    require(not (verify_tracking_begin and verify_participation_begin), 'Choose one guarded Begin verification policy')
    begin_kind = 'trackingBegin' if verify_tracking_begin else 'participationBegin' if verify_participation_begin else None
    check_alignments = any('roomAlignments' in entry for entry in entries)
    require(not check_alignments or journals, 'MR alignment evidence requires the original world journals for the full batch')
    preflights = any('udpPreflight' in entry for entry in entries)
    source_lists = any('udpSourcePreflights' in entry for entry in entries)
    single_batch, multiple_batches = 'udpPreflightBatch' in manifest, 'udpPreflightBatches' in manifest
    require(not (single_batch and multiple_batches), 'Use either one Quest UDP batch field or the batch list')
    batch_supplied = single_batch or multiple_batches
    source_preflights = source_lists or batch_supplied
    require(not (preflights and source_preflights), 'Use only one UDP preflight mode for the full batch')
    require(not preflights or all('udpPreflight' in entry for entry in entries), 'Provide UDP preflight reports for every session in this batch')
    require(not source_lists or batch_supplied or all('udpSourcePreflights' in entry for entry in entries),
            'Provide all-source UDP preflight reports for every session in this batch')

    venue_launcher, venue_results = None, {}
    if 'venueLauncherReport' in manifest:
        require(all('launcherReport' not in entry and 'sessionId' in entry for entry in entries),
                'Use sessionId instead of a per-session launcher report with venueLauncherReport')
        venue_launcher, venue_results = read_terminal_venue_launcher(evidence_path(manifest['venueLauncherReport']), mode, expected)
    batch_pairs, udp_launch_bindings = {}, {}
    if batch_supplied and not inspect_windows:
        batch_names = [manifest['udpPreflightBatch']] if single_batch else manifest['udpPreflightBatches']
        require(type(batch_names) is list and 1 <= len(batch_names) <= 25, 'Provide 1 to 25 Quest UDP batch reports')
        for name in batch_names:
            batch, launch = read_udp_preflight_batch(evidence_path(name), mode, expected_rooms,
                                                     expected_sessions={tuple(row['roomIds']): sid for sid, row in expected.items()})
            if launch is not None:
                for group, planned in launch[1].items():
                    require(udp_launch_bindings.setdefault(group, planned) == planned, 'UDP launch plans disagree on the original room binding')
            for room_ids, sources in batch.items():
                combined = batch_pairs.setdefault(room_ids, [])
                combined.extend(sources)
                require(len(combined) <= len(room_ids) * 5, 'Too many UDP preflight pairs for one original endpoint')
        require(source_lists or set(batch_pairs) == {tuple(rooms) for rooms in expected_rooms},
                'The Quest UDP preflight batches must cover every original endpoint')

    def preflight_pair(pair, base=manifest_path.parent):
        require(type(pair) is dict and set(pair) == {'listener', 'probe'}, 'Provide the original UDP listener and probe reports')
        return evidence_path(pair['listener'], base), evidence_path(pair['probe'], base)

    control_summary, controls = [], {}
    if 'venueControlBatches' in manifest and not inspect_windows:
        require(journals, 'Venue control batch verification requires the original world journals for the full batch')
        control_summary, controls = read_venue_control_batches(manifest['venueControlBatches'], expected, closure, recorded_at, evidence_path)

    inbox_supplied = 'windowsEvidenceDirectory' in manifest
    explicit_windows = 'windowsPlayers' in manifest
    require(not (inbox_supplied and explicit_windows), 'Use either windowsEvidenceDirectory or windowsPlayers')
    require(inbox_supplied or not (inspect_windows or 'windowsSeatMap' in manifest), 'Windows inbox inspection and seat maps require windowsEvidenceDirectory')
    require('windowsStationAddresses' not in manifest or (inbox_supplied and 'windowsSeatMap' in manifest),
            'Windows station addresses require the Windows evidence inbox and seat map')
    windows_supplied = inbox_supplied or explicit_windows
    windows_by_session = venue_windows_logs(manifest['windowsPlayers'], expected, evidence_path, players_per_room) if explicit_windows else {}

    capture_supplied = 'questCaptures' in manifest
    captures, capture_endpoints, capture_summary, capture_deployments = {}, {}, {}, []
    if capture_supplied and not inspect_windows:
        require(topology == 'direct-lan', 'Quest capture batches require direct LAN evidence')
        captures, capture_endpoints, capture_summary, capture_deployments = read_quest_capture_batches(manifest['questCaptures'], mode, expected, evidence_path)
    observed_quest_addresses = set() if capture_summary.get('questCaptureAddressSource') == 'server-observed' else None
    quest_deployments, deployment_summary = None, None
    require(not capture_deployments or 'questDeployments' in manifest, 'Provide the original Quest deployment reports referenced by the capture')
    if 'questDeployments' in manifest and not inspect_windows:
        require(topology == 'direct-lan', 'Quest deployment evidence requires direct LAN evidence')
        quest_deployments, deployment_summary = read_quest_deployments(manifest['questDeployments'], mode, evidence_path, release,
                                                                      capture_reports=capture_deployments)
        if capture_deployments:
            capture_summary['questCaptureDeploymentReportsMatched'] = len(capture_deployments)

    def load_session(entry):
        if venue_launcher is None:
            launcher = read_json(content(evidence_path(entry['launcherReport'])))
            launch_id = identity(launcher['sessionId']) if packed else None
        else:
            launch_id = identity(entry['sessionId'])
            launcher = venue_results.get(launch_id)
            require(launcher is not None and launch_id in expected, 'Venue sessionId differs from the original launcher report or repeats')
        if packed:
            require('evidenceZip' not in entry, 'Omit per-session evidenceZip when using venueBundle')
            original = expected.get(launch_id)
            require(original is not None, 'Launcher report belongs to a different or repeated venue session')
            name = 'linked.zip' if mode == 'Linked' else f"room-{original['roomIds'][0]:02}.zip"
            session, statistics, endpoint = management_zip_records(archives[name])
            require(session['id'] == launch_id, 'Venue ZIP member differs from its original launcher session')
        else:
            session, statistics, endpoint = management_zip(evidence_path(entry['evidenceZip']))
        if venue_launcher is not None:
            require_venue_launcher_source(session, venue_launcher['launchId'], launch_id, expected[launch_id])
        return entry, launcher, session, statistics, endpoint, content(evidence_path(entry['serverLog']))

    inputs = (load_session(entry) for entry in entries)
    station_summary = {}
    if inbox_supplied:
        for entry in entries:
            require(all(type(player) is dict and 'logcatPid' in player for player in entry.get('players', [])),
                    'Use only Quest evidence in per-session players when using a Windows inbox')
        seat_map = read_windows_seat_map(evidence_path(manifest['windowsSeatMap'])) if 'windowsSeatMap' in manifest else None
        station_addresses, address_hash = (read_windows_station_addresses(evidence_path(manifest['windowsStationAddresses']), seat_map)
                                           if 'windowsStationAddresses' in manifest else (None, None))
        require(seat_map is not None or not (capture_supplied or any(entry.get('players') for entry in entries)),
                'Provide the Windows seat map when the batch contains Quest evidence')
        name = manifest['windowsEvidenceDirectory']
        require(type(name) is str and bool(name), 'Windows evidence directory is missing')
        directory = (manifest_path.parent / name).resolve(strict=True)
        inputs = list(inputs)
        windows_by_session, inbox = windows_inbox(directory, inputs, expected, players_per_room, windows_hash,
                                                 seat_map, evidence_path, link_criteria, station_addresses=station_addresses)
        if station_addresses is not None:
            station_summary['windowsStationAddresses'] = {'sha256': address_hash, 'expectedSeats': len(station_addresses),
                                                          'verifiedSeats': inbox['receivedWindowsSeats']}
        if inspect_windows:
            return {'version': 1, 'scope': 'windows-inbox', 'mode': mode, 'closureRequestId': closure_id, **inbox, **station_summary}, None
        require(inbox['complete'], 'Windows inbox is incomplete or contains conflicting files; use --inspect-windows-inbox')

    rooms, summaries = {}, []
    quest_players, windows_players, windows_link_reports = 0, 0, 0
    stream_ids, bindings, player_ids, admission_ids, end_times, exchanges = set(), set(), set(), set(), set(), set()
    start_times = set()
    begin_request = None
    for entry, launcher, session, statistics, endpoint, server_log in inputs:
        alignments = None
        if check_alignments:
            experience = verify_experience(session, launcher['finalWorld']['header'])
            if experience == 'MR':
                files = entry.get('roomAlignments')
                require(type(files) is dict and set(files) == {str(room) for room in session['roomIds']},
                        'Provide a locked alignment file for every original MR room in this batch')
                alignments = {int(room): evidence_path(path) for room, path in files.items()}
            else:
                require('roomAlignments' not in entry, 'Room alignment evidence is only for MR sessions')
        row = expected.pop(identity(session['id']), None)
        require(row is not None and session['mode'] == mode and session['roomIds'] == row['roomIds'],
                'Session evidence differs from the original closure')
        require(row['combat'] == row['world'] == 'Sealed'
                and row['missionName'] == session['mission']['definition']['name']
                and row['replay']['streamId'] == launcher['streamId']
                and integer(row['replay']['throughSequence'], 1) == integer(launcher['finalWorld']['acceptedSequence'], 1)
                and integer(row['appliedAtSequence'], 1) < integer(session['sequence'], 1),
                'Closure and original sealed session boundaries differ')
        start_times.add(datetime.fromisoformat(session['startedAtUtc']))
        end_times.add(datetime.fromisoformat(session['endedAtUtc']))
        stream = identity(launcher['streamId'])
        guarded_begin = None
        if begin_kind is not None:
            verify_experience(session, launcher['finalWorld']['header'])
            require(not ('trackingBegin' in row and 'participationBegin' in row), 'Closure has conflicting guarded Begin witnesses')
            begin = row.get(begin_kind)
            require(type(begin) is dict and set(begin) == {'requestId', 'appliedAtSequence', 'frame'},
                    'Closure is missing an original guarded Begin witness')
            request = identity(begin['requestId'])
            require(request != closure['requestId'] and begin_request in (None, request),
                    'Venue sessions do not share one original guarded Begin request')
            begin_request = request
            integer(begin['appliedAtSequence'], 2, row['appliedAtSequence'] - 1)
            frame = begin['frame']
            require(type(frame) is dict and set(frame) == {'streamId', 'worldSequence', 'elapsedMilliseconds'}
                    and identity(frame['streamId']) == stream, 'Guarded Begin witness uses another world source')
            integer(frame['worldSequence'], 1, launcher['finalWorld']['acceptedSequence'] - 1)
            integer(frame['elapsedMilliseconds'])
            guarded_begin = begin_kind, begin
        binding = (ipv4(endpoint['address']), integer(endpoint['port'], 1024, 65535))
        launch_binding = udp_launch_bindings.get(tuple(row['roomIds']))
        if launch_binding is not None:
            source = session['combatStream']
            require(type(source) is dict, 'UDP launch plan requires an original sealed combat source')
            attached_sequence = source.get('expectedSequence')
            require(launch_binding['address'] == launch_binding['listenAddress'] == str(binding[0])
                    and launch_binding['port'] == binding[1] and launch_binding['missionId'] == session['mission']['id']
                    and (attached_sequence is None or launch_binding['sessionSequence'] == integer(attached_sequence, 1))
                    and launch_binding['sessionSequence'] < row['appliedAtSequence'],
                    'UDP launch plan does not match the sealed mission and game binding')
        require(stream not in stream_ids and binding not in bindings, 'Venue reused a world stream or server UDP binding')
        stream_ids.add(stream)
        bindings.add(binding)
        captured = captures.get(session['id'], [])
        planned_binding = capture_endpoints.get(tuple(row['roomIds']))
        if planned_binding is not None:
            planned_address, planned_port = planned_binding
            require(binding[1] == planned_port and (planned_address is None or str(binding[0]) == planned_address),
                    'Quest network plan endpoint differs from the original game binding' if planned_address is not None
                    else 'Quest capture port differs from the original game binding')
        logs = list(windows_by_session.get(session['id'], []))
        players = entry.get('players', []) if capture_supplied or windows_supplied else entry['players']
        require(type(players) is list and all(type(player) is dict for player in players), 'Invalid player log list')
        if windows_supplied:
            require(all('logcatPid' in player for player in players), 'Use windowsPlayers or per-session Windows logs, not both')
        size = len(players) + len(captured) + len(logs)
        require(size == len(row['roomIds']) * players_per_room,
                'Session player log count differs from the expected seats per room')
        quest_logs = []
        for player in players:
            if 'logcatPid' in player:
                require(not capture_supplied, 'Use the Quest capture batches or manual Quest logs, not both')
                require(not {'linkMetrics', 'launcherReport', 'evidenceZip'} & player.keys(),
                        'Windows launcher evidence requires a Windows player log')
                quest_logs.append((ipv4(player['address']), evidence_path(player['log']), integer(player['logcatPid'], 1, 2**31 - 1)))
            else:
                logs.append(windows_log_paths(player, evidence_path))
        windows_players += len(logs)
        if release is not None and logs:
            require(type(windows_hash) is str and re.fullmatch(r'[0-9a-f]{64}', windows_hash),
                    'Venue release report lacks a valid Windows player manifest digest')
            require(all(launch is not None or bundle is not None for _, _, launch, _, bundle in logs),
                    'Release evidence requires the launcher report for every Windows seat')
        if release is not None and (quest_logs or captured):
            require(deployment_summary is not None, 'Release evidence requires original deployments for every Quest seat')
        link_rows = []
        release_seats = []
        owners = {player['id']: player for player in session['players']}

        def windows_logs():
            for address, path, launch_path, metrics_path, bundle in logs:
                raw_log, raw_launch, raw_metrics = read_windows_evidence(path, launch_path, bundle)
                log = raw_log.decode('utf-8-sig')
                if raw_launch is None:
                    yield address, log
                    continue
                require(raw_metrics is None or metrics_path is None, 'Provide Windows link evidence either in the ZIP or as an original file')
                if metrics_path is not None:
                    with metrics_path.open('rb') as source:
                        raw_metrics = source.read(MAX_WINDOWS_LINK_BYTES + 1)
                require(release is not None or raw_metrics is not None, 'A Windows launcher report requires venue release or link evidence')
                log_hash = hashlib.sha256(raw_log).hexdigest()
                launch = read_json(raw_launch)
                require(bundle is None or raw_metrics is not None or 'linkMetrics' not in launch,
                        'Player ZIP lacks its recorded Windows link report')
                connection, result = client_result(log)
                owner = owners.get(result['playerId'])
                require(owner is not None, 'Windows launcher evidence belongs to a different session player')
                seat = {'roomId': owner['roomId'], 'seat': integer(owner['seat'], 0, 4) + 1}
                if raw_metrics is not None:
                    link_rows.append({**seat, **verify_windows_link(log_hash, connection, launch, raw_metrics, link_criteria)})
                if release is not None:
                    verify_windows_release(log_hash, launch, windows_hash, has_link_metrics=raw_metrics is not None)
                    release_seats.append(seat)
                yield address, log
        preflight_paths = preflight_pair(entry['udpPreflight']) if preflights else None
        source_paths = None
        if source_preflights:
            supplemental = entry.get('udpSourcePreflights', [])
            require(type(supplemental) is list and len(supplemental) <= size
                    and ('udpSourcePreflights' not in entry or supplemental), 'Invalid supplemental UDP preflight list')
            pairs = batch_pairs.get(tuple(row['roomIds']), []) + [(pair, manifest_path.parent) for pair in supplemental]
            require(1 <= len(pairs) <= size, 'Provide all-source UDP preflight reports for every original endpoint')
            source_paths = [preflight_pair(pair, base) for pair, base in pairs]
        report, sources = verify_session(topology, server_ips, launcher, session, statistics, endpoint,
                                         server_log, size, windows_logs(),
                                         require_remote=False,
                                         quest_player_logs=((address, content(path), pid) for address, path, pid in quest_logs),
                                         world_journal=evidence_path(entry['worldJournal']) if journals else None,
                                         combat_journal=evidence_path(entry['combatJournal']) if combat_journals else None,
                                         applied_end=row['appliedAtSequence'], room_alignments=alignments, udp_preflight=preflight_paths,
                                         udp_source_preflights=source_paths, verify_player_sources=verify_player_sources,
                                         quest_capture_logs=(quest_capture_log(*evidence) for evidence in captured),
                                         guarded_begin=guarded_begin, concurrency=concurrency,
                                         verify_reconnect_history=verify_reconnect_history, reconnect_window=reconnect_window,
                                         quest_deployments=quest_deployments,
                                         require_distinct_remote_roster=require_distinct_remote_roster,
                                         control_batches=controls.get(session['id'], ()), observed_quest_addresses=observed_quest_addresses)
        require(set(sources) == set(row['roomIds']) and all(len(peers) == players_per_room for peers in sources.values()),
                'Verified player count differs from the expected seats in an original room')
        if debrief_receipts is not None:
            verify_venue_debrief_session(debrief_receipts.pop(session['id'], None), session, stream, report)
        verified_pairs = ([report['udpPreflight']] if preflights else report['udpSourcePreflight']['pairs'] if source_preflights else [])
        for pair in verified_pairs:
            exchange = pair['exchangeSha256']
            require(exchange not in exchanges, 'Venue reused a UDP preflight exchange')
            exchanges.add(exchange)
        quest_players += len(quest_logs) + len(captured)
        windows_link_reports += len(link_rows)
        seats = {(player['roomId'], integer(player['seat'], 0, 4)) for player in session['players']}
        require(len(seats) == size, 'Final roster repeats a room seat')
        for player in session['players']:
            player_id, admission = player['id'], player['admissionId']
            require(player_id not in player_ids and admission not in admission_ids, 'Player or admission is reused across rooms')
            player_ids.add(player_id)
            admission_ids.add(admission)
        rooms.update(sources)
        summaries.append({'roomIds': row['roomIds'], 'serverAcknowledgements': report['serverAcknowledgements'],
                          'worldSequence': report['worldSequence'], 'combatSequence': report['combatSequence'],
                          **({'udpPreflight': report['udpPreflight']} if preflights else {}),
                          **({'udpSourcePreflight': report['udpSourcePreflight']} if source_preflights else {}),
                          **({'worldJournal': report['worldJournal']} if journals else {}),
                          **({'combatJournal': report['combatJournal']} if combat_journals else {}),
                          **({'playerSources': report['playerSources']} if verify_player_sources else {}),
                          **({'reconnectHistory': report['reconnectHistory']} if verify_reconnect_history else {}),
                          **({'windowsLinkMetrics': sorted(link_rows, key=lambda row: (row['roomId'], row['seat']))} if link_rows else {}),
                          **({'windowsReleaseSeats': sorted(release_seats, key=lambda row: (row['roomId'], row['seat']))} if release_seats else {}),
                          **({'experienceMode': experience} if check_alignments else {}),
                          **({'roomAlignments': report['roomAlignments']} if alignments is not None else {})})

    require(recorded_at in end_times and not expected, 'Closure time or session set differs from the terminal evidence')
    require(not quest_deployments, 'Quest deployment reports include seats without original Quest logcat evidence')
    require(windows_link_reports in (0, windows_players), 'Windows link evidence must cover every Windows seat in the venue')
    if link_criteria is not None:
        require(windows_link_reports == windows_players > 0,
                'Windows link criteria require original link reports for every Windows seat')
        outside_criteria = sorted((row['roomId'], row['seat']) for session in summaries
                                  for row in session.get('windowsLinkMetrics', ()) if row.get('criteriaFailures'))
        require(not outside_criteria, 'Windows link criteria not met at ' +
                ', '.join(f'room {room} seat {seat}' for room, seat in outside_criteria))
    peer_ips = {address for sources in rooms.values() for address in sources}
    remote = peer_ips - server_ips
    if require_distinct_remote_roster:
        require(len(remote) == len(player_ids),
                'Distinct remote roster requires one unique observed IPv4 outside the declared server addresses for every seat')
    require(topology != 'direct-lan' or remote, 'Direct LAN needs a peer outside the declared server addresses')
    begin_summary = {}
    if begin_kind is not None:
        counts = ('trackedPlayers', 'simulatedPlayers', 'participants') if verify_participation_begin else ('trackedPlayers',)
        begin_summary[begin_kind] = {'requestId': begin_request, 'sessions': len(summaries),
                                    **{name: sum(item['worldJournal'][begin_kind][name] for item in summaries) for name in counts}}
    reconnect_summary = {}
    if verify_reconnect_history:
        histories = [row['reconnectHistory'] for row in summaries]
        reconnect_summary['reconnectHistory'] = {
            **{key: sum(row[key] for row in histories) for key in ('observedConnections', 'retiredConnections')},
            'reconnectedSeats': sorted(chain.from_iterable(row['reconnectedSeats'] for row in histories),
                                       key=lambda row: (row['roomId'], row['seat']))}
    if reconnect_window is not None:
        reconnect_summary['reconnectWindow'] = reconnect_window.summary(reconnect_summary['reconnectHistory']['reconnectedSeats'], len(player_ids))
    report = {'version': 1, 'consistent': True, 'declaredTopology': topology, 'mode': mode, 'players': len(player_ids),
            **({'expectedPlayersPerRoom': players_per_room} if 'expectedPlayersPerRoom' in manifest else {}),
            'rooms': [{'roomId': room, 'players': len(rooms[room]),
                       'playersOutsideDeclaredServer': sum(address in remote for address in rooms[room])} for room in all_rooms],
            'sessions': sorted(summaries, key=lambda item: item['roomIds']),
            'distinctPeerAddresses': len(peer_ips), 'distinctAddressesOutsideDeclaredServer': len(remote),
            'serverAcknowledgements': sum(item['serverAcknowledgements'] for item in summaries),
            'physicalHostsVerified': False, 'networkCapacityAccepted': False,
            **station_summary,
            **({'venueLauncherReport': venue_launcher} if venue_launcher is not None else {}),
            **({'venueDebriefReceipts': {'sha256': debrief_hash, 'sessions': len(summaries), 'acknowledgedPlayers': len(player_ids)}}
               if debrief_receipts is not None else {}),
            **({'distinctRemoteRoster': {'seatsVerified': len(player_ids), 'distinctSourceAddresses': len(remote),
                'connectionsVerified': reconnect_summary['reconnectHistory']['observedConnections']}} if require_distinct_remote_roster else {}),
            **({'questLogcatPlayers': quest_players} if quest_players else {}),
            **({**capture_summary, 'questCaptureSeatsVerified': quest_players} if capture_supplied else {}),
            **({'questDeployment': deployment_summary} if deployment_summary is not None else {}),
            **({'venueRelease': {'reportSha256': release_hash,
                **({'windows': {'playerManifestSha256': windows_hash, 'seatsVerified': windows_players}} if windows_players else {}),
                **({'quest': deployment_summary} if deployment_summary is not None else {})}} if release is not None else {}),
            **({'windowsLinkMetricsVerified': windows_link_reports} if windows_link_reports else {}),
            **({'windowsLinkCriteria': {**link_criteria, 'seatsVerified': windows_link_reports}} if link_criteria is not None else {}),
            **({'udpPreflightsVerified': len(exchanges)} if preflights else {}),
            **({'udpSourcePreflightsVerified': len(exchanges)} if source_preflights else {}),
            **({'worldJournalsVerified': len(summaries)} if journals else {}),
            **({'combatJournalsVerified': len(summaries)} if combat_journals else {}),
            **({'venueControlBatches': control_summary} if control_summary else {}),
            **({'concurrentRoster': concurrency.summary(len(player_ids))} if concurrency is not None else {}),
            **begin_summary,
            **reconnect_summary,
            **({'roomAlignmentsVerified': sum(len(row.get('roomAlignments', [])) for row in summaries)} if check_alignments else {})}
    return report, {'manifestSha256': hashlib.sha256(raw_manifest).hexdigest(), 'closureRequestId': closure_id,
                    'started': min(start_times), 'ended': max(end_times),
                    'identities': {'closure': {closure_id}, 'session': {row['sessionId'] for row in rows},
                                   'world stream': stream_ids, 'admission': admission_ids}}


def verify_venue_stages(plan_path):
    plan_path = plan_path.resolve(strict=True)
    with plan_path.open('rb') as stream:
        raw_plan = limited_read(stream)
    plan = read_json(raw_plan.decode('utf-8-sig'))
    required = {'version', 'topology', 'minimumConcurrentMilliseconds', 'venueManifests'}
    require(type(plan) is dict and required <= plan.keys() <= required | {'requireDistinctRemoteRoster'},
            'Invalid staged venue plan fields')
    integer(plan['version'], 1, 1)
    topology = plan['topology']
    require(topology in ('same-host', 'direct-lan'), 'Invalid staged venue topology')
    minimum = integer(plan['minimumConcurrentMilliseconds'], 1000, 900000)
    distinct = plan.get('requireDistinctRemoteRoster', False)
    require(type(distinct) is bool and (not distinct or topology == 'direct-lan'),
            'Distinct staged roster requires a boolean option and direct-lan topology')
    modes, sizes = ('Independent', 'Linked'), (5, 10, 25)
    names = plan['venueManifests']
    require(type(names) is list and len(names) == len(modes) * len(sizes)
            and all(type(name) is str and bool(name.strip()) for name in names),
            'Provide six venue manifests for the two 5, 10 and 25 seat series')
    paths = [(plan_path.parent / name).resolve(strict=True) for name in names]
    require(plan_path not in paths and len(set(paths)) == len(paths), 'Staged venue manifest paths must be distinct')

    stages, used = {}, {}
    release_hash = None
    for path in paths:
        report, batch = verify_venue_batch(path)
        mode, players = report['mode'], report['players']
        key = mode, players
        require(mode in modes and players in sizes and key not in stages,
                'Staged venue evidence must cover each mode and seat count exactly once')
        require(report['declaredTopology'] == topology, 'Venue batch topology differs from the staged plan')
        for label, values in batch['identities'].items():
            seen = used.setdefault(label, set())
            require(seen.isdisjoint(values), f'Staged venue evidence reuses an original {label} identity')
            seen.update(values)
        current_release = report.get('venueRelease', {}).get('reportSha256')
        require(current_release is not None and release_hash in (None, current_release),
                'Every staged venue batch must use the same original verified release report')
        release_hash = current_release
        overlap = report.get('concurrentRoster')
        require(overlap is not None and overlap['longestMilliseconds'] >= minimum,
                'Venue batch lacks the continuous concurrent roster required by the staged plan')
        require(not distinct or report.get('distinctRemoteRoster', {}).get('seatsVerified') == players,
                'Venue batch lacks distinct original remote sources for every seat')
        stages[key] = (report, batch)

    for mode in modes:
        batches = [stages[mode, players][1] for players in sizes]
        require(all(before['ended'] <= after['started'] for before, after in zip(batches, batches[1:])),
                f'{mode} original sessions do not run in 5, 10 and 25 seat order')

    results = []
    for players in sizes:
        for mode in modes:
            report, batch = stages[mode, players]
            results.append({'mode': mode, 'players': players, 'closureRequestId': batch['closureRequestId'],
                            'manifestSha256': batch['manifestSha256'],
                            'startedAtUtc': batch['started'].astimezone(timezone.utc).isoformat(),
                            'endedAtUtc': batch['ended'].astimezone(timezone.utc).isoformat(),
                            'serverAcknowledgements': report['serverAcknowledgements'],
                            'worldJournalsVerified': report['worldJournalsVerified'],
                            'concurrentRoster': report['concurrentRoster'],
                            **{field: report[field] for field in ('combatJournalsVerified', 'distinctRemoteRoster', 'windowsLinkCriteria',
                                                                'windowsStationAddresses')
                               if field in report}})
    return {'version': 1, 'consistent': True, 'declaredTopology': topology,
            'planSha256': hashlib.sha256(raw_plan).hexdigest(), 'venueReleaseSha256': release_hash,
            'minimumConcurrentMilliseconds': minimum, 'requireDistinctRemoteRoster': distinct, 'stages': results,
            'serverAcknowledgements': sum(stage['serverAcknowledgements'] for stage in results),
            'physicalHostsVerified': False, 'networkCapacityAccepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    venue = parser.add_mutually_exclusive_group()
    venue.add_argument('--venue-manifest', type=Path, help='Check one five-room End batch from a private manifest')
    venue.add_argument('--venue-stages', type=Path, help='Verify the six original five-room batches for staged 5, 10 and 25 player runs')
    parser.add_argument('--inspect-windows-inbox', action='store_true', help='List missing seats, conflicts and verified Windows measurements in a venue inbox')
    parser.add_argument('--topology', choices=('same-host', 'direct-lan'))
    parser.add_argument('--server-ip', action='append', help='Repeat for each assigned server IPv4')
    parser.add_argument('--world-journal', type=Path, help='Original closed .worldlog for a single session')
    parser.add_argument('--combat-journal', type=Path, help='Original closed combat .journal for a single session')
    parser.add_argument('--verify-player-sources', action='store_true', help='Match each player log startup with accepted rigs in the closed journal')
    parser.add_argument('--verify-reconnect-history', action='store_true', help='Match the complete connection history to original server peer, release and result markers')
    parser.add_argument('--udp-preflight', nargs=2, type=Path, metavar=('LISTENER', 'PROBE'), help='Original UDP preflight reports for this session')
    parser.add_argument('--udp-source-preflight', action='append', nargs=2, type=Path, metavar=('LISTENER', 'PROBE'),
                        help='Repeat for every acknowledged UDP source address at this binding')
    parser.add_argument('--room-alignment', action='append', nargs=2, metavar=('ROOM', 'JSON'),
                        help='Repeat for each locked MR room in a single session')
    for name in ('launcher-report', 'session', 'statistics', 'endpoint', 'server-log'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--player', action='append', nargs=2, metavar=('EXPECTED_IPV4', 'LOG'))
    parser.add_argument('--quest-player', action='append', nargs=3, metavar=('EXPECTED_IPV4', 'LOGCAT', 'PID'))
    args = parser.parse_args()
    json_paths = [args.launcher_report, args.session, args.statistics, args.endpoint]
    single_args = [args.topology, args.server_ip, *json_paths, args.server_log, args.player or args.quest_player]
    batch = args.venue_manifest or args.venue_stages
    extra_single_args = [args.world_journal, args.combat_journal, args.room_alignment, args.udp_preflight,
                         args.udp_source_preflight, args.verify_player_sources, args.verify_reconnect_history]
    if (batch and any(single_args + extra_single_args)) or (not batch and not all(single_args)):
        parser.error('Provide --venue-manifest or --venue-stages alone, or all single-session options.')
    if args.inspect_windows_inbox and not args.venue_manifest:
        parser.error('--inspect-windows-inbox requires --venue-manifest.')
    if args.udp_preflight and args.udp_source_preflight:
        parser.error('Use either --udp-preflight or --udp-source-preflight.')
    try:
        if args.inspect_windows_inbox:
            report, _ = verify_venue_batch(args.venue_manifest, inspect_windows=True)
        elif args.venue_stages:
            report = verify_venue_stages(args.venue_stages)
        elif args.venue_manifest:
            report = verify_venue(args.venue_manifest)
        else:
            windows = args.player or []
            quest = args.quest_player or []
            integer(len(windows) + len(quest), 1, 25)
            inputs = [*json_paths, args.server_log, *(Path(row[1]) for row in chain(windows, quest))]
            if args.world_journal is not None:
                inputs.append(args.world_journal)
            if args.combat_journal is not None:
                inputs.append(args.combat_journal)
            if args.udp_preflight is not None:
                inputs.extend(args.udp_preflight)
            if args.udp_source_preflight is not None:
                integer(len(args.udp_source_preflight), 1, len(windows) + len(quest))
                inputs.extend(chain.from_iterable(args.udp_source_preflight))
            alignments = None
            if args.room_alignment:
                alignments = {}
                for room, path in args.room_alignment:
                    require(room in ('1', '2', '3', '4', '5') and int(room) not in alignments, 'Provide each MR room number once')
                    alignments[int(room)] = Path(path)
                inputs.extend(alignments.values())
            require(len({path.resolve(strict=True) for path in inputs}) == len(inputs), 'Evidence paths must be distinct')
            players = [(ipv4(address), content(Path(path))) for address, path in windows]
            quest_players = []
            for address, path, pid in quest:
                require(re.fullmatch(r'[1-9][0-9]{0,9}', pid), 'Provide the original Quest process ID')
                quest_players.append((ipv4(address), content(Path(path)), integer(int(pid), 1, 2**31 - 1)))
            report = verify(args.topology, {ipv4(address) for address in args.server_ip},
                            *(read_json(content(path)) for path in json_paths), content(args.server_log), players,
                            quest_player_logs=quest_players, world_journal=args.world_journal, combat_journal=args.combat_journal,
                            room_alignments=alignments,
                            udp_preflight=args.udp_preflight, udp_source_preflights=args.udp_source_preflight,
                            verify_player_sources=args.verify_player_sources, verify_reconnect_history=args.verify_reconnect_history)
    except EvidenceError as error:
        parser.exit(1, f'Field evidence rejected. {error}.\n')
    except (OSError, UnicodeError, ArithmeticError, AttributeError, KeyError, TypeError, ValueError, RecursionError,
            zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError):
        parser.exit(1, 'Field evidence rejected. Check topology, original admissions, UDP peer markers, final seals and complete logs.\n')
    print(json.dumps(report, indent=2))
    if args.inspect_windows_inbox and (not report['complete'] or not report.get('windowsLinkMetrics', {}).get('meetsCriteria', True)):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
