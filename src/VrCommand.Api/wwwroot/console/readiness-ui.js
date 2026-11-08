const labels = { NoRecording: '等待遊戲來源', WaitingFrame: '等待第一份快照', UnknownCaptureTime: '擷取時間未知', ClockSkew: '來源時鐘未同步',
  Stale: '快照已過期', Suspended: '管理連線中斷', PhasePending: '等待階段同步', Ended: '場次已結束', Fresh: '正在接收',
  AwaitingAdmission: '等待本次入場同步', AwaitingPose: '等待姿態', PoseUnavailable: '姿態未就緒／中斷', Eliminated: '已淘汰',
  Participating: '姿態有效', Updating: '正在更新入場狀態', Unavailable: '參戰狀態未確認' };

function sourceAt(report, elapsed) {
  const source = Object.hasOwn(labels, report.sourceState) ? report.sourceState : 'Unavailable';
  if (source === 'Fresh' && (!Number.isFinite(elapsed) || elapsed < 0 || elapsed > 1500 || !Number.isFinite(report.sourceAgeMilliseconds)
    || report.sourceAgeMilliseconds + elapsed > 1500 || report.sourceAgeMilliseconds + elapsed < -1000)) return 'Stale';
  return source;
}

export function readinessView(report, session, elapsed) {
  const matches = report?.version === 1 && report.sessionId === session?.id && Number.isSafeInteger(report.sessionSequence)
    && report.sessionSequence >= session.sequence && Array.isArray(report.players) && report.players.length <= 25;
  const source = session?.state === 'Ended' ? 'Ended' : !matches ? 'Updating' : sourceAt(report, elapsed);
  const rows = (session?.players || []).map(player => {
    const candidates = matches ? report.players.filter(row => row?.playerId === player.id && row.admissionId === player.admissionId && row.roomId === player.roomId && row.seat === player.seat) : [];
    const row = candidates.length === 1 ? candidates[0] : null;
    const kind = ['Simulated', 'Tracked'].includes(row?.rigKind) ? row.rigKind : 'None';
    let status = source !== 'Fresh' ? source : !row ? 'AwaitingAdmission' : Object.hasOwn(labels, row.state) ? row.state : 'Unavailable';
    if (status === 'Participating' && (row?.canParticipate !== true || kind === 'None')) status = 'Unavailable';
    return { id: player.id, admissionId: player.admissionId, ready: status === 'Participating', kind,
      text: labels[status] + (kind === 'Simulated' ? ' · 合成姿態' : kind === 'Tracked' ? ' · 追蹤姿態' : '') };
  });
  const origin = matches && ['Simulation', 'GameServer'].includes(report.origin) ? report.origin + ' · ' : '';
  return { source, rows, text: `${origin}${rows.filter(row => row.ready).length} / ${rows.length} 姿態有效 · ${labels[source]}` };
}

export function mrStartView(report, session, elapsed, actor) {
  if (session?.environment?.mode !== 'MR' || session.state !== 'Preparing') return null;
  const status = (state, text, rooms = []) => ({ state, text, rooms });
  const pending = () => status('Updating', '等待核對目前場次與名冊。');
  if (!session.players.length) return status('EmptyRoster', '請先將 Quest 3 玩家加入名冊。');
  if (report?.version !== 1 || report.sessionId !== session.id || report.sessionSequence !== session.sequence) return pending();
  const source = sourceAt(report, elapsed);
  if (source !== 'Fresh') return status('WaitingSource', '等待有效的 MR 準備快照 · ' + labels[source]);
  if (report.mrStartState === 'WaitingProfile')
    return status('WaitingProfile', '等待遊戲伺服器的 MR 錄製來源。');
  if (report.mrStartState === 'WaitingRevision')
    return status('WaitingRevision', '等待遊戲伺服器同步最新場次設定與名冊。');
  if (!['Ready', 'WaitingPlayers'].includes(report.mrStartState) || report.origin !== 'GameServer'
    || report.observedSequence !== session.sequence || !Array.isArray(report.players)
    || report.players.length !== session.players.length) return pending();

  const { rows } = readinessView(report, session, elapsed);
  const tracked = new Set(rows.filter(row => row.ready && row.kind === 'Tracked').map(row => row.id));
  if (report.mrStartState === 'Ready' && tracked.size !== session.players.length) return pending();
  const rooms = session.roomIds.filter(room => actor?.role === 'Master' || actor?.roomId === room).map(room => {
    const players = session.players.filter(player => player.roomId === room);
    const waiting = players.filter(player => !tracked.has(player.id)).map(player => player.seat + 1).sort((a, b) => a - b);
    const text = players.length === 0 ? '尚無玩家' : `${players.length - waiting.length} / ${players.length} 追蹤就緒`
      + (waiting.length ? ` · 等候席位 ${waiting.join('、')}` : '');
    return { room, text: `房間 ${room} · ${text}` };
  });
  return report.mrStartState === 'Ready' ? status('Ready', '目前快照顯示全場名冊已就緒。', rooms)
    : status('WaitingPlayers', '等待全場名冊的有效追蹤姿態。', rooms);
}

export function roomReadinessView(report, room, session, elapsed) {
  const waiting = { source: 'Updating', text: labels.Updating };
  if (!room.sessionId || session?.id !== room.sessionId || session.state === 'Ended'
    || report?.version !== 1 || !Array.isArray(report.rooms) || report.rooms.length > 5) return waiting;
  const matches = report.rooms.filter(row => row?.roomId === room.id);
  if (matches.length !== 1) return waiting;
  const row = matches[0];
  if (row.sessionId !== room.sessionId || !Number.isSafeInteger(row.sessionSequence) || row.sessionSequence < session.sequence
    || !Number.isInteger(row.registered) || row.registered < 0 || row.registered > room.capacity || row.registered !== room.playerCount) return waiting;
  const source = sourceAt(row, elapsed);
  if (source !== 'Fresh') return { source, text: labels[source] };
  const { simulatedReady, trackedReady } = row;
  if (![simulatedReady, trackedReady].every(count => Number.isInteger(count) && count >= 0) || simulatedReady + trackedReady > row.registered)
    return { source: 'Unavailable', text: labels.Unavailable };
  return { source, ready: simulatedReady + trackedReady, text: `${simulatedReady + trackedReady} / ${row.registered} 姿態有效 · 合成 ${simulatedReady} · 追蹤 ${trackedReady}` };
}

export function mountRoomReadiness(getState, unauthorized) {
  let active = false, controller, report, started = 0, attempted = -Infinity, failed = false;
  function render() {
    const { rooms, sessions } = getState();
    const elapsed = performance.now() - started;
    for (const cell of document.querySelectorAll('[data-room-readiness]')) {
      const room = rooms.find(value => value.id === Number(cell.dataset.roomReadiness));
      if (!room?.sessionId) continue;
      const session = sessions.find(value => value.id === room.sessionId);
      const view = failed ? { source: 'Unavailable', text: labels.Unavailable } : roomReadinessView(report, room, session, elapsed);
      cell.textContent = view.text;
      cell.dataset.sourceState = view.source;
      cell.classList.toggle('ready-player', view.ready > 0);
    }
  }
  async function poll() {
    const { epoch, key } = getState();
    const own = new AbortController();
    controller = own;
    const began = attempted = performance.now();
    const timeout = setTimeout(() => own.abort(), 5000);
    const current = () => controller === own && active && getState().epoch === epoch && getState().key === key;
    try {
      const response = await fetch('/api/rooms/readiness', { headers: { Authorization: 'Bearer ' + key }, signal: own.signal, cache: 'no-store' });
      if (!current()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error('Room readiness unavailable');
      const value = await response.json();
      if (current()) { report = value; started = began; failed = false; }
    } catch { if (current()) { report = null; failed = true; } }
    finally {
      clearTimeout(timeout);
      if (current()) { controller = null; render(); }
    }
  }
  function reset() {
    controller?.abort(); controller = null; report = null; attempted = -Infinity; failed = false;
    render();
  }
  function update() {
    const state = getState();
    if (!active || !state.actor || document.visibilityState !== 'visible') return;
    render();
    if (!controller && state.rooms.some(room => room.sessionId) && performance.now() - attempted >= 1000) void poll();
  }
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') update(); else reset(); });
  setInterval(update, 250);
  return { update, active(value) { active = value; if (value) update(); else reset(); } };
}

export function mountReadiness(getState, unauthorized) {
  let active = false, controller, generation = 0, identity = '', report, started = 0, attempted = -Infinity, failed = false;
  const summary = document.getElementById('readiness-summary');
  const mrPanel = document.getElementById('mr-start-requirement'), mrStatus = document.getElementById('mr-start-status');
  const mrRooms = document.getElementById('mr-start-rooms');
  let lastMrView;
  function renderMr(view) {
    const key = JSON.stringify(view);
    if (key === lastMrView) return;
    lastMrView = key;
    mrPanel.hidden = !view;
    mrPanel.dataset.state = view?.state || '';
    mrStatus.textContent = view?.text || '';
    mrStatus.classList.toggle('ready-player', view?.state === 'Ready');
    mrRooms.replaceChildren(...(view?.rooms || []).map(({ room, text }) => {
      const item = document.createElement('li');
      item.dataset.mrRoom = room;
      item.textContent = text;
      return item;
    }));
  }
  function reset() {
    generation++; controller?.abort(); controller = null; identity = ''; report = null; failed = false; attempted = -Infinity; summary.textContent = '等待選取場次。';
    renderMr(null);
    for (const cell of document.querySelectorAll('[data-readiness-player]')) { cell.textContent = '等待本次入場同步'; cell.classList.remove('ready-player'); }
  }
  function render() {
    const state = getState(); if (!state.actor || !state.session || state.session.id !== state.selected) return;
    const elapsed = performance.now() - started;
    const view = readinessView(report, state.session, elapsed);
    const mr = mrStartView(report, state.session, elapsed, state.actor);
    renderMr(failed && mr ? { state: 'Unavailable', text: '開場狀態未確認，正在重試。', rooms: [] } : mr);
    summary.textContent = failed ? '參戰狀態未確認，正在重試。' : view.text;
    summary.classList.toggle('warning', failed || ['Stale', 'ClockSkew', 'Suspended', 'Unavailable'].includes(view.source));
    for (const cell of document.querySelectorAll('[data-readiness-player]')) {
      const row = view.rows.find(value => value.id === cell.dataset.readinessPlayer && value.admissionId === cell.dataset.admission);
      cell.textContent = row?.text || '等待本次入場同步'; cell.classList.toggle('ready-player', !!row?.ready && !failed);
    }
  }
  async function poll() {
    const state = getState(); if (!active || !state.actor || !state.session || state.session.id !== state.selected || document.visibilityState !== 'visible' || controller) return;
    const id = state.selected, epoch = state.epoch, key = state.key, request = generation;
    const own = new AbortController(); controller = own; attempted = performance.now();
    const began = attempted, timeout = setTimeout(() => own.abort(), 5000);
    const current = () => request === generation && active && getState().selected === id && getState().epoch === epoch && getState().key === key;
    try {
      const response = await fetch(`/api/sessions/${id}/readiness`, { headers: { Authorization: 'Bearer ' + key }, signal: own.signal, cache: 'no-store' });
      if (!current()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (!response.ok) throw new Error('Readiness unavailable');
      const value = await response.json(); if (!current()) return;
      report = value; started = began; failed = false;
    } catch { if (current()) { report = null; failed = true; } }
    finally { clearTimeout(timeout); if (controller === own) controller = null; if (current()) render(); }
  }
  function update() {
    if (!active || document.visibilityState !== 'visible') return;
    const state = getState(), next = state.actor && state.session?.id === state.selected ? state.epoch + '/' + state.selected : '';
    if (next !== identity) { reset(); identity = next; }
    render(); if (performance.now() - attempted >= 1000) void poll();
  }
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') update(); else reset(); });
  setInterval(() => { if (active) update(); }, 250);
  return { update, reset, active(value) { active = value; if (!value) reset(); else update(); } };
}
