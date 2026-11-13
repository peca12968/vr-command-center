import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/readiness-ui.js', import.meta.url), 'utf8');
const missionClock = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/mission-clock.js', import.meta.url), 'utf8');
const connection = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/connection-ui.js', import.meta.url), 'utf8');
const dataModule = source => 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
const { readinessView, roomReadinessView, roomEndpointText, roomTicketDestination, roomTicketSourceLive, mrReadinessView, roomMissionTimeView, roomVenuePhaseView,
  roomMrTrackingPauseTarget, roomMrPauseView, venueTrackingRow, roomPoseFrameTarget } =
  await import(dataModule(code.replace('./mission-clock.js', dataModule(missionClock)).replace('./connection-ui.js', dataModule(connection))));
const player = { id: 'player', admissionId: 'first', roomId: 1, seat: 0 };
const session = { id: 'session', sequence: 10, state: 'Preparing', players: [player] };
const report = { version: 1, sessionId: 'session', sessionSequence: 10, sourceState: 'Fresh', sourceAgeMilliseconds: 10, origin: 'Simulation',
  players: [{ playerId: 'player', admissionId: 'first', roomId: 1, seat: 0, state: 'Participating', rigKind: 'Simulated', canParticipate: true }] };
test('The read-only pose frame requires the fresh original room, stream, revision and seat', () => {
  const room = { id: 1, sessionId: session.id, playerCount: 1, capacity: 5 };
  const running = { ...session, state: 'Running', mode: 'Linked', roomIds: [1, 2, 3, 4, 5], combatStream: { streamId: 'stream' } };
  const poseInterruption = { streamId: 'stream', worldSequence: 8, observedSequence: 9, seats: [1] };
  const row = { ...report, roomId: 1, registered: 1, poseInterruption };
  const operator = { role: 'RoomController', roomId: 1 };
  const target = (entry = row, state = running, elapsed = 0, actor = operator) =>
    roomPoseFrameTarget({ version: 1, rooms: [entry] }, room, state, elapsed, actor);
  assert.deepEqual(target(), { mode: 'replay', sessionId: session.id, roomId: 1, streamId: 'stream', complete: false,
    throughSequence: 8, witness: { kind: 'pose-interruption', observedSequence: 9, seats: [1], playerIds: ['player'] } });
  assert.equal(target(row, running, 1491), null);
  assert.equal(target(row, running, 0, { ...operator, roomId: 2 }), null);
  assert.equal(target(row, { ...running, sequence: 11 }), null);
  assert.equal(target(row, { ...running, state: 'Paused' }), null);
  assert.equal(target({ ...row, poseInterruption: null }), null);
  for (const change of [{ streamId: 'another' }, { worldSequence: 0 }, { observedSequence: 11 }, { seats: [2] }, { seats: [1, 1] }])
    assert.equal(target({ ...row, poseInterruption: { ...poseInterruption, ...change } }), null);
});
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
test('Selected roster room counts only its registered admissions and preserves the freshness boundary', () => {
  const other = { ...player, id: 'other', roomId: 5 };
  const current = { ...session, players: [player, other] };
  assert.match(readinessView(report, current, 0).text, /1 \/ 2 姿態有效/);
  assert.match(readinessView(report, current, 0, 5).text, /房間 5 · Simulation · 0 \/ 1 姿態有效/);
  const scoped = readinessView(report, current, 1490, 1);
  assert.deepEqual(scoped.rows.map(row => row.id), ['player']);
  assert.match(scoped.text, /房間 1 · Simulation · 1 \/ 1 姿態有效/);
  assert.match(readinessView(report, current, 1490.01, 1).text, /0 \/ 1 姿態有效/);
  assert.match(readinessView(report, current, 0, 2).text, /0 \/ 0 姿態有效/);
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
test('Live venue tracking counts only exact current seats and clears stale or malformed evidence', () => {
  const current = { ...session, state: 'Running', players: [0, 1, 2].map(seat => ({ ...player, seat })) };
  const venueTracking = { trackedSeats: [1], simulatedSeats: [2], waitingSeats: [], eliminatedSeats: [3] };
  const live = fields => ({ ...overview, trackingSampledAtUtc: '2026-11-10T01:00:00.1234567+00:00',
    rooms: [{ ...roomRow, venueTracking, trackingWorldSequence: 8, ...fields }] });
  assert.deepEqual(venueTrackingRow(live(), room, current, 1490), { state: 'Incomplete', tracked: 1, worldSequence: 8,
    text: '追蹤 1 / 5 席 · 合成席位 2 · 已淘汰席位 3 · 未編列席位 4、5' });
  assert.equal(venueTrackingRow(live(), room, current, 1490.01).state, 'Stale');
  assert.equal(venueTrackingRow(live({ sessionSequence: 9 }), room, current, 0).state, 'Updating');
  assert.equal(venueTrackingRow(live({ venueTracking: undefined }), room, current, 0).state, 'WaitingRevision');
  assert.equal(venueTrackingRow({ ...live(), trackingSampledAtUtc: 'invalid' }, room, current, 0).state, 'WaitingRevision');
  assert.equal(venueTrackingRow(live({ trackingWorldSequence: 0 }), room, current, 0).state, 'Unavailable');
  for (const invalid of [{ eliminatedSeats: [2] }, { eliminatedSeats: [4] }, { trackedSeats: [], waitingSeats: [1] }])
    assert.equal(venueTrackingRow(live({ venueTracking: { ...venueTracking, ...invalid } }), room, current, 0).state, 'Unavailable');
  assert.equal(venueTrackingRow(live(), room, { ...current, state: 'Paused' }, 0).tracked, undefined);
});
test('Quick MR pause requires a fresh loss in the original room and the correct operator scope', () => {
  const mr = { ...session, mode: 'Independent', state: 'Running', roomIds: [1], environment: { mode: 'MR' },
    combatStream: { origin: 'GameServer' } };
  const row = { ...roomRow, simulatedReady: 0, trackedReady: 1, mrLiving: 2, mrTrackingPauseAvailable: true };
  const report = { ...overview, rooms: [row] };
  const roomDesk = { role: 'RoomController', roomId: 1 }, master = { role: 'Master' };
  assert.deepEqual(roomMrTrackingPauseTarget(report, room, mr, 1490, roomDesk), { sessionId: 'session', sequence: 10, linked: false });
  const linked = { ...mr, mode: 'Linked', roomIds: [1, 2, 3, 4, 5] };
  assert.equal(roomMrTrackingPauseTarget(report, room, linked, 0, master).linked, true);
  assert.equal(roomMrTrackingPauseTarget(report, room, linked, 0, roomDesk), null);
  for (const change of [{ mrTrackingPauseAvailable: false }, { mrLiving: 1 }, { simulatedReady: 1 }, { sessionId: 'old' }, { sessionSequence: 9 }])
    assert.equal(roomMrTrackingPauseTarget({ ...report, rooms: [{ ...row, ...change }] }, room, mr, 0, master), null);
  assert.equal(roomMrTrackingPauseTarget(report, room, mr, 1490.01, master), null);
});
test('MR pause remains pending until the original source acknowledges a fresh paused frame', () => {
  const paused = { ...session, state: 'Paused', environment: { mode: 'MR' } };
  const source = mrPause => ({ ...overview, rooms: [{ ...roomRow, mrPause }] });
  assert.equal(roomMrPauseView(source({ appliedAtSequence: 10, worldSequence: 22 }), room, paused, 1490), 'MR 暫停已套用');
  for (const pause of [{ appliedAtSequence: 11, worldSequence: 22 }, { appliedAtSequence: 10, worldSequence: null }])
    assert.match(roomMrPauseView(source(pause), room, paused, 0), /待確認/);
  assert.match(roomMrPauseView(source({ appliedAtSequence: 10, worldSequence: 22 }), room, paused, 1490.01), /已過期/);
  assert.equal(roomMrPauseView(source({ appliedAtSequence: 10, worldSequence: 22 }), room, { ...paused, state: 'Running' }, 0), null);
});
test('Room endpoints distinguish publication, loopback and shared connections independently of pose freshness', () => {
  const current = { ...session, combatStream: { streamId: 'stream' } };
  const endpoint = { version: 1, sessionId: current.id, streamId: 'stream', address: '127.0.0.1', port: 7777, sessionEnded: false };
  const withEndpoint = (value, ticketSourceLive) => ({ ...overview, rooms: [{ ...roomRow, sourceState: 'Stale', endpoint: value, ticketSourceLive }] });
  assert.equal(roomEndpointText(overview, room, current), '等待伺服器公布連線端點');
  assert.equal(roomEndpointText(withEndpoint(endpoint), room, { ...current, mode: 'Linked' }), 'UDP 127.0.0.1:7777 · 五房共用 · 僅同機');
  assert.equal(roomEndpointText(withEndpoint({ ...endpoint, address: '192.168.1.10' }), room, current), 'UDP 192.168.1.10:7777');
  assert.equal(roomEndpointText(withEndpoint(endpoint, false), room, current), 'UDP 127.0.0.1:7777 · 僅同機 · 遊戲來源暫未確認，暫停配票');
  for (const invalid of [{ streamId: 'previous' }, { sessionId: 'old' }, { sessionEnded: true }, { address: '0.0.0.0' }])
    assert.equal(roomEndpointText(withEndpoint({ ...endpoint, ...invalid }), room, current), '連線端點未確認');
  assert.equal(roomEndpointText(withEndpoint(endpoint), room, { ...current, state: 'Ended' }), '連線端點未確認');
  assert.equal(roomEndpointText(withEndpoint(endpoint), { ...room, sessionId: 'replacement' }, current), '連線端點未確認');
});
test('A managed ticket preview requires a current frame from its own endpoint', () => {
  const current = { ...session, combatStream: { streamId: 'stream' } };
  const endpoint = { version: 1, sessionId: current.id, streamId: 'stream', address: '127.0.0.1', port: 7777, sessionEnded: false };
  const snapshot = extra => ({ ...overview, rooms: [{ ...roomRow, endpoint, ticketSourceLive: true, sourceAgeMilliseconds: 4000, ...extra }] });
  assert.equal(roomTicketSourceLive(snapshot(), room, current, endpoint, 1000), true);
  assert.equal(roomTicketSourceLive(snapshot(), room, current, endpoint, 1001), false);
  assert.equal(roomTicketSourceLive(snapshot({ ticketSourceLive: false }), room, current, endpoint, 0), false);
  assert.equal(roomTicketSourceLive(snapshot(), room, current, { ...endpoint, port: 7778 }, 0), false);
  assert.equal(roomTicketSourceLive(snapshot({ sessionSequence: current.sequence - 1 }), room, current, endpoint, 0), false);
  assert.deepEqual(roomTicketDestination(snapshot(), room, current, 1001), { endpoint, live: false });
  assert.deepEqual(roomTicketDestination(snapshot({ ticketSourceLive: undefined }), room, current, 1001), { endpoint, live: null });
  assert.equal(roomTicketDestination(snapshot({ sessionSequence: current.sequence - 1 }), room, current, 0), null);
});
test('Venue confirmation requires its exact room, phase and fresh accepted world evidence', () => {
  const paused = { ...session, state: 'Paused' };
  const phase = { action: 'Pause', appliedAtSequence: 9, worldSequence: 12, readyToResume: true };
  const source = venuePhase => ({ ...overview, rooms: [{ ...roomRow, venuePhase }] });
  assert.deepEqual(roomVenuePhaseView(source(phase), room, paused, 1490),
    { applied: true, ready: true, action: 'Pause', sequence: 9, state: 'Ready', text: '全館暫停已套用 · 可繼續' });
  assert.match(roomVenuePhaseView(source({ ...phase, readyToResume: false }), room, paused, 0).text, /等候 MR/);
  assert.match(roomVenuePhaseView(source(phase), room, paused, 1490.01).text, /快照已過期/);
  assert.match(roomVenuePhaseView(source(phase), room, paused, 0, true).text, /未確認/);
  assert.equal(roomVenuePhaseView(source({ ...phase, worldSequence: null }), room, paused, 0).ready, false);
  assert.equal(roomVenuePhaseView(source(phase), room, { ...paused, sequence: 11 }, 0), null);
  assert.equal(roomVenuePhaseView(source(phase), room, { ...paused, state: 'Running' }, 0), null);
});
const timed = { ...session, state: 'Running', combatStream: { missionClockVersion: 1 }, mission: { definition: { durationSeconds: 60 } },
  missionClock: { version: 1, autoEnd: true } };
const timer = { phase: 'Running', elapsedSeconds: 20, remainingSeconds: 40, durationSeconds: 60, autoEnd: true };
const timeReport = (clock, fields = {}) => ({ ...overview, rooms: [{ ...roomRow, clock, ...fields }] });
test('Room countdown freezes on accepted seconds and respects manual, paused and due modes', () => {
  assert.deepEqual(roomMissionTimeView(timeReport(timer), room, timed, 1490), { state: 'Running', text: '剩餘 00:40 · 自動結束' });
  assert.equal(roomMissionTimeView(timeReport({ ...timer, phase: 'Paused' }), room, { ...timed, state: 'Paused' }, 0).text, '暫停 · 剩餘 00:40 · 自動結束');
  assert.equal(roomMissionTimeView(timeReport({ ...timer, autoEnd: false }), room, { ...timed, missionClock: null }, 0).text, '活動 00:20 / 01:00');
  assert.equal(roomMissionTimeView(timeReport({ ...timer, elapsedSeconds: 60, remainingSeconds: 0 }), room, timed, 0).state, 'Due');
  assert.equal(roomMissionTimeView(null, room, { ...timed, state: 'Preparing' }, 0).text, '尚未開始 · 計畫 01:00');
  assert.equal(roomMissionTimeView(null, room, { ...timed, combatStream: { missionClockVersion: 0 } }, 0).state, 'Unsupported');
});
test('Room time clears for stale responses, mismatched phase, policy or session and invalid seconds', () => {
  assert.equal(roomMissionTimeView(timeReport(timer), room, timed, 1490.01).state, 'Waiting');
  for (const change of [{ phase: 'Paused' }, { autoEnd: false }, { elapsedSeconds: -1 }, { remainingSeconds: 39 }, { durationSeconds: 61 }])
    assert.equal(roomMissionTimeView(timeReport({ ...timer, ...change }), room, timed, 0).state, 'Waiting');
  for (const fields of [{ sessionId: 'other' }, { sessionSequence: 9 }, { registered: 4 }, { sourceState: 'Suspended' }])
    assert.equal(roomMissionTimeView(timeReport(timer, fields), room, timed, 0).state, 'Waiting');
});
test('A fresh game suspension freezes time while management remains running', () => {
  const paused = timeReport({ ...timer, phase: 'Paused' }, { sourceState: 'Suspended' });
  assert.deepEqual(roomMissionTimeView(paused, room, timed, 1490),
    { state: 'Suspended', text: '遊戲來源暫停 · 剩餘 00:40 · 自動結束' });
  assert.equal(roomMissionTimeView(paused, room, timed, 1490.01).state, 'Waiting');
  assert.equal(roomMissionTimeView(paused, room, { ...timed, state: 'Paused' }, 0).state, 'Waiting');
  assert.equal(roomMissionTimeView(paused, room, timed, NaN).state, 'Waiting');
  const due = timeReport({ ...timer, phase: 'Paused', elapsedSeconds: 60, remainingSeconds: 0 }, { sourceState: 'Suspended' });
  assert.equal(roomMissionTimeView(due, room, timed, 0).state, 'Suspended');
});
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

test('Running VR room alerts identify unavailable seats and distinguish eliminated players', () => {
  const running = { ...session, state: 'Running', environment: { mode: 'VR' } };
  const participation = { awaitingAdmission: [1], awaitingPose: [3], eliminated: [5] };
  const overviewFor = (seats, changes = {}) => ({ ...overview, rooms: [{ ...roomRow, simulatedReady: 0, trackedReady: 0,
    vrParticipation: seats, ...changes }] });
  const result = roomReadinessView(overviewFor(participation), room, running, 0);
  assert.equal(result.text, '0 / 2 姿態有效 · 合成 0 · 追蹤 0 · 入場待同步席位 1 · 姿態待確認席位 3 · 已淘汰席位 5');
  assert.equal(result.attention, true);
  const ready = roomReadinessView(overviewFor({ awaitingAdmission: [], awaitingPose: [], eliminated: [5] }, { simulatedReady: 2 }), room, running, 0);
  assert.equal(ready.attention, false);
  assert.equal(ready.ready, 2);
  assert.equal(roomReadinessView(overview, room, running, 0).source, 'PhasePending');
  assert.equal(roomReadinessView(overviewFor(participation), room, running, 1500).source, 'Stale');
  for (const change of [{ awaitingAdmission: [3] }, { awaitingPose: [0] }, { eliminated: [] }, { eliminated: '5' }])
    assert.equal(roomReadinessView(overviewFor({ ...participation, ...change }), room, running, 0).source, 'Unavailable');
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
