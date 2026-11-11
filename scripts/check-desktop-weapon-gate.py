"""Observe real keyboard fire/reload before and after native AI elimination.

Each printed step requires its own .done marker after actual UI input. Markers
only advance observation. World state and the rendered submission counter decide
acceptance. Uses fresh owned Simulation data, without GPU readback or PCM.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


venue = module('weapon_gate_venue', 'start-desktop-venue.py')
debrief = module('weapon_gate_debrief', 'check-desktop-debrief.py')
capacity = module('weapon_gate_capacity', 'check-desktop-capacity.py')


def run(v):
    v.start()
    mission = v.request('/api/missions', {
        'name': 'Desktop weapon eligibility', 'briefing': 'Actual keyboard observation',
        'durationSeconds': 600,
        'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False}, 'props': []
    }, expected=201)
    entry = v.create(mission, [3], 'weapon', role='Room3')
    player = entry['players'][0]
    probe = v.runtime_directory / 'weapon-hud'
    v.launch('weapon-player', v.client_config(entry, v.ticket(entry, player)), True,
             extra_args=['--vr-hud-trace', str(probe.resolve())])

    def sample():
        source = v.frame(entry, measure=True)
        try:
            path = probe / ('report.json' if (probe / 'report.json').exists() else 'status.json')
            report = json.loads(path.read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        if report['error']:
            raise RuntimeError(report['error'])
        frame = report.get('frame')
        hud = frame.get('hud') if frame else None
        if not hud:
            return None
        if 'weaponSubmissions' not in hud or 'weaponPresses' not in hud:
            raise RuntimeError('Build the submission-counter diagnostic before this check')
        body = next(row for row in source['packet']['frame']['players'] if row['id'] == player['id'])
        return {'hud': hud, 'body': body, 'worldSequence': source['packet']['sequence']}

    def until(predicate, label):
        return v.wait(lambda: value if (value := sample()) and predicate(value) else None, 30, label)

    def review(name, key):
        before = until(lambda value: True, name + ' initial rendered state')
        v.stage(name, key=key, presses=1)
        marker = v.directory / (name + '.done')
        v.wait(lambda: marker.exists(), 180, name + ' actual keyboard input')
        return until(lambda value: value['hud']['renderedAtSeconds'] > before['hud']['renderedAtSeconds'] + .25
                     and value['hud']['weaponPresses'] > before['hud']['weaponPresses'],
                     name + ' fresh rendered state')

    v.wait(lambda: v.connected(entry), 40, 'original player admission')
    v.command(entry, 'Begin')
    baseline = until(lambda value: value['hud']['status'] == 'ACTIVE' and value['body']['health'] == 100,
                     'active rendered player')
    if baseline['hud']['weaponSubmissions'] != 0:
        raise RuntimeError('The original player already submitted weapon input')
    observations = {'baseline': baseline}
    review('alive-fire', 'space')
    observations['aliveFire'] = until(lambda value: value['hud']['weaponSubmissions'] == 1
                                    and value['hud']['magazine'] == value['body']['magazine'] == 29,
                                    'one accepted keyboard shot')
    review('alive-reload', 'r')
    observations['aliveReload'] = until(lambda value: value['hud']['weaponSubmissions'] == 2
                                      and value['hud']['magazine'] == value['body']['magazine'] == 30
                                      and value['hud']['reserve'] == value['body']['reserve'] == 89
                                      and not value['hud']['reloading'], 'one accepted keyboard reload')
    v.command(entry, 'SetEnemies', enemies={'count': 1, 'behavior': 'Hold', 'autoAttack': True})
    observations['eliminated'] = until(lambda value: value['hud']['status'] == 'ELIMINATED'
                                      and value['hud']['health'] == value['body']['health'] == 0,
                                      'native AI elimination')
    observations['eliminatedFire'] = review('eliminated-fire', 'space')
    observations['eliminatedReload'] = review('eliminated-reload', 'r')
    accepted = all(observations[name]['hud']['weaponSubmissions'] == 2
                   for name in ('eliminated', 'eliminatedFire', 'eliminatedReload'))
    v.save('weapon-input-observations.json', observations)
    if any(not all(observations[name]['hud'][field] for field in ('ready', 'poseAccepted', 'connected', 'tracking'))
           for name in ('eliminated', 'eliminatedFire', 'eliminatedReload')):
        raise RuntimeError('Elimination check also lost control, pose acceptance, connection or tracking')
    sealed = v.seal(entry)
    delivery = v.wait_for_player_results(entry)
    if not delivery['allAcknowledged'] or delivery['timedOut']:
        raise RuntimeError('Original player did not acknowledge its sealed result')
    result = debrief.final_result(v, 'weapon-player')
    debrief.validate_result(result, entry, player, sealed)
    if (result['ammoUsed'], result['hitsReceived'], result['damageTaken'], result['health']) != (1, 5, 100, 0):
        raise RuntimeError('Final ammunition or AI damage differs from the original input')
    connections = re.findall(r'VR_CLIENT_CONNECTED id=(\d+)', debrief.log_text(v, 'weapon-player'))
    acknowledgments = re.findall(r'^VR_SERVER_DEBRIEF_ACK id=(\d+)\s*$', debrief.log_text(v, 'weapon-server'), re.M)
    if len(connections) != 1 or acknowledgments != connections:
        raise RuntimeError('Result acknowledgment belongs to another native connection')
    report = capacity.practice.save_report(v, entry, sealed['statistics'], filename='weapon-report.csv')
    v.stop_round(entry)
    rows = []
    request = urllib.request.Request(v.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',
                                    headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    with urllib.request.urlopen(request, timeout=10) as response:
        for value in capacity.sse_frames(response):
            if value['packet']['sequence'] != len(rows) + 1:
                raise RuntimeError('Original replay skipped a frame')
            rows.append(value)
    if len(rows) != sealed['world']['acceptedSequence'] or rows[-1]['statistics'] != sealed['statistics']['players']:
        raise RuntimeError('Replay differs from the original sealed result')
    v.save('weapon-replay.json', rows)
    previous = None
    for value in rows:
        packet = value['packet']
        if packet['frame']['phase'] != 'Running':
            previous = None
            continue
        if packet['suspended'] or previous is not None and packet['elapsedMilliseconds'] - previous >= 1500:
            raise RuntimeError('Running replay violates the original source continuity limit')
        previous = packet['elapsedMilliseconds']
    v.evidence.extend(['Actual keyboard shot and reload accepted before elimination',
                       'Native AI elimination and exact original result / acknowledgment / CSV / replay'])
    if accepted:
        v.evidence.append('Actual keyboard fire and reload after elimination submit no new weapon RPC')
    v.summary()
    return {'complete': False, 'executionFinished': True, 'acceptancePassed': accepted,
            'observations': observations, 'result': result, 'csv': report, 'replayFrames': len(rows),
            'scope': 'One native Windows player and server, actual keyboard, Simulation, no headset'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get(
        'VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args()
    args.duration = 600
    args.visible_room = 3
    args.job_workers = 2
    args.check = False
    venue.verify_player(args)
    v = venue.Venue(args)
    try:
        result = run(v)
        v.save('weapon-gate-result.json', result)
        if not result['acceptancePassed']:
            raise RuntimeError('Eliminated desktop player still submitted keyboard weapon requests')
    except BaseException as error:
        v.stage('failed', errorType=type(error).__name__)
        raise
    finally:
        failed = sys.exc_info()[0] is not None
        if not v.cleanup() and not failed:
            raise RuntimeError('Weapon input cleanup incomplete')
    result['complete'] = True
    v.save('weapon-gate-result.json', result)
    v.stage('passed', checks=len(v.evidence))


if __name__ == '__main__':
    main()
