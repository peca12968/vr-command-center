import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from '../../src/VrCommand.Api/wwwroot/console/vendor/three/three.module.js';
import {PLAYER_FIRE} from '../../src/VrCommand.Api/wwwroot/console/player-fire-data.js';
import {firingRifleFactory,playerFirePose,applyPlayerFire} from '../../src/VrCommand.Api/wwwroot/console/player-fire.js';
import {applyWeaponPose} from '../../src/VrCommand.Api/wwwroot/console/weapon-actions.js';
import {validateRecording} from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
import {playerFireFixture} from './player-fire-fixture.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
test('player profile equals its frozen Unity composition without rewriting source geometry',async()=>{
  const bytes=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Resources/VrCommand/player-fire-v1.json'));assert.equal(createHash('sha256').update(bytes).digest('hex'),'187c7df5346419edadafa1cc74a04db0763dda268650e066dbbcaf8304e60ff0');assert.deepEqual(JSON.parse(bytes),PLAYER_FIRE);
  assert.equal(PLAYER_FIRE.pulseScale,1.2);assert.equal(PLAYER_FIRE.flashTicks,3);assert.deepEqual(PLAYER_FIRE.recoilMetres,[.014,.022,.012,.004]);
});
test('player clock, connection, death and reload policy agree with compiled C#',()=>{
  const rows=JSON.parse(execFileSync('dotnet',[process.env.VR_COMMAND_CHECKS_DLL||path.join(root,'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'),'--player-fire-vectors'],{encoding:'utf8',windowsHide:true}));
  for(const row of rows){const p=playerFirePose({...row,hasFireState:true},row.tick);assert.equal(p.flash,row.flash);assert.ok(Math.abs(p.recoil-row.recoil)<1e-8);}
});
test('actual rifle graph recoils body and magazine, preserves grip/root and holds a historical world flash',()=>{
  const pool=firingRifleFactory(),mesh=pool.create(),parent=new THREE.Group();parent.add(mesh,mesh.userData.playerFire.flash);parent.position.set(0,0,3);mesh.position.set(.18,1.53,.9);
  const p={health:100,connected:true,reloading:false,hasWeaponPresentation:true,reloadUntilTick:0,rig:{kind:'Simulated'},hasFireState:true,fireSequence:1,fireTickPlusOne:1,fireOrigin:{x:0,y:1.5,z:2},fireDirection:{x:0,y:0,z:-1}};
  try{const position=mesh.position.toArray();applyWeaponPose(mesh,p,0);applyPlayerFire(mesh,p,0);parent.updateMatrixWorld(true);const v=mesh.userData.playerFire;
    assert.deepEqual(mesh.position.toArray(),position);assert.equal(v.recoil.position.z,-.014);assert.equal(mesh.userData.weaponActions.magazine.parent,v.recoil);assert.equal(v.flash.visible,true);
    assert.deepEqual(mesh.userData.weaponActions.right.position.toArray(),[0,-.15,-.535]);assert.ok(v.flash.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(0,1.5,2))<1e-8);
    parent.position.x=2;mesh.rotation.y=1;applyPlayerFire(mesh,p,1);parent.updateMatrixWorld(true);assert.ok(v.flash.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(0,1.5,2))<1e-8);
    applyPlayerFire(mesh,p,8);assert.equal(v.flash.visible,false);applyPlayerFire(mesh,p,0);assert.equal(v.flash.visible,true);
    applyWeaponPose(mesh,{...p,reloading:true,reloadUntilTick:30},8);applyPlayerFire(mesh,{...p,reloading:true,reloadUntilTick:30},8);assert.equal(Math.abs(v.recoil.position.z),0);assert.ok(mesh.userData.weaponActions.magazine.position.y<-.2);
    assert.throws(()=>firingRifleFactory({...PLAYER_FIRE,pulseScale:2}));
  }finally{pool.dispose();}assert.throws(()=>pool.create());
});
test('player replay requires the exact accepted sequence, tick and ray and preserves old readers',async()=>{
  const sample=JSON.parse(await readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8')),data=playerFireFixture(sample);validateRecording(data);
  const i=data.frames.findIndex(f=>f.players.some(p=>p.fireSequence>0));assert.ok(i>=0);
  for(const change of [p=>p.fireSequence++,p=>p.fireTickPlusOne++,p=>p.fireOrigin.x+=.001,p=>p.fireDirection={x:1,y:0,z:0},p=>p.hasFireState=false]){
    const d=structuredClone(data);change(d.frames[i].players.find(p=>p.fireSequence>0));assert.throws(()=>validateRecording(d),/玩家射擊/);}
  const old=structuredClone(data);old.assetSet='combat-effects-v1';old.playerFireVersion=0;assert.throws(()=>validateRecording(old),/舊玩家/);
});
