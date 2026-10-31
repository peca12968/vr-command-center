"""Observe direct-loopback native input timing with the current game build.

Two real clients, no loss gate / payload / pose / weapon injection. Explicitly
finish bounded in-memory timing traces before End. HUD trace records transitions
without GPU readback or PCM. Use actual Space once per shot stage, then create
shot-N.done only after observing the game; it is an acknowledgement, not input.
With --observation-only, acknowledge window-review.done without game keys.
Optional --heartbeat owns a separate bounded normal-priority timer process.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('input_venue', ROOT / 'scripts/start-desktop-venue.py')
venue_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(venue_module)


class InputVenue(venue_module.Venue):
    def launch(self, name, config, visible=False, *, extra_args=()):
        flags = list(extra_args)
        if name in ('pose-input-server', 'pose-input-player', 'pose-input-peer'):
            flags += ['--vr-pose-trace', str((self.runtime_directory / (name + '-trace')).resolve())]
            if self.args.player_loop: flags += ['--vr-pose-loop-trace']
        return super().launch(name, config, visible, extra_args=flags)


class Heartbeat:
    def __init__(self, directory):
        self.directory = directory
        self.child = subprocess.Popen([sys.executable, str(ROOT / 'scripts/pose-heartbeat.py'), '--directory', str(directory.resolve())],
                                      creationflags=subprocess.CREATE_NO_WINDOW)
        self.report = None

    def finish(self):
        if self.report is not None: return self.report
        deadline = time.monotonic() + 5
        while not self.directory.exists() and self.child.poll() is None and time.monotonic() < deadline: time.sleep(.05)
        if self.child.poll() is None and self.directory.exists(): (self.directory / 'finish.request').write_text('Explicit diagnostic stop')
        try: self.child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.child.terminate(); self.child.wait(timeout=5)
            raise RuntimeError('Independent heartbeat did not stop')
        if self.child.returncode != 0: raise RuntimeError('Independent heartbeat failed')
        report = json.loads((self.directory / 'report.json').read_text())
        if not report['complete']: raise RuntimeError('Independent heartbeat incomplete')
        self.report = report; return report


def run(v, heartbeats):
    v.start(); marks = []; samples = []
    def mark(phase):
        marks.append({'phase': phase, 'utc': datetime.now(timezone.utc).isoformat()}); v.save('input-stages.json', marks)
    mission = v.request('/api/missions', {'name': 'Pose input timing - Simulation', 'briefing': 'Direct loopback, current native first and repeated shots',
        'durationSeconds': 600, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False},
        'props': [{'assetId': 'sandbag', 'position': {'x': 0, 'y': 0, 'z': 2}, 'yawDegrees': 0},
                  {'assetId': 'barrel', 'position': {'x': 2, 'y': 0, 'z': 2}, 'yawDegrees': 30}]}, expected=201)
    entry = v.create(mission, [3], 'pose-input', role='Room3'); own = entry['players'][0]
    peer_id = str(uuid.uuid4())
    state = v.request(f'/api/sessions/{entry["id"]}/players', {'playerId': peer_id, 'name': 'Timing peer', 'roomId': 3, 'headset': 'Quest3'})
    peer = next(player for player in state['players'] if player['id'] == peer_id); entry['players'].append(peer)
    v.wait(lambda: v.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'world recording')
    v.launch('pose-input-peer', v.client_config(entry, v.ticket(entry, peer)))
    hud = v.runtime_directory / 'pose-input-hud'
    v.launch('pose-input-player', v.client_config(entry, v.ticket(entry, own)), True, extra_args=['--vr-hud-trace', str(hud.resolve())])
    v.wait(lambda: v.connected(entry), 100, 'both current native clients'); v.command(entry, 'Begin')
    heartbeat = Heartbeat(v.runtime_directory / 'pose-input-heartbeat') if v.args.heartbeat else None
    if heartbeat is not None: heartbeats.append(heartbeat)
    def observe(label):
        data = v.frame(entry, measure=True); frame = data['packet']['frame']; player = next(p for p in frame['players'] if p['id'] == own['id'])
        row = {'phase': label, 'utc': datetime.now(timezone.utc).isoformat(), 'tick': frame['tick'], 'connected': player['connected'],
               'magazine': player['magazine'], 'health': player['health'], 'sequence': data['packet']['sequence']}
        samples.append(row); v.save('input-world-samples.json', samples); return row
    mark('baseline-start'); v.stage('input-baseline', seconds=v.args.baseline_seconds)
    deadline = time.monotonic() + v.args.baseline_seconds
    while time.monotonic() < deadline: observe('baseline'); time.sleep(.15)
    mark('baseline-end')
    if v.args.observation_only:
        mark('window-review-start'); v.stage('window-review', acknowledgement='window-review.done', note='Window observation only; do not press game keys')
        v.wait(lambda: observe('window-review') and (v.directory / 'window-review.done').exists(), 120, 'window observation acknowledgement')
        mark('window-review-end'); mark('quiet-after-start'); v.stage('quiet-after', seconds=v.args.baseline_seconds)
        deadline = time.monotonic() + v.args.baseline_seconds
        while time.monotonic() < deadline: observe('quiet-after'); time.sleep(.15)
        mark('quiet-after-end')
    else:
        for shot in range(1, 4):
            mark(f'shot-{shot}-start'); v.stage('input-shot', shot=shot, key='space', presses=1, acknowledgement=f'shot-{shot}.done')
            v.wait(lambda: (row if (row := observe(f'shot-{shot}'))['connected'] and row['magazine'] == 30 - shot
                           and (v.directory / f'shot-{shot}.done').exists() else None), 45, f'actual shot {shot}')
            mark(f'shot-{shot}-end')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline: observe(f'after-shot-{shot}'); time.sleep(.15)
    mark('observation-end')
    if heartbeat is not None: heartbeat.finish()
    roles = {'Visible': ('player', 'Client'), 'Peer': ('peer', 'Client'), 'Server': ('server', 'Server')}
    for name, _ in roles.values():
        (v.runtime_directory / f'pose-input-{name}-trace/finish.request').write_text('Stop diagnostic only', encoding='utf-8')
    def report(name, role):
        try: value = json.loads((v.runtime_directory / f'pose-input-{name}-trace/report.json').read_text(encoding='utf-8-sig'))
        except (OSError, ValueError): return None
        if not value['complete'] or value['truncated'] or value['error'] or value['role'] != role: raise RuntimeError('Timing report incomplete')
        if v.args.player_loop and (not value.get('playerLoop') or not value['playerLoop']['complete'] or not value['playerLoop']['detached']):
            raise RuntimeError('Player loop diagnostic incomplete or not detached')
        return value
    reports = {label: v.wait(lambda name=name, role=role: report(name, role), 10, label + ' explicit diagnostic finish')
               for label, (name, role) in roles.items()}
    sealed = v.seal(entry)
    def final_hud():
        try: value = json.loads((hud / 'report.json').read_text(encoding='utf-8-sig'))
        except (OSError, ValueError): return None
        return value if value['complete'] else None
    state = v.wait(final_hud, 15, 'HUD transition report')
    if state['error'] or state['hudTransitionsTruncated'] or state['captures'] or state['audioSamples'] or state['callbackCount']:
        raise RuntimeError('HUD diagnostic is incomplete or captured GPU / PCM')
    metric = next(p for p in sealed['statistics']['players'] if p['playerId'] == own['id'])
    if metric['ammoUsed'] != (0 if v.args.observation_only else 3) or metric['health'] != 100: raise RuntimeError('Accepted input statistics disagree')
    v.save('input-timing-result.json', {'source': 'Actual Windows / direct loopback / Simulation', 'headsets': 0,
        'directLoopback': True, 'poseOrWeaponInjected': False, 'observationOnly': v.args.observation_only,
        'independentHeartbeat': heartbeat is not None, 'marks': marks, 'statistics': metric,
        'playerLoop': v.args.player_loop,
        'reports': {label: {'rows': len(value['rows']), 'seconds': value['endedSeconds']} for label, value in reports.items()},
        'hudTransitions': state['hudTransitions']})
    v.evidence.extend(['Two direct-loopback current native clients; natural baseline without packet-loss control',
        'Observation-only zero ammo verified' if v.args.observation_only else 'Three actual Space inputs agree with authority and final ledger', 'All three bounded timing reports explicitly finished before End',
        'Every rendered HUD status transition retained without native GPU readback / PCM; exact seals'])
    v.summary()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--baseline-seconds', type=int, choices=range(5, 61), default=15)
    parser.add_argument('--heartbeat', action='store_true', help='Independent bounded process timing; no game access')
    parser.add_argument('--player-loop', action='store_true', help='Explicit native PlayerLoop boundary observers; needs new matching player build')
    parser.add_argument('--observation-only', action='store_true', help='Quiet / window-observation / quiet; no shooting')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    args = parser.parse_args(); args.duration = 600; args.visible_room = 3; args.job_workers = 2; args.check = False
    venue_module.verify_player(args); v = InputVenue(args); heartbeats = []
    try: run(v, heartbeats)
    except BaseException as error: v.stage('failed', errorType=type(error).__name__); raise
    finally:
        errors = []
        for heartbeat in heartbeats:
            try: heartbeat.finish()
            except Exception as error: errors.append(type(error).__name__)
        cleaned = v.cleanup(); v.save('heartbeat-cleanup.json', {'errors': errors, 'remaining': [h.child.pid for h in heartbeats if h.child.poll() is None]})
        if (errors or not cleaned) and sys.exc_info()[0] is None: raise RuntimeError('Input timing cleanup failed')


if __name__ == '__main__': main()
