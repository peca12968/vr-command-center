const fs = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomUUID } = require('node:crypto');

module.exports = async function worldBrowser({ page, context, api, tokens, directory, root, base, screenshots, check }) {
  const keys = path.join(directory, 'world-keys.json'); await fs.writeFile(keys, JSON.stringify({ OperatorKeys: tokens }));
  const relay = process.env.VR_COMMAND_WORLD_RELAY_DLL || path.join(root, 'tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll');
  const children = [];
  function demo(name, seconds) {
    const child = spawn('dotnet', [relay, '--world-journal', path.join(directory, name + '.worldlog'), '--base-url', base, '--key-file', keys, '--demo-room', '2', '--seconds', String(seconds)], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '', error = ''; child.stdout.on('data', data => { output += data.toString(); }); child.stderr.on('data', data => { error += data.toString(); });
    const finished = new Promise(resolve => child.once('exit', code => resolve({ code, output, error }))); children.push(child);
    return { child, finished };
  }
  try {
    await page.setViewportSize({ width: 1440, height: 1080 });
    await page.locator('#tab-world').click(); await page.waitForFunction(() => document.querySelector('#world-message').textContent.includes('目前沒有'));
    check((await page.locator('#world-message').innerText()).includes('目前沒有'), 'World viewer reports an empty archive without inventing a recording');
    let source = demo('camera-world', 60);
    // Test credentials stay in this fixture's Node process, never window properties or storage.
    let entries;
    for (let attempt = 0; attempt < 100; attempt++) {
      entries = await api('/world-recordings');
      if (entries.some(info => info.acceptedSequence > 5)) break;
      if (source.child.exitCode !== null) throw new Error('World source exited: ' + (await source.finished).error);
      await page.waitForTimeout(50);
    }
    let live = entries[0];
    await page.locator('#world-refresh').click(); await page.locator('#world-recording option').waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(live.header.sessionId); await page.locator('#world-live').click();
    const canvas = page.locator('#world-canvas');
    await page.waitForFunction(() => Number(document.querySelector('#world-canvas').dataset.sequence) > 5 && Number(document.querySelector('#world-canvas').dataset.triangles) > 0);
    check((await page.locator('#world-status').innerText()).includes('Simulation') && (await page.locator('#world-message').innerText()).includes('無頭盔連接'), 'Real streamed world displays its simulation provenance and asset limits');
    check(await canvas.getAttribute('data-asset-set') === 'primitives-v1'
      && Number(await canvas.getAttribute('data-prop-triangles')) === live.header.props.length * 12,
      'A legacy streamed world retains its recorded primitive cover rather than receiving new field-prop art');
    check((await page.locator('#world-freshness').innerText()) === '正在接收快照' && (await page.locator('#world-actor-info').innerText()).includes('Simulated'), 'Live viewer distinguishes fresh snapshots and synthetic head/hand data');
    const before = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) > sequence, before);
    check((await page.locator('#world-statistics tr td').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80', 'Streamed per-frame combat statistics match the authoritative report prefix');
    const camera = await canvas.getAttribute('data-camera'); await page.locator('#world-camera').selectOption('top');
    check(await canvas.getAttribute('data-camera') !== camera, 'Streamed world supports the god-view camera preset');
    await page.locator('#world-room').selectOption('2'); await page.locator('#world-room').selectOption('all');
    check((await canvas.getAttribute('data-camera')).split(',').every(value => Number.isFinite(Number(value))), 'All-room focus restores a finite camera instead of using an invalid room coordinate');
    await require('./camera-controls.cjs')({ page, check, screenshots });
    async function customCamera() {
      await page.locator('#world-camera').selectOption('top');
      await canvas.scrollIntoViewIfNeeded();
      const bounds = await canvas.boundingBox(), x = bounds.x + bounds.width / 2, y = bounds.y + bounds.height / 2;
      await page.mouse.move(x, y); await page.mouse.down({ button: 'right' }); await page.mouse.move(x + 45, y + 10, { steps: 4 }); await page.mouse.up({ button: 'right' });
      await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 30, y + 30, { steps: 4 }); await page.mouse.up();
      return canvas.getAttribute('data-camera');
    }
    let savedPosition = await customCamera();
    const cameraRoute = '/sessions/' + live.header.sessionId + '/world/cameras';
    let loseSave = true, loseDelete = false; const saveBodies = [];
    await page.route('**/world/cameras/*', async route => {
      const method = route.request().method();
      if (method === 'PUT') saveBodies.push(route.request().postData());
      if ((method === 'PUT' && loseSave) || (method === 'DELETE' && loseDelete)) {
        if (method === 'PUT') loseSave = false; else loseDelete = false;
        await route.fetch(); await route.abort('failed');
      } else await route.continue();
    });
    await page.locator('#camera-name').fill('移除前的舊請求'); await page.locator('#camera-save').click();
    await page.locator('#camera-retry').waitFor({ state: 'visible' });
    check(await page.locator('#camera-name').isDisabled() && await page.locator('#world-recording').isDisabled(), 'Uncertain camera save preserves its original request and locks replacement settings');
    const acceptedCamera = (await api(cameraRoute))[0]; await api(cameraRoute + '/' + acceptedCamera.id, 'DELETE', undefined, 'Master', 204);
    await page.locator('#world-camera').selectOption('overview'); await page.locator('#camera-retry').click();
    await page.waitForFunction(() => document.querySelector('#camera-message').textContent.includes('已被其他視窗移除'));
    check(saveBodies[0] === saveBodies[1] && (await api(cameraRoute)).length === 0 && await page.locator('#camera-positions option').count() === 0,
      'Late browser save retry uses the original camera body and does not resurrect a position removed by another window');
    savedPosition = await customCamera();
    await page.locator('#camera-name').fill('<東側>沙包上方'); await page.locator('#camera-save').click();
    await page.locator('#camera-positions option').waitFor({ state: 'attached' });
    check(await page.locator('#camera-positions option').innerText() === '<東側>沙包上方' && await page.locator('#camera-positions img').count() === 0, 'Saved camera names render as literal text');
    await page.locator('#world-camera').selectOption('overview'); await page.locator('#camera-recall').click();
    check(await canvas.getAttribute('data-camera') === savedPosition && await page.locator('#world-camera').inputValue() === 'free', 'Recalling a position restores its fixed world target, angles and distance');
    const remembered = await context.newPage(); await remembered.setViewportSize({ width: 1440, height: 1080 });
    await remembered.goto(base + '/console/'); await remembered.locator('#login-key').fill(tokens.Master); await remembered.locator('#login-form button').click();
    await remembered.locator('#tab-world').click(); await remembered.locator('#world-recording option').waitFor({ state: 'attached' });
    await remembered.locator('#world-recording').selectOption(live.header.sessionId); await remembered.locator('#world-live').click();
    await remembered.locator('#camera-positions option').waitFor({ state: 'attached' }); await remembered.locator('#camera-recall').click();
    check(await remembered.locator('#world-canvas').getAttribute('data-camera') === savedPosition, 'A freshly authenticated page reloads and recalls the persisted camera position');
    await remembered.bringToFront(); // Capture the intended tab, including with headless Chromium.
    await remembered.screenshot({ path: path.join(screenshots, 'world-camera-positions.png'), fullPage: true });
    let releaseRead, readAccepted;
    const readGate = new Promise(resolve => { releaseRead = resolve; }), requestedRead = new Promise(resolve => { readAccepted = resolve; });
    await remembered.route('**/world/cameras', async route => {
      const response = await route.fetch(); readAccepted(); await readGate; await route.fulfill({ response }).catch(() => {});
    });
    await remembered.locator('#camera-refresh').click(); await requestedRead;
    await remembered.waitForFunction(() => !document.querySelector('#camera-refresh').disabled, null, { timeout: 15000 });
    check(await remembered.locator('#camera-message').evaluate(node => node.classList.contains('replay-error')) && await remembered.locator('#camera-positions option').count() === 1,
      'A stalled camera read times out, retains the last known collection and allows a new read');
    releaseRead(); await remembered.unroute('**/world/cameras');
    let releaseSave, saveAccepted;
    const saveGate = new Promise(resolve => { releaseSave = resolve; }), accepted = new Promise(resolve => { saveAccepted = resolve; });
    await remembered.route('**/world/cameras/*', async route => {
      if (route.request().method() !== 'PUT') { await route.continue(); return; }
      const response = await route.fetch(); saveAccepted(); await saveGate; await route.fulfill({ response });
    });
    await remembered.locator('#camera-name').fill('離開前的待確認位置'); await remembered.locator('#camera-save').click(); await accepted;
    const lateCamera = (await api(cameraRoute)).find(row => row.name === '離開前的待確認位置');
    await remembered.locator('#logout').click();
    check(await remembered.locator('#camera-positions option').count() === 0 && await remembered.locator('#camera-name').inputValue() === '', 'Logout clears camera names, saved positions and pending state from the page');
    check(await remembered.locator('#world-camera-x').inputValue() === '' && await remembered.locator('#world-camera-apply').isDisabled(), 'Logout clears the precise camera draft and disables applying it');
    await remembered.locator('#login-key').fill(tokens.Room2); await remembered.locator('#login-form button').click();
    await remembered.locator('#tab-world').click(); await remembered.locator('#world-recording option').waitFor({ state: 'attached' }); await remembered.locator('#world-live').click();
    await remembered.waitForFunction(() => !document.querySelector('#camera-save').disabled); releaseSave();
    await remembered.waitForTimeout(100);
    check(await remembered.locator('#camera-positions option').count() === 0 && !(await remembered.locator('#camera-message').innerText()).includes('離開前'), 'A delayed camera save response cannot repopulate a different operator after logout');
    await api(cameraRoute + '/' + lateCamera.id, 'DELETE', undefined, 'Master', 204); await remembered.close();
    await page.bringToFront();
    check((await api(cameraRoute, 'GET', undefined, 'Room2')).length === 0, 'An authorized room observer has a separate camera collection');
    loseDelete = true; await page.locator('#camera-remove').click(); await page.locator('#camera-retry').waitFor({ state: 'visible' });
    await page.locator('#camera-retry').click(); await page.waitForFunction(() => document.querySelector('#camera-positions').options.length === 0 && document.querySelector('#camera-retry').hidden);
    check((await api(cameraRoute)).length === 0, 'A lost remove response is safely retried without duplicating or restoring a camera');
    await page.unroute('**/world/cameras/*');
    await page.locator('#world-camera').selectOption('follow');
    await page.screenshot({ path: path.join(screenshots, 'world-live.png'), fullPage: true });
    check((await api('/sessions/' + live.header.sessionId)).players.length === 1, 'Observation creates no extra player seat');
    // Camera persistence and held-response checks may outlive the bounded 60-second
    // relay. Give capture-clock checks their own live source, not an ended archive.
    const cameraSession = live.header.sessionId;
    if (source.child.exitCode === null && source.child.signalCode === null) { source.child.kill(); await source.finished; }
    if ((await api('/sessions/' + cameraSession)).state !== 'Ended')
      await api('/sessions/' + cameraSession + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    source = demo('interrupted-world', 60);
    let clockWorld;
    for (let attempt = 0; attempt < 100; attempt++) {
      clockWorld = (await api('/world-recordings')).find(row => row.header.sessionId !== cameraSession && row.acceptedSequence > 5);
      if (clockWorld) break;
      if (source.child.exitCode !== null || source.child.signalCode !== null) throw new Error('Clock source exited before live observation');
      await page.waitForTimeout(50);
    }
    if (!clockWorld) throw new Error('Clock source did not publish its initial frames');
    live = clockWorld;
    await page.locator('#world-refresh').click();
    await page.locator(`#world-recording option[value="${live.header.sessionId}"]`).waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(live.header.sessionId); await page.locator('#world-live').click();
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '正在接收快照');
    check((await api('/sessions/' + live.header.sessionId)).state === 'Running' && source.child.exitCode === null && source.child.signalCode === null,
      'Capture-clock checks start from their own live bounded relay, not the completed camera fixture');
    await page.evaluate(() => {
      const original = window.fetch; window.worldClockMode = 'old'; window.restoreWorldFetch = () => { window.fetch = original; };
      window.fetch = async (...args) => {
        const response = await original(...args);
        if (!String(args[0]).includes('/world/watch') || !response.ok) return response;
        let buffer = ''; const decoder = new TextDecoder(), encoder = new TextEncoder();
        const body = response.body.pipeThrough(new TransformStream({ transform(bytes, controller) {
          buffer += decoder.decode(bytes, { stream: true }); let end;
          while ((end = buffer.indexOf('\n\n')) >= 0) {
            let block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
            if (/^event: (header|status)\n/.test(block)) {
              const value = JSON.parse(block.split('\ndata: ')[1]);
              value.header.captureStartedAtUtc = window.worldClockMode === 'unknown' ? '' : new Date(Date.now() + (window.worldClockMode === 'old' ? -60000 : 60000)).toISOString();
              block = block.split('\ndata: ')[0] + '\ndata: ' + JSON.stringify(value);
            }
            controller.enqueue(encoder.encode(block + '\n\n'));
          }
        } }));
        return new Response(body, { status: response.status, headers: response.headers });
      };
    });
    await page.locator('#world-live').click(); await page.waitForFunction(() => document.querySelector('#world-freshness').textContent.includes('過期'));
    const staleSequence = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) > sequence, staleSequence);
    check((await page.locator('#world-freshness').innerText()).includes('過期'), 'Newly received historical frames remain stale according to capture time');
    await page.screenshot({ path: path.join(screenshots, 'world-old-capture.png'), fullPage: true });
    await page.evaluate(() => { window.worldClockMode = 'unknown'; }); await page.locator('#world-live').click();
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '擷取時間未知');
    check(true, 'Legacy source without a capture clock is explicitly unknown instead of fresh');
    await page.evaluate(() => { window.worldClockMode = 'future'; }); await page.locator('#world-live').click();
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '來源時鐘未同步');
    check(true, 'Future source clock is not presented as current live data');
    await page.evaluate(() => window.restoreWorldFetch()); await page.locator('#world-live').click();
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '正在接收快照');
    check(true, 'Synchronized current source resumes a fresh live view after reconnecting');
    source.child.kill(); await source.finished;
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent.includes('過期'));
    check((await page.locator('#world-status').innerText()).includes('未封存'), 'Stopped source becomes visibly stale while its archive remains incomplete');
    await page.screenshot({ path: path.join(screenshots, 'world-stale.png'), fullPage: true });
    await api('/sessions/' + live.header.sessionId + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    const completeSource = demo('complete-world', 1), result = await completeSource.finished;
    check(result.code === 0, 'Native simulation produces a second complete persisted world: ' + result.error.slice(-300));
    const completed = JSON.parse(result.output);
    await page.locator('#world-refresh').click(); await page.locator(`#world-recording option[value="${completed.sessionId}"]`).waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(completed.sessionId);
    check(await page.locator('#world-camera-x').inputValue() === '' && await page.locator('#world-camera-apply').isDisabled(), 'Switching recordings clears the precise camera draft before reading a new world');
    await page.locator('#world-replay').click();
    await page.locator('#world-player').waitFor(); await page.locator('#world-speed').selectOption('4');
    await page.waitForFunction(() => !document.querySelector('#camera-save').disabled);
    check(await page.locator('#camera-positions option').count() === 0 && await page.locator('#camera-name').inputValue() === '', 'Switching recordings clears camera selection and draft names');
    await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('已結束') && document.querySelector('#world-status').textContent.includes('核對封存'));
    check((await page.locator('#world-statistics tr td').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80' && (await page.locator('#world-environment').innerText()).includes('Storm'), 'Persisted replay reaches the exact final statistics and recorded environment');
    await page.locator('#world-speed').selectOption('0.25');
    await page.locator('#world-timeline').evaluate(input => { input.value = '0'; input.dispatchEvent(new Event('change', { bubbles: true })); });
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.sequence === '1');
    await page.locator('#world-pause').click();
    const paused = await canvas.getAttribute('data-sequence'); await page.waitForTimeout(150);
    check(await canvas.getAttribute('data-sequence') === paused, 'Replay seek reads indexed early state and pause holds the current frame');
    await page.locator('#world-timeline').evaluate(input => { input.value = input.max; input.dispatchEvent(new Event('change', { bubbles: true })); });
    await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('已結束'));
    await page.locator('#world-camera').selectOption('overview');
    await page.setViewportSize({ width: 390, height: 844 }); await page.waitForTimeout(100);
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1) && (await canvas.boundingBox()).width > 280, 'Streamed world controls and canvas fit a mobile viewport');
    await page.screenshot({ path: path.join(screenshots, 'world-replay-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1080 });
    const other = await context.newPage(); await other.goto(base + '/console/'); await other.locator('#login-key').fill(tokens.Room1); await other.locator('#login-form button').click();
    await other.locator('#tab-world').click(); await other.waitForFunction(() => document.querySelector('#world-message').textContent.includes('目前沒有'));
    check(await other.locator('#world-recording option').count() === 0, 'Room-scoped observer list reveals no foreign world'); await other.close();
    await page.locator('#tab-operations').click();
    check(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && !document.cookie), 'Streaming preserves memory-only credentials');
  } finally {
    for (const child of children) if (child.exitCode === null && child.signalCode === null) { const exited = new Promise(resolve => child.once('exit', resolve)); child.kill(); await exited; }
  }
};
