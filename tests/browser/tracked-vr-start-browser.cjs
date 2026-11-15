const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const roomId = 1;
  const mission = await api('/missions', 'POST', { name: 'VR 追蹤開場', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const opened = new Set();
  async function prepare(origin) {
    const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [roomId] }, 'Master', 201);
    const route = `/sessions/${session.id}`;
    opened.add(route);
    const questId = randomUUID(), viveId = randomUUID(), streamId = randomUUID();
    const join = (playerId, headset) => api(route + '/players', 'POST', { playerId, name: headset, headset, roomId });
    await join(questId, 'Quest3'); await join(viveId, 'ViveXr');
    await api(route + '/combat-stream', 'POST', { streamId, origin }, 'GameServer');
    return { route, streamId, questId, viveId, join, view: await api(route) };
  }
  async function end(route) {
    const receipt = await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    opened.delete(route);
    return receipt.session;
  }
  function publisher({ route, streamId, viveId, view }, startAge = 0) {
    const began = Date.now() - startAge;
    let sequence = 0;
    const header = { sessionId: view.id, streamId, origin: 'GameServer', roomIds: [roomId],
      captureStartedAtUtc: new Date(began).toISOString().replace('Z', '0000+00:00') };
    function send(message) {
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${route}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, message] }) });
      assert.equal(result.status, 0, 'Tracked VR fixture publication: ' + result.stderr);
      return JSON.parse(result.stdout);
    }
    function publish(snapshot, { missing = false, simulated = false, tick = 0 } = {}) {
      const players = snapshot.players.map(({ id, seat }) => {
        const head = { x: -28 + (seat - 2) * 1.5, y: 1.65, z: -3 };
        const connected = !missing || id !== viveId;
        const kind = !connected ? 'None' : simulated && id === viveId ? 'Simulated' : 'Tracked';
        return { id, roomId, head, muzzle: head, forward: { x: 0, y: 0, z: 1 }, connected,
          health: 100, magazine: 30, reserve: 90, rig: kind === 'None' ? { kind } : { kind, left: head, right: head } };
      });
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - began,
        throughCombatSequence: 0, weather: 'Clear', events: [],
        frame: { phase: snapshot.state, tick, night: false, throughSequence: 0, players } };
      assert.equal(send({ type: 'frame', payload: packet }).acceptedSequence, sequence);
      return packet;
    }
    return { publish, seal: () => assert.equal(send({ type: 'seal', finalSequence: sequence }).complete, true) };
  }
  const page = await context.newPage();
  captureErrors(page);
  const start = page.locator('[data-command=Begin]'), status = page.locator('#tracked-vr-start-status');
  async function command(route) {
    const response = page.waitForResponse(item => item.url() === base + '/api' + route + '/commands'
      && item.request().method() === 'POST' && item.request().postDataJSON().action === 'Begin');
    await start.click();
    const result = await response;
    return { status: result.status(), body: await result.json(), intent: result.request().postDataJSON() };
  }

  try {
    const fixture = await prepare('GameServer');
    const { route, streamId, questId, viveId, join, view } = fixture;
    const { publish, seal } = publisher(fixture, 5000);
    const attempt = (snapshot, updates = {}, role = 'Room1', expected = 409) => api(route + '/commands', 'POST',
      { commandId: randomUUID(), action: 'Begin', expectedSequence: snapshot.sequence, requireTrackedStart: true, ...updates }, role, expected);
    const rejected = async snapshot => assert.equal((await attempt(snapshot)).code, 'tracked-vr-start-not-ready');
    await attempt(view, {}, 'Room2', 403);
    await attempt(view, { expectedSequence: null }, 'Room1', 400);
    await attempt(view, { action: 'Pause' }, 'Room1', 400);
    check(true, 'Tracked VR Begin requires original revision, Begin action and the owning control desk');

    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Room1); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(view.id);
    await page.getByRole('button', { name: '確認追蹤並開始' }).waitFor();
    const noFrame = await command(route);
    await page.locator('#notice').filter({ hasText: 'VR 追蹤開場尚未就緒' }).waitFor();
    check(noFrame.intent.requireTrackedStart === true && noFrame.status === 409 && (await api(route)).sequence === view.sequence,
      'The owning room console requests tracked Begin and leaves a source without a frame in Preparing');

    publish(view);
    await rejected(view);
    check((await api(route + '/readiness')).sourceState === 'Stale', 'An old Preparing frame with two tracked seats cannot start the session');
    publish(view, { simulated: true });
    await rejected(view);
    check((await api(route + '/readiness')).trackedVrStartReady === false, 'A fresh GameServer frame with one Simulated seat is insufficient');

    publish(view);
    await status.filter({ hasText: '2 / 2 席追蹤就緒。開始時會再核對' }).waitFor();
    publish(view, { missing: true });
    const lost = await command(route);
    check(lost.status === 409 && lost.body.code === 'tracked-vr-start-not-ready' && (await api(route)).sequence === view.sequence,
      'The primary Begin button rejects tracking lost after its earlier ready reading');
    await status.filter({ hasText: '1 / 2 席追蹤就緒' }).waitFor();

    const quest = view.players.find(player => player.id === questId);
    publish(view);
    await api(route + '/players/' + questId, 'DELETE', undefined, 'Master', 204, quest.admissionId);
    const replaced = await join(questId, 'Quest3');
    await rejected(replaced);
    check((await api(route + '/readiness')).players.find(player => player.playerId === questId).state === 'AwaitingAdmission',
      'A reused player ID must obtain tracking for its new admission and revision');

    await page.locator('#refresh').click();
    publish(replaced);
    await status.filter({ hasText: '2 / 2 席追蹤就緒。開始時會再核對' }).waitFor();
    await status.screenshot({ path: path.join(screenshots, 'tracked-vr-start-ready.png') });
    const accepted = publish(replaced);
    const confirmed = await command(route);
    assert.equal(confirmed.status, 200);
    const retry = await attempt(replaced, confirmed.intent, 'Room1', 200);
    await attempt(replaced, { ...confirmed.intent, requireTrackedStart: false });
    check(confirmed.body.session.state === 'Running' && retry.duplicate && retry.appliedAtSequence === confirmed.body.appliedAtSequence
      && retry.session.sequence === replaced.sequence + 1, 'Two tracked admissions start exactly once and the same command can be retried');

    // A later Preparing frame and a later roster removal must not replace the original accepted evidence.
    publish(replaced);
    const vive = replaced.players.find(player => player.id === viveId);
    await api(route + '/players/' + viveId, 'DELETE', undefined, 'Master', 204, vive.admissionId);
    publish(await api(route), { tick: 1 });
    const ended = await end(route);
    publish(ended, { tick: 1 });
    const closure = route + '/world?includeDebriefReceipts=true';
    await api(route + '/combat-stream/seal', 'POST', { streamId, finalSequence: 0 }, 'GameServer');
    check((await api(closure)).trackedVrStart === undefined, 'The closure withholds its start pointer until the original world also seals');
    seal();
    const saved = await api(closure, 'GET', undefined, 'Room1');
    assert.equal(saved.trackedVrStart?.worldSequence, accepted.sequence);
    assert.equal(saved.trackedVrStart?.elapsedMilliseconds, accepted.elapsedMilliseconds);
    assert.equal(saved.trackedVrStart?.appliedAtSequence, confirmed.body.appliedAtSequence);
    assert.deepEqual(saved.trackedVrStart?.players.map(owner => owner.playerId).sort(), [questId, viveId].sort());
    assert.deepEqual(saved.debriefReceipts.players.map(owner => owner.playerId), [questId]);
    await api(closure, 'GET', undefined, 'Room2', 403);
    check((await api(closure)).trackedVrStart?.streamId === streamId && (await api(route + '/world')).trackedVrStart === undefined,
      'The sealed archive gives its authorized room and Master the exact original roster and pointer, separately from the final roster');

    await api(route + '/connection-endpoint', 'PUT', { version: 1, streamId, address: '192.168.50.40', port: 7777 }, 'GameServer');
    const field = await fieldExport(route);
    assert.deepEqual(field.members, ['session.json', 'statistics.json', 'endpoint.json', 'tracked-vr-start.json', 'roster-departures.json']);
    assert.deepEqual(field.departures.players, [{ playerId: viveId, admissionId: vive.admissionId, roomId,
      joinedAtSequence: view.sequence - 1, leftAtSequence: confirmed.body.appliedAtSequence + 1 }]);
    check(field.session.players.length === 1 && field.statistics.players.length === 2 && field.departures.endedAtSequence === ended.sequence,
      'A tracked archive keeps all statistics together with the original removal and the separate final player roster');

    const simulation = await prepare('Simulation');
    await rejectedSimulation();
    await page.locator('#include-ended').check();
    await page.locator('#session-select').selectOption(view.id);
    const replay = page.locator('#open-tracked-vr-start');
    await replay.waitFor();
    const watch = `**/api/sessions/${view.id}/world/watch?**`;
    await page.route(watch, async route => {
      const response = await route.fetch();
      const body = (await response.text()).replace(/event: frame\ndata: (.+)/, (_, raw) => {
        const value = JSON.parse(raw);
        value.packet.frame.players[0].rig.kind = 'Simulated';
        return 'event: frame\ndata: ' + JSON.stringify(value);
      });
      await route.fulfill({ response, body });
    }, { times: 1 });
    await replay.click();
    await page.locator('#world-message').filter({ hasText: '回應快照的本場追蹤開場或指令序號不同' }).waitFor();
    check(await page.locator('#world-player').isHidden(), 'A substituted opening pose cannot be displayed as the original tracked frame');
    await page.locator('#tab-operations').click(); await replay.click();
    const original = page.locator(`#world-canvas[data-sequence="${accepted.sequence}"]`);
    await original.waitFor();
    check(await page.locator('#world-room').inputValue() === '1' && await page.locator('#world-camera').inputValue() === 'top',
      'After room reuse the room desk opens the original Preparing frame and its original top view');
    await page.locator('#world-frame-next').click();
    await page.locator(`#world-canvas[data-sequence="${accepted.sequence + 1}"]`).waitFor();
    await page.locator('#world-begin-original').click();
    await original.waitFor();
    check(await page.locator('#world-begin-original').isDisabled(), 'The archived opening supports adjacent-frame inspection and return to its exact pointer');
    await page.locator('#world-player').screenshot({ path: path.join(screenshots, 'tracked-vr-start-replay.png') });

    await page.locator('#tab-operations').click();
    await page.locator('#refresh').click(); await page.locator('#session-select').selectOption(simulation.view.id);
    await page.getByRole('button', { name: '開始任務' }).waitFor();
    const normal = await command(simulation.route);
    check(normal.status === 200 && normal.body.session.state === 'Running' && !('requireTrackedStart' in normal.intent)
      && await status.isHidden(), 'Simulation keeps its existing start path and does not show tracked game readiness');
    await end(simulation.route);
    await exportTrackedFieldEvidence();
    await exportTrackedFieldEvidence(true);

    async function rejectedSimulation() {
      const result = await api(simulation.route + '/commands', 'POST', { commandId: randomUUID(), action: 'Begin',
        expectedSequence: simulation.view.sequence, requireTrackedStart: true }, 'Room1', 409);
      assert.equal(result.code, 'tracked-vr-start-not-ready');
    }
  } finally {
    await page.close();
    for (const route of opened) await end(route);
  }

  async function fieldExport(route, file = null) {
    const url = `${base}/api${route}/field-evidence.zip?includeTrackedVrStart=true`;
    const response = await fetch(url, { headers: { Authorization: 'Bearer ' + tokens.Master }, signal: AbortSignal.timeout(8000) });
    assert.ok(response.ok, `Tracked field export ${response.status}: ${response.ok ? '' : await response.text()}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    if (file) assert.deepEqual(require('node:fs').readFileSync(file), bytes);
    const result = spawnSync('python', ['-c', `import io, json, sys, zipfile
with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as archive:
    members = archive.namelist()
    assert archive.testzip() is None
    print(json.dumps({'members': members, 'session': json.loads(archive.read('session.json')),
        'statistics': json.loads(archive.read('statistics.json')), 'start': json.loads(archive.read('tracked-vr-start.json')),
        'departures': json.loads(archive.read('roster-departures.json')) if 'roster-departures.json' in members else None}, ensure_ascii=True))`],
      { input: bytes, encoding: 'utf8', timeout: 6000, windowsHide: true });
    assert.equal(result.status, 0, result.stderr);
    assert.ok(Object.values(tokens).every(token => !result.stdout.includes(token)));
    return JSON.parse(result.stdout);
  }

  async function exportTrackedFieldEvidence(removeAll = false) {
    const fixture = await prepare('GameServer');
    const { route, streamId, view } = fixture;
    const { publish, seal } = publisher(fixture);
    const anchor = publish(view);
    const running = await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'Begin',
      expectedSequence: view.sequence, requireTrackedStart: true });
    publish(running.session, { tick: 1 });
    if (removeAll) {
      for (const player of view.players)
        await api(route + '/players/' + player.id, 'DELETE', undefined, 'Master', 204, player.admissionId);
    }
    publish(await end(route), { tick: 1 });
    await api(route + '/combat-stream/seal', 'POST', { streamId, finalSequence: 0 }, 'GameServer');
    seal();
    await api(route + '/connection-endpoint', 'PUT', { version: 1, streamId, address: '192.168.50.40', port: 7777 }, 'GameServer');
    const final = await api(route);
    const saved = (await api(route + '/world?includeDebriefReceipts=true')).trackedVrStart;
    assert.equal(saved.worldSequence, anchor.sequence);
    const evidenceUrl = `${base}/api${route}/field-evidence.zip?includeTrackedVrStart=true`;
    const forbidden = await fetch(evidenceUrl, { headers: { Authorization: 'Bearer ' + tokens.Room1 } });
    assert.equal(forbidden.status, 403);
    const exportPage = await context.newPage();
    captureErrors(exportPage);
    try {
      await exportPage.bringToFront(); await exportPage.goto(base + '/console/');
      await exportPage.locator('#login-key').fill(tokens.Master); await exportPage.locator('#login-form button').click();
      await exportPage.locator('#include-ended').check(); await exportPage.locator('#session-select').selectOption(view.id);
      await exportPage.locator('#open-tracked-vr-start').waitFor({ timeout: 10000 });
      const requested = exportPage.waitForResponse(response => response.url() === evidenceUrl, { timeout: 10000 }).catch(error => error);
      const downloading = exportPage.waitForEvent('download', { timeout: 10000 }).catch(error => error);
      await exportPage.locator('#download-field-evidence').click({ timeout: 10000 });
      const response = await requested;
      if (response instanceof Error) throw response;
      assert.ok(response.ok(), `Tracked field export ${response.status()}: ${response.ok() ? '' : await response.text()}`);
      assert.equal(response.headers()['cache-control'], 'no-store');
      const file = path.join(screenshots, removeAll ? 'tracked-vr-departed-field-evidence.zip' : 'tracked-vr-field-evidence.zip');
      const download = await downloading;
      if (download instanceof Error) throw download;
      await download.saveAs(file);
      const field = await fieldExport(route, file);
      assert.deepEqual(field.start, { version: 1, trackedVrStart: saved });
      assert.equal(field.session.players.length, removeAll ? 0 : 2);
      assert.equal(field.statistics.players.length, 2);
      assert.equal(field.departures?.players.length ?? 0, removeAll ? 2 : 0);
      check((await api(route)).sequence === final.sequence, removeAll
        ? 'Master downloads both removed players and sealed scores even with an empty final roster'
        : 'Master downloads the exact saved opening pointer with the original private field ZIP and creates no event');
      if (!removeAll) {
        const player = view.players[0];
        await api(route + '/players/' + player.id, 'DELETE', undefined, 'Master', 409, player.admissionId);
        check((await api(route)).sequence === final.sequence && (await fieldExport(route)).departures === null,
          'The original End still prevents roster writes from appearing as earlier departures');
      }
    } finally { await exportPage.close(); }
  }
};
