"""Check sealed Windows server results against Windows player logs or Quest logcat."""
import argparse
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
EMPTY_GUID = bytes(16)
LAN = tuple(map(ipaddress.IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
SERVER_MARKER = re.compile(r'VR_SERVER_(ADMISSION_APPROVED|PEER|DEBRIEF_ACK|DEBRIEF_TIMEOUT) id=(0|[1-9][0-9]{0,19})(?: endpoint=(\S+))?')
CONNECT = re.compile(r'VR_CLIENT_CONNECTED id=(0|[1-9][0-9]{0,19})')
LOGCAT_UNITY = re.compile(r'[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3} +'
                          r'([1-9][0-9]{0,9}) +[1-9][0-9]{0,9} I Unity *: (.*)')
OPENXR_RUNTIME = re.compile(r'\[XR\] .* Runtime Name: (\S.{0,127})')
PLAYER_MARKERS = ('VR_CLIENT_CONNECTED', 'VR_CLIENT_DISCONNECTED', 'VR_CLIENT_DEBRIEF_FINAL')
MAX_FILE_BYTES = 16 * 1024 * 1024
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
    parsed = uuid.UUID(value)
    require(parsed.int and str(parsed) == value, 'Invalid evidence identity')
    return value


def ipv4(value):
    address = ipaddress.IPv4Address(value)
    require(not (address.is_unspecified or address.is_multicast or address.is_reserved), 'Invalid IPv4 evidence address')
    return address


def read_quest_plan_file(path):
    with path.open('rb') as source:
        raw = source.read(MAX_QUEST_PLAN_BYTES + 1)
    require(len(raw) <= MAX_QUEST_PLAN_BYTES, 'Quest plan or report is too large')
    value = read_json(raw.decode('utf-8-sig'))
    require(type(value) is dict and type(value.get('version')) is int and value['version'] == 1,
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


def quest_network_address(value):
    require(type(value) is str, 'Expected a Quest plan IPv4 address')
    parsed = ipv4(value)
    require(str(parsed) == value and (parsed.is_loopback or any(parsed in network for network in LAN)),
            'Use a canonical private or loopback IPv4 address')
    return value


def read_quest_network_plan(path):
    plan = read_quest_plan_file(path)
    require(set(plan) == {'version', 'mode', 'endpoints', 'sources'}, 'Unexpected Quest network plan fields')
    sources = {seat: quest_network_address(value) for seat, value in quest_seats(plan['sources'], 'address').items()}
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


def server_connections(log, port):
    approved, peers, acknowledged = set(), {}, set()
    started = 0
    for line in log.splitlines():
        if line.startswith('VR_NETWORK_STARTED '):
            require(line == f'VR_NETWORK_STARTED role=Server started=True background=True port={port}',
                    'Server log startup differs from the reported UDP binding')
            started += 1
        if line.startswith('VR_SERVER_PEER_LIMIT'):
            raise EvidenceError('UDP peer log reached its recording limit')
        if not line.startswith(('VR_SERVER_ADMISSION_APPROVED ', 'VR_SERVER_PEER ', 'VR_SERVER_DEBRIEF_ACK ', 'VR_SERVER_DEBRIEF_TIMEOUT ')):
            continue
        require(started == 1, 'Server connection marker precedes startup')
        match = SERVER_MARKER.fullmatch(line)
        require(match is not None, 'Malformed server connection marker')
        kind, connection, endpoint = match.groups()
        require(bool(endpoint) == (kind == 'PEER'), 'Unexpected server marker format')
        if kind == 'ADMISSION_APPROVED':
            require(connection not in approved, 'Duplicate server admission marker')
            approved.add(connection)
        elif kind == 'PEER':
            require(connection in approved and connection not in peers, 'Missing approval or duplicate UDP peer marker')
            peers[connection] = endpoint
        elif kind == 'DEBRIEF_ACK':
            require(connection in peers and connection not in acknowledged, 'Missing UDP peer or duplicate server acknowledgement')
            acknowledged.add(connection)
        else:
            raise EvidenceError('Server recorded a player result timeout')
    require(started == 1, 'Expected one original server startup in the log')
    return peers, acknowledged


def client_result(log):
    connection = None
    final = None
    seen = set()
    for line in log.splitlines():
        if line.startswith('VR_CLIENT_CONNECTED '):
            match = CONNECT.fullmatch(line)
            require(match is not None and connection is None and final is None, 'Unexpected player connection marker')
            connection = match.group(1)
            require(connection not in seen, 'Player connection number reused')
            seen.add(connection)
        elif line == 'VR_CLIENT_DISCONNECTED':
            connection = None
        elif line.startswith('VR_CLIENT_DEBRIEF_FINAL '):
            require(connection is not None and final is None, 'Player final result lacks a unique live connection')
            final = (connection, read_json(line.removeprefix('VR_CLIENT_DEBRIEF_FINAL ')))
    require(final is not None and connection is None, 'Missing player final result or terminal disconnect')
    return final


def client_startup_on_port(message, port):
    return re.fullmatch(rf'VR_NETWORK_STARTED role=Client started=True background=(True|False) port={port}', message) is not None


def quest_client_result(log, pid, port):
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
    return client_result('\n'.join(markers))


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


def verify_combat_journal(path, session_id, stream_id, origin, final_sequence, authority_end, ledger):
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


def roster_periods(players, minimum_ms, applied_end, *, require_tracked=False):
    expected = {pid: player['roomId'] for pid, player in players.items()}
    periods = []
    start = previous = previous_tick = None

    def observe(packet):
        nonlocal start, previous, previous_tick
        frame = packet['frame']
        if frame['phase'] != 'Running' or packet['suspended'] is not False or packet['observedSequence'] >= applied_end:
            previous = None
            return
        rows = frame['players']
        require(type(rows) is list and len(rows) <= 25, 'Invalid player rows in the concurrent roster evidence')
        connected = {row['id']: integer(row['roomId'], 1, 5) for row in rows
                     if row['connected'] is True and (not require_tracked or row['rig']['kind'] == 'Tracked')}
        tick = integer(frame['tick'])
        if len(rows) != len(expected) or connected != expected or not tick:
            previous = None
            return
        elapsed = integer(packet['elapsedMilliseconds'])
        if previous is None or elapsed - previous > MAX_CONCURRENT_FRAME_GAP_MS or tick <= previous_tick:
            start = elapsed
        previous, previous_tick = elapsed, tick
        if elapsed - start >= minimum_ms:
            if periods and periods[-1][0] == start:
                periods[-1] = (start, elapsed)
            else:
                periods.append((start, elapsed))

    return observe, periods


class VenueRosterOverlap:
    def __init__(self, minimum_ms, *, require_tracked=False):
        self.minimum_ms = minimum_ms
        self.minimum = timedelta(milliseconds=minimum_ms)
        self.require_tracked = require_tracked
        self.intervals = None

    def add(self, capture_started_at, periods):
        require(capture_started_at is not None, 'Concurrent roster verification requires an original UTC capture clock')
        capture = datetime.fromisoformat(capture_started_at).astimezone(timezone.utc)
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
        start, end = max(self.intervals, key=lambda pair: pair[1] - pair[0])
        return {'players': players, 'minimumMilliseconds': self.minimum_ms,
                'longestMilliseconds': (end - start) // timedelta(milliseconds=1),
                'maxFrameGapMilliseconds': MAX_CONCURRENT_FRAME_GAP_MS,
                'fromUtc': start.isoformat(), 'throughUtc': end.isoformat(),
                **({'rigKind': 'Tracked'} if self.require_tracked else {})}


def verify_world_journal(path, world, combat_sequence, through, applied_end, *, player_sources=None, tracking_begin=None,
                         players=None, concurrency=None):
    spec = importlib.util.spec_from_file_location('field_world_journal', Path(__file__).with_name('analyze-world-journal.py'))
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    fields = ('schemaVersion', 'sessionId', 'streamId', 'origin', 'roomIds', 'calibration', 'captureStartedAtUtc')
    expected = {key: world['header'].get(key) for key in fields}
    tracked = None
    if concurrency is not None:
        observe_roster, periods = roster_periods(players, concurrency.minimum_ms, applied_end,
                                                require_tracked=concurrency.require_tracked)

    def observe_packet(packet):
        if tracking_begin is not None:
            check_tracking_frame(packet)
        if concurrency is not None:
            observe_roster(packet)

    def check_tracking_frame(packet):
        nonlocal tracked
        if packet['sequence'] != tracking_begin['frame']['worldSequence']:
            return
        frame = packet['frame']
        require(integer(packet['elapsedMilliseconds']) == tracking_begin['frame']['elapsedMilliseconds']
                and integer(packet['observedSequence'], 1) == tracking_begin['appliedAtSequence'] - 1
                and packet['suspended'] is False and frame['phase'] == 'Preparing' and integer(frame['tick'], 0, 0) == 0,
                'Guarded Begin frame differs from the original Preparing boundary')
        rows = roster(frame['players'], 'id', len(players))
        require(set(rows) == set(players) and all(row['connected'] is True and row['rig']['kind'] == 'Tracked'
                    and integer(row['health'], 1, 100) and integer(row['roomId'], 1, 5) == players[pid]['roomId']
                    for pid, row in rows.items()), 'Guarded Begin frame does not contain the original tracked roster')
        tracked = len(rows)

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
        journal = analyzer.analyze(path, accepted_sequence=tracking_begin['appliedAtSequence'] if tracking_begin is not None else None,
                                   expected_header=expected, on_running_frame=count_player_rigs if player_sources is not None else None,
                                   on_packet=observe_packet if tracking_begin is not None or concurrency is not None else None)
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
        concurrency.add(journal['captureStartedAtUtc'], periods)
    result = {'sha256': journal['sha256'], 'frames': sequence, 'runningFrames': journal['runningFrames']}
    if tracking_begin is not None:
        first = journal['firstApplied']
        require(tracked is not None and first is not None
                and first['worldSequence'] > tracking_begin['frame']['worldSequence'],
                'World journal lacks the guarded Begin witness or its subsequent application')
        result['trackingBegin'] = {'requestId': tracking_begin['requestId'], 'appliedAtSequence': tracking_begin['appliedAtSequence'],
                                   'preparingFrame': tracking_begin['frame']['worldSequence'],
                                   'firstRunningFrame': first['worldSequence'], 'trackedPlayers': tracked}
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


def verify(topology, server_ips, launcher, session, statistics, endpoint, server_log, player_logs, *, quest_player_logs=(),
           world_journal=None, combat_journal=None, room_alignments=None, udp_preflight=None, udp_source_preflights=None,
           verify_player_sources=False):
    report, _ = verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log,
                               len(player_logs) + len(quest_player_logs), player_logs, quest_player_logs=quest_player_logs,
                               world_journal=world_journal, combat_journal=combat_journal, room_alignments=room_alignments, udp_preflight=udp_preflight,
                               udp_source_preflights=udp_source_preflights, verify_player_sources=verify_player_sources)
    return report


def verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log, size, player_logs, *,
                   require_remote=True, quest_player_logs=(), world_journal=None, combat_journal=None, applied_end=None, room_alignments=None,
                   udp_preflight=None, udp_source_preflights=None, verify_player_sources=False, quest_capture_logs=(),
                   tracking_begin=None, concurrency=None):
    integer(size, 1, 25)
    require(topology in ('same-host', 'direct-lan') and server_ips, 'Missing topology or server addresses')
    require(not verify_player_sources or world_journal is not None, 'Player source verification requires the original closed world journal')
    require(udp_preflight is None or udp_source_preflights is None, 'Use either single-pair or all-source UDP preflight verification')
    require(integer(launcher['schemaVersion'], 1, 1) and launcher['status'] == 'sealed-stopped'
            and launcher['complete'] is launcher['childExited'] is launcher['cleanupCompleted'] is True
            and integer(launcher['exitCode'], 0, 0) == 0, 'Launcher lacks terminal evidence')
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
    origin = header['origin']
    require(world['complete'] is combat['sealed'] is True and statistics['pendingTelemetry'] is False
            and header['streamId'] == combat['streamId'] == stream_id and origin == combat['origin']
            and origin in ('Simulation', 'GameServer') and session['combatStream'] == combat,
            'World and combat seals disagree')
    world_sequence = integer(world['acceptedSequence'], 1)
    combat_sequence = integer(combat['acceptedSequence'])
    through = integer(session['sequence'], 1)
    require(integer(statistics['throughSequence'], 1) == through, 'Statistics do not match the terminal session sequence')
    players = roster(session['players'], 'id', size)
    ledger = roster(statistics['players'], 'playerId', size)
    require(set(players) == set(ledger), 'Final roster and statistics disagree')
    require(len({identity(p['admissionId']) for p in players.values()}) == size, 'Duplicate admission identity')
    if statistics['origin'] is None:
        require(combat_sequence == 0 and all(scores(p) == (0, 0, 0, 0, 0, 100, 0) for p in ledger.values()), 'Missing statistics origin for nonempty combat')
    else:
        require(statistics['origin'] == origin, 'Statistics source differs from the seals')

    peers, acknowledged = server_connections(server_log, port)
    used_players, used_connections, endpoints = set(), set(), set()
    room_sources = {}
    player_sources = {} if verify_player_sources else None
    source_seats = set()
    quest_players = 0
    windows_logs = ((address, log, None, None) for address, log in player_logs)
    quest_logs = ((address, log, pid, None) for address, log, pid in quest_player_logs)
    for expected_ip, log, pid, capture_seat in chain(windows_logs, quest_logs, quest_capture_logs):
        connection, result = client_result(log) if pid is None else quest_client_result(log, pid, port)
        require(connection in acknowledged and connection not in used_connections, 'Missing or reused server acknowledgement')
        observed = peer_address(peers[connection])
        require(observed[0] == expected_ip and observed not in endpoints, 'UDP peer differs from the declared source or is reused')
        player_id = identity(result['playerId'])
        require(player_id in players and player_id not in used_players, 'Unexpected or duplicated result player')
        owner, stats = players[player_id], ledger[player_id]
        if pid is not None:
            require(owner.get('headset') == 'Quest3' and topology == 'direct-lan' and expected_ip not in server_ips,
                    'Quest logcat requires a Quest 3 admission and its own direct LAN address')
            quest_players += 1
        room = integer(owner['roomId'], 1, 5)
        require(room in rooms and integer(result['roomId'], 1, 5) == integer(stats['roomId'], 1, 5) == room
                and result['admissionId'] == owner['admissionId'], 'Player result admission or room differs')
        if capture_seat is not None:
            require((room, integer(owner['seat'], 0, 4) + 1) == capture_seat,
                    'Quest capture room or seat differs from the original admission')
        require(integer(result['version'], 1, 1) and result['sessionId'] == session_id
                and result['streamId'] == stream_id and result['origin'] == origin
                and integer(result['worldSequence'], 1) == world_sequence and integer(result['throughSequence'], 1) == through
                and integer(result['finalStreamSequence']) == combat_sequence and scores(result) == scores(stats),
                'Player result differs from the final seals or statistics')
        if player_sources is not None:
            seat = integer(owner['seat'], 0, 4) + 1
            require((room, seat) not in source_seats, 'Duplicate seat in the player source evidence')
            source_seats.add((room, seat))
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
    journal = verify_world_journal(world_journal, world, combat_sequence, through, applied_end,
                                   player_sources=player_sources, tracking_begin=tracking_begin, players=players,
                                   concurrency=concurrency) if world_journal is not None else None
    combat_evidence = verify_combat_journal(combat_journal, session_id, stream_id, origin, combat_sequence,
                                            applied_end if applied_end is not None else through, ledger) if combat_journal is not None else None
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


def venue_windows_logs(rows, expected, evidence_path):
    require(type(rows) is list and 1 <= len(rows) <= 25, 'Provide one to 25 original Windows logs in windowsPlayers')
    groups = {}
    for row in rows:
        require(type(row) is dict and set(row) == {'address', 'log'}, 'A venue Windows log needs an address and log path')
        address, path = ipv4(row['address']), evidence_path(row['log'])
        _, result = client_result(content(path))
        session_id = identity(result['sessionId'])
        require(session_id in expected, 'Windows log belongs to a different venue session')
        group = groups.setdefault(session_id, [])
        group.append((address, path))
        require(len(group) <= len(expected[session_id]['roomIds']) * 5, 'Too many Windows logs for an original venue session')
    return groups


def read_udp_preflight_batch(path, mode, expected_rooms):
    batch = read_json(content(path))
    require(integer(batch['version'], 1, 1) and batch.get('scope') == 'quest-udp-preflight-only' and batch.get('mode') == mode
            and batch.get('complete') is True, 'Provide a complete Quest UDP preflight batch for the original mode')
    groups = batch['groups']
    require(type(groups) is list and 1 <= len(groups) <= len(expected_rooms), 'Invalid Quest UDP endpoint groups')
    sources = {}
    for group in groups:
        room_ids = group['roomIds']
        require(type(room_ids) is list and all(type(room) is int for room in room_ids) and room_ids in expected_rooms
                and tuple(room_ids) not in sources and group.get('complete') is True,
                'Invalid or repeated Quest UDP endpoint group')
        pairs = group['udpSourcePreflights']
        require(type(pairs) is list and 1 <= len(pairs) <= len(room_ids) * 5, 'Invalid all-source UDP preflight list')
        sources[tuple(room_ids)] = [(pair, path.parent) for pair in pairs]
    return sources


def read_quest_capture_batches(spec, mode, expected, evidence_path):
    require(type(spec) is dict and set(spec) == {'networkPlan', 'reports'},
            'Provide a Quest network plan and capture reports')
    plan_mode, endpoints, sources = read_quest_network_plan(evidence_path(spec['networkPlan']))
    require(plan_mode == mode, 'Quest network plan differs from the venue mode')
    reports = spec['reports']
    require(type(reports) is list and 1 <= len(reports) <= 25, 'Provide 1 to 25 Quest capture reports')
    captures, used_seats = {}, set()
    for name in reports:
        path = evidence_path(name)
        report = read_quest_plan_file(path)
        require(set(report) == {'version', 'complete', 'topology', 'expectedSeats', 'capturedSeats', 'scope', 'seats'}
                and report['complete'] is True and report['topology'] == mode and report['scope'] == 'quest-logcat-only',
                'Quest capture report is incomplete or has the wrong topology')
        count = integer(report['expectedSeats'], 1, 25)
        require(integer(report['capturedSeats'], 1, 25) == count and type(report['seats']) is list
                and len(report['seats']) == count, 'Quest capture report seat totals differ')
        for row in report['seats']:
            require(type(row) is dict and set(row) == {'roomId', 'seat', 'sessionId', 'port', 'complete', 'log',
                    'logcatPid', 'bytes', 'sha256'} and row['complete'] is True, 'Quest capture seat is incomplete')
            seat = integer(row['roomId'], 1, 5), integer(row['seat'], 1, 5)
            require(seat in sources and seat not in used_seats, 'Quest capture repeats or names an unplanned seat')
            session_id = identity(row['sessionId'])
            session = expected.get(session_id)
            require(session is not None and seat[0] in session['roomIds'], 'Quest capture does not match an original session and room')
            require(integer(row['port'], 1024, 65535) == endpoints[tuple(session['roomIds'])][1],
                    'Quest capture port differs from the network plan')
            require(row['log'] == f'room-{seat[0]:02}-seat-{seat[1]:02}-logcat.txt', 'Expected the original Quest capture log name')
            log = evidence_path(row['log'], path.parent)
            require(log.parent == path.parent and log.name == row['log'], 'Quest capture log must be next to its report')
            require(type(row['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['sha256']),
                    'Invalid original Quest capture digest')
            captures.setdefault(session_id, []).append((ipv4(sources[seat]), log, integer(row['logcatPid'], 1, 2**31 - 1),
                                                        seat, integer(row['bytes'], 1, MAX_FILE_BYTES), row['sha256']))
            used_seats.add(seat)
    require(used_seats == sources.keys(), 'Quest capture reports must cover the planned Quest seats exactly')
    return captures, endpoints, len(reports)


def quest_capture_log(address, path, pid, seat, size, digest):
    with path.open('rb') as source:
        raw = limited_read(source)
    require(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, 'Original Quest capture log size or digest differs')
    return address, raw.decode('utf-8-sig'), pid, seat


def verify_venue(manifest_path):
    manifest_path = manifest_path.resolve(strict=True)
    manifest = read_json(content(manifest_path))
    integer(manifest['version'], 1, 1)
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

    packed = 'venueBundle' in manifest
    require(packed != ('closure' in manifest), 'Provide either venueBundle or the original closure and per-session ZIPs')
    if packed:
        closure, archives = venue_bundle(evidence_path(manifest['venueBundle']), mode)
    else:
        closure = read_json(content(evidence_path(manifest['closure'])))['batch']
    identity(closure['requestId'])
    recorded_at = datetime.fromisoformat(closure['recordedAtUtc'])
    require(recorded_at.utcoffset() is not None, 'Closure time must specify a time zone')
    all_rooms = list(range(1, 6))
    expected_rooms = [all_rooms] if mode == 'Linked' else [[room] for room in all_rooms]
    entries = manifest['sessions']
    rows = closure['sessions']
    require(type(entries) is list and type(rows) is list and len(entries) == len(rows) == len(expected_rooms),
            'Venue must contain the original five independent sessions or one linked session')
    journals = any('worldJournal' in entry for entry in entries)
    require(not journals or all('worldJournal' in entry for entry in entries), 'Provide a world journal for every session in this batch')
    combat_journals = any('combatJournal' in entry for entry in entries)
    require(not combat_journals or all('combatJournal' in entry for entry in entries),
            'Provide a combat journal for every session in this batch')
    require_tracked = manifest.get('requireTrackedRoster', False)
    require(type(require_tracked) is bool, 'requireTrackedRoster must be a boolean')
    require(not require_tracked or 'minimumConcurrentMilliseconds' in manifest,
            'requireTrackedRoster requires minimumConcurrentMilliseconds')
    concurrency = None
    if 'minimumConcurrentMilliseconds' in manifest:
        require(journals, 'Concurrent roster verification requires the original world journals for the full batch')
        concurrency = VenueRosterOverlap(integer(manifest['minimumConcurrentMilliseconds'], 1000, 900000),
                                         require_tracked=require_tracked)
    verify_player_sources = manifest.get('verifyPlayerSources', False)
    require(type(verify_player_sources) is bool and (not verify_player_sources or journals),
            'Player source verification requires a boolean option and the original world journals for the full batch')
    verify_player_sources = verify_player_sources or require_tracked
    verify_tracking_begin = manifest.get('verifyTrackingBegin', False)
    require(type(verify_tracking_begin) is bool and (not verify_tracking_begin or journals),
            'Guarded Begin verification requires a boolean option and the original world journals for the full batch')
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

    batch_pairs = {}
    if batch_supplied:
        batch_names = [manifest['udpPreflightBatch']] if single_batch else manifest['udpPreflightBatches']
        require(type(batch_names) is list and 1 <= len(batch_names) <= 25, 'Provide 1 to 25 Quest UDP batch reports')
        for name in batch_names:
            batch = read_udp_preflight_batch(evidence_path(name), mode, expected_rooms)
            for room_ids, sources in batch.items():
                combined = batch_pairs.setdefault(room_ids, [])
                combined.extend(sources)
                require(len(combined) <= len(room_ids) * 5, 'Too many UDP preflight pairs for one original endpoint')
        require(source_lists or set(batch_pairs) == {tuple(rooms) for rooms in expected_rooms},
                'The Quest UDP preflight batches must cover every original endpoint')

    def preflight_pair(pair, base=manifest_path.parent):
        require(type(pair) is dict and set(pair) == {'listener', 'probe'}, 'Provide the original UDP listener and probe reports')
        return evidence_path(pair['listener'], base), evidence_path(pair['probe'], base)

    expected = {identity(row['sessionId']): row for row in rows}
    require(len(expected) == len(rows) and all(type(row['roomIds']) is list and row['roomIds']
            and all(integer(room, 1, 5) for room in row['roomIds']) for row in rows)
            and sorted(row['roomIds'] for row in rows) == expected_rooms, 'Closure does not cover exactly the five original rooms')

    windows_supplied = 'windowsPlayers' in manifest
    windows_by_session = venue_windows_logs(manifest['windowsPlayers'], expected, evidence_path) if windows_supplied else {}

    capture_supplied = 'questCaptures' in manifest
    captures, capture_endpoints, capture_batches = {}, {}, 0
    if capture_supplied:
        require(topology == 'direct-lan', 'Quest capture batches require direct LAN evidence')
        captures, capture_endpoints, capture_batches = read_quest_capture_batches(manifest['questCaptures'], mode, expected, evidence_path)

    rooms, summaries = {}, []
    quest_players = 0
    stream_ids, bindings, player_ids, admission_ids, end_times, exchanges = set(), set(), set(), set(), set(), set()
    begin_request = None
    for entry in entries:
        launcher = read_json(content(evidence_path(entry['launcherReport'])))
        if packed:
            require('evidenceZip' not in entry, 'Omit per-session evidenceZip when using venueBundle')
            launch_id = identity(launcher['sessionId'])
            original = expected.get(launch_id)
            require(original is not None, 'Launcher report belongs to a different or repeated venue session')
            name = 'linked.zip' if mode == 'Linked' else f"room-{original['roomIds'][0]:02}.zip"
            session, statistics, endpoint = management_zip_records(archives[name])
            require(session['id'] == launch_id, 'Venue ZIP member differs from its original launcher session')
        else:
            session, statistics, endpoint = management_zip(evidence_path(entry['evidenceZip']))
        server_log = content(evidence_path(entry['serverLog']))
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
        end_times.add(datetime.fromisoformat(session['endedAtUtc']))
        stream = identity(launcher['streamId'])
        tracking_begin = None
        if verify_tracking_begin:
            verify_experience(session, launcher['finalWorld']['header'])
            tracking_begin = row.get('trackingBegin')
            require(type(tracking_begin) is dict and set(tracking_begin) == {'requestId', 'appliedAtSequence', 'frame'},
                    'Closure is missing an original guarded Begin witness')
            request = identity(tracking_begin['requestId'])
            require(request != closure['requestId'] and begin_request in (None, request),
                    'Venue sessions do not share one original guarded Begin request')
            begin_request = request
            integer(tracking_begin['appliedAtSequence'], 2, row['appliedAtSequence'] - 1)
            frame = tracking_begin['frame']
            require(type(frame) is dict and set(frame) == {'streamId', 'worldSequence', 'elapsedMilliseconds'}
                    and identity(frame['streamId']) == stream, 'Guarded Begin witness uses another world source')
            integer(frame['worldSequence'], 1, launcher['finalWorld']['acceptedSequence'] - 1)
            integer(frame['elapsedMilliseconds'])
        binding = (ipv4(endpoint['address']), integer(endpoint['port'], 1024, 65535))
        require(stream not in stream_ids and binding not in bindings, 'Venue reused a world stream or server UDP binding')
        stream_ids.add(stream)
        bindings.add(binding)
        captured = captures.get(session['id'], [])
        if capture_supplied:
            require((str(binding[0]), binding[1]) == capture_endpoints[tuple(row['roomIds'])],
                    'Quest network plan endpoint differs from the original game binding')
        logs = list(windows_by_session.get(session['id'], []))
        players = entry.get('players', []) if capture_supplied or windows_supplied else entry['players']
        require(type(players) is list and all(type(player) is dict for player in players), 'Invalid player log list')
        if windows_supplied:
            require(all('logcatPid' in player for player in players), 'Use windowsPlayers or per-session Windows logs, not both')
        size = len(players) + len(captured) + len(logs)
        require(size == len(row['roomIds']) * 5,
                'Each original room must include five player logs')
        quest_logs = []
        for player in players:
            address, path = ipv4(player['address']), evidence_path(player['log'])
            if 'logcatPid' in player:
                require(not capture_supplied, 'Use the Quest capture batches or manual Quest logs, not both')
                quest_logs.append((address, path, integer(player['logcatPid'], 1, 2**31 - 1)))
            else:
                logs.append((address, path))
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
                                         server_log, size, ((address, content(path)) for address, path in logs),
                                         require_remote=False,
                                         quest_player_logs=((address, content(path), pid) for address, path, pid in quest_logs),
                                         world_journal=evidence_path(entry['worldJournal']) if journals else None,
                                         combat_journal=evidence_path(entry['combatJournal']) if combat_journals else None,
                                         applied_end=row['appliedAtSequence'], room_alignments=alignments, udp_preflight=preflight_paths,
                                         udp_source_preflights=source_paths, verify_player_sources=verify_player_sources,
                                         quest_capture_logs=(quest_capture_log(*evidence) for evidence in captured),
                                         tracking_begin=tracking_begin, concurrency=concurrency)
        verified_pairs = ([report['udpPreflight']] if preflights else report['udpSourcePreflight']['pairs'] if source_preflights else [])
        for pair in verified_pairs:
            exchange = pair['exchangeSha256']
            require(exchange not in exchanges, 'Venue reused a UDP preflight exchange')
            exchanges.add(exchange)
        quest_players += len(quest_logs) + len(captured)
        seats = {(player['roomId'], integer(player['seat'], 0, 4)) for player in session['players']}
        require(seats == {(room, seat) for room in row['roomIds'] for seat in range(5)}, 'Final roster must cover every room seat exactly once')
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
                          **({'experienceMode': experience} if check_alignments else {}),
                          **({'roomAlignments': report['roomAlignments']} if alignments is not None else {})})

    require(recorded_at in end_times and not expected, 'Closure time or session set differs from the terminal evidence')
    peer_ips = {address for sources in rooms.values() for address in sources}
    remote = peer_ips - server_ips
    require(topology != 'direct-lan' or remote, 'Direct LAN needs a peer outside the declared server addresses')
    return {'version': 1, 'consistent': True, 'declaredTopology': topology, 'mode': mode, 'players': len(player_ids),
            'rooms': [{'roomId': room, 'players': len(rooms[room]),
                       'playersOutsideDeclaredServer': sum(address in remote for address in rooms[room])} for room in all_rooms],
            'sessions': sorted(summaries, key=lambda item: item['roomIds']),
            'distinctPeerAddresses': len(peer_ips), 'distinctAddressesOutsideDeclaredServer': len(remote),
            'serverAcknowledgements': sum(item['serverAcknowledgements'] for item in summaries),
            'physicalHostsVerified': False, 'networkCapacityAccepted': False,
            **({'questLogcatPlayers': quest_players} if quest_players else {}),
            **({'questCaptureBatchesVerified': capture_batches, 'questCaptureSeatsVerified': quest_players} if capture_supplied else {}),
            **({'udpPreflightsVerified': len(exchanges)} if preflights else {}),
            **({'udpSourcePreflightsVerified': len(exchanges)} if source_preflights else {}),
            **({'worldJournalsVerified': len(summaries)} if journals else {}),
            **({'combatJournalsVerified': len(summaries)} if combat_journals else {}),
            **({'concurrentRoster': concurrency.summary(len(player_ids))} if concurrency is not None else {}),
            **({'trackingBegin': {'requestId': begin_request, 'sessions': len(summaries),
                                  'trackedPlayers': sum(item['worldJournal']['trackingBegin']['trackedPlayers'] for item in summaries)}}
               if verify_tracking_begin else {}),
            **({'roomAlignmentsVerified': sum(len(row.get('roomAlignments', [])) for row in summaries)} if check_alignments else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venue-manifest', type=Path, help='Check one full five-room End batch from a private manifest')
    parser.add_argument('--topology', choices=('same-host', 'direct-lan'))
    parser.add_argument('--server-ip', action='append', help='Repeat for each assigned server IPv4')
    parser.add_argument('--world-journal', type=Path, help='Original closed .worldlog for a single session')
    parser.add_argument('--combat-journal', type=Path, help='Original closed combat .journal for a single session')
    parser.add_argument('--verify-player-sources', action='store_true', help='Match each player log startup with accepted rigs in the closed journal')
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
    if (args.venue_manifest and (any(single_args) or args.world_journal or args.combat_journal or args.room_alignment or args.udp_preflight
                                 or args.udp_source_preflight or args.verify_player_sources)) or (not args.venue_manifest and not all(single_args)):
        parser.error('Provide --venue-manifest alone or all single-session options.')
    if args.udp_preflight and args.udp_source_preflight:
        parser.error('Use either --udp-preflight or --udp-source-preflight.')
    try:
        if args.venue_manifest:
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
                            verify_player_sources=args.verify_player_sources)
    except EvidenceError as error:
        parser.exit(1, f'Field evidence rejected. {error}.\n')
    except (OSError, UnicodeError, ArithmeticError, AttributeError, KeyError, TypeError, ValueError, RecursionError,
            zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError):
        parser.exit(1, 'Field evidence rejected. Check topology, original admissions, UDP peer markers, final seals and complete logs.\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
