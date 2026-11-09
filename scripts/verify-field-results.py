"""Check sealed Windows server results against Windows player logs or Quest logcat."""
import argparse
from datetime import datetime
from decimal import Decimal
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
import subprocess
import uuid
import zipfile
import zlib


COMBAT = ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken')
LAN = tuple(map(ipaddress.IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
SERVER_MARKER = re.compile(r'VR_SERVER_(ADMISSION_APPROVED|PEER|DEBRIEF_ACK|DEBRIEF_TIMEOUT) id=(0|[1-9][0-9]{0,19})(?: endpoint=(\S+))?')
CONNECT = re.compile(r'VR_CLIENT_CONNECTED id=(0|[1-9][0-9]{0,19})')
LOGCAT_UNITY = re.compile(r'[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3} +'
                          r'([1-9][0-9]{0,9}) +[1-9][0-9]{0,9} I Unity *: (.*)')
OPENXR_RUNTIME = re.compile(r'\[XR\] .* Runtime Name: (\S.{0,127})')
PLAYER_MARKERS = ('VR_CLIENT_CONNECTED', 'VR_CLIENT_DISCONNECTED', 'VR_CLIENT_DEBRIEF_FINAL')
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_ALIGNMENT_BYTES = 16 * 1024


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


def verify_world_journal(path, world, combat_sequence, through, applied_end, *, player_sources=None):
    spec = importlib.util.spec_from_file_location('field_world_journal', Path(__file__).with_name('analyze-world-journal.py'))
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    fields = ('schemaVersion', 'sessionId', 'streamId', 'origin', 'roomIds', 'calibration', 'captureStartedAtUtc')
    expected = {key: world['header'].get(key) for key in fields}

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
        journal = analyzer.analyze(path, expected_header=expected,
                                   on_running_frame=count_player_rigs if player_sources is not None else None)
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
    return {'sha256': journal['sha256'], 'frames': sequence, 'runningFrames': journal['runningFrames']}


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
           world_journal=None, room_alignments=None, udp_preflight=None, udp_source_preflights=None, verify_player_sources=False):
    report, _ = verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log,
                               len(player_logs) + len(quest_player_logs), player_logs, quest_player_logs=quest_player_logs,
                               world_journal=world_journal, room_alignments=room_alignments, udp_preflight=udp_preflight,
                               udp_source_preflights=udp_source_preflights, verify_player_sources=verify_player_sources)
    return report


def verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log, size, player_logs, *,
                   require_remote=True, quest_player_logs=(), world_journal=None, applied_end=None, room_alignments=None,
                   udp_preflight=None, udp_source_preflights=None, verify_player_sources=False):
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
    windows_logs = ((address, log, None) for address, log in player_logs)
    for expected_ip, log, pid in chain(windows_logs, quest_player_logs):
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
                                   player_sources=player_sources) if world_journal is not None else None
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
            **({'playerSources': sorted(player_sources.values(), key=lambda row: (row['roomId'], row['seat']))}
               if player_sources is not None else {}),
            **({'roomAlignments': alignments} if alignments is not None else {})}, room_sources


def management_zip(path):
    names = ('session.json', 'statistics.json', 'endpoint.json')
    with path.open('rb') as source, zipfile.ZipFile(io.BytesIO(limited_read(source))) as archive:
        require(sorted(archive.namelist()) == sorted(names), 'Management ZIP must contain exactly the three original JSON records')
        records = []
        for name in names:
            info = archive.getinfo(name)
            require(info.file_size <= MAX_FILE_BYTES and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    and not (info.flag_bits & 1), 'Unsupported or oversized management ZIP entry')
            with archive.open(info) as entry:
                records.append(read_json(limited_read(entry)))
    return records


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

    def evidence_path(value):
        require(type(value) is str and bool(value), 'Evidence path is missing')
        path = (manifest_path.parent / value).resolve(strict=True)
        require(path not in seen_paths, 'Evidence paths must be distinct across the venue')
        seen_paths.add(path)
        return path

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
    verify_player_sources = manifest.get('verifyPlayerSources', False)
    require(type(verify_player_sources) is bool and (not verify_player_sources or journals),
            'Player source verification requires a boolean option and the original world journals for the full batch')
    check_alignments = any('roomAlignments' in entry for entry in entries)
    require(not check_alignments or journals, 'MR alignment evidence requires the original world journals for the full batch')
    preflights = any('udpPreflight' in entry for entry in entries)
    source_preflights = any('udpSourcePreflights' in entry for entry in entries)
    require(not (preflights and source_preflights), 'Use either single-pair or all-source UDP preflight verification for the full batch')
    require(not preflights or all('udpPreflight' in entry for entry in entries), 'Provide UDP preflight reports for every session in this batch')
    require(not source_preflights or all('udpSourcePreflights' in entry for entry in entries),
            'Provide all-source UDP preflight reports for every session in this batch')

    def preflight_pair(pair):
        require(type(pair) is dict and set(pair) == {'listener', 'probe'}, 'Provide the original UDP listener and probe reports')
        return evidence_path(pair['listener']), evidence_path(pair['probe'])

    expected = {identity(row['sessionId']): row for row in rows}
    require(len(expected) == len(rows) and all(type(row['roomIds']) is list and row['roomIds']
            and all(integer(room, 1, 5) for room in row['roomIds']) for row in rows)
            and sorted(row['roomIds'] for row in rows) == expected_rooms, 'Closure does not cover exactly the five original rooms')

    rooms, summaries = {}, []
    quest_players = 0
    stream_ids, bindings, player_ids, admission_ids, end_times, exchanges = set(), set(), set(), set(), set(), set()
    for entry in entries:
        session, statistics, endpoint = management_zip(evidence_path(entry['evidenceZip']))
        launcher = read_json(content(evidence_path(entry['launcherReport'])))
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
        binding = (ipv4(endpoint['address']), integer(endpoint['port'], 1024, 65535))
        require(stream not in stream_ids and binding not in bindings, 'Venue reused a world stream or server UDP binding')
        stream_ids.add(stream)
        bindings.add(binding)
        players = entry['players']
        require(type(players) is list and len(players) == len(row['roomIds']) * 5, 'Each original room must include five player logs')
        logs, quest_logs = [], []
        for player in players:
            address, path = ipv4(player['address']), evidence_path(player['log'])
            if 'logcatPid' in player:
                quest_logs.append((address, path, integer(player['logcatPid'], 1, 2**31 - 1)))
            else:
                logs.append((address, path))
        preflight_paths = preflight_pair(entry['udpPreflight']) if preflights else None
        source_paths = None
        if source_preflights:
            pairs = entry['udpSourcePreflights']
            require(type(pairs) is list and 1 <= len(pairs) <= len(players), 'Invalid all-source UDP preflight list')
            source_paths = [preflight_pair(pair) for pair in pairs]
        report, sources = verify_session(topology, server_ips, launcher, session, statistics, endpoint,
                                         server_log, len(players), ((address, content(path)) for address, path in logs),
                                         require_remote=False,
                                         quest_player_logs=((address, content(path), pid) for address, path, pid in quest_logs),
                                         world_journal=evidence_path(entry['worldJournal']) if journals else None,
                                         applied_end=row['appliedAtSequence'], room_alignments=alignments, udp_preflight=preflight_paths,
                                         udp_source_preflights=source_paths, verify_player_sources=verify_player_sources)
        verified_pairs = ([report['udpPreflight']] if preflights else report['udpSourcePreflight']['pairs'] if source_preflights else [])
        for pair in verified_pairs:
            exchange = pair['exchangeSha256']
            require(exchange not in exchanges, 'Venue reused a UDP preflight exchange')
            exchanges.add(exchange)
        quest_players += len(quest_logs)
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
            **({'udpPreflightsVerified': len(exchanges)} if preflights else {}),
            **({'udpSourcePreflightsVerified': len(exchanges)} if source_preflights else {}),
            **({'worldJournalsVerified': len(summaries)} if journals else {}),
            **({'roomAlignmentsVerified': sum(len(row.get('roomAlignments', [])) for row in summaries)} if check_alignments else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venue-manifest', type=Path, help='Check one full five-room End batch from a private manifest')
    parser.add_argument('--topology', choices=('same-host', 'direct-lan'))
    parser.add_argument('--server-ip', action='append', help='Repeat for each assigned server IPv4')
    parser.add_argument('--world-journal', type=Path, help='Original closed .worldlog for a single session')
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
    if (args.venue_manifest and (any(single_args) or args.world_journal or args.room_alignment or args.udp_preflight
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
                            quest_player_logs=quest_players, world_journal=args.world_journal, room_alignments=alignments,
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
