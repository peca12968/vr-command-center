// Explicit Windows integration: run start-desktop-control.py first, then pass its
// ready.json. This uses only that helper's temporary credentials and actual UI.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../..');
let redactionTokens = [];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  const readyPath = path.resolve(process.argv[2] || '');
  const directory = path.dirname(readyPath);
  assert.equal(path.dirname(directory), path.join(root, 'artifacts/desktop-venue'));
  assert.match(path.basename(directory), /^\d{8}-\d{6}-[a-f0-9]{8}$/);
  const ready = JSON.parse(await fs.readFile(readyPath, 'utf8'));
  assert.equal(ready.source, 'Simulation'); assert.equal(ready.headsets, 0);
  const base = new URL(ready.baseUrl); assert.equal(base.hostname, '127.0.0.1'); assert.notEqual(base.port, '5080');
  const tokens = JSON.parse(await fs.readFile(path.join(directory, 'keys.json'), 'utf8')).OperatorKeys;
  redactionTokens = Object.values(tokens);
  const evidence = path.join(directory, 'operator-ui'); await fs.mkdir(evidence, { recursive: true });
  let checks = 0, session;
  function check(value, label) { assert.ok(value, label); checks++; console.log('PASS: ' + label); }
  async function api(route) {
    const response = await fetch(ready.baseUrl + '/api' + route, { headers: { Authorization: 'Bearer ' + tokens.Master }, signal: AbortSignal.timeout(5000) });
    assert.equal(response.status, 200, route); return response.json();
  }
  async function until(predicate, label, seconds = 30) {
    const end = Date.now() + seconds * 1000;
    while (Date.now() < end) { const value = await predicate(); if (value) return value; await sleep(150); }
    throw new Error('Timed out: ' + label);
  }
  async function native(predicate) {
    try { const state = JSON.parse(await fs.readFile(path.join(directory, 'operator-status.json'), 'utf8')); return state.sessionId === session && predicate(state) ? state : false; }
    catch { return false; }
  }
  async function nativeFrame(predicate) {
    try { const row=JSON.parse(await fs.readFile(path.join(directory,'operator-'+session+'-latest-frame.json'),'utf8'));
      return predicate(row.packet.frame) ? row.packet.frame : false; } catch { return false; }
  }
  async function manual(stage) {
    if (!process.argv.includes('--manual-inspection')) return;
    await fs.writeFile(path.join(evidence, 'stage.json'), JSON.stringify({ stage, sessionId: session }));
    console.log('NATIVE INSPECTION: ' + stage);
    await until(async () => { try { await fs.access(path.join(evidence, stage + '.done')); return true; } catch { return false; } }, 'native ' + stage, 300);
  }
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  page.setDefaultTimeout(15000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', dialog => dialog.type() === 'confirm' ? dialog.accept() : dialog.dismiss());
  try {
    await page.goto(ready.consoleUrl); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click();
    await page.locator('#draft-name').fill('Operator layout - Simulation'); await page.locator('#draft-briefing').fill('UI-authored scene; native desktop, no headset.');
    await page.locator('#draft-duration').fill('1200'); await page.locator('#draft-weather').selectOption('Clear'); await page.locator('#draft-time').selectOption('Day');
    await page.locator('#draft-count').fill('1'); await page.locator('#draft-auto-attack').uncheck();
    await page.locator('#add-sandbag').click();
    for (const [name, value] of [['prop-x','-3'],['prop-z','0'],['prop-yaw','15']]) { await page.locator('#'+name).fill(value); await page.locator('#'+name).press('Tab'); }
    await page.locator('#add-barrel').click();
    for (const [name, value] of [['prop-x','-1'],['prop-z','1.5'],['prop-yaw','90']]) { await page.locator('#'+name).fill(value); await page.locator('#'+name).press('Tab'); }
    await page.locator('#mission-form button[type=submit]').click();
    await until(async () => (await page.locator('#draft-status').innerText()).startsWith('已儲存'), 'saved mission');
    const missions = await api('/missions'); const mission = missions.find(m => m.definition.name === 'Operator layout - Simulation');
    check(mission && mission.definition.props[0].position.x === -3 && mission.definition.props[1].yawDegrees === 90, 'UI-authored geometry saved by the actual mission API');
    await page.locator('#new-mission').click(); await page.locator('#edit-mission').selectOption(mission.id); await page.locator('#load-mission').click();
    await until(async () => (await page.locator('#draft-name').inputValue()) === mission.definition.name, 'saved mission reloaded');
    check((await page.locator('#prop-select option').count()) === 2 && await page.locator('#draft-weather').inputValue() === 'Clear', 'Operator reloads saved task and geometry before selecting it for native play');
    await page.waitForFunction(() => document.querySelector('#draft-layout-summary').dataset.status === 'valid');
    check(await page.locator('#layout-spawns circle').count() === 5 && await page.locator('#prop-layer [data-layout-invalid=true]').count() === 0,
      'The native task editor approves the saved geometry with all five real spawn margins');
    await page.screenshot({ path: path.join(evidence, 'mission-editor.png'), fullPage: true });
    await page.locator('#tab-operations').click(); await page.locator('#launch-mission').selectOption(mission.id); await page.locator('#launch-room').selectOption('1');
    await page.waitForFunction(() => document.querySelector('#launch-layout-summary').dataset.status === 'valid');
    check(await page.locator('#create-session-form button').isEnabled() && (await api(`/missions/${mission.id}/layout?mode=Independent`)).canStart === true,
      'The exact saved native mission passes both operator UI and authenticated server preflight before reserving a room');
    await page.locator('#create-session-form button').click();
    await until(async () => (await api('/sessions')).length === 1, 'Preparing round'); session = (await api('/sessions'))[0].id;
    for (const name of ['Operator 01', 'Peer 02']) { await page.locator('#player-name').fill(name); await page.locator('#join-form button').click(); await until(async () => (await page.locator('#roster').innerText()).includes(name), 'roster ' + name); }
    await until(async () => { try { const status = JSON.parse(await fs.readFile(path.join(directory, 'operator-status.json'), 'utf8')); return status.sessionId === session && status.connectedPlayers.length === 2; } catch { return false; } }, 'two native clients', 100);
    check(true, 'UI roster drives two authenticated native clients without manual connection files');
    const removedPeer = (await api('/sessions/' + session)).players.find(p => p.name === 'Peer 02');
    await page.locator('#roster tr').filter({ hasText: 'Peer 02' }).getByRole('button', { name: '移除', exact: true }).click();
    await until(async () => !(await api('/sessions/' + session)).players.some(p => p.id === removedPeer.id), 'UI removes peer admission');
    await page.locator('#player-name').fill('Peer 03'); await page.locator('#join-form button').click();
    const replacement = await until(async () => (await api('/sessions/' + session)).players.find(p => p.name === 'Peer 03'), 'new peer roster');
    await until(async () => { try { const status = JSON.parse(await fs.readFile(path.join(directory, 'operator-status.json'), 'utf8')); return status.connectedPlayers.includes(replacement.id) && !status.connectedPlayers.includes(removedPeer.id); } catch { return false; } }, 'dynamic native roster', 60);
    check(true, 'GUI removal closes only the old native peer and a new admission starts a replacement');
    const world = await api('/sessions/' + session + '/world');
    check(world.header.props.length === 2 && world.header.props[0].feet.x === -31 && world.header.props[1].feet.z === 1.5, 'Real native world recording contains UI-authored room-relative props');
    async function refresh() {
      await page.locator('#refresh').click(); const state = await api('/sessions/' + session);
      await until(async () => Number((await page.locator('#session-meta').innerText()).match(/序號 (\d+)/)?.[1]) >= state.sequence, 'UI sequence refresh');
    }
    async function command(action) {
      for (let attempt = 0; attempt < 3; attempt++) {
        await refresh();
        const received = page.waitForResponse(response => response.url() === ready.baseUrl + '/api/sessions/' + session + '/commands' && response.request().method() === 'POST');
        await page.locator('[data-command=' + action + ']').click(); const response = await received;
        if (response.status() === 200) return;
        assert.equal(response.status(), 409, 'Unexpected UI command response');
        // This is a new explicit operator intent after a conflict and refresh,
        // not a replay of an accepted command or removal of the admission fence.
      }
      throw new Error('Operator command kept conflicting: ' + action);
    }
    await command('Begin');
    await until(async () => (await api('/sessions/' + session)).state === 'Running', 'Begin');
    await until(() => native(state => state.phase === 'Running'), 'native Running observation');
    check(true, 'Operator Begin reaches the native running world');
    await manual('native-day');
    await refresh(); await page.locator('#reload-environment').click(); await page.locator('#live-weather').selectOption('Storm'); await page.locator('#live-time').selectOption('Night'); await page.locator('#live-lightning').check(); await page.locator('#environment-form button[type=submit]').click();
    await until(async () => (await api('/sessions/' + session)).environment.weather === 'Storm', 'Storm override');
    await until(() => native(state => state.weather === 'Storm' && state.night && state.lightning), 'native environment observation');
    check(true, 'Operator applies Storm / Night / lightning to the native session');
    await manual('native-storm');
    await page.locator('#tab-world').click(); await page.locator('#world-refresh').click(); await until(async () => (await page.locator('#world-recording option').count()) > 0, 'native recording in console');
    await page.locator('#world-recording').selectOption(session); await page.locator('#world-live').click();
    await until(async () => (await page.locator('#world-environment').innerText()).includes('Storm') || (await page.locator('#world-environment').innerText()).includes('暴風雨'), 'native world observed');
    check(await page.locator('#world-canvas').getAttribute('data-asset-set') === 'weapon-actions-v1'
      && Number(await page.locator('#world-canvas').getAttribute('data-prop-triangles')) === 642,
      'Actual native header selects the same 256-triangle sandbags and 386-triangle drum in live observation');
    check(await page.locator('#world-canvas').getAttribute('data-rifle-triangles') === '264'
      && Number(await page.locator('#world-canvas').getAttribute('data-rifle-count')) >= 2,
      'Live actual-native observation renders the versioned player rifles from accepted muzzle poses');
    check(await page.locator('#world-canvas').getAttribute('data-enemy-triangles') === '404'
      && JSON.parse(await page.locator('#world-canvas').getAttribute('data-enemy-poses')).length === 1,
      'Actual native world explicitly selects the shared humanoid model and saved enemy orientation');
    await page.locator('#world-camera').selectOption('top'); await page.locator('#camera-name').fill('Operator overhead'); await page.locator('#camera-save').click();
    await until(async () => (await api('/sessions/' + session + '/world/cameras')).length === 1, 'persisted camera');
    const camera = (await api('/sessions/' + session + '/world/cameras'))[0];
    const savedPose = await page.locator('#world-canvas').getAttribute('data-camera');
    check(camera.name === 'Operator overhead', 'Operator saves an overhead camera on an actual native recording');
    await page.screenshot({ path: path.join(evidence, 'native-live-overhead.png'), fullPage: true });
    await require('./camera-controls.cjs')({ page, check, screenshots: evidence });
    await page.locator('#camera-name').fill('Precise native view'); await page.locator('#camera-save').click();
    await until(async () => (await api('/sessions/' + session + '/world/cameras')).length === 2, 'persisted custom camera');
    const preciseCamera = (await api('/sessions/' + session + '/world/cameras')).find(row => row.name === 'Precise native view');
    const precisePose = await page.locator('#world-canvas').getAttribute('data-camera');
    check(preciseCamera && preciseCamera.view.target[1] === 1.25 && preciseCamera.view.target[2] === .4
      && Math.abs(preciseCamera.view.theta - Math.PI / 4) < 1e-12 && Math.abs(preciseCamera.view.phi - Math.PI / 4) < 1e-12
      && preciseCamera.view.radius === 12, 'The numeric native-world target, degree angles and distance persist through the authenticated bookmark API');
    await page.locator('#tab-operations').click(); await command('Pause'); await until(async () => (await api('/sessions/' + session)).state === 'Paused', 'Pause');
    const paused = await until(() => native(state => state.phase === 'Paused'), 'native Pause observation');
    await sleep(400);
    const stablePause=await until(()=>native(state=>state.phase==='Paused'&&state.tick===paused.tick),'stable native paused tick');
    await fs.writeFile(path.join(evidence,'pause-observation.json'),JSON.stringify({initial:paused,stable:stablePause},null,2));
    check(stablePause.tick===paused.tick, 'Native tick freezes after the actual operator Pause');
    check(true, 'Operator Pause reaches the native world');
    await manual('native-paused');
    await refresh(); await page.locator('#reload-enemies').click(); await page.locator('#live-count').fill('2'); await page.locator('#live-behavior').selectOption('Advance'); await page.locator('#live-auto-attack').check(); await page.locator('#enemies-form button[type=submit]').click();
    await until(async () => (await api('/sessions/' + session)).enemies.count === 2, 'AI override');
    await until(() => native(state => state.enemyCount === 2 && state.behavior === 'Advance' && state.autoAttack), 'native AI policy observation');
    await command('Resume');
    await until(async () => (await api('/sessions/' + session + '/statistics')).players.some(p => p.hitsReceived > 0), 'UI-controlled native AI damage');
    // Stop combat first so the subsequent End uses a stable, explicitly refreshed version.
    await command('Pause'); await until(async () => (await api('/sessions/' + session)).state === 'Paused', 'final Pause');
    // Advance can reach its two-metre stop before the management poll. Use the
    // actual operator Patrol setting to verify moving poses independently.
    await refresh(); await page.locator('#reload-enemies').click(); await page.locator('#live-behavior').selectOption('Patrol'); await page.locator('#live-auto-attack').uncheck(); await page.locator('#enemies-form button[type=submit]').click();
    await until(() => native(s=>s.phase==='Paused' && s.behavior==='Patrol' && !s.autoAttack), 'native Patrol policy');
    let strideFrame;
    for(let attempt=0;attempt<4;attempt++) {
      await command('Resume');
      await until(()=>nativeFrame(f=>f.phase==='Running' && f.enemies.some(e=>e.walking) && f.tick%6!==0),'native walking stride');
      await command('Pause'); await until(()=>native(s=>s.phase==='Paused'),'native stride pause');
      strideFrame=await until(()=>nativeFrame(f=>f.phase==='Paused' && f.enemies.some(e=>e.walking)),'saved paused stride');
      if(strideFrame.tick%6!==0)break;
    }
    check(strideFrame.tick%6!==0 && strideFrame.enemies.some(e=>e.hasPresentation&&e.walking),'Operator Patrol moves actual native opponents and Pause preserves a nonzero saved stride');
    await manual('native-opponents');
    await command('End');
    await until(async () => (await api('/sessions/' + session + '/world')).complete, 'native exact seal');
    await page.locator('#tab-world').click(); await page.locator('#world-replay').click();
    await until(async () => await page.locator('#world-pause').isEnabled(), 'native replay');
    await page.locator('#world-camera').selectOption('follow'); await page.locator('#world-speed').selectOption('2');
    await page.locator('#camera-positions').selectOption(camera.id);
    await page.locator('#camera-recall').click();
    await until(async () => (await page.locator('#world-canvas').getAttribute('data-camera')) === savedPose, 'camera recalled on native replay');
    check(true, 'Saved native-world overhead position is recalled after switching to follow mode');
    await page.locator('#camera-positions').selectOption(preciseCamera.id); await page.locator('#camera-recall').click();
    check((await page.locator('#world-canvas').getAttribute('data-camera')) === precisePose, 'Custom native-world position and angles are restored exactly in sealed replay');
    await page.locator('#world-timeline').press('End');
    await until(async () => (await page.locator('#world-timeline').inputValue()) === (await page.locator('#world-timeline').getAttribute('max')), 'replay final seek');
    const finalInfo = await api('/sessions/' + session + '/world');
    await until(async () => (await page.locator('#world-time').innerText()).includes('幀 ' + finalInfo.acceptedSequence), 'rendered final replay frame');
    check(await page.locator('#world-canvas').getAttribute('data-asset-set') === 'weapon-actions-v1'
      && Number(await page.locator('#world-canvas').getAttribute('data-prop-triangles')) === 642,
      'Sealed native replay retains its saved field-prop appearance profile after camera recall / final seek');
    check(await page.locator('#world-canvas').getAttribute('data-rifle-triangles') === '264'
      && Number(await page.locator('#world-canvas').getAttribute('data-rifle-count')) >= 2,
      'Sealed native replay retains the same player rifle meshes after final seek and camera recall');
    const finalFrame = await until(async () => { try { const row=JSON.parse(await fs.readFile(path.join(directory,'operator-'+session+'-latest-frame.json'),'utf8'));
      return row.packet.frame.phase==='Ended'?row.packet.frame:false; } catch { return false; } }, 'saved native final enemy poses');
    const rendered=JSON.parse(await page.locator('#world-canvas').getAttribute('data-enemy-poses'));
    check(finalInfo.header.enemyPresentationVersion===1 && finalFrame.enemies.some(e=>e.walking) && rendered.length===finalFrame.enemies.length && rendered.every(p=>{
      const e=finalFrame.enemies.find(e=>e.id===p.id), yaw=Math.atan2(e.forward.x,e.forward.z)*180/Math.PI,
        pitch=Math.max(-45,Math.min(45,-Math.asin(Math.max(-1,Math.min(1,e.forward.y)))*180/Math.PI)),stride=e.walking?Math.sin((finalFrame.tick%12)*Math.PI/6)*18:0;
      return e.hasPresentation && Math.abs(p.yaw-yaw)<.0001 && Math.abs(p.pitch-pitch)<.0001 && Math.abs(p.left-stride)<.0001 && Math.abs(p.right+stride)<.0001;
    }),'Sealed real-native replay renders exact recorded facing and opposite-leg pose at the frozen final tick');
    await page.screenshot({ path: path.join(evidence, 'native-replay.png'), fullPage: true });
    const stats = await api('/sessions/' + session + '/statistics');
    check(stats.origin === 'Simulation' && !stats.pendingTelemetry && stats.players.some(p => p.hitsReceived > 0), 'UI-controlled AI produces sealed actual-native combat statistics');
    check(stats.players.some(p => p.playerId === removedPeer.id && p.name === 'Peer 02') && stats.players.some(p => p.playerId === replacement.id), 'Final native replay / ledger preserves removed and replacement player history');
    check((await api('/sessions')).length === 0, 'Operator End releases the round'); check(errors.length === 0, 'No browser page errors');
    await fs.writeFile(path.join(evidence, 'summary.json'), JSON.stringify({ sessionId: session, mission, statistics: stats, camera, preciseCamera, precisePose, checks, browserRenderer: 'Chromium SwiftShader; native GPU rendering requires separate inspection', pageErrors: errors }, null, 2));
    await fs.writeFile(path.join(directory, 'end.request'), '');
    console.log('Operator/native UI checks passed: ' + checks);
  } catch (error) { await page.screenshot({ path: path.join(evidence, 'failure.png'), fullPage: true }).catch(()=>{}); throw error; }
  finally { await browser.close(); }
}
main().catch(error => { console.error(redactionTokens.reduce((text, token) => text.replaceAll(token, '[redacted]'), error.message)); process.exitCode = 1; });
