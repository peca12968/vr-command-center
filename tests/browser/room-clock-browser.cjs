const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const page = await context.newPage();
  captureErrors(page);
  const rooms = [];
  const cell = room => page.locator(`[data-room-clock="${room}"]`);
  const command = (session, action, extra = {}) => api(`/sessions/${session.id}/commands`, 'POST',
    { commandId: randomUUID(), action, ...extra }).then(receipt => receipt.session);
  async function create(room, mission, autoEnd) {
    let session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room] }, 'Master', 201);
    rooms.push(session);
    session = await api(`/sessions/${session.id}/players`, 'POST', { playerId: randomUUID(), roomId: room, name: 'Clock seat', headset: 'Quest3' });
    const streamId = randomUUID(), origin = 'Simulation';
    await api(`/sessions/${session.id}/combat-stream`, 'POST', { streamId, origin, missionClockVersion: 1 }, 'GameServer');
    session = autoEnd ? await command(session, 'SetMissionClock', { missionClock: { autoEnd } }) : await api(`/sessions/${session.id}`);
    const start = Date.now();
    const header = { sessionId: session.id, streamId, origin, roomIds: [room], missionClockVersion: 1, missionDurationSeconds: 90,
      captureStartedAtUtc: new Date(start).toISOString().replace('Z', '0000+00:00') };
    let sequence = 0;
    function publish(snapshot, tick, suspended = false) {
      const point = { x: (room - 3) * 14, y: 1.65, z: -3 };
      const players = snapshot.players.map(player => ({ id: player.id, roomId: room, connected: false, head: point, muzzle: point,
        forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: 30, reserve: 90, rig: { kind: 'None' } }));
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - start,
        weather: 'Clear', suspended, throughCombatSequence: 0, events: [],
        frame: { phase: suspended ? 'Paused' : snapshot.state, tick, night: false, throughSequence: 0, players } };
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api/sessions/${snapshot.id}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, { type: 'frame', payload: packet }] }) });
      if (result.status !== 0) throw new Error('Clock fixture publication failed: ' + (result.stderr || result.error?.message));
      assert.equal(JSON.parse(result.stdout).acceptedSequence, sequence);
    }
    publish(session, 0);
    return { room, session, publish };
  }
  async function login(role) {
    await page.bringToFront(); await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]); await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function publishUntil(samples, expected) {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      for (const [source, tick, suspended] of samples) source.publish(source.session, tick, suspended);
      const matches = await Promise.all(expected.map(async ([room, text]) => (await cell(room).innerText()) === text));
      if (matches.every(Boolean)) return;
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    throw new Error('Expected room clocks were not displayed');
  }

  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', { name: '房卡計時驗證', briefing: '', durationSeconds: 90,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const automatic = await create(1, mission, true), manual = await create(2, mission, false);
    await login('Master');
    await cell(1).filter({ hasText: '尚未開始 · 計畫 01:30' }).waitFor();
    check(await cell(2).innerText() === '尚未開始 · 計畫 01:30' && await page.locator('[data-room-clock]').count() === 2,
      'Room cards show the saved plan before Begin and omit clocks for empty rooms');
    automatic.session = await command(automatic.session, 'Begin'); manual.session = await command(manual.session, 'Begin');
    await publishUntil([[automatic, 400], [manual, 140]], [[1, '剩餘 01:10 · 自動結束'], [2, '活動 00:07 / 01:30']]);
    check((await api('/rooms/readiness')).rooms.slice(0, 2).every(row => row.clock.phase === 'Running'),
      'Two independent room cards show different accepted ticks and the actual timing policy');
    await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'room-clock-running.png') });
    automatic.session = await command(automatic.session, 'Pause');
    await publishUntil([[automatic, 400], [manual, 180]], [[1, '暫停 · 剩餘 01:10 · 自動結束'], [2, '活動 00:09 / 01:30']]);
    check(await cell(1).getAttribute('data-clock-state') === 'Paused', 'One paused room freezes while another room advances');
    await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'room-clock-paused.png') });
    await cell(1).filter({ hasText: '活動時間未確認' }).waitFor();
    await cell(2).filter({ hasText: '活動時間未確認' }).waitFor();
    check((await api('/rooms/readiness')).rooms.slice(0, 2).every(row => !row.clock), 'Stale sources clear both room clocks without local extrapolation');
    automatic.session = await command(automatic.session, 'Resume');
    await publishUntil([[automatic, 420]], [[1, '剩餘 01:09 · 自動結束'], [2, '活動時間未確認']]);
    check(await cell(1).getAttribute('data-clock-state') === 'Running', 'A newly accepted Resume frame restores only its own clock');
    await publishUntil([[automatic, 420, true], [manual, 200]],
      [[1, '遊戲來源暫停 · 剩餘 01:09 · 自動結束'], [2, '活動 00:10 / 01:30']]);
    const suspended = (await api('/rooms/readiness')).rooms[0];
    check(await cell(1).getAttribute('data-clock-state') === 'Suspended' && suspended.sourceState === 'Suspended'
      && suspended.clock.phase === 'Paused' && (await api('/sessions/' + automatic.session.id)).state === 'Running',
      'A suspended game source displays its frozen clock without pausing management or the other room');
    await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'room-clock-source-suspended.png') });
    await cell(1).filter({ hasText: '活動時間未確認' }).waitFor();
    check(!(await api('/rooms/readiness')).rooms[0].clock,
      'A suspended clock clears when no fresh source frames arrive');
    await publishUntil([[automatic, 440]], [[1, '剩餘 01:08 · 自動結束']]);
    check(await cell(1).getAttribute('data-clock-state') === 'Running',
      'A running frame restores the countdown without an operator Resume');
    await page.locator('#tab-world').click();
    await page.locator('#world-recording').selectOption(automatic.session.id);
    await page.locator('#world-live').click();
    automatic.publish(automatic.session, 440, true);
    await page.locator('#world-status').filter({ hasText: '遊戲來源暫停' }).waitFor();
    check((await page.locator('#world-status').textContent()).includes('活動時間 00:22')
      && await page.locator('#world-environment').textContent() === 'Clear · 日間 · 無雷電',
      'Observation describes a suspended phase and keeps the recorded environment distinct');
    automatic.publish(automatic.session, 460);
    await page.locator('#world-status').filter({ hasText: '執行中' }).waitFor();
    check(!(await page.locator('#world-status').textContent()).includes('遊戲來源暫停'),
      'The next running world frame clears the suspension label');
    await login('Room2');
    await publishUntil([[manual, 200]], [[2, '活動 00:10 / 01:30']]);
    check(await page.locator('[data-room-clock]').count() === 1 && (await api('/rooms/readiness', 'GET', undefined, 'Room2')).rooms.length === 1,
      'Room control sees only the accepted clock for its own room');
  } finally {
    await page.close();
    for (const session of rooms) await command(session, 'End');
  }
};
