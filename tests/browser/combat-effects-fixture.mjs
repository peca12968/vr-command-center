import {weaponFixture} from './weapon-actions-fixture.mjs';
// Explicit synthetic presentation fixture, derived from retained accepted events.
export function fireFixture(sample){
  const data=weaponFixture(sample);data.assetSet='combat-effects-v1';data.enemyFireVersion=1;const last=new Map();let cursor=0;
  for(const frame of data.frames){
    while(cursor<frame.throughSequence){const e=data.events[cursor++];if(e.kind==='EnemyShot')last.set(e.enemyId,e);}
    for(const enemy of frame.enemies){const e=last.get(enemy.id);Object.assign(enemy,{hasFireState:true,fireSequence:e?.sequence??0,fireTickPlusOne:e?e.tick+1:0,
      fireOrigin:structuredClone(e?.origin??{x:0,y:0,z:0}),fireDirection:structuredClone(e?.direction??{x:0,y:0,z:0})});}
  }
  return data;
}
