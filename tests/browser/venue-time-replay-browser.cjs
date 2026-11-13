const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function venueTimeReplayBrowser({ context, api, tokens, base, root, screenshots, check, captureErrors }) {
  const page = await context.newPage(), active = new Set();
  captureErrors(page);
  const picker = page.locator('#world-recording'), note = page.locator('#world-venue-message'), basis = page.locator('#world-venue-basis');
  const align = room => page.locator(`[data-venue-align-room="${room}"]`);
  const liveRoom = room => page.locator(`[data-live-room="${room}"]`);
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
  async function source(session, start, times, ticks) {
    const { id, roomIds } = session;
    const streamId = randomUUID(), route = `/sessions/${id}`;
    for (const roomId of roomIds)
      await api(route + '/players', 'POST', { playerId: randomUUID(), name: `Replay room ${roomId}`, roomId, headset: 'Quest3' });
    await api(route + '/combat-stream', 'POST', { streamId, origin, ...(ticks ? { missionClockVersion: 1 } : {}) }, 'GameServer');
    const header = { sessionId: id, streamId, origin, roomIds, ...(start === null ? {} : { captureStartedAtUtc: utc(start) }),
      ...(ticks ? { missionClockVersion: 1, missionDurationSeconds: 120 } : {}) };
    function send(messages) {
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${route}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, ...messages] }) });
      assert.equal(result.status, 0, result.stderr || result.error?.message);
      return JSON.parse(result.stdout);
    }
    function frame(snapshot, elapsedMilliseconds, sequence) {
      const players = snapshot.players.map(({ id, roomId }) => {
        const head = { x: (roomId - 3) * 14, y: 1.65, z: -3 };
        return { id, roomId, head, muzzle: head, forward: { x: 0, y: 0, z: 1 }, connected: true, health: 100, magazine: 30, reserve: 90,
          rig: { kind: 'Simulated', left: head, right: head } };
      });
      return { type: 'frame', payload: { sequence, observedSequence: snapshot.sequence, elapsedMilliseconds, weather: 'Clear', lightning: false,
        throughCombatSequence: 0, events: [], frame: { phase: snapshot.state, tick: ticks?.[sequence - 1] ?? (snapshot.state === 'Preparing' ? 0 : sequence),
          night: false, throughSequence: 0, enemies: [], players } } };
    }
    assert.equal(send([frame(await api(route), times[0], 1)]).acceptedSequence, 1);
    let running = (await control(id, 'Begin')).session;
    for (let index = 1; index < times.length - 1; index++) {
      if (roomIds[0] === 2 && index === 2) running = (await control(id, 'Pause')).session;
      if (roomIds[0] === 2 && index === 3) running = (await control(id, 'Resume')).session;
      assert.equal(send([frame(running, times[index], index + 1)]).acceptedSequence, index + 1);
    }
    return async function seal() {
      assert.equal(send([frame(await api(route), times.at(-1), times.length)]).acceptedSequence, times.length);
      await api(route + '/combat-stream/seal', 'POST', { streamId, finalSequence: 0 }, 'GameServer');
      assert.equal(send([{ type: 'seal', finalSequence: times.length }]).complete, true);
    };
  }
  async function openLiveRoom(room, sessionId, sequence) {
    const observed = page.waitForRequest(request => {
      const url = new URL(request.url());
      return url.pathname === `/api/sessions/${sessionId}/world/watch` && url.searchParams.get('observerRoomId') === String(room)
        && url.searchParams.get('mode') === 'live' && request.method() === 'GET';
    });
    await liveRoom(room).click(); await observed;
    await page.locator('#world-status').filter({ hasText: `僅接收房間 ${room}` }).waitFor(); await canvasAt(sequence);
    assert.equal(await picker.inputValue(), sessionId);
    assert.equal(await page.locator('#world-room').inputValue(), String(room));
    assert.equal(await liveRoom(room).getAttribute('aria-pressed'), 'true');
  }
  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', { name: '同批錄製時間核對', briefing: '', durationSeconds: 120,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const { sessions } = await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Master', 201, undefined, randomUUID());
    for (const session of sessions) active.add(session.id);
    const ids = sessions.map(session => session.id), seals = [];
    const clocks = [[0, [0, 200, 1000, 1300, 1600], [0, 4, 30, 51, 64]],
      [200, [0, 300, 600, 1150, 1200], [0, 20, 20, 39, 40]], [900, [0, 100, 500]],
      [4000, [0, 200, 600], [0, 30, 45]], [null, [0, 300, 4000], [0, 21, 70]]];
    for (const [index, [start, times, ticks]] of clocks.entries()) seals.push(await source(sessions[index], start, times, ticks));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-world').click();
    await openLiveRoom(1, ids[0], 4);
    check(await page.locator('#world-live-rooms button').count() === 5 && await page.locator('#world-camera').inputValue() === 'top',
      'The master opens a room-scoped top view directly from the five active Independent rooms');
    await page.route(url => url.pathname === `/api/sessions/${ids[1]}/world` && url.searchParams.get('observerRoomId') === '2', async route => {
      const actual = await route.fetch(), altered = await actual.json();
      altered.header.streamId = randomUUID();
      await route.fulfill({ response: actual, json: altered });
    }, { times: 1 });
    await liveRoom(2).click();
    await page.locator('#world-message').filter({ hasText: '已保留目前畫面' }).waitFor();
    check(await picker.inputValue() === ids[0] && await page.locator('#world-room').inputValue() === '1'
      && await page.locator('#world-canvas').getAttribute('data-sequence') === '4',
      'A substituted recording stream leaves the current live room and frame intact');
    await openLiveRoom(2, ids[1], 4);
    check(await liveRoom(1).isEnabled() && await liveRoom(2).isDisabled() && (await liveRoom(2).innerText()).includes('觀戰中'),
      'The Independent room switch selects the exact other recording without returning to operations');
    await page.locator('#world-live-rooms').screenshot({ path: path.join(screenshots, 'world-live-rooms.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.locator('#world-live-rooms').evaluate(panel => panel.scrollWidth <= panel.clientWidth + 1),
      'The five live room entries fit the mobile observer panel');
    await page.locator('#world-live-rooms').screenshot({ path: path.join(screenshots, 'world-live-rooms-mobile.png') });
    await page.setViewportSize({ width: 1440, height: 1080 });
    const roomDesk = await context.newPage();
    captureErrors(roomDesk);
    try {
      await roomDesk.goto(base + '/console/');
      await roomDesk.locator('#login-key').fill(tokens.Room2); await roomDesk.locator('#login-form button').click();
      await roomDesk.locator('#tab-world').click();
      await roomDesk.locator(`#world-recording option[value="${ids[1]}"]`).waitFor({ state: 'attached' });
      check(await roomDesk.locator('#world-live-rooms').isHidden(), 'Room controllers keep the existing recording view without the master room selector');
    } finally { await roomDesk.close(); }
    const original = await batchEnd();
    await liveRoom(1).click();
    await page.locator('#world-message').filter({ hasText: '無法確認房間 1' }).waitFor();
    check(await picker.inputValue() === ids[1], 'An ended room cannot reopen from an earlier live room list');
    await page.locator('#world-refresh').click();
    await page.locator('#world-live-rooms').waitFor({ state: 'hidden' });
    check(await picker.inputValue() === ids[1], 'Ending the venue withdraws live room entries without selecting another recording');
    const compare = (room, from = ids[0], sequence = 3, batch = original) =>
      `/venue/closure/${batch}/replay-at?${new URLSearchParams({ fromSessionId: from, fromFrame: sequence, roomId: room })}`;
    const byTick = (...args) => compare(...args).replace('/replay-at?', '/replay-at-tick?');
    await api(compare(2), 'GET', undefined, 'Master', 409);
    await api(byTick(2), 'GET', undefined, 'Master', 409);
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
    const missionMatch = await api(byTick(2));
    const firstAtTwenty = await api(`/sessions/${ids[1]}/world/frames/2`);
    check(missionMatch.fromTick === 30 && missionMatch.frameTick === 20 && missionMatch.frame.packet.frame.phase === 'Running'
      && JSON.stringify(missionMatch.frame) === JSON.stringify(firstAtTwenty),
    'Mission alignment uses the first frame at the matching tick across a paused duplicate and the inclusive half-second floor');
    const noClock = await api(byTick(5));
    check(!Number.isFinite(Date.parse(noClock.recording.header.captureStartedAtUtc)) && noClock.fromTick === 30 && noClock.frameTick === 21
      && (await api(byTick(4))).frameTick === 30, 'Mission alignment works across nonoverlapping UTC clocks and on a recording without UTC');
    await api(byTick(2, ids[0], 4), 'GET', undefined, 'Master', 409);
    await api(byTick(5, ids[0], 4), 'GET', undefined, 'Master', 409);
    await api(byTick(5, ids[0], 1), 'GET', undefined, 'Master', 409);
    await api(byTick(3), 'GET', undefined, 'Master', 409);
    await api(byTick(2, ids[2], 2), 'GET', undefined, 'Master', 409);
    await api(byTick(2), 'GET', undefined, 'Room2', 403);
    await api(byTick(2, replacement.id), 'GET', undefined, 'Master', 404);
    check(true, 'The mission clock API rejects tick zero, legacy clocks, gaps, out-of-range ticks, reused rooms and room credentials');

    await page.locator('#tab-operations').click();
    await page.locator('#venue-closure-load').click();
    await page.locator('#venue-closure-batch').selectOption(original);
    await page.locator(`[data-venue-replay="${ids[0]}"]`).click();
    await canvasAt(5);
    for (const sequence of [4, 3]) { await page.locator('#world-frame-back').click(); await canvasAt(sequence); }
    const frameNumber = page.locator('#world-frame-number'), frameGo = page.locator('#world-frame-go');
    await frameNumber.fill('6');
    await frameGo.click();
    check(await frameNumber.getAttribute('max') === '5'
      && await frameNumber.evaluate(input => input.validity.rangeOverflow)
      && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
    'Direct frame jump rejects a sequence beyond the sealed recording');
    const direct = page.waitForResponse(value => new URL(value.url()).pathname.endsWith(`/sessions/${ids[0]}/world/frames/2`));
    await frameNumber.fill('2');
    await frameNumber.press('Enter');
    assert.equal((await direct).status(), 200);
    await canvasAt(2);
    await page.waitForFunction(() => !document.querySelector('#world-frame-go').disabled, null, { polling: 100 });
    check(await frameGo.isEnabled() && await picker.inputValue() === ids[0]
      && await page.locator('#world-room').inputValue() === '1'
      && (await page.locator('#world-frame-message').innerText()).includes('第 2 格'),
    'Direct frame jump loads the exact original frame and stays paused in the same room');
    await page.locator('#world-frame-jump').screenshot({ path: path.join(screenshots, 'world-frame-jump.png') });
    await frameNumber.fill('3');
    await frameGo.click();
    await canvasAt(3);
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
      && await page.locator('#world-camera').inputValue() === 'top' && await page.locator('#world-canvas').getAttribute('data-sequence') === '3'
      && await frameNumber.inputValue() === '',
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

    await align(1).click(); await canvasAt(4);
    await page.locator('#world-frame-back').click(); await canvasAt(3);
    await basis.selectOption('tick');
    check(await align(3).isDisabled() && await align(5).isEnabled(), 'The basis selector disables only destinations that lack the selected clock');
    await page.locator('#camera-name').fill('原房鏡頭待確認');
    await page.route('**/world/cameras/*', route => route.fulfill({ status: 503, json: { error: 'fixture response unavailable' } }), { times: 1 });
    await page.locator('#camera-save').click();
    await page.locator('#camera-retry').waitFor();
    await page.waitForFunction(() => document.querySelector('#world-venue-basis').disabled
      && [...document.querySelectorAll('[data-venue-align-room]')].every(button => button.disabled), null, { polling: 100 });
    check(await picker.inputValue() === ids[0], 'An unconfirmed camera write locks recording changes through both alignment modes');
    await page.locator('#camera-retry').click();
    await page.waitForFunction(() => !document.querySelector('#world-venue-basis').disabled, null, { polling: 100 });
    await page.route(url => url.pathname.endsWith('/replay-at-tick'), async route => {
      const actual = await route.fetch();
      const altered = await actual.json(); altered.frameTick++;
      await route.fulfill({ response: actual, json: altered });
    }, { times: 1 });
    await align(5).click();
    await note.filter({ hasText: '無法核對同批房間的原錄製' }).waitFor();
    check(await picker.inputValue() === ids[0] && await page.locator('#world-canvas').getAttribute('data-sequence') === '3',
      'A mismatched tick reply preserves the original paused room and frame');
    const tickReply = page.waitForResponse(value => value.url().includes('/replay-at-tick?'));
    await align(5).click();
    assert.equal((await tickReply).headers()['cache-control'], 'no-store');
    await note.filter({ hasText: '活動畫格早 450 毫秒' }).waitFor();
    assert.equal(await picker.inputValue(), ids[4]);
    await align(4).click(); await note.filter({ hasText: '房間 4 · 相同任務活動時間' }).waitFor();
    await align(2).click(); await note.filter({ hasText: '房間 2 · 活動畫格早 500 毫秒' }).waitFor();
    check(await picker.inputValue() === ids[1] && await page.locator('#world-canvas').getAttribute('data-sequence') === '2',
      'Successive mission-time switches keep the original tick and choose the first saved frame at a repeated tick');
    await page.locator('#world-venue-review').screenshot({ path: path.join(screenshots, 'venue-mission-time-aligned.png') });
    await align(1).click(); await note.filter({ hasText: '房間 1 · 相同任務活動時間' }).waitFor();
    await canvasAt(3);
    for (const sequence of [2, 1]) { await page.locator('#world-frame-back').click(); await canvasAt(sequence); }
    check(await align(2).isDisabled() && await basis.inputValue() === 'tick',
      'Returning to the anchor restores its exact frame and stepping to tick zero disables mission alignment');
    await picker.selectOption(ids[0]);
    check(await page.locator('#world-venue-review').isHidden() && await page.locator('#world-venue-rooms button').count() === 0,
      'Selecting a recording directly clears all original batch actions');

    const linked = await api('/sessions', 'POST', { mode: 'Linked', roomIds: [1, 2, 3, 4, 5], missionId: mission.id }, 'Master', 201);
    active.add(linked.id);
    const sealLinked = await source(linked, 0, [0, 300, 600], [0, 12, 24]);
    await page.locator('#world-refresh').click();
    await openLiveRoom(3, linked.id, 2);
    await openLiveRoom(5, linked.id, 2);
    check((await page.locator('#world-statistics tr').allTextContents()).some(row => row.includes('Replay room 5'))
      && !(await page.locator('#world-statistics tr').allTextContents()).some(row => row.includes('Replay room 3')),
      'Linked room navigation keeps the same session and renders only the newly selected room’s statistics');
    await control(linked.id, 'End'); active.delete(linked.id); await sealLinked();
  } finally {
    for (const id of active) await control(id, 'End');
    await page.close();
  }
};
