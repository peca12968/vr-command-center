const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function independentSetBrowser({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage(), roomPage = await context.newPage();
  captureErrors(page); captureErrors(roomPage);
  const endpoint = '**/api/sessions/independent-set';
  const mode = page.locator('#launch-mode'), missionList = page.locator('#launch-mission');
  const submit = page.locator('#create-session-form button'), notice = page.locator('#notice');
  const receipt = page.locator('#launch-independent-receipt');
  const receiptRows = () => page.locator('#launch-independent-receipt-rows tr').evaluateAll(rows => rows.map(row => ({
    missionId: row.dataset.missionId, cells: [...row.cells].map(cell => cell.textContent) })));
  async function confirmPlan(accept) {
    const pending = page.waitForEvent('dialog', { timeout: 5000 }).then(async dialog => {
      const message = dialog.message();
      if (accept) await dialog.accept(); else await dialog.dismiss();
      return message;
    });
    const [message] = await Promise.all([pending, submit.click()]);
    return message;
  }
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
    const originalReceipt = await receiptRows();
    check(await receipt.isVisible() && originalReceipt.length === 5 && originalReceipt.every((row, index) => row.missionId === mission.id
      && row.cells.join('|') === `房間 ${index + 1}|${draft.name} · 第 1 版|VR · 600 秒|${original[index]}`),
      'The confirmed uniform batch shows all five original session IDs and saved versions');
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
    for (const session of active) await end(session.id);
    const head = (await api(`/missions/${mission.id}/history`)).headId;
    const alternateDraft = { ...draft, name: '房間各自的夜戰版本', durationSeconds: 420, environment: { ...draft.environment, mode: 'MR', weather: 'Storm', lightning: true },
      props: [{ assetId: 'barrel', position: { x: 2, y: 0, z: 1 }, yawDegrees: 45 }] };
    const alternate = await api('/missions', 'POST', alternateDraft, 'Master', 201);
    const overlap = await api('/missions', 'POST', { ...draft, name: '重疊配置', props: [
      { assetId: 'sandbag', position: { x: 0, y: 0, z: 2 }, yawDegrees: 0 },
      { assetId: 'barrel', position: { x: 0, y: 0, z: 2 }, yawDegrees: 0 }
    ] }, 'Master', 201);
    await page.locator('#refresh').click();
    await missionList.selectOption(head);
    await page.locator('#launch-room-missions-toggle').check();
    const roomMission = room => page.locator('#launch-room-mission-' + room);
    const roomLayout = room => page.locator('#launch-room-layout-' + room);
    const previewRoom = page.locator('#launch-review-room');
    const overview = page.locator('#launch-room-layouts');
    const card = room => overview.locator(`[data-room-layout-preview="${room}"]`);
    await enabled();
    check(await roomMission(1).inputValue() === head && await roomMission(5).inputValue() === head,
      'Enabling room assignments starts from the explicitly selected shared version');
    await overview.locator('summary').click();
    await card(5).locator('svg').waitFor();
    check(await overview.locator('svg[viewBox="-11 -11 22 22"]').count() === 5
      && await overview.locator('.room-layout-spawns [data-seat]').count() === 25
      && await roomPage.locator('#launch-room-layouts').isHidden(),
      'The Master can compare five saved rooms at the same scale with their authoritative spawn locations');
    await roomMission(4).selectOption(dense.id);
    await roomLayout(4).filter({ hasText: '場地配置未通過' }).waitFor();
    await previewRoom.selectOption('1'); await valid();
    check(await submit.isDisabled() && (await api('/sessions')).length === 0,
      'An invalid fourth room blocks creation even while another room’s map is valid');

    let releaseLayout, finishLayout, layoutStarted = false;
    const layoutGate = new Promise(resolve => { releaseLayout = resolve; });
    const layoutDone = new Promise(resolve => { finishLayout = resolve; });
    const layoutRoute = `**/api/missions/${overlap.id}/layout?mode=Independent`;
    const holdLayout = async route => {
      layoutStarted = true;
      try { const response = await route.fetch(); await layoutGate; await route.fulfill({ response }); }
      finally { finishLayout(); }
    };
    await page.route(layoutRoute, holdLayout);
    try {
      const request = page.waitForRequest(layoutRoute);
      await roomMission(4).selectOption(overlap.id); await request;
      check(await card(4).locator('svg').count() === 0 && await card(4).locator('[data-status=pending]').count() === 1
        && await card(1).locator('svg').count() === 1,
        'Changing one saved assignment immediately clears its old map while other maps remain visible');
      await roomMission(4).selectOption(alternate.id); await card(4).locator('.room-layout-props [data-index="0"]').waitFor();
    } finally { releaseLayout(); if (layoutStarted) await layoutDone; await page.unroute(layoutRoute, holdLayout); }
    check(await card(4).getAttribute('data-mission-id') === alternate.id && await card(4).locator('[data-status=valid]').count() === 1,
      'A held response from a replaced assignment cannot change the new room map');
    await roomMission(4).selectOption(overlap.id);
    await card(4).locator('[data-status=invalid]').waitFor();
    check(await card(4).locator('[data-layout-invalid=true]').count() === 2 && await submit.isDisabled(),
      'The overview marks both overlapping props from the exact saved report and retains the original launch gate');
    for (const room of [2, 4, 5]) await roomMission(room).selectOption(alternate.id);
    await enabled();
    await card(5).getByRole('button').click();
    check(await page.locator('#launch-preview-rooms').innerText() === '房間 5'
      && await page.locator('#launch-preview-duration').innerText() === '420 秒'
      && (await page.locator('#launch-preview-environment').innerText()).includes('暴風雨')
      && await page.locator('#launch-layout-map-details').evaluate(node => node.open)
      && await page.locator('#launch-layout-props [data-index="0"]').getAttribute('transform') === 'translate(2 -1) rotate(45)'
      && await card(2).locator('.room-layout-props [data-index="0"]').getAttribute('transform') === 'translate(2 -1) rotate(45)'
      && await card(1).locator('.room-layout-props [data-index]').count() === 0,
      'Each room preview reflects its exact assigned duration, environment and saved geometry');
    await overview.screenshot({ path: path.join(screenshots, 'independent-room-layouts.png') });
    await page.locator('#launch-room-missions').screenshot({ path: path.join(screenshots, 'independent-room-missions.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await roomMission(5).isVisible() && await card(5).locator('svg').isVisible()
      && await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      'All five assignment controls fit the mobile console without horizontal overflow');
    await page.setViewportSize({ width: 1440, height: 1080 });
    const alternateHead = await api(`/missions/${alternate.id}/revisions`, 'POST', { ...alternateDraft, durationSeconds: 450 }, 'Master', 201, undefined, randomUUID());
    await page.locator('#refresh').click(); await roomMission(4).selectOption(alternateHead.id); await enabled();
    await page.locator('#tab-missions').click(); await page.locator('#edit-mission').selectOption(alternateHead.id); await page.locator('#load-mission').click();
    await page.waitForFunction(() => document.querySelector('#draft-duration').value === '450' && !document.querySelector('#mission-fields').disabled);
    await page.locator('#mission-version').selectOption(alternate.id); await page.locator('#compare-version').click();
    await page.locator('#launch-compared-version').click(); await enabled();
    check(await previewRoom.inputValue() === '4' && await roomMission(4).inputValue() === alternate.id && await roomMission(2).inputValue() === alternate.id
      && await roomMission(1).inputValue() === head && await page.locator('#draft-duration').inputValue() === '450'
      && (await roomLayout(4).innerText()).includes('MR · 420 秒'),
      'A compared historical version applies only to the previewed room and keeps the newer editor draft');
    const plan = [head, alternate.id, head, alternate.id, alternate.id].map((missionId, index) => ({ roomId: index + 1, missionId }));
    let mixed, sent, attempts = 0;
    await page.route(endpoint, async route => {
      attempts++;
      const current = { key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() };
      assert.deepEqual(current.body, { rooms: plan });
      if (!sent) {
        sent = current;
        const actual = await route.fetch();
        assert.equal(actual.status(), 201);
        mixed = await actual.json();
        for (const session of mixed.sessions) owned.add(session.id);
        await api(`/missions/${alternateHead.id}/revisions`, 'POST', { ...alternateDraft, durationSeconds: 480 }, 'Master', 201, undefined, randomUUID());
        await route.abort('failed');
      } else {
        assert.deepEqual(current, sent);
        const actual = await route.fetch();
        assert.equal(actual.status(), 200);
        const result = await actual.json();
        assert.equal(result.duplicate, true);
        if (attempts === 2) {
          result.sessions[3].mission.definition.durationSeconds = 480;
          await route.fulfill({ status: 200, json: result });
        } else await route.fulfill({ response: actual });
      }
    });
    const cancelled = await confirmPlan(false);
    check(plan.every(({ roomId, missionId }) => cancelled.includes(`房間 ${roomId}　${missionId === head
      ? `${draft.name} · 第 2 版 · VR · 600 秒` : `${alternateDraft.name} · 第 1 版 · MR · 420 秒`}`))
      && attempts === 0 && (await api('/sessions')).length === 0 && await roomMission(4).inputValue() === alternate.id,
      'Cancelling confirmation for the exact five saved versions leaves rooms free and sends no write');
    check(await confirmPlan(true) === cancelled, 'Confirmation submits the same five assignments that the operator reviewed');
    await notice.filter({ hasText: '結果未確認' }).waitFor();
    check(await roomMission(4).isDisabled() && await previewRoom.isDisabled() && JSON.stringify(await receiptRows()) === JSON.stringify(originalReceipt),
      'An unresolved mixed request locks its room assignments and retains only the last confirmed receipt');
    await page.locator('#retry-command').click();
    await page.waitForFunction(() => !document.querySelector('#retry-command').disabled && !document.querySelector('#pending-command').hidden, null, { polling: 100 });
    check(attempts === 2 && JSON.stringify(await receiptRows()) === JSON.stringify(originalReceipt),
      'A retry receipt with a different duration cannot replace the last confirmed batch');
    await page.locator('#retry-command').click(); await notice.filter({ hasText: '五個獨立場次已確認' }).waitFor();
    check(mixed.sessions.every((session, index) => session.roomIds[0] === index + 1 && session.mission.id === plan[index].missionId)
      && mixed.sessions[3].mission.definition.durationSeconds === 420
      && await roomMission(4).inputValue() === alternate.id && (await roomMission(4).locator('option:checked').innerText()).includes('歷史')
      && (await api('/rooms')).every((room, index) => room.sessionId === mixed.sessions[index].id),
      'A mixed retry keeps all original sessions and the assigned historical version after a library revision');
    const rows = await receiptRows();
    check(rows.length === 5 && rows.every((row, index) => row.missionId === plan[index].missionId
      && row.cells.join('|') === (row.missionId === head ? `房間 ${index + 1}|${draft.name} · 第 2 版|VR · 600 秒|${mixed.sessions[index].id}`
        : `房間 ${index + 1}|${alternateDraft.name} · 第 1 版|MR · 420 秒|${mixed.sessions[index].id}`)),
      'The confirmed mixed receipt identifies the exact accepted VR and MR versions and session IDs');
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'The receipt keeps its table scroll inside the mobile viewport');
    await receipt.screenshot({ path: path.join(screenshots, 'independent-mixed-receipt.png') });
    await page.locator('#logout').click();
    check(await receipt.evaluate(node => node.hidden) && (await receiptRows()).length === 0
      && await overview.isHidden() && await overview.locator('svg, [data-mission-id], [data-status]').count() === 0
      && (await overview.locator('[data-room-layout-preview] p').allTextContents()).every(value => value === ''),
    'Logout clears the confirmed receipt and all five saved previews, including labels and version identifiers');
  } finally {
    await page.unroute(endpoint);
    for (const id of owned) if ((await api(`/sessions/${id}`)).state !== 'Ended') await end(id);
    await page.close(); await roomPage.close();
  }
};
