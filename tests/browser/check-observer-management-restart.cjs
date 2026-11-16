// Serve only the selected console assets from disk. Every API request uses the real listener.
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const { base, output, consoleDirectory, sessionId, streamId, playerIds, observerRoomId, key } = JSON.parse(input);
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.match(sessionId, /^[a-f\d-]{36}$/);
  const index = await fs.readFile(path.join(consoleDirectory, 'index.html'), 'utf8');
  const consoleVersion = index.match(/控制台 v([\d.]+)/)?.[1];
  const moduleBytes = await fs.readFile(path.join(consoleDirectory, 'world-ui.js'));
  assert.ok(consoleVersion);
  const write = async (file, value) => {
    const target = path.join(output, file);
    const temporary = target + '.tmp';
    await fs.writeFile(temporary, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
    await fs.rename(temporary, target);
  };
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1100, height: 850 } });
    await context.route(url => url.origin === base && url.pathname.startsWith('/console/'), async route => {
      const relative = decodeURIComponent(new URL(route.request().url()).pathname.slice('/console/'.length)) || 'index.html';
      const asset = path.resolve(consoleDirectory, relative);
      const inside = path.relative(consoleDirectory, asset);
      if (inside.startsWith('..') || path.isAbsolute(inside)) return route.abort();
      return route.fulfill({ path: asset });
    });
    const page = await context.newPage();
    const watches = [], unexpectedWrites = [], errors = [];
    let navigations = 0;
    page.on('pageerror', error => errors.push(error.name));
    page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });
    const started = performance.now();
    page.on('request', request => {
      const url = new URL(request.url());
      if (url.origin !== base || !url.pathname.startsWith('/api/')) return;
      if (request.method() !== 'GET' && url.pathname !== '/api/mission-layout') unexpectedWrites.push(url.pathname);
      if (url.pathname.endsWith('/world/watch')) watches.push({ pathname: url.pathname, mode: url.searchParams.get('mode'),
        room: url.searchParams.get('observerRoomId'), atMilliseconds: Math.round(performance.now() - started) });
    });
    await page.goto(base + '/console/');
    try { await page.locator('#login-key').fill(key); }
    catch { throw new Error('The published console could not open its login form'); }
    await page.locator('#login-form button').click();
    await page.locator(observerRoomId === 4 ? '[data-watch-room-only="4"]' : '[data-watch-room="4"]').click();
    const canvas = page.locator('#world-canvas');
    const view = () => canvas.evaluate(node => ({ sequence: Number(node.dataset.sequence), camera: node.dataset.camera,
      room: document.querySelector('#world-room').value, session: document.querySelector('#world-recording').value,
      freshness: document.querySelector('#world-freshness').textContent, status: document.querySelector('#world-status').textContent,
      message: document.querySelector('#world-message').textContent }));
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '正在接收快照'
      && document.querySelector('#world-status').textContent.includes('執行中'), null, { polling: 100 });
    const before = await view();
    assert.equal(before.session, sessionId);
    assert.equal(before.room, '4');
    assert.ok(before.camera);
    await write('ready.json', before);
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent === '快照已中斷或過期', null,
      { polling: 50, timeout: 16000 });
    const stale = await view();
    assert.ok(stale.sequence >= before.sequence);
    assert.equal(stale.camera, before.camera);
    await page.waitForFunction(after => {
      const current = Number(document.querySelector('#world-canvas').dataset.sequence);
      return (current > after && document.querySelector('#world-freshness').textContent === '正在接收快照'
        && document.querySelector('#world-status').textContent.includes('執行中'))
        || document.querySelector('#world-message').textContent.includes('；可重新連接。');
    }, stale.sequence, { polling: 100, timeout: 28000 });
    const after = await view();
    const recovered = after.sequence > stale.sequence && after.freshness === '正在接收快照';
    assert.equal(navigations, 1);
    assert.equal(after.session, sessionId);
    assert.equal(after.room, '4');
    assert.equal(after.camera, before.camera);
    assert.ok(watches.length > 1 && watches.every(watch => watch.pathname === `/api/sessions/${sessionId}/world/watch`
      && watch.mode === 'live' && watch.room === (observerRoomId === 4 ? '4' : null)));
    assert.deepEqual(unexpectedWrites, []);
    assert.deepEqual(errors, []);
    if (recovered) {
      const headers = { Authorization: 'Bearer ' + key };
      const world = `${base}/api/sessions/${sessionId}/world`;
      const scope = observerRoomId === 4 ? '?observerRoomId=4' : '';
      const meta = await page.request.get(world + scope, { headers });
      assert.equal(meta.status(), 200);
      const data = await meta.json();
      assert.equal(data.header.streamId, streamId);
      const frame = await page.request.get(`${world}/frames/${after.sequence}${scope}`, { headers });
      assert.equal(frame.status(), 200);
      const dataFrame = await frame.json(), { packet } = dataFrame;
      assert.equal(dataFrame.observerRoomId ?? null, observerRoomId);
      assert.deepEqual(packet.frame.players.map(player => player.id).sort(), [...playerIds].sort());
      assert.ok(packet.frame.players.every(player => player.roomId === 4 && player.connected));
      assert.equal(packet.frame.phase, 'Running');
      assert.equal(packet.suspended, false);
    }
    await write('checks.json', { complete: recovered, consoleVersion, sessionId, streamId, observerRoomId, navigations, before, stale, after,
      worldUiSha256: createHash('sha256').update(moduleBytes).digest('hex'), watches });
    if (!recovered) throw new Error('The original view stopped retrying before the management API recovered');
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
