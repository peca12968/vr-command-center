"""Two real PC players, actual movement/reload input, observer framebuffer and seal."""
import argparse,importlib.util,json,math,os,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('body_venue',ROOT/'scripts/start-desktop-venue.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def run(v):
 v.start();mission=v.request('/api/missions',{'name':'Player body - Simulation','briefing':'Actual two PC players / movement / reload / observer GPU','durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
 e=v.create(mission,[3],'player-body',role='Room3');observer=e['players'][0];target_id=str(uuid.uuid4());state=v.request('/api/sessions/'+e['id']+'/players',{'playerId':target_id,'name':'Visible body target','roomId':3,'headset':'Quest3'},role='Room3');target=next(p for p in state['players']if p['id']==target_id);e['players'].append(target)
 v.wait(lambda:v.request('/api/sessions/'+e['id']+'/world',optional=True),90,'body recording');probe=v.runtime_directory/'player-body-probe'
 v.launch('body-observer',v.client_config(e,v.ticket(e,observer)),True,extra_args=['--vr-player-body-probe',str(probe.resolve())]);samples=[]
 def frame(label):
  q=v.frame(e,measure=True);samples.append({'label':label,'sequence':q['packet']['sequence'],'frame':q['packet']['frame']});v.save('body-samples.json',samples);return q['packet']['frame']
 def actor(f,p):return next(x for x in f['players']if x['id']==p['id'])
 v.wait(lambda:actor(frame('observer-connect'),observer)['connected'],30,'observer connection');v.command(e,'Begin')
 v.stage('observer-view',note='Actual S to head z <= -4.5, actual Down about 15 degrees and Right to heading 54, then observer.done')
 def ready_view():
  p=actor(frame('view-position'),observer)
  return p['head']['z']<=-4.5 and p['forward']['y']<-.15 and 45<=math.degrees(math.atan2(p['forward']['x'],p['forward']['z']))<=65 and (v.directory/'observer.done').exists()
 v.wait(ready_view,300,'actual observer keyboard view');v.launch('body-target',v.client_config(e,v.ticket(e,target)),True);v.wait(lambda:v.connected(e),45,'two actual players')
 def report(final=False):
  p=probe/('report.json'if final or(probe/'report.json').exists()else'status.json')
  try:r=json.loads(p.read_text(encoding='utf-8-sig'))
  except(FileNotFoundError,json.JSONDecodeError):return None
  if r['error']:raise RuntimeError(r['error'])
  return r
 def capture(name,seconds=15):
  request=probe/'capture.request';temporary=probe/('capture-'+uuid.uuid4().hex+'.tmp');temporary.write_text(name,encoding='utf-8');os.replace(temporary,request)
  return v.wait(lambda:(row if (r:=report())and (row:=next((c for c in r['captures']if c['file']==name+'.png'),None))else None),seconds,'actual body GPU '+name)
 time.sleep(.5);idle=capture('idle')
 rows=lambda c:next(p for p in c['players']if p['id']==target_id)
 v.stage('target-walk',note='Actual W in the newly opened target; native observer captures a genuinely nonzero visible walking pose before Pause')
 gait=capture('walking',180);assert gait['phase']=='Running'and rows(gait)['visible']and rows(gait)['walking']and abs(rows(gait)['stride'])>.5
 v.command(e,'Pause');paused=v.wait(lambda:(f if(f:=frame('pause-walk'))['phase']=='Paused'else None),10,'paused gait')
 time.sleep(1);walk=capture('paused-walk');time.sleep(.3);again=capture('paused-walk-again')
 a,b=rows(walk),rows(again);vectors=['head','feet','leftElbow','leftWrist','rightElbow','rightWrist']
 paused_delta=max(abs(a[k][axis]-b[k][axis])for k in vectors for axis in ['x','y','z'])
 assert a['visible']and paused_delta<=.000001 and all(a[k]==b[k]for k in a if k not in vectors)
 v.command(e,'Resume');v.wait(lambda:not actor(frame('idle-after-walk'),target)['walking'],10,'accepted idle gait');time.sleep(.3);after=capture('idle-after-walk');assert abs(rows(after)['stride'])<.001
 v.stage('reload',note='Actual Space once, then actual R on target; the helper pauses the accepted reload')
 def reload_frame():
  f=frame('reload-wait');p=actor(f,target);return f if p['magazine']==29 and p['reloading']and 8<=p['reloadUntilTick']-f['tick']<=22 else None
 v.wait(reload_frame,180,'actual Space and R');v.command(e,'Pause');f=v.wait(lambda:(f if(f:=frame('pause-reload'))['phase']=='Paused'else None),10,'paused reload');assert actor(f,target)['reloading']
 time.sleep(.5);reload=capture('paused-reload');assert rows(reload)['arms']
 v.stage('review',note='Inspect six actual observer PNGs and acknowledge review.done; no input or poses injected',probeDirectory=str(probe))
 v.wait(lambda:(v.directory/'review.done').exists(),180,'actual image review');(probe/'finish.request').write_text('Stop this diagnostic only',encoding='utf-8');final=v.wait(lambda:(r if(r:=report(True))and r['complete']else None),15,'body probe finish')
 assert final['audioSamples']==final['callbackCount']==0
 sealed=v.seal(e);assert sealed['world']['header']['assetSet']=='player-body-v1'and sealed['world']['header']['playerPresentationVersion']==1
 for p in sealed['statistics']['players']:assert p['ammoUsed']==(1 if p['playerId']==target_id else 0)and p['health']==100 and p['damageTaken']==0 and p['kills']==0
 v.save('player-body-result.json',{'observerId':observer['id'],'targetId':target_id,'probe':final,'gaitCapture':gait,'pausedFrame':paused,'pausedMaximumTransformDelta':paused_delta,'pausedReloadFrame':f,'source':'Actual two Windows clients / keyboard / own observer GPU','headsets':0,'poseOrWeaponInjected':False,'replayStatisticsMatch':sealed['replayStatisticsMatch']})
 v.evidence.extend(['Two real PC players show original military body from an actual observer camera','Actual target movement produces nonzero running gait; paused clock / gait identical and native endpoints within one micrometre','Actual Space / R drives saved adaptive glove arms while original ammo rules remain','Explicit bounded GPU finish, final replay / combat seal and no injected pose or input']);v.summary()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path);p.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')));p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')));a=p.parse_args();a.duration=600;a.visible_room=3;a.job_workers=2;a.check=False;m.verify_player(a);v=m.Venue(a)
 try:run(v)
 except BaseException as e:v.stage('failed',errorType=type(e).__name__);raise
 finally:
  if not v.cleanup()and sys.exc_info()[0]is None:raise RuntimeError('Body fixture cleanup failed')
if __name__=='__main__':main()
