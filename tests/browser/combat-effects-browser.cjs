const fs=require('node:fs/promises'),path=require('node:path');
module.exports=async function({context,tokens,base,root,screenshots,check}){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));const {fireFixture}=await import('./combat-effects-fixture.mjs');
  const sample=JSON.parse(await fs.readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8')),data=fireFixture(sample);
  try{await page.goto(base+'/console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-replay').click();
    await page.locator('#replay-file').setInputFiles({name:'fire.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});await page.waitForFunction(()=>document.querySelector('#replay-canvas').dataset.assetSet==='combat-effects-v1');
    const slider=page.locator('#replay-timeline'),shot=data.events.find(e=>e.kind==='EnemyShot'),index=data.frames.findIndex(f=>f.throughSequence>=shot.sequence&&f.tick-shot.tick<3);await slider.focus();for(let i=0;i<index;i++)await slider.press('ArrowRight');
    const state=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-enemy-fire-poses')),p=state.find(e=>e.id===shot.enemyId);
    check(p.flash&&p.recoil>0&&await page.locator('#replay-canvas').getAttribute('data-enemy-triangles')==='760','Actual WebGL renders the saved NPC muzzle pulse and nonzero sidearm recoil');
    const close=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]))<.00001;
    check(close(p.origin,[shot.origin.x,shot.origin.y,shot.origin.z])&&close(p.direction,[shot.direction.x,shot.direction.y,shot.direction.z]),'Actual flash world transform matches the saved ray rather than current body aim');
    const saved=await page.locator('#replay-canvas').getAttribute('data-enemy-fire-poses');await slider.press('End');await slider.press('Home');for(let i=0;i<index;i++)await slider.press('ArrowRight');check(await page.locator('#replay-canvas').getAttribute('data-enemy-fire-poses')===saved,'Direct seek reproduces the exact rendered flash and recoil');
    await page.locator('#replay-actor').selectOption('e:'+shot.enemyId);await page.locator('#replay-camera').selectOption('follow');await page.locator('#replay-canvas').hover();await page.mouse.wheel(0,-1400);await page.screenshot({path:path.join(screenshots,'combat-effects-replay.png'),fullPage:true});
    await slider.press('End');const final=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-enemy-fire-poses'));check(final.every(e=>!e.flash&&e.recoil===0)&&(await page.locator('#replay-statistics tr td').allTextContents()).join('|')==='Quest3-Simulation|3|1|20|1|66.67%|80','Ended replay has settled effects and unchanged exact event statistics');check(errors.length===0,'Enemy fire effects render without browser errors');
  }catch(e){await page.screenshot({path:path.join(screenshots,'combat-effects-failure.png'),fullPage:true}).catch(()=>{});throw e;}finally{await page.close();}
};
