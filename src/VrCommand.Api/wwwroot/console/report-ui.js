import { csvReportAccuracy, csvReportText, matchesReportRows } from './report-csv.js';

export const venueScoreFields = ['players', 'ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken'];

const finalColumns = ['reportVersion', 'rowType', 'sessionId', 'missionId', 'missionName', 'sessionMode', 'roomIds',
  'createdAtUtc', 'startedAtUtc', 'endedAtUtc', 'plannedDurationSeconds', 'throughSequence', 'origin', 'streamId',
  'finalStreamSequence', 'playerId', 'playerName', 'playerRoomId', 'ammoUsed', 'shotsHit', 'kills', 'damageTaken',
  'hitsReceived', 'accuracyPercent', 'health'];

function csvUtc(value) {
  if (value == null) return null;
  const parts = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!parts) return () => false;
  const [, clock, fraction = '', offset] = parts;
  const utc = new Date(clock + offset);
  return Number.isFinite(utc.getTime()) ? utc.toISOString().slice(0, 19) + '.' + fraction.padEnd(7, '0') + '+00:00' : () => false;
}

function matchesFinalCsv(bytes, { session, statistics }, roomId, playerId) {
  const { mission, combatStream } = session;
  const scope = [session.id, mission.id, csvReportText(mission.definition.name), session.mode, session.roomIds.join('|'),
    csvUtc(session.createdAtUtc), csvUtc(session.startedAtUtc), csvUtc(session.endedAtUtc), mission.definition.durationSeconds,
    statistics.throughSequence, statistics.origin ?? combatStream?.origin ?? 'None', combatStream?.streamId, combatStream?.acceptedSequence];
  const players = statistics.players.filter(player => (roomId === null || player.roomId === roomId)
    && (playerId === null || player.playerId === playerId));
  if (playerId && players.length !== 1) return false;
  const rows = players.length ? players.map(player => [1, 'Player', ...scope, player.playerId, csvReportText(player.name),
    player.roomId, player.ammoUsed, player.shotsHit, player.kills, player.damageTaken, player.hitsReceived,
    csvReportAccuracy(player.accuracyPercent), player.health]) : [[1, 'Session', ...scope, ...Array(10).fill(null)]];
  return roomId === null ? matchesReportRows(bytes, [finalColumns, ...rows])
    : matchesReportRows(bytes, [[...finalColumns, 'reportRoomId'], ...rows.map(row => [...row, roomId])]);
}

function venueScoreCsv(scores) {
  const header = ['reportVersion', 'rowType', 'requestId', 'sessionId', 'roomId', ...venueScoreFields, 'accuracyPercent'];
  const row = (type, session, room, totals) => [1, type, scores.requestId, session, room,
    ...venueScoreFields.map(field => totals[field]), totals.accuracyPercent];
  const rooms = scores.rooms.map(room => row('Room', room.sessionId, room.roomId, room.totals));
  return '\uFEFF' + [header, ...rooms, row('Total', '', '', scores.total)]
    .map(cells => cells.map(cell => `"${cell}"`).join(',') + '\r\n').join('');
}

export function mountReport(current, unauthorized, scopeChanged) {
  const button = document.getElementById('export-report'), status = document.getElementById('report-status');
  const bundle = document.getElementById('export-report-bundle');
  const roomField = document.getElementById('report-room-field'), room = document.getElementById('report-room');
  const playerPicker = document.getElementById('player-review-select'), playerButton = document.getElementById('export-player-report');
  let generation = 0, controller = null, availability = null, scopeIdentity = '';
  let playerShown = false, requestedPlayer = null;
  const ready = value => value.actor && value.session?.state === 'Ended' &&
    value.statistics?.sessionId === value.session.id && value.statistics.throughSequence === value.session.sequence &&
    !value.statistics.pendingTelemetry;
  const linked = value => value.actor && value.session?.mode === 'Linked';
  const canBundle = value => linked(value) && value.actor.role === 'Master';
  const scope = value => !linked(value) ? null : value.actor.role === 'RoomController' ? value.actor.roomId : Number(room.value) || null;
  const roomId = () => scope(current());
  function players() {
    const value = current();
    if (!value.session || value.statistics?.sessionId !== value.session.id) return [];
    const id = scope(value);
    return id === null ? value.statistics.players : value.statistics.players.filter(player => player.roomId === id);
  }
  const canExportPlayer = () => !current().pending && ready(current());
  function updatePlayer(shown = playerShown) {
    playerShown = shown;
    const eligible = shown && canExportPlayer() && players().some(player => player.playerId === playerPicker.value);
    if (requestedPlayer && (!eligible || playerPicker.value !== requestedPlayer)) {
      generation++; controller.abort(); controller = null; requestedPlayer = null;
      status.textContent = availability ?? '';
    }
    playerButton.disabled = !eligible || !!controller;
  }
  function update(shown = playerShown) {
    const value = current();
    const identity = linked(value) ? value.epoch + '/' + value.session.id : '';
    if (identity !== scopeIdentity) {
      scopeIdentity = identity;
      roomField.hidden = !identity;
      room.replaceChildren();
      if (identity) {
        if (value.actor.role === 'Master') room.add(new Option('全場', ''));
        for (const id of value.session.roomIds)
          if (value.actor.role === 'Master' || id === value.actor.roomId) room.add(new Option(`房間 ${id}`, String(id)));
      }
    }
    updatePlayer(shown);
    button.disabled = !!controller || !ready(value);
    bundle.hidden = !canBundle(value);
    bundle.disabled = bundle.hidden || button.disabled;
    room.disabled = !!controller || !identity || value.actor.role !== 'Master';
    const roomId = scope(value);
    const next = ready(value) ? (roomId ? `房間 ${roomId} 的戰鬥統計已完成，可下載 CSV（含離場玩家）。` : '戰鬥統計已完成，可下載 CSV（含離場玩家）。')
      : value.session?.state === 'Ended' ? '等待戰鬥資料確認封存後才可匯出。' : '結束任務並完成戰鬥封存後可匯出。';
    if (!controller && next !== availability) status.textContent = next;
    availability = next;
  }
  function reset() {
    generation++; controller?.abort(); controller = null; availability = null; scopeIdentity = '';
    playerShown = false; requestedPlayer = null; playerButton.disabled = true;
    status.textContent = ''; button.disabled = true; room.disabled = true; roomField.hidden = true; room.replaceChildren();
    bundle.hidden = bundle.disabled = true;
  }
  room.addEventListener('change', () => { availability = null; update(); scopeChanged(); });
  async function download(allRooms, playerId = null) {
    const value = current();
    if (controller || !ready(value) || (allRooms && !canBundle(value))) return;
    const attempt = ++generation, epoch = value.epoch, id = value.session.id, roomId = scope(value);
    const active = () => attempt === generation && current().epoch === epoch && current().session?.id === id
      && (allRooms ? canBundle(current()) : scope(current()) === roomId)
      && (!playerId || (playerShown && playerPicker.value === playerId && canExportPlayer()));
    const suffix = roomId === null ? '' : '-room-' + String(roomId).padStart(2, '0');
    const path = playerId ? `/players/${playerId}/report.csv` : allRooms ? '/reports.zip'
      : `${roomId === null ? '' : `/rooms/${roomId}`}/report.csv`;
    const request = new AbortController(); controller = request;
    requestedPlayer = playerId;
    const timeout = setTimeout(() => request.abort(), 8000);
    update(); status.textContent = allRooms ? '正在下載五房戰績 ZIP…' : '正在下載最終報表…';
    try {
      const response = await fetch(`/api/sessions/${id}${path}`, {
        headers: { Authorization: 'Bearer ' + value.key }, cache: 'no-store', signal: request.signal
      });
      if (!active()) return;
      if (!response.ok) {
        if (response.status === 401) { unauthorized(); return; }
        throw new Error(response.status === 409 ? '任務或戰鬥封存尚未完成，請更新後再匯出。'
          : response.status === 403 ? '目前身分沒有此場次的報表權限。' : '報表下載失敗，請更新後重試。');
      }
      const mediaType = allRooms ? 'application/zip' : 'text/csv';
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== mediaType) throw new Error('報表格式不符，請更新後重試。');
      const blob = await response.blob();
      if (!active()) return;
      if (!allRooms) {
        const bytes = await blob.arrayBuffer();
        if (!active()) return;
        const latest = current();
        if (!ready(latest) || !matchesFinalCsv(bytes, latest, playerId ? null : roomId, playerId))
          throw new Error('CSV 與目前場次的封存戰績不符，可重新下載。');
      }
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      try {
        link.href = url; link.download = allRooms ? `vr-command-reports-v1-${id}.zip`
          : `vr-command-report-v1-${id}${playerId ? `-player-${playerId}` : suffix}.csv`;
        document.body.append(link); link.click();
      } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
      status.textContent = playerId ? '已下載所選玩家的最終戰績。' : allRooms ? '已下載全場及五份分房戰績 CSV。'
        : '最終報表已下載；來源與封存序號列於 CSV。';
    } catch (error) {
      if (active()) status.textContent = request.signal.aborted ? '下載逾時或已中止，可重新下載。' : error.message;
    } finally {
      clearTimeout(timeout);
      if (attempt === generation) { controller = null; requestedPlayer = null; update(); }
    }
  }
  button.addEventListener('click', () => download(false));
  bundle.addEventListener('click', () => download(true));
  playerButton.addEventListener('click', () => { if (!playerButton.disabled) void download(false, playerPicker.value); });
  return { update, reset, roomId, players, canExportPlayer };
}

export function mountVenueReport(current, unauthorized, save) {
  const reports = mountVenueDownload(current, unauthorized, save, {
    actions: 'venue-report-actions', button: 'export-venue-reports', status: 'venue-report-status',
    route: 'reports', filename: 'reports',
    ready: session => ['Sealed', 'NoSource'].includes(session.combat),
    waiting: rooms => `等待房間 ${rooms} 的戰鬥資料封存。`,
    available: '本批戰績已可匯出。', loading: '正在下載本批戰績 ZIP…',
    conflict: '本批仍在等待戰鬥資料封存。', invalid: '報表格式不符，可重新下載。',
    failed: '本批戰績下載失敗，可重新整理後再試。', saved: '已下載本批戰績與原場次清單。'
  });
  const scores = mountVenueDownload(current, unauthorized, save, {
    actions: 'venue-score-actions', button: 'export-venue-scores', status: 'venue-score-status',
    route: 'scores', filename: 'scores', extension: 'csv', mediaType: 'text/csv', verifyContent: true,
    ready: session => ['Sealed', 'NoSource'].includes(session.combat),
    available: '', loading: '正在下載分房合計 CSV…',
    conflict: '本批仍在等待戰鬥資料封存。', invalid: '分房合計 CSV 與目前批次戰績不符，可重新下載。',
    failed: '分房合計下載失敗，可重新整理後再試。', saved: '已下載各房與全批戰績合計。'
  });
  const field = mountVenueDownload(current, unauthorized, save, {
    actions: 'venue-field-actions', button: 'export-venue-field', status: 'venue-field-status',
    route: 'field-evidence', filename: 'field',
    ready: session => session.fieldEvidenceReady === true,
    waiting: rooms => `房間 ${rooms} 缺少開場紀錄、雙封存、公告端點或完整名冊。`,
    available: '本批場館驗收資料已可匯出。', loading: '正在下載本批場館驗收 ZIP…',
    conflict: '本批場館驗收資料尚未齊備。', invalid: '場館驗收 ZIP 格式不符，可重新下載。',
    failed: '本批場館驗收 ZIP 下載失敗，可重新整理後再試。', saved: '已下載原批次與各場驗收資料，請私下保管。'
  });
  const fieldWithReceipts = mountVenueDownload(current, unauthorized, save, {
    actions: 'venue-field-receipt-actions', button: 'export-venue-field-with-receipts', status: 'venue-field-receipt-status',
    route: 'field-evidence', query: '?includeDebriefReceipts=true', filename: 'field-with-receipts',
    waitingRooms: (session, rooms) => session.roomIds.filter(room => {
      const info = rooms?.get(room);
      return !session.fieldEvidenceReady || !info || info.confirmedCount !== info.rosterCount;
    }),
    waiting: rooms => `等待房間 ${rooms} 的驗收資料及全員回條。`,
    available: '', loading: '正在下載驗收 ZIP 與全員回條…',
    conflict: '本批驗收資料或全員回條尚未齊備，請更新後重試。', invalid: '驗收 ZIP 格式不符，可重新下載。',
    failed: '驗收 ZIP 下載失敗，可重新整理後再試。', saved: '已下載本批驗收資料與全員確認回條，請私下保管。'
  });
  const debrief = mountVenueDownload(current, unauthorized, save, {
    actions: 'venue-debrief-actions', button: 'export-venue-debrief', status: 'venue-debrief-status',
    route: 'debrief-receipts', filename: 'debrief-receipts', extension: 'json', mediaType: 'application/json',
    ready: session => session.combat === 'Sealed' && session.world === 'Sealed',
    waiting: rooms => `等待房間 ${rooms} 的戰鬥與世界封存。`,
    available: '可保存本批目前的回條狀態。', loading: '正在下載本批戰績回條…',
    conflict: '本批尚未完成雙封存。', invalid: '戰績回條格式不符，可重新下載。',
    failed: '本批戰績回條下載失敗，可重新整理後再試。', saved: '已下載本批戰績回條，請私下保管。'
  });
  return { update(batch, totals, receipts) {
    reports(batch); field(batch); fieldWithReceipts(batch, null, receipts); debrief(batch);
    scores(batch, totals ? venueScoreCsv(totals) : null);
  } };
}

function mountVenueDownload(current, unauthorized, save, options) {
  const { extension = 'zip', mediaType = 'application/zip' } = options;
  const actions = document.getElementById(options.actions);
  const button = document.getElementById(options.button), status = document.getElementById(options.status);
  let id = null, waiting = '', controller = null, content = null;
  const updateButton = () => { button.disabled = !id || !!waiting || !!controller; };
  function update(batch, expected = null, context = null) {
    const nextId = (!options.verifyContent || expected !== null) && current().actor?.role === 'Master'
      && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(batch?.requestId ?? '')
      ? batch.requestId : null;
    const nextWaiting = nextId ? batch.sessions.flatMap(session => options.waitingRooms
      ? options.waitingRooms(session, context) : options.ready(session) ? [] : session.roomIds)
      .sort((a, b) => a - b).join('、') : '';
    if (id !== nextId || waiting !== nextWaiting || content !== expected) {
      controller?.abort(); controller = null;
      id = nextId; waiting = nextWaiting; content = expected;
      status.textContent = !id ? '' : waiting ? options.waiting(waiting) : options.available;
    }
    actions.hidden = !id;
    updateButton();
  }
  button.addEventListener('click', async () => {
    const { actor, epoch, key } = current(), batchId = id, expected = content;
    if (!batchId || waiting || controller || actor?.role !== 'Master') return;
    const request = new AbortController(); controller = request;
    const active = () => controller === request && id === batchId && current().epoch === epoch;
    const timeout = setTimeout(() => request.abort(), 8000);
    updateButton(); status.textContent = options.loading;
    try {
      const response = await fetch(`/api/venue/closure/${batchId}/${options.route}.${extension}${options.query ?? ''}`, {
        headers: { Authorization: 'Bearer ' + key }, signal: request.signal, cache: 'no-store'
      });
      if (!active()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error(response.status === 409 ? options.conflict : options.failed);
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== mediaType)
        throw new Error(options.invalid);
      const blob = await response.blob();
      if (!active()) return;
      if (expected !== null) {
        if (blob.size !== expected.length + 2) throw new Error(options.invalid); // The UTF-8 BOM occupies three bytes.
        const csv = new TextDecoder('utf-8', { ignoreBOM: true }).decode(await blob.arrayBuffer());
        if (!active()) return;
        if (csv !== expected) throw new Error(options.invalid);
      }
      save(`vr-command-venue-${options.filename}-v1-${batchId}.${extension}`, blob);
      status.textContent = options.saved;
    } catch (error) {
      if (active()) status.textContent = request.signal.aborted ? '下載逾時，可重新下載。' : error.message;
    } finally {
      clearTimeout(timeout);
      if (controller === request) { controller = null; updateButton(); }
    }
  });
  return update;
}
