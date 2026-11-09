const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, zip, output] = process.argv.slice(2);
  const config = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  const mixed = config.mode === 'Mixed';
  let verifiedRoomEndpoints;
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(config.base + '/console/');
    await page.locator('#login-key').fill(config.masterKey);
    await page.locator('#login-form button').click();
    if (config.expectedEndpoints) {
      await page.setViewportSize({ width: 390, height: 844 });
      for (const { roomId, address, port } of config.expectedEndpoints) {
        const label = `UDP ${address}:${port}` + (config.mode === 'Linked' ? ' · 五房共用' : '')
          + (address.startsWith('127.') ? ' · 僅同機' : '');
        const card = page.locator(`[data-room-endpoint="${roomId}"]`);
        await card.filter({ hasText: label }).waitFor();
        assert.equal(await card.textContent(), label);
        assert.ok(await card.evaluate(cell => cell.scrollWidth <= cell.clientWidth + 1));
      }
      verifiedRoomEndpoints = await page.locator('[data-room-endpoint]').count();
      assert.equal(verifiedRoomEndpoints, 5);
      await page.locator('#rooms').screenshot({ path: output.replace(/\.json$/, '-room-endpoints.png') });
      await page.setViewportSize({ width: 1280, height: 900 });
    }
    await page.locator('#vr-venue-read').click();
    const status = page.locator('#vr-venue-status');
    await status.filter({ hasText: mixed ? 'VR／MR 混合獨立場' : config.mode === 'Linked' ? '五房合併' : '五房獨立' }).waitFor();
    assert.equal(await page.locator('#vr-venue-rooms li').count(), 5);
    if (mixed) {
      assert.equal(await page.locator('#vr-venue-title').textContent(), 'VR／MR 混合五房配票');
      assert.equal(await page.locator('#vr-venue-files input').count(), Object.keys(config.alignments).length);
      assert.equal(await page.locator('#vr-venue-issue').isDisabled(), true);
      for (const [room, path] of Object.entries(config.alignments))
        await page.locator('#mixed-venue-alignment-' + room).setInputFiles(path);
    }
    const route = mixed ? '/api/mixed-deployment/venue-bundle' : '/api/vr-deployment/venue-bundle';
    const sent = page.waitForResponse(response => new URL(response.url()).pathname === route);
    const pending = page.waitForEvent('download');
    await page.locator('#vr-venue-issue').click();
    const response = await sent, download = await pending;
    assert.equal(response.status(), 200);
    assert.equal(response.headers()['cache-control'], 'no-store');
    const body = response.request().postDataJSON();
    if (mixed) {
      for (const room of body.rooms) {
        const path = config.alignments[room.roomId];
        assert.equal(room.mode, path ? 'MR' : 'VR');
        assert.equal(room.alignmentFile, path ? (await fs.readFile(path)).toString('base64') : undefined);
      }
    } else assert.equal(body.topology, config.mode);
    assert.equal(download.suggestedFilename(), mixed ? 'vr-mr-venue-deployment.zip' : 'vr-venue-connections.zip');
    await download.saveAs(zip);
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
  await fs.writeFile(output, JSON.stringify({ complete: true, mode: config.mode, verifiedRoomEndpoints }, null, 2), { flag: 'wx' });
}
main().catch(error => { console.error(error.name + ': native VR venue tickets failed'); process.exitCode = 1; });
