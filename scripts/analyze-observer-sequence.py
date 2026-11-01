"""Read closed observer metadata / sparse JSON, never saved SQLite or image data."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
sparse=load('observer_sparse','analyze-pose-continuity.py')
observer=load('observer_metadata','observer-sequence.py')
SCALE=10_000_000

def read(path):
    if path.stat().st_size>16*1024*1024:raise ValueError('Observer JSON exceeds its bounded input size')
    return json.loads(path.read_text(encoding='utf-8-sig'))

def union_seconds(intervals):
    merged=[]
    for start,end in sorted(intervals):
        if end<=start:continue
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    return sum(b-a for a,b in merged)/SCALE

def overlap(row,start,end):return row['fromUtcTicks']<end and row['toUtcTicks']>start

def join_operation(operation,report,validation,connection,caller_clock_valid):
    start=sparse.legacy.common.ticks(operation['fromUtc']);end=sparse.legacy.common.ticks(operation['toUtc'])
    valid=caller_clock_valid and validation['clockJoinValid'] and end>=start
    points={};complete=bool(valid)
    for point in (['PoseSend'] if report['role']=='Client' else ['PoseReceive','PoseAccepted']):
        streams=[s for s in report['streams'] if s['point']==point and s['connection']==connection and s['source']==1]
        covered=any(s['firstUtcTicks']<=start and s['lastUtcTicks']>=end for s in streams)
        if not valid or not covered:
            points[point]={'covered':covered,'overlappingGapCount':None,'overlapUnionSeconds':None,'examples':None};complete=False;continue
        gaps=[g for g in report['gaps'] if g['point']==point and g['connection']==connection and g['source']==1 and overlap(g,start,end)]
        points[point]={'covered':True,'overlappingGapCount':len(gaps),
            'overlapUnionSeconds':union_seconds([(max(start,g['fromUtcTicks']),min(end,g['toUtcTicks'])) for g in gaps]),
            'examples':gaps[:8],'examplesOmitted':max(0,len(gaps)-8)}
    covered=bool(report['streams']) and min(s['firstUtcTicks'] for s in report['streams'])<=start and max(s['lastUtcTicks'] for s in report['streams'])>=end
    windows=[w for w in validation['mainThreadWindows'] if overlap(w,start,end)] if valid and covered else None
    loop=validation.get('playerLoop')
    loops=[g for g in loop['gaps'] if overlap(g,start,end)] if valid and covered and loop else ([] if valid and covered else None)
    return {'complete':complete and covered,'clockJoinValid':valid,'observationCovered':covered,'points':points,
        'mainThreadWindowCount':len(windows) if windows is not None else None,'mainThreadWindowExamples':windows[:8] if windows is not None else None,
        'mainThreadWindowExamplesOmitted':max(0,len(windows)-8) if windows is not None else None,
        'playerLoopOverlapCount':len(loops) if loops is not None else None,'playerLoopExamples':loops[:8] if loops is not None else None,
        'limits':'CPU fields belong to the complete original Update sample brackets; never scaled or attributed to this external call. Point gaps are separate unions, never summed across points.'}

def analyze(directory):
    directory=directory.resolve()
    if directory.parent!=(ROOT/'artifacts/desktop-active').resolve() or not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}',directory.name):raise ValueError('Use an owned desktop-active run directory')
    for file,keys in [('cleanup.json',['errors','remainingTrackedChildren']),('observer-heartbeat-cleanup.json',['errors','remaining']),('active-pose-cleanup.json',['errors'])]:
        value=read(directory/file)
        if any(value.get(key)!=[] for key in keys):raise ValueError('Missing / unknown / failed cleanup')
    if read(directory/'active-pose-cleanup.json').get('finished') is not True:raise ValueError('Pose diagnostic is unfinished')
    cfg=read(directory/'observer-config.json');ready=read(directory/'active-ready.json');records=read(directory/'observer-operations.json')
    metadata=observer.validate_records(records,cfg['sessionId'],cfg['playerId'],cfg['visiblePid'],cfg['clockHostSha256'])
    native=read(directory/'active-native-clients.json');visible=[p for p in native if p['visible']]
    if len(native)!=25 or len(visible)!=1 or visible[0]['playerId']!=cfg['playerId'] or visible[0]['pid']!=cfg['visiblePid'] \
        or any(p['sessionId']!=cfg['sessionId'] for p in native):raise ValueError('Original visible / native owner metadata differs')
    result=read(directory/'active-result.json');stage=read(directory/'stage.json')['stage']
    if stage not in ('passed','failed') or (stage=='passed')!=(result['complete'] is True):raise ValueError('Run is not terminal or acceptance metadata contradicts its stage')
    if result['activePlayers']!=0 or result['receivingPeers']!=25 or result['inputStages']!=[] or result['statistics']['ammoUsed']!=0:
        raise ValueError('This was not a zero-key observation run')
    if result['operatorUi'] is not None:
        ui=result['operatorUi'];cleanup=read(directory/'active-ui-cleanup.json')
        if cleanup.get('errors')!=[] or cleanup.get('helperTerminal') is not True or ui['requests']!=0 or ui['attempts']!=0 or not ui['cleanShutdown']:
            raise ValueError('Idle console shutdown / zero-write proof is missing')
    programs=read(directory/'active-pose-diagnostics.json')['programs']
    if len(programs)!=2 or sorted(p['role'] for p in programs)!=['Client','Server']:raise ValueError('Expected only server and visible-client diagnostics')
    data={};validations={};source_hashes={}
    runtime=Path(ready['runtimeDirectory']).resolve()
    for program in programs:
        relative=Path(program['directory']).resolve().relative_to(runtime)
        path=directory/'runtime-snapshot'/relative/'report.json';report=read(path)
        validation=sparse.validate(report,program['role'],program['loop'])
        if program['role']=='Client' and (program['name']!=visible[0]['name'] or program['connection']!=visible[0]['nativeConnectionId']):raise ValueError('Pose diagnostic selected a different client connection')
        data[program['role']]=report;validations[program['role']]=validation
        source_hashes[program['role']]=hashlib.sha256(path.read_bytes()).hexdigest()
    operations=[]
    for row in records['operations']:
        operations.append({'index':row['index'],'epoch':row['epoch'],'mode':row['mode'],'fromUtc':row['fromUtc'],'toUtc':row['toUtc'],
            'externalCallSeconds':(row['toMilliseconds']-row['fromMilliseconds'])/1000,
            'native':{role:join_operation(row,data[role],validations[role],visible[0]['nativeConnectionId'],metadata['clockJoinValid']) for role in data}})
    marks=read(directory/'observer-stages.json');times={r['phase']:sparse.legacy.common.ticks(r['utc']) for r in marks}
    for row in operations:
        if not times['external-start']<=sparse.legacy.common.ticks(row['fromUtc'])<=sparse.legacy.common.ticks(row['toUtc'])<=times['external-end']:
            raise ValueError('Observer operation falls outside its declared collection phase')
    timer=read(directory/'runtime-snapshot/observer-heartbeat/report.json')
    periods={r['epoch']:(min(sparse.legacy.common.ticks(o['fromUtc']) for o in records['operations'] if o['epoch']==r['epoch']),
        max(sparse.legacy.common.ticks(o['toUtc']) for o in records['operations'] if o['epoch']==r['epoch'])) for r in records['operations']}
    heartbeat=sparse.legacy.heartbeat_analysis(timer,[],periods,metadata['clockJoinValid'])
    for row in operations:
        a=sparse.legacy.common.ticks(row['fromUtc']);b=sparse.legacy.common.ticks(row['toUtc'])
        covered=heartbeat['coverageFromUtcTicks']<=a<=b<=heartbeat['coverageToUtcTicks']
        row['heartbeat']={'covered':covered,'clockJoinValid':heartbeat['clockJoinValid'],
            'overlappingRecordedGaps':[g for g in timer['gaps'] if sparse.EPOCH+g['fromUnixNs']//100<b and sparse.EPOCH+g['toUnixNs']//100>a] if covered and heartbeat['clockJoinValid'] else None}
    complete=all(n['complete'] for r in operations for n in r['native'].values()) and all(r['heartbeat']['covered'] and r['heartbeat']['clockJoinValid'] for r in operations)
    return {'version':1,'complete':complete,'source':'Closed observer / sparse-pose / independent-timer JSON','sessionId':cfg['sessionId'],
        'missionAcceptancePassed':result['complete'] and result['continuityPassed'],'rootCauseProven':False,'observer':metadata,'nativeReportSha256':source_hashes,
        'operations':operations,'heartbeat':heartbeat,'limits':['Caller brackets include SDK queue, helper and result time; not native GPU time, FPS or network RTT',
        'Fixed-order same-host observations and overlap do not establish causation or exclude other load / observer perturbation',
        'No diagnostic point has a world sequence here; no point-to-world-frame pairing or cross-run calibration',
        'Sparse intervals below recording thresholds remain unknown; zero retained gaps is not zero timing jitter']}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();directory=args.directory.resolve();output=args.output.resolve()
    if directory.parent!=(ROOT/'artifacts/desktop-active').resolve() or not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}',directory.name):raise ValueError('Use an owned desktop-active run directory')
    runtime=Path(read(directory/'active-ready.json')['runtimeDirectory']).resolve()
    if output.is_relative_to(directory) or output.is_relative_to(runtime) or output.exists():raise ValueError('Use a new output outside the original run and runtime')
    result=analyze(directory)
    with output.open('x',encoding='utf-8') as file:json.dump(result,file,ensure_ascii=False,indent=2)
    print(json.dumps({'complete':result['complete'],'missionAcceptancePassed':result['missionAcceptancePassed'],'operations':len(result['operations'])}))
    if not result['complete']:raise SystemExit('Observer clock / observation coverage is insufficient; joins withheld')

if __name__=='__main__':main()
