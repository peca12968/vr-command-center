const fs=require('node:fs/promises'),path=require('node:path');
module.exports=async function({context,tokens,base,root,screenshots,check}){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const {weaponFixture}=await import('./weapon-actions-fixture.mjs');const sample=JSON.parse(await fs.readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));
  async function load(value){await page.locator('#replay-file').setInputFiles({name:'actions.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});await page.waitForFunction(profile=>document.querySelector('#replay-canvas').dataset.assetSet===profile&&Number(document.querySelector('#replay-canvas').dataset.triangles)>0,value.assetSet);}
  try{await page.goto(base+'/console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-replay').click();
    const old=weaponFixture(sample);old.assetSet='combatants-v1';old.weaponPresentationVersion=0;
    for(const f of old.frames)for(const p of f.players){p.hasWeaponPresentation=false;p.reloadUntilTick=0;}
    await load(old);const prior=Number(await page.locator('#replay-canvas').getAttribute('data-triangles'));check(await page.locator('#replay-canvas').getAttribute('data-weapon-poses')==='[]','Retained combatant recordings keep their static weapon and old hand markers');
    const data=weaponFixture(sample);await load(data);const state=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-weapon-poses'));
    check(Number(await page.locator('#replay-canvas').getAttribute('data-triangles'))-prior===228&&state[0].hands,'Actual WebGL replaces one synthetic hand marker with two original 120-triangle gloves and retains all 264 rifle triangles');
    const slider=page.locator('#replay-timeline'),index=data.frames.findIndex(f=>f.tick===28);await slider.focus();for(let i=0;i<index;i++)await slider.press('ArrowRight');
    const saved=await page.locator('#replay-canvas').getAttribute('data-weapon-poses');check(JSON.parse(saved)[0].magazine[1]<-.2,'Saved reload deadline drives the rendered magazine below its well');
    await slider.press('End');await slider.press('Home');for(let i=0;i<index;i++)await slider.press('ArrowRight');check(await page.locator('#replay-canvas').getAttribute('data-weapon-poses')===saved,'Direct seek restores the identical magazine and left-glove transforms');
    await page.locator('#replay-camera').selectOption('follow');await page.locator('#replay-canvas').hover();await page.mouse.wheel(0,-1100);await page.screenshot({path:path.join(screenshots,'weapon-actions-reload.png'),fullPage:true});
    await slider.press('End');check((await page.locator('#replay-statistics tr td').allTextContents()).join('|')==='Quest3-Simulation|3|1|20|1|66.67%|80'&&JSON.parse(await page.locator('#replay-canvas').getAttribute('data-weapon-poses'))[0].magazine[1]===-.075,'Completed reload returns the magazine without changing final event statistics');
    check(errors.length===0,'Animated reload renders without page errors');
  }catch(error){await page.screenshot({path:path.join(screenshots,'weapon-actions-failure.png'),fullPage:true}).catch(()=>{});
    await fs.writeFile(path.join(screenshots,'weapon-actions-failure.json'),JSON.stringify({errors,notice:await page.locator('#replay-notice').textContent().catch(()=>''),assetSet:await page.locator('#replay-canvas').getAttribute('data-asset-set').catch(()=>null)},null,2));throw error;
  }finally{await page.close();}
};
