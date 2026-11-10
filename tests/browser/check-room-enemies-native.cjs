const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const input = [];
  for await (const chunk of process.stdin) input.push(chunk);
  const { base, token, sessionId, restoreSequence, venuePreview } = JSON.parse(Buffer.concat(input).toString('utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage();
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    if (venuePreview) {
      await page.locator('#venue-enemies-targets').filter({ hasText: '套用時會清除房間 2 的分房策略。' }).waitFor();
      process.stdout.write(JSON.stringify({ roomsToClear: [2] }));
      return;
    }
    if (restoreSequence) {
      await page.locator('[data-room-enemies="2"]').filter({ hasText: '本房恢復沿用全場策略' }).waitFor();
      const button = page.locator('[data-room-enemies-frame="2"]');
      await button.click();
      await page.locator('#world-enemy-policy').filter({ hasText: '守備' }).waitFor();
      assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
      assert.equal(await page.locator('#world-room').inputValue(), '2');
      const worldSequence = Number(await page.locator('#world-canvas').getAttribute('data-sequence'));
      assert.ok(Number.isSafeInteger(worldSequence) && worldSequence > 0);
      const response = await page.request.get(base + '/api/sessions/' + sessionId + '/world/frames/' + worldSequence,
        { headers: { Authorization: 'Bearer ' + token } });
      assert.equal(response.status(), 200);
      const { packet } = await response.json();
      assert.equal(packet.sequence, worldSequence);
      assert.ok(packet.observedSequence >= restoreSequence);
      assert.ok(!packet.frame.roomEnemyPolicies?.some(row => row.roomId === 2));
      process.stdout.write(JSON.stringify({ worldSequence, observedSequence: packet.observedSequence }));
      return;
    }
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
    const { expectedPolicySequence, ...policy } = command.roomEnemyPolicy;
    assert.ok(Number.isSafeInteger(expectedPolicySequence) && expectedPolicySequence > 0);
    assert.deepEqual(policy, { roomId: 2, policy: { behavior: 'Patrol', autoAttack: true } });
    await page.locator('#room-enemies-current').filter({ hasText: '本房策略 · 巡邏 · 自動攻擊開啟' }).waitFor();
    process.stdout.write(JSON.stringify(await accepted.json()));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
