const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

async function verifySettingDownload(page, directory, name, key, requestId, readPhaseBytes) {
  const button = page.locator(`#venue-${name}-batch-download`);
  const phase = url => url.pathname === '/api/venue/phase';
  const isPhaseRead = response => phase(new URL(response.url())) && response.request().method() === 'GET';
  let expected;
  const serve = route => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill(expected ? { contentType: 'application/json', body: expected } : { status: 503, body: '' });
  };
  // Withdraw the previous snapshot. Room commands can change the plan without changing the batch ID.
  await button.waitFor({ state: 'visible' });
  await page.route(phase, serve);
  try {
    await page.waitForResponse(response => isPhaseRead(response) && response.status() === 503);
    await button.waitFor({ state: 'hidden' });
    assert.ok(await button.isDisabled());
    // Deliver exactly one known API snapshot on recovery, even if the console polls again.
    expected = await readPhaseBytes();
    assert.equal(JSON.parse(expected)[key].requestId, requestId);
    const [download] = await Promise.all([page.waitForEvent('download'), button.click()]);
    assert.equal(download.suggestedFilename(), `vr-command-venue-${name}-${requestId}.json`);
    const target = path.join(directory, download.suggestedFilename());
    await download.saveAs(target);
    assert.ok((await fs.readFile(target)).equals(expected), `Downloaded ${name} batch differs from the original phase response delivered to the page`);
  } finally {
    await page.unroute(phase, serve);
  }
}

module.exports = { verifySettingDownload };
