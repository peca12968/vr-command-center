const assert = require('node:assert/strict');
const fs = require('node:fs/promises');

module.exports = async ({ context, api, tokens, base }) => {
  const saved = await api('/missions', 'POST', {
    name: '草稿備份比對', briefing: '核對場景配置', durationSeconds: 180,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false },
    props: [{ assetId: 'barrel', position: { x: 1, y: 0, z: 2 }, yawDegrees: 30 }]
  }, 'Master', 201);
  const source = await context.newPage(), target = await context.newPage();
  const panel = target.locator('#template-comparison'), summary = panel.locator('summary');
  const rows = panel.locator('tbody tr');
  const upload = target.locator('#mission-template-file');
  const requests = [];
  target.on('request', request => {
    if (request.method() !== 'GET') requests.push(new URL(request.url()).pathname);
  });
  async function checkFile(file) {
    await upload.setInputFiles(file);
    await target.locator('#check-mission-template').click();
    await panel.waitFor();
    await summary.click();
    await panel.locator('#template-comparison-status').filter({ hasText: /差異|相同/ }).waitFor();
  }
  try {
    for (const page of [source, target]) {
      await page.goto(base + '/console/');
      await page.locator('#login-key').fill(tokens.Master);
      await page.locator('#login-form button').click();
      await page.locator('#tab-missions').click();
      await page.locator('#edit-mission').selectOption(saved.id);
      await page.locator('#load-mission').click();
      await page.locator('#draft-status').filter({ hasText: '第 1 版' }).waitFor();
    }
    await source.locator('#prop-x').fill('1.375'); await source.locator('#prop-x').blur();
    const started = source.waitForEvent('download');
    await source.locator('#export-draft-template').click();
    const download = await started;
    const file = { name: download.suggestedFilename(), mimeType: 'application/json', buffer: await fs.readFile(await download.path()) };
    requests.length = 0;
    await checkFile(file);
    assert.deepEqual(await rows.allTextContents(), ['物件 1barrel · (1.375, 0, 2) m · 30°barrel · (1, 0, 2) m · 30°']);
    assert.equal(await target.locator('#prop-x').inputValue(), '1');
    await target.locator('#prop-x').fill('1.375'); await target.locator('#prop-x').blur();
    assert.equal(await panel.evaluate(node => node.open), false);
    await summary.click();
    await panel.getByText('範本與目前草稿相同。').waitFor();
    assert.equal(await rows.count(), 0);
    await target.locator('#add-sandbag').click();
    await summary.click(); await rows.first().waitFor();
    assert.deepEqual(await rows.first().locator('th, td').allTextContents(), ['物件 2', '（無物件）', 'sandbag · (0, 0, 0) m · 0°']);
    assert.ok(await target.locator('#undo-prop').isEnabled());
    await upload.setInputFiles({ ...file, buffer: Buffer.from('{}') });
    await target.locator('#check-mission-template').click();
    await target.locator('#notice.error').waitFor();
    assert.ok(await panel.isHidden());
    assert.ok(await target.locator('#use-mission-template').isDisabled());
    assert.equal(await target.locator('#prop-select option').count(), 2);
    assert.deepEqual(requests.filter(route => route.startsWith('/api/mission') && route !== '/api/mission-layout'),
      ['/api/mission-templates/check-file', '/api/mission-templates/check-file']);
    target.once('dialog', dialog => dialog.accept());
    await target.reload();
    await target.locator('#login-key').fill(tokens.Master);
    await target.locator('#login-form button').click();
    await target.locator('#tab-missions').click();
    assert.ok(await panel.isHidden());
    await checkFile(file);
    await target.locator('#use-mission-template').click();
    assert.equal(await target.locator('#draft-name').inputValue(), saved.definition.name);
    assert.equal(await target.locator('#prop-x').inputValue(), '1.375');
    assert.equal(await target.locator('#prop-select option').count(), 1);
    assert.ok(await panel.isHidden());
    assert.ok(await target.locator('#save-revision').isDisabled());
    assert.equal((await api('/missions/' + saved.id + '/history')).headId, saved.id);
  } finally { await Promise.all([source.close(), target.close()]); }
};
