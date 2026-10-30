import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from '../../src/VrCommand.Api/wwwroot/console/vendor/three/three.module.js';
import {ARMED_COMBATANTS} from '../../src/VrCommand.Api/wwwroot/console/armed-combatants-data.js';
import {armedEnemyPose,armedOpponentFactory,poseArmedOpponent,solveArm} from '../../src/VrCommand.Api/wwwroot/console/armed-combatants.js';
import {opponentGeometry} from '../../src/VrCommand.Api/wwwroot/console/combatants.js';
import {weaponFixture} from './weapon-actions-fixture.mjs';
import {validateRecording} from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
test('armed NPC geometry equals its frozen Unity resource and all faces point outwards',async()=>{
  const bytes=await readFile(path.join(root,'clients/unity/Assets/VrCommand/Resources/VrCommand/armed-combatants-v1.json'));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),'cc011e951163d4b846c4e2c217592251906844c0dfcee2f795618c8c1c388102');assert.deepEqual(JSON.parse(bytes),ARMED_COMBATANTS);
  for(const part of ARMED_COMBATANTS.parts){const g=opponentGeometry(part),p=g.getAttribute('position'),n=g.getAttribute('normal'),t=g.index;
    try{for(let i=0;i<t.count;i+=3){const a=new THREE.Vector3().fromBufferAttribute(p,t.getX(i)),b=new THREE.Vector3().fromBufferAttribute(p,t.getX(i+1)),c=new THREE.Vector3().fromBufferAttribute(p,t.getX(i+2));
      assert.ok(b.sub(a).cross(c.sub(a)).dot(new THREE.Vector3().fromBufferAttribute(n,t.getX(i)))>.0000001);}}finally{g.dispose();}}
});
test('compiled C# and browser agree on both two-bone arms across yaw, pitch and tick boundaries',()=>{
  const rows=JSON.parse(execFileSync('dotnet',[process.env.VR_COMMAND_CHECKS_DLL||path.join(root,'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'),'--armed-enemy-vectors'],{encoding:'utf8',windowsHide:true}));
  for(const row of rows){const p=armedEnemyPose(row.forward,true,row.tick);assert.ok(Math.abs(p.gunPitch-row.gunPitch)<.0002);
    for(const side of ['left','right'])for(const joint of ['shoulder','elbow','wrist'])for(const [i,k] of ['x','y','z'].entries())assert.ok(Math.abs(p[side][joint][i]-row[side][joint][k])<.00001);
    for(const side of ['left','right']){assert.ok(Math.abs(new THREE.Vector3(...p[side].shoulder).distanceTo(new THREE.Vector3(...p[side].elbow))-.22)<1e-8);assert.ok(Math.abs(new THREE.Vector3(...p[side].elbow).distanceTo(new THREE.Vector3(...p[side].wrist))-.25)<1e-8);}}
  const near={x:0,y:.501,z:.87},p=armedEnemyPose(near,false,0);assert.ok(Math.abs(p.gunPitch+Math.asin(near.y/Math.hypot(near.y,near.z))*180/Math.PI)<1e-9);
  assert.throws(()=>solveArm([0,0,0],[0,2,0],[0,0,0]));assert.ok(solveArm([0,0,0],[0,.3,0],[0,.1,0]).elbow.every(Number.isFinite));
});
test('actual scene objects align gun to authority, attach gloves and restore arms on direct seek',()=>{
  const pool=armedOpponentFactory(),a=pool.create(),b=pool.create();assert.equal(pool.triangles,728);
  try{assert.equal(a.leftLeg.geometry,a.rightLeg.geometry);assert.equal(a.leftUpper.geometry,b.rightUpper.geometry);assert.notEqual(a.gun.material,b.gun.material);assert.equal(a.gun.material,a.body.material);
    const f=new THREE.Vector3(1,.6,-1).normalize(),enemy={hasPresentation:true,forward:{x:f.x,y:f.y,z:f.z},walking:true};a.group.position.set(28,0,3);poseArmedOpponent(a,enemy,3);a.group.updateMatrixWorld(true);
    const muzzle=a.gun.getWorldPosition(new THREE.Vector3()),forward=new THREE.Vector3(0,0,1).applyQuaternion(a.gun.getWorldQuaternion(new THREE.Quaternion()));
    assert.ok(muzzle.distanceTo(new THREE.Vector3(28,1.4,3))<1e-8);assert.ok(forward.distanceTo(f)<1e-8);
    const elbow=a.leftLower.getWorldPosition(new THREE.Vector3());poseArmedOpponent(a,{...enemy,forward:{x:0,y:0,z:1}},9);poseArmedOpponent(a,enemy,3);a.group.updateMatrixWorld(true);assert.ok(elbow.distanceTo(a.leftLower.getWorldPosition(new THREE.Vector3()))<1e-8);
    for(const side of ['left','right']){const wrist=a[side+'Lower'].localToWorld(new THREE.Vector3(0,1,0)),grip=side==='left'?[-.07,-.085,-.035]:[.07,-.11,-.075];assert.ok(wrist.distanceTo(a.gun.localToWorld(new THREE.Vector3(...grip)))<1e-8);}
    assert.equal(a.leftHand.parent,a.gun);assert.throws(()=>armedOpponentFactory({...ARMED_COMBATANTS,muzzle:[0,1.4,.1]}));
  }finally{pool.dispose();}assert.throws(()=>pool.create());
});
test('new armed replay requires both saved contracts while retained profiles remain valid',async()=>{
  const sample=JSON.parse(await readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8')),d=weaponFixture(sample);validateRecording(d);
  d.assetSet='armed-combatants-v1';validateRecording(d);d.enemyPresentationVersion=0;assert.throws(()=>validateRecording(d),/敵軍版本/);d.enemyPresentationVersion=1;d.weaponPresentationVersion=0;assert.throws(()=>validateRecording(d),/敵軍版本/);
});
