const assert = require('node:assert/strict');
const { createHash, randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function mrAlignmentPinsBrowser({ context, api, base, tokens, screenshots, check, captureErrors }) {
  const page = await context.newPage();
  captureErrors(page);
  const panel = page.locator('#mr-alignment-pins'), submit = page.locator('#mr-alignment-submit');
  const summary = page.locator('#mr-alignment-summary');
  const file = room => page.locator(`#mr-alignment-file-${room}`);
  const status = room => page.locator(`#mr-alignment-status-${room}`);
  const owned = [], exports = new Map();
  const checkRoute = '**/api/room-alignment/check-file';
  const commandRoute = '**/api/sessions/*/commands';
  const sha = bytes => createHash('sha256').update(bytes).digest('hex');
  const put = (room, bytes = exports.get(room), name = `room-${room}-floor-alignment.json`) =>
    file(room).setInputFiles({ name, mimeType: 'application/json', buffer: bytes });
  const checked = room => status(room).filter({ hasText: '已核對，可鎖定' }).waitFor();
  async function open(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#session-panel').waitFor();
  }
  async function select(session) {
    await page.locator('#session-select').selectOption(session.id);
    await page.locator('#session-panel').waitFor();
  }
  async function create(mission, rooms) {
    const state = await api('/sessions', 'POST', { missionId: mission.id, roomIds: rooms,
      mode: rooms.length === 5 ? 'Linked' : 'Independent' }, 'Master', 201);
    owned.push(state.id);
    return state;
  }
  const end = id => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
  let releaseCheck, finishCheck;
  try {
    const mission = await api('/missions', 'POST', { name: 'MR alignment pins browser fixture', briefing: 'Original export validation',
      durationSeconds: 600, environment: { mode: 'MR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const markers = [[-2,-2],[2,-2],[-2,2]].map(([x,z]) => ({ room: { x,z }, tracking: { x: x+1,z: z-1 } }));
    let firstReport;
    for (const room of [1,2,3,4,5]) {
      const report = await api('/room-alignment', 'POST', { roomId: room, markers });
      if (room === 1) firstReport = report;
      const json = JSON.stringify(report, null, 2) + '\n';
      exports.set(room, Buffer.from(room === 1 ? '\ufeff' + json.replaceAll('\n', '\r\n') : json));
    }
    async function rawCheck(bytes, role, expected) {
      const response = await fetch(base + '/api/room-alignment/check-file', { method: 'POST', body: bytes,
        headers: { Authorization: 'Bearer ' + tokens[role], 'Content-Type': 'application/octet-stream' } });
      assert.equal(response.status, expected);
      return { body: await response.json(), cache: response.headers.get('cache-control') };
    }
    const byteCheck = await rawCheck(exports.get(1), 'Master', 200);
    await rawCheck(exports.get(1), 'Room1', 403);
    await rawCheck(Buffer.alloc(16_385), 'Master', 400);
    check(byteCheck.cache === 'no-store' && byteCheck.body.roomId === 1 && byteCheck.body.sha256 === sha(exports.get(1)),
      'Master checks original binary bytes, including BOM and CRLF, without storing or returning a report');

    let a = await create(mission, [1]);
    const b = await create(mission, [2]);
    a = await api(`/sessions/${a.id}/players`, 'POST', { playerId: randomUUID(), name: 'Quest handoff seat', roomId: 1, headset: 'Quest3' }, 'Room1');
    await open('Master'); await select(a);
    check(await panel.isVisible() && await file(1).isVisible() && await file(2).count() === 0 && await submit.isDisabled(),
      'Independent MR exposes only its own room and starts with no lockable file');
    await page.locator('#ticket-room').selectOption('1');
    check(await page.locator('[data-player-action=ticket]').isDisabled() && await page.locator('#download-room-tickets').isDisabled()
      && (await page.locator('#mr-ticket-pin-hint').innerText()).includes('鎖定 MR 校正檔'),
    'The desk explains why both MR ticket downloads wait for the calibration lock');
    await put(1, exports.get(2));
    await status(1).filter({ hasText: '此檔案屬於房間 2' }).waitFor();
    check(await submit.isDisabled() && (await api(`/sessions/${a.id}`)).sequence === a.sequence,
      'Wrong-room exports stay out of the pin draft and leave the session untouched');
    const altered = structuredClone(firstReport); altered.markers[2].tracking.x += 5;
    await put(1, Buffer.from(JSON.stringify(altered)));
    await status(1).filter({ hasText: '校正檔未通過核對' }).waitFor();
    check(await submit.isDisabled(), 'A forged success flag cannot bypass a failed calibration fit');

    let startedCheck;
    const started = new Promise(resolve => { startedCheck = resolve; });
    const gate = new Promise(resolve => { releaseCheck = resolve; });
    let completedCheck;
    finishCheck = new Promise(resolve => { completedCheck = resolve; });
    async function holdFile(route) {
      startedCheck();
      try {
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        await gate; await route.fulfill({ response });
        completedCheck(true);
      } catch { completedCheck(false); }
    }
    await page.route(checkRoute, holdFile);
    await put(1); await started;
    check(await submit.isDisabled(), 'The pending file check cannot enable a write');
    await select(b); await file(2).waitFor();
    releaseCheck(); assert.equal(await finishCheck, true); releaseCheck = null;
    await page.unroute(checkRoute, holdFile);
    check(await file(1).count() === 0 && await submit.isDisabled() && (await summary.innerText()).includes('0／1'),
      'A valid check response arriving after a room switch cannot reapply the old draft');
    await select(a); await file(1).waitFor();
    check(await submit.isDisabled() && (await status(1).innerText()) === '尚未選擇校正檔', 'Returning to a room starts with an empty file draft');
    await put(1); await checked(1);
    page.once('dialog', dialog => dialog.dismiss()); await submit.click();
    check((await api(`/sessions/${a.id}`)).sequence === a.sequence && await submit.isEnabled(),
      'Dismissing confirmation preserves the checked file and does not send a lock');
    page.once('dialog', dialog => dialog.accept()); await submit.click();
    await status(1).filter({ hasText: '已鎖定' }).waitFor();
    const pinned = await api(`/sessions/${a.id}`);
    check(pinned.roomAlignment.room1 === sha(exports.get(1)) && pinned.sequence === a.sequence + 1 && await file(1).isHidden(),
      'Independent lock persists the exact original byte hash and becomes read-only');
    await open('Room1'); await select(a);
    await page.locator('#game-address').fill('192.168.1.100');
    const [single] = await Promise.all([page.waitForEvent('download'), page.locator('[data-player-action=ticket]').click()]);
    const singleBytes = [];
    for await (const chunk of await single.createReadStream()) singleBytes.push(chunk);
    const config = JSON.parse(Buffer.concat(singleBytes));
    const { joinTicket, ...fields } = config;
    assert.deepEqual(fields, { role: 'Client', address: '192.168.1.100', port: 7777, roomAlignmentSha256: pinned.roomAlignment.room1 });
    check(joinTicket.startsWith('v2.') && await panel.isHidden(), 'The room controller downloads the exact pinned MR hash and original ticket without access to pinning');
    await page.locator('#ticket-room').selectOption('1');
    const [zip] = await Promise.all([page.waitForEvent('download'), page.locator('#download-room-tickets').click()]);
    const zipBytes = [];
    for await (const chunk of await zip.createReadStream()) zipBytes.push(chunk);
    check(zip.suggestedFilename() === 'room-01-connections.zip' && Buffer.concat(zipBytes).subarray(0,4).equals(Buffer.from([0x50,0x4b,3,4])),
      'The same room controller can download its MR bundle after the calibration lock');
    await end(a.id); await end(b.id);

    const linked = await create(mission, [1,2,3,4,5]);
    await open('Master'); await select(linked); await file(5).waitFor();
    for (const room of [1,2,3,4]) { await put(room); await checked(room); }
    check(await submit.isDisabled() && (await summary.innerText()).includes('4／5'), 'Linked lock requires all five room files');
    await put(5); await checked(5);
    await page.setViewportSize({ width: 390, height: 844 });
    check(await panel.evaluate(node => node.scrollWidth <= node.clientWidth + 1), 'Five checked room files and full hashes fit on a narrow screen');
    await page.setViewportSize({ width: 1440, height: 1080 });
    await panel.screenshot({ path: path.join(screenshots, 'mr-alignment-pins-checked.png') });

    const attempts = [];
    let originalStatus;
    async function loseOnce(route) {
      const body = route.request().postDataJSON();
      if (body?.action !== 'SetRoomAlignment') return route.continue();
      attempts.push(body);
      if (attempts.length !== 1) return route.continue();
      const response = await route.fetch();
      originalStatus = response.status();
      await route.abort('failed');
    }
    await page.route(commandRoute, loseOnce);
    page.once('dialog', dialog => dialog.accept()); await submit.click();
    await page.locator('#pending-command').waitFor();
    check(await submit.isDisabled() && (await status(5).innerText()) !== '已鎖定', 'A lost response exposes a retry without showing an unconfirmed lock');
    await page.locator('#retry-command').click();
    await status(5).filter({ hasText: '已鎖定' }).waitFor();
    await page.unroute(commandRoute, loseOnce);
    const events = await api(`/sessions/${linked.id}/events`);
    const locks = events.filter(row => row.payload.action === 'SetRoomAlignment');
    assert.equal(originalStatus, 200);
    assert.equal(attempts.length, 2);
    assert.deepEqual(attempts[0], attempts[1]);
    assert.equal(attempts[0].expectedSequence, linked.sequence);
    assert.equal(locks.length, 1);
    const expectedPins = Object.fromEntries([...exports].map(([room, bytes]) => [`room${room}`, sha(bytes)]));
    assert.deepEqual(locks[0].payload.roomAlignment, expectedPins);
    check(locks[0].payload.commandId === attempts[0].commandId && await submit.isHidden(),
      'Linked retry uses the original UUID and exact five raw file hashes and persists one event');
    await panel.screenshot({ path: path.join(screenshots, 'mr-alignment-pins-locked.png') });
    await open('Master'); await select(linked);
    check(await panel.locator('code:visible').count() === 5 && await submit.isHidden(), 'Reload reads back the saved room hashes with no upload controls');
    await open('Room1'); await select(linked);
    check(await panel.isHidden(), 'Room control can see its session while the master calibration controls stay hidden');
    await open('Master'); await select(linked);
    await end(linked.id);
    await page.locator('#include-ended').check(); await select(linked);
    await page.locator('#session-phase').filter({ hasText: '已結束' }).waitFor();
    check(await panel.locator('code:visible').count() === 5 && await submit.isHidden()
      && (await summary.innerText()) === '下方為本場各房已鎖定的校正檔。', 'Ended sessions display the historical pins without suggesting another start');
  } catch (error) {
    await page.screenshot({ path: path.join(screenshots, 'mr-alignment-pins-failure.png'), timeout: 5000 }).catch(() => {});
    throw error;
  } finally {
    if (releaseCheck) { releaseCheck(); await finishCheck; }
    await page.close();
    for (const id of owned) if ((await api(`/sessions/${id}`)).state !== 'Ended') await end(id);
  }
};
