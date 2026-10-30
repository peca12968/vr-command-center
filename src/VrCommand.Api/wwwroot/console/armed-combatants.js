import * as THREE from './vendor/three/three.module.js';
import { ARMED_COMBATANTS } from './armed-combatants-data.js';
import { enemyPose, opponentGeometry, poseOpponent } from './combatants.js';

export const ARMED_ASSETS='armed-combatants-v1';
const add=(a,b)=>a.map((v,i)=>v+b[i]), sub=(a,b)=>a.map((v,i)=>v-b[i]), mul=(a,k)=>a.map(v=>v*k), dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0), norm=a=>Math.hypot(...a);
export const ENEMY_MUZZLE=[0,1.4,0], LEFT_GRIP=[0,-.085,-.035], RIGHT_GRIP=[0,-.11,-.075];
export function pitchPoint(p,degrees){const a=degrees*Math.PI/180,s=Math.sin(a),c=Math.cos(a);return[p[0],c*p[1]-s*p[2],s*p[1]+c*p[2]];}
export function solveArm(shoulder,wrist,hint,upper=.22,lower=.25){
  if([shoulder,wrist,hint].some(p=>!Array.isArray(p)||p.length!==3||!p.every(Number.isFinite))||![upper,lower].every(v=>Number.isFinite(v)&&v>0))throw new Error('Invalid cosmetic arm');
  const delta=sub(wrist,shoulder),distance=norm(delta);
  if(distance<.00001||distance>upper+lower||distance<Math.abs(upper-lower))throw new Error('Unreachable cosmetic arm');
  const axis=mul(delta,1/distance);let bend=sub(hint,shoulder);bend=sub(bend,mul(axis,dot(bend,axis)));
  if(norm(bend)<.00001){const fallback=Math.abs(axis[1])<.9?[0,1,0]:[1,0,0];bend=sub(fallback,mul(axis,dot(fallback,axis)));}
  const along=(upper*upper-lower*lower+distance*distance)/(2*distance),height=Math.sqrt(Math.max(0,upper*upper-along*along));
  return{shoulder,elbow:add(add(shoulder,mul(axis,along)),mul(bend,height/norm(bend))),wrist};
}
export function armedEnemyPose(forward,walking,tick){
  const body=enemyPose(forward,walking,tick),gunPitch=-Math.asin(Math.max(-1,Math.min(1,forward.y/Math.hypot(forward.x,forward.y,forward.z))))*180/Math.PI;
  const arm=left=>{const side=left?-1:1,grip=left?LEFT_GRIP:RIGHT_GRIP;
    return solveArm([side*.215,1.37,-.235],add(ENEMY_MUZZLE,pitchPoint(add(grip,[side*.07,0,0]),gunPitch)),[side*.36,1.1,.04]);};
  return{body,gunPitch,left:arm(true),right:arm(false)};
}
export function armedOpponentFactory(data=ARMED_COMBATANTS){
  const kinds=['Torso','Head','Leg','UpperArm','LowerArm','Sidearm','RightGlove','LeftGlove'];
  if(data?.assetSet!==ARMED_ASSETS||data.units!=='metres'||data.origin!=='feet'||data.forward!=='+Z'||data.enemyPresentationVersion!==1
    ||data.parts?.length!==8||data.parts.some((p,i)=>p?.kind!==kinds[i])
    ||[['headPivot',[0,1.51,-.26]],['leftHip',[-.11,.82,-.08]],['rightHip',[.11,.82,-.08]],['muzzle',ENEMY_MUZZLE],['leftGrip',LEFT_GRIP],['rightGrip',RIGHT_GRIP]].some(([k,p])=>
      !Array.isArray(data[k])||data[k].length!==3||data[k].some((v,i)=>!Number.isFinite(v)||Math.abs(v-p[i])>.000001)))throw new Error('Invalid armed opponent metadata');
  const geometries=[];let disposed=false;
  try{for(const part of data.parts)geometries.push(opponentGeometry(part));}catch(error){for(const g of geometries)g.dispose();throw error;}
  const part=(parent,index,position,material)=>{const mesh=new THREE.Mesh(geometries[index],material);mesh.position.fromArray(position);parent.add(mesh);return mesh;};
  return{triangles:geometries.reduce((sum,g,i)=>sum+g.index.count/3*([2,3,4].includes(i)?2:1),0),create(){
    if(disposed)throw new Error('Armed pool is disposed');
    const group=new THREE.Group(),material=new THREE.MeshStandardMaterial({color:0xffffff,roughness:.85,vertexColors:true});
    const body=part(group,0,[0,0,0],material),head=part(group,1,data.headPivot,material),leftLeg=part(group,2,data.leftHip,material),rightLeg=part(group,2,data.rightHip,material),gun=part(group,5,data.muzzle,material);
    const actor={group,body,head,leftLeg,rightLeg,gun,leftUpper:part(group,3,[0,0,0],material),leftLower:part(group,4,[0,0,0],material),
      rightUpper:part(group,3,[0,0,0],material),rightLower:part(group,4,[0,0,0],material),leftHand:part(gun,7,data.leftGrip,material),rightHand:part(gun,6,data.rightGrip,material),model:true,armed:true,enemy:true};
    poseArmedOpponent(actor,{hasPresentation:true,forward:{x:0,y:0,z:1},walking:false},0);return actor;
  },dispose(){if(!disposed){disposed=true;for(const g of geometries)g.dispose();}}};
}
export function poseArmedOpponent(actor,enemy,tick){
  poseOpponent(actor,enemy,tick);const pose=armedEnemyPose(enemy.forward,enemy.walking,tick);
  actor.gun.rotation.x=pose.gunPitch*Math.PI/180;
  const bone=(mesh,start,end)=>{const delta=new THREE.Vector3(...end).sub(new THREE.Vector3(...start));mesh.position.fromArray(start);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.clone().normalize());mesh.scale.set(1,delta.length(),1);};
  for(const side of ['left','right']){const p=pose[side];bone(actor[side+'Upper'],p.shoulder,p.elbow);bone(actor[side+'Lower'],p.elbow,p.wrist);}
}
