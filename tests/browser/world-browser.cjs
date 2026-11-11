const fs = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const readCsv = require('./csv.cjs');

module.exports = async function worldBrowser({ page, context, api, tokens, directory, root, base, screenshots, check, liveWatchOnly, liveEventOnly }) {
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
    check((await page.locator('#world-status').innerText()).includes('Simulation')
      && (await page.locator('#world-message').innerText()).includes('頭手來源請見角色資訊'),
      'The live viewer keeps simulation authority separate from the recorded pose provenance');
    check(await canvas.getAttribute('data-asset-set') === 'primitives-v1'
      && Number(await canvas.getAttribute('data-prop-triangles')) === live.header.props.length * 12,
      'A legacy streamed world retains its recorded primitive cover rather than receiving new field-prop art');
    check((await page.locator('#world-freshness').innerText()) === '正在接收快照' && (await page.locator('#world-actor-info').innerText()).includes('Simulated'), 'Live viewer distinguishes fresh snapshots and synthetic head/hand data');
    check(!await page.locator('#world-review').isVisible(), 'Live observation keeps frame review out of the playback controls');
    check(!await page.locator('#world-room-quick').isVisible(), 'Single-room observation keeps the existing compact controls');
    const before = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) > sequence, before);
    check((await page.locator('#world-statistics tr td:not(:last-child)').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80', 'Streamed per-frame combat statistics match the authoritative report prefix');
    const camera = await canvas.getAttribute('data-camera'); await page.locator('#world-camera').selectOption('top');
    check(await canvas.getAttribute('data-camera') !== camera, 'Streamed world supports the god-view camera preset');
    await page.locator('#world-room').selectOption('2');
    check((await page.locator('#world-statistics-heading').innerText()).startsWith('房間 2') && await page.locator('#world-camera').inputValue() === 'top',
      'The room selector scopes frame statistics and preserves the overhead preset');
    {
      const liveEvent = page.locator('#world-live-event'), liveKind = page.locator('#world-live-event-kind');
      const eventStatus = page.locator('#world-event-search-status'), returnLive = page.locator('#world-recent');
      const eventNeighbor = `**/api/sessions/${live.header.sessionId}/world/event-neighbor?*`;
      const eventResponse = result => new URL(result.url()).pathname.endsWith('/world/event-neighbor');
      const waitLiveEvent = () => page.waitForFunction(() => !document.querySelector('#world-live-event').disabled, null, { polling: 100 });
      const overhead = await canvas.getAttribute('data-camera');
      await liveKind.selectOption('PlayerDamaged');
      const located = page.waitForResponse(eventResponse);
      await liveEvent.click();
      const locatedResponse = await located, hit = await locatedResponse.json();
      await eventStatus.filter({ hasText: `已跳到第 ${hit.frame.frameSequence} 格` }).waitFor();
      const query = new URL(locatedResponse.url()).searchParams;
      check(hit.streamId === live.header.streamId && query.get('roomId') === '2' && query.get('kind') === 'PlayerDamaged'
        && query.get('fromFrame') === query.get('throughFrame') && hit.frame.frameSequence < hit.throughFrame
        && Number(await canvas.getAttribute('data-sequence')) === hit.frame.frameSequence
        && await page.locator('#world-events tr').count() === hit.frame.matchCount
        && await canvas.getAttribute('data-camera') === overhead && await returnLive.innerText() === '返回即時觀戰',
      'Live event lookup freezes the visible tail and pauses at the exact original damage frame in the selected room');
      await page.screenshot({ path: path.join(screenshots, 'world-live-event.png'), fullPage: true });
      await returnLive.click(); await waitLiveEvent();
      await page.waitForFunction(tail => Number(document.querySelector('#world-canvas').dataset.sequence) > tail, hit.throughFrame, { polling: 100 });
      check(Number(await canvas.getAttribute('data-sequence')) > hit.throughFrame
        && await page.locator('#world-room').inputValue() === '2' && await canvas.getAttribute('data-camera') === overhead
        && await page.locator('#world-review').isHidden(), 'Returning from a located event resumes the same live room with its overhead view');

      await page.route(eventNeighbor, async route => {
        const original = await route.fetch();
        await route.fulfill({ response: original, json: { ...await original.json(), streamId: randomUUID() } });
      });
      const replaced = page.waitForRequest(eventResponse);
      await liveEvent.click();
      const rejectedTail = new URL((await replaced).url()).searchParams.get('throughFrame');
      await eventStatus.filter({ hasText: '尋找事件失敗' }).waitFor();
      check(await canvas.getAttribute('data-sequence') === rejectedTail && await returnLive.isEnabled(),
        'Live event lookup ignores a substituted source and keeps the original paused frame');
      await page.unroute(eventNeighbor);
      await returnLive.click(); await waitLiveEvent();
      await liveKind.selectOption('ReloadStarted');
      const missing = page.waitForResponse(eventResponse);
      await liveEvent.click();
      const missingResult = await (await missing).json();
      await eventStatus.filter({ hasText: '沒有上一筆符合條件的事件' }).waitFor();
      check(missingResult.frame === null && Number(await canvas.getAttribute('data-sequence')) === missingResult.throughFrame
        && await returnLive.isEnabled() && await liveEvent.isHidden(), 'No matching live event preserves the visible saved frame and the return action');
      await returnLive.click(); await waitLiveEvent();
      await liveKind.selectOption('');
      await page.setViewportSize({ width: 390, height: 850 });
      check(await page.locator('#world-live-event-tools').evaluate(node => node.scrollWidth <= node.clientWidth),
        'The live event selector and action fit a mobile console');
      await page.setViewportSize({ width: 1440, height: 1080 });
    }
    if (liveEventOnly) return;
    const { checkLiveMetadata, checkLiveWatch } = require('./live-watch-fault.cjs');
    await checkLiveMetadata({ page, base, live, api, canvas, check });
    await checkLiveWatch({ page, base, live, api, canvas, screenshots, check, extended: liveWatchOnly });
    if (liveWatchOnly) return;
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
    check(await page.locator('#player-review-select').isDisabled() && await page.locator('#open-player-review').isDisabled()
      && await page.locator('#open-player-damage').isDisabled(),
      'An interrupted archive does not offer a sealed player review');
    const roomReplay = await context.newPage();
    try {
      await roomReplay.goto(base + '/console/');
      await roomReplay.locator('#login-key').fill(tokens.Room2);
      await roomReplay.locator('#login-form button').click();
      await roomReplay.locator('#include-ended').check();
      await roomReplay.locator('#session-select').selectOption(live.header.sessionId);
      const closureReplay = roomReplay.waitForRequest(request => {
        const { pathname, searchParams } = new URL(request.url());
        return pathname === `/api/sessions/${live.header.sessionId}/world/watch` && searchParams.get('mode') === 'replay'
          && searchParams.get('observerRoomId') === '2' && searchParams.get('fromFrame') === '1'
          && searchParams.get('throughFrame') === String(interrupted.acceptedSequence);
      });
      await roomReplay.locator('#open-closure-replay').click();
      await closureReplay;
      await roomReplay.waitForFunction(tail => Number(document.querySelector('#world-canvas').dataset.sequence) === tail
        && document.querySelector('#world-freshness').textContent === '已到已保存片段尾端', interrupted.acceptedSequence, { polling: 100 });
      const status = await roomReplay.locator('#world-status').innerText();
      check(status.includes('錄製未封存') && status.includes('僅接收房間 2'),
        'Room controller closure replays the exact scoped saved prefix from frame one without a seal');
      await roomReplay.locator('#world-player').screenshot({ path: path.join(screenshots, 'closure-saved-room-replay.png') });
    } finally { await roomReplay.close(); await page.bringToFront(); }
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
    const waitFrame = sequence => page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, sequence, { polling: 50 });
    const clipStart = page.locator('#world-clip-start'), clipEnd = page.locator('#world-clip-end'), clipPlay = page.locator('#world-clip-play');
    const clipStatus = page.locator('#world-clip-status');
    const waitClipEnd = () => clipStatus.filter({ hasText: '已到片段終點' }).waitFor();
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
    await page.locator('#world-frame-back').click(); await waitFrame(interrupted.acceptedSequence - 1);
    await page.locator('#world-frame-back').click(); await waitFrame(interrupted.acceptedSequence - 2);
    await clipStart.click();
    check(await clipEnd.isDisabled() && await clipPlay.isDisabled(), 'A saved replay interval needs an end after its start');
    await page.locator('#world-frame-next').click(); await waitFrame(interrupted.acceptedSequence - 1);
    await clipEnd.click(); await clipPlay.click(); await waitClipEnd();
    check(Number(await canvas.getAttribute('data-sequence')) === interrupted.acceptedSequence - 1
      && (await page.locator('#world-status').innerText()).includes(`已保存片段至第 ${interrupted.acceptedSequence} 格`)
      && await page.locator('#world-frame-next').isEnabled(),
      'A marked interval stops before the unsealed boundary without replacing the original fixed tail');
    await page.locator('#world-frame-next').click(); await waitFrame(interrupted.acceptedSequence);
    check(await page.locator('#world-frame-extend').isEnabled(), 'Review can still reach and extend the original saved tail after interval playback');
    const completeSource = demo('complete-world', 1), result = await completeSource.finished;
    check(result.code === 0, 'Native simulation produces a second complete persisted world: ' + result.error.slice(-300));
    const completed = JSON.parse(result.output);
    const archiveRoute = `/sessions/${completed.sessionId}/world`;
    const archiveInfo = await api(archiveRoute), finalFrame = archiveInfo.acceptedSequence;
    const quickPage = await context.newPage();
    try {
      await quickPage.bringToFront();
      await quickPage.goto(base + '/console/');
      await quickPage.locator('#login-key').fill(tokens.Room2);
      await quickPage.locator('#login-form button').click();
      await quickPage.locator('#tab-world').click();
      await quickPage.locator('#world-recording').selectOption(completed.sessionId);
      await quickPage.locator('#world-live').click();
      const quick = quickPage.locator('#world-recent'), quickCanvas = quickPage.locator('#world-canvas');
      const ready = () => quickPage.waitForFunction(() => !document.querySelector('#world-recent').disabled, null, { polling: 100 });
      const watch = new RegExp(`${archiveRoute}/watch\\?mode=replay&`);
      await ready();
      const first = await api(archiveRoute + '/frames/1');
      await quickPage.route(watch, route => route.fulfill({ status: 200, contentType: 'text/event-stream', body:
        `event: header\ndata: ${JSON.stringify({ ...archiveInfo, header: { ...archiveInfo.header, streamId: randomUUID() } })}\n\n` +
        `event: frame\ndata: ${JSON.stringify(first)}\n\n` }));
      await quick.click();
      await quickPage.locator('#world-message').filter({ hasText: '回應的錄製來源不同' }).waitFor();
      check(Number(await quickCanvas.getAttribute('data-sequence')) === finalFrame && await quick.innerText() === '返回即時觀戰',
        'Room operator instant replay rejects a replaced stream before displaying its frame and can return');
      await quickPage.unroute(watch);
      await quick.click();
      await ready();
      await quickPage.locator('#world-speed').selectOption('4');
      const shortWatch = quickPage.waitForRequest(request => watch.test(request.url()));
      await quick.click();
      const query = new URL((await shortWatch).url()).searchParams;
      await quickPage.locator('#world-freshness').filter({ hasText: '已到即時回看尾端' }).waitFor();
      check(archiveInfo.durationMilliseconds <= 10000 && query.get('fromFrame') === '1' && query.get('throughFrame') === String(finalFrame)
        && Number(await quickCanvas.getAttribute('data-sequence')) === finalFrame && await quickPage.locator('#world-frame-next').isDisabled()
        && (await quickPage.locator('#world-statistics tr td:not(:last-child)').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80',
      'Instant replay shorter than ten seconds includes the first exact frame and stops at the original tail with its combat totals');
      await quickPage.locator('#world-frame-back').click();
      await quickPage.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence, finalFrame - 1);
      await quick.click();
      await ready();
      check(Number(await quickCanvas.getAttribute('data-sequence')) === finalFrame && !await quickPage.locator('#world-review').isVisible(),
        'Return to observation uses the original stream after manually stepping back');
      await quick.click();
      await quickPage.locator('#tab-operations').click();
      await quickPage.locator('#tab-world').click();
      check(!await quick.isVisible(), 'Leaving observation clears the instant replay return action');
    } finally { await quickPage.close(); await page.bringToFront(); }
    await page.locator('#world-refresh').click(); await page.locator(`#world-recording option[value="${completed.sessionId}"]`).waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(completed.sessionId);
    check(await page.locator('#world-camera-x').inputValue() === '' && await page.locator('#world-camera-apply').isDisabled(), 'Switching recordings clears the precise camera draft before reading a new world');
    await page.locator('#world-replay').click();
    await page.locator('#world-player').waitFor(); await page.locator('#world-speed').selectOption('4');
    await page.waitForFunction(() => !document.querySelector('#camera-save').disabled);
    check(await page.locator('#camera-positions option').count() === 0 && await page.locator('#camera-name').inputValue() === '', 'Switching recordings clears camera selection and draft names');
    await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('已結束') && document.querySelector('#world-status').textContent.includes('核對封存'));
    check((await page.locator('#world-statistics tr td:not(:last-child)').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80' && (await page.locator('#world-environment').innerText()).includes('Storm'), 'Persisted replay reaches the exact final statistics and recorded environment');
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
    check(await clipPlay.isDisabled() && !(await clipStatus.innerText()).includes('起點 第'), 'Changing recordings clears the previous interval markers');
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
    const eventStatus = page.locator('#world-event-search-status');
    const previousEvent = page.locator('#world-event-previous'), nextEvent = page.locator('#world-event-next');
    await nextEvent.click();
    await eventStatus.filter({ hasText: '保存範圍內沒有下一筆符合條件的事件' }).waitFor();
    check(Number(await canvas.getAttribute('data-sequence')) === eventSequence, 'Next event never repeats the current event or exceeds the saved tail');
    await next.click();
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, eventSequence + 1, { polling: 50 });
    const neighbor = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/world/event-neighbor'));
    await previousEvent.click();
    await eventStatus.filter({ hasText: `已跳到第 ${eventSequence} 格` }).waitFor();
    const query = new URL((await neighbor).url()).searchParams;
    check(query.get('direction') === 'previous' && query.get('roomId') === '2' && query.get('kind') === 'PlayerDamaged'
      && query.get('throughFrame') === String(finalFrame) && Number(await canvas.getAttribute('data-sequence')) === eventSequence,
      'Previous event preserves the room and event kind and jumps to the original saved frame');
    await page.screenshot({ path: path.join(screenshots, 'world-event-neighbor.png'), fullPage: true });
    await clipStart.click();
    for (let sequence = eventSequence + 1; sequence <= finalFrame - 1; sequence++) {
      await next.click(); await waitFrame(sequence);
    }
    const clipTail = finalFrame - 1;
    await clipEnd.click();
    const clipStats = page.locator('#world-clip-stats-results');
    const clipStatsReply = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/world/clip-statistics'));
    await page.locator('#world-clip-stats-read').click();
    const statsResponse = await clipStatsReply;
    const clipReport = await statsResponse.json();
    await clipStats.waitFor();
    check(statsResponse.status() === 200 && clipReport.fromFrame === eventSequence && clipReport.throughFrame === clipTail
      && clipReport.roomId === 2 && clipReport.players.every(row => row.roomId === 2)
      && clipReport.players.some(row => row.hitsReceived > 0 && row.damageTaken > 0)
      && Number(await canvas.getAttribute('data-sequence')) === clipTail,
    'Clip statistics count original damage on the inclusive boundary without seeking or changing room');
    const clipExport = page.locator('#world-clip-stats-export'), clipExportStatus = page.locator('#world-clip-stats-export-status');
    const csvPath = new URL(statsResponse.url()).pathname + '.csv';
    const exportReply = page.waitForResponse(response => new URL(response.url()).pathname === csvPath);
    const clipExported = page.waitForEvent('download');
    await clipExport.click();
    const csvResponse = await exportReply, clipDownload = await clipExported;
    const raw = await fs.readFile(await clipDownload.path()), parsed = readCsv(raw);
    const clipQuery = new URL(csvResponse.url()).searchParams;
    const binaryReply = await fetch(csvResponse.url(), { headers: { Authorization: 'Bearer ' + tokens.Master } });
    // Chromium's network inspector can report an empty body for this attachment.
    const binary = Buffer.from(await binaryReply.arrayBuffer());
    const observed = await csvResponse.body().catch(() => null);
    await fs.writeFile(path.join(screenshots, 'world-clip-statistics-byte-readback.json'), JSON.stringify({
      download: raw.length, binary: binary.length, browserResponse: observed?.length ?? null,
      binaryExact: raw.equals(binary), browserResponseExact: observed ? raw.equals(observed) : null,
      downloadBom: raw.subarray(0, 3).toString('hex'), browserResponsePrefix: observed?.subarray(0, 3).toString('hex') ?? null
    }, null, 2));
    check(csvResponse.status() === 200 && csvResponse.headers()['cache-control'] === 'no-store'
      && binaryReply.status === 200 && raw.subarray(0, 3).toString('hex') === 'efbbbf' && raw.equals(binary)
      && clipDownload.suggestedFilename() === `vr-command-clip-statistics-v1-${clipReport.sessionId}-${eventSequence}-${clipTail}-room-02.csv`
      && clipQuery.get('streamId') === clipReport.streamId && clipQuery.get('roomId') === '2'
      && parsed.length === clipReport.players.length && parsed.every((row, index) => {
        const player = clipReport.players[index];
        return row.sessionId === clipReport.sessionId && row.streamId === clipReport.streamId
          && row.fromFrame === String(eventSequence) && row.throughFrame === String(clipTail) && row.reportRoomId === '2'
          && row.playerId === player.playerId && Number(row.damageTaken) === player.damageTaken && Number(row.matchedShots) === player.matchedShots;
      }), 'Clip CSV download preserves the exact authorized room, stream, bounds and saved counters');
    check((await clipStats.locator('tbody tr td:nth-last-child(2)').allTextContents()).join(',')
      === clipReport.players.map(row => row.matchedShots).join(','), 'Clip statistics display the actual hit numerator separately from recorded hits');
    await fs.writeFile(path.join(screenshots, 'world-clip-statistics.csv'), raw);
    await page.route(url => url.pathname === csvPath, route => route.fulfill({ status: 200, contentType: 'text/csv-fake', body: 'fixture' }), { times: 1 });
    await clipExport.click();
    await clipExportStatus.filter({ hasText: '無法下載片段戰績' }).waitFor();
    check(await clipExport.isEnabled() && await clipStats.isVisible(), 'Invalid clip CSV MIME leaves the verified table and allows a retry');

    const gate = Promise.withResolvers(), captured = Promise.withResolvers(), delivered = Promise.withResolvers();
    const csvRoute = url => url.pathname === csvPath;
    const holdCsv = async route => {
      try {
        const response = await route.fetch(); captured.resolve(response.status());
        await gate.promise; await route.fulfill({ response });
      } catch { captured.resolve(null); }
      finally { delivered.resolve(); }
    };
    let lateDownloads = 0;
    const countDownload = () => lateDownloads++;
    page.on('download', countDownload);
    await page.route(csvRoute, holdCsv);
    try {
      await clipExport.click();
      const observed = await captured.promise;
      await page.locator('#world-room').selectOption('all');
      gate.resolve(); await delivered.promise;
      check(observed === 200 && await clipStats.isHidden() && await clipExport.isDisabled() && lateDownloads === 0,
        'Changing the replay room invalidates a previously authorized clip CSV before download');
    } finally {
      gate.resolve(); await page.unroute(csvRoute, holdCsv); page.off('download', countDownload);
    }
    await page.locator('#world-room').selectOption('2');
    const clipWatch = (start, rate) => page.waitForRequest(request => {
      const query = new URL(request.url()).searchParams;
      return query.get('fromFrame') === String(start) && query.get('throughFrame') === String(clipTail) && query.get('rate') === rate;
    });
    await page.evaluate(() => {
      document.querySelector('#world-clip-play').click();
      document.querySelector('#world-pause').click();
    });
    check(Number(await canvas.getAttribute('data-sequence')) === clipTail && (await clipStatus.innerText()).includes('片段已暫停'),
      'Pausing before the first streamed frame keeps the visible frame and the requested interval start');
    await page.locator('#world-speed').selectOption('0.5');
    const startedClip = clipWatch(eventSequence, '0.5');
    await page.locator('#world-pause').click(); await startedClip;
    await waitFrame(eventSequence);
    await page.locator('#world-pause').click();
    await clipStatus.filter({ hasText: '片段已暫停' }).waitFor();
    const pausedClip = Number(await canvas.getAttribute('data-sequence'));
    check(pausedClip >= eventSequence && pausedClip < clipTail && await clipPlay.isEnabled(), 'Pausing an interval holds a frame inside its original range');
    await page.locator('#world-speed').selectOption('4');
    check(Number(await canvas.getAttribute('data-sequence')) === pausedClip, 'Changing speed while paused keeps the original frame');
    const resumedClip = clipWatch(pausedClip, '4');
    await page.locator('#world-pause').click(); await resumedClip; await waitClipEnd();
    check(Number(await canvas.getAttribute('data-sequence')) === clipTail && await next.isEnabled()
      && (await page.locator('#world-status').innerText()).includes('錄製已核對封存') && await page.locator('#world-room').inputValue() === '2',
      'Interval ends at the exact frame while preserving the full sealed archive, selected room and access to later frames');
    await page.screenshot({ path: path.join(screenshots, 'world-replay-interval.png'), fullPage: true });
    await page.route('**/world/watch?**', async route => {
      const original = await route.fetch();
      const body = (await original.text()).split('event: saved-end\n')[0];
      await route.fulfill({ response: original, body });
    }, { times: 1 });
    await clipPlay.click();
    await page.waitForFunction(() => document.querySelector('#world-message').textContent.includes('尚未讀到已保存片段尾端'), null, { polling: 100 });
    check(!(await clipStatus.innerText()).includes('已到片段終點') && await clipPlay.isEnabled(),
      'A stream missing the terminal acknowledgement does not mark the interval finished and remains retryable');
    const repeatedClip = clipWatch(eventSequence, '4');
    await clipPlay.click(); await repeatedClip; await waitClipEnd();
    check(Number(await canvas.getAttribute('data-sequence')) === clipTail, 'Retrying the interval repeats from the original start and finishes at the original end');
    const savedRoute = archiveRoute + '/clips', savedPicker = page.locator('#saved-clip-select');
    const clipName = '掩體 <東側> 複盤 ' + 'W'.repeat(45);
    const putRequests = [];
    const captureClipWrite = request => {
      if (request.method() === 'PUT' && new URL(request.url()).pathname.startsWith('/api' + savedRoute + '/'))
        putRequests.push({ path: new URL(request.url()).pathname, body: request.postData() });
    };
    page.on('request', captureClipWrite);
    await page.route('**/world/clips/*', async route => {
      const accepted = await route.fetch();
      if (!accepted.ok()) { await route.fulfill({ response: accepted }); return; }
      await route.abort('failed');
    }, { times: 1 });
    await page.locator('#saved-clip-name').fill(clipName);
    await page.locator('#saved-clip-save').click();
    await page.locator('#saved-clip-retry').waitFor();
    const originalClip = (await api(savedRoute, 'GET', undefined, 'Room2')).clips[0];
    check(originalClip.name === clipName && originalClip.startFrame === eventSequence && originalClip.endFrame === clipTail,
      'An accepted save with a lost response is readable in the same room with the exact original boundaries');
    await page.locator('#saved-clip-retry').click();
    await savedPicker.locator(`option[value="${originalClip.id}"]`).waitFor({ state: 'attached' });
    page.off('request', captureClipWrite);
    check(putRequests.length === 2 && JSON.stringify(putRequests[0]) === JSON.stringify(putRequests[1])
      && (await api(savedRoute)).clips.length === 1 && (await savedPicker.locator('option').innerText()).includes(clipName),
      'Retry uses the same ID and body, keeps one clip, and renders its name as text');
    const exportClip = page.locator('#saved-clip-export');
    await page.route('**/player-replay.json', async route => {
      const response = await route.fetch();
      const file = await response.json();
      file.header.streamId = randomUUID();
      await route.fulfill({ response, json: file });
    }, { times: 1 });
    await exportClip.click();
    await page.locator('#saved-clip-message').filter({ hasText: '下載回覆的錄製來源或範圍不符。' }).waitFor();
    check(await exportClip.isEnabled(), 'A replaced recording identity is rejected before downloading and remains retryable');
    const downloadStarted = page.waitForEvent('download');
    await exportClip.click();
    const download = await downloadStarted;
    const bytes = await fs.readFile(await download.path());
    const exported = JSON.parse(bytes);
    const originals = await Promise.all(Array.from({ length: clipTail - eventSequence + 1 },
      (_, offset) => api(`${archiveRoute}/frames/${eventSequence + offset}`)));
    check(download.suggestedFilename() === `vr-command-replay-${originalClip.id}.json`
      && isDeepStrictEqual(exported.packets, originals.map(frame => frame.packet))
      && !JSON.stringify(exported).includes('"statistics"'), 'Master downloads exactly the accepted saved interval without roster statistics');
    const playerContext = await context.browser().newContext({ viewport: { width: 390, height: 844 } });
    try {
      const player = await playerContext.newPage(), requests = [];
      player.on('request', request => {
        if (new URL(request.url()).pathname.startsWith('/api') || request.headers().authorization) requests.push(request.url());
      });
      await player.goto(base + '/console/player-replay.html');
      const input = player.locator('#player-replay-file'), note = player.locator('#player-replay-message');
      await input.setInputFiles({ name: download.suggestedFilename(), mimeType: 'application/json', buffer: bytes });
      await note.filter({ hasText: `已載入 ${exported.packets.length} 格。` }).waitFor();
      const position = player.locator('#player-replay-frame');
      const replayCanvas = player.locator('#replay-canvas');
      check((await player.locator('#player-replay-title').innerText()) === clipName
        && (await position.innerText()).startsWith(`第 ${eventSequence} 格`) && await player.locator('#player-replay-back').isDisabled()
        && await player.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        'Player opens the exact first frame on a small viewport without operator login');
      check(Number((await replayCanvas.getAttribute('data-camera')).split(',')[1]) < 40
        && Number(await replayCanvas.getAttribute('data-triangles')) > 0, 'The first room is framed using the visible canvas dimensions');
      await player.locator('#player-replay-next').click();
      check((await position.innerText()).startsWith(`第 ${eventSequence + 1} 格`), 'Player can step to the next saved frame');
      await player.locator('#player-replay-play').click();
      await position.filter({ hasText: `第 ${clipTail} 格` }).waitFor();
      check(await player.locator('#player-replay-next').isDisabled()
        && await player.locator('#player-replay-play').innerText() === '播放' && requests.length === 0,
        'Player stops at the exact exported boundary and sends no API requests');
      await player.screenshot({ path: path.join(screenshots, 'player-replay-mobile.png'), fullPage: true });
      const damaged = { ...exported, packets: exported.packets.slice(1) };
      await input.setInputFiles({ name: 'damaged.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(damaged)) });
      await note.filter({ hasText: '無法辨識回放檔' }).waitFor();
      check(await player.locator('#player-replay-view').isHidden() && requests.length === 0,
        'A truncated local file clears the old display without making a request');
    } finally {
      await playerContext.close();
      await page.bringToFront();
    }
    const roomClip = await context.newPage();
    try {
      await roomClip.goto(base + '/console/');
      await roomClip.locator('#login-key').fill(tokens.Room2);
      await roomClip.locator('#login-form button').click();
      await roomClip.locator('#tab-world').click();
      await roomClip.locator('#world-recording').selectOption(completed.sessionId);
      await roomClip.locator('#world-replay').click();
      const roomLoad = roomClip.locator('#saved-clip-load');
      await roomLoad.click();
      check(await roomClip.locator('#saved-clip-edit').isHidden() && await roomClip.locator('#saved-clip-export').isHidden()
        && (await roomClip.locator('#world-clip-status').innerText()).includes(`起點 第 ${eventSequence} 格`),
        'A new authorized room console loads the shared marks without editing controls');
      await roomClip.locator('#world-clip-play').click();
      await roomClip.locator('#world-clip-status').filter({ hasText: '已到片段終點' }).waitFor();
      check(Number(await roomClip.locator('#world-canvas').getAttribute('data-sequence')) === clipTail,
        'The room console plays the saved shared range to the original frame');
      await roomClip.locator('#saved-clip-select').screenshot({ path: path.join(screenshots, 'world-shared-replay-clip.png') });
    } finally {
      await roomClip.close();
      await page.bringToFront();
    }
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#saved-clip-remove').click();
    await page.locator('#saved-clip-message').filter({ hasText: '已移除片段。' }).waitFor();
    check(await savedPicker.locator('option').count() === 0 && (await api(savedRoute)).clips.length === 0
      && Number(await canvas.getAttribute('data-sequence')) === clipTail, 'Removing the shared entry leaves the selected recorded frame intact');
    await page.locator('#world-clip-clear').click();
    check(await clipPlay.isDisabled() && Number(await canvas.getAttribute('data-sequence')) === clipTail, 'Clearing interval markers leaves the current saved frame visible');
    await previousEvent.click();
    await eventStatus.filter({ hasText: `已跳到第 ${eventSequence} 格` }).waitFor();
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
      && (await page.locator('#world-statistics tr td:not(:last-child)').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80',
      'Final player statistics open the exact sealed tail and start a player-ID search of the original archive');
    await page.locator('#world-event-search-results button').first().click();
    await page.waitForFunction(value => Number(document.querySelector('#world-canvas').dataset.sequence) === value, personal.frames[0].frameSequence, { polling: 50 });
    check((await page.locator('#world-events tr').count()) === personal.frames[0].matchCount
      && await page.locator('#world-review-player-scope').isVisible(), 'Jumping from personal results retains the selected player and original event count');
    const personalNext = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/world/event-neighbor'));
    await nextEvent.click();
    const personalHit = await (await personalNext).json();
    await eventStatus.filter({ hasText: `已跳到第 ${personalHit.frame.frameSequence} 格` }).waitFor();
    check(personalHit.playerId === finalPlayer.playerId && personalHit.frame.frameSequence > personal.frames[0].frameSequence
      && Number(await canvas.getAttribute('data-sequence')) === personalHit.frame.frameSequence,
      'Next event follows the original selected player beyond the current frame');
    await page.screenshot({ path: path.join(screenshots, 'world-player-debrief.png'), fullPage: true });
    await page.locator('#world-review-clear-player').click();
    check(!await page.locator('#world-review-player-scope').isVisible() && await page.locator('#world-event-search-results button').count() === 0,
      'Showing all players clears the prior personal results');
    const damageShortcut = page.locator('#open-player-damage');
    const chooseFinalPlayer = async () => {
      await page.locator('#tab-operations').click();
      await page.locator('#player-review-select').selectOption(finalPlayer.playerId);
    };
    await chooseFinalPlayer();
    await page.route(`**${reviewRoute}/frames/${eventSequence}`, async route => {
      const original = await route.fetch();
      const body = await original.json();
      body.packet.events = body.packet.events.filter(event => event.kind !== 'PlayerDamaged');
      await route.fulfill({ response: original, json: body });
    }, { times: 1 });
    await damageShortcut.click();
    await eventStatus.filter({ hasText: '讀取事件快照失敗' }).waitFor();
    check(Number(await canvas.getAttribute('data-sequence')) === finalFrame && await page.locator('#world-no-events').isVisible(),
      'The latest damage shortcut rejects a saved frame with the right sequence but no matching damage');
    await chooseFinalPlayer();
    const damageRequest = page.waitForRequest(request => new URL(request.url()).pathname === `${reviewRoute}/event-neighbor`);
    await damageShortcut.click();
    const damageQuery = new URL((await damageRequest).url()).searchParams;
    await eventStatus.filter({ hasText: `已跳到第 ${eventSequence} 格` }).waitFor();
    check(damageQuery.get('playerId') === finalPlayer.playerId && damageQuery.get('direction') === 'previous'
      && damageQuery.get('kind') === 'PlayerDamaged' && damageQuery.get('throughFrame') === String(finalFrame)
      && damageQuery.get('fromFrame') === String(finalFrame) && Number(await canvas.getAttribute('data-sequence')) === eventSequence
      && await page.locator('#world-event-kind').inputValue() === 'PlayerDamaged'
      && (await page.locator('#world-events tr').allTextContents()).every(row => row.includes('玩家受傷'))
      && await page.locator('#world-review-player-scope').isVisible(),
      'The latest damage shortcut opens the original saved damage and keeps the personal event filter');
    await page.locator('#world-review').screenshot({ path: path.join(screenshots, 'world-player-latest-damage.png') });
    const contextButton = page.locator('#world-event-context'), contextStatus = page.locator('#world-event-context-status');
    await page.locator('#world-event-kind').selectOption('ReloadCompleted');
    check(await contextButton.isDisabled(), 'Marking event context requires a matching event at the current paused frame');
    await page.locator('#world-event-kind').selectOption('PlayerDamaged');
    await clipStart.click();
    const existingMarks = await clipStatus.innerText();
    const contextPattern = `**${reviewRoute}/frame-context?**`;
    await page.route(contextPattern, async route => {
      const original = await route.fetch(), value = await original.json();
      value.end.elapsedMilliseconds = value.center.elapsedMilliseconds + 5001;
      await route.fulfill({ response: original, json: value });
    }, { times: 1 });
    await contextButton.click();
    await contextStatus.filter({ hasText: '無法核對事件片段' }).waitFor();
    check(await clipStatus.innerText() === existingMarks && Number(await canvas.getAttribute('data-sequence')) === eventSequence,
      'A context response outside the five-second bound preserves the manually marked interval and current frame');
    const originalContext = page.waitForResponse(response => new URL(response.url()).pathname === `${reviewRoute}/frame-context`);
    await contextButton.click();
    const reply = await originalContext;
    const bounds = await reply.json();
    await contextStatus.filter({ hasText: `包含事件第 ${eventSequence} 格` }).waitFor();
    check(reply.headers()['cache-control'] === 'no-store' && bounds.throughFrame === finalFrame
      && bounds.center.sequence === eventSequence && bounds.start.sequence < bounds.end.sequence
      && Number(await canvas.getAttribute('data-sequence')) === eventSequence,
      'Event context marks only the original sealed range while leaving the selected player damage visible');
    await page.locator('#world-speed').evaluate(select => { select.value = '4'; });
    const contextWatch = page.waitForRequest(request => {
      const url = new URL(request.url());
      return url.pathname === `${reviewRoute}/watch` && url.searchParams.get('fromFrame') === String(bounds.start.sequence)
        && url.searchParams.get('throughFrame') === String(bounds.end.sequence);
    });
    await clipPlay.click(); await contextWatch; await waitClipEnd();
    check(Number(await canvas.getAttribute('data-sequence')) === bounds.end.sequence
      && await page.locator('#world-event-kind').inputValue() === 'PlayerDamaged'
      && await page.locator('#world-review-player-scope').isVisible(),
      'Playing the marked context stops at the exact original endpoint and retains the personal filter');
    await page.locator('#world-event-kind').selectOption('EnemyEliminated');
    await page.locator('#world-event-search-start').click();
    const killFrame = page.locator('#world-event-search-results button').first();
    const killSequence = Number(await killFrame.getAttribute('data-frame-sequence'));
    const killPacket = await api(`${archiveRoute}/frames/${killSequence}`);
    const kill = killPacket.packet.events.find(event => event.kind === 'EnemyEliminated' && event.playerId === finalPlayer.playerId);
    if (!kill) throw new Error('The completed combat fixture had no saved elimination for this player');
    await killFrame.click();
    const shotResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api${archiveRoute}/shot-trace`);
    await page.locator(`[data-shot-trace="${kill.eventId}"]`).click();
    const traceReply = await shotResponse, shotTrace = await traceReply.json();
    const tracePanel = page.locator('#world-shot-trace'), traceStatus = page.locator('#world-shot-trace-status');
    await traceStatus.filter({ hasText: '保存範圍內有 3 筆紀錄' }).waitFor();
    check(traceReply.headers()['cache-control'] === 'no-store' && shotTrace.eventId === kill.eventId
      && shotTrace.shotId === kill.shotId && shotTrace.throughFrame === finalFrame && shotTrace.playerId === finalPlayer.playerId
      && shotTrace.events.map(event => event.kind).join(',') === 'ShotFired,ShotHit,EnemyEliminated'
      && await tracePanel.locator('li').count() === 3 && Number(await canvas.getAttribute('data-sequence')) === killSequence,
      'Tracing the original elimination shows its own fire and hit in saved order without moving the reviewed frame');
    for (const [index, event] of shotTrace.events.entries()) {
      const button = tracePanel.locator('li button').nth(index);
      if (event.frameSequence === killSequence) {
        check(await button.isDisabled(), 'An event already at the current saved frame does not reload it');
      } else {
        await button.click();
        await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence,
          event.frameSequence, { polling: 50 });
        check(await tracePanel.isVisible(), 'Shot navigation opens the verified saved frame and keeps the linked records');
        break;
      }
    }
    await page.screenshot({ path: path.join(screenshots, 'world-shot-trace.png'), fullPage: true });
    const roomFilter = page.locator('#world-room');
    const previousRoom = await roomFilter.inputValue();
    await roomFilter.selectOption(previousRoom === 'all' ? '2' : 'all');
    check(!await tracePanel.isVisible() && await page.locator('#world-review-player-scope').isVisible(),
      'Changing the review room clears the trace while retaining the player filter');
    const other = await context.newPage(); await other.goto(base + '/console/'); await other.locator('#login-key').fill(tokens.Room1); await other.locator('#login-form button').click();
    await other.locator('#tab-world').click(); await other.waitForFunction(() => document.querySelector('#world-message').textContent.includes('目前沒有'));
    check(await other.locator('#world-recording option').count() === 0, 'Room-scoped observer list reveals no foreign world'); await other.close();
    await page.locator('#tab-operations').click();
    check(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && !document.cookie), 'Streaming preserves memory-only credentials');
  } finally {
    for (const child of children) if (child.exitCode === null && child.signalCode === null) { const exited = new Promise(resolve => child.once('exit', resolve)); child.kill(); await exited; }
  }
};
