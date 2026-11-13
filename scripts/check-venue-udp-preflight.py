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
import re


SPEC = importlib.util.spec_from_file_location('field_results', Path(__file__).with_name('verify-field-results.py'))
field = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(field)


def read_report_lines(path):
    with path.open('rb') as stream:
        raw = stream.read(32769)
    field.require(1 <= len(raw) <= 32768, 'Invalid UDP report size')
    encoding = 'utf-16' if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else 'utf-8-sig'
    return raw.decode(encoding).strip().splitlines()


def report_address(row, mode):
    local = field.quest_network_address(row['localAddress'])
    peer = field.quest_network_address(row['peerAddress'])
    server, player = (local, peer) if mode == 'listen' else (peer, local)
    return server, field.integer(row['port'], 1024, 65535), player


def probe_identity(path):
    lines = read_report_lines(path)
    field.require(len(lines) == 1, 'Expected a single UDP probe report')
    row = field.read_json(lines[0])
    field.require(type(row) is dict, 'Expected a UDP probe report object')
    return report_address(row, 'probe')


def load_inbox(directory):
    files = []
    for path in directory.iterdir():
        if path.suffix.lower() in ('.json', '.ndjson') and path.is_file():
            files.append(path)
            field.require(len(files) <= 100, 'Too many UDP reports in the inbox')
    exchanges, issues = defaultdict(list), []
    for path in sorted(files):
        try:
            lines = read_report_lines(path)
            field.require(1 <= len(lines) <= 2, 'Invalid UDP inbox report lines')
            row = field.read_json(lines[-1])
            mode, digest = row['mode'], row['exchangeSha256']
            field.require(type(row['version']) is int and row['version'] == 1
                          and row['scope'] == 'authenticated-udp-only' and row['stage'] == 'finished'
                          and row['complete'] is True and mode in ('listen', 'probe')
                          and (len(lines) == 1 or mode == 'listen')
                          and type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'Invalid completed UDP inbox report')
            exchanges[(*report_address(row, mode), digest)].append((mode, path.name))
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            issues.append({'status': 'invalid-report', 'files': [path.name]})

    pairs = []
    for entries in exchanges.values():
        roles = dict(entries)
        if len(roles) == len(entries) == 2:
            pairs.append(({'listener': roles['listen'], 'probe': roles['probe']}, directory, None))
        else:
            status = 'duplicate-role' if len(roles) < len(entries) else 'missing-counterpart'
            issues.append({'status': status, 'files': [name for _, name in entries]})
    return pairs, {'files': len(files), 'pairedExchanges': len(pairs), 'issues': issues}


def path_reference(path, directory):
    try:
        return os.path.relpath(path, directory)
    except ValueError:  # Different Windows drives.
        return str(path)


def load_pairs(pairs_path, batch_paths, mode, rooms, binding, plan_hash):
    pairs = []
    distinct = False
    if pairs_path:
        manifest = field.read_quest_plan_file(pairs_path)
        field.require(set(manifest) == {'version', 'pairs'} and type(manifest['pairs']) is list,
                      'Expected a version 1 list of report pairs')
        pairs.extend((row, pairs_path.parent, None) for row in manifest['pairs'])
    for path in batch_paths:
        report = field.read_json(field.content(path))
        batch_distinct = field.udp_preflight_distinct_roster(report)
        if batch_distinct:
            field.require(report.get('networkPlanSha256') == plan_hash,
                          'Reuse the original venue network plan when including a distinct-roster UDP report')
        distinct |= batch_distinct
        sources, launch = field.udp_preflight_batch(report, path, mode, rooms)
        if launch is not None:
            field.require(binding is not None and all(binding[key] == launch[0][key] for key in ('planSha256', 'previewSha256')),
                          'Reuse the original Windows plan and preview when including a bound UDP report')
        for group, rows in sources.items():
            pairs.extend((row, base, group) for row, base in rows)
    field.require(len(pairs) <= 50, 'Too many UDP preflight reports')
    return pairs, distinct


def read_pair(pair, base):
    field.require(type(pair) is dict and set(pair) == {'listener', 'probe'}
                  and all(type(value) is str and value for value in pair.values()), 'Invalid UDP report paths')
    return tuple((base / pair[key]).resolve(strict=True) for key in ('listener', 'probe'))


def pair_reference(paths, directory):
    return dict(zip(('listener', 'probe'), (path_reference(path, directory) for path in paths), strict=True))


def verify_source(address, paths, checked_at, hashes=None):
    server, port, peer = address
    before = pair_hashes(paths) if hashes is None else hashes
    summary, _ = field.verify_udp_preflight(paths, {'address': server, 'port': port, 'observedAtUtc': checked_at}, {field.ipv4(peer)})
    field.require(pair_hashes(paths) == before, 'UDP pair files changed during verification')
    return summary, before


def pair_hashes(paths):
    hashes = []
    for path in paths:
        with path.open('rb') as stream:
            raw = stream.read(32769)
        field.require(1 <= len(raw) <= 32768, 'Invalid UDP report size')
        hashes.append(hashlib.sha256(raw).hexdigest())
    return hashes


def read_retry(path, mode, plan_hash):
    with path.open('rb') as stream:
        raw = stream.read(128 * 1024 + 1)
    field.require(len(raw) <= 128 * 1024, 'Retry report exceeds its size limit')
    report = field.read_json(raw.decode('utf-8-sig'))
    field.require(type(report) is dict and field.integer(report['version'], 1, 1)
                  and report.get('scope') == 'venue-udp-preflight-only' and report.get('complete') is False
                  and report.get('mode') == mode and report.get('networkPlanSha256') == plan_hash,
                  'Use an incomplete report for the same original venue network plan')
    return report, hashlib.sha256(raw).hexdigest()


def retained_sources(path, report, mode, expected, launch_check, binding, checked_at):
    prior = field.read_udp_launch_binding(report, path.parent, mode)
    field.require(report.get('launcherPreview') == launch_check and (prior is None) == (binding is None)
                  and (prior is None or all(prior[0][key] == binding[key] for key in ('planSha256', 'previewSha256'))),
                  'Retry requires the same original Windows plan and preview')
    rows = report.get('retrySources')
    field.require(type(rows) is list and 0 <= len(rows) <= len(expected), 'Retry report lacks its original verified sources')
    by_seats = {tuple(seats): address for address, seats in expected.items()}
    valid, seen, previous_pairs = {}, set(), set()
    for row in rows:
        field.require(type(row) is dict and set(row) == {'seats', 'pair', 'exchangeSha256', 'pairSha256'},
                      'Invalid verified source in retry report')
        seats = row['seats']
        field.require(type(seats) is list and 1 <= len(seats) <= 25 and all(
            type(seat) is dict and set(seat) == {'roomId', 'seat'} for seat in seats), 'Invalid seats in retry report')
        key = tuple(sorted((field.integer(seat['roomId'], 1, 5), field.integer(seat['seat'], 1, 5)) for seat in seats))
        address = by_seats.get(key)
        field.require(address is not None and address not in seen, 'Retry report source differs from the original planned seats')
        seen.add(address)
        try:
            paths = read_pair(row['pair'], path.parent)
            previous_pairs.add(paths)
            field.require(probe_identity(paths[1]) == address, 'Retry reports name a different UDP source')
            hashes = pair_hashes(paths)
            field.require(hashes == row['pairSha256'], 'Retry pair differs from its original files')
            summary, _ = verify_source(address, paths, checked_at, hashes)
            field.require(summary['exchangeSha256'] == row['exchangeSha256'], 'Retry exchange differs from the original pair')
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            continue
        valid[address] = paths, summary, hashes
    return valid, seen - valid.keys(), previous_pairs


def check_venue(plan, pairs_path, batch_paths, output, launcher_preview=None, launch_plan=None, retry_report=None, inbox=None,
                *, require_distinct_remote_roster=False):
    document, raw = field.read_quest_document(plan)
    mode, endpoints, sources = field.parse_quest_network_plan(document, allow_shared_sources=True)
    inventory_checked = 'serverIps' in document
    require_distinct_remote_roster |= inventory_checked
    plan_hash = hashlib.sha256(raw).hexdigest()
    field.require({room for room, _ in sources} == set(field.QUEST_ROOMS), 'Plan a source for every room')
    field.require(launch_plan is None or launcher_preview is not None, 'A launch plan requires its original launcher preview')
    preview = field.read_udp_launcher_document(launcher_preview, preview=True) if launcher_preview else None
    if preview:
        field.check_udp_launcher_seats(preview, sources)
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

    checked_at = datetime.now(timezone.utc).isoformat()
    launch_matches = (launch_check is None or launch_check['complete']) and (binding is None or binding['complete'])
    prior = None
    if retry_report is not None:
        field.require(launch_matches, 'Retry requires the original matching Windows plan and preview')
        prior, prior_hash = read_retry(retry_report, mode, plan_hash)
        require_distinct_remote_roster |= field.udp_preflight_distinct_roster(prior)
    if require_distinct_remote_roster and not inventory_checked:
        field.require_distinct_remote_sources(sources, endpoints.values())
    pairs, batch_distinct = load_pairs(pairs_path, batch_paths, mode, [list(group) for group in rooms], binding, plan_hash)
    if batch_distinct and not require_distinct_remote_roster:
        field.require_distinct_remote_sources(sources, endpoints.values())
        require_distinct_remote_roster = True
    if prior is not None:
        retained, expired, previous_pairs = retained_sources(retry_report, prior, mode, expected, launch_check, binding, checked_at)
    else:
        retained, expired, previous_pairs, prior_hash = {}, set(), set(), None
    observed = defaultdict(list)
    path_counts = Counter()
    for address, (paths, _, _) in retained.items():
        observed[address].append(paths)
        path_counts.update(paths)
    unmatched = unreadable = 0
    inbox_summary = None
    if inbox is not None:
        inbox_pairs, inbox_summary = load_inbox(inbox)
    else:
        inbox_pairs = []
    field.require(len(pairs) + len(inbox_pairs) <= 50, 'Too many UDP preflight reports')
    for index, (pair, base, declared_group) in enumerate(pairs + inbox_pairs):
        try:
            paths = read_pair(pair, base)
            # The retry already checked these original paths and their stored hashes.
            if index >= len(pairs) and paths in previous_pairs:
                continue
            address = probe_identity(paths[1])
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            unreadable += 1
            continue
        if address not in expected or (declared_group is not None and
                                      declared_group != room_groups[expected[address][0][0]]):
            unmatched += 1
            continue
        observed[address].append(paths)
        path_counts.update(paths)

    results, exchange_counts = {}, Counter()
    for address, seats in expected.items():
        row = results[address] = {'seats': seats, 'status': 'missing'}
        choices = observed[address]
        if not choices:
            if address in expired:
                row['status'] = 'invalid-or-expired'
            continue
        if len(choices) != 1 or any(path_counts[path] != 1 for path in choices[0]):
            row['status'] = 'duplicate-pair'
            continue
        try:
            summary, hashes = retained[address][1:] if address in retained else verify_source(address, choices[0], checked_at)
        except (OSError, ValueError, KeyError, RecursionError):
            row['status'] = 'invalid-or-expired'
            continue
        row.update(status='verified', summary=summary, paths=choices[0], hashes=hashes)
        exchange_counts[summary['exchangeSha256']] += 1

    groups, retry_sources = [], []
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
            result['udpSourcePreflights'] = [pair_reference(row['paths'], output.parent) for row in bindings]
        if launch_matches:
            retry_sources.extend({'seats': entry['seats'], 'pair': pair_reference(row['paths'], output.parent),
                                  'exchangeSha256': row['summary']['exchangeSha256'], 'pairSha256': row['hashes']}
                                 for row, entry in zip(bindings, entries, strict=True) if row['status'] == 'verified')
        groups.append(result)

    inbox_complete = inbox_summary is None or not inbox_summary['issues']
    complete = not (unmatched or unreadable) and inbox_complete and all(group['complete'] for group in groups) and launch_matches
    return {'version': 1, 'scope': 'venue-udp-preflight-only', 'mode': mode,
            'networkPlanSha256': plan_hash,
            'network': 'same-host' if True in address_modes else 'private-lan-plan',
            'complete': complete,
            'checkedAtUtc': checked_at, 'expectedSources': len(expected),
            'verifiedSources': sum(row['status'] == 'verified' for row in results.values()),
            'unmatchedPairs': unmatched, 'unreadablePairs': unreadable, 'groups': groups,
            **({'requireDistinctRemoteRoster': True} if require_distinct_remote_roster else {}),
            **({'inbox': inbox_summary} if inbox_summary is not None else {}),
            **({'retrySources': retry_sources} if not complete and launch_matches else {}),
            **({'retryReportSha256': prior_hash, 'retainedSources': sum(results[address]['status'] == 'verified' for address in retained)}
               if prior_hash is not None else {}),
            **({'launcherPreview': launch_check} if launch_check is not None else {}),
            **({'launchBinding': binding} if binding is not None else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network-plan', required=True, type=Path)
    parser.add_argument('--pairs', type=Path, help='Version 1 JSON list of original listener and probe report paths')
    parser.add_argument('--inbox', type=Path, help='Directory of original UDP listener and probe reports to match by exchange')
    parser.add_argument('--batch', type=Path, action='append', default=[], help='Original completed UDP batch report')
    parser.add_argument('--retry-report', type=Path, help='Incomplete venue report whose verified sources should be checked again')
    parser.add_argument('--launcher-preview', type=Path, help='Original successful Launch-Server.exe --venue-check report')
    parser.add_argument('--launch-plan', type=Path, help='Original revision-guarded Windows launch plan for the provided preview')
    parser.add_argument('--require-distinct-remote-roster', action='store_true',
                        help='Require each planned seat to have its own private IPv4 outside the server endpoints')
    parser.add_argument('--output', required=True, type=Path, help='New readiness report (also usable for sealed verification)')
    args = parser.parse_args()
    if len(args.batch) > 25:
        parser.error('At most 25 existing batch reports are supported.')
    try:
        field.require(not args.output.exists(), 'Use a new output file')
        result = check_venue(args.network_plan, args.pairs, args.batch, args.output.resolve(), args.launcher_preview,
                             args.launch_plan, args.retry_report, args.inbox,
                             require_distinct_remote_roster=args.require_distinct_remote_roster)
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    except field.EvidenceError as error:
        parser.exit(1, f'UDP venue preflight rejected. {error}.\n')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        parser.exit(1, 'UDP venue preflight could not read its inputs or save the report. Check the plan, inbox, launcher preview and output path.\n')
    summary = {key: result[key] for key in ('complete', 'expectedSources', 'verifiedSources', 'unmatchedPairs', 'unreadablePairs')}
    if 'requireDistinctRemoteRoster' in result:
        summary['requireDistinctRemoteRoster'] = result['requireDistinctRemoteRoster']
    if 'launcherPreview' in result:
        summary['launcherPreviewMatches'] = result['launcherPreview']['complete']
    if 'launchBinding' in result:
        summary['launchPlanMatches'] = result['launchBinding']['complete']
    if 'retainedSources' in result:
        summary['retainedSources'] = result['retainedSources']
    if 'inbox' in result:
        summary['inboxPairs'] = result['inbox']['pairedExchanges']
        summary['inboxIssues'] = len(result['inbox']['issues'])
    print(json.dumps(summary))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
