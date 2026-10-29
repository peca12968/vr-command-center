"""Verify native desktop cover movement using actual keyboard input.

Starts its own API, room-3 server and visible Simulation client. For each stage,
use the displayed player window, then create <stage>.done in the printed evidence
directory. The marker only acknowledges input; accepted native world frames decide
the result. No poses or combat are injected. All fixture writers are closed before
the optional SSD runtime snapshot is copied back to F.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_venue', ROOT / 'scripts/start-desktop-venue.py')
venue_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(venue_module)


def run(venue):
    venue.start()
    mission = venue.request('/api/missions', {
        'name': 'Native desktop collision - Simulation', 'briefing': 'Actual keyboard only; no injected poses', 'durationSeconds': 1800,
        'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False},
        'props': [{'assetId': 'sandbag', 'position': {'x': -3.9, 'y': 0, 'z': -2}, 'yawDegrees': 0},
                  {'assetId': 'barrel', 'position': {'x': -2.5, 'y': 0, 'z': -1.3}, 'yawDegrees': 45}]}, expected=201)
    entry = venue.create(mission, [3], 'collision', role='Room3'); venue.clients([entry]); venue.command(entry, 'Begin')
    venue.wait(lambda: venue.frame(entry)['packet']['frame']['phase'] == 'Running', 20, 'Running')
    samples, results = [], []

    def sample(stage):
        value = venue.frame(entry, measure=True)
        body = next(p for p in value['packet']['frame']['players'] if p['id'] == entry['players'][0]['id'])
        samples.append({'stage': stage, 'body': body, 'frame': value['packet']['sequence']})
        venue.save('collision-samples.json', samples)
        return body

    sample('before')
    for name, key, count in [('sandbag', 'w', 17), ('retreat', 's', 5), ('sidestep', 'd', 10), ('barrel', 'w', 20)]:
        venue.stage('input-' + name, key=key, presses=count, source='Simulation', headsets=0)
        (ROOT / 'artifacts/latest-collision-path.txt').write_text(str(venue.directory), encoding='utf-8')

        def completed():
            sample('waiting-' + name)
            return (venue.directory / (name + '.done')).exists()

        venue.wait(completed, 600, 'real keyboard input: ' + name)
        time.sleep(.8)
        body = sample('after-' + name)
        assert body['connected'] and body['rig']['kind'] == 'Simulated', 'Native pose rejected or wrong rig source'
        assert body['health'] == 100 and body['magazine'] == 30 and body['reserve'] == 90, 'Player state reset'
        if name == 'sandbag': assert -2.72 < body['head']['z'] < -2.649, 'Sandbag crossing or movement missing'
        if name == 'retreat': assert body['head']['z'] < -2.82, 'Cannot retreat from cover'
        if name == 'sidestep': assert body['head']['x'] > -2.6, 'Cannot sidestep around sandbag'
        if name == 'barrel': assert -2.27 < body['head']['z'] < -2.21, 'Rotated barrel crossing or movement missing'
        results.append({'stage': name, 'key': key, 'presses': count, 'body': body})
        venue.evidence.append(name + ': native accepted pose and unchanged health / ammunition')
    venue.seal(entry); venue.summary()
    venue.save('collision-result.json', {'stages': results, 'source': 'Actual Unity Windows keyboard; Simulation',
        'headsets': 0, 'playerBuildReceipt': venue.receipt})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--runtime-root', type=Path)
    args = parser.parse_args(); args.visible_room = 3; args.job_workers = 2; args.duration = 1800; args.check = False
    try: venue_module.verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: parser.error(str(error))
    venue = venue_module.Venue(args)
    try: run(venue)
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__)
        raise
    finally:
        if not venue.cleanup() and sys.exc_info()[0] is None:
            raise RuntimeError('Collision cleanup / snapshot failed; inspect cleanup.json')


if __name__ == '__main__': main()
