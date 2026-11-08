const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const roomIds = [1, 2, 3, 4, 5];
  const mission = await api('/missions', 'POST', {
    name: 'MR 五房開場檢查', briefing: 'Synthetic tracked fixture through the accepted world publisher', durationSeconds: 600,
    environment: { mode: 'MR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: []
  }, 'Master', 201);
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds }, 'Master', 201);
  const route = '/sessions/' + session.id;
  const streamId = randomUUID();
  const page = await context.newPage();
  captureErrors(page);
  const panel = page.locator('#mr-start-requirement');
  async function login(target, role) {
    await target.bringToFront();
    await target.goto(base + '/console/');
    await target.locator('#login-key').fill(tokens[role]);
    await target.locator('#login-form button').click();
    await target.locator('#mr-start-requirement').waitFor();
  }
  try {
    await login(page, 'Master');
    check(await panel.getAttribute('data-state') === 'EmptyRoster', 'The MR start panel first identifies an empty roster');
    for (const roomId of roomIds) {
      for (let seat = 1; seat <= 5; seat++) {
        await api(route + '/players', 'POST', { playerId: randomUUID(), name: `Fixture ${roomId}/${seat}`, roomId, headset: 'Quest3' });
      }
    }
    await api(route + '/combat-stream', 'POST', { streamId, origin: 'GameServer' }, 'GameServer');
    const admitted = await api(route);
    const port = Number(new URL(base).port);
    const captureStart = Date.now();
    const header = { sessionId: session.id, streamId, roomIds, origin: 'GameServer', calibration: 'quest-room-mr-v1',
      captureStartedAtUtc: new Date(captureStart).toISOString().replace('Z', '0000+00:00') };
    let sequence = 0;
    function send(...messages) {
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], {
        input: JSON.stringify({ port, route: '/api' + route + '/world/publish', token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, ...messages] }),
        encoding: 'utf8', timeout: 6000, windowsHide: true
      });
      if (result.status !== 0) throw new Error('Tracked fixture failed: ' + (result.stderr || result.error?.message || 'no acknowledgment'));
      return JSON.parse(result.stdout);
    }
    function publish(snapshot, missing = []) {
      const players = snapshot.players.map(({ id, roomId, seat }) => {
        const head = { x: (roomId - 3) * 14 + (seat - 2) * 1.5, y: 1.65, z: -3 };
        const connected = roomId !== 4 || !missing.includes(seat + 1);
        return { id, roomId, connected, head, muzzle: head, forward: { x: 0, y: 0, z: 1 },
          health: 100, magazine: 30, reserve: 90, rig: connected ? { kind: 'Tracked', left: head, right: head } : { kind: 'None' } };
      });
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence,
        elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - captureStart,
        weather: snapshot.environment.weather, lightning: snapshot.environment.lightning,
        frame: { phase: snapshot.state, night: snapshot.environment.timeOfDay === 'Night', players } };
      if (send({ type: 'frame', payload: packet }).acceptedSequence !== sequence) throw new Error('Tracked fixture frame was not accepted');
    }
    async function publishUntil(target, state, snapshot, missing = []) {
      const deadline = performance.now() + 10000;
      while (performance.now() < deadline) {
        publish(snapshot, missing);
        if (await target.getAttribute('data-state') === state) return;
        await delay(150);
      }
      throw new Error(`MR start did not show ${state}; last state ${await target.getAttribute('data-state')}`);
    }
    await panel.locator('#mr-start-status').filter({ hasText: '等待遊戲來源' }).waitFor();
    check(await panel.locator('[data-mr-room]').count() === 0, 'An MR roster does not show tracked room counts before the world source attaches');
    await publishUntil(panel, 'WaitingPlayers', admitted, [2, 5]);
    const waitingRoom = panel.locator('[data-mr-room="4"]');
    check(await waitingRoom.innerText() === '房間 4 · 3 / 5 追蹤就緒 · 等候席位 2、5'
      && await panel.getByText('5 / 5 追蹤就緒', { exact: false }).count() === 4,
      'Real accepted MR snapshots identify exactly two waiting seats among five rooms and 25 roster entries');
    await panel.screenshot({ path: path.join(screenshots, 'mr-start-waiting-seats.png') });

    const roomPage = await context.newPage();
    captureErrors(roomPage);
    try {
      await login(roomPage, 'Room1');
      const roomPanel = roomPage.locator('#mr-start-requirement');
      await publishUntil(roomPanel, 'WaitingPlayers', admitted, [2, 5]);
      check(await roomPanel.locator('[data-mr-room]').count() === 1
        && await roomPanel.locator('[data-mr-room="1"]').innerText() === '房間 1 · 5 / 5 追蹤就緒'
        && await roomPage.locator('[data-command=Begin]').isDisabled(),
        'A room desk shows its own seats while only the master can start the linked MR session');
    } finally {
      await roomPage.close();
      await page.bringToFront();
    }

    await publishUntil(panel, 'Ready', admitted);
    check(await panel.locator('.ready-player').count() === 1 && await panel.locator('[data-mr-room]').count() === 5,
      'The exact current tracked roster can show full readiness across all five rooms');
    await panel.locator('#mr-start-status').filter({ hasText: '快照已過期' }).waitFor();
    check(await panel.locator('.ready-player, [data-mr-room]').count() === 0,
      'A previously ready MR snapshot ages out and clears the per-room display');

    const update = await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'SetEnvironment',
      environment: { ...admitted.environment, timeOfDay: 'Night' } });
    await publishUntil(panel, 'WaitingRevision', admitted);
    check(await panel.locator('[data-mr-room]').count() === 0 && update.session.sequence > admitted.sequence,
      'A fresh MR frame for the previous management sequence cannot restore ready seats');
    await publishUntil(panel, 'Ready', update.session);
    await panel.screenshot({ path: path.join(screenshots, 'mr-start-ready.png') });
    publish(update.session);
    const command = page.waitForResponse(response => response.url().endsWith('/api' + route + '/commands')
      && response.request().method() === 'POST');
    await page.locator('[data-command=Begin]').click();
    const response = await command;
    if (response.status() !== 200) throw new Error('MR Begin returned ' + response.status());
    const result = await response.json();
    await panel.waitFor({ state: 'hidden' });
    check(result.session.state === 'Running' && result.session.players.length === 25 && result.session.environment.timeOfDay === 'Night',
      'The real Begin starts the original 25-seat MR roster after a fresh observation of the exact revision');
    publish(result.session);
    const { session: ended } = await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    publish(ended);
    await api(route + '/combat-stream/seal', 'POST', { streamId, finalSequence: 0 }, 'GameServer');
    check(send({ type: 'seal', finalSequence: sequence }).complete === true,
      'The MR tracked fixture closes at its accepted final world and combat boundaries');
  } catch (error) {
    await page.screenshot({ path: path.join(screenshots, 'mr-start-failure.png'), timeout: 5000 }).catch(() => {});
    throw error;
  } finally {
    await page.close();
    const state = await api(route);
    if (state.state !== 'Ended') await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
  }
};
