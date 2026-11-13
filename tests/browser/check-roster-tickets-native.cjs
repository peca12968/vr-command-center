const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const input = [];
  for await (const chunk of process.stdin) input.push(chunk);
  const { base, token, rooms, output } = JSON.parse(Buffer.concat(input).toString('utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:(?!5080$)\d+$/);
  assert.deepEqual(rooms.map(room => room.roomId), [1, 2, 3, 4, 5]);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_SERVER_PLAN_CHROMIUM });
  try {
    const page = await browser.newPage({ acceptDownloads: true }), checks = [];
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    for (const { roomId, sessionId, address, port, players } of rooms) {
      await page.locator(`[data-begin-room="${roomId}"] button`).click();
      await page.locator('#roster-title:focus').waitFor();
      assert.equal(await page.locator('#session-select').inputValue(), sessionId);
      assert.equal(await page.locator('#roster-room').inputValue(), String(roomId));
      assert.equal(await page.locator('#roster tr:visible').count(), players.length);
      await page.waitForFunction(({ address, port }) =>
        document.querySelector('#game-address').value === address && Number(document.querySelector('#game-port').value) === port
        && document.querySelector('#roster-ticket-destination').textContent === `配票端點 ${address}:${port}`
        && !document.querySelector('#download-roster-room-tickets').disabled,
      { address, port });
      const route = `/api/sessions/${sessionId}/rooms/${roomId}/join-ticket-bundle`;
      const [file, response] = await Promise.all([
        page.waitForEvent('download'),
        page.waitForResponse(response => new URL(response.url()).pathname === route && response.request().method() === 'POST'),
        page.locator('#download-roster-room-tickets').click()
      ]);
      assert.equal(response.status(), 200);
      assert.deepEqual(response.request().postDataJSON(), { address, port, players });
      assert.equal(response.headers()['cache-control'], 'no-store');
      assert.equal(file.suggestedFilename(), `room-${String(roomId).padStart(2, '0')}-connections.zip`);
      const name = `room-${roomId}.zip`;
      await file.saveAs(path.join(output, name));
      checks.push({ roomId, sessionId, seats: players.length, zip: name });
    }
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify(checks, null, 2), { flag: 'wx' });
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
