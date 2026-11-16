// Server-only control helper plus separately owned PC clients launched from actual UI downloads.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { execFile, execFileSync, spawn } = require('node:child_process');
const { promisify } = require('node:util');
const { createHash } = require('node:crypto');
const { networkInterfaces } = require('node:os');
const { requireSilentWindowsLaunch } = require('./windows-firewall.cjs');
const root = path.resolve(__dirname, '../..');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(predicate, label, seconds = 35) {
  const deadline = Date.now() + seconds * 1000;
  while (Date.now() < deadline) { const value = await predicate(); if (value) return value; await sleep(150); }
  throw Error('Timed out: ' + label);
}
async function main() {
  const readyPath = path.resolve(process.argv[2] || ''), directory = path.dirname(readyPath);
  assert.equal(path.basename(readyPath), 'ready.json'); assert.equal(path.dirname(directory), path.join(root, 'artifacts/desktop-venue'));
  assert.match(path.basename(directory), /^\d{8}-\d{6}-[a-f0-9]{8}$/);
  const ready = JSON.parse(await fs.readFile(readyPath, 'utf8')); const base = new URL(ready.baseUrl);
  const options = process.argv.slice(3);
  const packageRoot = options[0] && !options[0].startsWith('--') ? path.resolve(options.shift()) : null;
  const addressOptions = options.filter(option => option.startsWith('--local-game-address='));
  const knownOptions = ['--package-interactive', '--package-path-input', '--package-ticket-preview', '--package-mock-openxr', '--launcher-status', '--room-ticket-bundle'];
  assert.ok(options.every(option => knownOptions.includes(option) || addressOptions.includes(option)), 'Unknown external workflow option');
  assert.ok(addressOptions.length <= 1, 'Specify one local game address');
  const gameAddress = addressOptions[0]?.slice('--local-game-address='.length) ?? '127.0.0.1';
  if (addressOptions.length) {
    const localInterface = Object.values(networkInterfaces()).flat().find(entry =>
      entry.family === 'IPv4' && !entry.internal && entry.address === gameAddress);
    assert.ok(localInterface, 'Game address must be an assigned non-loopback IPv4 on this host');
    const [first, second] = gameAddress.split('.').map(Number);
    assert.ok(first === 10 || (first === 172 && second >= 16 && second <= 31) ||
      (first === 192 && second === 168), 'Use a private IPv4 for the local game interface test');
  }
  assert.equal(ready.advertiseAddress, gameAddress, 'Fixture must advertise the selected game address');
  assert.equal(ready.listenAddress, gameAddress, 'Fixture must bind the selected game address');
  const interactivePackage = options.includes('--package-interactive');
  assert.ok(!interactivePackage || packageRoot, 'Interactive mode requires a player package');
  const packagePathInput = options.includes('--package-path-input');
  assert.ok(!packagePathInput || interactivePackage, 'Path entry requires the actual interactive player launcher');
  const packageTicketPreview = options.includes('--package-ticket-preview');
  assert.ok(!packageTicketPreview || packagePathInput, 'Ticket preview requires the actual launcher path entry');
  const packageMockOpenXR = options.includes('--package-mock-openxr');
  assert.ok(!packageMockOpenXR || interactivePackage && process.env.XR_RUNTIME_JSON && process.env.VR_COMMAND_OPENXR_MOCK_DLL,
    'Mock OpenXR requires an interactive player package and the per-process mock runtime');
  const launcherStatus = options.includes('--launcher-status');
  const roomTicketBundle = options.includes('--room-ticket-bundle');
  assert.ok(!launcherStatus || packageRoot && !interactivePackage, 'Status CLI checks require a package and no GUI mode');
  const packageManifest = packageRoot ? JSON.parse(await fs.readFile(path.join(packageRoot, 'player-package.json'), 'utf8')) : null;
  if (packageRoot) {
    assert.equal(path.basename(packageRoot), 'VRCommand-Player');
    assert.equal(packageManifest.version, 1); assert.equal(packageManifest.platform, 'Windows-x64');
    assert.equal(packageManifest.build.sourceFingerprint, ready.playerBuildReceipt.sourceFingerprint);
    assert.equal(packageManifest.launcherSourceSha256, createHash('sha256').update(await fs.readFile(path.join(root, 'tools/WindowsPlayerLauncher/PlayerLauncher.cs'))).digest('hex'));
  }
  assert.equal(ready.source, 'Simulation'); assert.equal(ready.clientMode, 'External'); assert.equal(ready.headsets, null);
  assert.equal(base.hostname, '127.0.0.1'); assert.equal(base.protocol, 'http:'); assert.notEqual(base.port, '5080');
  assert.ok(!base.username && !base.password && !base.search && !base.hash && base.pathname === '/');
  const playerExecutable = await fs.realpath(packageRoot ? path.join(packageRoot, 'VrCommand.exe') : ready.playerBuildReceipt.outputPath);
  const launcherExecutable = packageRoot ? path.join(packageRoot, 'Launch-Player.exe') : playerExecutable;
  const tokens = JSON.parse(await fs.readFile(path.join(directory, 'keys.json'), 'utf8')).OperatorKeys;
  const children = [], findings = [], errors = [], socketsToClose = []; let checks = 0, page, browser, outcome;
  const evidence = path.join(directory, 'external-ui'); await fs.mkdir(evidence, { recursive: false });
  async function fingerprint() {
    const hash = createHash('sha256');
    for (const file of ['scripts/start-desktop-control.py', 'scripts/start-desktop-venue.py', 'tests/browser/check-external-native.cjs',
      'tests/browser/windows-firewall.cjs', 'scripts/check-windows-firewall-notifications.ps1',
      ...(packageRoot ? ['scripts/package-windows-player.py', 'tools/WindowsPlayerLauncher/PlayerLauncher.cs'] : []),
      ...(packageTicketPreview ? ['tests/browser/check-player-ticket-ui.ps1'] : [])]) {
      hash.update(file); hash.update(await fs.readFile(path.join(root, file)));
    }
    return hash.digest('hex');
  }
  const originalTool = await fingerprint();
  const check = (value, message) => { assert.ok(value, message); checks++; findings.push(message); console.log('PASS:', message); };
  async function api(route, role = 'Master', method = 'GET', body, expected = 200) {
    const response = await fetch(ready.baseUrl + '/api' + route, { method, headers: { Authorization: 'Bearer ' + tokens[role], 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(5000) });
    assert.equal(response.status, expected, route); return response.status === 204 ? null : response.json();
  }
  try {
    requireSilentWindowsLaunch(root, playerExecutable);
    if (launcherStatus) requireSilentWindowsLaunch(root, process.execPath);
    browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, acceptDownloads: true }); page = await context.newPage(); page.setDefaultTimeout(25000);
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(ready.baseUrl + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click(); await page.locator('#draft-name').fill('外部玩家連線流程'); await page.locator('#draft-briefing').fill('Downloaded client configuration, normal native admission, Simulation');
    await page.locator('#draft-count').fill('0'); await page.locator('#draft-auto-attack').uncheck();
    await page.locator('#mission-form button[type=submit]').click(); await page.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存'));
    const mission = (await api('/missions'))[0];
    await page.locator('#tab-operations').click(); await page.locator('#launch-mission').selectOption(mission.id); await page.locator('#launch-room').selectOption('3');
    await page.locator('#create-session-form button').click(); await page.waitForFunction(() => !document.querySelector('#session-panel').hidden);
    const id = await page.locator('#session-select').inputValue();
    const endpoint = await until(async () => { const rows = JSON.parse(await fs.readFile(path.join(directory, 'connection-endpoints.json'), 'utf8').catch(() => '{}')); return rows[id]; }, 'own source endpoint');
    await page.waitForFunction(({ address, port }) => document.querySelector('#game-address').value === address && Number(document.querySelector('#game-port').value) === port, { address: gameAddress, port: endpoint.port });
    check(endpoint.version === 1 && endpoint.address === gameAddress && endpoint.sessionId === id, 'Server-only launcher publishes its own source-bound endpoint and the console applies its real port');
    const processes = JSON.parse(await fs.readFile(path.join(directory, 'server-processes.json'), 'utf8'));
    const probe = spawn('netstat.exe', ['-ano', '-p', 'UDP'], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let sockets = ''; probe.stdout.on('data', value => { sockets += value.toString(); });
    await new Promise((resolve, reject) => { probe.once('error', reject); probe.once('exit', code => code === 0 ? resolve() : reject(Error('Native UDP inventory failed'))); });
    const bound = sockets.split(/\r?\n/).map(line => line.trim().split(/\s+/)).filter(row => row[0] === 'UDP' && row.at(-1) === String(processes[id].processId) && row[1]?.endsWith(':' + endpoint.port));
    check(bound.length === 1 && bound[0][1] === `${gameAddress}:${endpoint.port}`, 'Actual owned server UDP socket binds the selected address and port');
    await fs.writeFile(path.join(evidence, 'native-listen.json'), JSON.stringify({ processId: processes[id].processId, address: bound[0][1] }, null, 2));
    for (const name of ['External PC 1', 'External PC 2']) {
      await page.locator('#player-name').fill(name); await page.locator('#join-form button').click();
      await page.waitForFunction(name => document.querySelector('#roster').textContent.includes(name), name);
    }
    let session = await api('/sessions/' + id);
    await sleep(1200);
    const before = await api(`/sessions/${id}/readiness`);
    const owned = (await fs.readdir(directory)).filter(name => name.startsWith('operator-' + id + '-client-'));
    check(owned.length === 0 && before.players.length === 2 && before.players.every(player => !player.canParticipate), 'Server-only mode leaves both admissions unclaimed until external clients start');
    let bundlePath;
    if (roomTicketBundle) {
      await page.locator('#ticket-room').selectOption('3');
      const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#download-room-tickets').click()]);
      assert.equal(download.suggestedFilename(), 'room-03-connections.zip');
      bundlePath = path.join(evidence, download.suggestedFilename());
      await download.saveAs(bundlePath);
    }
    const configs = [];
    for (let index = 0; index < 2; index++) {
      const name = 'External PC ' + (index + 1), row = page.locator('#roster tr').filter({ hasText: name });
      const player = session.players.find(player => player.name === name);
      const file = path.join(evidence, packageRoot ? 'player ' + (index + 1) + ' 玩家 &.json' : 'player-' + (index + 1) + '.json');
      if (bundlePath) {
        const seatFile = `room-03-seat-${String(player.seat + 1).padStart(2, '0')}.json`;
        const bytes = execFileSync('python', ['-c', `import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    assert len(archive.namelist()) == 2
    entry = archive.getinfo(sys.argv[2])
    assert entry.file_size <= 32768
    sys.stdout.buffer.write(archive.read(entry))`, bundlePath, seatFile],
          { windowsHide: true, timeout: 5000, maxBuffer: 32768 });
        await fs.writeFile(file, bytes, { flag: 'wx' });
      } else {
        const [download] = await Promise.all([page.waitForEvent('download'), row.getByRole('button', { name: '下載連線檔' }).click()]);
        await download.saveAs(file);
      }
      const config = JSON.parse(await fs.readFile(file, 'utf8'));
      assert.deepEqual(Object.keys(config).sort(), ['address', 'joinTicket', 'port', 'role']);
      assert.ok(!Object.values(tokens).some(token => JSON.stringify(config).includes(token))); assert.equal(config.port, endpoint.port); assert.equal(config.address, endpoint.address);
      const claims = await api('/player-tickets/validate', 'GameServer', 'POST', { sessionId: id, ticket: config.joinTicket, protocolVersion: 2 });
      assert.equal(claims.playerId, player.id); assert.equal(claims.admissionId, player.admissionId);
      const log = path.join(evidence, 'player ' + (index + 1) + ' native.log'), report = path.join(evidence, 'launcher-' + (index + 1) + '.json');
      const executable = launcherExecutable;
      const gui = interactivePackage && index === 0;
      const statusPath = path.join(evidence, 'connection-' + (index + 1) + '.json');
      const args = packageRoot ? [...gui && packagePathInput ? [] : ['--config', file], ...gui ? [] : ['--launch', '--headless', '--wait'], '--log', log, '--report', report, ...launcherStatus ? ['--status-report', statusPath] : []]
        : ['-batchmode', '-nographics', '-job-worker-count', '2', '-logFile', log, '--vr-config', file];
      requireSilentWindowsLaunch(root, playerExecutable);
      const child = spawn(executable, args, { cwd: path.dirname(executable), windowsHide: !gui, stdio: 'ignore' });
      child.on('error', error => { errors.push(error.message); }); const owned = { child, log, player, gui, statusPath, report }; children.push(owned);
      if (packageRoot) {
        if (gui) console.log('PACKAGED_LAUNCHER_UI_READY ' + JSON.stringify({ processId: child.pid, configPath: file }));
        if (gui && packageTicketPreview) {
          assert.ok(['1.2.0', '1.3.0'].includes(packageManifest.launcherVersion));
          assert.equal(claims.roomId, player.roomId); assert.equal(claims.seat, player.seat);
          const parts = config.joinTicket.split('.');
          const payload = Buffer.from(parts[1], 'base64url');
          assert.equal(Number(payload.readBigInt64BE(51)) * 1000, Date.parse(claims.expiresAtUtc));
          payload.writeBigInt64BE(BigInt(Math.floor(Date.now() / 1000) - 60), 51);
          const expired = path.join(evidence, 'expired-preview-fixture.json');
          await fs.writeFile(expired, JSON.stringify({ ...config, joinTicket: `v2.${payload.toString('base64url')}.${parts[2]}` }), { flag: 'wx' });
          const run = await promisify(execFile)('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
            '-File', path.join(__dirname, 'check-player-ticket-ui.ps1'), '-LauncherPid', String(child.pid),
            '-ExpiredConfig', expired, '-CurrentConfig', file, '-LoadLabel', '載入／更新',
            '-PlayLabel', '開始遊戲', '-SeatText', `房間 ${claims.roomId}／席位 ${claims.seat + 1}`,
            '-ExpiredText', '依本機時間已過期', '-RemainingText', '依本機時間尚餘'], { windowsHide: true, timeout: 45000 });
          const preview = JSON.parse(run.stdout);
          check(preview.expiredWarning && preview.changedFileCleared && preview.currentSeatAndTime && preview.launchKeepsSeat,
            'Actual WinForms warns about local expiry, clears stale selection and displays the real downloaded ticket seat before launch');
          await fs.writeFile(path.join(evidence, 'player-ticket-preview.json'), JSON.stringify(preview, null, 2), { flag: 'wx' });
        }
        const started = await until(async () => { if (child.exitCode !== null) throw Error('Packaged launcher exited before starting a player'); const value = JSON.parse(await fs.readFile(report, 'utf8').catch(() => '{}')); if (value.status === 'rejected') throw Error('Packaged launcher rejected the real downloaded config'); return value.status === 'started' && value; }, 'packaged player child', gui ? 240 : 35);
        assert.ok(Number.isSafeInteger(started.processId) && started.processId > 0 && started.processId !== process.pid && started.processId !== child.pid);
        owned.nativeId = started.processId;
      }
      configs.push({ role: config.role, address: config.address, port: config.port, playerId: player.id, admissionId: player.admissionId });
    }
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    check(true, 'Two separately owned real Unity clients join using only the actual UI-downloaded short-ticket configs');
    if (interactivePackage) {
      const [gui, peer] = children;
      const readiness = await api(`/sessions/${id}/readiness`);
      for (const [owned, rigKind] of [[gui, packageMockOpenXR ? 'Tracked' : 'Simulated'], [peer, 'Simulated']]) {
        const row = readiness.players.find(p => p.playerId === owned.player.id && p.admissionId === owned.player.admissionId);
        assert.ok(row?.canParticipate && row.rigKind === rigKind, 'Original seat reports the requested rig kind');
      }
      const lines = (await fs.readFile(gui.log, 'utf8')).split(/\r?\n/);
      const markers = lines.filter(line => line.startsWith('VR_OPENXR_STARTUP '));
      assert.deepEqual(markers, packageMockOpenXR ? ['VR_OPENXR_STARTUP status=requested', 'VR_OPENXR_STARTUP status=active'] : []);
      if (packageMockOpenXR) {
        const network = lines.findIndex(line => line.startsWith('VR_NETWORK_STARTED role=Client started=True '));
        assert.ok(lines.some(line => line.includes('Runtime Name: Unity Mock Runtime')), 'Owned player confirms the Unity Mock Runtime');
        assert.ok(lines.indexOf(markers[1]) < network, 'Selected OpenXR mode becomes active before the owned player starts transport');
      }
      check(true, packageMockOpenXR ? 'Actual WinForms OpenXR selection starts the tracked rig before transport'
        : 'Actual WinForms desktop launch starts the simulated rig without requesting OpenXR');
    }
    if (launcherStatus) {
      for (const owned of children) {
        const state = await until(async () => { const s = JSON.parse(await fs.readFile(owned.statusPath, 'utf8').catch(() => '{}')); return s.state === 'Connected' && s; }, 'launcher actual admission status');
        assert.equal(state.processId, owned.nativeId); assert.equal(state.complete, true); assert.equal(state.logAvailable, true);
      }
      check(true, 'Both actual launchers distinguish their own native Connected marker from process startup');
      const config = JSON.parse(await fs.readFile(path.join(evidence, 'player 1 玩家 &.json'), 'utf8'));
      const socket = require('node:dgram').createSocket('udp4'); socketsToClose.push(socket);
      await new Promise((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
      for (const [label, value, expected] of [['rejected', { ...config, joinTicket: 'invalid-status-test-ticket' }, ['Rejected']],
        ['no-gameserver', { ...config, port: socket.address().port }, ['Unconfirmed', 'Disconnected']]]) {
        const file = path.join(evidence, label + '.json'), log = path.join(evidence, label + '.log'), report = path.join(evidence, label + '-launch.json'), statusPath = path.join(evidence, label + '-status.json');
        await fs.writeFile(file, JSON.stringify(value), { flag: 'wx' });
        requireSilentWindowsLaunch(root, playerExecutable);
        const child = spawn(launcherExecutable, ['--config', file, '--launch', '--headless', '--wait', '--log', log, '--report', report, '--status-report', statusPath], { cwd: packageRoot, windowsHide: true, stdio: 'ignore' });
        child.on('error', error => errors.push(error.message)); const owned = { child, log, gui: false, statusPath }; children.push(owned);
        const started = await until(async () => { const r = JSON.parse(await fs.readFile(report, 'utf8').catch(() => '{}')); return r.status === 'started' && r; }, 'status probe child'); owned.nativeId = started.processId;
        const state = await until(async () => { const s = JSON.parse(await fs.readFile(statusPath, 'utf8').catch(() => '{}')); return expected.includes(s.state) && s; }, 'actual native ' + label + ' status', 45);
        assert.equal(state.complete, true); assert.ok(!state.transitions.includes('Connected'));
        check(true, label + ': actual native log status never fabricates admission or a specific network root cause');
      }
      assert.equal((await api(`/sessions/${id}/readiness`)).players.filter(p => p.canParticipate).length, 2);
    }
    await page.screenshot({ path: path.join(evidence, 'external-connected.png'), fullPage: true });
    await page.locator('[data-command=Begin]').click(); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    await page.locator('[data-command=Pause]').click(); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已暫停');
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    check((await page.locator('#readiness-summary').innerText()).includes('Simulation'), 'Control Begin and Pause reach both native clients while provenance stays Simulation');
    await page.locator('#include-ended').check(); page.once('dialog', dialog => dialog.accept()); await page.locator('[data-command=End]').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已結束');
    const world = await until(async () => { const value = await api(`/sessions/${id}/world`); return value.complete && value; }, 'exact world seal');
    const stats = await api(`/sessions/${id}/statistics`); assert.equal(stats.pendingTelemetry, false);
    const results = [];
    for (const { log, player, statusPath } of children.filter(child => child.player)) {
      const result = await until(async () => {
        const text = await fs.readFile(log, 'utf8').catch(() => ''); const found = text.match(/VR_CLIENT_DEBRIEF_FINAL (\{[^\r\n]+\})/);
        return found && text.includes('VR_CLIENT_DISCONNECTED') && JSON.parse(found[1]);
      }, 'external client final acknowledgement');
      const expected = stats.players.find(row => row.playerId === player.id);
      assert.equal(result.sessionId, id); assert.equal(result.playerId, player.id); assert.equal(result.admissionId, player.admissionId); assert.equal(result.origin, 'Simulation');
      assert.equal(result.streamId, world.header.streamId); assert.equal(result.worldSequence, world.acceptedSequence); assert.equal(result.throughSequence, stats.throughSequence);
      for (const field of ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent']) assert.equal(result[field], expected[field]);
      results.push(result);
      if (launcherStatus) {
        const state = await until(async () => { const s = JSON.parse(await fs.readFile(statusPath, 'utf8').catch(() => '{}')); return s.state === 'Final' && s; }, 'launcher retained sealed result status');
        assert.equal(state.complete, true);
        const pending = (await fs.readFile(log, 'utf8')).includes(`VR_CLIENT_DEBRIEF_PENDING ${id}`);
        assert.deepEqual(state.transitions, pending ? ['Waiting', 'Connected', 'ResultPending', 'Final'] : ['Waiting', 'Connected', 'Final']);
        const serialized = JSON.stringify(state); assert.ok(!serialized.includes(player.id) && !serialized.includes(player.admissionId) && !Object.values(tokens).some(token => serialized.includes(token)));
      }
    }
    check(results.length === 2, 'Both external clients receive only their own final admission result, matching all sealed ledger fields and world sequence');
    if (launcherStatus) check(true, 'Launcher Final survives normal disconnect and status reports contain no ticket, actor identity or raw result payload');
    await page.screenshot({ path: path.join(evidence, 'external-ended.png'), fullPage: true });
    check(await page.locator('#apply-connection-endpoint').isDisabled() && await page.locator('#roster .ready-player').count() === 0, 'Ended endpoint remains historical metadata and cannot restore player participation');
    check(errors.length === 0 && await page.evaluate(() => !localStorage.length && !sessionStorage.length && !document.cookie), 'External workflow has no script errors or persisted operator credentials');
    assert.equal(await fingerprint(), originalTool);
    if (packageRoot) check(children.every(row => row.nativeId) && packageManifest.build.sourceFingerprint === ready.playerBuildReceipt.sourceFingerprint, 'Both players run from the extracted portable package via its real launcher, with Unicode / spaces / ampersand config paths');
    const networkScope = addressOptions.length ? 'same-host private IPv4' : 'same-host loopback';
    outcome = { complete: true, toolFingerprint: originalTool, checks, findings, configs, results, world, stats, packageRoot, packageManifest, roomTicketBundle,
      guiMode: interactivePackage ? (packageMockOpenXR ? 'OpenXRMock' : 'Desktop') : null, networkScope, gameAddress,
      scope: `Two separately launched PC clients / ${networkScope} / Chromium SwiftShader / zero headsets` };
    await fs.writeFile(path.join(evidence, 'workflow-checks.json'), JSON.stringify({ ...outcome, complete: false, workflowComplete: true, cleanupPending: true }, null, 2));
  } catch (error) {
    if (page && !page.isClosed()) await page.screenshot({ path: path.join(evidence, 'failure.png'), fullPage: true }).catch(() => {});
    throw error;
  } finally {
    for (const socket of socketsToClose) socket.close();
    const cleanupErrors = [], stopped = [];
    for (const owned of children) {
      const { child, gui, report } = owned;
      let nativeId = owned.nativeId;
      try {
      const terminal = () => child.exitCode !== null || child.signalCode !== null;
      if (gui && !nativeId) {
        if (!terminal()) child.kill();
        await until(terminal, 'owned launcher exits after UI failure', 15);
        const state = JSON.parse(await fs.readFile(report, 'utf8').catch(() => '{}'));
        if (state.status === 'started' && Number.isSafeInteger(state.processId) && state.processId > 0
          && state.processId !== child.pid && state.processId !== process.pid) nativeId = state.processId;
      }
      if (nativeId) {
        try { process.kill(nativeId); } catch (error) { if (error.code !== 'ESRCH') throw error; }
        await until(() => { try { process.kill(nativeId, 0); return false; } catch (error) { if (error.code === 'ESRCH') return true; throw error; } }, 'owned packaged native child exits', 15);
        if (gui && !terminal()) child.kill();
        await until(terminal, 'owned launcher exits', 15);
      } else if (!terminal()) { const exited = new Promise(resolve => child.once('exit', resolve)); child.kill(); await exited; }
      stopped.push({ processId: child.pid, nativeId, exitCode: child.exitCode, signal: child.signalCode, nativeGone: nativeId ? true : null });
      } catch (error) { cleanupErrors.push(error.message); }
    }
    try { if (browser) await browser.close(); } catch (error) { cleanupErrors.push(error.message); }
    await fs.writeFile(path.join(directory, 'end.request'), 'End this owned helper after its external result grace\n', { flag: 'wx' }).catch(error => { if (error.code !== 'EEXIST') cleanupErrors.push(error.message); });
    await fs.writeFile(path.join(evidence, 'native-cleanup.json'), JSON.stringify({ complete: cleanupErrors.length === 0, stopped, errors: cleanupErrors }, null, 2));
    if (cleanupErrors.length) throw Error('Owned child cleanup failed: ' + cleanupErrors.join('; '));
  }
  await fs.writeFile(path.join(evidence, 'checks.json'), JSON.stringify(outcome, null, 2));
  console.log('PASS: ' + checks + ' actual external-player workflow checks');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
