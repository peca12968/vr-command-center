const $ = id => document.getElementById(`world-clip-stats-${id}`);
const metrics = ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken'];

export function mountWorldClipStatistics(response) {
  const button = $('read'), status = $('status'), results = $('results'), body = $('rows');
  let selection = null, selectionKey = '', idle = false, pending = null;

  function update(scope, available) {
    const key = scope ? JSON.stringify(scope) : '';
    if (key !== selectionKey) {
      pending?.abort(); pending = null;
      selectionKey = key; selection = scope;
      results.hidden = true; body.replaceChildren(); status.textContent = '';
    }
    idle = available;
    const tooLong = selection && selection.throughFrame - selection.fromFrame >= 300;
    if (tooLong) status.textContent = '片段戰績最多可核對 300 格。';
    button.disabled = !idle || !selection || !!pending || !!tooLong;
  }

  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const scope = selection;
    const own = new AbortController(); pending = own;
    const timeout = setTimeout(() => own.abort(), 8000);
    results.hidden = true; body.replaceChildren(); status.textContent = '正在讀取片段戰績…';
    update(scope, idle);
    try {
      const query = new URLSearchParams({ fromFrame: scope.fromFrame, throughFrame: scope.throughFrame });
      if (scope.roomId) query.set('roomId', scope.roomId);
      if (scope.playerId) query.set('playerId', scope.playerId);
      const route = `/api/sessions/${scope.sessionId}/world/clip-statistics?${query}`;
      const report = await (await response(route, own.signal)).json();
      if (pending !== own || own.signal.aborted) return;
      if (report.sessionId !== scope.sessionId || report.streamId !== scope.streamId || report.fromFrame !== scope.fromFrame
        || report.throughFrame !== scope.throughFrame || report.playerId !== scope.playerId
        || (scope.roomId !== null && report.roomId !== scope.roomId)
        || (report.roomId !== null && !scope.roomIds.includes(report.roomId)) || !Array.isArray(report.players)
        || report.players.some(row => !scope.roomIds.includes(row.roomId) || (report.roomId !== null && row.roomId !== report.roomId)
          || (scope.playerId && row.playerId !== scope.playerId) || typeof row.name !== 'string'
          || metrics.some(field => !Number.isSafeInteger(row[field]) || row[field] < 0)
          || (row.ammoUsed === 0 ? row.accuracyPercent !== null : !Number.isFinite(row.accuracyPercent)
            || row.accuracyPercent < 0 || row.accuracyPercent > 100))) throw new Error('Invalid clip statistics');
      const scopeName = report.roomId === null ? '全場' : `房間 ${report.roomId}`;
      status.textContent = `${scopeName} · 第 ${scope.fromFrame} 至 ${scope.throughFrame} 格`
        + (report.players.length ? '' : ' · 所選範圍沒有玩家戰鬥事件。');
      body.replaceChildren(...report.players.map(row => {
        const tr = document.createElement('tr');
        const values = [row.roomId, row.name, ...metrics.map(key => row[key]), row.accuracyPercent === null ? '—' : `${row.accuracyPercent}%`];
        for (const value of values) {
          const td = document.createElement('td'); td.textContent = value; tr.append(td);
        }
        return tr;
      }));
      results.hidden = report.players.length === 0;
    } catch (error) {
      if (pending === own) status.textContent = error.status === 403 ? '請選擇本房以核對片段戰績。' : '無法讀取片段戰績，請再試一次。';
    } finally {
      clearTimeout(timeout);
      if (pending === own) { pending = null; update(scope, idle); }
    }
  });
  return { update };
}
