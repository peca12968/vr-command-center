const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const input = [];
  for await (const chunk of process.stdin) input.push(chunk);
  const { base, token, sessionId } = JSON.parse(Buffer.concat(input).toString('utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(sessionId);
    await page.locator('#room-enemies-panel').waitFor();
    assert.deepEqual(await page.locator('#room-enemies-room option').evaluateAll(options => options.map(option => option.value)), ['2']);
    assert.equal(await page.locator('#enemies-fields').evaluate(fieldset => fieldset.disabled), true);
    assert.equal(await page.locator('#enemies-form button[type=submit]').isDisabled(), true);
    await page.locator('#room-enemies-inherit').uncheck();
    await page.locator('#room-enemies-behavior').selectOption('Patrol');
    await page.locator('#room-enemies-auto').check();
    const response = page.waitForResponse(value => value.url() === base + '/api/sessions/' + sessionId + '/commands'
      && value.request().method() === 'POST');
    await page.locator('#room-enemies-form button[type=submit]').click();
    const accepted = await response;
    assert.equal(accepted.status(), 200);
    const command = accepted.request().postDataJSON();
    assert.equal(command.action, 'SetRoomEnemies');
    assert.deepEqual(command.roomEnemyPolicy, { roomId: 2, policy: { behavior: 'Patrol', autoAttack: true } });
    await page.locator('#room-enemies-current').filter({ hasText: '本房策略 · 巡邏 · 自動攻擊開啟' }).waitFor();
    process.stdout.write(JSON.stringify(await accepted.json()));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
