const $ = id => document.getElementById(`world-clip-stats-${id}`);
const metrics = ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken'];
const playerIdPattern = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const csvColumns = ['reportVersion', 'rowType', 'sessionId', 'streamId', 'fromFrame', 'throughFrame',
  'reportRoomId', 'reportPlayerId', 'playerId', 'playerName', 'playerRoomId', 'ammoUsed', 'shotsHit', 'matchedShots',
  'kills', 'hitsReceived', 'damageTaken', 'accuracyPercent'];

export function matchesClipCsv(bytes, report) {
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { return false; }
  if (text[0] !== '\uFEFF') return false;
  // The server quotes every cell, including empty fields and multiline names.
  const field = /"((?:[^"]|"")*)"(,|\r\n)/y;
  field.lastIndex = 1;
  function matchesRow(expected, hasAccuracy = false) {
    return expected.every((value, index) => {
      const cell = field.exec(text);
      const last = index === expected.length - 1;
      if (!cell || cell[2] !== (last ? '\r\n' : ',')) return false;
      const actual = cell[1].replaceAll('""', '"');
      if (last && hasAccuracy && value !== null)
        return /^(?:0|[1-9]\d{0,2})(?:\.\d{1,2})?$/.test(actual) && Number(actual) === value;
      return actual === String(value ?? '');
    });
  }
  if (!matchesRow(csvColumns)) return false;
  const scope = [report.sessionId, report.streamId, report.fromFrame, report.throughFrame, report.roomId, report.playerId];
  if (report.players.length === 0)
    return matchesRow([1, 'Clip', ...scope, ...Array(10).fill(null)]) && field.lastIndex === text.length;
  return report.players.every(player => {
    const name = /\p{Cc}|^\p{White_Space}*[=+@-]/u.test(player.name) ? "'" + player.name : player.name;
    return matchesRow([1, 'Player', ...scope, player.playerId, name, player.roomId, player.ammoUsed, player.shotsHit,
      player.matchedShots, player.kills, player.hitsReceived, player.damageTaken, player.accuracyPercent], true);
  }) && field.lastIndex === text.length;
}

export function mountWorldClipStatistics(response, download) {
  const button = $('read'), status = $('status'), results = $('results'), body = $('rows');
  const exportButton = $('export'), exportStatus = $('export-status');
  let selection = null, selectionKey = '', idle = false, pending = null;
  let loaded = null;

  function queryFor({ fromFrame, throughFrame, roomId, playerId }) {
    const query = new URLSearchParams({ fromFrame, throughFrame });
    if (roomId !== null) query.set('roomId', roomId);
    if (playerId !== null) query.set('playerId', playerId);
    return query;
  }

  function update(scope, available) {
    const key = scope ? JSON.stringify(scope) : '';
    if (key !== selectionKey) {
      pending?.abort(); pending = null;
      selectionKey = key; selection = scope; loaded = null;
      results.hidden = true; body.replaceChildren(); status.textContent = ''; exportStatus.textContent = '';
    }
    idle = available;
    const tooLong = selection && selection.throughFrame - selection.fromFrame >= 300;
    if (tooLong) status.textContent = '片段戰績最多可核對 300 格。';
    button.disabled = !idle || !selection || !!pending || !!tooLong;
    exportButton.disabled = button.disabled || !loaded;
  }

  async function perform(action, failed) {
    const scope = selection;
    const own = new AbortController(); pending = own;
    const timeout = setTimeout(() => own.abort(), 8000);
    update(scope, idle);
    const current = () => pending === own && !own.signal.aborted;
    try { await action(scope, own.signal, current); }
    catch (error) { if (pending === own) failed(error); }
    finally {
      clearTimeout(timeout);
      if (pending === own) { pending = null; update(scope, idle); }
    }
  }

  button.addEventListener('click', () => {
    if (button.disabled) return;
    loaded = null; exportStatus.textContent = '';
    results.hidden = true; body.replaceChildren(); status.textContent = '正在讀取片段戰績…';
    void perform(async (scope, signal, current) => {
      const route = `/api/sessions/${scope.sessionId}/world/clip-statistics?${queryFor(scope)}`;
      const report = await (await response(route, signal)).json();
      if (!current()) return;
      if (report.sessionId !== scope.sessionId || report.streamId !== scope.streamId || report.fromFrame !== scope.fromFrame
        || report.throughFrame !== scope.throughFrame || report.playerId !== scope.playerId
        || (scope.roomId !== null && report.roomId !== scope.roomId)
        || (report.roomId !== null && !scope.roomIds.includes(report.roomId)) || !Array.isArray(report.players)
        || report.players.some(row => !row || typeof row.playerId !== 'string' || !playerIdPattern.test(row.playerId)
          || !scope.roomIds.includes(row.roomId) || (report.roomId !== null && row.roomId !== report.roomId)
          || (scope.playerId && row.playerId !== scope.playerId) || typeof row.name !== 'string'
          || metrics.some(field => !Number.isSafeInteger(row[field]) || row[field] < 0)
          || !Number.isSafeInteger(row.matchedShots) || row.matchedShots < 0 || row.matchedShots > Math.min(row.ammoUsed, row.shotsHit)
          || (row.ammoUsed === 0 ? row.accuracyPercent !== null : !Number.isFinite(row.accuracyPercent)
            || row.accuracyPercent < 0 || row.accuracyPercent > 100))
        || new Set(report.players.map(row => row.playerId + '/' + row.roomId)).size !== report.players.length)
        throw new Error('Invalid clip statistics');
      const scopeName = report.roomId === null ? '全場' : `房間 ${report.roomId}`;
      status.textContent = `${scopeName} · 第 ${scope.fromFrame} 至 ${scope.throughFrame} 格`
        + (report.players.length ? '' : ' · 所選範圍沒有玩家戰鬥事件。');
      body.replaceChildren(...report.players.map(row => {
        const tr = document.createElement('tr');
        const values = [row.roomId, row.name, ...metrics.map(key => row[key]), row.matchedShots,
          row.accuracyPercent === null ? '—' : `${row.accuracyPercent}%`];
        for (const value of values) {
          const td = document.createElement('td'); td.textContent = value; tr.append(td);
        }
        return tr;
      }));
      results.hidden = report.players.length === 0;
      loaded = report;
    }, error => { status.textContent = error.status === 403 ? '請選擇本房以核對片段戰績。' : '無法讀取片段戰績，請再試一次。'; });
  });
  exportButton.addEventListener('click', () => {
    if (exportButton.disabled) return;
    const report = loaded;
    exportStatus.textContent = '正在下載片段戰績…';
    void perform(async (scope, signal, current) => {
      const query = queryFor(report);
      query.set('streamId', report.streamId);
      const reply = await response(`/api/sessions/${scope.sessionId}/world/clip-statistics.csv?${query}`, signal);
      if (reply.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== 'text/csv') throw new Error('Invalid clip CSV');
      const blob = await reply.blob();
      if (!current()) return;
      if (!blob.size || blob.size > 64 * 1024) throw new Error('Invalid clip CSV size');
      const bytes = await blob.arrayBuffer();
      if (!current()) return;
      if (!matchesClipCsv(bytes, report)) throw new Error('Clip CSV does not match the verified statistics');
      const room = report.roomId === null ? '' : `-room-${String(report.roomId).padStart(2, '0')}`;
      const player = report.playerId === null ? '' : `-player-${report.playerId}`;
      download(`vr-command-clip-statistics-v1-${scope.sessionId}-${scope.fromFrame}-${scope.throughFrame}${room}${player}.csv`, blob);
      exportStatus.textContent = '已下載所選範圍的片段戰績。';
    }, () => { exportStatus.textContent = '無法下載片段戰績，請再試一次。'; });
  });
  return { update };
}
