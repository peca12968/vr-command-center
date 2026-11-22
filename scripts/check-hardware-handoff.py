"""Exercise the compiled hardware handoff verifier using local simulated reports."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def identity(number):
    return str(uuid.UUID(int=number))


def write_json(path, data):
    raw = json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    path.write_bytes(raw)
    return len(raw), hashlib.sha256(raw).hexdigest()


def prepare(root, mode, version, edit=lambda _: None):
    bindings, reports = root / 'bindings', root / 'reports'
    bindings.mkdir(parents=True)
    reports.mkdir()
    manifest = {'version': 1, 'mode': mode, 'rooms': []}
    aggregate = {'version': version, 'complete': True, 'mode': mode, 'simulatedHardwareOnly': True,
                 'physicalDeliveryConfirmed': False, 'rooms': []}
    outcomes = []
    for room in range(1, 6):
        session = identity(1 if mode == 'Linked' else room)
        stream = identity(10 if mode == 'Linked' else 10 + room)
        seat = {'seat': 0, 'deviceId': identity(100 + room), 'playerId': identity(110 + room), 'admissionId': identity(120 + room)}
        configuration = f'room-{room:02}.json'
        manifest['rooms'].append({'roomId': room, 'sessionId': session, 'sessionSequence': 7,
                                  'configuration': configuration, 'boundSeats': 1})
        _, config_hash = write_json(bindings / configuration, {'version': 2, 'roomId': room, 'sessionId': session, 'seconds': 15,
            'managementUrl': 'http://127.0.0.1:5081', 'mockPort': 19100 + room, 'bindings': [seat]})
        aggregate['rooms'].append({'roomId': room, 'sessionId': session, 'exitCode': 0, 'report': f'room-{room:02}-report.json',
                                   'configurationSha256': config_hash, 'error': None})
        attempts = []
        for index in range(2):
            number = room * 10 + index
            signal = {key: seat[key] for key in ('seat', 'playerId', 'admissionId')}
            signal.update(eventId=identity(1000 + number), reportId=identity(2000 + number), eventSequence=number,
                          streamSequence=number, observedSequence=9, kind='PlayerDamaged', damage=5,
                          acceptedAtUtc='2026-11-17T00:00:00+00:00')
            attempt = {'connectionId': identity(200 + room), 'batchId': identity(300 + number),
                       'status': 'simulated-acknowledged', 'deliveries': [{'deviceId': seat['deviceId'], 'signal': signal}]}
            if version == 4:
                attempt.update(streamId=stream, runningSinceSequence=8)
            attempts.append(attempt)
        outcomes.append({'version': 1, 'complete': True, 'simulatedHardwareOnly': True, 'physicalDeliveryConfirmed': False,
                         'sessionId': session, 'roomId': room, 'termination': 'duration', 'connections': 1, 'attachments': 1,
                         'managementFaults': 0, 'mockFaults': 0, 'dropped': 0, 'acknowledged': 2, 'attempts': attempts})
    edit(outcomes)
    manifest_path = bindings / 'venue-bindings.json'
    _, aggregate['bindingManifestSha256'] = write_json(manifest_path, manifest)
    for outcome, row in zip(outcomes, aggregate['rooms'], strict=True):
        row['bytes'], row['sha256'] = write_json(reports / row['report'], outcome)
    write_json(reports / 'venue-report.json', aggregate)
    return manifest_path, reports


def signal(outcomes, room=0, attempt=0):
    return outcomes[room]['attempts'][attempt]['deliveries'][0]['signal']


def duplicate_ack(outcomes):
    room = outcomes[0]
    duplicate = deepcopy(room['attempts'][-1])
    duplicate['batchId'] = identity(999)
    room['attempts'].append(duplicate)
    room['acknowledged'] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulator-dll', type=Path, default=ROOT / 'tools/VrCommand.HardwareSimulator/bin/Release/net10.0/VrCommand.HardwareSimulator.dll')
    args = parser.parse_args()
    tool = ['dotnet', str(args.simulator_dll.resolve(strict=True))]
    checks = 0

    def invoke(*arguments, reject=False):
        nonlocal checks
        result = subprocess.run([*tool, *map(str, arguments)], capture_output=True, encoding='utf-8', timeout=15)
        if reject:
            assert result.returncode == 1 and not result.stdout and result.stderr.strip().endswith('InvalidDataException'), result.stderr
        else:
            assert result.returncode == 0, result.stderr
        checks += 1
        return result.stdout

    with tempfile.TemporaryDirectory(prefix='vr-hardware-handoff-') as directory:
        root = Path(directory)
        sources = root / 'original-events'
        sources.mkdir()
        write_json(sources / (identity(1) + '.json'), [])
        for mode in ('Linked', 'Independent'):
            manifest, reports = prepare(root / mode, mode, 4, lambda rows: rows[3].update(managementFaults=2, mockFaults=3))
            original = invoke('--verify-venue-report', manifest, '--report-directory', reports)
            reviewed = json.loads(original)
            assert reviewed['attemptIdentitiesVerified'] and reviewed['configurationsVerified']
            assert not reviewed['sourceEventsVerified'] and reviewed['sourceSignalsVerified'] == 0
            assert [room['acknowledged'] for room in reviewed['rooms']] == [2] * 5
            assert reviewed['rehearsalComplete'] and all(room['mockFailed'] == 0 for room in reviewed['rooms'])
            assert [room['communicationFaults'] for room in reviewed['rooms']] == [
                {'management': 2, 'mockDevice': 3} if room == 4 else {'management': 0, 'mockDevice': 0}
                for room in range(1, 6)]
            archive = root / (mode + '.zip')
            assert invoke('--pack-venue-report', manifest, '--report-directory', reports, '--output', archive) == original
            assert invoke('--verify-venue-zip', archive) == original
            invoke('--verify-venue-report', manifest, '--report-directory', reports, '--events-directory', sources, reject=True)
            invoke('--verify-venue-zip', archive, '--events-directory', sources, reject=True)
            aggregate = reports / 'venue-report.json'
            incomplete = json.loads(aggregate.read_bytes())
            incomplete['complete'] = False
            missing = incomplete['rooms'][3]
            (reports / missing['report']).unlink()
            missing.update(report=None, sha256=None, bytes=None, exitCode=1, error='IOException')
            write_json(aggregate, incomplete)
            partial = json.loads(invoke('--verify-venue-report', manifest, '--report-directory', reports))
            assert not partial['rehearsalComplete'] and partial['rooms'][3]['error'] == 'IOException'
            assert partial['rooms'][3].get('communicationFaults') is None
        manifest, reports = prepare(root / 'legacy', 'Linked', 3, duplicate_ack)
        legacy = json.loads(invoke('--verify-venue-report', manifest, '--report-directory', reports))
        assert legacy['rooms'][0]['acknowledged'] == 3 and not legacy['attemptIdentitiesVerified']
        assert not legacy['sourceEventsVerified'] and legacy['sourceSignalsVerified'] == 0
        invoke('--verify-venue-report', manifest, '--report-directory', reports, '--events-directory', sources, reject=True)
        cases = (
            ('duplicated-ack', duplicate_ack),
            ('duplicated-event', lambda rows: signal(rows, attempt=1).update(eventId=signal(rows)['eventId'])),
            ('cross-room-report', lambda rows: signal(rows, room=1).update(reportId=signal(rows)['reportId'])),
            ('cross-room-stream-sequence', lambda rows: signal(rows, room=1).update(streamSequence=10)),
            ('cross-room-journal-sequence', lambda rows: signal(rows, room=1).update(eventSequence=10)),
            ('regressed-stream-sequence', lambda rows: signal(rows, attempt=1).update(streamSequence=9)),
            ('wrong-running-revision', lambda rows: rows[0]['attempts'][0].update(runningSinceSequence=10)),
            ('missing-stream', lambda rows: rows[0]['attempts'][0].pop('streamId')),
        )
        for label, edit in cases:
            manifest, reports = prepare(root / label, 'Linked', 4, edit)
            invoke('--verify-venue-report', manifest, '--report-directory', reports, reject=True)
            archive = root / (label + '.zip')
            invoke('--pack-venue-report', manifest, '--report-directory', reports, '--output', archive, reject=True)
            assert not archive.exists()
            with zipfile.ZipFile(archive, 'x') as bundle:
                for folder in (manifest.parent, reports):
                    for item in sorted(folder.iterdir()):
                        bundle.write(item, f'{folder.name}/{item.name}')
            invoke('--verify-venue-zip', archive, reject=True)
            print('PASS:', label)
    print(json.dumps({'complete': True, 'checks': checks, 'scope': 'offline-simulated-handoff'}))


if __name__ == '__main__':
    main()
