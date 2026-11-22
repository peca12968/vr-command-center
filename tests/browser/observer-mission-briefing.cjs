const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

module.exports = async function verifyObserverBriefing(page, revision) {
  const panel = page.locator('#world-mission-details'), toggle = panel.locator('summary');
  const version = page.locator('#world-mission-version'), briefing = page.locator('#world-mission-briefing');
  const camera = page.locator('#world-camera'), room = page.locator('#world-room');
  const originalCamera = await camera.inputValue(), originalRoom = await room.inputValue();
  const { mission, number } = revision;
  const endpoint = url => url.pathname === '/api/missions/' + mission.id + '/version';
  await page.route(endpoint, route => route.fulfill({ json: { ...revision, mission: { ...mission, id: randomUUID() } } }), { times: 1 });
  await toggle.click();
  await version.filter({ hasText: '無法核對本場任務簡報' }).waitFor();
  assert.equal(await briefing.textContent(), '');
  await toggle.click();
  const [reply] = await Promise.all([page.waitForResponse(r => endpoint(new URL(r.url()))), toggle.click()]);
  assert.equal(reply.status(), 200);
  await version.filter({ hasText: mission.id }).waitFor();
  assert.equal(await version.textContent(), `第 ${number} 版 · 計畫 ${mission.definition.durationSeconds} 秒 · ${mission.id}`);
  assert.equal(await briefing.textContent(), mission.definition.briefing || '此版本未填寫任務簡報。');
  assert.equal(await camera.inputValue(), originalCamera);
  assert.equal(await room.inputValue(), originalRoom);
  await toggle.click();
};
