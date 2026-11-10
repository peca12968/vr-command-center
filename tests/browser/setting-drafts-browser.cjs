const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

module.exports = async function checkSettingDrafts({ page, api, tokens, base, check }) {
  const definition = { name: '場中設定草稿', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] };
  const mission = await api('/missions', 'POST', definition, 'Master', 201);
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
  const route = '/sessions/' + session.id, commandPath = '/api' + route + '/commands';
  const weather = page.locator('#live-weather'), behavior = page.locator('#live-behavior');
  const notice = page.locator('#notice');
  const send = (action, extra, role = 'Room1') => api(route + '/commands', 'POST', { commandId: randomUUID(), action, ...extra }, role);
  async function submit(kind, action) {
    const response = page.waitForResponse(value => new URL(value.url()).pathname === commandPath
      && value.request().method() === 'POST' && value.request().postDataJSON().action === action);
    await page.locator('#' + kind + '-form button[type=submit]').click();
    return response;
  }
  try {
    await api(route + '/players', 'POST', { playerId: randomUUID(), name: '席位 1', roomId: 1, headset: 'Quest3' }, 'Room1');
    await send('Begin', {});
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    await page.locator('#session-phase').filter({ hasText: '執行中' }).waitFor();
    await weather.selectOption('Storm');
    await page.locator('#live-time').selectOption('Night');
    await page.locator('#live-lightning').check();
    await behavior.selectOption('Advance');
    const environment = await submit('environment', 'SetEnvironment');
    assert.equal(environment.status(), 200);
    await page.waitForFunction(() => document.querySelector('#live-environment').textContent.includes('暴風雨')
      && !document.querySelector('#environment-fields').disabled);
    check(await behavior.inputValue() === 'Advance', 'Applying the environment preserves the unsent enemy draft');
    const received = await submit('enemies', 'SetEnemies');
    check(received.status() === 200, 'The enemy draft can be applied after the environment changes');
    assert.equal((await received.json()).session.enemies.behavior, 'Advance');
    assert.equal(received.request().postDataJSON().expectedSettingSequence, 1);
    await page.locator('#live-enemies').filter({ hasText: '推進' }).waitFor();

    await weather.selectOption('Fog');
    await send('SetEnemies', { enemies: { ...definition.enemies, behavior: 'Patrol' } });
    const fog = await submit('environment', 'SetEnvironment');
    assert.equal(fog.status(), 200);
    check((await fog.json()).session.environment.weather === 'Fog',
      'Another operator can change enemies without invalidating the environment draft');
    await page.locator('#live-environment').filter({ hasText: '濃霧' }).waitFor();
    await weather.selectOption('Clear');
    await behavior.selectOption('Advance');
    assert.equal((await submit('enemies', 'SetEnemies')).status(), 200);
    await page.waitForFunction(() => document.querySelector('#live-enemies').textContent.includes('推進')
      && !document.querySelector('#enemies-fields').disabled);
    check(await weather.inputValue() === 'Clear', 'Applying the enemy strategy preserves the unsent environment draft');
    const remote = await send('SetEnvironment', { environment: { ...definition.environment, weather: 'Rain' } });
    const stale = await submit('environment', 'SetEnvironment');
    assert.equal(stale.status(), 409);
    assert.equal((await stale.json()).code, 'setting-revision-changed');
    await notice.filter({ hasText: '場次設定已變更' }).waitFor();
    check((await api(route)).sequence === remote.appliedAtSequence && await weather.inputValue() === 'Clear',
      'A same-setting conflict keeps the accepted revision and preserves the unsent local draft');
    await page.locator('#reload-environment').click();
    await page.waitForFunction(() => document.querySelector('#live-weather').value === 'Rain'
      && !document.querySelector('#environment-fields').disabled);
    check(await page.locator('#live-time').inputValue() === 'Day' && !await page.locator('#live-lightning').isChecked(),
      'Explicit reload reads the complete accepted environment');
  } finally { await api(route, 'DELETE', undefined, 'Master', 204); }

  const linked = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] }, 'Master', 201);
  const linkedRoute = '/sessions/' + linked.id;
  try {
    await api(linkedRoute + '/combat-stream', 'POST', { streamId: randomUUID(), origin: 'Simulation', roomEnemyPolicyVersion: 1 }, 'GameServer');
    await page.locator('#refresh').click();
    await page.locator('#session-select').selectOption(linked.id);
    await page.locator('#room-enemies-panel').waitFor();
    await behavior.selectOption('Advance');
    const local = await api(linkedRoute + '/commands', 'POST', { commandId: randomUUID(), action: 'SetRoomEnemies',
      roomEnemyPolicy: { roomId: 2, policy: { behavior: 'Patrol', autoAttack: true } } }, 'Room2');
    const rejected = page.waitForResponse(value => new URL(value.url()).pathname === '/api' + linkedRoute + '/commands'
      && value.request().method() === 'POST');
    await page.locator('#enemies-form button[type=submit]').click();
    const conflict = await rejected;
    assert.equal(conflict.status(), 409);
    assert.equal((await conflict.json()).code, 'setting-revision-changed');
    const latest = await api(linkedRoute);
    check(latest.sequence === local.appliedAtSequence && latest.roomEnemyPolicies?.[0]?.roomId === 2
      && await behavior.inputValue() === 'Advance', 'A stale whole-session enemy draft preserves the newer room override');
  } finally { await api(linkedRoute, 'DELETE', undefined, 'Master', 204); }
};
