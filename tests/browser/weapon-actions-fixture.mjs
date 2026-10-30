// Synthetic reload events added to the retained Simulation example. Native
// acceptance and real keyboard reloads are verified separately on Windows.
export function weaponFixture(sample) {
  const data=structuredClone(sample),player=data.frames[0].players[0].id;
  data.assetSet='weapon-actions-v1';data.enemyPresentationVersion=1;data.weaponPresentationVersion=1;
  const guid=suffix=>'a3780639-fb58-4dc1-84e2-0000000000'+suffix;
  for(const [tick,kind] of [[20,'ReloadStarted'],[50,'ReloadCompleted']])data.events.push({sequence:data.events.length+1,eventId:guid(tick===20?'01':'02'),tick,kind,playerId:player,shotId:null,enemyId:null,damage:0,origin:null,direction:null,distance:null,hit:null,targetId:null});
  for(const frame of data.frames){frame.throughSequence+=(frame.tick>=20?1:0)+(frame.tick>=50?1:0);
    for(const p of frame.players){p.hasWeaponPresentation=true;p.reloadUntilTick=0;p.connected=true;
      const w=Math.sqrt((1+p.forward.z)/2),rotation={x:-p.forward.y/(2*w),y:p.forward.x/(2*w),z:0,w};
      p.rig={kind:'Simulated',headRotation:rotation,rightRotation:rotation,leftRotation:rotation,
        right:{x:p.muzzle.x,y:p.muzzle.y,z:p.muzzle.z},left:{x:p.head.x-.2,y:p.head.y-.3,z:p.head.z+.3}};
      if(p.id===player&&frame.tick>=20&&frame.tick<50){p.reloading=true;p.reloadUntilTick=50;}
      else if(p.id===player&&frame.tick>=50){p.reloading=false;p.magazine=30;p.reserve=87;}}
    for(const e of frame.enemies)Object.assign(e,{hasPresentation:true,forward:{x:0,y:0,z:-1},walking:false});}
  return data;
}
