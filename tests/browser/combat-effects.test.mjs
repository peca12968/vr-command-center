import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from '../../src/VrCommand.Api/wwwroot/console/vendor/three/three.module.js';
import {COMBAT_EFFECTS} from '../../src/VrCommand.Api/wwwroot/console/combat-effects-data.js';
import {enemyFirePose,firingOpponentFactory,poseFiringOpponent} from '../../src/VrCommand.Api/wwwroot/console/combat-effects.js';
import {opponentGeometry} from '../../src/VrCommand.Api/wwwroot/console/combatants.js';
import {validateRecording} from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
import {fireFixture} from './combat-effects-fixture.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
test('muzzle pulse equals the fixed Unity resource and has outward closed triangles',async()=>{
  const bytes=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Resources/VrCommand/combat-effects-v1.json'));assert.equal(createHash('sha256').update(bytes).digest('hex'),'b8fe83d66781c2f65816d6873cc08ba01314418d42777a55e9eea2d1ee34a9bb');assert.deepEqual(JSON.parse(bytes),COMBAT_EFFECTS);
  const g=opponentGeometry(COMBAT_EFFECTS.mesh),p=g.getAttribute('position'),n=g.getAttribute('normal'),t=g.index;
  try{assert.equal(t.count/3,32);for(let i=0;i<t.count;i+=3){const a=new THREE.Vector3().fromBufferAttribute(p,t.getX(i)),b=new THREE.Vector3().fromBufferAttribute(p,t.getX(i+1)),c=new THREE.Vector3().fromBufferAttribute(p,t.getX(i+2));assert.ok(b.sub(a).cross(c.sub(a)).dot(new THREE.Vector3().fromBufferAttribute(n,t.getX(i)))>.0000001);}}
  finally{g.dispose();}
});
test('saved fire clock agrees with compiled C# through flash, recoil, death and seek boundaries',()=>{
  const rows=JSON.parse(execFileSync('dotnet',[process.env.VR_COMMAND_CHECKS_DLL||path.join(root,'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'),'--enemy-fire-vectors'],{encoding:'utf8',windowsHide:true}));
  for(const row of rows){const p=enemyFirePose({...row,hasFireState:true},row.tick);assert.equal(p.flash,row.flash);assert.ok(Math.abs(p.recoil-row.recoil)<1e-8);}
  const e={health:100,hasFireState:true,fireSequence:0,fireTickPlusOne:0,fireOrigin:{x:0,y:0,z:0},fireDirection:{x:0,y:0,z:0}};assert.deepEqual(enemyFirePose(e,0),{flash:false,recoil:0});assert.throws(()=>enemyFirePose({...e,fireOrigin:{x:1e-30,y:0,z:0}},0));
});
test('actual scene graph keeps the flash on the historical ray and recoils only one mesh',()=>{
  const pool=firingOpponentFactory(),a=pool.create(),b=pool.create();assert.equal(pool.triangles,760);
  const e={hasPresentation:true,forward:{x:1,y:0,z:0},walking:true,health:80,hasFireState:true,fireSequence:5,fireTickPlusOne:11,fireOrigin:{x:-1,y:1.4,z:2},fireDirection:{x:0,y:0,z:-1}};
  try{a.group.position.set(0,0,3);poseFiringOpponent(a,e,10);a.group.updateMatrixWorld(true);
    assert.equal(a.flash.geometry,b.flash.geometry);assert.ok(a.flash.material.isMeshBasicMaterial);assert.equal(a.flash.visible,true);assert.equal(a.sidearm.position.z,-.012);
    assert.ok(a.flash.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(-1,1.4,2))<1e-8);assert.ok(a.gun.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(0,1.4,3))<1e-8);
    assert.deepEqual(a.leftHand.position.toArray(),[0,-.085,-.035]);a.group.position.x=.1;poseFiringOpponent(a,{...e,forward:{x:0,y:0,z:1}},11);a.group.updateMatrixWorld(true);assert.ok(a.flash.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(-1,1.4,2))<1e-8);
    poseFiringOpponent(a,e,18);assert.equal(a.flash.visible,false);assert.equal(Math.abs(a.sidearm.position.z),0);poseFiringOpponent(a,e,10);assert.equal(a.flash.visible,true);assert.equal(a.sidearm.position.z,-.012);
  }finally{pool.dispose();}assert.throws(()=>pool.create());
});
test('replay imports require the exact accepted fire sequence, tick, origin and direction',async()=>{
  const sample=JSON.parse(await readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8')),data=fireFixture(sample);validateRecording(data);
  const index=data.frames.findIndex(f=>f.enemies.some(e=>e.fireSequence>0));assert.ok(index>=0);
  for(const mutate of [e=>e.fireSequence++,e=>e.fireTickPlusOne++,e=>e.fireOrigin.x+=.01,e=>e.fireDirection={x:1,y:0,z:0},e=>e.hasFireState=false]){const bad=structuredClone(data);mutate(bad.frames[index].enemies.find(e=>e.fireSequence>0));assert.throws(()=>validateRecording(bad),/射擊/);}
  const legacy=structuredClone(data);legacy.assetSet='armed-combatants-v1';legacy.enemyFireVersion=0;assert.throws(()=>validateRecording(legacy),/舊敵軍/);
});
