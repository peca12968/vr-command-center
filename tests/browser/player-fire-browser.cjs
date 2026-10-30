const fs=require('node:fs/promises'),path=require('node:path');
module.exports=async function({context,tokens,base,root,screenshots,check}){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));const {playerFireFixture}=await import('./player-fire-fixture.mjs');
  const sample=JSON.parse(await fs.readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8')),data=playerFireFixture(sample);
  try{await page.goto(base+'/console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-replay').click();
    await page.locator('#replay-file').setInputFiles({name:'player-fire.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});await page.waitForFunction(()=>document.querySelector('#replay-canvas').dataset.assetSet==='player-fire-v1');
    const shot=data.events.find(e=>e.kind==='ShotFired'),index=data.frames.findIndex(f=>f.throughSequence>=shot.sequence&&f.tick-shot.tick<3),slider=page.locator('#replay-timeline');await slider.focus();for(let i=0;i<index;i++)await slider.press('ArrowRight');
    const state=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-player-fire-poses')),p=state.find(p=>p.id===shot.playerId),near=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]))<.00001;
    check(p.flash&&p.recoil>0,'Actual WebGL renders the accepted player flash and nonzero rifle recoil');
    check(near(p.origin,[shot.origin.x,shot.origin.y,shot.origin.z])&&near(p.direction,[shot.direction.x,shot.direction.y,shot.direction.z]),'Rendered player pulse follows the saved shot ray rather than current aim');
    const saved=await page.locator('#replay-canvas').getAttribute('data-player-fire-poses');await slider.press('End');await slider.press('Home');for(let i=0;i<index;i++)await slider.press('ArrowRight');check(await page.locator('#replay-canvas').getAttribute('data-player-fire-poses')===saved,'Direct seek restores identical player flash, recoil and muzzle transforms');
    await page.locator('#replay-actor').selectOption('p:'+shot.playerId);await page.locator('#replay-camera').selectOption('follow');await page.locator('#replay-canvas').hover();await page.mouse.wheel(0,-1400);await page.screenshot({path:path.join(screenshots,'player-fire-replay.png'),fullPage:true});
    await slider.press('End');check(JSON.parse(await page.locator('#replay-canvas').getAttribute('data-player-fire-poses')).every(p=>!p.flash&&p.recoil===0)&&(await page.locator('#replay-statistics tr td').allTextContents()).join('|')==='Quest3-Simulation|3|1|20|1|66.67%|80','Settled player effects preserve the exact final statistics');check(errors.length===0,'Player fire composition renders without page errors');
  }catch(e){await page.screenshot({path:path.join(screenshots,'player-fire-failure.png'),fullPage:true}).catch(()=>{});throw e;}finally{await page.close();}
};
