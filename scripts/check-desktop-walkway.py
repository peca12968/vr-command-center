"""Compare a solid wall and its saved opening with W input in owned Windows players."""
import argparse
import importlib.util
import re
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


venue = module('walkway_venue', 'start-desktop-venue.py')
capacity = module('walkway_capacity', 'check-desktop-capacity.py')
debrief = module('walkway_debrief', 'check-desktop-debrief.py')
practice = module('walkway_practice', 'start-desktop-demo.py')


def player_position(frame, player):
    rows = frame['players']
    if len(rows) != 1:
        raise RuntimeError('Unexpected participant count')
    body = rows[0]
    head = body['head']
    if (body['id'] != player['id'] or body['roomId'] != 3 or not body['connected']
            or body['rig']['kind'] != 'Simulated' or body['health'] != 100
            or body['magazine'] != 30 or body['reserve'] != 90
            or abs(head['x'] + 3) > .02 or abs(head['y'] - 1.65) > .01):
        raise RuntimeError('Original standing participant, axis or game state changed')
    return head['z']


def exercise(v, mission, label):
    route = v.request(f'/api/missions/{mission["id"]}/layout')['routePreview']['seats'][0]
    opened = label == 'opening'
    expected_path = [{'x': -3, 'z': -3 + index * .5} for index in range(7)] if opened else []
    if route != {'seat': 0, 'path': expected_path}:
        raise RuntimeError('The saved layout preview differs from the expected test route')
    v.save(label + '-preview.json', route)
    entry = v.create(mission, [3], label, role='Room3')
    v.clients([entry])
    client = label + '-client-3'
    player = entry['players'][0]
    world = v.request(f'/api/sessions/{entry["id"]}/world')['header']
    expected = {(p['position']['x'], 0, -1) for p in mission['definition']['props']}
    geometry = world['props']
    if (len(geometry) != len(expected) or {(p['feet']['x'], p['feet']['y'], p['feet']['z']) for p in geometry} != expected
            or any(p['kind'] != 'Sandbag' or p['roomId'] != 3 or p['yaw'] != 0 for p in geometry)):
        raise RuntimeError('Actual world cover differs from the saved mission')
    begin = v.command(entry, 'Begin')['appliedAtSequence']
    references = {}

    def sample(predicate):
        value = v.frame(entry, measure=True)
        packet = value['packet']
        if packet['frame']['phase'] != 'Running' or packet['observedSequence'] < begin or packet['frame']['tick'] <= 0:
            return None
        if packet['suspended']:
            raise RuntimeError('World suspended during input')
        z = player_position(packet['frame'], player)
        return packet if predicate(z) else None

    references['before'] = v.wait(lambda: sample(lambda z: abs(z + 3) < .001), 20, label + ' original spawn')

    def input_stage(stage, predicate, taps):
        v.stage(stage, playerPid=v.processes[client].pid, key='w', targetTaps=taps, review=stage + '.review.json')
        path = v.directory / (stage + '.review.json')
        review = v.wait(lambda: venue.read_json(path) if path.exists() else None, 180, stage + ' keyboard review')
        if review != {'version': 1, 'stage': stage, 'key': 'w', 'taps': taps, 'pid': v.processes[client].pid}:
            raise RuntimeError('Keyboard review does not match the original input stage')
        references[stage] = v.wait(lambda: sample(predicate), 8, stage + ' accepted position')
        v.save(label + '-references.json', references)

    if opened:
        input_stage('input-opening-cross', lambda z: z >= 0, 120)
    else:
        contact = lambda z: -1.67 <= z <= -1.649
        input_stage('input-wall-contact', contact, 72)
        initial = references['input-wall-contact']
        contact_z = player_position(initial['frame'], player)
        input_stage('input-wall-continue', lambda z: contact(z) and abs(z - contact_z) <= .01, 36)
        if references['input-wall-continue']['sequence'] <= initial['sequence']:
            raise RuntimeError('Continued movement lacks a later source sample')

    sealed = v.seal(entry)
    delivery = v.wait_for_player_results(entry)
    result = debrief.validate_result(debrief.final_result(v, client), entry, player, sealed)
    connection = re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', debrief.log_text(v, client), re.M)
    acks = re.findall(r'^VR_SERVER_DEBRIEF_ACK id=(\d+)$', debrief.log_text(v, label + '-server'), re.M)
    if not delivery['allAcknowledged'] or len(connection) != 1 or connection != acks:
        raise RuntimeError('Original player did not acknowledge the sealed result')
    csv = practice.save_report(v, entry, sealed['statistics'], filename=label + '-report.csv')
    v.stop_round(entry)
    return entry, begin, references, {'result': result, 'csv': csv}


def replay(v, entry, begin, references):
    final = entry['sealed']['world']
    request = urllib.request.Request(v.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&rate=4',
        headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    expected = {packet['sequence']: packet for packet in references.values()}
    matched, band = set(), 0
    maximum, previous, count = -3., -3., 0
    deadline = time.monotonic() + final['durationMilliseconds'] / 4000 + 30
    with urllib.request.urlopen(request, timeout=10) as response:
        for value in capacity.sse_frames(response):
            count += 1
            packet = value['packet']
            frame = packet['frame']
            if packet['sequence'] != count or time.monotonic() > deadline:
                raise RuntimeError('Replay skipped frames or exceeded its playback bound')
            if count in expected:
                if packet != expected[count]:
                    raise RuntimeError('Saved replay differs from the live input checkpoint')
                matched.add(count)
            if frame['phase'] == 'Running' and packet['observedSequence'] >= begin:
                z = player_position(frame, entry['players'][0])
                if packet['suspended'] or z + .01 < previous:
                    raise RuntimeError('Unexpected suspended or backwards W path')
                previous = z
                maximum = max(maximum, z)
                band += int(-1.64 < z < -.36)
    if count != final['acceptedSequence'] or matched != set(expected):
        raise RuntimeError('Replay did not retain all input checkpoints and the final sequence')
    if entry['name'] == 'wall' and (maximum > -1.649 or band):
        raise RuntimeError('Solid wall incorrectly allowed forward passage')
    if entry['name'] == 'opening' and (maximum < 0 or not band):
        raise RuntimeError('No saved motion through the opening to midfield')
    return {'frames': count, 'matchedCheckpoints': len(matched), 'insideWallBandFrames': band, 'maximumZ': maximum}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--api-dll', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    args = parser.parse_args()
    args.duration, args.visible_room, args.job_workers, args.check = 600, 3, 2, True
    venue.verify_player(args)
    v = venue.Venue(args, artifact_family='desktop-walkway')
    try:
        v.stage('starting')
        v.start()
        props = [{'assetId': 'sandbag', 'position': {'x': x, 'y': 0, 'z': -1}, 'yawDegrees': 0}
                 for x in range(-5, 6, 2)]
        definition = {'name': 'Desktop walkway', 'briefing': 'W toward the saved cover line', 'durationSeconds': 600,
                      'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
                      'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': props}
        first = v.request('/api/missions', definition, expected=201)
        second = v.request(f'/api/missions/{first["id"]}/revisions',
            {**definition, 'props': [p for p in props if p['position']['x'] != -3]},
            expected=201, request_id=str(uuid.uuid4()))
        runs = [exercise(v, first, 'wall'), exercise(v, second, 'opening')]
        evidence = {}
        for entry, begin, references, receipts in runs:
            evidence[entry['name']] = {**replay(v, entry, begin, references), **receipts}
        v.evidence.extend(['Same original seat stops at solid cover after repeated W',
                           'Original seat crosses the saved opening and reaches midfield',
                           'Original accepted frames, results and CSV match both sealed replays'])
        v.summary()
    except BaseException as error:
        v.stage('failed', errorType=type(error).__name__)
        raise
    finally:
        failed = sys.exc_info()[0] is not None
        if not v.cleanup() and not failed:
            v.stage('failed', errorType='CleanupError')
            raise RuntimeError('Walkway cleanup failed')
    v.save('walkway-result.json', {'complete': True, 'input': 'Targeted Windows keyboard W', 'headsets': 0, 'rounds': evidence})


if __name__ == '__main__':
    main()
