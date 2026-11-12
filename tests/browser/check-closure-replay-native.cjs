const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const readCsv = require('./csv.cjs');

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const { base, token, roomId, recording, output } = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const { sessionId, streamId } = recording.header;
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    await page.locator('#include-ended').check();
    await page.locator('#session-select').selectOption(sessionId);
    const reply = page.waitForResponse(response => new URL(response.url()).pathname === `/api/sessions/${sessionId}/world/watch`);
    await page.getByRole('button', { name: '回放原場次', exact: true }).and(page.locator('#open-closure-replay')).click();
    const response = await reply;
    assert.equal(response.status(), 200);
    const replay = new URL(response.url()), query = replay.searchParams;
    assert.equal(query.get('mode'), 'replay');
    assert.equal(query.get('fromFrame'), '1');
    assert.equal(query.get('observerRoomId'), String(roomId));
    assert.equal(query.has('throughFrame'), false);
    const canvas = page.locator('#world-canvas');
    await page.waitForFunction(tail => Number(document.querySelector('#world-canvas').dataset.sequence) === tail,
      recording.acceptedSequence, { polling: 100 });
    assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
    assert.deepEqual(await page.locator('#world-room option').evaluateAll(options => options.map(option => option.value)), [String(roomId)]);
    assert.equal(await page.locator('#world-camera').inputValue(), 'top');
    assert.match(await page.locator('#world-status').innerText(), new RegExp(`僅接收房間 ${roomId}`));
    assert.equal(await canvas.getAttribute('data-sequence'), String(recording.acceptedSequence));
    assert.deepEqual(errors, []);
    // Read the same authenticated projection separately. Chromium does not
    // always retain a completed SSE response body for Network.getResponseBody.
    query.set('rate', '4');
    const captured = await fetch(replay, { headers: { Authorization: 'Bearer ' + token }, signal: AbortSignal.timeout(20000) });
    assert.equal(captured.status, 200);
    const records = (await captured.text()).trim().split('\n\n').map(block => {
      const lines = block.split('\n');
      return { event: lines.find(line => line.startsWith('event: '))?.slice(7),
        data: JSON.parse(lines.find(line => line.startsWith('data: ')).slice(6)) };
    });
    const first = records[0], last = records.at(-1);
    assert.equal(first.event, 'header');
    assert.equal(last.event, 'complete');
    for (const { data } of [first, last]) {
      assert.equal(data.header.sessionId, sessionId);
      assert.equal(data.header.streamId, streamId);
      assert.equal(data.acceptedSequence, recording.acceptedSequence);
      assert.equal(data.complete, true);
      assert.equal(data.observerRoomId, roomId);
      assert(data.header.props.length > 0 && data.header.props.every(prop => prop.roomId === roomId));
    }
    const frames = records.filter(row => row.event === 'frame').map(row => row.data);
    assert.equal(frames.length, recording.acceptedSequence);
    assert(frames.some(({ packet }) => packet.frame.players.length && packet.frame.enemies.length));
    for (const [index, { packet, statistics, observerRoomId }] of frames.entries()) {
      assert.equal(observerRoomId, roomId);
      assert.equal(packet.sequence, index + 1);
      assert([...packet.frame.players, ...packet.frame.enemies, ...statistics].every(row => row.roomId === roomId));
    }
    assert.equal(frames.at(-1).packet.frame.phase, 'Ended');
    await page.locator('#world-player').screenshot({ path: path.join(path.dirname(output), path.basename(output, '.json') + '.png') });
    const wanted = frames.flatMap(({ packet }) => {
      const matchCount = packet.events.filter(event => event.kind === 'PlayerDamaged').length;
      return matchCount ? [{ frameSequence: packet.sequence, elapsedMilliseconds: packet.elapsedMilliseconds, matchCount }] : [];
    });
    if (recording.header.roomIds.length === 1) assert(wanted.length > 0);
    const waitForRoute = suffix => page.waitForResponse(reply => {
      const url = new URL(reply.url());
      return url.pathname === `/api/sessions/${sessionId}/world/${suffix}` && url.searchParams.get('observerRoomId') === String(roomId);
    });
    await page.locator('#world-event-kind').selectOption('PlayerDamaged');
    const eventPath = `**/api/sessions/${sessionId}/world/event-frames?*`;
    await page.route(eventPath, async route => {
      const original = await route.fetch();
      await route.fulfill({ response: original, json: { ...(await original.json()), observerRoomId: roomId % 5 + 1 } });
    }, { times: 1 });
    await page.locator('#world-event-search-start').click();
    await page.locator('#world-event-search-status').filter({ hasText: '搜尋失敗' }).waitFor();
    assert.equal(await page.locator('#world-event-search-results button').count(), 0);
    const searchReply = waitForRoute('event-frames');
    await page.locator('#world-event-search-start').click();
    const search = await (await searchReply).json();
    assert.equal(search.observerRoomId, roomId);
    assert.deepEqual(search.frames, wanted.filter(hit => hit.frameSequence <= search.scannedThroughFrame).slice(0, 24));
    const neighborReply = waitForRoute('event-neighbor');
    await page.locator('#world-event-previous').click();
    const neighbor = await (await neighborReply).json();
    assert.equal(neighbor.observerRoomId, roomId);
    const previous = wanted.filter(hit => hit.frameSequence < recording.acceptedSequence).at(-1) ?? null;
    assert.deepEqual(neighbor.frame, previous);
    if (previous) {
      await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence,
        previous.frameSequence);
    }
    let clip = null;
    if (search.frames.length) {
      const [firstHit] = search.frames;
      const frameReply = waitForRoute(`frames/${firstHit.frameSequence}`);
      await page.locator('#world-event-search-results button').first().click();
      assert.equal((await (await frameReply).json()).observerRoomId, roomId);
      await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence,
        firstHit.frameSequence);
      const from = firstHit.frameSequence, through = from + 1;
      if (through <= recording.acceptedSequence) {
        await page.locator('#world-clip-start').click();
        await page.locator('#world-frame-next').click();
        await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence, through);
        await page.locator('#world-clip-end').click();
        const metricsReply = page.waitForResponse(reply => new URL(reply.url()).pathname.endsWith('/world/clip-statistics'));
        await page.locator('#world-clip-stats-read').click();
        const metrics = await (await metricsReply).json();
        assert.equal(metrics.roomId, roomId);
        assert.equal(metrics.fromFrame, from);
        assert.equal(metrics.throughFrame, through);
        assert(metrics.players.some(row => row.hitsReceived > 0) && metrics.players.every(row => row.roomId === roomId));
        const csvPath = `**/api/sessions/${sessionId}/world/clip-statistics.csv?*`;
        await page.route(csvPath, async route => {
          const original = await route.fetch();
          const bytes = await original.body();
          const altered = Buffer.from(bytes.toString('utf8').replace(streamId, '00000000-0000-0000-0000-000000000000'));
          assert(!bytes.equals(altered));
          await route.fulfill({ response: original, body: altered });
        }, { times: 1 });
        const refused = Promise.race([
          page.waitForEvent('download').then(() => false),
          page.locator('#world-clip-stats-export-status').filter({ hasText: '無法下載片段戰績' }).waitFor().then(() => true)
        ]);
        await page.locator('#world-clip-stats-export').click();
        assert(await refused, 'A same-type CSV from another stream must not download');
        assert(await page.locator('#world-clip-stats-results').isVisible());
        const download = page.waitForEvent('download');
        await page.locator('#world-clip-stats-export').click();
        const file = await download;
        const target = path.join(path.dirname(output), path.basename(output, '.json') + '-damage.csv');
        await file.saveAs(target);
        const rows = readCsv(await fs.readFile(target));
        assert(rows.length && rows.every(row => row.reportRoomId === String(roomId) && row.playerRoomId === String(roomId)));
        clip = { from, through, roomId, rows: rows.length, refusedForeignStream: true };
      }
    }
    await fs.writeFile(output, JSON.stringify({ sessionId, streamId, roomId, fromFrame: frames[0].packet.sequence,
      throughFrame: frames.at(-1).packet.sequence, complete: true, projectedFrames: frames.length,
      visibleRooms: [roomId], terminalPhase: frames.at(-1).packet.frame.phase,
      projectedDamageFrames: wanted, previousDamageFrame: neighbor.frame?.frameSequence ?? null,
      rejectedOtherRoomSearch: true, clip }, null, 2), { flag: 'wx' });
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
