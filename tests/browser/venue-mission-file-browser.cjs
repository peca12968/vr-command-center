const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');

module.exports = async function venueMissionFileBrowser({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage();
  captureErrors(page);
  const mode = page.locator('#launch-mode'), mission = page.locator('#launch-mission');
  const panel = page.locator('#launch-mission-file-panel'), input = page.locator('#venue-missions-file');
  const save = page.locator('#download-venue-missions'), load = page.locator('#load-venue-missions');
  const preview = page.locator('#preview-venue-missions'), review = page.locator('#venue-missions-review');
  const applyRoom = page.locator('#use-venue-mission-room');
  const applySelected = page.locator('#use-selected-venue-mission-rooms');
  const roomCheckbox = room => review.locator(`[data-venue-mission-file-room="${room}"]`);
  const reviewRows = review.locator('tbody tr');
  const maps = page.locator('#venue-missions-maps'), mapRoom = page.locator('#venue-missions-map-room');
  const currentMap = maps.locator('[data-source=current]'), fileMap = maps.locator('[data-source=file]');
  const status = page.locator('#venue-missions-file-status'), create = page.locator('#create-session-form button[type=submit]');
  const choices = page.locator('#launch-room-missions-fields select');
  const selected = () => choices.evaluateAll(fields => fields.map(field => field.value));
  const selectedFile = async value => {
    await input.setInputFiles({ name: 'configuration.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(value)) });
    await load.click();
  };
  const savedFile = async name => {
    const event = page.waitForEvent('download');
    await save.click();
    const file = await event;
    assert.equal(file.suggestedFilename(), name);
    const target = path.join(screenshots, name);
    await file.saveAs(target);
    return { target, value: JSON.parse(await fs.readFile(target, 'utf8')) };
  };
  const login = async role => {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  };
  const template = { name: '配置檔保存任務', briefing: '事先準備五房配置', durationSeconds: 360,
    environment: { mode: 'VR', weather: 'Rain', timeOfDay: 'Night', lightning: false },
    enemies: { count: 2, behavior: 'Hold', autoAttack: false },
    props: [{ assetId: 'barrel', position: { x: 2, y: 0, z: 2 }, yawDegrees: 30 }] };
  const end = id => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
  const active = new Set();
  try {
    assert.deepEqual(await api('/sessions'), []);
    const a = await api('/missions', 'POST', template, 'Master', 201);
    const b = await api('/missions', 'POST', { ...template, name: '配置檔 MR 任務', durationSeconds: 420,
      environment: { ...template.environment, mode: 'MR', weather: 'Storm', lightning: true },
      enemies: { count: 4, behavior: 'Patrol', autoAttack: true } }, 'Master', 201);
    await login('Room2');
    check(await panel.isHidden(), 'Room control has no venue mission file controls');
    await login('Master');
    await panel.locator('summary').click();
    check(await save.isDisabled() && await load.isDisabled() && await preview.isDisabled(),
      'A single room and an empty file selection cannot save, review or load a venue configuration');
    await mission.selectOption(a.id);
    await mode.selectOption('Linked');
    const linked = await savedFile('vr-venue-missions-linked.json');
    const rooms = ids => ids.map((missionId, index) => ({ roomId: index + 1, missionId }));
    assert.deepEqual(linked.value, { schemaVersion: 1, mode: 'Linked', rooms: rooms(Array(5).fill(a.id)) });
    await mode.selectOption('IndependentSet');
    await page.locator('#launch-room-missions-toggle').check();
    await choices.nth(1).selectOption(b.id);
    await choices.nth(4).selectOption(b.id);
    const independent = await savedFile('vr-venue-missions-independent.json');
    const ids = [a.id, b.id, a.id, a.id, b.id];
    assert.deepEqual(independent.value, { schemaVersion: 1, mode: 'IndependentSet', rooms: rooms(ids) });
    check((await api('/sessions')).length === 0, 'Both downloaded configuration files contain only version assignments and need no prior session');

    const savedPlan = await api('/venue/mission-plans', 'POST', { name: '原保存配置', mode: 'IndependentSet', missionIds: ids }, 'Master', 200, undefined, randomUUID());
    const savedPanel = page.locator('#saved-venue-mission-plans');
    const savedChoice = page.locator('#saved-venue-plan');
    await mode.selectOption('Linked');
    await mission.selectOption(a.id);
    const planList = '**/api/venue/mission-plans';
    await page.route(planList, route => route.fulfill({ status: 200,
      json: [{ ...savedPlan, plan: { ...savedPlan.plan, missionIds: [...ids.slice(0, 4), a.id] } }] }));
    try {
      await savedPanel.locator('summary').click();
      await savedChoice.selectOption(savedPlan.id);
      await page.locator('#load-venue-plan').click();
      await page.locator('#notice').filter({ hasText: '無法核對原五房配置' }).waitFor();
      check(await mode.inputValue() === 'Linked' && await mission.inputValue() === a.id,
        'Substituting a valid version in a saved list row cannot replace the current preparation');
    } finally { await page.unroute(planList); }
    await page.locator('#refresh-venue-plans').click();
    await page.locator('#preview-venue-plan').click();
    await savedPanel.locator('#venue-missions-review').waitFor();
    check(await mode.inputValue() === 'Linked' && await mission.inputValue() === a.id
      && JSON.stringify(await reviewRows.evaluateAll(rows => rows.map(row => row.dataset.fileMission))) === JSON.stringify(ids)
      && (await review.innerText()).includes('保存配置指定'), 'Previewing a saved plan compares all five original versions without applying them');
    await page.locator('#load-venue-plan').click();
    await page.locator('#venue-plan-status').filter({ hasText: '已載入「原保存配置」' }).waitFor();
    check(await mode.inputValue() === 'IndependentSet' && JSON.stringify(await selected()) === JSON.stringify(ids),
      'Reading the exact original plan restores all five ordered versions');

    const head = await api(`/missions/${a.id}/revisions`, 'POST', { ...template, durationSeconds: 690,
      props: [{ assetId: 'sandbag', position: { x: -2, y: 0, z: 1 }, yawDegrees: -30 }],
      environment: { ...template.environment, weather: 'Fog', timeOfDay: 'Day' },
      enemies: { count: 0, behavior: 'Advance', autoAttack: false } },
      'Master', 201, undefined, randomUUID());
    const invalidLayout = await api('/missions', 'POST', { ...template, name: '未修正配置',
      props: [template.props[0], template.props[0]] }, 'Master', 201);
    const blocker = await api('/sessions', 'POST', { mode: 'Independent', roomIds: [3], missionId: a.id }, 'Master', 201);
    active.add(blocker.id);
    await login('Master');
    await page.locator('#tab-missions').click();
    await page.locator('#edit-mission').selectOption(head.id);
    await page.locator('#load-mission').click();
    const draft = page.locator('#draft-duration');
    await page.waitForFunction(() => document.querySelector('#draft-duration').value === '690' && !document.querySelector('#mission-fields').disabled);
    await draft.fill('691');
    await page.locator('#tab-operations').click();
    await panel.locator('summary').click();
    await mission.selectOption(head.id);
    await page.locator('#launch-room').selectOption('1');
    await input.setInputFiles(independent.target);
    await preview.click();
    await review.waitFor();
    check(await mode.inputValue() === 'Independent' && await mission.inputValue() === head.id && await draft.inputValue() === '691'
      && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'Reviewing a file preserves the active preparation, draft and existing sessions');
    const expectedReview = ids.map((id, index) => [index === 0 ? head.id : '', id]);
    assert.deepEqual(await reviewRows.evaluateAll(rows => rows.map(row => [row.dataset.currentMission, row.dataset.fileMission])), expectedReview);
    check((await reviewRows.nth(0).innerText()).includes('第 1 版（歷史）')
      && (await reviewRows.nth(1).innerText()).includes('MR · 420 秒')
      && await reviewRows.locator('[data-status=valid]').count() === 5
      && (await review.innerText()).includes('目前為單房獨立，檔案指定五房各自獨立'),
      'The review shows exact original assignments, historical versions, MR duration and each original layout result');
    const climate = (column, index) => reviewRows.nth(index).locator(`td:nth-child(${column}) .mission-file-climate`).textContent();
    check(await climate(2, 0) === '濃霧 · 白天 · 閃電關閉' && await climate(3, 0) === '下雨 · 夜晚 · 閃電關閉'
      && await climate(3, 1) === '暴風雨 · 夜晚 · 閃電開啟',
      'The file review distinguishes saved historical weather, time of day and lightning from the current revision');
    const enemies = (column, index) => reviewRows.nth(index).locator(`td:nth-child(${column}) .mission-file-enemies`).textContent();
    check(await enemies(2, 0) === '0 名 · 推進 · 自動攻擊關閉' && await enemies(3, 0) === '2 名 · 守備 · 自動攻擊關閉'
      && await enemies(3, 1) === '4 名 · 巡邏 · 自動攻擊開啟',
      'The file review compares the exact saved historical and current enemy settings');
    await currentMap.locator('[data-seat]').first().waitFor();
    check(await mapRoom.inputValue() === '1' && await currentMap.getAttribute('data-mission-id') === head.id
      && await fileMap.getAttribute('data-mission-id') === a.id && await currentMap.locator('svg').getAttribute('viewBox') === await fileMap.locator('svg').getAttribute('viewBox')
      && await currentMap.locator('.room-layout-props [data-index="0"]').getAttribute('transform') === 'translate(-2 -1) rotate(-30)'
      && await fileMap.locator('.room-layout-props [data-index="0"]').getAttribute('transform') === 'translate(2 -2) rotate(30)'
      && await currentMap.locator('[data-seat]').count() === 5 && await fileMap.locator('[data-seat]').count() === 5,
      'The room comparison plots both original versions, exact object transforms and all five spawn slots at the same scale');
    await mapRoom.selectOption('2');
    check(await currentMap.locator('svg').count() === 0 && await fileMap.getAttribute('data-mission-id') === b.id
      && (await fileMap.locator('svg').getAttribute('aria-label')).startsWith('房間 2') && await mission.inputValue() === head.id,
      'An unassigned current room shows only the incoming MR map and leaves preparation unchanged');
    await mode.selectOption('Linked');
    check(await reviewRows.locator('td:nth-child(2)').evaluateAll(cells => cells.every(cell => cell.textContent.includes('第 2 版')))
      && (await review.innerText()).includes('目前為五房全連線'),
      'Changing the current plan updates the comparison while the file assignments stay fixed');
    await currentMap.locator('[data-seat]').first().waitFor();
    check(await mapRoom.inputValue() === '2' && await currentMap.getAttribute('data-mission-id') === head.id
      && await fileMap.getAttribute('data-mission-id') === b.id && await draft.inputValue() === '691',
      'Changing current topology updates the selected room map while the incoming assignment and draft stay pinned');
    await maps.screenshot({ path: path.join(screenshots, 'venue-mission-file-maps.png') });
    check(await maps.locator('article').evaluateAll(([before, after]) => before.offsetTop === after.offsetTop
      && before.offsetWidth === after.offsetWidth && before.offsetLeft < after.offsetLeft),
      'Desktop comparison places both plans side by side at equal width');
    await review.screenshot({ path: path.join(screenshots, 'venue-mission-file-review.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      'A narrow screen keeps the preview table inside its own scroll region');
    check(await maps.locator('article').evaluateAll(([before, after]) => before.offsetTop < after.offsetTop
      && before.offsetWidth === after.offsetWidth), 'Narrow comparison stacks both maps at equal width');
    await page.setViewportSize({ width: 1440, height: 1080 });
    check(await applyRoom.isHidden(), 'A linked preparation cannot apply individual file rooms');
    await mode.selectOption('IndependentSet');
    const toggle = page.locator('#launch-room-missions-toggle');
    assert.equal(await toggle.isChecked(), false);
    await applyRoom.click();
    await status.filter({ hasText: '已套用房間 2' }).waitFor();
    assert.deepEqual(await selected(), [head.id, b.id, head.id, head.id, head.id]);
    check(await toggle.isChecked() && await applyRoom.isDisabled() && await mapRoom.inputValue() === '2'
      && await page.locator('#launch-review-room').inputValue() === '2' && await draft.inputValue() === '691',
      'Applying room 2 keeps the common version in the other four rooms and preserves the draft');
    await mapRoom.selectOption('1');
    await applyRoom.click();
    assert.deepEqual(await selected(), [a.id, b.id, head.id, head.id, head.id]);
    check(await page.locator('#launch-review-room').inputValue() === '1' && await create.isDisabled()
      && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'Applying a second room keeps earlier selections and creates no sessions');
    assert(await applySelected.isDisabled() && await roomCheckbox(1).isDisabled());
    await roomCheckbox(5).check(); await roomCheckbox(3).check();
    await applySelected.click();
    await status.filter({ hasText: '已套用房間 3、5' }).waitFor();
    assert.deepEqual(await selected(), [a.id, b.id, a.id, head.id, b.id]);
    check(await applySelected.isDisabled() && await draft.inputValue() === '691' && await create.isDisabled()
      && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'Applying checked rooms preserves the other exact assignments, the draft and the occupied-room gate');
    await roomCheckbox(4).check();
    await mode.selectOption('Linked');
    assert(await applySelected.isHidden());
    await mode.selectOption('IndependentSet');
    check(!await roomCheckbox(4).isChecked() && await applySelected.isDisabled(),
      'Changing topology clears checked file rooms without applying them');
    await mode.selectOption('Linked');
    const withInvalidLayout = structuredClone(independent.value);
    withInvalidLayout.rooms[4].missionId = invalidLayout.id;
    const waitingLayout = url => url.pathname === `/api/missions/${invalidLayout.id}/layout` && url.searchParams.get('mode') === 'Linked';
    let releaseLayout;
    const layoutGate = new Promise(resolve => { releaseLayout = resolve; });
    const holdLayout = async route => { await layoutGate; await route.continue(); };
    await page.route(waitingLayout, holdLayout, { times: 1 });
    try {
      await Promise.all([page.waitForRequest(request => waitingLayout(new URL(request.url()))), mission.selectOption(invalidLayout.id)]);
      check(await currentMap.getAttribute('data-mission-id') === invalidLayout.id && await currentMap.locator('svg').count() === 1
        && await currentMap.locator('[data-seat]').count() === 0 && (await currentMap.innerText()).includes('正在核對'),
        'The current map shows the exact saved props while its own spawn report is pending');
      await input.setInputFiles({ name: 'layout.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(withInvalidLayout)) });
      check(await review.isHidden() && await maps.isHidden() && await maps.locator('svg').count() === 0,
        'Choosing a different file clears the old table and maps immediately');
      const response = page.waitForResponse(reply => waitingLayout(new URL(reply.url())));
      releaseLayout();
      assert.equal((await response).status(), 200);
      await mission.selectOption(head.id);
      check(await maps.isHidden() && await maps.locator('svg').count() === 0,
        'A completed old layout read cannot restore maps after replacing the file');
    } finally { releaseLayout(); await page.unroute(waitingLayout, holdLayout); }
    await preview.click();
    await review.waitFor();
    check(await reviewRows.last().locator('[data-status=invalid]').count() === 1
      && await mission.inputValue() === head.id && await mode.inputValue() === 'Linked',
      'The preview flags the actual invalid room layout while leaving the current plan untouched');
    await mapRoom.selectOption('5');
    check(await fileMap.getAttribute('data-mission-id') === invalidLayout.id
      && await fileMap.locator('[data-layout-invalid=true]').count() === 2 && await create.isDisabled(),
      'The incoming map marks both overlapping saved objects while the active preparation still controls creation');
    await input.setInputFiles(independent.target);
    await load.click();
    await status.filter({ hasText: '已載入' }).waitFor();
    await page.locator('#launch-room-layout-5[data-status=valid]').waitFor();
    check(await mode.inputValue() === 'IndependentSet' && await draft.inputValue() === '691'
      && JSON.stringify(await selected()) === JSON.stringify(ids) && await create.isDisabled(),
      'A fresh console loads exact independent versions, preserves the draft, and leaves occupied-room creation blocked');
    await page.locator('#launch-review-room').selectOption('2');
    assert.equal(await page.locator('#launch-preview-duration').innerText(), '420 秒');
    assert.match(await page.locator('#launch-preview-environment').innerText(), /MR/);

    const broken = structuredClone(independent.value);
    broken.rooms[4].missionId = randomUUID();
    await selectedFile(broken);
    await status.filter({ hasText: '無法核對房間 5' }).waitFor();
    check(JSON.stringify(await selected()) === JSON.stringify(ids), 'A missing version reports its room and applies no part of the file');
    for (const invalid of [
      { ...linked.value, rooms: rooms(ids) },
      { ...independent.value, rooms: [...independent.value.rooms.slice(0, 4), independent.value.rooms[0]] },
      { ...independent.value, extra: 'x'.repeat(4096) }
    ]) {
      await selectedFile(invalid);
      await status.filter({ hasText: '配置格式不符' }).waitFor();
    }
    check(await mode.inputValue() === 'IndependentSet' && JSON.stringify(await selected()) === JSON.stringify(ids),
      'Malformed, ambiguous or oversized files preserve all five selections');

    const versionPath = `**/api/missions/${a.id}/version`;
    await page.route(versionPath, async route => {
      const response = await route.fetch();
      const value = await response.json();
      value.mission.definition.environment.weather = 'Unknown';
      await route.fulfill({ response, json: value });
    }, { times: 1 });
    await input.setInputFiles(linked.target);
    await preview.click();
    await status.filter({ hasText: '無法核對房間 1、2、3、4、5' }).waitFor();
    check(await review.isHidden() && JSON.stringify(await selected()) === JSON.stringify(ids),
      'A malformed saved environment is refused for every affected room before applying the file');
    await page.route(versionPath, async route => {
      const response = await route.fetch();
      const value = await response.json();
      value.mission.definition.enemies.behavior = 'Unknown';
      await route.fulfill({ response, json: value });
    }, { times: 1 });
    await load.click();
    await status.filter({ hasText: '無法核對房間 1、2、3、4、5' }).waitFor();
    check(await review.isHidden() && JSON.stringify(await selected()) === JSON.stringify(ids),
      'Loading a file refuses a malformed saved enemy policy without changing the assignments');

    let intercept;
    const pending = new Promise(resolve => { intercept = resolve; });
    await page.route(versionPath, route => { intercept(route); }, { times: 1 });
    await input.setInputFiles(linked.target);
    await preview.click();
    const held = await Promise.race([pending, new Promise((_, reject) =>
      setTimeout(() => reject(new Error('The historical revision read did not start')), 10000).unref())]);
    try { await page.locator('#tab-missions').click(); }
    finally { await held.continue(); }
    await page.waitForFunction(() => !document.querySelector('#mission-fields').disabled);
    await page.locator('#tab-operations').click();
    check(await mode.inputValue() === 'IndependentSet' && await panel.getAttribute('open') === null
      && await input.inputValue() === '' && await status.textContent() === '' && await review.isHidden() && await maps.isHidden(),
      'Leaving operations discards an in-flight file read and clears the file selection');
    await panel.locator('summary').click();
    await input.setInputFiles(linked.target);
    await load.click();
    await status.filter({ hasText: '已載入' }).waitFor();
    await page.locator('#launch-layout-summary[data-status=valid]').waitFor();
    check(await mode.inputValue() === 'Linked' && await mission.inputValue() === a.id
      && await page.locator('#launch-preview-duration').innerText() === '360 秒' && await draft.inputValue() === '691'
      && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'The Linked file loads the original version and changes preparation only');
    await panel.screenshot({ path: path.join(screenshots, 'venue-mission-file.png') });
    await end(blocker.id);
    active.delete(blocker.id);
    await page.locator('#refresh').click();
    const endpoint = url => url.origin === base && url.pathname === '/api/sessions';
    const attempts = [];
    let created;
    const submit = async route => {
      if (route.request().method() !== 'POST') return route.continue();
      attempts.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() });
      const original = await route.fetch();
      assert.equal(original.status(), 201);
      const session = await original.json();
      if (attempts.length === 1) {
        created = session;
        active.add(session.id);
        const changed = structuredClone(session);
        changed.mission.definition.props[0].yawDegrees += 15;
        return route.fulfill({ response: original, json: changed });
      }
      assert.deepEqual(session, created);
      const definition = session.mission.definition;
      const orderedDifferently = { props: definition.props, enemies: definition.enemies, environment: definition.environment,
        durationSeconds: definition.durationSeconds, briefing: definition.briefing, name: definition.name };
      return route.fulfill({ response: original, json: { ...session, mission: { ...session.mission, definition: orderedDifferently } } });
    };
    await page.route(endpoint, submit);
    try {
      const notice = page.locator('#notice');
      await create.click();
      await notice.filter({ hasText: /結果未確認|場次建立結果已確認/ }).waitFor();
      check(!await page.locator('#pending-command').isHidden() && await page.locator('#session-panel').isHidden()
        && (await notice.innerText()).includes('場次回條與原選定的任務或房間不符'),
        'A Linked receipt with a different saved prop angle cannot confirm the selected historical mission');
      await page.locator('#retry-command').click();
      await notice.filter({ hasText: '場次建立結果已確認' }).waitFor();
      const [session] = await api('/sessions');
      assert.deepEqual(attempts[0].body, { missionId: a.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] });
      check(attempts.length === 2 && attempts[0].key && JSON.stringify(attempts[0]) === JSON.stringify(attempts[1])
        && session.id === created.id && session.mode === 'Linked' && session.mission.id === a.id && session.state === 'Preparing'
        && JSON.stringify(session.mission.definition) === JSON.stringify(created.mission.definition),
        'The same Linked request confirms the original historical session when the exact definition arrives in a different JSON field order');
    } finally { await page.unroute(endpoint, submit); }
  } finally {
    try { for (const id of active) await end(id); }
    finally { await page.close(); }
  }
};
