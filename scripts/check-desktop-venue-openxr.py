"""Exercise the 25-seat start policy with native desktop players and one OpenXR mock rig."""

import argparse
import importlib.util
from pathlib import Path
import uuid


spec = importlib.util.spec_from_file_location('guarded_openxr', Path(__file__).with_name('check-desktop-guarded-openxr.py'))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
field = native.field

ROOMS = list(range(1, 6))
PHASE = '/api/venue/phase'


class MixedVenue(native.GuardedVenue):
    def launch(self, name, config, visible=False, *, extra_args=(), environment=None):
        if config['role'] == 'Server':
            extra_args = (*extra_args, '--vr-peer-diagnostics')
        return super().launch(name, config, visible, extra_args=extra_args, environment=environment)


def session_route(entry):
    return '/api/sessions/' + entry['id']


def run(venue, mode):
    venue.start()
    scopes = [ROOMS] if mode == 'Linked' else [[room] for room in ROOMS]
    entries = []
    clients = {}
    tracked_id = None
    for scope in scopes:
        name = f'{mode.lower()}-room-{scope[0]}'
        mission = venue.mission(scope[0], name=f'{mode} VR 25 席追蹤混合測試 · 房間 {scope[0]}',
                                briefing='Windows 桌面玩家及一席原生 OpenXR Mock Runtime')
        entry = venue.create(mission, scope, name)
        entries.append(entry)
        route = session_route(entry)
        for room in scope:
            for seat in range(2, 6):
                player_id = str(uuid.uuid4())
                tracked = room == 5 and seat == 5
                state = venue.request(route + '/players', {'playerId': player_id, 'roomId': room,
                    'name': f'房間 {room} 席位 {seat}', 'headset': 'ViveXr' if tracked else 'Quest3'}, role=f'Room{room}')
                entry['players'].append(next(player for player in state['players'] if player['id'] == player_id))
                if tracked:
                    tracked_id = player_id
        for player in entry['players']:
            clients[player['id']] = (entry, player, f"{name}-client-{player['roomId']}-{player['seat']}")

    assert len(clients) == 25 and tracked_id in clients
    for entry in entries:
        world = venue.wait(lambda: venue.request(session_route(entry) + '/world', optional=True), 35, entry['name'] + ' recording')
        assert world['header']['origin'] == 'Simulation' and world['header']['roomIds'] == entry['roomIds']
        entry['streamId'] = world['header']['streamId']
    for player_id, (entry, player, name) in clients.items():
        if player_id != tracked_id:
            venue.launch(name, venue.client_config(entry, venue.ticket(entry, player)))
    tracked_entry, tracked_player, tracked_name = clients[tracked_id]
    loss, ack = native.launch_openxr(venue, tracked_entry, tracked_player, tracked_name)
    venue.stage('waiting-for-roster', mode=mode, players=len(clients))

    def read_all(live_rig, acknowledgement, after=0):
        def read():
            if not ack.is_file() or ack.read_text(encoding='ascii').splitlines() != acknowledgement:
                return None
            reports = {}
            for entry in entries:
                report = venue.request(session_route(entry) + '/readiness')
                if (report['sourceState'] != 'Fresh' or report['origin'] != 'Simulation'
                        or report['observedSequence'] != report['sessionSequence']
                        or entry is tracked_entry and report['worldSequence'] <= after):
                    return None
                rows = {row['playerId']: row for row in report['players']}
                assert set(rows) == {player['id'] for player in entry['players']}
                for player in entry['players']:
                    row = rows[player['id']]
                    assert (row['admissionId'], row['roomId'], row['seat']) == (player['admissionId'], player['roomId'], player['seat'])
                    rig = live_rig if player['id'] == tracked_id else 'Simulated'
                    if row['rigKind'] != rig or row['canParticipate'] is not (rig != 'None'):
                        return None
                reports[entry['id']] = report
            return reports

        return venue.wait(read, 35, f'{mode} 25-seat Preparing readiness with tracked seat {live_rig}')

    def venue_command(body, *, expected=200, key=None):
        return venue.request(PHASE, body, expected=expected, request_id=key or str(uuid.uuid4()))

    first = read_all('Tracked', ['0 7'])
    targets = venue.request(PHASE)['begin']
    assert {target['sessionId']: target['sessionSequence'] for target in targets} == {
        session: report['sessionSequence'] for session, report in first.items()}
    tracked_only = venue_command({'action': 'Begin', 'targets': targets, 'requireFullTracking': True}, expected=409)
    assert tracked_only['code'] == 'venue-begin-not-ready' and tracked_only['roomIds'] == ROOMS

    loss.touch(exist_ok=False)
    missing = read_all('None', ['0 7', '1 7'], first[tracked_entry['id']]['worldSequence'])
    body = {'action': 'Begin', 'targets': targets, 'requireFullParticipation': True}
    request_id = str(uuid.uuid4())
    denied = venue_command(body, expected=409, key=request_id)
    assert denied['code'] == 'venue-begin-not-ready' and denied['roomIds'] == [5]
    assert venue.request(PHASE)['begin'] == targets
    assert all(venue.state(entry)['state'] == 'Preparing' for entry in entries)
    venue.save('rejected-start.json', {'fullTracking': tracked_only, 'withoutSeat': denied,
                                      'requestId': request_id, 'targets': targets})

    loss.unlink()
    recovered = read_all('Tracked', ['0 7', '1 7', '0 7'], missing[tracked_entry['id']]['worldSequence'])
    venue.save('readiness-transition.json', {'trackedPlayerId': tracked_id, 'before': first, 'lost': missing, 'recovered': recovered})
    receipt = venue_command(body, key=request_id)
    duplicate = venue_command(body, key=request_id)
    assert receipt['requireFullParticipation'] is True and receipt['duplicate'] is False
    assert duplicate == {**receipt, 'duplicate': True}
    venue.save('accepted-start.json', {'receipt': receipt, 'duplicate': duplicate, 'requestId': request_id})

    by_session = {row['sessionId']: row for row in receipt['sessions']}
    assert set(by_session) == {entry['id'] for entry in entries}
    openings = {}
    running = {}
    for entry in entries:
        session = entry['id']
        route = session_route(entry)
        applied = by_session[session]['appliedAtSequence']
        assert applied == recovered[session]['sessionSequence'] + 1
        events = venue.request(route + f'/events?after={applied - 1}&limit=1')
        event, = events
        proof = event['venue']['participationFrame']
        assert event['sequence'] == applied and event['venue']['requireFullParticipation'] is True
        assert proof['streamId'] == entry['streamId'] and proof['worldSequence'] >= recovered[session]['worldSequence']
        openings[session] = {'requestId': request_id, 'appliedAtSequence': applied, 'frame': proof}

        def verify_running():
            packet = venue.frame(entry)['packet']
            frame = packet['frame']
            if frame['phase'] != 'Running' or frame['tick'] <= 0 or packet['observedSequence'] < applied:
                return None
            poses = {row['id']: row['rig']['kind'] for row in frame['players'] if row['connected'] is True}
            expected = {p['id']: 'Tracked' if p['id'] == tracked_id else 'Simulated' for p in entry['players']}
            return packet if poses == expected else None

        running[session] = venue.wait(verify_running, 20, entry['name'] + ' Running with its full roster')
    venue.save('running-frames.json', running)
    end = venue_command({'action': 'End', 'targets': venue.request(PHASE)['end']})
    ended_at = {row['sessionId']: row['appliedAtSequence'] for row in end['sessions']}
    assert set(ended_at) == set(by_session)
    venue.save('ended.json', end)
    for entry in entries:
        sealed = venue.seal(entry)
        applied = ended_at[entry['id']]
        events = venue.request(session_route(entry) + f'/events?after={applied - 1}&limit=3')
        command_event, seal_event = events
        assert (command_event['sequence'], command_event['kind']) == (applied, 'ControlApplied')
        assert (seal_event['sequence'], seal_event['kind']) == (sealed['statistics']['throughSequence'], 'CombatStreamSealed')
        entry['endedAtSequence'] = applied
        results = venue.wait_for_player_results(entry)
        expected_names = {name for player_entry, _, name in clients.values() if player_entry is entry}
        assert results['allAcknowledged'] and set(results['phases']) == expected_names
    venue.evidence.extend(('25 original admissions', 'tracked-only refusal', 'fifth room pose loss refused atomically',
                           'restored pose permits the same 25-seat request once', 'all native rooms reached Running',
                           'both recordings sealed with 25 terminal player results'))
    venue.summary(source='Windows native UDP / NGO; one OpenXR Mock Runtime rig and 24 simulated rigs')
    return entries, clients, openings, tracked_id


def verify_closed(venue, entries, clients, openings, tracked_id):
    def log(name):
        return (venue.directory / (name + '.log')).read_text(encoding='utf-8', errors='replace')

    checkpoints = native.desktop.read_json(venue.directory / 'readiness-transition.json')
    reports = {}
    for entry in entries:
        session = entry['id']
        sealed = entry['sealed']
        world, statistics = sealed['world'], sealed['statistics']
        final = native.desktop.read_json(venue.directory / (entry['name'] + '-latest-frame.json'))['packet']
        combat = final['throughCombatSequence']
        through, ended = statistics['throughSequence'], final['observedSequence']
        assert ended == entry['endedAtSequence']
        stream = world['header']['streamId']
        ledger = {row['playerId']: row for row in statistics['players']}
        sources = {}
        connections = set()
        for player_id, (player_entry, player, name) in clients.items():
            if player_entry is not entry:
                continue
            content = log(name)
            source, rig = field.windows_player_source(content, entry['port'])
            assert (source, rig) == (('windows-openxr-mock-tracked', 'Tracked') if player_id == tracked_id
                                     else ('windows-desktop-simulated', 'Simulated'))
            connection, result = field.client_result(content, require_startup=True, startup_port=entry['port'])
            assert connection not in connections
            connections.add(connection)
            assert (result['sessionId'], result['streamId'], result['playerId'], result['admissionId'],
                    result['roomId'], result['throughSequence'], result['worldSequence'], result['finalStreamSequence']) == (
                    session, stream, player_id, player['admissionId'], player['roomId'], through, world['acceptedSequence'], combat)
            assert all(result[key] == ledger[player_id][key] for key in
                       ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'accuracyPercent', 'health'))
            sources[player_id] = {'roomId': player['roomId'], 'rigKind': rig, 'source': source, 'runningFrames': 0}
        peers, acknowledged, approved, _ = field.server_connections(log(entry['name'] + '-server'), entry['port'])
        assert set(peers) == acknowledged == set(approved) == connections
        assert all(endpoint.startswith('127.0.0.1:') for endpoint in peers.values())
        telemetry = venue.runtime_directory / (entry['name'] + '-telemetry')
        steps = ('before', 'lost', 'recovered')
        observed = {step: checkpoints[step][session]['worldSequence'] for step in steps}
        remaining = set(steps)

        def check_preparing(packet):
            for step, sequence in observed.items():
                if packet['sequence'] != sequence:
                    continue
                frame = packet['frame']
                assert frame['phase'] == 'Preparing' and frame['tick'] == 0 and packet['suspended'] is False
                assert packet['observedSequence'] == checkpoints[step][session]['sessionSequence']
                expected = {player_id: source['rigKind'] for player_id, source in sources.items()
                            if step != 'lost' or player_id != tracked_id}
                actual = {row['id']: row['rig']['kind'] for row in frame['players'] if row['connected'] is True}
                assert actual == expected
                remaining.remove(step)

        world_proof = field.verify_world_journal(telemetry / (session + '.worldlog'), world, combat, through, ended,
            player_sources=sources, guarded_begin=('participationBegin', openings[session]),
            players={row['id']: row for row in entry['players']}, on_packet=check_preparing)
        combat_proof = field.verify_combat_journal(telemetry / (session + '.journal'), session, stream, 'Simulation',
                                                  combat, ended, ledger)
        assert not remaining and all(row['runningFrames'] > 0 for row in sources.values())
        reports[session] = {'rooms': entry['roomIds'], 'world': world_proof, 'combat': combat_proof,
                            'preparingFrames': observed, 'opening': openings[session], 'sources': sources,
                            'serverAcknowledgements': len(acknowledged)}
    venue.save('closed-readback.json', reports)
    assert sum(value['serverAcknowledgements'] for value in reports.values()) == 25


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    native.add_native_arguments(parser)
    parser.add_argument('--mode', choices=('Independent', 'Linked'), required=True)
    args = parser.parse_args()
    args.duration, args.job_workers, args.check = 300, 2, False
    try:
        native.verify_native_inputs(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    venue = MixedVenue(args, artifact_family='desktop-venue-openxr')
    try:
        closed = run(venue, args.mode)
    finally:
        if not venue.cleanup():
            raise RuntimeError('See cleanup.json for native test cleanup errors')
    verify_closed(venue, *closed)
    venue.stage('passed', mode=args.mode, checks=len(venue.evidence), closedJournalVerified=True)


if __name__ == '__main__':
    main()
