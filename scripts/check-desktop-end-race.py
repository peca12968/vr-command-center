"""Bounded real UDP delay / result loss across End, using owned Simulation clients."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid
from udp_gate import LoopbackGate
from windows_firewall import require_silent_windows_launch, start_checked_windows_process

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('race_debrief', ROOT/'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)
vm = debrief.venue_module


class PackagedRaceVenue(vm.Venue):
    def __init__(self, args, witness):
        super().__init__(args, artifact_family='desktop-end-race')
        self.witness = witness
        self.packaged = {}

    def launch(self, name, config, visible=False, *, extra_args=()):
        if name not in ('end-race-first', 'end-race-late'):
            return super().launch(name, config, visible, extra_args=extra_args)
        self.save(name + '.json', config)
        path = self.directory / name
        report = path.with_suffix('.launch.json')
        status = path.with_suffix('.status.json')
        require_silent_windows_launch(self.args.player_package / 'VrCommand.exe')
        process = start_checked_windows_process([self.args.player_package / 'Launch-Player.exe', '--launch', '--headless', '--wait',
            '--config', str(path.with_suffix('.json')), '--log', str(path.with_suffix('.log')),
            '--report', str(report), '--status-report', str(status)], cwd=self.directory, creationflags=subprocess.CREATE_NO_WINDOW)
        self.processes[name] = process
        self.packaged[name] = {'status': status, 'handle': None, 'pid': None}

        def started():
            if not report.is_file(): return None
            result = vm.read_json(report)
            return result if result['status'] == 'started' else None

        result = self.wait(started, 20, name + ' packaged native start')
        pid = result['processId']
        if type(pid) is not int or pid <= 0 or pid in (process.pid, os.getpid()):
            raise ValueError('Unexpected original packaged player process')
        self.packaged[name].update(pid=pid, handle=self.witness(pid, allow_terminate=True))

    def status(self, name, state):
        record = self.packaged[name]
        if not record['status'].is_file(): return None
        result = vm.read_json(record['status'])
        if result['processId'] != record['pid'] or result['complete'] is not True or result['logAvailable'] is not True:
            raise ValueError('Packaged status does not match the original native player log')
        return result if result['state'] == state else None

    def stop(self, name):
        if name not in self.packaged:
            return super().stop(name)
        process = self.processes[name]
        handle = self.packaged[name]['handle']
        if handle is not None:
            handle.terminate()
            handle.wait()
            if process.wait(timeout=15) != 0:
                raise RuntimeError('Packaged launcher did not publish its terminal status')
            handle.close()
            self.packaged[name]['handle'] = None
        elif process.poll() is None:
            subprocess.run([str(Path(os.environ['WINDIR']) / 'System32/taskkill.exe'), '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=10, check=True)
            process.wait(timeout=10)
        del self.processes[name]


def tool_fingerprint():
    digest=hashlib.sha256()
    for name in ['check-desktop-end-race.py','udp_gate.py','check-desktop-debrief.py','start-desktop-venue.py']:
        digest.update(name.encode());digest.update((ROOT/'scripts'/name).read_bytes())
    return digest.hexdigest()


def replay(v,entry,sealed):
    expected=v.frame(entry);last=None;previous=0
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',
        headers={'Authorization':'Bearer '+v.tokens['Master']})
    deadline=time.monotonic()+sealed['world']['durationMilliseconds']/4000+15
    with urllib.request.urlopen(request,timeout=5) as response:
        kind=''
        for raw in response:
            if time.monotonic()>deadline:raise RuntimeError('Replay observation deadline exceeded')
            line=raw.decode().strip()
            if line.startswith('event: '):kind=line[7:]
            if kind=='frame' and line.startswith('data: '):
                row=json.loads(line[6:]);number=row['packet']['sequence']
                if number!=previous+1:raise RuntimeError('Sealed replay is not contiguous')
                previous=number;last=row
    if previous!=sealed['world']['acceptedSequence'] or last!=expected or last['packet']['frame']['phase']!='Ended':
        raise RuntimeError('Final replay differs from exact sealed world / statistics')
    return {'complete':True,'frames':previous,'finalPacketAndStatisticsMatch':True}


def verify_personal_report(v, entry, player):
    route = f'/api/sessions/{entry["id"]}'
    filename = f'vr-command-report-v1-{entry["id"]}-player-{player["id"]}.csv'

    def download(suffix, role):
        request = urllib.request.Request(v.base + route + suffix, headers={'Authorization': 'Bearer ' + v.tokens[role]})
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.headers.get_content_type() != 'text/csv' or response.headers['Cache-Control'] != 'no-store':
                raise ValueError('Invalid final CSV response')
            return response.read(), response.headers['Content-Disposition']

    data, disposition = download(f'/players/{player["id"]}/report.csv', f'Room{player["roomId"]}')
    original, _ = download('/report.csv', 'Master')
    def rows(content):
        return list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
    selected = [row for row in rows(original) if row['playerId'] == player['id']]
    if len(selected) != 1 or rows(data) != selected or filename not in disposition:
        raise ValueError('The personal file did not preserve exactly the original sealed player row')
    with (v.directory / 'interrupted-player-report.csv').open('xb') as output:
        output.write(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--player-exe', type=Path, default=ROOT/'artifacts/desktop/VrCommand.exe')
    p.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    p.add_argument('--mode', choices=['join-delay','result-drop','result-large-drop'], default='join-delay')
    p.add_argument('--player-package', type=Path, help='For result-drop, verify waiting and interrupted status using the current extracted Windows player launcher')
    p.add_argument('--verify-personal-report', action='store_true', help='Verify the interrupted player can obtain its sealed row from the current management API')
    p.add_argument('--post-seal-delay', type=float, default=1, help='Additional join-delay seconds after exact seal, 0..3')
    args = p.parse_args(); args.duration=300; args.job_workers=2; args.visible_room=0; args.check=False
    if not 0 <= args.post_seal_delay <= 3: p.error('post-seal-delay must be 0..3 seconds')
    if args.verify_personal_report and not args.player_package: p.error('Personal report verification requires --player-package')
    if args.player_package:
        if args.mode != 'result-drop': p.error('Packaged status verification requires --mode result-drop')
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('race_package_check', ROOT/'scripts/check-player-package.py')
        check_package = module_from_spec(spec); spec.loader.exec_module(check_package)
        args.player_package = check_package.package.plain(args.player_package)
        manifest = check_package.package.verify(args.player_package)
        if manifest['launcherSourceSha256'] != check_package.package.digest(ROOT/'tools/WindowsPlayerLauncher/PlayerLauncher.cs'):
            p.error('Use the package from the current launcher source')
        args.player_exe = args.player_package / 'VrCommand.exe'
        spec = spec_from_file_location('race_control_check', ROOT/'scripts/check-control-package.py')
        control = module_from_spec(spec); spec.loader.exec_module(control)
    vm.verify_player(args, python_listener=True); fingerprint=tool_fingerprint(); gate = None; report = None
    v = PackagedRaceVenue(args, control.ChildWitness) if args.player_package else vm.Venue(args, artifact_family='desktop-end-race')
    try:
        v.start()
        mission = v.request('/api/missions', {'name':'End during approved join', 'briefing':'Owned UDP hold; genuine Windows clients, no injected gameplay',
            'durationSeconds':300, 'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
            'enemies':{'count':1,'behavior':'Hold','autoAttack':True}, 'props':[]}, expected=201)
        entry = v.create(mission, [3], 'end-race')
        v.wait(lambda:v.request(f'/api/sessions/{entry["id"]}/world', optional=True),90,'initial recording')
        first = entry['players'][0]; first_ticket=v.ticket(entry, first)
        v.launch('end-race-first',v.client_config(entry,first_ticket)); v.wait(lambda:v.connected(entry),90,'first rig')
        identity=str(uuid.uuid4()); state=v.request(f'/api/sessions/{entry["id"]}/players',{'playerId':identity,'roomId':3,'name':'Late approved player','headset':'Quest3'},role='Room3')
        late=next(x for x in state['players'] if x['id']==identity); entry['players'].append(late); ticket=v.ticket(entry,late)
        v.command(entry,'Begin'); v.wait(lambda:v.frame(entry)['packet']['frame']['phase']=='Running',20,'Running')
        v.wait(lambda:any(x['playerId']==first['id'] and x['damageTaken']>0 for x in v.frame(entry)['statistics']),20,'first player AI damage')
        server=lambda:debrief.log_text(v,'end-race-server')
        pending_before=server().count('VR_SERVER_CLIENT_PENDING ')
        approved_before=server().count('VR_SERVER_ADMISSION_APPROVED ')
        predicate = (lambda:server().count('VR_SERVER_CLIENT_PENDING ')>pending_before) if args.mode=='join-delay' else (
            lambda:'VR_CLIENT_DEBRIEF_PENDING ' in debrief.log_text(v,'end-race-late'))
        gate=LoopbackGate(entry['port'],predicate, mode='delay' if args.mode=='join-delay' else 'drop',pass_small_bytes=64 if args.mode=='result-large-drop' else 0,
                          max_hold_seconds=8 if args.mode=='join-delay' else 40).start()
        config=v.client_config(entry,ticket); config['port']=gate.port; v.launch('end-race-late',config)
        if args.mode=='join-delay':
            v.wait(lambda:gate.held.is_set() and server().count('VR_SERVER_ADMISSION_APPROVED ')>approved_before,20,'held approved join')
        else: v.wait(lambda:v.connected(entry),60,'both accepted rigs before End')
        before=debrief.log_text(v,'end-race-late')
        connected_before='VR_CLIENT_CONNECTED' in before
        if connected_before != (args.mode!='join-delay'): raise RuntimeError('Connection timing does not match the selected experiment')
        approvals=re.findall(r'^VR_SERVER_ADMISSION_APPROVED id=(\d+)$',server(),re.M)
        if len(approvals)!=approved_before+1: raise RuntimeError('Late approval count differs')
        late_connection=approvals[-1]
        v.save('before-end.json',{'approved':True,'clientConnectedLogged':connected_before,'mode':args.mode,'gate':gate.report()})
        end_started=time.monotonic()
        sealed=v.seal(entry)
        timeout_observation=None
        if args.mode=='join-delay':
            time.sleep(args.post_seal_delay)
        else:
            v.wait(lambda:gate.held.is_set(),5,'drop armed after pending receipt')
            if args.player_package:
                pending_status = v.wait(lambda:v.status('end-race-late', 'ResultPending'),5,'original packaged launcher waiting for results')
                v.save('packaged-result-pending.json', pending_status)
            def terminal():
                if re.search(r'^VR_SERVER_DEBRIEF_TIMEOUT id='+late_connection+r'$',server(),re.M): return 'resultDeadline'
                if args.mode=='result-drop' and re.search(r'^VR_SERVER_CLIENT_LEFT id='+late_connection+r'$',server(),re.M): return 'connectionReleased'
                return None
            terminal_kind=v.wait(terminal,36,'server result deadline or earlier connection release')
            if debrief.final_result(v,'end-race-late') is not None: raise RuntimeError('Final result escaped the intended loss interval')
            if 'VR_CLIENT_DEBRIEF_PENDING ' not in debrief.log_text(v,'end-race-late'): raise RuntimeError('Client did not first accept pending context')
            timeout_observation={'secondsSinceEndRequest':time.monotonic()-end_started,'terminalKind':terminal_kind,'finalReceived':False,'pendingReceived':True}
            v.save('timeout-observation.json',timeout_observation)
            v.wait(lambda:re.search(r'^VR_SERVER_CLIENT_LEFT id='+late_connection+r'$',server(),re.M),5,'server releases timed-out connection')
            if args.player_package:
                v.stop('end-race-late')  # Stop only the original native child while its result is still blocked.
                interrupted = v.status('end-race-late', 'ResultInterrupted')
                if (not interrupted or not interrupted['exited'] or interrupted['transitions'] !=
                        ['Waiting', 'Connected', 'ResultPending', 'ResultInterrupted']):
                    raise RuntimeError('The packaged launcher did not retain the exact interrupted result history')
                v.save('packaged-result-interrupted.json', interrupted)
        if gate.release_reason is not None: raise RuntimeError('Gate limit invalidated the intended experiment')
        gate.release()
        deadline=time.monotonic()+36
        while not args.player_package and time.monotonic()<deadline:
            if gate.error: raise RuntimeError(gate.error)
            text=debrief.log_text(v,'end-race-late')
            if 'VR_CLIENT_DEBRIEF_FINAL ' in text or 'VR_CLIENT_DISCONNECTED' in text or 'VR_CLIENT_ADMISSION_REJECTED' in text: break
            time.sleep(.1)
        first_result=v.wait(lambda:debrief.final_result(v,'end-race-first'),10,'first final result')
        debrief.validate_result(first_result,entry,first,sealed)
        late_result=debrief.final_result(v,'end-race-late')
        if late_result is not None: debrief.validate_result(late_result,entry,late,sealed)
        report={'complete':False,'source':'Actual Windows UDP; bounded opaque downstream delay or loss; Simulation rigs','headsets':0,
            'playerBuildReceipt':v.receipt,'mode':args.mode,'beforeEndClientConnectedLogged':connected_before,'firstResult':first_result,'lateResult':late_result,
            'timeoutObservation':timeout_observation,'sealed':sealed,'gate':gate.report()}
        if args.player_package:
            first_status = v.wait(lambda:v.status('end-race-first', 'Final'),5,'unaffected packaged launcher receives results')
            if first_status['transitions'] != ['Waiting', 'Connected', 'ResultPending', 'Final'] or late_result is not None:
                raise RuntimeError('The normal packaged result and interrupted result were not distinguished')
            v.save('packaged-result-final.json', first_status)
            report['packagedStatus'] = {'unaffected': first_status, 'pending': pending_status, 'interrupted': interrupted}
        v.save('race-result.json',report)
        if args.mode=='join-delay' and late_result is None: raise RuntimeError('Approved participant did not receive its sealed result')
        if args.mode=='join-delay': v.wait(lambda:server().count('VR_SERVER_DEBRIEF_ACK ')==2,5,'both result acknowledgements')
        v.launch('end-race-ended-ticket',v.client_config(entry,ticket))
        v.wait(lambda:'VR_CLIENT_ADMISSION_REJECTED' in debrief.log_text(v,'end-race-ended-ticket'),20,'Ended ticket rejection')
        if 'VR_CLIENT_DEBRIEF_' in debrief.log_text(v,'end-race-ended-ticket'): raise RuntimeError('New Ended connection received a result')
        if v.request(f'/api/sessions/{entry["id"]}/statistics')!=sealed['statistics']: raise RuntimeError('Final ledger changed')
        stream=v.state(entry)['combatStream']
        if not stream['sealed'] or any(r is not None and (r['streamId']!=stream['streamId'] or r['finalStreamSequence']!=stream['acceptedSequence']) for r in [first_result,late_result]):
            raise RuntimeError('Final combat stream boundary differs')
        report['replay']=replay(v,entry,sealed)
        report['toolFingerprint']=fingerprint
        report['checks']=['approved admission and client callback timing match the experiment',
            'unaffected peer receives exact own sealed result','delayed participant receives result' if args.mode=='join-delay' else 'pending participant has no final during bounded packet loss',
            'Ended ticket rejected without result or ledger mutation','combat stream id and final sequence agree',
            'entire replay contiguous and final packet / statistics unchanged']
        if args.player_package:
            report['checks'].append('Extracted player launcher distinguishes exact pending, interrupted and final histories')
        if args.verify_personal_report:
            verify_personal_report(v, entry, late)
            report['checks'].append('Room controller retrieves exactly the interrupted player sealed CSV row')
        v.save('race-result.json',report);v.evidence.extend(report['checks'])
        v.summary()
    except BaseException as error:
        v.stage('failed',errorType=type(error).__name__); raise
    finally:
        try:
            if gate is not None: gate.release(); gate.close(); v.save('gate.json',gate.report())
        finally:
            if not v.cleanup() and sys.exc_info()[0] is None: raise RuntimeError('Race cleanup failed')
    report['complete']=True; report['gate']=gate.report()
    if report['gate']['error'] or not report['gate']['threadStopped'] or report['gate']['releaseReason']!='requested': raise RuntimeError('Gate cleanup or bounds invalidated the experiment')
    if tool_fingerprint()!=fingerprint:raise RuntimeError('Fixture sources changed while the experiment was running')
    v.save('race-result.json',report); v.stage('passed',checks=len(report['checks']))


if __name__=='__main__': main()
