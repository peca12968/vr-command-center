import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { encodeUnconfirmedSeatsCsv, matchesReportRows } from '../../src/VrCommand.Api/wwwroot/console/report-csv.js';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/closure-ui.js', import.meta.url), 'utf8');
const { closureView, debriefReceiptPlayers } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const session = { id: 'session', sequence: 20, state: 'Ended', roomIds: [1], mission: { definition: { durationSeconds: 600 } }, combatStream: { streamId: 'stream', origin: 'Simulation', acceptedSequence: 0, sealed: true, missionClockVersion: 1 } };
const stats = { sessionId: session.id, throughSequence: 20, pendingTelemetry: false, origin: null };
const world = { header: { schemaVersion: 1, sessionId: session.id, streamId: 'stream', origin: 'Simulation', roomIds: [1], missionClockVersion: 1, missionDurationSeconds: 600 }, acceptedSequence: 2, complete: true };
const view = (s = session, p = stats, w = world, status = 'Received') => closureView(s, p, w, status);

test('Both archive seals require the current statistics boundary and matching world source; zero-combat origin may be null', () => {
  assert.equal(view().complete, true); assert.match(view().text, /不確認送達/);
  for (const p of [null, { ...stats, sessionId: 'other' }, { ...stats, throughSequence: 19 }, { ...stats, throughSequence: 21 }, { ...stats, pendingTelemetry: true }, { ...stats, pendingTelemetry: undefined }]) assert.equal(view(session, p).complete, false);
  assert.equal(view({ ...session, combatStream: { ...session.combatStream, sealed: false } }).complete, false);
});
test('Sealed combat alone does not complete world recording; empty or failed responses never turn it green', () => {
  for (const w of [null, { ...world, complete: false }, { ...world, acceptedSequence: 0 }, { ...world, complete: 'true' }, { ...world, acceptedSequence: Infinity }]) assert.equal(view(session, stats, w).complete, false);
  for (const status of ['Waiting', 'Missing', 'Unavailable']) assert.equal(view(session, stats, world, status).complete, false);
  assert.match(view(session, stats, null, 'Missing').text, /尚未取得/);
  assert.match(view(session, stats, null, 'Unavailable').text, /無法確認/);
});
test('Another session, source, provenance, room, schema or mission clock cannot certify this archive', () => {
  for (const change of [{ sessionId: 'other' }, { streamId: 'other' }, { origin: 'GameServer' }, { roomIds: [2] }, { roomIds: [1, 1] }, { schemaVersion: 2 }, { missionClockVersion: 0 }, { missionDurationSeconds: 120 }]) {
    const result = view(session, stats, { ...world, header: { ...world.header, ...change } }); assert.equal(result.complete, false); assert.equal(result.warning, true);
  }
});
test('Preparing, Running, Paused and source-free management sessions never claim a game archive', () => {
  for (const state of ['Preparing', 'Running', 'Paused']) assert.equal(view({ ...session, state }).complete, false);
  const absent = view({ ...session, combatStream: null }); assert.equal(absent.complete, false); assert.match(absent.text, /只有管理紀錄/);
});
test('Legacy mission-clock zero remains readable, while unsupported source and nonnumeric sequence fail closed', () => {
  const legacy = { ...session, combatStream: { ...session.combatStream, missionClockVersion: 0 } };
  assert.equal(view(legacy, stats, { ...world, header: { ...world.header, missionClockVersion: 0, missionDurationSeconds: 0 } }).complete, true);
  for (const sequence of ['20', -1, Number.MAX_SAFE_INTEGER + 1]) assert.equal(view({ ...session, sequence }).complete, false);
  for (const change of [{ origin: 'Unknown' }, { acceptedSequence: -1 }, { sealed: 'true' }]) assert.equal(view({ ...session, combatStream: { ...session.combatStream, ...change } }).complete, false);
});
test('Saved counts are independent of sealing and disappear when their own source is unconfirmed', () => {
  const pending = { ...session, combatStream: { ...session.combatStream, acceptedSequence: 6, sealed: false } };
  const partial = { ...world, complete: false };
  const current = view(pending, { ...stats, pendingTelemetry: true }, partial);
  assert.equal(current.complete, false); assert.equal(current.combatCount, 6); assert.equal(current.worldCount, 2);
  assert.match(current.text, /已保存的錄製可在/);
  assert.equal(view(pending, { ...stats, throughSequence: 19 }, partial).combatCount, null);
  assert.equal(view(pending, stats, partial, 'Unavailable').worldCount, null);
  assert.equal(view(pending, stats, { ...partial, header: { ...world.header, streamId: 'other' } }).worldCount, null);
});

test('Receipt rows require exact sealed boundaries and the original visible admissions', () => {
  const players = [{ id: 'player-1', admissionId: 'admission-1', roomId: 1, name: 'One' },
    { id: 'player-2', admissionId: 'admission-2', roomId: 2, name: 'Two' }];
  const linked = { ...session, players };
  const room = { role: 'RoomController', roomId: 1 };
  const row = { ...players[0], playerId: players[0].id, acknowledged: true };
  const payload = { streamId: 'stream', throughSequence: 20, finalStreamSequence: 0, worldSequence: 2, players: [row] };
  const read = change => debriefReceiptPlayers(linked, room, { ...world, debriefReceipts: { ...payload, ...change } });
  assert.deepEqual(read({}), [row]);
  for (const change of [{ streamId: 'other' }, { throughSequence: 21 }, { finalStreamSequence: 1 }, { worldSequence: 3 },
    { players: [] }, { players: [row, row] }, { players: [{ ...row, roomId: 2 }] },
    { players: [{ ...row, admissionId: 'revoked' }] }, { players: [{ ...row, acknowledged: 'true' }] }]) {
    assert.equal(read(change), null);
  }
});

test('The unconfirmed seat CSV keeps sealed identities and scores, excluding acknowledged seats', () => {
  const room = { sessionId: 'session', streamId: 'stream', roomId: 2, worldSequence: 60 };
  const score = { ammoUsed: 4, shotsHit: 3, kills: 2, hitsReceived: 1, damageTaken: 20, accuracyPercent: 75, health: 80 };
  const pending = { room, seat: 1, playerId: 'missing-id', name: ' =1+1, "玩家"\n第二行', acknowledged: false,
    throughSequence: 26, throughCombatSequence: 12, score };
  const confirmed = { ...pending, seat: 2, playerId: 'confirmed-id', acknowledged: true };
  const format = ['reportVersion', 'requestId', 'sessionId', 'streamId', 'roomId', 'seat', 'throughSequence',
    'finalStreamSequence', 'worldSequence', 'playerId', 'playerName', 'acknowledged', 'ammoUsed', 'shotsHit',
    'kills', 'hitsReceived', 'damageTaken', 'accuracyPercent', 'health'];
  const bytes = new TextEncoder().encode(encodeUnconfirmedSeatsCsv('batch', [pending, confirmed]));
  assert.ok(matchesReportRows(bytes, [format, [1, 'batch', 'session', 'stream', 2, 1, 26, 12, 60, 'missing-id',
    "' =1+1, \"玩家\"\n第二行", false, 4, 3, 2, 1, 20, 75, 80]]));
});
