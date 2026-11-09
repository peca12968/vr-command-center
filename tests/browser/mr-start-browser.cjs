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
  const venueButton = page.locator('#venue-begin');
  const venueRoom = (room, state) => page.locator(`[data-begin-room="${room}"][data-begin-state="${state}"]`);
  async function command(action) {
    const pending = page.waitForResponse(response => response.url().endsWith('/api' + route + '/commands')
      && response.request().method() === 'POST' && response.request().postDataJSON().action === action);
    await page.locator(`[data-command=${action}]`).click();
    const response = await pending;
    return { status: response.status(), body: await response.json(), intent: response.request().postDataJSON() };
  }
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
    await venueRoom(5, 'EmptyRoster').waitFor();
    check(await page.locator('[data-begin-state="EmptyRoster"]').count() === 5 && await venueButton.isDisabled(),
      'An empty Linked roster is shown as a shared blocker across the five target rooms');
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
    let sequence = 0, damage, damagePublished = false;
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
        const eliminated = id === damage?.playerId;
        const connected = !eliminated && (roomId !== 4 || !missing.includes(seat + 1));
        return { id, roomId, connected, head, muzzle: head, forward: { x: 0, y: 0, z: 1 },
          health: eliminated ? 0 : 100, magazine: 30, reserve: 90, rig: connected ? { kind: 'Tracked', left: head, right: head } : { kind: 'None' } };
      });
      const through = Number(Boolean(damage));
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence,
        elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - captureStart,
        weather: snapshot.environment.weather, lightning: snapshot.environment.lightning, throughCombatSequence: through,
        events: damage && !damagePublished ? [damage] : [],
        frame: { phase: snapshot.state, night: snapshot.environment.timeOfDay === 'Night', tick: through, throughSequence: through, players } };
      if (send({ type: 'frame', payload: packet }).acceptedSequence !== sequence) throw new Error('Tracked fixture frame was not accepted');
      if (damage) damagePublished = true;
    }
    async function publishUntil(target, state, snapshot, missing = [], matches = async () => true) {
      const deadline = performance.now() + 10000;
      while (performance.now() < deadline) {
        publish(snapshot, missing);
        if (await target.getAttribute('data-state') === state && await matches()) return;
        await delay(150);
      }
      throw new Error(`MR start did not show ${state}; last state ${await target.getAttribute('data-state')}`);
    }
    await panel.locator('#mr-start-status').filter({ hasText: '等待遊戲來源' }).waitFor();
    await venueRoom(4, 'NoRecording').waitFor();
    check(await venueButton.isDisabled(), 'The whole-venue preview distinguishes a missing source from an empty roster');
    check(await panel.locator('[data-mr-room]').count() === 0, 'An MR roster does not show tracked room counts before the world source attaches');
    const blockedStart = await command('Begin');
    await page.locator('#notice').filter({ hasText: 'MR 場次尚未就緒' }).waitFor();
    check(blockedStart.status === 409 && blockedStart.body.code === 'mr-readiness-required' && (await api(route)).sequence === admitted.sequence,
      'The original Begin conflict retains its own operator message and leaves the session preparing');
    await publishUntil(panel, 'WaitingPlayers', admitted, [2, 5], () => venueRoom(4, 'WaitingPlayers').isVisible());
    const waitingRoom = panel.locator('[data-mr-room="4"]');
    check(await waitingRoom.innerText() === '房間 4 · 3 / 5 追蹤就緒 · 等候席位 2、5'
      && await panel.getByText('5 / 5 追蹤就緒', { exact: false }).count() === 4,
      'Real accepted MR snapshots identify exactly two waiting seats among five rooms and 25 roster entries');
    check(await venueRoom(4, 'WaitingPlayers').innerText() === '房間 4 · 等候席位 2、5 的追蹤'
      && await page.locator('[data-begin-state="WaitingLinkedRooms"]').count() === 4 && await venueButton.isDisabled(),
      'Only the linked room with missing tracking names waiting seats, and the entire shared session remains blocked');
    await page.locator('#venue-phase').screenshot({ path: path.join(screenshots, 'venue-phase-begin-mr-blockers.png') });
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
      const readiness = await api('/rooms/readiness', 'GET', undefined, 'Room1');
      check(readiness.rooms.length === 1 && readiness.rooms[0].roomId === 1 && !Object.hasOwn(readiness.rooms[0], 'venueBegin')
        && await roomPage.locator('#venue-phase').isHidden() && await roomPage.locator('[data-begin-room]').count() === 0,
        'Room credentials neither receive the master-only Begin details nor render the whole-venue rows');
    } finally {
      await roomPage.close();
      await page.bringToFront();
    }

    await publishUntil(panel, 'Ready', admitted, [], () => venueButton.isEnabled());
    check(await panel.locator('.ready-player').count() === 1 && await panel.locator('[data-mr-room]').count() === 5,
      'The exact current tracked roster can show full readiness across all five rooms');
    await panel.locator('#mr-start-status').filter({ hasText: '快照已過期' }).waitFor();
    await venueRoom(4, 'Stale').waitFor();
    check(await panel.locator('.ready-player, [data-mr-room]').count() === 0,
      'A previously ready MR snapshot ages out and clears the per-room display');
    check(await venueButton.isDisabled() && await page.locator('[data-begin-state="Ready"], [data-begin-state="WaitingPlayers"]').count() === 0,
      'Expired MR evidence disables the batch and removes all old per-room tracked seat claims');

    const update = await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'SetEnvironment',
      environment: { ...admitted.environment, timeOfDay: 'Night' } });
    await publishUntil(panel, 'WaitingRevision', admitted, [], () => venueRoom(4, 'WaitingRevision').isVisible());
    check(await panel.locator('[data-mr-room]').count() === 0 && update.session.sequence > admitted.sequence,
      'A fresh MR frame for the previous management sequence cannot restore ready seats');
    check(await venueButton.isDisabled() && await page.locator('[data-begin-state="Ready"]').count() === 0,
      'An older but fresh frame is labeled as awaiting the new revision and cannot enable whole-venue Begin');
    await publishUntil(panel, 'Ready', update.session, [], () => venueButton.isEnabled());
    await panel.screenshot({ path: path.join(screenshots, 'mr-start-ready.png') });
    publish(update.session);
    const started = await command('Begin');
    if (started.status !== 200) throw new Error('MR Begin returned ' + started.status);
    const result = started.body;
    await panel.locator('#mr-start-title').filter({ hasText: 'MR 執行中追蹤' }).waitFor();
    check(result.session.state === 'Running' && result.session.players.length === 25 && result.session.environment.timeOfDay === 'Night',
      'The real Begin starts the original 25-seat MR roster after a fresh observation of the exact revision');
    publish(result.session);

    // Record a durable combat event so the eliminated seat is distinct from a living disconnected seat.
    const victim = result.session.players.find(player => player.roomId === 4 && player.seat === 4);
    const reportId = randomUUID();
    const hit = await api(route + '/combat-stream/reports', 'POST', { streamId, streamSequence: 1,
      observedSequence: result.session.sequence, report: { reportId, kind: 'PlayerDamaged', origin: 'GameServer',
        playerId: victim.id, damage: 100 } }, 'GameServer');
    damage = { sequence: 1, tick: 1, eventId: reportId, kind: 'PlayerDamaged', playerId: victim.id, enemyId: randomUUID(), damage: 100 };
    const damaged = await api(route);
    publish(damaged);
    await page.locator('#session-meta').filter({ hasText: `序號 ${damaged.sequence}` }).waitFor();
    const alertCard = page.locator('[data-room-readiness="4"]');
    const alerts = page.locator('[data-room-readiness].tracking-attention');
    const currentAlert = () => alertCard.evaluate(card => card.classList.contains('tracking-attention'));
    await publishUntil(panel, 'WaitingPlayers', damaged, [2], currentAlert);
    check(await waitingRoom.innerText() === '房間 4 · 3 / 4 追蹤就緒 · 等候席位 2 · 已淘汰 1'
      && await alertCard.innerText() === 'MR · 3 / 4 追蹤就緒 · 等候 1 席' && await alerts.count() === 1
      && (await api(route)).state === 'Running' && (await api(route)).sequence === damaged.sequence,
      'A real Running MR frame flags the one living lost seat in its room without changing the mission phase');
    await panel.screenshot({ path: path.join(screenshots, 'mr-running-waiting-seats.png') });
    await panel.locator('#mr-start-status').filter({ hasText: '快照已過期' }).waitFor();
    await alerts.waitFor({ state: 'hidden' });
    check(await panel.locator('[data-mr-room]').count() === 0 && !await currentAlert(),
      'A stale Running frame clears the previously known missing seats and room alert');
    await publishUntil(panel, 'Ready', damaged, [], async () => await alertCard.innerText() === 'MR · 4 / 4 追蹤就緒');
    check(await alerts.count() === 0 && await panel.locator('li.tracking-attention').count() === 0
      && await waitingRoom.innerText() === '房間 4 · 4 / 4 追蹤就緒 · 已淘汰 1',
      'A new tracked frame clears both Running alerts while preserving the eliminated seat');
    await publishUntil(panel, 'WaitingPlayers', damaged, [2], currentAlert);
    const paused = await command('Pause');
    if (paused.status !== 200) throw new Error(`MR Pause returned ${paused.status}: ${paused.body.error}`);
    await panel.locator('#mr-start-title').filter({ hasText: 'MR 繼續檢查' }).waitFor();
    publish(damaged);
    const pendingSource = await api(route + '/readiness');
    const early = await command('Resume');
    check(pendingSource.sourceState === 'PhasePending' && early.status === 409 && early.body.code === 'mr-resume-readiness-required'
      && (await api(route)).sequence === paused.body.session.sequence,
      'Resume cannot use a Running snapshot after Pause and preserves the paused sequence');

    await publishUntil(panel, 'WaitingPlayers', paused.body.session, [2]);
    check(hit.statistics.players.find(player => player.playerId === victim.id).health === 0
      && await waitingRoom.innerText() === '房間 4 · 3 / 4 追蹤就緒 · 等候席位 2 · 已淘汰 1',
      'The paused panel distinguishes a living seat that needs tracking from an eliminated seat');
    await panel.screenshot({ path: path.join(screenshots, 'mr-resume-waiting-seats.png') });
    const denied = await command('Resume');
    await page.locator('#notice').filter({ hasText: 'MR 場次尚未符合繼續條件' }).waitFor();
    check(denied.status === 409 && denied.body.code === 'mr-resume-readiness-required'
      && (await api(route)).sequence === paused.body.session.sequence,
      'A missing living pose rejects Resume without advancing management state');

    await publishUntil(panel, 'Ready', paused.body.session);
    check(await waitingRoom.innerText() === '房間 4 · 4 / 4 追蹤就緒 · 已淘汰 1',
      'Fresh paused tracking clears the living seat while the eliminated seat stays disconnected');
    await panel.screenshot({ path: path.join(screenshots, 'mr-resume-ready.png') });
    publish(paused.body.session);
    const resumed = await command('Resume');
    if (resumed.status !== 200) throw new Error('Recovered MR Resume returned ' + resumed.status);
    await panel.locator('#mr-start-title').filter({ hasText: 'MR 執行中追蹤' }).waitFor();
    check(resumed.body.session.state === 'Running' && resumed.body.session.startedAtUtc === result.session.startedAtUtc
      && resumed.body.session.players.length === 25 && resumed.body.duplicate === false,
      'The original MR session continues with the same 25 seats and original mission start');
    check((await api(route + '/commands', 'POST', resumed.intent)).duplicate === true,
      'The exact accepted MR Resume is idempotent');
    publish(resumed.body.session);
    const { session: ended } = await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    publish(ended);
    await api(route + '/combat-stream/seal', 'POST', { streamId, finalSequence: 1 }, 'GameServer');
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
