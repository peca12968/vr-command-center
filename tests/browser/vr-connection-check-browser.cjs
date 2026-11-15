const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');
const { holdTicketResponse } = require('./ticket-download-fence.cjs');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const page = await context.newPage();
  captureErrors(page);
  const panel = page.locator('#vr-deployment-panel'), seat = page.locator('#vr-deployment-seat');
  const file = page.locator('#vr-deployment-connection'), submit = page.locator('#vr-deployment-submit');
  const status = page.locator('#vr-deployment-status');
  const address = '127.0.0.1', port = 7777;
  const connectionBytes = value => Buffer.from('\ufeff' + JSON.stringify(value) + '\r\n');
  const upload = bytes => file.setInputFiles({ name: 'connection.json', mimeType: 'application/json', buffer: bytes });
  const message = text => status.filter({ hasText: text }).waitFor();
  const mission = await api('/missions', 'POST', { name: 'VR connection file check', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] }, 'Master', 201);
  const route = `/sessions/${session.id}`;
  let ended = false, sequence = 0;
  const url = (player, room = player.roomId, check = 'vr-connection-check') => `${base}/api${route}/rooms/${room}/players/${player.id}/${check}`;
  async function add(roomId, name, headset, playerId = randomUUID()) {
    const view = await api(route + '/players', 'POST', { roomId, name, headset, playerId });
    return view.players.find(player => player.id === playerId);
  }
  async function connection(player) {
    const signed = await api(`${route}/players/${player.id}/join-ticket`, 'POST', undefined, 'Master', 200, player.admissionId);
    return { role: 'Client', address, port, joinTicket: signed.ticket };
  }
  async function request(player, bytes, { role = 'Room1', room = player.roomId, admission = player.admissionId, expected = 200, endpoint } = {}) {
    const response = await fetch(url(player, room, endpoint), { method: 'POST', headers: { 'Content-Type': 'application/json',
      ...(role ? { Authorization: 'Bearer ' + tokens[role] } : {}), ...(admission ? { 'If-Match-Admission': admission } : {}) },
      body: JSON.stringify({ connectionFile: bytes.toString('base64') }) });
    assert.equal(response.status, expected, 'VR connection check HTTP status');
    const value = await response.json();
    if (expected === 200) {
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.deepEqual(Object.keys(value).sort(), ['address', 'expiresAtUtc', 'port', 'roomId', 'seat', 'status']);
      assert.equal(value.roomId, player.roomId); assert.equal(value.seat, player.seat);
    }
    return value;
  }
  const end = () => api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
  try {
    const first = await add(1, 'Quest Alpha', 'Quest3'), second = await add(1, 'VIVE Bravo', 'ViveXr');
    const other = await add(2, 'Quest Charlie', 'Quest3');
    const original = await connection(first), originalBytes = connectionBytes(original);
    const wrongSeat = connectionBytes(await connection(second));
    const call = (bytes = originalBytes, options) => request(first, bytes, options);
    await call(originalBytes, { role: null, expected: 401 });
    await call(originalBytes, { role: 'Room2', expected: 403 });
    await call(originalBytes, { role: 'GameServer', expected: 403 });
    await request(other, originalBytes, { room: 1, expected: 404 });
    await call(originalBytes, { admission: null, expected: 400 });
    await call(originalBytes, { admission: randomUUID(), expected: 409 });
    await call(Buffer.alloc(2049), { expected: 400 });
    check(true, 'Single-seat VR checks require authorization, the original admission fence and bounded bytes');
    check((await call()).status === 'endpoint-unpublished', 'A signed seat file does not verify before its game source publishes an endpoint');

    const streamId = randomUUID(), origin = 'Simulation', start = Date.now() - 6500;
    await api(route + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    const snapshot = await api(route);
    const header = { sessionId: session.id, streamId, origin, roomIds: session.roomIds,
      captureStartedAtUtc: new Date(start).toISOString().replace('Z', '0000+00:00') };
    const players = snapshot.players.map(player => {
      const point = { x: (player.roomId - 3) * 14, y: 1.65, z: -3 };
      return { id: player.id, roomId: player.roomId, connected: false, head: point, muzzle: point, forward: { x: 0, y: 0, z: 1 },
        health: 100, magazine: 30, reserve: 90, rig: { kind: 'None' } };
    });
    function publish(fresh) {
      const messages = [{ type: 'header', payload: header }];
      if (fresh !== undefined) messages.push({ type: 'frame', payload: { sequence: ++sequence, observedSequence: snapshot.sequence,
        elapsedMilliseconds: fresh ? Date.now() - start : 0, throughCombatSequence: 0, events: [], weather: 'Clear',
        frame: { phase: 'Preparing', tick: 0, night: false, throughSequence: 0, players } } });
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: '/api' + route + '/world/publish', token: tokens.GameServer, messages }) });
      assert.equal(result.status, 0, 'VR fixture source publish failed: ' + result.stderr);
      assert.equal(JSON.parse(result.stdout).acceptedSequence, sequence);
    }
    publish();
    await api(route + '/connection-endpoint', 'PUT', { version: 1, streamId, address, port }, 'GameServer');
    assert.equal((await call()).status, 'source-stale');
    publish(false);
    check((await call()).status === 'source-stale', 'An announced endpoint requires a recent accepted frame from the original source');
    assert.equal((await call(connectionBytes({ ...original, port: port + 1 }))).status, 'endpoint-mismatch');
    assert.equal((await call(wrongSeat)).status, 'wrong-seat');
    assert.equal((await call(connectionBytes({ ...original, joinTicket: original.joinTicket.replace(/\.[^.]+$/, '.forged') }))).status, 'ticket-invalid');
    assert.equal((await call(Buffer.from('{"role":"Client",' + JSON.stringify(original).slice(1)))).status, 'connection-invalid');
    check((await api(route)).sequence === snapshot.sequence, 'VR file, endpoint, signature and seat mismatches leave the original session revision intact');

    publish(true);
    const valid = await call(originalBytes, { role: 'Master' });
    check(valid.status === 'matched' && valid.address === address && valid.port === port && Date.parse(valid.expiresAtUtc) > Date.now(),
      'The live original endpoint verifies signed VR bytes and returns only the seat, endpoint and expiry');
    const quest = { endpoint: 'quest-deployment-check' };
    const questMatch = await call(originalBytes, quest);
    const wrongHeadset = await request(second, wrongSeat, quest);
    await call(originalBytes, { ...quest, role: 'Room2', expected: 403 });
    await call(originalBytes, { ...quest, admission: randomUUID(), expected: 409 });
    check(questMatch.status === 'matched' && wrongHeadset.status === 'headset-mismatch'
      && (await call(connectionBytes({ ...original, port: port + 1 }), quest)).status === 'endpoint-mismatch',
    'The single Quest deployment check verifies the original VR destination and refuses another headset or admission');

    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Room1); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id); await panel.waitFor();
    check(await page.locator('#mr-deployment-panel').isHidden()
      && (await seat.locator('option').allTextContents()).join('|') === '請選擇要核對的席位|房間 1／第 1 席 · Quest Alpha|房間 1／第 2 席 · VIVE Bravo',
      'The room console lists its own VR seats for both headset classifications');
    await seat.selectOption(first.admissionId);
    await upload(connectionBytes({ ...original, port: port + 1 })); await submit.click(); await message('連線檔與公告端點不符');
    assert.match(await status.innerText(), /127\.0\.0\.1:7777/);
    await upload(wrongSeat); await submit.click(); await message('連線檔屬於其他房間或席位');
    await upload(originalBytes); publish(true); await submit.click(); await message('僅同機');
    check((await status.innerText()).includes('票券有效至') && !await panel.getByText(original.joinTicket, { exact: true }).count(),
      'The console identifies mismatches, marks loopback as same-host only and never displays the ticket');
    await page.setViewportSize({ width: 390, height: 844 });
    check(await panel.evaluate(node => node.scrollWidth <= node.clientWidth + 1), 'VR seat file check fits a narrow console');
    await panel.screenshot({ path: path.join(screenshots, 'vr-seat-connection-check.png') });

    publish(true);
    const oldResponse = page.waitForResponse(response => response.url() === url(first));
    const held = await holdTicketResponse(page, url(first), () => submit.click(), () => seat.selectOption(second.admissionId),
      () => status.innerText());
    assert.equal((await (await oldResponse).json()).status, 'matched');
    check(held.signedResponses === 1 && await submit.isDisabled() && await file.inputValue() === ''
      && held.message.includes('請選擇席位'), 'A delivered valid reply cannot restore an old seat result or file after switching seats');

    await seat.selectOption(first.admissionId); await upload(originalBytes);
    await api(`${route}/players/${first.id}`, 'DELETE', undefined, 'Master', 204, first.admissionId);
    const replaced = await add(1, 'Quest Alpha renewed', 'Quest3', first.id);
    assert.equal((await request(replaced, originalBytes)).status, 'admission-changed');
    await call(originalBytes, { expected: 409 });
    await page.locator('#refresh').click(); await seat.locator('option').filter({ hasText: replaced.name }).waitFor({ state: 'attached' });
    check(await seat.inputValue() === '' && await file.inputValue() === '' && await submit.isDisabled(),
      'Replacing an admission clears the prior selection and rejects the original file');
    await end(); ended = true;
    await request(replaced, originalBytes, { expected: 409 });
    check(true, 'An ended VR session cannot verify a previously signed file');
  } finally {
    await page.close();
    if (!ended) await end();
  }
};
