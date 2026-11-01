// Optional companion for check-desktop-active.py. Only console forms issue writes.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const guid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;

function validateConfig(file, config) {
  const directory = path.dirname(path.resolve(file));
  assert.equal(path.basename(file), 'active-ui-config.json');
  const normalize = value => process.platform === 'win32' ? value.toLowerCase() : value;
  assert.equal(normalize(path.dirname(directory)), normalize(path.join(root, 'artifacts/desktop-active')));
  assert.match(path.basename(directory), /^\d{8}-\d{6}-[a-f0-9]{8}$/);
  assert.equal(config.source, 'Simulation'); assert.equal(config.headsets, 0);
  assert.match(config.sessionId, guid);
  const url = new URL(config.baseUrl);
  assert.equal(url.protocol, 'http:'); assert.equal(url.hostname, '127.0.0.1');
  assert.ok(Number(url.port) >= 1024 && Number(url.port) <= 65535 && url.port !== '5080');
  assert.equal(url.username + url.password + url.search + url.hash, ''); assert.equal(url.pathname, '/');
  assert.equal(config.baseUrl, url.origin);
  return directory;
}
function validateRequest(request, sessionId, next) {
  assert.equal(request.request, next); assert.ok(Number.isInteger(next) && next >= 1 && next <= 3);
  assert.equal(request.sessionId, sessionId); assert.equal(request.environment.mode, 'VR');
  assert.ok(['Clear', 'Rain', 'Fog', 'Storm'].includes(request.environment.weather));
  assert.ok(['Day', 'Night'].includes(request.environment.timeOfDay));
  assert.equal(typeof request.environment.lightning, 'boolean');
  assert.ok(['Hold', 'Patrol', 'Advance'].includes(request.behavior));
  assert.deepEqual(Object.keys(request.environment).sort(), ['lightning', 'mode', 'timeOfDay', 'weather']);
}
async function write(directory, name, value) {
  const destination = path.join(directory, name), temporary = destination + '.' + randomUUID() + '.tmp';
  await fs.writeFile(temporary, JSON.stringify(value, null, 2), { flag: 'wx' }); await fs.rename(temporary, destination);
}
async function main(file) {
  const config = JSON.parse(await fs.readFile(file, 'utf8')), directory = validateConfig(file, config);
  const tokens = JSON.parse(await fs.readFile(path.join(directory, 'keys.json'), 'utf8')).OperatorKeys;
  const redact = text => Object.values(tokens).reduce((value, key) => value.replaceAll(key, '[redacted]'), String(text));
  const { chromium } = require('playwright');
  let browser, page, stopping = false, reason, failure, count = 0, timer;
  const attempts = [], pageErrors = [], start = performance.now(), captureStartedAtUtc = new Date().toISOString();
  async function read(name) { try { return JSON.parse(await fs.readFile(path.join(directory, name), 'utf8')); } catch (error) { if (error.code === 'ENOENT') return null; throw error; } }
  async function stop(why) { if (stopping) return; stopping = true; reason = why; if (browser) await browser.close(); }
  async function api(route) {
    const response = await fetch(config.baseUrl + '/api' + route, { headers: { Authorization: 'Bearer ' + tokens.Master }, signal: AbortSignal.timeout(5000) });
    assert.equal(response.status, 200); return response.json();
  }
  const wait = (predicate, arg) => page.waitForFunction(predicate, arg, { polling: 100, timeout: 5000 });
  async function refresh() {
    await page.locator('#refresh').click(); const state = await api('/sessions/' + config.sessionId);
    assert.equal(state.id, config.sessionId);
    await wait(sequence => Number(document.querySelector('#session-meta').textContent.match(/序號 (\d+)/)?.[1]) >= sequence, state.sequence);
  }
  async function submit(request, action, fill, selector) {
    for (let intent = 1; intent <= 3; intent++) {
      const startedAtUtc = new Date().toISOString(), startedSeconds = (performance.now() - start) / 1000;
      await refresh(); await fill();
      const [response] = await Promise.all([
        page.waitForResponse(r => r.url() === config.baseUrl + '/api/sessions/' + config.sessionId + '/commands' && r.request().method() === 'POST', { timeout: 5000 }),
        page.locator(selector).click()
      ]);
      const body = response.request().postDataJSON(), receipt = await response.json();
      attempts.push({ request: request.request, action, intent, status: response.status(), body, receipt,
        startedAtUtc, startedSeconds, completedAtUtc: new Date().toISOString(), completedSeconds: (performance.now() - start) / 1000 });
      await write(directory, 'active-ui-attempts.json', attempts); // Preserve accepted and conflict responses immediately.
      assert.equal(body.action, action);
      if (response.status() === 200) {
        assert.equal(receipt.commandId, body.commandId); assert.equal(receipt.session.id, config.sessionId); assert.equal(receipt.duplicate, false);
        return receipt;
      }
      assert.equal(response.status(), 409, 'Unknown result must fail, not issue another intent');
      // A 409 was rejected. Refresh and explicitly submit a new UI intent;
      // never replay a successful or unknown command as a new command.
    }
    throw Error('Three UI intents conflicted: ' + action);
  }
  try {
    timer = setInterval(() => { (async () => {
      if (await read('active-ui-finish.json')) await stop('Requested');
      else if (performance.now() - start >= 180000) await stop('Deadline');
    })().catch(error => { failure = redact(error.stack); stop('Failure').catch(() => {}); }); }, 200);
    browser = await chromium.launch({ headless: true, timeout: 15000 });
    if (stopping) { await browser.close(); throw Error('Stopped while launching browser'); }
    const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
    page = await context.newPage(); page.setDefaultTimeout(5000); page.on('pageerror', error => pageErrors.push(redact(error.message)));
    await page.bringToFront(); await page.goto(config.baseUrl + '/console/');
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select option[value="' + config.sessionId + '"]').waitFor({ state: 'attached' });
    await page.locator('#session-select').selectOption(config.sessionId);
    await wait(() => !document.querySelector('#session-panel').hidden && document.querySelector('#identity').textContent === '全館主控');
    const world = await api('/sessions/' + config.sessionId + '/world');
    assert.equal(world.header.sessionId, config.sessionId); assert.equal(world.header.origin, 'Simulation'); assert.deepEqual(world.header.roomIds, [1, 2, 3, 4, 5]);
    await write(directory, 'active-ui-ready.json', { sessionId: config.sessionId, source: 'Real Chromium console forms', maximumSeconds: 180 });
    while (!stopping) {
      const request = await read('active-ui-request.json');
      if (!request || request.request === count) { await sleep(100); continue; }
      validateRequest(request, config.sessionId, count + 1);
      const environment = await submit(request, 'SetEnvironment', async () => {
        await page.locator('#reload-environment').click();
        await page.locator('#live-weather').selectOption(request.environment.weather); await page.locator('#live-time').selectOption(request.environment.timeOfDay);
        await page.locator('#live-lightning').setChecked(request.environment.lightning);
      }, '#environment-form button[type=submit]');
      const enemies = await submit(request, 'SetEnemies', async () => {
        await page.locator('#reload-enemies').click(); await page.locator('#live-count').fill('5');
        await page.locator('#live-behavior').selectOption(request.behavior); await page.locator('#live-auto-attack').uncheck();
      }, '#enemies-form button[type=submit]');
      assert.equal(pageErrors.length, 0, pageErrors.join('\n'));
      const relevant = attempts.filter(a => a.request === request.request);
      await write(directory, 'active-ui-response-' + request.request + '.json', { request: request.request, sessionId: config.sessionId, attempts: relevant, receipts: [environment, enemies] });
      count++;
    }
  } catch (error) {
    if (!stopping || reason !== 'Requested') {
      failure = redact(error.stack); reason = reason || 'Failure';
      if (page && !page.isClosed()) await page.screenshot({ path: path.join(directory, 'active-ui-failure.png'), timeout: 3000 }).catch(() => {});
    }
  } finally {
    clearInterval(timer); if (browser) await browser.close();
    const cleanShutdown = !browser || !browser.isConnected();
    await write(directory, 'active-ui-report.json', { complete: reason === 'Requested' && !failure, reason: reason || 'Failure', cleanShutdown,
      requests: count, attempts: attempts.length, pageErrors, error: failure || null, maximumSeconds: 180, captureStartedAtUtc, elapsedSeconds: (performance.now() - start) / 1000 });
    if (failure || reason !== 'Requested' || !cleanShutdown) { console.error(failure || reason); process.exitCode = 1; }
  }
}
module.exports = { validateConfig, validateRequest };
if (require.main === module) main(process.argv[2]).catch(error => { console.error('Active console startup failed: ' + error.name); process.exitCode = 1; });
