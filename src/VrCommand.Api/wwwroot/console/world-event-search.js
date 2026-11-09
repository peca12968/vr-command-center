export function mountWorldEventSearch(response, jump, eventNames, filterChanged) {
  const kind = document.getElementById('world-event-kind');
  const start = document.getElementById('world-event-search-start');
  const here = document.getElementById('world-event-search-here');
  const next = document.getElementById('world-event-search-next');
  const results = document.getElementById('world-event-search-results');
  const status = document.getElementById('world-event-search-status');
  let scope, scopeKey = '', page, pending;

  for (const [value, label] of Object.entries(eventNames)) kind.add(new Option(label, value));

  function controls() {
    const idle = scope?.idle && !pending;
    kind.disabled = !scope;
    start.disabled = here.disabled = !idle;
    next.disabled = !idle || page?.nextAfterFrame == null;
    for (const button of results.querySelectorAll('button')) button.disabled = !idle;
  }
  function cancel() {
    pending?.abort();
    pending = null;
  }
  function update(value) {
    if (!value) kind.value = '';
    const key = value ? JSON.stringify([value.sessionId, value.streamId, value.throughFrame, value.room, kind.value]) : '';
    scope = value;
    if (key !== scopeKey) {
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
    const { sessionId, streamId, throughFrame, room } = scope;
    const query = new URLSearchParams({ afterFrame, throughFrame });
    if (room !== 'all') query.set('roomId', room);
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
          || value.afterFrame !== afterFrame) throw new Error('回應的錄製範圍不同。');
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
  kind.addEventListener('change', () => { update(scope); filterChanged(); });
  start.addEventListener('click', () => search(0));
  here.addEventListener('click', () => search(scope.frameSequence - 1));
  next.addEventListener('click', () => search(page.nextAfterFrame));
  return { update, kind: () => kind.value };
}
