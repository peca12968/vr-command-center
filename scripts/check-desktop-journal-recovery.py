"""Abruptly stop an isolated native PC game and recover only its durable source."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def load(script, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture = load('check-desktop-seal-faults.py', 'recovery_seal')
world = load('analyze-world-journal.py', 'recovery_world')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def world_numbers(value):
    # Unity and System.Text.Json print float fields with different decimal precision.
    if isinstance(value, float):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    if isinstance(value, list):
        return [world_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: world_numbers(item) for key, item in value.items()}
    return value


def packets(path):
    # The closed-source analyzer has already verified envelopes and sequence limits.
    with path.open('rb') as source:
        source.seek(8)
        while size := source.read(4):
            payload = source.read(struct.unpack('<i', size)[0])
            source.seek(32, 1)
            if payload[0] == 1:
                yield json.loads(payload[1:])


def replay(venue, route, boundary):
    url = venue.base + route + '/watch?mode=replay&fromFrame=1&throughFrame=latest&rate=4'
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + venue.tokens['Room3']})
    deadline = time.monotonic() + boundary['durationMilliseconds'] / 4000 + 15
    events = []
    with urllib.request.urlopen(request, timeout=8) as response:
        assert response.headers.get_content_type() == 'text/event-stream'
        for raw in response:
            assert time.monotonic() < deadline
            line = raw.decode().strip()
            if line.startswith('event: '):
                kind = line[7:]
            elif line.startswith('data: '):
                events.append((kind, json.loads(line[6:])))
    assert events[0] == ('header', boundary) and events[-1] == ('saved-end', boundary)
    assert all(kind == 'frame' or (kind == 'status' and data == boundary) for kind, data in events[1:-1])
    return [frame for kind, frame in events[1:-1] if kind == 'frame']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-root', 'player-exe', 'api-dll'):
        parser.add_argument('--' + name, required=True, type=Path)
    for name in ('before-build', 'after-build', 'recovery-exe'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--browser', action='store_true', help='Also observe the real recovery in Chromium')
    args = parser.parse_args()
    portable = args.recovery_exe is not None
    if (portable and (args.before_build or args.after_build)) or (not portable and not (args.before_build and args.after_build)):
        parser.error('Provide either --recovery-exe or both --before-build and --after-build')
    if portable:
        args.recovery_exe = args.recovery_exe.resolve(strict=True)
    args.job_workers, args.visible_room = 2, 0
    try:
        fixture.vm.verify_player(args, python_listener=True)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    venue = fixture.SealVenue(args, artifact_family='desktop-journal-recovery')
    report = {}
    browser = browser_log = None
    try:
        venue.start()
        mission = venue.request('/api/missions', {
            'name': 'Durable PC journal recovery', 'briefing': 'Isolated native process loss',
            'durationSeconds': 60, 'props': [],
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': True}}, expected=201)
        entry = venue.create(mission, [3], 'recovery')
        def recover(label, *, reason=None):
            work = venue.runtime_directory / label
            env = dict(os.environ, DOTNET_ROOT=str(venue.runtime_directory / 'no-dotnet'),
                       DOTNET_MULTILEVEL_LOOKUP='0', PATH=str(Path(os.environ['WINDIR']) / 'System32'),
                       DOTNET_BUNDLE_EXTRACT_BASE_DIR=str(venue.runtime_directory / 'recovery-extract'))
            run = subprocess.run([str(args.recovery_exe), '--recover-server', str(venue.directory / 'recovery-server.json'),
                                  '--work', str(work)], cwd=venue.runtime_directory, env=env,
                                 capture_output=True, encoding='utf-8', timeout=45)
            assert not any(key in run.stdout + run.stderr for key in venue.tokens.values())
            venue.save(label + '.json', {'returnCode': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
            if reason:
                assert run.returncode == 1 and not (work / 'recovery.json').exists()
                assert json.loads(run.stderr)['reason'] == reason
                if reason == 'IOException':
                    assert not work.exists()
                return None
            assert run.returncode == 0, run.stderr
            proof = json.loads((work / 'recovery.json').read_bytes())
            assert proof == json.loads(run.stdout) and proof['recoverySucceeded'] and not proof['gameplayRestarted']
            return proof

        venue.clients([entry])
        venue.command(entry, 'Begin')
        session = '/api/sessions/' + entry['id']
        route = session + '/world'
        venue.wait(lambda: any(p['damageTaken'] > 0 for p in venue.frame(entry)['statistics']), 20, 'actual AI damage')
        venue.proxy.block('publication-combat')
        venue.wait(lambda: all(venue.proxy.snapshot()['counts'][name] > 0
                               for name in ('publicationBlocked', 'combatBatchBlocked')), 10, 'both publication faults')
        time.sleep(2)
        server = venue.processes['recovery-server']
        assert server.poll() is None and venue.state(entry)['state'] == 'Running'
        if portable:
            recover('original-still-locked', reason='IOException')
        venue.stop('recovery-server')
        assert server.returncode != 0
        venue.proxy.release()
        venue.stage('native-server-stopped', pid=server.pid, exitCode=server.returncode)

        source = venue.runtime_directory / 'recovery-telemetry' / entry['id']
        original_world, original_combat = source.with_suffix('.worldlog'), source.with_suffix('.journal')
        originals = {path: digest(path) for path in (original_world, original_combat)}
        before_world = venue.request(route)
        before_session = venue.state(entry)
        before_stats = venue.request(session + '/statistics')
        attached = before_session['combatStream']
        closed = world.analyze(original_world, expected_session=entry['id'])
        assert before_world['header']['streamId'] == attached['streamId'] and attached['missionClockVersion'] == 1
        assert closed['lastFrame']['worldSequence'] > before_world['acceptedSequence']
        assert closed['lastFrame']['phase'] == 'Running' and not closed['complete'] and not closed['sealed']
        venue.save('before.json', {'world': before_world, 'combat': attached, 'statistics': before_stats, 'journal': closed})

        def relay(build, kind, label, *, rejection=False, again=False):
            dll = (build / 'bin' / ('VrCommand.' + kind) / 'release' / ('VrCommand.' + kind + '.dll')).resolve()
            world_copy = venue.runtime_directory / (label + '.worldlog')
            combat_copy = venue.runtime_directory / (label + '.journal')
            if not again:
                shutil.copyfile(original_combat, combat_copy)
                if kind == 'WorldRelay':
                    shutil.copyfile(original_world, world_copy)
            files = [combat_copy, world_copy] if kind == 'WorldRelay' else [combat_copy]
            hashes = [digest(path) for path in files]
            paths = ['--world-journal', str(world_copy), '--combat-journal', str(combat_copy)] if kind == 'WorldRelay' else ['--journal', str(combat_copy)]
            run = subprocess.run(['dotnet', str(dll), *paths, '--base-url', venue.base,
                                  '--key-file', str(venue.directory / 'keys.json')], cwd=ROOT,
                                 capture_output=True, encoding='utf-8', timeout=45)
            result = {'dllSha256': digest(dll), 'returnCode': run.returncode,
                      'stdout': run.stdout, 'stderr': run.stderr}
            venue.save(label + ('-repeat' if again else '') + '.json', result)
            if rejection:
                assert run.returncode != 0 and '409 (Conflict)' in run.stderr
                assert hashes == [digest(path) for path in files]
                return
            assert run.returncode == 0
            if again:
                assert hashes == [digest(path) for path in files]
            return json.loads(run.stdout)

        if portable:
            recover('not-ended', reason='end-original-session-before-recovery')
        else:
            relay(args.before_build, 'WorldRelay', 'old-world', rejection=True)
            relay(args.before_build, 'TelemetryRelay', 'old-combat', rejection=True)
        assert venue.request(route) == before_world and venue.state(entry) == before_session
        assert venue.request(session + '/statistics') == before_stats
        if args.browser:
            venue.save('browser-review.json', {'base': venue.base, 'sessionId': entry['id'], 'tail': before_world['acceptedSequence']})
            browser_log = (venue.directory / 'browser.log').open('xb')
            browser = subprocess.Popen(['node', str(ROOT / 'tests/browser/check-saved-replay-native.cjs'), str(venue.directory)],
                                       cwd=ROOT, stdout=browser_log, stderr=subprocess.STDOUT)

            def browser_ready():
                if browser.poll() is not None:
                    raise RuntimeError('Browser observer exited before reading the original saved tail')
                return (venue.directory / 'browser-ready').is_file()

            venue.wait(browser_ready, 50, 'browser initial replay')

        if portable:
            venue.command(entry, 'End')
            venue.proxy.block('publication')
            try:
                recover('world-still-unreachable', reason='WorldConnectionInterrupted')
                combat_after_failure = venue.state(entry)['combatStream']['acceptedSequence']
                assert combat_after_failure > attached['acceptedSequence'] and venue.request(route) == before_world
            finally:
                venue.proxy.release()
            proof = recover('recovered-world')
            assert proof['worldBefore'] == before_world['acceptedSequence'] and proof['combatBefore'] == combat_after_failure
            assert proof['sessionId'] == entry['id'] and proof['streamId'] == attached['streamId'] and proof['origin'] == 'Simulation'
            assert not proof['worldSealed'] and not proof['combatSealed']
        else:
            outcome = relay(args.after_build, 'WorldRelay', 'recovered-world')
        recovered = venue.request(route)
        state = venue.state(entry)
        statistics = venue.request(session + '/statistics')
        tail = closed['lastFrame']['worldSequence']
        if portable:
            assert proof['worldAcknowledged'] == recovered['acceptedSequence'] == tail
            assert proof['combatAcknowledged'] == state['combatStream']['acceptedSequence']
        else:
            assert outcome['frames'] == outcome['acknowledged'] == recovered['acceptedSequence'] == tail
            assert outcome['sessionId'] == entry['id'] and outcome['origin'] == 'Simulation' and not outcome['complete']
        assert not recovered['complete'] and recovered['header'] == before_world['header']
        assert state['state'] == ('Ended' if portable else 'Running') and state['combatStream']['streamId'] == attached['streamId']
        assert state['combatStream']['missionClockVersion'] == 1 and not state['combatStream']['sealed']
        assert state['combatStream']['acceptedSequence'] > attached['acceptedSequence']
        venue.save('recovered.json', {'world': recovered, 'combat': state['combatStream'], 'statistics': statistics})
        assert statistics['players'][0]['damageTaken'] > before_stats['players'][0]['damageTaken']
        if portable:
            again = recover('recovered-repeat')
            assert again == dict(proof, worldBefore=proof['worldAcknowledged'], combatBefore=proof['combatAcknowledged'])
            for name in ('world.worldlog', 'combat.journal'):
                assert digest(venue.runtime_directory / 'recovered-world' / name) == digest(venue.runtime_directory / 'recovered-repeat' / name)
        else:
            assert relay(args.after_build, 'WorldRelay', 'recovered-world', again=True) == outcome
            combat = relay(args.after_build, 'TelemetryRelay', 'recovered-combat')
            assert combat['sessionId'] == entry['id'] and combat['acknowledged'] == state['combatStream']['acceptedSequence']
            assert not combat['complete'] and not combat['sealedStream'] and combat['statistics'] == statistics
            assert relay(args.after_build, 'TelemetryRelay', 'recovered-combat', again=True) == combat
        assert venue.request(route) == recovered and venue.state(entry) == state
        assert all(digest(path) == sha for path, sha in originals.items())
        if browser:
            exact = venue.request(route + f'/frames/{tail}')
            venue.save('browser-relay.json', {'tail': tail, 'damage': exact['statistics'][0]['damageTaken']})
            assert browser.wait(timeout=50) == 0

        if not portable:
            venue.command(entry, 'End')
        assert venue.state(entry)['state'] == 'Ended' and venue.request(route) == recovered
        assert venue.request(session + '/statistics')['pendingTelemetry']
        frames = replay(venue, route, recovered)
        venue.save('replay.json', frames)
        assert len(frames) == tail
        for index, (row, packet) in enumerate(zip(frames, packets(original_world), strict=True), 1):
            assert world_numbers(row['packet']) == world_numbers(packet), f'Packet mismatch at sequence {index}'
        assert frames[-1] == venue.request(route + f'/frames/{tail}')
        assert frames[-1]['packet']['frame']['phase'] == 'Running'
        player = entry['players'][0]
        assert any(row['playerId'] == player['id'] and row['damageTaken'] > 0 for row in frames[-1]['statistics'])
        venue.request(session + '/report.csv', expected=409)
        venue.request(session + '/field-evidence.zip', expected=409)
        client = 'recovery-client-3'
        venue.stop(client)
        assert 'VR_CLIENT_DEBRIEF_FINAL ' not in fixture.debrief.log_text(venue, client)
        assert all(room['sessionId'] is None for room in venue.request('/api/rooms'))
        report = {'serverExit': server.returncode, 'playerBuildReceipt': venue.receipt, 'headsets': 0,
                  'sourceHashes': {path.name: sha for path, sha in originals.items()}, 'admissionId': player['admissionId'],
                  'framesBefore': before_world['acceptedSequence'], 'framesRecovered': tail,
                  'combatBefore': attached['acceptedSequence'], 'combatRecovered': state['combatStream']['acceptedSequence'],
                  'damageBefore': before_stats['players'][0]['damageTaken'], 'damageRecovered': statistics['players'][0]['damageTaken'],
                  'terminalEvent': 'saved-end', 'gameplayRestarted': False, 'worldSealed': False,
                  'combatSealed': False, 'finalCsvAvailable': False, 'fieldEvidenceAvailable': False, 'playerFinalReceived': False}
        if portable:
            report['recoveryExeSha256'] = digest(args.recovery_exe)
            report['combatAfterFailedWorldPublish'] = combat_after_failure
    finally:
        if browser and browser.poll() is None:
            (venue.directory / 'browser-stop').touch(exist_ok=False)
            try:
                browser.wait(timeout=10)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait(timeout=5)
        if browser_log:
            browser_log.close()
        if venue.proxy:
            venue.proxy.close()
            gate = venue.proxy.snapshot()
            report['gate'] = gate
        # Intentional process loss has no seal. Issue only the normal management End if cleanup needs it.
        try:
            for entry in venue.rounds:
                if venue.state(entry)['state'] != 'Ended':
                    venue.command(entry, 'End')
        finally:
            for name in reversed(list(venue.processes)):
                venue.stop(name)
            if venue.api_log:
                venue.api_log.close()
            fixture.vm.snapshot_runtime(venue.runtime_directory, venue.directory / 'runtime-snapshot')
            venue.save('checks.json', report)
            print('Artifacts:', venue.directory, flush=True)
    assert not gate['limitsTriggered'] and not gate['activeTunnels']
    assert not any(gate['counts'][name] for name in ('handlerErrors', 'routeRejected', 'capacityRejected'))
    venue.stage('passed', frames=report['framesRecovered'], combat=report['combatRecovered'])


if __name__ == '__main__':
    main()
