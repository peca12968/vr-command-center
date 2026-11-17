const assert = require('node:assert/strict');

module.exports = async function savedLayoutIdentityBrowser({ context, api, tokens, base, check, captureErrors }) {
  const draft = { name: '五房場地版本核對', briefing: '核對同名版本的儲存配置', durationSeconds: 360,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 2, behavior: 'Hold', autoAttack: false }, props: [] };
  const good = await api('/missions', 'POST', draft, 'Master', 201);
  const cover = { assetId: 'sandbag', position: { x: 1, y: 0, z: 1 }, yawDegrees: 0 };
  const bad = await api('/missions', 'POST', { ...draft, props: [cover, cover] }, 'Master', 201);
  const page = await context.newPage();
  captureErrors(page);
  const launchMode = page.locator('#launch-mode'), mission = page.locator('#launch-mission');
  const recheck = page.locator('#layout-recheck-launch'), submit = page.locator('#create-session-form button[type=submit]');
  const summary = page.locator('#launch-layout-summary');
  const savedPath = (id, mode) => `/missions/${id}/layout?mode=${mode}`;
  const roomStatus = (room, state) => `#launch-room-layout-${room}[data-status="${state}"]`;
  const card = room => page.locator(`[data-room-layout-preview="${room}"]`);
  async function useOtherVersion(mode, select, settle) {
    const source = await api(savedPath(good.id, mode));
    assert.equal(source.canStart, true);
    const actual = base + '/api' + savedPath(bad.id, mode);
    const replace = route => route.fulfill({ status: 200, json: { ...source, missionId: good.id } });
    await page.route(actual, replace);
    try {
      const read = page.waitForResponse(response => response.url() === actual);
      await select();
      await recheck.click();
      await read;
      await settle();
      return await submit.isDisabled();
    } finally { await page.unroute(actual, replace); }
  }
  try {
    assert.deepEqual(await api('/sessions'), []);
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
    const linkedBlocked = await useOtherVersion('Linked', async () => {
      await launchMode.selectOption('Linked');
      await mission.selectOption(bad.id);
    }, () => summary.filter({ hasText: /場地檢查未完成|場地檢查通過/ }).waitFor());
    check(linkedBlocked && await mission.inputValue() === bad.id,
      'Linked preparation rejects an approved same-mode report from the other saved mission');
    await recheck.click();
    await page.locator('#launch-layout-summary[data-status=invalid]').waitFor();
    check(await page.locator('#launch-layout-props [data-layout-invalid=true]').count() === 2 && await submit.isDisabled(),
      'A genuine Linked recheck identifies the two overlapping saved props');
    await mission.selectOption(good.id);
    await page.locator('#launch-layout-summary[data-status=valid]').waitFor();
    check(await submit.isEnabled(), 'The correct Linked mission still passes the preparation gate');

    await launchMode.selectOption('IndependentSet');
    await page.locator('#launch-room-missions-toggle').check();
    await page.locator('#launch-room-layouts summary').click();
    for (let room = 1; room <= 5; room++) await page.locator(roomStatus(room, 'valid')).waitFor();
    const independentBlocked = await useOtherVersion('Independent', () => page.locator('#launch-room-mission-5').selectOption(bad.id),
      async () => {
        await page.locator(`${roomStatus(5, 'error')}, ${roomStatus(5, 'valid')}`).waitFor();
        await page.locator(roomStatus(1, 'valid')).waitFor();
      });
    check(independentBlocked && await card(5).locator('svg').count() === 0 && await card(1).locator('svg').count() === 1,
      'A substituted fifth-room report blocks the entire independent batch while other room maps remain available');
    await recheck.click();
    await page.locator(roomStatus(5, 'invalid')).waitFor();
    check(await card(5).locator('[data-layout-invalid=true]').count() === 2 && await submit.isDisabled(),
      'Rechecking the fifth room displays both real conflicts and keeps all five rooms blocked');
    const independentLayout = await api(savedPath(good.id, 'Independent'));
    const previewPath = base + '/api' + savedPath(bad.id, 'Independent');
    const stale = route => route.fulfill({ status: 200, json: { ...independentLayout, missionId: bad.id } });
    await page.route(previewPath, stale);
    try {
      await recheck.click();
      await page.locator(roomStatus(5, 'valid')).waitFor();
    } finally { await page.unroute(previewPath, stale); }
    const creation = page.waitForResponse(response => response.url() === base + '/api/sessions/independent-set'
      && response.request().method() === 'POST');
    page.once('dialog', dialog => dialog.accept());
    await submit.click();
    const response = await creation;
    assert.equal(response.status(), 400);
    const rejected = await response.json();
    await page.locator(roomStatus(5, 'invalid')).waitFor();
    const untouched = await api('/sessions');
    check(rejected.roomId === 5 && rejected.layout.missionId === bad.id && rejected.layout.canStart === false
      && await card(5).locator('[data-layout-invalid=true]').count() === 2 && await submit.isDisabled() && untouched.length === 0,
      'The real batch rejection identifies the exact fifth-room revision, marks its props, and creates no sessions');
    const linkedLayout = await api(savedPath(bad.id, 'Linked'));
    const proposal = await api('/mission-layout', 'POST', { experienceMode: 'VR', mode: 'Independent', enemyCount: 2, props: [] });
    check(linkedLayout.missionId === bad.id && independentLayout.missionId === good.id && !Object.hasOwn(proposal, 'missionId'),
      'Saved reports identify their immutable revision while draft inspections retain their original shape');
  } finally { await page.close(); }
};
