const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');
const { chromium } = require('playwright');
const { waitForLiveFrame } = require('./live-watch-fault.cjs');

async function main() {
  const [descriptor, out] = process.argv.slice(2);
  const { base, key, sessionId, roomId, seat, playerId, streamId } = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const errors = [], writes = [], watches = [];
    const sessionPath = `/api/sessions/${sessionId}`;
    page.on('pageerror', error => errors.push(error.name));
    page.on('request', request => {
      const url = new URL(request.url());
      if (url.origin !== base || !url.pathname.startsWith('/api/')) return;
      if (request.method() !== 'GET') writes.push(request.method());
      if (url.pathname.endsWith('/world/watch')) watches.push({ path: url.pathname, mode: url.searchParams.get('mode'),
        from: url.searchParams.get('fromFrame'), through: url.searchParams.get('throughFrame') });
    });
    const get = async route => {
      const response = await page.request.get(base + route, { headers: { Authorization: 'Bearer ' + key }, timeout: 5000 });
      assert.equal(response.status(), 200);
      return response.json();
    };
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(key);
    await page.locator('#login-form button').click();
    const initial = await get(sessionPath);
    assert.equal(initial.state, 'Running');
    assert.equal(initial.combatStream.streamId, streamId);
    await page.locator(`[data-room-pose-frame="${roomId}"]`).click();
    await page.waitForFunction(() => document.getElementById('world-frame-message').textContent.includes('姿態中斷快照')
      || document.getElementById('world-message').classList.contains('replay-error'), undefined, { polling: 100 });
    assert.match(await page.locator('#world-frame-message').textContent(), new RegExp(`房間 ${roomId} · 席位 ${seat}。$`),
      await page.locator('#world-message').textContent());
    const canvas = page.locator('#world-canvas');
    const camera = await canvas.getAttribute('data-camera');
    const before = Number(await canvas.getAttribute('data-sequence'));
    const viewed = (await get(sessionPath + '/world/frames/' + before)).packet;
    const original = viewed.frame.players.find(player => player.id === playerId);
    assert.ok(original?.health > 0 && original.roomId === roomId && original.connected === false);
    assert.equal(viewed.observedSequence, initial.sequence);
    assert.equal(await page.locator('#world-room').inputValue(), String(roomId));
    assert.equal(await page.locator('#world-camera').inputValue(), 'top');
    await page.locator('#world-player').screenshot({ path: path.join(out, 'saved.png') });
    await fs.writeFile(path.join(out, 'reviewed.json'), JSON.stringify({ sequence: before }), { flag: 'wx' });

    let resumed = false;
    const until = Date.now() + 15000;
    while (Date.now() < until) {
      const readiness = await get(sessionPath + '/readiness');
      const player = readiness.players.find(row => row.playerId === playerId);
      if (readiness.sourceState === 'Fresh' && player?.canParticipate && player.rigKind === 'Tracked') {
        resumed = true;
        break;
      }
      await delay(120);
    }
    assert.ok(resumed, 'The original tracked seat did not recover');
    const back = page.locator('#world-recent');
    assert.equal(await back.textContent(), '返回即時觀戰');
    await back.click();
    await waitForLiveFrame(page, before);
    const after = Number(await canvas.getAttribute('data-sequence'));
    const live = (await get(sessionPath + '/world/frames/' + after)).packet;
    assert.equal(live.observedSequence, initial.sequence);
    assert.ok(live.frame.players.some(player => player.id === playerId && player.connected && player.rig.kind === 'Tracked'));
    assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
    assert.equal(await page.locator('#world-room').inputValue(), String(roomId));
    assert.equal(await canvas.getAttribute('data-camera'), camera);
    assert.equal((await get(sessionPath)).sequence, initial.sequence);
    assert.deepEqual(watches, [{ path: sessionPath + '/world/watch', mode: 'replay', from: String(before), through: String(before) },
      { path: sessionPath + '/world/watch', mode: 'live', from: null, through: null }]);
    assert.deepEqual(writes, []);
    assert.deepEqual(errors, []);
    await page.locator('#world-player').screenshot({ path: path.join(out, 'live.png') });
    await fs.writeFile(path.join(out, 'checks.json'), JSON.stringify({ complete: true, sessionId, streamId, roomId, seat, before, after }, null, 2), { flag: 'wx' });
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.name + ': native pose review failed'); process.exitCode = 1; });
