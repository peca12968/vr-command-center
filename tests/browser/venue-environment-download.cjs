const assert = require('node:assert/strict');
const fs = require('node:fs/promises');

module.exports = async function venueEnvironmentDownload({ context, base, tokens }) {
  const page = await context.newPage();
  try {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await page.locator('#venue-hardware-review-panel summary').click();
    const exportButton = page.locator('#export-venue-environment');
    const endpoint = url => url.pathname === '/api/venue/hardware-environment';
    const ids = new Set(), downloads = [];
    page.on('download', file => downloads.push(file));
    function readId(url) {
      const id = url.searchParams.get('sampleId');
      assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
      assert.ok(!ids.has(id), 'Every export requests a new sample');
      ids.add(id);
      return id;
    }
    async function downloadCurrent() {
      const [file, response] = await Promise.all([
        page.waitForEvent('download'),
        page.waitForResponse(r => endpoint(new URL(r.url()))),
        exportButton.click()
      ]);
      const raw = await response.body();
      const snapshot = JSON.parse(raw);
      assert.equal(snapshot.sampleId, readId(new URL(response.url())));
      assert.equal(file.suggestedFilename(), 'vr-command-venue-environment.json');
      assert.deepEqual(JSON.parse(await fs.readFile(await file.path(), 'utf8')), snapshot);
      assert.deepEqual(snapshot.rooms.map(row => row.roomId), [1, 2, 3, 4, 5]);
      return raw;
    }
    const previous = await downloadCurrent();
    const legacy = JSON.parse(previous);
    delete legacy.sampleId;
    for (const body of [previous, Buffer.from(JSON.stringify(legacy))]) {
      await page.route(endpoint, route => route.fulfill({ contentType: 'application/json', body }));
      const [response] = await Promise.all([
        page.waitForResponse(r => endpoint(new URL(r.url()))), exportButton.click()
      ]);
      readId(new URL(response.url()));
      await page.locator('#notice.error').filter({ hasText: '無法確認這是本次讀取的五房環境設定' }).waitFor();
      await page.waitForFunction(() => !document.getElementById('export-venue-environment').disabled);
      await page.unroute(endpoint);
    }
    const recovered = JSON.parse(await downloadCurrent());
    await page.locator('#notice:not(.error)').filter({ hasText: '已下載本次讀取的五房環境設定' }).waitFor();
    assert.equal(downloads.length, 2);
    return recovered;
  } finally { await page.close(); }
};
