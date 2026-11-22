// Open the two HTML files exported by check-venue-world-ipc.py --segmented-replay-exports.
const assert = require('node:assert/strict');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main(directory) {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const context = await browser.newContext({ offline: true });
    for (const scope of ['full', 'room-5']) {
      const page = await context.newPage();
      const url = pathToFileURL(resolve(directory, scope + '.html')).href;
      const unexpected = [];
      page.on('request', r => { if (r.url() !== url) unexpected.push(r.url()); });
      page.on('pageerror', e => unexpected.push(e.message));
      page.on('console', m => { if (m.type() === 'error') unexpected.push(m.text()); });
      await page.goto(url);
      const field = name => page.locator('#player-replay-' + name);
      await field('message').filter({ hasText: '已載入 301 格。' }).waitFor();
      assert.equal(await field('room').locator('option').count(), scope === 'full' ? 6 : 1);
      assert.equal(await field('room').inputValue(), scope === 'full' ? 'all' : '5');
      assert.ok(Number(await page.locator('#replay-canvas').getAttribute('data-triangles')) > 0);
      const boundary = Number(await field('segment').locator('option').nth(2).getAttribute('value'));
      await field('number').fill(String(boundary));
      await field('number').press('Enter');
      assert.match(await field('frame').innerText(), new RegExp('第 ' + boundary + ' 格'));
      await field('next').click();
      assert.match(await field('frame').innerText(), new RegExp('第 ' + (boundary + 1) + ' 格'));
      await field('number').fill('300');
      await field('number').press('Enter');
      await field('play').click();
      await field('frame').filter({ hasText: '第 301 格' }).waitFor();
      assert.ok(await field('next').isDisabled());
      assert.deepEqual(unexpected, []);
      await page.close();
      console.log(scope + ': opened offline, crossed the original segment boundary and played to frame 301');
    }
  } finally { await browser.close(); }
}

main(process.argv[2]).catch(error => { console.error(error); process.exitCode = 1; });
