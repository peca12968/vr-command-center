const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');

async function main() {
  const input = [];
  for await (const chunk of process.stdin) input.push(chunk);
  const { base, token, rooms, output } = JSON.parse(Buffer.concat(input).toString('utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:(?!5080$)\d+$/);
  assert.deepEqual(rooms.map(room => room.roomId), [1, 2, 3, 4, 5]);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_SERVER_PLAN_CHROMIUM });
  try {
    const page = await browser.newPage(), writes = [], errors = [], observed = [];
    page.on('request', request => {
      const route = new URL(request.url()).pathname;
      if (route.startsWith('/api/') && request.method() !== 'GET'
          && !(route === '/api/mission-layout' && request.method() === 'POST')) writes.push([request.method(), route]);
    });
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    const policy = page.locator('#venue-full-participation');
    await policy.check();
    for (const { roomId, sessionId, players } of rooms) {
      const shortcut = page.locator(`[data-begin-room="${roomId}"] button`);
      await shortcut.click();
      await page.locator('#roster-title:focus').waitFor();
      assert.equal(await page.locator('#session-select').inputValue(), sessionId);
      assert.equal(await page.locator('#roster-room').inputValue(), String(roomId));
      const rows = await page.waitForFunction(expected => {
        const visible = [...document.querySelectorAll('#roster tr[data-roster-room]')].filter(row => !row.hidden);
        if (visible.length !== expected.length) return null;
        const rows = visible.map(row => {
          const status = row.querySelector('[data-readiness-player]');
          return { id: status.dataset.readinessPlayer, admissionId: status.dataset.admission, position: row.cells[1].textContent,
            status: status.textContent, ready: status.classList.contains('ready-player') };
        });
        return rows.every(row => row.ready && row.status.includes('合成姿態')
          && expected.some(player => player.id === row.id && player.admissionId === row.admissionId)) ? rows : null;
      }, players).then(handle => handle.jsonValue());
      for (const row of rows) {
        const expected = players.find(player => player.id === row.id);
        assert.equal(row.position, `${roomId} / ${expected.seat}`);
        assert.equal(row.admissionId, expected.admissionId);
      }
      assert(await policy.isChecked());
      observed.push({ roomId, sessionId, rows });
    }
    await page.locator('#refresh').click();
    await page.locator('#notice').filter({ hasText: '已更新。' }).waitFor();
    assert.equal(await page.locator('#roster-room').inputValue(), '5');
    assert.equal(await page.locator('#roster tr:visible').count(), 5);
    await page.locator('#session-panel').screenshot({ path: output.replace(/\.json$/, '.png') });
    assert.deepEqual(writes, []);
    assert.deepEqual(errors, []);
    await fs.writeFile(output, JSON.stringify({ rooms: observed, writeRequests: writes.length, refreshRoom: 5 }, null, 2), { flag: 'wx' });
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
