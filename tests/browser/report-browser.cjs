const fs = require('node:fs/promises');
const path = require('node:path');

module.exports = async function reportBrowser({ context, tokens, base, api, session, linked, screenshots, check }) {
  const page = await context.newPage(), errors = [], downloads = [];
  page.on('pageerror', error => errors.push(error.message)); page.on('download', download => downloads.push(download));
  const button = page.locator('#export-report');
  async function login() {
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.waitForFunction(() => !document.querySelector('#workspace').hidden && !document.querySelector('#session-select').disabled);
    await page.locator('#include-ended').check(); await page.locator('#refresh').click();
    await page.locator(`#session-select option[value="${session.id}"]`).waitFor({ state: 'attached' });
  }
  async function select(id) {
    await page.locator('#session-select').selectOption(id);
    await page.waitForFunction(id => document.querySelector('#session-select').value === id && !document.querySelector('#export-report').disabled, id);
  }
  const fetchCsv = id => fetch(`${base}/api/sessions/${id}/report.csv`, { headers: { Authorization: 'Bearer ' + tokens.Master } });
  async function downloadMatches(id) {
    const before = (await api('/sessions/' + id)).sequence;
    const waiting = page.waitForEvent('download'); await button.click(); const download = await waiting;
    const bytes = await fs.readFile(await download.path()), response = await fetchCsv(id);
    check(response.ok && download.suggestedFilename() === `vr-command-report-v1-${id}.csv`
      && bytes.equals(Buffer.from(await response.arrayBuffer())) && bytes.subarray(0, 3).equals(Buffer.from([239, 187, 191])),
      'Browser downloads the exact authorized final CSV bytes and safe UUID filename');
    check((await api('/sessions/' + id)).sequence === before, 'Final report download is read-only and does not append events');
    await fs.writeFile(path.join(screenshots, 'final-report.csv'), bytes);
  }
  // The server response is obtained under real authorization before delaying delivery.
  async function hold() {
    let requested, release, delivered;
    const request = new Promise(resolve => { requested = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    const done = new Promise(resolve => { delivered = resolve; });
    const handler = async route => {
      const response = await route.fetch(); requested(); await gate;
      try { await route.fulfill({ response }); } catch { /* The browser intentionally aborts this stale request. */ }
      finally { delivered(); }
    };
    await page.route('**/api/sessions/*/report.csv', handler);
    return { request, release, done, handler };
  }
  try {
    await page.goto(base + '/console/'); await login(); await select(session.id);
    await downloadMatches(session.id);
    check((await page.locator('#statistics').innerText()).includes('80') && (await page.locator('#report-status').innerText()).includes('報表已下載'),
      'Archived statistics and the report download result are visible together');
    await page.screenshot({ path: path.join(screenshots, 'final-report.png'), fullPage: true });
    let listRequested, releaseList, listDelivered, heldList = false;
    const listing = new Promise(resolve => { listRequested = resolve; });
    const listGate = new Promise(resolve => { releaseList = resolve; });
    const listDone = new Promise(resolve => { listDelivered = resolve; });
    const listHandler = async route => {
      if (heldList) return route.continue();
      heldList = true;
      const response = await route.fetch(); listRequested(); await listGate;
      await route.fulfill({ response }); listDelivered();
    };
    await page.route('**/api/sessions?includeEnded=*', listHandler);
    await page.locator('#refresh').click(); await listing;
    await page.locator('#session-select').selectOption(linked.id);
    check(await button.isDisabled() && await page.locator('#session-panel').isHidden(), 'Selecting a new session invalidates export immediately while a background refresh is pending');
    await page.locator('#session-select').selectOption(session.id);
    releaseList(); await listDone; await page.unroute('**/api/sessions?includeEnded=*', listHandler);
    await page.waitForFunction(() => !document.querySelector('#export-report').disabled && !document.querySelector('#session-panel').hidden);
    check(await page.locator('#session-select').inputValue() === session.id, 'Rapid session choices during a held refresh keep only the latest selection');
    const expectedCount = downloads.length;
    const delayed = await hold(); await button.click(); await delayed.request;
    check(await button.isDisabled() && await page.locator('#session-select').isEnabled(), 'Pending report prevents duplicate downloads while allowing session changes');
    await select(linked.id); await select(session.id); delayed.release(); await delayed.done;
    await page.unroute('**/api/sessions/*/report.csv', delayed.handler); await page.waitForTimeout(200);
    check(downloads.length === expectedCount && await button.isEnabled(), 'Late report cannot download after switching away and back to the same session');
    const loggedOut = await hold(); await button.click(); await loggedOut.request;
    await page.locator('#logout').click(); await login(); await select(session.id);
    loggedOut.release(); await loggedOut.done; await page.unroute('**/api/sessions/*/report.csv', loggedOut.handler);
    await page.waitForTimeout(200);
    check(downloads.length === expectedCount && await button.isEnabled(), 'Late report from an earlier login cannot download into the new login');
    await page.route('**/api/sessions/*/report.csv', route => route.fulfill({ status: 409, contentType: 'application/json', body: '{"error":"not sealed"}' }));
    await button.click(); await page.waitForFunction(() => document.querySelector('#report-status').textContent.includes('尚未完成'));
    check(downloads.length === expectedCount && await button.isEnabled(), 'Backend readiness conflict shows an actionable error and permits a fresh retry');
    await page.unroute('**/api/sessions/*/report.csv');
    await downloadMatches(session.id);
    await page.route('**/api/sessions/*/report.csv', route => route.fulfill({ status: 200, contentType: 'text/html', body: 'not a CSV' }));
    await button.click(); await page.waitForFunction(() => document.querySelector('#report-status').textContent.includes('格式不符'));
    check(downloads.length === expectedCount + 1 && await button.isEnabled(), 'Unexpected response format never becomes a downloaded report');
    await page.unroute('**/api/sessions/*/report.csv');
    await page.route('**/api/sessions/*/report.csv', route => route.fulfill({ status: 200, contentType: 'text/csv-fake', body: 'not a CSV MIME type' }));
    await button.click(); await page.waitForFunction(() => document.querySelector('#report-status').textContent.includes('格式不符'));
    check(downloads.length === expectedCount + 1 && await button.isEnabled(), 'CSV-like MIME prefixes are rejected unless the complete media type is text/csv');
    await page.unroute('**/api/sessions/*/report.csv');
    await page.route('**/api/sessions/*/report.csv', route => route.fulfill({ status: 401, contentType: 'application/json', body: '{}' }));
    await button.click(); await page.locator('#login-panel').waitFor({ state: 'visible' });
    check(await page.locator('#workspace').isHidden() && downloads.length === expectedCount + 1, 'Current unauthorized report response logs out without downloading a file');
    check(errors.length === 0, 'Report workflow has no uncaught browser errors');
  } finally { await page.close(); }
};
