export const MAX_RECORDING_BYTES = 25 * 1024 * 1024;
const phases = new Set(['Preparing', 'Running', 'Paused', 'Ended']);
const kinds = new Set(['ShotFired', 'ShotHit', 'EnemyEliminated', 'EnemyShot', 'PlayerDamaged', 'ReloadStarted', 'ReloadCompleted']);
function need(condition, message) { if (!condition) throw new Error('回放資料無效：' + message); }
function number(value, min, max) { return typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max; }
function integer(value, min, max) { return Number.isSafeInteger(value) && number(value, min, max); }
function guid(value) { return typeof value === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(value) && value !== '00000000-0000-0000-0000-000000000000'; }
function text(value, max) { return typeof value === 'string' && value.length <= max; }
function vector(value, bound = 100) { return value && number(value.x, -bound, bound) && number(value.y, -bound, bound) && number(value.z, -bound, bound); }
function unit(value) { return vector(value, 1.01) && Math.abs(Math.hypot(value.x, value.y, value.z) - 1) < .011; }
function roomPosition(value, room) { return vector(value) && Math.abs(value.x - (room - 3) * 14) <= 6.01 && Math.abs(value.z) <= 6.01; }

// Validate snapshots against their event boundary. Playback never reruns AI or guesses missing damage.
export function validateRecording(data) {
  need(data && data.schemaVersion === 2 && data.rulesVersion === '0.8.0', '需要 schema 2／rules 0.8.0，舊除錯檔請重新產生。');
  need(data.assetSet === undefined || ['primitives-v1', 'field-props-v1'].includes(data.assetSet), '不支援的素材版本。');
  need(data.origin === 'Simulation' && data.statistics?.origin === 'Simulation', '此版僅支援明確標記的 Simulation 紀錄。');
  need(guid(data.sessionId) && data.statistics.sessionId === data.sessionId, '場次身分不一致。');
  need(Array.isArray(data.roomIds) && [1, 5].includes(data.roomIds.length) && new Set(data.roomIds).size === data.roomIds.length && data.roomIds.every(r => integer(r, 1, 5)), '房間配置錯誤。');
  need(number(data.tickSeconds, .05, .05), '不支援的時間步。');
  need(text(data.mission?.definition?.name, 100) && text(data.mission.definition.briefing, 10000), '任務文字錯誤。');
  need(Array.isArray(data.frames) && data.frames.length >= 2 && data.frames.length <= 20000, '快照數量須為 2–20000。');
  need(Array.isArray(data.events) && data.events.length <= 100000, '事件數量超過上限。');
  need(Array.isArray(data.props) && data.props.length <= 2500, '物件數量超過上限。');
  need(Array.isArray(data.statistics.players) && data.statistics.players.length > 0 && data.statistics.players.length <= 25, '玩家統計錯誤。');
  const players = new Map(), enemies = new Map(), propIds = new Set(), entityIds = new Set();
  for (const player of data.statistics.players) {
    need(guid(player.playerId) && !entityIds.has(player.playerId) && text(player.name, 80) && data.roomIds.includes(player.roomId), '玩家身分或名稱錯誤。');
    players.set(player.playerId, player); entityIds.add(player.playerId);
  }
  for (const prop of data.props) {
    need(guid(prop.id) && !entityIds.has(prop.id) && data.roomIds.includes(prop.roomId) && ['Barrel', 'Sandbag'].includes(prop.kind)
      && roomPosition(prop.feet, prop.roomId) && number(prop.yaw, -100000, 100000), '場景物件不受支援。');
    propIds.add(prop.id); entityIds.add(prop.id);
  }
  let lastTick = -1, lastSequence = -1;
  for (const frame of data.frames) {
    need(integer(frame.tick, 0, 288000) && frame.tick >= lastTick && phases.has(frame.phase) && integer(frame.throughSequence, 0, data.events.length) && frame.throughSequence >= lastSequence, '快照時間或序號倒退。');
    need(['Hold', 'Patrol', 'Advance'].includes(frame.behavior) && ['Clear', 'Fog', 'Storm'].includes(frame.visibility) && typeof frame.night === 'boolean' && typeof frame.autoAttack === 'boolean', '快照環境或 AI 設定錯誤。');
    need(Array.isArray(frame.players) && frame.players.length <= 25 && Array.isArray(frame.enemies) && frame.enemies.length <= 100, '快照角色數量錯誤。');
    const ids = new Set(), seats = new Map();
    for (const player of frame.players) {
      const identity = players.get(player.id);
      need(identity && identity.roomId === player.roomId && !ids.has(player.id), '快照玩家身分不一致。'); ids.add(player.id);
      seats.set(player.roomId, (seats.get(player.roomId) || 0) + 1); need(seats.get(player.roomId) <= 5, '單房玩家超過五人。');
      need(roomPosition(player.head, player.roomId) && number(player.head.y, .45, 2.4) && roomPosition(player.muzzle, player.roomId) && number(player.muzzle.y, .1, 2.6) && unit(player.forward)
        && Math.hypot(player.head.x - player.muzzle.x, player.head.y - player.muzzle.y, player.head.z - player.muzzle.z) <= 1.201, '玩家姿態錯誤。');
      need(integer(player.health, 0, 100) && integer(player.magazine, 0, 30) && integer(player.reserve, 0, 90) && typeof player.reloading === 'boolean', '玩家血量或彈藥錯誤。');
    }
    for (const enemy of frame.enemies) {
      need(guid(enemy.id) && !ids.has(enemy.id) && !players.has(enemy.id) && !propIds.has(enemy.id) && data.roomIds.includes(enemy.roomId), '敵軍身分錯誤。'); ids.add(enemy.id);
      need(!enemies.has(enemy.id) || enemies.get(enemy.id) === enemy.roomId, '敵軍跨房間變更身分。'); enemies.set(enemy.id, enemy.roomId);
      need(roomPosition(enemy.feet, enemy.roomId) && Math.abs(enemy.feet.y) <= .001 && integer(enemy.health, 0, 100), '敵軍位置或血量錯誤。');
    }
    lastTick = frame.tick; lastSequence = frame.throughSequence;
  }
  need(data.frames[0].tick === 0 && data.frames[0].phase === 'Preparing' && data.frames[0].throughSequence === 0 && data.frames.at(-1).phase === 'Ended' && lastSequence === data.events.length, '紀錄須包含準備與結束快照及完整事件。');
  const metrics = new Map([...players].map(([id, identity]) => [id, { playerId: id, name: identity.name, roomId: identity.roomId, ammoUsed: 0, shotsHit: 0, kills: 0, hitsReceived: 0, damageTaken: 0, health: 100 }]));
  const eventIds = new Set(), shots = new Map(), eliminated = new Set(), enemyDamage = new Map(), causalEnemyDamage = new Map(), playerHealth = new Map([...players.keys()].map(id => [id, 100])), fireTicks = new Map(), enemyFireTicks = new Map();
  lastTick = -1;
  for (let i = 0; i < data.events.length; i++) {
    const event = data.events[i];
    need(event.sequence === i + 1 && guid(event.eventId) && !eventIds.has(event.eventId) && integer(event.tick, 0, data.frames.at(-1).tick) && event.tick >= lastTick && kinds.has(event.kind) && players.has(event.playerId), '事件身分、時間或連續序號錯誤。');
    eventIds.add(event.eventId); lastTick = event.tick;
    if (['ShotFired', 'EnemyShot'].includes(event.kind)) {
      need(vector(event.origin) && unit(event.direction) && number(event.distance, 0, event.kind === 'ShotFired' ? 40 : 15) && ['Miss', 'Cover', 'Friendly', 'Enemy'].includes(event.hit), '缺少已記錄射線或命中距離。');
      need(event.hit === 'Miss' ? event.targetId === null : guid(event.targetId), '射線目標錯誤。');
      if (event.hit === 'Cover') need(propIds.has(event.targetId), '射線掩體未記錄。');
      if (event.hit === 'Enemy') need(enemies.has(event.targetId), '射線敵軍未記錄。');
      if (event.hit === 'Friendly') need(players.has(event.targetId), '射線玩家未記錄。');
    }
    if (event.kind === 'ShotFired') {
      need(guid(event.shotId) && !shots.has(event.shotId) && playerHealth.get(event.playerId) > 0 && event.tick - (fireTicks.get(event.playerId) ?? -4) >= 4, '射擊 ID、射速或玩家狀態錯誤。');
      shots.set(event.shotId, { player: event.playerId, hit: null, rayHit: event.hit, target: event.targetId }); fireTicks.set(event.playerId, event.tick);
    }
    if (event.kind === 'ShotHit' || event.kind === 'EnemyEliminated') {
      const shot = shots.get(event.shotId);
      need(shot && shot.player === event.playerId && enemies.has(event.enemyId), '命中缺少對應射擊或敵軍。');
      if (event.kind === 'ShotHit') { need(!shot.hit && !eliminated.has(event.enemyId) && shot.rayHit === 'Enemy' && shot.target === event.enemyId && (causalEnemyDamage.get(event.enemyId) || 0) < 100, '射擊重複計分或與已記錄射線不符。'); shot.hit = event.enemyId; causalEnemyDamage.set(event.enemyId, (causalEnemyDamage.get(event.enemyId) || 0) + 50); }
      else { need(shot.hit === event.enemyId && !eliminated.has(event.enemyId) && causalEnemyDamage.get(event.enemyId) === 100, '擊殺缺少致命命中或重複。'); eliminated.add(event.enemyId); }
    }
    if (event.kind === 'EnemyShot') { need(enemies.has(event.enemyId) && !eliminated.has(event.enemyId) && event.hit === 'Friendly' && event.targetId === event.playerId && playerHealth.get(event.playerId) > 0
      && event.tick - (enemyFireTicks.get(event.enemyId) ?? -20) >= 20, '敵軍射擊身分、射速或目標錯誤。'); enemyFireTicks.set(event.enemyId, event.tick); }
    if (event.kind === 'PlayerDamaged') { const previous = data.events[i - 1]; need(integer(event.damage, 1, 20) && previous?.kind === 'EnemyShot' && previous.playerId === event.playerId && previous.enemyId === event.enemyId && previous.tick === event.tick, '傷害缺少對應敵軍射線。'); playerHealth.set(event.playerId, playerHealth.get(event.playerId) - event.damage); }
  }
  const frameStatistics = []; let eventIndex = 0;
  for (const frame of data.frames) {
    while (eventIndex < frame.throughSequence) {
      const event = data.events[eventIndex++], metric = metrics.get(event.playerId);
      need(event.tick <= frame.tick, '快照引用未來事件。');
      if (event.kind === 'ShotFired') metric.ammoUsed++;
      if (event.kind === 'ShotHit') { metric.shotsHit++; enemyDamage.set(event.enemyId, (enemyDamage.get(event.enemyId) || 0) + 50); }
      if (event.kind === 'EnemyEliminated') metric.kills++;
      if (event.kind === 'PlayerDamaged') { need(event.damage <= metric.health, '傷害超過剩餘血量。'); metric.hitsReceived++; metric.damageTaken += event.damage; metric.health -= event.damage; }
    }
    for (const player of frame.players) {
      const metric = metrics.get(player.id);
      need(player.health === metric.health && player.magazine + player.reserve === 120 - metric.ammoUsed, '快照血量／彈藥與事件不一致。');
    }
    for (const enemy of frame.enemies) need(enemy.health === Math.max(0, 100 - (enemyDamage.get(enemy.id) || 0)), '敵軍血量與事件不一致。');
    frameStatistics.push([...metrics.values()].map(metric => ({ ...metric, accuracyPercent: metric.ammoUsed ? Math.round(10000 * metric.shotsHit / metric.ammoUsed) / 100 : 0 })));
  }
  for (const computed of frameStatistics.at(-1)) {
    const stored = players.get(computed.playerId);
    for (const field of ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent']) need(stored[field] === computed[field], '結束統計與世界事件不一致。');
  }
  return { data, frameStatistics, duration: data.frames.at(-1).tick * data.tickSeconds };
}

// Return the final state for duplicate tick values; explicit frame stepping still reaches every sample.
export function frameAtTime(frames, seconds, tickSeconds) {
  let low = 0, high = frames.length - 1;
  while (low < high) { const middle = Math.ceil((low + high) / 2); if (frames[middle].tick * tickSeconds <= seconds + 1e-8) low = middle; else high = middle - 1; }
  return low;
}
