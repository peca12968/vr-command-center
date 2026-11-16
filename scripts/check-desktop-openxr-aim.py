"""Exercise aim-only loss through Windows Unity, OpenXR, NGO and management readback."""

import argparse
import csv
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen
import uuid

from local_api import checked_api_command


spec = importlib.util.spec_from_file_location('desktop_openxr_venue', Path(__file__).with_name('start-desktop-venue.py'))
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


def sha256(path):
    with path.open('rb') as binary:
        return hashlib.file_digest(binary, 'sha256').hexdigest()


def verify(v, args):
    v.start()
    mission = v.mission(1)
    entry = v.create(mission, [1], 'aim-loss', role='Room1')
    session = '/api/sessions/' + entry['id']
    peer = entry['players'][0]['id']
    tracked = str(uuid.uuid4())
    state = v.request(session + '/players', {'playerId': tracked, 'name': 'OpenXR aim fixture', 'roomId': 1,
                                            'headset': 'ViveXr'}, role='Room1')
    entry['players'] = state['players']
    admissions = {(row['id'], row['admissionId'], row['roomId'], row['seat']) for row in entry['players']}
    v.wait(lambda: v.request(session + '/world', optional=True), 30, 'native recording')

    manifest = v.directory / 'fixture-runtime.json'
    v.save(manifest.name, {'file_format_version': '1.0.0', 'runtime': {'api_version': '1.0',
            'name': 'VR Command aim-only test', 'library_path': str(args.pose_dll)}})
    loss = v.directory / 'aim-loss.request'
    aim_ack = v.directory / 'aim-loss-ack.txt'
    trigger = v.directory / 'trigger.request'
    trigger_ack = v.directory / 'trigger-ack.txt'
    trigger.write_text('0', encoding='ascii')
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() != 'XR_RUNTIME_JSON' and not key.upper().startswith('VR_COMMAND_OPENXR_')}
    environment.update(XR_RUNTIME_JSON=str(manifest), VR_COMMAND_OPENXR_MOCK_DLL=str(args.mock_dll),
                       VR_COMMAND_OPENXR_AIM_LOSS_FILE=str(loss), VR_COMMAND_OPENXR_AIM_LOSS_ACK=str(aim_ack),
                       VR_COMMAND_OPENXR_TRIGGER_COMMAND=str(trigger), VR_COMMAND_OPENXR_TRIGGER_ACK=str(trigger_ack))

    clients = {row['id']: entry['name'] + ('-tracked' if row['id'] == tracked else '-peer') for row in entry['players']}
    for player in sorted(entry['players'], key=lambda row: row['id'] == tracked):
        identity = player['id']
        config = v.client_config(entry, v.ticket(entry, player))
        if identity == tracked:
            v.launch(clients[identity], config, visible=True, extra_args=('-force-d3d11', '--vr-openxr'),
                     environment=environment)
        else:
            v.launch(clients[identity], config)

    def client_log(identity):
        path = v.directory / (clients[identity] + '.log')
        return path.read_text(encoding='utf-8', errors='replace') if path.exists() else ''

    def connections(identity):
        return re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', client_log(identity), flags=re.M)

    v.stage('awaiting_admission')
    v.wait(lambda: all(connections(identity) for identity in clients), 30, 'signed desktop and OpenXR admissions')
    original = {identity: connections(identity) for identity in clients}
    startup = ['VR_OPENXR_STARTUP status=requested', 'VR_OPENXR_STARTUP status=active']
    assert [line for line in client_log(tracked).splitlines() if line.startswith('VR_OPENXR_STARTUP ')] == startup
    assert 'Runtime Name: Unity Mock Runtime' in client_log(tracked)
    assert 'VR_OPENXR_STARTUP ' not in client_log(peer)
    v.save('runtime-identity.json', {'playerSha256': sha256(args.player_exe), 'mockSha256': sha256(args.mock_dll),
                                    'poseDllSha256': sha256(args.pose_dll), 'startup': startup})

    def ack(path, expected):
        return path.is_file() and path.read_text(encoding='ascii').splitlines() == expected

    v.wait(lambda: ack(aim_ack, ['0 7']), 15, 'initial aim and both grips tracked')
    v.wait(lambda: ack(trigger_ack, ['0 0']), 10, 'initial trigger neutral')
    revision = v.command(entry, 'Begin')['appliedAtSequence']
    frames = {}

    def sample(name, available, minimum_tick, rounds=None, *, after_press=False):
        def checkpoint():
            readiness = v.request(session + '/readiness')
            rows = {row['playerId']: row for row in readiness['players']}
            observed = readiness['observedSequence']
            current = readiness['sessionSequence']
            # An accepted shot appends a combat record to the management sequence.
            same_round = revision <= observed <= current if after_press else observed == current == revision
            if (readiness['sourceState'] != 'Fresh' or not same_round or not readiness['worldSequence']
                    or {(row['playerId'], row['admissionId'], row['roomId'], row['seat']) for row in rows.values()} != admissions
                    or not rows[peer]['canParticipate'] or rows[peer]['rigKind'] != 'Simulated'
                    or rows[tracked]['canParticipate'] is not available
                    or rows[tracked]['state'] != ('Participating' if available else 'PoseUnavailable')):
                return None
            original_frame = v.request(f'{session}/world/frames/{readiness["worldSequence"]}')
            frame = original_frame['packet']['frame']
            players = {row['id']: row for row in frame['players']}
            if (original_frame['packet']['observedSequence'] != observed or frame['phase'] != 'Running'
                    or frame['tick'] < minimum_tick or not players[peer]['connected']
                    or players[tracked]['connected'] is not available):
                return None
            player = players[tracked]
            if available and player['rig']['kind'] != 'Tracked':
                return None
            if rounds is not None:
                if player['magazine'] < rounds:
                    raise RuntimeError('The server accepted more than the expected trigger presses')
                if player['magazine'] != rounds:
                    return None
            return original_frame, player, readiness

        value, player, readiness = v.wait(checkpoint, 16, name)
        frames[name] = value
        v.save(name + '.json', {'world': value, 'readiness': readiness})
        return value['packet']['frame']['tick'], player

    initial_tick, player = sample('running', True, 1)
    magazine = player['magazine']
    loss.touch(exist_ok=False)
    v.wait(lambda: ack(aim_ack, ['0 7', '1 7']), 10, 'right aim untracked while both grips remain tracked')
    lost_tick, _ = sample('aim-lost', False, initial_tick + 1)
    trigger.write_text('1', encoding='ascii')
    trigger_witness = ['0 0', '1 1']
    v.wait(lambda: ack(trigger_ack, trigger_witness), 10, 'held trigger synced during aim loss')
    held_tick, _ = sample('held-during-loss', False, lost_tick + 15)
    loss.unlink()
    v.wait(lambda: ack(aim_ack, ['0 7', '1 7', '0 7']), 10, 'aim tracking restores with both grips')
    recovered_tick, recovered = sample('held-after-recovery', True, held_tick + 15, magazine)
    assert recovered['head'] == player['head'] and recovered['rig'] == player['rig']
    trigger.write_text('0', encoding='ascii')
    trigger_witness.append('0 0')
    v.wait(lambda: ack(trigger_ack, trigger_witness), 10, 'trigger release synced')
    released_tick, _ = sample('released', True, recovered_tick + 15, magazine)
    trigger.write_text('2', encoding='ascii')
    trigger_witness.extend(('2 1', '2 0'))
    v.wait(lambda: ack(trigger_ack, trigger_witness), 10, 'new trigger tap synced')
    shot_tick, _ = sample('new-press', True, released_tick + 1, magazine - 1, after_press=True)
    sample('after-press', True, shot_tick + 15, magazine - 1, after_press=True)
    assert all(connections(identity) == original[identity] and len(original[identity]) == 1
               and 'VR_CLIENT_DISCONNECTED' not in client_log(identity) for identity in clients)

    sealed = v.seal(entry)
    totals = {tracked: 1, peer: 0}
    assert {row['playerId']: row['ammoUsed'] for row in sealed['statistics']['players']} == totals
    for name, saved in frames.items():
        sequence = saved['packet']['sequence']
        assert v.request(f'{session}/world/frames/{sequence}') == saved, f'Closed frame changed: {name}'
    first = frames['released']['packet']['sequence'] + 1
    last = frames['after-press']['packet']['sequence']
    shots = []
    for sequence in range(first, last + 1):
        packet = v.request(f'{session}/world/frames/{sequence}')['packet']
        shots.extend({'frameSequence': sequence, 'event': event} for event in packet['events'] if event['kind'] == 'ShotFired')
    assert len(shots) == 1 and shots[0]['event']['playerId'] == tracked
    v.save('accepted-shot.json', shots[0])
    request = Request(v.base + session + '/report.csv', headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    with urlopen(request, timeout=5) as response:
        report = response.read()
    (v.directory / 'report.csv').write_bytes(report)
    rows = list(csv.DictReader(io.StringIO(report.decode('utf-8-sig'))))
    assert len(rows) == 2 and all(row['rowType'] == 'Player' and row['sessionId'] == entry['id']
                                  and row['streamId'] == sealed['world']['header']['streamId'] for row in rows)
    assert {row['playerId']: int(row['ammoUsed']) for row in rows} == totals
    assert v.wait_for_player_results(entry)['allAcknowledged']
    assert not v.request('/api/sessions')
    v.evidence.extend(frames)
    v.summary()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=desktop.ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--mock-dll', type=Path, required=True)
    parser.add_argument('--pose-dll', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    desktop.add_api_arguments(parser)
    args = parser.parse_args()
    args.duration = 300
    args.job_workers = 2
    args.check = True
    try:
        args.mock_dll = args.mock_dll.resolve(strict=True)
        args.pose_dll = args.pose_dll.resolve(strict=True)
        desktop.verify_player(args)
        checked_api_command(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    v = desktop.Venue(args, artifact_family='desktop-openxr-aim')
    try:
        verify(v, args)
    finally:
        if not v.cleanup():
            raise RuntimeError('See cleanup.json for native fixture cleanup errors')


if __name__ == '__main__':
    main()
