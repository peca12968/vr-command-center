"""Run the compiled gateway, real isolated management API and separate loopback mock processes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(args):
    out = ROOT/'artifacts/live-hardware-gateway'/('run-'+uuid.uuid4().hex)
    out.mkdir(parents=True)
    print(json.dumps({'stage':'starting','directory':str(out)}), flush=True)
    keys = {role:secrets.token_hex(32) for role in ('Master','GameServer','Room1','Room2')}
    token = secrets.token_hex(32)
    private = [*keys.values(), token]
    env = {k:v for k,v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in
           ('operatorkeyfile','playerticketsigningkey','controlpipetoken','datadirectory','sessiondatadirectory','vr_command_room_key')}
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

    def start(command, environment):
        process = subprocess.Popen(command, cwd=ROOT, env=environment, text=True, encoding='utf-8', stdin=subprocess.PIPE,
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
        def __init__(self):
            self.lines = queue.Queue()
            self.process = start([sys.executable, str(peer_script), '--manual'], env)
            self.reader = threading.Thread(target=self.collect, daemon=True)
            self.reader.start()
            self.port = self.read('listening')['port']

        def collect(self):
            for line in self.process.stdout:
                self.lines.put(line)

        def read(self, kind):
            frame = json.loads(self.lines.get(timeout=8))
            assert frame['kind'] == kind
            return frame

        def reply(self, command='ack'):
            self.process.stdin.write(command+'\n')
            self.process.stdin.flush()

    with tempfile.TemporaryDirectory(prefix='vr-live-hardware-') as temporary:
        runtime = Path(temporary)
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1',0))
            port = reserve.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        keyfile = runtime/'keys.json'
        keyfile.write_text(json.dumps({'OperatorKeys':keys}), encoding='utf-8')
        options = {**env, 'OperatorKeyFile':str(keyfile), 'DataDirectory':str(runtime/'missions'),
            'SessionDataDirectory':str(runtime/'sessions'), 'ControlPipeToken':token,
            'Logging__LogLevel__Default':'Warning', 'Logging__LogLevel__Microsoft.AspNetCore.Hosting.Diagnostics':'Information'}
        api = start(['dotnet', str(args.api_dll.resolve()), '--urls', base], options)

        def collect():
            for line in api.stdout:
                api_log.append(line)

        api_reader = threading.Thread(target=collect, daemon=True)
        api_reader.start()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def request(path, body=None, role='Master'):
            headers = {'Authorization':'Bearer '+keys[role], 'Content-Type':'application/json'}
            req = urllib.request.Request(base+path, headers=headers, data=json.dumps(body).encode() if body is not None else None)
            with opener.open(req, timeout=4) as reply:
                return json.load(reply)

        def health():
            try:
                return request('/health')['status']=='ok'
            except OSError:
                assert api.poll() is None
                return False

        try:
            wait(health,'management ready')
            mission = request('/api/missions', {'name':'Live mock feedback', 'briefing':'Isolated test session', 'durationSeconds':600,
                'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
                'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]})
            session = request('/api/sessions',{'missionId':mission['id'],'mode':'Linked','roomIds':[1,2,3,4,5]})
            sid = session['id']; path = '/api/sessions/'+sid
            for i, room in enumerate([1,1,1,2], 1):
                session = request(path+'/players', {'playerId':str(uuid.uuid4()),'roomId':room,'name':f'Fixture {i}','headset':'Quest3'}, f'Room{room}')
            alpha, bravo, unbound, charlie = session['players']
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

            def attached(room):
                target = f'{base}{path}/rooms/{room}/hardware-feedback - 200'
                return sum('Request finished' in line and target in line for line in api_log)

            def accept(peer, room, previous=None):
                previous_count = attached(room)
                hello = peer.read('hello')
                assert hello['roomId']==room and (not previous or hello['connectionId']!=previous)
                peer.reply()
                wait(lambda:attached(room)>previous_count,f'room {room} fresh cursor attachment')
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

            def invoke(room, key_role, report, *, config=None, stop=None):
                command = ['dotnet',str(binary),'--live',str(config or configs[room]),'--output',str(report)]
                if stop is not None:
                    command += ['--stop-file',str(stop)]
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

            ids = publish([(alpha,'ShotFired'),(bravo,'PlayerDamaged'),(unbound,'ShotFired'),(charlie,'PlayerDamaged')])
            feedback(1,ids[:2]); feedback(2,ids[3:]); peers[1].reply(); peers[2].reply()
            check(True, 'Two mock processes receive only their room and exact admission; a stale admission binding is excluded')

            for fault in ('wrong','timeout','drop'):
                ids = publish([(alpha,'ShotFired')])
                feedback(1,ids)
                peers[1].reply(fault)
                count = attached(1)
                hello = peers[1].read('hello')
                assert hello['connectionId']!=connections[1]
                publish([(alpha,'ShotFired')])
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
            connections[1] = accept(peers[1],1,connections[1])
            old_epoch = epoch; epoch = action('Resume')
            publish([(alpha,'ShotFired')], observed=old_epoch)
            ids = publish([(alpha,'ShotFired')]); feedback(1,ids); peers[1].reply()
            check(True, 'Resume emits only the new Running epoch after a paused in-flight batch')

            inflight_stop = runtime/'inflight.stop'
            inflight_report = out/'inflight-stop-report.json'
            inflight = invoke(1,'Room1',inflight_report,config=stop_config,stop=inflight_stop)
            stop_connection = accept(stop_peer,1,idle_connection)
            ids = publish([(alpha,'ShotFired')]); feedback(1,ids); peers[1].reply()
            stopped_batch = stop_peer.read('feedback')
            stop_peer.reply('observe-close')
            inflight_stop.touch()
            stop_close = stop_peer.read('closed')
            save('inflight-stop-close.json',stop_close)
            stop_result = stopped(inflight,inflight_report,attached_once=True)
            attempt, = stop_result['attempts']
            check(stop_close['connectionId']==stopped_batch['connectionId']==attempt['connectionId']==stop_connection
                  and stop_close['batchId']==stopped_batch['batchId']==attempt['batchId']
                  and attempt['status']=='cancelled' and [d['signal']['reportId'] for d in attempt['deliveries']]==ids,
                  'Operator stop closes the exact pending batch with no simulated acknowledgement')

            ids = publish([(charlie,'PlayerDamaged')]); feedback(2,ids); peers[2].reply()
            ids = publish([(charlie,'ShotFired')]); ended_batch = feedback(2,ids)
            action('End'); peers[2].reply('observe-close')
            closed_batch = peers[2].read('closed')
            save('end-close.json',closed_batch)
            check(closed_batch['connectionId']==ended_batch['connectionId'] and closed_batch['batchId']==ended_batch['batchId'],
                  'End closes the exact pending connection without an ACK')
            request(path+'/combat-stream/seal',{'streamId':stream,'finalSequence':sequence},'GameServer')
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
                  and reports[2]['acknowledged']==2 and reports[2]['connections']==1,
                  'The other room acknowledges on its original connection after the operator stop and still cancels at End')
            history = {e['eventId']:e for e in request(path+'/events')}
            for report in [*reports.values(),stop_result]:
                for attempt in report['attempts']:
                    for delivery in attempt['deliveries']:
                        signal = delivery['signal']; original = history[signal['eventId']]
                        assert original['sequence']==signal['eventSequence'] and original['payload']['report']['reportId']==signal['reportId']
            check(request('/api/sessions')==[] and request(path)['combatStream']['acceptedSequence']==sequence,
                  'Every attempted event preserves the accepted witness and the gateway never writes session events')
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
                         'scope':'Actual API and loopback mock devices, no physical device I/O'})
    print(json.dumps({'complete':True,'checks':len(findings),'directory':str(out)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-dll',type=Path,default=ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')
    parser.add_argument('--simulator-dll',type=Path,default=ROOT/'tools/VrCommand.HardwareSimulator/bin/Release/net10.0/VrCommand.HardwareSimulator.dll')
    parser.add_argument('--mock-peer-script',type=Path,default=ROOT/'scripts/hardware-mock-peer.py')
    run(parser.parse_args())
