// Real isolated native session, observed through the shipped console. No Unity input or UI fixture routes.
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const options = new Map();
for (let i = 2; i < process.argv.length; i += 2) options.set(process.argv[i], process.argv[i + 1]);
const read = file => fs.readFile(file, 'utf8').then(JSON.parse);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function readyRooms() {
  const cells = [...document.querySelectorAll('[data-room-readiness]')];
  return cells.length === 5 && cells.every(cell => cell.textContent === '5 / 5 姿態有效 · 合成 5 · 追蹤 0')
    ? cells.map(cell => Number(cell.dataset.roomReadiness)) : null;
}
function trackedRoomParticipation({ roomId, seat, available }) {
  const cells = [...document.querySelectorAll('[data-room-readiness]')];
  const cell = cells.find(item => item.dataset.roomReadiness === String(roomId));
  const alerts = cells.filter(item => item.classList.contains('tracking-attention'));
  const text = available ? '2 / 2 姿態有效 · 合成 1 · 追蹤 1'
    : `1 / 2 姿態有效 · 合成 1 · 追蹤 0 · 姿態待確認席位 ${seat}`;
  if (document.querySelectorAll('#rooms .room-card').length !== 5 || cells.length !== 1
      || cell?.dataset.sourceState !== 'Fresh' || cell.textContent !== text) return null;
  if (available ? alerts.length !== 0 : alerts.length !== 1 || alerts[0] !== cell) return null;
  return { roomId, seat, text };
}
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
      server = await chromium.launchServer({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
        args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
      browser = await chromium.connect(server.wsEndpoint()); const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } }); page = await context.newPage();
      const errors = []; page.on('pageerror', error => errors.push(error.name));
      const worldUrl = config.base + '/api/sessions/' + config.sessionId + '/world';
      page.on('response', response => { if ([worldUrl, worldUrl + '?includeDebriefReceipts=true'].includes(response.url()) && response.status() === 200)
        response.json().then(value => { lastWorld = value; }).catch(() => {}); });
      await page.goto(config.base + '/console/'); await page.locator('#login-key').fill(config.masterKey); await page.locator('#login-form button').click();
      await page.locator('#session-select').selectOption(config.sessionId); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
      assert.equal(await page.locator('#closure-status.closure-complete').count(), 0);
      let roomReadiness;
      if (config.roomReadiness) {
        const rooms = await page.waitForFunction(readyRooms, null, { polling: 100 });
        roomReadiness = await rooms.jsonValue();
        assert.deepEqual(roomReadiness, [1, 2, 3, 4, 5]);
      }
      if (config.trackedParticipation) {
        assert.ok(!config.roomReadiness && !config.roomParticipation);
        await page.waitForFunction(trackedRoomParticipation,
          { ...config.trackedParticipation, available: true }, { polling: 100 });
      }
      await page.screenshot({ path: path.join(out, 'running.png'), fullPage: true });
      await save('ready.json', { ready: true, selectedSessionId: await page.locator('#session-select').inputValue(), browserPid: server.process().pid, roomReadiness, scope: 'Real native Running session visible in shipped console; no game input, fixture routes or delivery claim.' });
      if (config.roomParticipation) {
        const alert = await page.waitForFunction(() => {
          const cells = [...document.querySelectorAll('[data-room-readiness]')];
          const alerts = cells.filter(cell => cell.classList.contains('tracking-attention'));
          const cell = alerts[0];
          return cells.length === 5 && alerts.length === 1 && cell.dataset.roomReadiness === '4' && cell.dataset.sourceState === 'Fresh'
            && cell.textContent === '4 / 5 姿態有效 · 合成 4 · 追蹤 0 · 姿態待確認席位 3'
            ? { roomId: 4, seat: 3, text: cell.textContent } : null;
        }, null, { polling: 100 });
        await save('participation-alert.json', await alert.jsonValue());
        await page.screenshot({ path: path.join(out, 'participation-alert.png'), fullPage: true });
        const restored = await page.waitForFunction(readyRooms, null, { polling: 100, timeout: 60000 });
        await save('participation-recovered.json', { rooms: await restored.jsonValue() });
      }
      if (config.trackedParticipation) {
        const target = config.trackedParticipation;
        const alert = await page.waitForFunction(trackedRoomParticipation, { ...target, available: false }, { polling: 100 });
        await page.screenshot({ path: path.join(out, 'participation-alert.png'), fullPage: true });
        await save('participation-alert.json', await alert.jsonValue());
        const recovered = await page.waitForFunction(trackedRoomParticipation, { ...target, available: true }, { polling: 100 });
        await page.screenshot({ path: path.join(out, 'participation-recovered.png'), fullPage: true });
        await save('participation-recovered.json', await recovered.jsonValue());
      }
      if (config.weaponAmmunition) {
        const observed = await page.waitForFunction(expected => {
          const rows = [...document.querySelectorAll('#statistics tr')].map(row => ({
            name: row.cells[0]?.textContent, ammoUsed: row.cells[1]?.textContent
          }));
          return document.querySelector('#session-phase')?.textContent === '執行中'
            && rows.length === expected.length
            && expected.every(player => rows.some(row => row.name === player.name && row.ammoUsed === String(player.ammoUsed)))
            ? rows : null;
        }, config.weaponAmmunition, { polling: 100 });
        await page.screenshot({ path: path.join(out, 'weapon-ammunition.png'), fullPage: true });
        await save('weapon-ammunition.json', await observed.jsonValue());
      }
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
      const summary = await page.locator('#closure-summary').innerText();
      if (!lastWorld?.debriefReceipts) assert.match(summary, /不確認送達/);
      else assert.match(summary, /遊戲伺服器會依原流程完成收尾/);
      assert.equal(await page.locator('#export-report').isEnabled(), true); assert.deepEqual(errors, []);
      if (config.debriefReceiptCount) {
        const count = page.locator('#debrief-receipt-count').filter({ hasText: `已確認 ${config.debriefReceiptCount}／${config.debriefReceiptCount} 席` });
        await count.waitFor();
        await count.click();
        const rows = await page.locator('#debrief-receipt-players li').allTextContents();
        assert.equal(rows.length, config.debriefReceiptCount);
        assert.ok(rows.every(row => row.endsWith(' · 已確認')));
        await page.screenshot({ path: path.join(out, 'debrief-receipts.png'), fullPage: true });
        await save('debrief-receipts.json', { sessionId: config.sessionId, streamId: config.streamId, rows });
      }
      if (config.battleOverview) {
        const reply = page.waitForResponse(response => response.url() === config.base + '/api/sessions/' + config.sessionId + '/overview');
        await page.locator('#refresh').click();
        const response = await reply;
        assert.equal(response.status(), 200);
        const { session, statistics, recentEvents } = await response.json();
        assert.equal(session.id, config.sessionId);
        assert.equal(session.combatStream.streamId, config.streamId);
        assert.equal(session.combatStream.sealed, true);
        assert.equal(statistics.pendingTelemetry, false);
        assert.equal(statistics.sessionId, session.id);
        assert.equal(statistics.throughSequence, session.sequence);
        assert.equal(recentEvents.at(-1).sequence, session.sequence);
        assert.equal(recentEvents.at(-1).kind, 'CombatStreamSealed');
        assert.ok((await page.locator('#session-meta').innerText()).endsWith('序號 ' + session.sequence));
        assert.ok((await page.locator('#event-list li').first().innerText()).includes('#' + session.sequence + ' '));
        const table = await page.locator('#statistics tr').evaluateAll(rows => rows.map(row => Array.from(row.cells, cell => cell.textContent)));
        assert.deepEqual(table, statistics.players.map(player => [player.name, player.ammoUsed, player.kills, player.damageTaken,
          player.hitsReceived, player.accuracyPercent + '%', player.health].map(String)));
        await save('archive-battle-overview.json', { sessionId: session.id, statistics, displayedRows: table, lastEventSequence: recentEvents.at(-1).sequence });
      }
      await page.screenshot({ path: path.join(out, 'archived.png'), fullPage: true });
      report = { complete: true, sessionId: config.sessionId, streamId: config.streamId, acceptedWorldSequence: lastWorld.acceptedSequence, origin: lastWorld.header.origin, roomIds: lastWorld.header.roomIds, summary, uncaughtErrors: errors, source: 'Actual console GET world response; no route fulfillment or replacement', scope: 'Native Simulation source and archive UI only. Client delivery / original journals / process cleanup separately verified by owning fixture.' }; success = true;
    })(), cancellation]);
  } catch (error) {
    failure = error.name;
    if (page && !page.isClosed()) {
      await save('failure-state.json', await page.evaluate(() => ({ selected: document.querySelector('#session-select')?.value, includeEnded: document.querySelector('#include-ended')?.checked,
        phase: document.querySelector('#session-phase')?.textContent?.slice(0, 100), summary: document.querySelector('#closure-summary')?.textContent?.slice(0, 800), combat: document.querySelector('#closure-combat')?.textContent?.slice(0, 100), world: document.querySelector('#closure-world')?.textContent?.slice(0, 100),
        notice: document.querySelector('#notice')?.textContent?.slice(0, 500), workspaceHidden: document.querySelector('#workspace')?.hidden,
        roomReadiness: [...document.querySelectorAll('[data-room-readiness]')].slice(0, 5).map(cell => ({
          roomId: cell.dataset.roomReadiness, source: cell.dataset.sourceState, text: cell.textContent.slice(0, 160)
        })) }))).catch(() => {});
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
