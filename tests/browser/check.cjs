// Runs the shipped console against an isolated, real API and SQLite store.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { randomBytes, randomUUID } = require('node:crypto');
const checkedLoopbackHost = require('./windows-firewall.cjs');
const root = path.resolve(__dirname, '../..');
let checks = 0;
function check(condition, description) { assert.ok(condition, description); checks++; console.log('PASS:', description); }
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function availablePort() {
  const server = net.createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port; await new Promise(resolve => server.close(resolve)); return port;
}
async function main() {
  const dotnet = checkedLoopbackHost(root);
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'vr-console-'));
  if (path.dirname(path.resolve(directory)) !== path.resolve(os.tmpdir()) || !path.basename(directory).startsWith('vr-console-')) throw new Error('Unsafe cleanup target');
  const screenshots = process.env.VR_COMMAND_BROWSER_ARTIFACTS ? path.resolve(process.env.VR_COMMAND_BROWSER_ARTIFACTS) : path.join(root, 'artifacts/console');
  if (process.env.VR_COMMAND_BROWSER_ARTIFACTS && (path.dirname(screenshots) !== path.join(root, 'artifacts') || !/^console-[a-zA-Z0-9-]+$/.test(path.basename(screenshots)))) throw new Error('Use a new direct artifacts/console-* output directory');
  await fs.mkdir(screenshots, { recursive: !process.env.VR_COMMAND_BROWSER_ARTIFACTS });
  const tokens = Object.fromEntries(['Master', 'Room1', 'Room2', 'Room4', 'GameServer'].map(role => [role, randomBytes(32).toString('hex')]));
  const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toLowerCase().startsWith('operatorkeys__') && !['operatorkeyfile', 'playerticketsigningkey'].includes(key.toLowerCase())));
  const instanceId = randomUUID();
  Object.assign(environment, { DataDirectory: path.join(directory, 'missions'), SessionDataDirectory: path.join(directory, 'sessions'), ControlInstanceId: instanceId, ASPNETCORE_ENVIRONMENT: 'Production', Logging__LogLevel__Default: 'Warning' });
  for (const [role, value] of Object.entries(tokens)) environment['OperatorKeys__' + role] = value;
  const base = 'http://127.0.0.1:' + await availablePort();
  const processApi = spawn(dotnet, [process.env.VR_COMMAND_API_DLL || path.join(root, 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll'), '--urls', base], { cwd: root, env: environment, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  const apiStarted = performance.now(), apiTerminal = () => processApi.exitCode !== null || processApi.signalCode !== null;
  let apiLog = '';
  for (const stream of [processApi.stdout, processApi.stderr]) stream.on('data', data => { apiLog = (apiLog + data.toString()).slice(-6000); });
  let browser, diagnosticPage;
  try {
    for (let attempt = 0; ; attempt++) {
      try { if ((await fetch(base + '/health')).ok) break; } catch { /* Wait only for this fixture's live child process. */ }
      if (apiTerminal() || attempt > 100) {
        const redacted = Object.values(tokens).reduce((text, key) => text.replaceAll(key, '[redacted]'), apiLog);
        await fs.writeFile(path.join(screenshots, 'api-startup-failure.json'), JSON.stringify({ attempts: attempt, elapsedMilliseconds: performance.now() - apiStarted, exitCode: processApi.exitCode, signalCode: processApi.signalCode, log: redacted }, null, 2));
        throw new Error('Isolated API did not start: ' + redacted);
      }
      await delay(100);
    }
    async function api(route, method = 'GET', body, role = 'Master', expected = 200, admissionId, requestId) {
      const response = await fetch(base + '/api' + route, { method, headers: { Authorization: 'Bearer ' + tokens[role], 'Content-Type': 'application/json', ...(admissionId ? { 'If-Match-Admission': admissionId } : {}), ...(requestId ? { 'Idempotency-Key': requestId } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
      assert.equal(response.status, expected, method + ' ' + route);
      return response.status === 204 ? null : response.json();
    }
    const shell = await fetch(base + '/console/');
    check(shell.ok && shell.headers.get('content-security-policy').includes("script-src 'self'") && shell.headers.get('cache-control').includes('no-store'), 'Console shell is served with its content and cache policies');
    check((await fetch(base + '/api/rooms')).status === 401, 'Serving the console does not bypass API authentication');
    browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, acceptDownloads: true });
    const page = await context.newPage(), browserErrors = [];
    diagnosticPage = page;
    function captureErrors(target) { target.on('pageerror', error => browserErrors.push(error.message)); target.on('console', message => { if (/Content Security Policy|violates.*directive/i.test(message.text())) browserErrors.push(message.text()); }); }
    captureErrors(page);
    if (process.argv.includes('--server-plan-only')) {
      await require('./server-plan-browser.cjs').checkServerPlan({ context, api, tokens, base, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Server plan has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'venue server plan with isolated API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused server plan checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--venue-launch-review-only')) {
      await require('./venue-launch-review-browser.cjs').checkVenueLaunchReview({ context, api, tokens, base, screenshots, check, captureErrors, instanceId });
      check(browserErrors.length === 0, 'Venue launch review has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'read-only launch review with isolated API and Chromium' }, null, 2));
      return;
    }
    if (process.argv.includes('--venue-time-replay-only')) {
      await require('./venue-time-replay-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Venue time replay has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'closed venue recordings and original UTC matches' }, null, 2));
      console.log(`PASS: ${checks} focused venue time replay checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--full-participation-only')) {
      await require('./full-tracking-begin-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors, participationOnly: true });
      check(browserErrors.length === 0, 'Participation Begin has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused participation checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--world-only') || process.argv.includes('--live-watch-only') || process.argv.includes('--live-event-only')) {
      const worldOnly = process.argv.includes('--world-only');
      const liveEventOnly = process.argv.includes('--live-event-only');
      await page.goto(base + '/console/');
      await page.locator('#login-key').fill(tokens.Master);
      await page.locator('#login-form button').click();
      await require('./world-browser.cjs')({ page, context, api, tokens, directory, root, base, screenshots, check, liveWatchOnly: !worldOnly, liveEventOnly });
      check(browserErrors.length === 0, 'World observation and replay have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused ${worldOnly ? 'world observation and replay' : 'live observation'} checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--environment-only')) {
      await page.goto(base + '/console/');
      await page.locator('#login-key').fill(tokens.Master);
      await page.locator('#login-form button').click();
      await require('./environment-browser.cjs')({ page, api, tokens, directory, root, base, screenshots, check });
      check(browserErrors.length === 0, 'Environment and recorded policy review have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused environment and policy checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--layout-only')) {
      const mission = await api('/missions', 'POST', { name: 'Layout test template', briefing: '', durationSeconds: 600,
        environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
        enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
      await require('./layout-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
      await require('./saved-layout-identity-browser.cjs')({ context, api, tokens, base, check, captureErrors });
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'Placement and walkthrough previews with real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused layout checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--ticket-download-fence-only')) {
      await require('./ticket-download-fence.cjs').checkTicketDownloadFence({ context, api, tokens, base, screenshots, check, captureErrors });
      await require('./seat-ticket-scope-browser.cjs')({ context, api, tokens, base, check, captureErrors });
      check(browserErrors.length === 0, 'Ticket download fence has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'Ticket download roster checks with real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused ticket download checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--statistics-snapshot-only')) {
      const mission = await api('/missions', 'POST', { name: 'Battle statistics snapshot', briefing: 'Verify consistent revisions', durationSeconds: 600, environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false }, enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
      const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
      const playerId = randomUUID();
      await api('/sessions/' + session.id + '/players', 'POST', { playerId, name: 'Alpha 01', roomId: 1, headset: 'Quest3' });
      await api('/sessions/' + session.id + '/commands', 'POST', { commandId: randomUUID(), action: 'Begin' });
      await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
      await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
      const held = await require('./statistics-fence.cjs')({ page, api, base, session, playerId, shotId: randomUUID(), enemyId: randomUUID(), reportId: randomUUID, screenshots, check });
      try {
        held.release();
        await page.waitForFunction(sequence => document.querySelector('#session-meta').textContent.endsWith('序號 ' + sequence)
          && document.querySelector('#event-list li')?.textContent.includes('#' + sequence + ' ')
          && Array.from(document.querySelectorAll('#statistics tr td'), cell => cell.textContent).join('|') === 'Alpha 01|1|1|20|1|100%|80', held.acceptedSequence, { polling: 100 });
        check(browserErrors.length === 0, 'Statistics snapshot refresh reaches final combat totals without browser or policy errors');
      } finally { await held.dispose(); }
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'Battle statistics snapshot, real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused statistics snapshot checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--mission-versions-only')) {
      const mission = await api('/missions', 'POST', { name: '任務版本核對', briefing: '原始開場簡報', durationSeconds: 900,
        environment: { mode: 'VR', weather: 'Storm', timeOfDay: 'Night', lightning: true }, enemies: { count: 1, behavior: 'Hold', autoAttack: false },
        props: [{ assetId: 'sandbag', position: { x: 3.5, y: 0, z: 2 }, yawDegrees: 45 }] }, 'Master', 201);
      const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [1] }, 'Master', 201);
      await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
      await page.locator('#tab-missions').click(); await page.locator(`#edit-mission option[value="${mission.id}"]`).waitFor({ state: 'attached' });
      await page.locator('#load-mission').click(); await page.waitForFunction(name => document.querySelector('#draft-name').value === name, mission.definition.name);
      await require('./mission-browser.cjs')({ page, context, api, tokens, base, mission, session, screenshots, check });
      await require('./mission-template-browser.cjs')({ context, api, tokens, directory, root, base, screenshots, check, captureErrors, availablePort, dotnet });
      check(browserErrors.length === 0, 'Mission versions have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'mission version comparison and exact launch with real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused mission version checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--vr-venue-tickets-only')) {
      await require('./vr-venue-tickets-browser.cjs')({ context, api, tokens, base, root, directory, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'VR venue ticketing has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'real API and Chromium VR ticketing with synthetic sources' }, null, 2));
      console.log(`PASS: ${checks} focused VR venue ticket checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--placement-history-only')) {
      const mission = await api('/missions', 'POST', { name: 'Placement history focused fixture', briefing: 'Local editing with actual immutable revision saves', durationSeconds: 600, environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false }, enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
      await require('./placement-history-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'focused object undo/redo UI with real mission revisions; no Unity or headset' }, null, 2));
      console.log(`PASS: ${checks} focused placement-history checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--closure-only')) {
      const mission = await api('/missions', 'POST', { name: 'Closure focused fixture', briefing: 'UI source metadata fixtures and real End retry', durationSeconds: 600, environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false }, enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
      await require('./closure-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'focused archive UI, real End retry and room command isolation; no Unity or headset' }, null, 2));
      console.log(`PASS: ${checks} focused closure checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--field-evidence-only')) {
      await require('./field-evidence-browser.cjs')({ context, api, tokens, directory, root, base, screenshots, check });
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'sealed field data ZIP using real API, WorldRelay and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused field evidence checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--mission-read-only')) {
      await require('./mission-read-recovery.cjs')({ context, api, tokens, base, screenshots, check });
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), playwright: require('playwright/package.json').version, result: 'passed', scope: 'focused mission read recovery only; isolated API and Chromium, no Unity or headset' }, null, 2));
      console.log(`PASS: ${checks} focused mission-read checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--mr-start-only')) {
      await require('./mr-start-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'MR lifecycle check has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'MR start and resume with a real API and synthetic tracked world publisher' }, null, 2));
      console.log(`PASS: ${checks} focused MR lifecycle checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--tracked-vr-start-only')) {
      await require('./tracked-vr-start-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Tracked VR start has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed', scope: 'real API and Chromium, synthetic tracked frames' }, null, 2));
      console.log(`PASS: ${checks} focused tracked VR start checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--mr-pins-only')) {
      await require('./mr-alignment-pins-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
      await require('./venue-mr-alignment-browser.cjs')({ context, api, tokens, base, check, captureErrors });
      check(browserErrors.length === 0, 'MR pin checks have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'MR file upload and pinning against a real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused MR pin checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--independent-set-only')) {
      await require('./independent-set-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
      await require('./archived-independent-plan-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
      await require('./venue-mission-file-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
      await require('./session-reprepare-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Independent set checks have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'Atomic five-room preparation with actual API, SQLite and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused independent set checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--vr-connection-check-only')) {
      await require('./vr-connection-check-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'VR file checks have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'VR seat file check against a real API and Chromium with synthetic game source' }, null, 2));
      console.log(`PASS: ${checks} focused VR connection file checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--mr-deployment-only')) {
      await require('./mr-deployment-browser.cjs')({ context, api, tokens, base, directory, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'MR deployment checks have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'MR deployment file checks against a real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused MR deployment checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--mr-venue-bundle-only')) {
      await require('./mr-venue-bundle-browser.cjs')({ context, api, tokens, base, root, directory, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'MR venue export has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), result: 'passed', scope: 'five-room MR deployment ZIP from a real API and Chromium, with synthetic endpoint publishers', powerShell: process.env.VR_COMMAND_VENUE_DEPLOY_CHECK === '1' }, null, 2));
      console.log(`PASS: ${checks} focused MR venue bundle checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--room-clock-only')) {
      await require('./room-clock-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Room clocks have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks,
        browser: await browser.version(), result: 'passed', scope: 'room clocks with real API, accepted synthetic WebSocket frames and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused room clock checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--vr-participation-pause-only')) {
      await require('./vr-participation-pause-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'VR participation pause has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused VR participation pause checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--venue-scores-only')) {
      await require('./venue-scores-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Venue scores have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused venue score checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--setting-drafts-only')) {
      await require('./setting-drafts-browser.cjs')({ page, api, tokens, base, check });
      check(browserErrors.length === 0, 'Live setting drafts have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused setting draft checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--room-enemy-edit-only')) {
      await require('./room-enemy-edit-browser.cjs')({ page, api, tokens, base, check });
      check(browserErrors.length === 0, 'Room policy edits have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checks, result: 'passed' }, null, 2));
      console.log(`PASS: ${checks} focused room policy checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--venue-phase-only')) {
      await require('./venue-phase-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Venue phase controls have no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks,
        browser: await browser.version(), result: 'passed', scope: 'whole-venue phase transitions with real API, SQLite and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused venue phase checks. Screenshots: ${screenshots}`); return;
    }
    if (process.argv.includes('--full-tracking-only')) {
      await require('./full-tracking-begin-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
      check(browserErrors.length === 0, 'Full tracking Begin has no uncaught browser or policy errors');
      await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks,
        browser: await browser.version(), result: 'passed', scope: 'guarded venue Begin with accepted synthetic poses, real API and Chromium' }, null, 2));
      console.log(`PASS: ${checks} focused full tracking checks. Screenshots: ${screenshots}`); return;
    }
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill('wrong-key'); await page.locator('#login-form button').click();
    await page.locator('#notice.error').waitFor();
    check(await page.locator('#login-panel').isVisible(), 'Invalid credentials keep the operator on the login screen');
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.waitForFunction(() => document.querySelectorAll('.room-card').length === 5);
    check(await page.locator('#identity').innerText() === '全館主控', 'Master sees all five rooms');
    check(await page.locator('#login-key').inputValue() === '', 'Credential input is cleared after authentication');
    await page.locator('#tab-missions').click();
    await require('./alignment-browser.cjs')({ page, api, base, tokens, screenshots, check });
    await page.locator('#draft-name').fill('夜間防衛・瀏覽器驗證');
    await page.locator('#draft-briefing').fill('守住據點，確認場次控制與配置儲存。');
    await page.locator('#draft-duration').fill('1200');
    await page.locator('#draft-weather').selectOption('Storm'); await page.locator('#draft-time').selectOption('Night'); await page.locator('#draft-lightning').check();
    await page.locator('#add-sandbag').click();
    for (const [id, value] of [['prop-x', '1'], ['prop-z', '3'], ['prop-yaw', '45']]) { await page.locator('#' + id).fill(value); await page.locator('#' + id).blur(); }
    await page.locator('#add-barrel').click();
    for (const [id, value] of [['prop-x', '2'], ['prop-z', '4']]) { await page.locator('#' + id).fill(value); await page.locator('#' + id).blur(); }
    await page.locator('#layout-map').scrollIntoViewIfNeeded();
    check(Number(await page.locator('[data-envelope=sandbag]').getAttribute('width')) === 2
      && Number(await page.locator('[data-envelope=sandbag]').getAttribute('height')) === .7
      && Number(await page.locator('[data-envelope=barrel]').getAttribute('width')) === .7,
      'Layout cover footprints use the authoritative 2m sandbag and 0.7m barrel envelopes');
    const coords = await page.locator('#layout-map').evaluate(svg => [[1, -3], [3, -2]].map(([x, y]) => { const p = svg.createSVGPoint(); p.x = x; p.y = y; const result = p.matrixTransform(svg.getScreenCTM()); return { x: result.x, y: result.y }; }));
    await page.mouse.move(coords[0].x, coords[0].y); await page.mouse.down(); await page.mouse.move(coords[1].x, coords[1].y, { steps: 8 }); await page.mouse.up();
    check(await page.locator('#prop-x').inputValue() === '3' && await page.locator('#prop-z').inputValue() === '2', 'Pointer drag moves a sandbag on the half-metre layout grid');
    await page.locator('#layout-map').press('ArrowRight');
    check(await page.locator('#prop-x').inputValue() === '3.5', 'Keyboard arrows can adjust a selected layout object');
    await page.locator('#mission-form button[type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存'));
    const mission = (await api('/missions'))[0];
    check(mission.definition.props.length === 2 && mission.definition.props[0].position.x === 3.5 && mission.definition.props[0].yawDegrees === 45 && mission.definition.environment.lightning, 'Mission save persists the edited layout and environment through the real API');
    await page.locator('#new-mission').click();
    await page.locator('#load-mission').click();
    await page.waitForFunction(name => document.querySelector('#draft-name').value === name && !document.querySelector('#mission-fields').disabled, mission.definition.name);
    check(await page.locator('#draft-name').inputValue() === mission.definition.name && await page.locator('#prop-layer [data-index]').count() === 2 && await page.locator('#prop-x').inputValue() === '3.5', 'Saved mission can be loaded back into the editor without losing layout coordinates');
    await page.screenshot({ path: path.join(screenshots, 'mission-planner.png'), fullPage: true });
    const lifecycleAttempts = [];
    let loseLifecycle = true, lifecycleKind = 'create';
    async function lifecycleRoute(route) {
      const request = route.request(), pathname = new URL(request.url()).pathname;
      const kind = request.method() === 'DELETE' && /\/players\/[^/]+$/.test(pathname) ? 'leave' : request.method() === 'POST' && /\/players$/.test(pathname) ? 'join' : request.method() === 'POST' && pathname === '/api/sessions' ? 'create' : null;
      if (kind !== lifecycleKind) return route.continue();
      lifecycleAttempts.push({ kind, method: request.method(), path: pathname, body: request.postData(), key: request.headers()['idempotency-key'], admission: request.headers()['if-match-admission'] || null });
      if (loseLifecycle) { loseLifecycle = false; await route.fetch(); await route.abort('failed'); }
      else await route.continue();
    }
    await page.route('**/api/sessions', lifecycleRoute);
    await page.route('**/api/sessions/*/players', lifecycleRoute);
    await page.route('**/api/sessions/*/players/*', lifecycleRoute);
    await page.locator('#tab-operations').click(); await page.locator('#create-session-form button').click();
    await page.locator('#pending-command').waitFor({ state: 'visible' });
    await delay(2100);
    check(await page.locator('#session-panel').isHidden() && await page.locator('#refresh').isDisabled() && (await api('/sessions')).length === 1,
      'Lost creation response exposes retry without a selected session and stops further writes or polling');
    await page.locator('#retry-command').click(); await page.locator('#pending-command').waitFor({ state: 'hidden' });
    await page.waitForFunction(() => !document.querySelector('#session-panel').hidden);
    let session = (await api('/sessions'))[0];
    check(lifecycleAttempts.length === 2 && lifecycleAttempts[0].key && JSON.stringify(lifecycleAttempts[0]) === JSON.stringify(lifecycleAttempts[1]) && (await api('/sessions/' + session.id + '/events')).length === 1,
      'Creation retry retains its UUID and exact body and confirms one durable session');
    check(session.mission.id === mission.id && session.state === 'Preparing', 'Selecting a saved mission creates a preparing session with that definition');
    lifecycleKind = 'join'; loseLifecycle = true; lifecycleAttempts.length = 0;
    await page.locator('#player-name').fill('Alpha 01'); await page.locator('#join-form button').click();
    await page.locator('#pending-command').waitFor({ state: 'visible' });
    check(await page.locator('#player-name').inputValue() === 'Alpha 01' && await page.locator('#join-form button').isDisabled(), 'Lost join response retains the entered player while locking duplicate admission');
    await page.locator('#retry-command').click(); await page.locator('#pending-command').waitFor({ state: 'hidden' });
    await page.waitForFunction(() => document.querySelector('#roster').textContent.includes('Alpha 01'));
    session = await api('/sessions/' + session.id);
    check(lifecycleAttempts.length === 2 && lifecycleAttempts[0].key && JSON.stringify(lifecycleAttempts[0]) === JSON.stringify(lifecycleAttempts[1]) && session.players.length === 1 && session.sequence === 2,
      'Join retry retains the original player UUID and request key with one admitted seat');
    lifecycleKind = null;
    // A lower fixed UUID puts this departed player before Alpha in statistics, exposing row-order assumptions.
    const temporaryPlayer = { playerId: '00000000-0000-0000-0000-000000000001', name: 'Temporary', roomId: session.roomIds[0], headset: 'Quest3' };
    const beforeLeave = await api('/sessions/' + session.id + '/players', 'POST', temporaryPlayer);
    const temporaryAdmission = beforeLeave.players.find(player => player.id === temporaryPlayer.playerId).admissionId;
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#roster').textContent.includes('Temporary'));
    lifecycleKind = 'leave'; loseLifecycle = true; lifecycleAttempts.length = 0;
    page.once('dialog', dialog => dialog.accept()); await page.locator('#roster tr').filter({ hasText: 'Temporary' }).getByRole('button', { name: '移除', exact: true }).click();
    await page.locator('#pending-command').waitFor({ state: 'visible' });
    check((await api('/sessions/' + session.id)).players.length === 1 && await page.locator('#game-address').isDisabled(), 'Lost leave response retains confirmation controls while the server has already removed the player');
    const replacementSession = await api('/sessions/' + session.id + '/players', 'POST', temporaryPlayer);
    const replacement = replacementSession.players.find(player => player.id === temporaryPlayer.playerId);
    check(replacement.admissionId !== temporaryAdmission && lifecycleAttempts[0].admission === temporaryAdmission, 'Removal captures the selected admission even when another operator readmits the same player');
    await page.locator('#retry-command').click(); await page.locator('#pending-command').waitFor({ state: 'hidden' });
    check(lifecycleAttempts.length === 2 && lifecycleAttempts[0].key && JSON.stringify(lifecycleAttempts[0]) === JSON.stringify(lifecycleAttempts[1]) && (await api('/sessions/' + session.id + '/events')).filter(event => event.kind === 'PlayerLeft').length === 1,
      'Leave retry returns confirmation after removal without a second event');
    check((await api('/sessions/' + session.id)).players.find(player => player.id === temporaryPlayer.playerId).admissionId === replacement.admissionId, 'Lost-response retry preserves the replacement player admission');
    lifecycleKind = null;
    await api('/sessions/' + session.id + '/players/' + temporaryPlayer.playerId, 'DELETE', undefined, 'Master', 204, replacement.admissionId);
    await page.locator('#refresh').click(); await page.waitForFunction(() => document.querySelectorAll('#roster tr').length === 1);
    const ticketButton = page.locator('#roster button').filter({ hasText: '下載連線檔' });
    const ticketRoute = '**/join-ticket'; let ticketRequests = 0;
    const observeTicket = async route => { ticketRequests++; await route.continue(); };
    await page.route(ticketRoute, observeTicket);
    for (const [address, port] of [['127.1', '7777'], ['0.0.0.0', '7777'], ['224.0.0.1', '7777'], ['127.0.0.1', '65536']]) {
      await page.locator('#game-address').fill(address); await page.locator('#game-port').fill(port);
      await ticketButton.click();
      await page.waitForFunction(() => !document.querySelector('#session-select').disabled);
      check(ticketRequests === 0 && (await page.locator('#notice').innerText()).includes('完整 IPv4'), `Invalid player destination ${address}:${port} is rejected before requesting a ticket`);
    }
    await page.locator('#game-address').fill('127.0.0.1');
    await page.locator('#game-port').fill('7777');
    const [download] = await Promise.all([page.waitForEvent('download'), ticketButton.click()]);
    await page.unroute(ticketRoute, observeTicket);
    check(ticketRequests === 1, 'A corrected player destination sends one ticket request');
    const configPath = path.join(directory, 'player.json'); await download.saveAs(configPath);
    const config = JSON.parse(await fs.readFile(configPath, 'utf8'));
    check(JSON.stringify(Object.keys(config).sort()) === JSON.stringify(['address', 'joinTicket', 'port', 'role']) && !Object.values(tokens).some(key => JSON.stringify(config).includes(key)), 'Downloaded headset configuration contains only player connection fields');
    const validatedTicket = await api('/player-tickets/validate', 'POST', { sessionId: session.id, ticket: config.joinTicket, protocolVersion: 2 }, 'GameServer');
    check(config.joinTicket.startsWith('v2.') && validatedTicket.playerId === session.players[0].id && validatedTicket.admissionId === session.players[0].admissionId, 'Downloaded V2 ticket validates the exact selected player admission');
    await page.locator('[data-command=Begin]').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
    check((await api('/sessions/' + session.id)).state === 'Running', 'Operator starts the mission from the console');
    await require('./mission-browser.cjs')({ page, context, api, tokens, base, mission, session, screenshots, check });
    await page.locator('#live-weather').selectOption('Fog'); await page.locator('#live-lightning').uncheck();
    await page.locator('#environment-form button[type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#live-environment').textContent.includes('濃霧'));
    check((await api('/sessions/' + session.id)).environment.weather === 'Fog', 'Environment control reaches the active session');
    await api('/sessions/' + session.id + '/commands', 'POST', { commandId: randomUUID(), action: 'SetEnemies', enemies: { count: 9, behavior: 'Patrol', autoAttack: true } });
    await page.locator('#live-count').fill('5');
    await page.locator('#enemies-form button[type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#notice').textContent.includes('場次設定已變更'));
    check((await api('/sessions/' + session.id)).enemies.count === 9, 'Stale editor sequence cannot overwrite another operator command');
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#live-enemies').textContent.startsWith('目標 9 名'));
    check(await page.locator('#live-count').inputValue() === '5', 'Background refresh does not silently replace an operator draft');
    await page.locator('#reload-enemies').click();
    await page.locator('#live-count').fill('5'); await page.locator('#live-behavior').selectOption('Advance'); await page.locator('#live-auto-attack').uncheck();
    await page.locator('#enemies-form button[type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#live-enemies').textContent.startsWith('目標 5 名'));
    const enemySettings = (await api('/sessions/' + session.id)).enemies;
    check(enemySettings.count === 5 && enemySettings.behavior === 'Advance' && !enemySettings.autoAttack, 'Enemy count, behavior and automatic attack controls update the session settings');
    const commands = []; let loseResponse = true, lossAction = 'Pause';
    await page.route('**/api/sessions/*/commands', async route => {
      const body = route.request().postDataJSON();
      if (body.action !== lossAction) return route.continue();
      commands.push(body);
      if (loseResponse) { loseResponse = false; await route.fetch(); await route.abort('failed'); }
      else await route.continue();
    });
    await page.locator('[data-command=Pause]').click();
    await page.locator('#pending-command').waitFor({ state: 'visible' });
    check(await page.locator('[data-command=End]').isDisabled(), 'Unknown command result locks further writes until it is resolved');
    await page.locator('#retry-command').click();
    await page.locator('#pending-command').waitFor({ state: 'hidden' });
    check(commands.length === 2 && JSON.stringify(commands[0]) === JSON.stringify(commands[1]), 'Retry preserves the exact command ID, body and expected sequence after a lost response');
    const history = await api('/sessions/' + session.id + '/events?limit=500');
    check(history.filter(event => event.kind === 'ControlApplied' && event.payload.action === 'Pause').length === 1, 'Lost-response retry applies Pause exactly once in durable history');
    await page.locator('[data-command=Resume]').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
    const playerId = session.players[0].id, shotId = randomUUID(), enemyId = randomUUID();
    const heldStatistics = await require('./statistics-fence.cjs')({ page, api, base, session, playerId, shotId, enemyId, reportId: randomUUID, screenshots, check });
    try {
      check(heldStatistics.partial.origin === '模擬資料' && heldStatistics.partial.rows.some(row => row.join('|') === 'Alpha 01|1|0|0|0|0%|100'),
        'A genuine older Simulation read does not prove the later accepted combat totals have reached the console');
      heldStatistics.release();
      try {
        await page.waitForFunction(() => {
          const row = [...document.querySelectorAll('#statistics tr')].find(row => row.cells[0]?.textContent === 'Alpha 01');
          return document.querySelector('#statistics-origin').textContent === '模擬資料' && row && [...row.cells].map(cell => cell.textContent).join('|') === 'Alpha 01|1|1|20|1|100%|80';
        }, undefined, { polling: 100 });
      } catch (error) {
        const diagnostic = await page.evaluate(() => ({ origin: document.querySelector('#statistics-origin').textContent,
          rows: [...document.querySelectorAll('#statistics tr')].map(row => [...row.cells].map(cell => cell.textContent)),
          phase: document.querySelector('#session-phase').textContent, notice: document.querySelector('#notice').textContent }));
        await fs.writeFile(path.join(screenshots, 'statistics-completion-failure.json'), JSON.stringify(diagnostic, null, 2)); throw error;
      }
      check((await page.locator('#statistics tr').filter({ hasText: 'Alpha 01' }).locator('td').allTextContents()).join('|') === 'Alpha 01|1|1|20|1|100%|80', 'Console shows ammo, kills, damage, hits, accuracy and health from durable simulated events');
    } finally { await heldStatistics.dispose(); }
    check(!(await page.locator('#event-list').innerText()).includes('Invalid Date'), 'History renders the server-recorded event time');
    await page.screenshot({ path: path.join(screenshots, 'operations.png'), fullPage: true });
    const xssName = '<img src=x onerror="window.injected=true">';
    lossAction = 'End'; loseResponse = true; commands.length = 0;
    page.once('dialog', dialog => dialog.accept()); await page.locator('[data-command=End]').click();
    await page.locator('#pending-command').waitFor({ state: 'visible' });
    await delay(2300); // Span the normal 2-second refresh interval to expose lost-End selection bugs.
    check(await page.locator('#session-panel').isVisible() && await page.locator('#pending-command').isVisible() && await page.locator('#refresh').isDisabled() && (await api('/sessions/' + session.id)).state === 'Ended', 'Lost End response retains its retry controls even after the server archives the session');
    await page.locator('#retry-command').click();
    await page.locator('#pending-command').waitFor({ state: 'hidden' });
    check(commands.length === 2 && JSON.stringify(commands[0]) === JSON.stringify(commands[1]) && (await api('/sessions/' + session.id + '/events?limit=500')).filter(event => event.kind === 'ControlApplied' && event.payload.action === 'End').length === 1, 'End can be confirmed by retry without ending twice or stranding the workspace');
    await page.locator('#launch-mode').selectOption('Linked');
    check(await page.locator('#launch-preview-rooms').innerText() === '房間 1、房間 2、房間 3、房間 4、房間 5'
      && await page.locator('#launch-room').isDisabled(), 'Linked preparation previews the exact five target rooms');
    await page.locator('#create-session-form button').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '準備中' && document.querySelector('#session-meta').textContent.startsWith('五房全連線'));
    const linked = (await api('/sessions'))[0];
    check(linked.mode === 'Linked' && linked.roomIds.length === 5 && (await api('/rooms')).every(room => room.sessionId === linked.id), 'Master can prepare one linked session reserving all five rooms from the console');
    check((await page.locator('#launch-preview-rooms').innerText()).match(/使用中/g)?.length === 5
      && await page.locator('#create-session-form button').isDisabled(), 'Occupied targets remain visible and block another launch');
    await api('/sessions/' + linked.id + '/players', 'POST', { playerId: randomUUID(), name: xssName, roomId: 2, headset: 'Quest3' });
    const roomContext = await browser.newContext({ viewport: { width: 390, height: 844 } }), roomPage = await roomContext.newPage(); captureErrors(roomPage);
    await roomPage.goto(base + '/console/'); await roomPage.locator('#login-key').fill(tokens.Room1); await roomPage.locator('#login-form button').click();
    await roomPage.waitForFunction(() => document.querySelector('#identity').textContent === '房間 1 控制台' && !document.querySelector('#session-panel').hidden);
    check(await roomPage.locator('.room-card').count() === 1 && await roomPage.locator('[data-command=End]').isDisabled() && await roomPage.locator('#player-room option').count() === 1, 'Room controller sees its own room, cannot command a linked session and can select only its player room');
    check(await roomPage.locator('#roster img').count() === 0 && !(await roomPage.evaluate(() => window.injected)), 'Untrusted player names render as text rather than executable markup');
    check(await roomPage.locator('#roster button').first().isDisabled(), 'Room controller cannot remove or issue tickets to another room player');
    check(await roomPage.locator('#download-room-tickets').isDisabled() && await roomPage.locator('#ticket-room option').count() === 1,
      'A room controller cannot select a populated foreign room for bundle download');
    await roomPage.locator('#player-name').fill('Room 1 Alpha'); await roomPage.locator('#join-form button').click();
    await roomPage.waitForFunction(() => document.querySelectorAll('#roster tr').length === 2);
    check((await api('/sessions/' + linked.id)).players.some(player => player.name === 'Room 1 Alpha' && player.roomId === 1), 'Room controller can add its own player to the linked roster');
    check(await roomPage.locator('#ticket-room option').allTextContents().then(options => JSON.stringify(options) === JSON.stringify(['請選擇房間', '房間 1（1 人）']))
      && await roomPage.locator('#download-room-tickets').isDisabled(), 'Room bundle requires an explicit authorized room selection');
    await roomPage.locator('#ticket-room').selectOption('1');
    await roomPage.locator('#game-address').fill('192.168.1.100');
    const [bundleDownload] = await Promise.all([roomPage.waitForEvent('download'), roomPage.locator('#download-room-tickets').click()]);
    const zipPath = path.join(directory, 'room-connections.zip'); await bundleDownload.saveAs(zipPath);
    check(bundleDownload.suggestedFilename() === 'room-01-connections.zip' && (await fs.readFile(zipPath)).subarray(0, 4).equals(Buffer.from([0x50, 0x4b, 0x03, 0x04])),
      'Room controller downloads an actual ZIP from its own room');
    await roomPage.locator('#tab-missions').click();
    check(await roomPage.locator('#draft-name').isDisabled() && await roomPage.locator('#mission-form button[type=submit]').isDisabled() && await roomPage.locator('#save-revision').isDisabled(), 'Room controller mission editing and revision saving remain read-only');
    check(await roomPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Console layout fits a 390-pixel viewport without page overflow');
    await roomPage.locator('#tab-operations').click(); await roomPage.screenshot({ path: path.join(screenshots, 'room-controller.png'), fullPage: true });
    await page.locator('#include-ended').check(); await page.locator('#refresh').click();
    await page.locator('#session-select').selectOption(session.id);
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已結束');
    check(await page.locator('[data-command=Begin]').isDisabled() && (await page.locator('#statistics').innerText()).includes('80'), 'Archived session remains viewable with statistics and no lifecycle writes');
    const streamId = randomUUID();
    await api('/sessions/' + linked.id + '/combat-stream', 'POST', { streamId, origin: 'Simulation' }, 'GameServer');
    await page.locator('#session-select').selectOption(linked.id);
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '準備中');
    await page.locator('#include-ended').uncheck(); await page.locator('[data-command=Begin]').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
    const observed = await api('/sessions/' + linked.id);
    const streamedPlayer = observed.players.find(player => player.roomId === 1);
    page.once('dialog', dialog => dialog.accept()); await page.locator('[data-command=End]').click();
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已結束' && document.querySelector('#telemetry-status').textContent.includes('尚未確認完整'));
    check(await page.locator('#session-panel').isVisible() && await page.locator('#include-ended').isChecked(), 'Ending a bound stream retains its archived session and visibly pending final statistics');
    check(await page.locator('#export-report').isDisabled() && await page.locator('#export-player-report').isDisabled(),
      'Unsealed ended session cannot offer a full or personal final report download');
    await page.locator('#report-room').selectOption('2');
    check(await page.locator('#statistics tr').count() === 1 && (await page.locator('#statistics').innerText()).includes(xssName)
      && await page.locator('#export-report').isDisabled(), 'Room statistics can be inspected before seal without enabling final CSV');
    await page.locator('#report-room').selectOption('');
    await page.screenshot({ path: path.join(screenshots, 'telemetry-pending.png'), fullPage: true });
    await api('/sessions/' + linked.id + '/combat-stream/batch', 'POST', [{ streamId, streamSequence: 1, observedSequence: observed.sequence,
      report: { reportId: randomUUID(), kind: 'ShotFired', origin: 'Simulation', playerId: streamedPlayer.id, shotId: randomUUID() } }], 'GameServer');
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#statistics-origin').textContent === '模擬資料');
    check((await page.locator('#statistics tr').filter({ hasText: streamedPlayer.name }).locator('td').allTextContents())[1] === '1' && (await page.locator('#telemetry-status').innerText()).includes('尚未確認完整'), 'Late confirmed stream report updates archived metrics without claiming the tail is complete');
    await api('/sessions/' + linked.id + '/combat-stream/seal', 'POST', { streamId, finalSequence: 1 }, 'GameServer');
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#telemetry-status').textContent.includes('全部確認並封存'));
    check((await api('/sessions/' + linked.id + '/statistics')).pendingTelemetry === false, 'Final-report UI changes only after the server accepts the exact seal boundary');
    await page.waitForFunction(() => !document.querySelector('#export-report').disabled);
    await require('./report-browser.cjs')({ context, tokens, base, api, session, linked, screenshots, check });
    await page.locator('#tab-replay').click(); await page.locator('#replay-example').click();
    await page.waitForFunction(() => !document.querySelector('#replay-player').hidden && Number(document.querySelector('#replay-canvas').dataset.triangles) > 0);
    check((await page.locator('#replay-message').innerText()).includes('統計核對一致') && (await page.locator('#replay-time').innerText()).includes('10.40'), 'Real WebGL viewer loads the recorded geometric simulation and validates its final statistics');
    check((await page.locator('#replay-statistics tr td').allTextContents()).join('|') === 'Quest3-Simulation|0|0|0|0|0%|100', 'Replay starts from the initial statistics instead of displaying the final report at every time');
    await page.locator('#replay-next').click(); await page.locator('#replay-next').click();
    check(await page.locator('#replay-canvas').getAttribute('data-trace-count') === '1' && (await page.locator('#replay-statistics tr td').allTextContents())[1] === '1', 'Frame stepping displays the recorded first shot ray and only its accepted ammunition event');
    const canvas = page.locator('#replay-canvas'); await canvas.scrollIntoViewIfNeeded();
    const initialCamera = await canvas.getAttribute('data-camera'), bounds = await canvas.boundingBox();
    await page.mouse.move(bounds.x + bounds.width * .5, bounds.y + bounds.height * .5); await page.mouse.down(); await page.mouse.move(bounds.x + bounds.width * .6, bounds.y + bounds.height * .55, { steps: 5 }); await page.mouse.up();
    check(await canvas.getAttribute('data-camera') !== initialCamera, 'Operator can orbit the actual 3D scene with a pointer');
    const orbitCamera = await canvas.getAttribute('data-camera'); await canvas.press('ArrowRight');
    check(await canvas.getAttribute('data-camera') !== orbitCamera && await page.locator('#replay-camera').inputValue() === 'free', 'Keyboard pan changes camera position and identifies the free camera mode');
    await page.locator('#replay-camera').selectOption('top');
    check(await canvas.getAttribute('data-camera') !== initialCamera, 'God-view camera preset changes the rendered perspective');
    await canvas.scrollIntoViewIfNeeded();
    const topBounds = await canvas.boundingBox(), topCamera = await canvas.getAttribute('data-camera'), locatedFrame = await canvas.getAttribute('data-frame');
    await page.mouse.dblclick(topBounds.x + topBounds.width * .55, topBounds.y + topBounds.height * .5);
    check(await canvas.getAttribute('data-camera') !== topCamera && await page.locator('#replay-camera').inputValue() === 'free'
      && await canvas.getAttribute('data-frame') === locatedFrame, 'Double-clicking a replay room relocates the camera without seeking or changing recorded combat');
    await page.locator('#replay-camera').selectOption('follow'); const followStart = (await canvas.getAttribute('data-camera')).split(',').map(Number);
    await page.locator('#replay-timeline').focus(); await page.locator('#replay-timeline').press('End');
    const followEnd = (await canvas.getAttribute('data-camera')).split(',').map(Number);
    check(followEnd[0] - followStart[0] > 1.5, 'Follow camera moves with the recorded player position');
    check((await page.locator('#replay-statistics tr td').allTextContents()).join('|') === 'Quest3-Simulation|3|1|20|1|66.67%|80' && await page.locator('#replay-phase').innerText() === '已結束', 'Seeking to the end reproduces the exact mission result');
    await page.locator('#replay-speed').selectOption('4'); await page.locator('#replay-play').click();
    await page.waitForFunction(() => Number(document.querySelector('#replay-canvas').dataset.frame) > 30 && document.querySelector('#replay-play').textContent === '暫停');
    await page.locator('#replay-play').click(); const pausedFrame = await canvas.getAttribute('data-frame'); await delay(350);
    check(await canvas.getAttribute('data-frame') === pausedFrame, 'Pause holds playback while speed controls affect the advancing timeline');
    const replaySample = JSON.parse(await fs.readFile(path.join(root, 'src/VrCommand.Api/wwwroot/console/examples/simulation.json'), 'utf8'));
    const malformed = structuredClone(replaySample); malformed.frames[0].players[0].health = 80;
    await page.locator('#replay-file').setInputFiles({ name: 'inconsistent.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(malformed)) });
    await page.locator('#replay-message.replay-error').waitFor();
    check(await page.locator('#replay-player').isVisible() && await canvas.getAttribute('data-frame') === pausedFrame, 'Invalid snapshot/event health is rejected while retaining the previous valid recording');
    const literal = structuredClone(replaySample); literal.mission.definition.name = '<img src=x onerror="window.replayInjected=true">';
    await page.locator('#replay-file').setInputFiles({ name: 'literal-name.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(literal)) });
    await page.waitForFunction(() => document.querySelector('#replay-name').textContent.startsWith('<img'));
    check(await page.locator('#replay-name img').count() === 0 && !(await page.evaluate(() => window.replayInjected)), 'Imported recording titles remain literal text rather than executable markup');
    await page.locator('#replay-example').click(); await page.waitForFunction(() => !document.querySelector('#replay-name').textContent.startsWith('<img'));
    await page.locator('#replay-camera').selectOption('overview');
    const combatFrame = replaySample.frames.findIndex(frame => frame.throughSequence === 5);
    await page.locator('#replay-timeline').evaluate((input, frame) => { input.value = frame; input.dispatchEvent(new Event('input', { bubbles: true })); }, combatFrame);
    await page.screenshot({ path: path.join(screenshots, 'replay-combat.png'), fullPage: true });
    check(await canvas.getAttribute('data-trace-count') === '3', 'Combat review shows the distinct player and enemy rays recorded around the selected tick');
    await roomPage.locator('#tab-replay').click(); await roomPage.locator('#replay-example').click();
    await roomPage.waitForFunction(() => Number(document.querySelector('#replay-canvas').dataset.triangles) > 0);
    check(await roomPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1 && document.querySelector('#replay-canvas').clientWidth > 200), 'Replay canvas and controls remain usable at a 390-pixel viewport');
    await roomPage.screenshot({ path: path.join(screenshots, 'replay-mobile.png'), fullPage: true });
    // This mobile room viewer has finished all its assertions. Release its
    // renderer before the streamed-world tests create a second observer page.
    await roomContext.close();
    await page.locator('#tab-operations').click();
    check(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && !document.cookie), 'Operator credentials are not persisted in browser storage or cookies');
    await require('./world-browser.cjs')({ page, context, api, tokens, directory, root, base, screenshots, check });
    await require('./environment-browser.cjs')({ page, api, tokens, directory, root, base, screenshots, check });
    await require('./layout-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
    await require('./placement-history-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
    await require('./rifle-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./combatants-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./player-fire-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./combat-audio-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./player-body-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./combat-effects-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./armed-combatants-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./weapon-actions-browser.cjs')({ context, tokens, base, root, screenshots, check });
    await require('./clock-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
    await require('./readiness-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
    await require('./connection-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
    await require('./closure-browser.cjs')({ context, api, tokens, base, mission, screenshots, check });
    await require('./field-evidence-browser.cjs')({ context, api, tokens, directory, root, base, screenshots, check });
    await require('./mission-read-recovery.cjs')({ context, api, tokens, base, screenshots, check });
    await page.bringToFront();
    let releaseReplay, requestedReplay;
    const replayGate = new Promise(resolve => { releaseReplay = resolve; }), replayRequested = new Promise(resolve => { requestedReplay = resolve; });
    await page.route('**/console/examples/simulation.json', async route => { requestedReplay(); await replayGate; await route.continue(); });
    await page.locator('#tab-replay').click(); await page.locator('#replay-example').click(); await replayRequested;
    await page.locator('#logout').click();
    const staleReplayResponse = page.waitForResponse('**/console/examples/simulation.json'); releaseReplay(); await staleReplayResponse;
    await page.waitForFunction(() => !document.querySelector('#replay-example').disabled);
    check(await page.locator('#replay-player').isHidden() && await page.locator('#replay-name').innerText() === '', 'A replay response arriving after logout cannot restore the previous recording');
    check(await page.locator('#login-panel').isVisible() && await page.locator('#workspace').isHidden(), 'Logout clears access to the console workspace');
    await page.reload();
    check(await page.locator('#login-panel').isVisible(), 'Reload requires authentication again');
    await require('./mr-start-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    await require('./tracked-vr-start-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    await require('./mr-alignment-pins-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./mr-deployment-browser.cjs')({ context, api, tokens, base, directory, screenshots, check, captureErrors });
    await require('./vr-connection-check-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    await require('./independent-set-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./server-plan-browser.cjs').checkServerPlan({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./venue-launch-review-browser.cjs').checkVenueLaunchReview({ context, api, tokens, base, screenshots, check, captureErrors, instanceId });
    await require('./mr-venue-bundle-browser.cjs')({ context, api, tokens, base, root, directory, screenshots, check, captureErrors });
    await require('./vr-venue-tickets-browser.cjs')({ context, api, tokens, base, root, directory, screenshots, check, captureErrors });
    await require('./room-clock-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    const roomEnemyEditor = await context.newPage();
    captureErrors(roomEnemyEditor);
    try { await require('./room-enemy-edit-browser.cjs')({ page: roomEnemyEditor, api, tokens, base, check }); }
    finally { await roomEnemyEditor.close(); }
    const settingEditor = await context.newPage();
    captureErrors(settingEditor);
    try { await require('./setting-drafts-browser.cjs')({ page: settingEditor, api, tokens, base, check }); }
    finally { await settingEditor.close(); }
    await require('./venue-phase-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    await require('./venue-scores-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./vr-participation-pause-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    await require('./full-tracking-begin-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    await require('./mission-template-browser.cjs')({ context, api, tokens, directory, root, base, screenshots, check, captureErrors, availablePort, dotnet });
    await require('./ticket-download-fence.cjs').checkTicketDownloadFence({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./seat-ticket-scope-browser.cjs')({ context, api, tokens, base, check, captureErrors });
    await require('./saved-layout-identity-browser.cjs')({ context, api, tokens, base, check, captureErrors });
    await require('./venue-mr-alignment-browser.cjs')({ context, api, tokens, base, check, captureErrors });
    await require('./archived-independent-plan-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./venue-mission-file-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./session-reprepare-browser.cjs')({ context, api, tokens, base, screenshots, check, captureErrors });
    await require('./venue-time-replay-browser.cjs')({ context, api, tokens, base, root, screenshots, check, captureErrors });
    check(browserErrors.length === 0, 'Browser has no uncaught script errors or CSP violations');
    await fs.writeFile(path.join(screenshots, 'checks.json'), JSON.stringify({ checkedAtUtc: new Date().toISOString(), checks, browser: await browser.version(), playwright: require('playwright/package.json').version, result: 'passed', scope: 'isolated real API and browser console; no Unity or headset test' }, null, 2));
    console.log(`PASS: ${checks} real-browser checks. Screenshots: ${screenshots}`);
  } catch (error) {
    if (diagnosticPage && !diagnosticPage.isClosed()) await diagnosticPage.screenshot({ path: path.join(screenshots, 'failure.png'), fullPage: true }).catch(() => {});
    throw error;
  } finally {
    if (browser) await browser.close();
    const stopped = new Promise(resolve => processApi.once('exit', resolve));
    if (!apiTerminal()) { processApi.kill(); await stopped; }
    // The unique directory was checked against the OS temp root before any recursive cleanup.
    await fs.rm(directory, { recursive: true, force: true });
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
