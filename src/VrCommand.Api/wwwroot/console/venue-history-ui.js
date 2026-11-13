const pageSize = 20;
const isId = value => typeof value === 'string' && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(value);

export function mountVenueHistory(api, onSelect) {
  const picker = document.getElementById('venue-closure-batch');
  const load = document.getElementById('venue-closure-load'), more = document.getElementById('venue-closure-more');
  const status = document.getElementById('venue-history-status');
  const items = new Map();
  let allowed = false, loading = false, loaded = false, next = null, epoch = 0;

  function controls() {
    picker.disabled = !allowed || picker.options.length < 2;
    load.disabled = !allowed || loading;
    load.textContent = loaded ? '更新批次清單' : '載入批次清單';
    more.hidden = !next;
    more.disabled = !allowed || loading || !next;
  }

  function renderOptions() {
    const selected = picker.value;
    const pinned = selected && !items.has(selected) ? picker.selectedOptions[0].cloneNode(true) : null;
    picker.replaceChildren(new Option('自動顯示最新批次', ''));
    for (const batch of items.values()) {
      const date = new Date(batch.recordedAtUtc).toLocaleString('zh-TW');
      picker.add(new Option(`${date} · 房間 ${batch.roomIds.join('、')} · ${batch.missionNames.join('／')} · ${batch.requestId.slice(0, 8)}`, batch.requestId));
    }
    if (pinned) picker.add(pinned);
    picker.value = selected;
  }

  async function fetchPage(earlier) {
    if (!allowed || loading || (earlier && !next)) return;
    const request = ++epoch, before = earlier ? next : null;
    loading = true; controls();
    status.textContent = '正在讀取批次清單…';
    try {
      const page = await api(`/venue/closure/history?limit=${pageSize}${before ? '&before=' + before : ''}`);
      if (request !== epoch) return;
      const batches = page?.batches;
      if (!Array.isArray(batches) || batches.length > pageSize || batches.some(batch => !isId(batch?.requestId)
        || batch.requestId === before || !Number.isFinite(Date.parse(batch.recordedAtUtc))
        || !Array.isArray(batch.roomIds) || !batch.roomIds.length || batch.roomIds.length > 5
        || !batch.roomIds.every(room => Number.isInteger(room) && room >= 1 && room <= 5)
        || !Array.isArray(batch.missionNames) || !batch.missionNames.length || batch.missionNames.length > 5
        || !batch.missionNames.every(name => typeof name === 'string'))
        || (page.nextBefore !== null && (!isId(page.nextBefore) || page.nextBefore !== batches.at(-1)?.requestId)))
        throw new Error('Invalid venue history page');
      if (!earlier) items.clear();
      for (const batch of batches) items.set(batch.requestId, batch);
      next = page.nextBefore;
      loaded = true;
      renderOptions();
      status.textContent = items.size ? `已載入 ${items.size} 個批次。` : '目前沒有已結束的全館批次。';
    } catch {
      if (request === epoch) status.textContent = '無法讀取批次清單，可重新載入。';
    } finally {
      if (request === epoch) { loading = false; controls(); }
    }
  }
  picker.addEventListener('change', () => onSelect());
  load.addEventListener('click', () => fetchPage(false));
  more.addEventListener('click', () => fetchPage(true));
  return {
    selected: () => picker.value,
    selectOriginal(id) {
      if (!allowed || !isId(id)) return false;
      if (![...picker.options].some(option => option.value === id))
        picker.add(new Option(`報告對應批次 ${id.slice(0, 8)}`, id));
      picker.value = id;
      controls();
      return true;
    },
    update(value) { allowed = value; controls(); },
    reset() {
      epoch++; allowed = loading = loaded = false; next = null; items.clear();
      picker.replaceChildren(new Option('自動顯示最新批次', ''));
      status.textContent = '';
      controls();
    }
  };
}
