import * as THREE from './vendor/three/three.module.js';
import {PLAYER_BODY} from './player-body-data.js';
import {opponentGeometry} from './combatants.js';
import {solveArm,pitchPoint} from './armed-combatants.js';
import {weaponPose,RIGHT_GRIP} from './weapon-actions.js';
export const PLAYER_BODY_ASSETS='player-body-v1';
const add=(a,b)=>a.map((v,i)=>v+b[i]),sub=(a,b)=>a.map((v,i)=>v-b[i]);
export const bodyYaw=(p,degrees)=>{const a=degrees*Math.PI/180,s=Math.sin(a),c=Math.cos(a);return[c*p[0]+s*p[2],p[1],-s*p[0]+c*p[2]];};
export function playerBodyPose(player,tick){
  const head=[player.head.x,player.head.y,player.head.z],f=player.forward;
  const q=player.rig?.headRotation;const headForward=q?new THREE.Vector3(0,0,1).applyQuaternion(new THREE.Quaternion(q.x,q.y,q.z,q.w).normalize()):new THREE.Vector3(f.x,f.y,f.z);
  const yaw=Math.atan2(headForward.x,headForward.z)*180/Math.PI,scale=head[1]/1.65,feet=[head[0],0,head[2]],stride=player.walking?Math.sin(tick%12*Math.PI/6)*18:0;
  const wp=weaponPose(tick,player.health,player.connected,player.rig?.kind==='Simulated',player.reloading,player.reloadUntilTick),gunYaw=Math.atan2(f.x,f.z)*180/Math.PI,gunPitch=-Math.asin(Math.max(-1,Math.min(1,f.y/Math.hypot(f.x,f.y,f.z))))*180/Math.PI;
  const arm=(side,grip)=>{const shoulder=add(feet,bodyYaw([side*.215,1.37*scale,-.035],yaw)),wrist=add([player.muzzle.x,player.muzzle.y,player.muzzle.z],bodyYaw(pitchPoint(grip,gunPitch),gunYaw));
    const d=Math.hypot(...sub(wrist,shoulder));if(d<.03||d>1.24)return null;const stretch=Math.max(1,d/.619);return solveArm(shoulder,wrist,add(feet,bodyYaw([side*.42,1.05*scale,-.12],yaw)),.30*stretch,.32*stretch);};
  const left=arm(-1,add(wp.left,[-.06,0,-.06])),right=arm(1,add(RIGHT_GRIP,[.06,0,-.06]));
  return{feet,yaw,scale,stride,arms:!!(wp.hands&&left&&right),left,right};
}
export function playerBodyFactory(data=PLAYER_BODY){
  const kinds=['Torso','Head','Leg','UpperArm','LowerArm'];
  if(data?.assetSet!==PLAYER_BODY_ASSETS||data.units!=='metres'||data.origin!=='floor-below-head'||data.forward!=='+Z'||data.playerPresentationVersion!==1||data.referenceEyeHeight!==1.65
    ||data.retainedAssetSet!=='player-fire-v1'||data.retainedSha256!=='187c7df5346419edadafa1cc74a04db0763dda268650e066dbbcaf8304e60ff0'||data.parts?.length!==5||data.parts.some((p,i)=>p.kind!==kinds[i]))throw Error('Invalid player body profile');
  const geometries=[];let disposed=false;try{for(const p of data.parts)geometries.push(opponentGeometry(p));}catch(e){for(const g of geometries)g.dispose();throw e;}
  return{triangles:geometries.reduce((n,g,i)=>n+g.index.count/3*(i>=2?2:1),0),create(){if(disposed)throw Error('Disposed player body pool');
    const group=new THREE.Group(),bodyFrame=new THREE.Group(),material=new THREE.MeshStandardMaterial({color:0xffffff,roughness:.85,vertexColors:true});group.add(bodyFrame);
    const part=(parent,i,pos=[0,0,0])=>{const m=new THREE.Mesh(geometries[i],material);m.position.fromArray(pos);parent.add(m);return m;};
    return{group,bodyFrame,body:part(bodyFrame,0),head:part(group,1),leftLeg:part(bodyFrame,2,[-.11,.82,0]),rightLeg:part(bodyFrame,2,[.11,.82,0]),
      leftUpper:part(group,3),leftLower:part(group,4),rightUpper:part(group,3),rightLower:part(group,4)};
  },dispose(){if(!disposed){disposed=true;for(const g of geometries)g.dispose();}}};
}
export function posePlayerBody(model,player,tick,origin){
  const p=playerBodyPose(player,tick);model.group.visible=player.connected!==false&&player.health>0;
  model.bodyFrame.position.fromArray(p.feet).sub(origin);model.bodyFrame.rotation.y=p.yaw*Math.PI/180;model.bodyFrame.scale.set(1,p.scale,1);
  model.head.position.set(player.head.x,player.head.y,player.head.z).sub(origin);const q=player.rig?.headRotation;if(q)model.head.quaternion.set(q.x,q.y,q.z,q.w).normalize();else model.head.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),new THREE.Vector3(player.forward.x,player.forward.y,player.forward.z));
  model.leftLeg.rotation.x=p.stride*Math.PI/180;model.rightLeg.rotation.x=-p.stride*Math.PI/180;
  const bone=(mesh,a,b)=>{const delta=new THREE.Vector3(...b).sub(new THREE.Vector3(...a));mesh.position.fromArray(a).sub(origin);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.clone().normalize());mesh.scale.set(1,delta.length(),1);};
  for(const side of ['left','right']){model[side+'Upper'].visible=model[side+'Lower'].visible=p.arms;if(p.arms){bone(model[side+'Upper'],p[side].shoulder,p[side].elbow);bone(model[side+'Lower'],p[side].elbow,p[side].wrist);}}
}
