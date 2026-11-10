const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const page = await context.newPage(), active = new Set();
  captureErrors(page);
  const command = (id, action) => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action });
  const button = page.locator('[data-room-vr-participation-pause="4"]');
  const pauseStatus = page.locator('[data-room-vr-pause="4"]');
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function until(publish, ready) {
    const deadline = Date.now() + 12000;
    do {
      publish();
      if (await ready()) return;
      await new Promise(resolve => setTimeout(resolve, 180));
    } while (Date.now() < deadline);
    assert.fail('The console did not observe the published VR pose');
  }
  const mission = await api('/missions', 'POST', { name: 'VR pose pause', briefing: '', durationSeconds: 180,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  async function create(mode, roomIds) {
    const { id } = await api('/sessions', 'POST', { missionId: mission.id, mode, roomIds }, 'Master', 201);
    active.add(id);
    return id;
  }
  try {
    for (const mode of ['Independent', 'Linked']) {
      const linked = mode === 'Linked';
      const roomIds = linked ? [1, 2, 3, 4, 5] : [4], id = await create(mode, roomIds);
      const unaffected = linked ? null : await create('Independent', [2]);
      if (unaffected) {
        await api(`/sessions/${unaffected}/players`, 'POST', { playerId: randomUUID(), roomId: 2, name: 'Other room', headset: 'Quest3' });
        await command(unaffected, 'Begin');
      }
      const player = { playerId: randomUUID(), roomId: 4, name: 'Original VR seat', headset: 'Quest3' };
      await api(`/sessions/${id}/players`, 'POST', player);
      const streamId = randomUUID(), started = Date.now();
      await api(`/sessions/${id}/combat-stream`, 'POST', { streamId, origin: 'Simulation' }, 'GameServer');
      let sequence = 0;
      const header = { sessionId: id, streamId, origin: 'Simulation', roomIds,
        captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00') };
      function publish(session, connected) {
        const point = { x: 14, y: 1.65, z: -3 }, rotation = { x: 0, y: 0, z: 0, w: 1 };
        const frame = { sequence: ++sequence, observedSequence: session.sequence,
          elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
          weather: 'Clear', lightning: false, suspended: false, throughCombatSequence: 0, events: [],
          frame: { phase: session.state, tick: session.state === 'Preparing' ? 0 : 1, night: false, visibility: 'Clear',
            behavior: 'Hold', autoAttack: false, throughSequence: 0, enemies: [], players: [
              { id: player.playerId, roomId: 4, head: point, muzzle: point, forward: { x: 0, y: 0, z: 1 },
                connected, health: 100, magazine: 30, reserve: 90, rig: connected ? { kind: 'Simulated',
                  left: point, right: point, headRotation: rotation, leftRotation: rotation, rightRotation: rotation } : { kind: 'None' } }
            ] } };
        const result = spawnSync('python', [path.join(root, 'scripts/world_test_socket.py')], { encoding: 'utf8', timeout: 6000, windowsHide: true,
          input: JSON.stringify({ port: Number(new URL(base).port), route: `/api/sessions/${id}/world/publish`, token: tokens.GameServer,
            messages: [{ type: 'header', payload: header }, { type: 'frame', payload: frame }] }) });
        assert.equal(result.status, 0, result.stderr || result.error?.message);
        assert.equal(JSON.parse(result.stdout).acceptedSequence, sequence);
      }
      const detail = `/sessions/${id}`, route = detail + '/commands';
      publish(await api(detail), false);
      const { session: running } = await command(id, 'Begin');
      const attempt = room => ({ commandId: randomUUID(), action: 'Pause', expectedSequence: running.sequence, vrParticipationRoomId: room });
      publish(running, false);
      const wrong = await api(route, 'POST', attempt(5), 'Master', 409);
      check(wrong.code === 'vr-participation-pause-no-witness' && (await api(detail)).sequence === running.sequence,
        mode + ' refuses a pause witness from the wrong room');
      await login('Room4');
      if (linked) {
        await until(() => publish(running, false), () => page.locator('[data-room-readiness="4"]').innerText()
          .then(text => text.includes('姿態待確認席位')));
        await api(route, 'POST', attempt(4), 'Room4', 403);
        check(await button.isHidden(), 'The room desk cannot pause a shared VR match');
        await login('Master');
      }
      await until(() => publish(running, false), () => button.isVisible());
      check(await page.locator('[data-room-vr-participation-pause]:visible').count() === 1,
        mode + ' offers the shortcut only on the original affected room');
      if (!linked) {
        const asked = page.waitForEvent('dialog');
        const click = button.click();
        const dialog = await asked;
        assert.match(dialog.message(), /暫停本房檢查席位/);
        await dialog.dismiss(); await click;
        assert.equal((await api(detail)).sequence, running.sequence);
        await until(() => publish(running, false), () => button.isVisible());
        const rejected = page.waitForResponse(reply => reply.url() === base + '/api' + route && reply.request().method() === 'POST');
        const confirming = page.waitForEvent('dialog');
        const selected = button.click();
        const recovery = await confirming;
        publish(running, true);
        await recovery.accept(); await selected;
        const denial = await rejected;
        check(denial.status() === 409 && (await denial.json()).code === 'vr-participation-pause-no-witness'
          && (await api(detail)).sequence === running.sequence, 'Recovery during the confirmation dialog invalidates the proposed pause');
      }
      await until(() => publish(running, false), () => button.isEnabled());
      const reply = page.waitForResponse(response => response.url() === base + '/api' + route && response.request().method() === 'POST');
      const accepted = page.waitForEvent('dialog').then(async dialog => {
        assert.match(dialog.message(), linked ? /所有房間一起暫停/ : /暫停本房檢查席位/);
        await dialog.accept();
      });
      await button.click(); await accepted;
      const result = await reply, receipt = await result.json();
      assert.equal(result.status(), 200);
      assert.equal(receipt.session.state, 'Paused');
      await pauseStatus.filter({ hasText: 'VR 暫停待確認' }).waitFor();
      check(await button.isHidden() && (!unaffected || (await api(`/sessions/${unaffected}`)).state === 'Running'),
        mode + ' acknowledges the scoped pause before the game observes it');
      await until(() => publish(receipt.session, false), () => pauseStatus.innerText().then(text => text.includes('VR 暫停已套用')));
      const retry = await api(route, 'POST', result.request().postDataJSON(), linked ? 'Master' : 'Room4');
      check(retry.duplicate && retry.appliedAtSequence === receipt.appliedAtSequence
        && await page.locator('[data-room-vr-pause]:visible').count() === roomIds.length,
        mode + ' confirms the original pause across the intended rooms and retries idempotently');
      if (linked) await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'vr-linked-pause.png') });
      await command(id, 'End'); active.delete(id);
      if (unaffected) { await command(unaffected, 'End'); active.delete(unaffected); }
    }
  } finally {
    await page.close();
    for (const id of active) await command(id, 'End');
  }
};
