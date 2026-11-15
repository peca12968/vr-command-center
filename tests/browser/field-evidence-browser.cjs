const assert = require('node:assert/strict');
const { execFile, execFileSync } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');
const { promisify } = require('node:util');
const { randomUUID } = require('node:crypto');

module.exports = async function fieldEvidence({ context, api, tokens, directory, root, base, screenshots, check }) {
  const room = (await api('/rooms')).find(value => [1, 2].includes(value.id) && !value.sessionId);
  assert.ok(room, 'Field evidence fixture requires a free room with a controller identity');
  const mission = await api('/missions', 'POST', { name: 'Field evidence gate', briefing: '未開始場次', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const waiting = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [room.id] }, 'Master', 201);
  const endpoint = id => `/sessions/${id}/field-evidence.zip`;
  await api(endpoint(waiting.id), 'GET', undefined, 'Master', 409);
  await api(`/sessions/${waiting.id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' });
  await api(endpoint(waiting.id), 'GET', undefined, 'Master', 409);
  check(true, 'Field evidence rejects preparing and ended-before-start sessions');

  const keys = path.join(directory, 'field-evidence-keys.json');
  await fs.writeFile(keys, JSON.stringify({ OperatorKeys: tokens }), { flag: 'wx' });
  const relay = process.env.VR_COMMAND_WORLD_RELAY_DLL || path.join(root, 'tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll');
  const { stdout } = await promisify(execFile)('dotnet', [relay, '--recording', path.join(directory, 'field-evidence.ndjson'),
    '--base-url', base, '--key-file', keys, '--demo-room', String(room.id), '--seconds', '2'], { cwd: root, windowsHide: true, timeout: 30000 });
  const run = JSON.parse(stdout.trim().split(/\r?\n/).at(-1));
  const id = run.sessionId, prefix = `/sessions/${id}`;
  const final = await api(prefix), world = await api(prefix + '/world');
  assert.ok(final.combatStream.sealed && world.complete && final.startedAtUtc && final.players.length === 1);
  await api(endpoint(id), 'GET', undefined, 'Master', 409);
  check(true, 'Both real API seals still require a published endpoint');
  await api(prefix + '/connection-endpoint', 'PUT', { version: 1, streamId: final.combatStream.streamId,
    address: '192.168.50.40', port: 7777 }, 'GameServer');
  const role = 'Room' + room.id;
  await api(endpoint(id), 'GET', undefined, role, 403);
  await api(endpoint(id), 'GET', undefined, 'GameServer', 403);
  assert.equal((await fetch(base + '/api' + endpoint(id))).status, 401);
  check(true, 'Field evidence download requires the Master role even in the controller’s own room');
  await api(endpoint(id) + '?includeTrackedVrStart=true', 'GET', undefined, 'Master', 409);
  check(true, 'Explicit tracked opening export rejects a Simulation archive without an original tracked pointer');
  const response = await fetch(base + '/api' + endpoint(id), { headers: { Authorization: 'Bearer ' + tokens.Master } });
  check(response.ok && response.headers.get('content-type') === 'application/zip'
    && response.headers.get('cache-control') === 'no-store'
    && response.headers.get('content-disposition').includes(`vr-command-field-v1-${id}.zip`), 'Private export uses the expected type, cache policy and session filename');
  await response.arrayBuffer();

  const page = await context.newPage(), errors = [], downloads = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('download', download => downloads.push(download));
  const button = page.locator('#download-field-evidence');
  async function login(operator) {
    await page.locator('#login-key').fill(tokens[operator]); await page.locator('#login-form button').click();
    await page.locator('#include-ended').check(); await page.locator('#session-select').selectOption(id);
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已結束', null, { polling: 100 });
  }
  try {
    await page.goto(base + '/console/'); await page.bringToFront(); await login('Master');
    await page.waitForFunction(() => !document.querySelector('#download-field-evidence').disabled, null, { polling: 100 });
    const pending = page.waitForEvent('download'); await button.click(); const download = await pending;
    assert.equal(download.suggestedFilename(), `vr-command-field-v1-${id}.zip`);
    const file = path.join(screenshots, 'field-evidence.zip'); await download.saveAs(file);
    const raw = execFileSync('python', ['-c', `import json, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    assert archive.namelist() == ['session.json', 'statistics.json', 'endpoint.json'] and archive.testzip() is None
    print(json.dumps([json.loads(archive.read(name)) for name in archive.namelist()], ensure_ascii=True))`, file], { encoding: 'utf-8' });
    assert.ok(Object.values(tokens).every(token => !raw.includes(token)));
    assert.deepEqual(JSON.parse(raw), [await api(prefix), await api(prefix + '/statistics'), await api(prefix + '/connection-endpoint')]);
    assert.equal((await api(prefix)).sequence, final.sequence);
    check(true, 'The browser ZIP contains precisely the three authorized records without credentials or writes');
    await page.screenshot({ path: path.join(screenshots, 'field-evidence.png'), fullPage: true });

    const routeName = `**/api${endpoint(id)}`;
    await page.route(routeName, route => route.fulfill({ status: 200, contentType: 'application/zip-fake', body: 'fixture' }));
    await button.click();
    await page.waitForFunction(() => document.querySelector('#field-evidence-status').textContent.includes('格式不符'), null, { polling: 100 });
    check(downloads.length === 1 && await button.isEnabled(), 'Unexpected download MIME type is rejected and a retry remains available');
    await page.unroute(routeName);

    let notify, release, finished;
    const requested = new Promise(resolve => { notify = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    const done = new Promise(resolve => { finished = resolve; });
    const hold = async route => {
      try { const reply = await route.fetch(); assert.equal(reply.status(), 200); notify(null); await gate;
        try { await route.fulfill({ response: reply }); } catch { /* Switching identity intentionally aborts this response. */ }
      } catch (error) { notify(error); } finally { finished(); }
    };
    await page.route(routeName, hold);
    try {
      await button.click(); const failure = await requested; if (failure) throw failure;
      assert.ok(await button.isDisabled());
      await page.locator('#logout').click(); await login(role);
    } finally { release(); await done; await page.unroute(routeName, hold); }
    check(await button.isHidden() && downloads.length === 1, 'Late Master ZIP cannot download after switching to the room identity');
    check(errors.length === 0, 'Field evidence workflow has no uncaught browser errors');
  } finally { await page.close(); }
};
