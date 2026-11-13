"""Real native countdown across separate management / publication outages. No synthetic gameplay input."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import time
import urllib.request
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
        if config['role'] == 'Server':
            self.proxy = VenueHttpGate(self.base, config['sessionId']).start()
            config = {**config, 'managementApiUrl': self.proxy.base}
        probe = self.runtime_directory / (name + '-replica')
        super().launch(name, config, visible, extra_args=(*extra_args, '--vr-replication-probe', str(probe)))


def replay(venue, entry, sealed, limit):
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
    if previous != sealed['world']['acceptedSequence'] or last != expected or last['packet']['frame']['phase'] != 'Ended' or not due_running or not suspended:
        raise RuntimeError('Sealed replay lost the suspension, deadline or exact final ledger')
    return {'frames': previous, 'maximumTick': maximum, 'dueRunningFrames': due_running, 'suspendedFrames': suspended, 'finalPacketAndStatisticsMatch': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--seconds', type=int, choices=[60, 180], default=180, help='Bounded active duration, below the existing probe 240-second lifetime')
    parser.add_argument('--delay-management', action='store_true',
                        help='Hold the original management GET until the native watchdog suspends the server')
    args = parser.parse_args(); args.duration = 230; args.job_workers = 2; args.visible_room = 0; args.check = True
    vm.verify_player(args); original_fingerprint = fingerprint(); venue = FaultVenue(args, artifact_family='desktop-clock-faults')
    report = None; proxy_closed = False
    try:
        venue.start()
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
    if not report or not report['complete']: raise RuntimeError('Fault check incomplete')
    print('PASS: 9 native clock fault checks; Simulation only', flush=True)


if __name__ == '__main__': main()
