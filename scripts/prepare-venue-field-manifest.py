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


def prepare(args, output):
    bundle, terminal = (path.resolve(strict=True) for path in (args.venue_bundle, args.launcher_report))
    mode = field.read_json(field.content(terminal))['topology']
    field.require(mode in ('Independent', 'Linked'), 'Invalid Windows venue launch mode')
    closure, archives = field.venue_bundle(bundle, mode)
    field.identity(closure['requestId'])
    groups, expected = field.venue_closure_sessions(mode, closure['sessions'])
    launch, results = field.read_terminal_venue_launcher(terminal, mode, expected)
    addresses = {field.ipv4(address) for address in args.server_ip}
    field.require(len(addresses) == len(args.server_ip) <= 128, 'Provide distinct server IPv4 addresses')
    work_root = args.server_work_root.resolve(strict=True) if args.server_work_root is not None else None

    def ref(path):
        return path_reference(path, output.parent)

    entries, venue_seats = [], set()
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
        field.require(result['peerDiagnosticsEnabled'] is True, f'Original Windows launch did not record UDP peers for {stem}')
        files = session_files(result, work_root / stem if work_root is not None else None, session_id)
        field.server_connections(field.content(files['serverLog']), port, allow_timeout=True)
        count = args.players_per_room * len(rooms)
        owners = field.roster(session['players'], 'id', count)
        ledger = field.roster(statistics['players'], 'playerId', count)
        seats = {(field.integer(player['roomId'], 1, 5), field.integer(player['seat'], 0, 4)) for player in owners.values()}
        field.require(owners.keys() == ledger.keys() and len(seats) == count
                      and all(sum(seat[0] == room for seat in seats) == args.players_per_room for room in rooms),
                      f'Original roster differs from the declared stage for {stem}')
        venue_seats.update((room, seat + 1) for room, seat in seats)
        field.verify_world_journal(files['worldJournal'], world, boundary['finalStreamSequence'], boundary['throughSequence'], applied_end)
        field.verify_combat_journal(files['combatJournal'], session_id, stream, boundary['origin'],
                                    boundary['finalStreamSequence'], applied_end, ledger)
        entries.append({'sessionId': session_id, **{key: ref(path) for key, path in files.items()}})

    manifest = {'version': 1, 'mode': mode, 'topology': args.topology, 'serverIps': args.server_ip,
                'venueBundle': ref(bundle), 'venueLauncherReport': ref(terminal), 'sessions': entries}
    if args.players_per_room != 5:
        manifest['expectedPlayersPerRoom'] = args.players_per_room
    if args.venue_release_report is not None:
        release_path = args.venue_release_report.resolve(strict=True)
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
        field.require(seats.keys() <= venue_seats, 'Windows seat map names a seat outside the original batch roster')
        manifest['windowsSeatMap'] = ref(seat_map)
        if args.windows_station_addresses is not None:
            addresses_path = args.windows_station_addresses.resolve(strict=True)
            field.read_windows_station_addresses(addresses_path, seats)
            manifest['windowsStationAddresses'] = ref(addresses_path)
    if args.udp_preflight_batch:
        paths = [path.resolve(strict=True) for path in args.udp_preflight_batch]
        field.require(len(paths) == len(set(paths)) <= 25, 'Provide up to 25 distinct original UDP preflight batches')
        sessions = {tuple(row['roomIds']): session_id for session_id, row in expected.items()}
        for path in paths:
            field.read_udp_preflight_batch(path, mode, groups, expected_sessions=sessions)
        if len(paths) == 1:
            manifest['udpPreflightBatch'] = ref(paths[0])
        else:
            manifest['udpPreflightBatches'] = [ref(path) for path in paths]
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
    parser.add_argument('--udp-preflight-batch', action='append', type=Path)
    args = parser.parse_args()
    if args.windows_inbox is not None and args.venue_release_report is None:
        parser.error('--windows-inbox requires --venue-release-report')
    if args.windows_seat_map is not None and args.windows_inbox is None:
        parser.error('--windows-seat-map requires --windows-inbox')
    if args.windows_station_addresses is not None and args.windows_seat_map is None:
        parser.error('--windows-station-addresses requires --windows-seat-map')
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
