"""Prepare an offline field manifest from the original five-room Windows launch and closure."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import zipfile
import zlib


SPEC = importlib.util.spec_from_file_location('field_results', Path(__file__).with_name('verify-field-results.py'))
field = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(field)


def path_reference(path, base):
    try:
        return os.path.relpath(path, base)
    except ValueError:  # Different Windows drives.
        return str(path)


def session_files(result, folder, session_id):
    if folder is None:
        original = result['workDirectory']
        field.require(type(original) is str and Path(original).is_absolute(),
                      'Provide --server-work-root if the original server workspace moved')
        folder = Path(original)
    files = {'serverLog': folder / 'server.log', 'worldJournal': folder / 'telemetry' / f'{session_id}.worldlog',
             'combatJournal': folder / 'telemetry' / f'{session_id}.journal'}
    for key, path in files.items():
        field.require(path.is_file(), f'Original {key} is missing for {folder.name}; check the server workspace')
    return {key: path.resolve(strict=True) for key, path in files.items()}


def check_quest_inputs(manifest, expected, evidence_path, release, sources, server_ips, windows_seats, venue_network):
    captures, endpoints, _, deployments, _, _ = field.read_venue_quest_evidence(
        manifest, manifest['mode'], expected, evidence_path, release, venue_network=venue_network)
    for source in sources.values():
        if source['rooms'] in endpoints:
            field.require_quest_capture_endpoint(source['binding'], endpoints[source['rooms']])
    captured_seats, observed_addresses = set(), set()
    for sid, rows in captures.items():
        source = sources[sid]
        port = source['binding'][1]
        for address, path, pid, seat, size, digest in rows:
            owner = source['players'].get(seat)
            field.require(owner is not None and owner.get('headset') == 'Quest3', 'Quest capture does not match a Quest 3 seat in the original roster')
            _, log, _, _ = field.quest_capture_log(address, path, pid, seat, size, digest)
            connection, result = field.quest_client_result(log, pid, port)
            field.require(result['playerId'] == owner['id'] and connection in source['acknowledged'],
                          'Quest capture lacks the original player or server acknowledgement')
            field.verify_player_terminal_result(result, owner, source['ledger'][owner['id']], source['boundary'])
            observed, _ = field.peer_address(source['peers'][connection])
            field.require(observed not in server_ips and observed not in observed_addresses
                          and any(observed in network for network in field.LAN) and (address is None or address == observed),
                          'Quest capture IPv4 differs from the original or declared direct LAN source')
            if venue_network is not None:
                field.require(observed == venue_network['seats'][seat],
                              f'Server-observed IPv4 differs from the venue network plan for room {seat[0]} seat {seat[1]}')
            captured_seats.add(seat)
            observed_addresses.add(observed)
    field.require(release is None or not captured_seats or deployments is not None,
                  'Release evidence requires original deployments for every Quest seat')
    if deployments is not None:
        field.require(not captured_seats or deployments.keys() == captured_seats, 'Quest capture and deployment reports must cover the same seats')
        for seat, (sid, player_id, admission_id, port) in deployments.items():
            source = sources.get(sid)
            owner = source['players'].get(seat) if source is not None else None
            field.require(owner is not None and owner.get('headset') == 'Quest3' and owner['id'] == player_id
                          and owner['admissionId'] == admission_id and source['binding'][1] == port,
                          'Quest deployment does not match an original Quest 3 admission and endpoint')
    quest_seats = captured_seats or set(deployments or ())
    if windows_seats is not None:
        roster_seats = set().union(*(source['players'] for source in sources.values()))
        field.require(windows_seats.isdisjoint(quest_seats) and windows_seats | quest_seats == roster_seats,
                      'Windows and Quest evidence must cover the original venue roster without overlapping seats')


def prepare(args, output):
    bundle, terminal = (path.resolve(strict=True) for path in (args.venue_bundle, args.launcher_report))
    mode = field.read_json(field.content(terminal))['topology']
    field.require(mode in ('Independent', 'Linked'), 'Invalid Windows venue launch mode')
    closure, archives, receipt_bytes = field.venue_bundle(bundle, mode)
    closure_id = field.identity(closure['requestId'])
    groups, expected = field.venue_closure_sessions(mode, closure['sessions'])
    receipts = field.read_venue_debrief_receipts(receipt_bytes, closure_id, len(expected))[0] if receipt_bytes is not None else None
    launch, results = field.read_terminal_venue_launcher(terminal, mode, expected)
    addresses = {field.ipv4(address) for address in args.server_ip}
    field.require(len(addresses) == len(args.server_ip) <= 128, 'Provide distinct server IPv4 addresses')
    work_root = args.server_work_root.resolve(strict=True) if args.server_work_root is not None else None

    def ref(path):
        return path_reference(path, output.parent)

    seen_paths = {output, bundle, terminal}

    def evidence_path(value, base=output.parent):
        path = (base / value).resolve(strict=True)
        field.require(path not in seen_paths, 'Evidence paths must be distinct across the venue')
        seen_paths.add(path)
        return path

    alignment_path = evidence_path(args.room_alignment_bundle.resolve()) if args.room_alignment_bundle is not None else None
    alignment_bundle = field.read_venue_alignment_bundle(alignment_path, mode, expected) if alignment_path is not None else None
    network_path = evidence_path(args.venue_network_plan.resolve()) if args.venue_network_plan is not None else None
    venue_network = field.read_venue_network_plan(network_path, mode, args.players_per_room) if network_path is not None else None
    entries, venue_seats = [], set()
    quest_sources = {}
    for session_id, row in sorted(expected.items(), key=lambda entry: entry[1]['roomIds']):
        rooms = row['roomIds']
        stem = 'linked' if mode == 'Linked' else f'room-{rooms[0]:02}'
        result = results[session_id]
        session, statistics, endpoint = field.management_zip_records(archives[stem + '.zip'])
        field.require_venue_launcher_source(session, launch['launchId'], session_id, row)
        stream, world, combat = result['streamId'], result['finalWorld'], result['finalCombatStream']
        boundary = field.sealed_result_boundary(session, statistics, world, combat, stream)
        applied_end = field.integer(row['appliedAtSequence'], 1, boundary['throughSequence'] - 1)
        field.require(session['state'] == 'Ended' and session['mode'] == mode and session['roomIds'] == rooms
                      and world['header']['sessionId'] == statistics['sessionId'] == session_id and world['header']['roomIds'] == rooms
                      and row['world'] == row['combat'] == 'Sealed' and row['missionName'] == session['mission']['definition']['name']
                      and field.integer(row['replay']['throughSequence'], 1) == boundary['worldSequence'],
                      f'Original management closure differs from the sealed session for {stem}')
        binding = result['udpBinding']
        address = field.ipv4(binding['address'])
        port = field.integer(binding['port'], 1024, 65535)
        field.require(endpoint['sessionEnded'] is True and endpoint['sessionId'] == session_id and endpoint['streamId'] == stream
                      and field.ipv4(endpoint['address']) == address and address in addresses
                      and field.integer(endpoint['port'], 1024, 65535) == port
                      and field.integer(binding['processId'], 1) == result['childPid'],
                      f'Original endpoint or server IPv4 inventory differs for {stem}')
        if venue_network is not None:
            field.check_venue_network_session(venue_network, session, endpoint, binding)
        if alignment_bundle is not None:
            experience = field.verify_experience(session, world['header'])
            alignments = field.venue_session_alignments(alignment_bundle, rooms, experience, endpoint)
            if alignments is not None:
                field.verify_room_alignments(session, world['header'], alignments)
        field.require(result['peerDiagnosticsEnabled'] is True, f'Original Windows launch did not record UDP peers for {stem}')
        files = session_files(result, work_root / stem if work_root is not None else None, session_id)
        peers, acknowledged, _, _ = field.server_connections(field.content(files['serverLog']), port, allow_timeout=True)
        count = args.players_per_room * len(rooms)
        owners = field.roster(session['players'], 'id', count)
        ledger = field.roster(statistics['players'], 'playerId', count)
        seats = {(field.integer(player['roomId'], 1, 5), field.integer(player['seat'], 0, 4)) for player in owners.values()}
        field.require(owners.keys() == ledger.keys() and len(seats) == count
                      and all(sum(seat[0] == room for seat in seats) == args.players_per_room for room in rooms),
                      f'Original roster differs from the declared stage for {stem}')
        if receipts is not None:
            field.verify_venue_debrief_session(receipts.get(session_id), session, stream,
                {'combatSequence': boundary['finalStreamSequence'], 'worldSequence': boundary['worldSequence'],
                 'serverAcknowledgements': len(acknowledged)})
        venue_seats.update((room, seat + 1) for room, seat in seats)
        if args.quest_capture_report or args.quest_deployment_report:
            quest_sources[session_id] = {'rooms': tuple(rooms), 'binding': (address, port), 'boundary': boundary, 'ledger': ledger,
                                         'players': {(player['roomId'], player['seat'] + 1): player for player in owners.values()},
                                         'peers': peers, 'acknowledged': acknowledged}
        field.verify_world_journal(files['worldJournal'], world, boundary['finalStreamSequence'], boundary['throughSequence'], applied_end)
        field.verify_combat_journal(files['combatJournal'], session_id, stream, boundary['origin'],
                                    boundary['finalStreamSequence'], applied_end, ledger)
        entries.append({'sessionId': session_id, **{key: ref(path) for key, path in files.items()}})
        seen_paths.update(files.values())

    manifest = {'version': 1, 'mode': mode, 'topology': args.topology, 'serverIps': args.server_ip,
                'venueBundle': ref(bundle), 'venueLauncherReport': ref(terminal), 'sessions': entries}
    if alignment_path is not None:
        manifest['roomAlignmentBundle'] = ref(alignment_path)
    if network_path is not None:
        manifest['venueNetworkPlan'] = ref(network_path)
    if args.players_per_room != 5:
        manifest['expectedPlayersPerRoom'] = args.players_per_room
    release = windows_seats = None
    if args.venue_release_report is not None:
        release_path = args.venue_release_report.resolve(strict=True)
        seen_paths.add(release_path)
        release, _ = field.read_venue_release(release_path)
        if args.windows_inbox is not None:
            digest = (release.get('windows') or {}).get('playerManifestSha256')
            field.require(type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest),
                          'Windows evidence inbox requires the original Windows release report')
        manifest['venueReleaseReport'] = ref(release_path)
    if args.windows_inbox is not None:
        inbox = args.windows_inbox.resolve(strict=True)
        field.require(inbox.is_dir(), 'Windows evidence inbox must be a directory')
        manifest['windowsEvidenceDirectory'] = ref(inbox)
    if args.windows_seat_map is not None:
        seat_map = args.windows_seat_map.resolve(strict=True)
        seats = field.read_windows_seat_map(seat_map)
        windows_seats = seats.keys()
        field.require(windows_seats <= venue_seats, 'Windows seat map names a seat outside the original batch roster')
        manifest['windowsSeatMap'] = ref(seat_map)
        seen_paths.add(seat_map)
        if args.windows_station_addresses is not None:
            addresses_path = args.windows_station_addresses.resolve(strict=True)
            station_addresses, _ = field.read_windows_station_addresses(addresses_path, seats)
            if venue_network is not None:
                field.require(all(venue_network['seats'].get(seat) == address for seat, address in station_addresses.items()),
                              'Windows station addresses disagree with the original venue network plan')
            manifest['windowsStationAddresses'] = ref(addresses_path)
            seen_paths.add(addresses_path)
    if args.udp_preflight_batch:
        paths = [path.resolve(strict=True) for path in args.udp_preflight_batch]
        field.require(len(paths) == len(set(paths)) <= 25, 'Provide up to 25 distinct original UDP preflight batches')
        sessions = {tuple(row['roomIds']): session_id for session_id, row in expected.items()}
        for path in paths:
            field.read_udp_preflight_batch(path, mode, groups, expected_sessions=sessions,
                                           venue_plan_hash=venue_network['sha256'] if venue_network else None)
        seen_paths.update(paths)
        if len(paths) == 1:
            manifest['udpPreflightBatch'] = ref(paths[0])
        else:
            manifest['udpPreflightBatches'] = [ref(path) for path in paths]
    if args.quest_capture_report:
        captures = {'reports': [ref(path.resolve(strict=True)) for path in args.quest_capture_report]}
        if args.quest_network_plan is not None:
            captures['networkPlan'] = ref(args.quest_network_plan.resolve(strict=True))
        if args.quest_device_map is not None:
            captures['deviceMap'] = ref(args.quest_device_map.resolve(strict=True))
        manifest['questCaptures'] = captures
    if args.quest_deployment_report:
        manifest['questDeployments'] = {'reports': [ref(path.resolve(strict=True)) for path in args.quest_deployment_report]}
    if args.quest_readiness_report:
        manifest['questReadinessReports'] = [ref(path.resolve(strict=True)) for path in args.quest_readiness_report]
    if quest_sources:
        check_quest_inputs(manifest, expected, evidence_path, release, quest_sources, addresses, windows_seats, venue_network)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venue-bundle', required=True, type=Path, help='Original full management closure ZIP')
    parser.add_argument('--launcher-report', required=True, type=Path, help='Original Windows batch terminal report')
    parser.add_argument('--output', required=True, type=Path, help='New venue manifest JSON')
    parser.add_argument('--topology', choices=('same-host', 'direct-lan'), required=True)
    parser.add_argument('--server-ip', action='append', required=True, help='Repeat for every assigned server IPv4')
    parser.add_argument('--server-work-root', type=Path, help='Moved batch workspace with the original room-01 through room-05 or linked folders')
    parser.add_argument('--players-per-room', type=int, choices=range(1, 6), default=5)
    parser.add_argument('--venue-release-report', type=Path)
    parser.add_argument('--windows-inbox', type=Path)
    parser.add_argument('--windows-seat-map', type=Path)
    parser.add_argument('--windows-station-addresses', type=Path)
    parser.add_argument('--venue-network-plan', type=Path, help='Original whole-venue network plan with all seat IPv4 assignments')
    parser.add_argument('--udp-preflight-batch', action='append', type=Path)
    parser.add_argument('--room-alignment-bundle', type=Path, help='Original MR or mixed venue deployment ZIP')
    parser.add_argument('--quest-capture-report', action='append', type=Path, help='Original batch logcat capture report; repeat for separate batches')
    parser.add_argument('--quest-network-plan', type=Path, help='Original Quest IPv4 plan')
    parser.add_argument('--quest-device-map', type=Path, help='Original Quest seat-to-ADB assignment')
    parser.add_argument('--quest-deployment-report', action='append', type=Path, help='Original Quest deployment report; repeat for separate batches')
    parser.add_argument('--quest-readiness-report', action='append', type=Path, help='Original pre-Begin Quest tracked sample; repeat for separate batches')
    args = parser.parse_args()
    if args.windows_inbox is not None and args.venue_release_report is None:
        parser.error('--windows-inbox requires --venue-release-report')
    if args.windows_seat_map is not None and args.windows_inbox is None:
        parser.error('--windows-seat-map requires --windows-inbox')
    if args.windows_station_addresses is not None and args.windows_seat_map is None:
        parser.error('--windows-station-addresses requires --windows-seat-map')
    if bool(args.quest_capture_report) != bool(args.quest_network_plan or args.quest_device_map):
        parser.error('Quest captures require reports and --quest-network-plan, --quest-device-map or both')
    if args.quest_deployment_report and args.venue_release_report is None:
        parser.error('--quest-deployment-report requires --venue-release-report')
    if args.quest_readiness_report and not args.quest_deployment_report:
        parser.error('--quest-readiness-report requires --quest-deployment-report')
    if (args.quest_capture_report or args.quest_deployment_report) and args.windows_inbox is not None and args.windows_seat_map is None:
        parser.error('Using Quest reports and --windows-inbox together requires --windows-seat-map')
    try:
        output = args.output.resolve()
        field.require(not output.exists(), 'Use a new output file')
        manifest = prepare(args, output)
        serialized = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
        with output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(serialized)
    except field.EvidenceError as error:
        parser.exit(1, f'Venue manifest could not be prepared. {error}.\n')
    except (OSError, UnicodeError, ArithmeticError, AttributeError, KeyError, TypeError, ValueError,
            RecursionError, zipfile.BadZipFile, zlib.error, RuntimeError):
        parser.exit(1, 'Venue manifest could not be prepared. Check the original closure, terminal report and workspace.\n')
    print(json.dumps({'prepared': True, 'mode': manifest['mode'], 'sessions': len(manifest['sessions'])}))


if __name__ == '__main__':
    main()
