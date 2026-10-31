const { randomUUID } = require('node:crypto');
const path = require('node:path');
module.exports = async ({ context, api, tokens, base, mission, screenshots, check }) => {
  const free = (await api('/rooms')).filter(room => !room.sessionId);
  if (free.length < 2) throw Error('Readiness browser check requires two free fixture rooms');
  const sessions = [];
  for (const room of free.slice(0, 2)) {
    const created = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room.id] }, 'Master', 201);
    const state = await api(`/sessions/${created.id}/players`, 'POST', { playerId: randomUUID(), name: 'Readiness <b>player</b>', roomId: room.id, headset: 'Quest3' });
    sessions.push(state);
  }
  const page = await context.newPage();
  try {
    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(sessions[0].id);
    await page.waitForFunction(() => document.querySelector('#readiness-summary').textContent.includes('等待遊戲來源'));
    check((await page.locator('#roster [data-readiness-player]').innerText()).includes('等待遊戲來源'), 'Registered headset category alone never appears as a connected pose');
    const first = sessions[0], player = first.players[0];
    const ready = { version: 1, sessionId: first.id, sessionSequence: first.sequence, sourceState: 'Fresh', origin: 'Simulation', sourceAgeMilliseconds: 0,
      players: [{ playerId: player.id, admissionId: player.admissionId, roomId: player.roomId, seat: player.seat, state: 'Participating', rigKind: 'Simulated', canParticipate: true }] };
    let mode = 'ready', release, requested;
    let gate = new Promise(resolve => { release = resolve; }), began = new Promise(resolve => { requested = resolve; });
    await page.route(`**/api/sessions/${first.id}/readiness`, async route => {
      if (mode === 'hold') { requested(); await gate; }
      await route.fulfill({ json: mode === 'old-admission' ? { ...ready, players: [{ ...ready.players[0], admissionId: randomUUID() }] } : ready }).catch(() => {});
    });
    await page.waitForFunction(() => document.querySelector('#readiness-summary').textContent.includes('1 / 1 姿態有效'));
    check((await page.locator('#roster .ready-player').innerText()).includes('合成姿態'), 'Readiness UI labels a valid synthetic snapshot explicitly; this response is a UI fixture');
    mode = 'old-admission'; await page.waitForFunction(() => document.querySelector('#readiness-summary').textContent.includes('0 / 1'));
    check((await page.locator('#roster [data-readiness-player]').innerText()).includes('等待本次入場'), 'A response for another admission cannot turn the current roster green');
    mode = 'ready'; await page.waitForFunction(() => document.querySelector('#roster .ready-player'));
    mode = 'hold'; await began;
    await page.waitForFunction(() => document.querySelector('#readiness-summary').textContent.includes('快照已過期'));
    check(await page.locator('#roster .ready-player').count() === 0, 'Silence expires the previous green snapshot before the next HTTP response');
    await page.screenshot({ path: path.join(screenshots, 'player-readiness-stale.png'), fullPage: true });
    await page.locator('#session-select').selectOption(sessions[1].id); release();
    await page.waitForFunction(() => document.querySelector('#readiness-summary').textContent.includes('等待遊戲來源'));
    check(await page.locator('#roster .ready-player').count() === 0, 'A delayed previous-session response cannot restore its green state after selection');
    await page.screenshot({ path: path.join(screenshots, 'player-readiness-waiting.png'), fullPage: true });
    // A second delayed request must also be fenced by logout; route payloads remain UI fixtures.
    gate = new Promise(resolve => { release = resolve; }); began = new Promise(resolve => { requested = resolve; });
    mode = 'hold'; await page.locator('#session-select').selectOption(first.id); await began;
    await page.locator('#logout').click(); release();
    await page.waitForFunction(() => document.querySelector('#workspace').hidden);
    check(await page.locator('#roster tr').count() === 0 && !await page.locator('#readiness-summary').innerText().then(text => text.includes('1 / 1')), 'Logout clears readiness and ignores delayed responses from the previous identity');
  } finally {
    await page.close();
    for (const session of sessions) await api(`/sessions/${session.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
  }
};
