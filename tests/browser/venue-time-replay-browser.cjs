const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function venueTimeReplayBrowser({ context, api, tokens, base, root, screenshots, check, captureErrors }) {
  const page = await context.newPage(), active = new Set();
  captureErrors(page);
  const picker = page.locator('#world-recording'), note = page.locator('#world-venue-message');
  const align = room => page.locator(`[data-venue-align-room="${room}"]`);
  const canvasAt = sequence => page.locator(`#world-canvas[data-sequence="${sequence}"]`).waitFor();
  const control = (id, action) => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action });
  const batchEnd = async () => {
    const { end: targets } = await api('/venue/phase');
    const batch = await api('/venue/phase', 'POST', { action: 'End', targets }, 'Master', 200, undefined, randomUUID());
    for (const target of targets) active.delete(target.sessionId);
    return batch.requestId;
  };
  const origin = 'Simulation', clock = Date.now() - 8000;
  function utc(offset) { return new Date(clock + offset).toISOString().replace('Z', '0000+00:00'); }
  async function source(session, start, times) {
    const { id, roomIds: [roomId] } = session;
    const streamId = randomUUID(), route = `/sessions/${id}`;
    await api(route + '/players', 'POST', { playerId: randomUUID(), name: `Replay room ${roomId}`, roomId, headset: 'Quest3' });
    await api(route + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    const header = { sessionId: id, streamId, origin, roomIds: [roomId], captureStartedAtUtc: utc(start) };
    function send(messages) {
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${route}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, ...messages] }) });
      assert.equal(result.status, 0, result.stderr || result.error?.message);
      return JSON.parse(result.stdout);
    }
    function frame(snapshot, elapsedMilliseconds, sequence) {
      const head = { x: (roomId - 3) * 14, y: 1.65, z: -3 };
      return { type: 'frame', payload: { sequence, observedSequence: snapshot.sequence, elapsedMilliseconds, weather: 'Clear', lightning: false,
        throughCombatSequence: 0, events: [], frame: { phase: snapshot.state, tick: snapshot.state === 'Preparing' ? 0 : sequence,
          night: false, throughSequence: 0, enemies: [], players: snapshot.players.map(player => ({ id: player.id, roomId,
            head, muzzle: head, forward: { x: 0, y: 0, z: 1 }, connected: true, health: 100, magazine: 30, reserve: 90,
            rig: { kind: 'Simulated', left: head, right: head } })) } } };
    }
    assert.equal(send([frame(await api(route), times[0], 1)]).acceptedSequence, 1);
    const running = (await control(id, 'Begin')).session;
    assert.equal(send(times.slice(1, -1).map((elapsed, index) => frame(running, elapsed, index + 2))).acceptedSequence, times.length - 1);
    return async function seal() {
      assert.equal(send([frame(await api(route), times.at(-1), times.length)]).acceptedSequence, times.length);
      await api(route + '/combat-stream/seal', 'POST', { streamId, finalSequence: 0 }, 'GameServer');
      assert.equal(send([{ type: 'seal', finalSequence: times.length }]).complete, true);
    };
  }
  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', { name: '同批錄製時間核對', briefing: '', durationSeconds: 120,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const { sessions } = await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Master', 201, undefined, randomUUID());
    for (const session of sessions) active.add(session.id);
    const ids = sessions.map(session => session.id), seals = [];
    const clocks = [[0, [0, 200, 1000, 1300, 1600]], [200, [0, 300, 600, 1200]], [900, [0, 100, 500]],
      [4000, [0, 200, 600]], [-1000, [0, 300, 4000]]];
    for (const [index, [start, times]] of clocks.entries()) seals.push(await source(sessions[index], start, times));
    const original = await batchEnd();
    const compare = (room, from = ids[0], sequence = 3, batch = original) =>
      `/venue/closure/${batch}/replay-at?${new URLSearchParams({ fromSessionId: from, fromFrame: sequence, roomId: room })}`;
    await api(compare(2), 'GET', undefined, 'Master', 409);
    for (const seal of seals) await seal();
    const match = await api(compare(2));
    const frame = await api(`/sessions/${ids[1]}/world/frames/3`);
    assert.deepEqual(match.frame, frame);
    check(match.requestId === original && match.roomId === 2 && match.recording.header.sessionId === ids[1]
      && match.recording.complete === true && Date.parse(match.capturedAtUtc) === clock + 1000
      && Date.parse(match.frameCapturedAtUtc) === clock + 800,
    'The API selects the original floor frame at its own UTC clock and returns the exact saved packet');
    await api(compare(4), 'GET', undefined, 'Master', 409);
    await api(compare(5), 'GET', undefined, 'Master', 409);
    await api(compare(2, ids[0], 0), 'GET', undefined, 'Master', 400);
    await api(compare(2, ids[0], 6), 'GET', undefined, 'Master', 404);
    await api(compare(2), 'GET', undefined, 'Room2', 403);
    const replacement = await api('/sessions', 'POST', { mode: 'Independent', roomIds: [2], missionId: mission.id }, 'Master', 201);
    active.add(replacement.id);
    const latest = await batchEnd();
    await api(compare(2, replacement.id), 'GET', undefined, 'Master', 404);
    await api(compare(2, ids[0], 3, latest), 'GET', undefined, 'Master', 404);
    check((await api(compare(2))).recording.header.sessionId === ids[1], 'Room reuse, an incomplete recording, another batch and room credentials cannot widen alignment');

    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#venue-closure-load').click();
    await page.locator('#venue-closure-batch').selectOption(original);
    await page.locator(`[data-venue-replay="${ids[0]}"]`).click();
    await canvasAt(5);
    for (const sequence of [4, 3]) { await page.locator('#world-frame-back').click(); await canvasAt(sequence); }
    check(await align(1).isDisabled() && await align(2).isEnabled() && await page.locator('#world-venue-rooms button').count() === 5,
      'Paused history offers only its original room choices, with the currently displayed room disabled');
    await align(4).click();
    await note.filter({ hasText: '已保留目前畫面' }).waitFor();
    check(await picker.inputValue() === ids[0] && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
      'An out-of-range room keeps the original paused recording and frame');
    await page.route(url => url.pathname.endsWith('/replay-at'), async route => {
      const actual = await route.fetch();
      const altered = await actual.json(); altered.recording.header.streamId = randomUUID();
      await route.fulfill({ response: actual, json: altered });
    }, { times: 1 });
    await align(2).click();
    await note.filter({ hasText: '無法核對同批房間的原錄製' }).waitFor();
    check(await picker.inputValue() === ids[0] && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
      'An altered destination stream cannot replace the paused view');

    const response = page.waitForResponse(value => value.url().includes('/replay-at?'));
    await align(2).click();
    assert.equal((await response).headers()['cache-control'], 'no-store');
    await note.filter({ hasText: '畫格早於對照時間 200 毫秒' }).waitFor();
    check(await picker.inputValue() === ids[1] && await page.locator('#world-room').inputValue() === '2'
      && await page.locator('#world-camera').inputValue() === 'top' && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
    'The verified match switches to the original room camera and pauses on the matched frame');
    await page.locator('#world-venue-review').screenshot({ path: path.join(screenshots, 'venue-time-aligned.png') });
    await align(3).click();
    await note.filter({ hasText: '房間 3 · 相同擷取時間' }).waitFor();
    check(await picker.inputValue() === ids[2] && await page.locator('#world-canvas').getAttribute('data-sequence') === '2',
      'Successive switches use the first paused UTC anchor instead of accumulating frame drift');
    await align(1).click();
    await note.filter({ hasText: '房間 1 · 相同擷取時間' }).waitFor();
    check(await picker.inputValue() === ids[0] && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
      'Returning to the anchor room restores its exact original sequence');
    await page.locator('#world-frame-next').click(); await canvasAt(4);
    await align(2).click();
    await note.filter({ hasText: '房間 2 · 畫格早於對照時間 500 毫秒' }).waitFor();
    check(await picker.inputValue() === ids[1] && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
      'Stepping resets the UTC anchor and accepts the inclusive 500 millisecond boundary');
    await picker.selectOption(ids[0]);
    check(await page.locator('#world-venue-review').isHidden() && await page.locator('#world-venue-rooms button').count() === 0,
      'Selecting a recording directly clears all original batch actions');
  } finally {
    for (const id of active) await control(id, 'End');
    await page.close();
  }
};
