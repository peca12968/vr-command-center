const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { createHash, randomUUID } = require('node:crypto');
const { chromium } = require('playwright');
const readCsv = require('./csv.cjs');

async function main() {
  const [descriptor, output] = process.argv.slice(2);
  const config = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(config.base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const results = [], fieldEvidence = [], participation = [], receiptExports = [], debriefSeats = [], debriefCsv = [], debriefReplay = [], debriefAll = [];
  let history, roomReplay, scores, alignment, missionTime, debriefReceipts;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 }, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(config.base + '/console/');
    await page.locator('#login-key').fill(config.masterKey);
    const scoreResponse = config.scores && page.waitForResponse(reply => {
      const url = new URL(reply.url());
      return url.pathname === '/api/venue/closure' && url.searchParams.get('includeScores') === 'true';
    });
    await page.locator('#login-form button').click();
    if (scoreResponse) {
      const response = await scoreResponse;
      const body = await response.json();
      assert.equal(response.status(), 200);
      assert.equal(body.batch.requestId, config.scores.requestId);
      assert.deepEqual(body.scores, config.scores);
      const cells = (label, totals) => [label, totals.players, totals.ammoUsed, totals.shotsHit, totals.kills,
        totals.hitsReceived, totals.damageTaken, totals.accuracyPercent + '%'].map(String);
      const expected = config.scores.rooms.map(room => cells('房間 ' + room.roomId, room.totals));
      expected.push(cells('本批合計', config.scores.total));
      const scoresTable = page.locator('#venue-score-table');
      await scoresTable.waitFor();
      assert.deepEqual(await scoresTable.locator('tbody tr').evaluateAll(rows =>
        rows.map(row => [...row.cells].map(cell => cell.textContent))), expected);
      await scoresTable.screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-scores.png') });
      scores = body.scores;
      if (config.debriefReceipts) {
        assert.deepEqual(body.debriefReceipts, config.debriefReceipts);
        const table = page.locator('#venue-closure-table');
        for (const room of config.debriefReceipts.rooms) {
          const cell = table.locator(`[data-venue-closure-session="${room.sessionId}"] [data-venue-debrief-room="${room.roomId}"]`);
          const label = config.mode === 'linked' ? `房間 ${room.roomId} · ` : '';
          assert.equal(await cell.textContent(), label + `已確認 ${room.confirmedCount}／${room.rosterCount} 席`);
        }
        assert.equal(await table.locator('[data-venue-debrief-room]').count(), config.debriefReceipts.rooms.length);
        await table.screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-debrief-receipts.png') });
        debriefReceipts = body.debriefReceipts;
      }
    }
    async function openReplay(session) {
      const original = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/api/sessions/${session.sessionId}/world/watch`);
      await page.locator(`[data-venue-replay="${session.sessionId}"]`).click();
      const stream = await original, query = new URL(stream.url()).searchParams;
      assert.equal(stream.status(), 200);
      assert.equal(query.get('mode'), 'replay');
      assert.equal(query.get('fromFrame'), '1');
      assert.equal(query.has('throughFrame'), false);
      const canvas = page.locator('#world-canvas[data-sequence]');
      await canvas.waitFor();
      const room = session.roomIds.length === 1 ? String(session.roomIds[0]) : 'all';
      assert.equal(await page.locator('#world-recording').inputValue(), session.sessionId);
      assert.equal(await page.locator('#world-room').inputValue(), room);
      assert.equal(await page.locator('#world-camera').inputValue(), room === 'all' ? 'overview' : 'top');
      const sequence = Number(await canvas.getAttribute('data-sequence'));
      assert(sequence > 0 && sequence <= session.replay.throughSequence);
      return { sessionId: session.sessionId, room, sequence, throughSequence: session.replay.throughSequence };
    }
    async function openParticipation(session) {
      const { worldSequence: sequence, elapsedMilliseconds } = session.participationBegin.frame;
      const stream = page.waitForResponse(response => {
        const url = new URL(response.url());
        return url.pathname === `/api/sessions/${session.sessionId}/world/watch` && url.searchParams.get('mode') === 'replay'
          && url.searchParams.get('fromFrame') === String(sequence) && url.searchParams.get('throughFrame') === String(sequence);
      });
      await page.locator(`[data-venue-participation-begin="${session.sessionId}"]`).click();
      assert.equal((await stream).status(), 200);
      const count = session.roomIds.length * 5;
      await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${sequence} 格的有效姿態開場快照。 此格追蹤 0 席、合成 ${count} 席` }).waitFor();
      assert.equal(await page.locator('#world-canvas').getAttribute('data-sequence'), String(sequence));
      const room = session.roomIds.length === 1 ? String(session.roomIds[0]) : 'all';
      assert.equal(await page.locator('#world-recording').inputValue(), session.sessionId);
      assert.equal(await page.locator('#world-room').inputValue(), room);
      assert.equal(await page.locator('#world-camera').inputValue(), room === 'all' ? 'overview' : 'top');
      assert.equal(await page.locator('#world-actor option[value^="p:"]').count(), count);
      assert.match(await page.locator('#world-status').innerText(), /錄製已核對封存 · 準備中/);
      assert.ok((await page.locator('#world-time').innerText()).startsWith((elapsedMilliseconds / 1000).toFixed(2) + ' 秒'));
      if (!participation.length) await page.locator('#world-player').screenshot({ path: path.join(path.dirname(output), config.mode + '-participation-begin.png') });
      await page.locator('#world-frame-next').click();
      await page.locator(`#world-canvas[data-sequence="${sequence + 1}"]`).waitFor();
      return { sessionId: session.sessionId, room, sequence, next: sequence + 1, simulatedPlayers: count };
    }
    async function reviewInterval(replay) {
      const canvas = page.locator('#world-canvas');
      await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('執行中'), null, { polling: 50 });
      await page.locator('#world-pause').click();
      const start = Number(await canvas.getAttribute('data-sequence')), end = start + 1;
      assert(start > 0 && end < replay.throughSequence);
      await page.locator('#world-clip-start').click();
      await page.locator('#world-frame-next').click();
      await page.waitForFunction(sequence => document.querySelector('#world-canvas').dataset.sequence === String(sequence), end, { polling: 50 });
      await page.locator('#world-clip-end').click();
      const bounded = page.waitForResponse(response => {
        const url = new URL(response.url());
        return url.pathname === `/api/sessions/${replay.sessionId}/world/watch`
          && url.searchParams.get('fromFrame') === String(start) && url.searchParams.get('throughFrame') === String(end);
      });
      await page.locator('#world-clip-play').click();
      assert.equal((await bounded).status(), 200);
      await page.locator('#world-clip-status').filter({ hasText: '已到片段終點' }).waitFor();
      assert.equal(Number(await canvas.getAttribute('data-sequence')), end);
      assert.equal(await page.locator('#world-room').inputValue(), replay.room);
      assert.equal(await page.locator('#world-frame-next').isEnabled(), true);
      assert.match(await page.locator('#world-status').innerText(), /錄製已核對封存/);
      const original = await fetch(`${config.base}/api/sessions/${replay.sessionId}/world/frames/${end}`,
        { headers: { Authorization: 'Bearer ' + config.masterKey } });
      assert.equal(original.status, 200);
      const { packet } = await original.json();
      assert.equal(packet.sequence, end);
      assert.equal(packet.frame.phase, 'Running');
      assert((await page.locator('#world-time').innerText()).startsWith((packet.elapsedMilliseconds / 1000).toFixed(2) + ' 秒'));
      await page.locator('#world-clip').screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-interval.png') });
      await page.locator('#saved-clip-name').fill('原生場次複盤');
      await page.locator('#saved-clip-save').click();
      const savedOption = page.locator('#saved-clip-select option').filter({ hasText: '原生場次複盤' });
      await savedOption.waitFor({ state: 'attached' });
      await page.locator('#world-clip-clear').click();
      await page.locator('#saved-clip-load').click();
      assert((await page.locator('#world-clip-status').innerText()).includes(`起點 第 ${start} 格`));
      await page.locator('#world-clip-play').click();
      await page.locator('#world-clip-status').filter({ hasText: '已到片段終點' }).waitFor();
      assert.equal(Number(await canvas.getAttribute('data-sequence')), end);
      const started = page.waitForEvent('download');
      await page.locator('#saved-clip-export').click();
      const download = await started;
      const bytes = await fs.readFile(await download.path());
      const exported = JSON.parse(bytes);
      assert.equal(exported.header.sessionId, replay.sessionId);
      assert.deepEqual(exported.packets[1], packet);
      const first = await fetch(`${config.base}/api/sessions/${replay.sessionId}/world/frames/${start}`,
        { headers: { Authorization: 'Bearer ' + config.masterKey } });
      assert.equal(first.status, 200);
      assert.deepEqual(exported.packets, [(await first.json()).packet, packet]);
      const player = await browser.newPage({ viewport: { width: 390, height: 844 } });
      const apiRequests = [];
      player.on('request', request => {
        if (new URL(request.url()).pathname.startsWith('/api')) apiRequests.push(request.url());
      });
      try {
        await player.goto(config.base + '/console/player-replay.html');
        await player.locator('#player-replay-file').setInputFiles({
          name: download.suggestedFilename(), mimeType: 'application/json', buffer: bytes
        });
        const position = player.locator('#player-replay-frame');
        await position.filter({ hasText: `第 ${start} 格` }).waitFor();
        await player.locator('#player-replay-play').click();
        await position.filter({ hasText: `第 ${end} 格` }).waitFor();
        assert.equal(await player.locator('#player-replay-next').isDisabled(), true);
        assert.deepEqual(apiRequests, []);
        await player.screenshot({ path: path.join(path.dirname(output), config.mode + '-player-replay.png') });
      } finally {
        await player.close();
        await page.bringToFront();
      }
      return { start, end, reached: Number(await canvas.getAttribute('data-sequence')), elapsedMilliseconds: packet.elapsedMilliseconds,
        clipId: await savedOption.getAttribute('value'), playerReplay: { start, end, originalPackets: exported.packets.length, apiRequests: apiRequests.length } };
    }
    async function reviewMissionTime(replay) {
      const panel = page.locator('#world-venue-review');
      if (config.mode === 'linked') {
        assert.equal(await panel.isHidden(), true);
        return { hidden: true };
      }
      const { requestId, targetSessionId, targetRoom, targetTimeline } = config.missionTime;
      const original = async (id, sequence) => {
        const received = await fetch(`${config.base}/api/sessions/${id}/world/frames/${sequence}`, {
          headers: { Authorization: 'Bearer ' + config.masterKey } });
        assert.equal(received.status, 200);
        return received.json();
      };
      const canvas = page.locator('#world-canvas');
      let sequence = Number(await canvas.getAttribute('data-sequence'));
      let source = await original(replay.sessionId, sequence);
      for (let attempt = 0; source.packet.frame.tick === 0 && attempt < 20; attempt++) {
        await page.locator('#world-frame-next').click();
        await page.locator(`#world-canvas[data-sequence="${++sequence}"]`).waitFor();
        source = await original(replay.sessionId, sequence);
      }
      const fromTick = source.packet.frame.tick;
      assert.ok(fromTick > 0 && fromTick <= targetTimeline.at(-1)[1]);
      const floor = targetTimeline.findLast(([, tick]) => tick <= fromTick)?.[1];
      assert.ok(floor > 0 && fromTick - floor <= 10);
      const expectedSequence = targetTimeline.find(([, tick]) => tick === floor)[0];
      await page.locator('#world-venue-basis').selectOption('tick');
      const match = page.waitForResponse(reply => new URL(reply.url()).pathname === `/api/venue/closure/${requestId}/replay-at-tick`);
      await page.locator(`[data-venue-align-room="${targetRoom}"]`).click();
      const response = await match;
      assert.equal(response.status(), 200);
      const body = await response.json();
      assert.deepEqual([body.requestId, body.fromSessionId, body.fromFrame, body.fromTick, body.roomId, body.frameTick],
        [requestId, replay.sessionId, sequence, fromTick, targetRoom, floor]);
      assert.deepEqual(body.frame, await original(targetSessionId, expectedSequence));
      await page.locator('#world-venue-message').filter({ hasText: '已對齊房間 ' + targetRoom }).waitFor();
      assert.equal(await page.locator('#world-recording').inputValue(), targetSessionId);
      assert.equal(await canvas.getAttribute('data-sequence'), String(expectedSequence));
      assert.equal(await page.locator('#world-clip-play').isDisabled(), true);
      await panel.screenshot({ path: path.join(path.dirname(output), 'independent-venue-mission-time.png') });
      return { requestId, fromSessionId: replay.sessionId, toSessionId: targetSessionId,
        fromFrame: sequence, toFrame: expectedSequence, fromTick, frameTick: floor };
    }
    async function reviewRoom(replay) {
      const roomId = 3;
      const originals = JSON.parse(await fs.readFile(config.roomReplaySource, 'utf8'));
      const rooms = new Map(originals.at(-1).statistics.map(player => [player.playerId, player.roomId]));
      const local = event => rooms.get(event.playerId) === roomId;
      const own = originals.find(row => row.packet.events.some(local));
      const other = originals.find(row => row.packet.events.some(event => !local(event)));
      assert.ok(own && other);
      const start = Math.min(own.packet.sequence, other.packet.sequence) - 1;
      const end = Math.max(own.packet.sequence, other.packet.sequence);
      assert.ok(start >= 1 && end > start && end - start < 300);
      const world = `${config.base}/api/sessions/${replay.sessionId}/world`, headers = { Authorization: 'Bearer ' + config.masterKey };
      const response = await fetch(world, { headers });
      assert.equal(response.status, 200);
      const { header } = await response.json();
      assert.deepEqual(header.roomIds, [1, 2, 3, 4, 5]);
      const clipId = randomUUID(), clipName = '原生第三房複盤';
      const saved = await fetch(`${world}/clips/${clipId}`, { method: 'PUT', headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ streamId: header.streamId, name: clipName, startFrame: start, endFrame: end }) });
      assert.equal(saved.status, 200);
      await page.locator('#saved-clip-refresh').click();
      await page.locator('#saved-clip-select').selectOption(clipId);
      const picker = page.locator('#saved-clip-export-room');
      assert.deepEqual(await picker.locator('option').evaluateAll(rows => rows.map(row => row.value)), ['', '1', '2', '3', '4', '5']);
      await picker.selectOption(String(roomId));
      const reply = page.waitForResponse(value => value.url() === `${world}/clips/${clipId}/player-replay.json?roomId=${roomId}`);
      const pending = page.waitForEvent('download');
      await page.locator('#saved-clip-export').click();
      assert.equal((await reply).status(), 200);
      const download = await pending;
      assert.equal(download.suggestedFilename(), `vr-command-replay-${clipId}-room-03.json`);
      const bytes = await fs.readFile(await download.path()), result = JSON.parse(bytes);
      const source = originals.slice(start - 1, end).map(row => row.packet);
      const packets = source.map(({ observedSequence, throughCombatSequence, frame, events, ...packet }) => {
        const { throughSequence, roomEnemyPolicies, players, enemies, ...scene } = frame;
        const policy = roomEnemyPolicies?.find(row => row.roomId === roomId);
        return { ...packet, frame: { ...scene, behavior: policy?.behavior ?? scene.behavior,
          autoAttack: policy?.autoAttack ?? scene.autoAttack, players: players.filter(player => player.roomId === roomId),
          enemies: enemies.filter(enemy => enemy.roomId === roomId) },
          events: events.filter(local).map(({ sequence, ...event }) => event) };
      });
      const props = header.props.filter(prop => prop.roomId === roomId);
      assert.equal(header.props.length, 5);
      assert.deepEqual(result.header, { ...header, roomIds: [roomId], props });
      assert.equal(result.playerReplayVersion, 2);
      assert.equal(result.roomId, roomId);
      assert.deepEqual([result.startFrame, result.endFrame], [start, end]);
      assert.deepEqual(result.packets, packets);
      const retainedEvents = packets.reduce((total, packet) => total + packet.events.length, 0);
      const omittedEvents = source.reduce((total, packet) => total + packet.events.length, 0) - retainedEvents;
      assert.ok(retainedEvents > 0 && omittedEvents > 0);
      for (const room of header.props.filter(prop => prop.roomId !== roomId)) assert.ok(!bytes.includes(room.id));
      for (const [id, room] of rooms) if (room !== roomId) assert.ok(!bytes.includes(id));
      const player = await browser.newPage({ viewport: { width: 390, height: 844 } }), apiRequests = [];
      player.on('request', request => {
        if (new URL(request.url()).pathname.startsWith('/api') || request.headers().authorization) apiRequests.push(request.url());
      });
      try {
        await player.goto(config.base + '/console/player-replay.html');
        await player.locator('#player-replay-file').setInputFiles({ name: download.suggestedFilename(), mimeType: 'application/json', buffer: bytes });
        const position = player.locator('#player-replay-frame');
        await position.filter({ hasText: `第 ${start} 格` }).waitFor();
        assert.match(await player.locator('#player-replay-source').textContent(), /僅房間 3/);
        assert.deepEqual(await player.locator('#player-replay-room option').evaluateAll(rows => rows.map(row => row.value)), ['3']);
        await player.locator('#player-replay-play').click();
        await position.filter({ hasText: `第 ${end} 格` }).waitFor();
        assert.equal(await player.locator('#player-replay-next').isDisabled(), true);
        assert.deepEqual(apiRequests, []);
        await player.screenshot({ path: path.join(path.dirname(output), 'linked-player-room-03.png') });
      } finally { await player.close(); await page.bringToFront(); }
      const damaged = originals.at(-1).statistics.find(player => player.roomId === roomId && player.hitsReceived > 0);
      assert.ok(damaged);
      const damageEvents = row => row.packet.events.filter(event => event.kind === 'PlayerDamaged' && event.playerId === damaged.playerId);
      const latest = originals.findLast(row => damageEvents(row).length);
      assert.ok(latest && latest.packet.sequence < replay.throughSequence);
      const center = latest.packet;
      const nearby = originals.map(row => row.packet).filter(packet => packet.sequence >= center.sequence - 149
        && packet.sequence <= center.sequence + 150 && Math.abs(packet.elapsedMilliseconds - center.elapsedMilliseconds) <= 5000);
      const mark = ({ sequence, elapsedMilliseconds }) => ({ sequence, elapsedMilliseconds });
      const contextStart = mark(nearby[0]), contextEnd = mark(nearby.at(-1));
      const review = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
      const writes = [];
      let clipStatistics, clipCsv;
      review.on('request', request => {
        if (new URL(request.url()).pathname.startsWith('/api/') && request.method() !== 'GET') writes.push(request.method());
      });
      try {
        await review.goto(config.base + '/console/');
        await review.locator('#login-key').fill(config.roomReviewKey);
        await review.locator('#login-form button').click();
        await review.locator('#include-ended').check();
        await review.locator('#session-select').selectOption(replay.sessionId);
        await review.locator('#player-review-select').selectOption(damaged.playerId);
        const neighbor = review.waitForRequest(request => new URL(request.url()).pathname === new URL(world).pathname + '/event-neighbor');
        const exact = review.waitForResponse(reply => new URL(reply.url()).pathname === new URL(world).pathname + `/frames/${latest.packet.sequence}`);
        await review.locator('#open-player-damage').click();
        const query = new URL((await neighbor).url()).searchParams;
        assert.deepEqual(['roomId', 'playerId', 'kind', 'direction', 'fromFrame', 'throughFrame'].map(field => query.get(field)),
          [String(roomId), damaged.playerId, 'PlayerDamaged', 'previous', String(replay.throughSequence), String(replay.throughSequence)]);
        assert.deepEqual(await (await exact).json(), latest);
        await review.locator('#world-event-search-status').filter({ hasText: `已跳到第 ${latest.packet.sequence} 格` }).waitFor();
        assert.equal(await review.locator('#world-room').inputValue(), String(roomId));
        assert.equal(await review.locator('#world-events tr').count(), damageEvents(latest).length);
        await review.locator('#world-review').screenshot({ path: path.join(path.dirname(output), 'linked-room-03-latest-damage.png') });
        const contextReply = review.waitForResponse(reply => new URL(reply.url()).pathname === new URL(world).pathname + '/frame-context');
        await review.locator('#world-event-context').click();
        const resolved = await contextReply;
        assert.equal(resolved.headers()['cache-control'], 'no-store');
        assert.deepEqual(await resolved.json(), { sessionId: replay.sessionId, streamId: header.streamId, throughFrame: replay.throughSequence,
          center: mark(center), start: contextStart, end: contextEnd });
        await review.locator('#world-event-context-status').filter({ hasText: `包含事件第 ${center.sequence} 格` }).waitFor();
        const canvas = review.locator('#world-canvas');
        assert.equal(Number(await canvas.getAttribute('data-sequence')), center.sequence);
        const statsReply = review.waitForResponse(reply => new URL(reply.url()).pathname === new URL(world).pathname + '/clip-statistics');
        await review.locator('#world-clip-stats-read').click();
        const statsResponse = await statsReply;
        assert.equal(statsResponse.status(), 200);
        assert.equal(statsResponse.headers()['cache-control'], 'no-store');
        clipStatistics = await statsResponse.json();
        const included = originals.filter(row => row.packet.sequence >= contextStart.sequence && row.packet.sequence <= contextEnd.sequence)
          .flatMap(damageEvents);
        assert.deepEqual(clipStatistics, { sessionId: replay.sessionId, streamId: header.streamId,
          fromFrame: contextStart.sequence, throughFrame: contextEnd.sequence, roomId, playerId: damaged.playerId,
          players: [{ playerId: damaged.playerId, name: damaged.name, roomId, ammoUsed: 0, shotsHit: 0, kills: 0,
            hitsReceived: included.length, damageTaken: included.reduce((sum, event) => sum + event.damage, 0), matchedShots: 0,
            accuracyPercent: null }] });
        const clipTable = review.locator('#world-clip-stats-results');
        await clipTable.waitFor();
        const displayed = [String(roomId), damaged.name, '0', '0', '0', String(included.length), String(clipStatistics.players[0].damageTaken)];
        if (await clipTable.getByRole('columnheader', { name: '計入命中率', exact: true }).count()) displayed.push('0');
        assert.deepEqual(await clipTable.locator('tbody td').allTextContents(), [...displayed, '—']);
        if (config.checkClipStatisticsCsv) {
          assert.equal(displayed.length, 8);
          const reply = review.waitForResponse(response => new URL(response.url()).pathname === new URL(world).pathname + '/clip-statistics.csv');
          const started = review.waitForEvent('download');
          await review.locator('#world-clip-stats-export').click();
          const csvReply = await reply, file = await started, raw = await fs.readFile(await file.path());
          const query = new URL(csvReply.url()).searchParams;
          assert.equal(csvReply.status(), 200);
          assert.equal(csvReply.headers()['cache-control'], 'no-store');
          assert.deepEqual([query.get('fromFrame'), query.get('throughFrame'), query.get('streamId'), query.get('roomId'), query.get('playerId')],
            [String(contextStart.sequence), String(contextEnd.sequence), header.streamId, '3', damaged.playerId]);
          const binaryReply = await fetch(csvReply.url(), { headers: { Authorization: 'Bearer ' + config.roomReviewKey } });
          assert.equal(binaryReply.status, 200);
          assert.equal(raw.subarray(0, 3).toString('hex'), 'efbbbf');
          assert.ok(raw.equals(Buffer.from(await binaryReply.arrayBuffer())), 'Downloaded CSV differs from the authorized binary response');
          const expectedName = `vr-command-clip-statistics-v1-${replay.sessionId}-${contextStart.sequence}-${contextEnd.sequence}-room-03-player-${damaged.playerId}.csv`;
          assert.equal(file.suggestedFilename(), expectedName);
          assert.deepEqual(readCsv(raw).map(row => [row.playerId, row.reportRoomId, row.matchedShots, row.accuracyPercent]),
            [[damaged.playerId, '3', '0', '']]);
          await fs.writeFile(path.join(path.dirname(output), 'linked-room-03-clip-statistics.csv'), raw, { flag: 'wx' });
          clipCsv = true;
        }
        assert.equal(Number(await canvas.getAttribute('data-sequence')), center.sequence);
        await review.locator('#world-clip').screenshot({ path: path.join(path.dirname(output), 'linked-room-03-clip-statistics.png') });
        // Setting the rate on a paused replay can start it. Set the value without changing the current frame.
        await review.locator('#world-speed').evaluate(select => { select.value = '4'; });
        const playback = review.waitForRequest(request => {
          const url = new URL(request.url());
          return url.pathname === new URL(world).pathname + '/watch'
            && url.searchParams.get('fromFrame') === String(contextStart.sequence)
            && url.searchParams.get('throughFrame') === String(contextEnd.sequence);
        });
        await review.locator('#world-clip-play').click();
        await playback;
        await review.locator('#world-clip-status').filter({ hasText: '已到片段終點' }).waitFor();
        assert.equal(Number(await canvas.getAttribute('data-sequence')), contextEnd.sequence);
        assert.equal(await review.locator('#world-room').inputValue(), String(roomId));
        assert.equal(await review.locator('#world-event-kind').inputValue(), 'PlayerDamaged');
        assert.equal(await review.locator('#world-review-player-scope').isVisible(), true);
        assert.deepEqual(writes, []);
        await review.locator('#world-review').screenshot({ path: path.join(path.dirname(output), 'linked-room-03-damage-context.png') });
      } finally { await review.close(); await page.bringToFront(); }
      return { roomId, start, end, retainedEvents, omittedEvents, props: props.length, apiRequests: apiRequests.length,
        latestDamage: { frame: latest.packet.sequence, matches: damageEvents(latest).length, managementWrites: writes.length,
          contextStart, contextEnd, clipStatistics, clipCsv } };
    }
    for (const session of config.sessions) {
      if (session.participationBegin) {
        participation.push(await openParticipation(session));
        if (config.alignReplay && !alignment) {
          if (config.mode === 'linked') {
            assert.equal(await page.locator('#world-venue-review').isHidden(), true);
            alignment = { hidden: true };
          } else {
            const roomId = 2, target = config.sessions.find(row => row.roomIds.join() === String(roomId));
            const sourceSequence = participation.at(-1).next;
            const match = page.waitForResponse(reply => new URL(reply.url()).pathname === `/api/venue/closure/${config.alignReplay}/replay-at`);
            await page.locator(`[data-venue-align-room="${roomId}"]`).click();
            const response = await match;
            assert.equal(response.status(), 200);
            const body = await response.json();
            assert.deepEqual([body.requestId, body.fromSessionId, body.fromFrame, body.roomId],
              [config.alignReplay, session.sessionId, sourceSequence, roomId]);
            await page.locator('#world-venue-message').filter({ hasText: '已對齊房間 2' }).waitFor();
            assert.equal(await page.locator('#world-recording').inputValue(), target.sessionId);
            assert.equal(await page.locator('#world-canvas').getAttribute('data-sequence'), String(body.frame.packet.sequence));
            const original = async (id, suffix) => {
              const received = await fetch(`${config.base}/api/sessions/${id}/world${suffix}`, {
                headers: { Authorization: 'Bearer ' + config.masterKey } });
              assert.equal(received.status, 200);
              return received.json();
            };
            const [source, sourceFrame, targetFrame, next] = await Promise.all([
              original(session.sessionId, ''), original(session.sessionId, `/frames/${sourceSequence}`),
              original(target.sessionId, `/frames/${body.frame.packet.sequence}`),
              original(target.sessionId, `/frames/${body.frame.packet.sequence + 1}`)
            ]);
            assert.deepEqual(body.frame, targetFrame);
            assert.equal(body.recording.header.streamId, target.replay.streamId);
            const anchor = Date.parse(source.header.captureStartedAtUtc) + sourceFrame.packet.elapsedMilliseconds;
            const targetStart = Date.parse(body.recording.header.captureStartedAtUtc);
            const gap = anchor - targetStart - targetFrame.packet.elapsedMilliseconds;
            assert.ok(gap >= 0 && gap <= 500 && targetStart + next.packet.elapsedMilliseconds > anchor);
            assert.equal(Date.parse(body.capturedAtUtc), anchor);
            await page.locator('#world-venue-review').screenshot({ path: path.join(path.dirname(output), 'independent-venue-replay-alignment.png') });
            alignment = { requestId: body.requestId, fromSessionId: session.sessionId, toSessionId: target.sessionId,
              fromFrame: sourceSequence, toFrame: targetFrame.packet.sequence, millisecondsBeforeAnchor: gap };
          }
        }
        await page.locator('#tab-operations').click();
      }
      const replay = await openReplay(session);
      if (!results.length) {
        await page.screenshot({ path: path.join(path.dirname(output), config.mode + '-venue-replay.png') });
        replay.interval = await reviewInterval(replay);
        if (config.roomReplaySource) roomReplay = await reviewRoom(replay);
        if (config.missionTime) missionTime = await reviewMissionTime(replay);
      }
      results.push(replay);
      await page.locator('#tab-operations').click();
    }
    for (const { batchId, zip, archived, debrief, debriefSeats: detail, debriefSeatReports: reports } of config.fieldEvidence ?? []) {
      if (archived) {
        await page.locator('#venue-closure-load').click();
        await page.locator('#venue-closure-batch').selectOption(batchId);
      }
      const route = `/api/venue/closure/${batchId}/field-evidence.zip`;
      const response = page.waitForResponse(reply => new URL(reply.url()).pathname === route);
      const started = page.waitForEvent('download');
      await page.locator('#export-venue-field').click();
      const download = await started;
      assert.equal((await response).status(), 200);
      assert.equal(download.suggestedFilename(), `vr-command-venue-field-v1-${batchId}.zip`);
      assert((await fs.readFile(await download.path())).equals(await fs.readFile(zip)));
      fieldEvidence.push(batchId);
      if (debrief) {
        const receiptRoute = `/api/venue/closure/${batchId}/debrief-receipts.json`;
        const receiptResponse = page.waitForResponse(reply => new URL(reply.url()).pathname === receiptRoute);
        const startedReceipt = page.waitForEvent('download');
        await page.locator('#export-venue-debrief').click();
        const receipt = await startedReceipt;
        assert.equal((await receiptResponse).status(), 200);
        assert.equal(receipt.suggestedFilename(), `vr-command-venue-debrief-receipts-v1-${batchId}.json`);
        assert((await fs.readFile(await receipt.path())).equals(await fs.readFile(debrief)));
        receiptExports.push(batchId);
      }
      if (detail) {
        const rooms = [];
        const personal = reports && JSON.parse(await fs.readFile(reports, 'utf8')).findLast(row => row.roomId === 5);
        const panel = page.locator('#venue-debrief-seats'), rows = page.locator('#venue-debrief-seat-rows tr');
        const originalRooms = JSON.parse(await fs.readFile(detail, 'utf8')).sort((a, b) => a.roomId - b.roomId);
        const originalSeats = originalRooms.flatMap(room => room.players.map(player => [String(room.roomId), String(player.seat), player.name, '已確認']));
        const groupRead = page.waitForResponse(reply => new URL(reply.url()).pathname === `/api/venue/closure/${batchId}/debrief-seats`);
        await page.locator('#venue-debrief-all').click();
        assert.deepEqual(await (await groupRead).json(), { version: 1, requestId: batchId, rooms: originalRooms });
        await page.locator('#venue-debrief-seats-status').filter({ hasText: '沒有未確認席位' }).waitFor();
        assert.equal(await rows.count(), 0);
        await page.locator('#venue-debrief-only-missing').uncheck();
        assert.deepEqual(await rows.evaluateAll(items => items.map(row => [...row.cells].slice(0, 4).map(cell => cell.textContent))), originalSeats);
        debriefAll.push({ batchId, seats: originalSeats.length });
        await page.locator('#venue-debrief-seats-close').click();
        for (const expected of originalRooms) {
          const roomId = expected.roomId;
          const route = `/api/venue/closure/${batchId}/rooms/${roomId}/debrief-receipts`;
          const read = page.waitForResponse(reply => new URL(reply.url()).pathname === route);
          await page.locator(`[data-venue-debrief-seats="${roomId}"]`).click();
          const response = await read;
          assert.equal(response.status(), 200);
          assert.equal(new URL(response.url()).searchParams.get('includeScores'), 'true');
          assert.equal(new URL(response.url()).searchParams.get('includePlayerIds'), 'true');
          assert.deepEqual(await response.json(), expected);
          await rows.last().waitFor();
          assert.deepEqual(await rows.evaluateAll(items => items.map(row => [...row.cells].slice(0, 3).map(cell => cell.textContent))),
            expected.players.map(player => [String(player.seat), player.name, '已確認']));
          assert.deepEqual(await rows.evaluateAll(items => items.map(row => [...row.cells].slice(4).map(cell => cell.textContent))),
            expected.players.map(({ score }) => [score.ammoUsed, score.shotsHit, score.kills, score.hitsReceived, score.damageTaken,
              `${score.accuracyPercent}%`, score.health].map(String)));
          if (personal && roomId === personal.roomId) {
            const download = page.waitForEvent('download');
            await page.locator(`[data-venue-debrief-csv="${personal.seat}"]`).click();
            const csv = await download;
            assert.equal(csv.suggestedFilename(), personal.filename);
            assert.equal(createHash('sha256').update(await fs.readFile(await csv.path())).digest('hex'), personal.sha256);
            debriefCsv.push({ batchId, ...personal });
          }
          await page.locator('#venue-debrief-only-missing').check();
          assert.equal(await rows.count(), 0);
          assert.match(await panel.innerText(), /沒有未確認席位/);
          if (personal && roomId === personal.roomId) {
            await page.locator('#venue-debrief-only-missing').uncheck();
            const player = expected.players.find(row => row.seat === personal.seat);
            const world = `/api/sessions/${expected.sessionId}/world`;
            const watch = page.waitForRequest(request => new URL(request.url()).pathname === world + '/watch');
            const findEvents = () => page.waitForResponse(reply => new URL(reply.url()).pathname === world + '/event-frames');
            const search = findEvents();
            await page.locator(`[data-venue-debrief-replay="${player.seat}"]`).click();
            const query = new URL((await watch).url()).searchParams;
            assert.deepEqual([query.get('mode'), query.get('fromFrame')], ['replay', String(expected.worldSequence)]);
            const { sessionId, streamId, worldSequence: throughFrame } = expected, { playerId } = player;
            const pages = [];
            let eventResponse = await search, cursor = 0;
            for (;;) {
              const events = await eventResponse.json();
              const { afterFrame, scannedThroughFrame, nextAfterFrame, frames } = events;
              assert.deepEqual([events.sessionId, events.streamId, events.playerId, events.throughFrame, afterFrame,
                new URL(eventResponse.url()).searchParams.get('roomId')], [sessionId, streamId, playerId, throughFrame, cursor, String(roomId)]);
              pages.push({ afterFrame, scannedThroughFrame, nextAfterFrame: nextAfterFrame ?? null, frames });
              if (frames.length || nextAfterFrame == null) break;
              assert(nextAfterFrame === scannedThroughFrame && nextAfterFrame > cursor && nextAfterFrame < throughFrame);
              cursor = nextAfterFrame;
              const following = findEvents();
              await page.locator('#world-event-search-next').click();
              eventResponse = await following;
            }
            const { frames } = pages.at(-1);
            assert.equal(await page.locator('#world-room').inputValue(), String(roomId));
            assert.match(await page.locator('#world-review-player-name').innerText(), new RegExp(playerId.slice(0, 8)));
            const canvas = page.locator('#world-canvas');
            assert.equal(Number(await canvas.getAttribute('data-sequence')), throughFrame);
            if (frames.length) {
              await page.locator(`#world-event-search-results button[data-frame-sequence="${frames[0].frameSequence}"]`).click();
              await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) === sequence,
                frames[0].frameSequence, { polling: 100 });
              assert.equal(await page.locator('#world-events tr').count(), frames[0].matchCount);
            }
            await page.locator('#world-review').screenshot({ path: path.join(path.dirname(output), `${config.mode}-${batchId}-seat-replay.png`) });
            debriefReplay.push({ batchId, sessionId, roomId, playerId, streamId, throughFrame, pages });
            await page.locator('#tab-operations').click();
          } else {
            await page.locator('#venue-debrief-seats-close').click();
          }
          rooms.push({ roomId, sessionId: expected.sessionId, seats: expected.players.length });
        }
        debriefSeats.push({ batchId, rooms });
      }
    }
    if (config.history) {
      const { batch, zip } = config.history;
      const picker = page.locator('#venue-closure-batch');
      await page.locator('#venue-closure-load').click();
      await picker.selectOption(batch.requestId);
      const older = batch.sessions[2];
      await page.locator(`[data-venue-replay="${older.sessionId}"]`).waitFor();
      const started = page.waitForEvent('download');
      await page.locator('#export-venue-reports').click();
      const download = await started;
      assert.equal(download.suggestedFilename(), `vr-command-venue-reports-v1-${batch.requestId}.zip`);
      assert((await fs.readFile(await download.path())).equals(await fs.readFile(zip)));
      let oldParticipation;
      if (older.participationBegin) {
        oldParticipation = await openParticipation(older);
        await page.locator('#tab-operations').click();
      }
      history = { requestId: batch.requestId, zipMatched: true, ...await openReplay(older), participation: oldParticipation };
      await page.locator('#tab-operations').click();
      assert.equal(await picker.inputValue(), batch.requestId);
    }
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
  await fs.writeFile(output, JSON.stringify({ complete: true, mode: config.mode, results, history, fieldEvidence, roomReplay, participation, scores, alignment, missionTime, debriefReceipts, receiptExports, debriefSeats, debriefCsv, debriefReplay, debriefAll }, null, 2), { flag: 'wx' });
}
main().catch(error => {
  const location = error.stack?.match(/check-venue-replay-native\.cjs:(\d+):(\d+)\)/);
  console.error(error.name + ': native venue replay UI failed' + (location ? ` at ${location[1]}:${location[2]}` : ''));
  process.exitCode = 1;
});
