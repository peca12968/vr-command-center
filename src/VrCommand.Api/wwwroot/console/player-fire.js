import * as THREE from './vendor/three/three.module.js';
import {PLAYER_FIRE} from './player-fire-data.js';
import {COMBAT_EFFECTS} from './combat-effects-data.js';
import {weaponActionsFactory} from './weapon-actions.js';
import {opponentGeometry} from './combatants.js';

export const PLAYER_FIRE_ASSETS='player-fire-v1';
export function playerFirePose(player,tick){
  const s=player.fireSequence,t=player.fireTickPlusOne,o=player.fireOrigin,d=player.fireDirection;
  if(player.hasFireState!==true||!Number.isSafeInteger(tick)||tick<0||tick>1728000||!Number.isSafeInteger(s)||s<0||!Number.isSafeInteger(t)||t<0||t>tick+1
    ||!Number.isInteger(player.health)||player.health<0||player.health>100||typeof player.connected!=='boolean'||typeof player.reloading!=='boolean'
    ||[o,d].some(p=>!p||![p.x,p.y,p.z].every(Number.isFinite))
    ||(s===0?t!==0||!['x','y','z'].every(k=>o[k]===0&&d[k]===0):t===0||Math.abs(Math.hypot(d.x,d.y,d.z)-1)>.01))throw new Error('Invalid player fire state');
  if(player.health===0||!player.connected||s===0)return{flash:false,recoil:0};
  const age=tick-(t-1);return{flash:age<3,recoil:player.reloading?0:[.014,.022,.012,.004][age]??0};
}
export function firingRifleFactory(data=PLAYER_FIRE){
  if(data?.assetSet!==PLAYER_FIRE_ASSETS||data.units!=='metres'||data.origin!=='accepted-player-shot'||data.forward!=='+Z'||data.playerFireVersion!==1
    ||data.weaponAssetSet!=='weapon-actions-v1'||data.pulseAssetSet!=='combat-effects-v1'||data.pulseScale!==1.2||data.flashTicks!==3
    ||data.weaponDataSha256!=='517c3616ec12dad34f25cc50f5309eae1033b62bcbbb636b4a3f378a5c12cab3'
    ||data.pulseDataSha256!=='b8fe83d66781c2f65816d6873cc08ba01314418d42777a55e9eea2d1ee34a9bb'
    ||data.recoilMetres?.length!==4||data.recoilMetres.some((v,i)=>v!==[.014,.022,.012,.004][i]))throw new Error('Unsupported player fire profile');
  const actions=weaponActionsFactory(),empty=new THREE.BufferGeometry();empty.setAttribute('position',new THREE.Float32BufferAttribute([],3));empty.setIndex([]);empty.userData.serviceRifleShared=true;let pulse;
  try{pulse=opponentGeometry(COMBAT_EFFECTS.mesh);}catch(e){actions.dispose();empty.dispose();throw e;}
  let disposed=false;
  return{triangles:actions.triangles,pulseTriangles:32,create(){
    if(disposed)throw new Error('Player fire pool is disposed');
    const root=actions.create(),body=new THREE.Mesh(root.geometry,root.material),recoil=new THREE.Group();root.geometry=empty;root.add(recoil);recoil.add(body);
    recoil.add(root.userData.weaponActions.magazine);
    const flash=new THREE.Mesh(pulse,new THREE.MeshBasicMaterial({vertexColors:true,toneMapped:false}));flash.scale.setScalar(data.pulseScale);flash.visible=false;
    root.userData.playerFire={body,recoil,flash};return root;
  },dispose(){if(!disposed){disposed=true;actions.dispose();empty.dispose();pulse.dispose();}}};
}
export function applyPlayerFire(root,player,tick){
  const v=root.userData.playerFire,p=playerFirePose(player,tick);v.recoil.position.z=-p.recoil;v.flash.visible=p.flash;
  if(player.fireSequence>0){
    const parent=v.flash.parent;parent.updateWorldMatrix(true,false);
    v.flash.position.copy(parent.worldToLocal(new THREE.Vector3(player.fireOrigin.x,player.fireOrigin.y,player.fireOrigin.z)));
    const q=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1),new THREE.Vector3(player.fireDirection.x,player.fireDirection.y,player.fireDirection.z).normalize());
    v.flash.quaternion.copy(parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(q));
  }
}
