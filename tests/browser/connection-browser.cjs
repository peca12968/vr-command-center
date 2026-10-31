const { randomUUID } = require('node:crypto');
const path = require('node:path');
module.exports = async ({ context, api, tokens, base, mission, screenshots, check }) => {
  const rooms = (await api('/rooms')).filter(room => !room.sessionId).slice(0, 2); if (rooms.length !== 2) throw Error('Connection UI fixture needs two free rooms');
  const sessions = [];
  for (const room of rooms) {
    let session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room.id] }, 'Master', 201);
    session = (await api(`/sessions/${session.id}/combat-stream`, 'POST', { streamId: randomUUID(), origin: 'Simulation' }, 'GameServer')).session || await api(`/sessions/${session.id}`);
    sessions.push(session);
  }
  const first = sessions[0], value = { version: 1, sessionId: first.id, streamId: first.combatStream.streamId, address: '127.0.0.1', port: 17777, sessionEnded: false };
  const page = await context.newPage(); let release, requested, hold = false;
  let gate = new Promise(resolve => { release = resolve; }), began = new Promise(resolve => { requested = resolve; });
  try {
    await page.route(`**/api/sessions/${first.id}/connection-endpoint`, async route => {
      if (hold) { requested(); await gate; }
      await route.fulfill({ json: value }).catch(() => {});
    });
    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(first.id);
    await page.waitForFunction(() => document.querySelector('#game-address').value === '127.0.0.1' && document.querySelector('#game-port').value === '17777');
    check((await page.locator('#connection-endpoint-status').innerText()).includes('僅供同機'), 'Selected source metadata fills its published address and port; this is a UI fixture');
    await page.locator('#game-address').fill('192.168.1.200'); await page.locator('#game-port').fill('19999');
    const reply = page.waitForResponse(`**/api/sessions/${first.id}/connection-endpoint`); await reply;
    check(await page.locator('#game-address').inputValue() === '192.168.1.200' && await page.locator('#game-port').inputValue() === '19999', 'Background endpoint refresh preserves manually edited connection fields');
    await page.locator('#apply-connection-endpoint').click();
    check(await page.locator('#game-port').inputValue() === '17777' && await page.locator('#game-address').inputValue() === '127.0.0.1', 'Explicit apply restores the published connection setting');
    await page.screenshot({ path: path.join(screenshots, 'connection-endpoint.png'), fullPage: true });
    hold = true; await began;
    await page.locator('#session-select').selectOption(sessions[1].id); release();
    await page.waitForFunction(() => document.querySelector('#connection-endpoint-status').textContent.includes('尚未公布'));
    check(await page.locator('#game-address').inputValue() === '' && await page.locator('#game-port').inputValue() === '7777', 'Selection clears another session port and ignores its late response');
    gate = new Promise(resolve => { release = resolve; }); began = new Promise(resolve => { requested = resolve; });
    await page.locator('#session-select').selectOption(first.id); await began;
    await page.locator('#logout').click(); release();
    check(await page.locator('#game-address').inputValue() === '' && await page.locator('#workspace').isHidden(), 'Logout clears connection drafts and fences the previous source response');
  } finally {
    await page.close();
    for (const session of sessions) {
      await api(`/sessions/${session.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
      await api(`/sessions/${session.id}/combat-stream/seal`, 'POST', { streamId: session.combatStream.streamId, finalSequence: 0 }, 'GameServer');
    }
  }
};
