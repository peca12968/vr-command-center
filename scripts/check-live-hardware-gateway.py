"""Run the compiled gateway, real isolated management API and separate loopback mock processes."""
import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from itertools import count
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode
import uuid
import zipfile

from local_api import add_api_arguments, api_command as resolve_api_command, checked_api_command
from windows_ipc_api import UnixHttpConnection, accept_unix, bind_unix, connect_unix, has_no_ip_endpoints, unix_address, unix_http_opener
from windows_firewall import require_silent_windows_launch

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
IPC_DIRECTORY = 'VR_COMMAND_HARDWARE_IPC_DIRECTORY'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class RehearsalIpc:
    def __init__(self, directory):
        self.directory = directory
        self.mock_ports = count(19000)
        self.authority_ports = count(18001)

    def management_socket(self, port):
        return self.directory / f'management-{port}.sock'

    def management(self, port):
        return UnixHttpConnection(unix_address(self.management_socket(port)))

    def peer(self, port):
        return connect_unix(unix_address(self.directory / f'mock-{port}.sock'))

    @contextmanager
    def fault_server(self, handler):
        port = next(self.authority_ports)
        path = self.management_socket(port)

        class Server(ThreadingHTTPServer):
            address_family = 1
            server_port = port
            server_name = 'localhost'

            def server_bind(self):
                bind_unix(self.socket, unix_address(path))

            def get_request(self):
                return accept_unix(self.socket), ('localhost', 0)

        try:
            with Server(str(path), handler) as server:
                yield server
        finally:
            path.unlink(missing_ok=True)


@contextmanager
def authority_gate(port, owners, ipc=None):
    routes = {f'/api/sessions/{session}/rooms/{room}/hardware-feedback': room for room, session in owners.items()}
    faults, injected = {}, set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = self.path.split('?', 1)[0]
            room = routes.get(path)
            fault = faults.get(room)
            if fault is not None:
                injected.add(room)
            if fault == 'delay':
                time.sleep(1.1)
                return
            if fault == 'disconnect':
                return
            if fault is not None and not callable(fault):
                status, body = fault
            elif room is not None or path == '/api/me':
                connection = ipc.management(port) if ipc else http.client.HTTPConnection('127.0.0.1', port, timeout=2)
                with closing(connection) as upstream:
                    upstream.request('GET', self.path, headers={
                        'Authorization': self.headers['Authorization'], 'Host': f'127.0.0.1:{port}'})
                    reply = upstream.getresponse()
                    status, body = reply.status, reply.read(192 * 1024 + 1)
                if fault is not None and status == 200:
                    body = json.dumps(fault(json.loads(body))).encode()
            else:
                status, body = 404, b''
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    listener = ipc.fault_server(Handler) if ipc else ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    with listener as server:
        server.daemon_threads = False
        worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05})
        worker.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}', faults, injected
        finally:
            server.shutdown()
            worker.join(2)
            assert not worker.is_alive()


def run(args, api_command, api_cwd):
    out = args.evidence_root.resolve()/('run-'+uuid.uuid4().hex)
    out.mkdir(parents=True)
    print(json.dumps({'stage':'starting','directory':str(out)}), flush=True)
    keys = {role:secrets.token_hex(32) for role in ('Master','GameServer',*(f'Room{room}' for room in range(1,6)))}
    token = secrets.token_hex(32)
    private = [*keys.values(), token]
    env = {k:v for k,v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in
           ('operatorkeyfile','playerticketsigningkey','controlpipetoken','datadirectory','sessiondatadirectory','vr_command_room_key','vr_command_master_key', IPC_DIRECTORY.lower())
           and k.upper() not in {f'VR_COMMAND_ROOM_{room}_KEY' for room in range(1,6)}}
    findings, closed, processes, api_log = [], [], [], []
    binary = args.simulator_dll.resolve()
    files = {p.name:sha(p) for p in binary.parent.iterdir() if p.is_file()}
    peer_script = args.mock_peer_script.resolve()
    peer_hash = sha(peer_script)

    def save(name, value):
        data = json.dumps(value, indent=2)+'\n'
        assert not any(secret in data for secret in private)
        (out/name).write_text(data, encoding='utf-8')

    def check(ok, label):
        assert ok, label
        findings.append(label)
        print('PASS: '+label, flush=True)

    def start(command, environment, *, cwd=ROOT):
        process = subprocess.Popen(command, cwd=cwd, env=environment, text=True, encoding='utf-8', stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=HIDDEN)
        processes.append(process)
        return process

    def wait(predicate, label):
        until = time.monotonic()+8
        while time.monotonic()<until:
            if value := predicate():
                return value
            time.sleep(.025)
        raise RuntimeError('Timeout: '+label)

    class Peer:
        def __init__(self, room=None):
            self.lines = queue.Queue()
            command = [sys.executable, str(peer_script), '--manual']
            if ipc:
                command += ['--port', str(next(ipc.mock_ports))]
            if room is not None:
                command += ['--room', str(room)]
            self.process = start(command, env)
            self.reader = threading.Thread(target=self.collect, daemon=True)
            self.reader.start()
            self.port = self.read('listening')['port']

        def collect(self):
            for line in self.process.stdout:
                self.lines.put(line)

        def read(self, kind=None):
            frame = json.loads(self.lines.get(timeout=8))
            assert kind is None or frame['kind'] == kind
            return frame

        def reply(self, command='ack'):
            self.process.stdin.write(command+'\n')
            self.process.stdin.flush()

    with tempfile.TemporaryDirectory(prefix='vr-hw-', dir=args.ipc_work_root) as temporary:
        runtime = Path(temporary)
        ipc = RehearsalIpc(runtime) if args.ipc_work_root else None
        if ipc:
            port = 18000
            env[IPC_DIRECTORY] = str(runtime)
        else:
            with socket.socket() as reserve:
                reserve.bind(('127.0.0.1',0))
                port = reserve.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        keyfile = runtime/'keys.json'
        keyfile.write_text(json.dumps({'OperatorKeys':keys}), encoding='utf-8')
        options = {**env, 'OperatorKeyFile':str(keyfile), 'DataDirectory':str(runtime/'missions'),
            'SessionDataDirectory':str(runtime/'sessions'), 'ControlPipeToken':token,
            'Logging__LogLevel__Default':'Warning', 'Logging__LogLevel__Microsoft.AspNetCore.Hosting.Diagnostics':'Information'}
        api_urls = ['--urls', 'http://unix:/' + str(ipc.management_socket(port)), '--preferHostingUrls', 'true'] if ipc else ['--urls', base]
        api = start([*api_command, *api_urls], options, cwd=api_cwd)

        def collect():
            for line in api.stdout:
                api_log.append(line)

        api_reader = threading.Thread(target=collect, daemon=True)
        api_reader.start()
        opener = unix_http_opener(ipc.management_socket) if ipc else urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def connect_peer(mock_port):
            return ipc.peer(mock_port) if ipc else socket.create_connection(('127.0.0.1', mock_port), timeout=3)

        def request(path, body=None, role='Master', *, method=None, admission=None):
            headers = {'Authorization':'Bearer '+keys[role], 'Content-Type':'application/json'}
            if admission:
                headers['If-Match-Admission'] = admission
            req = urllib.request.Request(base+path, method=method, headers=headers, data=json.dumps(body).encode() if body is not None else None)
            with opener.open(req, timeout=4) as reply:
                return json.load(reply) if reply.status != 204 else None

        def health():
            try:
                return request('/health')['status']=='ok'
            except OSError:
                assert api.poll() is None
                return False

        try:
            wait(health,'management ready')
            if ipc:
                check(has_no_ip_endpoints([os.getpid(), api.pid]), 'Windows IPC begins with no TCP listeners or UDP endpoints')
            mission = request('/api/missions', {'name':'Live mock feedback', 'briefing':'Isolated test session', 'durationSeconds':600,
                'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
                'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]})
            session = request('/api/sessions',{'missionId':mission['id'],'mode':'Linked','roomIds':[1,2,3,4,5]})
            sid = session['id']; path = '/api/sessions/'+sid
            for i, room in enumerate([1,1,1,2,3], 1):
                session = request(path+'/players', {'playerId':str(uuid.uuid4()),'roomId':room,'name':f'Fixture {i}','headset':'Quest3'}, f'Room{room}')
            alpha, bravo, unbound, charlie, delta = session['players']
            stream = str(uuid.uuid4())
            request(path+'/combat-stream',{'streamId':stream,'origin':'Simulation'},'GameServer')

            def action(name):
                return request(path+'/commands', {'commandId':str(uuid.uuid4()),'action':name})['appliedAtSequence']

            epoch = action('Begin')
            sequence = 0

            def publish(items, observed=None):
                nonlocal sequence
                rows = []
                for player, kind in items:
                    sequence += 1
                    report = {'reportId':str(uuid.uuid4()),'kind':kind,'origin':'Simulation','playerId':player['id']}
                    report.update({'shotId':str(uuid.uuid4())} if kind=='ShotFired' else {'damage':10})
                    rows.append({'streamId':stream,'streamSequence':sequence,'observedSequence':epoch if observed is None else observed,'report':report})
                request(path+'/combat-stream/batch', rows, 'GameServer')
                return [item['report']['reportId'] for item in rows]

            def attached(room, bound=False):
                query = '?includeBindings=true' if bound else ''
                target = f'{base}{path}/rooms/{room}/hardware-feedback{query} - 200'
                return sum('Request finished' in line and target in line for line in api_log)

            def accept(peer, room, previous=None, *, bound=False):
                hello = peer.read('hello')
                assert hello['roomId']==room and (not previous or hello['connectionId']!=previous)
                previous_count = attached(room, bound)
                peer.reply()
                wait(lambda:attached(room,bound)>previous_count,f'room {room} fresh cursor attachment')
                return hello['connectionId']

            peers = {1:Peer(), 2:Peer()}
            configs = {}
            expected = {}
            for room, players in [(1,[alpha,bravo]),(2,[charlie])]:
                bindings = [{'deviceId':str(uuid.uuid4()),'playerId':p['id'],'admissionId':p['admissionId'],'seat':p['seat']} for p in players]
                if room==1:
                    bindings.append({'deviceId':str(uuid.uuid4()),'playerId':unbound['id'],'admissionId':str(uuid.uuid4()),'seat':unbound['seat']})
                expected.update({b['playerId']:b for b in bindings})
                config = {'version':1,'managementUrl':base,'sessionId':sid,'roomId':room,'mockPort':peers[room].port,'seconds':35,'bindings':bindings}
                configs[room] = runtime/f'room-{room}.json'
                configs[room].write_text(json.dumps(config),encoding='utf-8')

            def invoke(room, key_role, report, *, config=None, stop=None, status_directory=None):
                command = ['dotnet',str(binary),'--live',str(config or configs[room]),'--output',str(report)]
                if stop is not None:
                    command += ['--stop-file',str(stop)]
                if status_directory is not None:
                    command += ['--status-directory',str(status_directory)]
                return start(command, {**env,'VR_COMMAND_ROOM_KEY':keys[key_role]})

            def stopped(gateway, report, *, attached_once):
                output, _ = gateway.communicate(timeout=8)
                raw = report.read_text(encoding='utf-8')
                assert not any(secret in output or secret in raw for secret in private)
                result = json.loads(raw)
                assert gateway.returncode==(0 if attached_once else 1), output
                assert result['termination']=='operator-stop' and result['complete'] is attached_once
                assert result['simulatedHardwareOnly'] is True and result['physicalDeliveryConfirmed'] is False
                assert result['attachments']==int(attached_once) and result['acknowledged']==0
                assert result['managementFaults']==result['mockFaults']==0
                return result

            denied = invoke(1,'Room2',out/'denied.json')
            denied_log, _ = denied.communicate(timeout=8)
            check(denied.returncode==1 and 'AccessDeniedException' in denied_log and not (out/'denied.json').exists()
                  and not any(secret in denied_log for secret in private), 'Wrong room identity is refused before creating a report')

            stale_stop = runtime/'previous.stop'
            stale_stop.touch()
            for marker in (stale_stop, out/'invalid-stop.json'):
                denied = invoke(1,'Room1',out/'invalid-stop.json',stop=marker)
                denied_log, _ = denied.communicate(timeout=8)
                assert denied.returncode==1 and 'ArgumentException' in denied_log and not (out/'invalid-stop.json').exists()
                assert not any(secret in denied_log for secret in private)
            check(stale_stop.is_file(), 'Stale and report-alias stop markers are refused without replacing either file')

            stop_peer = Peer()
            stop_config = runtime/'room-1-stop.json'
            stop_config.write_text(json.dumps({**json.loads(configs[1].read_text(encoding='utf-8')), 'mockPort':stop_peer.port}),encoding='utf-8')
            early_stop = runtime/'handshake.stop'
            early_report = out/'handshake-stop-report.json'
            early = invoke(1,'Room1',early_report,config=stop_config,stop=early_stop)
            hello = stop_peer.read('hello')
            stop_peer.reply('observe-close')
            early_stop.touch()
            early_close = stop_peer.read('closed')
            save('handshake-stop-close.json',early_close)
            check(early_close['connectionId']==hello['connectionId'] and early_close['batchId'] is None
                  and stopped(early,early_report,attached_once=False)['attempts']==[],
                  'Operator stop closes the original handshake and reports an incomplete attachment')

            idle_stop = runtime/'idle.stop'
            idle_report = out/'idle-stop-report.json'
            idle = invoke(1,'Room1',idle_report,config=stop_config,stop=idle_stop)
            idle_connection = accept(stop_peer,1,hello['connectionId'])
            wait(lambda:any('Request finished' in line and f'{base}{path}/rooms/1/hardware-feedback?after=' in line
                            and ' - 200 ' in line for line in api_log), 'idle gateway begins cursor polling')
            idle_stop.touch()
            check(stopped(idle,idle_report,attached_once=True)['attempts']==[] and idle_stop.is_file(),
                  'Operator stop finishes an idle attached gateway and preserves the marker')

            pause_stop = runtime/'idle-pause.stop'
            pause_report = out/'idle-pause-report.json'
            idle_pause = invoke(1,'Room1',pause_report,config=stop_config,stop=pause_stop)
            idle_hello = stop_peer.read('hello')
            previous_count = attached(1)
            stop_peer.reply('ready-observe-close')
            wait(lambda:attached(1)>previous_count,'idle Pause original attachment')
            action('Pause')
            idle_closed = stop_peer.read()
            save('idle-pause-close.json',idle_closed)
            check(idle_closed['kind']=='closed' and idle_closed['connectionId']==idle_hello['connectionId']
                  and idle_closed['batchId'] is None, 'Pause closes an already attached idle connection')
            try:
                unexpected = stop_peer.lines.get(timeout=.6)
            except queue.Empty:
                unexpected = None
            check(unexpected is None and idle_pause.poll() is None, 'The gateway stays disconnected while paused')
            epoch = action('Resume')
            resumed_idle = accept(stop_peer,1,idle_hello['connectionId'])
            pause_stop.touch()
            idle_log,_ = idle_pause.communicate(timeout=8)
            idle_result = json.loads(pause_report.read_text(encoding='utf-8'))
            check(idle_pause.returncode==0 and not any(secret in idle_log for secret in private)
                  and resumed_idle != idle_hello['connectionId'] and idle_result['attempts']==[]
                  and idle_result['termination']=='operator-stop' and idle_result['connections']==idle_result['attachments']==2,
                  'Resume establishes a new connection with a fresh cursor after an idle Pause')

            crossing_stop = runtime/'crossing-handshake.stop'
            crossing_report = out/'crossing-handshake-report.json'
            crossing = invoke(1,'Room1',crossing_report,config=stop_config,stop=crossing_stop)
            stale_hello = stop_peer.read('hello')
            action('Pause')
            epoch = action('Resume')
            stop_peer.reply('ready-observe-close')
            stale_close = stop_peer.read('closed')
            accept(stop_peer,1,stale_hello['connectionId'])
            crossing_stop.touch()
            crossing_log,_ = crossing.communicate(timeout=8)
            crossing_result = json.loads(crossing_report.read_text(encoding='utf-8'))
            save('crossing-handshake-close.json',stale_close)
            check(crossing.returncode==0 and not any(secret in crossing_log for secret in private)
                  and stale_close['connectionId']==stale_hello['connectionId'] and stale_close['batchId'] is None
                  and crossing_result['connections']==2 and crossing_result['attachments']==1 and crossing_result['attempts']==[],
                  'A late ready after Pause and Resume cannot attach its old connection to the new Running epoch')

            status_report = out/'operator-status-report.json'
            status_stop = runtime/'operator-status.stop'
            status_command = ['dotnet',str(binary),'--live',str(stop_config),'--output',str(status_report),'--status']
            status_env = {**env,'VR_COMMAND_ROOM_KEY':keys['Room1']}
            duplicate_status = start([*status_command,'--status'], status_env)
            duplicate_output, _ = duplicate_status.communicate(timeout=8)
            check(duplicate_status.returncode==1 and 'ArgumentException' in duplicate_output and not status_report.exists(),
                  'Duplicate status options fail before creating a report or opening a mock connection')

            action('Pause')
            status_gateway = start([*status_command,'--stop-file',str(status_stop)], status_env)
            status_lines = queue.Queue()
            status_history = []

            def collect_status():
                for line in status_gateway.stdout:
                    status_lines.put(line)

            status_reader = threading.Thread(target=collect_status, daemon=True)
            status_reader.start()

            def read_status(phase):
                deadline = time.monotonic()+8
                while time.monotonic()<deadline:
                    raw = status_lines.get(timeout=max(0.01, deadline-time.monotonic()))
                    assert not any(secret in raw for secret in private)
                    event = json.loads(raw)
                    assert set(event)=={'version','kind','roomId','sequence','observedAtUtc','phase','connections','attachments',
                                        'managementFaults','mockFaults','dropped','acknowledged','batches','termination','fault',
                                        'simulatedHardwareOnly','physicalDeliveryConfirmed'}
                    assert event['kind']=='gateway-status' and event['version']==event['roomId']==1
                    assert event['sequence']==len(status_history)+1
                    assert event['simulatedHardwareOnly'] is True and event['physicalDeliveryConfirmed'] is False
                    status_history.append(event)
                    if event['phase']==phase:
                        return event
                raise RuntimeError('Missing live gateway status: '+phase)

            check(read_status('paused')['connections']==0 and status_gateway.poll() is None and not status_report.exists(),
                  'Live operator output reports paused without waiting for a terminal report')
            epoch = action('Resume')
            read_status('connecting')
            first_status_connection = accept(stop_peer,1)
            check(read_status('active')['attachments']==1, 'Live active status requires the original mock handshake and authority attachment')
            lost_ids = publish([(alpha,'ShotFired')])
            lost_status_batch = stop_peer.read('feedback')
            assert [row['signal']['reportId'] for row in lost_status_batch['signals']]==lost_ids
            check(read_status('awaiting-ack')['acknowledged']==0, 'A pending batch is visible without claiming an acknowledgement')
            stop_peer.reply('drop')
            lost_status = read_status('mock-unavailable')
            check(lost_status['fault']=='mock-disconnected' and lost_status['mockFaults']==1 and lost_status['acknowledged']==0,
                  'Mock disconnection reports a bounded fault code and no delivery acknowledgement')
            read_status('connecting')
            accept(stop_peer,1,first_status_connection)
            check(read_status('active')['attachments']==2, 'After disconnection the live status reports a fresh attachment')
            next_ids = publish([(alpha,'ShotFired')])
            next_status_batch = stop_peer.read('feedback')
            assert [row['signal']['reportId'] for row in next_status_batch['signals']]==next_ids
            read_status('awaiting-ack')
            stop_peer.reply()
            check(read_status('active')['acknowledged']==1, 'Only the new confirmed batch advances the live acknowledgement count')
            pending_ids = publish([(alpha,'ShotFired')])
            pending_status_batch = stop_peer.read('feedback')
            assert [row['signal']['reportId'] for row in pending_status_batch['signals']]==pending_ids
            read_status('awaiting-ack')
            stop_peer.reply('observe-close')
            status_stop.touch()
            assert stop_peer.read('closed')['batchId']==pending_status_batch['batchId']
            final_status = read_status('stopped')
            status_result = json.loads(status_report.read_text(encoding='utf-8'))
            status_gateway.wait(timeout=8)
            status_reader.join(timeout=5)
            final_summary = json.loads(status_lines.get(timeout=1))
            check(status_gateway.returncode==0 and not status_reader.is_alive() and status_lines.empty()
                  and final_status['termination']=='operator-stop' and final_status['batches']==3
                  and final_status['acknowledged']==status_result['acknowledged']==final_summary['acknowledged']==1
                  and [row['status'] for row in status_result['attempts']]==['mock-disconnected','simulated-acknowledged','cancelled'],
                  'The final live status agrees with the durable report after operator stop cancels the pending batch')
            save('operator-status.json', status_history)

            gateways = {room:invoke(room,f'Room{room}',out/f'room-{room}-report.json') for room in peers}
            connections = {room:accept(peer,room) for room,peer in peers.items()}

            def feedback(room, ids):
                frame = peers[room].read('feedback')
                assert frame['roomId']==room and frame['connectionId']==connections[room] and frame['streamId']==stream
                assert [item['signal']['reportId'] for item in frame['signals']]==ids
                for item in frame['signals']:
                    signal = item['signal']; binding = expected[signal['playerId']]
                    assert (item['deviceId'],signal['admissionId'],signal['seat'])==(binding['deviceId'],binding['admissionId'],binding['seat'])
                return frame

            duplicate_report = out/'duplicate-room-report.json'
            duplicate = invoke(1,'Room1',duplicate_report,config=stop_config)
            wait(lambda:duplicate.poll() is not None or not stop_peer.lines.empty(), 'duplicate room decision')
            if not stop_peer.lines.empty():
                other_connection = accept(stop_peer,1)
                ids = publish([(alpha,'ShotFired')]); original_feedback = feedback(1,ids)
                copied_feedback = stop_peer.read('feedback')
                assert copied_feedback['connectionId']==other_connection
                assert copied_feedback['signals']==original_feedback['signals']
                save('duplicate-room-witness.json', {'original':original_feedback,'duplicate':copied_feedback})
                raise AssertionError('A second gateway in the same room received the same accepted signal')
            denial, _ = duplicate.communicate(timeout=8)
            check(duplicate.returncode==1 and 'GatewayLeaseUnavailable' in denial and not duplicate_report.exists()
                  and not any(secret in denial for secret in private),
                  'A different configuration, peer port and report cannot open a second gateway for the same room and session')

            ids = publish([(alpha,'ShotFired'),(bravo,'PlayerDamaged'),(unbound,'ShotFired'),(charlie,'PlayerDamaged')])
            feedback(1,ids[:2]); feedback(2,ids[3:]); peers[1].reply(); peers[2].reply()
            check(True, 'Two mock processes receive only their room and exact admission; a stale admission binding is excluded')

            for fault in ('wrong','timeout','drop'):
                ids = publish([(alpha,'ShotFired')])
                feedback(1,ids)
                before_reconnect = attached(1)
                peers[1].reply(fault)
                hello = peers[1].read('hello')
                assert hello['connectionId']!=connections[1]
                publish([(alpha,'ShotFired')])
                # The read before hello must not count as the attachment after ready.
                wait(lambda:attached(1)>before_reconnect, 'pre-handshake read after '+fault)
                count = attached(1)
                peers[1].reply()
                wait(lambda:attached(1)>count, 'reattachment after '+fault)
                connections[1] = hello['connectionId']
                ids = publish([(alpha,'ShotFired')])
                feedback(1,ids); peers[1].reply()
                check(True, 'Fresh cursor after '+fault+' skips the feedback generated while disconnected')

            ids = publish([(alpha,'ShotFired')]); paused_batch = feedback(1,ids)
            action('Pause'); peers[1].reply('observe-close')
            closed_batch = peers[1].read('closed')
            save('pause-close.json',closed_batch)
            check(closed_batch['connectionId']==paused_batch['connectionId'] and closed_batch['batchId']==paused_batch['batchId'],
                  'Pause closes the exact pending connection without an ACK')
            old_epoch = epoch; epoch = action('Resume')
            connections = {room:accept(peer,room,connections[room]) for room,peer in peers.items()}
            publish([(alpha,'ShotFired')], observed=old_epoch)
            ids = publish([(alpha,'ShotFired')]); feedback(1,ids); peers[1].reply()
            check(True, 'Resume emits only the new Running epoch after a paused in-flight batch')

            inflight_stop = runtime/'inflight.stop'
            inflight_report = out/'inflight-stop-report.json'
            room_three = runtime/'room-3-stop.json'
            room_three.write_text(json.dumps({'version':1,'managementUrl':base,'sessionId':sid,'roomId':3,'mockPort':stop_peer.port,
                'seconds':35,'bindings':[{'deviceId':str(uuid.uuid4()),'playerId':delta['id'],'admissionId':delta['admissionId'],
                                          'seat':delta['seat']}]}),encoding='utf-8')
            inflight = invoke(3,'Room3',inflight_report,config=room_three,stop=inflight_stop)
            stop_connection = accept(stop_peer,3,idle_connection)
            ids = publish([(alpha,'ShotFired'),(delta,'ShotFired')]); feedback(1,ids[:1]); peers[1].reply()
            stopped_batch = stop_peer.read('feedback')
            stop_peer.reply('observe-close')
            inflight_stop.touch()
            stop_close = stop_peer.read('closed')
            save('inflight-stop-close.json',stop_close)
            stop_result = stopped(inflight,inflight_report,attached_once=True)
            attempt, = stop_result['attempts']
            check(stop_close['connectionId']==stopped_batch['connectionId']==attempt['connectionId']==stop_connection
                  and stop_close['batchId']==stopped_batch['batchId']==attempt['batchId']
                  and attempt['status']=='cancelled' and [d['signal']['reportId'] for d in attempt['deliveries']]==ids[1:],
                  'Operator stop closes the exact pending batch with no simulated acknowledgement')

            interrupted_report = out/'interrupted-room-3-report.json'
            interrupted = invoke(3,'Room3',interrupted_report,config=room_three)
            dead_connection = accept(stop_peer,3,stop_connection)
            held, = publish([(delta,'ShotFired')])
            pending = stop_peer.read('feedback'); stop_peer.reply('observe-close')
            interrupted.kill(); interrupted.wait(timeout=8)
            disconnected = stop_peer.read('closed')
            check(interrupted.returncode!=0 and not interrupted_report.exists()
                  and disconnected['connectionId']==pending['connectionId']==dead_connection
                  and disconnected['batchId']==pending['batchId'] and disconnected['transport'] in ('eof','reset')
                  and pending['signals'][0]['signal']['reportId']==held,
                  'An abruptly killed owner closes its held batch and cannot publish a successful report')
            save('interrupted-room-3-close.json',disconnected)
            skipped, = publish([(delta,'ShotFired')])
            recovered_report = out/'room-3-recovered-report.json'
            recovered = invoke(3,'Room3',recovered_report,config=room_three)
            recovered_connection = accept(stop_peer,3,dead_connection)
            delivered, = publish([(delta,'PlayerDamaged')]); resumed = stop_peer.read('feedback'); stop_peer.reply()
            assert resumed['connectionId']==recovered_connection and resumed['signals'][0]['signal']['reportId']==delivered

            ids = publish([(charlie,'PlayerDamaged')]); feedback(2,ids); peers[2].reply()
            ids = publish([(charlie,'ShotFired')]); ended_batch = feedback(2,ids)
            action('End'); peers[2].reply('observe-close')
            closed_batch = peers[2].read('closed')
            save('end-close.json',closed_batch)
            check(closed_batch['connectionId']==ended_batch['connectionId'] and closed_batch['batchId']==ended_batch['batchId'],
                  'End closes the exact pending connection without an ACK')
            request(path+'/combat-stream/seal',{'streamId':stream,'finalSequence':sequence},'GameServer')
            recovered_log, _ = recovered.communicate(timeout=8)
            recovered_result = json.loads(recovered_report.read_text(encoding='utf-8'))
            resumed_attempt, = recovered_result['attempts']
            check(recovered.returncode==0 and not any(secret in recovered_log for secret in private)
                  and recovered_result['termination']=='ended' and recovered_result['acknowledged']==1
                  and recovered_result['physicalDeliveryConfirmed'] is False and resumed_attempt['connectionId']==recovered_connection
                  and [item['signal']['reportId'] for item in resumed_attempt['deliveries']]==[delivered]
                  and delivered not in (held,skipped),
                  'Replacement acquires the room after process death and skips the held and offline signals')
            reports = {}
            for room, gateway in gateways.items():
                output, _ = gateway.communicate(timeout=8)
                assert not any(secret in output for secret in private)
                assert gateway.returncode==0, output
                raw = (out/f'room-{room}-report.json').read_text(encoding='utf-8')
                assert not any(secret in raw for secret in private)
                report = json.loads(raw)
                check(report['complete'] and report['termination']=='ended' and report['physicalDeliveryConfirmed'] is False,
                      f'Room {room} completes the mock rehearsal at End')
                reports[room] = report
            check([a['status'] for a in reports[1]['attempts']]==['simulated-acknowledged','mock-invalid-reply','simulated-acknowledged',
                  'mock-timeout','simulated-acknowledged','mock-disconnected','simulated-acknowledged','cancelled','simulated-acknowledged',
                  'simulated-acknowledged'] and reports[1]['acknowledged']==7 and reports[1]['mockFaults']==3,
                  'Wrong ACK, timeout, disconnect and Pause remain non-acknowledged attempts')
            check([a['status'] for a in reports[2]['attempts']]==['simulated-acknowledged','simulated-acknowledged','cancelled']
                  and reports[2]['acknowledged']==2 and reports[2]['connections']==2,
                  'The other room acknowledges on its resumed connection after the operator stop and still cancels at End')
            history = {e['eventId']:e for e in request(path+'/events')}
            for report in [*reports.values(),stop_result,recovered_result]:
                for attempt in report['attempts']:
                    for delivery in attempt['deliveries']:
                        signal = delivery['signal']; original = history[signal['eventId']]
                        assert original['sequence']==signal['eventSequence'] and original['payload']['report']['reportId']==signal['reportId']
            check(request('/api/sessions')==[] and request(path)['combatStream']['acceptedSequence']==sequence,
                  'Every attempted event preserves the accepted witness and the gateway never writes session events')

            rooms = list(range(1,6))
            session = request('/api/sessions', {'missionId':mission['id'],'mode':'Linked','roomIds':rooms})
            sid = session['id']; path = '/api/sessions/'+sid
            for room in rooms:
                session = request(path+'/players', {'playerId':str(uuid.uuid4()),'roomId':room,
                    'name':f'Bound fixture {room}','headset':'Quest3'}, f'Room{room}')
            players = {player['roomId']:player for player in session['players']}
            original = players[1]
            bound_peers = {room:Peer(room) for room in rooms}
            def mock_send(sock, frame):
                data = json.dumps(frame).encode()
                sock.sendall(struct.pack('>I',len(data))+data)

            def mock_refused(stream):
                try:
                    return stream.read(1) == b''
                except (ConnectionResetError, ConnectionAbortedError):
                    return True

            hello = {'version':1,'kind':'hello','mode':'simulation','connectionId':str(uuid.uuid4()),'roomId':1}
            with connect_peer(bound_peers[2].port) as sock, sock.makefile('rb') as wire:
                mock_send(sock,hello)
                assert mock_refused(wire)
            check(bound_peers[2].read('room-rejected')=={'kind':'room-rejected','roomId':1,'expectedRoomId':2},
                  'A room-assigned mock rejects the wrong room even when no gateway owns its port')
            for wrong in ({'roomId':1},{'connectionId':str(uuid.uuid4())}):
                with connect_peer(bound_peers[2].port) as sock, sock.makefile('rb') as wire:
                    valid = {**hello,'roomId':2,'connectionId':str(uuid.uuid4())}
                    mock_send(sock,valid)
                    assert bound_peers[2].read('hello')==valid
                    bound_peers[2].reply()
                    size, = struct.unpack('>I',wire.read(4))
                    assert json.loads(wire.read(size))=={'version':1,'kind':'ready','connectionId':valid['connectionId']}
                    mock_send(sock,{**valid,'kind':'feedback','batchId':str(uuid.uuid4()),'signals':[],**wrong})
                    assert mock_refused(wire) and bound_peers[2].lines.empty()
            check(True, 'Mock feedback must retain both the handshaken room and connection before it can be acknowledged')
            maps = {room:{'version':1,'managementUrl':base,'sessionId':sid,'roomId':room,
                'mockPort':peer.port,'seconds':35,'devices':[{'seat':0,'deviceId':str(uuid.uuid4())}]}
                for room,peer in bound_peers.items()}
            feed = path+'/rooms/1/hardware-feedback'
            old_page = request(feed, role='Room1')
            new_page = request(feed+'?includeBindings=true', role='Room1')
            assert old_page['version']==1 and 'bindings' not in old_page
            assert new_page['version']==2 and new_page['bindings']==[{k:original[v] for k,v in
                (('playerId','id'),('admissionId','admissionId'),('seat','seat'))}]
            for role in ('Room2','GameServer'):
                try:
                    request(feed+'?includeBindings=true', role=role)
                except urllib.error.HTTPError as denied:
                    assert denied.code==403
                    denied.close()
                else:
                    raise AssertionError('Foreign feedback roster was readable')
            check(True, 'Opt-in roster is exact and room scoped while legacy feedback keeps its original shape')

            def bind(label, seat_map, role, expected_type=None):
                input_path = runtime/(label+'-map.json')
                result_path = runtime/(label+'-binding.json')
                input_path.write_text(json.dumps(seat_map),encoding='utf-8')
                process = start(['dotnet',str(binary),'--bind-room',str(input_path),'--output',str(result_path)],
                                {**env,'VR_COMMAND_ROOM_KEY':keys[role]})
                output, _ = process.communicate(timeout=8)
                assert not any(secret in output for secret in private)
                if expected_type:
                    assert process.returncode==1 and expected_type in output and not result_path.exists(), output
                    return None
                assert process.returncode==0 and json.loads(output)['boundSeats']==len(seat_map['devices']), output
                raw = result_path.read_text(encoding='utf-8')
                assert not any(secret in raw for secret in private)
                return result_path

            before_bind = request(path)
            original_config = bind('original', maps[1], 'Room1')
            assert all(peer.lines.empty() for peer in bound_peers.values())
            bind('wrong-room', maps[1], 'Room2', 'AccessDeniedException')
            bind('vacant', {**maps[1],'devices':[{'seat':4,'deviceId':str(uuid.uuid4())}]}, 'Room1', 'InvalidOperationException')
            bind('missing-seat', {**maps[1],'devices':[{'deviceId':str(uuid.uuid4())}]}, 'Room1', 'JsonException')
            check(request(path)==before_bind and all(peer.lines.empty() for peer in bound_peers.values()),
                  'Binding generation is read-only, opens no mock connection and refuses wrong, vacant and incomplete maps')
            request(path+'/players/'+original['id'], role='Room1', method='DELETE', admission=original['admissionId'])
            session = request(path+'/players',{'playerId':original['id'],'roomId':1,'name':'Same ID, new admission','headset':'Quest3'},'Room1')
            replacement = next(p for p in session['players'] if p['id']==original['id'])
            assert replacement['seat']==original['seat'] and replacement['admissionId']!=original['admissionId']

            def mismatch(gateway, report, connections):
                output, _ = gateway.communicate(timeout=8)
                assert gateway.returncode==1 and not any(secret in output for secret in private), output
                result = json.loads(report.read_text(encoding='utf-8'))
                assert result['termination']=='binding-mismatch' and not result['complete'] and result['acknowledged']==0
                assert result['attachments']==result['connections']==connections and result['physicalDeliveryConfirmed'] is False
                return result

            stale_report = out/'stale-binding-report.json'
            stale = invoke(1,'Room1',stale_report,config=original_config)
            check(mismatch(stale,stale_report,0)['attempts']==[] and bound_peers[1].lines.empty(),
                  'A replaced admission with the same player and seat is refused before any mock handshake')
            players[1] = replacement
            updated = {room:bind(f'updated-{room}',maps[room],f'Room{room}') for room in rooms}
            for room,player in players.items():
                value = json.loads(updated[room].read_text(encoding='utf-8'))
                assert value['version']==2 and value['bindings']==[{'deviceId':maps[room]['devices'][0]['deviceId'],
                    'playerId':player['id'],'admissionId':player['admissionId'],'seat':player['seat']}]
                save(f'bound-room-{room}-config.json',value)
            check(True, 'Explicit regeneration preserves each of the five device maps and binds the new admission')
            bound_reports = {room:out/f'bound-room-{room}-report.json' for room in bound_peers}
            preparing_reads = attached(1, bound=True)
            preparing = invoke(1,'Room1',bound_reports[1],config=updated[1])
            wait(lambda:attached(1,bound=True)>=preparing_reads+2 or not bound_peers[1].lines.empty(),
                 'gateway polls the Preparing room without arming the mock')
            check(bound_peers[1].lines.empty() and preparing.poll() is None,
                  'A correctly bound Preparing room waits for Running without a mock handshake')
            stream = str(uuid.uuid4())
            request(path+'/combat-stream', {'streamId':stream,'origin':'Simulation'}, 'GameServer')
            epoch = action('Begin'); sequence = 0
            peers = bound_peers
            expected = {player['id']:json.loads(updated[room].read_text(encoding='utf-8'))['bindings'][0] for room,player in players.items()}
            gateways = {1:preparing}
            connections = {1:accept(peers[1],1,bound=True)}
            room_two = json.loads(updated[2].read_text(encoding='utf-8'))
            device_id = expected[replacement['id']]['deviceId']
            shared_device = runtime/'shared-device.json'
            shared_device.write_text(json.dumps({**room_two,'bindings':[{**room_two['bindings'][0],'deviceId':device_id}]}),encoding='utf-8')
            device_report = out/'shared-device-report.json'
            candidate = invoke(2,'Room2',device_report,config=shared_device)
            wait(lambda:candidate.poll() is not None or not peers[2].lines.empty(), 'shared device decision')
            if not peers[2].lines.empty():
                foreign_connection = accept(peers[2],2,bound=True)
                ids = publish([(replacement,'ShotFired'),(players[2],'ShotFired')])
                original_batch = feedback(1,ids[:1]); foreign_batch = peers[2].read('feedback')
                assert foreign_batch['connectionId']==foreign_connection and foreign_batch['roomId']==2
                assert foreign_batch['signals'][0]['signal']['reportId']==ids[1]
                assert original_batch['signals'][0]['deviceId']==foreign_batch['signals'][0]['deviceId']==device_id
                peers[1].reply(); peers[2].reply()
                save('shared-device-witness.json',{'original':original_batch,'foreign':foreign_batch})
                raise AssertionError('Two active rooms sent different accepted signals to the same logical device ID')
            denial,_ = candidate.communicate(timeout=8)
            check(candidate.returncode==1 and 'DeviceLeaseUnavailable' in denial and not device_report.exists()
                  and not any(secret in denial for secret in private),
                  'Another room cannot acquire a bound device even with its own mock port and valid admission')

            shared_port = runtime/'shared-port.json'
            shared_port.write_text(json.dumps({**room_two,'mockPort':peers[1].port}),encoding='utf-8')
            port_report = out/'shared-port-report.json'
            candidate = invoke(2,'Room2',port_report,config=shared_port)
            denial,_ = candidate.communicate(timeout=8)
            check(candidate.returncode==1 and 'MockPortLeaseUnavailable' in denial and not port_report.exists()
                  and peers[1].lines.empty() and not any(secret in denial for secret in private),
                  'Another room cannot use the original active mock port even with a distinct device binding')
            for room in rooms[1:]:
                gateways[room] = invoke(room,f'Room{room}',bound_reports[room],config=updated[room])
                connections[room] = accept(peers[room],room,bound=True)
            check(len(set(connections.values()))==5, 'Denied starts release partial leases and all five correct rooms attach')
            ids = publish([(replacement,'ShotFired')]); revoked_batch = feedback(1,ids)
            peers[1].reply('observe-close')
            request(path+'/players/'+replacement['id'], role='Room1', method='DELETE', admission=replacement['admissionId'])
            removed = peers[1].read('closed')
            attempt, = mismatch(gateways[1],bound_reports[1],1)['attempts']
            check(attempt['status']=='cancelled' and attempt['batchId']==removed['batchId']==revoked_batch['batchId']
                  and attempt['connectionId']==removed['connectionId']==revoked_batch['connectionId'],
                  'Removing an admission cancels the exact in-flight batch and closes its mock connection')
            save('binding-mismatch-close.json',removed)
            first_reports = {}
            for room in rooms[1:]:
                first_reports[room] = publish([(players[room],'ShotFired')])[0]
                feedback(room,[first_reports[room]]); peers[room].reply()
            # Receipt of the second batch proves the first round has cleared its ACK and eligibility check.
            for room in rooms[1:]:
                ids = publish([(players[room],'PlayerDamaged')]); feedback(room,ids); peers[room].reply()
            action('End')
            for room in rooms[1:]:
                stdout,_ = gateways[room].communicate(timeout=8)
                result = json.loads(bound_reports[room].read_text(encoding='utf-8'))
                confirmed = [delivery['signal']['reportId'] for batch in result['attempts'] if batch['status']=='simulated-acknowledged'
                             for delivery in batch['deliveries']]
                assert gateways[room].returncode==0 and not any(secret in stdout for secret in private)
                assert first_reports[room] in confirmed and result['connections']==result['attachments']==1
                assert result['termination']=='ended' and result['complete'] and result['physicalDeliveryConfirmed'] is False
            check(peers[1].lines.empty(), 'All four other rooms keep their original connections after a binding mismatch and end normally')
            request(path+'/combat-stream/seal',{'streamId':stream,'finalSequence':sequence},'GameServer')
            bind('ended',maps[2],'Room2','InvalidOperationException')
            check(request('/api/sessions')==[], 'Room binding rehearsal leaves no active session')

            def venue_denied(role, status):
                try:
                    request('/api/venue/hardware-bindings', role=role)
                except urllib.error.HTTPError as denied:
                    assert denied.code == status
                    denied.close()
                else:
                    raise AssertionError('An unavailable or unauthorized venue snapshot was readable')

            venue_denied('Master', 409)
            for role in ('Room1', 'GameServer'):
                venue_denied(role, 403)
            check(True, 'Only a master with all five occupied rooms can read the venue binding snapshot')

            def bind_venue(label, venue_map, role='Master', error=None, *, destination=None):
                input_path = runtime / f'{label}-venue-map.json'
                input_path.write_text(json.dumps(venue_map), encoding='utf-8')
                result_path = destination or out / f'{label}-bindings'
                existed = result_path.exists()
                process = start(['dotnet',str(binary),'--bind-venue',str(input_path),'--output',str(result_path)],
                                {**env, 'VR_COMMAND_MASTER_KEY':keys[role]})
                output, _ = process.communicate(timeout=8)
                assert not any(secret in output for secret in private)
                if error:
                    assert process.returncode == 1 and error in output and result_path.exists() == existed, output
                    return None
                assert process.returncode == 0 and json.loads(output) == {
                    'complete':True,'mode':venue_map['mode'],'rooms':5,'boundSeats':25}, output
                return result_path

            for mode in ('Linked', 'Independent'):
                groups = [list(rooms)] if mode == 'Linked' else [[room] for room in rooms]
                label = mode.lower()
                owners, venue_streams, rosters = {}, {}, {}
                venue_peers = {room:Peer(room) for room in rooms}
                for group in groups:
                    view = request('/api/sessions', {'missionId':mission['id'],'mode':mode,'roomIds':group})
                    venue_path = '/api/sessions/' + view['id']
                    for room in group:
                        owners[room] = view['id']
                        for seat in range(5):
                            view = request(venue_path+'/players', {'playerId':str(uuid.uuid4()),'roomId':room,
                                'name':f'Venue binding {room}/{seat}','headset':'Quest3'},f'Room{room}')
                        rosters[room] = [player for player in view['players'] if player['roomId'] == room]
                venue_map = {'version':1,'managementUrl':base,'mode':mode,'seconds':60,'rooms':[
                    {'roomId':room,'sessionId':owners[room],'mockPort':venue_peers[room].port,
                     'devices':[{'seat':seat,'deviceId':str(uuid.uuid4())} for seat in reversed(range(5))]}
                    for room in reversed(rooms)]}
                original = request('/api/venue/hardware-bindings')
                assert original['version'] == 1 and original['mode'] == mode and len(original['rooms']) == 5
                if mode == 'Linked':
                    venue_denied('Room2', 403)
                    before = request('/api/sessions')
                    altered = json.loads(json.dumps(venue_map))
                    altered['rooms'][0]['devices'][0]['deviceId'] = altered['rooms'][1]['devices'][0]['deviceId']
                    bind_venue('duplicate-venue-device', altered, error='ArgumentException')
                    altered = json.loads(json.dumps(venue_map))
                    altered['rooms'][0]['mockPort'] = altered['rooms'][1]['mockPort']
                    bind_venue('duplicate-venue-port', altered, error='ArgumentException')
                    bind_venue('stale-venue', {**venue_map, 'rooms': [dict(row, sessionId=str(uuid.UUID(int=37))) for row in venue_map['rooms']]},
                               error='InvalidOperationException')
                    bind_venue('wrong-venue-role', venue_map, 'Room1', error='AccessDeniedException')
                    missing = rosters[5][-1]
                    target_path = '/api/sessions/'+owners[5]+'/players'
                    request(target_path+'/'+missing['id'], role='Room5', method='DELETE', admission=missing['admissionId'])
                    bind_venue('vacant-venue-seat', venue_map, error='InvalidOperationException')
                    view = request(target_path, {'playerId':missing['id'],'roomId':5,'name':missing['name'],'headset':'Quest3'},'Room5')
                    rosters[5] = [player for player in view['players'] if player['roomId'] == 5]
                    original = request('/api/venue/hardware-bindings')
                    assert request('/api/sessions')[0]['sequence'] > before[0]['sequence']
                    check(all(peer.lines.empty() for peer in venue_peers.values()),
                          'Duplicate resources, stale sessions, vacant seats and wrong roles publish no venue settings or device traffic')

                previous = request('/api/sessions')
                folder = bind_venue(label, venue_map)
                manifest = json.loads((folder/'venue-bindings.json').read_bytes())
                assert manifest['version'] == 1 and manifest['mode'] == mode
                assert sorted(file.name for file in folder.iterdir()) == [*[f'room-{room:02}.json' for room in rooms], 'venue-bindings.json']
                config_files, expected_devices = {}, {}
                for plan, actual, snapshot in zip(sorted(venue_map['rooms'], key=lambda row: row['roomId']), manifest['rooms'], original['rooms'], strict=True):
                    room = plan['roomId']
                    assert actual == {'roomId':room,'sessionId':owners[room],'sessionSequence':snapshot['sessionSequence'],
                                      'configuration':f'room-{room:02}.json','boundSeats':5}
                    config_files[room] = folder/actual['configuration']
                    assert not any(secret in config_files[room].read_text(encoding='utf-8') for secret in private)
                    config = json.loads(config_files[room].read_bytes())
                    expected_devices[room] = {device['seat']:device['deviceId'] for device in plan['devices']}
                    assert config == {'version':2,'managementUrl':base,'sessionId':owners[room],'roomId':room,
                        'mockPort':plan['mockPort'],'seconds':60,'bindings':[
                            {'deviceId':expected_devices[room][player['seat']], 'playerId':player['id'],
                             'admissionId':player['admissionId'],'seat':player['seat']}
                            for player in sorted(rosters[room], key=lambda player: player['seat'])]}
                hashes = {file:sha(file) for file in folder.iterdir()}
                bind_venue(label+'-same-path', venue_map, error='ArgumentException', destination=folder)
                check(request('/api/sessions') == previous and all(peer.lines.empty() for peer in venue_peers.values())
                      and all(sha(file)==digest for file,digest in hashes.items()) and not list(out.glob('.vr-venue-bindings-*')),
                      f'{mode} publishes all 25 exact bindings from one read-only snapshot and preserves existing output')

                for owner in set(owners.values()):
                    venue_path = '/api/sessions/' + owner
                    stream_id = str(uuid.uuid4())
                    request(venue_path+'/combat-stream', {'streamId':stream_id,'origin':'Simulation'}, 'GameServer')
                    started = request(venue_path+'/commands', {'commandId':str(uuid.uuid4()),'action':'Begin'})
                    venue_streams[owner] = (stream_id, started['appliedAtSequence'], 0)
                status_directory = out/f'{label}-status'
                status_directory.mkdir()

                def venue_status(directory=status_directory):
                    result = subprocess.run(['dotnet',str(binary),'--venue-status',str(folder/'venue-bindings.json'),
                                             '--status-directory',str(directory)],env=env,check=True,timeout=5,
                                            capture_output=True,text=True,encoding='utf-8',creationflags=HIDDEN)
                    assert not result.stderr and not any(secret in result.stdout for secret in private)
                    summary = json.loads(result.stdout)
                    assert summary['mode']==mode and summary['physicalDeliveryConfirmed'] is False
                    assert [(row['roomId'],row['sessionId']) for row in summary['rooms']]==list(owners.items())
                    return summary['rooms']

                def venue_ack_count(directory, room):
                    snapshot = venue_status(directory)[room-1]['status']
                    return snapshot['progress']['acknowledged'] if snapshot is not None else None

                check(all(row['state']=='waiting' and row['status'] is None for row in venue_status()) and not list(status_directory.iterdir()),
                      f'{mode} status without credentials reports five waiting rooms and writes no files')
                venue_connections = {}

                def publish_venue_batch(room, count):
                    stream_id, observed, position = venue_streams[owners[room]]
                    reports = [{'streamId':stream_id,'streamSequence':position+index+1,'observedSequence':observed,
                                'report':{'reportId':str(uuid.uuid4()),'kind':'ShotFired','origin':'Simulation','playerId':player['id'],
                                          'shotId':str(uuid.uuid4())}} for index,player in enumerate(rosters[room][:count])]
                    request('/api/sessions/'+owners[room]+'/combat-stream/batch', reports, 'GameServer')
                    venue_streams[owners[room]] = (stream_id, observed, position+count)
                    return reports

                def send_venue_batch(room, count, decision='ack'):
                    reports = publish_venue_batch(room, count)
                    received = venue_peers[room].read('feedback')
                    assert received['roomId']==room and received['connectionId']==venue_connections[room]
                    assert [(row['signal']['reportId'],row['deviceId']) for row in received['signals']] == [
                        (report['report']['reportId'],expected_devices[room][player['seat']])
                        for report,player in zip(reports,rosters[room][:count],strict=True)]
                    if decision is not None:
                        venue_peers[room].reply(decision)
                    return {report['report']['reportId'] for report in reports}

                def start_fleet(bindings_folder, destination, stop, **overrides):
                    credentials = {f'VR_COMMAND_ROOM_{room}_KEY':keys[f'Room{room}'] for room in rooms}
                    return start(['dotnet',str(binary),'--live-venue',str(bindings_folder/'venue-bindings.json'),
                                  '--output',str(destination),'--stop-file',str(stop)], {**env, **credentials, **overrides})

                fleet_stop = runtime/f'{label}-fleet.stop'
                fleet_directory = out/f'{label}-fleet'
                if mode=='Linked':
                    def refused(bindings_folder, error, **overrides):
                        denied = start_fleet(bindings_folder, fleet_directory, fleet_stop, **overrides)
                        diagnostic, _ = denied.communicate(timeout=8)
                        assert denied.returncode==1 and error in diagnostic and not any(secret in diagnostic for secret in private)
                        assert not fleet_directory.exists()

                    refused(folder, 'AccessDeniedException', VR_COMMAND_ROOM_5_KEY=keys['Room4'])
                    altered = runtime/'altered-venue-bindings'
                    shutil.copytree(folder, altered)
                    changed_path = altered/config_files[5].name
                    configuration = json.loads(changed_path.read_bytes())
                    changed_path.write_text(json.dumps(dict(configuration, managementUrl='http://127.0.0.1:1')), encoding='utf-8')
                    refused(altered, 'InvalidDataException')
                    configuration['bindings'][0]['admissionId'] = str(uuid.uuid4())
                    changed_path.write_text(json.dumps(configuration), encoding='utf-8')
                    refused(altered, 'InvalidOperationException')
                    check(all(peer.lines.empty() for peer in venue_peers.values()),
                          'Wrong room key, mixed management origins and stale admissions refuse the fleet before publishing or connecting')

                    owner_stop = runtime/'original-room-five.stop'
                    owner_report = out/'original-room-five-stop-report.json'
                    original_room = invoke(5,'Room5',owner_report,config=config_files[5],stop=owner_stop)
                    path = '/api/sessions/' + owners[5]
                    original_hello = venue_peers[5].read('hello')
                    prior_attach = attached(5,bound=True)
                    venue_peers[5].reply('ready-observe-close')
                    wait(lambda:attached(5,bound=True)>prior_attach, 'original room five attaches before the conflicting fleet')
                    refused(folder, 'GatewayLeaseUnavailable')
                    assert original_room.poll() is None and all(peer.lines.empty() for peer in venue_peers.values())
                    owner_stop.touch()
                    original_close = venue_peers[5].read('closed')
                    stopped(original_room,owner_report,attached_once=True)
                    check(original_close['connectionId']==original_hello['connectionId'],
                          'A lease conflict keeps the original room five alive and releases the four partial fleet leases')

                fleet = start_fleet(folder, fleet_directory, fleet_stop)
                for room in rooms:
                    path = '/api/sessions/' + owners[room]
                    venue_connections[room] = accept(venue_peers[room], room, bound=True)
                fleet_delivered = {room:send_venue_batch(room, 5) for room in rooms}
                wait(lambda:all(row['state']=='current' and row['status']['progress']['acknowledged']==5
                                for row in venue_status(fleet_directory)), f'{mode} fleet acknowledges all 25 current bindings')
                room_two_pending = send_venue_batch(2, 1, 'observe-close')
                (fleet_directory/'room-02.stop').touch()
                local_close = venue_peers[2].read('closed')
                stopped_room = wait(lambda:row if (row:=venue_status(fleet_directory)[1])['state']=='stopped' else None,
                                    f'{mode} room two stops independently')
                assert stopped_room['status']['termination']=='operator-room-stop'
                assert stopped_room['status']['progress']['acknowledged']==5
                local_report_path = fleet_directory/'room-02-report.json'
                local_report_bytes = local_report_path.read_bytes()
                assert fleet.poll() is None and not fleet_stop.exists() and not (fleet_directory/'venue-report.json').exists()
                wait(lambda:all(row['state']=='current' for room,row in zip(rooms,venue_status(fleet_directory),strict=True) if room!=2),
                     f'{mode} the four unaffected rooms publish current snapshots after room two stops')
                fleet_delivered[5] |= send_venue_batch(5, 1)
                wait(lambda:venue_ack_count(fleet_directory, 5)==6,
                     f'{mode} room five acknowledges on its original connection after room two stops')

                separate_marker = runtime/f'{label}-room-two-restart.stop'
                separate_report = out/f'{label}-room-two-restart.json'
                restarted = invoke(2,'Room2',separate_report,config=config_files[2],stop=separate_marker)
                path = '/api/sessions/' + owners[2]
                restart_hello = venue_peers[2].read('hello')
                assert restart_hello['roomId']==2 and restart_hello['connectionId']!=venue_connections[2]
                prior_attach = attached(2,bound=True)
                venue_peers[2].reply('ready-observe-close')
                wait(lambda:attached(2,bound=True)>prior_attach, f'{mode} room two attaches on released leases')
                separate_marker.touch()
                restart_close = venue_peers[2].read('closed')
                stopped(restarted,separate_report,attached_once=True)
                assert restart_close['connectionId']==restart_hello['connectionId'] and fleet.poll() is None
                save(f'{label}-fleet-room-stop-close.json', local_close)
                save(f'{label}-fleet-room-restart-close.json', restart_close)
                held_ids = send_venue_batch(3, 1, 'observe-close')
                if mode=='Independent':
                    player = rosters[3][0]
                    room_path = '/api/sessions/'+owners[3]
                    request(room_path+'/players/'+player['id'], role='Room3', method='DELETE', admission=player['admissionId'])
                    closed_batch = venue_peers[3].read('closed')
                    wait(lambda:venue_status(fleet_directory)[2]['state']=='stopped', 'revoked fleet room stops')
                    assert fleet.poll() is None and not (fleet_directory/'venue-report.json').exists()
                    fleet_delivered[4] |= send_venue_batch(4, 1)
                    wait(lambda:venue_ack_count(fleet_directory, 4)==6, 'unaffected room still acknowledges')
                    fleet_stop.touch()
                else:
                    fleet_stop.touch()
                    closed_batch = venue_peers[3].read('closed')
                fleet_stdout, _ = fleet.communicate(timeout=8)
                fleet_report = json.loads((fleet_directory/'venue-report.json').read_bytes())
                assert json.loads(fleet_stdout)==fleet_report and fleet_report['mode']==mode and not fleet_report['physicalDeliveryConfirmed']
                manifest_path = folder/'venue-bindings.json'
                assert fleet_report['version']==4 and fleet_report['bindingManifestSha256']==sha(manifest_path)
                assert fleet.returncode==int(mode=='Independent') and fleet_report['complete'] is (mode=='Linked') and fleet_stop.is_file()
                assert len(set(venue_connections.values()))==5
                assert [(row['roomId'],row['sessionId']) for row in fleet_report['rooms']]==list(owners.items())
                assert local_report_path.read_bytes()==local_report_bytes
                for room, row in zip(rooms,fleet_report['rooms'],strict=True):
                    mismatch_room = mode=='Independent' and room==3
                    original_report = fleet_directory/f'room-{room:02}-report.json'
                    assert row=={'roomId':room,'sessionId':owners[room],'exitCode':int(mismatch_room),
                                 'report':original_report.name,'error':None,'sha256':sha(original_report),
                                 'bytes':original_report.stat().st_size,'configurationSha256':sha(config_files[room])}
                    report = json.loads(original_report.read_bytes())
                    delivered = {delivery['signal']['reportId'] for attempt in report['attempts']
                                 if attempt['status']=='simulated-acknowledged' for delivery in attempt['deliveries']}
                    assert delivered==fleet_delivered[room] and not report['physicalDeliveryConfirmed']
                    reason = {2:'operator-room-stop',3:'binding-mismatch' if mismatch_room else 'operator-stop'}
                    assert report['termination']==reason.get(room,'operator-stop')
                    if room in (2,3):
                        observed_close, cancelled_ids = (local_close,room_two_pending) if room==2 else (closed_batch,held_ids)
                        attempt, = [attempt for attempt in report['attempts'] if attempt['status']=='cancelled']
                        assert attempt['batchId']==observed_close['batchId'] and attempt['connectionId']==observed_close['connectionId']==venue_connections[room]
                        assert {delivery['signal']['reportId'] for delivery in attempt['deliveries']}==cancelled_ids
                assert all(row['state']=='stopped' for row in venue_status(fleet_directory))
                assert all(session['state']=='Running' for session in request('/api/sessions'))
                assert all(not any(secret in file.read_text(encoding='utf-8') for secret in private) for file in fleet_directory.glob('*.json'))
                save(f'{label}-fleet-close.json', closed_batch)
                check(True, f'{mode} room marker cancels only its original held batch and releases leases while other rooms continue')
                check(True, f'{mode} single-process fleet delivers all 25 exact bindings, cancels the held batch and publishes all terminal results')
                def review(directory, manifest=manifest_path):
                    return subprocess.run(['dotnet',str(binary),'--verify-venue-report',str(manifest),
                        '--report-directory',str(directory)],env={key:value for key,value in os.environ.items()
                        if not key.upper().startswith('VR_COMMAND_')},capture_output=True,timeout=10,creationflags=HIDDEN)
                reviewed = review(fleet_directory)
                assert reviewed.returncode==0 and not reviewed.stderr
                summary = json.loads(reviewed.stdout)
                assert summary['verified'] and summary['rehearsalComplete'] is fleet_report['complete']
                assert summary['bindingManifestSha256']==sha(manifest_path) and summary['physicalDeliveryConfirmed'] is False
                assert summary['configurationsVerified'] is True
                for row in summary['rooms']:
                    original = json.loads((fleet_directory/f"room-{row['roomId']:02}-report.json").read_bytes())
                    assert row['termination']==original['termination'] and row['acknowledged']==original['acknowledged']
                    assert row['cancelled']==sum(len(attempt['deliveries']) for attempt in original['attempts'] if attempt['status']=='cancelled')
                    assert row['mockFailed']==0
                    assert [seat['seat'] for seat in row['seats']]==list(range(5))
                    for seat in row['seats']:
                        for count, status in [('acknowledged','simulated-acknowledged'),('cancelled','cancelled')]:
                            assert seat[count]==sum(delivery['signal']['seat']==seat['seat']
                                for attempt in original['attempts'] if attempt['status']==status for delivery in attempt['deliveries'])
                        assert seat['mockFailed']==0
                save(f'{label}-fleet-offline-review.json',summary)
                check(True,f'{mode} offline review verifies all room reports and distinguishes completion from report consistency')
                def handoff(*options):
                    return subprocess.run(['dotnet',str(binary),*map(str,options)],env={key:value for key,value in os.environ.items()
                        if not key.upper().startswith('VR_COMMAND_')},capture_output=True,timeout=10,creationflags=HIDDEN)
                package = out/f'{label}-handoff.zip'
                pack_args = ('--pack-venue-report',manifest_path,'--report-directory',fleet_directory,'--output')
                packed = handoff(*pack_args,package)
                assert packed.returncode==0 and packed.stdout==reviewed.stdout and not packed.stderr
                with zipfile.ZipFile(package) as zipped:
                    archive_files = {name:zipped.read(name) for name in zipped.namelist()}
                expected = {f'bindings/{name}':(folder/name).read_bytes()
                    for name in ['venue-bindings.json',*[f'room-{room:02}.json' for room in rooms]]}
                expected.update({f'reports/{name}':(fleet_directory/name).read_bytes()
                    for name in ['venue-report.json',*[f'room-{room:02}-report.json' for room in rooms]]})
                assert archive_files==expected
                assert handoff('--verify-venue-zip',package).stdout==reviewed.stdout
                check(True,f'{mode} handoff ZIP preserves exactly the original evidence and verifies without extraction')
                if args.verify_event_export:
                    handoff_session_ids = list(dict.fromkeys(row['sessionId'] for row in summary['rooms']))
                    event_route = '/api/venue/hardware-events.zip?' + urlencode({'sessionId': handoff_session_ids}, doseq=True)
                    event_request = urllib.request.Request(base + event_route, headers={'Authorization': 'Bearer ' + keys['Master']})
                    try:
                        with opener.open(event_request, timeout=8):
                            raise AssertionError('The original fleet is still running')
                    except urllib.error.HTTPError as unavailable:
                        assert unavailable.code == 409
                        unavailable.close()
                    check(True, f'{mode} source archive is withheld until the original sessions are sealed')
                if mode=='Independent':
                    copied = runtime/'copied-venue-review'
                    shutil.copytree(fleet_directory,copied)
                    copied_bindings = runtime/'copied-venue-bindings'
                    shutil.copytree(folder,copied_bindings)
                    copied_manifest = copied_bindings/manifest_path.name
                    assert review(copied,copied_manifest).stdout==reviewed.stdout
                    destination = copied/'room-01-report.json'
                    exact = destination.read_bytes()
                    original_manifest = manifest_path.read_bytes()
                    edited_manifest = runtime/'modified-venue-manifest.json'
                    edited_manifest.write_bytes(original_manifest+b'\n')
                    rejected = [review(copied,edited_manifest)]
                    destination.write_bytes(exact+b'\n')
                    rejected.append(review(copied))
                    destination.unlink()
                    rejected.append(review(copied))
                    destination.write_bytes(exact)
                    copied_aggregate = copied/'venue-report.json'
                    original_aggregate = copied_aggregate.read_bytes()
                    invalid = json.loads(original_aggregate)
                    invalid['rooms'][0]['report'] = '../room-01-report.json'
                    copied_aggregate.write_text(json.dumps(invalid),encoding='utf-8')
                    rejected.append(review(copied))
                    copied_aggregate.write_bytes(original_aggregate)
                    config_path = copied_bindings/'room-01.json'
                    exact_config = config_path.read_bytes()
                    config_path.write_bytes(exact_config+b'\n')
                    rejected.append(review(copied,copied_manifest))
                    config_path.unlink()
                    rejected.append(review(copied,copied_manifest))
                    config_path.write_bytes(exact_config)
                    altered_room = json.loads(exact)
                    altered_room['attempts'][0]['deliveries'][0]['deviceId'] = str(uuid.uuid4())
                    destination.write_text(json.dumps(altered_room),encoding='utf-8')
                    invalid = json.loads(original_aggregate)
                    invalid['rooms'][0].update(sha256=sha(destination), bytes=destination.stat().st_size)
                    copied_aggregate.write_text(json.dumps(invalid),encoding='utf-8')
                    rejected.append(review(copied,copied_manifest))
                    assert all(result.returncode==1 and not result.stdout and b'Venue hardware report rejected:' in result.stderr
                               for result in rejected)
                    check(True,'Offline review survives relocation and rejects a changed manifest, changed or missing report, and a path outside the run')
                    check(True,'Offline review rejects changed or missing configurations and a rehashed delivery for the wrong device')
                    destination.write_bytes(exact)
                    legacy = json.loads(original_aggregate)
                    legacy['version'] = 2
                    for room in legacy['rooms']:
                        del room['configurationSha256']
                    copied_aggregate.write_text(json.dumps(legacy),encoding='utf-8')
                    old_review = review(copied)
                    assert old_review.returncode==0 and not old_review.stderr
                    old_summary = json.loads(old_review.stdout)
                    assert old_summary['configurationsVerified'] is False
                    assert all(row['seats'] is None for row in old_summary['rooms'])
                    check(True,'Legacy version 2 remains readable without a claim about room configuration or seat counts')
                    legacy_package = out/'legacy-handoff.zip'
                    legacy_packed = handoff('--pack-venue-report',manifest_path,'--report-directory',copied,'--output',legacy_package)
                    assert legacy_packed.returncode==0 and legacy_packed.stdout==old_review.stdout
                    assert handoff('--verify-venue-zip',legacy_package).stdout==old_review.stdout
                    with zipfile.ZipFile(legacy_package) as zipped:
                        assert len(zipped.namelist())==7 and not any(name.startswith('bindings/room-') for name in zipped.namelist())
                    check(True,'A legacy version 2 handoff retains only its verified original files')
                    original_zip = package.read_bytes()
                    assert handoff(*pack_args,package).returncode==1 and package.read_bytes()==original_zip
                    rejected_pack = runtime/'invalid-handoff.zip'
                    altered_config = copied_bindings/'room-01.json'
                    altered_config.write_bytes(exact_config+b'\n')
                    # Restore the original aggregate to check the altered configuration.
                    copied_aggregate.write_bytes(original_aggregate)
                    refused = handoff('--pack-venue-report',copied_manifest,'--report-directory',copied,'--output',rejected_pack)
                    assert refused.returncode==1 and not refused.stdout and not rejected_pack.exists()
                    assert not list(runtime.glob('.vr-hardware-handoff-*.tmp'))
                    for label_suffix, entries in (
                        ('outside-path', [(name if name!='reports/room-01-report.json' else '../extra.json',data)
                                          for name,data in archive_files.items()]),
                        ('changed', [(name,data+b'\n' if name=='bindings/room-01.json' else data) for name,data in archive_files.items()]),
                        ('missing', [(name,data) for name,data in archive_files.items() if name!='reports/room-01-report.json']),
                    ):
                        invalid_zip = runtime/f'{label_suffix}-handoff.zip'
                        with zipfile.ZipFile(invalid_zip,'x') as zipped:
                            for name,data in entries: zipped.writestr(name,data)
                        refused = handoff('--verify-venue-zip',invalid_zip)
                        assert refused.returncode==1 and not refused.stdout and b'Venue hardware ZIP rejected:' in refused.stderr
                    check(True,'Handoff rejects extra paths, changed or missing entries and preserves existing output on failure')
                if mode=='Linked':
                    fault_directory = out/'linked-fleet-authority-faults'
                    fault_stop = runtime/'linked-fleet-authority-faults.stop'
                    fault_bindings = runtime/'linked-fleet-authority-fault-bindings'
                    shutil.copytree(folder, fault_bindings)
                    with authority_gate(port, owners, ipc) as (origin, faults, injected):
                        for file in fault_bindings.glob('room-*.json'):
                            value = json.loads(file.read_bytes())
                            file.write_text(json.dumps(dict(value, managementUrl=origin)), encoding='utf-8')
                        faulty = start_fleet(fault_bindings, fault_directory, fault_stop)
                        for room in rooms:
                            path = '/api/sessions/' + owners[room]
                            venue_connections[room] = accept(venue_peers[room], room, venue_connections[room], bound=True)
                        recovered_room = 4
                        recovery_peer = venue_peers[recovered_room]
                        prior_connection = venue_connections[recovered_room]
                        first = send_venue_batch(recovered_room, 1)
                        wait(lambda:venue_ack_count(fault_directory, 4)==1,
                             'original room 4 acknowledgement before a temporary outage')
                        lost = send_venue_batch(recovered_room, 1, 'observe-close')
                        faults[recovered_room] = (503, b'')
                        outage_close = recovery_peer.read('closed')
                        assert outage_close['connectionId']==prior_connection
                        outage_statuses = []
                        for fault, reason in [((503, b''), 'management-service-unavailable'), ('delay', 'management-timeout'),
                                              ('disconnect', 'management-transport')]:
                            faults[recovered_room] = fault
                            def observed_fault():
                                row = venue_status(fault_directory)[recovered_room-1]
                                status = row['status']
                                return status if row['state']=='current' and status['progress']['phase']=='management-unavailable' \
                                    and status['fault']==reason else None

                            observed = wait(observed_fault, 'room 4 reports ' + reason)
                            assert observed['progress']['acknowledged']==1 and observed['progress']['attachments']==1
                            outage_statuses.append(observed)
                        check(all(later['sequence']>earlier['sequence'] and later['runId']==earlier['runId']
                                  for earlier,later in zip(outage_statuses,outage_statuses[1:])),
                              'A 503 response, read deadline and disconnected HTTP response publish distinct sanitized faults in the same run')
                        save('linked-fleet-management-statuses.json', outage_statuses)
                        del faults[recovered_room]
                        new_hello = recovery_peer.read('hello')
                        assert new_hello['connectionId']!=prior_connection and new_hello['roomId']==recovered_room
                        recovery_peer.reply()
                        wait(lambda:(status := venue_status(fault_directory)[3]['status']) and status['progress']['attachments']==2,
                             'room 4 attaches after management recovers')
                        venue_connections[recovered_room] = new_hello['connectionId']
                        fresh = send_venue_batch(recovered_room, 1)
                        recovered_status = wait(lambda:status if (status:=venue_status(fault_directory)[3]['status'])
                                                and status['progress']['acknowledged']==2 else None,
                                                'room 4 only acknowledges fresh feedback on the recovered connection')
                        assert recovered_status['fault'] is None and recovered_status['runId']==outage_statuses[0]['runId']

                        compatibility = runtime/'legacy-management-status'
                        compatibility.mkdir()
                        snapshot = compatibility/'room-04.status.json'
                        legacy = dict(outage_statuses[0], fault=None, observedAtUtc=datetime.now(timezone.utc).isoformat())
                        snapshot.write_text(json.dumps(legacy),encoding='utf-8')
                        legacy_row = venue_status(compatibility)[3]
                        snapshot.write_text(json.dumps(dict(legacy, fault='mock-timeout')),encoding='utf-8')
                        rejected_row = venue_status(compatibility)[3]
                        check(legacy_row['state']=='current' and legacy_row['status']['fault'] is None
                              and rejected_row['state']=='invalid' and rejected_row['status'] is None,
                              'Legacy management fault snapshots remain readable and mock fault codes in the management phase are refused')

                        cases = [(1, (403, b''), 'management-refused'),
                                 (2, (200, b'{'), 'management-invalid-response'),
                                 (3, (200, b'{}'), 'management-invalid-response'),
                                 (4, lambda page: dict(page, combatOrigin='GameServer'), 'management-invalid-response')]
                        acknowledged, cancelled = {}, {}
                        for room, fault, reason in cases:
                            acknowledged[room] = first | fresh if room == recovered_room else send_venue_batch(room, 1)
                            expected_count = len(acknowledged[room])
                            wait(lambda:venue_ack_count(fault_directory, room)==expected_count,
                                 'original acknowledgment before authority fault')
                            cancelled[room] = send_venue_batch(room, 1, 'observe-close')
                            faults[room] = fault
                            closed_batch = venue_peers[room].read('closed')
                            assert closed_batch['connectionId']==venue_connections[room]
                            terminal = wait(lambda:row if (row:=venue_status(fault_directory)[room-1])['state']=='stopped' else None,
                                            'authority fault publishes a stopped room')
                            assert terminal['status']['termination']==reason and terminal['status']['progress']['acknowledged']==expected_count
                        assert faulty.poll() is None and not (fault_directory/'venue-report.json').exists()
                        unaffected = send_venue_batch(5, 1)
                        wait(lambda:venue_ack_count(fault_directory, 5)==1,
                             'unaffected room acknowledges on its original connection')
                        fault_stop.touch()
                        stdout, _ = faulty.communicate(timeout=8)
                        aggregate = json.loads((fault_directory/'venue-report.json').read_bytes())
                        assert faulty.returncode==1 and json.loads(stdout)==aggregate and aggregate['complete'] is False
                        assert injected == {room for room, _, _ in cases}
                        for room, _, reason in cases:
                            row = aggregate['rooms'][room-1]
                            assert row['exitCode']==1 and row['error'] is None
                            result = json.loads((fault_directory/row['report']).read_bytes())
                            assert result['termination']==reason and result['complete'] is False
                            assert result['acknowledged']==len(acknowledged[room]) and result['physicalDeliveryConfirmed'] is False
                            delivered = {item['signal']['reportId'] for attempt in result['attempts']
                                         if attempt['status']=='simulated-acknowledged' for item in attempt['deliveries']}
                            assert delivered==acknowledged[room]
                            attempts = [attempt for attempt in result['attempts'] if attempt['status']=='cancelled']
                            if room==recovered_room:
                                assert result['managementFaults']>=2 and result['attachments']==2
                                outage_attempt, = [attempt for attempt in attempts if attempt['batchId']==outage_close['batchId']]
                                assert outage_attempt['connectionId']==prior_connection
                                assert {item['signal']['reportId'] for item in outage_attempt['deliveries']}==lost
                                save('linked-fleet-recover-close.json',outage_close)
                                attempts.remove(outage_attempt)
                            else:
                                assert result['managementFaults']==1
                            cancelled_attempt, = attempts
                            assert {item['signal']['reportId'] for item in cancelled_attempt['deliveries']}==cancelled[room]
                        room_five = json.loads((fault_directory/aggregate['rooms'][4]['report']).read_bytes())
                        assert room_five['acknowledged']==1 and room_five['termination']=='operator-stop'
                        assert {item['signal']['reportId'] for attempt in room_five['attempts']
                                for item in attempt['deliveries']}==unaffected
                        assert all(not any(secret in file.read_text(encoding='utf-8') for secret in private)
                                   for file in fault_directory.glob('*.json'))
                        check(True, 'Temporary authority loss cancels the original batch and recovers only fresh feedback on a new connection')
                        check(True, 'Authority refusal, malformed feedback and a changed origin cancel their batches and leave room five active')

                        faults.clear()
                        faults[4] = lambda page: dict(page, combatOrigin=None)
                        invalid_directory = out/'linked-fleet-missing-origin'
                        invalid = start_fleet(fault_bindings, invalid_directory, runtime/'linked-fleet-missing-origin.stop')
                        diagnostic, _ = invalid.communicate(timeout=8)
                        check(invalid.returncode==1 and 'InvalidDataException' in diagnostic and not invalid_directory.exists()
                              and all(peer.lines.empty() for peer in venue_peers.values())
                              and not any(secret in diagnostic for secret in private),
                              'A current stream without a combat origin is refused before any fleet handshake')
                if mode=='Independent':
                    check(True, 'The revoked room fails the fleet result while an unaffected room confirms fresh feedback on its original connection')
                    old_stream, _, position = venue_streams.pop(owners[3])
                    request(room_path+'/commands', {'commandId':str(uuid.uuid4()),'action':'End'})
                    request(room_path+'/combat-stream/seal', {'streamId':old_stream,'finalSequence':position}, 'GameServer')
                    restored = request('/api/sessions', {'missionId':mission['id'],'mode':'Independent','roomIds':[3]})
                    owners[3] = restored['id']
                    room_path = '/api/sessions/'+owners[3]
                    for occupant in rosters[3]:
                        restored = request(room_path+'/players', {'playerId':occupant['id'],'roomId':3,
                                           'name':occupant['name'],'headset':'Quest3'},'Room3')
                    rosters[3] = restored['players']
                    next(plan for plan in venue_map['rooms'] if plan['roomId']==3)['sessionId'] = owners[3]
                    folder = bind_venue(label+'-rebound', venue_map)
                    config_files = {room:folder/file.name for room,file in config_files.items()}
                    new_stream = str(uuid.uuid4())
                    request(room_path+'/combat-stream', {'streamId':new_stream,'origin':'Simulation'}, 'GameServer')
                    started = request(room_path+'/commands', {'commandId':str(uuid.uuid4()),'action':'Begin'})
                    venue_streams[owners[3]] = (new_stream, started['appliedAtSequence'], 0)

                continuity_bindings = runtime/f'{label}-continuity-bindings'
                shutil.copytree(folder, continuity_bindings)
                continuity_directory = out/f'{label}-continuity'
                continuity_stop = runtime/f'{label}-continuity.stop'
                with authority_gate(port, owners, ipc) as (origin, faults, _):
                    for file in continuity_bindings.glob('room-*.json'):
                        config = json.loads(file.read_bytes())
                        file.write_text(json.dumps(dict(config, managementUrl=origin)), encoding='utf-8')
                    continuous = start_fleet(continuity_bindings, continuity_directory, continuity_stop)
                    for room in rooms:
                        path = '/api/sessions/' + owners[room]
                        venue_connections[room] = accept(venue_peers[room], room, venue_connections[room], bound=True)
                    for room, kind, weather in ((1, 'cursor', 'Fog'), (2, 'clock', 'Rain')):
                        original_ids = send_venue_batch(room, 1)
                        wait(lambda:venue_ack_count(continuity_directory,room)==1,
                             'original acknowledgment before the continuity test')
                        pending_ids = send_venue_batch(room, 1, decision=None)
                        observed = request('/api/sessions/'+owners[room]+'/commands', {'commandId':str(uuid.uuid4()),
                            'action':'SetEnvironment','environment':{'mode':'VR','weather':weather,'timeOfDay':'Day','lightning':False}})
                        upper = observed['appliedAtSequence']
                        advanced, rewind = threading.Event(), threading.Event()
                        delivered_pages, stale_pages = [], []

                        def substitute(page):
                            signals = [row for row in page['signals'] if row['reportId'] in pending_ids]
                            if page['throughSequence'] != upper or len(signals) != 1:
                                return page
                            if not rewind.is_set():
                                delivered_pages.append(page)
                                advanced.set()
                                return page
                            assert signals[0]['eventSequence'] < upper
                            stale = (dict(page, throughSequence=upper-1) if kind=='cursor'
                                     else dict(page, checkedAtUtc=signals[0]['acceptedAtUtc']))
                            stale_pages.append(stale)
                            return stale

                        faults[room] = substitute
                        assert advanced.wait(.55), 'Gateway did not inspect the newer page while waiting for the mock ACK'
                        rewind.set()
                        venue_peers[room].reply('ack')

                        def observed_result():
                            row = venue_status(continuity_directory)[room-1]
                            if row['state']=='stopped' or (row['status'] and row['status']['progress']['acknowledged'] > 1):
                                return row

                        terminal = wait(observed_result, f'{mode} {kind} after a newer authority read')
                        assert delivered_pages and stale_pages
                        save(f'{label}-continuity-{kind}.json', {'advanced':delivered_pages[0], 'substituted':stale_pages[0],
                            'originalIds':sorted(original_ids),'pendingIds':sorted(pending_ids),'result':terminal})
                        check(terminal['state']=='stopped' and terminal['status']['termination']=='management-invalid-response'
                              and terminal['status']['progress']['acknowledged']==1,
                              f'{mode} rejects a regressed {kind} after observing a newer original pending batch')
                        result = json.loads((continuity_directory/f'room-{room:02}-report.json').read_bytes())
                        assert [attempt['status'] for attempt in result['attempts']]==['simulated-acknowledged','cancelled']
                        assert {item['signal']['reportId'] for item in result['attempts'][1]['deliveries']}==pending_ids
                        assert not result['complete'] and result['acknowledged']==1 and not result['physicalDeliveryConfirmed']
                        del faults[room]

                    for room, identity in ((3, 'eventId'), (4, 'reportId')):
                        same_page = mode == 'Linked' and room == 4
                        count = 2 if same_page else 1
                        seen, substituted = [], []

                        def duplicate_signal(page):
                            signals = page['signals']
                            if not signals:
                                return page
                            if not seen:
                                assert len(signals) == 1
                                seen.append(signals[0])
                            elif len(signals) == count and signals[0]['eventSequence'] > seen[0]['eventSequence']:
                                original = signals[0] if same_page else seen[0]
                                duplicate = dict(signals[-1], **{identity: original[identity]})
                                substituted.append(duplicate)
                                return dict(page, signals=[*signals[:-1], duplicate])
                            return page

                        faults[room] = duplicate_signal
                        original_ids = send_venue_batch(room, 1)
                        wait(lambda:venue_ack_count(continuity_directory,room)==1,
                             'original acknowledgment before a repeated signal identity')
                        fresh = publish_venue_batch(room, count)[-1]

                        def duplicate_outcome():
                            if not venue_peers[room].lines.empty():
                                return {'duplicateFeedback': venue_peers[room].read('feedback')}
                            row = venue_status(continuity_directory)[room-1]
                            return row if row['state']=='stopped' else None

                        terminal = wait(duplicate_outcome, f'{mode} repeated {identity}')
                        assert seen[0]['reportId'] in original_ids and substituted
                        assert substituted[0]['eventSequence'] > seen[0]['eventSequence']
                        assert substituted[0]['streamSequence'] == fresh['streamSequence']
                        save(f'{label}-continuity-duplicate-{identity}.json',
                             {'original':seen[0], 'substituted':substituted[0], 'samePage':same_page, 'result':terminal})
                        assert 'duplicateFeedback' not in terminal, f'{mode} repeated {identity} reached the mock device'
                        result = json.loads((continuity_directory/f'room-{room:02}-report.json').read_bytes())
                        check(terminal['status']['termination']=='management-invalid-response'
                              and terminal['status']['progress']['acknowledged']==1
                              and terminal['status']['progress']['batches']==1
                              and [attempt['status'] for attempt in result['attempts']]==['simulated-acknowledged']
                              and result['acknowledged']==1 and not result['physicalDeliveryConfirmed'],
                              f'{mode} stops a repeated {identity} before another mock batch and retains the original acknowledgment')
                        del faults[room]

                    unaffected = send_venue_batch(5, 1)
                    wait(lambda:venue_ack_count(continuity_directory,5)==1,
                         'room five remains active after other rooms reject authority regressions')
                    assert continuous.poll() is None
                    continuity_stop.touch()
                    stdout, _ = continuous.communicate(timeout=8)
                    aggregate = json.loads((continuity_directory/'venue-report.json').read_bytes())
                    assert continuous.returncode==1 and json.loads(stdout)==aggregate
                    assert [row['exitCode'] for row in aggregate['rooms']]==[1,1,1,1,0]
                    room_five = json.loads((continuity_directory/'room-05-report.json').read_bytes())
                    assert {item['signal']['reportId'] for attempt in room_five['attempts']
                            for item in attempt['deliveries']}==unaffected
                    check(room_five['attempts'][0]['status']=='simulated-acknowledged' and room_five['termination']=='operator-stop',
                          f'{mode} unaffected room confirms fresh feedback on its original connection')

                    order_directory = out/f'{label}-stream-order'
                    order_directory.mkdir()
                    order_report = order_directory/'room-05-report.json'
                    ordered = invoke(5,'Room5',order_report,config=continuity_bindings/config_files[5].name,
                                     status_directory=order_directory)
                    room = 5
                    venue_connections[room] = accept(venue_peers[room],room,venue_connections[room],bound=True)
                    first = publish_venue_batch(room,1)[0]
                    received = venue_peers[room].read('feedback')
                    assert received['signals'][0]['signal']['reportId']==first['report']['reportId']
                    venue_peers[room].reply('ack')
                    wait(lambda:venue_ack_count(order_directory,room)==1,
                         'original acknowledgement before stream order fault')
                    same_page = mode=='Linked'
                    substitutions = []

                    def regress_stream(page):
                        signals = page['signals']
                        if len(signals)==(2 if same_page else 1) and signals[0]['streamSequence']>first['streamSequence']:
                            replacement = signals[0]['streamSequence'] if same_page else first['streamSequence']-1
                            assert 0 < replacement < signals[-1]['streamSequence']
                            changed = dict(signals[-1],streamSequence=replacement)
                            substitutions.append({'original':signals[-1],'substituted':changed})
                            return dict(page,signals=[*signals[:-1],changed])
                        return page

                    faults[room] = regress_stream
                    publish_venue_batch(room,2 if same_page else 1)

                    def stream_order_outcome():
                        if not venue_peers[room].lines.empty():
                            return {'outbound':venue_peers[room].read('feedback')}
                        exit_code = ordered.poll()
                        return {'exitCode':exit_code} if exit_code is not None else None

                    terminal = wait(stream_order_outcome,f'{mode} verifies the original combat stream order')
                    assert substitutions
                    order_proof = {'samePage':same_page,'confirmedStreamSequence':first['streamSequence'],
                                   **substitutions[0],'result':terminal}
                    if 'outbound' in terminal:
                        save(f'{label}-stream-order.json',order_proof)
                        raise AssertionError(f'{mode} sent a regressed combat stream sequence to the mock device')
                    output, _ = ordered.communicate(timeout=8)
                    result = json.loads(order_report.read_bytes())
                    status = venue_status(order_directory)[room-1]
                    save(f'{label}-stream-order.json',{**order_proof,'status':status,'report':result,'summary':output.strip()})
                    check(venue_peers[room].lines.empty() and ordered.returncode==1
                          and json.loads(output)=={'complete':False,'simulatedHardwareOnly':True,
                          'physicalDeliveryConfirmed':False,'acknowledged':1}
                          and status['state']=='stopped' and status['status']['termination']=='management-invalid-response'
                          and result['acknowledged']==1 and len(result['attempts'])==1
                          and result['attempts'][0]['status']=='simulated-acknowledged',
                          f'{mode} keeps only the original ACK and rejects a repeated or regressed combat sequence before delivery')
                    del faults[room]

                stop_venue_room = runtime/f'{label}-stop-room-1'
                room1_options = {'config':config_files[1],'status_directory':status_directory}
                alias_path = status_directory/'room-01.status.json'
                alias = invoke(1, 'Room1', alias_path, **room1_options)
                alias_log, _ = alias.communicate(timeout=8)
                assert alias.returncode==1 and 'ArgumentException' in alias_log and not alias_path.exists()
                venue_reports = {room:out/f'{label}-venue-room-{room}-report.json' for room in rooms}
                gateways = {room:invoke(room, f'Room{room}', venue_reports[room], config=config_files[room],
                                        stop=stop_venue_room if room==1 and mode=='Linked' else None,
                                        status_directory=status_directory) for room in rooms}
                for room in rooms:
                    path = '/api/sessions/' + owners[room]
                    venue_connections[room] = accept(venue_peers[room], room, venue_connections[room], bound=True)
                assert len(set(venue_connections.values())) == 5

                def all_at_count(count):
                    rows = venue_status()
                    return rows if all(row['state']=='current' and row['status']['progress']['phase']=='active'
                                       and row['status']['progress']['acknowledged']==count for row in rows) else None

                confirmed = {room:send_venue_batch(room, 5) for room in rooms}
                for room in rooms:
                    send_venue_batch(room, 1)
                original_status = wait(lambda:all_at_count(6), 'five active room snapshots with six ACKs each')
                def refreshed():
                    rows = all_at_count(6)
                    return rows if rows and all(new['status']['sequence']>old['status']['sequence']
                                                and new['status']['runId']==old['status']['runId']
                                                for new,old in zip(rows,original_status,strict=True)) else None
                snapshot_path = status_directory/'room-01.status.json'
                if os.name == 'nt':
                    def open_windows_status(*, share_delete):
                        share = '[IO.FileShare]::ReadWrite' + (' -bor [IO.FileShare]::Delete' if share_delete else '')
                        return start(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                            "$file=[IO.FileStream]::new($env:VR_TEST_STATUS_PATH,[IO.FileMode]::Open,[IO.FileAccess]::Read,"
                            f"({share})); try {{ "
                            "[Console]::WriteLine('open'); $null=[Console]::ReadLine(); "
                            "$text=[IO.StreamReader]::new($file); [Console]::WriteLine($text.ReadToEnd()) } finally { $file.Dispose() }"],
                            {**env,'VR_TEST_STATUS_PATH':str(snapshot_path)})

                    reader = open_windows_status(share_delete=True)
                    assert reader.stdout.readline().strip()=='open'
                    held_status = venue_status()[0]['status']
                    fresh = wait(lambda:rows if (rows:=refreshed()) and rows[0]['status']['sequence']>held_status['sequence'] else None,
                                 'all five idle snapshots advance while Windows reader holds room 1 open')
                    old_snapshot, _ = reader.communicate(input='close\n',timeout=5)
                    assert reader.returncode==0 and json.loads(old_snapshot)['sequence']<=held_status['sequence']
                else:
                    with snapshot_path.open('rb') as reader:
                        held_status = json.load(reader)
                        fresh = wait(lambda:rows if (rows:=refreshed()) and rows[0]['status']['sequence']>held_status['sequence'] else None,
                                     'all five idle snapshots advance while a reader holds room 1 open')
                save(f'{label}-venue-status-active.json', fresh)
                check(all(sha(file)==digest for file,digest in hashes.items()),
                      f'{mode} five statuses preserve bindings and advance while room 1 is open in another reader')

                if mode=='Linked':
                    bad = runtime/'invalid-venue-status'
                    bad.mkdir()
                    (bad/'room-01.status.json').write_text('{',encoding='utf-8')
                    sample = fresh[1]['status']
                    (bad/'room-02.status.json').write_text(json.dumps({**sample,'sessionId':str(uuid.uuid4())}),encoding='utf-8')
                    (bad/'room-03.status.json').write_text(json.dumps({**fresh[2]['status'],'observedAtUtc':'2099-01-01T00:00:00Z'}),encoding='utf-8')
                    (bad/'room-04.status.json').write_text(json.dumps({**fresh[3]['status'],'physicalDeliveryConfirmed':True}),encoding='utf-8')
                    rejected = venue_status(bad)
                    check([row['state'] for row in rejected]==['invalid','mismatch','invalid','invalid','waiting']
                          and all(row['status'] is None for row in rejected), 'Invalid, future-dated and wrong-session files expose no old ACK counters')

                    first_room = gateways[1]
                    final_ack_count = 6
                    if os.name=='nt':
                        reader = open_windows_status(share_delete=False)
                        assert reader.stdout.readline().strip()=='open'
                        held = json.loads(snapshot_path.read_bytes())
                        try:
                            published = publish_venue_batch(1,1)[0]['report']['reportId']

                            def feedback_or_exit():
                                if not venue_peers[1].lines.empty():
                                    return {'frame':venue_peers[1].read('feedback')}
                                code = first_room.poll()
                                return {'exitCode':code} if code is not None else None

                            observed = wait(feedback_or_exit,'mock feedback while a reader prevents room status replacement')
                            save('linked-locked-status-feedback.json',{'statusPath':str(snapshot_path),'held':held,
                                 'originalReportId':published,'observed':observed})
                            assert 'frame' in observed, 'The status reader stopped the feedback gateway'
                            signal, = observed['frame']['signals']
                            assert observed['frame']['connectionId']==venue_connections[1] and signal['signal']['reportId']==published
                            venue_peers[1].reply('ack')
                            final_ack_count += 1
                            # A status reader keeps the last complete heartbeat while the mock receives its batch.
                            assert json.loads(snapshot_path.read_bytes())==held
                            check(True,'A reader blocking replacement leaves the mock connection and its feedback active')
                        finally:
                            taken, _ = reader.communicate(input='close\n',timeout=5)
                            assert reader.returncode==0 and json.loads(taken)==held

                        wait(lambda:venue_ack_count(status_directory,1)==final_ack_count,'confirmed feedback after releasing the reader')
                        reader = open_windows_status(share_delete=False)
                        assert reader.stdout.readline().strip()=='open'
                        held = json.loads(snapshot_path.read_bytes())
                        try:
                            stop_venue_room.touch()

                            def durable_room_result():
                                try:
                                    return json.loads(venue_reports[1].read_bytes())
                                except (FileNotFoundError, PermissionError, json.JSONDecodeError):
                                    return None

                            result = wait(durable_room_result,'original room report while terminal status replacement is locked')
                            time.sleep(.10)
                            assert result['termination']=='operator-stop' and first_room.poll() is None
                        finally:
                            taken, _ = reader.communicate(input='close\n',timeout=5)
                            assert reader.returncode==0 and json.loads(taken)==held
                    else:
                        stop_venue_room.touch()
                    stdout, _ = first_room.communicate(timeout=8)
                    assert first_room.returncode==0 and not any(secret in stdout for secret in private)
                    stopped_room = venue_status()[0]
                    check(stopped_room['state']=='stopped' and stopped_room['status']['termination']=='operator-stop'
                          and stopped_room['status']['progress']['acknowledged']==final_ack_count and venue_reports[1].is_file(),
                          'Graceful room stop publishes the terminal heartbeat after the original report')
                    if os.name=='nt':
                        final_signal, = result['attempts'][-1]['deliveries']
                        assert result['acknowledged']==final_ack_count and final_signal['signal']['reportId']==published
                        assert stopped_room['status']['runId']==held['runId'] and stopped_room['status']['sequence']>held['sequence']
                        save('linked-locked-status-stop.json',{'statusPath':str(snapshot_path),'held':held,
                             'terminal':stopped_room,'reportAckCount':result['acknowledged'],'originalReportId':published})

                    crash_report = out/'linked-venue-crash-report.json'
                    crashed = invoke(1, 'Room1', crash_report, **room1_options)
                    venue_connections[1] = accept(venue_peers[1], 1, venue_connections[1], bound=True)
                    send_venue_batch(1, 1)
                    def room_one_at_count(count):
                        row = venue_status()[0]
                        return row if row['state']=='current' and row['status']['progress']['phase']=='active' and row['status']['progress']['acknowledged']==count else None
                    before_crash = wait(lambda:room_one_at_count(1), 'original ACK before forced room exit')
                    crashed.kill()
                    crashed.communicate(timeout=8)
                    assert crashed.returncode!=0 and not crash_report.exists()
                    def stale_room():
                        rows = venue_status()
                        return rows if rows[0]['state']=='stale' else None
                    stale = wait(stale_room, 'killed gateway becomes stale')
                    assert stale[0]['status'] is None and all(row['state']=='current' and row['status']['runId']==old['status']['runId']
                                                            for row,old in zip(stale[1:],fresh[1:],strict=True))
                    for room in rooms[1:]:
                        send_venue_batch(room, 1)
                    during = wait(lambda:rows if (rows:=stale_room()) and all(row['status'] and row['status']['progress']['acknowledged']==7 for row in rows[1:])
                                  else None, 'four original connections ACK while room 1 stays stale')
                    save('linked-venue-status-stale.json', during)
                    check(during[0]['status'] is None, 'Killed room becomes stale while the other four original connections acknowledge fresh feedback')

                    restart_report = out/'linked-venue-restart-report.json'
                    restarted = invoke(1, 'Room1', restart_report, **room1_options)
                    venue_connections[1] = accept(venue_peers[1], 1, venue_connections[1], bound=True)
                    recovered = wait(lambda:room_one_at_count(0), 'restarted room initially has no acknowledgements')
                    assert recovered['status']['runId'] not in (before_crash['status']['runId'],stopped_room['status']['runId'])
                    assert venue_peers[1].lines.empty()
                    restarted_ids = send_venue_batch(1, 1)
                    final_recovered = wait(lambda:room_one_at_count(1), 'restarted room acknowledges exactly one new batch')
                    save('linked-venue-status-restarted.json', final_recovered)
                    check(final_recovered['status']['runId']==recovered['status']['runId'],
                          'Restart uses a new run ID, clears ACK counts and delivers only fresh feedback')
                for owner, (stream_id, _, position) in venue_streams.items():
                    venue_path = '/api/sessions/'+owner
                    request(venue_path+'/commands', {'commandId':str(uuid.uuid4()),'action':'End'})
                    request(venue_path+'/combat-stream/seal', {'streamId':stream_id,'finalSequence':position}, 'GameServer')
                for room, gateway in gateways.items():
                    stdout, _ = gateway.communicate(timeout=8)
                    assert gateway.returncode == 0 and not any(secret in stdout for secret in private), stdout
                    result = json.loads(venue_reports[room].read_bytes())
                    ids = {delivery['signal']['reportId'] for attempt in result['attempts'] if attempt['status']=='simulated-acknowledged'
                           for delivery in attempt['deliveries']}
                    termination = 'operator-stop' if mode=='Linked' and room==1 else 'ended'
                    assert confirmed[room] <= ids and result['physicalDeliveryConfirmed'] is False and result['termination']==termination
                if mode=='Linked':
                    stdout, _ = restarted.communicate(timeout=8)
                    report = json.loads(restart_report.read_bytes())
                    assert restarted.returncode==0 and not any(secret in stdout for secret in private)
                    assert report['termination']=='ended' and report['acknowledged']==1 and {
                        delivery['signal']['reportId'] for attempt in report['attempts'] for delivery in attempt['deliveries']}==restarted_ids
                terminal = venue_status()
                check(all(row['state']=='stopped' and row['status']['termination']=='ended' for row in terminal),
                      f'{mode} all five terminal snapshots identify the mock run that ended')
                save(f'{label}-venue-status-terminal.json', terminal)
                check(request('/api/sessions')==[], f'{mode} launches all five generated settings and confirms 25 exact mock deliveries before ending')
                if args.verify_event_export:
                    with opener.open(event_request, timeout=8) as response:
                        assert response.headers['Content-Type'] == 'application/zip' and response.headers['Cache-Control'] == 'no-store'
                        exported = response.read(4 * 1024 * 1024 + 1)
                    assert len(exported) <= 4 * 1024 * 1024
                    events_path = out / f'{label}-original-events'
                    events_path.mkdir()
                    with zipfile.ZipFile(BytesIO(exported)) as archive:
                        assert sorted(archive.namelist()) == sorted(session_id + '.json' for session_id in handoff_session_ids)
                        for session_id in handoff_session_ids:
                            data = archive.read(session_id + '.json')
                            events = json.loads(data)
                            assert events[-1]['kind'] == 'CombatStreamSealed'
                            assert events == request('/api/sessions/' + session_id + '/events?limit=500')
                            assert not any(secret in data.decode('utf-8') for secret in private)
                            (events_path / (session_id + '.json')).write_bytes(data)
                    verified = handoff('--verify-venue-zip', package, '--events-directory', events_path)
                    assert verified.returncode == 0 and not verified.stderr, verified.stderr.decode('utf-8', errors='replace')
                    agree = json.loads(verified.stdout)
                    signals = sum(row['acknowledged'] + row['cancelled'] + row['mockFailed'] for row in summary['rooms'])
                    assert agree == {**summary, 'sourceEventsVerified': True, 'sourceSignalsVerified': signals}
                    check(True, f'{mode} live handoff verifies all {signals} attempts against the exported sealed original events')
                    save(f'{label}-source-verified.json', agree)
                    alternate = runtime / f'{label}-altered-events'
                    shutil.copytree(events_path, alternate)
                    altered_history = alternate / (handoff_session_ids[0] + '.json')
                    altered = json.loads(altered_history.read_bytes())
                    first_signal = json.loads(expected['reports/room-01-report.json'])['attempts'][0]['deliveries'][0]['signal']
                    row = altered[first_signal['eventSequence'] - 1]
                    assert row['eventId'] == first_signal['eventId']
                    row['eventId'] = str(uuid.uuid4())
                    altered_history.write_text(json.dumps(altered), encoding='utf-8')
                    refused = handoff('--verify-venue-zip', package, '--events-directory', alternate)
                    assert refused.returncode == 1 and not refused.stdout and b'InvalidDataException' in refused.stderr
                    assert handoff('--verify-venue-zip', package, '--events-directory', events_path).stdout == verified.stdout
                    check(True, f'{mode} rejects an altered event ID while the original handoff and export still verify')
                    (out / f'{label}-original-events.zip').write_bytes(exported)
            if ipc:
                check(has_no_ip_endpoints([os.getpid(), *(process.pid for process in processes if process.poll() is None)]),
                      'Owned IPC fixtures and mock processes have zero TCP listeners and UDP endpoints')
        finally:
            for process in reversed(processes):
                if process is api:
                    if process.poll() is None:
                        process.stdin.write('STOP '+token+'\n')
                        process.stdin.flush()
                elif process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                closed.append(process.poll() is not None)
            api_reader.join(timeout=5)
            save('cleanup.json', {'allStopped':all(closed),'apiExitCode':api.returncode})
    check(all(closed) and api.returncode==0, 'All owned processes stop and the management API exits normally')
    check(all(sha(binary.parent/name)==digest for name,digest in files.items()), 'Compiled simulator graph remains byte-identical')
    check(sha(peer_script)==peer_hash, 'The exact mock peer remains byte-identical')
    save('checks.json', {'complete':True,'checks':len(findings),'findings':findings,'simulatorDll':str(binary),
                         'binaryFiles':files,'helperSha256':sha(Path(__file__)),'peerSha256':peer_hash,
                         'transport':'Windows AF_UNIX' if args.ipc_work_root else 'Loopback TCP',
                         'ipcSupportSha256':sha(Path(__file__).with_name('windows_ipc_api.py')) if args.ipc_work_root else None,
                         'scope':'Actual API and mock devices, no physical device I/O'})
    print(json.dumps({'complete':True,'checks':len(findings),'directory':str(out)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    add_api_arguments(parser)
    parser.add_argument('--simulator-dll',type=Path,default=ROOT/'tools/VrCommand.HardwareSimulator/bin/Release/net10.0/VrCommand.HardwareSimulator.dll')
    parser.add_argument('--mock-peer-script',type=Path,default=ROOT/'scripts/hardware-mock-peer.py')
    parser.add_argument('--evidence-root',type=Path,default=ROOT/'artifacts/live-hardware-gateway')
    parser.add_argument('--ipc-work-root', type=Path, help='Short existing Windows folder for the AF_UNIX rehearsal')
    parser.add_argument('--verify-event-export', action='store_true', help='Compare live handoffs with sealed events from management console 0.31.265 or later')
    args = parser.parse_args()
    try:
        if args.ipc_work_root:
            if os.name != 'nt' or not args.ipc_work_root.is_dir():
                raise ValueError('Use a short existing Windows IPC work root.')
            args.ipc_work_root = args.ipc_work_root.resolve(strict=True)
            api_command, api_cwd, _ = resolve_api_command(args)
        else:
            api_command, api_cwd, _ = checked_api_command(args)
            require_silent_windows_launch(sys.executable)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    run(args, api_command, api_cwd)
