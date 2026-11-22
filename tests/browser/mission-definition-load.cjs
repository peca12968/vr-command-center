const assert = require('node:assert/strict');

module.exports = async function missionDefinitionLoad({ context, api, tokens, base }) {
  const definition = { name: '風雨場地', briefing: '集合後開始', durationSeconds: 180,
    environment: { mode: 'VR', weather: 'Storm', timeOfDay: 'Night', lightning: true },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false },
    props: [{ assetId: 'sandbag', position: { x: 1.25, y: 0, z: -2.5 }, yawDegrees: 30 }] };
  const saved = await api('/missions', 'POST', definition, 'Master', 201);
  const version = await api('/missions/' + saved.id + '/version');
  const template = { format: 'vr-command-mission-template', version: 1, definition };
  const page = await context.newPage();
  const field = id => page.locator('#' + id);
  try {
    await page.goto(base + '/console/');
    await field('login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await field('tab-missions').click();
    await field('edit-mission').selectOption(saved.id);
    await field('draft-name').fill('目前編輯中的任務');
    await field('add-barrel').click();
    const originalHistory = await field('prop-history-status').textContent();
    const badVersion = structuredClone(version);
    delete badVersion.mission.definition.props[0].position.z;
    await page.route('**/api/missions/' + saved.id + '/version', route => route.fulfill({ json: badVersion }), { times: 1 });
    page.once('dialog', dialog => dialog.accept());
    await field('load-mission').click();
    await page.waitForFunction(name => document.querySelector('#draft-name').value === name
      || document.querySelector('#notice').textContent.includes('核對不符'), definition.name);
    assert.equal(await field('draft-name').inputValue(), '目前編輯中的任務');
    assert.match(await field('notice').innerText(), /核對不符/);
    assert.equal(await field('prop-asset').inputValue(), 'barrel');
    assert.equal(await field('prop-history-status').textContent(), originalHistory);
    await field('mission-template-file').setInputFiles({ name: 'mission.json', mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify(template)) });
    const badTemplate = structuredClone(template);
    delete badTemplate.definition.environment.lightning;
    await page.route('**/api/mission-templates/check-file', route => route.fulfill({ json: badTemplate }), { times: 1 });
    await field('check-mission-template').click();
    await field('notice').filter({ hasText: '範本回應內容不完整' }).waitFor();
    assert.ok(await field('use-mission-template').isDisabled());
    assert.equal(await field('prop-history-status').textContent(), originalHistory);
    await field('check-mission-template').click();
    await field('mission-template-status').filter({ hasText: '暴風雨 · 夜晚 · 閃電開啟' }).waitFor();
    assert.equal(await field('draft-name').inputValue(), '目前編輯中的任務');
    page.once('dialog', dialog => dialog.accept());
    await field('load-mission').click();
    await page.waitForFunction(name => document.querySelector('#draft-name').value === name, definition.name);
    assert.equal(await field('draft-duration').inputValue(), '180');
    assert.equal(await field('draft-weather').inputValue(), 'Storm');
    assert.ok(await field('draft-lightning').isChecked());
    assert.equal(await field('prop-z').inputValue(), '-2.5');
    assert.equal(await field('prop-yaw').inputValue(), '30');
    await field('draft-duration').fill('240');
    await field('save-revision').click();
    await page.waitForFunction(original => document.querySelector('#mission-version').value !== original
      && document.querySelector('#draft-status').textContent.startsWith('已儲存於'), saved.id);
    const revisionId = await field('mission-version').inputValue();
    assert.deepEqual((await api('/missions/' + revisionId)).definition, { ...definition, durationSeconds: 240 });
    assert.deepEqual((await api('/missions/' + saved.id)).definition, definition);
  } finally { await page.close(); }
};
