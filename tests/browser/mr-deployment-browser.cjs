const assert = require('node:assert/strict');
const { createHash, createHmac, randomUUID } = require('node:crypto');
const { readFile } = require('node:fs/promises');
const path = require('node:path');

module.exports = async function mrDeploymentBrowser({ context, api, tokens, base, directory, screenshots, check, captureErrors }) {
  const page = await context.newPage();
  captureErrors(page);
  const panel = page.locator('#mr-deployment-panel'), seat = page.locator('#mr-deployment-seat');
  const configInput = page.locator('#mr-deployment-connection'), alignmentInput = page.locator('#mr-deployment-alignment');
  const submit = page.locator('#mr-deployment-submit'), status = page.locator('#mr-deployment-status');
  const files = new Map(), sessions = [];
  const routePattern = '**/deployment-check';
  let release, delivery;
  const sha = bytes => createHash('sha256').update(bytes).digest('hex');
  const json = value => Buffer.from(JSON.stringify(value));
  async function login(role, session) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    await page.locator('#session-panel').waitFor();
  }
  async function add(session, roomId, name, playerId = randomUUID()) {
    const view = await api(`/sessions/${session.id}/players`, 'POST', { playerId, name, roomId, headset: 'Quest3' });
    return view.players.find(player => player.id === playerId);
  }
  async function connection(session, player) {
    const ticket = await api(`/sessions/${session.id}/players/${player.id}/join-ticket`, 'POST', undefined, 'Master', 200, player.admissionId);
    return { role: 'Client', address: '192.168.1.100', port: 7777, joinTicket: ticket.ticket, roomAlignmentSha256: ticket.roomAlignmentSha256 };
  }
  async function request(session, player, config, alignment, role, expected = 200, room = player.roomId) {
    const response = await fetch(`${base}/api/sessions/${session.id}/rooms/${room}/players/${player.id}/deployment-check`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...(role ? { Authorization: 'Bearer ' + tokens[role] } : {}) },
      body: JSON.stringify({ connectionFile: config.toString('base64'), alignmentFile: alignment.toString('base64') })
    });
    assert.equal(response.status, expected, 'deployment check HTTP status');
    const value = await response.json();
    if (expected === 200) {
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.deepEqual(Object.keys(value).sort(), ['expiresAtUtc', 'roomId', 'seat', 'status']);
      assert.equal(value.roomId, room); assert.equal(value.seat, player.seat);
    }
    return value;
  }
  async function upload(config, alignment) {
    await configInput.setInputFiles({ name: 'connection.json', mimeType: 'application/json', buffer: config });
    await alignmentInput.setInputFiles({ name: 'alignment.json', mimeType: 'application/json', buffer: alignment });
  }
  const message = text => status.filter({ hasText: text }).waitFor();
  try {
    const mission = await api('/missions', 'POST', { name: 'MR seat deployment fixture', briefing: 'Verify preparation files', durationSeconds: 600,
      environment: { mode: 'MR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] }, 'Master', 201);
    sessions.push(session.id);
    const first = await add(session, 1, 'Quest Alpha'), second = await add(session, 1, 'Quest Bravo');
    const other = await add(session, 2, 'Quest Charlie');
    await login('Room1', session);
    check(await panel.isHidden(), 'MR deployment check stays hidden until alignment is locked');
    const markers = [[-2, -2], [2, -2], [-2, 2]].map(([x, z]) => ({ room: { x, z }, tracking: { x: x + 1, z: z - 1 } }));
    for (const roomId of session.roomIds) {
      const report = await api('/room-alignment', 'POST', { roomId, markers });
      files.set(roomId, Buffer.from('\ufeff' + JSON.stringify(report, null, 2).replaceAll('\n', '\r\n') + '\r\n'));
    }
    const pins = Object.fromEntries([...files].map(([roomId, bytes]) => [`room${roomId}`, sha(bytes)]));
    const lock = await api(`/sessions/${session.id}/commands`, 'POST', { commandId: randomUUID(), action: 'SetRoomAlignment', roomAlignment: pins });
    const firstConfig = await connection(session, first), secondConfig = await connection(session, second), otherConfig = await connection(session, other);
    const firstFile = json(firstConfig), original = files.get(1);
    const call = (config, alignment = original, role = 'Room1', expected = 200) => request(session, first, config, alignment, role, expected);
    await request(session, other, json(otherConfig), files.get(2), 'Room1', 403);
    await request(session, other, firstFile, original, 'Room1', 404, 1);
    await call(firstFile, original, 'Room2', 403);
    await call(firstFile, original, 'GameServer', 403);
    await call(firstFile, original, null, 401);
    check(true, 'Deployment checks are restricted to Master or the selected room, including guessed player IDs');
    assert.equal((await call(firstFile, original, 'Master')).status, 'matched');
    const good = await call(firstFile);
    check(good.status === 'matched' && Date.parse(good.expiresAtUtc) > Date.now(), 'Exact BOM and CRLF calibration bytes and valid signed ticket match the current seat');
    const [version, encoded] = firstConfig.joinTicket.split('.');
    const ticketKey = Buffer.from(await readFile(path.join(directory, 'player-ticket-signing.key'), 'utf8'), 'base64');
    const expired = Buffer.from(encoded, 'base64url'); expired.writeBigInt64BE(BigInt(Math.floor(Date.now() / 1000) - 10), 51);
    const expiredTicket = [version, expired.toString('base64url'), createHmac('sha256', ticketKey).update(expired).digest('base64url')].join('.');
    ticketKey.fill(0);
    assert.equal((await call(json({ ...firstConfig, joinTicket: expiredTicket }))).status, 'ticket-invalid');
    assert.equal((await call(json({ ...firstConfig, joinTicket: firstConfig.joinTicket.replace(/\.[^.]+$/, '.forged') }))).status, 'ticket-invalid');
    check(true, 'A correctly signed expired ticket and a tampered ticket both fail verification');
    assert.equal((await call(json(secondConfig))).status, 'wrong-seat');
    assert.equal((await call(json(otherConfig))).status, 'wrong-seat');
    assert.equal((await call(json({ ...firstConfig, roomAlignmentSha256: undefined }))).status, 'connection-hash-mismatch');
    assert.equal((await call(firstFile, files.get(2))).status, 'alignment-wrong-room');
    assert.equal((await call(firstFile, Buffer.concat([original, Buffer.from('\n')]))).status, 'alignment-hash-mismatch');
    assert.equal((await call(firstFile, json({}))).status, 'alignment-invalid');
    assert.equal((await call(json({ ...firstConfig, address: '224.0.0.1' }))).status, 'connection-invalid');
    assert.equal((await call(Buffer.from(firstFile.toString().replace('{', '{"role":"Client",')))).status, 'connection-invalid');
    await call(Buffer.alloc(2049), original, 'Room1', 400);
    await call(firstFile, Buffer.alloc(16385), 'Room1', 400);
    await call(Buffer.alloc(30000), original, 'Room1', 400);
    check((await api(`/sessions/${session.id}`)).sequence === lock.session.sequence,
      'Wrong seat, room, hash, JSON, IPv4 and oversized files are diagnosed without changing the session');

    await login('Room1', session); await panel.waitFor();
    assert.deepEqual(await seat.locator('option').evaluateAll(options => options.map(option => option.textContent)),
      ['請選擇要核對的席位', '房間 1／第 1 席 · Quest Alpha', '房間 1／第 2 席 · Quest Bravo']);
    await seat.selectOption(first.admissionId);
    await upload(json(secondConfig), original); await submit.click(); await message('連線檔屬於其他房間或席位');
    await upload(firstFile, Buffer.concat([original, Buffer.from('\n')])); await submit.click(); await message('原始位元組與鎖定版本不符');
    await upload(firstFile, original); await submit.click(); await message('連線檔與校正檔相符');
    check((await status.innerText()).includes('房間 1／第 1 席') && !await panel.getByText(firstConfig.joinTicket, { exact: true }).count(),
      'The room console identifies the seat and offers an actionable file diagnosis without displaying the ticket');
    await page.setViewportSize({ width: 390, height: 844 });
    check(await panel.evaluate(node => node.scrollWidth <= node.clientWidth + 1), 'Seat deployment checks fit on a narrow console');
    await panel.screenshot({ path: path.join(screenshots, 'mr-deployment-room-seat.png') });
    await page.setViewportSize({ width: 1440, height: 1080 });

    let requested, delivered;
    const started = new Promise(resolve => { requested = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    delivery = new Promise(resolve => { delivered = resolve; });
    async function held(route) {
      requested();
      try { const response = await route.fetch(); await gate; await route.fulfill({ response }); delivered(response.ok()); }
      catch { delivered(false); }
    }
    await page.route(routePattern, held);
    await submit.click(); await started;
    await seat.selectOption(second.admissionId);
    release(); assert.equal(await delivery, true); release = null;
    await page.unroute(routePattern, held);
    check(await submit.isDisabled() && await configInput.inputValue() === '' && await alignmentInput.inputValue() === '' &&
      (await status.innerText()).includes('請選擇席位'), 'A delayed response cannot restore a result or files after the seat changes');

    await seat.selectOption(first.admissionId); await upload(firstFile, original); await submit.click(); await message('連線檔與校正檔相符');
    await api(`/sessions/${session.id}/players/${first.id}`, 'DELETE', undefined, 'Master', 204, first.admissionId);
    const replacement = await add(session, 1, 'Quest Alpha renewed', first.id);
    assert.equal((await request(session, replacement, firstFile, original, 'Room1')).status, 'admission-changed');
    await page.locator('#refresh').click(); await seat.locator('option').filter({ hasText: 'Quest Alpha renewed' }).waitFor({ state: 'attached' });
    check(await seat.inputValue() === '' && await submit.isDisabled() && await configInput.inputValue() === '',
      'A replaced admission rejects the old file and clears the console’s prior result');
    await login('Master', session); await panel.waitFor();
    check((await seat.locator('option').allTextContents()).includes('房間 2／第 1 席 · Quest Charlie'), 'Master can select another occupied room in the same linked session');
    await page.locator('#logout').click();
    check(await panel.isHidden() && await seat.locator('option').count() === 0, 'Logout clears deployment selections');
    await api(`/sessions/${session.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
    await call(firstFile, original, 'Master', 409);
    check(true, 'Ended sessions cannot accept deployment checks');

    const independent = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [2] }, 'Master', 201);
    sessions.push(independent.id);
    const player = await add(independent, 2, 'Quest Delta');
    const roomFile = files.get(2);
    await api(`/sessions/${independent.id}/commands`, 'POST', { commandId: randomUUID(), action: 'SetRoomAlignment', roomAlignment: { room2: sha(roomFile) } });
    const independentConfig = json(await connection(independent, player));
    assert.equal((await request(independent, player, independentConfig, roomFile, 'Room2')).status, 'matched');
    assert.equal((await request(independent, player, json(otherConfig), roomFile, 'Room2')).status, 'ticket-invalid');
    await login('Room2', independent); await panel.waitFor();
    await seat.selectOption(player.admissionId); await upload(independentConfig, roomFile); await submit.click();
    await message('房間 2／第 1 席 · 連線檔與校正檔相符');
    check(true, 'An independent room can verify its own deployment files and rejects a valid ticket from the previous linked session');
  } finally {
    if (release) { release(); await delivery; }
    for (const id of sessions) if ((await api(`/sessions/${id}`)).state !== 'Ended')
      await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
    await page.close();
  }
};
