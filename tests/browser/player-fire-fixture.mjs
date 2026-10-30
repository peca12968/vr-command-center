import {fireFixture} from './combat-effects-fixture.mjs';
// Synthetic display fixture. Native input acceptance is checked separately.
export function playerFireFixture(sample){
  const data=fireFixture(sample);data.assetSet='player-fire-v1';data.playerFireVersion=1;let cursor=0;const last=new Map();
  for(const frame of data.frames){
    while(cursor<frame.throughSequence){const e=data.events[cursor++];if(e.kind==='ShotFired')last.set(e.playerId,e);}
    for(const player of frame.players){const e=last.get(player.id);Object.assign(player,{hasFireState:true,fireSequence:e?.sequence??0,fireTickPlusOne:e?e.tick+1:0,
      fireOrigin:structuredClone(e?.origin??{x:0,y:0,z:0}),fireDirection:structuredClone(e?.direction??{x:0,y:0,z:0})});}
  }
  return data;
}
