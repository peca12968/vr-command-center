// Observe the original Linked Windows recording through the packaged console.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, out] = process.argv.slice(2);
  const { base, masterKey, sessionId, players } = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.equal(players.length, 25);
  await fs.mkdir(out);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const errors = [], writes = [], watches = [];
  const checks = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    page.on('pageerror', error => errors.push(error.name));
    page.on('request', request => {
      const url = new URL(request.url());
      if (url.origin !== base) return;
      if (request.method() !== 'GET' && url.pathname.startsWith('/api/')) writes.push(request.method());
      if (url.pathname.endsWith('/world/watch')) watches.push(url.pathname);
    });
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(masterKey);
    await page.locator('#login-form button').click();
    await page.locator('[data-watch-room="4"]').click();
    const picker = page.locator('#world-actor'), canvas = page.locator('#world-canvas'), camera = page.locator('#world-camera');
    const forRoom = room => players.filter(player => player.roomId === room);
    const playerOptions = () => picker.locator('option[value^="p:"]').evaluateAll(options => options.map(option => [option.value.slice(2), option.textContent]));
    const enemies = picker.locator('option[value^="e:"]');
    async function checkRoom(room) {
      assert.equal(await page.locator('#world-room').inputValue(), String(room));
      const options = new Map(await playerOptions());
      assert.equal(options.size, 5);
      for (const player of forRoom(room)) assert.ok(options.get(player.id)?.startsWith(`${player.name} · 房間 ${room} · `));
      const names = await page.locator('#world-statistics tr td:first-child').allTextContents();
      assert.deepEqual(names.sort(), forRoom(room).map(player => player.name).sort());
      assert.ok((await enemies.allTextContents()).every(label => label.includes(` · 房間 ${room} · `)));
    }
    await picker.locator(`option[value="p:${forRoom(4)[0].id}"]`).waitFor({ state: 'attached' });
    assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
    await checkRoom(4);
    assert.equal(await camera.inputValue(), 'top');
    checks.push('Original room card scopes named native players, enemies and statistics');
    const following = forRoom(4)[2];
    await picker.selectOption('p:' + following.id);
    await camera.selectOption('follow');
    await page.locator('#world-actor-info').filter({ hasText: following.name }).waitFor();
    const position = await canvas.getAttribute('data-camera');
    await page.locator('[data-world-room="2"]').click();
    await checkRoom(2);
    const sequence = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(after => Number(document.querySelector('#world-canvas').dataset.sequence) > after, sequence, { polling: 100 });
    assert.equal(await picker.inputValue(), '');
    assert.equal(await camera.inputValue(), 'free');
    assert.notEqual(await canvas.getAttribute('data-camera'), position);
    checks.push('Switching rooms clears the foreign follow target across new native frames');
    await page.locator('#world-player').screenshot({ path: path.join(out, 'room-2.png') });
    await page.locator('[data-world-room="all"]').click();
    assert.equal((await playerOptions()).length, 25);
    assert.ok(await enemies.count() > 0);
    assert.equal(await picker.inputValue(), '');
    assert.deepEqual(watches, [`/api/sessions/${sessionId}/world/watch`]);
    assert.deepEqual(writes, []);
    assert.deepEqual(errors, []);
    checks.push('All-room list restores 25 names through the original read-only stream');
  } finally { await browser.close(); }
  await fs.writeFile(path.join(out, 'checks.json'), JSON.stringify({ complete: true, checks, sessionId, players: 25 }, null, 2), { flag: 'wx' });
}
main().catch(error => { console.error(error); process.exitCode = 1; });
