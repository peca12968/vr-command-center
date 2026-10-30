"""Verify the visible rifle, reticle and actual aimed hits with real keyboard input.

Own API / native server / normal visible Simulation client. No input, poses or
combat are injected by this script; .done files acknowledge the external UI steps.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rifle_venue', ROOT / 'scripts/start-desktop-venue.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def run(v):
    v.start()
    mission = v.request('/api/missions', {'name': 'Aimed rifle hit - Simulation', 'briefing': 'Actual keyboard aim / two shots; no injected poses or combat',
        'durationSeconds': 600, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
    entry = v.create(mission, [3], 'rifle', role='Room3'); v.clients([entry]); v.command(entry, 'Begin')
    player = entry['players'][0]['id']; observations = []

    def observe(stage):
        value = v.frame(entry, measure=True); frame = value['packet']['frame']
        own = next(p for p in frame['players'] if p['id'] == player)
        if not own['connected'] or own['rig']['kind'] != 'Simulated': return None
        if own['health'] != 100: raise RuntimeError('Unexpected damage in the held-fire fixture')
        observations.append({'stage': stage, 'sequence': value['packet']['sequence'], 'body': own, 'enemies': frame['enemies']})
        v.save('rifle-samples.json', observations)
        return own, frame['enemies']

    baseline = v.wait(lambda: observe('baseline'), 30, 'connected player')
    assert baseline[0]['magazine'] == 30 and baseline[1][0]['health'] == 100
    v.stage('aim', source='Simulation', headsets=0, leftPresses=14, downPresses=5,
            note='Use actual Left then Down keys in the native window; review the target and reticle, then create aim.done')
    v.wait(lambda: observe('aim-wait') and (v.directory / 'aim.done').exists(), 240, 'actual aim input')
    aimed = observe('aimed'); assert aimed is not None
    assert aimed[0]['head'] == baseline[0]['head'] and aimed[0]['magazine'] == 30, 'Aiming changed player position or ammunition'
    v.stage('fire', source='Simulation', headsets=0, key='space', presses=2,
            note='Two separate actual Space presses; accepted world and sealed hit statistics decide the result')
    v.wait(lambda: observe('fire-wait') and (v.directory / 'fire.done').exists(), 240, 'actual fire input')
    def hit():
        value = observe('hit-wait')
        return value if value and value[0]['magazine'] == 28 and value[1][0]['health'] == 0 else None
    after = v.wait(hit, 20, 'two actual aimed hits and elimination')
    v.stage('review', health=after[0]['health'], magazine=after[0]['magazine'], enemyHealth=after[1][0]['health'])
    v.wait(lambda: observe('review-wait') and (v.directory / 'review.done').exists(), 120, 'native hit review')
    sealed = v.seal(entry); stats = next(p for p in sealed['statistics']['players'] if p['playerId'] == player)
    assert stats['ammoUsed'] == 2 and stats['shotsHit'] == 2 and stats['kills'] == 1 and stats['accuracyPercent'] == 100
    assert stats['damageTaken'] == stats['hitsReceived'] == 0 and stats['health'] == 100
    assert sealed['world']['header']['assetSet'] == 'combatants-v1'
    v.save('rifle-result.json', {'source': 'Actual normal Windows player keyboard / native GPU review; Simulation', 'headsets': 0,
        'baseline': baseline, 'aimed': aimed, 'after': after, 'statistics': stats, 'replayStatisticsMatch': sealed['replayStatisticsMatch'],
        'poseOrCombatInjected': False, 'diagnosticProbeEnabled': False})
    v.evidence.extend(['Actual keyboard reticle aim without moving player', 'Two actual shots / two hits / one kill agree with sealed replay and statistics'])
    v.summary()


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--runtime-root', type=Path)
    p.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = p.parse_args(); args.duration = 600; args.visible_room = 3; args.job_workers = 2; args.check = False
    try: module.verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: p.error(str(error))
    v = module.Venue(args)
    try: run(v)
    except BaseException as error: v.stage('failed', errorType=type(error).__name__); raise
    finally:
        if not v.cleanup() and sys.exc_info()[0] is None: raise RuntimeError('Rifle cleanup failed; inspect cleanup.json')


if __name__ == '__main__': main()
