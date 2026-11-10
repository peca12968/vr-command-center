const { randomUUID } = require('node:crypto');
const path = require('node:path');
module.exports = async ({ context, api, tokens, base, mission, screenshots, check }) => {
  const rooms = (await api('/rooms')).filter(room => !room.sessionId).slice(0, 2);
  if (rooms.length !== 2) throw Error('Closure fixture needs two free rooms');
  const sessions = [];
  for (const room of rooms) {
    const created = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room.id] }, 'Master', 201);
    await api(`/sessions/${created.id}/players`, 'POST', { playerId: randomUUID(), name: 'Closure receipt fixture', roomId: room.id, headset: 'Quest3' });
    await api(`/sessions/${created.id}/combat-stream`, 'POST', { streamId: randomUUID(), origin: 'Simulation', missionClockVersion: 1 }, 'GameServer');
    await api(`/sessions/${created.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
    await api(`/sessions/${created.id}/combat-stream/seal`, 'POST', { streamId: (await api(`/sessions/${created.id}`)).combatStream.streamId, finalSequence: 0 }, 'GameServer');
    sessions.push(await api(`/sessions/${created.id}`));
  }
  const [first, second] = sessions;
  const recording = (session, complete) => ({ header: { schemaVersion: 1, sessionId: session.id, streamId: session.combatStream.streamId, origin: 'Simulation', roomIds: session.roomIds, missionClockVersion: 1, missionDurationSeconds: session.mission.definition.durationSeconds }, acceptedSequence: 1, complete });
  let mode = 'pending', release, requested, hold = false;
  let gate = new Promise(resolve => { release = resolve; }), began = new Promise(resolve => { requested = resolve; });
  const page = await context.newPage();
  const completed = () => page.locator('#closure-status.closure-complete');
  try {
    await page.route(`**/api/sessions/${first.id}/world?includeDebriefReceipts=true`, async route => {
      if (hold) { requested(); await gate; }
      const status = ({ unavailable: 503, missing: 404, forbidden: 403, unauthorized: 401 })[mode];
      const value = recording(first, ['complete', 'unconfirmed-receipt', 'confirmed-receipt'].includes(mode));
      if (mode === 'foreign') value.header.streamId = randomUUID();
      if (mode.endsWith('-receipt')) {
        const [player] = first.players;
        value.debriefReceipts = { streamId: first.combatStream.streamId, throughSequence: first.sequence,
          finalStreamSequence: 0, worldSequence: value.acceptedSequence, players: [{ playerId: player.id, admissionId: player.admissionId,
            roomId: player.roomId, name: player.name, acknowledged: mode === 'confirmed-receipt' }] };
      }
      await route.fulfill(status ? { status, json: { error: 'fixture' } } : { json: value }).catch(() => {});
    });
    await page.route(`**/api/sessions/${second.id}/world?includeDebriefReceipts=true`, route => route.fulfill({ json: recording(second, false) }));
    await page.goto(base + '/console/'); await page.bringToFront();
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#include-ended').check(); await page.locator('#session-select').selectOption(first.id);
    await page.waitForFunction(() => document.querySelector('#closure-combat').textContent.includes('已封存') && document.querySelector('#closure-world').textContent.includes('等待封存'));
    check(await completed().count() === 0 && await page.locator('#export-report').isEnabled(), 'Combat seal permits the original CSV independently while world archive remains pending; world response is a UI fixture');
    await page.screenshot({ path: path.join(screenshots, 'closure-pending.png'), fullPage: true });
    mode = 'complete'; await completed().waitFor();
    check((await page.locator('#closure-summary').innerText()).includes('不確認送達'), 'Dual archive confirmation explicitly leaves player result delivery and server shutdown unconfirmed');
    await page.screenshot({ path: path.join(screenshots, 'closure-complete.png'), fullPage: true });
    mode = 'unconfirmed-receipt';
    await page.locator('#debrief-receipt-count').filter({ hasText: '已確認 0／1 席' }).waitFor();
    await page.locator('#debrief-receipt-count').click();
    check((await page.locator('#debrief-receipt-players li').innerText()).endsWith('未確認'), 'A terminal roster entry without a receipt stays unconfirmed');
    mode = 'confirmed-receipt';
    await page.locator('#debrief-receipt-count').filter({ hasText: '已確認 1／1 席' }).waitFor();
    check((await page.locator('#debrief-receipt-players li').innerText()).endsWith('已確認'), 'A matching receipt updates the original terminal roster entry');
    for (const [next, expected] of [['unavailable', '暫時無法確認'], ['missing', '尚未取得'], ['foreign', '尚未對上'], ['forbidden', '暫時無法確認']]) {
      mode = next; await page.waitForFunction(text => document.querySelector('#closure-summary').textContent.includes(text), expected);
      check(await completed().count() === 0, `World ${next} cannot reuse a previous completed archive`);
      if (next === 'unavailable') check(await page.locator('#debrief-receipts').isHidden(), 'A failed refresh clears displayed player receipts');
    }
    await page.screenshot({ path: path.join(screenshots, 'closure-unconfirmed.png'), fullPage: true });
    mode = 'complete'; await completed().waitFor();
    await page.route('**/api/rooms', route => route.fulfill({ status: 503, json: { error: 'fixture refresh failure' } }));
    await page.locator('#refresh').click(); await page.waitForFunction(() => document.querySelector('#closure-summary').textContent.includes('場次更新失敗'));
    check(await completed().count() === 0, 'A failed management refresh invalidates archive confirmation even if the old world was complete');
    await page.unroute('**/api/rooms'); await page.locator('#refresh').click(); await completed().waitFor();
    hold = true; await began; await page.locator('#session-select').selectOption(second.id); release();
    await page.waitForFunction(() => document.querySelector('#closure-world').textContent.includes('等待封存'));
    check(await completed().count() === 0, 'Late previous-session archive response cannot complete the newly selected session');
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Archive progress text wraps inside a 390-pixel operator view');
    await page.screenshot({ path: path.join(screenshots, 'closure-mobile.png'), fullPage: true });
    gate = new Promise(resolve => { release = resolve; }); began = new Promise(resolve => { requested = resolve; });
    await page.locator('#session-select').selectOption(first.id); await began; await page.locator('#logout').click(); release();
    check(await completed().count() === 0 && await page.locator('#workspace').isHidden(), 'Logout clears archive confirmation and fences the delayed old identity');
    hold = false; mode = 'unauthorized';
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click(); await page.locator('#include-ended').check(); await page.locator('#session-select').selectOption(first.id);
    await page.locator('#login-panel').waitFor();
    check(await page.locator('#workspace').isHidden() && await completed().count() === 0, 'A current archive 401 follows the existing logout path instead of keeping a stale green status');
    // A real lost End response followed by a sealed duplicate must retain the archived selection.
    const retry = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [rooms[0].id] }, 'Master', 201);
    const retryStream = randomUUID(); await api(`/sessions/${retry.id}/combat-stream`, 'POST', { streamId: retryStream, origin: 'Simulation', missionClockVersion: 1 }, 'GameServer');
    const intents = [];
    await page.route(`**/api/sessions/${retry.id}/commands`, async route => {
      intents.push(route.request().postDataJSON());
      if (intents.length === 1) {
        const response = await route.fetch(); if (response.status() !== 200) throw Error('Expected first real End acceptance');
        await api(`/sessions/${retry.id}/combat-stream/seal`, 'POST', { streamId: retryStream, finalSequence: 0 }, 'GameServer');
        await route.abort('failed');
      } else await route.continue();
    });
    await page.setViewportSize({ width: 1440, height: 1080 }); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#include-ended').uncheck(); await page.locator('#session-select').selectOption(retry.id);
    page.once('dialog', dialog => dialog.accept()); await page.locator('[data-command=End]').click(); await page.locator('#pending-command').waitFor();
    const duplicateResponse = page.waitForResponse(response => response.url() === base + `/api/sessions/${retry.id}/commands` && response.request().method() === 'POST');
    await page.locator('#retry-command').click(); const reply = await duplicateResponse, duplicate = await reply.json();
    check(reply.status() === 200 && duplicate.duplicate && duplicate.session.combatStream.sealed && intents.length === 2 && intents[0].commandId === intents[1].commandId && intents[0].expectedSequence === intents[1].expectedSequence,
      'The real End retry keeps its UUID / expected sequence and returns the already sealed duplicate receipt');
    try {
      await page.waitForFunction(id => document.querySelector('#session-select').value === id && document.querySelector('#include-ended').checked && !document.querySelector('#session-panel').hidden && document.querySelector('#session-phase').textContent === '已結束', retry.id, { polling: 100 });
    } catch (error) {
      const fs = require('node:fs/promises'); await fs.writeFile(path.join(screenshots, 'closure-retry-failure.json'), JSON.stringify(await page.evaluate(() => ({ selected: document.querySelector('#session-select').value, includeEnded: document.querySelector('#include-ended').checked, panelHidden: document.querySelector('#session-panel').hidden, phase: document.querySelector('#session-phase').textContent, summary: document.querySelector('#closure-summary').textContent.slice(0, 800), pendingHidden: document.querySelector('#pending-command').hidden })), null, 2));
      await page.screenshot({ path: path.join(screenshots, 'closure-retry-failure.png'), fullPage: true, timeout: 5000 }).catch(() => {}); throw error;
    }
    check(true, 'A confirmed already-sealed End retains its archived selection and closure view instead of switching away');

    const live = [];
    for (const room of rooms) {
      const state = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room.id] }, 'Master', 201);
      await api(`/sessions/${state.id}/players`, 'POST', { playerId: randomUUID(), name: 'Room operator fixture', roomId: room.id, headset: 'Quest3' });
      await api(`/sessions/${state.id}/commands`, 'POST', { commandId: randomUUID(), action: 'Begin' });
      live.push(state);
    }
    const [ending, other] = live;
    await page.locator('#include-ended').uncheck();
    await page.locator('#session-select').selectOption(ending.id);
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中'
      && !document.querySelector('#session-panel').hidden && !document.querySelector('[data-command=Pause]').disabled);
    const list = url => url.pathname === '/api/sessions' && url.searchParams.get('includeEnded') === 'false';
    let requestHeld, allowList, finishList, held = false;
    const holdList = new Promise(resolve => { allowList = resolve; });
    const listRequested = new Promise(resolve => { requestHeld = resolve; });
    const listSent = new Promise(resolve => { finishList = resolve; });
    const writes = [];
    const recordWrite = request => {
      if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/commands'))
        writes.push({ path: new URL(request.url()).pathname, action: request.postDataJSON().action });
    };
    page.on('request', recordWrite);
    const holdNextList = async route => {
      if (held) return route.continue();
      held = true; requestHeld();
      await holdList;
      try { await route.continue(); finishList(null); }
      catch (error) { finishList(error); }
    };
    await page.route(list, holdNextList);
    try {
      await page.locator('#refresh').click();
      await listRequested;
      await api(`/sessions/${ending.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
      await page.locator('[data-command=Pause]').click();
      allowList();
      const deliveryError = await listSent;
      if (deliveryError) throw deliveryError;
      await page.waitForFunction(() => !document.querySelector('#session-select').disabled, null, { timeout: 15000 });
      const otherPhase = (await api(`/sessions/${other.id}`)).state;
      await require('node:fs/promises').writeFile(path.join(screenshots, 'room-command-fence.json'),
        JSON.stringify({ expectedTarget: ending.id, other: other.id, otherPhase, writes,
          selected: await page.locator('#session-select').inputValue() }, null, 2));
      check(otherPhase === 'Running' && writes.length === 0, 'Pause queued for an externally ended room never writes to the remaining live room');
      check(await page.locator('#session-select').inputValue() === '' && await page.locator('#session-panel').isHidden(),
        'Losing the selected room clears its controls without automatically switching to another room');
      await page.locator('#refresh').click();
      await page.waitForFunction(() => document.querySelector('#notice').textContent === '已更新。');
      check(await page.locator('#session-select').inputValue() === '', 'A second refresh leaves the replacement room unselected');
      await page.screenshot({ path: path.join(screenshots, 'room-command-fence.png'), fullPage: true });
      await page.locator('#include-ended').check();
      await page.locator('#session-select').selectOption(ending.id);
      await page.waitForFunction(() => !document.querySelector('#session-panel').hidden && document.querySelector('#session-phase').textContent === '已結束');
      check(await page.locator('[data-command=Pause]').isDisabled(), 'An explicitly chosen archived session remains readable and cannot be paused');
      await page.locator('#include-ended').uncheck();
      await page.waitForFunction(() => document.querySelector('#session-select').value === '');
      await page.locator('#session-select').selectOption(other.id);
      await page.locator('[data-command=Pause]').click();
      await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已暫停');
      check(writes.length === 1 && writes[0].path === `/api/sessions/${other.id}/commands` && writes[0].action === 'Pause',
        'A fresh explicit room selection permits exactly one real Pause for that room');
    } finally {
      allowList();
      if (held) await listSent;
      await page.unroute(list, holdNextList);
      page.off('request', recordWrite);
      await api(`/sessions/${other.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
    }
  } finally { release?.(); await page.close(); }
};
