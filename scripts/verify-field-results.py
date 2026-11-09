"""Check closed Windows field sessions' endpoints, admissions and sealed results."""
import argparse
from datetime import datetime
from decimal import Decimal
import ipaddress
import io
import json
from pathlib import Path
import re
import uuid
import zipfile
import zlib


COMBAT = ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken')
LAN = tuple(map(ipaddress.IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
SERVER_MARKER = re.compile(r'VR_SERVER_(ADMISSION_APPROVED|PEER|DEBRIEF_ACK|DEBRIEF_TIMEOUT) id=(0|[1-9][0-9]{0,19})(?: endpoint=(\S+))?')
CONNECT = re.compile(r'VR_CLIENT_CONNECTED id=(0|[1-9][0-9]{0,19})')
MAX_FILE_BYTES = 16 * 1024 * 1024


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


def verify(topology, server_ips, launcher, session, statistics, endpoint, server_log, player_logs):
    report, _ = verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log, len(player_logs), player_logs)
    return report


def verify_session(topology, server_ips, launcher, session, statistics, endpoint, server_log, size, player_logs, *, require_remote=True):
    integer(size, 1, 25)
    require(topology in ('same-host', 'direct-lan') and server_ips, 'Missing topology or server addresses')
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
    for expected_ip, log in player_logs:
        connection, result = client_result(log)
        require(connection in acknowledged and connection not in used_connections, 'Missing or reused server acknowledgement')
        observed = peer_address(peers[connection])
        require(observed[0] == expected_ip and observed not in endpoints, 'UDP peer differs from the declared source or is reused')
        player_id = identity(result['playerId'])
        require(player_id in players and player_id not in used_players, 'Unexpected or duplicated result player')
        owner, stats = players[player_id], ledger[player_id]
        room = integer(owner['roomId'], 1, 5)
        require(room in rooms and integer(result['roomId'], 1, 5) == integer(stats['roomId'], 1, 5) == room
                and result['admissionId'] == owner['admissionId'], 'Player result admission or room differs')
        require(integer(result['version'], 1, 1) and result['sessionId'] == session_id
                and result['streamId'] == stream_id and result['origin'] == origin
                and integer(result['worldSequence'], 1) == world_sequence and integer(result['throughSequence'], 1) == through
                and integer(result['finalStreamSequence']) == combat_sequence and scores(result) == scores(stats),
                'Player result differs from the final seals or statistics')
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
    return {'version': 1, 'consistent': True, 'declaredTopology': topology, 'mode': mode,
            'players': size, 'playersPerRoom': {room: len(room_sources[room]) for room in sorted(room_sources)}, 'distinctPeerAddresses': len(peer_ips),
            'distinctAddressesOutsideDeclaredServer': len(remote), 'serverAcknowledgements': len(acknowledged),
            'worldSequence': world_sequence, 'combatSequence': combat_sequence, 'physicalHostsVerified': False,
            'networkCapacityAccepted': False}, room_sources


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
    expected = {identity(row['sessionId']): row for row in rows}
    require(len(expected) == len(rows) and all(type(row['roomIds']) is list and row['roomIds']
            and all(integer(room, 1, 5) for room in row['roomIds']) for row in rows)
            and sorted(row['roomIds'] for row in rows) == expected_rooms, 'Closure does not cover exactly the five original rooms')

    rooms, summaries = {}, []
    stream_ids, bindings, player_ids, admission_ids, end_times = set(), set(), set(), set(), set()
    for entry in entries:
        session, statistics, endpoint = management_zip(evidence_path(entry['evidenceZip']))
        launcher = read_json(content(evidence_path(entry['launcherReport'])))
        server_log = content(evidence_path(entry['serverLog']))
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
        logs = ((ipv4(player['address']), content(evidence_path(player['log']))) for player in players)
        report, sources = verify_session(topology, server_ips, launcher, session, statistics, endpoint,
                                         server_log, len(players), logs, require_remote=False)
        seats = {(player['roomId'], integer(player['seat'], 0, 4)) for player in session['players']}
        require(seats == {(room, seat) for room in row['roomIds'] for seat in range(5)}, 'Final roster must cover every room seat exactly once')
        for player in session['players']:
            player_id, admission = player['id'], player['admissionId']
            require(player_id not in player_ids and admission not in admission_ids, 'Player or admission is reused across rooms')
            player_ids.add(player_id)
            admission_ids.add(admission)
        rooms.update(sources)
        summaries.append({'roomIds': row['roomIds'], 'serverAcknowledgements': report['serverAcknowledgements'],
                          'worldSequence': report['worldSequence'], 'combatSequence': report['combatSequence']})

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
            'physicalHostsVerified': False, 'networkCapacityAccepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venue-manifest', type=Path, help='Check one full five-room End batch from a private manifest')
    parser.add_argument('--topology', choices=('same-host', 'direct-lan'))
    parser.add_argument('--server-ip', action='append', help='Repeat for each assigned server IPv4')
    for name in ('launcher-report', 'session', 'statistics', 'endpoint', 'server-log'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--player', action='append', nargs=2, metavar=('EXPECTED_IPV4', 'LOG'))
    args = parser.parse_args()
    json_paths = [args.launcher_report, args.session, args.statistics, args.endpoint]
    single_args = [args.topology, args.server_ip, *json_paths, args.server_log, args.player]
    if (args.venue_manifest and any(single_args)) or (not args.venue_manifest and not all(single_args)):
        parser.error('Provide --venue-manifest alone or all single-session options.')
    try:
        if args.venue_manifest:
            report = verify_venue(args.venue_manifest)
        else:
            integer(len(args.player), 1, 25)
            paths = [Path(path).resolve(strict=True) for _, path in args.player]
            inputs = [*json_paths, args.server_log, *paths]
            require(len({path.resolve(strict=True) for path in inputs}) == len(inputs), 'Evidence paths must be distinct')
            players = [(ipv4(address), content(path)) for (address, _), path in zip(args.player, paths)]
            report = verify(args.topology, {ipv4(address) for address in args.server_ip},
                            *(read_json(content(path)) for path in json_paths), content(args.server_log), players)
    except EvidenceError as error:
        parser.exit(1, f'Field evidence rejected. {error}.\n')
    except (OSError, UnicodeError, ArithmeticError, AttributeError, KeyError, TypeError, ValueError, RecursionError,
            zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError):
        parser.exit(1, 'Field evidence rejected. Check topology, original admissions, UDP peer markers, final seals and complete logs.\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
