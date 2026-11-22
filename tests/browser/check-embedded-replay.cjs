// Open the HTML files from --segmented-replay-exports, or from --volume-exports with its venue report.
const assert = require('node:assert/strict');
const { readFile } = require('node:fs/promises');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main(directory, reportPath) {
  let files = ['full', 'room-5'].map(name => ({ name, full: name === 'full', first: 1, last: 301, parts: 2 }));
  if (reportPath) {
    const volumes = JSON.parse(await readFile(reportPath, 'utf8')).replayVolumes;
    files = Object.entries(volumes).flatMap(([label, volume]) => volume.ranges.map(([first, last, parts]) =>
      ({ name: `${label}-${first}-${last}`, full: label === 'dense', first, last, parts })));
    assert.ok(files.length >= 4);
  }
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const context = await browser.newContext({ offline: true });
    for (const { name, full, first, last, parts } of files) {
      const page = await context.newPage();
      const url = pathToFileURL(resolve(directory, name + '.html')).href;
      const unexpected = [];
      page.on('request', r => { if (r.url() !== url) unexpected.push(r.url()); });
      page.on('pageerror', e => unexpected.push(e.message));
      page.on('console', m => { if (m.type() === 'error') unexpected.push(m.text()); });
      await page.goto(url);
      const field = name => page.locator('#player-replay-' + name);
      await field('message').filter({ hasText: `已載入 ${last - first + 1} 格。` }).waitFor();
      assert.match(await field('frame').innerText(), new RegExp('第 ' + first + ' 格'));
      assert.equal(await field('room').locator('option').count(), full ? 6 : 1);
      assert.equal(await field('room').inputValue(), full ? 'all' : '5');
      assert.ok(Number(await page.locator('#replay-canvas').getAttribute('data-triangles')) > 0);
      if (parts > 1) {
        const offset = Number(await field('segment').locator('option').nth(2).getAttribute('value'));
        const boundary = first + offset - 1;
        await field('number').fill(String(boundary));
        await field('number').press('Enter');
        assert.match(await field('frame').innerText(), new RegExp('第 ' + boundary + ' 格'));
        await field('next').click();
        assert.match(await field('frame').innerText(), new RegExp('第 ' + (boundary + 1) + ' 格'));
      }
      await field('number').fill(String(last - 1));
      await field('number').press('Enter');
      await field('play').click();
      await field('frame').filter({ hasText: `第 ${last} 格` }).waitFor();
      assert.ok(await field('next').isDisabled());
      assert.deepEqual(unexpected, []);
      await page.close();
      console.log(`${name}: opened offline at frame ${first} and played to frame ${last}`);
    }
  } finally { await browser.close(); }
}

main(process.argv[2], process.argv[3]).catch(error => { console.error(error); process.exitCode = 1; });
