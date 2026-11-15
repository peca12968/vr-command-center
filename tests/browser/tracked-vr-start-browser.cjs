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
    await api(route + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    opened.delete(route);
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
    const { route, streamId, questId, viveId, join, view } = await prepare('GameServer');
    const began = Date.now() - 5000;
    let sequence = 0;
    function publish(snapshot, { missing = false, simulated = false } = {}) {
      const players = snapshot.players.map(({ id, seat }) => {
        const head = { x: -28 + (seat - 2) * 1.5, y: 1.65, z: -3 };
        const connected = !missing || id !== viveId;
        const kind = !connected ? 'None' : simulated && id === viveId ? 'Simulated' : 'Tracked';
        return { id, roomId, head, muzzle: head, forward: { x: 0, y: 0, z: 1 }, connected,
          health: 100, magazine: 30, reserve: 90, rig: kind === 'None' ? { kind } : { kind, left: head, right: head } };
      });
      const header = { sessionId: view.id, streamId, origin: 'GameServer', roomIds: [roomId],
        captureStartedAtUtc: new Date(began).toISOString().replace('Z', '0000+00:00') };
      const packet = { sequence: ++sequence, observedSequence: snapshot.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - began,
        throughCombatSequence: 0, weather: 'Clear', events: [],
        frame: { phase: 'Preparing', tick: 0, night: false, throughSequence: 0, players } };
      const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${route}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, { type: 'frame', payload: packet }] }) });
      assert.equal(result.status, 0, 'Tracked VR fixture publication: ' + result.stderr);
      assert.equal(JSON.parse(result.stdout).acceptedSequence, sequence);
    }
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
    publish(replaced);
    const confirmed = await command(route);
    assert.equal(confirmed.status, 200);
    const retry = await attempt(replaced, confirmed.intent, 'Room1', 200);
    await attempt(replaced, { ...confirmed.intent, requireTrackedStart: false });
    check(confirmed.body.session.state === 'Running' && retry.duplicate && retry.appliedAtSequence === confirmed.body.appliedAtSequence
      && retry.session.sequence === replaced.sequence + 1, 'Two tracked admissions start exactly once and the same command can be retried');
    await end(route);

    const simulation = await prepare('Simulation');
    await rejectedSimulation();
    await page.locator('#refresh').click(); await page.locator('#session-select').selectOption(simulation.view.id);
    await page.getByRole('button', { name: '開始任務' }).waitFor();
    const normal = await command(simulation.route);
    check(normal.status === 200 && normal.body.session.state === 'Running' && !('requireTrackedStart' in normal.intent)
      && await status.isHidden(), 'Simulation keeps its existing start path and does not show tracked game readiness');

    async function rejectedSimulation() {
      const result = await api(simulation.route + '/commands', 'POST', { commandId: randomUUID(), action: 'Begin',
        expectedSequence: simulation.view.sequence, requireTrackedStart: true }, 'Room1', 409);
      assert.equal(result.code, 'tracked-vr-start-not-ready');
    }
  } finally {
    await page.close();
    for (const route of opened) await end(route);
  }
};
