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
  let worldText = worldSealed ? '已封存' : result === 'Unavailable' ? '暫時無法確認' : result === 'Missing' ? '尚無世界錄製紀錄'
    : result === 'Received' && !valid ? '來源尚未對上' : result === 'Received' ? '等待封存' : '正在確認';
  return { complete, combat: combatSealed ? '已封存' : combat ? '等待封存' : '等待統計同步', world: worldText,
    text: complete ? '戰鬥統計與世界回放已封存。請繼續等待遊戲伺服器完成玩家戰績傳送與收尾；此頁不確認送達。'
      : result === 'Unavailable' ? '暫時無法確認世界回放，正在重試；請先保留遊戲伺服器。'
      : result === 'Missing' ? '尚未取得世界錄製紀錄；請先保留遊戲伺服器並確認來源。'
      : result === 'Received' && !valid ? '世界回放尚未對上本場遊戲來源，等待更新。'
      : '場次已結束，仍在等待同一場次的戰鬥統計與世界回放封存。',
    warning: result === 'Unavailable' || result === 'Missing' || result === 'Received' && !valid };
}

export function mountClosure(getState, unauthorized) {
  const panel = document.getElementById('closure-status'), combat = document.getElementById('closure-combat'), worldLabel = document.getElementById('closure-world'), summary = document.getElementById('closure-summary');
  let active = false, generation = 0, identity = '', controller = null, attempted = -Infinity, world = null, result = 'Waiting', refreshFailed = false;
  const context = () => {
    const state = getState(), session = state.session;
    return state.actor && state.key && !state.pending && session?.id === state.selected && sequence(session.sequence)
      ? [state.epoch, state.selected, session.sequence, session.combatStream?.streamId || '', state.actor.id, state.actor.role, state.actor.roomId ?? ''].join('/') : '';
  };
  function stop() { generation++; controller?.abort(); controller = null; }
  function clear() { stop(); world = null; result = 'Waiting'; attempted = -Infinity; }
  function render() {
    const state = getState();
    const view = !active || !context() || document.visibilityState !== 'visible' ? { complete: false, combat: '未確認', world: '未確認', text: '選取場次後可確認資料封存狀態。', warning: false }
      : refreshFailed ? { complete: false, combat: '未確認', world: '未確認', text: '場次更新失敗，封存狀態未確認；等待重新取得場次資料。', warning: true }
      : closureView(state.session, state.statistics, world, result);
    combat.textContent = '戰鬥統計：' + view.combat; worldLabel.textContent = '世界回放：' + view.world; summary.textContent = view.text;
    panel.classList.toggle('closure-complete', view.complete); panel.classList.toggle('warning', view.warning);
  }
  function reset() { clear(); identity = ''; refreshFailed = false; render(); }
  async function poll() {
    const state = getState(), id = identity, epoch = state.epoch, key = state.key, request = generation;
    if (!active || !id || id !== context() || refreshFailed || document.visibilityState !== 'visible' || controller
      || state.session.state !== 'Ended' || !state.session.combatStream) return;
    const own = new AbortController(); controller = own; attempted = performance.now();
    const current = () => request === generation && active && context() === id && getState().epoch === epoch && getState().key === key && document.visibilityState === 'visible';
    const timeout = setTimeout(() => own.abort(), 5000);
    try {
      const response = await fetch(`/api/sessions/${state.selected}/world`, { headers: { Authorization: 'Bearer ' + key }, signal: own.signal, cache: 'no-store' });
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
  setInterval(() => { if (active) update(); }, 500);
  document.addEventListener('visibilitychange', () => { clear(); render(); if (document.visibilityState === 'visible') update(); });
  return { reset, update, invalidate() { clear(); refreshFailed = true; render(); }, active(on) { active = on; clear(); render(); if (on) update(); } };
}
