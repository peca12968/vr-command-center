// Read-only observer of check-desktop-reload.py's own isolated native world.
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const {chromium}=require('playwright');
const root=path.resolve(__dirname,'../..');
async function main(){
  const dir=path.resolve(process.argv[2]||'');assert.equal(path.dirname(dir),path.join(root,'artifacts/desktop-venue'));assert.match(path.basename(dir),/^\d{8}-\d{6}-[a-f0-9]{8}$/);
  const cfg=JSON.parse(await fs.readFile(path.join(dir,'reload-server.json'),'utf8')),tokens=JSON.parse(await fs.readFile(path.join(dir,'keys.json'),'utf8')).OperatorKeys;
  const base=new URL(cfg.managementApiUrl);assert.equal(base.hostname,'127.0.0.1');assert.notEqual(base.port,'5080');
  const samples=JSON.parse(await fs.readFile(path.join(dir,'reload-samples.json'),'utf8')),own=samples[0].body.id;
  const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));let checks=0;const check=(value,label)=>{assert.ok(value,label);checks++;console.log('PASS: '+label);};
  try{
    await page.goto(base.href+'console/');await page.locator('#login-key').fill(tokens.Master);await page.locator('#login-form button').click();await page.locator('#tab-world').click();await page.locator('#world-refresh').click();
    await page.locator('#world-recording option').first().waitFor({state:'attached'});await page.locator('#world-recording').selectOption(cfg.sessionId);await page.locator('#world-live').click();
    await page.waitForFunction(id=>{try{return JSON.parse(document.querySelector('#world-canvas').dataset.weaponPoses).some(p=>p.id===id);}catch{return false;}},own);
    const value=JSON.parse(await fs.readFile(path.join(dir,'reload-latest-frame.json'),'utf8')),frame=value.packet.frame,player=frame.players.find(p=>p.id===own);
    check(frame.phase==='Paused'&&player.reloading&&player.hasWeaponPresentation,'Actual native saved frame is paused inside an accepted reload');
    const {weaponPose}=await import(pathToFileURL(path.join(root,'src/VrCommand.Api/wwwroot/console/weapon-actions.js')).href);
    const expected=weaponPose(frame.tick,player.health,player.connected,player.rig.kind==='Simulated',player.reloading,player.reloadUntilTick),pivot=[0,-.075,-.4025];
    const rendered=JSON.parse(await page.locator('#world-canvas').getAttribute('data-weapon-poses')).find(p=>p.id===own),near=(a,b)=>Math.abs(a-b)<.00001;
    check(rendered.magazine.every((v,i)=>near(v,pivot[i]+expected.offset[i]))&&near(rendered.roll,expected.roll)&&rendered.magazineVisible===expected.visible,'Native clock produces the exact rendered magazine displacement, roll and exchange visibility');
    check(rendered.left.every((v,i)=>near(v,expected.left[i]))&&near(rendered.leftRoll,expected.leftRoll)&&rendered.hands===expected.hands,'Native recorded source selects the matching simulated left-glove pose');
    await page.locator('#world-actor').selectOption('p:'+own);
    const target=[player.muzzle.x,player.muzzle.y-.1,player.muzzle.z-.35];for(const [key,v] of [['x',target[0]],['y',target[1]],['z',target[2]],['azimuth',-110],['elevation',15],['distance',2.4]])await page.locator('#world-camera-'+key).fill(String(v));
    await page.locator('#world-camera-apply').click();await page.screenshot({path:path.join(dir,'reload-observer.png'),fullPage:true});
    check(Number(await page.locator('#world-canvas').getAttribute('data-triangles'))>0&&await page.locator('#world-canvas').getAttribute('data-asset-set')==='armed-combatants-v1','Real software WebGL renders the versioned native reload from an operator camera');
    check(errors.length===0,'Actual-native reload observation has no page errors');
    await fs.writeFile(path.join(dir,'reload-observer.json'),JSON.stringify({source:'Actual native recording; Chromium SwiftShader observer',frame,expected,rendered,checks,errors},null,2));
  }catch(error){await page.screenshot({path:path.join(dir,'reload-observer-failure.png'),fullPage:true}).catch(()=>{});throw error;}
  finally{await browser.close();}
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
