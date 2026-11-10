const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { createHash, randomUUID } = require('node:crypto');
const { mkdir, readFile, readdir, writeFile } = require('node:fs/promises');
const path = require('node:path');
const { holdTicketResponse } = require('./ticket-download-fence.cjs');

module.exports = async ({ context, api, tokens, base, root, directory, screenshots, check, captureErrors }) => {
  const page = await context.newPage();
  captureErrors(page);
  const roomIds = [1, 2, 3, 4, 5];
  const route = '/mr-deployment/venue-bundle';
  const panel = page.locator('#mr-venue-panel'), submit = page.locator('#mr-venue-submit'), status = page.locator('#mr-venue-status');
  const alignment = roomId => page.locator(`#mr-venue-alignment-${roomId}`);
  const active = new Set();
  const roomPath = id => `/sessions/${id}`;
  const hash = file => createHash('sha256').update(file).digest('hex');
  const command = (id, action, extra = {}) => api(roomPath(id) + '/commands', 'POST', { commandId: randomUUID(), action, ...extra });
  async function end(id) { await command(id, 'End'); active.delete(id); }
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#session-panel').waitFor();
  }
  async function post(body, expected, role = 'Master') {
    const response = await fetch(base + '/api' + route, { method: 'POST', body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokens[role]}` } });
    assert.equal(response.status, expected);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    return response.json();
  }
  async function add(sessionId, roomId, seat, playerId = randomUUID()) {
    const view = await api(roomPath(sessionId) + '/players', 'POST', { playerId, roomId, name: `Venue ${roomId}/${seat}`, headset: 'Quest3' });
    const player = view.players.find(entry => entry.id === playerId);
    return { playerId, admissionId: player.admissionId };
  }
  async function publish(session, port) {
    const streamId = randomUUID();
    const origin = 'GameServer';
    await api(roomPath(session.id) + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    const header = { sessionId: session.id, streamId, roomIds: session.roomIds, origin, calibration: 'quest-room-mr-v1',
      captureStartedAtUtc: new Date().toISOString().replace('Z', '0000+00:00') };
    const process = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
      input: JSON.stringify({ port: Number(new URL(base).port), route: '/api' + roomPath(session.id) + '/world/publish',
        token: tokens.GameServer, messages: [{ type: 'header', payload: header }] }) });
    assert.equal(process.status, 0, 'World source must attach before publishing a connection endpoint');
    const address = '192.0.2.51';
    const endpoint = await api(roomPath(session.id) + '/connection-endpoint', 'PUT', { version: 1, streamId, address, port }, 'GameServer');
    assert.equal(endpoint.streamId, streamId);
    return endpoint;
  }
  async function upload(files) {
    for (const roomId of roomIds)
      await alignment(roomId).setInputFiles({ name: `original-${roomId}.json`, mimeType: 'application/json', buffer: files[roomId - 1] });
  }
  function execute(name, args, options = {}) {
    const process = spawnSync(name, args, { encoding: 'utf8', timeout: 20000, windowsHide: true, ...options });
    assert.equal(process.status, 0, `${name} must complete successfully (${process.error?.code ?? process.status})`);
    return process.stdout;
  }
  async function inspect(download, request, files, endpoints) {
    assert.equal(download.suggestedFilename(), 'quest-mr-venue.zip');
    const folder = path.join(directory, request.topology.toLowerCase() + '-venue');
    await mkdir(folder);
    const outer = path.join(directory, request.topology.toLowerCase() + '-venue.zip');
    await download.saveAs(outer);
    execute('python', ['-m', 'zipfile', '-e', outer, folder]);
    const manifestPath = path.join(folder, 'venue.json');
    const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
    assert.deepEqual(manifest, { version: 1, topology: request.topology, rooms: request.rooms.map(({ roomId, sessionId }) => ({
      roomId, sessionId, ticketsZip: `room-0${roomId}-connections.zip`, alignmentFile: `room-0${roomId}-alignment.json` })) });
    assert.equal((await readdir(folder)).length, 11);
    const verify = { topology: request.topology, rooms: [] };
    for (const room of manifest.rooms) {
      const bytes = await readFile(path.join(folder, room.alignmentFile));
      assert.deepEqual(bytes, files[room.roomId - 1]);
      const seats = path.join(folder, `seats-${room.roomId}`);
      execute('python', ['-m', 'zipfile', '-e', path.join(folder, room.ticketsZip), seats]);
      const names = (await readdir(seats)).sort();
      assert.deepEqual(names, roomIds.map(seat => `room-0${room.roomId}-seat-0${seat}.json`));
      const endpoint = endpoints.get(room.sessionId), connectionFiles = [];
      for (const name of names) {
        const raw = await readFile(path.join(seats, name));
        const { role, address, port, roomAlignmentSha256, ...ticket } = JSON.parse(raw.toString('utf8'));
        assert.deepEqual({ role, address, port, roomAlignmentSha256 }, { role: 'Client', address: endpoint.address, port: endpoint.port, roomAlignmentSha256: hash(bytes) });
        assert.deepEqual(Object.keys(ticket), ['joinTicket']);
        connectionFiles.push(raw.toString('base64'));
      }
      verify.rooms.push({ roomId: room.roomId, sessionId: room.sessionId, connectionFiles, alignmentFile: bytes.toString('base64') });
    }
    const result = await api('/mr-deployment/venue-check', 'POST', verify);
    assert.ok(result.allMatched && result.seats.length === 25);
    if (process.env.VR_COMMAND_VENUE_DEPLOY_CHECK === '1') {
      const options = { env: { ...process.env, VR_COMMAND_MASTER_KEY: tokens.Master } };
      const common = ['-NoProfile', '-File', path.join(root, 'scripts/deploy-quest.ps1'), '-ManagementApi', base];
      const report = JSON.parse(execute('pwsh', [...common, '-VenueManifest', manifestPath], options));
      const direct = JSON.parse(execute('pwsh', [...common, '-VenueBundle', outer], options));
      assert.deepEqual(direct, report);
      assert.ok(direct.managementVerified && direct.topology === request.topology);
      const seat = JSON.parse(execute('pwsh', [...common, '-VenueBundle', outer, '-RoomId', '4', '-Seat', '2', '-CheckOnly'], options));
      assert.equal(seat.roomId, 4);
      assert.equal(seat.seat, 2);
      assert.equal(seat.mode, 'MR');
      assert.equal(seat.alignmentSha256, hash(files[3]));
      assert.ok(seat.managementVerified && seat.alignmentPinsVerified);
    }
  }

  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', { name: '五房部署包測試', briefing: '25 seats and measured file bytes', durationSeconds: 600,
      environment: { mode: 'MR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const files = [];
    const markers = [[-2, -2], [2, -2], [-2, 2]].map(([x, z]) => ({ room: { x, z }, tracking: { x: x + 1, z: z - 1 } }));
    for (const roomId of roomIds) {
      const report = await api('/room-alignment', 'POST', { roomId, markers });
      files.push(Buffer.from('\ufeff' + JSON.stringify(report, null, 2).replaceAll('\n', '\r\n') + '\r\n'));
    }
    for (const topology of ['Linked', 'Independent']) {
      const sessions = topology === 'Linked'
        ? [await api('/sessions', 'POST', { missionId: mission.id, mode: topology, roomIds }, 'Master', 201)]
        : (await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Master', 201, undefined, randomUUID())).sessions;
      for (const session of sessions) active.add(session.id);
      const request = { topology, rooms: [] };
      for (const session of sessions) {
        const roomAlignment = Object.fromEntries(session.roomIds.map(id => [`room${id}`, hash(files[id - 1])]));
        await command(session.id, 'SetRoomAlignment', { roomAlignment });
        for (const roomId of session.roomIds) {
          const room = { roomId, sessionId: session.id, players: [], alignmentFile: files[roomId - 1].toString('base64') };
          for (const seat of roomIds) room.players.push(await add(session.id, roomId, seat));
          request.rooms.push(room);
        }
      }
      if (topology === 'Linked') {
        await post(request, 403, 'Room1');
        await post(request, 403, 'GameServer');
        await login('Room1');
        check(await panel.isHidden(), 'Five-room MR deployment is available only to the master console');
        await post({ ...request, rooms: request.rooms.slice(1) }, 400);
        await post({ ...request, rooms: request.rooms.map((room, i) => i === 0
          ? { ...room, alignmentFile: Buffer.alloc(17 * 1024).toString('base64') } : room) }, 400);
        const missing = await post(request, 409);
        assert.equal(missing.code, 'venue-endpoint-missing');
      }
      await login('Master'); await panel.waitFor(); await upload(files);
      if (topology === 'Linked') {
        await submit.click();
        await status.filter({ hasText: '房間 1 · 尚未公布端點' }).waitFor();
        check(await panel.locator('label').filter({ hasText: '5/5 Quest 3 席' }).count() === 5,
          'Five complete rosters do not allow export until the game source publishes its endpoint');
      }
      const endpoints = new Map();
      for (const [index, session] of sessions.entries()) endpoints.set(session.id, await publish(session, 17800 + index));
      if (topology === 'Linked') {
        const changedFile = Buffer.concat([files[3], Buffer.from('\n')]);
        await alignment(4).setInputFiles({ name: 'reformatted.json', mimeType: 'application/json', buffer: changedFile });
        await submit.click(); await status.filter({ hasText: '房間 4 · 校正檔不符' }).waitFor();
        check(true, 'Reformatting an otherwise valid calibration JSON rejects the entire ZIP and identifies the affected room');
        await upload(files);
        const room = request.rooms[2], prior = room.players[1];
        await api(`${roomPath(room.sessionId)}/players/${prior.playerId}`, 'DELETE', undefined, 'Master', 204, prior.admissionId);
        room.players[1] = await add(room.sessionId, room.roomId, 2, prior.playerId);
        const stale = structuredClone(request);
        stale.rooms[2].players[1] = prior;
        const error = await post(stale, 409);
        check(error.code === 'venue-roster-changed' && error.roomId === 3, 'A replaced admission rejects the entire ZIP for a stale roster');
        await page.locator('#refresh').click();
        await page.locator('#last-update').waitFor();
      }
      const before = await api('/sessions');
      const downloading = page.waitForEvent('download');
      await submit.click();
      const downloaded = await downloading;
      await status.filter({ hasText: '已下載五房部署包' }).waitFor();
      await inspect(downloaded, request, files, endpoints);
      assert.deepEqual(await api('/sessions'), before);
      check(true, `${topology} download verifies 25 original admissions and exact published destinations without adding session events`);
      await panel.screenshot({ path: path.join(screenshots, `mr-venue-${topology.toLowerCase()}.png`) });
      if (topology === 'Independent') {
        const room = request.rooms[4], seat = room.players[0];
        const result = await holdTicketResponse(page, base + '/api' + route, () => submit.click(), async () => {
          await api(`${roomPath(room.sessionId)}/players/${seat.playerId}`, 'DELETE', undefined, 'Master', 204, seat.admissionId);
          await add(room.sessionId, room.roomId, 1, seat.playerId);
        }, async () => {
          await status.filter({ hasText: /名冊已變更|已下載五房/ }).waitFor();
          return status.innerText();
        });
        await writeFile(path.join(screenshots, 'mr-venue-late-ticket.json'), JSON.stringify(result, null, 2));
        check(result.signedResponses === 1 && result.downloads === 0 && result.message.includes('未下載'),
          'A signed 25-seat MR ZIP cannot download after one original room admission changes during delivery');
      }
      for (const session of sessions) await end(session.id);
      const ended = await post(request, 409);
      assert.equal(ended.code, 'venue-session-changed');
    }
  } finally {
    await page.close();
    for (const id of active) await end(id);
  }
};
