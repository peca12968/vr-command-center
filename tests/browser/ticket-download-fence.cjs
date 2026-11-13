const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { spawnSync } = require('node:child_process');

async function holdTicketResponse(page, url, issue, mutate, settled) {
  const captured = Promise.withResolvers(), release = Promise.withResolvers(), delivered = Promise.withResolvers(), download = Promise.withResolvers();
  let issued = 0, downloads = 0, timer;
  const record = file => { downloads++; download.resolve(file); };
  const hold = async route => {
    try {
      const response = await route.fetch(); issued++;
      assert.equal(response.status(), 200);
      captured.resolve();
      await release.promise;
      await route.fulfill({ response });
      delivered.resolve();
    } catch (error) { captured.resolve(error); delivered.resolve(error); }
  };
  await page.route(url, hold); page.on('download', record);
  try {
    await issue();
    const issueError = await Promise.race([captured.promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('No original ticket response captured')), 8000);
    })]);
    if (issueError) throw issueError;
    await mutate();
    release.resolve();
    const deliveryError = await delivered.promise;
    if (deliveryError) throw deliveryError;
    const message = await settled();
    if (/已產生|已下載五房/.test(message)) await (await download.promise).delete();
    return { signedResponses: issued, downloads, message };
  } finally {
    clearTimeout(timer);
    release.resolve(); await page.unroute(url, hold); page.off('download', record);
  }
}

async function checkTicketDownloadFence({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage(), cases = [];
  captureErrors(page);
  const mission = await api('/missions', 'POST', { name: 'Ticket download roster check', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const roomId = (await api('/rooms')).find(room => !room.sessionId).id;
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [roomId] }, 'Master', 201);
  const detail = '/sessions/' + session.id, playerId = randomUUID(), playerRoute = detail + '/players/' + playerId;
  const add = name => api(detail + '/players', 'POST', { playerId, roomId, name, headset: 'Quest3' });
  let { players: [player] } = await add('Original admission');
  try {
    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    const shortcut = page.locator('#download-roster-room-tickets');
    check(await shortcut.isHidden(), 'Room ticket shortcut waits for a room selection');
    for (const scope of ['seat', 'room', 'roster-room']) {
      const isRoom = scope !== 'seat', previous = player.admissionId;
      const routeUrl = base + '/api' + (isRoom ? detail + '/rooms/' + roomId + '/join-ticket-bundle' : playerRoute + '/join-ticket');
      await page.locator('#roster').filter({ hasText: player.name }).waitFor();
      if (scope === 'room') await page.locator('#ticket-room').selectOption(String(roomId));
      if (scope === 'roster-room') {
        await page.locator('#ticket-room').selectOption('');
        await page.locator(`[data-begin-room="${roomId}"] button`).click();
        await page.locator('#roster-title:focus').waitFor();
        check(await page.locator('#ticket-room').inputValue() === '' && await shortcut.isDisabled()
          && (await page.locator('#roster-ticket-destination').textContent()).includes('請先設定'),
          'Roster shortcut waits for a valid endpoint without changing the separate ticket selector');
      }
      await page.locator('#game-address').fill('127.0.0.1');
      if (scope === 'roster-room') {
        await page.locator('#game-port').fill('17777');
        check(await shortcut.isEnabled()
          && (await page.locator('#roster-ticket-destination').textContent()).includes('127.0.0.1:17777'),
          'Manual endpoint edits immediately update the roster shortcut');
      }
      const button = scope === 'roster-room' ? shortcut
        : isRoom ? page.locator('#download-room-tickets') : page.locator('[data-player-action=ticket]');
      const result = await holdTicketResponse(page, routeUrl, () => button.click(), async () => {
        await api(playerRoute, 'DELETE', undefined, 'Master', 204, previous);
        ({ players: [player] } = await add('Replacement for ' + scope));
        assert.notEqual(player.admissionId, previous);
      }, async () => {
        await page.waitForFunction(() => !document.querySelector('#session-select').disabled);
        return page.locator('#notice').innerText();
      });
      cases.push({ scope, replaced: player.admissionId !== previous, ...result });
      await page.locator('#refresh').click();
      await page.locator('#roster').filter({ hasText: player.name }).waitFor();
    }
    const url = base + '/api' + detail + '/rooms/' + roomId + '/join-ticket-bundle';
    const [file, response] = await Promise.all([page.waitForEvent('download'),
      page.waitForResponse(reply => reply.url() === url && reply.request().method() === 'POST'), shortcut.click()]);
    assert.equal(response.status(), 200);
    assert.equal(response.request().postDataJSON().port, 17777);
    assert.deepEqual(response.request().postDataJSON().players, [{ playerId, admissionId: player.admissionId }]);
    assert.equal(file.suggestedFilename(), `room-${String(roomId).padStart(2, '0')}-connections.zip`);
    await file.delete();
    check(true, 'Roster shortcut downloads the newly confirmed room bundle after refresh');
    await fs.writeFile(path.join(screenshots, 'ticket-download-fence.json'), JSON.stringify(cases, null, 2));
    for (const result of cases)
      check(result.signedResponses === 1 && result.replaced && result.downloads === 0 && result.message.includes('名冊已變更'),
        `A signed ${result.scope} download is discarded after another operator replaces the original admission`);
  } finally {
    await page.close();
    await api(detail + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
  }
  await checkManagedRoomTickets({ context, api, tokens, base, check, captureErrors, mission });
}

async function checkManagedRoomTickets({ context, api, tokens, base, check, captureErrors, mission }) {
  const roomIds = [1, 2, 3, 4, 5], roomId = 1;
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds }, 'Master', 201);
  const detail = '/sessions/' + session.id, streamId = randomUUID(), origin = 'Simulation';
  const port = 17777, address = '192.0.2.52';
  const page = await context.newPage();
  captureErrors(page);
  try {
    await api(detail + '/players', 'POST', { playerId: randomUUID(), roomId, name: 'Original managed seat', headset: 'Quest3' });
    await api(detail + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    const current = await api(detail);
    const [player] = current.players;
    const seatRoute = detail + '/players/' + player.id + '/join-ticket';
    const issueSeat = (expected, role = 'Room1') => api(seatRoute, 'POST', undefined, role, expected, player.admissionId);
    const header = { sessionId: session.id, streamId, origin, roomIds,
      captureStartedAtUtc: new Date().toISOString().replace('Z', '0000+00:00') };
    const publish = (...packets) => {
      const messages = [{ type: 'header', payload: header }, ...packets.map(payload => ({ type: 'frame', payload }))];
      const result = spawnSync('python', [path.resolve(__dirname, '../../scripts/world_test_socket.py')], {
        encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: '/api' + detail + '/world/publish', token: tokens.GameServer, messages })
      });
      assert.equal(result.status, 0, result.stderr);
      return JSON.parse(result.stdout);
    };
    const head = { x: -28, y: 1.65, z: -3 };
    const packet = (sequence, elapsedMilliseconds) => ({ sequence, observedSequence: current.sequence, elapsedMilliseconds,
      weather: 'Clear', lightning: false, throughCombatSequence: 0, events: [],
      frame: { phase: 'Preparing', tick: 0, night: false, visibility: 'Clear', behavior: 'Hold', autoAttack: false, throughSequence: 0,
        players: [{ id: player.id, roomId, head, muzzle: head, connected: false, forward: { x: 0, y: 0, z: 1 },
          health: 100, magazine: 30, reserve: 90, rig: { kind: 'None' } }], enemies: [] } });
    const elapsed = () => Date.now() - Date.parse(header.captureStartedAtUtc);
    const route = detail + '/rooms/' + roomId + '/join-ticket-bundle';
    const request = { address, port, players: [{ playerId: player.id, admissionId: player.admissionId }] };
    publish();
    await api('/venue/connection-endpoints', 'PUT', { version: 1, topology: 'Linked',
      servers: [{ sessionId: session.id, endpoint: { version: 1, streamId, address, port } }] }, 'GameServer');
    assert.equal((await api(route, 'POST', request, 'Room1', 409)).code, 'ticket-source-unavailable');
    assert.equal((await issueSeat(409)).code, 'ticket-source-unavailable');
    publish(packet(1, 0), packet(2, elapsed()));
    const invitation = await issueSeat(200);
    assert.deepEqual(invitation.endpoint, { address, port });
    await issueSeat(403, 'Room2');
    check(true, 'Single-seat issuance returns the original managed endpoint to its own room controller');
    assert.equal((await api(route, 'POST', { ...request, port: port + 1 }, 'Room1', 409)).code, 'ticket-endpoint-mismatch');
    assert.equal((await api(route, 'POST', { ...request, address: '192.0.2.53' }, 'Master', 409)).code, 'ticket-endpoint-mismatch');
    check(true, 'Managed room ZIP API refuses a different IPv4 or UDP port, including direct requests from a room controller');

    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    await page.locator('#roster-room').selectOption(String(roomId));
    const status = page.locator('#roster-ticket-destination'), shortcut = page.locator('#download-roster-room-tickets');
    const seat = page.locator('[data-player-action="ticket"]');
    await status.filter({ hasText: '遊戲來源暫未確認' }).waitFor();
    check(await shortcut.isDisabled() && await seat.isDisabled() && (await status.textContent()).includes(`${address}:${port}`),
      'An expired original frame disables both single-seat and roster ZIP downloads');
    assert.equal((await api(route, 'POST', request, 'Room1', 409)).code, 'ticket-source-unavailable');
    publish(packet(3, elapsed()));
    await shortcut.locator('xpath=self::*[not(@disabled)]').waitFor();
    await page.locator('#game-port').fill(String(port + 1));
    check(await shortcut.isDisabled() && (await status.textContent()).includes(`公告端點為 ${address}:${port}`),
      'A manual port from another destination is blocked beside the roster shortcut');
    await page.locator('#game-address').fill('');
    const [seatFile, seatResponse] = await Promise.all([page.waitForEvent('download'),
      page.waitForResponse(reply => reply.url() === base + '/api' + seatRoute && reply.request().method() === 'POST'), seat.click()]);
    assert.equal(seatResponse.status(), 200);
    assert.equal(seatResponse.headers()['cache-control'], 'no-store');
    const seatTicket = await seatResponse.json();
    const config = JSON.parse(await fs.readFile(await seatFile.path(), 'utf8'));
    assert.deepEqual(config, { role: 'Client', address, port, joinTicket: seatTicket.ticket });
    const resolved = await api('/player-tickets/validate', 'POST',
      { ticket: config.joinTicket, sessionId: session.id, protocolVersion: 2 }, 'GameServer');
    assert.equal(resolved.admissionId, player.admissionId);
    await seatFile.delete();
    check(true, 'A reissued single-seat file uses the signed response endpoint even when the manual fields are blank or wrong');
    publish(packet(4, elapsed()));
    await page.locator('#apply-connection-endpoint').click();
    const [file, response] = await Promise.all([page.waitForEvent('download'),
      page.waitForResponse(reply => reply.url() === base + '/api' + route && reply.request().method() === 'POST'), shortcut.click()]);
    assert.equal(response.status(), 200);
    assert.equal(response.headers()['cache-control'], 'no-store');
    assert.deepEqual(response.request().postDataJSON(), request);
    await file.delete();
    check(true, 'A fresh original frame and explicit apply restore the exact published endpoint and room ZIP');
  } finally {
    await page.close();
    await api(detail + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
  }
}

module.exports = { checkTicketDownloadFence, holdTicketResponse };
