const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

async function holdTicketResponse(page, url, issue, mutate, settled) {
  const captured = Promise.withResolvers(), release = Promise.withResolvers(), delivered = Promise.withResolvers(), download = Promise.withResolvers();
  let issued = 0, downloads = 0, timer;
  const record = file => { downloads++; download.resolve(file); };
  const hold = async route => {
    try {
      const response = await route.fetch(); issued++;
      assert.equal(response.status(), 200);
      captured.resolve();
      await release.promise;
      await route.fulfill({ response });
      delivered.resolve();
    } catch (error) { captured.resolve(error); delivered.resolve(error); }
  };
  await page.route(url, hold); page.on('download', record);
  try {
    await issue();
    const issueError = await Promise.race([captured.promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('No original ticket response captured')), 8000);
    })]);
    if (issueError) throw issueError;
    await mutate();
    release.resolve();
    const deliveryError = await delivered.promise;
    if (deliveryError) throw deliveryError;
    const message = await settled();
    if (/已產生|已下載五房/.test(message)) await (await download.promise).delete();
    return { signedResponses: issued, downloads, message };
  } finally {
    clearTimeout(timer);
    release.resolve(); await page.unroute(url, hold); page.off('download', record);
  }
}

async function checkTicketDownloadFence({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage(), cases = [];
  captureErrors(page);
  const mission = await api('/missions', 'POST', { name: 'Ticket download roster check', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const roomId = (await api('/rooms')).find(room => !room.sessionId).id;
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [roomId] }, 'Master', 201);
  const detail = '/sessions/' + session.id, playerId = randomUUID(), playerRoute = detail + '/players/' + playerId;
  const add = name => api(detail + '/players', 'POST', { playerId, roomId, name, headset: 'Quest3' });
  let { players: [player] } = await add('Original admission');
  try {
    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    for (const scope of ['seat', 'room']) {
      const isRoom = scope === 'room', previous = player.admissionId;
      const routeUrl = base + '/api' + (isRoom ? detail + '/rooms/' + roomId + '/join-ticket-bundle' : playerRoute + '/join-ticket');
      await page.locator('#roster').filter({ hasText: player.name }).waitFor();
      await page.locator('#game-address').fill('127.0.0.1');
      if (isRoom) await page.locator('#ticket-room').selectOption(String(roomId));
      const button = isRoom ? page.locator('#download-room-tickets') : page.locator('[data-player-action=ticket]');
      const result = await holdTicketResponse(page, routeUrl, () => button.click(), async () => {
        await api(playerRoute, 'DELETE', undefined, 'Master', 204, previous);
        ({ players: [player] } = await add('Replacement for ' + scope));
        assert.notEqual(player.admissionId, previous);
      }, async () => {
        await page.waitForFunction(() => !document.querySelector('#session-select').disabled);
        return page.locator('#notice').innerText();
      });
      cases.push({ scope, replaced: player.admissionId !== previous, ...result });
      await page.locator('#refresh').click();
      await page.locator('#roster').filter({ hasText: player.name }).waitFor();
    }
    await fs.writeFile(path.join(screenshots, 'ticket-download-fence.json'), JSON.stringify(cases, null, 2));
    for (const result of cases)
      check(result.signedResponses === 1 && result.replaced && result.downloads === 0 && result.message.includes('名冊已變更'),
        `A signed ${result.scope} download is discarded after another operator replaces the original admission`);
  } finally {
    await page.close();
    await api(detail + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
  }
}

module.exports = { checkTicketDownloadFence, holdTicketResponse };
