const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

module.exports = async function missionSearchRefresh({ context, api, tokens, base }) {
  const query = '任務搜尋 ' + randomUUID().slice(0, 8);
  const definition = { name: query, briefing: '', durationSeconds: 600, props: [],
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false } };
  const save = (route, name) => api(route, 'POST', { ...definition, name }, 'Master', 201, undefined, randomUUID());
  const first = await save('/missions', query + ' 甲'), second = await save('/missions', query + ' 乙');
  const page = await context.newPage();
  const field = id => page.locator('#' + id);
  const select = field('edit-mission');
  const refreshUntil = async id => {
    await field('refresh').click();
    await page.locator(`#launch-mission option[value="${id}"]`).waitFor({ state: 'attached' });
  };
  try {
    await page.goto(base + '/console/');
    await field('login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await field('tab-missions').click();
    await field('mission-search').fill(query);
    await select.selectOption(first.id);
    await field('launch-selected-mission').click();
    await field('tab-missions').click();
    await field('draft-name').fill('尚在編輯的任務');
    const renamed = await save('/missions/' + first.id + '/revisions', '另一場次的新版');
    await refreshUntil(renamed.id);
    assert.equal(await select.inputValue(), '', 'Refresh must not select a different mission');
    assert.ok(await field('load-mission').isDisabled() && await field('launch-selected-mission').isDisabled());

    const updated = await save('/missions/' + second.id + '/revisions', query + ' 乙修訂');
    await refreshUntil(updated.id);
    assert.equal(await select.inputValue(), '', 'A later refresh must keep the operator selection empty');
    assert.equal(await field('mission-search').inputValue(), query);
    assert.equal(await field('launch-mission').inputValue(), first.id);
    assert.equal(await field('draft-name').inputValue(), '尚在編輯的任務');
    await select.selectOption(updated.id);
    assert.ok(await field('load-mission').isEnabled() && await field('launch-selected-mission').isEnabled());
    await field('launch-selected-mission').click();
    assert.equal(await field('launch-mission').inputValue(), updated.id);
    await field('tab-missions').click();
    const latest = await save('/missions/' + updated.id + '/revisions', query + ' 乙最新版');
    await refreshUntil(latest.id);
    assert.equal(await select.inputValue(), latest.id, 'Matching revisions must follow the selected series');
    assert.equal(await field('launch-mission').inputValue(), updated.id);
    const gone = await save('/missions/' + latest.id + '/revisions', '移出搜尋結果');
    await refreshUntil(gone.id);
    assert.equal(await select.inputValue(), '');
    assert.ok((await field('mission-search-status').textContent()).includes('找到 0 項任務'));
    const added = await save('/missions', query + ' 丙');
    await refreshUntil(added.id);
    assert.equal(await select.inputValue(), '', 'New matches must not replace a lost selection');
    await field('mission-search').fill(query + ' 丙');
    assert.equal(await select.inputValue(), added.id);
    assert.ok(await field('load-mission').isEnabled());
    assert.equal(await field('draft-name').inputValue(), '尚在編輯的任務');
  } finally { await page.close(); }
};
