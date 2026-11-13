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
    original = field.content(readiness)
    report = field.read_json(original)
    field.require(type(report) is dict and report.get('scope') == 'venue-udp-preflight-only'
                  and report.get('complete') is True, 'Provide a complete venue UDP readiness report')
    proof = field.read_udp_launch_binding(report, readiness.parent, report.get('mode'))
    field.require(proof is not None, 'Provide a readiness report bound to the original Windows plan and preview')
    binding, _ = proof
    preview = (readiness.parent / report['launchBinding']['preview']).resolve(strict=True)
    with args.launch_plan.open('rb') as stream:
        raw_plan = stream.read(field.MAX_QUEST_PLAN_BYTES + 1)
    field.require(len(raw_plan) <= field.MAX_QUEST_PLAN_BYTES
                  and hashlib.sha256(raw_plan).hexdigest() == binding['planSha256'],
                  'The launch plan differs from the original readiness proof')

    launcher = args.launcher.resolve(strict=True)
    field.require(launcher.name.lower() == 'launch-server.exe' and launcher.is_file(),
                  'Use Launch-Server.exe from the extracted Windows server package')
    with tempfile.TemporaryDirectory(prefix='vr-verified-venue-') as directory:
        snapshot = Path(directory) / 'venue-plan.json'
        snapshot.write_bytes(raw_plan)
        checked = preflight.check_venue(args.network_plan, None, [readiness], readiness, preview, snapshot)
        field.require(checked['networkPlanSha256'] == report.get('networkPlanSha256')
                      and field.content(readiness) == original
                      and checked['launchBinding']['previewSha256'] == binding['previewSha256'],
                      'The original network plan, readiness report or preview changed')
        field.require(checked['complete'], 'UDP readiness is no longer complete or within its original time window')
        print(json.dumps({'status': 'udp-preflight-verified', 'mode': checked['mode'],
                          'verifiedSources': checked['verifiedSources'], 'launchPlanSha256': binding['planSha256'],
                          'networkPlanSha256': checked['networkPlanSha256']}), flush=True)
        command = [str(launcher), '--venue-run', str(snapshot), '--work', str(args.work.resolve()),
                   '--seconds', str(args.seconds), '--ready-report', str(args.ready_report.resolve()),
                   '--report', str(args.report.resolve())]
        if args.peer_diagnostics:
            command.extend(('--peer-diagnostics', 'on'))
        own_launcher_processes()
        with subprocess.Popen(command) as process:
            try:
                return process.wait()
            except KeyboardInterrupt:
                if process.poll() is None:
                    process.terminate()
                process.wait()
                return 130


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', type=Path, required=True)
    parser.add_argument('--launch-plan', type=Path, required=True)
    parser.add_argument('--network-plan', type=Path, required=True)
    parser.add_argument('--readiness', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('--ready-report', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--peer-diagnostics', action='store_true')
    args = parser.parse_args()
    try:
        field.require(os.name == 'nt', 'This launcher runs on Windows')
        field.require(60 <= args.seconds <= 86400, 'Use a run limit from 60 to 86400 seconds')
        return launch(args)
    except field.EvidenceError as error:
        parser.exit(1, f'Verified venue start rejected. {error}.\n')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        parser.exit(1, 'Verified venue start could not read its original inputs or start the Windows launcher.\n')


if __name__ == '__main__':
    raise SystemExit(main())
