"""Real native countdown across separate management / publication outages. No synthetic gameplay input."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import time
import urllib.request
import uuid
from venue_http_gate import VenueHttpGate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fault_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)
vm = debrief.venue_module


def management_suspension(log, observed_sequence, resumed_sequence, *, delayed=False):
    # Read message lines only. Unity emits separate stack traces after warnings.
    events = [line for line in log.splitlines() if line.startswith(
        ('VR_MANAGEMENT_REFRESH_FAILED ', 'VR_AUTHORITY_SUSPENDED ', 'VR_AUTHORITY_RESUMED '))]
    cause = 'ManagementWatchdog' if delayed else 'ManagementRefresh'
    expected = [
        rf'VR_AUTHORITY_SUSPENDED reason={cause} observedSequence={observed_sequence} '
        r'managementAgeSeconds=([\d.]+) monotonicSeconds=([\d.]+)',
        rf'VR_AUTHORITY_RESUMED observedSequence={resumed_sequence} phase=Running monotonicSeconds=([\d.]+)',
    ]
    if not delayed:
        expected.insert(0, r'VR_MANAGEMENT_REFRESH_FAILED reason=ProtocolError httpStatus=503 elapsedSeconds=[\d.]+ monotonicSeconds=([\d.]+)')
    matches = [re.fullmatch(pattern, event) for pattern, event in zip(expected, events)]
    if len(events) != len(expected) or not all(matches):
        raise RuntimeError('Native suspension diagnostics did not distinguish the original management fault')
    times = [float(match.groups()[-1]) for match in matches]
    management_age = float(matches[-2].group(1))
    if times != sorted(times) or times[-2] == times[-1] or (delayed and management_age < 1.5):
        raise RuntimeError('Native suspension diagnostics are out of order')
    if resumed_sequence != observed_sequence:
        raise RuntimeError('Management recovery changed the original observed sequence')
    return {'events': events, 'cause': cause, 'managementAgeSeconds': management_age,
            'observedSequence': observed_sequence, 'resumedSequence': resumed_sequence}


def fingerprint():
    digest = hashlib.sha256()
    for name in ['check-desktop-clock-faults.py', 'venue_http_gate.py', 'check-desktop-debrief.py', 'start-desktop-venue.py']:
        digest.update(name.encode()); digest.update((ROOT / 'scripts' / name).read_bytes())
    return digest.hexdigest()


class FaultVenue(vm.Venue):
    proxy = None
    def launch(self, name, config, visible=False, *, extra_args=()):
        if config['role'] == 'Server' and (not self.args.five_room_isolation or name == 'room-1-server'):
            self.proxy = VenueHttpGate(self.base, config['sessionId']).start()
            config = {**config, 'managementApiUrl': self.proxy.base}
        probe = self.runtime_directory / (name + '-replica')
        if not (self.args.five_room_isolation or self.args.five_room_linked):
            extra_args = (*extra_args, '--vr-replication-probe', str(probe))
        super().launch(name, config, visible, extra_args=extra_args)


def replay(venue, entry, sealed, limit, *, frozen_tick=None, isolation=False):
    expected = venue.frame(entry); previous, last, maximum, due_running, suspended = 0, None, 0, 0, 0
    message = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4', headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    deadline = time.monotonic() + sealed['world']['durationMilliseconds'] / 4000 + 20
    with urllib.request.urlopen(message, timeout=10) as response:
        kind = ''
        for raw in response:
            if time.monotonic() > deadline: raise RuntimeError('Replay exceeded its observation bound')
            line = raw.decode().strip()
            if line.startswith('event: '): kind = line[7:]
            if kind != 'frame' or not line.startswith('data: '): continue
            row = json.loads(line[6:]); packet = row['packet']; frame = packet['frame']
            if packet['sequence'] != previous + 1 or not maximum <= frame['tick'] <= limit: raise RuntimeError('Replay sequence / clock boundary invalid')
            previous, last, maximum = packet['sequence'], row, frame['tick']
            due_running += frame['tick'] == limit and frame['phase'] == 'Running'
            suspended += packet['suspended']
            if isolation:
                if packet['suspended'] and (frozen_tick is None or frame['phase'] != 'Paused' or frame['tick'] != frozen_tick):
                    raise RuntimeError('Replay suspension left the selected room or its frozen tick')
                if frame['phase'] == 'Paused' and not packet['suspended']:
                    raise RuntimeError('Unexpected operator pause in the isolation fixture')
    expects_suspension = not isolation or frozen_tick is not None
    if previous != sealed['world']['acceptedSequence'] or last != expected or last['packet']['frame']['phase'] != 'Ended' or not due_running or bool(suspended) != expects_suspension:
        raise RuntimeError('Sealed replay lost the suspension, deadline or exact final ledger')
    return {'frames': previous, 'maximumTick': maximum, 'dueRunningFrames': due_running, 'suspendedFrames': suspended, 'finalPacketAndStatisticsMatch': True}


def require_live_room(entry, packet, phase, *, require_fresh_pose=True):
    frame = packet['frame']
    expected = {player['id']: player['roomId'] for player in entry['players']}
    players = frame['players']
    if frame['phase'] != phase or packet['suspended'] != (phase == 'Paused'):
        raise RuntimeError(f'{entry["name"]} expected {phase} at frame {packet["sequence"]}, got {frame["phase"]}')
    if (packet['observedSequence'] < entry['beginSequence'] or len(players) != len(expected)
            or {player['id']: player['roomId'] for player in players} != expected):
        raise RuntimeError(f'{entry["name"]} changed its original room roster at frame {packet["sequence"]}')
    if require_fresh_pose and any(not player['connected'] or player['rig']['kind'] != 'Simulated' for player in players):
        raise RuntimeError(f'{entry["name"]} lost an original fresh simulated pose at frame {packet["sequence"]}')


def client_name(entry, player):
    if len(entry['roomIds']) == 1:
        return f'{entry["name"]}-client-{player["seat"]}'
    return f'{entry["name"]}-client-{player["roomId"]}-{player["seat"]}'


def linked_room_views(venue, entry, *packets):
    views = []
    for packet in packets:
        route = f'/api/sessions/{entry["id"]}/world/frames/{packet["sequence"]}?observerRoomId='
        for room in entry['roomIds']:
            view = venue.request(route + str(room), role=f'Room{room}')
            projected = view['packet']
            expected = [player for player in packet['frame']['players'] if player['roomId'] == room]
            if (view['observerRoomId'] != room or len(expected) != 5 or projected['frame']['players'] != expected
                    or any(projected[key] != packet[key] for key in ('sequence', 'observedSequence', 'suspended'))
                    or any(projected['frame'][key] != packet['frame'][key] for key in ('phase', 'tick'))
                    or {player['playerId'] for player in view['statistics']} != {player['id'] for player in expected}
                    or any(player['roomId'] != room for player in view['statistics'])):
                raise RuntimeError(f'Room {room} view differs from its original linked frame')
            venue.request(route + str(room % 5 + 1), role=f'Room{room}', expected=403)
            views.append({'roomId': room, 'worldSequence': packet['sequence'], 'phase': packet['frame']['phase'],
                          'tick': packet['frame']['tick'], 'players': len(expected), 'otherRoomRejected': True})
    return views


def five_room_management_delay(venue):
    linked = venue.args.five_room_linked
    rooms = list(range(1, 6))
    mission = venue.request('/api/missions', {
        'name': 'Five-room management delay', 'briefing': 'One owned management GET is delayed',
        'durationSeconds': 60,
        'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': [],
    }, expected=201)
    entries = [venue.create(mission, rooms, 'linked')] if linked else [
        venue.create(mission, [room], f'room-{room}') for room in rooms]
    for entry in entries:
        for room in entry['roomIds']:
            for _ in range(4):
                identity = str(uuid.uuid4())
                roster = venue.request(f'/api/sessions/{entry["id"]}/players', {
                    'playerId': identity, 'roomId': room, 'name': f'PC room {room}', 'headset': 'Quest3',
                }, role=f'Room{room}')
                entry['players'].append(next(player for player in roster['players'] if player['id'] == identity))
        venue.wait(lambda: venue.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, entry['name'] + ' recording')
        for player in entry['players']:
            venue.launch(client_name(entry, player), venue.client_config(entry, venue.ticket(entry, player)))
    for entry in entries:
        venue.wait(lambda: venue.connected(entry), 100, entry['name'] + ' original rigs')
    for entry in entries:
        venue.command(entry, 'SetMissionClock', missionClock={'autoEnd': True})
        entry['beginSequence'] = venue.command(entry, 'Begin')['appliedAtSequence']

    def packet(entry):
        route = f'/api/sessions/{entry["id"]}/world'
        meta = venue.request(route)
        sequence = meta['acceptedSequence']
        value = venue.request(f'{route}/frames/{sequence}')['packet']
        captured = datetime.fromisoformat(meta['capturedAtUtc'])
        age = (datetime.now(timezone.utc) - captured).total_seconds()
        entry['sourceAges'].append(age)
        if value['sequence'] != sequence or value['elapsedMilliseconds'] != meta['durationMilliseconds'] or not -1 <= age < 1.5:
            raise RuntimeError(f'{entry["name"]} could not read a fresh exact accepted frame {sequence} (age {age}s)')
        return {'packet': value, 'capturedAtUtc': captured.isoformat(timespec='microseconds')}

    def running(entry):
        value = packet(entry)['packet']
        return value if value['frame']['phase'] == 'Running' and value['frame']['tick'] >= 100 else None

    before = {entry['name']: venue.wait(lambda: running(entry), 20, entry['name'] + ' active clock') for entry in entries}
    for entry in entries:
        require_live_room(entry, before[entry['name']], 'Running')
    target, *peers = entries
    venue.proxy.block('management-delay')
    if linked:
        venue.stage('linked-management-delayed', rooms=rooms)
    else:
        venue.stage('one-room-management-delayed', room=1)
    venue.wait(lambda: venue.proxy.snapshot()['counts']['managementDelayed'] == 1, 5, 'one original management GET')

    def suspended():
        value = packet(target)
        return value if value['packet']['suspended'] else None

    paused = venue.wait(suspended, 5, target['name'] + ' watchdog suspension')
    require_live_room(target, paused['packet'], 'Paused', require_fresh_pose=False)

    def peer_sample(entry, *, after_utc, after_tick=0):
        value = packet(entry)
        return value if value['capturedAtUtc'] >= after_utc and value['packet']['frame']['tick'] > after_tick else None

    peer_before, peer_after = {}, {}
    if peers:
        with ThreadPoolExecutor(max_workers=4) as pool:
            def sample_peers(label, threshold):
                futures = [pool.submit(venue.wait, lambda entry=entry: peer_sample(entry, **threshold(entry)), 2, label)
                           for entry in peers]
                return {entry['name']: future.result() for entry, future in zip(peers, futures, strict=True)}

            peer_before = sample_peers('peer frame inside room 1 suspension', lambda entry: {'after_utc': paused['capturedAtUtc']})
            time.sleep(.4)
            peer_after = sample_peers('peer clock advances inside room 1 suspension', lambda entry: {
                'after_utc': peer_before[entry['name']]['capturedAtUtc'],
                'after_tick': peer_before[entry['name']]['packet']['frame']['tick'],
            })
    else:
        time.sleep(.4)
    last_capture = max((value['capturedAtUtc'] for value in peer_after.values()), default=paused['capturedAtUtc'])

    def later_frame():
        value = packet(target)
        return value if (value['capturedAtUtc'] >= last_capture
                         and value['packet']['sequence'] > paused['packet']['sequence']) else None

    still = venue.wait(later_frame, 2, target['name'] + ' second suspended frame')
    frozen_tick = paused['packet']['frame']['tick']
    witness = {'paused': paused, 'stillPaused': still, 'peersBefore': peer_before, 'peersAfter': peer_after}

    venue.save('isolation-witness.json', witness)
    # While the authority is suspended, the existing 0.5 s pose freshness
    # timer can mark a body disconnected. Verify transport in the client logs.
    require_live_room(target, still['packet'], 'Paused', require_fresh_pose=False)
    if (still['packet']['frame']['tick'] != frozen_tick
            or still['packet']['observedSequence'] != paused['packet']['observedSequence']
            or venue.state(target)['state'] != 'Running'):
        raise RuntimeError('Delayed room did not retain its running management state and frozen game clock')
    for entry in peers:
        first, last = peer_before[entry['name']]['packet'], peer_after[entry['name']]['packet']
        require_live_room(entry, first, 'Running')
        require_live_room(entry, last, 'Running')
        if (last['frame']['tick'] <= first['frame']['tick'] or last['sequence'] <= first['sequence']
                or last['observedSequence'] != first['observedSequence']
                or peer_before[entry['name']]['capturedAtUtc'] < paused['capturedAtUtc']):
            raise RuntimeError('An unaffected room did not advance during the selected suspension')
    venue.proxy.release()

    def recovered():
        value = packet(target)['packet']
        return value if (not value['suspended'] and value['frame']['tick'] > frozen_tick
                         and all(player['connected'] for player in value['frame']['players'])) else None

    resumed = venue.wait(recovered, 10, target['name'] + ' resumes on the same management revision')
    require_live_room(target, resumed, 'Running')
    diagnostics = management_suspension(debrief.log_text(venue, target['name'] + '-server'), paused['packet']['observedSequence'],
                                        resumed['observedSequence'], delayed=True)
    witness.update(resumed=resumed, diagnostics=diagnostics)
    venue.save('isolation-witness.json', witness)
    if linked:
        witness['roomViews'] = linked_room_views(venue, target, still['packet'], resumed)
        venue.save('isolation-witness.json', witness)
    venue.stage('rooms-running-after-recovery')
    venue.wait(lambda: all(venue.state(entry)['state'] == 'Ended' for entry in entries), 75, 'original mission-clock Ends')
    limit = 1200
    results = []
    for entry in entries:
        sealed = venue.seal(entry)
        delivery = venue.wait_for_player_results(entry)
        if not delivery['allAcknowledged'] or delivery['timedOut']:
            raise RuntimeError('Original room results did not all reach their clients')
        for player in entry['players']:
            name = client_name(entry, player)
            result = debrief.final_result(venue, name)
            debrief.validate_result(result, entry, player, sealed)
            events = [line.split(' ', 1)[0] for line in debrief.log_text(venue, name).splitlines()
                      if line.startswith(('VR_CLIENT_CONNECTED ', 'VR_CLIENT_DISCONNECTED', 'VR_CLIENT_DEBRIEF_FINAL '))]
            if events[:2] != ['VR_CLIENT_CONNECTED', 'VR_CLIENT_DEBRIEF_FINAL'] or events[2:] not in ([], ['VR_CLIENT_DISCONNECTED']):
                raise RuntimeError(f'{name} did not keep its original UDP connection through its final result')
        admissions = {player['admissionId'] for player in entry['players']}

        def recorded_receipts():
            info = venue.request(f'/api/sessions/{entry["id"]}/world?includeDebriefReceipts=true')
            rows = (info.get('debriefReceipts') or {}).get('players', [])
            return rows if len(rows) == len(admissions) and {row['admissionId'] for row in rows if row['acknowledged']} == admissions else None

        receipts = venue.wait(recorded_receipts, 5, 'original management debrief acknowledgements', required={'api'})
        events = venue.request(f'/api/sessions/{entry["id"]}/events?after=0&limit=500')
        expiry = [event for event in events if event['kind'] == 'ControlApplied' and event['payload'].get('clockExpiration')]
        if len(expiry) != 1 or expiry[0]['payload']['clockExpiration']['tick'] != limit or expiry[0]['actor']['id'] != 'mission-clock':
            raise RuntimeError('Room deadline did not commit exactly one original End')
        location = {'roomIds': entry['roomIds']} if linked else {'room': entry['roomIds'][0]}
        results.append({**location, 'sessionId': entry['id'], 'receipts': receipts, 'automaticEnd': expiry[0]})
        venue.stop_round(entry)
    with ThreadPoolExecutor(max_workers=5) as pool:
        replays = [pool.submit(replay, venue, entry, entry['sealed'], limit,
                               frozen_tick=frozen_tick if entry is target else None, isolation=True) for entry in entries]
        for result, future in zip(results, replays, strict=True):
            result['replay'] = future.result()
    if venue.request('/api/sessions'):
        raise RuntimeError('An isolation fixture session is still active')
    topology = {'topology': 'Linked', 'sessions': results, 'roomViews': witness['roomViews']} if linked else {'rooms': results}
    return {'complete': False, **topology,
            'managementDiagnostics': diagnostics, 'frozenTick': frozen_tick,
            'playerBuildReceipt': venue.receipt, 'scope': '25 same-host Windows simulated players'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--seconds', type=int, choices=[60, 180], default=180, help='Bounded active duration, below the existing probe 240-second lifetime')
    parser.add_argument('--delay-management', action='store_true',
                        help='Hold the original management GET until the native watchdog suspends the server')
    multiplayer = parser.add_mutually_exclusive_group()
    multiplayer.add_argument('--five-room-isolation', action='store_true',
                             help='Delay room 1 management while 25 clients occupy five independent rooms')
    multiplayer.add_argument('--five-room-linked', action='store_true',
                             help='Delay shared management while 25 clients occupy one linked session')
    args = parser.parse_args(); args.duration = 230; args.job_workers = 2; args.visible_room = 0; args.check = True
    five_room = args.five_room_isolation or args.five_room_linked
    if five_room and (not args.delay_management or args.seconds != 60):
        parser.error('Five-room modes require --delay-management --seconds 60')
    vm.verify_player(args, python_listener=True); original_fingerprint = fingerprint(); venue = FaultVenue(args, artifact_family='desktop-clock-faults')
    report = None; proxy_closed = False
    try:
        venue.start()
        if five_room:
            multiplayer_report = five_room_management_delay(venue)
            venue.proxy.close(); proxy_closed = True
            gate = venue.proxy.snapshot()
            venue.save('proxy-final.json', gate)
            if (gate['limitsTriggered'] or gate['activeTunnels'] or gate['counts']['managementDelayed'] != 1
                    or any(gate['counts'][name] for name in ('managementBlocked', 'handlerErrors', 'routeRejected', 'capacityRejected'))):
                raise RuntimeError('Management proxy did not preserve the original delayed request')
            report = {**multiplayer_report, 'proxy': gate, 'toolFingerprint': original_fingerprint}
            return
        mission = venue.request('/api/missions', {'name': 'PC clock fault recovery', 'briefing': 'Separate owned management and publication failures', 'durationSeconds': args.seconds,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        entry = venue.create(mission, [3], 'clock-fault'); venue.clients([entry])
        names = ['clock-fault-server', 'clock-fault-client-3']; counters = dict.fromkeys(names, 0)
        def capture(name=names[0]):
            counters[name] += 1; number = counters[name]
            if number > 64: raise RuntimeError('Native capture request bound exceeded')
            directory = venue.runtime_directory / (name + '-replica'); vm.atomic_json(directory / 'capture.request', number)
            return venue.wait(lambda: vm.read_json(directory / f'capture-{number}.json') if (directory / f'capture-{number}.json').exists() else None, 5, 'native replicated snapshot')
        def frame(): return venue.frame(entry)['packet']
        venue.command(entry, 'SetMissionClock', missionClock={'autoEnd': True}); venue.command(entry, 'Begin')
        venue.wait(lambda: frame()['frame']['tick'] >= 100, 20, 'active native timer')
        venue.proxy.block('management-delay' if args.delay_management else 'management')
        venue.stage('management-blocked', delayed=args.delay_management)
        if args.delay_management:
            venue.wait(lambda: venue.proxy.snapshot()['counts']['managementDelayed'] == 1, 5, 'one original pending management GET')
        paused = venue.wait(lambda: (f if (f := frame())['suspended'] and f['frame']['phase'] == 'Paused' else None), 8, 'management suspension')
        frozen_tick = paused['frame']['tick']; management_samples = [capture()]; hold_started = time.monotonic()
        for _ in range(3):
            time.sleep(.35 if args.delay_management else 1.75); sample = capture(); management_samples.append(sample)
            accepted = frame()
            if sample['presentation']['tick'] != frozen_tick or sample['ready'] or sample['phase'] != 'Paused' or accepted['frame']['tick'] != frozen_tick or not accepted['suspended']:
                raise RuntimeError('Management outage consumed mission ticks or hid suspension')
            if venue.state(entry)['state'] != 'Running': raise RuntimeError('Source suspension incorrectly changed management lifecycle')
        hold_seconds = time.monotonic() - hold_started
        venue.proxy.release(); resumed = venue.wait(lambda: (f if not (f := frame())['suspended'] and f['frame']['phase'] == 'Running' and f['frame']['tick'] > frozen_tick else None), 10, 'same-policy recovery')
        diagnostics = management_suspension(debrief.log_text(venue, names[0]), paused['observedSequence'],
                                            resumed['observedSequence'], delayed=args.delay_management)
        limit = args.seconds * 20
        venue.stage('running-before-publication-fault', durationSeconds=args.seconds, resumedTick=resumed['frame']['tick'])
        venue.wait(lambda: frame()['frame']['tick'] >= limit - 100, args.seconds + 10, 'near deadline')
        venue.proxy.block('publication'); venue.stage('publication-blocked')
        venue.wait(lambda: venue.proxy.snapshot()['counts']['publicationBlocked'] > 0, 5, 'publication retry sees the outage')
        accepted_before_due = frame()
        if accepted_before_due['frame']['tick'] >= limit: raise RuntimeError('Fault missed the unaccepted deadline boundary')
        due = None; observation_deadline = time.monotonic() + 10
        while time.monotonic() < observation_deadline:
            sample = capture()
            if sample['presentation']['tick'] == limit and not sample['ready']: due = sample; break
            time.sleep(.35)
        if due is None: raise RuntimeError('Local authority did not freeze at the native deadline')
        due_client = capture(names[1]); held_samples = [due]; due_started = time.monotonic()
        for _ in range(3):
            time.sleep(2); sample = capture(); held_samples.append(sample)
            if sample['presentation']['tick'] != limit or sample['ready'] or sample['phase'] != 'Running': raise RuntimeError('Unpublished due authority did not remain frozen')
            current = frame()
            if current['sequence'] != accepted_before_due['sequence'] or venue.state(entry)['state'] != 'Running': raise RuntimeError('Unaccepted deadline incorrectly authorized an End')
        due_hold_seconds = time.monotonic() - due_started
        if due_client['presentation']['tick'] != limit or due_client['ready']: raise RuntimeError('Client replica failed to receive the local due boundary')
        # Finish diagnostics before normal client disconnect and before their fixed 240-second cap.
        for name in names:
            directory = venue.runtime_directory / (name + '-replica'); (directory / 'finish.request').write_text('finish\n')
            probe = venue.wait(lambda d=directory: vm.read_json(d / 'report.json') if (d / 'report.json').exists() else None, 5, 'complete native probe')
            if not probe['complete'] or probe['truncated'] or probe['sendQueueErrors']: raise RuntimeError('Native observation incomplete / overflowed')
        venue.proxy.release(); venue.stage('publication-restored', dueTick=limit)
        venue.wait(lambda: venue.state(entry)['state'] == 'Ended', 20, 'accepted buffered deadline End')
        sealed = venue.seal(entry); results = venue.wait_for_player_results(entry)
        if not results['allAcknowledged']: raise RuntimeError('Final result was not acknowledged after recovery')
        result = debrief.final_result(venue, names[1]); debrief.validate_result(result, entry, entry['players'][0], sealed)
        def recorded_receipt():
            info = venue.request(f'/api/sessions/{entry["id"]}/world?includeDebriefReceipts=true')
            rows = (info.get('debriefReceipts') or {}).get('players', [])
            return next((row for row in rows if row['admissionId'] == result['admissionId'] and row['acknowledged']), None)
        receipt = venue.wait(recorded_receipt, 5, 'original management debrief acknowledgement')
        events = venue.request(f'/api/sessions/{entry["id"]}/events?after=0&limit=500')
        expiry = [event for event in events if event['kind'] == 'ControlApplied' and event['payload'].get('clockExpiration')]
        if len(expiry) != 1 or expiry[0]['payload']['clockExpiration']['tick'] != limit or expiry[0]['actor']['id'] != 'mission-clock': raise RuntimeError('Deadline was not committed exactly once')
        venue.proxy.close(); proxy_closed = True; gate = venue.proxy.snapshot()
        venue.save('proxy-final.json', gate)
        if args.delay_management and (gate['counts']['managementDelayed'] != 1 or gate['counts']['managementBlocked']):
            raise RuntimeError('Expected one delayed original management request without a forced HTTP error')
        if gate['limitsTriggered'] or gate['activeTunnels'] or gate['counts']['handlerErrors'] or gate['counts']['routeRejected'] or gate['counts']['capacityRejected'] or gate['counts']['webSockets'] < 2:
            raise RuntimeError('Fault proxy scope / bounds / reconnection invalid')
        report = {'complete': False, 'source': 'Actual Windows Unity UDP / native local replicas; Simulation rigs', 'headsets': 0, 'durationSeconds': args.seconds,
            'playerBuildReceipt': venue.receipt, 'toolFingerprint': original_fingerprint, 'managementPausedTick': frozen_tick, 'managementHoldSeconds': hold_seconds,
            'managementSamples': management_samples, 'managementDiagnostics': diagnostics,
            'resumedPacket': resumed, 'acceptedBeforeDue': accepted_before_due,
            'localDueSamples': held_samples, 'clientDue': due_client, 'unacceptedDueHoldSeconds': due_hold_seconds, 'proxy': gate,
            'automaticEnd': expiry[0], 'sealed': sealed, 'clientResult': result,
            'managementDebriefReceipt': receipt, 'replay': replay(venue, entry, sealed, limit),
            'checks': ['management loss visibly freezes the authority and published clock', 'same policy resumes without resetting elapsed ticks',
                       'publication loss does not pause an otherwise managed timer', 'native server and client freeze at exact due tick before API acceptance',
                       'unaccepted local due time cannot authorize End', 'restored publication commits exactly one internal End',
                       'both seals, targeted result and management acknowledgement match the original admission', 'entire sealed replay is contiguous and never exceeds the deadline',
                       'native logs identify the management fault, authority suspension and recovery in order']}
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__); raise
    finally:
        if venue.proxy: venue.proxy.release()
        cleanup = venue.cleanup()
        if venue.proxy and not proxy_closed: venue.proxy.close()
        if report is not None:
            if fingerprint() != original_fingerprint: raise RuntimeError('Tool sources changed during the native run')
            report['complete'] = cleanup; venue.save('checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Fault fixture cleanup failed')
        if five_room and report and report['complete']:
            topology = 'one linked session across five rooms' if args.five_room_linked else 'five independent rooms'
            print(f'PASS: {topology} and 25 original acknowledgements; Simulation only', flush=True)
    if not report or not report['complete']: raise RuntimeError('Fault check incomplete')
    print('PASS: 9 native clock fault checks; Simulation only', flush=True)


if __name__ == '__main__': main()
