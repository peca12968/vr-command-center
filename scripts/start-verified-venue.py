"""Recheck the original UDP evidence before starting a Windows venue batch."""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile


SPEC = importlib.util.spec_from_file_location('venue_preflight', Path(__file__).with_name('check-venue-udp-preflight.py'))
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
field = preflight.field


def own_launcher_processes():
    # Keep the private, non-inheritable handle open for this CLI's lifetime.
    # Windows closes it even if the CLI is terminated before the launcher exits.
    class BasicLimits(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', wintypes.DWORD), ('min_working_set', ctypes.c_size_t),
                    ('max_working_set', ctypes.c_size_t), ('active_limit', wintypes.DWORD),
                    ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('basic', BasicLimits), ('io_counters', ctypes.c_uint64 * 6),
                    ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                    ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    field.require(job, 'Could not create a private Windows launcher job')
    limits = ExtendedLimits()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not (kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
            and kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess())):
        kernel.CloseHandle(job)
        raise field.EvidenceError('Could not own the Windows launcher and game processes')


def launch(args):
    readiness = args.readiness.resolve(strict=True)
    with readiness.open('rb') as stream:
        original = field.limited_read(stream)
    report = field.read_json(original.decode('utf-8-sig'))
    field.require(type(report) is dict and report.get('scope') == 'venue-udp-preflight-only'
                  and report.get('complete') is True, 'Provide a complete venue UDP readiness report')
    distinct = field.udp_preflight_distinct_roster(report) or args.require_distinct_remote_roster
    proof = field.read_udp_launch_binding(report, readiness.parent, report.get('mode'))
    field.require(proof is not None, 'Provide a readiness report bound to the original Windows plan and preview')
    binding, _ = proof
    preview = (readiness.parent / report['launchBinding']['preview']).resolve(strict=True)
    with args.launch_plan.open('rb') as stream:
        raw_plan = stream.read(field.MAX_QUEST_PLAN_BYTES + 1)
    field.require(len(raw_plan) <= field.MAX_QUEST_PLAN_BYTES
                  and hashlib.sha256(raw_plan).hexdigest() == binding['planSha256'],
                  'The launch plan differs from the original readiness proof')

    if not args.verify_only:
        launcher = args.launcher.resolve(strict=True)
        field.require(launcher.name.lower() == 'launch-server.exe' and launcher.is_file(),
                      'Use Launch-Server.exe from the extracted Windows server package')
        ready_path, result_path = args.ready_report.resolve(), args.report.resolve()
        receipt_path = args.start_receipt.resolve() if args.start_receipt else None
        if receipt_path is not None:
            field.require(not receipt_path.exists() and receipt_path.parent.is_dir()
                          and receipt_path not in (ready_path, result_path) and not receipt_path.is_relative_to(args.work.resolve())
                          and not receipt_path.is_relative_to(launcher.parent)
                          and not receipt_path.is_relative_to(Path(field.read_json(raw_plan.decode('utf-8-sig'))['controlInstance']).resolve().parent),
                          'Use a separate new start receipt path outside the package, work directory and management instance')
    with tempfile.TemporaryDirectory(prefix='vr-verified-venue-') as directory:
        snapshot = Path(directory) / 'venue-plan.json'
        snapshot.write_bytes(raw_plan)
        with args.network_plan.open('rb') as stream:
            network_raw = stream.read(field.MAX_QUEST_PLAN_BYTES + 1)
        field.require(len(network_raw) <= field.MAX_QUEST_PLAN_BYTES, 'The network plan is too large')
        network = Path(directory) / 'venue-network.json'
        network.write_bytes(network_raw)
        checked = preflight.check_venue(network, None, [readiness], readiness, preview, snapshot,
                                        require_distinct_remote_roster=distinct, explain_failures=args.verify_only)
        with readiness.open('rb') as stream:
            field.require(checked['networkPlanSha256'] == report.get('networkPlanSha256')
                          and field.limited_read(stream) == original
                          and checked['launchBinding']['previewSha256'] == binding['previewSha256'],
                          'The original network plan, readiness report or preview changed')
        if args.verify_only:
            pending = [{**seat, 'status': row['status'], **{key: row[key] for key in ('reason', 'missingRole') if key in row}}
                       for group in checked['groups'] for row in group['sources'] if row['status'] != 'verified'
                       for seat in row['seats']]
            print(json.dumps({'status': 'udp-evidence-verified' if checked['complete'] else 'udp-evidence-incomplete',
                              'mode': checked['mode'], 'verifiedSources': checked['verifiedSources'],
                              'expectedSources': checked['expectedSources'], 'unreadablePairs': checked['unreadablePairs'],
                              'unmatchedPairs': checked['unmatchedPairs'],
                              'pendingSeats': sorted(pending, key=lambda seat: (seat['roomId'], seat['seat']))}), flush=True)
            return 0 if checked['complete'] else 1
        field.require(checked['complete'], 'UDP readiness is no longer complete or within its original time window')
        distinct = field.udp_preflight_distinct_roster(checked)
        original_preview = field.read_udp_launcher_document(preview, preview=True)
        field.require(original_preview[0] == binding['previewSha256'], 'The original Windows launcher preview changed')
        own_launcher_processes()
        if any('registeredSeats' in row for row in original_preview[2].values()):
            fresh_path = Path(directory) / 'current-preview.json'
            current = subprocess.run([str(launcher), '--venue-check', str(snapshot), '--report', str(fresh_path)], timeout=45)
            field.require(current.returncode == 0, 'Windows launcher no longer accepts the original session revisions')
            fresh = field.read_udp_launcher_document(fresh_path, preview=True)
            field.require(fresh == original_preview, 'Current Windows launcher preview differs from the original sessions, seats or bindings')
        print(json.dumps({'status': 'udp-preflight-verified', 'mode': checked['mode'],
                          'verifiedSources': checked['verifiedSources'], 'launchPlanSha256': binding['planSha256'],
                          'networkPlanSha256': checked['networkPlanSha256'],
                          **({'requireDistinctRemoteRoster': True} if distinct else {})}), flush=True)
        command = [str(launcher), '--venue-run', str(snapshot), '--work', str(args.work.resolve()),
                   '--seconds', str(args.seconds), '--ready-report', str(ready_path), '--report', str(result_path)]
        if args.peer_diagnostics:
            command.extend(('--peer-diagnostics', 'on'))
        with subprocess.Popen(command) as process:
            try:
                code = process.wait()
            except KeyboardInterrupt:
                if process.poll() is None:
                    process.terminate()
                process.wait()
                return 130
        if code == 0 and receipt_path is not None:
            write_start_receipt(receipt_path, ready_path, result_path, readiness, original, checked)
        return code


def write_start_receipt(path, ready_path, result_path, readiness, original, checked):
    ready, ready_raw = field.read_quest_document(ready_path)
    with result_path.open('rb') as stream:
        result_raw = field.limited_read(stream)
    terminal = field.read_json(result_raw.decode('utf-8-sig'))
    field.require(terminal['status'] == 'venue-sealed-stopped' and terminal['complete'] is terminal['readyPublished'] is True,
                  'The original Windows venue launch did not seal and stop')
    receipt = {'version': 1, 'scope': 'verified-windows-venue-start', 'mode': checked['mode'],
               'checkedAtUtc': checked['checkedAtUtc'], 'readinessSha256': hashlib.sha256(original).hexdigest(),
               'terminalSha256': hashlib.sha256(result_raw).hexdigest(),
               'readyReport': preflight.path_reference(ready_path, path.parent), 'readySha256': hashlib.sha256(ready_raw).hexdigest(),
               **({'requireDistinctRemoteRoster': True} if checked.get('requireDistinctRemoteRoster') else {})}
    with readiness.open('rb') as stream:
        field.require(ready['status'] == 'venue-ready' and ready['topology'] == terminal['topology'] == checked['mode']
                      and ready['instanceId'] == terminal['instanceId'] and field.limited_read(stream) == original,
                      'The original readiness or Windows venue reports changed')
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true', help='Recheck archived UDP evidence without contacting management or starting Windows')
    parser.add_argument('--launcher', type=Path)
    parser.add_argument('--launch-plan', type=Path, required=True)
    parser.add_argument('--network-plan', type=Path, required=True)
    parser.add_argument('--readiness', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--seconds', type=int)
    parser.add_argument('--ready-report', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--start-receipt', type=Path, help='New optional receipt after the original batch seals and stops')
    parser.add_argument('--require-distinct-remote-roster', action='store_true',
                        help='Require each planned seat to have its own private IPv4 outside the server endpoints')
    parser.add_argument('--peer-diagnostics', action='store_true')
    args = parser.parse_args()
    launch_options = ('launcher', 'work', 'seconds', 'ready_report', 'report')
    if args.verify_only:
        if any(getattr(args, name) is not None for name in launch_options) or args.start_receipt or args.peer_diagnostics:
            parser.error('--verify-only does not accept Windows launch or output options')
    elif any(getattr(args, name) is None for name in launch_options):
        parser.error('Starting Windows requires --launcher --work --seconds --ready-report --report')
    try:
        if not args.verify_only:
            field.require(os.name == 'nt', 'This launcher runs on Windows')
            field.require(60 <= args.seconds <= 86400, 'Use a run limit from 60 to 86400 seconds')
        return launch(args)
    except field.EvidenceError as error:
        parser.exit(1, f'Verified venue start rejected. {error}.\n')
    except (OSError, ValueError, KeyError, TypeError, RecursionError, subprocess.TimeoutExpired):
        parser.exit(1, 'Verified venue start could not read its original inputs or start the Windows launcher.\n')


if __name__ == '__main__':
    raise SystemExit(main())
