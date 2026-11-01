"""Bounded same-host observation metadata; never generates UI or game input."""
from datetime import datetime,timezone
import importlib.util
import hashlib
import json
import math
from pathlib import Path
import socket
import sys
import time

PLAN=[(f'{mode.lower()}-{epoch}',mode) for epoch in (1,2) for mode in ('Accessibility','Screenshot') for _ in range(3)]


def stationary_faults(frame,baseline):
    original={p['id']:p for p in baseline['players']};players=frame['players']
    if len(players)!=len(original) or {p['id'] for p in players}!=set(original):return [{'playerId':None,'fields':['roster']}]
    fields=('head','muzzle','forward','magazine','reserve','reloading','fireSequence')
    return [{'playerId':p['id'],'fields':[key for key in fields if p[key]!=original[p['id']][key]]}
        for p in players if any(p[key]!=original[p['id']][key] for key in fields)]


def validate_records(value,session,player,pid,host):
    if set(value)!={'version','sessionId','playerId','visiblePid','platform','clockHostSha256','operations'} \
        or value['version']!=1 or value['sessionId']!=session or value['playerId']!=player or value['visiblePid']!=pid:
        raise ValueError('Observer records belong to another fixture / original player')
    rows=value['operations']
    if len(rows)!=len(PLAN):raise ValueError('Missing / extra observer operations')
    clocks=[];prior=None;window=None
    keys={'index','epoch','mode','windowId','fromUtc','toUtc','fromMilliseconds','toMilliseconds','screenshots','apiReturned'}
    for index,(row,expected) in enumerate(zip(rows,PLAN),1):
        if set(row)!=keys or row['index']!=index or (row['epoch'],row['mode'])!=expected or row['apiReturned'] is not True:
            raise ValueError('Observer operation order / result / metadata differs')
        if type(row['windowId']) is not int or row['windowId']<1 or type(row['screenshots']) is not int \
            or (row['screenshots']!=0 if row['mode']=='Accessibility' else row['screenshots']<1):raise ValueError('Observer surface / image mode differs')
        if window is not None and row['windowId']!=window:raise ValueError('Observer switched target windows')
        window=row['windowId'];begin=row['fromMilliseconds'];end=row['toMilliseconds']
        if any(type(t) not in (int,float) or not math.isfinite(t) or t<0 for t in (begin,end)) or end<begin:
            raise ValueError('Invalid observer monotonic interval')
        a=datetime.fromisoformat(row['fromUtc']);b=datetime.fromisoformat(row['toUtc'])
        if a.utcoffset() is None or b.utcoffset() is None:raise ValueError('Observer UTC requires an explicit offset')
        clocks.append(abs((b-a).total_seconds()-(end-begin)/1000))
        if prior:
            if begin<prior[0]:raise ValueError('Observer monotonic intervals overlap / rewind')
            clocks.append(abs((a-prior[1]).total_seconds()-(begin-prior[0])/1000))
        prior=(end,b)
    error=max(clocks,default=0)
    same_host=value['platform']=='win32' and value['clockHostSha256']==host
    return {'complete':True,'operations':len(rows),'windowId':window,'clockHostMatched':same_host,'clockJoinValid':error<.05 and same_host,'maximumClockStepSeconds':error,
        'source':'External CUA call brackets; includes queue / helper / response time, not GPU CPU / RTT'}


def run(v,entry,own,native,references,capture,check):
    pid=next(p['pid'] for p in native if p['visible']);marks=[];samples=[];state_faults=[]
    baseline=references[min(references)]['packet']['frame']
    def mark(name):
        marks.append({'phase':name,'utc':datetime.now(timezone.utc).isoformat()});v.save('observer-stages.json',marks)
    def sample(label):
        if (v.directory/'observer-abort.json').exists():raise RuntimeError('Observer reported an aborted or unknown operation')
        if v.observer_heartbeat and v.observer_heartbeat.child.poll() is not None:raise RuntimeError('Observer independent timer exited before explicit finish')
        value=v.frame(entry,measure=True);frame=value['packet']['frame']
        faults=stationary_faults(frame,baseline)
        if faults and len(state_faults)<64:state_faults.append({'sequence':value['packet']['sequence'],'tick':frame['tick'],'faults':faults})
        if len(samples)>=4096:raise RuntimeError('Observer source sample bound exceeded')
        samples.append({'phase':label,'sequence':value['packet']['sequence'],'tick':frame['tick'],'phaseValue':frame['phase'],
            'utc':datetime.now(timezone.utc).isoformat(),'connected':sum(p['connected'] for p in frame['players'])})
        return value
    host=hashlib.sha256(socket.gethostname().encode()).hexdigest()
    v.save('observer-config.json',{'version':1,'sessionId':entry['id'],'playerId':own['id'],'visiblePid':pid,'platform':sys.platform,'clockHostSha256':host,
        'plan':[{'epoch':epoch,'mode':mode} for epoch,mode in PLAN],'maximumOperations':12,'maximumWindowSeconds':120,
        'keysAllowed':False,'directory':str(v.directory)})
    v.stage('observer-ready',acknowledgement='observer-ready.done',seconds=40,note='Select and observe the sole owned game window; no game keys')
    v.wait(lambda:sample('setup') and (v.directory/'observer-ready.done').exists(),40,'observer surface confirmation')
    spec=importlib.util.spec_from_file_location('observer_timer_owner',Path(__file__).with_name('check-desktop-pose-input.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    v.observer_heartbeat=module.Heartbeat(v.runtime_directory/'observer-heartbeat')
    v.processes['observer-independent-timer']=v.observer_heartbeat.child
    v.wait(lambda:v.observer_heartbeat.directory.exists() and v.observer_heartbeat.child.poll() is None,5,'observer independent timer startup')
    try:
        mark('baseline-start');v.stage('observer-baseline',seconds=8)
        end=time.monotonic()+8
        while time.monotonic()<end:sample('baseline');time.sleep(.15)
        mark('baseline-end');mark('external-start')
        v.stage('observer-sequence',acknowledgement='observer-operations.done',seconds=120,operations=12,note='Only Accessibility / Screenshot observations from observer-config.json; no game keys')
        v.wait(lambda:sample('external') and (v.directory/'observer-operations.done').exists(),120,'observer operation review')
        records=v.directory/'observer-operations.json'
        if not records.is_file():raise RuntimeError('Observer acknowledgement has no operation records')
        if records.stat().st_size>65536:raise ValueError('Observer records exceed their bounded metadata size')
        summary=validate_records(json.loads(records.read_text(encoding='utf-8-sig')),entry['id'],own['id'],pid,host)
        mark('external-end');mark('quiet-after-start');v.stage('observer-quiet-after',seconds=8)
        end=time.monotonic()+8
        while time.monotonic()<end:sample('quiet-after');time.sleep(.15)
        mark('quiet-after-end');mark('observation-end')
    finally:
        v.save('observer-world-samples.json',samples)
        v.save('observer-state-checks.json',{'passed':not state_faults,'samples':len(samples),'faults':state_faults,'maximumFaultSamples':64})
    timer=v.finish_observer_timer()
    v.command(entry,'Pause');v.wait(lambda:v.frame(entry)['packet']['frame']['phase']=='Paused',15,'observer final Pause')
    capture(v,entry,native,'observer-final',references)
    stats=v.request(f'/api/sessions/{entry["id"]}/statistics')
    if state_faults:raise RuntimeError('Stationary observer source pose / weapon state changed; no-input acceptance failed')
    if len(stats['players'])!=25 or any(p['health']!=100 or any(p[k]!=0 for k in ('ammoUsed','shotsHit','kills','damageTaken','hitsReceived','accuracyPercent')) for p in stats['players']):
        raise RuntimeError('Observation-only flow changed combat statistics')
    check(True,'twelve bounded external observations preserve zero weapon input; exact source / replica checks retained')
    result={'complete':True,'scope':'Controlled zero-key observation sequence, not active-player capacity or root-cause proof','marks':marks,
        'operations':summary,'independentHeartbeat':{'complete':timer['complete'],'maximumGapNs':timer['maximumGapNs']},'sourceSamples':len(samples)}
    v.save('observer-sequence-result.json',result)
    return next(p for p in stats['players'] if p['playerId']==own['id']),result
