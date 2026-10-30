const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
module.exports=async function({context,tokens,base,root,screenshots,check}){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const{playerFireFixture}=await import('./player-fire-fixture.mjs');const sample=JSON.parse(await fs.readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));
  const data=playerFireFixture(sample);data.combatAudioVersion=1;
  try{
    await page.goto(base+'/console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-replay').click();
    await page.locator('#replay-file').setInputFiles({name:'combat-audio.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
    await page.waitForFunction(()=>document.querySelector('#replay-canvas').dataset.combatAudioVersion==='1');
    check(await page.locator('#replay-canvas').getAttribute('data-combat-audio-count')==='0'&&await page.locator('#replay-canvas').getAttribute('data-weather-audio')==='off','Combat replay remains silent before an explicit audio gesture');
    for(const name of ['rifle-shot-v1.wav','pistol-shot-v1.wav']){const r=await fetch(base+'/console/audio/'+name),remote=Buffer.from(await r.arrayBuffer()),local=await fs.readFile(path.join(root,'clients/unity/Assets/VrCommand/Audio',name));check(r.status===200&&crypto.createHash('sha256').update(remote).digest('hex')===crypto.createHash('sha256').update(local).digest('hex'),'Browser serves the exact canonical combat PCM: '+name);}
    await page.locator('#replay-sound').click();await page.waitForFunction(()=>document.querySelector('#replay-canvas').dataset.weatherAudio==='on');
    const slider=page.locator('#replay-timeline');await slider.focus();await slider.press('End');await slider.press('Home');
    check(await page.locator('#replay-canvas').getAttribute('data-combat-audio-count')==='0','Manual forward/backward seek never replays accepted shots');
    await page.locator('#replay-play').click();await page.waitForFunction(()=>Number(document.querySelector('#replay-canvas').dataset.combatAudioCount)>0&&Number(document.querySelector('#replay-canvas').dataset.combatAudioPeak)>.000001,{},{timeout:12000});
    const cue=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-combat-audio-last')),event=data.events.find(e=>e.sequence===cue.sequence);
    check(event&&event.kind===(cue.enemy?'EnemyShot':'ShotFired')&&event.tick===cue.tick&&['x','y','z'].every(k=>event.origin[k]===cue.origin[k]),'Actual Web Audio cue uses the accepted event sequence, clock and historical muzzle');
    await page.locator('#replay-play').click();await page.waitForTimeout(100);check(await page.locator('#replay-canvas').getAttribute('data-combat-audio-voices')==='0','Pause immediately releases active combat audio nodes');
    await page.screenshot({path:path.join(screenshots,'combat-audio-replay.png'),fullPage:true});
    await page.locator('#replay-file').setInputFiles({name:'old-player-fire.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(playerFireFixture(sample)))});
    await page.waitForFunction(()=>document.querySelector('#replay-canvas').dataset.combatAudioVersion==='0');check(await page.locator('#replay-sound').isDisabled()&&await page.locator('#replay-sound').getAttribute('aria-pressed')==='false'&&await page.locator('#replay-canvas').getAttribute('data-combat-audio-count')==='0'&&errors.length===0,'Legacy replay stays without combat sounds, resets the enabled label and has no page errors');
  }catch(e){await fs.writeFile(path.join(screenshots,'combat-audio-failure.json'),JSON.stringify({dataset:await page.locator('#replay-canvas').evaluate(c=>({...c.dataset})).catch(()=>null),errors},null,2));await page.screenshot({path:path.join(screenshots,'combat-audio-failure.png'),fullPage:true}).catch(()=>{});throw e;}finally{await page.close();}
};
