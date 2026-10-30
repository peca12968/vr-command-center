import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {WEAPON_ACTIONS} from '../../src/VrCommand.Api/wwwroot/console/weapon-actions-data.js';
import {SERVICE_RIFLE} from '../../src/VrCommand.Api/wwwroot/console/service-rifle-data.js';
import {weaponPose,weaponActionsFactory,applyWeaponPose} from '../../src/VrCommand.Api/wwwroot/console/weapon-actions.js';
import {validateRecording} from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
import {weaponFixture} from './weapon-actions-fixture.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const sample=JSON.parse(await readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));
test('split rifle is frozen, identical to Unity, and preserves every old rifle triangle at its home pose',async()=>{
  const bytes=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Resources/VrCommand/weapon-actions-v1.json'));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),'517c3616ec12dad34f25cc50f5309eae1033b62bcbbb636b4a3f378a5c12cab3');assert.deepEqual(JSON.parse(bytes),WEAPON_ACTIONS);
  const triangles=(part,pivot=[0,0,0])=>{const rows=[];for(let i=0;i<part.triangles.length;i+=3)rows.push(part.triangles.slice(i,i+3).map(index=>[...part.positions.slice(index*3,index*3+3).map((v,k)=>Number((v+pivot[k]).toFixed(7))),...part.normals.slice(index*3,index*3+3),...part.colors.slice(index*4,index*4+4)]).flat().join(','));return rows;};
  assert.deepEqual([...triangles(WEAPON_ACTIONS.parts[0]),...triangles(WEAPON_ACTIONS.parts[1],WEAPON_ACTIONS.magazinePivot)].sort(),triangles(SERVICE_RIFLE.mesh).sort());
});
test('all thirty reload ticks and tracked-hand policy agree with compiled C#',()=>{
  const rows=JSON.parse(execFileSync('dotnet',[process.env.VR_COMMAND_CHECKS_DLL||path.join(root,'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'),'--weapon-vectors'],{encoding:'utf8',windowsHide:true}));
  for(const r of rows){const p=weaponPose(r.tick,r.health,r.connected,r.simulated,r.reloading,r.until);for(const key of ['offset','left'])r[key].forEach((v,i)=>assert.ok(Math.abs(p[key][i]-v)<.00001));for(const key of ['roll','leftRoll'])assert.ok(Math.abs(p[key]-r[key])<.0001);assert.equal(p.visible,r.visible);assert.equal(p.hands,r.hands);}
});
test('actual child transforms seek deterministically without moving the accepted muzzle root',()=>{
  const pool=weaponActionsFactory(),a=pool.create(),b=pool.create(),player={hasWeaponPresentation:true,health:100,connected:true,reloading:true,reloadUntilTick:30,rig:{kind:'Simulated'}};
  a.position.set(2,1.5,3);a.rotation.set(.2,.3,.4);const rootPose=[...a.position.toArray(),...a.quaternion.toArray()];
  applyWeaponPose(a,player,8);const rig=a.userData.weaponActions,saved=[...rig.magazine.position.toArray(),...rig.left.position.toArray(),rig.magazine.rotation.z];assert.ok(rig.magazine.position.y<-.2);assert.equal(rig.left.visible,true);
  applyWeaponPose(a,player,14);assert.equal(rig.magazine.visible,false);applyWeaponPose(a,player,8);assert.deepEqual([...rig.magazine.position.toArray(),...rig.left.position.toArray(),rig.magazine.rotation.z],saved);assert.deepEqual([...a.position.toArray(),...a.quaternion.toArray()],rootPose);
  player.rig.kind='Tracked';applyWeaponPose(a,player,8);assert.equal(rig.left.visible,false);assert.equal(rig.right.visible,false);
  assert.equal(a.geometry,b.geometry);assert.notEqual(a.material,b.material);assert.equal(pool.triangles,264);assert.equal(pool.handTriangles,240);
  let releases=0;a.geometry.addEventListener('dispose',()=>releases++);a.material.dispose();assert.equal(releases,0);pool.dispose();pool.dispose();assert.equal(releases,1);assert.throws(()=>pool.create());b.material.dispose();
});
test('new recordings require witnessed reload clocks while old recordings keep the old static rifle',()=>{
  assert.doesNotThrow(()=>validateRecording(sample));const data=weaponFixture(sample);assert.doesNotThrow(()=>validateRecording(data));
  const change=structuredClone(data);change.frames.find(f=>f.tick===28).players[0].reloadUntilTick++;assert.throws(()=>validateRecording(change),/時鐘/);
  const missing=structuredClone(data);delete missing.frames[0].players[0].hasWeaponPresentation;assert.throws(()=>validateRecording(missing),/動作/);
  data.weaponPresentationVersion=2;assert.throws(()=>validateRecording(data),/版本/);
});
test('invalid geometry and phantom or expired reload clocks fail before rendering',()=>{
  for(const mutate of [d=>d.origin='grip',d=>d.parts[1].triangles[0]=99999,d=>d.parts[2].normals[0]=NaN,d=>d.magazinePivot[0]=Infinity]){const data=structuredClone(WEAPON_ACTIONS);mutate(data);assert.throws(()=>weaponActionsFactory(data));}
  assert.throws(()=>weaponPose(31,100,true,true,true,30));assert.throws(()=>weaponPose(0,100,true,true,false,30));assert.equal(weaponPose(50,0,true,true,true,30).hands,false);
});
