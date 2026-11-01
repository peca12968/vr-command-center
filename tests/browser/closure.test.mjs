import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/closure-ui.js', import.meta.url), 'utf8');
const { closureView } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
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
