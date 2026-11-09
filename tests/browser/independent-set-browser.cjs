const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function independentSetBrowser({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage(), roomPage = await context.newPage();
  captureErrors(page); captureErrors(roomPage);
  const endpoint = '**/api/sessions/independent-set';
  const mode = page.locator('#launch-mode'), missionList = page.locator('#launch-mission');
  const submit = page.locator('#create-session-form button'), notice = page.locator('#notice');
  const owned = new Set();
  async function open(target, role) {
    await target.goto(base + '/console/');
    await target.locator('#login-key').fill(tokens[role]);
    await target.locator('#login-form button').click();
    await target.locator('#rooms .room-card').first().waitFor();
  }
  async function end(id) { await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' }); }
  const valid = () => page.locator('#launch-layout-summary[data-status=valid]').waitFor();
  const enabled = () => page.waitForFunction(() => !document.querySelector('#create-session-form button').disabled, null, { polling: 100 });
  const draft = { name: '五房同步準備測試', briefing: '固定的原始版本', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Rain', timeOfDay: 'Night', lightning: false },
    enemies: { count: 2, behavior: 'Hold', autoAttack: false }, props: [] };
  try {
    assert.deepEqual(await api('/sessions'), []);
    const mission = await api('/missions', 'POST', draft, 'Master', 201);
    await open(roomPage, 'Room2');
    await api('/sessions/independent-set', 'POST', { missionId: mission.id }, 'Room2', 403, undefined, randomUUID());
    check(await roomPage.locator('#launch-mode option[value=IndependentSet]').evaluate(option => option.disabled), 'A room console cannot prepare the five-room set');
    await open(page, 'Master');
    await missionList.selectOption(mission.id); await mode.selectOption('IndependentSet'); await valid(); await enabled();
    check(await page.locator('#launch-room').isDisabled() && (await page.locator('#launch-preview-rooms').innerText()) === '房間 1、房間 2、房間 3、房間 4、房間 5'
      && (await page.locator('#launch-preview-enemies').innerText()).startsWith('各場 2 名') && (await submit.innerText()).includes('五個準備場次'),
    'Five-room preparation previews all rooms and the full enemy count in each independent session');
    await page.locator('#launch-preview').screenshot({ path: path.join(screenshots, 'independent-set-preview.png') });

    let blocker;
    async function occupy(route) {
      blocker = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [4] }, 'Master', 201);
      owned.add(blocker.id);
      await route.continue();
    }
    await page.route(endpoint, occupy, { times: 1 });
    await submit.click(); await notice.filter({ hasText: '房間 4 使用中，五場都未建立' }).waitFor();
    check((await api('/sessions')).map(session => session.id).join() === blocker.id && await page.locator('#pending-command').isHidden(),
      'A room reserved after the preview rejects the whole batch with the exact occupied room');
    await end(blocker.id); await page.locator('#refresh').click(); await enabled();

    const dense = await api('/missions', 'POST', { ...draft, name: '五房獨立容量測試', enemies: { ...draft.enemies, count: 100 },
      props: [2, 4].flatMap(z => [-3, -1, 1, 3].map(x => ({ assetId: 'sandbag', position: { x, y: 0, z }, yawDegrees: 0 }))) }, 'Master', 201);
    await page.locator('#refresh').click(); await missionList.selectOption(dense.id);
    await page.locator('#launch-layout-summary[data-status=invalid]').waitFor();
    check(await submit.isDisabled(), 'Five independent rooms use independent layout limits');
    await mode.selectOption('Linked'); await valid(); await enabled();
    check(await submit.isEnabled(), 'The same dense mission can still use the separate linked layout check');
    await mode.selectOption('IndependentSet'); await missionList.selectOption(mission.id); await valid(); await enabled();

    const requests = []; let committed;
    async function intercept(route) {
      requests.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() });
      if (requests.length === 1) {
        await api(`/missions/${mission.id}/revisions`, 'POST', { ...draft, briefing: '建立請求送出後的新版本' }, 'Master', 201, undefined, randomUUID());
        const actual = await route.fetch();
        assert.equal(actual.status(), 201);
        committed = await actual.json();
        for (const session of committed.sessions) owned.add(session.id);
        await route.abort('failed');
      } else {
        const actual = await route.fetch();
        assert.equal(actual.status(), 200);
        assert.equal((await actual.json()).duplicate, true);
        await route.fulfill({ response: actual });
      }
    }
    await page.route(endpoint, intercept);
    await submit.click(); await notice.filter({ hasText: '結果未確認' }).waitFor();
    const original = committed.sessions.map(session => session.id);
    check(await page.locator('#pending-command').isVisible() && await page.locator('#refresh').isDisabled()
      && (await api('/sessions')).length === 5, 'A lost creation reply keeps the original request pending after the actual commit');
    await page.locator('#retry-command').click(); await notice.filter({ hasText: '五個獨立場次已確認' }).waitFor();
    assert.deepEqual(requests[0], requests[1]);
    assert.ok(requests[0].key);
    check((await api('/rooms')).map(room => room.sessionId).join() === original.join() && await page.locator('#session-select').inputValue() === original[0]
      && committed.sessions.every(session => session.mission.id === mission.id && session.mission.definition.briefing === draft.briefing
        && session.mode === 'Independent' && session.state === 'Preparing'), 'Retry restores exactly the five original IDs and saved revision even after the mission head changes');
    await page.unroute(endpoint, intercept);
    await page.locator('#rooms').screenshot({ path: path.join(screenshots, 'independent-set-prepared.png') });

    await roomPage.locator('#refresh').click(); await roomPage.locator('#session-panel').waitFor();
    check(await roomPage.locator('#rooms .room-card').count() === 1 && await roomPage.locator('#session-select').inputValue() === original[1],
      'Room control sees only its own newly prepared independent session');
    roomPage.once('dialog', dialog => dialog.accept()); await roomPage.locator('[data-command=End]').click();
    await roomPage.locator('#session-phase').filter({ hasText: '已結束' }).waitFor();
    const active = await api('/sessions');
    check(active.length === 4 && active.every(session => original.includes(session.id) && session.id !== original[1] && session.state === 'Preparing'),
      'Ending one room leaves the other four prepared sessions intact');
  } finally {
    await page.unroute(endpoint);
    for (const id of owned) if ((await api(`/sessions/${id}`)).state !== 'Ended') await end(id);
    await page.close(); await roomPage.close();
  }
};
