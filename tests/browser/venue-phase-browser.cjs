const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
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
  async function prepare(id, room, withSource, connected = false, reinforcementVersion = 0) {
    let snapshot = await api(`/sessions/${id}/players`, 'POST', { playerId: randomUUID(), roomId: room, name: 'Venue seat', headset: 'Quest3' });
    let publish;
    if (withSource) {
      const streamId = randomUUID(), origin = 'Simulation', started = Date.now();
      await api(`/sessions/${id}/combat-stream`, 'POST', { streamId, origin }, 'GameServer');
      snapshot = await api(`/sessions/${id}`);
      const header = { sessionId: id, streamId, origin, roomIds: snapshot.roomIds, reinforcementVersion,
        captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00') };
      let sequence = 0;
      const send = message => {
        const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
          input: JSON.stringify({ port: Number(new URL(base).port), route: `/api/sessions/${id}/world/publish`, token: tokens.GameServer,
            messages: [{ type: 'header', payload: header }, message] }) });
        if (result.status !== 0) throw new Error('Venue fixture publication failed: ' + (result.stderr || result.error?.message));
        return JSON.parse(result.stdout);
      };
      publish = (current, enemies = []) => {
        const players = current.players.map(player => {
          const head = { x: (player.roomId - 3) * 14 + player.seat, y: 1.65, z: -3 };
          const rotation = { x: 0, y: 0, z: 0, w: 1 };
          const rig = connected ? { kind: 'Simulated', headRotation: rotation, rightRotation: rotation, leftRotation: rotation,
            right: head, left: head } : { kind: 'None' };
          return { id: player.id, roomId: player.roomId, head, muzzle: head,
            connected, forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: 30, reserve: 90, rig };
        });
        const { weather, timeOfDay, lightning } = current.environment;
        const { behavior, autoAttack } = current.enemies;
        const visibility = ['Fog', 'Storm'].includes(weather) ? weather : 'Clear';
        const packet = { sequence: ++sequence, observedSequence: current.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
          weather, lightning, throughCombatSequence: 0, events: [],
          frame: { phase: current.state, tick: 0, night: timeOfDay === 'Night', visibility, behavior, autoAttack, throughSequence: 0, players, enemies } };
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
    active.add(linked.id);
    const subject = randomUUID(), roomPeer = randomUUID(), subjectName = '觀戰 <img> 玩家';
    await api(`/sessions/${linked.id}/players`, 'POST', { playerId: subject, roomId: 2, name: subjectName, headset: 'Quest3' });
    await api(`/sessions/${linked.id}/players`, 'POST', { playerId: roomPeer, roomId: 2, name: '同房玩家', headset: 'Quest3' });
    const linkedPublish = await prepare(linked.id, 1, true, true);
    await run(linked.id, 'Begin');
    let linkedState = await api(`/sessions/${linked.id}`);
    linkedPublish(linkedState);
    await page.locator('#refresh').click();
    await page.locator('[data-watch-room="2"]').click();
    const actorPicker = page.locator('#world-actor'), view = page.locator('#world-camera'), linkedCanvas = page.locator('#world-canvas');
    const choices = () => actorPicker.locator('option').evaluateAll(options => options.map(option => option.value));
    await actorPicker.locator(`option[value="p:${subject}"]`).waitFor({ state: 'attached' });
    check(await page.locator('#world-room').inputValue() === '2' && (await choices()).length === 3
      && (await actorPicker.locator(`option[value="p:${subject}"]`).textContent()).includes(subjectName)
      && await actorPicker.locator('img').count() === 0, 'Linked room observation lists only its actors and renders recorded player names as text');
    await actorPicker.selectOption('p:' + subject);
    await view.selectOption('follow');
    const lastTarget = await linkedCanvas.getAttribute('data-camera');
    await api(`/sessions/${linked.id}/players/${subject}`, 'DELETE', undefined, 'Master', 204,
      linkedState.players.find(player => player.id === subject).admissionId);
    linkedState = await api(`/sessions/${linked.id}`);
    linkedPublish(linkedState);
    await view.locator('option[value="follow"]:disabled').waitFor({ state: 'attached' });
    check(await actorPicker.inputValue() === '' && (await choices()).includes('p:' + roomPeer)
      && await view.inputValue() === 'free' && await linkedCanvas.getAttribute('data-camera') === lastTarget,
      'A removed follow target leaves the last camera position and never selects the remaining teammate');
    await page.locator('[data-world-room="all"]').click();
    check((await choices()).length === 3 && await actorPicker.inputValue() === '',
      'All-room observation restores other actors without silently resuming follow');
    await page.locator('[data-world-room="2"]').click();
    await actorPicker.selectOption('p:' + roomPeer);
    await page.locator('#world-canvas').screenshot({ path: path.join(screenshots, 'world-room-actor-scope.png') });
    await page.locator('#tab-operations').click();
    await page.locator('#refresh').click(); await summary.filter({ hasText: '可暫停 房間 1、2、3、4、5' }).waitFor();
    await click('pause', '1、2、3、4、5 的 1 個場次'); await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    check((await api(`/sessions/${linked.id}/events`)).filter(event => event.venue).length === 1,
      'A linked venue sends one transition for all five rooms');
    await end(linked.id);
    const archivedLinked = await api(`/sessions/${linked.id}`);
    await api(`/sessions/${linked.id}/combat-stream/seal`, 'POST', { streamId: archivedLinked.combatStream.streamId, finalSequence: 0 }, 'GameServer');
    linkedPublish(await api(`/sessions/${linked.id}`));
    linkedPublish.seal();
    await page.locator('#include-ended').check();
    await page.locator(`#session-select option[value="${linked.id}"]`).waitFor({ state: 'attached' });
    await page.locator('#session-select').selectOption(linked.id);
    const reportRoom = page.locator('#report-room'), review = page.locator('#player-review-select'), openReview = page.locator('#open-player-review');
    await reportRoom.selectOption('2');
    await review.selectOption(subject);
    check((await review.locator('option').evaluateAll(options => options.map(option => option.value))).sort().join(',')
      === ['', subject, roomPeer].sort().join(',') && await openReview.isEnabled(),
      'A sealed linked review offers only the selected room players, including a removed player from the ledger');
    await reportRoom.selectOption('1');
    check(await review.inputValue() === '' && await openReview.isDisabled(), 'Switching rooms clears a previous personal review selection outside the scope');
    await reportRoom.selectOption('2');
    await review.selectOption(subject);
    const scopedSearch = page.waitForResponse(response => new URL(response.url()).pathname === `/api/sessions/${linked.id}/world/event-frames`);
    await openReview.click();
    const searchQuery = new URL((await scopedSearch).url()).searchParams;
    check(searchQuery.get('roomId') === '2' && searchQuery.get('playerId') === subject
      && await page.locator('#world-room').inputValue() === '2' && await page.locator('#world-review-player-scope').isVisible(),
      'The linked personal review opens the exact sealed source and starts its first search in the selected room');
    await page.locator('#tab-operations').click();
    await page.locator('#include-ended').uncheck();

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
    const beginRoom = room => page.locator(`[data-begin-room="${room}"]`);
    const preview = await getBegin();
    const firstReady = await api(`/sessions/${preparing[0]}`);
    const declinedBegin = await api('/venue/phase', 'POST', { action: 'Begin', targets: preview }, 'Master', 409, undefined, randomUUID());
    await page.locator('#refresh').click();
    await publishUntil(first, firstReady, async () =>
      await beginRoom(1).getAttribute('data-begin-state') === 'Ready' && await beginRoom(2).getAttribute('data-begin-state') === 'EmptyRoster');
    check(declinedBegin.code === 'venue-begin-not-ready' && declinedBegin.roomIds.join() === '2' && await beginButton.isDisabled(),
      'A missing roster and source in one room blocks the whole Begin batch in both HTTP and Chromium');
    check(await beginRoom(1).innerText() === '房間 1 · 1 席姿態就緒'
      && await beginRoom(2).innerText() === '房間 2 · 名冊尚無玩家' && await page.locator('[data-begin-room]').count() === 2,
      'The master sees only the target rooms and can distinguish a ready VR room from an empty independent roster');
    await beginRoom(1).filter({ hasText: '快照已過期' }).waitFor();
    check(await beginButton.isDisabled() && await beginRoom(2).getAttribute('data-begin-state') === 'EmptyRoster',
      'Expired VR evidence clears the ready label while the independent empty-room reason remains');
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-begin-blockers.png') });
    const second = await prepare(preparing[1], 2, true, true, 1);
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
    await beginEvidence.waitFor({ state: 'hidden' });
    check(await page.locator('[data-begin-room]').count() === 0, 'Accepted Begin removes the preparing room rows');
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
    const climateResponse = await acceptedClimate;
    assert.equal(climateResponse.status(), 200);
    const climateReceipt = await climateResponse.json();
    const changedClimate = await Promise.all(preparing.map(id => api(`/sessions/${id}`)));
    check(climateDialog.includes('房間 1、2') && climateDialog.includes('暴風雨 · 夜晚 · 閃電開啟')
      && changedClimate.every(session => session.environment.weather === 'Storm' && session.environment.timeOfDay === 'Night' && session.environment.lightning),
      'The console confirms the target rooms and applies the three climate values in one request');
    const roomEnvironment = room => page.locator(`[data-room-venue-environment="${room}"]`);
    const environmentFrame = room => page.locator(`[data-room-environment-frame="${room}"]`);
    const environmentBatch = page.locator('#venue-environment-batch');
    const climateRoom = (room, state) => environmentBatch.locator(`[data-environment-batch-room="${room}"][data-environment-batch-state="${state}"]`);
    const climateReplay = (room, state) => climateRoom(room, state).getByRole('button', { name: '檢視環境快照' });
    const durableBatch = (await api('/venue/phase')).latestEnvironment;
    check(durableBatch?.requestId === climateReceipt.requestId && durableBatch.weather === 'Storm'
      && durableBatch.timeOfDay === 'Night' && durableBatch.lightning === true
      && durableBatch.sessions.every((row, index) => row.sessionId === preparing[index] && row.roomIds.join() === String(index + 1)
        && row.state === 'Current' && row.appliedAtSequence === climateReceipt.sessions.find(target => target.sessionId === row.sessionId).appliedAtSequence),
      'The phase plan exposes the original accepted environment batch, command sequences and room scopes');
    await roomEnvironment(1).filter({ hasText: '全館環境待確認' }).waitFor();
    check(await environmentFrame(1).isHidden(), 'An accepted venue command does not offer a replay before its matching game frame');
    await climateRoom(1, 'Waiting').waitFor();
    check(await climateReplay(1, 'Waiting').count() === 0 && await environmentBatch.getByText('0 / 2 房已確認', { exact: false }).isVisible(),
      'Accepted environment commands are visible before any matching native frame without approving a replay');
    await publishUntil(first, changedClimate[0], () => climateReplay(1, 'Applied').isVisible());
    check(await climateRoom(2, 'Waiting').isVisible() && await environmentBatch.getByText('1 / 2 房已確認', { exact: false }).isVisible(),
      'The environment batch confirms each room only after its own source applies the command');
    await publishUntil(first, changedClimate[0], () => {
      second(changedClimate[1]);
      return Promise.all([1, 2].map(room => roomEnvironment(room).filter({ hasText: '全館環境已套用' }).isVisible())).then(rows => rows.every(Boolean));
    });
    check(true, 'Both rooms confirm their own matching environment frames');
    async function openSetting(kind, room, id, button = page.locator(`[data-room-${kind}-frame="${room}"]`)) {
      const watched = page.waitForResponse(response => new URL(response.url()).pathname === `/api/sessions/${id}/world/watch`);
      await button.click();
      const response = await watched;
      assert.equal(response.status(), 200);
      const query = new URL(response.url()).searchParams;
      assert.equal(query.get('mode'), 'replay');
      assert.equal(query.get('fromFrame'), query.get('throughFrame'));
      const frame = Number(query.get('fromFrame'));
      assert(frame > 0);
      return frame;
    }
    const original = await openSetting('environment', 1, preparing[0], climateReplay(1, 'Applied'));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${original} 格的環境快照` }).waitFor();
    const durableClimate = await api(`/sessions/${preparing[0]}/world/frames/${original}`);
    check(durableClimate.packet.observedSequence >= climateReceipt.sessions.find(row => row.sessionId === preparing[0]).appliedAtSequence
      && await page.locator('#world-room').inputValue() === '1' && await page.locator('#world-camera').inputValue() === 'top'
      && await page.locator('#world-environment').innerText() === 'Storm · 夜間 · 雷電啟用',
      'The venue weather shortcut pauses on a saved frame at or after its original command, with the exact room and environment');
    await page.locator('#world-viewport').screenshot({ path: path.join(screenshots, 'venue-environment-frame.png') });
    await page.locator('#tab-operations').click();
    const override = await updateRoom2({ ...changedClimate[1].environment, weather: 'Rain', lightning: false });
    await page.locator('#refresh').click();
    await roomEnvironment(2).waitFor({ state: 'hidden' });
    await climateRoom(2, 'Superseded').waitFor();
    check(await climateRoom(2, 'Superseded').getByText(`原命令 ${durableBatch.sessions[1].appliedAtSequence}`, { exact: false }).isVisible()
      && await climateReplay(2, 'Superseded').count() === 0, 'A later local environment change preserves the original batch row without its live shortcut');
    const localEnvironment = page.locator('[data-room-environment="2"]');
    await localEnvironment.filter({ hasText: '場次環境待確認' }).waitFor();
    second(changedClimate[1]);
    check(await environmentFrame(2).isHidden(), 'A single-room override clears the venue marker and cannot reuse the previous command frame');
    await publishUntil(second, override.session, () => environmentFrame(2).isVisible());
    const scoped = (await api('/rooms/readiness', 'GET', undefined, 'Room2')).rooms;
    check(scoped.length === 1 && scoped[0].roomId === 2 && scoped[0].environment.venue === false
      && scoped[0].environment.setting.appliedAtSequence === override.appliedAtSequence && !scoped[0].venueEnvironment,
      'The scoped readiness response confirms the single-room command without leaking another room');
    const weatherRoute = `**/api/sessions/${preparing[1]}/world/watch?**`;
    await page.route(weatherRoute, async route => {
      const original = await route.fetch();
      const body = (await original.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
        const value = JSON.parse(raw); value.packet.lightning = true;
        return 'event: frame\ndata: ' + JSON.stringify(value);
      });
      await route.fulfill({ response: original, body });
    }, { times: 1 });
    await publishUntil(second, override.session, () => environmentFrame(2).isVisible());
    await openSetting('environment', 2, preparing[1]);
    await page.locator('#world-message').filter({ hasText: '回應快照的環境或指令序號不同' }).waitFor();
    check(await page.locator('#world-player').isHidden(), 'A substituted lightning value cannot open the anchored frame');
    await page.locator('#tab-operations').click();
    await publishUntil(second, override.session, () => environmentFrame(2).isVisible());
    const localFrame = await openSetting('environment', 2, preparing[1]);
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${localFrame} 格的環境快照` }).waitFor();
    check(await page.locator('#world-room').inputValue() === '2' && await page.locator('#world-environment').innerText() === 'Rain · 夜間 · 無雷電',
      'The single-room shortcut opens the new rain setting without the previous lightning flag');
    await page.locator('#tab-operations').click();
    await roomEnvironment(1).filter({ hasText: '快照已過期' }).waitFor();
    check(await roomEnvironment(1).filter({ hasText: '全館環境待確認' }).isVisible() && await environmentFrame(1).isHidden(),
      'A room-specific override clears its marker and the other room expires independently');
    await climateRoom(1, 'Waiting').waitFor();
    check(await climateRoom(2, 'Superseded').isVisible() && await environmentBatch.getByRole('button').count() === 0,
      'Expired environment evidence removes its shortcut while the original superseded room remains visible');

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
    const enemyResponse = await acceptedEnemies;
    assert.equal(enemyResponse.status(), 200);
    const enemyReceipt = await enemyResponse.json();
    const changedEnemies = await Promise.all(preparing.map(id => api(`/sessions/${id}`)));
    check(enemyDialog.includes('房間 1、2') && enemyDialog.includes('巡邏 · 自動攻擊開啟')
      && changedEnemies.every(session => session.enemies.count === 0 && session.enemies.behavior === 'Patrol' && session.enemies.autoAttack),
      'The console applies behavior and attack across rooms while preserving the original counts');
    const roomEnemies = room => page.locator(`[data-room-venue-enemies="${room}"]`);
    const enemyFrame = room => page.locator(`[data-room-enemies-frame="${room}"]`);
    const enemyBatch = page.locator('#venue-enemy-batch');
    const batchRoom = (room, status) => page.locator(`[data-enemy-batch-room="${room}"][data-enemy-batch-state="${status}"]`);
    const batchReplay = (room, status) => batchRoom(room, status).getByRole('button', { name: '檢視敵軍快照' });
    const batch = (await api('/venue/phase')).latestEnemies;
    assert.equal(batch.requestId, enemyReceipt.requestId);
    assert.deepEqual(batch.sessions.map(row => [row.sessionId, row.roomIds, row.appliedAtSequence, row.targetCount]),
      preparing.map((id, index) => [id, [index + 1], enemyReceipt.sessions.find(row => row.sessionId === id).appliedAtSequence, 0]));
    await roomEnemies(1).filter({ hasText: '全館敵軍策略待確認' }).waitFor();
    await batchRoom(1, 'Waiting').waitFor(); await batchRoom(2, 'Waiting').waitFor();
    check(await batchReplay(1, 'Waiting').count() === 0 && await enemyBatch.locator('p').filter({ hasText: '0 / 2 房已確認' }).isVisible(),
      'Latest strategy receipt retains its original targets and waits for game evidence');
    const enemyViewport = page.viewportSize();
    await page.setViewportSize({ width: 390, height: 900 });
    check(await enemyBatch.evaluate(panel => panel.scrollWidth <= panel.clientWidth), 'The latest enemy batch fits a narrow console');
    await page.setViewportSize(enemyViewport);
    check(await enemyFrame(1).isHidden() && !(await roomEnemies(1).innerText()).includes('本房在場'),
      'A strategy receipt shows the configured target but withholds the population and replay until a fresh game frame');
    await publishUntil(first, changedEnemies[0], () => batchRoom(1, 'Applied').isVisible());
    check(await batchRoom(2, 'Waiting').isVisible() && await enemyBatch.locator('p').filter({ hasText: '1 / 2 房已確認' }).isVisible(),
      'Latest enemy batch counts only the room whose original source has confirmed');
    await publishUntil(first, changedEnemies[0], () => {
      second(changedEnemies[1]);
      return Promise.all([1, 2].map(room => roomEnemies(room).filter({ hasText: '全館敵軍策略已套用' }).isVisible())).then(rows => rows.every(Boolean));
    });
    check(true, 'Enemy policy is confirmed only by both original game sources');
    const patrol = await openSetting('enemies', 1, preparing[0], batchReplay(1, 'Applied'));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${patrol} 格的敵軍快照` }).waitFor();
    const patrolFrame = await api(`/sessions/${preparing[0]}/world/frames/${patrol}`);
    check(patrolFrame.packet.observedSequence >= enemyReceipt.sessions.find(row => row.sessionId === preparing[0]).appliedAtSequence
      && await page.locator('#world-room').inputValue() === '1' && await page.locator('#world-camera').inputValue() === 'top'
      && (await page.locator('#world-enemy-policy').innerText()).endsWith('巡邏 · 自動攻擊開啟'),
      'The enemy shortcut opens the exact venue strategy frame in the original room');
    await page.locator('#tab-operations').click();
    const worldView = page.locator('#world-view'), recording = page.locator('#world-recording');
    const playerCanvas = page.locator('#world-canvas');
    const openedLive = page.waitForRequest(request => new URL(request.url()).pathname === `/api/sessions/${preparing[1]}/world/watch`);
    await page.locator('[data-watch-room="2"]').click();
    assert.equal(new URL((await openedLive).url()).searchParams.get('mode'), 'live');
    await page.locator('#world-canvas[data-sequence]').waitFor();
    check(await worldView.isVisible() && await recording.inputValue() === preparing[1]
      && await page.locator('#world-room').inputValue() === '2' && await page.locator('#world-camera').inputValue() === 'top',
      'The room card opens its original live source and focuses the room in the top view');
    await page.locator('#tab-operations').click();
    const localPolicy = await changeEnemies({ count: 2, behavior: 'Advance', autoAttack: false });
    await page.locator('#refresh').click();
    const localEnemies = page.locator('[data-room-enemies="2"]');
    await localEnemies.filter({ hasText: '場次敵軍策略待確認' }).waitFor();
    await roomEnemies(1).waitFor();
    await batchRoom(2, 'Superseded').waitFor();
    check(await batchReplay(2, 'Superseded').count() === 0 && await batchRoom(2, 'Superseded').filter({ hasText: '全場目標 0 名' }).isVisible(),
      'A room override retains its old command and count while removing the batch replay shortcut');
    check(await roomEnemies(2).isHidden() && await enemyFrame(2).isHidden(),
      'The single-room override clears only its own venue marker and withholds its old frame');
    const npc = { id: randomUUID(), roomId: 2, health: 100, feet: { x: -14, y: 0, z: 3 } };
    const publishAdvance = snapshot => second(snapshot, [npc]);
    await publishUntil(publishAdvance, localPolicy.session, () => enemyFrame(2).isVisible());
    const localStatus = (await api('/rooms/readiness', 'GET', undefined, 'Room2')).rooms;
    check(localStatus.length === 1 && localStatus[0].roomId === 2 && localStatus[0].enemies.venue === false
      && localStatus[0].enemies.targetCount === 2 && localStatus[0].enemies.population.present === 1 && localStatus[0].enemies.population.alive === 1
      && (await localEnemies.innerText()).includes('全場目標 2 名 · 本房在場 1 名、存活 1 名'),
      'A valid partial reinforcement separates the configured target from the recorded and living counts');
    await page.route(`**/api/sessions/${preparing[1]}/world/watch?**`, async route => {
      const original = await route.fetch();
      const body = (await original.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
        const value = JSON.parse(raw); value.packet.frame.enemies = [];
        return 'event: frame\ndata: ' + JSON.stringify(value);
      });
      await route.fulfill({ response: original, body });
    }, { times: 1 });
    await publishUntil(publishAdvance, localPolicy.session, () => enemyFrame(2).isVisible());
    await openSetting('enemies', 2, preparing[1]);
    await page.locator('#world-message').filter({ hasText: '回應快照的敵軍或指令序號不同' }).waitFor();
    check(await page.locator('#world-player').isHidden(), 'A frame with a substituted enemy population cannot open the replay');
    await page.locator('#tab-operations').click();
    await publishUntil(publishAdvance, localPolicy.session, () => enemyFrame(2).isVisible());
    const advance = await openSetting('enemies', 2, preparing[1]);
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${advance} 格的敵軍快照` }).waitFor();
    check(await page.locator('#world-room').inputValue() === '2'
      && (await page.locator('#world-enemy-policy').innerText()).endsWith('推進 · 自動攻擊關閉'),
      'The corrected shortcut opens the original single-room advance policy with auto-attack disabled');
    await page.locator('#world-enemy-policy').screenshot({ path: path.join(screenshots, 'venue-enemy-frame-policy.png') });
    await page.locator('#tab-operations').click();
    await localEnemies.filter({ hasText: '快照已過期' }).waitFor();
    check(await enemyFrame(2).isHidden() && !(await localEnemies.innerText()).includes('本房在場'),
      'Expired enemy snapshots clear the actual population and shortcut together');
    await batchRoom(1, 'Waiting').waitFor();
    check(await batchReplay(1, 'Waiting').count() === 0 && await batchRoom(2, 'Superseded').isVisible(),
      'A stale source loses batch confirmation without changing the other room override');

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
    const reportsPath = `/venue/closure/${closure.requestId}/reports.zip`;
    const reportButton = page.locator('#export-venue-reports');
    const reportStatus = page.locator('#venue-report-status');
    const fieldPath = id => `/venue/closure/${id}/field-evidence.zip`;
    const fieldButton = page.locator('#export-venue-field'), fieldStatus = page.locator('#venue-field-status');
    const waitingReport = await api(reportsPath, 'GET', undefined, 'Master', 409);
    await api(reportsPath, 'GET', undefined, 'Room2', 403);
    check(waitingReport.code === 'venue-reports-not-ready' && waitingReport.roomIds.join() === '2'
      && await reportButton.isDisabled() && (await reportStatus.textContent()).includes('房間 2'),
      'Batch export waits for the last combat seal and rejects a room controller');
    const pausedEnding = await api(`/sessions/${preparing[1]}`);
    await api(`/sessions/${pausedEnding.id}/combat-stream/seal`, 'POST', { streamId: pausedEnding.combatStream.streamId, finalSequence: 0 }, 'GameServer');
    await archive(pausedEnding.id).nth(2).filter({ hasText: '已封存' }).waitFor();
    check(await archive(pausedEnding.id).nth(3).textContent() === '等待封存' && await reportButton.isEnabled(),
      'Batch combat export is available while a world replay remains unsealed');
    const waitingField = await api(fieldPath(closure.requestId), 'GET', undefined, 'Master', 409);
    await api(fieldPath(closure.requestId), 'GET', undefined, 'Room2', 403);
    await api(fieldPath(randomUUID()), 'GET', undefined, 'Master', 404);
    check(waitingField.code === 'venue-field-evidence-not-ready' && waitingField.roomIds.join() === '1,2,3'
      && await fieldButton.isDisabled(), 'The private batch field export rejects unready rooms even when the combat ZIP is available');
    await page.locator('#venue-closure').screenshot({ path: path.join(screenshots, 'venue-closure.png') });
    const replacement = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
    active.add(replacement.id);
    await login('Master');
    await archive(ending.id).nth(3).filter({ hasText: '已封存' }).waitFor();
    await batchRoom(1, 'Ended').waitFor(); await batchRoom(2, 'Ended').waitFor();
    check(await enemyBatch.getByRole('button').count() === 0
      && await batchRoom(1, 'Ended').filter({ hasText: `原命令 ${batch.sessions[0].appliedAtSequence}` }).isVisible(),
      'Relogin restores the original ended enemy batch even after the room is reused');
    await climateRoom(1, 'Ended').waitFor(); await climateRoom(2, 'Ended').waitFor();
    check(await environmentBatch.getByRole('button').count() === 0
      && await climateRoom(1, 'Ended').filter({ hasText: `原命令 ${durableBatch.sessions[0].appliedAtSequence}` }).isVisible(),
      'After relogin and room reuse the environment batch still refers only to its original ended sessions');
    await archive(ending.id).last().getByRole('button', { name: '查看場次' }).click();
    await page.waitForFunction(id => document.getElementById('session-select').value === id, ending.id);
    check(await page.locator('#include-ended').isChecked() && (await api(`/sessions/${replacement.id}`)).state === 'Preparing',
      'Reload restores the original archived batch and the table opens that session after the room is reused');
    const readyReplay = (await api('/venue/closure')).batch.sessions;
    const originalReplay = readyReplay.find(row => row.sessionId === ending.id).replay;
    const partialReplay = readyReplay.find(row => row.sessionId === pausedEnding.id).replay;
    const openReplay = id => page.locator(`[data-venue-replay="${id}"]`);
    check(await page.locator('[data-venue-tracking-begin]').count() === 0, 'Ordinary archived sessions retain their replay without a tracking shortcut');
    check(await openReplay(extra.id).count() === 0 && originalReplay.streamId === ending.combatStream.streamId,
      'A no-source room has no replay shortcut and the original closure identifies its actual stream');
    const archiveListRoute = '**/api/world-recordings';
    await page.route(archiveListRoute, async route => {
      const original = await route.fetch();
      const recordings = await original.json();
      await route.fulfill({ response: original, json: recordings.filter(item => item.header.sessionId !== ending.id) });
    });
    await openReplay(ending.id).click();
    await page.locator('#world-message').filter({ hasText: '目前無法讀取原場次的錄製' }).waitFor();
    check(await recording.inputValue() === '' && await page.locator('#world-replay').isDisabled() && !await playerCanvas.isVisible(),
      'When the original recording is missing, the shortcut leaves other available recordings unselected');
    await page.unroute(archiveListRoute);
    await page.locator('#tab-operations').click();
    async function replayRequest(id) {
      const started = page.waitForRequest(request => new URL(request.url()).pathname === `/api/sessions/${id}/world/watch`);
      await openReplay(id).click();
      const query = new URL((await started).url()).searchParams;
      assert.equal(query.get('mode'), 'replay'); assert.equal(query.get('fromFrame'), '1');
      await page.locator('#world-canvas[data-sequence]').waitFor();
      assert.equal(await recording.inputValue(), id);
      return query;
    }
    const partial = await replayRequest(pausedEnding.id);
    check(Number(partial.get('throughFrame')) === partialReplay.throughSequence,
      'A partial shortcut uses the exact original saved boundary from the closure');
    await page.locator('#tab-operations').click();
    const sealed = await replayRequest(ending.id);
    check(!sealed.has('throughFrame') && await page.locator('#world-room').inputValue() === '1'
      && await page.locator('#world-camera').inputValue() === 'top',
      'A sealed shortcut opens the original room in top view after a new session occupies the room');
    await page.locator('#tab-operations').click();
    const reportsUrl = base + '/api' + reportsPath;
    const fetchReports = () => fetch(reportsUrl, { headers: { Authorization: 'Bearer ' + tokens.Master } });
    const downloadEvent = page.waitForEvent('download');
    await reportButton.click();
    const download = await downloadEvent, reportZip = await fs.readFile(await download.path());
    const response = await fetchReports();
    check(response.ok && response.headers.get('cache-control') === 'no-store'
      && download.suggestedFilename() === `vr-command-venue-reports-v1-${closure.requestId}.zip`
      && reportZip.equals(Buffer.from(await response.arrayBuffer())), 'Browser downloads the exact original batch ZIP after room reuse');
    await fs.writeFile(path.join(screenshots, 'venue-reports.zip'), reportZip);
    await page.route(reportsUrl, route => route.fulfill({ status: 200, contentType: 'application/zip-fake', body: 'fixture' }));
    await reportButton.click();
    await reportStatus.filter({ hasText: '報表格式不符' }).waitFor();
    check(await reportButton.isEnabled(), 'An invalid ZIP media type reports an error and releases the download button');
    await page.unroute(reportsUrl);
    const archiveRoute = '**/api/venue/closure';
    await page.route(archiveRoute, request => request.fulfill({ status: 503 }));
    await page.locator('#refresh').click();
    await page.locator('#venue-closure-summary').filter({ hasText: '暫時無法確認' }).waitFor();
    check(await table.isHidden() && !await reportButton.isVisible(), 'A failed closure read removes the previous seal and download display');
    await page.unroute(archiveRoute);
    const replacementEnd = (await api('/venue/phase')).end;
    const nextBatch = await api('/venue/phase', 'POST', { action: 'End', targets: replacementEnd }, 'Master', 200, undefined, randomUUID());
    active.delete(replacement.id);
    await page.locator('#refresh').click();
    await archive(replacement.id).first().waitFor();
    const oldResponse = await fetchReports();
    const nextDownload = page.waitForEvent('download');
    await reportButton.click();
    check(oldResponse.ok && reportZip.equals(Buffer.from(await oldResponse.arrayBuffer()))
      && (await nextDownload).suggestedFilename() === `vr-command-venue-reports-v1-${nextBatch.requestId}.zip`,
      'A new closure changes the browser download while the original batch URL stays byte-identical');

    await api('/venue/closure/history', 'GET', undefined, 'Room2', 403);
    await api(`/venue/closure/${closure.requestId}`, 'GET', undefined, 'Room2', 403);
    const one = await api('/venue/closure/history?limit=1');
    const older = await api(`/venue/closure/history?limit=1&before=${one.nextBefore}`);
    check(one.batches[0].requestId === nextBatch.requestId && older.batches[0].requestId === closure.requestId && older.nextBefore === null,
      'Venue history returns an exclusive cursor from the newest original batch');
    let evidenceBatch;
    for (let i = 0; i < 19; i++) {
      const synthetic = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [4] }, 'Master', 201);
      active.add(synthetic.id);
      const publish = i === 0 ? await start(synthetic.id, 4, true) : null;
      const preview = (await api('/venue/phase')).end;
      const batch = await api('/venue/phase', 'POST', { action: 'End', targets: preview }, 'Master', 200, undefined, randomUUID());
      active.delete(synthetic.id);
      if (publish) {
        const final = await api(`/sessions/${synthetic.id}`);
        const streamId = final.combatStream.streamId;
        publish(final);
        await api(`/sessions/${synthetic.id}/combat-stream/seal`, 'POST', { streamId, finalSequence: 0 }, 'GameServer');
        publish.seal();
        const unavailable = await api(fieldPath(batch.requestId), 'GET', undefined, 'Master', 409);
        check(unavailable.roomIds.join() === '4', 'Double-sealed batch evidence still waits for the original endpoint');
        await api(`/sessions/${synthetic.id}/connection-endpoint`, 'PUT',
          { version: 1, streamId, address: '192.168.50.40', port: 7777 }, 'GameServer');
        evidenceBatch = { requestId: batch.requestId, sessionId: synthetic.id };
      }
    }
    const picker = page.locator('#venue-closure-batch'), moreBatches = page.locator('#venue-closure-more');
    await page.locator('#venue-closure-load').click();
    await moreBatches.waitFor();
    check(await picker.locator('option').count() === 21 && !await picker.locator(`option[value="${closure.requestId}"]`).count(),
      'The first page stays bounded while the oldest batch remains available through pagination');
    await moreBatches.click();
    await picker.locator(`option[value="${closure.requestId}"]`).waitFor({ state: 'attached' });
    await picker.selectOption(closure.requestId);
    await openReplay(ending.id).waitFor();
    await page.locator('#venue-closure-load').click();
    await page.locator('#venue-history-status').filter({ hasText: '已載入 20 個批次' }).waitFor();
    await page.locator('#refresh').click();
    check(await picker.inputValue() === closure.requestId && await openReplay(ending.id).isVisible()
      && !await archive(replacement.id).first().count(), 'Refreshing the list and session state preserves the selected original batch');
    const historyDownload = page.waitForEvent('download');
    await reportButton.click();
    const historyZip = await historyDownload;
    check(historyZip.suggestedFilename() === `vr-command-venue-reports-v1-${closure.requestId}.zip`
      && reportZip.equals(await fs.readFile(await historyZip.path())), 'The older selection downloads the exact original ZIP');
    await replayRequest(ending.id);
    await page.locator('#tab-operations').click();
    check(await picker.inputValue() === closure.requestId, 'Returning from the older replay preserves its history selection');

    const { requestId: evidenceId, sessionId: originalSession } = evidenceBatch;
    await picker.selectOption(evidenceId);
    await fieldStatus.filter({ hasText: '已可匯出' }).waitFor();
    const auth = { headers: { Authorization: 'Bearer ' + tokens.Master } };
    const privatePath = fieldPath(evidenceId), fieldUrl = base + '/api' + privatePath;
    const batchZip = await fetch(fieldUrl, auth), directZip = await fetch(base + `/api/sessions/${originalSession}/field-evidence.zip`, auth);
    const batchBytes = Buffer.from(await batchZip.arrayBuffer());
    const fieldDownload = page.waitForEvent('download');
    await fieldButton.click();
    const downloadedField = await fieldDownload;
    const fieldFile = path.join(screenshots, 'venue-field-evidence.zip');
    await downloadedField.saveAs(fieldFile);
    assert.equal((await fetch(fieldUrl)).status, 401);
    check(batchZip.ok && directZip.ok && batchZip.headers.get('cache-control') === 'no-store'
      && batchZip.headers.get('content-type') === 'application/zip'
      && batchZip.headers.get('content-disposition').includes(`vr-command-venue-field-v1-${evidenceId}.zip`)
      && downloadedField.suggestedFilename() === `vr-command-venue-field-v1-${evidenceId}.zip`
      && batchBytes.equals(await fs.readFile(fieldFile)), 'The Master downloads the selected archived batch as the exact private API ZIP');
    const unpacked = spawnSync('python', ['-c', `import base64, json, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    assert archive.namelist() == ['closure.json', 'room-04.zip'] and archive.testzip() is None
    print(json.dumps([json.loads(archive.read('closure.json')), base64.b64encode(archive.read('room-04.zip')).decode()], ensure_ascii=True))`,
    fieldFile], { encoding: 'utf8', windowsHide: true, timeout: 6000 });
    assert.equal(unpacked.status, 0, unpacked.stderr);
    const [closureRecord, inner] = JSON.parse(unpacked.stdout);
    assert.deepEqual(closureRecord, await api(`/venue/closure/${evidenceId}`));
    check(Buffer.from(inner, 'base64').equals(Buffer.from(await directZip.arrayBuffer())),
      'Batch evidence contains the exact original closure and the byte-identical individual field ZIP');

    const heldRoute = '**/api' + privatePath;
    let notify, release, finished, lateDownload = false;
    const requested = new Promise(resolve => { notify = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    const done = new Promise(resolve => { finished = resolve; });
    const late = () => { lateDownload = true; };
    const hold = async route => {
      try {
        const response = await route.fetch();
        assert.equal(response.status(), 200); notify(null);
        await gate;
        try { await route.fulfill({ response }); } catch { /* Changing batch aborts this download. */ }
      } catch (error) { notify(error); } finally { finished(); }
    };
    page.on('download', late);
    await page.route(heldRoute, hold);
    try {
      await fieldButton.click();
      const failure = await requested;
      if (failure) throw failure;
      await picker.selectOption('');
      await fieldStatus.filter({ hasText: '缺少開場紀錄' }).waitFor();
    } finally {
      release(); await done; await page.unroute(heldRoute, hold); page.off('download', late);
    }
    check(!lateDownload && await fieldButton.isDisabled(), 'A held field ZIP cannot download after changing to a different batch');
    await login('Room2');
    check(await page.locator('#venue-closure').isHidden() && await fieldButton.isHidden() && await picker.locator('option').count() === 1
      && await enemyBatch.isHidden() && await environmentBatch.isHidden(), 'Switching to room control clears Master-only history and setting batches');
  } finally {
    await page.unroute(route); await page.close();
    for (const id of active) await end(id);
  }
};
