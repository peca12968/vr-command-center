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
      assert.deepEqual(source.props.filter(prop => prop.roomId === room).map(prop => [prop.kind, prop.yaw]), [['Sandbag', 15], ['Barrel', 90]]);
    }
    await page.locator('[data-command=End]').click();
    const sealed = await until('exact world seal', async () => {
      const world = await api(route + '/world');
      return world.complete && world;
    });
    const final = await api(route);
    assert.equal(final.state, 'Ended');
    assert.equal(final.combatStream.sealed, true);
    assert.deepEqual(final.mission, original);
    assert.equal((await api('/sessions')).length, 0);
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(directory, 'launch-preview-checks.json'), JSON.stringify({
      sessionId: session.id, originalId: original.id, revisedId: revised.id, shown, rooms, enemyCounts,
      runningSequence: running.packet.sequence, sealedSequence: sealed.acceptedSequence, pageErrors: errors, headsets: 0
    }, null, 2), { flag: 'wx' });
    await fs.writeFile(path.join(directory, 'end.request'), '', { flag: 'wx' });
    console.log('PASS: saved historical preview, Linked admission, native initial conditions and dual seal');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error.name + ': ' + error.message); process.exitCode = 1; });
