const kinds = ['ShotFired', 'ShotHit', 'EnemyEliminated'];

export function isTraceableShot(event) {
  return Boolean(event.shotId) && kinds.includes(event.kind);
}

export function mountWorldShotTrace(response, jump, names) {
  const panel = document.getElementById('world-shot-trace');
  const status = document.getElementById('world-shot-trace-status');
  const list = document.getElementById('world-shot-trace-events');
  const table = document.getElementById('world-events');
  let scope, key = '', idle = false, pending, trace;

  function controls() {
    for (const button of table.querySelectorAll('button[data-shot-trace]'))
      button.disabled = !idle || Boolean(pending);
    for (const button of list.querySelectorAll('button'))
      button.disabled = !idle || Number(button.dataset.frameSequence) === scope?.frameSequence;
  }

  function clear() {
    pending?.abort();
    pending = trace = null;
    list.replaceChildren();
    status.textContent = '';
    panel.hidden = true;
  }

  function update(value, ready) {
    const nextKey = value ? JSON.stringify([value.sessionId, value.streamId, value.throughFrame, value.roomId, value.playerId]) : '';
    const moved = value?.frameSequence !== scope?.frameSequence;
    if (nextKey !== key || (pending && (!ready || moved))
        || (moved && !trace?.events.some(event => event.frameSequence === value?.frameSequence))) clear();
    scope = value;
    key = nextKey;
    idle = ready;
    controls();
  }

  async function read(event) {
    if (!idle || pending || !isTraceableShot(event) || (scope.playerId && scope.playerId !== event.playerId)) return;
    clear();
    const { sessionId, streamId, throughFrame, roomId, roomIds, frameSequence: fromFrame } = scope;
    const request = pending = new AbortController();
    const query = new URLSearchParams({ fromFrame, throughFrame, eventId: event.eventId });
    if (roomId != null) query.set('roomId', roomId);
    panel.hidden = false;
    status.textContent = '正在核對同發射擊的保存畫格…';
    controls();
    try {
      const signal = AbortSignal.any([request.signal, AbortSignal.timeout(8000)]);
      const value = await (await response(`/api/sessions/${sessionId}/world/shot-trace?${query}`, signal)).json();
      if (request !== pending) return;
      const { events } = value;
      if (value.sessionId !== sessionId || value.streamId !== streamId || value.fromFrame !== fromFrame || value.throughFrame !== throughFrame
          || value.eventId !== event.eventId || value.shotId !== event.shotId || value.playerId !== event.playerId
          || (roomId != null && value.roomId !== roomId) || (value.roomId != null && !roomIds.includes(value.roomId))
          || !Array.isArray(events) || events.length < 1 || events.length > kinds.length
          || events.some((row, i) => !row.eventId || !kinds.includes(row.kind) || !roomIds.includes(row.roomId)
            || (value.roomId != null && row.roomId !== value.roomId) || !Number.isSafeInteger(row.elapsedMilliseconds) || row.elapsedMilliseconds < 0
            || !Number.isSafeInteger(row.frameSequence) || row.frameSequence < 1 || row.frameSequence > throughFrame
            || (i > 0 && (kinds.indexOf(row.kind) <= kinds.indexOf(events[i - 1].kind) || row.frameSequence < events[i - 1].frameSequence)))
          || !events.some(row => row.eventId === event.eventId && row.kind === event.kind && row.frameSequence === fromFrame))
        throw new Error('回應的射擊紀錄不同。');
      trace = value;
      status.textContent = `同發射擊 · 保存範圍內有 ${events.length} 筆紀錄`;
      list.replaceChildren(...events.map(row => {
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'quiet';
        button.dataset.frameSequence = String(row.frameSequence);
        button.textContent = `${names[row.kind]} · 第 ${row.frameSequence} 格 · 房間 ${row.roomId}`;
        button.addEventListener('click', () => jump(row.frameSequence, () => trace === value, frame =>
          frame.packet.elapsedMilliseconds === row.elapsedMilliseconds
          && frame.packet.events.some(saved => saved.eventId === row.eventId && saved.kind === row.kind
            && saved.playerId === value.playerId && saved.shotId === value.shotId)
          && frame.statistics.some(player => player.playerId === value.playerId && player.roomId === row.roomId)));
        item.append(button);
        return item;
      }));
    } catch {
      if (request === pending) status.textContent = '無法核對同發射擊的保存畫格，請再試一次。';
    } finally {
      if (request === pending) { pending = null; controls(); }
    }
  }

  return { update, read };
}
