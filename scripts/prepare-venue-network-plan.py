"""Prepare a five-room UDP network plan from the original Windows launch plan and preview."""

import argparse
import importlib.util
import json
from pathlib import Path


SPEC = importlib.util.spec_from_file_location('field_results', Path(__file__).with_name('verify-field-results.py'))
field = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(field)


def prepare(launch_path, preview_path, seat_path, players_per_room, device_path=None, *, require_distinct_remote_roster=False,
            server_ips=None):
    launch = field.read_udp_launcher_document(launch_path, preview=False)
    preview = field.read_udp_launcher_document(preview_path, preview=True)
    checked = field.compare_udp_launch_documents(launch, preview)
    field.require(checked['mode'] == preview[1], 'The launch plan and preview use different venue modes')
    for group in checked['groups']:
        field.require(not group['issues'], 'Room(s) ' + ', '.join(map(str, group['roomIds']))
                      + ' differ between the launch plan and preview (' + ', '.join(group['issues']) + ')')

    endpoints = []
    for rooms, row in sorted(launch[2].items()):
        field.require(row['address'] == row['listenAddress'],
                      'Room(s) ' + ', '.join(map(str, rooms)) + ' require one concrete advertised and listening IPv4 address')
        endpoints.append({'roomIds': list(rooms), 'address': row['address'], 'port': row['port']})

    inventory = field.read_quest_plan_file(seat_path)
    field.require(set(inventory) == {'version', 'seats'}, 'Expected a version 1 seat address inventory')
    seats = {seat: field.quest_network_address(address) for seat, address in field.quest_seats(inventory['seats'], 'address').items()}
    field.check_udp_launcher_seats(preview, seats)
    incomplete = [room for room in field.QUEST_ROOMS if sum(seat[0] == room for seat in seats) != players_per_room]
    field.require(not incomplete, 'Seat count differs from the requested stage in room(s) ' + ', '.join(map(str, incomplete)))
    addresses = {row['address'] for row in endpoints} | set(seats.values())
    field.require(len({field.ipv4(address).is_loopback for address in addresses}) == 1,
                  'Use only loopback or only private LAN addresses in one plan')
    if server_ips is not None:
        server_ips = field.read_network_server_ips(server_ips)
        field.require({row['address'] for row in endpoints} <= set(server_ips), 'Server IPv4 inventory must include every advertised endpoint')
    if require_distinct_remote_roster or server_ips is not None:
        field.require_distinct_remote_sources(seats, ((row['address'], row['port']) for row in endpoints), server_ips or ())

    included = seats
    if device_path is not None:
        devices = field.read_quest_device_map(device_path)
        missing = sorted(devices.keys() - seats.keys())
        field.require(not missing, 'Mapped Quest seats are missing from the inventory: '
                      + ', '.join(f'room {room} seat {seat}' for room, seat in missing))
        included = {seat: seats[seat] for seat in devices}
        field.require(len(set(included.values())) == len(included), 'Use a distinct IPv4 for each mapped Quest')

    network = {'version': 1, 'mode': checked['mode'], 'endpoints': endpoints,
               'sources': [{'roomId': room, 'seat': seat, 'address': address} for (room, seat), address in sorted(included.items())]}
    if server_ips is not None:
        network['serverIps'] = server_ips
    summary = {'prepared': True, 'mode': checked['mode'], 'plannedSeats': len(seats), 'includedSeats': len(included),
               'endpointCount': len(endpoints), 'planSha256': checked['planSha256'], 'previewSha256': checked['previewSha256']}
    return network, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch-plan', required=True, type=Path)
    parser.add_argument('--launcher-preview', required=True, type=Path)
    parser.add_argument('--seat-addresses', required=True, type=Path, help='Version 1 inventory of the planned seats and their IPv4 addresses')
    parser.add_argument('--players-per-room', type=int, choices=range(1, 6), default=5)
    parser.add_argument('--quest-device-map', type=Path, help='Include only these Quest seats in the generated plan')
    parser.add_argument('--require-distinct-remote-roster', action='store_true',
                        help='Require each planned seat to have its own private IPv4 outside the server endpoints')
    parser.add_argument('--server-ip', action='append', help='Repeat for each server IPv4, including all advertised endpoints; requires distinct remote seats')
    parser.add_argument('--output', required=True, type=Path, help='New version 1 network plan JSON')
    args = parser.parse_args()
    try:
        field.require(not args.output.exists(), 'Use a new output file')
        plan, summary = prepare(args.launch_plan, args.launcher_preview, args.seat_addresses, args.players_per_room,
                                args.quest_device_map, require_distinct_remote_roster=args.require_distinct_remote_roster,
                                server_ips=args.server_ip)
        payload = json.dumps(plan, indent=2) + '\n'
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(payload)
    except field.EvidenceError as error:
        parser.exit(1, f'Venue network plan rejected. {error}.\n')
    except (OSError, ValueError, AttributeError, KeyError, TypeError, RecursionError):
        parser.exit(1, 'Could not prepare the venue network plan. Check the original launch plan, preview and seat inventory.\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
