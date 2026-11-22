const assert = require('node:assert/strict');
const fs = require('node:fs/promises');

module.exports = async function venueEnvironmentDownload({ context, base, tokens }) {
  const page = await context.newPage();
  try {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await page.locator('#venue-hardware-review-panel summary').click();
    const [file, response] = await Promise.all([
      page.waitForEvent('download'),
      page.waitForResponse(r => new URL(r.url()).pathname === '/api/venue/hardware-environment'),
      page.locator('#export-venue-environment').click()
    ]);
    assert.equal(file.suggestedFilename(), 'vr-command-venue-environment.json');
    const downloaded = JSON.parse(await fs.readFile(await file.path(), 'utf8'));
    assert.deepEqual(downloaded, await response.json());
    assert.deepEqual(downloaded.rooms.map(row => row.roomId), [1, 2, 3, 4, 5]);
    return downloaded;
  } finally { await page.close(); }
};
