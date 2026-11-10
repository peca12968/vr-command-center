const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, root, screenshots, check, captureErrors }) => {
  const page = await context.newPage(), active = new Set();
  captureErrors(page);
  const command = (id, action) => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action });
  const button = page.locator('[data-room-vr-participation-pause="4"]');
  const poseFrame = page.locator('[data-room-pose-frame="4"]');
  const resumeButton = page.locator('[data-room-vr-resume="4"]');
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
      const peer = linked ? { ...player, playerId: randomUUID(), roomId: 2, name: 'Other linked seat' } : null;
      if (peer) await api(`/sessions/${id}/players`, 'POST', peer);
      const streamId = randomUUID(), started = Date.now();
      await api(`/sessions/${id}/combat-stream`, 'POST', { streamId, origin: 'Simulation' }, 'GameServer');
      let sequence = 0;
      const header = { sessionId: id, streamId, origin: 'Simulation', roomIds,
        captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00') };
      function publish(session, connected, peerConnected = true) {
        const rotation = { x: 0, y: 0, z: 0, w: 1 };
        const body = (seat, online) => {
          const point = { x: (seat.roomId - 3) * 14, y: 1.65, z: -3 };
          return { id: seat.playerId, roomId: seat.roomId, head: point, muzzle: point, forward: { x: 0, y: 0, z: 1 },
            connected: online, health: 100, magazine: 30, reserve: 90, rig: online ? { kind: 'Simulated',
              left: point, right: point, headRotation: rotation, leftRotation: rotation, rightRotation: rotation } : { kind: 'None' } };
        };
        const frame = { sequence: ++sequence, observedSequence: session.sequence,
          elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
          weather: 'Clear', lightning: false, suspended: false, throughCombatSequence: 0, events: [],
          frame: { phase: session.state, tick: session.state === 'Preparing' ? 0 : 1, night: false, visibility: 'Clear',
            behavior: 'Hold', autoAttack: false, throughSequence: 0, enemies: [],
            players: peer ? [body(peer, peerConnected), body(player, connected)] : [body(player, connected)] } };
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
      await until(() => publish(running, false), () => poseFrame.isEnabled());
      await poseFrame.click();
      await page.waitForFunction(() => document.getElementById('world-frame-message').textContent.includes('姿態中斷快照')
        || document.getElementById('world-message').classList.contains('replay-error'), undefined, { polling: 100 });
      assert.match(await page.locator('#world-frame-message').textContent(), /姿態中斷快照。\s*房間 4 · 席位 1/,
        await page.locator('#world-message').textContent());
      const viewed = Number(await page.locator('#world-canvas').getAttribute('data-sequence'));
      const original = await api(detail + '/world/frames/' + viewed, 'GET', undefined, 'Room4');
      check(viewed > 1 && original.packet.sequence === viewed && original.packet.observedSequence === running.sequence
        && original.packet.frame.players.find(row => row.id === player.playerId)?.connected === false
        && (await api(detail)).sequence === running.sequence,
        mode + ' room desk opens its exact original saved interruption frame without changing the mission');
      await page.locator('#tab-operations').click();
      if (!linked) {
        const watch = url => url.pathname === '/api' + detail + '/world/watch' && url.searchParams.get('mode') === 'replay';
        await page.route(watch, async request => {
          const response = await request.fetch();
          const body = (await response.text()).split('\n').map(line => {
            if (!line.startsWith('data: ')) return line;
            const data = JSON.parse(line.slice(6));
            if (data.packet) data.packet.observedSequence--;
            return 'data: ' + JSON.stringify(data);
          }).join('\n');
          await request.fulfill({ response, body });
        });
        try {
          await until(() => publish(running, false), () => poseFrame.isEnabled());
          await poseFrame.click();
          await page.locator('#world-message').filter({ hasText: '姿態中斷或指令序號不同' }).waitFor();
          check(await page.locator('#world-canvas').getAttribute('data-sequence') === null,
            'An altered interruption replay packet does not leave any frame on the viewer');
        } finally {
          await page.unroute(watch);
        }
        await page.locator('#tab-operations').click();
      }
      await until(() => publish(running, true), async () => await poseFrame.isHidden()
        && (await page.locator('[data-room-readiness="4"]').innerText()).startsWith('1 / 1'));
      check(await poseFrame.isHidden(), mode + ' recovery withdraws the live pose frame shortcut');
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
      const role = linked ? 'Master' : 'Room4';
      const recoveryCommand = () => ({ commandId: randomUUID(), action: 'Resume', expectedSequence: receipt.session.sequence });
      const denied = await api(route, 'POST', recoveryCommand(), role, 409);
      check(denied.code === 'vr-participation-resume-not-ready', mode + ' blocks a Resume before the game observes the pause');
      await pauseStatus.filter({ hasText: 'VR 暫停待確認' }).waitFor();
      check(await button.isHidden() && (!unaffected || (await api(`/sessions/${unaffected}`)).state === 'Running'),
        mode + ' acknowledges the scoped pause before the game observes it');
      await until(() => publish(receipt.session, false), () => pauseStatus.innerText().then(text => text.includes('等候席位 1')));
      const retry = await api(route, 'POST', result.request().postDataJSON(), role);
      check(retry.duplicate && retry.appliedAtSequence === receipt.appliedAtSequence
        && await page.locator('[data-room-vr-pause]:visible').count() === roomIds.length,
        mode + ' confirms the original pause across the intended rooms and retries idempotently');
      if (linked) await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'vr-linked-pause.png') });
      check(await resumeButton.isDisabled() && (await api(route, 'POST', recoveryCommand(), role, 409)).code
        === 'vr-participation-resume-not-ready' && !(await api('/venue/phase')).resume.some(target => target.sessionId === id),
        mode + ' shows the missing seat, rejects a direct Resume and stays out of the batch Resume plan');
      if (linked) {
        await until(() => publish(receipt.session, true, false), () =>
          page.locator('[data-room-vr-pause="2"]').innerText().then(text => text.includes('等候席位 1')));
        check(await resumeButton.isDisabled() && (await api(route, 'POST', recoveryCommand(), role, 409)).code
          === 'vr-participation-resume-not-ready', 'A recovered trigger room cannot resume Linked while another room still lacks a living pose');
      }
      await until(() => publish(receipt.session, true), () => resumeButton.isEnabled());
      if (linked) await api(route, 'POST', recoveryCommand(), 'Room4', 403);
      if (!linked) {
        const response = page.waitForResponse(value => value.url() === base + '/api' + route && value.request().method() === 'POST');
        const asked = page.waitForEvent('dialog');
        const click = resumeButton.click();
        const dialog = await asked;
        publish(receipt.session, false);
        await dialog.accept(); await click;
        const rejected = await response;
        check(rejected.status() === 409 && (await rejected.json()).code === 'vr-participation-resume-not-ready',
          'A second loss during the resume confirmation keeps the original room paused');
      }
      await until(() => publish(receipt.session, true), () => resumeButton.isEnabled());
      if (linked) await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'vr-linked-ready-to-resume.png') });
      const resumeReply = page.waitForResponse(value => value.url() === base + '/api' + route && value.request().method() === 'POST');
      const confirmResume = page.waitForEvent('dialog').then(async dialog => {
        assert.match(dialog.message(), linked ? /一起繼續合併場次/ : /繼續本房/);
        await dialog.accept();
      });
      await resumeButton.click(); await confirmResume;
      const resuming = await resumeReply, resumed = await resuming.json();
      assert.equal(resuming.status(), 200);
      assert.equal(resumed.session.state, 'Running');
      await until(() => publish(resumed.session, true), async () => await resumeButton.isHidden()
        && (await page.locator('[data-room-readiness="4"][data-source-state="Fresh"]').allTextContents())
          .some(text => text.includes('1 / 1 姿態有效')));
      const resumeRetry = await api(route, 'POST', resuming.request().postDataJSON(), role);
      check(resumeRetry.duplicate && resumeRetry.appliedAtSequence === resumed.appliedAtSequence && await resumeButton.isHidden(),
        mode + ' uses the recovered frame to continue the original scope and retries once');
      await command(id, 'End'); active.delete(id);
      if (unaffected) { await command(unaffected, 'End'); active.delete(unaffected); }
    }
  } finally {
    await page.close();
    for (const id of active) await command(id, 'End');
  }
};
