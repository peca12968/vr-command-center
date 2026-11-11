const $ = id => document.getElementById(id);
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const sequence = value => Number.isSafeInteger(value) && value >= 0;

export function mountVenueDebriefSeats(current, unauthorized) {
  const panel = $('venue-debrief-seats'), title = $('venue-debrief-seats-title');
  const rows = $('venue-debrief-seat-rows'), status = $('venue-debrief-seats-status');
  const table = $('venue-debrief-seat-table'), onlyMissing = $('venue-debrief-only-missing');
  const refresh = $('venue-debrief-seats-refresh');
  let active = false, rooms = new Map(), target = null, controller = null, players = null;

  function render() {
    const visible = players?.filter(player => !onlyMissing.checked || !player.acknowledged) ?? [];
    rows.replaceChildren(...visible.map(player => {
      const row = rows.insertRow();
      for (const value of [player.seat, player.name, player.acknowledged ? '已確認' : '未確認'])
        row.insertCell().textContent = value;
      return row;
    }));
    table.hidden = !visible.length;
    onlyMissing.disabled = !players;
    refresh.disabled = !!controller;
    if (players) status.textContent = `已確認 ${players.filter(player => player.acknowledged).length}／${players.length} 席`
      + (!visible.length ? ' · 沒有未確認席位' : '');
  }

  function close() {
    controller?.abort(); controller = null; target = null; players = null;
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
