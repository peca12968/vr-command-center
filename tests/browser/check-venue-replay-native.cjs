const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, output] = process.argv.slice(2);
  const config = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const results = [], fieldEvidence = [];
  let history;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 }, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(config.base + '/console/');
    await page.locator('#login-key').fill(config.masterKey);
    await page.locator('#login-form button').click();
    async function openReplay(session) {
      const original = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/api/sessions/${session.sessionId}/world/watch`);
      await page.locator(`[data-venue-replay="${session.sessionId}"]`).click();
      const stream = await original, query = new URL(stream.url()).searchParams;
      assert.equal(stream.status(), 200);
      assert.equal(query.get('mode'), 'replay');
      assert.equal(query.get('fromFrame'), '1');
      assert.equal(query.has('throughFrame'), false);
      const canvas = page.locator('#world-canvas[data-sequence]');
      await canvas.waitFor();
      const room = session.roomIds.length === 1 ? String(session.roomIds[0]) : 'all';
      assert.equal(await page.locator('#world-recording').inputValue(), session.sessionId);
      assert.equal(await page.locator('#world-room').inputValue(), room);
      assert.equal(await page.locator('#world-camera').inputValue(), room === 'all' ? 'overview' : 'top');
      const sequence = Number(await canvas.getAttribute('data-sequence'));
      assert(sequence > 0 && sequence <= session.replay.throughSequence);
      return { sessionId: session.sessionId, room, sequence, throughSequence: session.replay.throughSequence };
    }
    async function reviewInterval(replay) {
      const canvas = page.locator('#world-canvas');
      await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('執行中'), null, { polling: 50 });
      await page.locator('#world-pause').click();
      const start = Number(await canvas.getAttribute('data-sequence')), end = start + 1;
      assert(start > 0 && end < replay.throughSequence);
      await page.locator('#world-clip-start').click();
      await page.locator('#world-frame-next').click();
      await page.waitForFunction(sequence => document.querySelector('#world-canvas').dataset.sequence === String(sequence), end, { polling: 50 });
      await page.locator('#world-clip-end').click();
      const bounded = page.waitForResponse(response => {
        const url = new URL(response.url());
        return url.pathname === `/api/sessions/${replay.sessionId}/world/watch`
          && url.searchParams.get('fromFrame') === String(start) && url.searchParams.get('throughFrame') === String(end);
      });
      await page.locator('#world-clip-play').click();
      assert.equal((await bounded).status(), 200);
      await page.locator('#world-clip-status').filter({ hasText: '已到片段終點' }).waitFor();
      assert.equal(Number(await canvas.getAttribute('data-sequence')), end);
      assert.equal(await page.locator('#world-room').inputValue(), replay.room);
      assert.equal(await page.locator('#world-frame-next').isEnabled(), true);
      assert.match(await page.locator('#world-status').innerText(), /錄製已核對封存/);
      const original = await fetch(`${config.base}/api/sessions/${replay.sessionId}/world/frames/${end}`,
        { headers: { Authorization: 'Bearer ' + config.masterKey } });
      assert.equal(original.status, 200);
      const { packet } = await original.json();
      assert.equal(packet.sequence, end);
      assert.equal(packet.frame.phase, 'Running');
      assert((await page.locator('#world-time').innerText()).startsWith((packet.elapsedMilliseconds / 1000).toFixed(2) + ' 秒'));
      await page.locator('#world-clip').screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-interval.png') });
      return { start, end, reached: Number(await canvas.getAttribute('data-sequence')), elapsedMilliseconds: packet.elapsedMilliseconds };
    }
    for (const session of config.sessions) {
      const replay = await openReplay(session);
      if (!results.length) {
        await page.screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-replay.png') });
        replay.interval = await reviewInterval(replay);
      }
      results.push(replay);
      await page.locator('#tab-operations').click();
    }
    for (const { batchId, zip, archived } of config.fieldEvidence ?? []) {
      if (archived) {
        await page.locator('#venue-closure-load').click();
        await page.locator('#venue-closure-batch').selectOption(batchId);
      }
      const route = `/api/venue/closure/${batchId}/field-evidence.zip`;
      const response = page.waitForResponse(reply => new URL(reply.url()).pathname === route);
      const started = page.waitForEvent('download');
      await page.locator('#export-venue-field').click();
      const download = await started;
      assert.equal((await response).status(), 200);
      assert.equal(download.suggestedFilename(), `vr-command-venue-field-v1-${batchId}.zip`);
      assert((await fs.readFile(await download.path())).equals(await fs.readFile(zip)));
      fieldEvidence.push(batchId);
    }
    if (config.history) {
      const { batch, zip } = config.history;
      const picker = page.locator('#venue-closure-batch');
      await page.locator('#venue-closure-load').click();
      await picker.selectOption(batch.requestId);
      const older = batch.sessions[2];
      await page.locator(`[data-venue-replay="${older.sessionId}"]`).waitFor();
      const started = page.waitForEvent('download');
      await page.locator('#export-venue-reports').click();
      const download = await started;
      assert.equal(download.suggestedFilename(), `vr-command-venue-reports-v1-${batch.requestId}.zip`);
      assert((await fs.readFile(await download.path())).equals(await fs.readFile(zip)));
      history = { requestId: batch.requestId, zipMatched: true, ...await openReplay(older) };
      await page.locator('#tab-operations').click();
      assert.equal(await picker.inputValue(), batch.requestId);
    }
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
  await fs.writeFile(output, JSON.stringify({ complete: true, mode: config.mode, results, history, fieldEvidence }, null, 2), { flag: 'wx' });
}
main().catch(error => { console.error(error.name + ': native venue replay UI failed'); process.exitCode = 1; });
