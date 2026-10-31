const { randomUUID } = require('node:crypto');
const path = require('node:path');
module.exports = async ({ context, api, tokens, base, mission, screenshots, check }) => {
  const room = (await api('/rooms')).find(value => !value.sessionId);
  if (!room) throw new Error('Clock browser fixture needs its own free room');
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room.id] }, 'Master', 201);
  const page = await context.newPage();
  try {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    await page.waitForFunction(() => !document.querySelector('#session-panel').hidden);
    check(await page.locator('#clock-fields').evaluate(node => node.disabled), 'Clock policy waits for an attached capable source');
    const streamId = randomUUID();
    await api(`/sessions/${session.id}/combat-stream`, 'POST', { streamId, origin: 'Simulation', missionClockVersion: 1 }, 'GameServer');
    await page.locator('#refresh').click(); await page.waitForFunction(() => !document.querySelector('#clock-fields').disabled);
    await page.locator('#clock-auto-end').check();
    await page.locator('#refresh').click();
    check(await page.locator('#clock-auto-end').isChecked() && !(await api(`/sessions/${session.id}`)).missionClock, 'Background refresh preserves a clock draft without applying it');
    let once = true; const requests = [];
    await page.route('**/api/sessions/*/commands', async route => {
      const body = route.request().postDataJSON();
      if (body.action !== 'SetMissionClock') return route.continue();
      requests.push(body);
      if (once) { once = false; await route.fetch(); await route.abort('failed'); }
      else await route.continue();
    });
    await page.locator('#clock-form button[type=submit]').click();
    await page.waitForFunction(() => !document.querySelector('#pending-command').hidden);
    await page.locator('#retry-command').click();
    await page.waitForFunction(() => document.querySelector('#pending-command').hidden);
    check(requests.length === 2 && JSON.stringify(requests[0]) === JSON.stringify(requests[1]) && (await api(`/sessions/${session.id}`)).missionClock.autoEnd,
      'A lost clock response retries the exact accepted command once');
    await api(`/sessions/${session.id}/commands`, 'POST', { commandId: randomUUID(), action: 'SetMissionClock', missionClock: { autoEnd: false } });
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#clock-status').textContent.includes('手動結束'));
    check(await page.locator('#clock-auto-end').isChecked() && (await page.locator('#clock-status').innerText()).includes('手動結束'), 'Server policy status stays distinct from the retained checkbox draft');
    await page.locator('#reload-clock').click();
    check(!await page.locator('#clock-auto-end').isChecked(), 'Explicit reload discards the clock draft and loads the accepted policy');
    await page.screenshot({ path: path.join(screenshots, 'mission-clock.png'), fullPage: true });
    await api(`/sessions/${session.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
    await api(`/sessions/${session.id}/combat-stream/seal`, 'POST', { streamId, finalSequence: 0 }, 'GameServer');
    await page.locator('#include-ended').check(); await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已結束');
    check(await page.locator('#clock-fields').evaluate(node => node.disabled), 'Ended history cannot change its mission clock policy');
  } finally { await page.close(); }
};
