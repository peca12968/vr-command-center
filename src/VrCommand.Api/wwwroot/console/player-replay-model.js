import { recordedPointInRoom } from './recorded-room.js';
import { eventNames } from './world-event-names.js';

export const MAX_REPLAY_BYTES = 8 * 1024 * 1024;
export const MAX_REPLAY_FRAMES = 300;
export const MAX_REPLAY_FILES = 24;
export const MAX_REPLAY_SET_BYTES = 64 * 1024 * 1024;
const phase = ['Preparing', 'Running', 'Paused', 'Ended'];
const weather = ['Clear', 'Rain', 'Fog', 'Storm'];
const guid = value => typeof value === 'string' && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(value);
const integer = (value, min, max = Number.MAX_SAFE_INTEGER) => Number.isSafeInteger(value) && value >= min && value <= max;
const text = (value, max) => typeof value === 'string' && value.length > 0 && value.length <= max;
const list = (value, max) => Array.isArray(value) && value.length <= max;
const number = value => Number.isFinite(value) && Math.abs(value) <= 1e6;
const point = value => value && [value.x, value.y, value.z].every(number);
const rotation = value => point(value) && number(value.w);
const bool = value => typeof value === 'boolean';
function require(value, message = '無法辨識回放檔，請使用場館匯出的完整片段。') {
  if (!value) throw new Error(message);
}

export function readPlayerReplay(data) {
  return validateReplay(data, MAX_REPLAY_FRAMES);
}

function validateReplay(data, maxFrames) {
  const { header, packets, startFrame, endFrame, playerReplayVersion, roomId } = data ?? {};
  const scoped = playerReplayVersion === 2;
  require((scoped || playerReplayVersion === 1) && text(data.missionName, 120) && text(data.clipName, 60)
    && integer(startFrame, 1) && integer(endFrame, startFrame + 1)
    && list(packets, maxFrames) && packets.length === endFrame - startFrame + 1);
  require(header?.schemaVersion === 1 && guid(header.sessionId) && guid(header.streamId)
    && ['GameServer', 'Simulation'].includes(header.origin) && header.rulesVersion === '0.8.0'
    && [0, 1].includes(header.environmentVersion) && list(header.roomIds, 5)
    && [1, 5].includes(header.roomIds.length) && new Set(header.roomIds).size === header.roomIds.length
    && header.roomIds.every(room => integer(room, 1, 5)) && list(header.props, 2500)
    && header.props.every(prop => prop && header.roomIds.includes(prop.roomId) && point(prop.feet)
      && number(prop.yaw) && ['Sandbag', 'Barrel'].includes(prop.kind)));
  require(scoped ? header.roomIds.length === 1 && roomId === header.roomIds[0] : roomId === undefined);
  if (scoped) require(header.props.every(prop => recordedPointInRoom(prop.feet, roomId, 6)),
    `回放檔的場景物件超出房間 ${roomId}，請重新取得場館匯出的片段。`);

  const eventRooms = data.eventRooms;
  if (eventRooms !== undefined) require(!scoped && header.roomIds.length > 1 && eventRooms !== null
    && typeof eventRooms === 'object' && !Array.isArray(eventRooms)
    && Object.entries(eventRooms).every(([id, room]) => guid(id) && header.roomIds.includes(room)));
  const unusedEvents = new Set(Object.keys(eventRooms ?? {}));
  let elapsed = 0, tick = 0;
  for (const [index, packet] of packets.entries()) {
    const frame = packet?.frame;
    require(packet?.sequence === startFrame + index && integer(packet.elapsedMilliseconds, elapsed, 86400000)
      && weather.includes(packet.weather) && bool(packet.lightning)
      && (packet.suspended === undefined || bool(packet.suspended)) && list(packet.events, 500)
      && frame && integer(frame.tick, tick, header.environmentVersion === 1 ? 1728000 : Number.MAX_SAFE_INTEGER)
      && phase.includes(frame.phase) && bool(frame.night)
      && ['Clear', 'Fog', 'Storm'].includes(frame.visibility)
      && list(frame.players, 25) && list(frame.enemies, 100));
    if (scoped) require(!('observedSequence' in packet) && !('throughCombatSequence' in packet) && !('throughSequence' in frame));
    const actors = new Set();
    for (const player of frame.players) {
      const rig = player?.rig;
      require(player && guid(player.id) && !actors.has(player.id) && header.roomIds.includes(player.roomId)
        && point(player.head) && point(player.forward) && point(player.muzzle) && integer(player.health, 0, 100)
        && rig && ['None', 'Simulated', 'Tracked'].includes(rig.kind) && point(rig.left) && point(rig.right)
        && [rig.headRotation, rig.leftRotation, rig.rightRotation].every(rotation)
        && (!player.hasFireState || (point(player.fireOrigin) && point(player.fireDirection))));
      actors.add(player.id);
    }
    for (const enemy of frame.enemies) {
      require(enemy && guid(enemy.id) && !actors.has(enemy.id) && header.roomIds.includes(enemy.roomId)
        && point(enemy.feet) && integer(enemy.health, 0, 100) && (!enemy.hasPresentation || point(enemy.forward))
        && (!enemy.hasFireState || (point(enemy.fireOrigin) && point(enemy.fireDirection))));
      actors.add(enemy.id);
    }
    require(packet.events.every(event => event && typeof event === 'object' && (!scoped || !('sequence' in event)) && bool(event.hasRay) && (!event.hasRay
      || (point(event.origin) && point(event.direction) && number(event.distance) && event.distance >= 0))));
    if (scoped) require(packet.events.every(event => !event.hasRay || recordedPointInRoom(event.origin, roomId, 6.01)),
      `回放檔的射線起點超出房間 ${roomId}，請重新取得場館匯出的片段。`);
    if (eventRooms) for (const event of packet.events) {
      if (Object.hasOwn(eventRooms, event.eventId))
        require(unusedEvents.delete(event.eventId) && !frame.players.some(player => player.id === event.playerId));
    }
    elapsed = packet.elapsedMilliseconds;
    tick = frame.tick;
  }
  require(unusedEvents.size === 0);
  return data;
}

function sameJson(left, right) {
  if (left === right) return true;
  if (!left || !right || typeof left !== 'object' || typeof right !== 'object' || Array.isArray(left) !== Array.isArray(right)) return false;
  const keys = Object.keys(left);
  return keys.length === Object.keys(right).length && keys.every(key => Object.hasOwn(right, key) && sameJson(left[key], right[key]));
}

export function samePlayerReplaySource(left, right) {
  return left.playerReplayVersion === right.playerReplayVersion && left.roomId === right.roomId &&
    sameJson(left.header, right.header);
}

export function readPlayerReplaySet(documents) {
  require(documents.length && documents.length <= MAX_REPLAY_FILES, '請一次選擇 1 至 24 份回放檔。');
  const clips = documents.map(readPlayerReplay).sort((a, b) => a.startFrame - b.startFrame || a.endFrame - b.endFrame);
  const first = clips[0];
  const segments = clips.map(({ clipName, startFrame, endFrame }) => ({ clipName, startFrame, endFrame }));
  if (clips.length === 1) return { replay: first, segments };
  const packets = [], eventRooms = {};
  for (const clip of clips) {
    require(samePlayerReplaySource(clip, first), '請選擇同一場錄製、相同房間範圍的回放檔。');
    const next = first.startFrame + packets.length;
    require(clip.startFrame <= next, `缺少第 ${next} 至 ${clip.startFrame - 1} 格，請一併選取涵蓋這段的回放檔。`);
    for (const packet of clip.packets) {
      const saved = packets[packet.sequence - first.startFrame];
      if (saved) require(sameJson(saved, packet), `片段的第 ${packet.sequence} 格內容不同，請重新取得原錄製匯出檔。`);
      else packets.push(packet);
    }
    for (const [id, room] of Object.entries(clip.eventRooms ?? {})) {
      require(!Object.hasOwn(eventRooms, id) || eventRooms[id] === room, '片段對同一事件記載的房號不同。');
      eventRooms[id] = room;
    }
  }
  const replay = { ...first, packets, endFrame: packets.at(-1).sequence };
  if (Object.keys(eventRooms).length) replay.eventRooms = eventRooms;
  // Recheck the timeline and event ownership across boundaries as one recording.
  return { replay: validateReplay(replay, MAX_REPLAY_FRAMES * MAX_REPLAY_FILES), segments };
}

export function sourcePaused(packet) {
  return packet?.suspended === true && packet.frame.phase === 'Paused';
}

export function playerReplayPlayers(packets) {
  const players = new Map();
  const roomCounts = new Map();
  for (const { frame } of packets) {
    for (const { id, roomId } of frame.players) {
      if (players.has(id)) continue;
      const number = (roomCounts.get(roomId) ?? 0) + 1;
      roomCounts.set(roomId, number);
      players.set(id, { id, roomId, number });
    }
  }
  return [...players.values()].sort((left, right) => left.roomId - right.roomId || left.number - right.number);
}

export function playerReplayEventFrames(packets, playerIds = null, roomId = null, eventRooms = {}) {
  const frames = [];
  for (const [index, packet] of packets.entries()) {
    const counts = {};
    for (const { kind, playerId, eventId } of packet.events) {
      if (playerIds) {
        const savedRoom = Object.hasOwn(eventRooms, eventId) ? eventRooms[eventId] : undefined;
        if (savedRoom !== undefined ? savedRoom !== roomId : !playerIds.has(playerId)) continue;
      }
      if (typeof kind === 'string' && Object.hasOwn(eventNames, kind)) counts[kind] = (counts[kind] || 0) + 1;
    }
    if (Object.keys(counts).length) frames.push({ index, counts });
  }
  return frames;
}

export function sourceTransitions(packets, previousTail = null) {
  const rows = [];
  for (const [index, packet] of packets.entries()) {
    const previous = index === 0 ? previousTail : packets[index - 1];
    if (sourcePaused(packet) && !sourcePaused(previous)) rows.push({ index, suspended: true });
    if (previous?.suspended === true && packet.suspended !== true && packet.frame.phase === 'Running')
      rows.push({ index, suspended: false });
  }
  return rows;
}
