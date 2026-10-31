import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/readiness-ui.js', import.meta.url), 'utf8');
const { readinessView } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const player = { id: 'player', admissionId: 'first', roomId: 1, seat: 0 };
const session = { id: 'session', sequence: 10, state: 'Preparing', players: [player] };
const report = { version: 1, sessionId: 'session', sessionSequence: 10, sourceState: 'Fresh', sourceAgeMilliseconds: 10, origin: 'Simulation',
  players: [{ playerId: 'player', admissionId: 'first', roomId: 1, seat: 0, state: 'Participating', rigKind: 'Simulated', canParticipate: true }] };
test('Participation requires the current session, sequence, admission, room and seat', () => {
  assert.equal(readinessView(report, session, 0).rows[0].ready, true);
  for (const change of [{ sessionId: 'other' }, { version: 2 }, { sessionSequence: 9 }]) assert.equal(readinessView({ ...report, ...change }, session, 0).rows[0].ready, false);
  for (const change of [{ admissionId: 'new' }, { roomId: 2 }, { seat: 1 }]) assert.equal(readinessView(report, { ...session, players: [{ ...player, ...change }] }, 0).rows[0].ready, false);
});
test('A response ages from request start, including download time and silent intervals', () => {
  assert.equal(readinessView(report, session, 1490).rows[0].ready, true);
  for (const elapsed of [1490.01, 1501, Infinity, NaN, -1]) assert.equal(readinessView(report, session, elapsed).rows[0].ready, false);
  assert.equal(readinessView({ ...report, sourceAgeMilliseconds: null }, session, 0).rows[0].ready, false);
});
test('Source suspension, stale capture, clock skew and ended session override a prior ready body', () => {
  for (const sourceState of ['NoRecording', 'Stale', 'ClockSkew', 'Suspended', 'UnknownCaptureTime', 'Ended', 'PhasePending', 'new-status'])
    assert.equal(readinessView({ ...report, sourceState }, session, 0).rows[0].ready, false);
  assert.equal(readinessView(report, { ...session, state: 'Ended' }, 0).rows[0].ready, false);
});
test('Synthetic or tracked provenance is explicit, malformed or duplicated bodies fail closed', () => {
  assert.match(readinessView(report, session, 0).rows[0].text, /合成姿態/);
  const tracked = { ...report, players: [{ ...report.players[0], rigKind: 'Tracked' }] };
  assert.match(readinessView(tracked, session, 0).rows[0].text, /追蹤姿態/);
  for (const players of [[{ ...report.players[0], canParticipate: false }], [{ ...report.players[0], rigKind: 'None' }], [...report.players, ...report.players]])
    assert.equal(readinessView({ ...report, players }, session, 0).rows[0].ready, false);
});
