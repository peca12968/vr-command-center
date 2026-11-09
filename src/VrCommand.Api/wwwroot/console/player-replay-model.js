export const MAX_REPLAY_BYTES = 8 * 1024 * 1024;
export const MAX_REPLAY_FRAMES = 300;
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
function require(value) {
  if (!value) throw new Error('無法辨識回放檔，請使用場館匯出的完整片段。');
}

export function readPlayerReplay(data) {
  const { header, packets, startFrame, endFrame } = data ?? {};
  require(data?.playerReplayVersion === 1 && text(data.missionName, 120) && text(data.clipName, 60)
    && integer(startFrame, 1) && integer(endFrame, startFrame + 1)
    && list(packets, MAX_REPLAY_FRAMES) && packets.length === endFrame - startFrame + 1);
  require(header?.schemaVersion === 1 && guid(header.sessionId) && guid(header.streamId)
    && ['GameServer', 'Simulation'].includes(header.origin) && header.rulesVersion === '0.8.0'
    && [0, 1].includes(header.environmentVersion) && list(header.roomIds, 5)
    && [1, 5].includes(header.roomIds.length) && new Set(header.roomIds).size === header.roomIds.length
    && header.roomIds.every(room => integer(room, 1, 5)) && list(header.props, 2500)
    && header.props.every(prop => prop && header.roomIds.includes(prop.roomId) && point(prop.feet)
      && number(prop.yaw) && ['Sandbag', 'Barrel'].includes(prop.kind)));

  let elapsed = 0, tick = 0;
  for (const [index, packet] of packets.entries()) {
    const frame = packet?.frame;
    require(packet?.sequence === startFrame + index && integer(packet.elapsedMilliseconds, elapsed, 86400000)
      && weather.includes(packet.weather) && bool(packet.lightning) && list(packet.events, 500)
      && frame && integer(frame.tick, tick, header.environmentVersion === 1 ? 1728000 : Number.MAX_SAFE_INTEGER)
      && phase.includes(frame.phase) && bool(frame.night)
      && ['Clear', 'Fog', 'Storm'].includes(frame.visibility)
      && list(frame.players, 25) && list(frame.enemies, 100));
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
    require(packet.events.every(event => event && bool(event.hasRay) && (!event.hasRay
      || (point(event.origin) && point(event.direction) && number(event.distance) && event.distance >= 0))));
    elapsed = packet.elapsedMilliseconds;
    tick = frame.tick;
  }
  return data;
}
