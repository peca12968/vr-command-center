"""Prove guarded VR Begin and replay evidence with the native Windows mock runtime."""

import argparse
import hashlib
import http.client
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import Request, urlopen
import uuid

from local_api import api_command
from windows_firewall import require_silent_windows_launch
from windows_ipc_api import LoopbackIpcRelay, connect_unix, unix_address


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


desktop = load('start-desktop-venue')
field = load('verify-field-results')


class GuardedVenue(desktop.Venue):
    def __init__(self, args):
        super().__init__(args, artifact_family='desktop-guarded-openxr')
        self.endpoint = self.runtime_directory.with_suffix('.sock')
        self.relay = None

    def start(self):
        command, cwd, assembly = api_command(self.args)
        address = unix_address(self.endpoint)
        needed = {'systemroot', 'systemdrive', 'windir', 'temp', 'tmp', 'userprofile', 'localappdata'}
        environment = {key: value for key, value in os.environ.items() if key.lower() in needed}
        environment.update(DataDirectory=str(self.runtime_directory / 'missions'),
                           SessionDataDirectory=str(self.runtime_directory / 'sessions'),
                           OperatorKeyFile=str(self.directory / 'keys.json'), ASPNETCORE_ENVIRONMENT='Production',
                           Logging__LogLevel__Default='Information')
        self.api_log = (self.directory / 'api.log').open('wb')
        pipe_url = 'http://unix:/' + str(self.endpoint)
        api = subprocess.Popen([*command, '--urls', pipe_url, '--preferHostingUrls', 'true'], cwd=cwd, env=environment,
                               stdout=self.api_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        self.processes['api'] = api

        def healthy():
            with connect_unix(address) as stream:
                stream.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
                with http.client.HTTPResponse(stream) as response:
                    response.begin()
                    return response.status == 200

        self.wait(healthy, 25, 'management API on its local socket')
        log = (self.directory / 'api.log').read_text(encoding='utf-8', errors='replace')
        listeners = [line.partition('Now listening on: ')[2] for line in log.splitlines() if 'Now listening on: ' in line]
        if listeners != ['http://unix:' + str(self.endpoint)]:
            raise RuntimeError('Expected the sole Kestrel endpoint to be the owned Windows IPC socket')
        inspection = (f'@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object OwningProcess -EQ {api.pid}).Count; '
                      f'@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object OwningProcess -EQ {api.pid}).Count')
        ports = subprocess.check_output([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command', inspection],
                                       creationflags=subprocess.CREATE_NO_WINDOW, text=True, timeout=15).split()
        if ports != ['0', '0'] or api.poll() is not None:
            raise RuntimeError('The management process must have zero TCP listeners and zero UDP endpoints')
        self.relay = LoopbackIpcRelay(address, sys.executable)
        self.base = f'http://127.0.0.1:{self.relay.server_address[1]}'
        with urlopen(self.base + '/console/index.html', timeout=5) as page:
            if f'v{self.args.console_version}'.encode() not in page.read(1024 * 1024):
                raise RuntimeError('The original management console version did not load')
        with assembly.open('rb') as binary:
            assembly_sha = hashlib.file_digest(binary, 'sha256').hexdigest()
        self.save('api-runtime.json', {'program': command[0], 'assemblySha256': assembly_sha, 'processId': api.pid,
                                      'consoleVersion': self.args.console_version, 'apiEndpoint': listeners[0],
                                      'tcpListeners': 0, 'udpEndpoints': 0, 'loopbackRelay': self.base})

    def cleanup(self):
        try:
            return super().cleanup()
        finally:
            if self.relay is not None:
                self.relay.close()
            if 'api' not in self.processes:
                self.endpoint.unlink(missing_ok=True)


def verify(venue, args):
    venue.start()
    mission = venue.mission(1)
    entry = venue.create(mission, [1], 'guarded-openxr', role='Room1', origin='GameServer', headset='ViveXr')
    session = '/api/sessions/' + entry['id']
    player, = entry['players']
    world = venue.wait(lambda: venue.request(session + '/world', optional=True), 30, 'original recording')
    stream = world['header']['streamId']
    assert world['header']['origin'] == 'GameServer'
    venue.request(session + '/connection-endpoint', {'version': 1, 'streamId': stream, 'address': '127.0.0.1', 'port': entry['port']},
                  role='GameServer', method='PUT')

    manifest = venue.directory / 'fixture-runtime.json'
    venue.save(manifest.name, {'file_format_version': '1.0.0', 'runtime':
        {'api_version': '1.0', 'name': 'VR Command guarded start test', 'library_path': str(args.pose_dll)}})
    loss = venue.directory / 'aim-loss.request'
    ack = venue.directory / 'aim-loss-ack.txt'
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() != 'XR_RUNTIME_JSON' and not key.upper().startswith('VR_COMMAND_OPENXR_')}
    environment.update(XR_RUNTIME_JSON=str(manifest), VR_COMMAND_OPENXR_MOCK_DLL=str(args.mock_dll),
                       VR_COMMAND_OPENXR_AIM_LOSS_FILE=str(loss), VR_COMMAND_OPENXR_AIM_LOSS_ACK=str(ack))
    name = entry['name'] + '-player'
    venue.launch(name, venue.client_config(entry, venue.ticket(entry, player)), visible=True,
                 extra_args=('-force-d3d11', '--vr-openxr'), environment=environment)
    log = venue.directory / (name + '.log')

    def log_text():
        return log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''

    venue.wait(lambda: 'VR_CLIENT_CONNECTED id=' in log_text(), 30, 'original Unity OpenXR player admission')
    assert field.windows_player_source(log_text(), entry['port']) == ('windows-openxr-mock-tracked', 'Tracked')

    def readiness(ready, acknowledgement, after=0):
        def sample():
            if not ack.is_file() or ack.read_text(encoding='ascii').splitlines() != acknowledgement:
                return None
            report = venue.request(session + '/readiness')
            row, = report['players']
            assert (row['playerId'], row['admissionId'], row['roomId'], row['seat']) == (
                player['id'], player['admissionId'], player['roomId'], player['seat'])
            if (report['sourceState'] != 'Fresh' or report['origin'] != 'GameServer'
                    or report['sessionSequence'] != report['observedSequence'] or report['worldSequence'] <= after
                    or report.get('trackedVrStartReady') is not ready or row['canParticipate'] is not ready):
                return None
            value = venue.request(f'{session}/world/frames/{report["worldSequence"]}')
            packet = value['packet']
            body, = packet['frame']['players']
            assert (packet['frame']['phase'], packet['frame']['tick'], body['id'], body['connected']) == (
                'Preparing', 0, player['id'], ready)
            assert not ready or body['rig']['kind'] == 'Tracked'
            return {'readiness': report, 'packet': packet}

        return venue.wait(sample, 15, 'original Preparing readiness and right-aim acknowledgement')

    first = readiness(True, ['0 7'])
    venue.save('before-loss.json', first)
    loss.touch(exist_ok=False)
    missing = readiness(False, ['0 7', '1 7'], first['packet']['sequence'])
    venue.save('tracking-lost.json', missing)
    revision = first['readiness']['sessionSequence']
    assert revision == missing['readiness']['sessionSequence']
    command = {'commandId': str(uuid.uuid4()), 'expectedSequence': revision, 'requireTrackedStart': True}
    blocked = venue.command(entry, 'Begin', expected=409, **command)
    assert blocked['code'] == 'tracked-vr-start-not-ready'
    state = venue.state(entry)
    assert state['state'] == 'Preparing' and state['sequence'] == revision
    venue.save('rejected-begin.json', {'command': command, 'response': blocked})
    loss.unlink()
    recovered = readiness(True, ['0 7', '1 7', '0 7'], missing['packet']['sequence'])
    assert recovered['readiness']['sessionSequence'] == revision
    venue.save('tracking-recovered.json', recovered)
    receipt = venue.command(entry, 'Begin', **command)
    duplicate = venue.command(entry, 'Begin', **command)
    assert receipt['duplicate'] is False and duplicate['duplicate'] is True
    assert receipt['appliedAtSequence'] == duplicate['appliedAtSequence'] > revision
    venue.save('accepted-begin.json', {'accepted': receipt, 'duplicate': duplicate})

    def running():
        packet = venue.frame(entry)['packet']
        if (packet['observedSequence'] >= receipt['appliedAtSequence'] and packet['frame']['phase'] == 'Running'
                and packet['frame']['tick'] > 0 and packet['frame']['players'][0]['connected'] is True):
            return packet
        return None

    venue.save('first-verified-running.json', venue.wait(running, 15, 'actual running tracked frame'))
    sealed = venue.seal(entry)
    request = Request(venue.base + session + '/field-evidence.zip?includeTrackedVrStart=true',
                      headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    with urlopen(request, timeout=5) as response:
        original = response.read()
    (venue.directory / 'field-evidence.zip').write_bytes(original)
    records, documents = field.unpack_management_zip(original, allow_session_evidence=True)
    evidence = documents['tracked-vr-start.json']
    opening = evidence['trackedVrStart']
    assert opening['sessionId'] == entry['id'] and opening['streamId'] == stream
    assert opening['appliedAtSequence'] == receipt['appliedAtSequence']
    assert opening['worldSequence'] >= recovered['packet']['sequence'] > missing['packet']['sequence']
    assert opening['players'] == [{'playerId': player['id'], 'roomId': 1}]
    witness = venue.request(f'{session}/world/frames/{opening["worldSequence"]}')['packet']
    assert witness['frame']['phase'] == 'Preparing' and witness['observedSequence'] == revision
    assert witness['frame']['players'][0]['rig']['kind'] == 'Tracked' and witness['frame']['players'][0]['connected'] is True
    assert sealed['world']['header']['streamId'] == stream and records[1]['players'] == sealed['statistics']['players']
    venue.save('original-opening.json', {'evidence': evidence, 'packet': witness})
    assert venue.wait_for_player_results(entry)['allAcknowledged']
    venue.evidence.extend(('tracked Preparing', 'lost tracked aim', 'Begin rejected', 'tracked aim restored',
                          'same Begin accepted and deduplicated', 'native Running', 'exported original opening', 'final result acknowledged'))
    venue.summary(source='Windows native Unity and management 0.31; Unity Mock Runtime; IPC-only management process')
    return sealed, records, evidence


def verify_closed(venue, sealed, records, evidence):
    session = records[0]
    world = sealed['world']
    through = sealed['statistics']['throughSequence']
    final = desktop.read_json(venue.directory / (sealed['name'] + '-latest-frame.json'))['packet']
    boundary = field.tracked_vr_start_boundary(evidence, session, world, through)
    telemetry = venue.runtime_directory / (sealed['name'] + '-telemetry')
    combat = final['throughCombatSequence']
    ended = final['observedSequence']
    world_report = field.verify_world_journal(telemetry / (session['id'] + '.worldlog'), world, combat, through,
                                               ended, guarded_begin=boundary)
    ledger = {row['playerId']: row for row in sealed['statistics']['players']}
    combat_report = field.verify_combat_journal(telemetry / (session['id'] + '.journal'), session['id'],
                                                 world['header']['streamId'], 'GameServer', combat, ended, ledger)
    venue.save('closed-readback.json', {'world': world_report, 'combat': combat_report})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=desktop.ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--control-package', type=Path, required=True)
    parser.add_argument('--mock-dll', type=Path, required=True)
    parser.add_argument('--pose-dll', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    args = parser.parse_args()
    args.duration, args.job_workers, args.check = 300, 2, False
    try:
        if os.name != 'nt':
            raise ValueError('Requires the Windows Unity player and Windows IPC')
        package = args.control_package.resolve(strict=True)
        manifest = load('package-control-server').verify(package)
        args.console_version = manifest['consoleVersion']
        if tuple(map(int, args.console_version.split('.'))) < (0, 31, 201):
            raise ValueError('Use a management package with the exported original guarded VR Begin frame')
        args.api_exe = package / 'Runtime/VrCommand.Api.exe'
        args.mock_dll = args.mock_dll.resolve(strict=True)
        args.pose_dll = args.pose_dll.resolve(strict=True)
        desktop.verify_player(args)
        require_silent_windows_launch(sys.executable)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    venue = GuardedVenue(args)
    try:
        sealed, records, evidence = verify(venue, args)
    finally:
        if not venue.cleanup():
            raise RuntimeError('See cleanup.json for guarded test cleanup errors')
    verify_closed(venue, sealed, records, evidence)
    venue.stage('passed', checks=len(venue.evidence), closedJournalVerified=True)


if __name__ == '__main__':
    main()
