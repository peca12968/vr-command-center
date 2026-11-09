const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const rooms = [1, 2, 3, 4, 5];
  const page = await context.newPage();
  captureErrors(page);
  const active = new Set();
  const option = page.locator('#venue-full-tracking');
  const start = page.locator('#venue-begin');
  const status = room => page.locator(`[data-begin-room="${room}"]`);
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
    return { route, snapshot: await api(route), publish(snapshot, allTracked) {
      const players = snapshot.players.map(({ id, roomId, seat }) => {
        const head = { x: (roomId - 3) * 14 + (seat - 2) * 1.5, y: 1.65, z: -3 };
        const rig = { kind: !allTracked && roomId === 1 && seat === 4 ? 'Simulated' : 'Tracked', left: head, right: head };
        return { id, roomId, head, muzzle: head, connected: true, forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: 30, reserve: 90, rig };
      });
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
        weather: 'Clear', lightning: false, throughCombatSequence: 0, events: [],
        frame: { phase: snapshot.state, night: false, tick: 0, throughSequence: 0, players } };
      const sent = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${route}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, { type: 'frame', payload: packet }] }) });
      assert.equal(sent.status, 0, sent.stderr || sent.error?.message);
      assert.equal(JSON.parse(sent.stdout).acceptedSequence, sequence);
    } };
  }
  async function publishUntil(sources, tracked, condition) {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      for (const source of sources) source.publish(source.snapshot, tracked);
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
  try {
    const vr = await mission('VR'), mr = await mission('MR');
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
      for (const id of active) {
        await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
        active.delete(id);
      }
    }
    await login('Room2');
    check(await option.isHidden(), 'The room console cannot activate the master tracking policy');
  } finally {
    await page.close();
    for (const id of active) await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
  }
};
