export function mountReport(current, unauthorized) {
  const button = document.getElementById('export-report'), status = document.getElementById('report-status');
  const bundle = document.getElementById('export-report-bundle');
  const roomField = document.getElementById('report-room-field'), room = document.getElementById('report-room');
  let generation = 0, controller = null, availability = null, scopeIdentity = '';
  const ready = value => value.actor && value.session?.state === 'Ended' &&
    value.statistics?.sessionId === value.session.id && value.statistics.throughSequence === value.session.sequence &&
    !value.statistics.pendingTelemetry;
  const linked = value => value.actor && value.session?.mode === 'Linked';
  const canBundle = value => linked(value) && value.actor.role === 'Master';
  const scope = value => !linked(value) ? null : value.actor.role === 'RoomController' ? value.actor.roomId : Number(room.value) || null;
  function update() {
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
    button.disabled = !!controller || !ready(value);
    bundle.hidden = !canBundle(value);
    bundle.disabled = bundle.hidden || button.disabled;
    room.disabled = button.disabled || value.actor?.role !== 'Master';
    const roomId = scope(value);
    const next = ready(value) ? (roomId ? `房間 ${roomId} 的戰鬥統計已完成，可下載 CSV（含離場玩家）。` : '戰鬥統計已完成，可下載 CSV（含離場玩家）。')
      : value.session?.state === 'Ended' ? '等待戰鬥資料確認封存後才可匯出。' : '結束任務並完成戰鬥封存後可匯出。';
    if (!controller && next !== availability) status.textContent = next;
    availability = next;
  }
  function reset() {
    generation++; controller?.abort(); controller = null; availability = null; scopeIdentity = '';
    status.textContent = ''; button.disabled = true; room.disabled = true; roomField.hidden = true; room.replaceChildren();
    bundle.hidden = bundle.disabled = true;
  }
  room.addEventListener('change', () => { availability = null; update(); });
  async function download(allRooms) {
    const value = current();
    if (controller || !ready(value) || (allRooms && !canBundle(value))) return;
    const attempt = ++generation, epoch = value.epoch, id = value.session.id, roomId = scope(value);
    const active = () => attempt === generation && current().epoch === epoch && current().session?.id === id
      && (allRooms ? canBundle(current()) : scope(current()) === roomId);
    const suffix = roomId === null ? '' : '-room-' + String(roomId).padStart(2, '0');
    const path = allRooms ? '/reports.zip' : `${roomId === null ? '' : `/rooms/${roomId}`}/report.csv`;
    const request = new AbortController(); controller = request;
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
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      try {
        link.href = url; link.download = allRooms ? `vr-command-reports-v1-${id}.zip` : `vr-command-report-v1-${id}${suffix}.csv`;
        document.body.append(link); link.click();
      } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
      status.textContent = allRooms ? '已下載全場及五份分房戰績 CSV。' : '最終報表已下載；來源與封存序號列於 CSV。';
    } catch (error) {
      if (active()) status.textContent = request.signal.aborted ? '下載逾時或已中止，可重新下載。' : error.message;
    } finally {
      clearTimeout(timeout);
      if (attempt === generation) { controller = null; update(); }
    }
  }
  button.addEventListener('click', () => download(false));
  bundle.addEventListener('click', () => download(true));
  return { update, reset };
}

export function mountVenueReport(current, unauthorized, save) {
  const actions = document.getElementById('venue-report-actions');
  const button = document.getElementById('export-venue-reports'), status = document.getElementById('venue-report-status');
  let id = null, waiting = '', controller = null;
  const updateButton = () => { button.disabled = !id || !!waiting || !!controller; };
  function update(batch) {
    const nextId = current().actor?.role === 'Master' && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(batch?.requestId ?? '')
      ? batch.requestId : null;
    const nextWaiting = nextId ? batch.sessions.filter(session => !['Sealed', 'NoSource'].includes(session.combat))
      .flatMap(session => session.roomIds).sort((a, b) => a - b).join('、') : '';
    if (id !== nextId || waiting !== nextWaiting) {
      controller?.abort(); controller = null;
      id = nextId; waiting = nextWaiting;
      status.textContent = !id ? '' : waiting ? `等待房間 ${waiting} 的戰鬥資料封存。` : '本批戰績已可匯出。';
    }
    actions.hidden = !id;
    updateButton();
  }
  button.addEventListener('click', async () => {
    const { actor, epoch, key } = current(), batchId = id;
    if (!batchId || waiting || controller || actor?.role !== 'Master') return;
    const request = new AbortController(); controller = request;
    const active = () => controller === request && id === batchId && current().epoch === epoch;
    const timeout = setTimeout(() => request.abort(), 8000);
    updateButton(); status.textContent = '正在下載本批戰績 ZIP…';
    try {
      const response = await fetch(`/api/venue/closure/${batchId}/reports.zip`, {
        headers: { Authorization: 'Bearer ' + key }, signal: request.signal, cache: 'no-store'
      });
      if (!active()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error(response.status === 409 ? '本批仍在等待戰鬥資料封存。' : '本批戰績下載失敗，可重新整理後再試。');
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== 'application/zip')
        throw new Error('報表格式不符，可重新下載。');
      const blob = await response.blob();
      if (!active()) return;
      save(`vr-command-venue-reports-v1-${batchId}.zip`, blob);
      status.textContent = '已下載本批戰績與原場次清單。';
    } catch (error) {
      if (active()) status.textContent = request.signal.aborted ? '下載逾時，可重新下載。' : error.message;
    } finally {
      clearTimeout(timeout);
      if (controller === request) { controller = null; updateButton(); }
    }
  });
  return { update };
}
