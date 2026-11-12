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


def load_pairs(pairs_path, batch_paths, mode, rooms, binding):
    pairs = []
    if pairs_path:
        manifest = field.read_quest_plan_file(pairs_path)
        field.require(set(manifest) == {'version', 'pairs'} and type(manifest['pairs']) is list,
                      'Expected a version 1 list of report pairs')
        pairs.extend((row, pairs_path.parent, None) for row in manifest['pairs'])
    for path in batch_paths:
        sources, launch = field.read_udp_preflight_batch(path, mode, rooms)
        if launch is not None:
            field.require(binding is not None and all(binding[key] == launch[0][key] for key in ('planSha256', 'previewSha256')),
                          'Reuse the original Windows plan and preview when including a bound UDP report')
        for group, rows in sources.items():
            pairs.extend((row, base, group) for row, base in rows)
    field.require(len(pairs) <= 50, 'Too many UDP preflight reports')
    return pairs


def check_venue(plan, pairs_path, batch_paths, output, launcher_preview=None, launch_plan=None):
    document, raw = field.read_quest_document(plan)
    mode, endpoints, sources = field.parse_quest_network_plan(document, allow_shared_sources=True)
    plan_hash = hashlib.sha256(raw).hexdigest()
    field.require({room for room, _ in sources} == set(field.QUEST_ROOMS), 'Plan a source for every room')
    field.require(launch_plan is None or launcher_preview is not None, 'A launch plan requires its original launcher preview')
    preview = field.read_udp_launcher_document(launcher_preview, preview=True) if launcher_preview else None
    launch_check = field.check_udp_launcher_endpoints(preview, mode, endpoints) if preview else None
    binding = None
    if launch_plan:
        planned = field.read_udp_launcher_document(launch_plan, preview=False)
        binding = {'plan': path_reference(launch_plan.resolve(), output.parent),
                   'preview': path_reference(launcher_preview.resolve(), output.parent),
                   **field.compare_udp_launch_documents(planned, preview)}
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
    for pair, base, declared_group in load_pairs(pairs_path, batch_paths, mode, [list(group) for group in rooms], binding):
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
                and (launch_check is None or launch_check['complete']) and (binding is None or binding['complete']))
    return {'version': 1, 'scope': 'venue-udp-preflight-only', 'mode': mode,
            'networkPlanSha256': plan_hash,
            'network': 'same-host' if True in address_modes else 'private-lan-plan',
            'complete': complete,
            'checkedAtUtc': checked_at, 'expectedSources': len(expected),
            'verifiedSources': sum(row['status'] == 'verified' for row in results.values()),
            'unmatchedPairs': unmatched, 'unreadablePairs': unreadable, 'groups': groups,
            **({'launcherPreview': launch_check} if launch_check is not None else {}),
            **({'launchBinding': binding} if binding is not None else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network-plan', required=True, type=Path)
    parser.add_argument('--pairs', type=Path, help='Version 1 JSON list of original listener and probe report paths')
    parser.add_argument('--batch', type=Path, action='append', default=[], help='Original completed UDP batch report')
    parser.add_argument('--launcher-preview', type=Path, help='Original successful Launch-Server.exe --venue-check report')
    parser.add_argument('--launch-plan', type=Path, help='Original revision-guarded Windows launch plan for the provided preview')
    parser.add_argument('--output', required=True, type=Path, help='New readiness report (also usable for sealed verification)')
    args = parser.parse_args()
    if len(args.batch) > 25:
        parser.error('At most 25 existing batch reports are supported.')
    try:
        field.require(not args.output.exists(), 'Use a new output file')
        result = check_venue(args.network_plan, args.pairs, args.batch, args.output.resolve(), args.launcher_preview, args.launch_plan)
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        parser.exit(1, 'UDP venue preflight could not read its inputs or save the report. Check the plan, launcher preview and output path.\n')
    summary = {key: result[key] for key in ('complete', 'expectedSources', 'verifiedSources', 'unmatchedPairs', 'unreadablePairs')}
    if 'launcherPreview' in result:
        summary['launcherPreviewMatches'] = result['launcherPreview']['complete']
    if 'launchBinding' in result:
        summary['launchPlanMatches'] = result['launchBinding']['complete']
    print(json.dumps(summary))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
