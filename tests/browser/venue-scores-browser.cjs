const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs/promises');
const readCsv = require('./csv.cjs');

module.exports = async ({ context, api, tokens, base, screenshots, check, captureErrors }) => {
  const page = await context.newPage(), active = new Set();
  captureErrors(page);
  const table = page.locator('#venue-score-table');
  const exportScores = page.locator('#export-venue-scores'), exportStatus = page.locator('#venue-score-status');
  const score = (players, ammoUsed, shotsHit, kills, hitsReceived, damageTaken, accuracyPercent) =>
    ({ players, ammoUsed, shotsHit, kills, hitsReceived, damageTaken, accuracyPercent });
  const blank = score(0, 0, 0, 0, 0, 0, 0);
  const scoresUrl = id => '/venue/closure' + (id ? '/' + id : '') + '?includeScores=true';
  const csvUrl = id => `/venue/closure/${id}/scores.csv`;
  const fetchCsv = id => fetch(base + '/api' + csvUrl(id), { headers: { Authorization: 'Bearer ' + tokens.Master } });
  const command = (id, action) => api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action });
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function finish() {
    const targets = (await api('/venue/phase')).end;
    assert.deepEqual(new Set(targets.map(target => target.sessionId)), active);
    const batch = await api('/venue/phase', 'POST', { action: 'End', targets }, 'Master', 200, undefined, randomUUID());
    active.clear();
    return batch.requestId;
  }
  async function showTotal(expected) {
    await page.waitForFunction(text => document.querySelector('#venue-score-rows tr:last-child')?.textContent === text
      && !document.querySelector('#venue-score-table').hidden, '本批合計' + expected.join(''), { polling: 100 });
  }
  async function checkDownload(scores, label) {
    const { requestId } = scores, saved = page.waitForEvent('download');
    await exportScores.click();
    const download = await saved, filename = `vr-command-venue-scores-v1-${requestId}.csv`;
    const bytes = await fs.readFile(await download.path());
    const apiResponse = await fetchCsv(requestId);
    const expected = (rowType, sessionId, roomId, totals) => ({ reportVersion: '1', rowType, requestId, sessionId, roomId,
      ...Object.fromEntries(Object.entries(totals).map(([key, value]) => [key, String(value)])) });
    assert.deepEqual(readCsv(bytes), [...scores.rooms.map(room => expected('Room', room.sessionId, String(room.roomId), room.totals)),
      expected('Total', '', '', scores.total)]);
    check(apiResponse.ok && apiResponse.headers.get('cache-control') === 'no-store' && bytes.equals(Buffer.from(await apiResponse.arrayBuffer()))
      && download.suggestedFilename() === filename && bytes.subarray(0, 3).equals(Buffer.from([239, 187, 191])), label);
    await fs.writeFile(path.join(screenshots, filename), bytes);
    const archiveReady = page.waitForEvent('download');
    const archiveResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api/venue/closure/${requestId}/reports.zip`);
    await page.locator('#export-venue-reports').click();
    const [archive, response] = await Promise.all([archiveReady, archiveResponse]);
    check(response.ok() && new URL(response.url()).searchParams.get('includeScores') === 'true'
      && archive.suggestedFilename() === `vr-command-venue-reports-v1-${requestId}.zip`
      && (await fs.readFile(await archive.path())).equals(await response.body()),
      'The selected batch downloads the exact API ZIP with its room and venue totals requested');
  }
  const shot = (playerId, hit) => {
    const shotId = randomUUID(), enemyId = randomUUID();
    return [{ playerId, kind: 'ShotFired', shotId },
      ...(hit ? [{ playerId, kind: 'ShotHit', shotId, enemyId }] : [])];
  };
  const record = event => ({ ...event, reportId: randomUUID(), origin: 'Simulation' });

  try {
    const mission = await api('/missions', 'POST', { name: 'Venue sealed scores', briefing: '', durationSeconds: 300,
      environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
    async function prepare(mode, roomIds) {
      const { id } = await api('/sessions', 'POST', { missionId: mission.id, mode, roomIds }, 'Master', 201);
      active.add(id);
      return id;
    }
    async function join(id, roomId) {
      const playerId = randomUUID();
      await api(`/sessions/${id}/players`, 'POST', { playerId, roomId, name: 'Venue score seat', headset: 'Quest3' });
      return playerId;
    }
    async function report(id, events) {
      for (const event of events) await api(`/sessions/${id}/combat`, 'POST', record(event), 'GameServer');
    }
    const first = await prepare('Independent', [1]), second = await prepare('Independent', [2]);
    const empty = await prepare('Independent', [3]);
    const alpha = await join(first, 1), bravo = await join(second, 2), streamId = randomUUID();
    await api(`/sessions/${second}/combat-stream`, 'POST', { streamId, origin: 'Simulation' }, 'GameServer');
    await command(first, 'Begin');
    await command(second, 'Begin');
    const hit = shot(alpha, true);
    await report(first, [...hit, { ...hit[1], kind: 'EnemyEliminated' }, { playerId: alpha, kind: 'PlayerDamaged', damage: 20 }]);
    const observed = (await api(`/sessions/${second}`)).sequence;
    const events = [...shot(bravo, true), ...shot(bravo, false), ...shot(bravo, false)];
    await api(`/sessions/${second}/combat-stream/batch`, 'POST', events.map((event, index) =>
      ({ streamId, streamSequence: index + 1, observedSequence: observed, report: record(event) })), 'GameServer');
    const independent = await finish();
    await login('Master');
    await page.locator('#venue-report-status').filter({ hasText: '房間 2' }).waitFor();
    check(!Object.hasOwn(await api(scoresUrl(independent)), 'scores') && await table.isHidden(),
      'The batch score table never displays partial totals before the final combat seal');
    const waiting = await fetchCsv(independent);
    check(waiting.status === 409 && (await waiting.json()).roomIds.join() === '2' && await exportScores.isHidden(),
      'Unsealed combat blocks the summary CSV and keeps the download hidden');
    await api(`/sessions/${second}/combat-stream/seal`, 'POST', { streamId, finalSequence: events.length }, 'GameServer');
    const separate = await api(scoresUrl(independent));
    assert.deepEqual(separate.scores, { requestId: independent, rooms: [
      { roomId: 1, sessionId: first, totals: score(1, 1, 1, 1, 1, 20, 100) },
      { roomId: 2, sessionId: second, totals: score(1, 3, 1, 0, 0, 0, 33.33) },
      { roomId: 3, sessionId: empty, totals: blank }
    ], total: score(2, 4, 2, 1, 1, 20, 50) });
    await showTotal([2, 4, 2, 1, 1, 20, '50%']);
    check(separate.batch.sessions[1].world === 'Missing' && (await table.locator('[data-venue-score-room="3"] td').allTextContents()).join('|')
      === '房間 3|0|0|0|0|0|0|0%', 'Independent room totals include the original empty room and weighted accuracy once combat is final');
    assert.deepEqual(await api('/venue/closure/' + independent), { batch: separate.batch });
    const privateRead = await fetch(base + '/api' + scoresUrl(independent), { headers: { Authorization: 'Bearer ' + tokens.Master } });
    await api(scoresUrl(independent), 'GET', undefined, 'Room1', 403);
    check(privateRead.headers.get('cache-control') === 'no-store', 'Private batch scores retain Master authorization and leave the default closure response unchanged');
    await api(csvUrl(independent), 'GET', undefined, 'Room1', 403);
    await api(csvUrl(randomUUID()), 'GET', undefined, 'Master', 404);
    check((await fetch(base + '/api' + csvUrl(independent))).status === 401, 'Only an authenticated Master can download an original batch summary');
    await checkDownload(separate.scores, 'Independent CSV matches the displayed original rooms including an empty room and the weighted total');

    const rooms = [1, 2, 3, 4, 5], linked = await prepare('Linked', rooms);
    const leader = await join(linked, 1), wing = await join(linked, 5);
    await command(linked, 'Begin');
    await report(linked, [...shot(leader, true), ...shot(wing, false), ...shot(wing, false)]);
    const linkedBatch = await finish();
    const combined = await api(scoresUrl());
    assert.deepEqual(combined.scores, { requestId: linkedBatch, rooms: rooms.map(roomId => ({ roomId, sessionId: linked,
      totals: roomId === 1 ? score(1, 1, 1, 0, 0, 0, 100) : roomId === 5 ? score(1, 2, 0, 0, 0, 0, 0) : blank })),
      total: score(2, 3, 1, 0, 0, 0, 33.33) });
    await showTotal([2, 3, 1, 0, 0, 0, '33.33%']);
    check(await table.locator('[data-venue-score-room]').count() === 5, 'Linked room scores count their original players once and show all five rooms');
    await checkDownload(combined.scores, 'Linked CSV counts the shared session once and preserves the original decimal accuracy');

    await page.locator('#venue-closure-load').click();
    const selector = page.locator('#venue-closure-batch');
    await selector.locator(`option[value="${independent}"]`).waitFor({ state: 'attached' });
    const target = base + '/api' + scoresUrl(independent) + '&includeDebriefReceipts=true';
    const swap = async route => {
      const response = await route.fetch();
      await route.fulfill({ response, json: { ...await response.json(), scores: combined.scores } });
    };
    await page.route(target, swap);
    try {
      await selector.selectOption(independent);
      await page.locator(`[data-venue-closure-session="${first}"]`).waitFor();
      check(await table.isHidden() && await exportScores.isHidden(), 'Selecting an older batch clears score rows and rejects totals from another batch');
    } finally { await page.unroute(target, swap); }
    await page.locator('#refresh').click();
    await showTotal([2, 4, 2, 1, 1, 20, '50%']);
    check(await table.locator('[data-venue-score-room]').count() === 3, 'The original independent totals return after the rooms have been reused by Linked');
    const historicalCsv = base + '/api' + csvUrl(independent);
    let downloads = 0;
    page.on('download', () => downloads++);
    await page.route(historicalCsv, async route => {
      const original = await route.fetch();
      const text = (await original.body()).toString('utf8').replaceAll(independent, linkedBatch);
      await route.fulfill({ response: original, body: text });
    }, { times: 1 });
    await exportScores.click();
    await exportStatus.filter({ hasText: '與目前批次戰績不符' }).waitFor();
    check(downloads === 0 && await table.isVisible(), 'A CSV carrying another batch ID is discarded and the visible original scores stay available');
    await page.route(historicalCsv, async route => {
      const original = await route.fetch();
      const text = (await original.body()).toString('utf8').replace('"50"\r\n', '"51"\r\n');
      await route.fulfill({ response: original, body: text });
    }, { times: 1 });
    await exportScores.click();
    await exportStatus.filter({ hasText: '與目前批次戰績不符' }).waitFor();
    check(downloads === 0, 'A CSV for the right batch with changed accuracy is discarded');
    await checkDownload(separate.scores, 'Historical batch CSV still uses its original session IDs and totals after room reuse');
    await table.screenshot({ path: path.join(screenshots, 'venue-battle-scores.png') });
    await login('Room1');
    check(await page.locator('#venue-closure').isHidden() && await table.isHidden() && await exportScores.isHidden(),
      'The room console never presents Master batch scores');
  } finally {
    await page.close();
    for (const id of active) await command(id, 'End');
  }
};
