import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/readiness-ui.js', import.meta.url), 'utf8');
const { readinessView, roomReadinessView, mrReadinessView } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
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

const room = { id: 1, sessionId: 'session', playerCount: 3, capacity: 5 };
const roomRow = { roomId: 1, sessionId: 'session', sessionSequence: 10, registered: 3, sourceState: 'Fresh',
  sourceAgeMilliseconds: 10, simulatedReady: 1, trackedReady: 1 };
const overview = { version: 1, rooms: [roomRow] };
test('Room totals are scoped to the current room and session and retain both rig kinds', () => {
  const foreign = { ...roomRow, roomId: 2, simulatedReady: 3, trackedReady: 0 };
  assert.deepEqual(roomReadinessView({ ...overview, rooms: [foreign, roomRow] }, room, session, 0),
    { source: 'Fresh', ready: 2, text: '2 / 3 姿態有效 · 合成 1 · 追蹤 1' });
  for (const changes of [{ roomId: 2 }, { sessionId: 'other' }, { sessionSequence: 9 }, { registered: 4 }])
    assert.equal(roomReadinessView({ ...overview, rooms: [{ ...roomRow, ...changes }] }, room, session, 0).ready, undefined);
  assert.equal(roomReadinessView({ ...overview, rooms: [roomRow, roomRow] }, room, session, 0).ready, undefined);
  assert.equal(roomReadinessView(overview, room, { ...session, state: 'Ended' }, 0).ready, undefined);
});
test('Room readiness expires from request start and never renders invalid totals as ready', () => {
  assert.equal(roomReadinessView(overview, room, session, 1490).ready, 2);
  assert.equal(roomReadinessView(overview, room, session, 1490.01).source, 'Stale');
  for (const changes of [{ simulatedReady: -1 }, { trackedReady: 3 }, { trackedReady: '1' }])
    assert.equal(roomReadinessView({ ...overview, rooms: [{ ...roomRow, ...changes }] }, room, session, 0).source, 'Unavailable');
  for (const sourceState of ['Suspended', 'PhasePending', 'NoRecording', 'ClockSkew'])
    assert.equal(roomReadinessView({ ...overview, rooms: [{ ...roomRow, sourceState }] }, room, session, 0).ready, undefined);
});

const mr = { ...session, roomIds: [1, 2], environment: { mode: 'MR' },
  players: [player, { id: 'peer', admissionId: 'second', roomId: 2, seat: 3 }] };
const master = { role: 'Master' }, room1 = { role: 'RoomController', roomId: 1 };
const oneTracked = { ...report.players[0], rigKind: 'Tracked' };
const peer = { playerId: 'peer', admissionId: 'second', roomId: 2, seat: 3, state: 'PoseUnavailable', rigKind: 'None', canParticipate: false };
const mrReport = { ...report, observedSequence: 10, origin: 'GameServer', mrStartState: 'WaitingPlayers',
  players: [oneTracked, peer] };
test('MR start shows the exact waiting seat and scopes the detailed list to the room controller', () => {
  const view = mrReadinessView(mrReport, mr, 0, master);
  assert.equal(view.state, 'WaitingPlayers');
  assert.deepEqual(view.rooms, [{ room: 1, text: '房間 1 · 1 / 1 追蹤就緒', attention: false },
    { room: 2, text: '房間 2 · 0 / 1 追蹤就緒 · 等候席位 4', attention: false }]);
  assert.deepEqual(mrReadinessView(mrReport, mr, 0, room1).rooms, view.rooms.slice(0, 1));
  assert.equal(mrReadinessView(mrReport, { ...mr, players: [] }, 0, master).state, 'EmptyRoster');
  assert.equal(mrReadinessView(mrReport, { ...mr, state: 'Running' }, 0, master).state, 'Updating');
  assert.equal(mrReadinessView(mrReport, { ...mr, environment: { mode: 'VR' } }, 0, master), null);
});

test('MR ready requires a fresh current revision and every original admission to be tracked', () => {
  const complete = { ...mrReport, mrStartState: 'Ready', players: [oneTracked,
    { ...peer, state: 'Participating', rigKind: 'Tracked', canParticipate: true }] };
  assert.equal(mrReadinessView(complete, mr, 1490, master).state, 'Ready');
  assert.equal(mrReadinessView(complete, mr, 1490.1, master).state, 'WaitingSource');
  for (const invalid of [{ sessionSequence: 11 }, { observedSequence: 9 }, { origin: 'Simulation' },
    { players: [oneTracked, { ...complete.players[1], admissionId: 'other' }] }, { players: [oneTracked, oneTracked] },
    { players: [{ ...oneTracked, rigKind: 'Simulated' }, complete.players[1]] }]) {
    const blocked = mrReadinessView({ ...complete, ...invalid }, mr, 0, master);
    assert.equal(blocked.state, 'Updating');
    assert.deepEqual(blocked.rooms, []);
  }
  assert.equal(mrReadinessView({ ...complete, mrStartState: 'WaitingRevision', observedSequence: 9 }, mr, 0, master).state, 'WaitingRevision');
});

test('Paused MR readiness requires its own fresh report and excludes only confirmed eliminated seats', () => {
  const paused = { ...mr, state: 'Paused' };
  const casualty = { ...peer, state: 'Eliminated' };
  const ready = { ...mrReport, mrStartState: null, mrResumeState: 'Ready', players: [oneTracked, casualty] };
  const view = mrReadinessView(ready, paused, 0, master);
  assert.equal(view.action, 'Resume');
  assert.equal(view.state, 'Ready');
  assert.match(view.rooms[1].text, /已淘汰 1/);
  assert.doesNotMatch(view.rooms[1].text, /等候席位/);
  for (const invalid of [{ ...casualty, admissionId: 'previous' }, peer]) {
    const result = mrReadinessView({ ...ready, players: [oneTracked, invalid] }, paused, 0, master);
    assert.equal(result.state, 'Updating');
    assert.deepEqual(result.rooms, []);
  }
  assert.equal(mrReadinessView({ ...ready, mrStartState: 'Ready', mrResumeState: null }, paused, 0, master).state, 'Updating');
  assert.equal(mrReadinessView(ready, paused, 1501, master).state, 'WaitingSource');
});

test('Running MR shows the missing living seat while preserving known roster and scope', () => {
  const running = { ...mr, state: 'Running' };
  const live = { ...mrReport, mrStartState: null, mrTrackingState: 'WaitingPlayers', observedSequence: 9 };
  const view = mrReadinessView(live, running, 0, master);
  assert.equal(view.action, 'Monitor');
  assert.deepEqual(view.rooms.filter(row => row.attention).map(row => row.room), [2]);
  assert.equal(mrReadinessView(live, running, 0, room1).rooms.length, 1);
  assert.equal(mrReadinessView({ ...live, sessionSequence: 11 }, running, 0, master).state, 'WaitingPlayers');
  assert.deepEqual(mrReadinessView(live, running, 1501, master).rooms, []);
  assert.equal(mrReadinessView({ ...live, players: [oneTracked, { ...peer, admissionId: 'different' }] },
    running, 0, master).state, 'Updating');
  const recovered = { ...live, mrTrackingState: 'Ready', players: [oneTracked, { ...peer, state: 'Eliminated' }] };
  assert.equal(mrReadinessView(recovered, running, 0, master).state, 'Ready');
});

test('Running room cards warn only when their fresh, scoped MR report has a missing live seat', () => {
  const running = { ...mr, state: 'Running' };
  const live = { ...overview, rooms: [{ ...roomRow, simulatedReady: 0, trackedReady: 1, mrLiving: 2 }] };
  assert.equal(roomReadinessView(live, room, running, 0).attention, true);
  assert.match(roomReadinessView(live, room, running, 0).text, /1 \/ 2.*等候 1 席/);
  assert.equal(roomReadinessView(live, room, running, 1501).attention, undefined);
  for (const change of [{ mrLiving: null }, { mrLiving: 0 }, { mrLiving: 4 }, { simulatedReady: 1 }]) {
    assert.equal(roomReadinessView({ ...live, rooms: [{ ...live.rooms[0], ...change }] }, room, running, 0).source, 'Unavailable');
  }
});
