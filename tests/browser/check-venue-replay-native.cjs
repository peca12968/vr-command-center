const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, output] = process.argv.slice(2);
  const config = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const results = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(config.base + '/console/');
    await page.locator('#login-key').fill(config.masterKey);
    await page.locator('#login-form button').click();
    for (const session of config.sessions) {
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
      results.push({ sessionId: session.sessionId, room, sequence, throughSequence: session.replay.throughSequence });
      if (results.length === 1) await page.screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-replay.png') });
      await page.locator('#tab-operations').click();
    }
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
  await fs.writeFile(output, JSON.stringify({ complete: true, mode: config.mode, results }, null, 2), { flag: 'wx' });
}
main().catch(error => { console.error(error.name + ': native venue replay UI failed'); process.exitCode = 1; });
