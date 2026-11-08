// Observe a real interrupted Windows source before and after the offline relay.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));

async function main() {
  const [directory] = process.argv.slice(2);
  const config = await read(path.join(directory, 'browser-review.json'));
  const { Room3: key } = (await read(path.join(directory, 'keys.json'))).OperatorKeys;
  const route = `/api/sessions/${config.sessionId}/world`;
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.ok(Number.isSafeInteger(config.tail) && config.tail > 0);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  let monitor;
  try {
    const review = async () => {
      const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
      const errors = [], watches = [];
      page.on('pageerror', error => errors.push(error.name));
      page.on('request', request => {
        const url = new URL(request.url());
        if (url.origin === config.base && url.pathname === route + '/watch') {
          const { searchParams } = url;
          watches.push({ mode: searchParams.get('mode'), from: searchParams.get('fromFrame'), through: searchParams.get('throughFrame') });
        }
      });
      await page.goto(config.base + '/console/');
      await page.locator('#login-key').fill(key);
      await page.locator('#login-form button').click();
      await page.locator('#tab-world').click();
      await page.locator('#world-recording').selectOption(config.sessionId);
      await page.locator('#world-replay').click();
      const extend = page.locator('#world-frame-extend');
      const canvas = page.locator('#world-canvas');
      const savedTail = async sequence => page.waitForFunction(expected =>
        document.querySelector('#world-freshness').textContent === '已到已保存片段尾端'
        && document.querySelector('#world-canvas').dataset.sequence === String(expected),
      sequence, { polling: 50 });
      await savedTail(config.tail);
      assert.equal(await extend.isEnabled(), true);
      await extend.click();
      await page.waitForFunction(() => document.querySelector('#world-frame-message').textContent === '目前沒有新的保存快照。');
      assert.equal(watches.length, 1);
      await page.screenshot({ path: path.join(directory, 'browser-prefix.png') });
      await fs.writeFile(path.join(directory, 'browser-ready'), '', { flag: 'wx' });

      let relay;
      while (!relay) {
        try { relay = await read(path.join(directory, 'browser-relay.json')); }
        catch (error) {
          if (error.code !== 'ENOENT') throw error;
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      assert.equal(Number(await canvas.getAttribute('data-sequence')), config.tail);
      await extend.click();
      await savedTail(relay.tail);
      assert.deepEqual(watches, [
        { mode: 'replay', from: '1', through: 'latest' },
        { mode: 'replay', from: String(config.tail + 1), through: String(relay.tail) }
      ]);
      assert.match(await page.locator('#world-status').innerText(), /錄製未封存/);
      assert.equal(await page.locator('#world-frame-next').isDisabled(), true);
      assert.equal((await page.locator('#world-statistics tr td').allTextContents())[3], String(relay.damage));
      assert.deepEqual(errors, []);
      await page.screenshot({ path: path.join(directory, 'browser-extended.png') });
      await fs.writeFile(path.join(directory, 'browser-checks.json'), JSON.stringify({ sessionId: config.sessionId, watches,
        finalSequence: relay.tail, damage: relay.damage, unsealed: true, browserErrors: errors }, null, 2), { flag: 'wx' });
    };
    const cancelled = new Promise((resolve, reject) => {
      monitor = setInterval(() => fs.stat(path.join(directory, 'browser-stop')).then(() => reject(new Error('Browser check cancelled'))).catch(() => {}), 200);
    });
    await Promise.race([review(), cancelled]);
  } finally {
    clearInterval(monitor);
    await browser.close();
  }
}

main().catch(error => { console.error(error.name + ': ' + error.message); process.exitCode = 1; });
