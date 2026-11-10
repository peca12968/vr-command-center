// Observe the original Linked Windows recording through the packaged console.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const { armLiveWatchFault, cutLiveWatch, waitForLiveFrame } = require('./live-watch-fault.cjs');

async function main() {
  const [descriptor, out] = process.argv.slice(2);
  const { base, roomKey, sessionId, players } = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.equal(players.length, 25);
  await fs.mkdir(out);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const errors = [], requests = [], watches = [];
  const checks = [];
  let recent, reconnect, rowFollow;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    page.on('pageerror', error => errors.push(error.name));
    page.on('request', request => {
      const url = new URL(request.url());
      if (url.origin !== base) return;
      if (request.method() !== 'GET' && url.pathname.startsWith('/api/')) requests.push(`${request.method()} ${url.pathname}`);
      if (url.pathname.endsWith('/world/watch')) watches.push(url.pathname);
    });
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(roomKey);
    await page.locator('#login-form button').click();
    async function sessionRevision() {
      const response = await page.request.get(`${base}/api/sessions/${sessionId}`, { headers: { Authorization: 'Bearer ' + roomKey } });
      assert.equal(response.status(), 200);
      const session = await response.json();
      assert.equal(session.players.length, 25);
      return session.sequence;
    }
    const revision = await sessionRevision();
    await page.locator('[data-watch-room="4"]').click();
    const picker = page.locator('#world-actor'), canvas = page.locator('#world-canvas'), camera = page.locator('#world-camera');
    const forRoom = room => players.filter(player => player.roomId === room);
    const playerOptions = () => picker.locator('option[value^="p:"]').evaluateAll(options => options.map(option => [option.value.slice(2), option.textContent]));
    const enemies = picker.locator('option[value^="e:"]');
    async function checkRoom(room) {
      assert.equal(await page.locator('#world-room').inputValue(), String(room));
      const options = new Map(await playerOptions());
      assert.equal(options.size, 5);
      for (const player of forRoom(room)) assert.ok(options.get(player.id)?.startsWith(`${player.name} · 房間 ${room} · `));
      const names = await page.locator('#world-statistics tr td:first-child').allTextContents();
      assert.deepEqual(names.sort(), forRoom(room).map(player => player.name).sort());
      assert.ok((await enemies.allTextContents()).every(label => label.includes(` · 房間 ${room} · `)));
    }
    await picker.locator(`option[value="p:${forRoom(4)[0].id}"]`).waitFor({ state: 'attached' });
    assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
    await checkRoom(4);
    assert.equal(await camera.inputValue(), 'top');
    checks.push('Original room card scopes named native players, enemies and statistics');
    const following = forRoom(4)[2];
    const rowFollowButton = page.locator(`#world-statistics tr[data-player-id="${following.id}"] button`);
    const overhead = await canvas.getAttribute('data-camera');
    await rowFollowButton.focus();
    const focusedAt = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(after => Number(document.querySelector('#world-canvas').dataset.sequence) >= after + 3,
      focusedAt, { polling: 100 });
    assert.equal(await rowFollowButton.evaluate(button => document.activeElement === button), true);
    const activatedAt = Number(await canvas.getAttribute('data-sequence'));
    await page.keyboard.press('Enter');
    await page.locator('#world-actor-info').filter({ hasText: following.name }).waitFor();
    const position = await canvas.getAttribute('data-camera');
    assert.equal(await picker.inputValue(), 'p:' + following.id);
    assert.equal(await camera.inputValue(), 'follow');
    assert.notEqual(position, overhead);
    assert.deepEqual(watches, [`/api/sessions/${sessionId}/world/watch`]);
    rowFollow = { roomId: 4, focusedAt, activatedAt, withoutNewStream: true };
    checks.push('A focused player row survives newer native frames and follows the exact actor with Enter');
    await page.locator('[data-world-room="2"]').click();
    await checkRoom(2);
    const sequence = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(after => Number(document.querySelector('#world-canvas').dataset.sequence) > after, sequence, { polling: 100 });
    assert.equal(await picker.inputValue(), '');
    assert.equal(await camera.inputValue(), 'free');
    assert.equal(await rowFollowButton.count(), 0);
    assert.notEqual(await canvas.getAttribute('data-camera'), position);
    checks.push('Switching rooms clears the foreign follow target across new native frames');
    await page.locator('#world-player').screenshot({ path: path.join(out, 'room-2.png') });
    await page.locator('[data-world-room="all"]').click();
    assert.equal((await playerOptions()).length, 25);
    assert.ok(await enemies.count() > 0);
    assert.equal(await picker.inputValue(), '');
    assert.deepEqual(watches, [`/api/sessions/${sessionId}/world/watch`]);
    checks.push('All-room list restores 25 names through the original read-only stream');

    await camera.selectOption('top');
    await page.locator('[data-world-room="2"]').click();
    const fixedCamera = await canvas.getAttribute('data-camera');
    await page.locator('#world-speed').selectOption('4');
    await page.waitForFunction(() => !document.querySelector('#world-recent').disabled
      && parseFloat(document.querySelector('#world-time').textContent) > 11, null, { polling: 100 });
    const replayResponse = page.waitForResponse(response => {
      const url = new URL(response.url());
      return url.pathname === `/api/sessions/${sessionId}/world/watch` && url.searchParams.get('mode') === 'replay';
    });
    const tail = await page.evaluate(() => {
      const sequence = Number(document.querySelector('#world-canvas').dataset.sequence);
      document.querySelector('#world-recent').click();
      return sequence;
    });
    const replay = await replayResponse;
    assert.equal(replay.status(), 200);
    const query = new URL(replay.url()).searchParams;
    assert.equal(query.get('throughFrame'), String(tail));
    assert.equal(query.get('rate'), '4');
    // DevTools need not retain a streamed response body. Read the same fixed
    // range independently while asserting the browser reaches its exact tail.
    const [savedReplay] = await Promise.all([
      page.request.get(replay.url(), { headers: { Authorization: 'Bearer ' + roomKey } }),
      page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '已到即時回看尾端', null, { polling: 100 })
    ]);
    assert.equal(savedReplay.status(), 200);
    const events = (await savedReplay.text()).trim().split('\n\n').map(record => {
      const [event, data] = record.split('\n');
      return [event.slice(7), JSON.parse(data.slice(6))];
    });
    const frames = events.filter(([type]) => type === 'frame').map(([, value]) => value.packet);
    const end = frames.at(-1), start = frames[0];
    const from = end.elapsedMilliseconds - 10000;
    assert.equal(query.get('fromMs'), String(from));
    assert.equal(events[0][1].header.sessionId, sessionId);
    assert.equal(events.at(-1)[0], 'saved-end');
    assert.equal(events.at(-1)[1].acceptedSequence, tail);
    assert.equal(end.sequence, tail);
    assert.ok(start.elapsedMilliseconds <= from && frames[1].elapsedMilliseconds > from);
    assert.ok(frames.every((frame, index) => frame.sequence === start.sequence + index));
    await checkRoom(2);
    assert.equal(await canvas.getAttribute('data-camera'), fixedCamera);
    assert.equal(await canvas.getAttribute('data-sequence'), String(tail));
    assert.equal(await page.locator('#world-frame-extend').isVisible(), false);
    await page.locator('#world-player').screenshot({ path: path.join(out, 'recent-tail.png') });
    checks.push('Instant replay seeks the witnessed ten-second window and confirms its exact displayed native tail');
    await armLiveWatchFault(page, sessionId, 'eof');
    await page.getByRole('button', { name: '返回即時觀戰' }).click();
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) > sequence
      && !document.querySelector('#world-recent').disabled && document.querySelector('#world-review').hidden,
    tail, { polling: 100 });
    await checkRoom(2);
    assert.equal(await canvas.getAttribute('data-camera'), fixedCamera);
    assert.equal(await camera.inputValue(), 'top');
    assert.deepEqual(watches, Array(3).fill(`/api/sessions/${sessionId}/world/watch`));
    recent = { streamId: events[0][1].header.streamId, firstFrame: start.sequence, tail, frames: frames.length,
      fromMilliseconds: from, firstMilliseconds: start.elapsedMilliseconds, tailMilliseconds: end.elapsedMilliseconds,
      resumedFrame: Number(await canvas.getAttribute('data-sequence')), roomId: 2 };
    checks.push('Instant replay returns to newer live frames from the same source with room and overhead camera preserved');
    const disconnectedFrame = await cutLiveWatch(page);
    await waitForLiveFrame(page, disconnectedFrame);
    await checkRoom(2);
    assert.equal(await canvas.getAttribute('data-camera'), fixedCamera);
    assert.deepEqual(watches, Array(4).fill(`/api/sessions/${sessionId}/world/watch`));
    reconnect = { disconnectedFrame, recoveredFrame: Number(await canvas.getAttribute('data-sequence')), roomId: 2 };
    checks.push('An EOF on the real native observation response reconnects once without changing room or camera');
    // The operations tab may calculate a read-only draft layout while the browser logs in.
    assert.deepEqual(requests.filter(request => request !== 'POST /api/mission-layout'), []);
    assert.equal(await sessionRevision(), revision);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
  await fs.writeFile(path.join(out, 'checks.json'), JSON.stringify({ complete: true, checks, sessionId, players: 25, rowFollow, recent, reconnect, nonGetRequests: requests }, null, 2), { flag: 'wx' });
}
main().catch(error => { console.error(error); process.exitCode = 1; });
