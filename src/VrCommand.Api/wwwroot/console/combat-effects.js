import * as THREE from './vendor/three/three.module.js';
import {COMBAT_EFFECTS} from './combat-effects-data.js';
import {armedOpponentFactory,poseArmedOpponent} from './armed-combatants.js';
import {opponentGeometry} from './combatants.js';

export const COMBAT_EFFECT_ASSETS='combat-effects-v1';
const zero=p=>p&&p.x===0&&p.y===0&&p.z===0;
export function enemyFirePose(enemy,tick){
  const seq=enemy.fireSequence,tp=enemy.fireTickPlusOne,o=enemy.fireOrigin,d=enemy.fireDirection;
  if(enemy.hasFireState!==true||!Number.isSafeInteger(tick)||tick<0||tick>1728000||!Number.isSafeInteger(seq)||seq<0||!Number.isSafeInteger(tp)||tp<0||tp>tick+1
    ||!Number.isInteger(enemy.health)||enemy.health<0||enemy.health>100||[o,d].some(p=>!p||![p.x,p.y,p.z].every(Number.isFinite))
    ||(seq===0?tp!==0||!zero(o)||!zero(d):tp===0||Math.abs(Math.hypot(d.x,d.y,d.z)-1)>.01))throw new Error('Invalid saved enemy fire state');
  if(enemy.health===0||seq===0)return{flash:false,recoil:0};
  const age=tick-(tp-1);return{flash:age<3,recoil:[.012,.018,.010,.004,.001][age]??0};
}
export function firingOpponentFactory(data=COMBAT_EFFECTS){
  if(data?.assetSet!==COMBAT_EFFECT_ASSETS||data.units!=='metres'||data.origin!=='accepted-enemy-shot'||data.forward!=='+Z'||data.enemyFireVersion!==1||data.mesh?.kind!=='EnemyMuzzleFlash')throw new Error('Invalid enemy fire metadata');
  const bodies=armedOpponentFactory();let geometry;
  try{geometry=opponentGeometry(data.mesh);}catch(e){bodies.dispose();throw e;}
  let disposed=false;
  return{triangles:bodies.triangles+geometry.index.count/3,create(){
    if(disposed)throw new Error('Enemy fire pool is disposed');
    const actor=bodies.create(),sidearm=actor.gun,anchor=new THREE.Group();anchor.position.copy(sidearm.position);
    actor.group.remove(sidearm);actor.group.add(anchor);sidearm.position.set(0,0,0);anchor.add(sidearm);
    anchor.add(actor.leftHand,actor.rightHand);actor.gun=anchor;actor.sidearm=sidearm;
    actor.flash=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({vertexColors:true,toneMapped:false}));actor.flash.visible=false;actor.group.add(actor.flash);actor.fire=true;return actor;
  },dispose(){if(!disposed){disposed=true;bodies.dispose();geometry.dispose();}}};
}
export function poseFiringOpponent(actor,enemy,tick){
  poseArmedOpponent(actor,enemy,tick);const pose=enemyFirePose(enemy,tick);actor.sidearm.position.z=-pose.recoil;actor.flash.visible=pose.flash;
  actor.group.updateWorldMatrix(true,false);
  if(enemy.fireSequence>0){
    actor.flash.position.copy(actor.group.worldToLocal(new THREE.Vector3(enemy.fireOrigin.x,enemy.fireOrigin.y,enemy.fireOrigin.z)));
    const worldRotation=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1),new THREE.Vector3(enemy.fireDirection.x,enemy.fireDirection.y,enemy.fireDirection.z).normalize());
    actor.flash.quaternion.copy(actor.group.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(worldRotation));
  }
}
