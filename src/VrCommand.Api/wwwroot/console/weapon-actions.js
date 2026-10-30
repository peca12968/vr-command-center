import * as THREE from './vendor/three/three.module.js';
import { WEAPON_ACTIONS } from './weapon-actions-data.js';
import { opponentGeometry } from './combatants.js';

export const WEAPON_ACTION_ASSETS='weapon-actions-v1';
export const RIGHT_GRIP=[0,-.15,-.535],LEFT_GRIP=[0,0,-.22];
const magGrip=[0,-.17,-.4025],lowered=[-.16,-.32,0];
const mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
export function weaponPose(tick,health,connected,simulated,reloading,until) {
  if(!Number.isSafeInteger(tick)||tick<0||tick>1728000||!Number.isInteger(health)||health<0||health>100
    || ![connected,simulated,reloading].every(v=>typeof v==='boolean') || !Number.isSafeInteger(until)||until<0||until>1728030
    || (reloading?until<30||until-30>tick||(health>0&&until<=tick):until!==0))throw new Error('Invalid saved weapon presentation');
  const hands=simulated&&connected&&health>0;
  if(!reloading||!connected||health===0)return {offset:[0,0,0],left:LEFT_GRIP,roll:0,leftRoll:0,visible:true,hands};
  const elapsed=tick-(until-30);let offset,left,roll,leftRoll;
  if(elapsed<5){offset=[0,0,0];roll=0;left=mix(LEFT_GRIP,magGrip,elapsed/5);leftRoll=0;}
  else if(elapsed<11){const t=(elapsed-5)/6;offset=lowered.map(v=>v*t);roll=-20*t;left=magGrip.map((v,i)=>v+offset[i]);leftRoll=roll;}
  else if(elapsed<18){offset=lowered;roll=-20;left=magGrip.map((v,i)=>v+offset[i]);leftRoll=roll;}
  else if(elapsed<25){const t=(25-elapsed)/7;offset=lowered.map(v=>v*t);roll=-20*t;left=magGrip.map((v,i)=>v+offset[i]);leftRoll=roll;}
  else{offset=[0,0,0];roll=0;left=mix(magGrip,LEFT_GRIP,(elapsed-25)/5);leftRoll=0;}
  return {offset,left,roll,leftRoll,visible:elapsed<12||elapsed>=18,hands};
}
export function weaponActionsFactory(data=WEAPON_ACTIONS) {
  if(data?.assetSet!==WEAPON_ACTION_ASSETS||data.units!=='metres'||data.origin!=='muzzle'||data.forward!=='+Z'||data.weaponPresentationVersion!==1
    ||data.parts?.length!==4||data.parts.some((p,i)=>p?.kind!==['Body','Magazine','RightGlove','LeftGlove'][i])
    ||data.magazinePivot?.length!==3||data.magazinePivot.some(v=>!Number.isFinite(v)||Math.abs(v)>1))throw new Error('Invalid weapon action metadata');
  const geometries=[];let disposed=false;
  try{for(const part of data.parts){const g=opponentGeometry(part);g.userData.serviceRifleShared=true;geometries.push(g);}}
  catch(error){for(const g of geometries)g.dispose();throw error;}
  return {triangles:264,handTriangles:geometries[2].index.count/3+geometries[3].index.count/3,
    create(){if(disposed)throw new Error('Weapon pool is disposed');const material=new THREE.MeshStandardMaterial({color:0xffffff,roughness:.8,vertexColors:true});
      const root=new THREE.Mesh(geometries[0],material),parts=geometries.slice(1).map(g=>new THREE.Mesh(g,material));root.add(...parts);
      parts[0].position.fromArray(data.magazinePivot);parts[1].visible=parts[2].visible=false;
      root.userData.weaponActions={magazine:parts[0],right:parts[1],left:parts[2],pivot:data.magazinePivot};return root;},
    dispose(){if(!disposed){disposed=true;for(const g of geometries)g.dispose();}}};
}
export function applyWeaponPose(mesh,player,tick) {
  if(!player.hasWeaponPresentation)throw new Error('Missing saved weapon action');
  const p=weaponPose(tick,player.health,player.connected,player.rig?.kind==='Simulated',player.reloading,player.reloadUntilTick),v=mesh.userData.weaponActions;
  v.magazine.position.fromArray(v.pivot.map((x,i)=>x+p.offset[i]));v.magazine.rotation.z=p.roll*Math.PI/180;v.magazine.visible=p.visible;
  v.right.position.fromArray(RIGHT_GRIP);v.left.position.fromArray(p.left);v.left.rotation.z=p.leftRoll*Math.PI/180;v.left.visible=v.right.visible=p.hands;
}
