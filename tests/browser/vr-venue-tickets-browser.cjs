const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { holdTicketResponse } = require('./ticket-download-fence.cjs');

module.exports = async ({ context, api, tokens, base, root, directory, screenshots, check, captureErrors }) => {
  const page = await context.newPage(), active = new Set(), roomIds = [1, 2, 3, 4, 5];
  captureErrors(page);
  const preview = '/vr-deployment/venue', bundle = preview + '-bundle', endpoint = base + '/api' + bundle;
  const panel = page.locator('#vr-venue-panel'), load = page.locator('#vr-venue-read'), issue = page.locator('#vr-venue-issue');
  const status = page.locator('#vr-venue-status');
  const verify = '/vr-deployment/venue-check';
  const fence = plan => ({ topology: plan.topology, rooms: plan.rooms.map(room => ({
    roomId: room.roomId, sessionId: room.sessionId, streamId: room.endpoint.streamId,
    players: room.seats.map(({ playerId, admissionId }) => ({ playerId, admissionId }))
  })) });
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function post(body, expected, role = 'Master') {
    const response = await fetch(endpoint, { method: 'POST', body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tokens[role] } });
    assert.equal(response.status, expected);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    return response.json();
  }
  async function end(id) {
    await api(`/sessions/${id}/commands`, 'POST', { action: 'End', commandId: randomUUID() });
    active.delete(id);
  }
  function publishWorld(sessionId, messages) {
    const fixture = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], {
      encoding: 'utf8', timeout: 6000, windowsHide: true, input: JSON.stringify({ port: Number(new URL(base).port),
        route: `/api/sessions/${sessionId}/world/publish`, token: tokens.GameServer, messages }) });
    assert.equal(fixture.status, 0, fixture.stderr);
    return JSON.parse(fixture.stdout);
  }
  async function publish(session, address, port) {
    const streamId = randomUUID(), origin = 'Simulation';
    const route = `/sessions/${session.id}`;
    await api(route + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    const header = { sessionId: session.id, streamId, origin, roomIds: session.roomIds,
      captureStartedAtUtc: new Date().toISOString().replace('Z', '0000+00:00') };
    publishWorld(session.id, [{ type: 'header', payload: header }]);
    await api(route + '/connection-endpoint', 'PUT', { version: 1, streamId, address, port }, 'GameServer');
    return header;
  }
  async function add(id, roomId, seat, playerId = randomUUID()) {
    return api(`/sessions/${id}/players`, 'POST', { playerId, roomId, name: `VR ${roomId} seat ${seat}`,
      headset: seat % 2 === 0 ? 'ViveXr' : 'Quest3' });
  }
  async function inspect(download, plan) {
    assert.equal(download.suggestedFilename(), 'vr-venue-connections.zip');
    const file = path.join(directory, `vr-${plan.topology}-seats.zip`);
    await download.saveAs(file);
    const reader = spawnSync('python', ['-c', `import base64,io,json,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as outer:
    assert outer.testzip() is None
    manifest = json.loads(outer.read('venue.json'))
    assert outer.namelist() == ['venue.json', *[room['ticketsZip'] for room in manifest['rooms']]]
    rooms = []
    for room in manifest['rooms']:
        with zipfile.ZipFile(io.BytesIO(outer.read(room['ticketsZip']))) as inner:
            assert inner.testzip() is None
            rooms.append([[name, base64.b64encode(inner.read(name)).decode()] for name in inner.namelist()])
    print(json.dumps([manifest, rooms], ensure_ascii=True))`, file], { encoding: 'utf8', timeout: 6000, windowsHide: true });
    assert.equal(reader.status, 0, reader.stderr);
    assert.ok(Object.values(tokens).every(token => !reader.stdout.includes(token)));
    const [manifest, rooms] = JSON.parse(reader.stdout);
    assert.deepEqual(manifest, { version: 1, mode: 'VR', topology: plan.topology, rooms: plan.rooms.map(room => ({
      roomId: room.roomId, sessionId: room.sessionId, address: room.endpoint.address, port: room.endpoint.port,
      ticketsZip: `room-0${room.roomId}-connections.zip`, seats: room.seats.map(seat => ({ seat: seat.number, name: seat.name }))
    })) });
    for (const [index, files] of rooms.entries()) {
      const room = plan.rooms[index];
      assert.deepEqual(files.map(([name]) => name), roomIds.map(seat => `room-0${room.roomId}-seat-0${seat}.json`));
      for (const [seatIndex, [, encoded]] of files.entries()) {
        const raw = Buffer.from(encoded, 'base64').toString('utf8');
        assert.ok(Object.values(tokens).every(token => !raw.includes(token)));
        const config = JSON.parse(raw);
        const seat = room.seats[seatIndex];
        assert.deepEqual(Object.keys(config).sort(), ['address', 'joinTicket', 'port', 'role']);
        assert.equal(config.address, room.endpoint.address); assert.equal(config.port, room.endpoint.port); assert.equal(config.role, 'Client');
        const claims = await api('/player-tickets/validate', 'POST',
          { ticket: config.joinTicket, sessionId: room.sessionId, protocolVersion: 2 }, 'GameServer');
        assert.equal(claims.playerId, seat.playerId); assert.equal(claims.admissionId, seat.admissionId);
        assert.equal(claims.roomId, room.roomId); assert.equal(claims.seat + 1, seat.number);
      }
    }
    return { topology: plan.topology, rooms: plan.rooms.map((room, index) => ({
      roomId: room.roomId, sessionId: room.sessionId, connectionFiles: rooms[index].map(([, encoded]) => encoded)
    })) };
  }

  try {
    assert.deepEqual(await api('/sessions'), []);
    await api(preview, 'GET', undefined, 'Room1', 403);
    await post({}, 403, 'GameServer');
    await login('Room1');
    check(await panel.isHidden(), 'VR venue ticketing is confined to the master in both the console and API');
    const mission = await api('/missions', 'POST', { name: 'VR 25 seats', briefing: '', durationSeconds: 600,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    let previous, previousOverview;
    for (const topology of ['Linked', 'Independent']) {
      const sessions = topology === 'Linked'
        ? [await api('/sessions', 'POST', { missionId: mission.id, mode: topology, roomIds }, 'Master', 201)]
        : (await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Master', 201, undefined, randomUUID())).sessions;
      for (const session of sessions) active.add(session.id);
      if (previous) {
        const conflict = await post(previous, 409);
        check(conflict.roomId === 1 && conflict.code === 'vr-venue-session-changed', 'Old linked seats cannot be issued into a replacement independent room');
      }
      let linkedSource;
      for (const session of sessions) {
        for (const room of session.roomIds)
          for (const seat of roomIds) if (room !== 5 || seat !== 5) await add(session.id, room, seat);
        if (topology === 'Linked') {
          const noSource = await api(preview);
          check(!noSource.ready && noSource.rooms.every(room => room.problem === 'vr-venue-endpoint-missing'),
            'A linked venue with players still needs its game server to publish the endpoint');
        }
        const source = await publish(session, topology === 'Linked' ? '127.0.0.1' : '192.0.2.51', 7770 + session.roomIds[0]);
        if (topology === 'Linked') linkedSource = source;
      }
      await login('Master');
      const roomOverview = await api('/rooms/readiness');
      const deskOverview = await api('/rooms/readiness', 'GET', undefined, 'Room1');
      assert.deepEqual(deskOverview.rooms.map(row => row.roomId), [1]);
      assert.deepEqual(deskOverview.rooms[0].endpoint, roomOverview.rooms[0].endpoint);
      for (const row of roomOverview.rooms) {
        const source = sessions.find(session => session.id === row.sessionId);
        assert.deepEqual(row.endpoint, await api(`/sessions/${source.id}/connection-endpoint`));
        const label = `UDP ${row.endpoint.address}:${row.endpoint.port}`
          + (topology === 'Linked' ? ' · 五房共用 · 僅同機' : '');
        await page.locator(`[data-room-endpoint="${row.roomId}"]`).filter({ hasText: label }).waitFor();
      }
      check(await page.locator('[data-room-endpoint]').count() === 5,
        topology + ' room cards show the original published UDP settings with room-scoped API access');
      await load.click();
      await page.locator('#vr-venue-rooms li').last().filter({ hasText: '4/5 席' }).waitFor();
      check(await issue.isDisabled() && await status.textContent() === '請確認各房列出的條件，再重新讀取。',
        topology + ' venue requires five current admissions in every room');
      await add(sessions.at(-1).id, 5, 5);
      await page.locator('#refresh').click();
      await page.locator('#vr-venue-status').filter({ hasText: '名冊已變更' }).waitFor();
      await load.click();
      await status.filter({ hasText: '已讀取 25 席' }).waitFor();
      const plan = await api(preview);
      const ready = fence(plan);
      const mismatch = structuredClone(ready); mismatch.rooms[4].streamId = randomUUID();
      const conflict = await post(mismatch, 409);
      await post(ready, 403, 'Room1');
      check(plan.ready && conflict.roomId === 5 && conflict.code === 'vr-venue-source-changed',
        topology + ' venue uses published sources and refuses a stale source before issuing a ZIP');
      if (topology === 'Linked') assert.match(await page.locator('#vr-venue-rooms').textContent(), /僅本機/);
      if (topology === 'Independent') {
        const archiveRoute = '**/api' + bundle;
        for (const fault of ['bytes', 'request']) {
          const received = Promise.withResolvers();
          const substitute = async route => {
            try {
              const original = await route.fetch(), headers = original.headers(), body = Buffer.from(await original.body());
              assert.equal(original.status(), 200);
              if (fault === 'bytes') body[0] ^= 1;
              else headers['x-vrcommand-archive-request'] = randomUUID();
              await route.fulfill({ response: original, headers, body });
              received.resolve(null);
            } catch (error) { received.resolve(error); }
          };
          const downloads = [];
          const record = file => downloads.push(file);
          await page.route(archiveRoute, substitute, { times: 1 });
          page.on('download', record);
          try {
            await issue.click();
            await status.filter({ hasText: /無法核對五房連線檔|已下載五房/ }).waitFor();
            const error = await received.promise;
            if (error) throw error;
            check((await status.textContent()).includes('無法核對五房連線檔') && downloads.length === 0,
              fault === 'bytes' ? 'Modified ZIP bytes are rejected even when the response is labelled as a ZIP'
                : 'A genuine ZIP with the wrong issuance request ID is rejected');
          } finally {
            await page.unroute(archiveRoute, substitute);
            page.off('download', record);
            for (const file of downloads) await file.delete();
          }
          await load.click();
          await status.filter({ hasText: '已讀取 25 席' }).waitFor();
        }
      }
      const downloaded = page.waitForEvent('download');
      await issue.click();
      const proof = await inspect(await downloaded, plan);
      check(true, topology + ' browser ZIP has all 25 original signed admissions, room and seat names, and published endpoints');
      const readback = await api(verify, 'POST', proof);
      const sampleRoute = '/venue/tracked-readiness';
      const scope = { topology, rooms: proof.rooms.map(({ roomId, sessionId }) => ({ roomId, sessionId })) };
      const sample = await api(sampleRoute, 'POST', { ...scope, rooms: [...scope.rooms].reverse() });
      const originalSessions = [...new Set(scope.rooms.map(room => room.sessionId))];
      check(sample.version === 1 && sample.maxSourceAgeMilliseconds === 1500 && sample.topology === topology
        && typeof sample.sampledAtUtc === 'string' && sample.sessions.length === originalSessions.length
        && sample.sessions.every((row, i) => row.sessionId === originalSessions[i] && row.sampledAtUtc === sample.sampledAtUtc
          && row.sourceState === 'WaitingFrame' && row.worldSequence === 0 && row.players.every(seat => !seat.canParticipate)),
      `${topology} tracking sample binds every original session to a common clock and waits for accepted frames`);
      if (topology === 'Independent') {
        await api(sampleRoute, 'POST', scope, 'Room1', 403);
        await api(sampleRoute, 'POST', { ...scope, rooms: scope.rooms.slice(1) }, 'Master', 400);
        await api(sampleRoute, 'POST', { ...scope, rooms: scope.rooms.map((room, index) => ({ ...room,
          sessionId: originalSessions[(index + 1) % originalSessions.length] })) }, 'Master', 409);
      }
      const wrong = structuredClone(proof), first = JSON.parse(Buffer.from(wrong.rooms[0].connectionFiles[0], 'base64').toString('utf8'));
      first.port++;
      wrong.rooms[0].connectionFiles[0] = Buffer.from(JSON.stringify(first)).toString('base64');
      const denied = await api(verify, 'POST', wrong);
      await api(verify, 'POST', proof, 'Room1', 403);
      check(readback.allMatched && readback.seats.length === 25
        && readback.seats.filter(seat => seat.headset === 'Quest3').length === 15
        && !denied.allMatched && denied.seats[0].status === 'endpoint-mismatch'
        && denied.seats.slice(1).every(seat => seat.status === 'matched'),
        topology + ' VR live check verifies original bytes, current headset assignment and endpoint');
      const deployment = await api(verify, 'POST', { ...proof, requireLiveSource: true });
      const blockedBy = topology === 'Linked' ? 'endpoint-mismatch' : 'source-stale';
      check(!Object.hasOwn(readback, 'liveSourceVerified') && !deployment.allMatched && deployment.liveSourceVerified === false
        && deployment.seats.length === 25 && deployment.seats.every(seat => seat.status === blockedBy),
      `${topology} device writes reject ${blockedBy} even when the original 25 signed files pass read-only verification`);
      if (topology === 'Linked') {
        const windowsProof = { ...proof, requireLiveSource: true, allowLoopback: true };
        const waiting = await api(verify, 'POST', windowsProof);
        check(!waiting.allMatched && waiting.liveSourceVerified === false && waiting.seats.every(seat => seat.status === 'source-stale'),
          'Windows loopback deployment still requires a current world frame');
        const state = await api(`/sessions/${linkedSource.sessionId}`);
        const players = state.players.map(player => {
          const head = { x: (player.roomId - 3) * 14, y: 1.65, z: -3 };
          return { id: player.id, roomId: player.roomId, head, muzzle: head, connected: false,
            forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: 30, reserve: 90, rig: { kind: 'None' } };
        });
        const packet = { sequence: 1, observedSequence: state.sequence, elapsedMilliseconds: 0, weather: 'Clear', lightning: false,
          throughCombatSequence: 0, events: [],
          frame: { phase: 'Preparing', tick: 0, night: false, visibility: 'Clear', behavior: 'Hold', autoAttack: false,
            throughSequence: 0, players, enemies: [] } };
        const fresh = { ...packet, sequence: 2, elapsedMilliseconds: Date.now() - Date.parse(linkedSource.captureStartedAtUtc) };
        const accepted = publishWorld(state.id, [{ type: 'header', payload: linkedSource },
          { type: 'frame', payload: packet }, { type: 'frame', payload: fresh }]);
        const current = await api(verify, 'POST', windowsProof);
        const quest = await api(verify, 'POST', { ...proof, requireLiveSource: true });
        check(accepted.acceptedSequence === 2 && current.allMatched && current.liveSourceVerified === true
          && current.seats.length === 25 && current.seats.every(seat => seat.status === 'matched')
          && quest.liveSourceVerified === false && quest.seats.every(seat => seat.status === 'endpoint-mismatch'),
          'A current Windows loopback source verifies every original seat while Quest still requires a LAN endpoint');
        await panel.screenshot({ path: path.join(screenshots, 'vr-venue-tickets.png') });
      }
      if (topology === 'Independent') {
        let notify, release, finish, late = false;
        const requested = new Promise(resolve => { notify = resolve; });
        const gate = new Promise(resolve => { release = resolve; });
        const done = new Promise(resolve => { finish = resolve; });
        const target = '**/api' + bundle, lateDownload = () => { late = true; };
        const hold = async route => {
          try {
            const response = await route.fetch();
            assert.equal(response.status(), 200); notify(null);
            await gate;
            await route.fulfill({ response });
            finish(null);
          } catch (error) { notify(error); finish(error); }
        };
        await page.route(target, hold);
        page.on('download', lateDownload);
        try {
          await issue.click();
          const error = await requested;
          if (error) throw error;
          await page.locator('#tab-missions').click();
        } finally {
          release();
          const error = await done;
          await page.unroute(target, hold);
          page.off('download', lateDownload);
          if (error) throw error;
        }
        await page.locator('#tab-operations').click();
        check(!late && await issue.isDisabled() && await page.locator('#vr-venue-rooms li').count() === 0,
          'A held signed venue ZIP cannot download after leaving the operations view');
      }

      const seat = plan.rooms[4].seats[0];
      const replace = async () => {
        await api(`/sessions/${ready.rooms[4].sessionId}/players/${seat.playerId}`, 'DELETE', undefined, 'Master', 204, seat.admissionId);
        await add(ready.rooms[4].sessionId, 5, 1, seat.playerId);
      };
      if (topology === 'Linked') {
        const result = await holdTicketResponse(page, endpoint, () => issue.click(), replace, async () => {
          await status.filter({ hasText: /名冊已變更|已下載五房/ }).waitFor();
          return status.innerText();
        });
        await fs.writeFile(path.join(screenshots, 'vr-venue-late-ticket.json'), JSON.stringify(result, null, 2));
        check(result.signedResponses === 1 && result.downloads === 0 && result.message.includes('未下載'),
          'A signed 25-seat VR ZIP cannot download after one admission changes during delivery');
      } else await replace();
      const stale = await post(ready, 409);
      check(stale.roomId === 5 && stale.code === 'vr-venue-roster-changed', topology + ' venue rejects one replaced admission without issuing the other 24');
      const after = await api(verify, 'POST', proof);
      check(!after.allMatched && after.seats[20].status === 'admission-changed'
        && after.seats.filter(seat => seat.status === 'matched').length === 24,
        topology + ' VR live check rejects the superseded original ticket after reassigning one seat');
      previous = ready;
      previousOverview = roomOverview;
      for (const session of sessions) await end(session.id);
    }
    const one = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
    const two = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [2] }, 'Master', 201);
    active.add(one.id); active.add(two.id);
    const staleRoomRoute = route => route.fulfill({ json: previousOverview });
    await page.route('**/api/rooms/readiness', staleRoomRoute);
    try {
      const received = page.waitForResponse('**/api/rooms/readiness');
      await page.locator('#refresh').click();
      await received;
      await page.waitForFunction(() => {
        const cells = [...document.querySelectorAll('[data-room-endpoint]')];
        return cells.length === 2 && cells.every(cell => cell.textContent === '連線端點未確認');
      });
      check(true, 'Old endpoint responses cannot restore addresses to a replacement room');
    } finally { await page.unroute('**/api/rooms/readiness', staleRoomRoute); }
    await publish(one, '192.0.2.51', 7777); await publish(two, '192.0.2.51', 7777);
    const repeated = await api(preview);
    check(!repeated.ready && repeated.rooms[1].problem === 'vr-venue-endpoint-reused'
      && repeated.rooms[2].problem === 'vr-venue-session-missing', 'Independent venue preview distinguishes shared endpoints and empty rooms');
  } finally {
    await page.close();
    for (const id of active) await end(id);
  }
};
