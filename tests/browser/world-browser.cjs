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
    await page.bringToFront();
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
    check(!await page.locator('#world-review').isVisible(), 'Live observation keeps frame review out of the playback controls');
    check(!await page.locator('#world-room-quick').isVisible(), 'Single-room observation keeps the existing compact controls');
    const before = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) > sequence, before);
    check((await page.locator('#world-statistics tr td').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80', 'Streamed per-frame combat statistics match the authoritative report prefix');
    const camera = await canvas.getAttribute('data-camera'); await page.locator('#world-camera').selectOption('top');
    check(await canvas.getAttribute('data-camera') !== camera, 'Streamed world supports the god-view camera preset');
    await page.locator('#world-room').selectOption('2');
    check((await page.locator('#world-statistics-heading').innerText()).startsWith('房間 2') && await page.locator('#world-camera').inputValue() === 'top',
      'The room selector scopes frame statistics and preserves the overhead preset');
    await page.locator('#world-room').selectOption('all');
    check((await canvas.getAttribute('data-camera')).split(',').every(value => Number.isFinite(Number(value))), 'All-room focus restores a finite camera instead of using an invalid room coordinate');
    await require('./camera-controls.cjs')({ page, check, screenshots });
    await require('./camera-ground-controls.cjs')({ page, check, screenshots });
    async function customCamera() {
      await page.locator('#world-camera').selectOption('top');
      await canvas.scrollIntoViewIfNeeded();
      const bounds = await canvas.boundingBox(), x = bounds.x + bounds.width / 2, y = bounds.y + bounds.height / 2;
      await page.mouse.move(x, y); await page.mouse.down({ button: 'right' }); await page.mouse.move(x + 45, y + 10, { steps: 4 }); await page.mouse.up({ button: 'right' });
      await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 30, y + 30, { steps: 4 }); await page.mouse.up();
      await page.mouse.dblclick(x + bounds.width * .05, y);
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
    check((await api(cameraRoute))[0].view.target[1] === .8, 'The authenticated bookmark stores the double-clicked room target at its viewing height');
    await page.locator('#world-camera').selectOption('overview'); await page.locator('#camera-recall').click();
    check(await canvas.getAttribute('data-camera') === savedPosition && await page.locator('#world-camera').inputValue() === 'free', 'Recalling a position restores its floor-located world target, angles and distance');
    const remembered = await context.newPage(); await remembered.setViewportSize({ width: 1440, height: 1080 });
    await remembered.bringToFront();
    // Observe only this page's first reload; no routing, headers, bodies, query
    // strings or credentials. Callback intervals are not network RTT.
    const requestStarted = performance.now(), requestRows = [], requests = new WeakMap();
    let requestTruncated = false;
    const at = () => performance.now() - requestStarted;
    const requestObserved = request => {
      const url = new URL(request.url());
      if (request.method() !== 'GET' || url.origin !== new URL(base).origin || !url.pathname.startsWith('/api/')) return;
      if (requestRows.length >= 128) { requestTruncated = true; return; }
      const row = { index: requestRows.length + 1, path: url.pathname, startedMilliseconds: at() }; requests.set(request, row); requestRows.push(row);
    };
    const responseObserved = response => { const row = requests.get(response.request()); if (row) { row.status = response.status(); row.responseMilliseconds = at(); } };
    const requestFinished = request => { const row = requests.get(request); if (row) row.finishedMilliseconds = at(); };
    const requestFailed = request => { const row = requests.get(request); if (row) { const code = request.failure()?.errorText || ''; row.failure = /^net::ERR_[A-Z0-9_]{1,64}$/.test(code) ? code : 'Other'; row.failedMilliseconds = at(); } };
    remembered.on('request', requestObserved); remembered.on('response', responseObserved); remembered.on('requestfinished', requestFinished); remembered.on('requestfailed', requestFailed);
    try {
      await remembered.goto(base + '/console/'); await remembered.locator('#login-key').fill(tokens.Master); await remembered.locator('#login-form button').click();
      await remembered.locator('#tab-world').click(); await remembered.locator('#world-recording option').waitFor({ state: 'attached' });
      await remembered.locator('#world-recording').selectOption(live.header.sessionId); await remembered.locator('#world-live').click();
      await remembered.locator('#camera-positions option').waitFor({ state: 'attached' }); await remembered.locator('#camera-recall').click();
      if (requestTruncated) throw new Error('Remembered camera request diagnostic exceeded 128 rows');
    } catch (error) {
      const diagnostic = await remembered.evaluate(() => ({ visibility: document.visibilityState,
        worldMessage: document.querySelector('#world-message').textContent,
        cameraMessage: document.querySelector('#camera-message').textContent,
        worldStatus: document.querySelector('#world-status').textContent,
        cameraOptions: document.querySelector('#camera-positions').options.length,
        worldSequence: document.querySelector('#world-canvas').dataset.sequence })).catch(() => ({ unavailable: true }));
      await fs.writeFile(path.join(screenshots, 'world-remembered-failure.json'), JSON.stringify(diagnostic, null, 2));
      await remembered.screenshot({ path: path.join(screenshots, 'world-remembered-failure.png'), fullPage: true, timeout: 5000 }).catch(() => {});
      throw error;
    } finally {
      remembered.off('request', requestObserved); remembered.off('response', responseObserved); remembered.off('requestfinished', requestFinished); remembered.off('requestfailed', requestFailed);
      await fs.writeFile(path.join(screenshots, 'world-remembered-requests.json'), JSON.stringify({ complete: !requestTruncated, truncated: requestTruncated, maximumRows: 128,
        scope: 'This page reload GET metadata only; not body decoding, complete dependencies, network RTT or cause proof', elapsedMilliseconds: at(), requests: requestRows }, null, 2));
    }
    check(await remembered.locator('#world-canvas').getAttribute('data-camera') === savedPosition, 'A freshly authenticated page reloads and recalls the persisted camera position');
    await remembered.bringToFront(); // Capture the intended tab, including with headless Chromium.
    await remembered.screenshot({ path: path.join(screenshots, 'world-camera-positions.png'), fullPage: true });
    let releaseRead, readAccepted;
    const readGate = new Promise(resolve => { releaseRead = resolve; }), requestedRead = new Promise(resolve => { readAccepted = resolve; });
    await remembered.route('**/world/cameras', async route => {
      const response = await route.fetch(); readAccepted(); await readGate; await route.fulfill({ response }).catch(() => {});
    });
    const stalledReadStates = [], stalledReadStart = process.hrtime.bigint(); let stalledReadComplete = false;
    async function stalledReadState(stage) {
      const state = await remembered.evaluate(() => ({ visibility: document.visibilityState, focused: document.hasFocus(),
        disabled: document.querySelector('#camera-refresh').disabled,
        error: document.querySelector('#camera-message').classList.contains('replay-error'),
        optionCount: document.querySelector('#camera-positions').options.length }));
      stalledReadStates.push({ stage, elapsedMilliseconds: Number(process.hrtime.bigint() - stalledReadStart) / 1e6, ...state });
    }
    try {
      await stalledReadState('before-click');
      await remembered.locator('#camera-refresh').click(); await requestedRead;
      await stalledReadState('response-held');
      // This is a DOM/control wait; it does not need the renderer's animation clock.
      await remembered.waitForFunction(() => !document.querySelector('#camera-refresh').disabled, null, { polling: 100, timeout: 15000 });
      await stalledReadState('button-enabled');
      check(await remembered.locator('#camera-message').evaluate(node => node.classList.contains('replay-error')) && await remembered.locator('#camera-positions option').count() === 1,
        'A stalled camera read times out, retains the last known collection and allows a new read');
      stalledReadComplete = true;
    } catch (error) {
      await stalledReadState('failure').catch(() => {});
      await remembered.screenshot({ path: path.join(screenshots, 'world-camera-stalled-read-failure.png'), fullPage: true, timeout: 5000 }).catch(() => {});
      throw error;
    } finally {
      releaseRead(); await remembered.unroute('**/world/cameras');
      await fs.writeFile(path.join(screenshots, 'world-camera-stalled-read.json'), JSON.stringify({ complete: stalledReadComplete, maximumRows: 4,
        scope: 'Bounded control-state metadata only; no input values, headers, bodies, credentials or cause proof', states: stalledReadStates }, null, 2));
    }
    let releaseSave, saveAccepted, finishHeldSave, heldSaveFailure, heldSaveRequests = 0;
    const saveGate = new Promise(resolve => { releaseSave = resolve; }), accepted = new Promise(resolve => { saveAccepted = resolve; });
    const heldSaveFinished = new Promise(resolve => { finishHeldSave = resolve; });
    await remembered.route('**/world/cameras/*', async route => {
      if (route.request().method() !== 'PUT') { await route.continue(); return; }
      heldSaveRequests++;
      try {
        const response = await route.fetch(); saveAccepted(); await saveGate; await route.fulfill({ response });
        finishHeldSave({ fulfilled: true });
      } catch (error) {
        heldSaveFailure = error; saveAccepted(); finishHeldSave({ fulfilled: false, error });
      }
    });
    // Keep the pending-save action on its intended renderer. Observe only the
    // bounded control state: no HTML, input values, credentials or request data.
    const saveDiagnostics = []; let saveDiagnosticsTruncated = false;
    async function saveState(stage) {
      const state = await remembered.evaluate(() => {
        const button = document.querySelector('#camera-save'), box = button.getBoundingClientRect(), style = getComputedStyle(button);
        return { visibility: document.visibilityState, focused: document.hasFocus(), activeId: document.activeElement?.id,
          disabled: button.disabled, hidden: button.hidden, display: style.display, cssVisibility: style.visibility,
          box: { x: box.x, y: box.y, width: box.width, height: box.height },
          cameraMessage: document.querySelector('#camera-message').textContent.slice(0, 500),
          refreshDisabled: document.querySelector('#camera-refresh').disabled,
          worldSequence: document.querySelector('#world-canvas').dataset.sequence,
          worldStatus: document.querySelector('#world-status').textContent.slice(0, 500) };
      }).catch(() => ({ unavailable: true }));
      if (saveDiagnostics.length < 8) saveDiagnostics.push({ stage, elapsedMilliseconds: at(), ...state });
      else saveDiagnosticsTruncated = true;
      await fs.writeFile(path.join(screenshots, 'world-pending-save-state.json'), JSON.stringify({
        scope: 'This camera-save control only; no original failure cause proof', maximumRows: 8, truncated: saveDiagnosticsTruncated, observations: saveDiagnostics }, null, 2));
    }
    try {
      await remembered.bringToFront(); await saveState('before-name');
      await remembered.locator('#camera-name').fill('離開前的待確認位置'); await saveState('before-click');
      await remembered.locator('#camera-save').click(); await saveState('after-click'); await accepted;
      if (heldSaveFailure) throw heldSaveFailure;
    } catch (error) {
      await saveState('failure');
      await remembered.screenshot({ path: path.join(screenshots, 'world-pending-save-failure.png'), fullPage: true, timeout: 5000 }).catch(() => {});
      releaseSave(); await remembered.unroute('**/world/cameras/*'); throw error;
    }
    const lateCamera = (await api(cameraRoute)).find(row => row.name === '離開前的待確認位置');
    await remembered.locator('#logout').click();
    check(await remembered.locator('#camera-positions option').count() === 0 && await remembered.locator('#camera-name').inputValue() === '', 'Logout clears camera names, saved positions and pending state from the page');
    check(await remembered.locator('#world-camera-x').inputValue() === '' && await remembered.locator('#world-camera-apply').isDisabled(), 'Logout clears the precise camera draft and disables applying it');
    let reloginFailure;
    try {
      await remembered.bringToFront(); await saveState('before-relogin');
      await remembered.locator('#login-key').fill(tokens.Room2); await remembered.locator('#login-form button').click();
      await remembered.locator('#tab-world').click(); await remembered.locator('#world-recording option').waitFor({ state: 'attached' });
      await remembered.locator('#world-recording').selectOption(live.header.sessionId); await remembered.locator('#world-live').click();
      await saveState('relogin-source-requested');
      await remembered.waitForFunction(() => !document.querySelector('#camera-save').disabled, null, { polling: 100, timeout: 30000 });
      await saveState('relogin-camera-enabled');
    } catch (error) {
      reloginFailure = error;
      await saveState('relogin-failure');
      await remembered.screenshot({ path: path.join(screenshots, 'world-relogin-camera-failure.png'), fullPage: true, timeout: 5000, mask: [remembered.locator('#login-key')] }).catch(() => {});
      throw error;
    } finally {
      releaseSave(); const delivery = await heldSaveFinished;
      await fs.writeFile(path.join(screenshots, 'world-pending-save-delivery.json'), JSON.stringify({
        fulfilled: delivery.fulfilled, requests: heldSaveRequests, errorName: delivery.error?.name?.slice(0, 64) || null,
        scope: 'This held original PUT callback only; fulfillment must succeed before the delayed-response isolation assertion' }, null, 2));
      await remembered.unroute('**/world/cameras/*');
      if (!reloginFailure && !delivery.fulfilled) throw delivery.error;
      if (!reloginFailure && heldSaveRequests !== 1) throw new Error('Expected exactly one held original camera PUT');
    }
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
    const interrupted = await api(`/sessions/${live.header.sessionId}/world`);
    const combat = (await api(`/sessions/${live.header.sessionId}`)).combatStream;
    await api(`/sessions/${live.header.sessionId}/report.csv`, 'GET', undefined, 'Master', 409);
    await page.locator('#world-speed').selectOption('4');
    await page.locator('#tab-operations').click();
    await page.locator('#include-ended').check();
    await page.locator('#session-select').selectOption(live.header.sessionId);
    await page.waitForFunction(({ shots, frames }) => document.querySelector('#closure-retained').textContent === `已接受 ${shots} 筆戰鬥資料 · 已保存 ${frames} 格錄製`,
      { shots: combat.acceptedSequence, frames: interrupted.acceptedSequence }, { polling: 100 });
    check(!(await page.locator('#closure-status').evaluate(panel => panel.classList.contains('closure-complete'))) && await page.locator('#export-report').isDisabled(),
      'Actual interrupted session reports accepted counts without declaring seals or enabling the final CSV');
    check(await page.locator('#player-review-select').isDisabled() && await page.locator('#open-player-review').isDisabled(),
      'An interrupted archive does not offer a sealed player review');
    await page.locator('#tab-world').click();
    await page.locator('#world-recording').selectOption(live.header.sessionId);
    check(await page.locator('#world-replay').innerText() === '回放已保存片段', 'An incomplete recording offers a bounded saved replay');
    const savedStart = page.waitForRequest(request => {
      const query = new URL(request.url()).searchParams;
      return query.get('throughFrame') === 'latest' && query.get('fromFrame') === '1';
    });
    await page.locator('#world-replay').click();
    await savedStart;
    const waitSavedEnd = () => page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '已到已保存片段尾端', null, { polling: 100 });
    await waitSavedEnd();
    check((await page.locator('#world-status').innerText()).includes('錄製未封存') && Number(await canvas.getAttribute('data-sequence')) === interrupted.acceptedSequence &&
      await page.locator('#world-frame-next').isDisabled(), 'Saved replay stops at the real interrupted tail and keeps the archive unsealed');
    await page.screenshot({ path: path.join(screenshots, 'world-saved-tail.png'), fullPage: true });
    const savedSearch = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/world/event-frames'));
    await page.locator('#world-event-search-here').click();
    const savedHits = await (await savedSearch).json();
    check(savedHits.throughFrame === interrupted.acceptedSequence && savedHits.afterFrame === interrupted.acceptedSequence - 1 &&
      savedHits.scannedThroughFrame === interrupted.acceptedSequence && savedHits.nextAfterFrame === null,
      'Current-frame search includes the original paused frame and preserves the fixed unsealed tail');
    await page.locator('#world-frame-back').click();
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence, interrupted.acceptedSequence - 1, { polling: 50 });
    const savedResume = page.waitForRequest(request => {
      const query = new URL(request.url()).searchParams;
      return query.get('throughFrame') === String(interrupted.acceptedSequence) && query.get('fromFrame') === String(interrupted.acceptedSequence - 1);
    });
    await page.locator('#world-pause').click(); await savedResume; await waitSavedEnd();
    check(true, 'Resuming after stepping back preserves the original saved replay boundary');
    await page.locator('#world-frame-extend').click();
    await page.waitForFunction(() => document.querySelector('#world-frame-message').textContent === '目前沒有新的保存快照。');
    check(Number(await canvas.getAttribute('data-sequence')) === interrupted.acceptedSequence
      && await page.locator('#world-frame-extend').isEnabled(), 'Checking an unchanged saved tail retains the paused frame and permits another check');
    const completeSource = demo('complete-world', 1), result = await completeSource.finished;
    check(result.code === 0, 'Native simulation produces a second complete persisted world: ' + result.error.slice(-300));
    const completed = JSON.parse(result.output);
    const archiveRoute = `/sessions/${completed.sessionId}/world`;
    const finalFrame = (await api(archiveRoute)).acceptedSequence;
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
    const back = page.locator('#world-frame-back'), next = page.locator('#world-frame-next');
    await page.waitForFunction(() => !document.querySelector('#world-frame-back').disabled);
    check(await next.isDisabled() && Number(await canvas.getAttribute('data-sequence')) === finalFrame,
      'Paused review stays at the final saved frame and disables advancing beyond it');
    check(!await page.locator('#world-frame-extend').isVisible(), 'The sealed replay does not offer to check for another saved tail');
    let eventFrame;
    for (let sequence = finalFrame - 1; sequence >= 1; sequence--) {
      const saved = await api(`${archiveRoute}/frames/${sequence}`);
      if (saved.packet.events.some(value => value.kind === 'PlayerDamaged')) { eventFrame = saved; break; }
    }
    if (!eventFrame) throw new Error('The completed combat fixture had no saved player damage');
    const eventSequence = eventFrame.packet.sequence;
    await page.locator('#world-review').scrollIntoViewIfNeeded();
    for (let sequence = finalFrame - 1; sequence >= eventSequence; sequence--) {
      await back.click();
      await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, sequence, { polling: 50 });
    }
    const rows = await page.locator('#world-events tr').allTextContents();
    check(rows.length === eventFrame.packet.events.length && rows.some(row => /玩家受傷.*World Simulation · 房間 2.*20$/.test(row)) &&
      (await page.locator('#world-frame-message').innerText()) === `已停在第 ${eventSequence} 格。`,
      'Real Previous clicks render the exact saved damage event, room, and amount');
    await page.screenshot({ path: path.join(screenshots, 'world-frame-review.png'), fullPage: true });
    await next.click();
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, eventSequence + 1, { polling: 50 });
    check(await back.isEnabled(), 'Next moves one exact frame forward and allows stepping back');
    await page.locator('#world-room').selectOption('2');
    await page.locator('#world-event-kind').selectOption('PlayerDamaged');
    await page.locator('#world-event-search-start').click();
    const hit = page.locator(`#world-event-search-results button[data-frame-sequence="${eventSequence}"]`);
    await hit.waitFor();
    const exactJump = page.waitForRequest(request => new URL(request.url()).pathname.endsWith(`/world/frames/${eventSequence}`));
    await hit.click(); await exactJump;
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, eventSequence, { polling: 50 });
    check(await page.locator('#world-room').inputValue() === '2' && (await page.locator('#world-events tr').allTextContents()).every(row => /玩家受傷.*房間 2/.test(row)) &&
      await page.locator('#world-events tr').count() === eventFrame.packet.events.filter(event => event.kind === 'PlayerDamaged').length,
      'Room-scoped search jumps to the exact original damage frame and filters its event rows');
    await page.screenshot({ path: path.join(screenshots, 'world-event-search.png'), fullPage: true });
    await page.locator('#world-event-kind').selectOption('ReloadCompleted');
    check(await page.locator('#world-event-search-results button').count() === 0 && await page.locator('#world-no-events').isVisible(),
      'Changing the kind clears obsolete search results and refreshes the paused frame');
    await page.locator('#world-event-kind').selectOption('');
    await page.locator('#world-room').selectOption('all');
    await next.click();
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, eventSequence + 1, { polling: 50 });
    const resumedRequest = page.waitForRequest(request => new URL(request.url()).pathname.endsWith('/world/watch') && new URL(request.url()).searchParams.get('fromFrame') === String(eventSequence + 1));
    await page.locator('#world-pause').click();
    await resumedRequest;
    check(true, 'Resume requests the selected frame by original sequence');
    await page.locator('#world-timeline').evaluate(input => { input.value = input.max; input.dispatchEvent(new Event('change', { bubbles: true })); });
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, finalFrame, { polling: 50 });
    await page.locator('#world-camera').selectOption('overview');
    await page.setViewportSize({ width: 390, height: 844 }); await page.waitForTimeout(100);
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1) && (await canvas.boundingBox()).width > 280, 'Streamed world controls and canvas fit a mobile viewport');
    await page.screenshot({ path: path.join(screenshots, 'world-replay-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1080 });
    const finalPlayer = (await api(`/sessions/${completed.sessionId}/statistics`)).players[0];
    await page.locator('#tab-operations').click();
    await page.locator('#refresh').click();
    await page.locator(`#session-select option[value="${completed.sessionId}"]`).waitFor({ state: 'attached' });
    await page.locator('#session-select').selectOption(completed.sessionId);
    await page.locator('#player-review-select').selectOption(finalPlayer.playerId);
    const reviewRoute = '/api' + archiveRoute;
    const watchPattern = `**${reviewRoute}/watch?**`;
    await page.route(watchPattern, async route => {
      const original = await route.fetch();
      const body = (await original.text()).replace(/"throughCombatSequence":(\d+)/,
        (_, sequence) => '"throughCombatSequence":' + (Number(sequence) + 1));
      await route.fulfill({ response: original, body });
    }, { times: 1 });
    await page.locator('#open-player-review').click();
    await page.waitForFunction(() => document.querySelector('#world-message').textContent.includes('戰鬥封存序號不同'));
    check(!await page.locator('#world-player').isVisible() && !await page.locator('#world-review-player-scope').isVisible(),
      'A substituted combat boundary does not open the sealed player review');
    await page.locator('#tab-operations').click();
    await page.locator('#player-review-select').selectOption(finalPlayer.playerId);
    const reviewWatch = page.waitForRequest(request => new URL(request.url()).pathname === reviewRoute + '/watch');
    const reviewSearch = page.waitForResponse(response => new URL(response.url()).pathname === reviewRoute + '/event-frames');
    await page.locator('#open-player-review').click();
    const watchQuery = new URL((await reviewWatch).url()).searchParams;
    const personal = await (await reviewSearch).json();
    await page.locator('#world-event-search-results button').first().waitFor();
    check(watchQuery.get('mode') === 'replay' && watchQuery.get('fromFrame') === String(finalFrame)
      && personal.playerId === finalPlayer.playerId && personal.throughFrame === finalFrame && personal.afterFrame === 0
      && Number(await canvas.getAttribute('data-sequence')) === finalFrame && await page.locator('#world-review-player-scope').isVisible()
      && (await page.locator('#world-statistics tr td').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80',
      'Final player statistics open the exact sealed tail and start a player-ID search of the original archive');
    await page.locator('#world-event-search-results button').first().click();
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, personal.frames[0].frameSequence, { polling: 50 });
    check((await page.locator('#world-events tr').count()) === personal.frames[0].matchCount
      && await page.locator('#world-review-player-scope').isVisible(), 'Jumping from personal results retains the selected player and original event count');
    await page.screenshot({ path: path.join(screenshots, 'world-player-debrief.png'), fullPage: true });
    await page.locator('#world-review-clear-player').click();
    check(!await page.locator('#world-review-player-scope').isVisible() && await page.locator('#world-event-search-results button').count() === 0,
      'Showing all players clears the prior personal results');
    const other = await context.newPage(); await other.goto(base + '/console/'); await other.locator('#login-key').fill(tokens.Room1); await other.locator('#login-form button').click();
    await other.locator('#tab-world').click(); await other.waitForFunction(() => document.querySelector('#world-message').textContent.includes('目前沒有'));
    check(await other.locator('#world-recording option').count() === 0, 'Room-scoped observer list reveals no foreign world'); await other.close();
    await page.locator('#tab-operations').click();
    check(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && !document.cookie), 'Streaming preserves memory-only credentials');
  } finally {
    for (const child of children) if (child.exitCode === null && child.signalCode === null) { const exited = new Promise(resolve => child.once('exit', resolve)); child.kill(); await exited; }
  }
};
