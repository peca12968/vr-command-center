const $ = id => document.getElementById(id);
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const sequence = value => Number.isSafeInteger(value) && value >= 0;

export function mountVenueDebriefSeats(current, unauthorized, save) {
  const panel = $('venue-debrief-seats'), title = $('venue-debrief-seats-title');
  const rows = $('venue-debrief-seat-rows'), status = $('venue-debrief-seats-status');
  const table = $('venue-debrief-seat-table'), onlyMissing = $('venue-debrief-only-missing');
  const refresh = $('venue-debrief-seats-refresh');
  const csvStatus = $('venue-debrief-csv-status');
  let active = false, rooms = new Map(), target = null, controller = null, players = null;
  let csvRequest = null;

  function updateCsvButtons() {
    for (const button of rows.querySelectorAll('[data-venue-debrief-csv]')) button.disabled = !!csvRequest;
  }

  async function downloadSeat(seat) {
    const { actor, key, epoch } = current(), requested = target;
    if (!active || !requested || csvRequest || actor?.role !== 'Master' || !players?.some(player => player.seat === seat)) return;
    const request = new AbortController(); csvRequest = request;
    const timeout = setTimeout(() => request.abort(), 8000);
    const inScope = () => csvRequest === request && active && current().epoch === epoch && target?.id === requested.id;
    updateCsvButtons(); csvStatus.textContent = `正在下載第 ${seat} 席的個人戰績…`;
    try {
      const response = await fetch(`/api/venue/closure/${requested.batchId}/rooms/${requested.roomId}/seats/${seat}/report.csv`, {
        headers: { Authorization: 'Bearer ' + key }, cache: 'no-store', signal: request.signal
      });
      if (!inScope()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error('Unavailable');
      const contentType = response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase();
      const name = response.headers.get('Content-Disposition')?.match(/^attachment;\s*filename="?([^";\s]+)"?(?:;|$)/i)?.[1];
      const prefix = `vr-command-report-v1-${requested.sessionId}-player-`;
      if (contentType !== 'text/csv' || !name?.startsWith(prefix) || !name.endsWith('.csv')
        || !uuid.test(name.slice(prefix.length, -4))) throw new Error('Mismatch');
      const blob = await response.blob();
      if (!inScope()) return;
      save(name, blob);
      csvStatus.textContent = `已下載第 ${seat} 席的原封存戰績。`;
    } catch { if (inScope()) csvStatus.textContent = '暫時無法下載原封存戰績，可重新下載。'; }
    finally {
      clearTimeout(timeout);
      if (csvRequest === request) { csvRequest = null; updateCsvButtons(); }
    }
  }

  function render() {
    const visible = players?.filter(player => !onlyMissing.checked || !player.acknowledged) ?? [];
    rows.replaceChildren(...visible.map(player => {
      const row = rows.insertRow();
      for (const value of [player.seat, player.name, player.acknowledged ? '已確認' : '未確認'])
        row.insertCell().textContent = value;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'quiet small'; button.textContent = '下載 CSV';
      button.setAttribute('aria-label', `下載第 ${player.seat} 席個人戰績 CSV`);
      button.dataset.venueDebriefCsv = String(player.seat);
      button.addEventListener('click', () => downloadSeat(player.seat));
      row.insertCell().append(button);
      return row;
    }));
    table.hidden = !visible.length;
    onlyMissing.disabled = !players;
    refresh.disabled = !!controller;
    updateCsvButtons();
    if (players) status.textContent = `已確認 ${players.filter(player => player.acknowledged).length}／${players.length} 席`
      + (!visible.length ? ' · 沒有未確認席位' : '');
  }

  function close() {
    controller?.abort(); controller = null; target = null; players = null;
    csvRequest?.abort(); csvRequest = null; csvStatus.textContent = '';
    panel.hidden = true; onlyMissing.checked = false; status.textContent = ''; render();
  }

  async function read() {
    const state = current(), requested = target;
    if (!active || !requested || controller || state.actor?.role !== 'Master') return;
    const request = new AbortController(); controller = request; players = null;
    const timeout = setTimeout(() => request.abort(), 8000);
    const stateEpoch = state.epoch;
    const inScope = () => controller === request && active && current().epoch === stateEpoch && target?.id === requested.id;
    render(); status.textContent = '正在讀取原批次的席位回條…';
    try {
      const response = await fetch(`/api/venue/closure/${requested.batchId}/rooms/${requested.roomId}/debrief-receipts`, {
        headers: { Authorization: 'Bearer ' + state.key }, cache: 'no-store', signal: request.signal
      });
      if (!inScope()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error('Unavailable');
      const body = await response.json();
      if (!inScope()) return;
      if (body?.version !== 1 || body.requestId !== target.batchId || body.sessionId !== target.sessionId
        || body.roomId !== target.roomId || body.streamId !== target.streamId || body.worldSequence !== target.worldSequence
        || !sequence(body.throughSequence) || body.throughSequence < target.appliedAtSequence || !sequence(body.finalStreamSequence)
        || !Array.isArray(body.players) || body.players.length !== target.rosterCount
        || new Set(body.players.map(player => player?.seat)).size !== target.rosterCount
        || !body.players.every(player => Number.isInteger(player?.seat) && player.seat >= 1 && player.seat <= 5
          && typeof player.name === 'string' && typeof player.acknowledged === 'boolean')
        || body.players.filter(player => player.acknowledged).length < target.confirmedCount) throw new Error('Mismatch');
      players = [...body.players].sort((a, b) => a.seat - b.seat);
    } catch { if (inScope()) status.textContent = '暫時無法確認原席位回條，可重新讀取。'; }
    finally {
      clearTimeout(timeout);
      if (inScope()) { controller = null; render(); }
    }
  }

  function update(batch, counts = new Map()) {
    rooms = new Map();
    if (uuid.test(batch?.requestId ?? '')) for (const session of batch.sessions) {
      const replay = session.replay;
      if (session.combat !== 'Sealed' || session.world !== 'Sealed' || !uuid.test(session.sessionId)
        || !uuid.test(replay?.streamId ?? '') || !sequence(replay.throughSequence) || replay.throughSequence < 1
        || !sequence(session.appliedAtSequence) || session.appliedAtSequence < 1) continue;
      for (const roomId of session.roomIds) {
        const count = counts.get(roomId);
        if (!count?.rosterCount || count.confirmedCount === null) continue;
        rooms.set(roomId, { id: `${batch.requestId}/${roomId}/${session.sessionId}/${replay.streamId}/${replay.throughSequence}`,
          batchId: batch.requestId, sessionId: session.sessionId, roomId, streamId: replay.streamId,
          worldSequence: replay.throughSequence, appliedAtSequence: session.appliedAtSequence,
          rosterCount: count.rosterCount, confirmedCount: count.confirmedCount });
      }
    }
    if (!target) return;
    const next = rooms.get(target.roomId);
    if (next?.id !== target.id || next.rosterCount !== target.rosterCount) { close(); return; }
    const advanced = next.confirmedCount > target.confirmedCount;
    target = next;
    if (advanced && (players?.filter(player => player.acknowledged).length ?? -1) < next.confirmedCount) void read();
  }

  onlyMissing.addEventListener('change', render);
  refresh.addEventListener('click', read);
  $('venue-debrief-seats-close').addEventListener('click', close);
  return { update, available: roomId => rooms.has(roomId), active(on) { active = on; if (!on) close(); },
    open(roomId) {
      if (!active || current().actor?.role !== 'Master' || !rooms.has(roomId)) return;
      close(); target = rooms.get(roomId); panel.hidden = false;
      title.textContent = `房間 ${roomId} 的戰績回條`; title.focus(); void read();
    } };
}
