import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from '../../src/VrCommand.Api/wwwroot/console/vendor/three/three.module.js';
import { COMBATANTS } from '../../src/VrCommand.Api/wwwroot/console/combatants-data.js';
import { enemyPose,opponentGeometry,opponentFactory,poseOpponent } from '../../src/VrCommand.Api/wwwroot/console/combatants.js';
import { validateRecording } from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const sample=JSON.parse(await readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));
test('original opponent mesh matches the frozen Unity resource and has outward finite faces',async()=>{
  const bytes=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Resources/VrCommand/combatants-v1.json'));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),'39fa5e9baceec0eb71ce6a4664fc4460e7b0f212f2c58b75c7b4d75b3565fdf2');assert.deepEqual(JSON.parse(bytes),COMBATANTS);
  let count=0;
  for(const part of COMBATANTS.parts){const g=opponentGeometry(part),p=g.getAttribute('position'),n=g.getAttribute('normal'),t=g.index;
    try{count+=t.count/3*(part.kind==='Leg'?2:1);for(let i=0;i<t.count;i+=3){const a=new THREE.Vector3().fromBufferAttribute(p,t.getX(i)),b=new THREE.Vector3().fromBufferAttribute(p,t.getX(i+1)),c=new THREE.Vector3().fromBufferAttribute(p,t.getX(i+2));
      assert.ok(b.sub(a).cross(c.sub(a)).dot(new THREE.Vector3().fromBufferAttribute(n,t.getX(i)))>.0000001);}}
    finally{g.dispose();}}
  assert.equal(count,404);
});
test('browser poses agree with compiled shared C# at every gait and clock boundary',()=>{
  const rows=JSON.parse(execFileSync('dotnet',[process.env.VR_COMMAND_CHECKS_DLL||path.join(root,'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'),'--enemy-vectors'],{encoding:'utf8',windowsHide:true}));
  for(const row of rows){const p=enemyPose(row.forward,row.walking,row.tick);for(const key of ['yaw','pitch','stride'])assert.ok(Math.abs(p[key]-row[key])<.0001);}
});
test('shared meshes preserve independent fading, opposite actual leg transforms, and direct seeks',()=>{
  const pool=opponentFactory(),a=pool.create(),b=pool.create();let released=0;
  assert.equal(pool.triangles,404);assert.equal(a.body.geometry,b.body.geometry);assert.equal(a.leftLeg.geometry,a.rightLeg.geometry);assert.equal(a.head.material,a.body.material);assert.notEqual(a.body.material,b.body.material);
  a.body.material.opacity=.18;assert.equal(b.head.material.opacity,1);
  const npc={hasPresentation:true,forward:{x:1,y:0,z:0},walking:true};poseOpponent(a,npc,3);
  const saved=[a.group.rotation.y,a.head.rotation.x,a.leftLeg.rotation.x,a.rightLeg.rotation.x];assert.ok(Math.abs(saved[2]-Math.PI/10)<1e-10);assert.equal(saved[2],-saved[3]);
  poseOpponent(a,npc,9);poseOpponent(a,npc,3);assert.deepEqual([a.group.rotation.y,a.head.rotation.x,a.leftLeg.rotation.x,a.rightLeg.rotation.x],saved);
  a.body.geometry.addEventListener('dispose',()=>released++);a.body.material.dispose();assert.equal(released,0);pool.dispose();pool.dispose();assert.equal(released,1);assert.throws(()=>pool.create());b.body.material.dispose();
});
test('invalid enemy rigs, normals, indices and time never reach a renderer',()=>{
  for(const mutate of [d=>d.origin='muzzle',d=>d.headPivot[0]=NaN,d=>d.parts[0].positions[0]=Infinity,d=>d.parts[1].normals[0]=99,d=>d.parts[2].triangles[0]=999999]){
    const data=structuredClone(COMBATANTS);mutate(data);assert.throws(()=>opponentFactory(data));}
  for(const [v,w,t] of [[{x:0,y:0,z:0},true,0],[{x:0,y:0,z:1},true,1728001],[{x:0,y:0,z:1},1,0]])assert.throws(()=>enemyPose(v,w,t));
});
test('old exports stay unanimated and new combatants explicitly require complete saved poses',()=>{
  const old=structuredClone(sample);assert.doesNotThrow(()=>validateRecording(old));
  const current=structuredClone(sample);current.assetSet='combatants-v1';assert.throws(()=>validateRecording(current),/姿態版本/);
  current.enemyPresentationVersion=1;for(const frame of current.frames)for(const e of frame.enemies)Object.assign(e,{hasPresentation:true,forward:{x:0,y:0,z:-1},walking:false});
  assert.doesNotThrow(()=>validateRecording(current));current.frames[0].enemies[0].forward={x:0,y:0,z:1.0105};assert.throws(()=>validateRecording(current),/姿態/);
  delete current.frames[0].enemies[0].forward;assert.throws(()=>validateRecording(current),/姿態/);
  current.enemyPresentationVersion=2;assert.throws(()=>validateRecording(current),/姿態版本/);
});
