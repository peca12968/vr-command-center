"""Prepare the six-batch venue plan from existing batch manifests."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path


spec = spec_from_file_location('prepare_venue_manifest', Path(__file__).with_name('prepare-venue-field-manifest.py'))
manifest_tool = module_from_spec(spec)
spec.loader.exec_module(manifest_tool)
field = manifest_tool.field


def prepare(args, output):
    minimum = field.integer(args.minimum_concurrent_ms, 1000, 900000)
    field.require(not args.require_distinct_remote_roster or args.topology == 'direct-lan',
                  'Distinct staged roster requires direct-lan topology')
    plan = {'version': 1, 'topology': args.topology, 'minimumConcurrentMilliseconds': minimum}
    for key, enabled in (
        ('requireDistinctRemoteRoster', args.require_distinct_remote_roster),
        ('requireVerifiedVenueStart', args.require_verified_venue_start),
        ('requireTrackedRoster', args.require_tracked_roster),
        ('requireConcurrentFire', args.require_concurrent_fire),
    ):
        if enabled:
            plan[key] = True
    if args.windows_minimum_replies is not None or args.windows_maximum_p95_ms is not None:
        field.require(args.windows_minimum_replies is not None and args.windows_maximum_p95_ms is not None,
                      'Provide both Windows link criteria')
        plan['windowsLinkCriteria'] = {'minimumReplies': args.windows_minimum_replies,
                                       'maximumP95RoundTripMs': args.windows_maximum_p95_ms}
        field.read_windows_link_criteria(plan)

    batches, paths, release_digests = {}, set(), set()
    for index, supplied in enumerate(args.venue_manifest, 1):
        try:
            path = supplied.resolve(strict=True)
            field.require(path != output and path not in paths, 'Staged venue manifest paths must be distinct')
            paths.add(path)
            batch = field.read_json(field.content(path))
            field.require(type(batch) is dict and batch.get('topology') == args.topology,
                          'Venue batch topology differs from the staged plan')
            field.integer(batch.get('version'), 1, 1)
            seats = field.integer(batch.get('expectedPlayersPerRoom', 5), 1, 5)
            mode = batch.get('mode')
            key = (mode, seats * 5)
            field.require(key in field.VENUE_STAGE_KEYS and key not in batches,
                          'Staged venue must cover each mode and seat count exactly once')
            release = batch.get('venueReleaseReport')
            field.require(type(release) is str and release.strip(),
                          'Provide the original venue release report in every batch manifest')
            _, digest = field.read_venue_release(path.parent / release)
            release_digests.add(digest)
            batches[key] = path
        except field.EvidenceError as error:
            raise field.EvidenceError(f'Batch input {index}: {error}') from None
        except (OSError, ValueError, TypeError, RuntimeError):
            raise field.EvidenceError(f'Batch input {index}: unreadable manifest or release report') from None

    field.require(len(release_digests) == 1, 'Every staged venue batch must use the same original verified release report')
    plan['venueManifests'] = [manifest_tool.path_reference(batches[key], output.parent) for key in field.VENUE_STAGE_KEYS]
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('venue_manifest', nargs=len(field.VENUE_STAGE_KEYS), type=Path, help='Batch manifests in any order')
    parser.add_argument('--output', required=True, type=Path, help='New stages.json file')
    parser.add_argument('--topology', required=True, choices=('same-host', 'direct-lan'))
    parser.add_argument('--minimum-concurrent-ms', required=True, type=int)
    parser.add_argument('--require-distinct-remote-roster', action='store_true')
    parser.add_argument('--require-verified-venue-start', action='store_true')
    parser.add_argument('--require-tracked-roster', action='store_true')
    parser.add_argument('--require-concurrent-fire', action='store_true')
    parser.add_argument('--windows-minimum-replies', type=int)
    parser.add_argument('--windows-maximum-p95-ms', type=int)
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        field.require(not output.exists(), 'Use a new output file')
        plan = prepare(args, output)
        with output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(plan, indent=2, ensure_ascii=False) + '\n')
    except field.EvidenceError as error:
        parser.exit(1, f'Staged venue plan could not be prepared. {error}.\n')
    except (OSError, ValueError, RuntimeError):
        parser.exit(1, 'Staged venue plan could not be prepared. Check the output path.\n')
    print(json.dumps({'prepared': True, 'batches': len(plan['venueManifests'])}))


if __name__ == '__main__':
    main()
