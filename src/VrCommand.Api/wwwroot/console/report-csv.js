const finalColumns = ['reportVersion', 'rowType', 'sessionId', 'missionId', 'missionName', 'sessionMode', 'roomIds',
  'createdAtUtc', 'startedAtUtc', 'endedAtUtc', 'plannedDurationSeconds', 'throughSequence', 'origin', 'streamId',
  'finalStreamSequence', 'playerId', 'playerName', 'playerRoomId', 'ammoUsed', 'shotsHit', 'kills', 'damageTaken',
  'hitsReceived', 'accuracyPercent', 'health'];

function finalPlayerFields(player) {
  return [player.playerId, csvReportText(player.name), player.roomId, player.ammoUsed, player.shotsHit, player.kills,
    player.damageTaken, player.hitsReceived, csvReportAccuracy(player.accuracyPercent), player.health];
}

function csvUtc(value) {
  if (value == null) return null;
  const parts = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!parts) return () => false;
  const [, clock, fraction = '', offset] = parts;
  const utc = new Date(clock + offset);
  return Number.isFinite(utc.getTime()) ? utc.toISOString().slice(0, 19) + '.' + fraction.padEnd(7, '0') + '+00:00' : () => false;
}

export function matchesFinalCsv(bytes, { session, statistics }, roomId, playerId) {
  const { mission, combatStream } = session;
  const scope = [session.id, mission.id, csvReportText(mission.definition.name), session.mode, session.roomIds.join('|'),
    csvUtc(session.createdAtUtc), csvUtc(session.startedAtUtc), csvUtc(session.endedAtUtc), mission.definition.durationSeconds,
    statistics.throughSequence, statistics.origin ?? combatStream?.origin ?? 'None', combatStream?.streamId, combatStream?.acceptedSequence];
  const players = statistics.players.filter(player => (roomId === null || player.roomId === roomId)
    && (playerId === null || player.playerId === playerId));
  if (playerId && players.length !== 1) return false;
  const rows = players.length ? players.map(player => [1, 'Player', ...scope, ...finalPlayerFields(player)])
    : [[1, 'Session', ...scope, ...Array(10).fill(null)]];
  return roomId === null ? matchesReportRows(bytes, [finalColumns, ...rows])
    : matchesReportRows(bytes, [[...finalColumns, 'reportRoomId'], ...rows.map(row => [...row, roomId])]);
}

export function matchesDebriefCsv(bytes, { playerId, name, room, throughSequence, throughCombatSequence, score }) {
  // Mission metadata is not part of the seat view. Check the exact schema and the sealed values it provides.
  const metadata = () => true;
  const row = [1, 'Player', room.sessionId, ...Array(8).fill(metadata), throughSequence, metadata,
    room.streamId, throughCombatSequence, ...finalPlayerFields({ ...score, playerId, name, roomId: room.roomId })];
  return matchesReportRows(bytes, [finalColumns, row]);
}

export function encodeUnconfirmedSeatsCsv(batchId, players) {
  const rows = [['reportVersion', 'requestId', 'sessionId', 'streamId', 'roomId', 'seat', 'throughSequence',
    'finalStreamSequence', 'worldSequence', 'playerId', 'playerName', 'acknowledged', 'ammoUsed', 'shotsHit',
    'kills', 'hitsReceived', 'damageTaken', 'accuracyPercent', 'health']];
  for (const player of players) {
    if (player.acknowledged) continue;
    const { room, seat, throughSequence, throughCombatSequence, playerId, name, score } = player;
    rows.push([1, batchId, room.sessionId, room.streamId, room.roomId, seat, throughSequence, throughCombatSequence,
      room.worldSequence, playerId, csvReportText(name), false, score.ammoUsed, score.shotsHit, score.kills,
      score.hitsReceived, score.damageTaken, score.accuracyPercent, score.health]);
  }
  return encodeReportRows(rows);
}

export function encodeReportRows(rows) {
  return '\uFEFF' + rows.map(row => row.map(cell => `"${String(cell).replaceAll('"', '""')}"`).join(',') + '\r\n').join('');
}

export function csvReportText(value) {
  return /\p{Cc}|^\p{White_Space}*[=+@-]/u.test(value) ? "'" + value : value;
}

export function csvReportAccuracy(value) {
  return actual => /^(?:0|[1-9]\d{0,2})(?:\.\d{1,2})?$/.test(actual) && Number(actual) === value;
}

export function matchesReportRows(bytes, rows) {
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { return false; }
  if (text[0] !== '\uFEFF') return false;
  // The server quotes every cell, including empty fields and multiline names.
  const field = /"((?:[^"]|"")*)"(,|\r\n)/y;
  field.lastIndex = 1;
  return rows.every(row => row.every((expected, index) => {
    const cell = field.exec(text);
    if (!cell || cell[2] !== (index === row.length - 1 ? '\r\n' : ',')) return false;
    const actual = cell[1].replaceAll('""', '"');
    return typeof expected === 'function' ? expected(actual) : actual === String(expected ?? '');
  })) && field.lastIndex === text.length;
}
