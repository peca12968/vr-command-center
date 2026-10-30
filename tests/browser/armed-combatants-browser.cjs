const fs=require('node:fs/promises'),path=require('node:path');
module.exports=async function({context,tokens,base,root,screenshots,check}){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const {weaponFixture}=await import('./weapon-actions-fixture.mjs');const sample=JSON.parse(await fs.readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));
  const load=async value=>{await page.locator('#replay-file').setInputFiles({name:'armed.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});await page.waitForFunction(p=>document.querySelector('#replay-canvas').dataset.assetSet===p&&Number(document.querySelector('#replay-canvas').dataset.triangles)>0,value.assetSet);};
  try{await page.goto(base+'/console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-replay').click();
    const old=weaponFixture(sample);await load(old);const previous=Number(await page.locator('#replay-canvas').getAttribute('data-triangles'));
    check(await page.locator('#replay-canvas').getAttribute('data-armed-poses')==='[]','Retained weapon-actions NPCs preserve their unarmed silhouette');
    const current=weaponFixture(sample);current.assetSet='armed-combatants-v1';for(const f of current.frames)for(const e of f.enemies){e.forward={x:0,y:.2,z:-Math.sqrt(.96)};e.walking=e.health>0&&f.phase!=='Preparing';}
    await load(current);let poses=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-armed-poses'));
    check(Number(await page.locator('#replay-canvas').getAttribute('data-triangles'))-previous===sample.frames[0].enemies.length*(728-404)&&await page.locator('#replay-canvas').getAttribute('data-enemy-triangles')==='728','Actual WebGL composes 728-triangle armed NPCs with the retained props and animated rifle');
    check(poses.every(p=>{const e=current.frames[0].enemies.find(e=>e.id===p.id);return Math.hypot(p.muzzle[0]-e.feet.x,p.muzzle[1]-1.4,p.muzzle[2]-e.feet.z)<1e-8&&Math.hypot(p.forward[0]-e.forward.x,p.forward[1]-e.forward.y,p.forward[2]-e.forward.z)<1e-8;}),'Rendered gun world origin and forward match the saved authority pose');
    const slider=page.locator('#replay-timeline');await slider.focus();for(let i=0;i<5;i++)await slider.press('ArrowRight');const saved=await page.locator('#replay-canvas').getAttribute('data-armed-poses');
    await slider.press('End');await slider.press('Home');for(let i=0;i<5;i++)await slider.press('ArrowRight');check(await page.locator('#replay-canvas').getAttribute('data-armed-poses')===saved,'Direct seek restores identical rendered elbows, wrists, muzzle and full gun pitch');
    await page.locator('#replay-actor').selectOption('e:'+sample.frames[0].enemies[0].id);await page.locator('#replay-camera').selectOption('follow');await page.locator('#replay-canvas').hover();await page.mouse.wheel(0,-1450);
    await page.screenshot({path:path.join(screenshots,'armed-combatants-closeup.png'),fullPage:true});
    await slider.press('End');check((await page.locator('#replay-statistics tr td').allTextContents()).join('|')==='Quest3-Simulation|3|1|20|1|66.67%|80','Armed visuals preserve exact final event statistics');
    for(const profile of ['weapon-actions-v1','armed-combatants-v1','weapon-actions-v1'])await load({...current,assetSet:profile});check(errors.length===0,'Armed and retained model pools switch without browser errors');
  }catch(e){await page.screenshot({path:path.join(screenshots,'armed-combatants-failure.png'),fullPage:true}).catch(()=>{});throw e;}finally{await page.close();}
};
