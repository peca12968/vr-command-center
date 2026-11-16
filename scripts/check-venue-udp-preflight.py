"""Check collected Windows and Quest UDP report pairs against a five-room launch plan."""

import argparse
import codecs
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import NamedTuple


SPEC = importlib.util.spec_from_file_location('field_results', Path(__file__).with_name('verify-field-results.py'))
field = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(field)


class PairInput(NamedTuple):
    reports: dict
    base: Path
    group: tuple | None = None
    hashes: list | None = None
    source: tuple | None = None
    exchange: str | None = None
    samples: int | None = None
    timeout_ms: int | None = None


def read_report_lines(path, expected_sha256=None):
    with path.open('rb') as stream:
        raw = stream.read(32769)
    field.require(1 <= len(raw) <= 32768, 'Invalid UDP report size')
    if expected_sha256 is not None:
        field.require(hashlib.sha256(raw).hexdigest() == expected_sha256, 'UDP pair differs from its original files')
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


def load_inbox(directory, expected_sources):
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
    for (server, port, peer, _), entries in exchanges.items():
        roles = dict(entries)
        if len(roles) == len(entries) == 2:
            pairs.append(PairInput({'listener': roles['listen'], 'probe': roles['probe']}, directory))
        else:
            status = 'duplicate-role' if len(roles) < len(entries) else 'missing-counterpart'
            issue = {'status': status, 'files': [name for _, name in entries]}
            seats = expected_sources.get((server, port, peer))
            if seats:
                issue['seats'] = [{'roomId': room, 'seat': seat} for room, seat in seats]
                if status == 'missing-counterpart':
                    issue['missingRole'] = 'probe' if 'listen' in roles else 'listener'
            issues.append(issue)
    return pairs, {'files': len(files), 'pairedExchanges': len(pairs), 'issues': issues}


def path_reference(path, directory):
    try:
        return os.path.relpath(path, directory)
    except ValueError:  # Different Windows drives.
        return str(path)


def quest_batch_pairs(report, path, mode, endpoints, sources):
    field.require(field.integer(report['version'], 1, 1) and report.get('mode') == mode
                  and type(report.get('complete')) is bool, 'Quest UDP preflight batch must use the original mode')
    groups = report['groups']
    field.require(type(groups) is list and 1 <= len(groups) <= len(endpoints), 'Invalid Quest UDP endpoint groups')
    samples = field.integer(report.get('sampleCount'), 1, 20)
    timeout_ms = field.integer(report['sampleTimeoutMs'], 200, 3000) if 'sampleTimeoutMs' in report else None
    seen_groups, seen_seats, pairs = set(), set(), []
    for group in groups:
        rooms = group['roomIds']
        field.require(type(rooms) is list and all(type(room) is int for room in rooms)
                      and tuple(rooms) in endpoints and tuple(rooms) not in seen_groups, 'Invalid or repeated Quest UDP endpoint group')
        group_key = tuple(rooms)
        seen_groups.add(group_key)
        rows = group['seats']
        field.require(type(rows) is list and 1 <= len(rows) <= len(rooms) * 5, 'Invalid Quest UDP seat list')
        verified = []
        for row in rows:
            seat = field.integer(row['roomId'], 1, 5), field.integer(row['seat'], 1, 5)
            field.require(seat[0] in rooms and seat in sources and seat not in seen_seats,
                          'Quest UDP seat differs from the original venue network plan')
            seen_seats.add(seat)
            stage = row.get('stage')
            field.require(type(row['complete']) is bool and type(stage) is str
                          and row['complete'] == (stage in ('verified', 'reused')), 'Invalid Quest UDP seat outcome')
            if not row['complete']:
                continue
            refs = {role: row[role] for role in ('listener', 'probe')}
            hashes = [row['listenerSha256'], row['probeSha256']]
            exchange = row['exchangeSha256']
            field.require(all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) for value in (*hashes, exchange))
                          and all(type(value) is str and value for value in refs.values()), 'Invalid original Quest UDP pair metadata')
            pairs.append(PairInput(refs, path.parent, group_key, hashes, (*endpoints[group_key], sources[seat]),
                                   exchange, samples, timeout_ms))
            verified.append(refs)
        complete = len(verified) == len(rows)
        field.require(group.get('complete') is complete and (
            group.get('udpSourcePreflights') == verified if complete else 'udpSourcePreflights' not in group
        ), 'Quest UDP endpoint completeness differs from its seat outcomes')
    field.require(field.integer(report.get('expectedSeats'), 1, 25) == len(seen_seats)
                  and field.integer(report.get('verifiedSeats'), 0, 25) == len(pairs)
                  and report['complete'] == (len(seen_seats) == len(pairs)), 'Quest UDP batch totals differ from its seat outcomes')
    return pairs


def load_pairs(pairs_path, batch_paths, mode, endpoints, sources, binding, plan_hash):
    pairs = []
    distinct = False
    if pairs_path:
        manifest = field.read_quest_plan_file(pairs_path)
        field.require(set(manifest) == {'version', 'pairs'} and type(manifest['pairs']) is list,
                      'Expected a version 1 list of report pairs')
        pairs.extend(PairInput(row, pairs_path.parent) for row in manifest['pairs'])
    for path in batch_paths:
        report = field.read_json(field.content(path))
        batch_distinct = field.udp_preflight_distinct_roster(report)
        if batch_distinct:
            field.require(report.get('networkPlanSha256') == plan_hash,
                          'Reuse the original venue network plan when including a distinct-roster UDP report')
        distinct |= batch_distinct
        groups = report.get('groups')
        seat_rows = type(groups) is list and any(type(group) is dict and 'seats' in group for group in groups)
        if report.get('scope') == 'quest-udp-preflight-only' and (report.get('complete') is False or seat_rows):
            pairs.extend(quest_batch_pairs(report, path, mode, endpoints, sources))
            launch = field.read_udp_launch_binding(report, path.parent, mode)
        else:
            batch_pairs, launch = field.udp_preflight_batch(report, path, mode, [list(group) for group in sorted(endpoints)])
            digests = {tuple(group['roomIds']): field.udp_pair_digests(group) for group in report['groups']} if (
                report['scope'] == 'venue-udp-preflight-only') else {}
            for group, rows in batch_pairs.items():
                pairs.extend(PairInput(row, base, group, hashes) for (row, base), hashes in
                             zip(rows, digests.get(group, [None] * len(rows)), strict=True))
        if launch is not None:
            field.require(binding is not None and all(binding[key] == launch[0][key] for key in ('planSha256', 'previewSha256')),
                          'Reuse the original Windows plan and preview when including a bound UDP report')
    field.require(len(pairs) <= 50, 'Too many UDP preflight reports')
    return pairs, distinct


def read_pair(pair, base):
    field.require(type(pair) is dict and set(pair) == {'listener', 'probe'}
                  and all(type(value) is str and value for value in pair.values()), 'Invalid UDP report paths')
    return tuple((base / pair[key]).resolve(strict=True) for key in ('listener', 'probe'))


def pair_reference(paths, directory):
    return dict(zip(('listener', 'probe'), (path_reference(path, directory) for path in paths), strict=True))


def verify_source(address, paths, checked_at, hashes=None, *, failure_reason=False):
    server, port, peer = address
    before = field.udp_pair_hashes(paths) if hashes is None else hashes
    summary, _ = field.verify_udp_preflight(paths, {'address': server, 'port': port, 'observedAtUtc': checked_at},
                                           {field.ipv4(peer)}, failure_reason=failure_reason)
    field.require(field.udp_pair_hashes(paths) == before, 'UDP pair files changed during verification')
    return summary, before


def quest_pair_matches(candidate, probe, summary):
    if (summary['exchangeSha256'], summary['samples']) != (candidate.exchange, candidate.samples):
        return False
    if candidate.timeout_ms is None:
        return True
    try:
        samples = field.read_json(read_report_lines(probe, candidate.hashes[1])[0])['samples']
        return type(samples) is list and len(samples) == candidate.samples and all(
            type(sample['roundTripMs']) in (int, Decimal) and 0 <= sample['roundTripMs'] <= candidate.timeout_ms for sample in samples)
    except (OSError, ValueError, IndexError, KeyError, TypeError, RecursionError):
        return False


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


def retained_sources(path, report, mode, expected, launch_check, binding, checked_at, *, explain_failures=False):
    prior = field.read_udp_launch_binding(report, path.parent, mode)
    field.require(report.get('launcherPreview') == launch_check and (prior is None) == (binding is None)
                  and (prior is None or all(prior[0][key] == binding[key] for key in ('planSha256', 'previewSha256'))),
                  'Retry requires the same original Windows plan and preview')
    rows = report.get('retrySources')
    field.require(type(rows) is list and 0 <= len(rows) <= len(expected), 'Retry report lacks its original verified sources')
    by_seats = {tuple(seats): address for address, seats in expected.items()}
    valid, rejected, seen, previous_pairs = {}, {}, set(), set()
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
            hashes = field.udp_pair_hashes(paths)
            if hashes != row['pairSha256']:
                rejected[address] = 'changed-original'
                continue
            field.require(probe_identity(paths[1]) == address, 'Retry reports name a different UDP source')
            summary, _ = verify_source(address, paths, checked_at, hashes, failure_reason=explain_failures)
            field.require(summary['exchangeSha256'] == row['exchangeSha256'], 'Retry exchange differs from the original pair')
        except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
            rejected[address] = getattr(error, 'reason', None) or 'invalid-report'
            continue
        valid[address] = paths, summary, hashes
    return valid, rejected, previous_pairs


def check_venue(plan, pairs_path, batch_paths, output, launcher_preview=None, launch_plan=None, retry_report=None, inbox=None,
                *, require_distinct_remote_roster=False, explain_failures=False, inspect_retry=False):
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
    pairs, batch_distinct = load_pairs(pairs_path, batch_paths, mode, endpoints, sources, binding, plan_hash)
    if batch_distinct and not require_distinct_remote_roster:
        field.require_distinct_remote_sources(sources, endpoints.values())
        require_distinct_remote_roster = True
    if prior is not None:
        retained, rejected, previous_pairs = retained_sources(retry_report, prior, mode, expected, launch_check, binding,
                                                              checked_at, explain_failures=explain_failures)
    else:
        retained, rejected, previous_pairs, prior_hash = {}, {}, set(), None
    observed = defaultdict(list)
    path_counts = Counter()
    for address, (paths, _, _) in retained.items():
        observed[address].append((paths, None))
        path_counts.update(paths)
    unmatched = unreadable = 0
    unreadable_sources = defaultdict(set)
    inbox_summary = None
    if inspect_retry:
        # This is an inspection of the old inputs. Only an explicit retry can resolve their issues.
        field.require(prior is not None, 'Use an incomplete report for offline inspection')
        unmatched = field.integer(prior.get('unmatchedPairs'), 0, 50)
        unreadable = field.integer(prior.get('unreadablePairs'), 0, 50)
        if 'inbox' in prior:
            inbox_summary = prior['inbox']
            field.require(type(inbox_summary) is dict and set(inbox_summary) == {'files', 'pairedExchanges', 'issues'}
                          and type(inbox_summary['issues']) is list and len(inbox_summary['issues']) <= 100
                          and all(type(issue) is dict for issue in inbox_summary['issues']),
                          'Invalid UDP retry inbox summary')
            field.integer(inbox_summary['files'], 0, 100)
            field.integer(inbox_summary['pairedExchanges'], 0, 50)
    if inbox is not None:
        inbox_pairs, inbox_summary = load_inbox(inbox, expected)
    else:
        inbox_pairs = []
    field.require(len(pairs) + len(inbox_pairs) <= 50, 'Too many UDP preflight reports')
    for index, candidate in enumerate(pairs + inbox_pairs):
        pair, base, declared_group = candidate.reports, candidate.base, candidate.group
        try:
            paths = read_pair(pair, base)
            # The retry already checked these original paths and their stored hashes.
            if index >= len(pairs) and paths in previous_pairs:
                continue
            address = probe_identity(paths[1])
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            unreadable += 1
            if explain_failures and declared_group is not None:
                # Either readable original can identify the planned source even if its counterpart is missing.
                identities = {}
                for key, role in (('listener', 'listen'), ('probe', 'probe')):
                    try:
                        row = field.read_json(read_report_lines(base / pair[key])[-1])
                        if (row.get('mode') == role and row.get('scope') == 'authenticated-udp-only'
                                and row.get('stage') == 'finished' and row.get('complete') is True):
                            identities[key] = report_address(row, role)
                    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError):
                        continue
                candidates = set(identities.values())
                if len(candidates) == 1:
                    source, = candidates
                    if ((candidate.source is None or source == candidate.source)
                            and source in expected and room_groups[expected[source][0][0]] == declared_group):
                        unreadable_sources[source].update({'listener', 'probe'} - identities.keys())
            continue
        if (address not in expected or (declared_group is not None and declared_group != room_groups[expected[address][0][0]])
                or (candidate.source is not None and address != candidate.source)):
            unmatched += 1
            continue
        prior_source = retained.get(address)
        if candidate.exchange is not None and prior_source is not None:
            retained_paths, receipt, hashes = prior_source
            if (paths, candidate.hashes) == (retained_paths, hashes) and quest_pair_matches(candidate, paths[1], receipt):
                continue  # The Quest retry can carry the same original pair as the venue retry.
        observed[address].append((paths, candidate))
        path_counts.update(paths)

    results, exchange_counts = {}, Counter()
    for address, seats in expected.items():
        row = results[address] = {'seats': seats, 'status': 'missing'}
        choices = observed[address]
        if not choices:
            if address in rejected:
                row['status'] = 'invalid-or-expired'
                if explain_failures:
                    row['reason'] = rejected[address]
            elif address in unreadable_sources:
                row['reason'] = 'unreadable-original'
                if len(unreadable_sources[address]) == 1:
                    row['missingRole'], = unreadable_sources[address]
            continue
        if len(choices) != 1 or any(path_counts[path] != 1 for path in choices[0][0]):
            row['status'] = 'duplicate-pair'
            continue
        paths, candidate = choices[0]
        try:
            summary, hashes = retained[address][1:] if address in retained else verify_source(
                address, paths, checked_at, failure_reason=explain_failures)
        except (OSError, ValueError, KeyError, RecursionError) as error:
            row['status'] = 'invalid-or-expired'
            if explain_failures:
                row['reason'] = getattr(error, 'reason', None) or 'invalid-report'
            continue
        if candidate is not None and candidate.hashes is not None and hashes != candidate.hashes:
            row['status'] = 'invalid-or-expired'
            row['reason'] = 'changed-original'
            continue
        if candidate is not None and candidate.exchange is not None and not quest_pair_matches(candidate, paths[1], summary):
            row['status'] = 'invalid-or-expired'
            row['reason'] = 'invalid-report'
            continue
        row.update(status='verified', summary=summary, paths=paths, hashes=hashes)
        exchange_counts[summary['exchangeSha256']] += 1

    groups, retry_sources = [], []
    for group in rooms:
        bindings = [row for row in results.values() if room_groups[row['seats'][0][0]] == group]
        for row in bindings:
            if row['status'] == 'verified' and exchange_counts[row['summary']['exchangeSha256']] > 1:
                row['status'] = 'duplicate-exchange'
        complete = all(row['status'] == 'verified' for row in bindings)
        entries = [{'seats': [{'roomId': room, 'seat': seat} for room, seat in row['seats']], 'status': row['status'],
                    **{key: row[key] for key in ('reason', 'missingRole') if key in row}}
                   for row in bindings]
        result = {'roomIds': list(group), 'complete': complete, 'sources': entries}
        if complete:
            result['udpSourcePreflights'] = [pair_reference(row['paths'], output.parent) for row in bindings]
            result['udpSourcePreflightSha256'] = [row['hashes'] for row in bindings]
        if launch_matches:
            retry_sources.extend({'seats': entry['seats'], 'pair': pair_reference(row['paths'], output.parent),
                                  'exchangeSha256': row['summary']['exchangeSha256'], 'pairSha256': row['hashes']}
                                 for row, entry in zip(bindings, entries, strict=True) if row['status'] == 'verified')
        groups.append(result)

    inbox_complete = inbox_summary is None or not inbox_summary['issues']
    complete = not (unmatched or unreadable) and inbox_complete and all(group['complete'] for group in groups) and launch_matches
    field.require(not inspect_retry or not complete, 'Incomplete readiness has no outstanding UDP sources or report issues')
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


def windows_retest_endpoint(plan_path, report, room, seat):
    room, seat = field.integer(room, 1, 5), field.integer(seat, 1, 5)
    document, raw = field.read_quest_document(plan_path)
    field.require(report['networkPlanSha256'] == hashlib.sha256(raw).hexdigest(), 'The original venue network plan changed during recheck')
    _, endpoints, sources = field.parse_quest_network_plan(document, allow_shared_sources=True)
    field.require((room, seat) in sources, 'The Windows retest seat is not in the original venue network plan')
    group = next(group for group in report['groups'] if room in group['roomIds'])
    source = next(row for row in group['sources'] if {'roomId': room, 'seat': seat} in row['seats'])
    if source['status'] == 'verified':
        return None, {'status': 'no-windows-retest', 'coveredSeats': source['seats']}
    server, port = endpoints[tuple(group['roomIds'])]
    endpoint = {'version': 1, 'scope': 'windows-udp-retest-endpoint', 'serverAddress': server,
                'peerAddress': sources[room, seat], 'port': port}
    return endpoint, {'status': 'windows-retest-endpoint', 'coveredSeats': source['seats']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network-plan', required=True, type=Path)
    parser.add_argument('--pairs', type=Path, help='Version 1 JSON list of original listener and probe report paths')
    parser.add_argument('--inbox', type=Path, help='Directory of original UDP listener and probe reports to match by exchange')
    parser.add_argument('--batch', type=Path, action='append', default=[],
                        help='Original completed UDP batch or incomplete Quest batch with verified seats')
    parser.add_argument('--retry-report', type=Path, help='Incomplete venue report whose verified sources should be checked again')
    parser.add_argument('--windows-retest-seat', nargs=2, type=int, metavar=('ROOM', 'SEAT'),
                        help='Export the currently pending Windows source for this seat using --retry-report')
    parser.add_argument('--launcher-preview', type=Path, help='Original successful Launch-Server.exe --venue-check report')
    parser.add_argument('--launch-plan', type=Path, help='Original revision-guarded Windows launch plan for the provided preview')
    parser.add_argument('--require-distinct-remote-roster', action='store_true',
                        help='Require each planned seat to have its own private IPv4 outside the server endpoints')
    parser.add_argument('--output', required=True, type=Path, help='New readiness report or Windows retest endpoint file')
    args = parser.parse_args()
    if len(args.batch) > 25:
        parser.error('At most 25 existing batch reports are supported.')
    export_retest = args.windows_retest_seat is not None
    if export_retest and (args.retry_report is None or args.pairs is not None or args.inbox is not None or args.batch):
        parser.error('--windows-retest-seat needs --retry-report and the original inputs only')
    try:
        field.require(not args.output.exists(), 'Use a new output file')
        result = check_venue(args.network_plan, args.pairs, args.batch, args.output.resolve(), args.launcher_preview,
                             args.launch_plan, args.retry_report, args.inbox,
                             require_distinct_remote_roster=args.require_distinct_remote_roster, inspect_retry=export_retest)
        output = result
        if export_retest:
            output, retest_summary = windows_retest_endpoint(args.network_plan, result, *args.windows_retest_seat)
        if output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(output, stream, indent=2)
                stream.write('\n')
    except field.EvidenceError as error:
        parser.exit(1, f'UDP venue preflight rejected. {error}.\n')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        parser.exit(1, 'UDP venue preflight could not read its inputs or save the report. Check the plan, inbox, launcher preview and output path.\n')
    if export_retest:
        print(json.dumps(retest_summary))
        return 0
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
