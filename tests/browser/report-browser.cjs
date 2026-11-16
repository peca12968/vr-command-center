const fs = require('node:fs/promises');
const path = require('node:path');
const readCsv = require('./csv.cjs');

module.exports = async function reportBrowser({ context, tokens, base, api, session, linked, screenshots, check }) {
  const page = await context.newPage(), errors = [], downloads = [];
  page.on('pageerror', error => errors.push(error.message)); page.on('download', download => downloads.push(download));
  const button = page.locator('#export-report');
  const bundleButton = page.locator('#export-report-bundle');
  async function login(role = 'Master', initialId = session.id) {
    await page.locator('#login-key').fill(tokens[role]); await page.locator('#login-form button').click();
    await page.waitForFunction(() => !document.querySelector('#workspace').hidden && !document.querySelector('#session-select').disabled);
    await page.locator('#include-ended').check(); await page.locator('#refresh').click();
    await page.locator(`#session-select option[value="${initialId}"]`).waitFor({ state: 'attached' });
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
  async function hold(pattern = '**/api/sessions/*/report.csv') {
    let requested, release, delivered;
    const request = new Promise(resolve => { requested = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    const done = new Promise(resolve => { delivered = resolve; });
    const handler = async route => {
      const response = await route.fetch(); requested(); await gate;
      try { await route.fulfill({ response }); } catch { /* The browser intentionally aborts this stale request. */ }
      finally { delivered(); }
    };
    await page.route(pattern, handler);
    return { request, release, done, handler, pattern };
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
    await page.unroute('**/api/sessions/*/report.csv');
    await login(); await select(linked.id);
    const scope = page.locator('#report-room');
    check(await scope.inputValue() === '' && await scope.locator('option').count() === 6, 'Master may choose the full linked report or any of five rooms');
    const displayedRooms = () => page.locator('#statistics tr td:last-child').allTextContents();
    check((await displayedRooms()).join(',') === '1,2', 'The full statistics table identifies the original room of each linked player');
    async function scopedDownload(roomId, role) {
      const pending = page.waitForEvent('download'); await button.click(); const download = await pending;
      const bytes = await fs.readFile(await download.path());
      const response = await fetch(`${base}/api/sessions/${linked.id}/rooms/${roomId}/report.csv`, { headers: { Authorization: 'Bearer ' + tokens[role] } });
      const rows = readCsv(bytes);
      check(response.ok && bytes.equals(Buffer.from(await response.arrayBuffer())) &&
        download.suggestedFilename() === `vr-command-report-v1-${linked.id}-room-0${roomId}.csv`
        && rows.length === 1 && rows[0].reportRoomId === String(roomId) && rows[0].playerRoomId === String(roomId)
        && (await displayedRooms()).join() === rows[0].playerRoomId
        && await page.locator('#statistics tr td:first-child').innerText() === rows[0].playerName
        && rows[0].roomIds === '1|2|3|4|5' && rows[0].sessionId === linked.id,
        `${role} downloads its exact single-room rows, preserving linked session metadata`);
      await fs.writeFile(path.join(screenshots, `scoped-report-${role}.csv`), bytes);
    }
    await scope.selectOption('2'); await scopedDownload(2, 'Master');
    await page.locator('#refresh').click();
    check(await scope.inputValue() === '2' && (await displayedRooms()).join() === '2',
      'A refresh preserves the current linked statistics and CSV room');
    await page.screenshot({ path: path.join(screenshots, 'scoped-report-master.png'), fullPage: true });
    const bundleEndpoint = `${base}/api/sessions/${linked.id}/reports.zip`;
    const zipReady = page.waitForEvent('download');
    await bundleButton.click();
    const zip = await zipReady, archive = await fs.readFile(await zip.path());
    const authoritative = await fetch(bundleEndpoint, { headers: { Authorization: 'Bearer ' + tokens.Master } });
    check(authoritative.ok && archive.equals(Buffer.from(await authoritative.arrayBuffer()))
      && zip.suggestedFilename() === `vr-command-reports-v1-${linked.id}.zip` && await scope.inputValue() === '2',
      'Master downloads the exact linked ZIP from any CSV scope without changing that selection');
    await fs.writeFile(path.join(screenshots, 'linked-reports.zip'), archive);
    const beforeWrongMime = downloads.length;
    const zipMethods = [];
    await page.route(bundleEndpoint, async route => {
      const method = route.request().method();
      zipMethods.push(method);
      if (method !== 'HEAD') return route.continue();
      const original = await route.fetch();
      await route.fulfill({ response: original, headers: { ...original.headers(), 'content-type': 'application/zip-fake' } });
    });
    await bundleButton.click();
    await page.locator('#report-status').filter({ hasText: '無法核對戰績 ZIP 的原始內容' }).waitFor();
    check(zipMethods.join() === 'HEAD' && downloads.length === beforeWrongMime && await bundleButton.isEnabled(),
      'ZIP export rejects an incorrect MIME at HEAD before downloading and permits retry');
    await page.unroute(bundleEndpoint);
    await scope.selectOption('5');
    check(await page.locator('#statistics .empty-cell').innerText() === '此房尚無玩家戰績'
      && await page.locator('#statistics-scope-status').innerText() === '房間 5 · 0 名玩家戰績',
      'An empty room has an explicit zero-player view instead of showing the whole linked ledger');
    await select(session.id); await select(linked.id);
    check(await scope.inputValue() === '' && (await displayedRooms()).join(',') === '1,2',
      'Changing sessions resets the previous room filter');
    const picker = page.locator('#player-review-select'), personalButton = page.locator('#export-player-report');
    const finalRows = readCsv(Buffer.from(await (await fetchCsv(linked.id)).arrayBuffer()));
    const player1 = finalRows.find(row => row.playerRoomId === '1').playerId;
    const player2 = finalRows.find(row => row.playerRoomId === '2').playerId;
    const personalUrl = player => `${base}/api/sessions/${linked.id}/players/${player}/report.csv`;
    async function rejectCsv(url, button, substitute) {
      const count = downloads.length;
      await page.route(url, async route => {
        const original = await route.fetch();
        const body = new TextDecoder('utf-8', { ignoreBOM: true }).decode(await original.body());
        await route.fulfill({ response: original, body: substitute(body) });
      });
      try {
        await button.click();
        await page.locator('#report-status').filter({ hasText: '封存戰績不符' }).waitFor();
        check(downloads.length === count && await button.isEnabled(), 'A mismatched CSV is rejected before download and permits retry');
      } finally { await page.unroute(url); }
    }
    await rejectCsv(`${base}/api/sessions/${linked.id}/report.csv`, button, body => body.replaceAll(linked.id, session.id));
    await scope.selectOption('1');
    const roomUrl = `${base}/api/sessions/${linked.id}/rooms/1/report.csv`;
    await rejectCsv(roomUrl, button, body => body.replace(/,"1"\r\n$/, ',"2"\r\n'));
    await scopedDownload(1, 'Master');
    await scope.selectOption('');
    await picker.selectOption(player1);
    const otherPlayer = await fetch(personalUrl(player2), { headers: { Authorization: 'Bearer ' + tokens.Master } });
    const otherCsv = '\uFEFF' + (await otherPlayer.text());
    await rejectCsv(personalUrl(player1), personalButton, () => otherCsv);
    await rejectCsv(personalUrl(player1), personalButton, body => {
      const rows = body.split('\r\n'), header = rows[0].split(',');
      const value = header.indexOf('"ammoUsed"');
      // This original player's simple-name row has no comma in its text fields.
      const columns = rows[1].split(',');
      columns[value] = '"999"';
      return [rows[0], columns.join(','), ''].join('\r\n');
    });
    check(await personalButton.isEnabled() && await page.locator('#open-player-review').isDisabled(),
      'The sealed combat ledger allows a personal download while the world recording is unavailable');
    const personalHeld = await hold(personalUrl(player1));
    const beforePersonal = downloads.length;
    await personalButton.click(); await personalHeld.request;
    try {
      await picker.selectOption(player2); await picker.selectOption(player1);
    } finally { personalHeld.release(); }
    await personalHeld.done; await page.unroute(personalHeld.pattern, personalHeld.handler);
    check(downloads.length === beforePersonal && await personalButton.isEnabled(),
      'Switching the individual selection away and back cancels the old download');
    await page.locator('#logout').click(); await login('Room1', linked.id); await select(linked.id);
    check(await scope.inputValue() === '1' && await scope.isDisabled() && await scope.locator('option').count() === 1,
      'Room controller sees only its own report scope, with no stale master choice after logout');
    await scopedDownload(1, 'Room1');
    await picker.selectOption(player1);
    const personalReady = page.waitForEvent('download');
    await personalButton.click(); const personalFile = await personalReady;
    const personalBytes = await fs.readFile(await personalFile.path());
    const personalRows = readCsv(personalBytes);
    check(personalFile.suggestedFilename() === `vr-command-report-v1-${linked.id}-player-${player1}.csv`
      && JSON.stringify(personalRows) === JSON.stringify(finalRows.filter(row => row.playerId === player1))
      && (await picker.locator('option').evaluateAll(options => options.map(option => option.value))).join(',') === `,${player1}`,
      'Room 1 downloads exactly the selected original player row and its picker omits the other room');
    check((await fetch(personalUrl(player2), { headers: { Authorization: 'Bearer ' + tokens.Room1 } })).status === 404,
      'An individual CSV request cannot expose another room player');
    await fs.writeFile(path.join(screenshots, 'individual-report-room1.csv'), personalBytes);
    check(!await bundleButton.isVisible(), 'Room controller never sees the all-room ZIP action');
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)
      && await page.locator('#statistics-scope-status').isVisible(), 'The linked room statistics and selector fit a mobile console');
    await page.locator('#statistics-scope').screenshot({ path: path.join(screenshots, 'statistics-room-scope-mobile.png') });
    check(errors.length === 0, 'Report workflow has no uncaught browser errors');
  } finally { await page.close(); }
};
