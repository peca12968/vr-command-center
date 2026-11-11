// Verify the packaged master console against live, original Windows game sources.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const roomOrder = [1, 4, 2, 5, 3];
const statisticsCells = row => [row.name, row.ammoUsed, row.kills, row.damageTaken,
  row.hitsReceived, `${row.accuracyPercent}%`, row.health].map(String);

async function main() {
  const [descriptor, output] = process.argv.slice(2);
  const { base, masterKey, topology, rooms, requireDamage } = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.ok(['Linked', 'Independent'].includes(topology));
  assert.deepEqual(rooms.map(row => row.roomId), [1, 2, 3, 4, 5]);
  assert.equal(new Set(rooms.map(row => row.sessionId)).size, topology === 'Linked' ? 1 : 5);
  await fs.mkdir(output);

  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const samples = [], watches = [], writes = [], errors = [];
  const retired = new Set();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
  try {
    page.on('pageerror', error => errors.push(error.name));
    page.on('request', request => {
      const url = new URL(request.url());
      if (url.origin !== base) return;
      if (request.method() !== 'GET' && url.pathname.startsWith('/api/')) writes.push(`${request.method()} ${url.pathname}`);
      if (url.pathname.endsWith('/world/watch')) watches.push(request);
    });
    page.on('requestfailed', request => retired.add(request));
    page.on('requestfinished', request => retired.add(request));

    async function get(route) {
      const response = await page.request.get(base + '/api' + route, { headers: { Authorization: `Bearer ${masterKey}` } });
      assert.equal(response.status(), 200, route);
      return response.json();
    }

    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(masterKey);
    await page.locator('#login-form button').click();
    await page.locator('#tab-world').click();
    await page.locator('[data-live-room="1"]').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#world-live-rooms button').count(), 5);

    for (const roomId of roomOrder) {
      const { sessionId, streamId, minimumSequence, playerIds } = rooms.find(room => room.roomId === roomId);
      const route = `/sessions/${sessionId}/world`, scope = `observerRoomId=${roomId}`;
      const selector = `[data-live-room="${roomId}"]`;
      const started = page.waitForRequest(request => {
        const url = new URL(request.url());
        return url.pathname === '/api' + route + '/watch' && url.searchParams.get('mode') === 'live'
          && url.searchParams.get('observerRoomId') === String(roomId) && request.method() === 'GET';
      });
      await page.locator(selector).click();
      await started;

      const readScreen = async (after = 0) => {
        const value = await page.waitForFunction(({ roomId, sessionId, after, players, selector }) => {
          const $ = id => document.getElementById(id);
          const sequence = Number($('world-canvas').dataset.sequence);
          const rows = [...$('world-statistics').rows].map(row => [row.dataset.playerId,
            [...row.cells].slice(0, 7).map(cell => cell.textContent)]);
          if (sequence > after && rows.length === players && $('world-recording').value === sessionId
            && $('world-room').value === String(roomId) && $('world-camera').value === 'top'
            && $('world-status').textContent.includes(`僅接收房間 ${roomId}`)
            && $('world-status').textContent.includes('執行中') && $('world-freshness').textContent === '正在接收快照'
            && document.querySelector(selector).getAttribute('aria-pressed') === 'true') return { sequence, rows };
        }, { roomId, sessionId, after, players: playerIds.length, selector }, { polling: 100, timeout: 12000 });
        return value.jsonValue();
      };
      const first = await readScreen();
      const screen = await readScreen(first.sequence);
      const recording = await get(`${route}?${scope}`);
      assert.equal(recording.header.sessionId, sessionId);
      assert.equal(recording.header.streamId, streamId);
      assert.equal(recording.observerRoomId, roomId);
      assert.equal(recording.complete, false);
      assert.ok(recording.acceptedSequence >= screen.sequence);
      assert.ok(recording.header.props.every(prop => prop.roomId === roomId));
      const frame = await get(`${route}/frames/${screen.sequence}?${scope}`);
      assert.equal(frame.observerRoomId, roomId);
      assert.equal(frame.packet.sequence, screen.sequence);
      assert.equal(frame.packet.frame.phase, 'Running');
      assert.ok(frame.packet.frame.tick > 0 && frame.packet.observedSequence >= minimumSequence);
      assert.ok(frame.packet.frame.players.every(player => player.roomId === roomId && player.connected));
      assert.deepEqual(frame.packet.frame.players.map(player => player.id).sort(), [...playerIds].sort());
      assert.deepEqual(frame.statistics.map(player => player.playerId).sort(), [...playerIds].sort());
      assert.ok(frame.statistics.every(player => player.roomId === roomId));
      assert.deepEqual(new Map(screen.rows), new Map(frame.statistics.map(row => [row.playerId, statisticsCells(row)])));
      if (requireDamage) assert.ok(frame.statistics.every(row => row.damageTaken > 0 && row.hitsReceived > 0));
      samples.push({ roomId, sessionId, streamId, firstSequence: first.sequence, sequence: screen.sequence, frame });
    }

    assert.deepEqual(watches.map(request => {
      const url = new URL(request.url());
      return [url.pathname, url.searchParams.get('mode'), Number(url.searchParams.get('observerRoomId'))];
    }), samples.map(row => [`/api/sessions/${row.sessionId}/world/watch`, 'live', row.roomId]));
    assert.equal(watches.filter(request => retired.has(request)).length, 4);
    assert.deepEqual(writes.filter(request => request !== 'POST /api/mission-layout'), []);
    assert.deepEqual(errors, []);
    await page.locator('#world-player').screenshot({ path: path.join(output, 'live-room.png') });
    await page.locator('#world-live-rooms').screenshot({ path: path.join(output, 'room-selector.png') });
    await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify({ complete: true, topology, samples,
      scopedWatches: watches.length, retiredWatches: 4, nonGetRequests: writes }, null, 2), { flag: 'wx' });
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'failure.png'), timeout: 5000 }).catch(() => {});
    throw error;
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
