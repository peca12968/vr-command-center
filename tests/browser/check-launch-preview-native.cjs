// Use an isolated start-desktop-control.py run and its actual Unity processes.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const rooms = [1, 2, 3, 4, 5];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(description, predicate, seconds = 30) {
  const end = Date.now() + seconds * 1000;
  while (Date.now() < end) {
    const result = await predicate();
    if (result) return result;
    await sleep(150);
  }
  throw new Error('Timed out: ' + description);
}

async function verifyRoomView(page, api, route, room) {
  const snapshot = await page.evaluate(() => ({
    sequence: Number(document.querySelector('#world-canvas').dataset.sequence),
    scope: document.querySelector('#world-room').value,
    counts: [...document.querySelectorAll('[data-world-room]')].map(button => [button.dataset.worldRoom,
      button.lastElementChild.textContent, button.getAttribute('aria-pressed')]),
    statistics: [...document.querySelectorAll('#world-statistics tr')].map(row => [...row.cells].map(cell => cell.textContent))
  }));
  assert.equal(snapshot.scope, String(room));
  const exact = await api(`${route}/world/frames/${snapshot.sequence}`);
  const { players, enemies } = exact.packet.frame;
  assert.deepEqual(snapshot.counts, ['all', ...rooms.map(String)].map(id => {
    const localPlayers = players.filter(player => id === 'all' || player.roomId === Number(id));
    const localEnemies = enemies.filter(enemy => id === 'all' || enemy.roomId === Number(id));
    return [id, `連線玩家 ${localPlayers.filter(player => player.connected).length}/${localPlayers.length} · 存活敵軍 ${localEnemies.filter(enemy => enemy.health > 0).length}/${localEnemies.length}`, String(id === String(room))];
  }));
  const statistics = exact.statistics.filter(player => room === 'all' || player.roomId === room);
  assert.deepEqual(snapshot.statistics, statistics.map(p => [p.name, p.ammoUsed, p.kills, p.damageTaken, p.hitsReceived, p.accuracyPercent + '%', p.health].map(String)));
  return { sequence: snapshot.sequence, room, counts: snapshot.counts, statistics };
}

async function main() {
  const readyPath = path.resolve(process.argv[2]);
  const directory = path.dirname(readyPath);
  assert.equal(path.dirname(directory), path.resolve(__dirname, '../../artifacts/desktop-venue'));
  assert.match(path.basename(directory), /^\d{8}-\d{6}-[a-f0-9]{8}$/);
  const ready = await read(readyPath);
  assert.equal(ready.source, 'Simulation');
  assert.equal(ready.headsets, 0);
  assert.match(ready.baseUrl, /^http:\/\/127\.0\.0\.1:(?!5080$)\d+$/);
  assert.equal(ready.consoleUrl, ready.baseUrl + '/console/');
  const key = (await read(path.join(directory, 'keys.json'))).OperatorKeys.Master;
  const headers = { Authorization: 'Bearer ' + key };
  async function api(route, body, status = 200) {
    const response = await fetch(ready.baseUrl + '/api' + route, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', ...(body === undefined ? {} : { 'Idempotency-Key': randomUUID() }) },
      body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(8000)
    });
    assert.equal(response.status, status, route);
    return response.json();
  }

  const definition = { name: '五房夜戰配置', briefing: '守備區回報 <夜戰>\n核對五房配置。', durationSeconds: 120,
    environment: { mode: 'VR', weather: 'Storm', timeOfDay: 'Night', lightning: true },
    enemies: { count: 7, behavior: 'Patrol', autoAttack: false },
    props: [{ assetId: 'sandbag', position: { x: -3, y: 0, z: 0 }, yawDegrees: 15 },
      { assetId: 'barrel', position: { x: -1, y: 0, z: 1.5 }, yawDegrees: 90 }] };
  const original = await api('/missions', definition, 201);
  const revised = await api(`/missions/${original.id}/revisions`, { ...definition, durationSeconds: 180,
    environment: { ...definition.environment, weather: 'Clear', timeOfDay: 'Day', lightning: false }, enemies: { count: 2, behavior: 'Hold', autoAttack: true }, props: [] }, 201);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    page.on('dialog', dialog => dialog.accept());
    await page.goto(ready.consoleUrl);
    await page.locator('#login-key').fill(key);
    await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click();
    await page.locator('#edit-mission').selectOption(revised.id);
    await page.locator('#load-mission').click();
    await page.locator('#mission-version').selectOption(original.id);
    await page.locator('#load-version').click();
    await page.waitForFunction(() => document.querySelector('#draft-duration').value === '120');
    await page.locator('#draft-briefing').fill('未儲存的替代簡報');
    await page.locator('#prop-select').selectOption('0');
    await page.locator('#prop-x').fill('3.5');
    await page.locator('#prop-x').blur();
    assert.equal(await page.locator('#prop-layer [data-index="0"]').getAttribute('transform'), 'translate(3.5 0) rotate(-15)');
    await page.locator('#launch-version').click();
    await page.locator('#launch-mode').selectOption('Linked');
    await page.locator('#launch-preview-briefing summary').click();
    const shown = {};
    for (const item of ['version', 'rooms', 'duration', 'environment', 'enemies', 'props', 'briefing-text']) {
      shown[item] = await page.locator('#launch-preview-' + item).innerText();
    }
    assert.deepEqual(shown, { version: '五房夜戰配置 · 第 1 版（歷史）', rooms: '房間 1、房間 2、房間 3、房間 4、房間 5',
      duration: '120 秒', environment: 'VR · 暴風雨 · 夜晚 · 閃電開啟', enemies: '全場 7 名 · 巡邏 · 自動攻擊關閉',
      props: '每房 2 件 · 沙包 1 · 油桶 1', 'briefing-text': definition.briefing });
    await page.locator('#launch-layout-map-details summary').click();
    const map = await page.evaluate(() => ({
      props: [...document.querySelectorAll('#launch-layout-props [data-index]')].map(group => ({
        index: Number(group.dataset.index), transform: group.getAttribute('transform'),
        asset: group.querySelector('[data-envelope]').dataset.envelope
      })),
      spawns: [...document.querySelectorAll('#launch-layout-spawns [data-seat]')].map(group => ({
        seat: Number(group.dataset.seat), transform: group.getAttribute('transform'), radius: Number(group.querySelector('circle').getAttribute('r'))
      })),
      routes: [...document.querySelectorAll('#launch-layout-routes polyline')].map(line => line.getAttribute('points'))
    }));
    const layout = await api(`/missions/${original.id}/layout?mode=Linked`);
    assert.deepEqual(map.props, definition.props.map((prop, index) => ({ index, asset: prop.assetId,
      transform: `translate(${prop.position.x} ${-prop.position.z}) rotate(${-prop.yawDegrees})` })));
    assert.deepEqual(map.spawns, layout.spawns.map(spawn => ({ seat: spawn.seat, radius: layout.playerRadius,
      transform: `translate(${spawn.x} ${-spawn.z})` })));
    assert.equal(map.routes.length, 5);
    assert.deepEqual(map.routes, layout.routePreview.seats.map(route => route.path.map(point => `${point.x},${-point.z}`).join(' ')));
    await page.screenshot({ path: path.join(directory, 'launch-preview.png'), fullPage: true });
    await page.locator('#create-session-form button').click();
    const session = await until('UI creates the Linked session', async () => (await api('/sessions'))[0]);
    assert.equal(session.mode, 'Linked');
    assert.deepEqual(session.roomIds, rooms);
    assert.deepEqual(session.mission, original);
    await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '準備中');
    for (const room of rooms) {
      const name = 'Preview room ' + room;
      await page.locator('#player-room').selectOption(String(room));
      await page.locator('#player-name').fill(name);
      await page.locator('#join-form button').click();
      await page.locator('#roster tr').filter({ hasText: name }).waitFor();
    }
    const runningPath = path.join(directory, 'operator-' + session.id + '-latest-frame.json');
    const native = async () => read(runningPath).catch(error => { if (error.code !== 'ENOENT') throw error; });
    await until('five native players admitted', async () => {
      const frame = (await native())?.packet.frame;
      return frame?.players.filter(player => player.connected).length === 5;
    }, 100);
    await page.locator('[data-command=Begin]').click();
    const running = await until('actual Running frame', async () => {
      const value = await native();
      return value?.packet.frame.phase === 'Running' && value.packet.frame.tick > 0 && value;
    });
    assert.deepEqual(running.packet.frame.players.filter(player => player.connected).map(player => player.roomId).sort(), rooms);
    assert.equal(running.packet.weather, definition.environment.weather);
    assert.equal(running.packet.lightning, true);
    assert.equal(running.packet.frame.night, true);
    assert.equal(running.packet.frame.behavior, definition.enemies.behavior);
    assert.equal(running.packet.frame.autoAttack, false);
    const enemyCounts = rooms.map(room => running.packet.frame.enemies.filter(enemy => enemy.roomId === room).length);
    assert.deepEqual(enemyCounts, [2, 2, 1, 1, 1]);
    const route = '/sessions/' + session.id;
    const source = (await api(route + '/world')).header;
    assert.equal(source.missionDurationSeconds, definition.durationSeconds);
    assert.deepEqual(source.roomIds, rooms);
    assert.equal(source.props.length, 10);
    for (const room of rooms) {
      const originX = (room - 3) * 14;
      assert.deepEqual(source.props.filter(prop => prop.roomId === room).map(prop => [prop.kind, prop.feet.x - originX, prop.feet.y, prop.feet.z, prop.yaw]),
        [['Sandbag', -3, 0, 0, 15], ['Barrel', -1, 0, 1.5, 90]]);
    }
    await page.locator('#live-auto-attack').check();
    await page.locator('#enemies-form button[type=submit]').click();
    const victim = await until('native AI damages a connected player', async () =>
      (await native())?.statistics.find(player => player.damageTaken > 0));
    await page.locator('#tab-world').click();
    await page.locator('#world-recording').selectOption(session.id);
    await page.locator('#world-live').click();
    await page.waitForFunction(() => document.querySelector('[data-world-room="all"] span')?.textContent.includes('5/5'));
    const full = await verifyRoomView(page, api, route, 'all');
    await page.locator('#world-camera').selectOption('top');
    await page.locator(`[data-world-room="${victim.roomId}"]`).click();
    await page.locator('#world-camera-read').click();
    assert.equal(await page.locator('#world-camera').inputValue(), 'top');
    assert.equal(Number(await page.locator('#world-camera-x').inputValue()), (victim.roomId - 3) * 14);
    assert.ok(Number(await page.locator('#world-camera-elevation').inputValue()) > 80);
    const focused = await verifyRoomView(page, api, route, victim.roomId);
    assert.ok(focused.statistics.some(player => player.damageTaken > 0));
    await page.screenshot({ path: path.join(directory, 'world-room-live.png'), fullPage: true });
    const otherRoom = rooms.find(room => room !== victim.roomId);
    await page.locator('#world-room').selectOption(String(otherRoom));
    const other = await verifyRoomView(page, api, route, otherRoom);
    await page.locator('[data-world-room="all"]').click();
    const restored = await verifyRoomView(page, api, route, 'all');
    assert.equal(restored.statistics.length, 5);
    await page.locator('#tab-operations').click();
    // Let active AI reports settle, then refresh the sequence used by the UI End.
    await until('AI reporting becomes idle', async () => {
      const players = (await native())?.statistics;
      return players?.length === 5 && players.every(player => player.health === 0);
    });
    await page.locator('#refresh').click();
    await page.waitForFunction(() => document.querySelector('#notice').textContent === '已更新。');
    const endResponse = page.waitForResponse(response => response.url() === ready.baseUrl + '/api' + route + '/commands'
      && response.request().method() === 'POST' && response.request().postDataJSON().action === 'End');
    await page.locator('[data-command=End]').click();
    const end = await endResponse;
    assert.equal(end.status(), 200, JSON.stringify(await end.json()));
    const sealed = await until('exact world seal', async () => {
      const world = await api(route + '/world');
      return world.complete && world;
    });
    const final = await api(route);
    assert.deepEqual(sealed.header.props, source.props);
    assert.equal(final.state, 'Ended');
    assert.equal(final.combatStream.sealed, true);
    assert.deepEqual(final.mission, original);
    assert.equal((await api('/sessions')).length, 0);
    await page.locator('#tab-world').click();
    const replayRequest = page.waitForRequest(request => {
      const url = new URL(request.url());
      return url.pathname === '/api' + route + '/world/watch' && url.searchParams.get('mode') === 'replay';
    });
    await page.locator('#world-replay').click();
    await replayRequest;
    await page.locator('#world-speed').selectOption('4');
    await page.locator('[data-world-room="5"]').click();
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence, sealed.acceptedSequence);
    const replay = await verifyRoomView(page, api, route, 5);
    assert.equal(replay.sequence, sealed.acceptedSequence);
    await page.screenshot({ path: path.join(directory, 'world-room-replay.png'), fullPage: true });
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(directory, 'launch-preview-checks.json'), JSON.stringify({
      sessionId: session.id, originalId: original.id, revisedId: revised.id, shown, map, rooms, enemyCounts,
      runningSequence: running.packet.sequence, sealedSequence: sealed.acceptedSequence,
      roomViews: { full, focused, other, restored, replay }, pageErrors: errors, headsets: 0
    }, null, 2), { flag: 'wx' });
    await fs.writeFile(path.join(directory, 'end.request'), '', { flag: 'wx' });
    console.log('PASS: Linked room focus and per-frame statistics match native live and replay snapshots');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error.name + ': ' + error.message); process.exitCode = 1; });
