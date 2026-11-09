import { formatClock } from './mission-clock.js';
import { validEndpoint } from './connection-ui.js';

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
    return { id: player.id, admissionId: player.admissionId, ready: status === 'Participating', kind, state: status, matched: !!row,
      text: labels[status] + (kind === 'Simulated' ? ' · 合成姿態' : kind === 'Tracked' ? ' · 追蹤姿態' : '') };
  });
  const origin = matches && ['Simulation', 'GameServer'].includes(report.origin) ? report.origin + ' · ' : '';
  return { source, rows, text: `${origin}${rows.filter(row => row.ready).length} / ${rows.length} 姿態有效 · ${labels[source]}` };
}

export function mrReadinessView(report, session, elapsed, actor) {
  if (session?.environment?.mode !== 'MR' || !['Preparing', 'Paused', 'Running'].includes(session.state)) return null;
  const resuming = session.state === 'Paused';
  const monitoring = session.state === 'Running';
  const action = monitoring ? 'Monitor' : resuming ? 'Resume' : 'Begin';
  const status = (state, text, rooms = []) => ({ action, state, text, rooms });
  const pending = () => status('Updating', '等待核對目前場次與名冊。');
  if (action === 'Begin' && !session.players.length) return status('EmptyRoster', '請先將 Quest 3 玩家加入名冊。');
  if (report?.version !== 1 || report.sessionId !== session.id || !Number.isSafeInteger(report.sessionSequence)
    || (monitoring ? report.sessionSequence < session.sequence : report.sessionSequence !== session.sequence)) return pending();
  const source = sourceAt(report, elapsed);
  const phase = monitoring ? '執行中' : resuming ? '暫停' : '準備';
  if (source !== 'Fresh') return status('WaitingSource', `等待有效的 MR ${phase}快照 · ${labels[source]}`);
  const readiness = monitoring ? report.mrTrackingState : resuming ? report.mrResumeState : report.mrStartState;
  if (readiness === 'WaitingProfile')
    return status('WaitingProfile', '等待遊戲伺服器的 MR 錄製來源。');
  if (readiness === 'WaitingRevision')
    return status('WaitingRevision', '等待遊戲伺服器同步最新場次設定與名冊。');
  if (!['Ready', 'WaitingPlayers'].includes(readiness) || report.origin !== 'GameServer'
    || (!monitoring && report.observedSequence !== session.sequence) || !Array.isArray(report.players)
    || report.players.length !== session.players.length) return pending();

  const { rows } = readinessView(report, session, elapsed);
  if (monitoring && rows.some(row => !row.matched)) return pending();
  const tracked = new Set(rows.filter(row => row.ready && row.kind === 'Tracked').map(row => row.id));
  const eliminated = new Set(action !== 'Begin' ? rows.filter(row => row.state === 'Eliminated').map(row => row.id) : []);
  if (readiness === 'Ready' && tracked.size + eliminated.size !== session.players.length) return pending();
  const rooms = session.roomIds.filter(room => actor?.role === 'Master' || actor?.roomId === room).map(room => {
    const players = session.players.filter(player => player.roomId === room);
    const living = players.filter(player => !eliminated.has(player.id));
    const waiting = living.filter(player => !tracked.has(player.id)).map(player => player.seat + 1).sort((a, b) => a - b);
    const casualties = players.length - living.length;
    const text = players.length === 0 ? '尚無玩家' : `${living.length - waiting.length} / ${living.length} 追蹤就緒`
      + (waiting.length ? ` · 等候席位 ${waiting.join('、')}` : '') + (casualties ? ` · 已淘汰 ${casualties}` : '');
    return { room, text: `房間 ${room} · ${text}`, attention: monitoring && waiting.length > 0 };
  });
  if (monitoring) return readiness === 'Ready' ? status('Ready', '目前快照中的存活席位都有有效追蹤。', rooms)
    : status('WaitingPlayers', '有存活席位尚無有效追蹤，請查看房間與席位。', rooms);
  return readiness === 'Ready' ? status('Ready', resuming ? '目前快照顯示已符合繼續條件。' : '目前快照顯示全場名冊已就緒。', rooms)
    : status('WaitingPlayers', resuming ? '等待存活玩家重新取得有效追蹤姿態。' : '等待全場名冊的有效追蹤姿態。', rooms);
}

function roomReadinessRow(report, room, session) {
  if (!room.sessionId || session?.id !== room.sessionId || session.state === 'Ended'
    || report?.version !== 1 || !Array.isArray(report.rooms) || report.rooms.length > 5) return null;
  const matches = report.rooms.filter(row => row?.roomId === room.id);
  if (matches.length !== 1) return null;
  const row = matches[0];
  if (row.sessionId !== room.sessionId || !Number.isSafeInteger(row.sessionSequence) || row.sessionSequence < session.sequence
    || !Number.isInteger(row.registered) || row.registered < 0 || row.registered > room.capacity || row.registered !== room.playerCount) return null;
  return row;
}

export function roomEndpointText(report, room, session) {
  const row = roomReadinessRow(report, room, session);
  if (!row) return '連線端點未確認';
  const endpoint = row.endpoint;
  if (endpoint == null) return '等待伺服器公布連線端點';
  if (!validEndpoint(endpoint, session) || endpoint.sessionEnded) return '連線端點未確認';
  return `UDP ${endpoint.address}:${endpoint.port}`
    + (session.mode === 'Linked' ? ' · 五房共用' : '')
    + (endpoint.address.startsWith('127.') ? ' · 僅同機' : '');
}

export function roomVenuePhaseView(report, room, session, elapsed, unavailable = false) {
  const row = roomReadinessRow(report, room, session), phase = row?.venuePhase;
  if (!phase || !Number.isSafeInteger(phase.appliedAtSequence) || phase.appliedAtSequence < 1 || phase.appliedAtSequence > row.sessionSequence
    || !['Begin', 'Pause', 'Resume'].includes(phase.action) || typeof phase.readyToResume !== 'boolean'
    || session.state !== (phase.action === 'Pause' ? 'Paused' : 'Running')) return null;
  const verb = { Begin: '全館開始', Pause: '全館暫停', Resume: '全館繼續' }[phase.action];
  const source = unavailable ? 'Unavailable' : sourceAt(row, elapsed);
  const applied = source === 'Fresh' && Number.isSafeInteger(phase.worldSequence) && phase.worldSequence > 0;
  const ready = applied && phase.action === 'Pause' && phase.readyToResume;
  const text = applied ? `${verb}已套用` + (phase.action === 'Pause' && !ready ? ' · 等候 MR 追蹤' : '')
    : `${verb}待確認 · ${source === 'Fresh' ? '等待階段同步' : labels[source]}`;
  return { applied, ready, action: phase.action, sequence: phase.appliedAtSequence, text };
}

function roomVenueSettingView(row, setting, elapsed, unavailable, label, details) {
  if (!Number.isSafeInteger(setting.appliedAtSequence) || setting.appliedAtSequence < 1
    || setting.appliedAtSequence > row.sessionSequence) return null;
  const source = unavailable ? 'Unavailable' : sourceAt(row, elapsed);
  const applied = source === 'Fresh' && Number.isSafeInteger(setting.worldSequence) && setting.worldSequence > 0;
  const status = applied ? `${label}已套用` : `${label}待確認 · ${source === 'Fresh' ? '等待同步' : labels[source]}`;
  return { applied, text: `${status} · ${details}` };
}

export function roomMissionTimeView(report, room, session, elapsed) {
  const waiting = { state: 'Waiting', text: '活動時間未確認' };
  const duration = session?.mission?.definition?.durationSeconds;
  if (!room.sessionId || room.sessionId !== session?.id || !Number.isInteger(duration) || duration < 60 || duration > 14400) return waiting;
  if (session.state === 'Preparing') return { state: 'Preparing', text: `尚未開始 · 計畫 ${formatClock(duration)}` };
  if (!['Running', 'Paused'].includes(session.state)) return waiting;
  if (session.combatStream?.missionClockVersion === 0) return { state: 'Unsupported', text: '來源未提供活動時間' };
  const row = roomReadinessRow(report, room, session), clock = row?.clock;
  if (!row || sourceAt(row, elapsed) !== 'Fresh' || clock?.phase !== session.state || clock.durationSeconds !== duration
    || clock.autoEnd !== (session.missionClock?.version === 1 && session.missionClock.autoEnd === true)
    || !Number.isSafeInteger(clock.elapsedSeconds) || clock.elapsedSeconds < 0
    || clock.remainingSeconds !== Math.max(0, duration - clock.elapsedSeconds)) return waiting;
  if (clock.autoEnd && clock.remainingSeconds === 0) return { state: 'Due', text: '活動時間已到期 · 等待結束確認' };
  const prefix = session.state === 'Paused' ? '暫停 · ' : '';
  const time = clock.autoEnd ? `剩餘 ${formatClock(clock.remainingSeconds)} · 自動結束`
    : `活動 ${formatClock(clock.elapsedSeconds)} / ${formatClock(duration)}`;
  return { state: session.state, text: prefix + time };
}

export function roomReadinessView(report, room, session, elapsed) {
  const row = roomReadinessRow(report, room, session);
  if (!row) return { source: 'Updating', text: labels.Updating };
  const source = sourceAt(row, elapsed);
  if (source !== 'Fresh') return { source, text: labels[source] };
  const { simulatedReady, trackedReady } = row;
  if (![simulatedReady, trackedReady].every(count => Number.isInteger(count) && count >= 0) || simulatedReady + trackedReady > row.registered)
    return { source: 'Unavailable', text: labels.Unavailable };
  if (session.environment?.mode === 'MR' && session.state === 'Running') {
    const living = row.mrLiving;
    if (!Number.isInteger(living) || living < trackedReady || living > row.registered || simulatedReady !== 0)
      return { source: 'Unavailable', text: labels.Unavailable };
    const missing = living - trackedReady;
    return { source, ready: missing ? 0 : trackedReady, attention: missing > 0,
      text: `MR · ${trackedReady} / ${living} 追蹤就緒` + (missing ? ` · 等候 ${missing} 席` : '') };
  }
  return { source, ready: simulatedReady + trackedReady, text: `${simulatedReady + trackedReady} / ${row.registered} 姿態有效 · 合成 ${simulatedReady} · 追蹤 ${trackedReady}` };
}

export function mountRoomReadiness(getState, unauthorized, venueUpdated, describeClimate, describeEnemies) {
  let active = false, controller, report, started = 0, attempted = -Infinity, failed = false;
  function venueReady(target, action) {
    if (!active || failed) return false;
    const { rooms, sessions } = getState();
    const room = rooms.find(row => row.id === target.roomIds[0] && row.sessionId === target.sessionId);
    const session = sessions.find(row => row.id === target.sessionId);
    if (!room || !session) return false;
    const elapsed = performance.now() - started;
    if (action === 'Begin') {
      const row = roomReadinessRow(report, room, session);
      return session.state === 'Preparing' && row?.sessionSequence === target.sessionSequence
        && row.venueBeginReady === true && sourceAt(row, elapsed) === 'Fresh';
    }
    const venue = roomVenuePhaseView(report, room, session, elapsed);
    return venue?.ready === true && venue.sequence === target.phaseSinceSequence;
  }
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
      cell.classList.toggle('tracking-attention', !!view.attention);
      cell.parentElement.querySelector('[data-room-endpoint]').textContent = roomEndpointText(failed ? null : report, room, session);
      const clock = roomMissionTimeView(failed ? null : report, room, session, elapsed);
      const clockCell = cell.parentElement.querySelector('[data-room-clock]');
      clockCell.textContent = clock.text;
      clockCell.dataset.clockState = clock.state;
      clockCell.classList.toggle('tracking-attention', clock.state === 'Due');
      const phase = roomVenuePhaseView(report, room, session, elapsed, failed);
      const phaseCell = cell.parentElement.querySelector('[data-room-venue-phase]');
      phaseCell.hidden = !phase;
      phaseCell.textContent = phase?.text ?? '';
      phaseCell.classList.toggle('tracking-attention', !!phase && (!phase.applied || (phase.action === 'Pause' && !phase.ready)));
      const row = ['Running', 'Paused'].includes(session?.state) ? roomReadinessRow(report, room, session) : null;
      const environment = row?.venueEnvironment, enemies = row?.venueEnemies;
      const climateView = environment && ['Clear', 'Rain', 'Fog', 'Storm'].includes(environment.weather)
        && ['Day', 'Night'].includes(environment.timeOfDay) && typeof environment.lightning === 'boolean'
        ? roomVenueSettingView(row, environment, elapsed, failed, '全館環境', describeClimate(environment)) : null;
      const enemiesView = enemies && ['Hold', 'Patrol', 'Advance'].includes(enemies.behavior) && typeof enemies.autoAttack === 'boolean'
        ? roomVenueSettingView(row, enemies, elapsed, failed, '全館敵軍策略', describeEnemies(enemies)) : null;
      for (const [selector, setting] of [['[data-room-venue-environment]', climateView], ['[data-room-venue-enemies]', enemiesView]]) {
        const settingCell = cell.parentElement.querySelector(selector);
        settingCell.hidden = !setting;
        settingCell.textContent = setting?.text ?? '';
        settingCell.classList.toggle('tracking-attention', !!setting && !setting.applied);
      }
    }
    venueUpdated();
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
    } catch { if (current()) failed = true; }
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
  return { update, venueReady, active(value) { active = value; if (value) update(); else reset(); } };
}

export function mountReadiness(getState, unauthorized) {
  let active = false, controller, generation = 0, identity = '', report, started = 0, attempted = -Infinity, failed = false;
  const summary = document.getElementById('readiness-summary');
  const mrPanel = document.getElementById('mr-start-requirement'), mrStatus = document.getElementById('mr-start-status');
  const mrRooms = document.getElementById('mr-start-rooms');
  const mrTitle = document.getElementById('mr-start-title'), mrHint = document.getElementById('mr-start-hint');
  let lastMrView;
  function renderMr(view) {
    const key = JSON.stringify(view);
    if (key === lastMrView) return;
    lastMrView = key;
    mrPanel.hidden = !view;
    mrPanel.dataset.state = view?.state || '';
    const resuming = view?.action === 'Resume';
    const monitoring = view?.action === 'Monitor';
    mrTitle.textContent = monitoring ? 'MR 執行中追蹤' : resuming ? 'MR 繼續檢查' : 'MR 開場檢查';
    mrHint.textContent = monitoring ? '需要重新對位時，操作員可先暫停，再用「MR 繼續檢查」確認追蹤。'
      : resuming ? '需要重新對位的玩家可在暫停中完成三點量測。按繼續時，伺服器會再核對當時的快照。'
      : '請讓名冊上的 Quest 3 玩家完成三點對位。按開始時，伺服器會再核對當時的快照。';
    mrStatus.textContent = view?.text || '';
    mrStatus.classList.toggle('ready-player', view?.state === 'Ready');
    mrStatus.classList.toggle('tracking-attention', monitoring && view?.state === 'WaitingPlayers');
    mrRooms.replaceChildren(...(view?.rooms || []).map(({ room, text, attention }) => {
      const item = document.createElement('li');
      item.dataset.mrRoom = room;
      item.textContent = text;
      item.classList.toggle('tracking-attention', !!attention);
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
    const mr = mrReadinessView(report, state.session, elapsed, state.actor);
    renderMr(failed && mr ? { ...mr, state: 'Unavailable', text: 'MR 就緒狀態未確認，正在重試。', rooms: [] } : mr);
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
