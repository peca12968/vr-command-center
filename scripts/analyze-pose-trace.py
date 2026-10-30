"""Read closed pose-timing fixture evidence; never open SQLite or credentials."""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def ticks(iso):
    delta=datetime.fromisoformat(iso.replace('Z','+00:00')).astimezone(timezone.utc)-datetime(1,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*10000000+delta.microseconds*10

def load_report(path,role):
    r=json.loads(path.read_text(encoding='utf-8-sig'))
    assert r['schemaVersion']==1 and r['source']=='NativeWindowsMonotonicTiming' and r['role']==role
    assert r['complete'] and not r['truncated'] and not r['error'] and len(r['rows'])<=r['capacity']==32768
    previous=None
    for row in r['rows']:
        assert all(math.isfinite(row[k])for k in ['seconds','engineSeconds','durationSeconds','poseAgeSeconds'])
        assert type(row['utcTicks'])is int and row['seconds']>=0 and row['durationSeconds']>=0
        if previous:assert row['seconds']>=previous['seconds']
        previous=row
    assert r['endedSeconds']>=r['rows'][-1]['seconds']
    return r

def analyze(directory):
    marks=json.loads((directory/'trace-stages.json').read_text());mark={r['phase']:ticks(r['utc'])for r in marks}
    rt=directory/'runtime-snapshot'
    reports={role:load_report(rt/('pose-timing-'+name+'-trace/report.json'),role)for name,role in [('player','Client'),('server','Server')]}
    def window(start,end):return(mark[start],mark[end])
    def overlaps(row,period):return row['utcTicks']>=period[0] and row['utcTicks']-int(row['durationSeconds']*10000000)<=period[1]
    def gaps(role,point,period):
        rows=[r for r in reports[role]['rows']if r['point']==point];out=[]
        for a,b in zip(rows,rows[1:]):
            if a['utcTicks']<=period[1] and b['utcTicks']>=period[0]:out.append({'seconds':b['seconds']-a['seconds'],'fromUtcTicks':a['utcTicks'],'toUtcTicks':b['utcTicks']})
        return out
    def summary(period):
        result={}
        for role,point in [('Client','PoseSend'),('Server','PoseReceive'),('Server','PoseAccepted')]:
            g=gaps(role,point,period);result[point]={'count':len(g),'maximumGapSeconds':max((r['seconds']for r in g),default=None),'gapsOverHalfSecond':[r for r in g if r['seconds']>.5]}
        for role in reports:
            rows=[r for r in reports[role]['rows']if overlaps(r,period)]
            result[role]={'maximumMainThreadGapSeconds':max((r['durationSeconds']for r in rows if r['point']=='MainThreadGap'),default=0),
                'maximumSpans':{point:max(r['durationSeconds']for r in rows if r['point']==point)for point in sorted({r['point']for r in rows if r['durationSeconds']>0 and r['point']!='MainThreadGap'})},
                'staleTransitions':[{'utcTicks':r['utcTicks'],'poseAgeSeconds':r['poseAgeSeconds'],'connection':r['connection']}for r in rows if r['point']=='BodyConnection' and not r['connected']],
                'invalidOrRejected':sum(r['point']in ['PoseInvalid','PoseRejected','LocalPoseInvalid','TrackingUnavailable']for r in rows),
                'throttled':sum(r['point']=='PoseThrottled'for r in rows)}
        return result
    phases={'naturalBaseline':summary(window('baseline-start','baseline-end')),'controlledLoss':summary(window('loss-start','loss-recovered')),'gpuStage':summary(window('gpu-stage-start','gpu-stage-end'))}
    control=phases['controlledLoss'];calibrated=bool(control['Server']['staleTransitions']) and control['PoseReceive']['maximumGapSeconds']>=.5
    calibrated=calibrated and control['PoseSend']['maximumGapSeconds']<.5 and control['Client']['maximumMainThreadGapSeconds']<.5 and control['Server']['maximumMainThreadGapSeconds']<.5
    # UTC is used only for this same-host interval join. Detect clock adjustments
    # rather than silently treating them as network or execution latency.
    clock_errors={role:max((abs((b['utcTicks']-a['utcTicks'])/10000000-(b['seconds']-a['seconds']))for a,b in zip(r['rows'],r['rows'][1:])),default=0)for role,r in reports.items()}
    calibrated=calibrated and all(v<.05 for v in clock_errors.values())
    return {'source':'Actual native same-host timing; no per-packet correlation or cross-machine latency claim','calibrated':calibrated,'clockStepMaximumSeconds':clock_errors,'mainThreadGapRecordingThresholdSeconds':.1,
        'phases':phases,'limits':['PoseSend marks the RPC call, not transport completion; no pose payload or per-packet correlation','BodyConnection changes are sampled at state publication, not every simulation tick','Intervals include boundary send/receive gaps','Main-thread gap maximum zero means no gap over 100ms was recorded','A clean baseline does not establish the cause of a historical stall','Diagnostic final report serialization and IO occur after observation ends']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);args=p.parse_args();d=args.directory.resolve()
    if d.parent!=ROOT/'artifacts/desktop-venue' or not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}',d.name):p.error('Pass this repository own desktop-venue evidence directory')
    assert json.loads((d/'cleanup.json').read_text())=={'errors':[],'remainingTrackedChildren':[]}
    result=analyze(d);(d/'pose-timing-analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    if not result['calibrated']:raise SystemExit('Controlled loss calibration was confounded; inspect retained evidence')

if __name__=='__main__':main()
