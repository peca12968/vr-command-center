const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');

async function login(page, base, token) {
  await page.goto(base + '/console/');
  await page.locator('#login-key').fill(token);
  await page.locator('#login-form button').click();
  await page.locator('#rooms .room-card').first().waitFor();
}

async function selectEnded(page, id) {
  await page.locator('#include-ended').check();
  await page.locator('#session-select').selectOption(id);
  await page.locator('#session-phase').filter({ hasText: '已結束' }).waitFor();
}

async function applyOriginal(page, session) {
  await page.locator('#prepare-from-session').click();
  await page.locator('#notice').filter({ hasText: '已選用原場次的任務版本' }).waitFor();
  await page.locator('#launch-layout-summary[data-status=valid]').waitFor();
  assert.equal(await page.locator('#launch-mode').inputValue(), session.mode);
  assert.equal(await page.locator('#launch-mission').inputValue(), session.mission.id);
  assert.equal(await page.locator('#launch-preview-duration').innerText(), `${session.mission.definition.durationSeconds} 秒`);
  if (session.mode === 'Independent') assert.equal(await page.locator('#launch-room').inputValue(), String(session.roomIds[0]));
}

async function submit(page, original) {
  const accepted = page.waitForResponse(reply => new URL(reply.url()).pathname === '/api/sessions' && reply.request().method() === 'POST');
  await page.locator('#create-session-form button[type=submit]').click();
  const response = await accepted;
  assert.equal(response.status(), 201);
  assert.deepEqual(response.request().postDataJSON(), { missionId: original.mission.id, mode: original.mode, roomIds: original.roomIds });
  return response.json();
}

module.exports = async function sessionReprepareBrowser({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage();
  captureErrors(page);
  const button = page.locator('#prepare-from-session'), mission = page.locator('#launch-mission');
  const create = page.locator('#create-session-form button[type=submit]');
  const active = new Set();
  const definition = { name: '房控原場任務', briefing: '保存的原任務內容', durationSeconds: 360,
    environment: { mode: 'VR', weather: 'Rain', timeOfDay: 'Night', lightning: false },
    enemies: { count: 2, behavior: 'Hold', autoAttack: false },
    props: [{ assetId: 'barrel', position: { x: 2, y: 0, z: 2 }, yawDegrees: 30 }] };
  async function start(mode, roomIds, missionId) {
    const session = await api('/sessions', 'POST', { mode, roomIds, missionId }, 'Master', 201);
    active.add(session.id);
    return session;
  }
  async function end(id) {
    await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
    active.delete(id);
  }
  try {
    const saved = await api('/missions', 'POST', definition, 'Master', 201);
    const oldLinked = await start('Linked', [1, 2, 3, 4, 5], saved.id);
    await end(oldLinked.id);
    const old = await start('Independent', [2], saved.id);
    await api(`/sessions/${old.id}/commands`, 'POST', { commandId: randomUUID(), action: 'SetEnvironment',
      environment: { ...definition.environment, weather: 'Fog', timeOfDay: 'Day' } });
    await end(old.id);
    const head = await api(`/missions/${saved.id}/revisions`, 'POST', { ...definition, durationSeconds: 600, props: [] },
      'Master', 201, undefined, randomUUID());
    const other = await start('Independent', [3], head.id);
    const occupied = await start('Independent', [2], head.id);
    await login(page, base, tokens.Room2);
    await page.locator('#session-panel').waitFor();
    check(await button.isHidden(), 'Active sessions do not offer historical preparation');
    await selectEnded(page, oldLinked.id);
    check(await button.isHidden(), 'Room control cannot prepare a linked session from its history');
    await selectEnded(page, old.id);
    await mission.selectOption(head.id);
    const route = `**/api/missions/${saved.id}/version`;
    const wrong = await api(`/missions/${head.id}/version`);
    await page.route(route, request => request.fulfill({ status: 200, json: wrong }), { times: 1 });
    await button.click();
    await page.locator('#notice').filter({ hasText: '無法核對原場次' }).waitFor();
    check(await mission.inputValue() === head.id, 'A mismatched reply cannot replace the preparation selection');
    await applyOriginal(page, old);
    check(await create.isDisabled() && (await api('/sessions')).length === 2
      && (await page.locator('#launch-preview-environment').innerText()).includes('下雨')
      && (await page.locator('#launch-preview-version').innerText()).includes('歷史'),
      'Room history applies the saved rain configuration while an occupied room still blocks creation');
    await page.locator('#launch-preview').screenshot({ path: path.join(screenshots, 'original-room-mission.png') });
    await end(occupied.id);
    await page.locator('#refresh').click();
    const fresh = await submit(page, old);
    active.add(fresh.id);
    check(fresh.id !== old.id && fresh.players.length === 0 && fresh.state === 'Preparing'
      && fresh.mission.id === saved.id && fresh.environment.weather === 'Rain'
      && (await api(`/sessions/${old.id}`)).environment.weather === 'Fog'
      && (await api(`/sessions/${other.id}`)).sequence === other.sequence,
      'Explicit room creation preserves other rooms and history, and uses the original starting conditions');
    await end(fresh.id);
    await end(other.id);

    await login(page, base, tokens.Master);
    await selectEnded(page, oldLinked.id);
    await applyOriginal(page, oldLinked);
    const linked = await submit(page, oldLinked);
    active.add(linked.id);
    check(linked.id !== oldLinked.id && linked.state === 'Preparing' && linked.players.length === 0
      && linked.roomIds.join() === '1,2,3,4,5' && linked.mission.id === saved.id,
      'Master can explicitly prepare a fresh linked session from the individual ended session');
  } finally {
    try { for (const id of active) await end(id); }
    finally { await page.close(); }
  }
};

if (require.main === module) {
  (async () => {
    const { chromium } = require('playwright');
    const chunks = [];
    for await (const chunk of process.stdin) chunks.push(chunk);
    const { base, token, session, output } = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
    const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_SERVER_PLAN_CHROMIUM });
    try {
      const page = await browser.newPage();
      await login(page, base, token);
      await selectEnded(page, session.id);
      await applyOriginal(page, session);
      assert.match(await page.locator('#launch-preview-version').innerText(), /歷史/);
      await page.locator('#launch-preview').screenshot({ path: path.join(path.dirname(output), 'original-room-mission.png') });
      await fs.writeFile(output, JSON.stringify(await submit(page, session), null, 2), { flag: 'wx' });
    } finally { await browser.close(); }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
