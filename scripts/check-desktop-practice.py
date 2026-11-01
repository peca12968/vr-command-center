"""Windows native practice validation; no headset, pose injection or test RPC.

Default: five clients / operator End, one client / end.request, and two clients /
60-second duration. --interactive instead opens two clients (one visible) and
waits for real W / Space / R and normal window close.
"""
import argparse
import csv
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('practice_artifacts',ROOT/'scripts/start-desktop-venue.py')
artifacts=importlib.util.module_from_spec(spec);spec.loader.exec_module(artifacts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt': parser.error('Actual Windows native players are required')
    evidence = ROOT / 'artifacts/desktop-practice-checks' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    evidence.mkdir(parents=True)
    (ROOT / 'artifacts/latest-desktop-practice-check-path.txt').write_text(str(evidence), encoding='utf-8')
    checks, cases = [], []

    def check(value, message):
        if not value: raise AssertionError(message)
        checks.append(message); print('PASS: ' + message, flush=True)

    for label, peers, end in ([('visible', 1, 'windowClosed')] if args.interactive else
            [('five-clients', 4, 'operatorEnded'), ('one-client', 0, 'endRequested'), ('duration', 1, 'durationElapsed')]):
        output = (evidence / (label + '.log')).open('w', encoding='utf-8')
        lines = queue.Queue()
        command = [sys.executable, '-u', str(ROOT / 'scripts/start-desktop-demo.py'), '--api-dll', str(args.api_dll.resolve()),
                   '--runtime-root', str(args.runtime_root), '--duration', '600' if args.interactive else '60', '--peers', str(peers), '--enemies', '1' if args.interactive else '0']
        if not args.interactive: command += ['--headless']
        environment = os.environ.copy(); environment['PYTHONIOENCODING'] = 'utf-8'
        child = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)

        def read_output():
            for line in child.stdout:
                output.write(line); output.flush(); lines.put(line)
        reader = threading.Thread(target=read_output, daemon=True); reader.start()
        directory = None
        try:
            # Covers the existing API / recording / admission startup waits;
            # this is an observation bound, not a wider source-freshness limit.
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                if child.poll() is not None: raise RuntimeError('Practice launcher exited before ready: ' + label)
                try: line = lines.get(timeout=.15)
                except queue.Empty: continue
                try: stage = json.loads(line)
                except json.JSONDecodeError: continue
                if 'directory' in stage:
                    candidate = Path(stage['directory']).resolve()
                    if candidate.parent != ROOT / 'artifacts/desktop-demo' or not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}', candidate.name):
                        raise RuntimeError('Unexpected practice directory')
                    directory = candidate
                if stage.get('stage') == 'ready': break
            else: raise RuntimeError('Practice startup did not become ready')
            ready = artifacts.read_json(directory/'ready.json')
            tokens = artifacts.read_json(directory/'keys.json')['OperatorKeys']
            def api(route, body=None):
                request = urllib.request.Request(ready['baseUrl'] + route,
                    data=None if body is None else json.dumps(body).encode(),
                    headers={'Authorization': 'Bearer ' + tokens['Master'], 'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=5) as response: return json.load(response)
            def until(predicate, label, seconds=30):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    if child.poll() is not None: raise RuntimeError('Practice stopped during ' + label)
                    try:
                        value = predicate()
                        if value: return value
                    except (OSError, ValueError): pass
                    time.sleep(.1)
                raise RuntimeError('Timed out: ' + label)
            def frame(): return artifacts.read_json(directory/'latest-frame.json')['packet']['frame']
            initial = until(lambda: (value if (value := frame())['phase'] == 'Running' else None), 'initial practice frame')
            session = ready['sessionId']; ids = set(ready['playerIds'])
            check(len(ids) == peers + 1 and {p['id'] for p in initial['players'] if p['connected'] and p['rig']['kind'] == 'Simulated'} == ids,
                  label + ': every expected native client is connected with an accepted Simulation rig')
            check(ready['headsets'] == 0 and ready['jobWorkersPerProcess'] == 2 and api('/')['version'] == '0.30.1',
                  label + ': current API, two job workers and explicit no-headset provenance')
            case = {'label': label, 'directory': str(directory), 'initialFrame': initial}
            if args.interactive:
                (evidence / 'stage.json').write_text(json.dumps({'stage': 'input', 'ready': str(directory / 'ready.json')}), encoding='utf-8')
                print('INTERACTIVE: use real W, one Space, R; wait for reload. Then wait for close stage.', flush=True)
                actor = ready['playerIds'][0]; start = next(p for p in initial['players'] if p['id'] == actor)['head']
                def accepted_input():
                    value = frame(); player = next(p for p in value['players'] if p['id'] == actor)
                    metric = next(p for p in api(f'/api/sessions/{session}/statistics')['players'] if p['playerId'] == actor)
                    moved = (player['head']['x'] - start['x'])**2 + (player['head']['z'] - start['z'])**2
                    return value if metric['ammoUsed'] == 1 and moved > .02**2 and player['magazine'] == 30 and player['reserve'] == 89 and not player['reloading'] else None
                case['acceptedInputFrame'] = until(accepted_input, 'real movement, one shot and completed reload', 240)
                check(True, 'visible: actual W / Space / R reached the accepted native world and ammunition ledger')
                (evidence / 'stage.json').write_text(json.dumps({'stage': 'close', 'ready': str(directory / 'ready.json')}), encoding='utf-8')
                print('INTERACTIVE: close this owned game window normally.', flush=True)
            else:
                def control(action): return api(f'/api/sessions/{session}/commands', {'commandId': str(uuid.uuid4()), 'action': action})
                control('Pause')
                paused = until(lambda: (value if (value := frame())['phase'] == 'Paused' else None), 'Pause applied')
                time.sleep(.5)
                check(frame()['phase'] == 'Paused' and frame()['tick'] == paused['tick'], label + ': Pause freezes the authority clock')
                control('Resume')
                until(lambda: frame()['tick'] > paused['tick'], 'Resume advances')
                if end == 'operatorEnded': control('End')
                elif end == 'endRequested': (directory / 'end.request').write_text('', encoding='utf-8')
            rc = child.wait(timeout=300 if args.interactive else 100)
            check(rc == 0, label + ': launcher exits successfully after ' + end)
            summary = artifacts.read_json(directory/'summary.json')
            cleanup = artifacts.read_json(directory/'cleanup.json')
            report = (directory / 'final-report.csv').read_bytes()
            rows = list(csv.DictReader(io.StringIO(report.decode('utf-8-sig'))))
            check(summary['stopReason'] == end and summary['world']['complete'] and not summary['statistics']['pendingTelemetry']
                  and summary['replayStatisticsMatch'] and summary['activeSessions'] == 0,
                  label + ': exact combat / world seals and replay / ledger agreement precede completion')
            check(summary['finalReport']['verified'] and len(rows) == peers + 1 and {row['playerId'] for row in rows} == ids
                  and hashlib.sha256(report).hexdigest() == summary['finalReport']['sha256'], label + ': verified final CSV preserves every player')
            check(cleanup == {'errors': [], 'remainingTrackedChildren': []}, label + ': no owned API or native children remain')
            def hashes(folder): return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
            original = hashes(Path(summary['runtimeDirectory'])); snapshot = hashes(directory / 'runtime-snapshot')
            check(bool(original) and original == snapshot, label + ': stopped SSD writers have an identical preserved F snapshot')
            check(-1 <= summary['rounds'][0]['maximumSourceAgeSeconds'] < 1.5, label + ': captured-UTC source age stays below the original limit')
            if not args.interactive:
                delivery = summary['playerResults']
                check(delivery['allAcknowledged'] and not delivery['timedOut'] and len(delivery['phases']) == peers + 1,
                      label + ': every connected native player receives and acknowledges its sealed result')
            case.update(summary=summary, snapshotFiles=len(original)); cases.append(case)
        finally:
            if directory is not None and child.poll() is None:
                (directory / 'end.request').write_text('', encoding='utf-8')
                child.wait(timeout=300)
            elif child.poll() is None:
                # Starting is emitted before any API or native player can be spawned.
                child.terminate(); child.wait(timeout=10)
            reader.join(timeout=5); output.close()
    (evidence / 'summary.json').write_text(json.dumps({'checks': len(checks), 'cases': cases, 'headsets': 0, 'scope': 'Actual Windows native processes; Simulation rigs; not cross-machine or headset load'}, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'checks': len(checks), 'directory': str(evidence)}), flush=True)


if __name__ == '__main__': main()
