const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const page = await context.newPage();
  captureErrors(page);
  const route = '**/api/venue/phase';
  const active = new Set();
  const panel = page.locator('#venue-phase'), summary = page.locator('#venue-phase-targets');
  const notice = page.locator('#notice');
  const evidence = page.locator('#venue-phase-evidence');
  const roomPhase = room => page.locator(`[data-room-venue-phase="${room}"]`);
  const run = (id, action) => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action });
  async function prepare(id, room, withSource, connected = false) {
    let snapshot = await api(`/sessions/${id}/players`, 'POST', { playerId: randomUUID(), roomId: room, name: 'Venue seat', headset: 'Quest3' });
    let publish;
    if (withSource) {
      const streamId = randomUUID(), origin = 'Simulation', started = Date.now();
      await api(`/sessions/${id}/combat-stream`, 'POST', { streamId, origin }, 'GameServer');
      snapshot = await api(`/sessions/${id}`);
      const header = { sessionId: id, streamId, origin, roomIds: [room], captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00') };
      let sequence = 0;
      const send = message => {
        const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
          input: JSON.stringify({ port: Number(new URL(base).port), route: `/api/sessions/${id}/world/publish`, token: tokens.GameServer,
            messages: [{ type: 'header', payload: header }, message] }) });
        if (result.status !== 0) throw new Error('Venue fixture publication failed: ' + (result.stderr || result.error?.message));
        return JSON.parse(result.stdout);
      };
      publish = current => {
        const head = { x: (room - 3) * 14, y: 1.65, z: -3 };
        const rotation = { x: 0, y: 0, z: 0, w: 1 };
        const rig = connected ? { kind: 'Simulated', headRotation: rotation, rightRotation: rotation, leftRotation: rotation,
          right: head, left: head } : { kind: 'None' };
        const players = current.players.map(player => ({ id: player.id, roomId: room, head, muzzle: head,
          connected, forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: 30, reserve: 90, rig }));
        const { weather, timeOfDay, lightning } = current.environment;
        const { behavior, autoAttack } = current.enemies;
        const visibility = ['Fog', 'Storm'].includes(weather) ? weather : 'Clear';
        const packet = { sequence: ++sequence, observedSequence: current.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
          weather, lightning, throughCombatSequence: 0, events: [],
          frame: { phase: current.state, tick: 0, night: timeOfDay === 'Night', visibility, behavior, autoAttack, throughSequence: 0, players } };
        assert.equal(send({ type: 'frame', payload: packet }).acceptedSequence, sequence);
      };
      publish.seal = () => assert.equal(send({ type: 'seal', finalSequence: sequence }).complete, true);
      publish(snapshot);
    }
    return publish;
  }
  async function start(id, room, withSource = false) {
    const publish = await prepare(id, room, withSource);
    await run(id, 'Begin');
    return publish;
  }
  async function end(id) { await run(id, 'End'); active.delete(id); }
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]); await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function click(action, rooms) {
    let message;
    const confirmed = page.waitForEvent('dialog').then(async dialog => { message = dialog.message(); await dialog.accept(); });
    await page.locator(`#venue-${action}`).click();
    await confirmed;
    assert.match(message, new RegExp(rooms));
  }
  async function publishUntil(publish, snapshot, ready) {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      publish(snapshot);
      if (await ready()) return;
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    throw new Error('Expected a room confirmation from the accepted frame');
  }

  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', { name: '全館暫停測試', briefing: '', durationSeconds: 180,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const created = await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Master', 201, undefined, randomUUID());
    const ids = created.sessions.map(session => session.id);
    for (const id of ids) active.add(id);
    const publish = await start(ids[0], 1, true);
    await start(ids[1], 2); await start(ids[2], 3);
    await run(ids[2], 'Pause'); await end(ids[4]);
    await api('/venue/phase', 'GET', undefined, 'Room2', 403);
    await api('/venue/phase', 'POST', { action: 'Pause', targets: [] }, 'Room2', 403, undefined, randomUUID());
    await api('/venue/phase', 'POST', { action: 'Pause', targets: [] }, 'Master', 400);
    await login('Room2');
    check(await panel.isHidden(), 'Whole-venue phase controls are scoped to Master in the API and console');
    await login('Master');
    await summary.filter({ hasText: '可暫停 房間 1、2 · 可繼續 無' }).waitFor();
    check(await page.locator('#venue-resume').isDisabled(), 'The preview excludes manual pauses and rooms that are preparing or ended');
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-preview.png') });

    async function changed(request) {
      if (request.request().method() !== 'POST') return request.continue();
      await run(ids[1], 'Pause'); await run(ids[1], 'Resume');
      await request.continue();
    }
    await page.route(route, changed);
    await click('pause', '房間 1、2');
    await notice.filter({ hasText: '本批命令未套用' }).waitFor();
    await page.unroute(route, changed);
    check((await api(`/sessions/${ids[0]}`)).state === 'Running' && (await api(`/sessions/${ids[1]}`)).state === 'Running',
      'A room returning to Running after preview rejects the entire stale browser submission');
    await page.locator('#refresh').click();
    await summary.filter({ hasText: '可暫停 房間 1、2 · 可繼續 無' }).waitFor();

    const requests = [];
    async function lost(request) {
      if (request.request().method() !== 'POST') return request.continue();
      requests.push({ id: request.request().headers()['idempotency-key'], body: request.request().postDataJSON() });
      const response = await request.fetch();
      assert.equal(response.status(), 200);
      assert.equal((await response.json()).duplicate, requests.length > 1);
      if (requests.length === 1) await request.abort('failed');
      else await request.fulfill({ response });
    }
    await page.route(route, lost);
    await click('pause', '房間 1、2'); await notice.filter({ hasText: '結果未確認' }).waitFor();
    check(await page.locator('#pending-command').isVisible() && await page.locator('#venue-resume').isDisabled()
      && (await api(`/sessions/${ids[0]}`)).state === 'Paused', 'A lost reply leaves the actual committed pause pending in the console');
    await page.locator('#retry-command').click(); await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    await page.unroute(route, lost);
    check(requests.length === 2 && requests[0].id && JSON.stringify(requests[0]) === JSON.stringify(requests[1])
      && (await api(`/sessions/${ids[0]}/events`)).filter(event => event.venue).length === 1,
      'The retry sends the exact original key and target phases with only one durable event in each original session');
    await summary.filter({ hasText: '可暫停 無 · 可繼續 房間 1、2' }).waitFor();
    await evidence.filter({ hasText: '等候房間 1、2' }).waitFor();
    await roomPhase(1).filter({ hasText: '全館暫停待確認' }).waitFor();
    check(await page.locator('#venue-resume').isDisabled(),
      'An accepted management pause displays a separate waiting game status and disables whole-venue Resume');
    await run(ids[1], 'Resume'); await run(ids[1], 'Pause');
    await page.locator('#refresh').click(); await summary.filter({ hasText: /^可暫停 無 · 可繼續 房間 1$/ }).waitFor();
    const paused = await api(`/sessions/${ids[0]}`);
    const pausePlan = (await api('/venue/phase')).resume.map(({ sessionId, phaseSinceSequence }) => ({ sessionId, phaseSinceSequence }));
    const allowed = () => page.locator('#venue-resume').isEnabled();
    await publishUntil(publish, paused, allowed);
    await roomPhase(2).waitFor({ state: 'hidden' });
    check(await roomPhase(1).filter({ hasText: '全館暫停已套用' }).isVisible(),
      'The original source confirms the venue pause while the later manual pause has no venue marker');
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-resume.png') });
    await roomPhase(1).filter({ hasText: '快照已過期' }).waitFor();
    const declined = await api('/venue/phase', 'POST', { action: 'Resume', targets: pausePlan }, 'Master', 409, undefined, randomUUID());
    check(declined.code === 'venue-pause-not-observed' && declined.roomIds.join() === '1' && await page.locator('#venue-resume').isDisabled(),
      'Expired pause evidence clears the live confirmation and the HTTP API rejects an early Resume');
    await publishUntil(publish, paused, allowed);
    await click('resume', '房間 1'); await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    const states = await Promise.all(ids.map(id => api(`/sessions/${id}`).then(session => session.state)));
    check(states.join(',') === 'Running,Paused,Paused,Preparing,Ended', 'Resume affects only a room still in its whole-venue paused phase');
    await roomPhase(1).filter({ hasText: '全館繼續待確認' }).waitFor();
    const resumed = await api(`/sessions/${ids[0]}`);
    await publishUntil(publish, resumed, () => roomPhase(1).filter({ hasText: '全館繼續已套用' }).isVisible());
    check(true, 'A new running frame confirms Resume separately from the management receipt');
    for (const id of ids.slice(0, 4)) await end(id);

    const linked = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] }, 'Master', 201);
    active.add(linked.id); await start(linked.id, 1);
    await page.locator('#refresh').click(); await summary.filter({ hasText: '可暫停 房間 1、2、3、4、5' }).waitFor();
    await click('pause', '1、2、3、4、5 的 1 個場次'); await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    check((await api(`/sessions/${linked.id}/events`)).filter(event => event.venue).length === 1,
      'A linked venue sends one transition for all five rooms');
    await end(linked.id);

    const preparing = [];
    for (const room of [1, 2]) {
      const next = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room] }, 'Master', 201);
      active.add(next.id); preparing.push(next.id);
    }
    const first = await prepare(preparing[0], 1, true, true);
    const getBegin = async () => (await api('/venue/phase')).begin.map(({ sessionId, phaseSinceSequence, sessionSequence }) =>
      ({ sessionId, phaseSinceSequence, sessionSequence }));
    const beginEvidence = page.locator('#venue-begin-evidence');
    const beginButton = page.locator('#venue-begin');
    const preview = await getBegin();
    const firstReady = await api(`/sessions/${preparing[0]}`);
    const declinedBegin = await api('/venue/phase', 'POST', { action: 'Begin', targets: preview }, 'Master', 409, undefined, randomUUID());
    await page.locator('#refresh').click();
    await publishUntil(first, firstReady, () => beginEvidence.filter({ hasText: '等候房間 2 的名冊或遊戲快照' }).isVisible());
    check(declinedBegin.code === 'venue-begin-not-ready' && declinedBegin.roomIds.join() === '2' && await beginButton.isDisabled(),
      'A missing roster and source in one room blocks the whole Begin batch in both HTTP and Chromium');
    const second = await prepare(preparing[1], 2, true, true);
    const staleBegin = await api('/venue/phase', 'POST', { action: 'Begin', targets: preview }, 'Master', 409, undefined, randomUUID());
    check(staleBegin.code === 'venue-phase-changed' && (await api('/sessions')).every(session => session.state === 'Preparing'),
      'Preparing roster and source changes invalidate the previous Begin preview without starting either room');
    const secondReady = await api(`/sessions/${preparing[1]}`);
    await page.locator('#refresh').click();
    await publishUntil(first, firstReady, () => { second(secondReady); return beginButton.isEnabled(); });
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-begin.png') });
    await publishUntil(first, firstReady, () => { second(secondReady); return beginButton.isEnabled(); });
    await click('begin', '房間 1、2 的 2 個場次');
    await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    const running = await Promise.all(preparing.map(id => api(`/sessions/${id}`)));
    check(running.every((session, index) => session.state === 'Running' && session.sequence === [firstReady, secondReady][index].sequence + 1),
      'The browser submits one Begin batch and both durable sessions advance exactly one revision');
    await roomPhase(1).filter({ hasText: '全館開始待確認' }).waitFor();
    await publishUntil(first, running[0], () => {
      second(running[1]);
      return Promise.all([1, 2].map(room => roomPhase(room).filter({ hasText: '全館開始已套用' }).isVisible())).then(rows => rows.every(Boolean));
    });
    check(true, 'Both room cards confirm Begin from their accepted Running frames');

    const climate = { weather: 'Storm', timeOfDay: 'Night', lightning: true };
    const climateTargets = async () => (await api('/venue/phase')).environment.map(({ sessionId, phaseSinceSequence, environmentSinceSequence }) =>
      ({ sessionId, phaseSinceSequence, environmentSinceSequence }));
    const oldEnvironment = await climateTargets();
    const updateRoom2 = environment => api(`/sessions/${preparing[1]}/commands`, 'POST',
      { commandId: randomUUID(), action: 'SetEnvironment', environment }, 'Room2');
    await api('/venue/phase', 'POST', { action: 'SetEnvironment', targets: oldEnvironment, environment: climate }, 'Room2', 403, undefined, randomUUID());
    await api('/venue/phase', 'POST', { action: 'SetEnvironment', targets: oldEnvironment, environment: { weather: 'Storm' } },
      'Master', 400, undefined, randomUUID());
    await updateRoom2(running[1].environment);
    const staleClimate = await api('/venue/phase', 'POST', { action: 'SetEnvironment', targets: oldEnvironment, environment: climate },
      'Master', 409, undefined, randomUUID());
    check(staleClimate.code === 'venue-phase-changed' && (await api(`/sessions/${preparing[0]}`)).environment.weather === 'Clear',
      'A room environment write invalidates the whole preview even when it repeats the same weather');
    await page.locator('#refresh').click();
    await page.locator('#venue-environment-targets').filter({ hasText: '房間 1、2' }).waitFor();
    await page.locator('#venue-weather').selectOption('Storm');
    await page.locator('#venue-time').selectOption('Night');
    await page.locator('#venue-lightning').check();
    let climateDialog;
    const climateConfirmed = page.waitForEvent('dialog').then(async dialog => { climateDialog = dialog.message(); await dialog.accept(); });
    const acceptedClimate = page.waitForResponse(response => response.url().endsWith('/api/venue/phase') && response.request().method() === 'POST');
    await page.locator('#venue-apply-environment').click();
    await climateConfirmed;
    assert.equal((await acceptedClimate).status(), 200);
    const changedClimate = await Promise.all(preparing.map(id => api(`/sessions/${id}`)));
    check(climateDialog.includes('房間 1、2') && climateDialog.includes('暴風雨 · 夜晚 · 閃電開啟')
      && changedClimate.every(session => session.environment.weather === 'Storm' && session.environment.timeOfDay === 'Night' && session.environment.lightning),
      'The console confirms the target rooms and applies the three climate values in one request');
    const roomEnvironment = room => page.locator(`[data-room-venue-environment="${room}"]`);
    await roomEnvironment(1).filter({ hasText: '全館環境待確認' }).waitFor();
    await publishUntil(first, changedClimate[0], () => {
      second(changedClimate[1]);
      return Promise.all([1, 2].map(room => roomEnvironment(room).filter({ hasText: '全館環境已套用' }).isVisible())).then(rows => rows.every(Boolean));
    });
    await page.locator('#venue-environment').screenshot({ path: path.join(screenshots, 'venue-environment.png') });
    check(true, 'Both rooms confirm their own matching environment frames');
    await updateRoom2({ ...changedClimate[1].environment, weather: 'Rain', lightning: false });
    await page.locator('#refresh').click();
    await roomEnvironment(2).waitFor({ state: 'hidden' });
    await roomEnvironment(1).filter({ hasText: '快照已過期' }).waitFor();
    check(await roomEnvironment(1).filter({ hasText: '全館環境待確認' }).isVisible(),
      'A room-specific override clears its marker and the other room expires independently');

    const policy = { behavior: 'Patrol', autoAttack: true };
    const enemyTargets = (await api('/venue/phase')).enemies;
    const changeEnemies = enemies => api(`/sessions/${preparing[1]}/commands`, 'POST',
      { commandId: randomUUID(), action: 'SetEnemies', enemies }, 'Room2');
    await api('/venue/phase', 'POST', { action: 'SetEnemies', targets: enemyTargets, enemyPolicy: policy }, 'Room2', 403, undefined, randomUUID());
    const unsupportedCount = await fetch(base + '/api/venue/phase', { method: 'POST',
      headers: { Authorization: 'Bearer ' + tokens.Master, 'Content-Type': 'application/json', 'Idempotency-Key': randomUUID() },
      body: JSON.stringify({ action: 'SetEnemies', targets: enemyTargets, enemyPolicy: { ...policy, count: 5 } }) });
    assert.equal(unsupportedCount.status, 400);
    await changeEnemies(changedClimate[1].enemies);
    const staleEnemies = await api('/venue/phase', 'POST', { action: 'SetEnemies', targets: enemyTargets, enemyPolicy: policy },
      'Master', 409, undefined, randomUUID());
    check(staleEnemies.code === 'venue-phase-changed' && !(await api(`/sessions/${preparing[0]}`)).enemies.autoAttack,
      'The batch enemy policy rejects a stale room preview and leaves the other room untouched');
    await page.locator('#refresh').click();
    await page.locator('#venue-enemies-targets').filter({ hasText: '房間 1、2' }).waitFor();
    await page.locator('#venue-behavior').selectOption('Patrol');
    await page.locator('#venue-auto-attack').check();
    let enemyDialog;
    const enemyConfirmed = page.waitForEvent('dialog').then(async dialog => { enemyDialog = dialog.message(); await dialog.accept(); });
    const acceptedEnemies = page.waitForResponse(response => response.url().endsWith('/api/venue/phase') && response.request().method() === 'POST');
    await page.locator('#venue-apply-enemies').click();
    await enemyConfirmed;
    assert.equal((await acceptedEnemies).status(), 200);
    const changedEnemies = await Promise.all(preparing.map(id => api(`/sessions/${id}`)));
    check(enemyDialog.includes('房間 1、2') && enemyDialog.includes('巡邏 · 自動攻擊開啟')
      && changedEnemies.every(session => session.enemies.count === 0 && session.enemies.behavior === 'Patrol' && session.enemies.autoAttack),
      'The console applies behavior and attack across rooms while preserving the original counts');
    const roomEnemies = room => page.locator(`[data-room-venue-enemies="${room}"]`);
    await roomEnemies(1).filter({ hasText: '全館敵軍策略待確認' }).waitFor();
    await publishUntil(first, changedEnemies[0], () => {
      second(changedEnemies[1]);
      return Promise.all([1, 2].map(room => roomEnemies(room).filter({ hasText: '全館敵軍策略已套用' }).isVisible())).then(rows => rows.every(Boolean));
    });
    await page.locator('#venue-enemies').screenshot({ path: path.join(screenshots, 'venue-enemies.png') });
    check(true, 'Enemy policy is confirmed only by both original game sources');
    await changeEnemies({ count: 0, behavior: 'Hold', autoAttack: false });
    await page.locator('#refresh').click();
    await roomEnemies(2).waitFor({ state: 'hidden' });
    check(await roomEnemies(1).isVisible(), 'The single-room enemy policy override clears only its own venue marker');

    const extra = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [3] }, 'Master', 201);
    active.add(extra.id);
    await run(preparing[1], 'Pause');
    const endPlan = (await api('/venue/phase')).end;
    await api('/venue/closure', 'GET', undefined, 'Room2', 403);
    await api('/venue/phase', 'POST', { action: 'End', targets: endPlan }, 'Room2', 403, undefined, randomUUID());
    await page.locator('#refresh').click();
    await page.locator('#venue-end-targets').filter({ hasText: '房間 1、2、3' }).waitFor();
    let warning;
    const canceled = page.waitForEvent('dialog').then(async dialog => { warning = dialog.message(); await dialog.dismiss(); });
    await page.locator('#venue-end').click();
    await canceled;
    check(warning.includes('尚未開始的準備場次') && (await api('/sessions')).length === 3
      && (await api('/venue/closure')).batch === null, 'Canceling the explicit End confirmation leaves every original room active');

    requests.length = 0;
    await page.route(route, lost);
    await click('end', '房間 1、2、3 的 3 個場次');
    await notice.filter({ hasText: '結果未確認' }).waitFor();
    check((await api('/sessions')).length === 0 && await page.locator('#pending-command').isVisible(),
      'One durable End releases the running, paused and preparing rooms while the lost response remains pending');
    for (const id of [...preparing, extra.id]) active.delete(id);
    await page.locator('#retry-command').click();
    await notice.filter({ hasText: '全館結束已記錄' }).waitFor();
    await page.unroute(route, lost);
    const table = page.locator('#venue-closure-table');
    const archive = id => page.locator(`[data-venue-closure-session="${id}"] td`);
    const closure = (await api('/venue/closure')).batch;
    check(closure.requestId === requests[0].id && requests.length === 2 && JSON.stringify(requests[0]) === JSON.stringify(requests[1])
      && closure.sessions.every((session, index) => session.roomIds.join() === String(index + 1)),
      'Retry preserves the original End request and the closure table keeps the original room order');
    await table.waitFor();
    check((await archive(preparing[0]).allTextContents()).slice(2, 4).join() === '等待封存,等待封存'
      && (await archive(extra.id).allTextContents()).slice(2, 4).join() === '沒有遊戲來源,沒有遊戲來源',
      'The archive distinguishes an unsealed source from a preparing room that never had a source');
    const ending = await api(`/sessions/${preparing[0]}`);
    first(ending);
    await api(`/sessions/${ending.id}/combat-stream/seal`, 'POST', { streamId: ending.combatStream.streamId, finalSequence: 0 }, 'GameServer');
    await archive(ending.id).nth(2).filter({ hasText: '已封存' }).waitFor();
    check(await archive(ending.id).nth(3).textContent() === '等待封存', 'A combat seal alone does not mark the world replay sealed');
    first.seal();
    await archive(ending.id).nth(3).filter({ hasText: '已封存' }).waitFor();
    await page.locator('#venue-closure').screenshot({ path: path.join(screenshots, 'venue-closure.png') });
    const replacement = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
    active.add(replacement.id);
    await login('Master');
    await archive(ending.id).nth(3).filter({ hasText: '已封存' }).waitFor();
    await archive(ending.id).last().getByRole('button').click();
    await page.waitForFunction(id => document.getElementById('session-select').value === id, ending.id);
    check(await page.locator('#include-ended').isChecked() && (await api(`/sessions/${replacement.id}`)).state === 'Preparing',
      'Reload restores the original archived batch and the table opens that session after the room is reused');
    const archiveRoute = '**/api/venue/closure';
    await page.route(archiveRoute, request => request.fulfill({ status: 503 }));
    await page.locator('#refresh').click();
    await page.locator('#venue-closure-summary').filter({ hasText: '暫時無法確認' }).waitFor();
    check(await table.isHidden(), 'A failed closure read removes the previous seal display');
    await page.unroute(archiveRoute);
  } finally {
    await page.unroute(route); await page.close();
    for (const id of active) await end(id);
  }
};
