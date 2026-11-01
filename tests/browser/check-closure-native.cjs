// Real isolated native session, observed through the shipped console. No Unity input or UI fixture routes.
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const options = new Map();
for (let i = 2; i < process.argv.length; i += 2) options.set(process.argv[i], process.argv[i + 1]);
const read = file => fs.readFile(file, 'utf8').then(JSON.parse);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  assert.equal(options.size, 3); const config = await read(options.get('--descriptor')), out = path.resolve(options.get('--output')), stop = path.resolve(options.get('--stop-file'));
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/); assert.equal(typeof config.masterKey, 'string');
  await fs.mkdir(out); let server, browser, page, success = false, failure, report, lastWorld;
  const save = (name, value) => fs.writeFile(path.join(out, name), JSON.stringify(value, null, 2), { flag: 'wx' });
  let cancelled; const cancellation = new Promise((resolve, reject) => { cancelled = () => reject(new Error('Observer cancelled')); });
  process.on('SIGTERM', cancelled); process.on('SIGINT', cancelled);
  const timer = setInterval(() => fs.stat(stop).then(cancelled).catch(() => {}), 250);
  const budget = setTimeout(cancelled, 90000);
  try {
    await Promise.race([(async () => {
      server = await chromium.launchServer({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
      browser = await chromium.connect(server.wsEndpoint()); const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } }); page = await context.newPage();
      const errors = []; page.on('pageerror', error => errors.push(error.name));
      page.on('response', response => { if (response.url() === config.base + '/api/sessions/' + config.sessionId + '/world' && response.status() === 200)
        response.json().then(value => { lastWorld = value; }).catch(() => {}); });
      await page.goto(config.base + '/console/'); await page.locator('#login-key').fill(config.masterKey); await page.locator('#login-form button').click();
      await page.locator('#session-select').selectOption(config.sessionId); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
      assert.equal(await page.locator('#closure-status.closure-complete').count(), 0);
      await page.screenshot({ path: path.join(out, 'running.png'), fullPage: true });
      await save('ready.json', { ready: true, selectedSessionId: await page.locator('#session-select').inputValue(), browserPid: server.process().pid, scope: 'Real native Running session visible in shipped console; no game input, fixture routes or delivery claim.' });
      for (;;) { try { await fs.stat(config.endRequestFile); break; } catch { await sleep(100); } }
      const endResponse = page.waitForResponse(response => response.url() === config.base + '/api/sessions/' + config.sessionId + '/commands' && response.request().method() === 'POST', { timeout: 30000 });
      page.once('dialog', dialog => dialog.accept()); await page.locator('[data-command=End]').click();
      const response = await endResponse; assert.equal(response.status(), 200); const receipt = await response.json(), intent = response.request().postDataJSON();
      assert.equal(receipt.duplicate, false); assert.equal(receipt.session.id, config.sessionId); assert.equal(receipt.session.state, 'Ended'); assert.equal(intent.action, 'End');
      await save('end-receipt.json', { sessionId: receipt.session.id, sequence: receipt.session.sequence, duplicate: receipt.duplicate, commandId: intent.commandId, expectedSequence: intent.expectedSequence, method: 'POST', status: response.status() });
      await page.locator('#closure-status.closure-complete').waitFor({ timeout: 60000 });
      assert.equal(await page.locator('#session-select').inputValue(), config.sessionId); assert.equal(await page.locator('#session-phase').innerText(), '已結束');
      assert.equal(await page.locator('#include-ended').isChecked(), true);
      assert.equal(lastWorld?.header.sessionId, config.sessionId); assert.equal(lastWorld?.header.streamId, config.streamId); assert.equal(lastWorld?.complete, true);
      assert.equal(await page.locator('#closure-combat').innerText(), '戰鬥統計：已封存'); assert.equal(await page.locator('#closure-world').innerText(), '世界回放：已封存');
      const summary = await page.locator('#closure-summary').innerText(); assert.match(summary, /不確認送達/); assert.equal(await page.locator('#export-report').isEnabled(), true); assert.deepEqual(errors, []);
      await page.screenshot({ path: path.join(out, 'archived.png'), fullPage: true });
      report = { complete: true, sessionId: config.sessionId, streamId: config.streamId, acceptedWorldSequence: lastWorld.acceptedSequence, origin: lastWorld.header.origin, roomIds: lastWorld.header.roomIds, summary, uncaughtErrors: errors, source: 'Actual console GET world response; no route fulfillment or replacement', scope: 'Native Simulation source and archive UI only. Client delivery / original journals / process cleanup separately verified by owning fixture.' }; success = true;
    })(), cancellation]);
  } catch (error) {
    failure = error.name;
    if (page && !page.isClosed()) {
      await save('failure-state.json', await page.evaluate(() => ({ selected: document.querySelector('#session-select')?.value, includeEnded: document.querySelector('#include-ended')?.checked,
        phase: document.querySelector('#session-phase')?.textContent?.slice(0, 100), summary: document.querySelector('#closure-summary')?.textContent?.slice(0, 800), combat: document.querySelector('#closure-combat')?.textContent?.slice(0, 100), world: document.querySelector('#closure-world')?.textContent?.slice(0, 100),
        notice: document.querySelector('#notice')?.textContent?.slice(0, 500), workspaceHidden: document.querySelector('#workspace')?.hidden }))).catch(() => {});
      await page.screenshot({ path: path.join(out, 'failure.png'), fullPage: true, timeout: 5000 }).catch(() => {});
    }
  }
  finally {
    clearInterval(timer); clearTimeout(budget);
    if (browser) await browser.close(); if (server) await server.close();
    const process = server?.process(); const browserClosed = !process || process.exitCode !== null || process.signalCode !== null;
    await save('checks.json', { ...report, complete: success && browserClosed, browserClosed, browserPid: process?.pid, browserExitCode: process?.exitCode, browserSignal: process?.signalCode, errorType: failure });
    if (!success || !browserClosed) throw new Error('Native archive UI observation incomplete');
  }
}
main().catch(error => { console.error(error.name + ': archive UI observation failed'); process.exitCode = 1; });
