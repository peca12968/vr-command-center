const origins = new Set(['Simulation', 'GameServer']);
const sequence = value => Number.isSafeInteger(value) && value >= 0;
const roomsMatch = (a, b) => Array.isArray(a) && Array.isArray(b) && a.length > 0 && a.length <= 5 && a.length === b.length
  && new Set(a).size === a.length && a.every((room, index) => Number.isInteger(room) && room >= 1 && room <= 5 && room === b[index]);

// Archive state only. This never certifies current poses, local journal receipts, client delivery or safe shutdown.
export function closureView(session, statistics, world, result = 'Waiting') {
  const unknown = { complete: false, combat: '未確認', world: '未確認', text: '正在確認本場次的資料封存狀態。', warning: false };
  if (!session || !sequence(session.sequence) || session.sequence < 1) return unknown;
  if (session.state !== 'Ended') return { ...unknown, combat: '任務結束後確認', world: '任務結束後確認', text: session.state === 'Preparing'
    ? '先啟動本場遊戲伺服器、加入玩家並交付連線檔，再開始任務。' : '任務結束後，這裡會分別確認戰鬥統計與世界回放的封存。' };
  const stream = session.combatStream;
  if (!stream) return { ...unknown, combat: '沒有遊戲來源', world: '沒有遊戲來源', text: '這個場次未連結遊戲來源；只有管理紀錄與統計，沒有可確認的遊戲錄製。' };
  const combat = statistics?.sessionId === session.id && statistics.throughSequence === session.sequence
    && typeof statistics.pendingTelemetry === 'boolean' && sequence(stream.acceptedSequence) && origins.has(stream.origin)
    && typeof stream.sealed === 'boolean';
  const combatSealed = combat && stream.sealed === true && statistics.pendingTelemetry === false;
  const header = world?.header;
  const valid = header?.schemaVersion === 1 && header.sessionId === session.id && typeof stream.streamId === 'string' && stream.streamId.length > 0
    && header.streamId === stream.streamId && header.origin === stream.origin && origins.has(header.origin)
    && roomsMatch(header.roomIds, session.roomIds) && header.missionClockVersion === stream.missionClockVersion
    && [0, 1].includes(header.missionClockVersion) && (header.missionClockVersion === 0 || header.missionDurationSeconds === session.mission?.definition.durationSeconds)
    && sequence(world.acceptedSequence) && typeof world.complete === 'boolean';
  const worldSealed = result === 'Received' && valid && world.complete === true && world.acceptedSequence > 0;
  const complete = combatSealed && worldSealed;
  const worldText = worldSealed ? '已封存' : result === 'Unavailable' ? '暫時無法確認' : result === 'Missing' ? '尚無世界錄製紀錄'
    : result === 'Received' && !valid ? '來源尚未對上' : result === 'Received' ? '等待封存' : '正在確認';
  return { complete, worldComplete: worldSealed, combat: combatSealed ? '已封存' : combat ? '等待封存' : '等待統計同步', world: worldText,
    combatCount: combat ? stream.acceptedSequence : null, worldCount: result === 'Received' && valid ? world.acceptedSequence : null,
    text: complete ? '戰鬥統計與世界回放已封存。請繼續等待遊戲伺服器完成玩家戰績傳送與收尾；此頁不確認送達。'
      : result === 'Unavailable' ? '暫時無法確認世界回放，正在重試；請先保留遊戲伺服器。'
      : result === 'Missing' ? '尚未取得世界錄製紀錄；請先保留遊戲伺服器並確認來源。'
      : result === 'Received' && !valid ? '世界回放尚未對上本場遊戲來源，等待更新。'
      : result === 'Received' && world.acceptedSequence > 0 && !worldSealed ? '已保存的錄製可在「觀戰與任務回放」中查看。封存仍在等待確認。'
      : '場次已結束，仍在等待同一場次的戰鬥統計與世界回放封存。',
    warning: result === 'Unavailable' || result === 'Missing' || result === 'Received' && !valid };
}

export function debriefReceiptPlayers(session, actor, world) {
  const receipts = world?.debriefReceipts;
  if (!receipts || receipts.streamId !== session.combatStream.streamId || receipts.throughSequence !== session.sequence
    || receipts.finalStreamSequence !== session.combatStream.acceptedSequence || receipts.worldSequence !== world.acceptedSequence
    || !Array.isArray(receipts.players) || !Array.isArray(session.players) || !['Master', 'RoomController'].includes(actor.role)) return null;
  const roster = session.players.filter(player => actor.role === 'Master' || player.roomId === actor.roomId);
  if (receipts.players.length !== roster.length || new Set(receipts.players.map(row => row?.playerId)).size !== roster.length
    || !receipts.players.every(row => row && typeof row.acknowledged === 'boolean' && roster.some(player => player.id === row.playerId
      && player.admissionId === row.admissionId && player.roomId === row.roomId && player.name === row.name))) return null;
  return receipts.players;
}

function trackedStartTarget(session, actor, world) {
  const start = world.trackedVrStart;
  const roomId = session.roomIds.length === 1 ? session.roomIds[0] : null;
  if (actor.role !== 'Master' && !(actor.role === 'RoomController' && roomId === actor.roomId)) return null;
  if (!start || start.sessionId !== session.id || start.streamId !== session.combatStream.streamId
    || session.environment?.mode !== 'VR' || world.header.origin !== 'GameServer'
    || !sequence(start.appliedAtSequence) || start.appliedAtSequence < 2 || start.appliedAtSequence >= session.sequence
    || !sequence(start.worldSequence) || start.worldSequence < 1 || start.worldSequence >= world.acceptedSequence
    || !sequence(start.elapsedMilliseconds) || !sequence(world.durationMilliseconds) || start.elapsedMilliseconds > world.durationMilliseconds
    || !Array.isArray(start.players) || start.players.length < 1 || start.players.length > session.roomIds.length * 5
    || !start.players.every(player => /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(player?.playerId)
      && session.roomIds.includes(player.roomId)) || new Set(start.players.map(player => player.playerId)).size !== start.players.length)
    return null;
  return { mode: 'replay', sessionId: session.id, streamId: start.streamId, origin: 'GameServer', roomId, complete: false,
    throughSequence: start.worldSequence, witness: { kind: 'tracked-vr-start', appliedAtSequence: start.appliedAtSequence,
      elapsedMilliseconds: start.elapsedMilliseconds, players: start.players, roomIds: session.roomIds,
      archiveComplete: true, archiveThroughSequence: world.acceptedSequence } };
}

export function mountClosure(getState, unauthorized, openReview, report) {
  const panel = document.getElementById('closure-status'), combat = document.getElementById('closure-combat'), worldLabel = document.getElementById('closure-world'), summary = document.getElementById('closure-summary');
  const retained = document.getElementById('closure-retained');
  const replayButton = document.getElementById('open-closure-replay');
  const trackedStartButton = document.getElementById('open-tracked-vr-start');
  const receiptsPanel = document.getElementById('debrief-receipts'), receiptsLabel = document.getElementById('debrief-receipt-count');
  const receiptsList = document.getElementById('debrief-receipt-players');
  const fieldPanel = document.getElementById('field-evidence'), fieldButton = document.getElementById('download-field-evidence');
  const fieldStatus = document.getElementById('field-evidence-status');
  const reviewPanel = document.getElementById('player-review'), reviewPlayer = document.getElementById('player-review-select');
  const reviewButton = document.getElementById('open-player-review'), damageButton = document.getElementById('open-player-damage');
  let active = false, generation = 0, identity = '', controller = null, attempted = -Infinity, world = null, result = 'Waiting', refreshFailed = false;
  let fieldRequest = null;
  let replayTarget = null, trackedStart = null, reviewTarget = null, reviewOptions = '', receiptRows = '';
  const context = () => {
    const state = getState(), session = state.session;
    return state.actor && state.key && !state.pending && session?.id === state.selected && sequence(session.sequence)
      ? [state.epoch, state.selected, session.sequence, session.combatStream?.streamId || '', state.actor.id, state.actor.role, state.actor.roomId ?? ''].join('/') : '';
  };
  function stop() { generation++; controller?.abort(); controller = null; }
  function clear() {
    stop(); world = null; result = 'Waiting'; attempted = -Infinity;
    fieldRequest?.abort(); fieldRequest = null; fieldStatus.textContent = '';
    receiptsPanel.open = false;
  }
  function render() {
    const state = getState();
    const view = !active || !context() || document.visibilityState !== 'visible' ? { complete: false, combat: '未確認', world: '未確認', text: '選取場次後可確認資料封存狀態。', warning: false }
      : refreshFailed ? { complete: false, combat: '未確認', world: '未確認', text: '場次更新失敗，封存狀態未確認；等待重新取得場次資料。', warning: true }
      : closureView(state.session, state.statistics, world, result);
    combat.textContent = '戰鬥統計：' + view.combat; worldLabel.textContent = '世界回放：' + view.world; summary.textContent = view.text;
    const receipts = view.complete ? debriefReceiptPlayers(state.session, state.actor, world) : null;
    receiptsPanel.hidden = !receipts?.length;
    if (receipts) summary.textContent = '戰鬥統計與世界回放已封存。遊戲伺服器會依原流程完成收尾。';
    const rows = JSON.stringify(receipts);
    if (rows !== receiptRows) {
      receiptRows = rows;
      receiptsLabel.textContent = receipts?.length
        ? `玩家戰績回條 · 已確認 ${receipts.filter(player => player.acknowledged).length}／${receipts.length} 席` : '';
      receiptsList.replaceChildren(...(receipts || []).map(player => {
        const row = document.createElement('li');
        row.textContent = `房間 ${player.roomId} · ${player.name} · ${player.acknowledged ? '已確認' : '未確認'}`;
        return row;
      }));
    }
    const counts = [];
    if (sequence(view.combatCount)) counts.push(`已接受 ${view.combatCount} 筆戰鬥資料`);
    if (sequence(view.worldCount)) counts.push(`已保存 ${view.worldCount} 格錄製`);
    retained.textContent = counts.join(' · '); retained.hidden = counts.length === 0;
    const { session, actor } = state;
    const roomId = actor?.role === 'RoomController' ? actor.roomId
      : session?.roomIds.length === 1 ? session.roomIds[0] : null;
    const scope = actor?.role === 'RoomController' && session?.roomIds.includes(roomId) ? roomId : null;
    replayTarget = view.worldCount > 0 && (actor?.role === 'Master' || scope !== null) ? {
      mode: 'replay', sessionId: session.id, streamId: session.combatStream.streamId, roomId,
      observerRoomId: scope, throughSequence: view.worldCount, complete: view.worldComplete
    } : null;
    replayButton.hidden = !replayTarget;
    replayButton.disabled = !replayTarget || state.busy;
    replayButton.textContent = view.worldComplete ? '回放原場次' : '回放已保存片段';
    trackedStart = view.complete ? trackedStartTarget(session, actor, world) : null;
    trackedStartButton.hidden = !trackedStart;
    trackedStartButton.disabled = !trackedStart || state.busy;
    panel.classList.toggle('closure-complete', view.complete); panel.classList.toggle('warning', view.warning);
    fieldPanel.hidden = state.actor?.role !== 'Master' || state.session?.state !== 'Ended';
    fieldButton.disabled = fieldPanel.hidden || !!fieldRequest || !view.complete || !state.session?.startedAtUtc || !state.statistics?.players?.length;
    renderReview(state, view.complete);
  }
  function renderReview(state, complete) {
    const { session } = state;
    const players = report.players(), roomId = report.roomId();
    const shown = active && session?.state === 'Ended' && players.length > 0;
    const options = JSON.stringify(shown ? [session.id, players.map(player => [player.playerId, player.name, player.roomId])] : null);
    if (options !== reviewOptions) {
      const previous = reviewPlayer.dataset.session === session?.id ? reviewPlayer.value : '';
      reviewPlayer.replaceChildren(new Option('請選擇玩家', ''), ...(shown ? players : []).map(player =>
        new Option(`${player.name} · 房間 ${player.roomId} · ${player.playerId.slice(0, 8)}`, player.playerId)));
      reviewPlayer.value = shown && players.some(player => player.playerId === previous) ? previous : '';
      reviewPlayer.dataset.session = shown ? session.id : '';
      reviewOptions = options;
    }
    const player = players.find(player => player.playerId === reviewPlayer.value);
    reviewTarget = complete && player ? { mode: 'replay', sessionId: session.id, streamId: session.combatStream.streamId,
      throughSequence: world.acceptedSequence, throughCombatSequence: session.combatStream.acceptedSequence, complete: true,
      playerId: player.playerId, playerName: player.name, roomId } : null;
    const reportVisible = shown && !refreshFailed && !!context() && document.visibilityState === 'visible';
    reviewPanel.hidden = !shown;
    reviewPlayer.disabled = !shown || (!complete && !(reportVisible && report.canExportPlayer()));
    reviewButton.disabled = !reviewTarget;
    damageButton.disabled = !reviewTarget || !Number.isSafeInteger(player.hitsReceived) || player.hitsReceived < 1;
    report.update(reportVisible);
  }
  reviewPlayer.addEventListener('change', render);
  replayButton.addEventListener('click', () => { render(); if (!replayButton.disabled) openReview(replayTarget); });
  trackedStartButton.addEventListener('click', () => { render(); if (!trackedStartButton.disabled) openReview(trackedStart); });
  reviewButton.addEventListener('click', () => { render(); if (reviewTarget) openReview(reviewTarget); });
  damageButton.addEventListener('click', () => { render(); if (!damageButton.disabled) openReview({ ...reviewTarget, latestDamage: true }); });
  function reset() { clear(); identity = ''; refreshFailed = false; render(); }
  async function poll() {
    const state = getState(), id = identity, epoch = state.epoch, key = state.key, request = generation;
    if (!active || !id || id !== context() || refreshFailed || document.visibilityState !== 'visible' || controller
      || state.session.state !== 'Ended' || !state.session.combatStream) return;
    const own = new AbortController(); controller = own; attempted = performance.now();
    const current = () => request === generation && active && context() === id && getState().epoch === epoch && getState().key === key && document.visibilityState === 'visible';
    const timeout = setTimeout(() => own.abort(), 5000);
    try {
      const response = await fetch(`/api/sessions/${state.selected}/world?includeDebriefReceipts=true`, { headers: { Authorization: 'Bearer ' + key }, signal: own.signal, cache: 'no-store' });
      if (!current()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (response.status === 404) { world = null; result = 'Missing'; return; }
      if (!response.ok) throw new Error('World archive unavailable');
      const body = await response.json(); if (!current()) return;
      world = body; result = 'Received';
    } catch { if (current()) { world = null; result = 'Unavailable'; } }
    finally { clearTimeout(timeout); if (controller === own) controller = null; if (current()) render(); }
  }
  function update(refreshed = false) {
    const next = context(); if (next !== identity) { clear(); identity = next; }
    if (refreshed) refreshFailed = false;
    render(); if (active && performance.now() - attempted >= 2000) void poll();
  }
  fieldButton.addEventListener('click', async () => {
    if (fieldButton.disabled || fieldRequest) return;
    const { selected: id, key } = getState(), startContext = context(), request = new AbortController();
    const source = `/api/sessions/${id}/field-evidence.zip${trackedStart ? '?includeTrackedVrStart=true' : ''}`;
    const current = () => fieldRequest === request && active && !refreshFailed && context() === startContext
      && getState().key === key && document.visibilityState === 'visible';
    fieldRequest = request; render(); fieldStatus.textContent = '正在下載場館驗收資料…';
    const timeout = setTimeout(() => request.abort(), 8000);
    try {
      const response = await fetch(source, {
        headers: { Authorization: 'Bearer ' + key }, signal: request.signal, cache: 'no-store'
      });
      if (!current()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error(response.status === 404 || response.status === 409
        ? '尚缺封存資料、端點公告或完整名冊，請確認後重試。' : '場館驗收資料下載失敗。');
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== 'application/zip')
        throw new Error('場館驗收資料格式不符。');
      const blob = await response.blob();
      if (!current()) return;
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      try {
        link.href = url; link.download = `vr-command-field-v1-${id}.zip`; document.body.append(link); link.click();
      } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
      fieldStatus.textContent = '驗收資料已下載，請與同場的原始日誌一併保管。';
    } catch (error) {
      if (current()) fieldStatus.textContent = request.signal.aborted ? '下載逾時，可重新下載。' : error.message;
    } finally {
      clearTimeout(timeout);
      if (fieldRequest === request) { fieldRequest = null; render(); }
    }
  });
  setInterval(() => { if (active) update(); }, 500);
  document.addEventListener('visibilitychange', () => { clear(); render(); if (document.visibilityState === 'visible') update(); });
  return { reset, update, invalidate() { clear(); refreshFailed = true; render(); }, active(on) { active = on; clear(); render(); if (on) update(); } };
}
