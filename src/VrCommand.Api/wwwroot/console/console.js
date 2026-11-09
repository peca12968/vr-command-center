import { mountWorld } from './world-ui.js';
import { mountReplay } from './replay-ui.js';
import { mountLayout } from './layout-ui.js';
import { mountAlignment } from './alignment-ui.js';
import { mountAlignmentPins } from './alignment-pins-ui.js';
import { mountMrDeployment } from './mr-deployment-ui.js';
import { mountMrVenueBundle } from './mr-venue-bundle-ui.js';
import { mountReport } from './report-ui.js';
import { mountReadiness, mountRoomReadiness } from './readiness-ui.js';
import { mountConnections, validDestination } from './connection-ui.js';
import { mountClosure } from './closure-ui.js';
import { placementHistory } from './placement-history.js';
const replay = mountReplay();
const $ = id => document.getElementById(id);
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const behaviorNames = { Hold: '守備', Patrol: '巡邏', Advance: '推進' };
const archiveNames = { NoSource: '沒有遊戲來源', Missing: '尚無錄製紀錄', Waiting: '等待封存', SourceMismatch: '來源尚未對上', Sealed: '已封存' };
const state = { key: '', actor: null, epoch: 0, busy: false, refreshPromise: null, rooms: [], venue: null, missions: [], catalog: [], launchPinned: null, history: null, draftBase: null, draftChanged: false, draftSavedAt: '', sessions: [], session: null, selected: null, pending: null, props: [], prop: -1, environmentSequence: null, enemiesSequence: null };
const objectHistory = placementHistory();
const world = mountWorld(() => state.key, logout);
const report = mountReport(() => state, logout);
const readiness = mountReadiness(() => state, logout);
const roomReadiness = mountRoomReadiness(() => state, logout, applyVenuePermissions);
const connections = mountConnections(() => state, logout);
const closure = mountClosure(() => state, logout);
const alignment = mountAlignment(api, download);
const mrDeployment = mountMrDeployment(() => state, api);
const mrVenue = mountMrVenueBundle(() => state, api, download);
const alignmentPins = mountAlignmentPins({ state: () => state,
  checkFile: file => api('/room-alignment/check-file', 'POST', file),
  pin: (id, roomAlignment, sequence) => runSession(() => {
    const session = state.session;
    if (!master() || session.id !== id || session.environment.mode !== 'MR' || session.state !== 'Preparing' || session.combatStream || session.roomAlignment) {
      notify('場次已變更。請重新確認 MR 校正檔。', true);
      return;
    }
    return command('SetRoomAlignment', { roomAlignment }, sequence);
  }) });
const placement = mountLayout({ api, epoch: () => state.epoch, active: () => !!state.actor, editable: master,
  draft: () => ({ experienceMode: $('draft-mode').value, mode: $('layout-session-mode').value, enemyCount: Number($('draft-count').value), props: structuredClone(state.props) }),
  selectedProp: () => state.prop,
  selection: () => ({ id: $('launch-mission').value, mode: launchLayoutMode() }), changed: applyPermissions,
  selectProp: index => { if (!state.props[index]) return; finishPropGesture(); state.prop = index; renderProps(); $('prop-select').focus(); } });
let timer;
let selectionEpoch = 0;

function notify(message, error = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
  $('notice').hidden = !message;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function option(value, text) { const node = element('option', text); node.value = value; return node; }
function fillOptions(id, entries, preferred) {
  const select = $(id), value = preferred ?? select.value;
  select.replaceChildren(...entries.map(([key, text]) => option(key, text)));
  if (entries.some(([key]) => String(key) === value)) select.value = value;
}
function uuid() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, x => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
function master() { return state.actor?.role === 'Master'; }
function manages(session = state.session) { return !!session && (master() || (state.actor?.role === 'RoomController' && session.mode === 'Independent' && session.roomIds[0] === state.actor.roomId)); }
function ownsRoom(room) { return master() || (state.actor?.role === 'RoomController' && state.actor.roomId === room); }
function launchLayoutMode() { return $('launch-mode').value === 'Linked' ? 'Linked' : 'Independent'; }
function canIssueTicket(session, room) {
  return !!session && session.state !== 'Ended' && (session.environment.mode !== 'MR'
    || /^[a-f0-9]{64}$/.test(session.roomAlignment?.[`room${room}`] ?? ''));
}
function time(value) { return new Date(value).toLocaleTimeString('zh-TW', { hour12: false }); }

async function api(path, method = 'GET', body, requestId, admissionId, responseType = 'json') {
  const controller = new AbortController(), epoch = state.epoch;
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const binary = body instanceof Blob;
    const response = await fetch('/api' + path, { method, headers: { Authorization: 'Bearer ' + state.key, 'Content-Type': binary ? 'application/octet-stream' : 'application/json', ...(requestId ? { 'Idempotency-Key': requestId } : {}), ...(admissionId ? { 'If-Match-Admission': admissionId } : {}) }, body: binary || body === undefined ? body : JSON.stringify(body), signal: controller.signal, cache: 'no-store' });
    if (epoch !== state.epoch) throw new Error('登入狀態已變更，已忽略舊回應。');
    const content = responseType === 'blob' && response.ok ? await response.blob() : await response.text();
    if (epoch !== state.epoch) throw new Error('登入狀態已變更，已忽略舊回應。');
    if (!response.ok) {
      let message = '操作未完成，請重新整理後確認。', layout, code, maxCount, roomIds, roomId;
      try { const data = JSON.parse(content); message = data.error || message; layout = data.layout; code = data.code; maxCount = data.maxCount; roomIds = data.roomIds; roomId = data.roomId; } catch { /* Non-domain errors have no stable JSON contract. */ }
      if (response.status === 401) { logout(); message = '憑證無效或已更換，請重新登入。'; }
      if (response.status === 403) message = '目前身分沒有此操作權限。';
      if (response.status === 409) {
        if (code === 'mr-readiness-required') message = 'MR 場次尚未就緒。請查看「MR 開場檢查」，並確認等候中的 Quest 3 玩家已完成場地對位。';
        else if (code === 'mr-resume-readiness-required') message = 'MR 場次尚未符合繼續條件。請查看「MR 繼續檢查」。';
        else if (code === 'mr-alignment-required') message = '請由主控鎖定 MR 校正檔後再配票。';
        else if (code === 'independent-rooms-occupied' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 使用中，五場都未建立。請確認房間狀態後再試。`;
        else if (code === 'venue-phase-changed') message = '全館場次狀態已變更，本批命令未套用。請重新整理後確認房間。';
        else if (code === 'venue-pause-not-observed' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 尚未回傳有效的暫停快照，本批場次維持暫停。`;
        else if (code === 'venue-resume-not-ready' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 的 MR 追蹤尚未就緒，本批場次維持暫停。`;
        else if (code === 'venue-begin-not-ready' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 的名冊或遊戲快照尚未就緒，本批場次維持準備中。`;
        else message = path.startsWith('/missions') ? '任務版本已變更或原請求內容不一致；草稿仍保留，可載入最新版或另存新任務。' : '場次狀態或名額已變更，請重新整理並確認後再操作。';
      }
      if (layout) message = '場地配置未通過檢查，請修正並保存新版本後再開場。';
      if (code === 'enemy-capacity-exceeded' && Number.isInteger(maxCount)) message = `此場地最多可設定 ${maxCount} 名敵軍。請調低目標數量後再套用。`;
      const error = new Error(message); error.status = response.status; error.layout = layout; error.code = code; error.roomId = roomId; throw error;
    }
    if (responseType === 'blob') return content;
    return content ? JSON.parse(content) : null;
  } finally { clearTimeout(timeout); }
}
async function run(action, independentRead = false) {
  if (state.busy) return;
  const epoch = state.epoch; let refreshFailed = false;
  finishPropGesture(); state.busy = true; applyPermissions();
  try {
    if (state.refreshPromise) {
      try { await state.refreshPromise; }
      catch (error) {
        // Only explicit mission GETs may recover from an unrelated transport / 5xx
        // failure. Writes, authentication failures and a changed login stay fenced.
        if (!independentRead || epoch !== state.epoch || !state.actor || (error.status && error.status < 500)) throw error;
        refreshFailed = true;
      }
    }
    if (epoch !== state.epoch || !state.actor) return;
    await action();
    if (refreshFailed && epoch === state.epoch && state.actor) notify('已讀取任務；背景列表更新失敗，請稍後重新整理。', true);
  }
  catch (error) { notify(error.status ? error.message : '連線或操作結果未確認，請重新整理查看。' + (state.pending ? ' 可使用「重試確認結果」確認原命令。' : ''), true); }
  finally { state.busy = false; applyPermissions(); }
}
function runSession(action) {
  const target = state.session?.id;
  return run(() => {
    if (!target || state.selected !== target || state.session?.id !== target || state.session.state === 'Ended') {
      notify('原場次已結束或不在目前清單。請重新選擇要操作的場次。', true);
      return;
    }
    return action();
  });
}
function logout() {
  selectionEpoch++;
  report.reset(); state.statistics = null;
  closure.active(false); closure.reset();
  alignment.reset();
  alignmentPins.active(false);
  mrDeployment.active(false);
  mrVenue.active(false);
  replay.active(false); replay.reset(); world.active(false); world.reset(); readiness.active(false); readiness.reset(); roomReadiness.active(false); connections.active(false); connections.reset();
  state.epoch++; state.key = ''; state.actor = null; state.selected = null; state.session = null; state.pending = null;
  state.rooms = []; state.venue = null; state.missions = []; state.catalog = []; state.launchPinned = null; state.history = null; state.draftBase = null; state.draftChanged = false; state.draftSavedAt = ''; state.sessions = []; state.refreshPromise = null;
  renderVenueClosure(null);
  state.props = []; state.prop = -1; clearPropHistory();
  placement.reset();
  clearInterval(timer);
  $('workspace').hidden = true; $('login-panel').hidden = false; $('logout').hidden = true;
  $('identity').textContent = '尚未登入'; $('login-key').value = '';
  $('rooms').replaceChildren(); $('roster').replaceChildren(); $('statistics').replaceChildren(); $('event-list').replaceChildren();
  $('ticket-room').replaceChildren(); delete $('ticket-room').dataset.session;
  $('mission-form').reset(); $('launch-mission').replaceChildren(); $('edit-mission').replaceChildren(); renderLaunchPreview(launchPlan()); renderHistory(); renderProps(); $('draft-status').textContent = '尚未儲存的草稿'; $('session-panel').hidden = true; notify('');
}
async function login(event) {
  event.preventDefault();
  if (state.busy) return;
  state.busy = true; $('login-form').querySelector('button').disabled = true;
  state.key = $('login-key').value.trim();
  try {
    const actor = await api('/me');
    if (!['Master', 'RoomController'].includes(actor.role)) { logout(); notify('請使用主控台或房間控制台的操作憑證。', true); return; }
    state.actor = actor;
    tab('operations');
    $('identity').textContent = master() ? '全館主控' : `房間 ${actor.roomId} 控制台`;
    $('login-key').value = ''; $('login-panel').hidden = true; $('workspace').hidden = false; $('logout').hidden = false;
    for (const mode of ['Linked', 'IndependentSet']) $('launch-mode').querySelector(`[value=${mode}]`).disabled = !master();
    $('launch-mode').value = 'Independent';
    $('mission-permission').textContent = master() ? '全館共用任務庫' : '任務庫唯讀，編輯由全館主控負責';
    resetDraft(); notify('');
    await refresh(); timer = setInterval(() => { if (!state.busy && !state.pending && document.visibilityState === 'visible') refresh().catch(showRefreshError); }, 2000);
  } catch (error) { if (!state.actor) state.key = ''; notify(error.status ? error.message : '無法連接控制台服務。', true); }
  finally { state.busy = false; $('login-form').querySelector('button').disabled = false; applyPermissions(); }
}
function showRefreshError(error) { if (state.actor) notify(error.status ? error.message : '更新失敗；目前顯示上次資料，請確認連線。', true); }
function refresh() {
  if (!state.actor || state.pending) return Promise.resolve();
  if (state.refreshPromise) return state.refreshPromise;
  const epoch = state.epoch;
  const pending = refreshData(epoch).catch(error => {
    if (epoch === state.epoch) { closure.invalidate(); state.venue = null; applyVenuePermissions(); renderVenueClosure(null); }
    throw error;
  }).finally(() => { if (state.refreshPromise === pending) state.refreshPromise = null; });
  state.refreshPromise = pending;
  return pending;
}
async function refreshData(epoch) {
  const selection = selectionEpoch, includeEnded = $('include-ended').checked;
  const current = () => epoch === state.epoch && selection === selectionEpoch && includeEnded === $('include-ended').checked;
  const venueRead = master() ? api('/venue/phase').catch(error => { if (error.status === 401) throw error; return null; }) : null;
  const venueClosureRead = master() ? api('/venue/closure').catch(error => { if (error.status === 401) throw error; return null; }) : null;
  const [rooms, catalog, sessions, venue, venueClosure] = await Promise.all([
    api('/rooms'), api('/mission-library'), api('/sessions?includeEnded=' + includeEnded), venueRead, venueClosureRead
  ]);
  if (!current()) return;
  const merged = new Map(state.catalog.map(row => [row.seriesId, row]));
  for (const row of catalog) if (!merged.has(row.seriesId) || merged.get(row.seriesId).number < row.number) merged.set(row.seriesId, row);
  const heads = [...merged.values()].sort((a, b) => Date.parse(b.mission.createdAtUtc) - Date.parse(a.mission.createdAtUtc) || a.mission.id.localeCompare(b.mission.id));
  const launch = $('launch-mission').value, edit = $('edit-mission').value;
  const prior = [...state.catalog, state.launchPinned].find(row => row?.mission.id === launch);
  const editedSeries = state.catalog.find(row => row.mission.id === edit)?.seriesId;
  state.launchPinned = prior && !heads.some(row => row.mission.id === launch) ? prior : null;
  state.rooms = rooms; state.venue = venue; state.catalog = heads; state.missions = heads.map(row => row.mission); state.sessions = sessions;
  renderVenueClosure(venueClosure);
  if (state.selected === null && sessions.length) state.selected = sessions[0].id;
  else if (state.selected && !sessions.some(s => s.id === state.selected)) resetSelection('');
  missionOptions(launch, heads.find(row => row.seriesId === editedSeries)?.mission.id || edit);
  draftStatus();
  fillOptions('session-select', [['', sessions.length ? '請選擇場次' : '目前沒有場次'],
    ...sessions.map(s => [s.id, `${phases[s.state]} · ${s.mission.definition.name} · 房 ${s.roomIds.join('、')}`])], state.selected ?? '');
  $('selection-hint').textContent = state.selected === ''
    ? '請選擇要查看的場次。若要找已結束的場次，請勾選「包含已結束紀錄」。'
    : '選取後可查看名冊、控制環境與統計。';
  const ownRooms = rooms.filter(r => ownsRoom(r.id));
  fillOptions('launch-room', ownRooms.map(r => [String(r.id), `房間 ${r.id}${r.sessionId ? '（使用中）' : '（空閒）'}`]));
  renderRooms();
  const selected = state.selected, previous = state.session;
  if (selected) {
    const [session, statistics] = await Promise.all([api('/sessions/' + selected), api('/sessions/' + selected + '/statistics')]);
    const events = await api(`/sessions/${selected}/events?after=${Math.max(0, session.sequence - 20)}&limit=20`);
    if (!current() || selected !== state.selected) return;
    state.session = session;
    if (previous?.id !== session.id) { loadEnvironment(); loadEnemies(); loadClock(); }
    renderSession(statistics, events);
  }
  $('last-update').textContent = '更新於 ' + time(Date.now());
  applyPermissions();
}
function renderRooms() {
  $('rooms').replaceChildren(...state.rooms.map(room => {
    const card = element('article', undefined, 'room-card'), session = state.sessions.find(s => s.id === room.sessionId);
    const mode = session?.environment.mode === 'MR' ? 'MR · ' : '';
    card.append(element('p', `ROOM 0${room.id}`, 'eyebrow'), element('h3', `房間 ${room.id}`), element('div', `${room.playerCount} / ${room.capacity}`, 'occupancy'), element('p', session ? `${phases[session.state]} · ${mode}${session.mission.definition.name}` : room.sessionId ? '場次使用中' : '房間空閒', 'room-mission'));
    if (room.sessionId) {
      const status = element('p', '正在更新入場狀態', 'hint room-readiness');
      status.dataset.roomReadiness = room.id;
      const clock = element('p', '活動時間未確認', 'hint room-clock');
      clock.dataset.roomClock = room.id;
      const phase = element('p', '', 'hint room-venue-phase');
      phase.dataset.roomVenuePhase = room.id;
      phase.hidden = true;
      card.append(status, clock, phase);
    }
    const button = element('button', room.sessionId ? '查看場次' : '選擇此房間', 'quiet small');
    button.type = 'button'; button.disabled = state.busy || !!state.pending;
    button.addEventListener('click', () => { if (room.sessionId) selectSession(room.sessionId); else { $('launch-room').value = String(room.id); $('launch-mode').value = 'Independent'; placement.scheduleLaunch(); applyPermissions(); $('launch-mission').focus(); } });
    card.append(button); return card;
  }));
  roomReadiness.update();
}
function resetSelection(id) {
  report.reset(); readiness.reset(); connections.reset(); state.statistics = null; state.selected = id; state.session = null;
  closure.reset();
  alignmentPins.reset();
  mrDeployment.reset();
  $('session-panel').hidden = true;
}
async function selectSession(id) {
  if (state.pending || state.busy) { notify('請先確認目前命令的結果。', true); return; }
  const selection = ++selectionEpoch, epoch = state.epoch;
  resetSelection(id);
  if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* Refresh below reports errors. */ } }
  if (selection !== selectionEpoch || epoch !== state.epoch) return;
  try { await refresh(); } catch (error) { showRefreshError(error); }
}
function launchPlan() {
  const missionId = $('launch-mission').value, mode = $('launch-mode').value;
  const revision = state.catalog.find(row => row.mission.id === missionId)
    ?? (state.launchPinned?.mission.id === missionId ? state.launchPinned : null);
  const roomIds = mode === 'Independent' ? [Number($('launch-room').value)] : [1, 2, 3, 4, 5];
  const rooms = roomIds.map(id => state.rooms.find(room => room.id === id && ownsRoom(id)));
  const authorized = master() || (mode === 'Independent' && state.actor?.role === 'RoomController');
  return { revision, rooms, available: authorized && rooms.every(room => room && !room.sessionId),
    body: { missionId, mode, roomIds } };
}
function renderLaunchPreview(plan) {
  const { revision, rooms, body } = plan, preview = $('launch-preview');
  preview.hidden = !revision;
  if (preview.dataset.missionId !== body.missionId) $('launch-preview-briefing').open = false;
  if (!revision) {
    delete preview.dataset.missionId;
    for (const part of ['version', 'rooms', 'duration', 'environment', 'enemies', 'props', 'briefing-text'])
      $('launch-preview-' + part).textContent = '';
    return;
  }
  preview.dataset.missionId = body.missionId;
  const { name, briefing, durationSeconds, environment: env, enemies: enemy, props } = revision.mission.definition;
  const historical = state.catalog.some(row => row.seriesId === revision.seriesId && row.number > revision.number);
  $('launch-preview-version').textContent = `${name} · 第 ${revision.number} 版${historical ? '（歷史）' : ''}`;
  $('launch-preview-rooms').textContent = rooms.every(Boolean)
    ? rooms.map(room => `房間 ${room.id}${room.sessionId ? '（使用中）' : ''}`).join('、') : '尚無可用的房間資訊';
  $('launch-preview-duration').textContent = `${durationSeconds} 秒`;
  $('launch-preview-environment').textContent = `${env.mode} · ${weatherNames[env.weather]} · ${env.timeOfDay === 'Night' ? '夜晚' : '白天'} · ${env.lightning ? '閃電開啟' : '閃電關閉'}`;
  $('launch-preview-enemies').textContent = `${body.mode === 'IndependentSet' ? '各場' : '全場'} ${enemy.count} 名 · ${behaviorNames[enemy.behavior]} · ${enemy.autoAttack ? '自動攻擊開啟' : '自動攻擊關閉'}`;
  const sandbags = props.filter(prop => prop.assetId === 'sandbag').length;
  const barrels = props.filter(prop => prop.assetId === 'barrel').length;
  $('launch-preview-props').textContent = `每房 ${props.length} 件 · 沙包 ${sandbags} · 油桶 ${barrels}`;
  $('launch-preview-briefing-text').textContent = briefing || '此任務未填寫簡報。';
}
function applyPermissions() {
  if (!state.actor) return;
  const session = state.session, ended = session?.state === 'Ended', locked = state.busy || !!state.pending;
  applyVenuePermissions();
  $('create-fields').disabled = locked || state.actor.role === 'GameServer';
  $('launch-room').disabled = $('launch-mode').value !== 'Independent';
  const plan = launchPlan();
  renderLaunchPreview(plan);
  const create = $('create-session-form').querySelector('button');
  create.textContent = plan.body.mode === 'IndependentSet' ? '建立五個準備場次' : '建立準備場次';
  create.disabled = locked || !plan.revision || !plan.available || !placement.canLaunch();
  $('mission-fields').disabled = locked || !master();
  renderPropHistory();
  $('load-mission').disabled = locked || !state.missions.length; $('new-mission').disabled = locked || !master();
  $('edit-mission').disabled = locked;
  $('mission-version').disabled = locked || !state.history;
  $('load-version').disabled = locked || !state.history;
  $('more-versions').disabled = locked || !state.history?.nextBefore;
  $('launch-version').disabled = locked || !state.draftBase;
  $('save-revision').disabled = locked || !master() || !state.draftBase || state.draftBase.number !== knownHeadNumber(state.draftBase.seriesId);
  for (const id of ['environment-fields', 'enemies-fields']) $(id).disabled = locked || !manages() || ended || !session;
  $('clock-fields').disabled = locked || !manages() || session?.state !== 'Preparing' || session?.combatStream?.missionClockVersion !== 1;
  $('join-fields').disabled = locked || session?.state !== 'Preparing';
  const mixedReality = session?.environment.mode === 'MR';
  $('player-headset').querySelector('option[value="ViveXr"]').disabled = mixedReality;
  if (mixedReality) $('player-headset').value = 'Quest3';
  $('ticket-fields').disabled = locked || ended || !session;
  $('download-room-tickets').disabled = locked || !$('ticket-room').value || !canIssueTicket(session, Number($('ticket-room').value));
  const pinHint = $('mr-ticket-pin-hint');
  pinHint.hidden = !mixedReality || ended;
  const pinMessage = session?.roomAlignment
    ? 'MR 連線檔帶有主控鎖定的雜湊。部署時請使用對應房間的原始校正檔。'
    : '請由主控鎖定 MR 校正檔後再配票。';
  if (pinHint.textContent !== pinMessage) pinHint.textContent = pinMessage;
  connections.update();
  for (const button of document.querySelectorAll('[data-command]')) {
    const action = button.dataset.command, phase = session?.state;
    const allowed = action === 'Begin' ? phase === 'Preparing' && session.players.length > 0 : action === 'Pause' ? phase === 'Running' : action === 'Resume' ? phase === 'Paused' : !!session && !ended;
    button.disabled = locked || !manages() || !allowed;
  }
  $('pending-command').hidden = !state.pending;
  $('retry-command').disabled = state.busy;
  $('session-select').disabled = locked;
  $('include-ended').disabled = locked;
  $('refresh').disabled = !!state.pending;
  document.querySelectorAll('.room-card button').forEach(button => { button.disabled = locked; });
  document.querySelectorAll('[data-player-room]').forEach(button => {
    const room = Number(button.dataset.playerRoom);
    button.disabled = locked || ended || !ownsRoom(room) || (button.dataset.playerAction === 'ticket' && !canIssueTicket(session, room));
  });
  alignmentPins.update();
  mrDeployment.update();
  mrVenue.update();
}
function venueTargets(action) {
  const rows = state.venue?.[action.toLowerCase()];
  return Array.isArray(rows) && rows.length <= 5 && rows.every(row => typeof row?.sessionId === 'string'
    && Number.isSafeInteger(row.phaseSinceSequence) && row.phaseSinceSequence > 0 && Array.isArray(row.roomIds)
    && (action !== 'Begin' || (Number.isSafeInteger(row.sessionSequence) && row.sessionSequence >= row.phaseSinceSequence))
    && row.roomIds.length > 0 && row.roomIds.every(id => Number.isInteger(id) && id >= 1 && id <= 5)) ? rows : [];
}
function venueRoomText(targets) { return targets.flatMap(row => row.roomIds).sort((a, b) => a - b).join('、'); }
function applyVenuePermissions() {
  $('venue-phase').hidden = !master();
  const begin = venueTargets('Begin'), pause = venueTargets('Pause'), resume = venueTargets('Resume'), end = venueTargets('End');
  const locked = state.busy || !!state.pending || !master();
  const starting = begin.filter(target => !roomReadiness.venueReady(target, 'Begin'));
  const waiting = resume.filter(target => !roomReadiness.venueReady(target));
  $('venue-begin').disabled = locked || !begin.length || !!starting.length;
  $('venue-pause').disabled = locked || !pause.length;
  $('venue-resume').disabled = locked || !resume.length || !!waiting.length;
  $('venue-end').disabled = locked || !end.length;
  const describe = targets => targets.length ? '房間 ' + venueRoomText(targets) : '無';
  $('venue-end-targets').hidden = !end.length;
  $('venue-end-targets').textContent = end.length ? `可結束 ${describe(end)} · 包含準備、執行與暫停的場次。` : '';
  const beginStatus = $('venue-begin-evidence');
  beginStatus.hidden = !begin.length;
  const beginMessage = starting.length ? `準備開始 ${describe(begin)} · 等候房間 ${venueRoomText(starting)} 的名冊或遊戲快照。`
    : `準備開始 ${describe(begin)} · 目標場次已就緒。`;
  if (beginStatus.textContent !== beginMessage) beginStatus.textContent = beginMessage;
  $('venue-phase-targets').textContent = state.venue ? `可暫停 ${describe(pause)} · 可繼續 ${describe(resume)}` : '等待房間狀態。';
  const evidence = $('venue-phase-evidence');
  evidence.hidden = !resume.length;
  const message = waiting.length ? `等候房間 ${venueRoomText(waiting)} 的遊戲端確認或 MR 追蹤。` : '目標房間的暫停快照已確認。';
  if (evidence.textContent !== message) evidence.textContent = message;
}
async function venuePhase(action) {
  if (!master() || state.pending) return;
  const targets = venueTargets(action);
  if (!targets.length || (['Begin', 'Resume'].includes(action) && targets.some(target => !roomReadiness.venueReady(target, action)))) return;
  const verb = { Begin: '開始', Pause: '暫停', Resume: '繼續', End: '結束' }[action];
  const message = `${verb}房間 ${venueRoomText(targets)} 的 ${targets.length} 個場次？`;
  if (!confirm(action === 'End' ? message + '\n包含尚未開始的準備場次。結束後無法繼續原場次。' : message)) return;
  state.pending = { kind: 'venue-phase', path: '/venue/phase', method: 'POST', requestId: uuid(),
    body: { action, targets: targets.map(({ sessionId, phaseSinceSequence, sessionSequence }) => ({ sessionId, phaseSinceSequence, sessionSequence })) } };
  await sendPending();
}
function renderVenueClosure(report) {
  const panel = $('venue-closure'), batch = report?.batch;
  const signature = master() ? JSON.stringify(report) : '';
  if (panel.dataset.report === signature) return;
  panel.dataset.report = signature;
  panel.hidden = !master() || batch === null;
  const rows = $('venue-closure-rows');
  rows.replaceChildren();
  $('venue-closure-table').hidden = true;
  if (panel.hidden) { $('venue-closure-summary').textContent = ''; return; }
  if (!Array.isArray(batch?.sessions) || !batch.sessions.length || batch.sessions.length > 5
    || !Number.isFinite(Date.parse(batch.recordedAtUtc))
    || batch.sessions.some(session => typeof session?.sessionId !== 'string' || typeof session.missionName !== 'string'
      || !Array.isArray(session.roomIds) || !session.roomIds.length || session.roomIds.length > 5
      || !session.roomIds.every(id => Number.isInteger(id) && id >= 1 && id <= 5)
      || !Object.hasOwn(archiveNames, session.combat) || !Object.hasOwn(archiveNames, session.world))) {
    $('venue-closure-summary').textContent = '暫時無法確認全館封存狀態。';
    return;
  }
  $('venue-closure-summary').textContent = `${new Date(batch.recordedAtUtc).toLocaleString('zh-TW')} · 請等遊戲伺服器完成玩家戰績傳送與收尾。`;
  for (const session of batch.sessions) {
    const button = element('button', '查看場次', 'quiet small');
    button.type = 'button';
    button.addEventListener('click', () => {
      if (!master() || state.busy || state.pending) return;
      $('include-ended').checked = true;
      void selectSession(session.sessionId);
    });
    const result = row([`房間 ${session.roomIds.join('、')}`, session.missionName, archiveNames[session.combat], archiveNames[session.world], button]);
    result.dataset.venueClosureSession = session.sessionId;
    rows.append(result);
  }
  $('venue-closure-table').hidden = false;
}
function row(cells) { const tr = element('tr'); for (const value of cells) { const td = element('td'); if (value instanceof Node) td.append(value); else td.textContent = value; tr.append(td); } return tr; }
function emptyTable(id, columns, message) { const tr = element('tr'), td = element('td', message, 'empty-cell'); td.colSpan = columns; tr.append(td); $(id).replaceChildren(tr); }
function renderSession(statistics, events) {
  state.statistics = statistics; report.update();
  closure.update(true);
  const session = state.session;
  $('session-panel').hidden = false;
  $('session-name').textContent = session.mission.definition.name;
  $('session-meta').textContent = `${session.mode === 'Linked' ? '五房全連線' : '單房獨立'} / 房 ${session.roomIds.join('、')} / 序號 ${session.sequence}`;
  $('session-phase').textContent = phases[session.state]; $('session-phase').className = 'badge ' + session.state.toLowerCase();
  $('session-briefing').textContent = session.mission.definition.briefing;
  $('clock-status').textContent = `計畫 ${session.mission.definition.durationSeconds} 秒 · ${session.missionClock?.autoEnd ? '已啟用到時自動結束' : '手動結束'}${session.combatStream?.missionClockVersion !== 1 ? ' · 等待支援計時的遊戲伺服器就緒' : ''}`;
  const env = session.environment, enemies = session.enemies;
  $('live-environment').textContent = `${env.mode} · ${weatherNames[env.weather]} · ${env.timeOfDay === 'Night' ? '夜晚' : '白天'} · ${env.lightning ? '閃電開啟' : '無閃電'}`;
  $('live-enemies').textContent = `目標 ${enemies.count} 名 · ${behaviorNames[enemies.behavior]} · ${enemies.autoAttack ? '自動攻擊' : '手動設定'}`;
  fillOptions('player-room', session.roomIds.filter(ownsRoom).map(id => [String(id), `房間 ${id}`]));
  const ticketRooms = session.roomIds.filter(ownsRoom).flatMap(id => {
    const count = session.players.filter(player => player.roomId === id).length;
    return count ? [[String(id), `房間 ${id}（${count} 人）`]] : [];
  });
  fillOptions('ticket-room', [['', ticketRooms.length ? '請選擇房間' : '尚無可配票的房間'], ...ticketRooms],
    $('ticket-room').dataset.session === session.id ? undefined : '');
  $('ticket-room').dataset.session = session.id;
  $('player-count').textContent = `${session.players.length} / ${session.roomIds.length * 5} 人（名冊）`;
  $('roster').replaceChildren(...session.players.map(player => {
    const actions = element('div', undefined, 'button-row');
    for (const [kind, label, action, cls] of [['ticket', '下載連線檔', () => downloadTicket(player), 'secondary'], ['remove', '移除', () => removePlayer(player), 'danger']]) {
      const button = element('button', label, cls + ' small'); button.type = 'button'; button.dataset.playerRoom = player.roomId;
      button.dataset.playerAction = kind;
      button.addEventListener('click', () => runSession(action)); actions.append(button);
    }
    const participation = element('span', '等待本次入場同步'); participation.dataset.readinessPlayer = player.id; participation.dataset.admission = player.admissionId;
    return row([player.name, `${player.roomId} / ${player.seat + 1}`, player.headset === 'Quest3' ? 'Quest 3' : 'VIVE XR', participation, actions]);
  }));
  if (!session.players.length) emptyTable('roster', 5, '尚未加入玩家');
  readiness.update();
  connections.update();
  $('statistics-origin').textContent = statistics.origin === 'Simulation' ? '模擬資料' : statistics.origin === 'GameServer' ? '遊戲伺服器回報' : '尚無戰鬥資料';
  $('telemetry-status').hidden = !session.combatStream;
  $('telemetry-status').textContent = statistics.pendingTelemetry ? '已要求結束；等待遊戲伺服器補送事件並封存，統計尚未確認完整。'
    : session.combatStream?.sealed ? '戰鬥事件已全部確認並封存。' : '戰鬥資料接收中；目前統計將隨資料更新。';
  $('statistics').replaceChildren(...statistics.players.map(player => row([player.name, player.ammoUsed, player.kills, player.damageTaken, player.hitsReceived, player.accuracyPercent + '%', player.health])));
  if (!statistics.players.length) emptyTable('statistics', 7, '加入玩家後顯示統計');
  const eventNames = { Created: '建立場次', PlayerJoined: '玩家加入', PlayerLeft: '玩家離開', ControlApplied: '套用控制命令', CombatRecorded: '戰鬥事件', CombatStreamOpened: '綁定戰鬥來源', StreamCombatRecorded: '接收戰鬥事件', CombatStreamSealed: '戰鬥事件封存' };
  $('event-list').replaceChildren(...events.slice().reverse().map(event => {
    const item = element('li'); item.append(element('span', time(event.recordedAtUtc), 'event-time'), element('span', `#${event.sequence} ${eventNames[event.kind] || event.kind}`), element('span', event.actor?.id || '舊版紀錄', 'event-actor')); return item;
  }));
}
function environment(prefix) { return { mode: prefix === 'live' ? state.session.environment.mode : $('draft-mode').value, weather: $(prefix + '-weather').value, timeOfDay: $(prefix + '-time').value, lightning: $(prefix + '-lightning').checked }; }
function enemies(prefix) { return { count: Number($(prefix + '-count').value), behavior: $(prefix + '-behavior').value, autoAttack: $(prefix + '-auto-attack').checked }; }
function setEnvironment(prefix, value) { $(prefix + '-mode').value = value.mode; $(prefix + '-weather').value = value.weather; $(prefix + '-time').value = value.timeOfDay; $(prefix + '-lightning').checked = value.lightning; }
function setEnemies(prefix, value) { $(prefix + '-count').value = value.count; $(prefix + '-behavior').value = value.behavior; $(prefix + '-auto-attack').checked = value.autoAttack; }
function loadEnvironment() { if (state.session) { setEnvironment('live', state.session.environment); state.environmentSequence = state.session.sequence; } }
function loadEnemies() { if (state.session) { setEnemies('live', state.session.enemies); state.enemiesSequence = state.session.sequence; } }
function loadClock() { if (state.session) { $('clock-auto-end').checked = state.session.missionClock?.autoEnd === true; state.clockSequence = state.session.sequence; } }
async function createSession() {
  if (state.pending) return;
  if (!placement.canLaunch()) { placement.scheduleLaunch(); notify('請先完成保存版本的場地檢查，再建立新場次。', true); return; }
  const plan = launchPlan();
  if (!plan.revision || !plan.available) { notify('請選取已保存的任務及空閒房間。', true); return; }
  const independentSet = plan.body.mode === 'IndependentSet';
  state.pending = { kind: independentSet ? 'create-set' : 'create', path: independentSet ? '/sessions/independent-set' : '/sessions',
    method: 'POST', requestId: uuid(), body: independentSet ? { missionId: plan.body.missionId } : plan.body };
  await sendPending();
}
async function command(action, extra = {}, expectedSequence = state.session.sequence) {
  if (state.pending) return;
  if (action === 'End' && !confirm(`結束房間 ${state.session.roomIds.join('、')} 的場次「${state.session.mission.definition.name}」並釋放房間？歷史與統計會保留。`)) return;
  state.pending = { kind: 'command', path: '/sessions/' + state.session.id + '/commands', method: 'POST', body: { commandId: uuid(), action, expectedSequence, ...extra } };
  await sendPending();
}
async function sendPending() {
  const pending = state.pending, epoch = state.epoch;
  if (!pending) return;
  try {
    const response = await api(pending.path, pending.method, pending.body, pending.requestId, pending.admissionId);
    if (state.pending !== pending) return;
    if (pending.kind === 'mission-create' || pending.kind === 'mission-revise') {
      pending.accepted = response.id;
      await refreshData(epoch);
      if (epoch !== state.epoch) return;
      const revision = await api(`/missions/${response.id}/version`);
      if (epoch !== state.epoch) return;
      const history = await api(`/missions/${response.id}/history`);
      if (epoch !== state.epoch) return;
      if (!await rememberHead(history, epoch)) return;
      state.draftBase = revision; state.draftChanged = false; state.draftSavedAt = response.createdAtUtc; state.history = history;
      state.launchPinned = revision; renderHistory(response.id); missionOptions(response.id, history.headId); draftStatus();
      state.pending = null;
      notify('任務保存已確認，原版本與既有場次保持不變。可選擇此版本開場。'); return;
    }
    if (pending.kind === 'create-set') {
      const sessions = response?.sessions;
      if (!Array.isArray(sessions) || sessions.length !== 5 || new Set(sessions.map(session => session?.id)).size !== 5
          || sessions.some((session, index) => !session?.id || session.mode !== 'Independent' || session.roomIds?.length !== 1
            || session.roomIds[0] !== index + 1 || session.mission?.id !== pending.body.missionId))
        throw new Error('Incomplete five-room preparation receipt');
      $('include-ended').checked = sessions.some(session => session.state === 'Ended');
      resetSelection((sessions.find(session => session.state !== 'Ended') ?? sessions[0]).id);
    }
    if (pending.kind === 'venue-phase') {
      const targets = pending.body.targets;
      if (response?.requestId !== pending.requestId || response.action !== pending.body.action || typeof response.duplicate !== 'boolean'
          || !Array.isArray(response.sessions) || response.sessions.length !== targets.length
          || targets.some(target => !response.sessions.some(row => row?.sessionId === target.sessionId
            && Number.isSafeInteger(row.appliedAtSequence) && (pending.body.action === 'Begin'
              ? row.appliedAtSequence === target.sessionSequence + 1 : row.appliedAtSequence > target.phaseSinceSequence))))
        throw new Error('Incomplete venue phase receipt');
    }
    state.pending = null;
    if (pending.kind === 'create') { $('include-ended').checked = response.state === 'Ended'; resetSelection(response.id); }
    if (pending.kind === 'command' && pending.body.action === 'End' && response.session.state === 'Ended') $('include-ended').checked = true;
    const venueEnded = pending.kind === 'venue-phase' && pending.body.action === 'End';
    if (venueEnded) $('include-ended').checked = true;
    if (pending.kind === 'join') $('player-name').value = '';
    await refresh(); loadEnvironment(); loadEnemies(); loadClock();
    notify(venueEnded ? '全館結束已記錄。可查看各場的資料封存狀態。'
      : { create: '場次建立結果已確認。請核對目前狀態，再加入玩家及開始任務。', 'create-set': '五個獨立場次已確認。請由各房核對名冊及準備狀態。', join: '玩家加入操作已確認，請核對目前名冊；尚不代表頭盔在線。', leave: '玩家移出操作已確認，請核對目前名冊。', command: '控制命令已確認。', 'venue-phase': '全館管理命令已確認。可從各房快照核對遊戲端套用狀態。' }[pending.kind]);
  } catch (error) {
    if (pending.kind === 'create' && error.layout) placement.rejected(pending.body.missionId, pending.body.mode, error.layout);
    if (pending.kind === 'create-set' && error.layout) placement.rejected(pending.body.missionId, 'Independent', error.layout);
    if (state.pending === pending && !pending.accepted && error.status >= 400 && error.status < 500) {
      state.pending = null;
      if (pending.kind === 'venue-phase') state.venue = null;
    }
    throw error;
  }
}
async function joinPlayer() {
  if (state.pending) return;
  state.pending = { kind: 'join', path: '/sessions/' + state.selected + '/players', method: 'POST', requestId: uuid(), body: { playerId: uuid(), name: $('player-name').value.trim(), roomId: Number($('player-room').value), headset: $('player-headset').value } };
  await sendPending();
}
async function removePlayer(player) {
  if (state.pending) return;
  if (!player.admissionId) throw new Error('控制台與 API 版本不一致，請更新服務並重新整理。');
  if (!confirm(`將「${player.name}」移出本次入場？此入場票券將立即失效。`)) return;
  state.pending = { kind: 'leave', path: `/sessions/${state.selected}/players/${player.id}`, method: 'DELETE', requestId: uuid(), admissionId: player.admissionId };
  await sendPending();
}
function download(filename, blob) {
  const url = URL.createObjectURL(blob);
  const anchor = element('a'); anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function ticketDestination() {
  const address = $('game-address').value.trim(), port = Number($('game-port').value);
  if (!validDestination(address, port)) {
    notify('請輸入完整 IPv4 位址（例如 192.168.1.100）及 1024–65535 的連線埠。', true);
    return null;
  }
  return { address, port };
}
async function downloadTicket(player) {
  const session = state.session;
  if (!canIssueTicket(session, player.roomId)) return;
  if (!player.admissionId) throw new Error('控制台與 API 版本不一致，請更新服務並重新整理。');
  const destination = ticketDestination();
  if (!destination) return;
  const ticket = await api(`/sessions/${session.id}/players/${player.id}/join-ticket`, 'POST', undefined, undefined, player.admissionId);
  const config = { role: 'Client', ...destination, joinTicket: ticket.ticket };
  if (session.environment.mode === 'MR') {
    if (ticket.roomAlignmentSha256 !== session.roomAlignment[`room${player.roomId}`])
      throw new Error('MR 連線檔的校正雜湊與目前場次不符。');
    config.roomAlignmentSha256 = ticket.roomAlignmentSha256;
  }
  download(`quest-player-${player.id}.json`, new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' }));
  notify(`玩家連線檔已產生，有效至 ${time(ticket.expiresAtUtc)}。請將各自檔案配置到對應玩家端。`);
}
function downloadRoomTickets() {
  const session = state.session, roomId = Number($('ticket-room').value);
  if (!canIssueTicket(session, roomId) || !ownsRoom(roomId) || !session.roomIds.includes(roomId)) return;
  const destination = ticketDestination();
  if (!destination) return;
  const players = session.players.filter(player => player.roomId === roomId)
    .map(player => ({ playerId: player.id, admissionId: player.admissionId }));
  if (!players.length) return;
  void runSession(async () => {
    const bundle = await api(`/sessions/${session.id}/rooms/${roomId}/join-ticket-bundle`, 'POST',
      { ...destination, players }, undefined, undefined, 'blob');
    if (state.session?.id !== session.id || state.selected !== session.id || state.session.state === 'Ended') return;
    if (bundle.type !== 'application/zip') throw new Error('Expected a ZIP download.');
    download(`room-${String(roomId).padStart(2, '0')}-connections.zip`, bundle);
    notify(`房間 ${roomId} 的 ${players.length} 份連線檔已產生。請按檔名席位個別交付，票券有效五分鐘。`);
  });
}

function resetDraft() {
  placement.clearTrial();
  $('mission-form').reset(); state.props = []; state.prop = -1; state.draftBase = null; state.draftChanged = false; state.draftSavedAt = ''; state.history = null;
  clearPropHistory();
  renderProps(); renderHistory(); draftStatus(); applyPermissions();
}
function missionOptions(launch, edit) {
  const entries = state.catalog.map(row => [row.mission.id, `${row.mission.definition.name} · 第 ${row.number} 版`]);
  const pinned = state.launchPinned;
  const launchEntries = pinned && !entries.some(([id]) => id === pinned.mission.id) ? [...entries, [pinned.mission.id, `${pinned.mission.definition.name} · 第 ${pinned.number} 版（歷史）`]] : entries;
  fillOptions('launch-mission', launchEntries.length ? launchEntries : [['', '請先儲存任務']], launch);
  fillOptions('edit-mission', entries.length ? entries : [['', '尚無儲存任務']], edit);
  placement.scheduleLaunch();
}
function knownHeadNumber(seriesId) {
  return Math.max(state.catalog.find(row => row.seriesId === seriesId)?.number || 0, state.history?.seriesId === seriesId ? state.history.headNumber : 0);
}
async function rememberHead(history, epoch) {
  const index = state.catalog.findIndex(row => row.seriesId === history.seriesId), known = state.catalog[index];
  if (known && known.number >= history.headNumber) return epoch === state.epoch;
  const revision = await api(`/missions/${history.headId}/version`);
  if (epoch !== state.epoch) return false;
  const currentIndex = state.catalog.findIndex(row => row.seriesId === history.seriesId), current = state.catalog[currentIndex];
  if (current && current.number >= revision.number) return true;
  if (current?.mission.id === $('launch-mission').value) state.launchPinned = current;
  if (currentIndex < 0) state.catalog.push(revision); else state.catalog[currentIndex] = revision;
  state.missions = state.catalog.map(row => row.mission); return true;
}
function draftStatus() {
  const base = state.draftBase;
  let text = state.draftChanged ? '尚未儲存的修改' : state.draftSavedAt ? '已儲存於 ' + time(state.draftSavedAt) : base ? '已載入草稿' : '尚未儲存的草稿';
  if (base) {
    text += ` · 基於「${base.mission.definition.name}」第 ${base.number} 版`;
    const latest = knownHeadNumber(base.seriesId);
    if (latest > base.number) text += ` · 已有第 ${latest} 版，修訂前請載入最新版，或另存新任務`;
  }
  $('draft-status').textContent = text;
}
function renderHistory(selected) {
  const history = state.history;
  $('mission-history').hidden = !history;
  fillOptions('mission-version', history ? [...history.versions].sort((a, b) => b.number - a.number).map(row => [row.id, `第 ${row.number} 版 · ${row.name} · ${new Date(row.createdAtUtc).toLocaleString('zh-TW')}`]) : [], selected);
  $('history-status').textContent = history ? `已讀取 ${history.versions.length} 版 · 本次查詢最新第 ${history.headNumber} 版` : '';
}
async function loadDraft(id = $('edit-mission').value, older = false) {
  if (!id) return;
  const epoch = state.epoch;
  const history = await api(`/missions/${id}/history`);
  if (epoch !== state.epoch) return;
  const revision = await api(`/missions/${older ? id : history.headId}/version`), mission = revision.mission;
  if (epoch !== state.epoch) return;
  if (!await rememberHead(history, epoch)) return;
  placement.clearTrial();
  const draft = mission.definition;
  $('draft-name').value = draft.name; $('draft-briefing').value = draft.briefing; $('draft-duration').value = draft.durationSeconds;
  setEnvironment('draft', draft.environment); setEnemies('draft', draft.enemies);
  state.props = structuredClone(draft.props); state.prop = state.props.length ? 0 : -1; clearPropHistory();
  state.draftBase = revision; state.draftChanged = false; state.draftSavedAt = ''; state.history = history;
  if (!history.versions.some(row => row.id === mission.id)) history.versions.push({ id: mission.id, number: revision.number, name: draft.name, createdAtUtc: mission.createdAtUtc });
  renderProps(); renderHistory(mission.id); missionOptions(undefined, history.headId); draftStatus();
}
async function saveMission(revise = false) {
  if (state.pending || (revise && !state.draftBase)) return;
  state.pending = { kind: revise ? 'mission-revise' : 'mission-create', path: revise ? `/missions/${state.draftBase.mission.id}/revisions` : '/missions', method: 'POST', requestId: uuid(),
    body: { name: $('draft-name').value.trim(), briefing: $('draft-briefing').value, durationSeconds: Number($('draft-duration').value), environment: environment('draft'), enemies: enemies('draft'), props: structuredClone(state.props) } };
  await sendPending();
}
function svgNode(tag, attributes) { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value); return node; }
function renderProps(updateInspector = true) {
  renderPropHistory();
  const layer = $('prop-layer');
  layer.replaceChildren(...state.props.map((prop, index) => {
    const group = svgNode('g', { transform: `translate(${prop.position.x} ${-prop.position.z}) rotate(${-prop.yawDegrees})`, 'data-index': index, 'data-selected': index === state.prop, role: 'button', tabindex: '0', 'aria-label': `物件 ${index + 1} ${prop.assetId}` });
    const barrel = prop.assetId === 'barrel';
    const shape = barrel ? svgNode('circle', { r: '.35', fill: '#658d87' }) : svgNode('rect', { x: '-1', y: '-.35', width: '2', height: '.7', rx: '.08', fill: '#a69b63' });
    const envelope = svgNode('rect', { x: barrel ? '-.35' : '-1', y: '-.35', width: barrel ? '.7' : '2', height: '.7', fill: 'none', stroke: '#d2dca2', 'stroke-width': '.04', 'stroke-dasharray': '.1 .06', 'data-envelope': prop.assetId });
    const label = svgNode('text', { y: '.12' }); label.textContent = index + 1; group.append(shape, envelope, label); return group;
  }));
  placement.scheduleDraft();
  if (!updateInspector) return;
  fillOptions('prop-select', state.props.length ? state.props.map((p, i) => [String(i), `${i + 1} · ${p.assetId}`]) : [['', '尚無物件']], String(state.prop));
  $('prop-inspector').hidden = state.prop < 0;
  const prop = state.props[state.prop];
  if (prop) { $('prop-asset').value = prop.assetId; for (const axis of ['x', 'y', 'z']) $('prop-' + axis).value = prop.position[axis]; $('prop-yaw').value = prop.yawDegrees; }
}
function editable() { return master() && !state.busy && !state.pending; }
function dirtyDraft() { state.draftChanged = true; draftStatus(); placement.scheduleDraft(); }
let propGesture = null;
function propSnapshot() { return { props: structuredClone(state.props), prop: state.prop }; }
function renderPropHistory() {
  const status = objectHistory.status();
  $('undo-prop').disabled = !editable() || !status.undo;
  $('redo-prop').disabled = !editable() || !status.redo;
  $('prop-history-status').textContent = `可復原 ${status.undo} 步 · 可重做 ${status.redo} 步`;
}
function finishPropGesture() {
  if (propGesture) objectHistory.record(propGesture, propSnapshot());
  propGesture = null; dragging = false; renderPropHistory();
}
function clearPropHistory() { propGesture = null; dragging = false; objectHistory.clear(); renderPropHistory(); }
function beginPropGesture() { if (!propGesture) propGesture = propSnapshot(); }
function editProp(action) {
  if (!editable()) return;
  finishPropGesture(); const before = propSnapshot(); action(); objectHistory.record(before, propSnapshot()); renderProps(); dirtyDraft();
}
function travelProps(undo) {
  if (!editable()) return;
  finishPropGesture(); const result = objectHistory[undo ? 'undo' : 'redo'](propSnapshot());
  if (result) { state.props = result.props; state.prop = result.prop; renderProps(); dirtyDraft(); }
  else renderPropHistory();
}
function addProp(assetId) {
  if (!editable()) return;
  if (state.props.length >= 500) { notify('最多可放置 500 個物件。', true); return; }
  editProp(() => { state.props.push({ assetId, position: { x: 0, y: 0, z: 0 }, yawDegrees: 0 }); state.prop = state.props.length - 1; });
}
function moveProp(x, z) { const prop = state.props[state.prop]; if (prop && editable()) { prop.position.x = Math.round(Math.max(-10, Math.min(10, x)) * 2) / 2; prop.position.z = Math.round(Math.max(-10, Math.min(10, z)) * 2) / 2; renderProps(false); $('prop-x').value = prop.position.x; $('prop-z').value = prop.position.z; dirtyDraft(); } }
let dragging = false, offset = { x: 0, z: 0 };
function mapPoint(event) { const point = $('layout-map').createSVGPoint(); point.x = event.clientX; point.y = event.clientY; const local = point.matrixTransform($('layout-map').getScreenCTM().inverse()); return { x: local.x, z: -local.y }; }
$('layout-map').addEventListener('pointerdown', event => {
  const target = event.target.closest('[data-index]');
  if (!target || !editable()) return;
  event.preventDefault(); state.prop = Number(target.dataset.index); const point = mapPoint(event), prop = state.props[state.prop];
  finishPropGesture(); beginPropGesture();
  offset = { x: prop.position.x - point.x, z: prop.position.z - point.z }; dragging = true;
  $('layout-map').setPointerCapture(event.pointerId); renderProps(); $('layout-map').focus();
});
$('layout-map').addEventListener('pointermove', event => { if (dragging) { const point = mapPoint(event); moveProp(point.x + offset.x, point.z + offset.z); } });
for (const type of ['pointerup', 'pointercancel', 'lostpointercapture', 'blur']) $('layout-map').addEventListener(type, finishPropGesture);
$('layout-map').addEventListener('keyup', event => { if (event.key.startsWith('Arrow')) finishPropGesture(); });
window.addEventListener('blur', finishPropGesture);
document.addEventListener('visibilitychange', () => { if (document.hidden) finishPropGesture(); });
$('layout-map').addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && !event.altKey && ['z', 'y'].includes(event.key.toLowerCase())) {
    event.preventDefault(); if (!event.repeat) travelProps(event.key.toLowerCase() === 'z' && !event.shiftKey); return;
  }
  const target = event.target.closest('[data-index]');
  if ((event.key === 'Enter' || event.key === ' ') && target) { event.preventDefault(); state.prop = Number(target.dataset.index); renderProps(); $('layout-map').focus(); return; }
  const prop = state.props[state.prop];
  if (!prop || !editable()) return;
  const directions = { ArrowLeft: [-.5, 0], ArrowRight: [.5, 0], ArrowUp: [0, .5], ArrowDown: [0, -.5] }, delta = directions[event.key];
  if (delta && !event.ctrlKey && !event.metaKey && !event.altKey) { event.preventDefault(); $('layout-map').focus(); beginPropGesture(); moveProp(prop.position.x + delta[0], prop.position.z + delta[1]); }
});
$('undo-prop').addEventListener('click', () => travelProps(true));
$('redo-prop').addEventListener('click', () => travelProps(false));
$('prop-select').addEventListener('change', () => { finishPropGesture(); state.prop = Number($('prop-select').value); renderProps(); });
for (const id of ['prop-asset', 'prop-x', 'prop-y', 'prop-z', 'prop-yaw']) $(id).addEventListener('change', () => {
  const prop = state.props[state.prop]; if (!prop || !editable()) return;
  const value = $(id).value;
  if (id === 'prop-asset' ? !value.trim() : value === '' || !Number.isFinite(Number(value))) { renderProps(); return; }
  editProp(() => {
    if (id === 'prop-asset') prop.assetId = value.trim();
    else if (id === 'prop-yaw') prop.yawDegrees = Number(value); else prop.position[id.slice(-1)] = Number(value);
  });
});

function tab(name) {
  if (name !== 'missions') placement.clearTrial();
  finishPropGesture();
  for (const candidate of ['operations', 'missions', 'replay', 'world']) { const active = candidate === name; $(candidate + '-view').hidden = !active; $('tab-' + candidate).classList.toggle('active', active); $('tab-' + candidate).setAttribute('aria-pressed', String(active)); }
  replay.active(name === 'replay'); world.active(name === 'world'); readiness.active(name === 'operations'); connections.active(name === 'operations');
  roomReadiness.active(name === 'operations');
  closure.active(name === 'operations');
  alignment.active(name === 'missions' && master());
  alignmentPins.active(name === 'operations');
  mrDeployment.active(name === 'operations');
  mrVenue.active(name === 'operations');
}
function submit(id, action, execute = run) { $(id).addEventListener('submit', event => { event.preventDefault(); execute(action); }); }
$('login-form').addEventListener('submit', login);
$('logout').addEventListener('click', logout);
$('refresh').addEventListener('click', () => refresh().then(() => notify('已更新。')).catch(showRefreshError));
$('include-ended').addEventListener('change', async () => {
  const epoch = state.epoch;
  if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* Refresh below reports errors. */ } }
  if (epoch === state.epoch) await refresh().catch(showRefreshError);
});
$('session-select').addEventListener('change', () => selectSession($('session-select').value));
$('launch-mode').addEventListener('change', () => { placement.scheduleLaunch(); applyPermissions(); });
$('launch-mission').addEventListener('change', () => { placement.scheduleLaunch(); applyPermissions(); });
$('launch-room').addEventListener('change', applyPermissions);
$('reload-environment').addEventListener('click', loadEnvironment);
$('reload-enemies').addEventListener('click', loadEnemies);
$('retry-command').addEventListener('click', () => run(sendPending));
$('venue-begin').addEventListener('click', () => run(() => venuePhase('Begin')));
$('venue-pause').addEventListener('click', () => run(() => venuePhase('Pause')));
$('venue-resume').addEventListener('click', () => run(() => venuePhase('Resume')));
$('venue-end').addEventListener('click', () => run(() => venuePhase('End')));
$('download-room-tickets').addEventListener('click', downloadRoomTickets);
$('ticket-room').addEventListener('change', applyPermissions);
document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => runSession(() => command(button.dataset.command))));
submit('create-session-form', createSession);
submit('join-form', joinPlayer, runSession);
submit('environment-form', () => command('SetEnvironment', { environment: environment('live') }, state.environmentSequence), runSession);
submit('enemies-form', () => command('SetEnemies', { enemies: enemies('live') }, state.enemiesSequence), runSession);
submit('clock-form', () => command('SetMissionClock', { missionClock: { autoEnd: $('clock-auto-end').checked } }, state.clockSequence), runSession);
$('reload-clock').addEventListener('click', loadClock);
$('clock-auto-end').addEventListener('change', () => { state.clockSequence = state.session?.sequence; });
submit('mission-form', saveMission);
$('load-mission').addEventListener('click', () => run(() => loadDraft(), true));
$('load-version').addEventListener('click', () => run(() => loadDraft($('mission-version').value, true), true));
$('more-versions').addEventListener('click', () => run(async () => {
  if (!state.history?.nextBefore) return;
  const previous = state.history, epoch = state.epoch;
  const history = await api(`/missions/${previous.seriesId}/history?before=${previous.nextBefore}`);
  if (epoch !== state.epoch || state.history !== previous) return;
  history.versions = [...previous.versions, ...history.versions.filter(row => !previous.versions.some(old => old.id === row.id))];
  state.history = history; renderHistory(); draftStatus();
}, true));
$('save-revision').addEventListener('click', () => { if ($('mission-form').reportValidity()) run(() => saveMission(true)); });
$('launch-version').addEventListener('click', () => {
  if (!state.draftBase || state.pending || state.busy) return;
  state.launchPinned = state.draftBase; missionOptions(state.draftBase.mission.id); tab('operations');
  notify(`已選取保存的第 ${state.draftBase.number} 版開場；未儲存的草稿修改不會套用。`);
});
$('new-mission').addEventListener('click', () => { if (confirm('清除目前未儲存的草稿並建立新任務？')) resetDraft(); });
$('add-sandbag').addEventListener('click', () => addProp('sandbag'));
$('add-barrel').addEventListener('click', () => addProp('barrel'));
$('rotate-prop').addEventListener('click', () => { if (state.props[state.prop]) editProp(() => { state.props[state.prop].yawDegrees = (state.props[state.prop].yawDegrees + 15) % 360; }); });
$('remove-prop').addEventListener('click', () => { if (state.prop >= 0) editProp(() => { state.props.splice(state.prop, 1); state.prop = Math.min(state.prop, state.props.length - 1); }); });
for (const type of ['input', 'change']) $('mission-form').addEventListener(type, event => {
  if (!['layout-session-mode', 'prop-select'].includes(event.target.id)) dirtyDraft();
});
$('layout-session-mode').addEventListener('change', () => placement.scheduleDraft());
$('layout-recheck-draft').addEventListener('click', () => placement.recheckDraft());
$('layout-recheck-launch').addEventListener('click', () => placement.recheckLaunch());
for (const name of ['operations', 'missions', 'replay', 'world']) $('tab-' + name).addEventListener('click', () => tab(name));
window.addEventListener('beforeunload', event => { if (state.pending) { event.preventDefault(); event.returnValue = ''; } });
