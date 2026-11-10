const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors, participationOnly }) => {
  const rooms = [1, 2, 3, 4, 5];
  const page = await context.newPage();
  captureErrors(page);
  const active = new Set();
  const option = page.locator('#venue-full-tracking');
  const start = page.locator('#venue-begin');
  const liveTracking = page.locator('#venue-live-tracking');
  const liveSummary = page.locator('#venue-live-tracking-summary');
  const liveRoom = room => page.locator(`[data-live-tracking-room="${room}"]`);
  const status = room => page.locator(`[data-begin-room="${room}"]`);
  const tracking = id => page.locator(`[data-venue-tracking-begin="${id}"]`);
  const canvas = page.locator('#world-canvas');
  async function openTracking(row) {
    const expected = row.trackingBegin.frame.worldSequence;
    const request = page.waitForRequest(request => new URL(request.url()).pathname === `/api/sessions/${row.sessionId}/world/watch`);
    await tracking(row.sessionId).click();
    const query = new URL((await request).url()).searchParams;
    assert.equal(query.get('mode'), 'replay');
    assert.equal(query.get('fromFrame'), String(expected));
    assert.equal(query.get('throughFrame'), String(expected));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${expected} 格的追蹤開場快照` }).waitFor();
    assert.equal(await canvas.getAttribute('data-sequence'), String(expected));
    assert.equal(await page.locator('#world-recording').inputValue(), row.sessionId);
    assert.equal(await page.locator('#world-room').inputValue(), row.roomIds.length === 1 ? String(row.roomIds[0]) : 'all');
    await page.locator('#world-status').filter({ hasText: '準備中' }).waitFor();
  }
  async function mission(mode) {
    return api('/missions', 'POST', { name: `Full tracking ${mode}`, briefing: '', durationSeconds: 180,
      environment: { mode, weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  }
  async function admit(id, room, seat) {
    return api(`/sessions/${id}/players`, 'POST', { playerId: randomUUID(), roomId: room, name: `Seat ${room}/${seat}`,
      headset: room === 1 ? 'ViveXr' : 'Quest3' });
  }
  async function publisher(session) {
    const mr = session.environment.mode === 'MR', origin = mr ? 'GameServer' : 'Simulation', streamId = randomUUID();
    const route = `/sessions/${session.id}`;
    await api(route + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    const started = Date.now();
    const header = { sessionId: session.id, streamId, origin, roomIds: session.roomIds,
      ...(mr ? { calibration: 'quest-room-mr-v1' } : {}), captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00') };
    let sequence = 0;
    function send(message) {
      const sent = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${route}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, message] }) });
      assert.equal(sent.status, 0, sent.stderr || sent.error?.message);
      return JSON.parse(sent.stdout);
    }
    return { route, streamId, port: 7776 + session.roomIds[0], snapshot: await api(route), seal() {
      assert.equal(send({ type: 'seal', finalSequence: sequence }).complete, true);
    }, publish(snapshot, allTracked, loseTracking = false) {
      const players = snapshot.players.map(({ id, roomId, seat }) => {
        const head = { x: (roomId - 3) * 14 + (seat - 2) * 1.5, y: 1.65, z: -3 };
        const connected = !(loseTracking && roomId === 5 && seat === 1);
        const rig = { kind: !connected ? 'None' : !allTracked && roomId === 1 && seat === 4 ? 'Simulated' : 'Tracked', left: head, right: head };
        return { id, roomId, head, muzzle: head, connected, forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: 30, reserve: 90, rig };
      });
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
        weather: 'Clear', lightning: false, throughCombatSequence: 0, events: [],
        frame: { phase: snapshot.state, night: false, tick: snapshot.state === 'Preparing' ? 0 : 1, throughSequence: 0, players } };
      assert.equal(send({ type: 'frame', payload: packet }).acceptedSequence, sequence);
    } };
  }
  async function publishUntil(sources, tracked, condition, loseTracking = false) {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      for (const source of sources) source.publish(source.snapshot, tracked, loseTracking);
      if (await condition()) return;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error('The console did not show the expected full tracking state');
  }
  const getFences = async () => (await api('/venue/phase')).begin.map(({ sessionId, phaseSinceSequence, sessionSequence }) =>
    ({ sessionId, phaseSinceSequence, sessionSequence }));
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function checkParticipation(vr, mr) {
    const option = page.locator('#venue-full-participation');
    for (const mode of ['Linked', 'Mixed']) {
      const sessions = mode === 'Linked' ? [await api('/sessions', 'POST',
        { missionId: vr.id, mode: 'Linked', roomIds: rooms }, 'Master', 201)]
        : (await api('/sessions/independent-set', 'POST', { rooms: rooms.map(roomId => ({ roomId,
          missionId: [2, 4].includes(roomId) ? mr.id : vr.id })) }, 'Master', 201, undefined, randomUUID())).sessions;
      for (const session of sessions) active.add(session.id);
      const forRoom = room => sessions.find(session => session.roomIds.includes(room));
      for (const room of rooms)
        for (let seat = 1; seat <= (room === 5 ? 4 : 5); seat++) await admit(forRoom(room).id, room, seat);
      const sources = [];
      for (const session of sessions) sources.push(await publisher(session));
      const targets = await getFences();
      const payload = { action: 'Begin', targets, requireFullParticipation: true };
      for (const source of sources) source.publish(source.snapshot, false);
      const missing = await api('/venue/phase', 'POST', payload, 'Master', 409, undefined, randomUUID());
      check(missing.code === 'venue-begin-not-ready' && missing.roomIds.join() === '5'
        && (await api('/sessions')).every(session => session.state === 'Preparing'),
      `${mode} full participation rejects the original 24-seat roster atomically`);
      await api('/venue/phase', 'POST', { ...payload, requireFullTracking: true }, 'Master', 400, undefined, randomUUID());
      await api('/venue/phase', 'POST', { ...payload, action: 'End' }, 'Master', 400, undefined, randomUUID());
      await login('Master');
      assert.equal(await option.isChecked(), false);
      await option.check();
      await publishUntil(sources, false, async () => (await status(5).getAttribute('data-begin-state')) === 'WaitingFullParticipation');
      check(await start.isDisabled() && (await status(5).innerText()).includes('名冊 4/5 席 · 有效姿態 4/5 席'),
        `${mode} operator sees the missing seat before sending Begin`);
      await page.locator('#venue-phase').screenshot({ path: path.join(screenshots, `full-participation-${mode.toLowerCase()}-waiting.png`) });
      const last = sources.find(source => source.route === `/sessions/${forRoom(5).id}`);
      last.snapshot = await admit(forRoom(5).id, 5, 5);
      await page.locator('#refresh').click();
      await publishUntil(sources, false, async () => (await status(5).getAttribute('data-begin-state')) === 'WaitingFullParticipation', true);
      check(await start.isDisabled() && (await status(5).innerText()).includes('名冊 5/5 席 · 有效姿態 4/5 席'),
        `${mode} full roster still cannot start when a registered seat has no effective pose`);
      const readyFences = await getFences();
      for (const source of sources) source.publish(source.snapshot, false, true);
      const disconnected = await api('/venue/phase', 'POST', { ...payload, targets: readyFences }, 'Master', 409, undefined, randomUUID());
      check(disconnected.code === 'venue-begin-not-ready' && disconnected.roomIds.join() === '5'
        && (await api('/sessions')).every(session => session.state === 'Preparing'), `${mode} server identifies only the room with a disconnected seat`);
      await publishUntil(sources, false, () => start.isEnabled());
      const receiptPromise = page.waitForResponse(response => response.url().endsWith('/api/venue/phase') && response.request().method() === 'POST');
      const confirmation = page.waitForEvent('dialog').then(async dialog => { assert.match(dialog.message(), /25 席已連線且姿態有效/); await dialog.accept(); });
      await start.click(); await confirmation;
      const response = await receiptPromise, receipt = await response.json(), body = response.request().postDataJSON();
      const requestId = (await response.request().allHeaders())['idempotency-key'];
      check(response.status() === 200 && body.requireFullParticipation === true && !body.requireFullTracking
        && receipt.requireFullParticipation === true && receipt.sessions.length === sessions.length,
      `${mode} accepts the optional 25-seat policy with both simulated and tracked sources`);
      const retry = await api('/venue/phase', 'POST', body, 'Master', 200, undefined, requestId);
      await api('/venue/phase', 'POST', { ...body, requireFullParticipation: false }, 'Master', 409, undefined, requestId);
      const proofs = new Map();
      for (const { sessionId, appliedAtSequence } of receipt.sessions) {
        const fence = readyFences.find(fence => fence.sessionId === sessionId);
        const history = await api(`/sessions/${sessionId}/events`);
        const event = history.find(entry => entry.sequence === appliedAtSequence);
        const proof = event.venue.participationFrame;
        const frame = await api(`/sessions/${sessionId}/world/frames/${proof.worldSequence}`);
        assert.equal(appliedAtSequence, fence.sessionSequence + 1);
        assert.equal(event.venue.requireFullParticipation, true);
        assert.equal(event.venue.trackingFrame, undefined);
        assert.equal(proof.streamId, sources.find(source => source.route === `/sessions/${sessionId}`).streamId);
        assert.equal(frame.packet.observedSequence, fence.sessionSequence);
        assert.equal(frame.packet.elapsedMilliseconds, proof.elapsedMilliseconds);
        assert.equal(frame.packet.frame.phase, 'Preparing');
        assert.ok(frame.packet.frame.players.every(player => player.connected && ['Simulated', 'Tracked'].includes(player.rig.kind)));
        proofs.set(sessionId, { requestId, appliedAtSequence, frame: proof });
      }
      check(retry.duplicate && retry.requireFullParticipation && JSON.stringify(retry.sessions) === JSON.stringify(receipt.sessions),
        `${mode} retry preserves the original policy and the exact accepted Preparing frames`);
      const endTargets = (await api('/venue/phase')).end.map(({ sessionId, phaseSinceSequence }) => ({ sessionId, phaseSinceSequence }));
      const ended = await api('/venue/phase', 'POST', { action: 'End', targets: endTargets }, 'Master', 200, undefined, randomUUID());
      for (const { id } of sessions) active.delete(id);
      const { batch } = await api(`/venue/closure/${ended.requestId}`);
      assert.equal(batch.sessions.length, proofs.size);
      for (const row of batch.sessions) {
        assert.deepEqual(row.participationBegin, proofs.get(row.sessionId));
        assert.equal(row.trackingBegin, undefined);
      }
      check(true, `${mode} closure carries the same participation proof without a tracking-only claim`);
    }
  }
  try {
    const vr = await mission('VR'), mr = await mission('MR');
    await checkParticipation(vr, mr);
    if (participationOnly) return;
    let originalLinked;
    for (const mode of ['Linked', 'Mixed']) {
      const sessions = mode === 'Linked' ? [await api('/sessions', 'POST',
        { missionId: vr.id, mode: 'Linked', roomIds: rooms }, 'Master', 201)]
        : (await api('/sessions/independent-set', 'POST', { rooms: rooms.map(roomId => ({ roomId,
          missionId: [2, 4].includes(roomId) ? mr.id : vr.id })) }, 'Master', 201, undefined, randomUUID())).sessions;
      for (const session of sessions) active.add(session.id);
      const forRoom = room => sessions.find(session => session.roomIds.includes(room));
      for (const room of rooms)
        for (let seat = 1; seat <= (room === 5 ? 4 : 5); seat++) await admit(forRoom(room).id, room, seat);
      const sources = [];
      for (const session of sessions) sources.push(await publisher(session));
      await login('Master');
      check(!await option.isChecked(), `${mode} defaults to normal Begin`);
      await option.check();
      await publishUntil(sources, false, async () => (await status(1).getAttribute('data-begin-state')) === 'WaitingFullTracking'
        && (await status(5).getAttribute('data-begin-state')) === 'WaitingFullTracking');
      check((await status(1).innerText()).includes('名冊 5/5 席 · 追蹤 4/5 席')
        && (await status(5).innerText()).includes('名冊 4/5 席 · 追蹤 4/5 席') && await start.isDisabled()
        && (await page.locator('#venue-begin-evidence').innerText()).includes('仍有開場條件待確認'),
      `${mode} shows the simulated seat and the missing seat before opening`);
      await page.locator('#venue-phase').screenshot({ path: path.join(screenshots, `full-tracking-${mode.toLowerCase()}-waiting.png`) });
      const targets = await getFences();
      for (const source of sources) source.publish(source.snapshot, false);
      const rejected = await api('/venue/phase', 'POST', { action: 'Begin', targets, requireFullTracking: true }, 'Master', 409, undefined, randomUUID());
      check(rejected.code === 'venue-begin-not-ready' && rejected.roomIds.join() === '1,5'
        && (await api('/sessions')).every(session => session.state === 'Preparing'), `${mode} rejects the entire current Begin with exactly rooms 1 and 5`);
      const last = sources.find(source => source.route === `/sessions/${forRoom(5).id}`);
      last.snapshot = await admit(forRoom(5).id, 5, 5);
      await page.locator('#refresh').click();
      await publishUntil(sources, true, () => start.isEnabled());
      check(await page.locator('[data-begin-state="Ready"]').count() === 5
        && (await page.locator('#venue-begin-evidence').innerText()).includes('目標場次已就緒'),
      `${mode} shows all five rooms ready after receiving all 25 tracked poses`);
      const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/venue/phase') && response.request().method() === 'POST');
      const confirmation = page.waitForEvent('dialog').then(async dialog => { assert.match(dialog.message(), /25 席追蹤就緒/); await dialog.accept(); });
      await start.click();
      await confirmation;
      const response = await responsePromise;
      const body = response.request().postDataJSON(), requestId = (await response.request().allHeaders())['idempotency-key'];
      const receipt = await response.json();
      check(response.status() === 200 && body.requireFullTracking === true && receipt.requireFullTracking === true
        && receipt.sessions.length === sessions.length && (await api('/sessions')).every(session => session.state === 'Running'),
      `${mode} accepts one guarded Begin for the original sessions`);
      const retry = await api('/venue/phase', 'POST', body, 'Master', 200, undefined, requestId);
      await api('/venue/phase', 'POST', { ...body, requireFullTracking: false }, 'Master', 409, undefined, requestId);
      await api('/venue/phase', 'POST', { ...body, action: 'End' }, 'Master', 400, undefined, randomUUID());
      check(retry.duplicate && retry.requireFullTracking && JSON.stringify(retry.sessions) === JSON.stringify(receipt.sessions),
        `${mode} retry keeps the original policy and rejects changing it`);
      for (const source of sources) source.snapshot = await api(source.route);
      const waitSummary = text => () => liveSummary.filter({ hasText: text }).isVisible();
      check(await liveTracking.count() === 1, `${mode} provides a live tracking overview after Begin`);
      await publishUntil(sources, true, waitSummary('追蹤 25 / 25 席'));
      const overview = (await api('/rooms/readiness')).rooms;
      const scoped = (await api('/rooms/readiness', 'GET', undefined, 'Room2')).rooms;
      check(overview.every(room => room.venueTracking.trackedSeats.join() === '1,2,3,4,5')
        && scoped.length === 1 && !Object.hasOwn(scoped[0], 'venueTracking'), `${mode} verifies five original seats per room and keeps the venue breakdown Master-only`);
      await publishUntil(sources, false, waitSummary('追蹤 23 / 25 席'), true);
      check((await liveRoom(1).innerText()).includes('合成席位 5') && (await liveRoom(5).innerText()).includes('待確認席位 2'),
        `${mode} separates one simulated seat and a different seat that lost tracking`);
      await liveTracking.screenshot({ path: path.join(screenshots, `live-tracking-${mode.toLowerCase()}-loss.png`) });
      const first = sources.find(source => source.route === `/sessions/${forRoom(1).id}`);
      const changed = await api(first.route + '/commands', 'POST', { commandId: randomUUID(), action: 'SetEnvironment',
        environment: first.snapshot.environment });
      first.publish(first.snapshot, true);
      const readback = await api(first.route + '/readiness');
      check(readback.observedSequence < changed.appliedAtSequence
        && (await api('/rooms/readiness')).rooms.find(room => room.roomId === 1).venueTracking.trackedSeats.length === 5,
        `${mode} preserves current tracking through an unrelated environment revision`);
      await api(first.route + '/commands', 'POST', { commandId: randomUUID(), action: 'Pause' });
      const resumed = await api(first.route + '/commands', 'POST', { commandId: randomUUID(), action: 'Resume' });
      await page.locator('#refresh').click();
      await publishUntil(sources, true, async () => (await liveRoom(1).getAttribute('data-live-tracking-state')) === 'WaitingRevision');
      check(!(await waitSummary('追蹤 25 / 25 席')()), `${mode} withholds the old tracking count until the game observes the new Resume`);
      first.snapshot = resumed.session;
      await publishUntil(sources, true, waitSummary('追蹤 25 / 25 席'));
      await liveRoom(1).filter({ hasText: '快照已過期' }).waitFor();
      check(!(await waitSummary('追蹤 25 / 25 席')()), `${mode} withdraws confirmed counts when the original snapshots expire`);
      await publishUntil(sources, true, waitSummary('追蹤 25 / 25 席'));
      const endTargets = (await api('/venue/phase')).end.map(({ sessionId, phaseSinceSequence }) => ({ sessionId, phaseSinceSequence }));
      const ended = await api('/venue/phase', 'POST', { action: 'End', targets: endTargets }, 'Master', 200, undefined, randomUUID());
      const closurePath = `/venue/closure/${ended.requestId}`;
      if (mode === 'Linked') {
        const partial = (await api(closurePath)).batch.sessions[0];
        assert.equal(partial.world, 'Waiting');
        await page.locator('#refresh').click();
        await openTracking(partial);
        check((await page.locator('#world-status').innerText()).includes('錄製未封存') && await page.locator('#world-frame-next').isEnabled(),
          'An accepted guarded frame can open in a partial recording with its already saved next frame');
        await page.locator('#tab-operations').click();
      }
      for (const source of sources) {
        source.publish(await api(source.route), true);
        await api(source.route + '/combat-stream/seal', 'POST', { streamId: source.streamId, finalSequence: 0 }, 'GameServer');
        source.seal();
        await api(source.route + '/connection-endpoint', 'PUT',
          { version: 1, streamId: source.streamId, address: '192.168.50.40', port: source.port }, 'GameServer');
      }
      for (const session of sessions) active.delete(session.id);
      const closure = await api(closurePath);
      for (const row of closure.batch.sessions) {
        const { requestId: original, appliedAtSequence, frame } = row.trackingBegin;
        const originalSequence = receipt.sessions.find(session => session.sessionId === row.sessionId).appliedAtSequence;
        const accepted = (await api(`/sessions/${row.sessionId}/world/frames/${frame.worldSequence}`)).packet;
        assert.equal(original, requestId);
        assert.equal(appliedAtSequence, originalSequence);
        assert.equal(frame.streamId, row.replay.streamId);
        assert.equal(accepted.observedSequence, appliedAtSequence - 1);
        assert.equal(accepted.elapsedMilliseconds, frame.elapsedMilliseconds);
        assert.equal(accepted.frame.phase, 'Preparing');
        assert.equal(accepted.frame.players.length, row.roomIds.length * 5);
        assert.ok(accepted.frame.players.every(player => player.rig.kind === 'Tracked' && player.connected));
      }
      check(closure.batch.sessions.length === sources.length && closure.batch.sessions.every(row => row.fieldEvidenceReady),
        `${mode} sealed closure points to the exact accepted Preparing frames and guarded Begin`);
      const zipUrl = base + '/api' + closurePath + '/field-evidence.zip';
      const zip = await fetch(zipUrl, { headers: { Authorization: 'Bearer ' + tokens.Master } });
      assert.equal(zip.status, 200);
      const bytes = Buffer.from(await zip.arrayBuffer());
      const decoded = spawnSync('python', ['-c', `import io, sys, zipfile
with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as archive:
    print(archive.read('closure.json').decode('utf-8'))`], { input: bytes, encoding: 'utf8', timeout: 6000, windowsHide: true });
      assert.equal(decoded.status, 0, decoded.stderr);
      assert.deepEqual(JSON.parse(decoded.stdout), closure);
      await fs.writeFile(path.join(screenshots, `tracking-begin-${mode.toLowerCase()}-venue.zip`), bytes);
      check((await fetch(zipUrl, { headers: { Authorization: 'Bearer ' + tokens.Room2 } })).status === 403,
        `${mode} includes the original frame witnesses in the Master-only venue ZIP`);

      const row = closure.batch.sessions.find(row => row.roomIds.includes(mode === 'Linked' ? 1 : 2));
      await page.locator('#refresh').click();
      if (mode === 'Linked') {
        originalLinked = { row, batch: ended.requestId };
        const list = '**/api/world-recordings';
        await page.route(list, async route => {
          const response = await route.fetch(), rows = await response.json();
          rows.find(item => item.header.sessionId === row.sessionId).header.streamId = randomUUID();
          await route.fulfill({ response, json: rows });
        }, { times: 1 });
        await tracking(row.sessionId).click();
        await page.locator('#world-message').filter({ hasText: '目前無法讀取原場次的錄製' }).waitFor();
        check(await page.locator('#world-player').isHidden() && await page.locator('#world-recording').inputValue() === '',
          'The tracking shortcut refuses a substituted archive source without selecting another recording');
      } else {
        const watch = `**/api/sessions/${row.sessionId}/world/watch?**`;
        await page.route(watch, async route => {
          const response = await route.fetch();
          const body = (await response.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
            const value = JSON.parse(raw);
            value.packet.frame.players[0].rig.kind = 'Simulated';
            return 'event: frame\ndata: ' + JSON.stringify(value);
          });
          await route.fulfill({ response, body });
        }, { times: 1 });
        await tracking(row.sessionId).click();
        await page.locator('#world-message').filter({ hasText: '回應快照的追蹤開場或指令序號不同' }).waitFor();
        check(await page.locator('#world-player').isHidden() && await canvas.getAttribute('data-sequence') === null,
          'The tracking shortcut refuses a frame with substituted pose provenance');
      }
      await page.locator('#tab-operations').click();
      await openTracking(row);
      assert.match(await page.locator('#world-message').innerText(), mode === 'Linked' ? /VR 未校正/ : /Quest 3 MR 錄製設定/);
      assert.match(await page.locator('#world-actor-info').innerText(), /頭手來源 Tracked/);
      if (mode === 'Mixed') assert.ok(Number((await canvas.getAttribute('data-camera')).split(',')[1]) < 30,
        'The original room preset fits the visible replay canvas');
      await page.locator('#world-player').screenshot({ path: path.join(screenshots, `tracking-begin-${mode.toLowerCase()}-replay.png`) });
      const next = page.locator('#world-frame-next');
      assert.ok(await next.isEnabled());
      await next.click();
      await page.locator(`#world-canvas[data-sequence="${row.trackingBegin.frame.worldSequence + 1}"]`).waitFor();
      check((await page.locator('#world-status').innerText()).includes('錄製已核對封存')
        && (mode === 'Linked' || await page.locator('#world-camera').inputValue() === 'top'),
        `${mode} opens the verified frame with the original room scope and retains adjacent-frame review`);
      await page.locator('#tab-operations').click();
    }
    const replacement = await api('/sessions', 'POST', { missionId: vr.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
    active.add(replacement.id);
    await page.locator('#venue-closure-load').click();
    await page.locator(`#venue-closure-batch option[value="${originalLinked.batch}"]`).waitFor({ state: 'attached' });
    await page.locator('#venue-closure-batch').selectOption(originalLinked.batch);
    await openTracking(originalLinked.row);
    check((await api(`/sessions/${replacement.id}`)).state === 'Preparing', 'Selecting the older tracking closure keeps its original replay after room reuse');
    await login('Room2');
    check(await option.isHidden() && await page.locator('[data-venue-tracking-begin]').count() === 0,
      'The room console cannot activate the master tracking policy or see its closure shortcut');
  } finally {
    await page.close();
    for (const id of active) await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
  }
};
