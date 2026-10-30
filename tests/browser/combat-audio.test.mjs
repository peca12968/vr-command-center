import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {CombatAudioCursor} from '../../src/VrCommand.Api/wwwroot/console/combat-audio.js';
import {validateRecording} from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
import {playerFireFixture} from './player-fire-fixture.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
test('frozen original PCM and sound metadata retain their canonical pins',async()=>{
  const profile=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Resources/VrCommand/combat-audio-v1.json'));
  assert.equal(createHash('sha256').update(profile).digest('hex'),'92d1a05a3d6598e61f88e38b9386efd882ac5776f58e27b4f122c98fef043a2f');
  const p=JSON.parse(profile);assert.equal(p.voices,32);assert.equal(p.maximumDistance,25);
  for(const[name,v]of Object.entries(p.files)){const b=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Audio',name));assert.equal(createHash('sha256').update(b).digest('hex'),v.sha256);assert.equal(b.readUInt32LE(24),22050);assert.equal(b.readUInt16LE(22),1);assert.equal((b.length-44)/2,v.frames);}
});
test('compiled C# and JS accepted-shot cursor agree across join, pause, mute, gap and seeks',()=>{
  const rows=JSON.parse(execFileSync('dotnet',[process.env.VR_COMMAND_CHECKS_DLL||path.join(root,'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'),'--combat-audio-vectors'],{encoding:'utf8',windowsHide:true}));const c=new CombatAudioCursor();
  for(const r of rows)assert.equal(c.advance(r.tick,r.phase,r.sequence,r.tickPlusOne,r.continuous),r.sound);
});
test('rapid snapshots do not duplicate a cue and detached old clocks cannot catch up',()=>{
  const c=new CombatAudioCursor();assert.equal(c.advance(0,'Preparing',0,0,true),false);assert.equal(c.advance(0,'Running',1,1,true),true);
  for(let i=0;i<20;i++)assert.equal(c.advance(0,'Running',1,1,true),false);
  assert.equal(c.advance(8,'Running',2,1,true),false);assert.throws(()=>c.advance(0,'Running',1,2,true));
});
test('new audio policy requires fire witnesses while old files remain silent',async()=>{
  const sample=JSON.parse(await readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));const data=playerFireFixture(sample);data.combatAudioVersion=1;validateRecording(data);
  const bad=structuredClone(data);bad.playerFireVersion=0;assert.throws(()=>validateRecording(bad),/戰鬥音效/);data.combatAudioVersion=2;assert.throws(()=>validateRecording(data),/音效版本/);
  assert.equal(sample.combatAudioVersion,undefined);validateRecording(sample);
});
