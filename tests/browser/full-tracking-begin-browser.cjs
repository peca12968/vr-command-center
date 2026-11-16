const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { waitForLiveFrame } = require('./live-watch-fault.cjs');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors, participationOnly }) => {
  const rooms = [1, 2, 3, 4, 5];
  const page = await context.newPage();
  captureErrors(page);
  const active = new Set();
  const option = page.locator('#venue-full-tracking');
  const start = page.locator('#venue-begin');
  const liveTracking = page.locator('#venue-live-tracking');
  const liveSummary = page.locator('#venue-live-tracking-summary');
  const liveSample = page.locator('#venue-live-tracking-sample');
  const liveRoom = room => page.locator(`[data-live-tracking-room="${room}"]`);
  const status = room => page.locator(`[data-begin-room="${room}"]`);
  const seatState = (room, seat) => page.locator(`[data-begin-seat-room="${room}"] [data-begin-seat="${seat}"]`).getAttribute('data-seat-state');
  const tracking = id => page.locator(`[data-venue-tracking-begin="${id}"]`);
  const participation = id => page.locator(`[data-venue-participation-begin="${id}"]`);
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
  async function compareBegin(row, policy, tamper = false) {
    const anchor = row[policy].frame.worldSequence, first = anchor + 2;
    const route = `/sessions/${row.sessionId}/world/venue-begin-running`;
    const running = page.locator('#world-begin-running'), original = page.locator('#world-begin-original');
    const note = page.locator('#world-frame-message');
    const room = await page.locator('#world-room').inputValue(), camera = await page.locator('#world-camera').inputValue();
    const bounded = await api(`${route}?throughFrame=${anchor + 1}`);
    assert.equal(bounded.frame, null);
    await api(`${route}?throughFrame=${first}`, 'GET', undefined, 'Room2', 403);
    if (tamper) {
      await page.route(url => url.pathname === '/api' + route, async intercepted => {
        const response = await intercepted.fetch(), value = await response.json();
        value.beginRequestId = randomUUID();
        await intercepted.fulfill({ response, json: value });
      }, { times: 1 });
      await running.click();
      await note.filter({ hasText: '已保留目前畫面' }).waitFor();
      check(await canvas.getAttribute('data-sequence') === String(anchor), 'A mismatched Begin request retains the original frame');
    }
    await running.click();
    await note.filter({ hasText: `首個執行畫格（第 ${first} 格）` }).waitFor();
    check(await canvas.getAttribute('data-sequence') === String(first)
      && (await page.locator('#world-status').innerText()).includes('執行中')
      && await page.locator('#world-room').inputValue() === room && await page.locator('#world-camera').inputValue() === camera,
    `${policy} skips the later Preparing frame and keeps the original room and camera`);
    await original.click();
    await note.filter({ hasText: `已停在第 ${anchor} 格` }).waitFor();
    check(await canvas.getAttribute('data-sequence') === String(anchor) && await original.isDisabled(),
      `${policy} returns to the independently verified original Preparing frame`);
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
  async function publisher(session, trackedVr = false) {
    const mr = session.environment.mode === 'MR', origin = mr || trackedVr ? 'GameServer' : 'Simulation', streamId = randomUUID();
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
      return packet;
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
      assert.deepEqual(missing.blockedRooms?.map(({ roomId, seats }) => ({ roomId, seats })),
        [{ roomId: 5, seats: [{ seat: 5, state: 'Vacant' }] }]);
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
      check(await seatState(5, 5) === 'Vacant' && await seatState(1, 5) === 'Simulated',
        `${mode} seat matrix distinguishes an empty seat from an eligible simulated pose`);
      await status(5).getByRole('button', { name: '查看房間 5 名冊' }).click();
      await page.locator('#roster-title:focus').waitFor();
      check(await page.locator('#session-select').inputValue() === forRoom(5).id
        && await page.locator('#roster-room').inputValue() === '5'
        && await page.locator('#roster tr:visible').count() === 4
        && await page.locator('#roster tr[data-roster-room="5"]:visible').count() === 4,
        `${mode} opening shortcut selects the original room and shows only its four registered seats`);
      check(await option.isChecked() && (await api('/sessions')).every(session => session.state === 'Preparing'),
        `${mode} visiting a roster leaves the active Begin policy and original phases intact`);
      check((await page.locator('#readiness-summary').textContent()).startsWith('房間 5 · ')
        && (await page.locator('#player-count').textContent()) === '房間 5 · 4 / 5 人（名冊）',
        `${mode} roster and readiness summaries both use the selected room`);
      if (mode === 'Linked') {
        await page.locator('#roster-room').selectOption('');
        check(await page.locator('#roster tr:visible').count() === 24
          && (await page.locator('#player-count').textContent()) === '24 / 25 人（名冊）'
          && !(await page.locator('#readiness-summary').textContent()).startsWith('房間 5 · '),
          'Linked roster can return to all rooms without changing the selected session');
        await login('Room1');
        await page.locator('#session-panel').waitFor();
        check(await status(5).getByRole('button').count() === 0 && await page.locator('#roster-room-filter').isHidden()
          && await page.locator('#roster-room option[value="5"]').count() === 0,
          'Room controller has no foreign opening shortcut or room filter option');
        await login('Master');
        await option.check();
        await status(5).getByRole('button', { name: '查看房間 5 名冊' }).click();
        await page.locator('#roster-title:focus').waitFor();
      }
      await page.locator('#venue-phase').screenshot({ path: path.join(screenshots, `full-participation-${mode.toLowerCase()}-waiting.png`) });
      const last = sources.find(source => source.route === `/sessions/${forRoom(5).id}`);
      const newRoster = await admit(forRoom(5).id, 5, 5);
      await page.locator('#refresh').click();
      await publishUntil(sources, false, async () => (await status(5).getAttribute('data-begin-state')) === 'WaitingRevision');
      check(await page.locator('#roster-room').inputValue() === '5' && await page.locator('#roster tr:visible').count() === 5,
        `${mode} roster refresh keeps the original room filter and shows its new admission`);
      check(await seatState(5, 5) === 'AwaitingAdmission' && await seatState(5, 4) === 'WaitingRevision' && await start.isDisabled(),
        `${mode} the previous revision cannot mark the new admission or any seat in that room ready`);
      last.snapshot = newRoster;
      await publishUntil(sources, false, async () => (await status(5).getAttribute('data-begin-state')) === 'WaitingFullParticipation', true);
      check(await start.isDisabled() && (await status(5).innerText()).includes('名冊 5/5 席 · 有效姿態 4/5 席'),
        `${mode} full roster still cannot start when a registered seat has no effective pose`);
      check(await seatState(5, 2) === 'PoseUnavailable' && await seatState(5, 5) === 'Tracked',
        `${mode} the live matrix identifies the affected seat and the newly confirmed admission`);
      const readyFences = await getFences();
      for (const source of sources) source.publish(source.snapshot, false, true);
      const disconnected = await api('/venue/phase', 'POST', { ...payload, targets: readyFences }, 'Master', 409, undefined, randomUUID());
      check(disconnected.code === 'venue-begin-not-ready' && disconnected.roomIds.join() === '5'
        && (await api('/sessions')).every(session => session.state === 'Preparing'), `${mode} server identifies only the room with a disconnected seat`);
      await publishUntil(sources, false, () => start.isEnabled());
      let lostSequence;
      const phaseUrl = '**/api/venue/phase';
      const interrupt = async intercepted => {
        if (intercepted.request().method() === 'POST') {
          for (const source of sources) {
            const frame = source.publish(source.snapshot, false, true);
            if (source === last) lostSequence = frame.sequence;
          }
        }
        await intercepted.continue();
      };
      await page.route(phaseUrl, interrupt);
      try {
        const refused = page.waitForResponse(response => response.url().endsWith('/api/venue/phase') && response.request().method() === 'POST');
        page.once('dialog', dialog => dialog.accept());
        await start.click();
        const reply = await refused;
        const body = await reply.json();
        assert.deepEqual(body.blockedRooms, [{ roomId: 5, worldSequence: lostSequence, seats: [{ seat: 2, state: 'PoseUnavailable' }] }]);
        const notice = page.locator('#notice').filter({ hasText: '拒絕時房間 5 第 2 席姿態未就緒。' });
        await notice.waitFor();
        await notice.screenshot({ path: path.join(screenshots, `full-participation-${mode.toLowerCase()}-refused-seat.png`) });
        check(reply.status() === 409 && JSON.stringify(await getFences()) === JSON.stringify(readyFences),
          `${mode} keeps the original fences and tells the operator which seat failed when sending Begin`);
      } finally {
        await page.unroute(phaseUrl, interrupt);
      }
      await page.locator('#refresh').click();
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
      for (const source of sources) {
        source.publish(source.snapshot, false);
        source.snapshot = await api(source.route);
        source.publish(source.snapshot, false);
      }
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
      const selected = mode === 'Linked' ? batch.sessions[0] : batch.sessions.find(row => row.roomIds[0] === 2);
      const originalFrame = selected.participationBegin.frame.worldSequence;
      await page.locator('#refresh').click();
      await participation(selected.sessionId).waitFor({ timeout: 5000 });
      const watch = `**/api/sessions/${selected.sessionId}/world/watch?**`;
      await page.route(watch, async route => {
        const response = await route.fetch();
        const body = (await response.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
          const value = JSON.parse(raw);
          if (mode === 'Linked') value.packet.frame.players[0].connected = false;
          else value.packet.frame.players[0].rig.kind = 'Simulated';
          return `event: frame\ndata: ${JSON.stringify(value)}`;
        });
        await route.fulfill({ response, body });
      }, { times: 1 });
      await participation(selected.sessionId).click();
      await page.locator('#world-message').filter({ hasText: '回應快照的有效姿態開場或指令序號不同' }).waitFor();
      check(await page.locator('#world-player').isHidden() && await canvas.getAttribute('data-sequence') === null,
        `${mode} rejects the bounded opening frame with an ineligible substituted pose`);
      await page.locator('#tab-operations').click();
      const requested = page.waitForRequest(request => new URL(request.url()).pathname === `/api/sessions/${selected.sessionId}/world/watch`);
      await participation(selected.sessionId).click();
      const query = new URL((await requested).url()).searchParams;
      assert.equal(query.get('mode'), 'replay');
      assert.equal(query.get('fromFrame'), String(originalFrame));
      assert.equal(query.get('throughFrame'), String(originalFrame));
      const poseCounts = mode === 'Linked' ? '追蹤 24 席、合成 1 席' : '追蹤 5 席、合成 0 席';
      await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${originalFrame} 格的有效姿態開場快照。 此格${poseCounts}` }).waitFor();
      check(await canvas.getAttribute('data-sequence') === String(originalFrame)
        && await page.locator('#world-room').inputValue() === (mode === 'Linked' ? 'all' : '2')
        && await page.locator('#world-camera').inputValue() === (mode === 'Linked' ? 'overview' : 'top'),
      `${mode} reopens the exact original participation frame and room scope`);
      await compareBegin(selected, 'participationBegin', mode === 'Linked');
      await page.locator('#world-player').screenshot({ path: path.join(screenshots, `participation-begin-${mode.toLowerCase()}-replay.png`) });
      await page.locator('#world-frame-next').click();
      await page.locator(`#world-canvas[data-sequence="${originalFrame + 1}"]`).waitFor();
      check(!(await page.locator('#world-frame-message').innerText()).includes('有效姿態開場'),
        `${mode} can step beyond the witnessed frame into the original saved recording`);
      await page.locator('#tab-operations').click();
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
      for (const session of sessions) sources.push(await publisher(session, mode === 'Linked'));
      await login('Master');
      check(!await option.isChecked(), `${mode} defaults to normal Begin`);
      await option.check();
      const origins = rooms.map(room => mode === 'Linked' || [2, 4].includes(room) ? 'GameServer' : 'Simulation');
      await publishUntil(sources, false, async () => (await status(1).getAttribute('data-begin-state')) === 'WaitingFullTracking'
        && (await status(5).getAttribute('data-begin-state')) === 'WaitingFullTracking'
        && (await Promise.all(rooms.map((room, index) => status(room).filter({ hasText: `錄製來源 ${origins[index]}` }).isVisible()))).every(Boolean));
      check((await status(1).innerText()).includes('名冊 5/5 席 · 追蹤 4/5 席')
        && (await status(5).innerText()).includes('名冊 4/5 席 · 追蹤 4/5 席') && await start.isDisabled()
        && (await page.locator('#venue-begin-evidence').innerText()).includes('仍有開場條件待確認'),
      `${mode} shows the simulated seat and the missing seat before opening`);
      check(await seatState(1, 5) === 'NeedsTracking' && await seatState(5, 5) === 'Vacant'
        && await page.locator('[data-begin-seat-room] td[data-begin-seat]').count() === 25,
      `${mode} the tracked-only policy identifies exactly which simulated and vacant seats need attention`);
      await page.locator('#venue-phase').screenshot({ path: path.join(screenshots, `full-tracking-${mode.toLowerCase()}-waiting.png`) });
      if (mode === 'Linked') {
        await status(1).filter({ hasText: '快照已過期' }).waitFor();
        check(!(await status(1).innerText()).includes('錄製來源') && await start.isDisabled(),
          'The preparing source label expires with the original readiness sample');
        const stale = await api('/venue/phase', 'POST', { action: 'Begin', targets: await getFences(), requireFullTracking: true },
          'Master', 409, undefined, randomUUID());
        check(stale.roomIds.join() === '1,2,3,4,5' && stale.blockedRooms === undefined,
          'A stale Linked snapshot never diagnoses individual seats in the rejection');
      }
      const targets = await getFences();
      for (const source of sources) source.publish(source.snapshot, false);
      const rejected = await api('/venue/phase', 'POST', { action: 'Begin', targets, requireFullTracking: true }, 'Master', 409, undefined, randomUUID());
      assert.deepEqual(rejected.blockedRooms?.map(({ roomId, seats }) => ({ roomId, seats })),
        [{ roomId: 1, seats: [{ seat: 5, state: 'NeedsTracking' }] }, { roomId: 5, seats: [{ seat: 5, state: 'Vacant' }] }]);
      check(rejected.code === 'venue-begin-not-ready' && rejected.roomIds.join() === '1,5'
        && (await api('/sessions')).every(session => session.state === 'Preparing'), `${mode} rejects the entire current Begin with exactly rooms 1 and 5`);
      const last = sources.find(source => source.route === `/sessions/${forRoom(5).id}`);
      last.snapshot = await admit(forRoom(5).id, 5, 5);
      await page.locator('#refresh').click();
      await publishUntil(sources, true, () => start.isEnabled());
      check(await page.locator('[data-begin-state="Ready"]').count() === 5
        && (await page.locator('#venue-begin-evidence').innerText()).includes('目標場次已就緒')
        && await page.locator('[data-begin-seat][data-seat-state="Tracked"]').count() === 25,
      `${mode} shows all five rooms ready after receiving all 25 tracked poses`);
      const fullTargets = await getFences();
      for (const source of sources) source.publish(source.snapshot, true, true);
      const lostPose = await api('/venue/phase', 'POST', { action: 'Begin', targets: fullTargets, requireFullTracking: true },
        'Master', 409, undefined, randomUUID());
      assert.deepEqual(await getFences(), fullTargets);
      check(lostPose.code === 'venue-begin-not-ready' && lostPose.roomIds.join() === '5',
        `${mode} rejects the whole Begin and reports only the room that lost a registered player's pose`);
      await publishUntil(sources, true, () => start.isEnabled());
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
      for (const source of sources) {
        source.publish(source.snapshot, true);
        source.snapshot = await api(source.route);
      }
      const waitSummary = text => () => liveSummary.filter({ hasText: text }).isVisible();
      check(await liveTracking.count() === 1, `${mode} provides a live tracking overview after Begin`);
      await publishUntil(sources, true, waitSummary('追蹤 25 / 25 席'));
      const overview = await api('/rooms/readiness');
      const scoped = await api('/rooms/readiness', 'GET', undefined, 'Room2');
      check(overview.rooms.every(room => room.venueTracking.trackedSeats.join() === '1,2,3,4,5' && room.trackingWorldSequence > 0)
        && Number.isFinite(Date.parse(overview.trackingSampledAtUtc)) && scoped.rooms.length === 1
        && !Object.hasOwn(scoped, 'trackingSampledAtUtc') && !Object.hasOwn(scoped.rooms[0], 'venueTracking')
        && !Object.hasOwn(scoped.rooms[0], 'trackingWorldSequence'), `${mode} verifies original frames at a shared time and keeps the venue breakdown Master-only`);
      check(await liveSample.isVisible() && Number.isFinite(Date.parse(await liveSample.locator('time').getAttribute('datetime')))
        && (await liveRoom(1).innerText()).includes('原畫格 #'), `${mode} live tracking exposes the shared clock and room frame number`);
      await publishUntil(sources, false, waitSummary('追蹤 23 / 25 席'), true);
      check((await liveRoom(1).innerText()).includes('合成席位 5') && (await liveRoom(5).innerText()).includes('待確認席位 2'),
        `${mode} separates one simulated seat and a different seat that lost tracking`);
      await liveTracking.screenshot({ path: path.join(screenshots, `live-tracking-${mode.toLowerCase()}-loss.png`) });
      const interruption = liveRoom(5).getByRole('button', { name: '房間 5 檢視姿態中斷快照' });
      await publishUntil(sources, false, () => interruption.isVisible(), true);
      const lostSession = forRoom(5).id;
      const beforeReview = await api('/sessions');
      const read = page.waitForRequest(request => new URL(request.url()).pathname === `/api/sessions/${lostSession}/world/watch`);
      const originalFrame = await liveRoom(5).getAttribute('data-world-sequence');
      await interruption.click();
      const query = new URL((await read).url()).searchParams;
      await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${originalFrame} 格的姿態中斷快照` }).waitFor();
      check(query.get('mode') === 'replay' && query.get('throughFrame') === originalFrame
        && await canvas.getAttribute('data-sequence') === originalFrame && await page.locator('#world-room').inputValue() === '5'
        && JSON.stringify(await api('/sessions')) === JSON.stringify(beforeReview), `${mode} tracking opens the exact original interruption frame without changing the session`);
      for (const source of sources) source.publish(source.snapshot, false);
      await page.locator('#world-recent').filter({ hasText: '返回即時觀戰' }).click();
      await waitForLiveFrame(page, Number(originalFrame));
      check(await page.locator('#world-recording').inputValue() === lostSession && await page.locator('#world-room').inputValue() === '5',
        `${mode} returns from the exact interruption frame to the original live room`);
      await page.locator('#tab-operations').click();
      const first = sources.find(source => source.route === `/sessions/${forRoom(1).id}`);
      const changed = await api(first.route + '/commands', 'POST', { commandId: randomUUID(), action: 'SetEnvironment',
        environment: first.snapshot.environment });
      await publishUntil(sources, true, async () => {
        const readback = await api(first.route + '/readiness');
        const room = (await api('/rooms/readiness')).rooms.find(room => room.roomId === 1);
        return readback.sourceState === 'Fresh' && readback.sessionSequence === changed.appliedAtSequence
          && readback.observedSequence === first.snapshot.sequence && readback.observedSequence < changed.appliedAtSequence
          && room?.sessionSequence === changed.appliedAtSequence && room.venueTracking?.trackedSeats.join() === '1,2,3,4,5';
      });
      check(true, `${mode} preserves current tracking through an unrelated environment revision`);
      await api(first.route + '/commands', 'POST', { commandId: randomUUID(), action: 'Pause' });
      const resumed = await api(first.route + '/commands', 'POST', { commandId: randomUUID(), action: 'Resume' });
      await page.locator('#refresh').click();
      await publishUntil(sources, true, async () => (await liveRoom(1).getAttribute('data-live-tracking-state')) === 'WaitingRevision');
      check(!(await waitSummary('追蹤 25 / 25 席')()), `${mode} withholds the old tracking count until the game observes the new Resume`);
      first.snapshot = resumed.session;
      await publishUntil(sources, true, waitSummary('追蹤 25 / 25 席'));
      await liveRoom(1).filter({ hasText: '快照已過期' }).waitFor();
      await liveSample.waitFor({ state: 'hidden' });
      check(!(await waitSummary('追蹤 25 / 25 席')()) && await interruption.isHidden(),
        `${mode} withdraws counts, common time and review actions when the original snapshots expire`);
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
        const list = url => url.pathname === '/api/world-recordings/page';
        await page.route(list, async route => {
          const response = await route.fetch(), catalog = await response.json();
          [...catalog.recordings, ...catalog.pinned].find(item => item.header.sessionId === row.sessionId).header.streamId = randomUUID();
          await route.fulfill({ response, json: catalog });
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
      await compareBegin(row, 'trackingBegin');
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
