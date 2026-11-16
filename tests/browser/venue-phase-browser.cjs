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
  async function rejectReplayStatistics(button, sessionId, playerId, change, label) {
    const route = url => url.pathname === `/api/sessions/${sessionId}/world/watch` && url.searchParams.get('mode') === 'replay';
    const substituted = async request => {
      const response = await request.fetch();
      let changed = false;
      const body = (await response.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
        const data = JSON.parse(raw);
        const player = data.statistics.find(row => row.playerId === playerId);
        assert.ok(player);
        change(player);
        changed = true;
        return 'event: frame\ndata: ' + JSON.stringify(data);
      });
      assert.ok(changed);
      await request.fulfill({ response, body });
    };
    await page.route(route, substituted, { times: 1 });
    try {
      await button.click();
      await page.waitForFunction(() => document.querySelector('#world-message').textContent.includes('個人封存戰績不同')
        || document.querySelector('#world-review-player-scope').getClientRects().length > 0);
      check((await page.locator('#world-message').textContent()).includes('個人封存戰績不同')
        && await page.locator('#world-review-player-scope').isHidden() && await page.locator('#world-player').isHidden(), label);
    } finally { await page.unroute(route, substituted); }
  }
  async function prepare(id, room, withSource, connected = false, reinforcementVersion = 0) {
    let snapshot = await api(`/sessions/${id}/players`, 'POST', { playerId: randomUUID(), roomId: room, name: 'Venue seat', headset: 'Quest3' });
    let publish;
    if (withSource) {
      const streamId = randomUUID(), origin = 'Simulation', started = Date.now();
      await api(`/sessions/${id}/combat-stream`, 'POST', { streamId, origin }, 'GameServer');
      snapshot = await api(`/sessions/${id}`);
      const header = { sessionId: id, streamId, origin, roomIds: snapshot.roomIds, reinforcementVersion,
        captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00') };
      let sequence = 0, tick = 0;
      const send = message => {
        const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
          input: JSON.stringify({ port: Number(new URL(base).port), route: `/api/sessions/${id}/world/publish`, token: tokens.GameServer,
            messages: [{ type: 'header', payload: header }, message] }) });
        if (result.status !== 0) throw new Error('Venue fixture publication failed: ' + (result.stderr || result.error?.message));
        return JSON.parse(result.stdout);
      };
      publish = (current, enemies = [], { events = [], throughCombatSequence = 0, magazines = new Map() } = {}) => {
        const players = current.players.map(player => {
          const head = { x: (player.roomId - 3) * 14 + player.seat, y: 1.65, z: -3 };
          const rotation = { x: 0, y: 0, z: 0, w: 1 };
          const rig = connected ? { kind: 'Simulated', headRotation: rotation, rightRotation: rotation, leftRotation: rotation,
            right: head, left: head } : { kind: 'None' };
          return { id: player.id, roomId: player.roomId, head, muzzle: head,
            connected, forward: { x: 0, y: 0, z: 1 }, health: 100, magazine: magazines.get(player.id) ?? 30, reserve: 90, rig };
        });
        const { weather, timeOfDay, lightning } = current.environment;
        const { behavior, autoAttack } = current.enemies;
        const visibility = ['Fog', 'Storm'].includes(weather) ? weather : 'Clear';
        const packet = { sequence: ++sequence, observedSequence: current.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
          weather, lightning, throughCombatSequence, events,
          frame: { phase: current.state, tick: current.state === 'Running' ? ++tick : tick,
            night: timeOfDay === 'Night', visibility, behavior, autoAttack, throughSequence: throughCombatSequence, players, enemies } };
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
  async function verifySettingDownload(name, key, requestId) {
    const button = page.locator(`#venue-${name}-batch-download`);
    const response = await page.request.get(base + '/api/venue/phase', { headers: { Authorization: 'Bearer ' + tokens.Master } });
    assert.equal(response.status(), 200);
    const expected = await response.body();
    assert.equal(JSON.parse(expected)[key].requestId, requestId);
    const file = page.waitForEvent('download');
    await button.click();
    const downloaded = await file;
    assert.equal(downloaded.suggestedFilename(), `vr-command-venue-${name}-${requestId}.json`);
    const target = path.join(screenshots, downloaded.suggestedFilename());
    await downloaded.saveAs(target);
    check((await fs.readFile(target)).equals(expected), `The ${name} batch downloads the byte-identical original venue phase response`);
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
    check(await page.locator('[data-resume-room]').count() === 2
      && (await page.locator('[data-resume-room="2"]').innerText()).includes('等待遊戲來源'),
      'The venue Resume preview shows the original target rooms and identifies a missing game source');
    await run(ids[1], 'Resume'); await run(ids[1], 'Pause');
    await page.locator('#refresh').click(); await summary.filter({ hasText: /^可暫停 無 · 可繼續 房間 1$/ }).waitFor();
    const paused = await api(`/sessions/${ids[0]}`);
    const pausePlan = (await api('/venue/phase')).resume.map(({ sessionId, phaseSinceSequence }) => ({ sessionId, phaseSinceSequence }));
    const allowed = () => page.locator('#venue-resume').isEnabled();
    await publishUntil(publish, paused, allowed);
    await roomPhase(2).waitFor({ state: 'hidden' });
    check(await roomPhase(1).filter({ hasText: '全館暫停已套用' }).isVisible(),
      'The original source confirms the venue pause while the later manual pause has no venue marker');
    check(await page.locator('[data-resume-room="1"][data-resume-state="Ready"]').isVisible()
      && await page.locator('[data-resume-room="2"]').count() === 0,
      'A confirmed original pause is marked ready while a later manual pause leaves the preview');
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-resume.png') });
    await roomPhase(1).filter({ hasText: '快照已過期' }).waitFor();
    const declined = await api('/venue/phase', 'POST', { action: 'Resume', targets: pausePlan }, 'Master', 409, undefined, randomUUID());
    check(declined.code === 'venue-pause-not-observed' && declined.roomIds.join() === '1' && await page.locator('#venue-resume').isDisabled(),
      'Expired pause evidence clears the live confirmation and the HTTP API rejects an early Resume');
    check(await page.locator('[data-resume-room="1"][data-resume-state="Stale"]').isVisible(),
      'The room preview withdraws readiness when the original paused frame expires');
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
    const followRow = page.locator(`#world-statistics tr[data-player-id="${subject}"] button`);
    check((await followRow.getAttribute('aria-label')).includes(subjectName) && await followRow.locator('img').count() === 0,
      'Player row follow control uses the accepted name as literal text');
    await followRow.click();
    check(await actorPicker.inputValue() === 'p:' + subject && await view.inputValue() === 'follow',
      'The player statistics row activates its exact follow target');
    const lastTarget = await linkedCanvas.getAttribute('data-camera');
    await api(`/sessions/${linked.id}/players/${subject}`, 'DELETE', undefined, 'Master', 204,
      linkedState.players.find(player => player.id === subject).admissionId);
    linkedState = await api(`/sessions/${linked.id}`);
    linkedPublish(linkedState);
    await view.locator('option[value="follow"]:disabled').waitFor({ state: 'attached' });
    check(await actorPicker.inputValue() === '' && (await choices()).includes('p:' + roomPeer)
      && await view.inputValue() === 'free' && await linkedCanvas.getAttribute('data-camera') === lastTarget && await followRow.isDisabled(),
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
      === ['', subject, roomPeer].sort().join(',') && await openReview.isEnabled() && await page.locator('#open-player-damage').isDisabled(),
      'A sealed linked review includes the removed player in scope while keeping the damage shortcut disabled for zero hits');
    await reportRoom.selectOption('1');
    check(await review.inputValue() === '' && await openReview.isDisabled(), 'Switching rooms clears a previous personal review selection outside the scope');
    await reportRoom.selectOption('2');
    await review.selectOption(subject);
    await rejectReplayStatistics(openReview, linked.id, subject, player => { player.playerId = randomUUID(); },
      'A different archived player at the exact final frame prevents opening the personal replay');
    await page.locator('#tab-operations').click();
    await review.selectOption(subject);
    const [scopedSearch] = await Promise.all([
      page.waitForResponse(response => new URL(response.url()).pathname === `/api/sessions/${linked.id}/world/event-frames`),
      openReview.click()
    ]);
    const searchQuery = new URL(scopedSearch.url()).searchParams;
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
    const beginRoomText = room => beginRoom(room).evaluate(row =>
      [...row.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).map(node => node.textContent).join('').trim());
    const preview = await getBegin();
    const firstReady = await api(`/sessions/${preparing[0]}`);
    const declinedBegin = await api('/venue/phase', 'POST', { action: 'Begin', targets: preview }, 'Master', 409, undefined, randomUUID());
    await page.locator('#refresh').click();
    await publishUntil(first, firstReady, async () =>
      await beginRoom(1).getAttribute('data-begin-state') === 'Ready' && await beginRoom(2).getAttribute('data-begin-state') === 'EmptyRoster');
    check(declinedBegin.code === 'venue-begin-not-ready' && declinedBegin.roomIds.join() === '2' && await beginButton.isDisabled(),
      'A missing roster and source in one room blocks the whole Begin batch in both HTTP and Chromium');
    check(await beginRoomText(1) === '房間 1 · 1 席姿態就緒 · 錄製來源 Simulation'
      && await beginRoomText(2) === '房間 2 · 名冊尚無玩家' && await page.locator('[data-begin-room]').count() === 2,
      'The master sees only the target rooms and can distinguish a ready VR room from an empty independent roster');
    await beginRoom(1).filter({ hasText: '快照已過期' }).waitFor();
    check(await beginButton.isDisabled() && await beginRoom(2).getAttribute('data-begin-state') === 'EmptyRoster',
      'Expired VR evidence clears the ready label while the independent empty-room reason remains');
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-begin-blockers.png') });
    const second = await prepare(preparing[1], 2, true, true, 1);
    const staleBegin = await api('/venue/phase', 'POST', { action: 'Begin', targets: preview }, 'Master', 409, undefined, randomUUID());
    check(staleBegin.code === 'venue-phase-changed' && staleBegin.roomIds.join() === '2'
      && (await api('/sessions')).every(session => session.state === 'Preparing'),
      'Preparing roster and source changes invalidate the previous Begin preview without starting either room');
    let secondReady = await api(`/sessions/${preparing[1]}`);
    await page.locator('#refresh').click();
    await publishUntil(first, firstReady, () => { second(secondReady); return beginButton.isEnabled(); });
    const beginPath = '**/api/venue/phase';
    const conflicts = [];
    const rejectStale = async route => {
      if (route.request().method() !== 'POST') return route.continue();
      secondReady = await api(`/sessions/${preparing[1]}/players`, 'POST', {
        playerId: randomUUID(), roomId: 2, name: 'New seat while confirming', headset: 'Quest3'
      });
      const response = await route.fetch();
      conflicts.push([response.status(), (await response.json()).roomIds]);
      await route.fulfill({ response });
    };
    await page.route(beginPath, rejectStale);
    try {
      await click('begin', '房間 1、2 的 2 個場次');
      await notice.filter({ hasText: '房間 2 的場次狀態已變更，本批命令未套用' }).waitFor();
      check(JSON.stringify(conflicts) === '[[409,[2]]]'
        && (await api('/sessions')).every(session => session.state === 'Preparing'),
        'The rejected confirmation names only the changed room and keeps the whole original batch preparing');
    } finally { await page.unroute(beginPath, rejectStale); }
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
    const originalClimateReplay = (room, state) => climateRoom(room, state).getByRole('button', { name: '查找原環境畫格' });
    const climateEvidence = (id, requestId = climateReceipt.requestId) => `/sessions/${id}/world/venue-environment/${requestId}`;
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
    const unobserved = await api(climateEvidence(preparing[0]));
    await api(climateEvidence(preparing[0]), 'GET', undefined, 'Room2', 403);
    await api(climateEvidence(preparing[0], randomUUID()), 'GET', undefined, 'Master', 404);
    check(unobserved.worldSequence === null, 'Original environment lookup is Master-scoped and returns no frame before the game observes the command');
    await publishUntil(first, changedClimate[0], () => climateReplay(1, 'Applied').isVisible());
    check(await climateRoom(2, 'Waiting').isVisible() && await environmentBatch.getByText('1 / 2 房已確認', { exact: false }).isVisible(),
      'The environment batch confirms each room only after its own source applies the command');
    await publishUntil(first, changedClimate[0], () => {
      second(changedClimate[1]);
      return Promise.all([1, 2].map(room => roomEnvironment(room).filter({ hasText: '全館環境已套用' }).isVisible())).then(rows => rows.every(Boolean));
    });
    check(true, 'Both rooms confirm their own matching environment frames');
    await verifySettingDownload('environment', 'latestEnvironment', climateReceipt.requestId);
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
    const originalRoomTwo = await api(climateEvidence(preparing[1]));
    const firstRoomTwo = (await api(`/sessions/${preparing[1]}/world/frames/${originalRoomTwo.worldSequence}`)).packet;
    const preceding = (await api(`/sessions/${preparing[1]}/world/frames/${originalRoomTwo.worldSequence - 1}`)).packet;
    check(firstRoomTwo.observedSequence === originalRoomTwo.appliedAtSequence && firstRoomTwo.frame.tick > 0
      && preceding.observedSequence < originalRoomTwo.appliedAtSequence,
      'The look-up selects the first active frame at the original environment command sequence');
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
    const priorRoomTwoFrame = await openSetting('environment', 2, preparing[1], originalClimateReplay(2, 'Superseded'));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${priorRoomTwoFrame} 格的環境快照` }).waitFor();
    check(priorRoomTwoFrame === originalRoomTwo.worldSequence && await page.locator('#world-room').inputValue() === '2'
      && await page.locator('#world-environment').innerText() === 'Storm · 夜間 · 雷電啟用',
      'After a room switches to rain, the old batch opens its exact storm frame with the original room scope');
    await page.locator('#tab-operations').click();
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
    check(await climateRoom(2, 'Superseded').isVisible()
      && await environmentBatch.getByRole('button', { name: '檢視環境快照' }).count() === 0,
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
    const originalEnemyReplay = (room, status) => batchRoom(room, status).getByRole('button', { name: '查找原敵軍畫格' });
    const enemyEvidence = (id, requestId = enemyReceipt.requestId) => `/sessions/${id}/world/venue-enemies/${requestId}`;
    const batch = (await api('/venue/phase')).latestEnemies;
    assert.equal(batch.requestId, enemyReceipt.requestId);
    assert.deepEqual(batch.sessions.map(row => [row.sessionId, row.roomIds, row.appliedAtSequence, row.targetCount]),
      preparing.map((id, index) => [id, [index + 1], enemyReceipt.sessions.find(row => row.sessionId === id).appliedAtSequence, 0]));
    await roomEnemies(1).filter({ hasText: '全館敵軍策略待確認' }).waitFor();
    await batchRoom(1, 'Waiting').waitFor(); await batchRoom(2, 'Waiting').waitFor();
    check(await batchReplay(1, 'Waiting').count() === 0 && await enemyBatch.locator('p').filter({ hasText: '0 / 2 房已確認' }).isVisible(),
      'Latest strategy receipt retains its original targets and waits for game evidence');
    const pendingEnemy = await api(enemyEvidence(preparing[0]));
    await api(enemyEvidence(preparing[0]), 'GET', undefined, 'Room2', 403);
    await api(enemyEvidence(preparing[0], climateReceipt.requestId), 'GET', undefined, 'Master', 404);
    check(pendingEnemy.worldSequence === null && !Object.hasOwn(pendingEnemy, 'enemyPopulations'),
      'An enemy batch without its original running frame has no population, and the lookup is Master-scoped');
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
    await verifySettingDownload('enemy', 'latestEnemies', enemyReceipt.requestId);
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
    const originalEnemy = await api(enemyEvidence(preparing[1]));
    const enemyWatch = `**/api/sessions/${preparing[1]}/world/watch?**`;
    await page.route(enemyWatch, async route => {
      const response = await route.fetch();
      const body = (await response.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
        const value = JSON.parse(raw); value.packet.observedSequence++;
        return 'event: frame\ndata: ' + JSON.stringify(value);
      });
      await route.fulfill({ response, body });
    }, { times: 1 });
    await openSetting('enemies', 2, preparing[1], originalEnemyReplay(2, 'Superseded'));
    await page.locator('#world-message').filter({ hasText: '回應快照的敵軍或指令序號不同' }).waitFor();
    check(await page.locator('#world-player').isHidden(), 'A later observed revision cannot substitute for the original enemy frame in replay');
    await page.locator('#tab-operations').click();
    const oldPatrol = await openSetting('enemies', 2, preparing[1], originalEnemyReplay(2, 'Superseded'));
    const originalEnemyMessage = `已停在第 ${oldPatrol} 格的敵軍快照。 本房在場 0 名、存活 0 名。`;
    await page.locator('#world-frame-message').filter({ hasText: originalEnemyMessage }).waitFor();
    check(oldPatrol === originalEnemy.worldSequence && await page.locator('#world-room').inputValue() === '2'
      && (await page.locator('#world-enemy-policy').innerText()).endsWith('巡邏 · 自動攻擊開啟'),
      'After a room changes its policy and population, the old batch opens the original patrol and counts');
    await page.locator('#tab-operations').click();
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
    const debriefRoom = id => page.locator(`[data-venue-debrief-room="${id}"]`);
    const closure = (await api('/venue/closure')).batch;
    const debriefExport = id => `/venue/closure/${id}/debrief-receipts.json`;
    const debriefDetail = (id, room) => `/venue/closure/${id}/rooms/${room}/debrief-receipts`;
    const batchSeats = id => `/venue/closure/${id}/debrief-seats`;
    const showAllSeats = page.locator('#venue-debrief-all');
    const seatPanel = page.locator('#venue-debrief-seats');
    const seatStatus = page.locator('#venue-debrief-seats-status');
    const groupRows = page.locator('#venue-debrief-seat-rows tr');
    const seatReport = (id, room, seat) => `/venue/closure/${id}/rooms/${room}/seats/${seat}/report.csv`;
    const showSeats = room => page.locator(`[data-venue-debrief-seats="${room}"]`);
    const debriefButton = page.locator('#export-venue-debrief');
    await api(debriefExport(closure.requestId), 'GET', undefined, 'Master', 409);
    check(closure.requestId === requests[0].id && requests.length === 2 && JSON.stringify(requests[0]) === JSON.stringify(requests[1])
      && closure.sessions.every((session, index) => session.roomIds.join() === String(index + 1)),
      'Retry preserves the original End request and the closure table keeps the original room order');
    await table.waitFor();
    check(await debriefButton.isVisible() && await debriefButton.isDisabled(),
      'The full receipt file waits for every original session to seal');
    check((await archive(preparing[0]).allTextContents()).slice(2, 4).join() === '等待封存,等待封存'
      && (await archive(extra.id).allTextContents()).slice(2, 4).join() === '沒有遊戲來源,沒有遊戲來源',
      'The archive distinguishes an unsealed source from a preparing room that never had a source');
    check(await debriefRoom(1).textContent() === '等待雙封存' && await debriefRoom(3).textContent() === '沒有遊戲來源',
      'The receipt column distinguishes a waiting source from a room without a game server');
    await api(debriefDetail(closure.requestId, 1), 'GET', undefined, 'Master', 409);
    await api(debriefDetail(closure.requestId, 3), 'GET', undefined, 'Master', 409);
    await api(debriefDetail(closure.requestId, 5), 'GET', undefined, 'Master', 404);
    await api(seatReport(closure.requestId, 1, 1), 'GET', undefined, 'Master', 409);
    check(await showSeats(1).count() === 0 && await showSeats(3).count() === 0,
      'Unsealed or source-free rooms cannot expose a receipt detail');
    assert.deepEqual(await api(batchSeats(closure.requestId)), { version: 1, requestId: closure.requestId, rooms: [] });
    await api(batchSeats(closure.requestId), 'GET', undefined, 'Room1', 403);
    await api(batchSeats(closure.requestId), 'GET', undefined, 'GameServer', 403);
    await api(batchSeats(randomUUID()), 'GET', undefined, 'Master', 404);
    check(await showAllSeats.isHidden(), 'The aggregate requires Master and an original batch with sealed seats before opening in the console');
    const ending = await api(`/sessions/${preparing[0]}`);
    first(ending);
    await api(`/sessions/${ending.id}/combat-stream/seal`, 'POST', { streamId: ending.combatStream.streamId, finalSequence: 0 }, 'GameServer');
    await archive(ending.id).nth(2).filter({ hasText: '已封存' }).waitFor();
    check(await archive(ending.id).nth(3).textContent() === '等待封存', 'A combat seal alone does not mark the world replay sealed');
    first.seal();
    await archive(ending.id).nth(3).filter({ hasText: '已封存' }).waitFor();
    const readyDetail = await api(debriefDetail(closure.requestId, 1) + '?includeScores=true&includePlayerIds=true');
    assert.deepEqual(await api(batchSeats(closure.requestId)), { version: 1, requestId: closure.requestId, rooms: [readyDetail] });
    await showAllSeats.click();
    await seatStatus.filter({ hasText: '房間 2 尚無可核對回條' }).waitFor();
    check(await groupRows.count() === readyDetail.players.length
      && (await groupRows.locator('td:first-child').allTextContents()).every(room => room === '1')
      && await page.locator('#venue-debrief-only-missing').isChecked(),
      'The group shows the sealed independent room and calls out the still-unsealed occupied room');
    await page.locator('#venue-debrief-seats-close').click();
    const reportsPath = `/venue/closure/${closure.requestId}/reports.zip?includeScores=true`;
    const reportButton = page.locator('#export-venue-reports');
    const reportStatus = page.locator('#venue-report-status');
    const fieldPath = id => `/venue/closure/${id}/field-evidence.zip`;
    const fieldReceiptsPath = id => fieldPath(id) + '?includeDebriefReceipts=true';
    const fieldButton = page.locator('#export-venue-field'), fieldStatus = page.locator('#venue-field-status');
    const fieldReceiptsButton = page.locator('#export-venue-field-with-receipts');
    const fieldReceiptsStatus = page.locator('#venue-field-receipt-status');
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
    assert.deepEqual(await api(fieldReceiptsPath(closure.requestId), 'GET', undefined, 'Master', 409), waitingField);
    assert.ok(await fieldReceiptsButton.isDisabled());
    await page.locator('#venue-closure').screenshot({ path: path.join(screenshots, 'venue-closure.png') });
    const replacement = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
    active.add(replacement.id);
    await login('Master');
    await archive(ending.id).nth(3).filter({ hasText: '已封存' }).waitFor();
    await batchRoom(1, 'Ended').waitFor(); await batchRoom(2, 'Ended').waitFor();
    check(await enemyBatch.getByRole('button', { name: '檢視敵軍快照' }).count() === 0
      && await page.locator('#venue-enemy-batch-download').isEnabled()
      && await batchRoom(1, 'Ended').filter({ hasText: `原命令 ${batch.sessions[0].appliedAtSequence}` }).isVisible(),
      'Relogin restores the original ended enemy batch even after the room is reused');
    const originalEndedEnemy = await api(enemyEvidence(ending.id));
    const reopenedEnemy = await openSetting('enemies', 1, ending.id, originalEnemyReplay(1, 'Ended'));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${reopenedEnemy} 格的敵軍快照` }).waitFor();
    check(reopenedEnemy === originalEndedEnemy.worldSequence && await recording.inputValue() === ending.id,
      'The ended batch opens the original enemy frame after room 1 has a new session');
    await page.locator('#tab-operations').click();
    await climateRoom(1, 'Ended').waitFor(); await climateRoom(2, 'Ended').waitFor();
    check(await environmentBatch.getByRole('button', { name: '檢視環境快照' }).count() === 0
      && await page.locator('#venue-environment-batch-download').isEnabled()
      && await climateRoom(1, 'Ended').filter({ hasText: `原命令 ${durableBatch.sessions[0].appliedAtSequence}` }).isVisible(),
      'After relogin and room reuse the environment batch still refers only to its original ended sessions');
    const originalEnded = await api(climateEvidence(ending.id));
    const reopened = await openSetting('environment', 1, ending.id, originalClimateReplay(1, 'Ended'));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${reopened} 格的環境快照` }).waitFor();
    check(reopened === originalEnded.worldSequence && await recording.inputValue() === ending.id,
      'The ended batch opens its original environment frame even after room 1 is assigned to another session');
    await page.locator('#tab-operations').click();
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
    const archiveListRoute = url => url.pathname === '/api/world-recordings/page';
    await page.route(archiveListRoute, async route => {
      const original = await route.fetch();
      const catalog = await original.json();
      const keep = item => item.header.sessionId !== ending.id;
      await route.fulfill({ response: original, json: {
        ...catalog, recordings: catalog.recordings.filter(keep), pinned: catalog.pinned.filter(keep)
      } });
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
    for (let i = 0; i < 31; i++) {
      const historical = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [4] }, 'Master', 201);
      active.add(historical.id);
      await prepare(historical.id, 4, true);
      await end(historical.id);
    }
    const { recordings: newestRecordings, nextBefore: recordingCursor } = await api('/world-recordings/page');
    assert.equal(newestRecordings.length, 30);
    assert.ok(newestRecordings.every(row => row.header.sessionId !== ending.id));
    const directCatalog = page.waitForResponse(response => {
      const url = new URL(response.url());
      return archiveListRoute(url) && url.searchParams.getAll('include').includes(ending.id);
    });
    const sealed = await replayRequest(ending.id);
    check(!sealed.has('throughFrame') && await page.locator('#world-room').inputValue() === '1'
      && await page.locator('#world-camera').inputValue() === 'top',
      'A sealed shortcut opens the original room in top view after a new session occupies the room');
    const directPage = await (await directCatalog).json();
    const olderRecordings = page.locator('#world-older');
    check(directPage.recordings.length === 30 && directPage.nextBefore === recordingCursor
      && directPage.pinned.some(row => row.header.sessionId === ending.id)
      && await recording.locator('option').count() === 30 + directPage.pinned.length,
      'The closure shortcut requests and displays its original recording outside the bounded first page');
    const earlierCatalog = page.waitForResponse(response => {
      const url = new URL(response.url());
      return archiveListRoute(url) && url.searchParams.get('before') === recordingCursor;
    });
    await olderRecordings.click();
    const earlierPage = await (await earlierCatalog).json();
    let loaded = 30 + earlierPage.recordings.length, nextBefore = earlierPage.nextBefore;
    await page.locator('#world-list-status').filter({ hasText: `已載入 ${loaded} 筆錄製` }).waitFor();
    check(earlierPage.recordings.some(row => row.header.sessionId === ending.id)
      && await recording.locator(`option[value="${ending.id}"]`).count() === 1
      && await recording.inputValue() === ending.id && await playerCanvas.isVisible(),
      'Loading older recordings preserves the selected replay and shows the original recording only once');
    while (nextBefore !== null) {
      const cursor = nextBefore;
      const following = page.waitForResponse(response => {
        const url = new URL(response.url());
        return archiveListRoute(url) && url.searchParams.get('before') === cursor;
      });
      await olderRecordings.click();
      const result = await (await following).json();
      assert.notEqual(result.nextBefore, cursor);
      loaded += result.recordings.length;
      nextBefore = result.nextBefore;
      await page.locator('#world-list-status').filter({ hasText: `已載入 ${loaded} 筆錄製` }).waitFor();
    }
    check(await olderRecordings.isHidden() && await recording.locator(`option[value="${ending.id}"]`).count() === 1
      && await recording.inputValue() === ending.id && await playerCanvas.isVisible(),
      'The archive cursor ends without duplicating or deselecting the original replay');
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
    const reportMethods = [];
    await page.route(reportsUrl, async route => {
      reportMethods.push(route.request().method());
      if (route.request().method() !== 'HEAD') return route.continue();
      const original = await route.fetch();
      await route.fulfill({ response: original, headers: { ...original.headers(), 'content-type': 'application/zip-fake' } });
    });
    await reportButton.click();
    await reportStatus.filter({ hasText: '無法核對戰績 ZIP 的原始內容' }).waitFor();
    check(reportMethods.join() === 'HEAD' && await reportButton.isEnabled(),
      'Invalid ZIP metadata prevents the GET and releases the download button');
    await page.unroute(reportsUrl);
    const archiveRoute = url => url.pathname === '/api/venue/closure' && url.searchParams.get('includeScores') === 'true';
    await page.route(archiveRoute, request => request.fulfill({ status: 503 }));
    await page.locator('#refresh').click();
    await page.locator('#venue-closure-summary').filter({ hasText: '暫時無法確認' }).waitFor();
    check(await table.isHidden() && !await reportButton.isVisible() && !await page.locator('#venue-score-table').isVisible(),
      'A failed closure read removes the previous seal, downloads and score display');
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
      if (i === 0) await api(`/sessions/${synthetic.id}/players`, 'POST',
        { playerId: randomUUID(), roomId: 4, name: 'Unconfirmed fixture seat', headset: 'Quest3' });
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
    await debriefRoom(4).filter({ hasText: '已確認 0／2 席 · 2 席未確認' }).waitFor();
    const sessionPath = `/sessions/${originalSession}`;
    const { debriefReceipts: originalReceipts } = await api(sessionPath + '/world?includeDebriefReceipts=true');
    const [acknowledged] = originalReceipts.players;
    const { streamId, throughSequence, finalStreamSequence, worldSequence } = originalReceipts;
    const detailPath = debriefDetail(evidenceId, 4);
    const scoredDetailPath = detailPath + '?includeScores=true';
    const identifiedDetailPath = scoredDetailPath + '&includePlayerIds=true';
    const detailRoute = url => url.pathname === `/api${detailPath}` && url.searchParams.get('includeScores') === 'true'
      && url.searchParams.get('includePlayerIds') === 'true';
    const detailPanel = page.locator('#venue-debrief-seats'), detailStatus = page.locator('#venue-debrief-seats-status');
    const seatRows = page.locator('#venue-debrief-seat-rows tr');
    const activeReplacement = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [4] }, 'Master', 201);
    active.add(activeReplacement.id);
    await api(`/sessions/${activeReplacement.id}/players`, 'POST',
      { playerId: randomUUID(), roomId: 4, name: 'Replacement fixture seat', headset: 'Quest3' });
    await showSeats(4).click();
    await detailStatus.filter({ hasText: '已確認 0／2 席' }).waitFor();
    const beforeReceipt = await api(detailPath);
    const roster = (await api(sessionPath)).players.sort((a, b) => a.seat - b.seat);
    assert.deepEqual(beforeReceipt, { version: 1, requestId: evidenceId, sessionId: originalSession, roomId: 4, streamId,
      throughSequence, finalStreamSequence, worldSequence,
      players: roster.map(player => ({ seat: player.seat + 1, name: player.name, acknowledged: false })) });
    await api(detailPath, 'GET', undefined, 'Room4', 403);
    await api(detailPath, 'GET', undefined, 'GameServer', 403);
    await api(scoredDetailPath, 'GET', undefined, 'Room4', 403);
    await api(scoredDetailPath, 'GET', undefined, 'GameServer', 403);
    await api(identifiedDetailPath, 'GET', undefined, 'Room4', 403);
    await api(identifiedDetailPath, 'GET', undefined, 'GameServer', 403);
    check(await seatRows.count() === 2 && !(await detailPanel.innerText()).includes('Replacement fixture seat')
      && (await fetch(base + '/api' + detailPath, auth)).headers.get('cache-control') === 'no-store',
      'The original archived room exposes only its terminal seats even while a new room roster uses the same room');
    const finalScore = { ammoUsed: 0, shotsHit: 0, kills: 0, hitsReceived: 0, damageTaken: 0, accuracyPercent: 0, health: 100 };
    const scored = await fetch(base + '/api' + scoredDetailPath, auth);
    assert.deepEqual(await scored.json(), { ...beforeReceipt, players: beforeReceipt.players.map(row => ({ ...row, score: finalScore })) });
    assert.deepEqual(await api(identifiedDetailPath), { ...beforeReceipt, players: beforeReceipt.players.map((row, index) =>
      ({ ...row, score: finalScore, playerId: roster[index].id })) });
    check(scored.headers.get('cache-control') === 'no-store'
      && (await seatRows.evaluateAll(rows => rows.map(row => [...row.cells].slice(4).map(cell => cell.textContent).join('|')))).join(';')
        === '0|0|0|0|0|0%|100;0|0|0|0|0|0%|100',
      'The opted-in receipt includes the original final score of both unconfirmed seats and the browser renders every metric');
    const brokenScore = async route => {
      const response = await route.fetch();
      const original = await response.json();
      original.players[0].score.ammoUsed = -1;
      await route.fulfill({ response, json: original });
    };
    await page.route(detailRoute, brokenScore);
    try {
      await page.locator('#venue-debrief-seats-refresh').click();
      await detailStatus.filter({ hasText: '暫時無法確認原席位回條' }).waitFor();
      check(await seatRows.count() === 0, 'An invalid score clears the table without keeping prior values');
    } finally { await page.unroute(detailRoute, brokenScore); }
    const repeatedPlayer = async route => {
      const response = await route.fetch();
      const body = await response.json();
      body.players[1].playerId = body.players[0].playerId;
      await route.fulfill({ response, json: body });
    };
    await page.route(detailRoute, repeatedPlayer);
    try {
      await page.locator('#venue-debrief-seats-refresh').click();
      await detailStatus.filter({ hasText: '暫時無法確認原席位回條' }).waitFor();
      check(await page.locator('[data-venue-debrief-replay]').count() === 0,
        'Repeated player identities cannot expose a seat replay action');
    } finally { await page.unroute(detailRoute, repeatedPlayer); }
    await api(sessionPath + '/debrief-receipts', 'POST', { streamId, throughSequence, finalStreamSequence, worldSequence,
      players: [{ playerId: acknowledged.playerId, admissionId: acknowledged.admissionId, roomId: 4 }] }, 'GameServer', 204);
    const closurePath = '/venue/closure/' + evidenceId;
    const receiptsPath = closurePath + '?includeDebriefReceipts=true';
    const { debriefReceipts } = await api(receiptsPath);
    assert.deepEqual(debriefReceipts, { requestId: evidenceId, rooms: [
      { sessionId: originalSession, roomId: 4, rosterCount: 2, confirmedCount: 1 }] });
    assert.equal(Object.hasOwn(await api(closurePath), 'debriefReceipts'), false);
    await api(receiptsPath, 'GET', undefined, 'Room4', 403);
    await debriefRoom(4).filter({ hasText: '已確認 1／2 席 · 1 席未確認' }).waitFor();
    await fieldReceiptsStatus.filter({ hasText: '等待房間 4' }).waitFor();
    const pendingReceipts = await api(fieldReceiptsPath(evidenceId), 'GET', undefined, 'Master', 409);
    check(pendingReceipts.code === 'venue-field-receipts-not-confirmed' && pendingReceipts.roomIds.join() === '4'
      && await fieldReceiptsButton.isDisabled() && await fieldButton.isEnabled(),
      'One pending original receipt blocks only the combined field ZIP');
    await api(fieldReceiptsPath(evidenceId), 'GET', undefined, 'Room4', 403);
    await api(fieldReceiptsPath(evidenceId), 'GET', undefined, 'GameServer', 403);
    await detailStatus.filter({ hasText: '已確認 1／2 席' }).waitFor();
    check((await seatRows.evaluateAll(rows => rows.map(row => [...row.cells].slice(0, 3).map(cell => cell.textContent).join('')))).join('|')
      === roster.map(player => `${player.seat + 1}${player.name}`
      + (player.admissionId === acknowledged.admissionId ? '已確認' : '未確認')).join('|'),
      'A late acknowledgement updates the open original room without switching batches');
    await page.locator('#venue-debrief-only-missing').check();
    check(await seatRows.count() === 1 && (await seatRows.first().innerText()).includes('未確認')
      && await seatRows.first().locator('td').last().innerText() === '100',
      'The receipt filter leaves only the exact unconfirmed seat');
    const missing = roster.find(player => player.admissionId !== acknowledged.admissionId);
    const reportPath = seatReport(evidenceId, 4, missing.seat + 1), csvRoute = '**/api' + reportPath;
    const csvButton = page.locator(`[data-venue-debrief-csv="${missing.seat + 1}"]`);
    const csvStatus = page.locator('#venue-debrief-csv-status');
    const direct = await fetch(base + `/api/sessions/${originalSession}/players/${missing.id}/report.csv`, auth);
    const exactCsv = Buffer.from(await direct.arrayBuffer());
    assert(direct.ok);
    await api(reportPath, 'GET', undefined, 'Room4', 403);
    await api(reportPath, 'GET', undefined, 'GameServer', 403);
    await api(seatReport(evidenceId, 4, 5), 'GET', undefined, 'Master', 404);
    await api(seatReport(evidenceId, 1, 1), 'GET', undefined, 'Master', 404);
    const csvResponse = page.waitForResponse(csvRoute), csvDownload = page.waitForEvent('download');
    await csvButton.click();
    const personal = await csvDownload;
    check((await csvResponse).headers()['cache-control'] === 'no-store'
      && personal.suggestedFilename() === `vr-command-report-v1-${originalSession}-player-${missing.id}.csv`
      && exactCsv.equals(await fs.readFile(await personal.path())),
      'The unconfirmed archived seat downloads the original personal CSV even after the room has been reused');
    check((await api(detailPath)).players.find(player => player.seat === missing.seat + 1)?.acknowledged === false,
      'Downloading the personal CSV leaves the original acknowledgement unchanged');
    const foreignCsv = async route => {
      const response = await route.fetch();
      await route.fulfill({ response, headers: { ...response.headers(), 'content-disposition':
        `attachment; filename=vr-command-report-v1-${activeReplacement.id}-player-${missing.id}.csv` } });
    };
    await page.route(csvRoute, foreignCsv);
    let unexpectedCsv = 0;
    const unexpected = () => { unexpectedCsv++; };
    page.on('download', unexpected);
    try {
      await csvButton.click();
      await csvStatus.filter({ hasText: '暫時無法下載原封存戰績' }).waitFor();
      check(unexpectedCsv === 0 && await csvButton.isEnabled(), 'A substituted session filename is rejected and the exact seat can retry');
    } finally { await page.unroute(csvRoute, foreignCsv); page.off('download', unexpected); }
    const otherPlayerCsv = async route => {
      const response = await route.fetch();
      await route.fulfill({ response, headers: { ...response.headers(), 'content-disposition':
        `attachment; filename=vr-command-report-v1-${originalSession}-player-${acknowledged.playerId}.csv` } });
    };
    await page.route(csvRoute, otherPlayerCsv); page.on('download', unexpected);
    try {
      await csvButton.click();
      await csvStatus.filter({ hasText: '暫時無法下載原封存戰績' }).waitFor();
      check(unexpectedCsv === 0 && await csvButton.isEnabled(), 'A different player CSV from the same archive is refused');
    } finally { await page.unroute(csvRoute, otherPlayerCsv); page.off('download', unexpected); }
    const otherSeat = await fetch(base + `/api/sessions/${originalSession}/players/${acknowledged.playerId}/report.csv`, auth);
    assert(otherSeat.ok);
    const otherSeatBytes = Buffer.from(await otherSeat.arrayBuffer());
    const originalText = exactCsv.toString('utf8');
    const changedBoundary = originalText.replace(`,"${streamId}",`, `,"${randomUUID()}",`);
    const changedScore = originalText.replace(/,"100"\r\n$/, ',"99"\r\n');
    assert.notEqual(changedBoundary, originalText);
    assert.notEqual(changedScore, originalText);
    for (const [body, reason] of [[otherSeatBytes, 'player'], [changedBoundary, 'source'], [changedScore, 'score']]) {
      const substitute = async route => { const response = await route.fetch(); await route.fulfill({ response, body }); };
      await page.route(csvRoute, substitute); page.on('download', unexpected);
      try {
        await csvButton.click();
        await csvStatus.filter({ hasText: '暫時無法下載原封存戰績' }).waitFor();
        check(unexpectedCsv === 0 && await csvButton.isEnabled(),
          `The original filename cannot authorize a substituted ${reason} in an archived seat CSV`);
      } finally { await page.unroute(csvRoute, substitute); page.off('download', unexpected); }
    }
    const retriedCsv = page.waitForEvent('download');
    await csvButton.click();
    const retriedSeat = await retriedCsv;
    check(exactCsv.equals(await fs.readFile(await retriedSeat.path())), 'Retry after CSV content mismatches downloads the original sealed seat');
    await retriedSeat.delete();
    await page.setViewportSize({ width: 390, height: 844 });
    check(await detailPanel.evaluate(panel => panel.scrollWidth <= panel.clientWidth + 1), 'The receipt detail fits the mobile console');
    await page.setViewportSize({ width: 1440, height: 1080 });
    await detailPanel.screenshot({ path: path.join(screenshots, 'venue-debrief-seats.png') });
    const worldPath = `/api/sessions/${originalSession}/world`;
    const replaySeat = page.locator(`[data-venue-debrief-replay="${missing.seat + 1}"]`);
    await rejectReplayStatistics(replaySeat, originalSession, missing.id, player => { player.roomId = 5; },
      'A changed player room at the sealed frame prevents opening the seat replay');
    await page.locator('#tab-operations').click();
    await showSeats(4).click();
    await detailStatus.filter({ hasText: '已確認 1／2 席' }).waitFor();
    const watchSeat = page.waitForRequest(request => new URL(request.url()).pathname === worldPath + '/watch');
    const findSeat = page.waitForResponse(response => new URL(response.url()).pathname === worldPath + '/event-frames');
    await replaySeat.click();
    const watch = new URL((await watchSeat).url()).searchParams;
    const search = await findSeat;
    const personalFrames = await search.json();
    check(watch.get('mode') === 'replay' && watch.get('fromFrame') === String(worldSequence)
      && personalFrames.playerId === missing.id && new URL(search.url()).searchParams.get('roomId') === '4'
      && personalFrames.throughFrame === worldSequence
      && personalFrames.streamId === streamId && await detailPanel.isHidden()
      && await page.locator('#world-recording').inputValue() === originalSession && await page.locator('#world-room').inputValue() === '4'
      && (await page.locator('#world-review-player-name').innerText()).includes(missing.id.slice(0, 8)),
      'The unconfirmed seat opens its original scoped replay even after the room has been reused');
    await page.locator('#tab-operations').click();
    await showSeats(4).click();
    await detailStatus.filter({ hasText: '已確認 1／2 席' }).waitFor();
    let releaseCsv, finishCsv, startedCsv = false;
    const csvGate = new Promise(resolve => { releaseCsv = resolve; });
    const csvDone = new Promise(resolve => { finishCsv = resolve; });
    const holdCsv = async route => {
      startedCsv = true;
      try {
        const response = await route.fetch();
        await csvGate;
        await route.fulfill({ response });
      } catch { /* Changing batch aborts the original download. */ }
      finally { finishCsv(); }
    };
    await page.route(csvRoute, holdCsv); page.on('download', unexpected);
    try {
      const request = page.waitForRequest(csvRoute);
      await csvButton.click(); await request;
      await picker.selectOption(closure.requestId);
      await detailPanel.waitFor({ state: 'hidden' });
    } finally {
      releaseCsv(); if (startedCsv) await csvDone;
      await page.unroute(csvRoute, holdCsv); page.off('download', unexpected);
    }
    await picker.selectOption(evidenceId);
    await showSeats(4).click();
    await detailStatus.filter({ hasText: '已確認 1／2 席' }).waitFor();
    check(unexpectedCsv === 0 && await csvStatus.textContent() === '',
      'A held personal CSV cannot download after changing the batch');
    const foreignDetail = async route => {
      const response = await route.fetch();
      await route.fulfill({ response, json: { ...await response.json(), roomId: 3 } });
    };
    await page.route(detailRoute, foreignDetail);
    try {
      await page.locator('#venue-debrief-seats-refresh').click();
      await detailStatus.filter({ hasText: '暫時無法確認原席位回條' }).waitFor();
      check(await seatRows.count() === 0, 'A response for another room removes all previous detail rows');
    } finally { await page.unroute(detailRoute, foreignDetail); }
    let releaseDetail, finishDetail, startedDetail = false;
    const detailGate = new Promise(resolve => { releaseDetail = resolve; });
    const detailDone = new Promise(resolve => { finishDetail = resolve; });
    const holdDetail = async route => {
      startedDetail = true;
      try {
        const response = await route.fetch();
        await detailGate;
        await route.fulfill({ response });
      } catch { /* Changing batch aborts the original request. */ }
      finally { finishDetail(); }
    };
    await page.route(detailRoute, holdDetail);
    try {
      const request = page.waitForRequest(request => detailRoute(new URL(request.url())));
      await page.locator('#venue-debrief-seats-refresh').click(); await request;
      await picker.selectOption(closure.requestId);
      await detailPanel.waitFor({ state: 'hidden' });
    } finally { releaseDetail(); if (startedDetail) await detailDone; await page.unroute(detailRoute, holdDetail); }
    await picker.selectOption(evidenceId);
    await showSeats(4).waitFor();
    check(await detailPanel.isHidden() && await seatRows.count() === 0, 'A held old-batch receipt cannot reopen the detail after switching batches');
    const receiptUrl = base + '/api' + debriefExport(evidenceId);
    const receiptResponse = await fetch(receiptUrl, auth);
    const bytes = Buffer.from(await receiptResponse.arrayBuffer());
    const snapshot = JSON.parse(bytes);
    assert.deepEqual(snapshot, { version: 1, requestId: evidenceId, sessions: [{ sessionId: originalSession, streamId,
      throughSequence, finalStreamSequence, worldSequence, players: originalReceipts.players.map(({ playerId, admissionId, roomId }) =>
        ({ playerId, admissionId, roomId, acknowledged: admissionId === acknowledged.admissionId })) }] });
    await api(debriefExport(evidenceId), 'GET', undefined, 'Room4', 403);
    await api(debriefExport(randomUUID()), 'GET', undefined, 'Master', 404);
    const receiptDownload = page.waitForEvent('download');
    await debriefButton.click();
    const downloadedReceipts = await receiptDownload;
    check(receiptResponse.ok && receiptResponse.headers.get('cache-control') === 'no-store'
      && downloadedReceipts.suggestedFilename() === `vr-command-venue-debrief-receipts-v1-${evidenceId}.json`
      && bytes.equals(await fs.readFile(await downloadedReceipts.path())),
      'The Master saves the exact selected batch receipt file including an unconfirmed admission');
    await page.locator('#venue-debrief-actions').screenshot({ path: path.join(screenshots, 'venue-debrief-export.png') });
    check(batchBytes.equals(Buffer.from(await (await fetch(fieldUrl, auth)).arrayBuffer())),
      'A late receipt updates only the original historical room count without changing its private evidence ZIP');
    await table.screenshot({ path: path.join(screenshots, 'venue-debrief-partial.png') });
    const selectedClosure = url => url.pathname === '/api' + closurePath && url.searchParams.get('includeDebriefReceipts') === 'true';
    await page.route(selectedClosure, async route => {
      const response = await route.fetch();
      const body = await response.json();
      body.debriefReceipts.requestId = closure.requestId;
      await route.fulfill({ response, json: body });
    });
    try {
      await page.locator('#refresh').click();
      await debriefRoom(4).filter({ hasText: '回條狀態未取得' }).waitFor();
      check(await fieldButton.isEnabled(), 'A foreign receipt batch is hidden while the original sealed export stays available');
    } finally { await page.unroute(selectedClosure); }
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

    const [, lastPlayer] = originalReceipts.players;
    await api(sessionPath + '/debrief-receipts', 'POST', { streamId, throughSequence, finalStreamSequence, worldSequence,
      players: [{ playerId: lastPlayer.playerId, admissionId: lastPlayer.admissionId, roomId: 4 }] }, 'GameServer', 204);
    await page.waitForFunction(() => !document.getElementById('export-venue-field-with-receipts').disabled);
    const combinedResponse = await fetch(base + '/api' + fieldReceiptsPath(evidenceId), auth);
    const finalReceipt = await fetch(receiptUrl, auth);
    const combinedDownload = page.waitForEvent('download');
    await fieldReceiptsButton.click();
    const downloadedCombined = await combinedDownload;
    const combinedFile = path.join(screenshots, 'venue-field-with-receipts.zip');
    await downloadedCombined.saveAs(combinedFile);
    const combinedRead = spawnSync('python', ['-c', `import base64, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as original, zipfile.ZipFile(sys.argv[2]) as combined:
    assert combined.namelist() == original.namelist() + ['debrief-receipts.json'] and combined.testzip() is None
    assert all(combined.read(name) == original.read(name) for name in original.namelist())
    print(base64.b64encode(combined.read('debrief-receipts.json')).decode())`, fieldFile, combinedFile],
    { encoding: 'utf8', windowsHide: true, timeout: 6000 });
    assert.equal(combinedRead.status, 0, combinedRead.stderr);
    const receiptBytes = Buffer.from(combinedRead.stdout.trim(), 'base64');
    check(combinedResponse.ok && combinedResponse.headers.get('cache-control') === 'no-store'
      && downloadedCombined.suggestedFilename() === `vr-command-venue-field-with-receipts-v1-${evidenceId}.zip`
      && Buffer.from(await combinedResponse.arrayBuffer()).equals(await fs.readFile(combinedFile))
      && receiptBytes.equals(Buffer.from(await finalReceipt.arrayBuffer()))
      && JSON.parse(receiptBytes).sessions[0].players.every(player => player.acknowledged),
      'Late receipt enables the historical batch combined ZIP with unchanged original members and exact final receipt bytes');

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
      && await enemyBatch.isHidden() && await environmentBatch.isHidden() && await showAllSeats.isHidden()
      && await page.locator('#venue-enemy-batch-download').isDisabled() && await page.locator('#venue-environment-batch-download').isDisabled(),
      'Switching to room control clears Master-only history, setting batches and their downloads');

    for (const id of active) await end(id);
    const combined = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] }, 'Master', 201);
    active.add(combined.id);
    const roomTwo = randomUUID();
    await api(`/sessions/${combined.id}/players`, 'POST', { playerId: roomTwo, roomId: 2, name: '第二房席位', headset: 'Quest3' });
    const combinedPublish = await prepare(combined.id, 1, true, false, 1);
    await run(combined.id, 'Begin');
    const setCombinedEnvironment = async () => api('/venue/phase', 'POST', {
      action: 'SetEnvironment', targets: await climateTargets(), environment: climate
    }, 'Master', 200, undefined, randomUUID());
    const skippedEnvironment = await setCombinedEnvironment();
    const nextEnvironment = await setCombinedEnvironment();
    combinedPublish(await api(`/sessions/${combined.id}`));
    const skippedFrame = await api(climateEvidence(combined.id, skippedEnvironment.requestId));
    const nextFrame = await api(climateEvidence(combined.id, nextEnvironment.requestId));
    check(skippedFrame.worldSequence === null && nextFrame.worldSequence > 0 && nextFrame.roomIds.join() === '1,2,3,4,5',
      'A later identical environment frame cannot stand in for an earlier command in a linked venue');
    await api(`/sessions/${combined.id}/commands`, 'POST', { commandId: randomUUID(), action: 'SetEnemies',
      enemies: { count: 6, behavior: 'Hold', autoAttack: false } });
    const setCombinedEnemies = async () => api('/venue/phase', 'POST', {
      action: 'SetEnemies', enemyPolicy: policy,
      targets: (await api('/venue/phase')).enemies.map(({ sessionId, phaseSinceSequence, enemiesSinceSequence, roomEnemiesSinceSequence }) =>
        ({ sessionId, phaseSinceSequence, enemiesSinceSequence, roomEnemiesSinceSequence }))
    }, 'Master', 200, undefined, randomUUID());
    const skippedEnemy = await setCombinedEnemies();
    const nextEnemy = await setCombinedEnemies();
    const combinedEnemies = [1, 1, 2].map((roomId, index) => ({
      id: randomUUID(), roomId, health: 100, feet: { x: (roomId - 3) * 14 + index, y: 0, z: 3 }
    }));
    combinedPublish(await api(`/sessions/${combined.id}`), combinedEnemies);
    const skippedEnemyFrame = await api(enemyEvidence(combined.id, skippedEnemy.requestId));
    const nextEnemyFrame = await api(enemyEvidence(combined.id, nextEnemy.requestId));
    check(skippedEnemyFrame.worldSequence === null && nextEnemyFrame.worldSequence > 0
      && nextEnemyFrame.enemyPopulations.map(row => `${row.roomId}:${row.present}/${row.alive}`).join() === '1:2/2,2:1/1,3:0/0,4:0/0,5:0/0',
      'A linked historical lookup keeps the exact revision and each room population in its shared recording');
    const combinedEnd = (await api('/venue/phase')).end;
    const originalBatch = await api('/venue/phase', 'POST', { action: 'End', targets: combinedEnd }, 'Master', 200, undefined, randomUUID());
    active.delete(combined.id);
    const combinedPath = `/sessions/${combined.id}`;
    const finalCombined = await api(combinedPath);
    combinedPublish(finalCombined, combinedEnemies);
    await api(combinedPath + '/combat-stream/seal', 'POST', { streamId: finalCombined.combatStream.streamId, finalSequence: 0 }, 'GameServer');
    combinedPublish.seal();
    await login('Master');
    await showAllSeats.click();
    await seatStatus.filter({ hasText: '已確認 0／2 席' }).waitFor();
    check((await groupRows.locator('td:first-child').allTextContents()).join() === '1,2'
      && (await api(batchSeats(originalBatch.requestId))).rooms.every(room => room.sessionId === combined.id),
      'The linked group shows the original shared recording as two distinct occupied rooms');
    const groupRoute = '**/api' + batchSeats(originalBatch.requestId);
    const foreignRoomSource = async route => {
      const response = await route.fetch();
      const body = await response.json();
      body.rooms[1].streamId = randomUUID();
      await route.fulfill({ response, json: body });
    };
    await page.route(groupRoute, foreignRoomSource);
    try {
      await page.locator('#venue-debrief-seats-refresh').click();
      await seatStatus.filter({ hasText: '暫時無法確認原席位回條' }).waitFor();
      check(await groupRows.count() === 0, 'A substituted room stream clears the aggregate and its seat actions');
    } finally { await page.unroute(groupRoute, foreignRoomSource); }
    const originalView = (await api(combinedPath + '/world?includeDebriefReceipts=true')).debriefReceipts;
    const roomOne = originalView.players.find(player => player.roomId === 1);
    await api(combinedPath + '/debrief-receipts', 'POST', { ...originalView,
      players: [{ playerId: roomOne.playerId, admissionId: roomOne.admissionId, roomId: roomOne.roomId }] }, 'GameServer', 204);
    await seatStatus.filter({ hasText: '已確認 1／2 席' }).waitFor();
    check(await groupRows.count() === 1 && await groupRows.first().locator('td').first().textContent() === '2',
      'A late acknowledgement removes only its original seat from the open whole-venue filter');
    const groupDownload = page.waitForEvent('download');
    await seatPanel.getByRole('button', { name: '下載房間 2 第 1 席個人戰績 CSV' }).click();
    const seatFile = await groupDownload;
    const roomTwoCsv = await fetch(base + '/api' + combinedPath + `/players/${roomTwo}/report.csv`, auth);
    check(seatFile.suggestedFilename() === `vr-command-report-v1-${combined.id}-player-${roomTwo}.csv`
      && (await fs.readFile(await seatFile.path())).equals(Buffer.from(await roomTwoCsv.arrayBuffer())),
      'The group downloads the byte-identical original room and player CSV even when seat numbers repeat');
    await seatPanel.screenshot({ path: path.join(screenshots, 'venue-debrief-all.png') });
    await seatPanel.getByRole('button', { name: '開啟房間 2 第 1 席個人回放' }).click();
    await page.locator('#world-review-player-scope').waitFor();
    check(await recording.inputValue() === combined.id && await page.locator('#world-room').inputValue() === '2',
      'The group opens the original scoped replay for the selected seat');

    for (const mode of ['Independent', 'Linked']) {
      const rooms = [1, 2, 3, 4, 5];
      const groups = mode === 'Independent' ? rooms.map(room => [room]) : [rooms];
      const sources = [];
      for (const roomIds of groups) {
        const session = await api('/sessions', 'POST', { missionId: mission.id, mode, roomIds }, 'Master', 201);
        const sessionPath = `/sessions/${session.id}`;
        active.add(session.id);
        for (const roomId of roomIds.slice(1)) {
          await api(sessionPath + '/players', 'POST', { playerId: randomUUID(), roomId, name: 'Remaining seat', headset: 'Quest3' });
        }
        const publish = await start(session.id, roomIds[0], true);
        const running = await api(sessionPath);
        publish(running);
        sources.push({ sessionPath, publish, running });
      }
      const first = sources[0];
      const departed = first.running.players.find(player => player.roomId === 1);
      const eventId = randomUUID(), shotId = randomUUID();
      await api(first.sessionPath + '/combat-stream/reports', 'POST', { streamId: first.running.combatStream.streamId,
        streamSequence: 1, observedSequence: first.running.sequence,
        report: { reportId: eventId, shotId, kind: 'ShotFired', origin: 'Simulation', playerId: departed.id } }, 'GameServer');
      first.publish(await api(first.sessionPath), [], { throughCombatSequence: 1, magazines: new Map([[departed.id, 29]]), events: [{ eventId, shotId, kind: 'ShotFired',
        playerId: departed.id, sequence: 1, tick: 2, hasRay: true, origin: { x: -28 + departed.seat, y: 1.65, z: -3 },
        direction: { x: 0, y: 0, z: 1 }, hit: 'Miss', distance: 20 }] });
      await api(first.sessionPath + '/players/' + departed.id, 'DELETE', undefined, 'Master', 204, departed.admissionId);
      const targets = (await api('/venue/phase')).end;
      const batch = await api('/venue/phase', 'POST', { action: 'End', targets }, 'Master', 200, undefined, randomUUID());
      const departurePath = `/venue/closure/${batch.requestId}/sessions/${first.running.id}/departed-players`;
      const reportPath = `/sessions/${first.running.id}/players/${departed.id}/report.csv`;
      await api(departurePath, 'GET', undefined, 'Master', 409);
      await api(reportPath, 'GET', undefined, 'Master', 409);
      await api(fieldPath(batch.requestId), 'GET', undefined, 'Master', 409);
      for (const { sessionPath, publish, running } of sources) {
        active.delete(running.id);
        const terminal = await api(sessionPath);
        const { streamId } = terminal.combatStream;
        const finalSequence = sessionPath === first.sessionPath ? 1 : 0;
        publish(terminal, [], { throughCombatSequence: finalSequence });
        await api(sessionPath + '/combat-stream/seal', 'POST', { streamId, finalSequence }, 'GameServer');
        publish.seal();
        await api(sessionPath + '/connection-endpoint', 'PUT', { version: 1, streamId, address: '192.168.50.40',
          port: 7776 + terminal.roomIds[0] }, 'GameServer');
      }
      const closurePath = `/venue/closure/${batch.requestId}`;
      const saved = (await api(closurePath)).batch;
      check(saved.sessions.every(session => session.fieldEvidenceReady)
        && saved.sessions[0].rosterDepartureCount === 1
        && saved.sessions.slice(1).every(session => !Object.hasOwn(session, 'rosterDepartureCount')),
      `The ${mode} closure enables the private archive after sealing and reports each departure only once`);
      await api(fieldReceiptsPath(batch.requestId), 'GET', undefined, 'Master', 409);
      for (const { sessionPath } of sources) {
        const original = (await api(sessionPath + '/world?includeDebriefReceipts=true')).debriefReceipts;
        if (original?.players.length) {
          assert.ok(original.players.every(row => row.roomId !== 1 && row.playerId !== departed.id));
          const { streamId, throughSequence, finalStreamSequence, worldSequence } = original;
          const players = original.players.map(({ playerId, admissionId, roomId }) => ({ playerId, admissionId, roomId }));
          await api(sessionPath + '/debrief-receipts', 'POST', { streamId, throughSequence, finalStreamSequence, worldSequence, players }, 'GameServer', 204);
        }
      }
      const response = await fetch(base + '/api' + fieldReceiptsPath(batch.requestId), auth);
      assert.ok(response.ok, `Departure archive ${response.status}: ${response.ok ? '' : await response.text()}`);
      assert.equal(response.headers.get('Cache-Control'), 'no-store');
      const file = path.join(screenshots, `venue-${mode.toLowerCase()}-departed-field.zip`);
      await fs.writeFile(file, Buffer.from(await response.arrayBuffer()));
      const result = spawnSync('python', ['-c', `import io, json, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    assert archive.testzip() is None
    docs = {}
    for member in archive.namelist():
        if not member.endswith('.zip'):
            continue
        with zipfile.ZipFile(io.BytesIO(archive.read(member))) as nested:
            assert nested.testzip() is None
            docs[member] = {name: json.loads(nested.read(name)) for name in nested.namelist()}
    print(json.dumps([docs, json.loads(archive.read('debrief-receipts.json'))], ensure_ascii=True))`, file],
      { encoding: 'utf8', windowsHide: true, timeout: 6000 });
      assert.equal(result.status, 0, result.stderr);
      const [docs, receipts] = JSON.parse(result.stdout);
      const target = docs[mode === 'Independent' ? 'room-01.zip' : 'linked.zip'];
      const roster = target['session.json'].players;
      const evidence = target['roster-departures.json'];
      assert.deepEqual(Object.keys(docs).sort(), mode === 'Independent' ? rooms.map(room => `room-0${room}.zip`) : ['linked.zip']);
      assert.deepEqual(evidence.players.map(({ playerId, admissionId, roomId }) => ({ playerId, admissionId, roomId })),
        [{ playerId: departed.id, admissionId: departed.admissionId, roomId: 1 }]);
      assert.equal(evidence.endedAtSequence, saved.sessions[0].appliedAtSequence);
      assert.ok(evidence.players[0].joinedAtSequence < evidence.players[0].leftAtSequence
        && evidence.players[0].leftAtSequence < evidence.endedAtSequence);
      assert.equal(roster.length, mode === 'Independent' ? 0 : 4);
      assert.equal(target['statistics.json'].players.length, roster.length + 1);
      assert.ok(target['statistics.json'].players.some(row => row.playerId === departed.id));
      assert.ok(!JSON.stringify(receipts).includes(departed.admissionId));
      await api(departurePath, 'GET', undefined, 'Room1', 403);
      await api(`/venue/closure/${batch.requestId}/sessions/${combined.id}/departed-players`, 'GET', undefined, 'Master', 404);
      const review = await api(departurePath);
      assert.deepEqual(review, { requestId: batch.requestId, sessionId: first.running.id, streamId: evidence.streamId,
        worldSequence: saved.sessions[0].replay.throughSequence, finalStreamSequence: 1, endedAtSequence: evidence.endedAtSequence,
        throughSequence: target['statistics.json'].throughSequence,
        players: [{ leftAtSequence: evidence.players[0].leftAtSequence,
          statistics: target['statistics.json'].players.find(row => row.playerId === departed.id) }] });
      await api(reportPath, 'GET', undefined, 'Room2', mode === 'Independent' ? 403 : 404);
      await api(reportPath, 'GET', undefined, 'GameServer', 403);
      const reportUrl = base + '/api' + reportPath;
      const originalCsv = await fetch(reportUrl, auth);
      assert.equal(originalCsv.status, 200);
      assert.equal(originalCsv.headers.get('Cache-Control'), 'no-store');
      const csvBytes = Buffer.from(await originalCsv.arrayBuffer());
      await login('Master');
      const openDeparture = archive(first.running.id).last().getByRole('button', { name: '查看離場玩家戰績（1）' });
      await openDeparture.waitFor();
      await fieldReceiptsButton.waitFor({ state: 'visible' });
      check(await fieldReceiptsButton.isEnabled(), `The ${mode} console lists the departed player's score and enables the archive after the four remaining seats acknowledge`);
      const departureTable = page.locator('#venue-departed-table');
      if (mode === 'Linked') {
        const requestUrl = '**/api' + departurePath;
        const substituted = async route => {
          const response = await route.fetch();
          await route.fulfill({ response, json: { ...await response.json(), streamId: randomUUID() } });
        };
        await page.route(requestUrl, substituted);
        try {
          await openDeparture.click();
          await page.locator('#venue-departed-status').filter({ hasText: '暫時無法確認離場玩家戰績' }).waitFor();
          check(await departureTable.isHidden(), 'The departed player view rejects a different stream without showing scores or replay links');
        } finally { await page.unroute(requestUrl, substituted); }
        let release;
        const gate = new Promise(resolve => { release = resolve; });
        const held = async route => {
          const response = await route.fetch();
          await gate;
          await route.fulfill({ response });
        };
        await page.route(requestUrl, held);
        try {
          const delivered = page.waitForResponse(base + '/api' + departurePath).catch(error => error);
          await openDeparture.click();
          await page.locator('#venue-departed-close').click();
          release();
          const response = await delivered;
          if (response instanceof Error) throw response;
          assert.ok(response.ok());
          await response.finished();
          check(await page.locator('#venue-departed-players').isHidden() && await departureTable.locator('tbody tr').count() === 0,
            'A completed older departure response cannot reopen its closed view');
        } finally { release(); await page.unroute(requestUrl, held); }
      }
      await openDeparture.click();
      await departureTable.waitFor();
      const departureCells = await departureTable.locator('tbody td').allTextContents();
      assert.deepEqual(departureCells, ['1', departed.name, '1', '0', '0', '0', '0', '0%', '100', '下載 CSV', '個人回放']);
      const csvButton = departureTable.getByRole('button', { name: `下載房間 1 ${departed.name} 的個人戰績 CSV` });
      if (mode === 'Linked') {
        const substituted = async route => {
          const response = await route.fetch();
          const changed = csvBytes.toString('utf8').replace(/,"100"\r\n$/, ',"99"\r\n');
          assert.notEqual(changed, csvBytes.toString('utf8'));
          await route.fulfill({ response, body: changed });
        };
        let wrongDownload = false;
        const markDownload = () => { wrongDownload = true; };
        page.on('download', markDownload);
        await page.route(reportUrl, substituted);
        try {
          await csvButton.click();
          await page.locator('#venue-departed-status').filter({ hasText: '暫時無法下載原封存戰績' }).waitFor();
          check(!wrongDownload && await csvButton.isEnabled(), 'A changed departed score prevents the CSV download and allows retry');
        } finally {
          await page.unroute(reportUrl, substituted);
          page.off('download', markDownload);
        }
        let release, reached;
        const allowDelivery = new Promise(resolve => { release = resolve; });
        const requested = new Promise(resolve => { reached = resolve; });
        const held = async () => {
          reached();
          await allowDelivery;
        };
        await page.route(reportUrl, held);
        try {
          const aborted = page.waitForEvent('requestfailed', candidate => candidate.url() === reportUrl);
          await csvButton.click();
          await requested;
          await page.locator('#venue-departed-close').click();
          const canceled = await aborted;
          check(canceled.failure()?.errorText === 'net::ERR_ABORTED' && await departureTable.isHidden(),
            'Closing the departed player view cancels its pending CSV download');
        } finally {
          release();
          await page.unroute(reportUrl, held);
        }
        await openDeparture.click();
        await departureTable.waitFor();
      }
      const [downloaded] = await Promise.all([page.waitForEvent('download'), csvButton.click()]);
      const filename = `vr-command-report-v1-${first.running.id}-player-${departed.id}.csv`;
      assert.equal(downloaded.suggestedFilename(), filename);
      assert.deepEqual(await fs.readFile(await downloaded.path()), csvBytes);
      await downloaded.saveAs(path.join(screenshots, `venue-${mode.toLowerCase()}-departed.csv`));
      check(true, `The ${mode} departed player download matches the original sealed personal CSV byte for byte`);
      const replayDeparture = departureTable.getByRole('button', { name: `開啟房間 1 ${departed.name} 的個人回放` });
      if (mode === 'Linked') {
        await page.locator('#venue-departed-players').screenshot({ path: path.join(screenshots, 'venue-departed-players.png') });
        await rejectReplayStatistics(replayDeparture, first.running.id, departed.id, player => { player.ammoUsed++; },
          'Changed rounds used at the sealed frame prevent opening the departed player replay');
        await page.locator('#world-message').screenshot({ path: path.join(screenshots, 'venue-departed-replay-score-refused.png') });
        await page.locator('#tab-operations').click();
        await openDeparture.click();
        await departureTable.waitFor();
      }
      await replayDeparture.click();
      await page.locator('#world-review-player-name').filter({ hasText: departed.name }).waitFor();
      check(await recording.inputValue() === first.running.id && await page.locator('#world-room').inputValue() === '1'
        && await page.locator('#venue-departed-players').isHidden(), `The ${mode} archived scores open the departed player in the original room and recording`);
      const savedShot = page.locator('#world-event-search-results button[data-frame-sequence="3"]');
      if (mode === 'Linked') {
        const frameRoute = url => url.pathname === `/api/sessions/${first.running.id}/world/frames/3`;
        const changedEvent = async route => {
          const response = await route.fetch(), body = await response.json();
          const shot = body.packet.events.find(event => event.eventId === eventId);
          assert.ok(shot);
          shot.eventId = randomUUID();
          await route.fulfill({ response, json: body });
        };
        const frameMessage = page.locator('#world-frame-message');
        const canvas = page.locator('#world-canvas');
        const originalTail = await canvas.getAttribute('data-sequence');
        const jumps = [
          [savedShot, 'search result', '#world-frame-message', '讀取快照失敗|已停在第 3 格'],
          [page.locator('#world-event-previous'), 'previous event', '#world-event-search-status', '讀取事件快照失敗|已跳到第 3 格']
        ];
        for (const [button, action, selector, message] of jumps) {
          await page.route(frameRoute, changedEvent, { times: 1 });
          try {
            await button.click();
            await page.waitForFunction(({ selector, message }) => new RegExp(message).test(document.querySelector(selector).textContent),
              { selector, message });
            check((await frameMessage.innerText()).includes('讀取快照失敗') && await canvas.getAttribute('data-sequence') === originalTail,
              `The ${action} rejects a substituted shot ID despite matching frame, time, player, kind and count`);
          } finally { await page.unroute(frameRoute, changedEvent); }
        }
      }
      await savedShot.click();
      await page.locator('#world-events tr').first().filter({ hasText: departed.name }).waitFor();
      check(await savedShot.count() === 1, `The ${mode} personal replay finds the departed player's original saved shot`);
    }
  } finally {
    await page.unroute(route); await page.close();
    for (const id of active) await end(id);
  }
};
