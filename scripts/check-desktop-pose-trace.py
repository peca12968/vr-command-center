"""Observe native pose timing, calibrate with loss, then inspect an actual shot.

No pose / combat injection. The loopback gate forwards unchanged UDP and only
drops upstream traffic during one explicitly recorded interval. Native trace
buffers stay in memory until an explicit finish, independently on each process.
"""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('trace_venue',ROOT/'scripts/start-desktop-venue.py');venue_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(venue_module)
spec=importlib.util.spec_from_file_location('trace_loss',ROOT/'scripts/check-desktop-pose.py');loss_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(loss_module)

class TraceVenue(venue_module.Venue):
    def launch(self,name,configuration,visible=False,extra_args=None):
        args=list(extra_args or [])
        if name in ['pose-timing-server','pose-timing-player']:args+=['--vr-pose-trace',str((self.runtime_directory/(name+'-trace')).resolve())]
        return super().launch(name,configuration,visible,extra_args=args)

def run(v,gates):
    v.start();marks=[];samples=[]
    def mark(phase,**extra):
        marks.append({'phase':phase,'utc':datetime.now(timezone.utc).isoformat(),**extra});v.save('trace-stages.json',marks)
    mission=v.request('/api/missions',{'name':'Pose timing - Simulation','briefing':'Timing only / one controlled upstream loss / actual Space',
        'durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
        'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
    entry=v.create(mission,[3],'pose-timing',role='Room3');own=entry['players'][0]
    v.wait(lambda:v.request('/api/sessions/'+entry['id']+'/world',optional=True),90,'recording')
    gate=loss_module.LossGate(entry['port']);gates.append(gate);config=v.client_config(entry,v.ticket(entry,own));config['port']=gate.port
    gpu=v.runtime_directory/'player-fire-probe';v.launch('pose-timing-player',config,True,extra_args=['--vr-player-fire-probe',str(gpu.resolve())])
    v.wait(lambda:v.connected(entry),45,'admitted visible native client');v.command(entry,'Begin')
    def observe(label):
        if gate.error:raise RuntimeError('Loopback gate failed: '+gate.error)
        q=v.frame(entry,measure=True);f=q['packet']['frame'];p=next(p for p in f['players']if p['id']==own['id'])
        row={'label':label,'utc':datetime.now(timezone.utc).isoformat(),'sequence':q['packet']['sequence'],'tick':f['tick'],
            'connected':p['connected'],'rig':p['rig']['kind'],'magazine':p['magazine'],'health':p['health'],
            'head':p['head'],'muzzle':p['muzzle'],'forward':p['forward']};samples.append(row);v.save('trace-world-samples.json',samples);return row
    v.stage('baseline',seconds=v.args.baseline_seconds);mark('baseline-start');deadline=time.monotonic()+v.args.baseline_seconds
    while time.monotonic()<deadline:observe('baseline');time.sleep(.15)
    mark('baseline-end');v.wait(lambda:observe('before-loss')['connected'],10,'fresh baseline')
    mark('loss-start',durationSeconds=1.2);gate.until=time.monotonic()+1.2
    stale=v.wait(lambda:(r if not (r:=observe('controlled-loss'))['connected'] else None),5,'controlled pose expiry')
    assert stale['rig']=='None' and stale['health']==100 and stale['magazine']==30
    recovered=v.wait(lambda:(r if (r:=observe('loss-recovery'))['connected'] and r['rig']=='Simulated' else None),10,'same admission recovery')
    mark('loss-recovered');assert gate.dropped>0
    assert all(recovered[key]==stale[key]for key in ['head','muzzle','forward','health','magazine'])
    mark('gpu-stage-start');v.stage('fire',key='space',presses=1,note='Actual Space once, then fire.done')
    v.wait(lambda:(r if (r:=observe('fire'))['connected'] and r['magazine']==29 and (v.directory/'fire.done').exists() else None),90,'actual native shot')
    def gpu_report(final=False):
        path=gpu/('report.json'if final or (gpu/'report.json').exists()else'status.json')
        try:r=json.loads(path.read_text(encoding='utf-8-sig'))
        except(FileNotFoundError,json.JSONDecodeError):return None
        if r['error']:raise RuntimeError(r['error'])
        return r
    v.wait(lambda:(r if (r:=gpu_report()) and any(p['visible']for c in r['captures']for p in c['players'])else None),10,'actual player GPU pulse')
    v.command(entry,'Pause');v.wait(lambda:v.frame(entry)['packet']['frame']['phase']=='Paused',10,'native Pause')
    v.wait(lambda:(r if (r:=gpu_report()) and any(c['phase']=='Paused'for c in r['captures'])else None),10,'paused GPU capture')
    mark('gpu-stage-end');v.stage('review',probeDirectory=str(gpu),note='Review actual shot and Pause PNGs, then review.done')
    v.wait(lambda:(v.directory/'review.done').exists(),60,'GPU review')
    for folder in [gpu,v.runtime_directory/'pose-timing-player-trace',v.runtime_directory/'pose-timing-server-trace']:
        (folder/'finish.request').write_text('Finish local diagnostic only; no gameplay mutation',encoding='utf-8')
    def trace(folder):
        try:r=json.loads((folder/'report.json').read_text(encoding='utf-8-sig'))
        except(FileNotFoundError,json.JSONDecodeError):return None
        assert r['complete'] and not r['truncated'] and not r['error'];return r
    reports={role:v.wait(lambda role=role:trace(v.runtime_directory/('pose-timing-'+role+'-trace')),10,role+' timing report')for role in ['player','server']}
    final=v.wait(lambda:(r if (r:=gpu_report(True)) and r['complete']else None),10,'explicit GPU diagnostic finish')
    assert final['audioSamples']==final['callbackCount']==0 and not final['observedEnd']
    v.wait(lambda:observe('after-report-write')['connected'],10,'fresh pose after diagnostic report IO')
    sealed=v.seal(entry);stats=next(p for p in sealed['statistics']['players']if p['playerId']==own['id'])
    assert stats['ammoUsed']==1 and stats['shotsHit']==stats['kills']==stats['damageTaken']==0 and stats['health']==100
    v.save('pose-timing-result.json',{'headsets':0,'source':'Actual native Windows / same host timing / Simulation','baselineSeconds':v.args.baseline_seconds,
        'marks':marks,'controlledLoss':{'stale':stale,'recovered':recovered,'dropped':gate.dropped,'forwarded':gate.forwarded},
        'traceReports':{role:{'rows':len(r['rows']),'duration':r['endedSeconds'],'complete':r['complete']}for role,r in reports.items()},
        'statistics':stats,'gpuProbe':final,'poseOrCombatInjected':False})
    v.evidence.extend(['Natural no-GPU-readback baseline; both process pose and main-thread timing retained',
        'Controlled upstream packet loss expires pose and recovers same admission without changing freshness rules',
        'Actual Space / GPU readback, PNG encode and write spans retained separately','Explicitly finished bounded traces and exact replay / combat seal'])
    v.summary()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path)
    p.add_argument('--baseline-seconds',type=int,choices=range(10,91),default=60)
    p.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args=p.parse_args();args.duration=600;args.visible_room=3;args.job_workers=2;args.check=False
    try:venue_module.verify_player(args, python_listener=True)
    except(OSError,RuntimeError,ValueError)as error:p.error(str(error))
    v=TraceVenue(args);gates=[]
    try:run(v,gates)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        gate_errors=[]
        for gate in gates:
            try:gate.close()
            except Exception as error:gate_errors.append(type(error).__name__)
        cleaned=v.cleanup();v.save('gate-cleanup.json',{'errors':gate_errors})
        if (gate_errors or not cleaned) and sys.exc_info()[0]is None:raise RuntimeError('Pose timing cleanup failed')

if __name__=='__main__':main()
