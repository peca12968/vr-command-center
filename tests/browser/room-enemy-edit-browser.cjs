const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

module.exports = async function checkRoomEnemyEdit({ page, api, tokens, base, check }) {
  const mission = await api('/missions', 'POST', { name: 'Room enemy policy edit', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] },
    'Master', 201);
  const route = '/sessions/' + session.id, commandPath = '/api' + route + '/commands';
  const policy = (roomId, behavior, autoAttack = false) => ({ commandId: randomUUID(), action: 'SetRoomEnemies',
    roomEnemyPolicy: { roomId, policy: { behavior, autoAttack } } });
  const send = (command, role = 'Master', status = 200) => api(route + '/commands', 'POST', command, role, status);
  const edit = page.locator('#room-enemies-form button[type=submit]');
  const behavior = page.locator('#room-enemies-behavior'), attack = page.locator('#room-enemies-auto');
  const current = page.locator('#room-enemies-current');
  const submit = async () => {
    const response = page.waitForResponse(value => new URL(value.url()).pathname === commandPath && value.request().method() === 'POST');
    await edit.click();
    return response;
  };
  try {
    await api(route + '/combat-stream', 'POST', { streamId: randomUUID(), origin: 'Simulation', roomEnemyPolicyVersion: 1 }, 'GameServer');
    await send(policy(2, 'Patrol'), 'Room2');
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Room2);
    await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(session.id);
    await current.filter({ hasText: '本房策略 · 巡邏' }).waitFor();
    await behavior.selectOption('Advance');
    const overview = await api(route + '/overview', 'GET', undefined, 'Room2');
    const overviewUrl = '**/api' + route + '/overview';
    const holdOverview = request => request.fulfill({ json: overview });
    await page.route(overviewUrl, holdOverview);
    let latest;
    try {
      latest = await send(policy(2, 'Hold', true));
      const rejected = await submit();
      check(rejected.status() === 409, `A room policy draft cannot overwrite a newer same-room setting (HTTP ${rejected.status()})`);
      assert.equal((await rejected.json()).code, 'room-enemy-policy-changed');
      assert.equal(rejected.request().postDataJSON().roomEnemyPolicy.expectedPolicySequence, overview.roomEnemyPolicySequences[2]);
    } finally { await page.unroute(overviewUrl, holdOverview); }
    await page.locator('#notice.error').filter({ hasText: '本房敵軍策略已變更' }).waitFor();
    check((await api(route)).sequence === latest.appliedAtSequence && await behavior.inputValue() === 'Advance',
      'A rejected policy leaves the accepted revision and the stale operator draft intact');
    await page.locator('#room-enemies-reload').click();
    await current.filter({ hasText: '本房策略 · 守備 · 自動攻擊開啟' }).waitFor();
    assert.equal(await behavior.inputValue(), 'Hold');
    assert.equal(await attack.isChecked(), true);
    await behavior.selectOption('Advance');
    await send(policy(1, 'Patrol'), 'Room1');
    const accepted = await submit();
    assert.equal(accepted.status(), 200);
    const receipt = await accepted.json();
    assert.equal(accepted.request().postDataJSON().roomEnemyPolicy.expectedPolicySequence, latest.appliedAtSequence);
    check(receipt.session.roomEnemyPolicies.map(row => row.behavior).join(',') === 'Patrol,Advance',
      'A different room can update independently while the original room is editing');
    await current.filter({ hasText: '本房策略 · 推進' }).waitFor();
    await attack.uncheck();
    let originalReceipt;
    await page.route('**' + commandPath, async request => {
      const response = await request.fetch();
      originalReceipt = await response.json();
      await request.fulfill({ response, json: { ...originalReceipt, commandId: randomUUID() } });
    }, { times: 1 });
    const unconfirmed = await submit();
    await page.locator('#retry-command').waitFor();
    const retry = page.waitForResponse(value => new URL(value.url()).pathname === commandPath && value.request().method() === 'POST');
    await page.locator('#retry-command').click();
    const confirmed = await retry, duplicate = await confirmed.json();
    check(confirmed.status() === 200 && duplicate.duplicate && duplicate.appliedAtSequence === originalReceipt.appliedAtSequence
      && confirmed.request().postData() === unconfirmed.request().postData(),
      'An unconfirmed room policy retries the identical command and returns its original acceptance');
    await current.filter({ hasText: '本房策略 · 推進 · 自動攻擊關閉' }).waitFor();
    const restore = { commandId: randomUUID(), action: 'SetRoomEnemies', roomEnemyPolicy: { roomId: 2, policy: null } };
    await send(restore, 'Room2');
    await page.locator('#refresh').click();
    await current.filter({ hasText: '沿用全場' }).waitFor();
    check(await edit.isDisabled() && await behavior.inputValue() === 'Advance',
      'A known same-room update disables the stale draft without rewriting its fields');
    await page.locator('#room-enemies-reload').click();
    await page.locator('#room-enemies-inherit:checked').waitFor();
    check(await behavior.inputValue() === 'Hold' && await attack.isChecked() === false,
      'Explicit reload reads the currently inherited values');
  } finally {
    await api(route, 'DELETE', undefined, 'Master', 204);
  }
};
