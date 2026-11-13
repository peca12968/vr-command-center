const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { spawnSync } = require('node:child_process');

const route = '/venue/server-launch-review';
const panel = '#venue-launch-review', input = panel + '-file', button = panel + '-check', summary = panel + '-summary';
const rows = panel + '-rooms li';
const rosterShortcut = roomId => `[data-launch-review-roster="${roomId}"]`;
const replayShortcut = roomId => `[data-launch-review-replay="${roomId}"]`;
const closureShortcut = '[data-launch-review-action="closure"]';
const seatStatus = roomId => `[data-launch-review-seats="${roomId}"]`;
const rosterStatus = panel + '-roster-status';

async function openRoomRoster(page, sessionId, roomId) {
  await page.locator(rosterShortcut(roomId)).click();
  await page.locator(rosterStatus).filter({ hasText: `已開啟房間 ${roomId} 的原場次名冊` }).waitFor();
  assert.equal(await page.locator('#session-select').inputValue(), sessionId);
  assert.equal(await page.locator('#roster-room').inputValue(), String(roomId));
  assert.equal(await page.evaluate(() => document.activeElement.id), 'roster-title');
}

async function openRoomReplay(page, sessionId, roomId, worldSequence) {
  const watch = page.waitForRequest(request => {
    const url = new URL(request.url());
    return url.pathname === `/api/sessions/${sessionId}/world/watch` && url.searchParams.get('mode') === 'replay'
      && url.searchParams.get('fromFrame') === '1';
  });
  await page.locator(replayShortcut(roomId)).click();
  await watch;
  await page.locator('#world-status').filter({ hasText: '錄製已核對封存' }).waitFor();
  await page.locator('#world-canvas[data-sequence]').waitFor();
  assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
  assert.equal(await page.locator('#world-room').inputValue(), String(roomId));
  assert.equal(await page.locator('#world-recording option:checked').getAttribute('data-accepted'), String(worldSequence));
}

async function login(page, base, token) {
  await page.goto(base + '/console/');
  await page.locator('#login-key').fill(token);
  await page.locator('#login-form button').click();
  await page.locator('#rooms .room-card').first().waitFor();
}

async function checkSelected(page) {
  const result = page.waitForResponse(response => response.url().endsWith('/api' + route) && response.request().method() === 'POST');
  await page.locator(button).click();
  return result;
}

function projected(body) {
  assert.deepEqual(Object.keys(body).sort(), ['instanceId', 'launchId', 'servers', 'topology', 'version']);
  for (const server of body.servers) {
    assert.deepEqual(Object.keys(server).sort(), body.version === 3 ? ['roomIds', 'seal', 'sessionId', 'streamId', 'udp']
      : ['roomIds', 'sessionId', 'streamId', 'udp']);
    if (server.udp) assert.deepEqual(Object.keys(server.udp).sort(), body.version === 2 ? ['address', 'bindAddress', 'port'] : ['bindAddress', 'port']);
    if (body.version === 3) {
      assert.equal(server.udp, null);
      assert.deepEqual(Object.keys(server.seal).sort(), ['combatSequence', 'origin', 'worldSequence']);
    }
  }
}

async function choose(page, value) {
  await page.locator(input).setInputFiles({ name: 'launcher-result.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(value)) });
}

async function checkVenueLaunchReview({ context, api, tokens, base, screenshots, check, captureErrors, instanceId }) {
  const page = await context.newPage();
  captureErrors(page);
  const launchId = randomUUID(), streamId = randomUUID();
  const mission = await api('/missions', 'POST', { name: 'Launch review fixture', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const roomIds = [1, 2, 3, 4, 5];
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds }, 'Master', 201);
  const sessionPath = '/sessions/' + session.id;
  let replacement;
  const raw = { schemaVersion: 1, status: 'venue-incomplete', complete: false, readyPublished: false, instanceId,
    venueLaunchId: launchId, topology: 'Linked', sourceAttachment: 'unconfirmed', endpointPublication: 'not-attempted',
    publicationError: 'PRIVATE_FIXTURE_MESSAGE',
    servers: [{ roomIds, result: { sessionId: session.id, streamId: null, udpBinding: null, childPid: 123,
      workDirectory: 'C:/PRIVATE_FIXTURE_DIRECTORY', gameServerKey: 'PRIVATE_FIXTURE_VALUE' } }] };
  const requests = [];
  page.on('request', request => { if (request.url().endsWith('/api' + route)) requests.push(request.postDataJSON()); });
  let release;
  try {
    const target = { version: 1, instanceId, launchId, topology: 'Linked', servers: [{ roomIds, sessionId: session.id, streamId: null, udp: null }] };
    await api(route, 'POST', target, 'Room1', 403);
    await api(route, 'POST', target, 'GameServer', 403);
    await login(page, base, tokens.Room1);
    check(await page.locator(panel).isHidden(), 'Only the master can open the original launch review');
    await login(page, base, tokens.Master);
    await page.locator(panel + ' summary').click();
    await choose(page, { ...raw, readyPublished: true });
    await page.locator(button).click();
    await page.locator(summary).filter({ hasText: '請選擇 64 KiB' }).waitFor();
    check(!requests.length && await page.locator(rows).count() === 0, 'Completed and unsupported reports stay local');
    await choose(page, { ...raw, instanceId: randomUUID() });
    assert.equal((await checkSelected(page)).status(), 409);
    await page.locator(summary).filter({ hasText: '另一個管理實例' }).waitFor();
    check(await page.locator(rows).count() === 0, 'A different instance cannot show a valid room result');
    await choose(page, raw);
    const unbound = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '場次尚未登記來源' }).waitFor();
    projected(requests.at(-1));
    assert.deepEqual(requests.at(-1), target);
    check(unbound.instanceVerified
      && unbound.servers[0].phase === 'Preparing' && (await page.locator(rows).textContent()).includes(session.id),
      'The browser sends only original identities, and shows the exact unbound Preparing session');

    await api('/venue/combat-streams', 'PUT', { version: 1, launchId, topology: 'Linked',
      servers: [{ sessionId: session.id, streamId, origin: 'Simulation', expectedSequence: session.sequence }] }, 'GameServer');
    const before = await api(sessionPath);
    const attached = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '尚未公告端點' }).waitFor();
    check(attached.servers[0].streamId === streamId && (await page.locator(rows).textContent()).includes('已登記本批來源')
      && JSON.stringify(await api(sessionPath)) === JSON.stringify(before), 'An original source can be present without an endpoint and without a new event');
    await page.locator(panel).screenshot({ path: path.join(screenshots, 'venue-launch-review-source.png') });

    const ready = { schemaVersion: 1, status: 'venue-ready', topology: 'Linked', instanceId,
      servers: [{ roomIds, ready: { schemaVersion: 1, status: 'ready', sessionId: session.id, streamId, childPid: 123,
        address: '192.168.1.20', port: 17777, udpBinding: { address: '0.0.0.0', port: 17777, processId: 123 },
        workDirectory: 'C:/PRIVATE_FIXTURE_DIRECTORY' } }] };
    const readyTarget = { version: 2, instanceId, launchId: null, topology: 'Linked',
      servers: [{ roomIds, sessionId: session.id, streamId, udp: { address: '192.168.1.20', bindAddress: '0.0.0.0', port: 17777 } }] };
    await api(route, 'POST', readyTarget, 'Room1', 403);
    await api(route, 'POST', { ...readyTarget, servers: [{ ...readyTarget.servers[0], streamId: null }] }, 'Master', 400);
    await choose(page, ready);
    const missingEndpoint = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '尚未公告端點' }).waitFor();
    projected(requests.at(-1));
    assert.deepEqual(requests.at(-1), readyTarget);
    check(missingEndpoint.servers[0].endpointState === 'not-published', 'A ready file is checked against the API before it can show a matching endpoint');
    const started = Date.now();
    const header = { sessionId: session.id, streamId, origin: 'Simulation', roomIds, missionClockVersion: 1,
      captureStartedAtUtc: new Date(started).toISOString().replace('Z', '0000+00:00'),
      missionDurationSeconds: session.mission.definition.durationSeconds };
    function send(...messages) {
      const result = spawnSync('python', [path.resolve(__dirname, '../../scripts/world_test_socket.py')], {
        encoding: 'utf8', timeout: 6000, windowsHide: true,
        input: JSON.stringify({ port: Number(new URL(base).port), route: `/api${sessionPath}/world/publish`, token: tokens.GameServer,
          messages: [{ type: 'header', payload: header }, ...messages] })
      });
      assert.equal(result.status, 0, result.stderr || result.error?.message);
      return JSON.parse(result.stdout);
    }
    send();
    await api('/venue/connection-endpoints', 'PUT', { version: 1, topology: 'Linked', servers: [{ sessionId: session.id,
      endpoint: { version: 1, streamId, address: '192.168.1.21', port: 17777 } }] }, 'GameServer');
    const wrongAddress = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '公告端點與報告不符' }).waitFor();
    check(wrongAddress.servers[0].addressMatched === false, 'The ready file compares the advertised IPv4 even when Unity binds to all interfaces');
    assert.equal(await page.locator(rosterShortcut(5)).count(), 0);
    ready.servers[0].ready.address = '192.168.1.21';
    await choose(page, ready);
    const saved = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '管理端已保存端點' }).waitFor();
    check(saved.servers[0].endpointState === 'published' && saved.servers[0].recentSource !== true
      && !(await page.locator(summary).innerText()).includes('皆相符，並收到'),
      'A matching endpoint alone does not show a fresh game source');
    for (const roomId of [1, 5]) await api(sessionPath + '/players', 'POST', {
      playerId: randomUUID(), roomId, name: `Original room ${roomId}`, headset: 'Quest3'
    });
    const originalRoster = await api(sessionPath);
    assert.equal(await page.locator('[data-launch-review-roster]').count(), 5);
    const players = originalRoster.players.map(({ id, roomId }) => {
      const head = { x: (roomId - 3) * 14, y: 1.65, z: -3 };
      const connected = roomId === 1;
      return { id, roomId, connected, head, muzzle: head, forward: { x: 0, y: 0, z: 1 }, health: 100,
        magazine: 30, reserve: 90, rig: connected ? { kind: 'Simulated', left: head, right: head } : { kind: 'None' } };
    });
    await page.bringToFront();
    let sequence = 0;
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline && !(await page.locator(seatStatus(1)).innerText()).includes('合成姿態就緒 1')) {
      const packet = { sequence: ++sequence, observedSequence: originalRoster.sequence, elapsedMilliseconds: sequence === 1 ? 0 : Date.now() - started,
        weather: 'Clear', throughCombatSequence: 0, events: [],
        frame: { phase: 'Preparing', tick: 0, night: false, throughSequence: 0, players } };
      assert.equal(send({ type: 'frame', payload: packet }).acceptedSequence, sequence);
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    check((await page.locator(seatStatus(1)).innerText()).includes('合成姿態就緒 1')
      && (await page.locator(seatStatus(5)).innerText()).includes('姿態未就緒 1')
      && (await page.locator(seatStatus(2)).innerText()).includes('未編列 1、2、3、4、5'),
      'Live seat rows distinguish connected simulation, missing pose and vacant rooms in the original linked venue');
    await page.locator(seatStatus(1)).filter({ hasText: '快照已過期' }).waitFor({ timeout: 5000 });
    check(!(await page.locator(seatStatus(1)).innerText()).includes('合成姿態就緒'), 'Expired game evidence withdraws previously confirmed seats');
    await openRoomRoster(page, session.id, 5);
    check(await page.locator('#roster [data-roster-room="5"]').isVisible()
      && await page.locator('#roster [data-roster-room="1"]').isHidden(),
      'A shared endpoint opens exactly the requested linked room and focuses its roster');
    await openRoomRoster(page, session.id, 1);
    check(JSON.stringify(await api(sessionPath)) === JSON.stringify(originalRoster), 'Both roster shortcuts leave the original session unchanged');
    await page.setViewportSize({ width: 390, height: 850 });
    await page.locator(panel).screenshot({ path: path.join(screenshots, 'venue-ready-roster-mobile.png') });
    check(await page.locator(panel).evaluate(element => element.scrollWidth <= element.clientWidth),
      'Five linked room shortcuts and the source details fit a narrow console');
    await page.setViewportSize({ width: 1440, height: 1080 });
    await api(sessionPath, 'DELETE', undefined, 'Master', 204);
    replacement = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Independent', roomIds: [5] }, 'Master', 201);
    await page.locator(rosterShortcut(5)).click();
    await page.locator(rosterStatus).filter({ hasText: '無法開啟原場次名冊' }).waitFor();
    check(await page.locator('#session-select').inputValue() !== replacement.id,
      'A stale shortcut rejects an ended original session before selecting a replacement');
    await choose(page, { ...ready, servers: [{ roomIds, ready: { ...ready.servers[0].ready, streamId: randomUUID() } }] });
    const otherStream = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '已登記其他來源' }).waitFor();
    check(otherStream.servers[0].endpointAddress === null, 'An unrelated stream cannot borrow the published endpoint of the current session');

    await choose(page, { ...raw, venueLaunchId: randomUUID() });
    const foreign = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '已登記其他來源' }).waitFor();
    check(foreign.servers[0].streamId === null && !(await page.locator(rows).textContent()).includes(streamId),
      'A mismatched launch does not identify another source as the original');
    await choose(page, ready);
    await checkSelected(page);
    await page.locator(rows).filter({ hasText: '已結束' }).waitFor();
    check(await page.locator(rosterShortcut(5)).count() === 0, 'A ready file for an ended session never links to the replacement room roster');
    await choose(page, raw);
    const ended = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '已結束' }).waitFor();
    check(ended.servers[0].phase === 'Ended' && ended.servers[0].streamId === streamId,
      'A closed original session remains available for review');

    const terminal = { ...raw, status: 'venue-sealed-stopped', complete: true, readyPublished: true,
      sourceAttachment: 'confirmed', endpointPublication: 'confirmed', servers: [{ roomIds, result: {
        ...raw.servers[0].result, schemaVersion: 1, status: 'sealed-stopped', complete: true, childExited: true,
        cleanupCompleted: true, streamId, finalWorld: { complete: true, acceptedSequence: sequence,
          header: { ...header, schemaVersion: 1 } },
        finalCombatStream: { sealed: true, streamId, origin: 'Simulation', venueLaunchId: launchId, acceptedSequence: 0 }
      } }] };
    const terminalTarget = { version: 3, instanceId, launchId, topology: 'Linked', servers: [{ roomIds, sessionId: session.id,
      streamId, udp: null, seal: { origin: 'Simulation', combatSequence: 0, worldSequence: sequence } }] };
    await api(route, 'POST', terminalTarget, 'Room1', 403);
    await api(route, 'POST', { ...terminalTarget, servers: [{ ...terminalTarget.servers[0], seal: { origin: 'Simulation', worldSequence: sequence } }] }, 'Master', 400);
    await choose(page, terminal);
    assert.equal((await (await checkSelected(page)).json()).servers[0].sealState, 'pending');
    await page.locator(rows).filter({ hasText: '管理端尚未完成雙封存' }).waitFor();
    check(!(await page.locator(summary).textContent()).includes('均相符') && await page.locator(replayShortcut(5)).count() === 0,
      'The report cannot confirm closure or offer replay before the management seals');
    const endedState = await api(sessionPath);
    const finalSequence = ++sequence;
    assert.equal(send({ type: 'frame', payload: { sequence, observedSequence: endedState.sequence, elapsedMilliseconds: Date.now() - started,
      weather: 'Clear', throughCombatSequence: 0, events: [], frame: { phase: 'Ended', tick: 0, night: false, throughSequence: 0, players } } }).acceptedSequence, sequence);
    await api(sessionPath + '/combat-stream/seal', 'POST', { streamId, finalSequence: 0 }, 'GameServer');
    assert.equal(send({ type: 'seal', finalSequence }).complete, true);
    terminal.servers[0].result.finalWorld.acceptedSequence = sequence;
    await choose(page, terminal);
    const originalClosed = await api(sessionPath);
    assert.equal((await (await checkSelected(page)).json()).servers[0].sealState, 'matched');
    projected(requests.at(-1));
    terminalTarget.servers[0].seal.worldSequence = sequence;
    assert.deepEqual(requests.at(-1), terminalTarget);
    await page.locator(summary).filter({ hasText: '五房原戰鬥與回放封存序號均相符' }).waitFor();
    check(await page.locator(rosterShortcut(5)).count() === 0 && JSON.stringify(await api(sessionPath)) === JSON.stringify(originalClosed),
      'A sealed report matches both original tails without uploading private fields or changing the session');
    check(await page.locator(closureShortcut).count() === 0, 'An individually ended recording offers replay without inventing a venue closure');
    await page.locator(panel).screenshot({ path: path.join(screenshots, 'venue-terminal-review.png') });
    await openRoomReplay(page, session.id, 5, sequence);
    check(await page.locator('#world-view').isVisible() && await page.locator('#world-recording').inputValue() !== replacement.id,
      'A verified room shortcut opens its original sealed recording even after the room is reused');
    check(await page.locator('#world-venue-review').isHidden(),
      'Linked replay keeps its room selector without offering alignment between separate recordings');
    await page.locator('#tab-operations').click();
    await page.locator(panel + ' summary').click();
    await choose(page, terminal);
    await checkSelected(page);
    await page.route('**/api/world-recordings/page?**', async handler => {
      const original = await handler.fetch();
      const payload = await original.json();
      const row = [...payload.recordings, ...payload.pinned].find(item => item.header.sessionId === session.id);
      if (row) row.acceptedSequence++;
      await handler.fulfill({ response: original, json: payload });
    });
    let replayRequested = false;
    const trackReplay = request => { if (request.url().includes(`/api/sessions/${session.id}/world/watch?`)) replayRequested = true; };
    page.on('request', trackReplay);
    await page.locator(replayShortcut(5)).click();
    await page.locator('#world-message').filter({ hasText: '目前無法讀取原場次的錄製' }).waitFor();
    check(!replayRequested && await page.locator('#world-recording').inputValue() === '',
      'A changed recording tail is rejected before a replay stream opens');
    page.off('request', trackReplay);
    await page.unroute('**/api/world-recordings/page?**');
    await page.locator('#tab-operations').click();
    await page.locator(panel + ' summary').click();
    for (const evidence of ['finalCombatStream', 'finalWorld']) {
      terminal.servers[0].result[evidence].acceptedSequence++;
      await choose(page, terminal);
      assert.equal((await (await checkSelected(page)).json()).servers[0].sealState, 'mismatch');
      await page.locator(rows).filter({ hasText: '原錄製來源或封存序號不符' }).waitFor();
      check(!(await page.locator(summary).textContent()).includes('均相符') && await page.locator(replayShortcut(5)).count() === 0,
        `A different ${evidence} tail cannot confirm closure or offer replay`);
      terminal.servers[0].result[evidence].acceptedSequence--;
    }
    const terminalResult = terminal.servers[0].result;
    terminalResult.finalWorld.header.origin = terminalResult.finalCombatStream.origin = 'GameServer';
    await choose(page, terminal);
    assert.equal((await (await checkSelected(page)).json()).servers[0].sealState, 'mismatch');
    await page.locator(rows).filter({ hasText: '原錄製來源或封存序號不符' }).waitFor();
    check(!(await page.locator(summary).textContent()).includes('均相符'), 'Matching sequence numbers from a different origin cannot confirm closure');

    let received;
    const observed = new Promise(resolve => { received = resolve; });
    const held = new Promise(resolve => { release = resolve; });
    await page.route('**/api' + route, async handler => { received(); await held; await handler.continue(); });
    await page.locator(button).click();
    await observed;
    await page.locator('#tab-missions').click();
    const late = page.waitForResponse('**/api' + route);
    release();
    await late;
    await page.locator('#tab-operations').click();
    check(await page.locator(input).inputValue() === '' && await page.locator(rows).count() === 0
      && await page.locator(summary).textContent() === '', 'Leaving operations discards the file and ignores the held response');
  } finally {
    release?.();
    await page.close();
    const current = await api(sessionPath);
    if (current.state !== 'Ended') await api(sessionPath, 'DELETE', undefined, 'Master', 204);
    if (replacement) await api('/sessions/' + replacement.id, 'DELETE', undefined, 'Master', 204);
  }
}

module.exports = { checkVenueLaunchReview };

if (require.main === module) {
  (async () => {
    const { chromium } = require('playwright');
    const inputChunks = [];
    for await (const chunk of process.stdin) inputChunks.push(chunk);
    const { base, token, reportPath, expected, output, liveReady, replayAlignment } = JSON.parse(Buffer.concat(inputChunks).toString('utf8'));
    assert.match(base, /^http:[/][/]127[.]0[.]0[.]1:[0-9]+$/);
    const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_SERVER_PLAN_CHROMIUM,
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    try {
      const page = await browser.newPage();
      await login(page, base, token);
      await page.locator(panel + ' summary').click();
      await page.locator(input).setInputFiles(reportPath);
      const response = await checkSelected(page);
      assert.equal(response.status(), 200);
      projected(response.request().postDataJSON());
      const review = await response.json();
      assert.equal(review.instanceVerified, true);
      assert.equal(review.servers.length, expected.length);
      for (const [index, fields] of expected.entries())
        for (const [key, value] of Object.entries(fields)) assert.deepEqual(review.servers[index][key], value);
      await page.locator(rows).nth(expected.length - 1).waitFor();
      assert.match(await page.locator(summary).textContent(), /管理實例相符/);
      if (response.request().postDataJSON().version === 3) {
        assert.match(await page.locator(summary).textContent(), /五房原戰鬥與回放封存序號均相符/);
        assert.equal(await page.locator(rows).filter({ hasText: '雙封存序號相符' }).count(), expected.length);
        assert.equal(await page.locator('[data-launch-review-roster]').count(), 0);
        const targets = response.request().postDataJSON().servers;
        assert.ok(review.closureBatchId);
        const closurePath = `/api/venue/closure/${review.closureBatchId}`;
        const isClosure = url => url.pathname === closurePath && url.searchParams.get('includeScores') === 'true'
          && url.searchParams.get('includeDebriefReceipts') === 'true';
        await page.route(isClosure, async route => {
          const response = await route.fetch();
          const report = await response.json();
          report.batch.sessions[0].replay.throughSequence++;
          await route.fulfill({ response, json: report });
        }, { times: 1 });
        await page.locator(closureShortcut).click();
        await page.getByText('無法確認原批次戰績與回條。請重新核對結束報告。', { exact: true }).waitFor();
        assert.equal(await page.locator('#venue-closure-batch').inputValue(), '');
        const readClosure = page.waitForResponse(value => isClosure(new URL(value.url())));
        await page.locator(closureShortcut).click();
        const archived = await readClosure;
        assert.equal(archived.status(), 200);
        const report = await archived.json();
        await page.waitForFunction(id => document.activeElement.id === 'venue-closure-title'
          && document.querySelector('#venue-closure-batch').value === id, review.closureBatchId, { polling: 100 });
        assert.equal(await page.locator('#venue-score-table').isVisible(), true);
        assert.equal(await page.locator('[data-venue-debrief-room]').count(), 5);
        assert.deepEqual(report.batch.sessions.map(row => row.sessionId), targets.map(row => row.sessionId));
        review.checkedClosure = { requestId: report.batch.requestId, players: report.scores.total.players,
          receipts: report.debriefReceipts.rooms.reduce((total, room) => total + room.confirmedCount, 0) };
        const checkedReplays = [];
        for (const { sessionId, roomIds, seal } of targets) for (const roomId of roomIds) {
          if (checkedReplays.length) {
            await page.locator('#tab-operations').click();
            await page.locator(panel + ' summary').click();
            await page.locator(input).setInputFiles(reportPath);
            assert.equal((await checkSelected(page)).status(), 200);
          }
          await openRoomReplay(page, sessionId, roomId, seal.worldSequence);
          if (replayAlignment && roomId === 1) {
            const { requestId, fromSessionId, toSessionId, fromFrame, fromElapsed, fromTick, toFrame, frameTick } = replayAlignment;
            assert.equal(review.replayBatchId, requestId);
            await page.locator('#world-speed').selectOption('0.25');
            const frame = page.locator(`#world-canvas[data-sequence="${fromFrame}"]`);
            await page.locator('#world-timeline').evaluate((slider, value) => {
              slider.value = value;
              slider.dispatchEvent(new Event('change', { bubbles: true }));
            }, fromElapsed);
            await frame.waitFor();
            await page.locator('#world-pause').filter({ hasText: '暫停回放' }).click();
            const paused = Number(await page.locator('#world-canvas').getAttribute('data-sequence'));
            for (let offset = paused; offset > fromFrame; offset--) {
              await page.locator('#world-frame-back').click();
              await page.locator(`#world-canvas[data-sequence="${offset - 1}"]`).waitFor();
            }
            assert.equal(await frame.count(), 1);
            await page.locator('#world-venue-basis').selectOption('tick');
            const pending = page.waitForResponse(value => new URL(value.url()).pathname === `/api/venue/closure/${requestId}/replay-at-tick`);
            await page.locator('[data-venue-align-room="2"]').click();
            const aligned = await pending;
            assert.equal(aligned.status(), 200);
            const result = await aligned.json();
            assert.deepEqual([result.requestId, result.fromSessionId, result.fromFrame, result.fromTick, result.roomId,
              result.recording.header.sessionId, result.frame.packet.sequence, result.frameTick],
            [requestId, fromSessionId, fromFrame, fromTick, 2, toSessionId, toFrame, frameTick]);
            await page.locator('#world-venue-message').filter({ hasText: '已對齊房間 2' }).waitFor();
            assert.equal(await page.locator('#world-recording').inputValue(), toSessionId);
            assert.equal(await page.locator('#world-room').inputValue(), '2');
            assert.equal(await page.locator('#world-canvas').getAttribute('data-sequence'), String(toFrame));
            review.checkedAlignment = replayAlignment;
          }
          checkedReplays.push({ sessionId, roomId, worldSequence: seal.worldSequence });
        }
        review.checkedReplays = checkedReplays;
      }
      if (liveReady) {
        assert.equal(response.request().postDataJSON().version, 2);
        assert.match(await page.locator(summary).textContent(), /五房原端點皆相符，並收到近期來源快照/);
        const checkedRosters = [];
        for (const { roomIds, sessionId } of expected) for (const roomId of roomIds) {
          await page.locator(seatStatus(roomId)).filter({ hasText: '合成姿態就緒 1、2、3、4、5' }).waitFor();
          await openRoomRoster(page, sessionId, roomId);
          assert.equal(await page.locator(`#roster [data-roster-room="${roomId}"]:visible`).count(), 5);
          assert.equal(await page.locator(`#roster [data-roster-room]:visible:not([data-roster-room="${roomId}"])`).count(), 0);
          checkedRosters.push({ roomId, sessionId });
        }
        review.checkedRosters = checkedRosters;
      }
      await fs.writeFile(output, JSON.stringify(review, null, 2) + '\n', { flag: 'wx' });
    } finally { await browser.close(); }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
