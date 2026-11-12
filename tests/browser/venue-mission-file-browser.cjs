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
  const reviewRows = review.locator('tbody tr');
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

    const head = await api(`/missions/${a.id}/revisions`, 'POST', { ...template, durationSeconds: 690, props: [],
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
    await mode.selectOption('Linked');
    check(await reviewRows.locator('td:nth-child(2)').evaluateAll(cells => cells.every(cell => cell.textContent.includes('第 2 版')))
      && (await review.innerText()).includes('目前為五房全連線'),
      'Changing the current plan updates the comparison while the file assignments stay fixed');
    await review.screenshot({ path: path.join(screenshots, 'venue-mission-file-review.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      'A narrow screen keeps the preview table inside its own scroll region');
    await page.setViewportSize({ width: 1440, height: 1080 });
    const withInvalidLayout = structuredClone(independent.value);
    withInvalidLayout.rooms[4].missionId = invalidLayout.id;
    await input.setInputFiles({ name: 'layout.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(withInvalidLayout)) });
    check(await review.isHidden(), 'Choosing a different file clears the old comparison immediately');
    await preview.click();
    await review.waitFor();
    check(await reviewRows.last().locator('[data-status=invalid]').count() === 1
      && await mission.inputValue() === head.id && await mode.inputValue() === 'Linked',
      'The preview flags the actual invalid room layout while leaving the current plan untouched');
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
      && await input.inputValue() === '' && await status.textContent() === '' && await review.isHidden(),
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
    await create.click();
    await page.locator('#notice').filter({ hasText: '場次建立結果已確認' }).waitFor();
    const [session] = await api('/sessions');
    active.add(session.id);
    check(session.mode === 'Linked' && session.mission.id === a.id && session.state === 'Preparing',
      'Explicit creation uses the loaded historical version');
  } finally {
    try { for (const id of active) await end(id); }
    finally { await page.close(); }
  }
};
