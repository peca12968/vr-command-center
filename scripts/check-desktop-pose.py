"""Native pose freshness regression with a loopback-only UDP loss gate.

Forwards unchanged datagrams for one own fixture client; temporarily drops its
outbound packets. No payload parsing / storage, input injection, firewall or
external network changes. Finish with one actual Space press in the window.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('venue', ROOT / 'scripts/start-desktop-venue.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class LossGate:
    def __init__(self, server_port):
        self.server = ('127.0.0.1', server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if hasattr(socket, 'SIO_UDP_CONNRESET'): self.socket.ioctl(socket.SIO_UDP_CONNRESET, False)
        self.socket.bind(('127.0.0.1', 0)); self.socket.settimeout(.1)
        self.port = self.socket.getsockname()[1]
        self.client = None; self.until = 0; self.dropped = 0; self.forwarded = 0
        self.done = threading.Event(); self.error = None
        self.worker = threading.Thread(target=self.run, daemon=True); self.worker.start()

    def run(self):
        try:
            while not self.done.is_set():
                try: data, sender = self.socket.recvfrom(65535)
                except socket.timeout: continue
                if sender == self.server:
                    if self.client: self.socket.sendto(data, self.client)
                elif sender[0] == '127.0.0.1' and (self.client is None or sender == self.client):
                    self.client = sender
                    if time.monotonic() < self.until: self.dropped += 1
                    else: self.socket.sendto(data, self.server); self.forwarded += 1
        except OSError as error:
            if not self.done.is_set(): self.error = type(error).__name__

    def close(self):
        self.done.set(); self.worker.join(2); self.socket.close()
        if self.worker.is_alive() or self.error: raise RuntimeError('Loopback loss gate did not stop cleanly')


def run(v, gates):
    v.start()
    mission = v.request('/api/missions', {'name': 'Pose freshness - Simulation', 'briefing': 'Loopback packet loss; real native player',
        'durationSeconds': 300, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
    entry = v.create(mission, [3], 'pose', role='Room3'); player = entry['players'][0]
    v.wait(lambda: v.request('/api/sessions/' + entry['id'] + '/world', optional=True), 90, 'native recording')
    gate = LossGate(entry['port']); gates.append(gate)
    config = v.client_config(entry, v.ticket(entry, player)); config['port'] = gate.port
    probe = v.runtime_directory / 'hud-trace'
    v.launch('pose-player', config, True, extra_args=['--vr-hud-trace', str(probe.resolve())])
    (ROOT / 'artifacts/latest-pose-path.txt').write_text(str(v.directory), encoding='utf-8')

    def status():
        if gate.error: raise RuntimeError('Loopback gate failed: ' + gate.error)
        world = v.frame(entry, measure=True)
        try: report = json.loads((probe / 'status.json').read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError): return None
        if report['error']: raise RuntimeError(report['error'])
        hud = (report.get('frame') or {}).get('hud')
        if not hud: return None
        body = next(p for p in world['packet']['frame']['players'] if p['id'] == player['id'])
        return {'hud': hud, 'body': body, 'sequence': world['packet']['sequence']}

    def until(predicate, label, seconds=30):
        return v.wait(lambda: value if (value := status()) and predicate(value) else None, seconds, label)

    v.wait(lambda: v.connected(entry), 45, 'native admission')
    v.command(entry, 'Begin'); until(lambda s: s['hud']['status'] == 'ACTIVE', 'active HUD')
    v.stage('loss-review', marker='loss.done')
    until(lambda s: (v.directory / 'loss.done').exists(), 'review active player before packet loss', 90)
    pulses = []
    for index, duration in enumerate([1.2, 1.2, 6]):
        gate.until = time.monotonic() + duration
        stale = until(lambda s: s['hud']['status'] == 'POSE STREAM STALE' and not s['body']['connected'], 'authoritative expired pose')
        assert stale['hud']['poseAccepted'] and stale['hud']['ready'] and stale['hud']['tracking'] and not stale['hud']['connected']
        assert stale['body']['health'] == 100 and stale['body']['magazine'] == 30
        v.stage('stale-review', pulse=index + 1, durationSeconds=duration)
        recovered = until(lambda s: s['hud']['status'] == 'ACTIVE' and s['body']['connected'], 'fresh pose recovers without reticket', duration + 15)
        assert recovered['body']['head'] == stale['body']['head']
        pulses.append({'stale': stale, 'recovered': recovered})
        time.sleep(.5)
    v.stage('fire', key='space', presses=1)
    until(lambda s: (v.directory / 'fire.done').exists(), 'actual keyboard input', 90)
    fired = until(lambda s: s['hud']['magazine'] == s['body']['magazine'] == 29 and s['hud']['status'] == 'ACTIVE', 'fire after recovery')
    sealed = v.seal(entry)
    def final():
        try: value = json.loads((probe / 'report.json').read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError): return None
        return value if value['complete'] else None
    report = v.wait(final, 15, 'complete trace')
    assert report['complete'] and not report['error'] and not report['hudTransitionsTruncated']
    assert report['mode'] == 'hud-trace' and report['audioSamples'] == report['callbackCount'] == 0
    assert not report['captures'] and not report['captureTimings'] and not list(probe.glob('*.png')) and not (probe / 'audio.wav').exists()
    transitions = report['hudTransitions']; stale_events = [x for x in transitions if x['hud']['status'] == 'POSE STREAM STALE']
    assert len(stale_events) >= 3 and all(x['hud']['poseAccepted'] and not x['hud']['connected'] for x in stale_events)
    own = next(p for p in sealed['statistics']['players'] if p['playerId'] == player['id'])
    assert own['ammoUsed'] == 1 and own['damageTaken'] == 0 and gate.dropped > 0
    v.evidence.extend(['Three actual loopback packet-loss intervals expire authoritative poses', 'HUD distinguishes stale stream from rejection; fresh packets recover same admission',
        'Actual keyboard fire after recovery matches sealed ammo / replay', 'Every rendered status transition retained; no GPU readback / PCM'])
    v.summary(); v.save('pose-result.json', {'source': 'Actual Windows / loopback packet loss; Simulation', 'headsets': 0, 'pulses': pulses,
        'fired': fired, 'hudTransitions': transitions, 'ownStatistics': own, 'droppedDatagrams': gate.dropped, 'forwardedDatagrams': gate.forwarded})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root', type=Path)
    p.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = p.parse_args(); args.duration = 300; args.visible_room = 3; args.job_workers = 2; args.check = False
    module.verify_player(args); v = module.Venue(args); gates = []
    try: run(v, gates)
    except BaseException as error: v.stage('failed', errorType=type(error).__name__); raise
    finally:
        try:
            if not v.cleanup(): raise RuntimeError('Pose fixture cleanup failed; inspect cleanup.json')
        finally:
            for gate in gates: gate.close()


if __name__ == '__main__': main()
