import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readPlayerReplay, sourcePaused, sourceTransitions } from '../../src/VrCommand.Api/wwwroot/console/player-replay-model.js';

const point = { x: 0, y: 0, z: 0 };
const actor = '71100000-0000-0000-0000-000000000000';
function replay(version, rooms) {
  const header = { schemaVersion: 1, environmentVersion: 1, rulesVersion: '0.8.0', origin: 'GameServer',
    sessionId: actor, streamId: '82200000-0000-0000-0000-000000000000', roomIds: rooms,
    props: [{ roomId: 3, kind: 'Barrel', feet: point, yaw: 0 }] };
  const packets = [10, 11].map((sequence, index) => ({
    sequence, elapsedMilliseconds: 1000 + index * 100, weather: 'Clear', lightning: false,
    frame: { tick: 22 + index, phase: 'Running', night: false, visibility: 'Clear', players: [],
      enemies: [{ id: actor, roomId: 3, feet: point, health: 100 }] },
    events: [{ hasRay: true, origin: point, direction: { x: 1, y: 0, z: 0 }, distance: 2 }]
  }));
  return { playerReplayVersion: version, ...(version === 2 ? { roomId: 3 } : {}), missionName: 'Mission', clipName: 'Clip',
    startFrame: 10, endFrame: 11, header, packets };
}

test('keeps original contiguous timing in both full and room player files', () => {
  for (const file of [replay(1, [1, 2, 3, 4, 5]), replay(2, [3])])
    assert.equal(readPlayerReplay(file), file);
});

test('finds saved source pauses and running recoveries without counting an operator pause', () => {
  const packets = [
    { frame: { phase: 'Paused' } },
    { frame: { phase: 'Running' } },
    { suspended: true, frame: { phase: 'Paused' } },
    { suspended: true, frame: { phase: 'Paused' } },
    { suspended: false, frame: { phase: 'Running' } },
    { suspended: true, frame: { phase: 'Paused' } },
    { suspended: false, frame: { phase: 'Ended' } }
  ];
  assert.deepEqual(sourceTransitions(packets), [
    { index: 2, suspended: true }, { index: 4, suspended: false }, { index: 5, suspended: true }
  ]);
  assert.deepEqual(sourceTransitions(packets.slice(3, 5)), [{ index: 0, suspended: true }, { index: 1, suspended: false }]);
  assert.equal(sourcePaused(packets[0]), false);
});

test('keeps the optional suspension flag in both replay formats and rejects invalid types', () => {
  for (const file of [replay(1, [1, 2, 3, 4, 5]), replay(2, [3])]) {
    file.packets[0].suspended = true;
    file.packets[0].frame.phase = 'Paused';
    assert.equal(readPlayerReplay(file), file);
    file.packets[0].suspended = 'true';
    assert.throws(() => readPlayerReplay(file), /無法辨識回放檔/);
  }
});

test('rejects disagreement between scoped room, geometry or recorded actors', () => {
  for (const corrupt of [
    file => { file.roomId = 4; },
    file => { file.header.roomIds = [1, 2, 3, 4, 5]; },
    file => { file.header.props[0].roomId = 4; },
    file => { file.packets[0].frame.enemies[0].roomId = 4; }
  ]) {
    const file = replay(2, [3]); corrupt(file);
    assert.throws(() => readPlayerReplay(file), /無法辨識回放檔/);
  }
});

test('rejects global event boundaries and invalid event rows in a room file', () => {
  for (const corrupt of [
    file => { file.packets[0].observedSequence = 7; },
    file => { file.packets[0].throughCombatSequence = 9; },
    file => { file.packets[0].frame.throughSequence = 8; },
    file => { file.packets[0].events[0].sequence = 8; },
    file => { file.packets[0].events[0] = 'not an event'; }
  ]) {
    const file = replay(2, [3]); corrupt(file);
    assert.throws(() => readPlayerReplay(file), /無法辨識回放檔/);
  }
});

test('rejects out-of-room prop positions and ray origins in a player room replay', () => {
  for (const corrupt of [
    file => { file.header.props[0].feet = { ...point, x: 14 }; },
    file => { file.header.props[0].feet = { ...point, z: -6.001 }; },
    file => { file.packets[1].events[0].origin = { ...point, x: -14 }; },
    file => { file.packets[1].events[0].origin = { ...point, z: 6.011 }; }
  ]) {
    const file = replay(2, [3]); corrupt(file);
    assert.throws(() => readPlayerReplay(file), /超出房間 3/);
  }
});

test('keeps native room boundary rays and full replay compatibility', () => {
  const room = replay(2, [5]);
  room.roomId = 5;
  room.header.props[0] = { ...room.header.props[0], roomId: 5, feet: { ...point, x: 34, z: -6 } };
  for (const packet of room.packets) {
    packet.frame.enemies[0].roomId = 5;
    packet.frame.enemies[0].feet = { ...point, x: 28 };
    packet.events[0].origin = { ...point, x: 34.009998, z: Math.fround(-6.01) };
    packet.events[0].distance = 20;
  }
  assert.equal(readPlayerReplay(room), room);
  const full = replay(1, [1, 2, 3, 4, 5]);
  full.packets[0].events[0].origin = { ...point, x: 28 };
  assert.equal(readPlayerReplay(full), full);
});
