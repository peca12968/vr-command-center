const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');
const { holdTicketResponse } = require('./ticket-download-fence.cjs');

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
    const panel = page.locator('#mr-venue-panel');
    const submit = page.locator('#mr-venue-submit');
    const status = page.locator('#mr-venue-status');
    await panel.waitFor();
    assert.equal(await submit.isDisabled(), true);
    const originalFiles = await Promise.all(config.files.map(async (file, index) => {
      const input = page.locator(`#mr-venue-alignment-${index + 1}`);
      await input.setInputFiles(file);
      return input.evaluate(element => element.files[0].name);
    }));
    const endpointRows = panel.locator('label').filter({ hasText: `UDP ${config.endpoint}` });
    const held = await holdTicketResponse(page, config.base + '/api/mr-deployment/venue-bundle', () => submit.click(), async () => {
      assert.equal(await endpointRows.count(), 5);
      await fs.writeFile(config.signed, 'original ZIP signed', { flag: 'wx' });
      await page.waitForFunction(() => [...document.querySelectorAll('#mr-venue-files label')]
        .filter(row => row.textContent.includes('暫停配票')).length === 5, null, { polling: 100 });
    }, async () => {
      await status.filter({ hasText: /未下載部署包|已下載五房/ }).waitFor();
      return status.innerText();
    });
    assert.equal(held.signedResponses, 1);
    assert.equal(held.downloads, 0);
    assert.match(held.message, /房間 1.*等待原遊戲來源更新.*未下載部署包/);
    assert.equal(await submit.isDisabled(), true);
    const selectedFiles = () => panel.locator('input[type=file]').evaluateAll(inputs => inputs.map(input => input.files[0]?.name));
    assert.deepEqual(await selectedFiles(), originalFiles);
    await fs.writeFile(config.blocked, 'original ZIP discarded', { flag: 'wx' });
    await page.waitForFunction(() => !document.querySelector('#mr-venue-submit').disabled, null, { polling: 100 });
    assert.deepEqual(await selectedFiles(), originalFiles);
    assert.equal(await endpointRows.count(), 5);
    const pending = page.waitForEvent('download');
    await submit.click();
    const download = await pending;
    assert.equal(download.suggestedFilename(), 'quest-mr-venue.zip');
    await download.saveAs(zip);
    assert.deepEqual(errors, []);
    await fs.writeFile(output, JSON.stringify({ complete: true, held, restoredFiveFiles: true, endpointRows: 5 }), { flag: 'wx' });
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error.name + ': native MR venue source check failed'); process.exitCode = 1; });
