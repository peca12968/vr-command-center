const assert = require('node:assert/strict');

module.exports = async function missionMerge({ context, api, tokens, base }) {
  const original = await api('/missions', 'POST', { name: '兩台主控的任務', briefing: '集合', durationSeconds: 90,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const local = await context.newPage(), remote = await context.newPage();
  async function load(page, id, number) {
    await page.locator('#refresh').click();
    await page.locator('#edit-mission').selectOption(id);
    await page.locator('#load-mission').click();
    await page.locator('#draft-status').filter({ hasText: `第 ${number} 版` }).waitFor();
  }
  async function save(page, number) {
    await page.locator('#save-revision').click();
    await page.locator('#draft-status').filter({ hasText: '已儲存於' }).filter({ hasText: `第 ${number} 版` }).waitFor();
    return page.locator('#mission-version').inputValue();
  }
  try {
    for (const page of [local, remote]) {
      await page.goto(base + '/console/');
      await page.locator('#login-key').fill(tokens.Master);
      await page.locator('#login-form button').click();
      await page.locator('#tab-missions').click();
      await load(page, original.id, 1);
    }
    await local.locator('#launch-version').click();
    assert.equal(await local.locator('#launch-preview').getAttribute('data-mission-id'), original.id);
    await local.locator('#tab-missions').click();
    await local.locator('#draft-briefing').fill('從入口集合');
    await local.locator('#add-barrel').click();
    const undo = await local.locator('#prop-history-status').innerText();
    await remote.locator('#draft-duration').fill('240');
    await remote.locator('#draft-weather').selectOption('Rain');
    const second = await save(remote, 2);
    await local.locator('#refresh').click();
    await local.locator('#merge-mission-head').click();
    await local.locator('#notice').filter({ hasText: '草稿已合併第 2 版' }).waitFor();
    assert.equal(await local.locator('#draft-duration').inputValue(), '240');
    assert.equal(await local.locator('#draft-weather').inputValue(), 'Rain');
    assert.equal(await local.locator('#draft-briefing').inputValue(), '從入口集合');
    assert.equal(await local.locator('#prop-asset').inputValue(), 'barrel');
    assert.equal(await local.locator('#prop-history-status').innerText(), undo);
    assert.equal((await api('/missions/' + original.id + '/history')).headId, second);
    const third = await save(local, 3);
    const saved = await api('/missions/' + third + '/version');
    assert.equal(saved.previousId, second);
    assert.equal(saved.mission.definition.props[0].assetId, 'barrel');
    assert.equal(saved.mission.definition.durationSeconds, 240);
    assert.equal(saved.mission.definition.briefing, '從入口集合');
    assert.equal(await local.locator('#launch-preview').getAttribute('data-mission-id'), original.id);
    await load(remote, third, 3);
    await local.locator('#draft-duration').fill('300');
    await local.locator('#add-sandbag').click();
    const conflictUndo = await local.locator('#prop-history-status').innerText();
    await remote.locator('#draft-duration').fill('420');
    await remote.locator('#add-barrel').click();
    const fourth = await save(remote, 4);
    await local.locator('#refresh').click();
    await local.locator('#merge-mission-head').click();
    await local.locator('#notice').filter({ hasText: '任務時間、場景物件' }).waitFor();
    assert.equal(await local.locator('#draft-duration').inputValue(), '300');
    assert.equal(await local.locator('#prop-asset').inputValue(), 'sandbag');
    assert.equal(await local.locator('#prop-history-status').innerText(), conflictUndo);
    assert.equal(await local.locator('#mission-version').inputValue(), fourth);
    assert.ok(await local.locator('#save-revision').isDisabled());
    assert.equal((await api('/missions/' + original.id + '/history')).headId, fourth);
    await local.locator('#compare-version').click();
    await local.locator('#mission-comparison-summary').filter({ hasText: '第 4 版' }).waitFor();
    // Adopt the published duration and undo only the local extra prop. The latest layout can now be used.
    await local.locator('#draft-duration').fill('420');
    await local.locator('#undo-prop').click();
    await local.locator('#merge-mission-head').click();
    await local.locator('#notice').filter({ hasText: '已包含在第 4 版' }).waitFor();
    assert.ok(await local.locator('#undo-prop').isDisabled());
    assert.equal(await local.locator('#prop-select option').count(), 2);
    assert.equal((await api('/missions/' + original.id)).definition.durationSeconds, 90);
    await local.locator('#mission-version').selectOption(original.id);
    await local.locator('#load-version').click();
    await local.waitForFunction(() => document.querySelector('#draft-duration').value === '90');
    assert.ok(await local.locator('#save-revision').isDisabled());
  } finally { await Promise.all([local.close(), remote.close()]); }
};
