// Inspect sealed genuine native recordings through an independently copied runtime.
// Never open the preserved SQLite original or runtime-snapshot, even read-only.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const checkedLoopbackHost = require('./windows-firewall.cjs');
const root = path.resolve(__dirname, '../..');
async function main() {
  const directory = path.resolve(process.argv[2] || '');
  assert.equal(path.dirname(directory), path.join(root, 'artifacts/desktop-clock'));
  assert.match(path.basename(directory), /^\d{8}-\d{6}-[a-f0-9]{8}$/);
  const native = JSON.parse(await fs.readFile(path.join(directory, 'checks.json'), 'utf8'));
  assert.equal(native.complete, true); assert.equal(native.headsets, 0);
  const dotnet = checkedLoopbackHost(root);
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'vr-clock-observer-'));
  const runtime = path.join(temporary, 'runtime');
  await fs.cp(path.join(directory, 'runtime-snapshot'), runtime, { recursive: true, errorOnExist: true, force: false });
  const output = path.join(directory, 'clock-observer'); await fs.mkdir(output, { recursive: true });
  await fs.writeFile(path.join(output, 'audit-copy.json'), JSON.stringify({ runtime, source: 'Separate copy of stopped native runtime; original and snapshot never opened as SQLite' }));
  const tokens = JSON.parse(await fs.readFile(path.join(directory, 'keys.json'), 'utf8')).OperatorKeys;
  const server = net.createServer(); await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port; await new Promise(resolve => server.close(resolve));
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toLowerCase().startsWith('operatorkeys__') && !['operatorkeyfile', 'playerticketsigningkey'].includes(key.toLowerCase())));
  Object.assign(env, { DataDirectory: path.join(runtime, 'missions'), SessionDataDirectory: path.join(runtime, 'sessions'), OperatorKeyFile: path.join(directory, 'keys.json'), Logging__LogLevel__Default: 'Warning' });
  const processApi = spawn(dotnet, [process.env.VR_COMMAND_API_DLL || path.join(root, 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll'), '--urls', base], { cwd: root, env, windowsHide: true, stdio: 'ignore' });
  let browser; let checks = 0; const errors = [];
  const check = (value, label) => { assert.ok(value, label); checks++; console.log('PASS: ' + label); };
  try {
    for (let i = 0; ; i++) {
      try { if ((await fetch(base + '/health')).ok) break; } catch { }
      if (i > 100 || processApi.exitCode !== null) throw new Error('Owned audit API did not start');
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
    if (process.argv.includes('--controls')) {
      const api = async (route, method = 'GET', body, role = 'Master', expected = 200) => {
        const response = await fetch(base + '/api' + route, { method, headers: { Authorization: 'Bearer ' + tokens[role], 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
        assert.equal(response.status, expected, route); return response.status === 204 ? null : response.json();
      };
      const session = await api('/sessions/' + native.automaticSealed.world.header.sessionId);
      await require('./clock-browser.cjs')({ context, api, tokens, base, mission: session.mission, screenshots: output, check });
    }
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-world').click();
    await page.waitForFunction(() => document.querySelector('#world-recording').options.length === 2);
    for (const [name, sealed, tick] of [['automatic', native.automaticSealed, native.automaticReplay.finalTick], ['manual', native.manualSealed, native.manualReplay.finalTick]]) {
      const sessionResponse = await fetch(base + '/api/sessions/' + sealed.world.header.sessionId, { headers: { Authorization: 'Bearer ' + tokens.Master } });
      assert.equal(sessionResponse.status, 200); const session = await sessionResponse.json(), player = session.players[0];
      const log = await fs.readFile(path.join(directory, `clock-${name === 'automatic' ? 'auto' : 'manual'}-client-${player.roomId}.log`), 'utf8');
      const results = log.split(/\r?\n/).filter(line => line.startsWith('VR_CLIENT_DEBRIEF_FINAL '));
      assert.equal(results.length, 1); const result = JSON.parse(results[0].slice('VR_CLIENT_DEBRIEF_FINAL '.length));
      assert.equal(result.sessionId, session.id); assert.equal(result.playerId, player.id); assert.equal(result.admissionId, player.admissionId);
      assert.equal(result.streamId, session.combatStream.streamId); assert.equal(result.roomId, player.roomId); assert.equal(result.origin, 'Simulation');
      assert.equal(result.throughSequence, sealed.statistics.throughSequence); assert.equal(result.worldSequence, sealed.world.acceptedSequence);
      assert.equal(result.finalStreamSequence, session.combatStream.acceptedSequence);
      const expected = sealed.statistics.players.find(value => value.playerId === player.id);
      for (const field of ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent']) assert.equal(result[field], expected[field]);
      check(true, name + ' client final payload matches its original admission and both sealed boundaries / ledger');
      await page.locator('#world-recording').selectOption(sealed.world.header.sessionId);
      await page.locator('#world-live').click();
      await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence, sealed.world.acceptedSequence);
      const elapsed = `${Math.floor(tick / 1200).toString().padStart(2, '0')}:${Math.floor(tick / 20 % 60).toString().padStart(2, '0')}`;
      check((await page.locator('#world-status').innerText()).includes(`活動時間 ${elapsed} / 計畫 01:00`), name + ' observer clock matches the sealed native source tick');
      check((await page.locator('#world-freshness').innerText()).includes('封存') && (await page.locator('#world-statistics').innerText()).includes('PC room'), name + ' native recording remains sealed with its real ledger');
      await page.screenshot({ path: path.join(output, name + '-clock.png'), fullPage: true });
    }
    check(errors.length === 0, 'Native recording clock viewer has no uncaught page errors');
    await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify({ complete: true, checks, source: 'Actual native recordings; Chromium SwiftShader observer; separate runtime copy', headsets: 0 }, null, 2));
  } finally {
    if (browser) await browser.close();
    if (processApi.exitCode === null) { const stopped = new Promise(resolve => processApi.once('exit', resolve)); processApi.kill(); await stopped; }
  }
  console.log('PASS: ' + checks + ' native recording observer checks');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
