"""Interactive native tactical HUD check using actual keyboard input.

Own API / server / two Simulation clients. Complete the printed input in the
visible window and create <stage>.done in its evidence directory. Markers never
inject input: accepted world / combat data and the rendered HUD decide results.
HUD-only capture records no PCM and leaves normal weather playback unchanged.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('venue', ROOT / 'scripts/start-desktop-venue.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def run(v):
    v.start()
    mission = v.request('/api/missions', {'name': 'Tactical HUD - Simulation', 'briefing': 'Real keyboard, authoritative ammo / damage; no injected poses', 'durationSeconds': 300,
        'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 2, 'behavior': 'Hold', 'autoAttack': False},
        'props': [{'assetId': 'barrel', 'position': {'x': -3.4875, 'y': 0, 'z': -1.7}, 'yawDegrees': 0}]}, expected=201)
    entry = v.create(mission, [3], 'hud', role='Room3')
    peer_id = str(uuid.uuid4())
    state = v.request('/api/sessions/' + entry['id'] + '/players', {'playerId': peer_id, 'roomId': 3, 'name': 'HUD ally', 'headset': 'Quest3'}, role='Room3')
    peer = next(p for p in state['players'] if p['id'] == peer_id); entry['players'].append(peer)
    v.wait(lambda: v.request('/api/sessions/' + entry['id'] + '/world', optional=True), 90, 'native recording')
    v.launch('hud-peer', v.client_config(entry, v.ticket(entry, peer)))
    probe = v.runtime_directory / 'hud-probe'; player = entry['players'][0]
    v.launch('hud-player', v.client_config(entry, v.ticket(entry, player)), True, extra_args=['--vr-hud-probe', str(probe.resolve())])
    samples = []; seen_reload = False

    def sample():
        nonlocal seen_reload
        world = v.frame(entry, measure=True)
        try:
            source = probe / ('report.json' if (probe / 'report.json').exists() else 'status.json')
            report = json.loads(source.read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError): return None
        if report['error']: raise RuntimeError(report['error'])
        frame = report.get('frame'); hud = frame.get('hud') if frame else None
        if not hud: return None
        body = next(p for p in world['packet']['frame']['players'] if p['id'] == player['id'])
        seen_reload |= hud['reloading'] or body['reloading']
        value = {'hud': hud, 'body': body, 'worldSequence': world['packet']['sequence']}
        samples.append(value); v.save('hud-samples.json', samples)
        return value

    def until(predicate, label, seconds=30):
        return v.wait(lambda: (value if (value := sample()) and predicate(value) else None), seconds, label)

    def stage(name, **extra):
        v.stage(name, **extra); (ROOT / 'artifacts/latest-tactical-path.txt').write_text(str(v.directory), encoding='utf-8')
        until(lambda value: (v.directory / (name + '.done')).exists(), name + ' actual input / review', 240)

    v.wait(lambda: v.connected(entry), 30, 'both native clients')
    until(lambda s: s['hud']['status'] == 'AWAITING START', 'Preparing HUD')
    v.command(entry, 'Begin')
    baseline = until(lambda s: s['hud']['status'] == 'ACTIVE' and len(s['hud']['labels']) == 1, 'visible hostile and occluded hostile')
    world = v.frame(entry)['packet']['frame']; enemies = sorted(world['enemies'], key=lambda e: e['feet']['x'])
    assert len(enemies) == 2 and set(baseline['hud']['labels']) == {enemies[0]['id']}, 'Torso-obscured hostile leaked a tag'
    assert baseline['hud']['health'] == 100 and baseline['hud']['magazine'] == 30 and baseline['hud']['reserve'] == 90
    stage('fire', key='space', presses=1)
    fired = until(lambda s: s['body']['magazine'] == s['hud']['magazine'] == 29, 'authoritative ammo shown by HUD')
    stage('reload', key='r', presses=1)
    reloaded = until(lambda s: s['hud']['magazine'] == s['body']['magazine'] == 30 and s['hud']['reserve'] == s['body']['reserve'] == 89 and not s['hud']['reloading'], 'reload HUD / body')
    assert seen_reload, 'Reloading state was never displayed / accepted'
    stage('turn', key='Right', presses=20)
    turned = until(lambda s: 58 <= s['hud']['bearing'] <= 62 and peer_id in s['hud']['labels'], 'bearing and ally tag after actual keyboard turn')
    v.command(entry, 'SetEnemies', enemies={'count': 2, 'behavior': 'Hold', 'autoAttack': True})
    until(lambda s: s['body']['health'] <= 60, 'native AI damage')
    v.command(entry, 'Pause')
    damaged = until(lambda s: s['hud']['status'] == 'MISSION PAUSED' and s['hud']['health'] == s['body']['health'] and 0 < s['hud']['health'] <= 60, 'paused damaged vitals HUD')
    stage('damage-review')
    v.command(entry, 'Resume')
    eliminated = until(lambda s: s['hud']['status'] == 'ELIMINATED' and s['hud']['health'] == s['body']['health'] == 0 and not s['hud']['labels'], 'elimination wins over invalid pose warning')
    stage('eliminated-review')
    sealed = v.seal(entry)
    own = next(p for p in sealed['statistics']['players'] if p['playerId'] == player['id'])
    assert own['ammoUsed'] == 1 and own['damageTaken'] == 100 and own['hitsReceived'] == 5
    def final():
        try: value = json.loads((probe / 'report.json').read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError): return None
        return value if value['complete'] else None
    report = v.wait(final, 15, 'HUD report')
    assert report['mode'] == 'hud' and not report['error'] and report['audioSamples'] == report['callbackCount'] == 0 and not (probe / 'audio.wav').exists()
    v.evidence.extend(['Actual keyboard fire / reload agrees with HUD and sealed ammo', 'Rotated-view bearing / ally tag; occluded hostile omitted', 'Actual AI damage, Pause and eliminated HUD; no PCM captured'])
    v.summary(); v.save('hud-result.json', {'source': 'Actual Windows keyboard / GPU HUD; Simulation', 'headsets': 0, 'baseline': baseline, 'fired': fired,
        'reloaded': reloaded, 'turned': turned, 'damaged': damaged, 'eliminated': eliminated, 'captures': report['captures'], 'ownStatistics': own, 'audioCaptured': False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root', type=Path)
    p.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = p.parse_args(); args.duration = 300; args.visible_room = 3; args.job_workers = 2; args.check = False
    try: module.verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: p.error(str(error))
    v = module.Venue(args)
    try: run(v)
    except BaseException as error: v.stage('failed', errorType=type(error).__name__); raise
    finally:
        if not v.cleanup() and sys.exc_info()[0] is None: raise RuntimeError('HUD cleanup failed; inspect cleanup.json')


if __name__ == '__main__': main()
