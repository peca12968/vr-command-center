const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, zip, output] = process.argv.slice(2);
  const config = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(config.base + '/console/');
    await page.locator('#login-key').fill(config.masterKey);
    await page.locator('#login-form button').click();
    await page.locator('#vr-venue-read').click();
    const status = page.locator('#vr-venue-status');
    await status.filter({ hasText: config.mode === 'Linked' ? '五房合併' : '五房獨立' }).waitFor();
    assert.equal(await page.locator('#vr-venue-rooms li').count(), 5);
    const sent = page.waitForResponse(response => new URL(response.url()).pathname === '/api/vr-deployment/venue-bundle');
    const pending = page.waitForEvent('download');
    await page.locator('#vr-venue-issue').click();
    const response = await sent, download = await pending;
    assert.equal(response.status(), 200);
    assert.equal(response.headers()['cache-control'], 'no-store');
    assert.equal(response.request().postDataJSON().topology, config.mode);
    assert.equal(download.suggestedFilename(), 'vr-venue-connections.zip');
    await download.saveAs(zip);
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
  await fs.writeFile(output, JSON.stringify({ complete: true, mode: config.mode }, null, 2), { flag: 'wx' });
}
main().catch(error => { console.error(error.name + ': native VR venue tickets failed'); process.exitCode = 1; });
