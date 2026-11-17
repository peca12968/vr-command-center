import { encodeUnconfirmedSeatsCsv, matchesDebriefCsv } from './report-csv.js';

const $ = id => document.getElementById(id);
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const sequence = value => Number.isSafeInteger(value) && value >= 0;
const countFields = ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken'];

function validScore(score) {
  return score && countFields.every(field => sequence(score[field])) && score.shotsHit <= score.ammoUsed
    && Number.isFinite(score.accuracyPercent) && score.accuracyPercent >= 0 && score.accuracyPercent <= 100
    && sequence(score.health) && score.health <= 100;
}

function validatedPlayers(body, room) {
  if (body?.version !== 1 || body.requestId !== room.batchId || body.sessionId !== room.sessionId
    || body.roomId !== room.roomId || body.streamId !== room.streamId || body.worldSequence !== room.worldSequence
    || !sequence(body.throughSequence) || body.throughSequence < room.appliedAtSequence || !sequence(body.finalStreamSequence)
    || !Array.isArray(body.players) || body.players.length !== room.rosterCount
    || new Set(body.players.map(player => player?.seat)).size !== room.rosterCount
    || new Set(body.players.map(player => player?.playerId)).size !== room.rosterCount
    || !body.players.every(player => Number.isInteger(player?.seat) && player.seat >= 1 && player.seat <= 5
      && uuid.test(player.playerId ?? '') && typeof player.name === 'string' && typeof player.acknowledged === 'boolean' && validScore(player.score))
    || body.players.filter(player => player.acknowledged).length < room.confirmedCount) throw new Error('Mismatch');
  return [...body.players].sort((a, b) => a.seat - b.seat)
    .map(player => ({ ...player, room, throughSequence: body.throughSequence, throughCombatSequence: body.finalStreamSequence }));
}

export function mountVenueDebriefSeats(current, unauthorized, save, openReplay) {
  const panel = $('venue-debrief-seats'), title = $('venue-debrief-seats-title');
  const rows = $('venue-debrief-seat-rows'), status = $('venue-debrief-seats-status');
  const table = $('venue-debrief-seat-table'), onlyMissing = $('venue-debrief-only-missing');
  const refresh = $('venue-debrief-seats-refresh');
  const csvStatus = $('venue-debrief-csv-status');
  const missingCsv = $('venue-debrief-missing-csv');
  const all = $('venue-debrief-all'), roomHeading = $('venue-debrief-room-heading');
  let active = false, rooms = new Map(), batchTarget = null, target = null, controller = null, players = null;
  let csvRequest = null;

  function canDownloadMissing() {
    return active && target && !target.pendingRooms?.length && !controller && !csvRequest
      && current().actor?.role === 'Master' && players?.some(player => !player.acknowledged);
  }

  function updateCsvButtons() {
    for (const button of rows.querySelectorAll('[data-venue-debrief-csv]')) button.disabled = !!csvRequest;
    missingCsv.disabled = !canDownloadMissing();
  }

  function downloadMissing() {
    if (!canDownloadMissing()) return;
    const { batchId, roomId } = target;
    const scope = roomId === null ? '' : `-room-${String(roomId).padStart(2, '0')}`;
    const file = `vr-command-venue-unconfirmed-seats-v1-${batchId}${scope}.csv`;
    save(file, new Blob([encodeUnconfirmedSeatsCsv(batchId, players)], { type: 'text/csv;charset=utf-8' }));
    const count = players.filter(player => !player.acknowledged).length;
    csvStatus.textContent = `已下載 ${count} 席的未確認清單。`;
  }

  async function downloadSeat(player) {
    const { actor, key, epoch } = current(), requested = target;
    if (!active || !requested || csvRequest || actor?.role !== 'Master' || !players?.includes(player)) return;
    const { seat, playerId, room } = player;
    const seatLabel = requested.roomId === null ? `房間 ${room.roomId} 第 ${seat} 席` : `第 ${seat} 席`;
    const request = new AbortController(); csvRequest = request;
    const timeout = setTimeout(() => request.abort(), 8000);
    const inScope = () => csvRequest === request && active && current().epoch === epoch && target?.id === requested.id;
    updateCsvButtons(); csvStatus.textContent = `正在下載${seatLabel}的個人戰績…`;
    try {
      const response = await fetch(`/api/venue/closure/${requested.batchId}/rooms/${room.roomId}/seats/${seat}/report.csv`, {
        headers: { Authorization: 'Bearer ' + key }, cache: 'no-store', signal: request.signal
      });
      if (!inScope()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error('Unavailable');
      const contentType = response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase();
      const name = response.headers.get('Content-Disposition')?.match(/^attachment;\s*filename="?([^";\s]+)"?(?:;|$)/i)?.[1];
      if (contentType !== 'text/csv' || name !== `vr-command-report-v1-${room.sessionId}-player-${playerId}.csv`)
        throw new Error('Mismatch');
      const blob = await response.blob();
      if (!inScope()) return;
      if (blob.size < 1 || blob.size > 16 * 1024) throw new Error('Mismatch');
      const bytes = await blob.arrayBuffer();
      if (!inScope()) return;
      const currentSeat = players?.find(row => row.room.id === room.id && row.seat === seat && row.playerId === playerId);
      if (!currentSeat || !matchesDebriefCsv(bytes, player) || !matchesDebriefCsv(bytes, currentSeat))
        throw new Error('Mismatch');
      save(name, blob);
      csvStatus.textContent = `已下載${seatLabel}的原封存戰績。`;
    } catch { if (inScope()) csvStatus.textContent = '暫時無法下載原封存戰績，可重新下載。'; }
    finally {
      clearTimeout(timeout);
      if (csvRequest === request) { csvRequest = null; updateCsvButtons(); }
    }
  }

  function replaySeat(player, latestDamage = false) {
    const { actor, busy, pending } = current();
    if (!active || !target || actor?.role !== 'Master' || busy || pending || !players?.includes(player)) return;
    const { room, throughCombatSequence } = player;
    openReplay({ mode: 'replay', complete: true, sessionId: room.sessionId, roomId: room.roomId,
      streamId: room.streamId, throughSequence: room.worldSequence, throughCombatSequence,
      playerId: player.playerId, playerName: player.name, playerScore: { ...player.score, roomId: room.roomId }, latestDamage },
    { batchId: room.batchId, roomId: target.roomId, onlyMissing: onlyMissing.checked });
  }

  function render() {
    const combined = target?.roomId === null;
    roomHeading.hidden = !combined;
    const visible = players?.filter(player => !onlyMissing.checked || !player.acknowledged) ?? [];
    rows.replaceChildren(...visible.map(player => {
      const row = rows.insertRow();
      const seatLabel = combined ? `房間 ${player.room.roomId} 第 ${player.seat} 席` : `第 ${player.seat} 席`;
      if (combined) row.insertCell().textContent = player.room.roomId;
      for (const value of [player.seat, player.name, player.acknowledged ? '已確認' : '未確認'])
        row.insertCell().textContent = value;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'quiet small'; button.textContent = '下載 CSV';
      button.setAttribute('aria-label', `下載${seatLabel}個人戰績 CSV`);
      button.dataset.venueDebriefCsv = String(player.seat);
      button.addEventListener('click', () => downloadSeat(player));
      const replay = document.createElement('button');
      replay.type = 'button'; replay.className = 'quiet small'; replay.textContent = '個人回放';
      replay.setAttribute('aria-label', `開啟${seatLabel}個人回放`);
      replay.dataset.venueDebriefReplay = String(player.seat);
      replay.dataset.venueDebriefPlayer = player.playerId;
      replay.addEventListener('click', () => replaySeat(player));
      const actions = document.createElement('div');
      actions.className = 'button-row'; actions.append(button, replay);
      if (player.score.hitsReceived > 0) {
        const damage = document.createElement('button');
        damage.type = 'button'; damage.className = 'quiet small'; damage.textContent = '跳到最近中彈';
        damage.setAttribute('aria-label', `跳到${seatLabel}最近中彈`);
        damage.addEventListener('click', () => replaySeat(player, true));
        actions.append(damage);
      }
      row.insertCell().append(actions);
      for (const value of [...countFields.map(field => player.score[field]), `${player.score.accuracyPercent}%`, player.score.health])
        row.insertCell().textContent = value;
      return row;
    }));
    table.hidden = !visible.length;
    onlyMissing.disabled = !players;
    refresh.disabled = !!controller;
    updateCsvButtons();
    if (players) {
      const pending = target.pendingRooms ?? [];
      status.textContent = `已確認 ${players.filter(player => player.acknowledged).length}／${players.length} 席`
        + (!visible.length ? (pending.length ? ' · 已封存房間沒有未確認席位' : ' · 沒有未確認席位') : '')
        + (pending.length ? ` · 房間 ${pending.join('、')} 尚無可核對回條` : '');
    }
  }

  function close() {
    controller?.abort(); controller = null; target = null; players = null;
    csvRequest?.abort(); csvRequest = null; csvStatus.textContent = '';
    panel.hidden = true; onlyMissing.checked = false; status.textContent = ''; render();
  }

  async function read(focusPlayer = null) {
    const state = current(), requested = target;
    if (!active || !requested || controller || state.actor?.role !== 'Master') return;
    const request = new AbortController(); controller = request; players = null;
    const timeout = setTimeout(() => request.abort(), 8000);
    const stateEpoch = state.epoch;
    const inScope = () => controller === request && active && current().epoch === stateEpoch && target?.id === requested.id;
    render(); status.textContent = '正在讀取原批次的席位回條…';
    try {
      const path = `/api/venue/closure/${requested.batchId}`;
      const detailPath = requested.roomId === null ? '/debrief-seats'
        : `/rooms/${requested.roomId}/debrief-receipts?includeScores=true&includePlayerIds=true`;
      const response = await fetch(path + detailPath, {
        headers: { Authorization: 'Bearer ' + state.key }, cache: 'no-store', signal: request.signal
      });
      if (!inScope()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error('Unavailable');
      const body = await response.json();
      if (!inScope()) return;
      if (target.roomId === null) {
        if (body?.version !== 1 || body.requestId !== target.batchId || !Array.isArray(body.rooms)
          || body.rooms.length !== target.rooms.length) throw new Error('Mismatch');
        const returned = new Map(body.rooms.map(room => [room?.roomId, room]));
        players = target.rooms.flatMap(room => validatedPlayers(returned.get(room.roomId), room));
      } else players = validatedPlayers(body, target);
    } catch { if (inScope()) status.textContent = '暫時無法確認原席位回條，可重新讀取。'; }
    finally {
      clearTimeout(timeout);
      if (inScope()) {
        controller = null; render();
        if (uuid.test(focusPlayer ?? '')) rows.querySelector(`[data-venue-debrief-player="${focusPlayer}"]`)?.focus();
      }
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
    batchTarget = rooms.size ? { id: batch.requestId + '/all', batchId: batch.requestId, roomId: null,
      rooms: [...rooms.values()].sort((a, b) => a.roomId - b.roomId),
      pendingRooms: [...counts.values()].filter(count => count.rosterCount > 0 && !rooms.has(count.roomId))
        .map(count => count.roomId).sort((a, b) => a - b) } : null;
    all.hidden = all.disabled = !batchTarget;
    if (!target) return;
    const next = target.roomId === null ? batchTarget : rooms.get(target.roomId);
    if (next?.id !== target.id || next.rosterCount !== target.rosterCount) { close(); return; }
    const before = target.rooms ?? [target], after = next.rooms ?? [next];
    const changedRooms = after.length !== before.length || after.some((room, index) => room.id !== before[index].id);
    const advanced = after.some(room => (before.find(previous => previous.id === room.id)?.confirmedCount ?? -1) < room.confirmedCount
      && (players?.filter(player => player.room.id === room.id && player.acknowledged).length ?? -1) < room.confirmedCount);
    const pendingChanged = String(next.pendingRooms) !== String(target.pendingRooms);
    target = next;
    if (changedRooms || advanced) {
      controller?.abort(); controller = null; void read();
    } else if (pendingChanged && players) render();
  }

  function open(selection, filter = null, focusPlayer = null) {
    if (!active || current().actor?.role !== 'Master' || !selection) return;
    close(); target = selection; panel.hidden = false;
    onlyMissing.checked = filter ?? (selection.roomId === null);
    title.textContent = selection.roomId === null ? '全館席位戰績回條' : `房間 ${selection.roomId} 的戰績回條`;
    title.focus(); void read(focusPlayer);
  }

  onlyMissing.addEventListener('change', render);
  refresh.addEventListener('click', () => void read());
  missingCsv.addEventListener('click', downloadMissing);
  $('venue-debrief-seats-close').addEventListener('click', close);
  all.addEventListener('click', () => open(batchTarget));
  return { update, available: roomId => rooms.has(roomId), active(on) { active = on; if (!on) close(); },
    open: roomId => open(rooms.get(roomId)),
    resume(roomId, filter, playerId) { open(roomId === null ? batchTarget : rooms.get(roomId), filter, playerId); } };
}
