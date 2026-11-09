const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async ({ context, api, tokens, base, screenshots, check, captureErrors }) => {
  const page = await context.newPage();
  captureErrors(page);
  const route = '**/api/venue/phase';
  const active = new Set();
  const panel = page.locator('#venue-phase'), summary = page.locator('#venue-phase-targets');
  const notice = page.locator('#notice');
  const run = (id, action) => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action });
  async function start(id, room) {
    await api(`/sessions/${id}/players`, 'POST', { playerId: randomUUID(), roomId: room, name: 'Venue seat', headset: 'Quest3' });
    await run(id, 'Begin');
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

  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', { name: '全館暫停測試', briefing: '', durationSeconds: 180,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    const created = await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Master', 201, undefined, randomUUID());
    const ids = created.sessions.map(session => session.id);
    for (const id of ids) active.add(id);
    for (const [index, id] of ids.slice(0, 3).entries()) await start(id, index + 1);
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
    await run(ids[1], 'Resume'); await run(ids[1], 'Pause');
    await page.locator('#refresh').click(); await summary.filter({ hasText: /^可暫停 無 · 可繼續 房間 1$/ }).waitFor();
    await panel.screenshot({ path: path.join(screenshots, 'venue-phase-resume.png') });
    await click('resume', '房間 1'); await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    const states = await Promise.all(ids.map(id => api(`/sessions/${id}`).then(session => session.state)));
    check(states.join(',') === 'Running,Paused,Paused,Preparing,Ended', 'Resume affects only a room still in its whole-venue paused phase');
    for (const id of ids.slice(0, 4)) await end(id);

    const linked = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] }, 'Master', 201);
    active.add(linked.id); await start(linked.id, 1);
    await page.locator('#refresh').click(); await summary.filter({ hasText: '可暫停 房間 1、2、3、4、5' }).waitFor();
    await click('pause', '1、2、3、4、5 的 1 個場次'); await notice.filter({ hasText: '全館管理命令已確認' }).waitFor();
    check((await api(`/sessions/${linked.id}/events`)).filter(event => event.venue).length === 1,
      'A linked venue sends one transition for all five rooms');
  } finally {
    await page.unroute(route); await page.close();
    for (const id of active) await end(id);
  }
};
