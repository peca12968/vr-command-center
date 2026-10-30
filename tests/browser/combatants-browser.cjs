const fs=require('node:fs/promises'),path=require('node:path');
module.exports=async function({context,tokens,base,root,screenshots,check}){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const sample=JSON.parse(await fs.readFile(path.join(root,'src/VrCommand.Api/wwwroot/console/examples/simulation.json'),'utf8'));
  async function load(profile){const value=structuredClone(sample);value.assetSet=profile;
    if(profile==='combatants-v1'){value.enemyPresentationVersion=1;for(const frame of value.frames)for(const e of frame.enemies)Object.assign(e,{hasPresentation:true,forward:{x:1,y:.2,z:1},walking:e.health>0&&frame.phase!=='Preparing'});
      // Unit saved orientation; these are explicitly synthetic replay fixtures.
      for(const frame of value.frames)for(const e of frame.enemies){const n=Math.hypot(e.forward.x,e.forward.y,e.forward.z);for(const k of ['x','y','z'])e.forward[k]/=n;}}
    await page.locator('#replay-file').setInputFiles({name:profile+'.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
    await page.waitForFunction(p=>document.querySelector('#replay-canvas').dataset.assetSet===p&&Number(document.querySelector('#replay-canvas').dataset.triangles)>0,profile);
    return Number(await page.locator('#replay-canvas').getAttribute('data-triangles'));}
  try{await page.goto(base+'/console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-replay').click();
    const old=await load('service-rifle-v1');check(await page.locator('#replay-canvas').getAttribute('data-enemy-triangles')==='0','Old service-rifle recordings preserve their original opponent geometry');
    const current=await load('combatants-v1');
    const poses=JSON.parse(await page.locator('#replay-canvas').getAttribute('data-enemy-poses'));
    check(current-old===sample.frames[0].enemies.length*(404-204)&&await page.locator('#replay-canvas').getAttribute('data-enemy-triangles')==='404'&&poses.length===sample.frames[0].enemies.length,
      'Real WebGL uses the explicitly versioned 404-triangle humanoids while retaining the rifle and cover profile');
    const slider=page.locator('#replay-timeline');await slider.focus();for(let i=0;i<5;i++)await slider.press('ArrowRight');const saved=await page.locator('#replay-canvas').getAttribute('data-enemy-poses');
    await slider.press('End');await slider.press('Home');for(let i=0;i<5;i++)await slider.press('ArrowRight');
    check(await page.locator('#replay-canvas').getAttribute('data-enemy-poses')===saved&&JSON.parse(saved).every(p=>Math.abs(p.left-18)<.0001&&Math.abs(p.left+p.right)<1e-9&&Math.abs(p.yaw-45)<.0001),
      'Direct replay seeks restore identical rendered yaw, head pitch and opposite leg rotations from saved ticks');
    await page.screenshot({path:path.join(screenshots,'combatants-replay.png'),fullPage:true});
    await page.locator('#replay-actor').selectOption('e:'+sample.frames[0].enemies[0].id);await page.locator('#replay-camera').selectOption('follow');await page.locator('#replay-canvas').hover();await page.mouse.wheel(0,-1100);
    await page.screenshot({path:path.join(screenshots,'combatants-closeup.png'),fullPage:true});
    await slider.press('End');check((await page.locator('#replay-statistics tr td').allTextContents()).join('|')==='Quest3-Simulation|3|1|20|1|66.67%|80','Humanoid appearance preserves exact final replay statistics');
    for(const profile of ['primitives-v1','combatants-v1','field-props-v1','combatants-v1'])await load(profile);
    check(errors.length===0,'Switching legacy and humanoid recordings releases shared resources without browser errors');
  }finally{await page.close();}
};
