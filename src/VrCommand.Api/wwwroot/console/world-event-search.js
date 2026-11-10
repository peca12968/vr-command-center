export function mountWorldEventSearch(response, jump, eventNames, filterChanged) {
  const kind = document.getElementById('world-event-kind');
  const start = document.getElementById('world-event-search-start');
  const here = document.getElementById('world-event-search-here');
  const next = document.getElementById('world-event-search-next');
  const previousEvent = document.getElementById('world-event-previous');
  const nextEvent = document.getElementById('world-event-next');
  const results = document.getElementById('world-event-search-results');
  const status = document.getElementById('world-event-search-status');
  let scope, scopeKey = '', revision = 0, page, pending;

  for (const [value, label] of Object.entries(eventNames)) kind.add(new Option(label, value));

  function controls() {
    const idle = scope?.idle && !pending;
    kind.disabled = !scope;
    start.disabled = here.disabled = !idle;
    previousEvent.disabled = !idle || scope.frameSequence <= 1;
    nextEvent.disabled = !idle || scope.frameSequence >= scope.throughFrame;
    next.disabled = !idle || page?.nextAfterFrame == null;
    for (const button of results.querySelectorAll('button')) button.disabled = !idle;
  }
  function cancel() {
    pending?.abort();
    pending = null;
  }
  function update(value) {
    if (!value) kind.value = '';
    const key = value ? JSON.stringify([value.sessionId, value.streamId, value.throughFrame, value.room, value.playerId, kind.value]) : '';
    scope = value;
    if (key !== scopeKey) {
      revision++;
      cancel();
      page = null;
      results.replaceChildren();
      status.textContent = '';
      scopeKey = key;
    } else if (!scope?.idle && pending) {
      cancel();
      status.textContent = '回放暫停後可重新搜尋。';
    }
    controls();
  }

  async function search(afterFrame) {
    if (!scope?.idle || pending) return;
    const { sessionId, streamId, throughFrame, room, playerId } = scope;
    const query = new URLSearchParams({ afterFrame, throughFrame });
    if (room !== 'all') query.set('roomId', room);
    if (playerId) query.set('playerId', playerId);
    if (kind.value) query.set('kind', kind.value);
    const request = new AbortController();
    pending = request;
    controls();
    status.textContent = '正在搜尋已保存的事件…';
    try {
      const signal = AbortSignal.any([request.signal, AbortSignal.timeout(8000)]);
      const value = await (await response(`/api/sessions/${sessionId}/world/event-frames?${query}`, signal)).json();
      if (pending !== request) return;
      if (value.sessionId !== sessionId || value.streamId !== streamId || value.throughFrame !== throughFrame
          || value.afterFrame !== afterFrame || (value.playerId ?? null) !== playerId) throw new Error('回應的錄製範圍不同。');
      page = value;
      results.replaceChildren(...page.frames.map(hit => {
        const row = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'quiet';
        button.dataset.frameSequence = String(hit.frameSequence);
        button.textContent = `第 ${hit.frameSequence} 格 · ${(hit.elapsedMilliseconds / 1000).toFixed(2)} 秒 · ${hit.matchCount} 筆`;
        button.addEventListener('click', () => jump(hit.frameSequence));
        row.append(button);
        return row;
      }));
      const scanned = page.scannedThroughFrame === afterFrame ? '已到搜尋範圍尾端'
        : `已搜尋第 ${afterFrame + 1} 至 ${page.scannedThroughFrame} 格，找到 ${page.frames.length} 格`;
      status.textContent = scanned + (page.nextAfterFrame == null ? '。' : '。可繼續搜尋後續快照。');
    } catch {
      if (pending === request) status.textContent = '搜尋失敗，請再試一次。';
    } finally {
      if (pending === request) { pending = null; controls(); }
    }
  }
  async function navigate(direction, countMatches) {
    if (!scope?.idle || pending) return;
    const { sessionId, streamId, throughFrame, room, playerId, frameSequence } = scope;
    const filter = kind.value || null, roomId = room === 'all' ? null : Number(room);
    const generation = revision, request = new AbortController();
    pending = request;
    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(30000)]);
    const label = direction === 'previous' ? '上一筆' : '下一筆';
    status.textContent = `正在尋找${label}符合條件的事件…`;
    controls();
    let cursor = frameSequence;
    try {
      const query = new URLSearchParams({ throughFrame, direction });
      if (roomId !== null) query.set('roomId', room);
      if (playerId) query.set('playerId', playerId);
      if (filter) query.set('kind', filter);
      for (;;) {
        query.set('fromFrame', cursor);
        const value = await (await response(`/api/sessions/${sessionId}/world/event-neighbor?${query}`, signal)).json();
        if (pending !== request || scope.frameSequence !== frameSequence) return;
        const end = direction === 'previous' ? 1 : throughFrame;
        const scanned = value.scannedToFrame;
        if (value.sessionId !== sessionId || value.streamId !== streamId || value.throughFrame !== throughFrame
            || value.fromFrame !== cursor || value.direction !== direction || (value.roomId ?? null) !== roomId
            || (value.kind ?? null) !== filter || (value.playerId ?? null) !== playerId
            || !Number.isSafeInteger(scanned) || (direction === 'previous' ? scanned < end || scanned >= cursor : scanned > end || scanned <= cursor))
          throw new Error('回應的事件範圍不同。');
        if (value.frame) {
          if (value.nextFromFrame != null || value.frame.frameSequence !== scanned || !Number.isSafeInteger(value.frame.matchCount)
              || value.frame.matchCount < 1) throw new Error('回應的事件快照不同。');
          pending = null;
          const matches = countMatches && (frame => frame.packet.elapsedMilliseconds === value.frame.elapsedMilliseconds
            && countMatches(frame) === value.frame.matchCount);
          const jumped = await jump(scanned, () => revision === generation && scope?.frameSequence === frameSequence, matches);
          if (revision === generation && !pending && scope?.frameSequence === (jumped ? scanned : frameSequence))
            status.textContent = jumped ? `已跳到第 ${scanned} 格，共 ${value.frame.matchCount} 筆符合事件。` : '讀取事件快照失敗，請再試一次。';
          return;
        }
        if (value.nextFromFrame == null && scanned === end) {
          status.textContent = `保存範圍內沒有${label}符合條件的事件。`;
          return;
        }
        if (value.nextFromFrame !== scanned || scanned === end) throw new Error('回應的搜尋游標不同。');
        cursor = scanned;
      }
    } catch {
      if (pending === request) status.textContent = '尋找事件失敗，請再試一次。';
    } finally {
      if (pending === request) { pending = null; controls(); }
    }
  }

  function fromLatest(filter, frame, countMatches) {
    if (!scope?.idle) return;
    kind.value = filter;
    update(scope);
    filterChanged();
    const count = countMatches(frame);
    if (count) status.textContent = `已停在第 ${scope.frameSequence} 格，共 ${count} 筆符合事件。`;
    else if (scope.frameSequence > 1) return navigate('previous', countMatches);
    else status.textContent = '保存範圍內沒有符合條件的事件。';
  }
  kind.addEventListener('change', () => { update(scope); filterChanged(); });
  start.addEventListener('click', () => search(0));
  here.addEventListener('click', () => search(scope.frameSequence - 1));
  next.addEventListener('click', () => search(page.nextAfterFrame));
  previousEvent.addEventListener('click', () => navigate('previous'));
  nextEvent.addEventListener('click', () => navigate('next'));
  return { update, fromStart: () => search(0), fromLatest, kind: () => kind.value };
}
