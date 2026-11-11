"""Check collected Windows and Quest UDP report pairs against a five-room launch plan."""

import argparse
import codecs
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path


SPEC = importlib.util.spec_from_file_location('field_results', Path(__file__).with_name('verify-field-results.py'))
field = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(field)


def probe_identity(path):
    with path.open('rb') as stream:
        raw = stream.read(32769)
    field.require(1 <= len(raw) <= 32768, 'Invalid UDP report size')
    encoding = 'utf-16' if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else 'utf-8-sig'
    row = field.read_json(raw.decode(encoding))
    field.require(type(row) is dict, 'Expected a UDP probe report object')
    return (field.quest_network_address(row['peerAddress']), field.integer(row['port'], 1024, 65535),
            field.quest_network_address(row['localAddress']))


def path_reference(path, directory):
    try:
        return os.path.relpath(path, directory)
    except ValueError:  # Different Windows drives.
        return str(path)


def load_pairs(pairs_path, batch_paths, mode, rooms):
    pairs = []
    if pairs_path:
        manifest = field.read_quest_plan_file(pairs_path)
        field.require(set(manifest) == {'version', 'pairs'} and type(manifest['pairs']) is list,
                      'Expected a version 1 list of report pairs')
        pairs.extend((row, pairs_path.parent, None) for row in manifest['pairs'])
    for path in batch_paths:
        for group, rows in field.read_udp_preflight_batch(path, mode, rooms).items():
            pairs.extend((row, base, group) for row, base in rows)
    field.require(len(pairs) <= 50, 'Too many UDP preflight reports')
    return pairs


def check_launcher_preview(path, mode, endpoints):
    with path.open('rb') as stream:
        raw = stream.read(field.MAX_QUEST_PLAN_BYTES + 1)
    field.require(len(raw) <= field.MAX_QUEST_PLAN_BYTES, 'Launcher preview is too large')
    preview = field.read_json(raw.decode('utf-8-sig'))
    field.require(type(preview) is dict and field.integer(preview['schemaVersion'], 1, 1) == 1
                  and preview['status'] == 'venue-checked' and preview['complete'] is True,
                  'Provide the original successful Windows launcher preview')
    topology, servers = preview['topology'], preview['servers']
    field.require(topology in ('Independent', 'Linked'), 'Invalid launcher topology')
    rooms = {field.QUEST_ROOMS} if topology == 'Linked' else {(room,) for room in field.QUEST_ROOMS}
    field.require(type(servers) is list and len(servers) == len(rooms), 'Incomplete launcher preview')
    bindings, sessions = {}, set()
    for row in servers:
        field.require(type(row) is dict and type(row['sessionId']) is str and type(row['roomIds']) is list
                      and all(type(room) is int for room in row['roomIds']), 'Invalid launcher room group')
        group = tuple(row['roomIds'])
        session = field.identity(row['sessionId'])
        field.require(group in rooms and group not in bindings and session not in sessions, 'Repeated launcher room or session')
        address = field.quest_network_address(row['address'])
        listen = row['listenAddress']
        if listen != '0.0.0.0':
            listen = field.quest_network_address(listen)
        bindings[group] = address, listen, field.integer(row['port'], 1024, 65535)
        sessions.add(session)
    field.require(len({port for _, _, port in bindings.values()}) == len(bindings), 'Repeated launcher port')

    groups = []
    for group in sorted(endpoints.keys() | bindings.keys()):
        if group not in bindings:
            issues = ['missing-launch-endpoint']
        elif group not in endpoints:
            issues = ['unexpected-launch-endpoint']
        else:
            address, port = endpoints[group]
            advertised, listen, launch_port = bindings[group]
            issues = [name for matches, name in (
                (port == launch_port, 'port-mismatch'),
                (address == advertised, 'advertised-address-mismatch'),
                (address == listen, 'listen-address-mismatch'),
            ) if not matches]
        groups.append({'roomIds': list(group), 'issues': issues})
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'complete': topology == mode and not any(row['issues'] for row in groups),
            'topologyMatches': topology == mode, 'groups': groups}


def check_venue(plan, pairs_path, batch_paths, output, launcher_preview=None):
    mode, endpoints, sources = field.read_quest_network_plan(plan, allow_shared_sources=True)
    field.require({room for room, _ in sources} == set(field.QUEST_ROOMS), 'Plan a source for every room')
    launch_check = check_launcher_preview(launcher_preview, mode, endpoints) if launcher_preview else None
    rooms = sorted(endpoints)
    room_groups = {room: group for group in rooms for room in group}
    expected = defaultdict(list)
    for (room, seat), peer in sorted(sources.items()):
        group = room_groups[room]
        expected[(*endpoints[group], peer)].append((room, seat))
    address_modes = {field.ipv4(address).is_loopback for server, _, peer in expected for address in (server, peer)}
    field.require(len(address_modes) == 1, 'Use only loopback or only private LAN addresses in one plan')

    observed = defaultdict(list)
    path_counts = Counter()
    unmatched = unreadable = 0
    for pair, base, declared_group in load_pairs(pairs_path, batch_paths, mode, [list(group) for group in rooms]):
        try:
            field.require(type(pair) is dict and set(pair) == {'listener', 'probe'}
                          and all(type(value) is str and value for value in pair.values()), 'Invalid UDP report paths')
            paths = tuple((base / pair[key]).resolve(strict=True) for key in ('listener', 'probe'))
            address = probe_identity(paths[1])
        except (OSError, ValueError, KeyError, RecursionError):
            unreadable += 1
            continue
        if address not in expected or (declared_group is not None and
                                      declared_group != room_groups[expected[address][0][0]]):
            unmatched += 1
            continue
        observed[address].append(paths)
        path_counts.update(paths)

    checked_at = datetime.now(timezone.utc).isoformat()
    results, exchange_counts = {}, Counter()
    for address, seats in expected.items():
        row = results[address] = {'seats': seats, 'status': 'missing'}
        choices = observed[address]
        if not choices:
            continue
        if len(choices) != 1 or any(path_counts[path] != 1 for path in choices[0]):
            row['status'] = 'duplicate-pair'
            continue
        server, port, peer = address
        try:
            summary, _ = field.verify_udp_preflight(choices[0],
                {'address': server, 'port': port, 'observedAtUtc': checked_at}, {field.ipv4(peer)})
        except (OSError, ValueError, KeyError, RecursionError):
            row['status'] = 'invalid-or-expired'
            continue
        row.update(status='verified', summary=summary, paths=choices[0])
        exchange_counts[summary['exchangeSha256']] += 1

    groups = []
    for group in rooms:
        bindings = [row for row in results.values() if room_groups[row['seats'][0][0]] == group]
        for row in bindings:
            if row['status'] == 'verified' and exchange_counts[row['summary']['exchangeSha256']] > 1:
                row['status'] = 'duplicate-exchange'
        complete = all(row['status'] == 'verified' for row in bindings)
        entries = [{'seats': [{'roomId': room, 'seat': seat} for room, seat in row['seats']], 'status': row['status']}
                   for row in bindings]
        result = {'roomIds': list(group), 'complete': complete, 'sources': entries}
        if complete:
            result['udpSourcePreflights'] = [dict(zip(('listener', 'probe'),
                (path_reference(path, output.parent) for path in row['paths']), strict=True)) for row in bindings]
        groups.append(result)

    complete = (not (unmatched or unreadable) and all(group['complete'] for group in groups)
                and (launch_check is None or launch_check['complete']))
    return {'version': 1, 'scope': 'venue-udp-preflight-only', 'mode': mode,
            'network': 'same-host' if True in address_modes else 'private-lan-plan',
            'complete': complete,
            'checkedAtUtc': checked_at, 'expectedSources': len(expected),
            'verifiedSources': sum(row['status'] == 'verified' for row in results.values()),
            'unmatchedPairs': unmatched, 'unreadablePairs': unreadable, 'groups': groups,
            **({'launcherPreview': launch_check} if launch_check is not None else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network-plan', required=True, type=Path)
    parser.add_argument('--pairs', type=Path, help='Version 1 JSON list of original listener and probe report paths')
    parser.add_argument('--batch', type=Path, action='append', default=[], help='Original completed UDP batch report')
    parser.add_argument('--launcher-preview', type=Path, help='Original successful Launch-Server.exe --venue-check report')
    parser.add_argument('--output', required=True, type=Path, help='New readiness report (also usable for sealed verification)')
    args = parser.parse_args()
    if len(args.batch) > 25:
        parser.error('At most 25 existing batch reports are supported.')
    try:
        field.require(not args.output.exists(), 'Use a new output file')
        result = check_venue(args.network_plan, args.pairs, args.batch, args.output.resolve(), args.launcher_preview)
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        parser.exit(1, 'UDP venue preflight could not read its inputs or save the report. Check the plan, launcher preview and output path.\n')
    summary = {key: result[key] for key in ('complete', 'expectedSources', 'verifiedSources', 'unmatchedPairs', 'unreadablePairs')}
    if 'launcherPreview' in result:
        summary['launcherPreviewMatches'] = result['launcherPreview']['complete']
    print(json.dumps(summary))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
