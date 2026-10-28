import { mountReplay } from './replay-ui.js';
const replay = mountReplay();
const $ = id => document.getElementById(id);
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const behaviorNames = { Hold: '守備', Patrol: '巡邏', Advance: '推進' };
const state = { key: '', actor: null, epoch: 0, busy: false, refreshPromise: null, rooms: [], missions: [], sessions: [], session: null, selected: '', pending: null, props: [], prop: -1, environmentSequence: null, enemiesSequence: null };
let timer;

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
function time(value) { return new Date(value).toLocaleTimeString('zh-TW', { hour12: false }); }

async function api(path, method = 'GET', body, requestId) {
  const controller = new AbortController(), epoch = state.epoch;
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch('/api' + path, { method, headers: { Authorization: 'Bearer ' + state.key, 'Content-Type': 'application/json', ...(requestId ? { 'Idempotency-Key': requestId } : {}) }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal, cache: 'no-store' });
    if (epoch !== state.epoch) throw new Error('登入狀態已變更，已忽略舊回應。');
    const content = await response.text();
    if (epoch !== state.epoch) throw new Error('登入狀態已變更，已忽略舊回應。');
    if (!response.ok) {
      let message = '操作未完成，請重新整理後確認。';
      try { message = JSON.parse(content).error || message; } catch { /* Non-domain errors have no stable JSON contract. */ }
      if (response.status === 401) { logout(); message = '憑證無效或已更換，請重新登入。'; }
      if (response.status === 403) message = '目前身分沒有此操作權限。';
      if (response.status === 409) message = '場次狀態或名額已變更，請重新整理並確認後再操作。';
      const error = new Error(message); error.status = response.status; throw error;
    }
    return content ? JSON.parse(content) : null;
  } finally { clearTimeout(timeout); }
}
async function run(action) {
  if (state.busy) return;
  state.busy = true; applyPermissions();
  try { if (state.refreshPromise) await state.refreshPromise; await action(); }
  catch (error) { notify(error.status ? error.message : '連線或操作結果未確認，請重新整理查看。' + (state.pending ? ' 可使用「重試確認結果」確認原命令。' : ''), true); }
  finally { state.busy = false; applyPermissions(); }
}
function logout() {
  replay.active(false); replay.reset();
  state.epoch++; state.key = ''; state.actor = null; state.selected = ''; state.session = null; state.pending = null;
  state.rooms = []; state.missions = []; state.sessions = []; state.refreshPromise = null;
  state.props = []; state.prop = -1;
  clearInterval(timer);
  $('workspace').hidden = true; $('login-panel').hidden = false; $('logout').hidden = true;
  $('identity').textContent = '尚未登入'; $('login-key').value = '';
  $('rooms').replaceChildren(); $('roster').replaceChildren(); $('statistics').replaceChildren(); $('event-list').replaceChildren();
  $('mission-form').reset(); $('session-panel').hidden = true; notify('');
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
    $('launch-mode').querySelector('[value=Linked]').disabled = !master();
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
  const pending = refreshData(epoch).finally(() => { if (state.refreshPromise === pending) state.refreshPromise = null; });
  state.refreshPromise = pending;
  return pending;
}
async function refreshData(epoch) {
  const [rooms, missions, sessions] = await Promise.all([api('/rooms'), api('/missions'), api('/sessions?includeEnded=' + $('include-ended').checked)]);
  if (epoch !== state.epoch) return;
  state.rooms = rooms; state.missions = missions; state.sessions = sessions;
  if (!sessions.some(s => s.id === state.selected)) state.selected = sessions[0]?.id || '';
  fillOptions('launch-mission', missions.length ? missions.map(m => [m.id, m.definition.name]) : [['', '請先儲存任務']]);
  fillOptions('edit-mission', missions.length ? missions.map(m => [m.id, m.definition.name]) : [['', '尚無儲存任務']]);
  fillOptions('session-select', sessions.length ? sessions.map(s => [s.id, `${phases[s.state]} · ${s.mission.definition.name} · 房 ${s.roomIds.join('、')}`]) : [['', '目前沒有場次']], state.selected);
  const ownRooms = rooms.filter(r => ownsRoom(r.id));
  fillOptions('launch-room', ownRooms.map(r => [String(r.id), `房間 ${r.id}${r.sessionId ? '（使用中）' : '（空閒）'}`]));
  renderRooms();
  const selected = state.selected, previous = state.session;
  if (selected) {
    const [session, statistics] = await Promise.all([api('/sessions/' + selected), api('/sessions/' + selected + '/statistics')]);
    const events = await api(`/sessions/${selected}/events?after=${Math.max(0, session.sequence - 20)}&limit=20`);
    if (epoch !== state.epoch || selected !== state.selected) return;
    state.session = session;
    if (previous?.id !== session.id) { loadEnvironment(); loadEnemies(); }
    renderSession(statistics, events);
  } else { state.session = null; $('session-panel').hidden = true; }
  $('last-update').textContent = '更新於 ' + time(Date.now());
  applyPermissions();
}
function renderRooms() {
  $('rooms').replaceChildren(...state.rooms.map(room => {
    const card = element('article', undefined, 'room-card'), session = state.sessions.find(s => s.id === room.sessionId);
    card.append(element('p', `ROOM 0${room.id}`, 'eyebrow'), element('h3', `房間 ${room.id}`), element('div', `${room.playerCount} / ${room.capacity}`, 'occupancy'), element('p', session ? `${phases[session.state]} · ${session.mission.definition.name}` : room.sessionId ? '場次使用中' : '房間空閒', 'room-mission'));
    const button = element('button', room.sessionId ? '查看場次' : '選擇此房間', 'quiet small');
    button.type = 'button'; button.addEventListener('click', () => { if (room.sessionId) selectSession(room.sessionId); else { $('launch-room').value = String(room.id); $('launch-mode').value = 'Independent'; applyPermissions(); $('launch-mission').focus(); } });
    card.append(button); return card;
  }));
}
async function selectSession(id) {
  if (state.pending || state.busy) { notify('請先確認目前命令的結果。', true); return; }
  if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* Refresh below reports errors. */ } }
  state.selected = id; state.session = null;
  $('session-panel').hidden = true;
  try { await refresh(); } catch (error) { showRefreshError(error); }
}
function applyPermissions() {
  if (!state.actor) return;
  const session = state.session, ended = session?.state === 'Ended', locked = state.busy || !!state.pending;
  $('create-fields').disabled = locked || state.actor.role === 'GameServer';
  $('launch-room').disabled = $('launch-mode').value === 'Linked';
  $('create-session-form').querySelector('button').disabled = locked || !state.missions.length || ($('launch-mode').value === 'Linked' ? !master() || state.rooms.some(r => r.sessionId) : !!state.rooms.find(r => r.id === Number($('launch-room').value))?.sessionId);
  $('mission-fields').disabled = locked || !master();
  $('load-mission').disabled = locked || !state.missions.length; $('new-mission').disabled = locked || !master();
  for (const id of ['environment-fields', 'enemies-fields']) $(id).disabled = locked || !manages() || ended || !session;
  $('join-fields').disabled = locked || session?.state !== 'Preparing';
  $('ticket-fields').disabled = locked || ended || !session;
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
  document.querySelectorAll('[data-player-room]').forEach(button => { button.disabled = locked || ended || !ownsRoom(Number(button.dataset.playerRoom)); });
}
function row(cells) { const tr = element('tr'); for (const value of cells) { const td = element('td'); if (value instanceof Node) td.append(value); else td.textContent = value; tr.append(td); } return tr; }
function emptyTable(id, columns, message) { const tr = element('tr'), td = element('td', message, 'empty-cell'); td.colSpan = columns; tr.append(td); $(id).replaceChildren(tr); }
function renderSession(statistics, events) {
  const session = state.session;
  $('session-panel').hidden = false;
  $('session-name').textContent = session.mission.definition.name;
  $('session-meta').textContent = `${session.mode === 'Linked' ? '五房全連線' : '單房獨立'} / 房 ${session.roomIds.join('、')} / 序號 ${session.sequence}`;
  $('session-phase').textContent = phases[session.state]; $('session-phase').className = 'badge ' + session.state.toLowerCase();
  $('session-briefing').textContent = session.mission.definition.briefing;
  const env = session.environment, enemies = session.enemies;
  $('live-environment').textContent = `${env.mode} · ${weatherNames[env.weather]} · ${env.timeOfDay === 'Night' ? '夜晚' : '白天'} · ${env.lightning ? '閃電開啟' : '無閃電'}`;
  $('live-enemies').textContent = `${enemies.count} 名 · ${behaviorNames[enemies.behavior]} · ${enemies.autoAttack ? '自動攻擊' : '手動設定'}`;
  fillOptions('player-room', session.roomIds.filter(ownsRoom).map(id => [String(id), `房間 ${id}`]));
  $('player-count').textContent = `${session.players.length} / ${session.roomIds.length * 5} 人（名冊）`;
  $('roster').replaceChildren(...session.players.map(player => {
    const actions = element('div', undefined, 'button-row');
    for (const [label, action, cls] of [['下載連線檔', () => downloadTicket(player), 'secondary'], ['移除', () => removePlayer(player), 'danger']]) {
      const button = element('button', label, cls + ' small'); button.type = 'button'; button.dataset.playerRoom = player.roomId;
      button.addEventListener('click', () => run(action)); actions.append(button);
    }
    return row([player.name, `${player.roomId} / ${player.seat + 1}`, player.headset === 'Quest3' ? 'Quest 3' : 'VIVE XR', actions]);
  }));
  if (!session.players.length) emptyTable('roster', 4, '尚未加入玩家');
  $('statistics-origin').textContent = statistics.origin === 'Simulation' ? '模擬資料' : statistics.origin === 'GameServer' ? '遊戲伺服器回報' : '尚無戰鬥資料';
  $('statistics').replaceChildren(...statistics.players.map(player => row([player.name, player.ammoUsed, player.kills, player.damageTaken, player.hitsReceived, player.accuracyPercent + '%', player.health])));
  if (!statistics.players.length) emptyTable('statistics', 7, '加入玩家後顯示統計');
  const eventNames = { Created: '建立場次', PlayerJoined: '玩家加入', PlayerLeft: '玩家離開', ControlApplied: '套用控制命令', CombatRecorded: '戰鬥事件' };
  $('event-list').replaceChildren(...events.slice().reverse().map(event => {
    const item = element('li'); item.append(element('span', time(event.recordedAtUtc), 'event-time'), element('span', `#${event.sequence} ${eventNames[event.kind] || event.kind}`), element('span', event.actor?.id || '舊版紀錄', 'event-actor')); return item;
  }));
}
function environment(prefix) { return { mode: $(prefix + '-mode').value, weather: $(prefix + '-weather').value, timeOfDay: $(prefix + '-time').value, lightning: $(prefix + '-lightning').checked }; }
function enemies(prefix) { return { count: Number($(prefix + '-count').value), behavior: $(prefix + '-behavior').value, autoAttack: $(prefix + '-auto-attack').checked }; }
function setEnvironment(prefix, value) { $(prefix + '-mode').value = value.mode; $(prefix + '-weather').value = value.weather; $(prefix + '-time').value = value.timeOfDay; $(prefix + '-lightning').checked = value.lightning; }
function setEnemies(prefix, value) { $(prefix + '-count').value = value.count; $(prefix + '-behavior').value = value.behavior; $(prefix + '-auto-attack').checked = value.autoAttack; }
function loadEnvironment() { if (state.session) { setEnvironment('live', state.session.environment); state.environmentSequence = state.session.sequence; } }
function loadEnemies() { if (state.session) { setEnemies('live', state.session.enemies); state.enemiesSequence = state.session.sequence; } }
async function createSession() {
  if (state.pending) return;
  const mode = $('launch-mode').value;
  state.pending = { kind: 'create', path: '/sessions', method: 'POST', requestId: uuid(), body: { missionId: $('launch-mission').value, mode, roomIds: mode === 'Linked' ? [1, 2, 3, 4, 5] : [Number($('launch-room').value)] } };
  await sendPending();
}
async function command(action, extra = {}, expectedSequence = state.session.sequence) {
  if (state.pending) return;
  if (action === 'End' && !confirm('結束此場次並釋放房間？歷史與統計會保留。')) return;
  state.pending = { kind: 'command', path: '/sessions/' + state.session.id + '/commands', method: 'POST', body: { commandId: uuid(), action, expectedSequence, ...extra } };
  await sendPending();
}
async function sendPending() {
  const pending = state.pending;
  if (!pending) return;
  try {
    const response = await api(pending.path, pending.method, pending.body, pending.requestId);
    if (state.pending !== pending) return;
    state.pending = null;
    if (pending.kind === 'create') { $('include-ended').checked = response.state === 'Ended'; state.selected = response.id; state.session = null; }
    if (pending.kind === 'join') $('player-name').value = '';
    await refresh(); loadEnvironment(); loadEnemies();
    notify({ create: '場次建立結果已確認。請核對目前狀態，再加入玩家及開始任務。', join: '玩家加入操作已確認，請核對目前名冊；尚不代表頭盔在線。', leave: '玩家移出操作已確認，請核對目前名冊。', command: '控制命令已確認。' }[pending.kind]);
  } catch (error) {
    if (state.pending === pending && error.status >= 400 && error.status < 500) state.pending = null;
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
  if (!confirm(`將「${player.name}」移出名冊？現有頭盔連線尚不會自動斷開。`)) return;
  state.pending = { kind: 'leave', path: `/sessions/${state.selected}/players/${player.id}`, method: 'DELETE', requestId: uuid() };
  await sendPending();
}
function download(filename, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const anchor = element('a'); anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function downloadTicket(player) {
  const address = $('game-address').value.trim(), port = Number($('game-port').value);
  if (!address || /[\s/\\?#@]/.test(address) || !Number.isInteger(port) || port < 1024 || port > 65535) { notify('請先輸入遊戲伺服器地址及 1024–65535 的連線埠。', true); return; }
  const ticket = await api(`/sessions/${state.selected}/players/${player.id}/join-ticket`, 'POST');
  download(`quest-player-${player.id}.json`, { role: 'Client', address, port, joinTicket: ticket.ticket });
  notify(`玩家連線檔已產生，有效至 ${time(ticket.expiresAtUtc)}。請將各自檔案配置到對應頭盔。`);
}

function resetDraft() {
  $('mission-form').reset(); state.props = []; state.prop = -1; renderProps(); $('draft-status').textContent = '尚未儲存的草稿';
}
function loadDraft() {
  const mission = state.missions.find(m => m.id === $('edit-mission').value);
  if (!mission) return;
  const draft = mission.definition;
  $('draft-name').value = draft.name; $('draft-briefing').value = draft.briefing; $('draft-duration').value = draft.durationSeconds;
  setEnvironment('draft', draft.environment); setEnemies('draft', draft.enemies);
  state.props = structuredClone(draft.props); state.prop = state.props.length ? 0 : -1;
  renderProps(); $('draft-status').textContent = '已載入草稿，修改後另存新任務';
}
async function saveMission() {
  const mission = await api('/missions', 'POST', { name: $('draft-name').value.trim(), briefing: $('draft-briefing').value, durationSeconds: Number($('draft-duration').value), environment: environment('draft'), enemies: enemies('draft'), props: structuredClone(state.props) });
  await refresh(); $('launch-mission').value = mission.id; $('edit-mission').value = mission.id;
  $('draft-status').textContent = '已儲存於 ' + time(mission.createdAtUtc); notify('任務已儲存，可到「房間與場次」選取開局。');
}
function svgNode(tag, attributes) { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value); return node; }
function renderProps(updateInspector = true) {
  const layer = $('prop-layer');
  layer.replaceChildren(...state.props.map((prop, index) => {
    const group = svgNode('g', { transform: `translate(${prop.position.x} ${-prop.position.z}) rotate(${-prop.yawDegrees})`, 'data-index': index, 'data-selected': index === state.prop, role: 'button', tabindex: '0', 'aria-label': `物件 ${index + 1} ${prop.assetId}` });
    const shape = prop.assetId === 'barrel' ? svgNode('circle', { r: '.4', fill: '#658d87' }) : svgNode('rect', { x: '-.8', y: '-.3', width: '1.6', height: '.6', rx: '.1', fill: '#a69b63' });
    const label = svgNode('text', { y: '.12' }); label.textContent = index + 1; group.append(shape, label); return group;
  }));
  if (!updateInspector) return;
  fillOptions('prop-select', state.props.length ? state.props.map((p, i) => [String(i), `${i + 1} · ${p.assetId}`]) : [['', '尚無物件']], String(state.prop));
  $('prop-inspector').hidden = state.prop < 0;
  const prop = state.props[state.prop];
  if (prop) { $('prop-asset').value = prop.assetId; for (const axis of ['x', 'y', 'z']) $('prop-' + axis).value = prop.position[axis]; $('prop-yaw').value = prop.yawDegrees; }
}
function editable() { return master() && !state.busy && !state.pending; }
function dirtyDraft() { $('draft-status').textContent = '尚未儲存的草稿'; }
function addProp(assetId) {
  if (!editable()) return;
  if (state.props.length >= 500) { notify('最多可放置 500 個物件。', true); return; }
  state.props.push({ assetId, position: { x: 0, y: 0, z: 0 }, yawDegrees: 0 }); state.prop = state.props.length - 1; renderProps(); dirtyDraft();
}
function moveProp(x, z) { const prop = state.props[state.prop]; if (prop && editable()) { prop.position.x = Math.round(Math.max(-10, Math.min(10, x)) * 2) / 2; prop.position.z = Math.round(Math.max(-10, Math.min(10, z)) * 2) / 2; renderProps(false); $('prop-x').value = prop.position.x; $('prop-z').value = prop.position.z; dirtyDraft(); } }
let dragging = false, offset = { x: 0, z: 0 };
function mapPoint(event) { const point = $('layout-map').createSVGPoint(); point.x = event.clientX; point.y = event.clientY; const local = point.matrixTransform($('layout-map').getScreenCTM().inverse()); return { x: local.x, z: -local.y }; }
$('layout-map').addEventListener('pointerdown', event => {
  const target = event.target.closest('[data-index]');
  if (!target || !editable()) return;
  event.preventDefault(); state.prop = Number(target.dataset.index); const point = mapPoint(event), prop = state.props[state.prop];
  offset = { x: prop.position.x - point.x, z: prop.position.z - point.z }; dragging = true;
  $('layout-map').setPointerCapture(event.pointerId); renderProps(); $('layout-map').focus();
});
$('layout-map').addEventListener('pointermove', event => { if (dragging) { const point = mapPoint(event); moveProp(point.x + offset.x, point.z + offset.z); } });
for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) $('layout-map').addEventListener(type, () => { dragging = false; });
$('layout-map').addEventListener('keydown', event => {
  const target = event.target.closest('[data-index]');
  if ((event.key === 'Enter' || event.key === ' ') && target) { event.preventDefault(); state.prop = Number(target.dataset.index); renderProps(); $('layout-map').focus(); return; }
  const prop = state.props[state.prop];
  if (!prop || !editable()) return;
  const directions = { ArrowLeft: [-.5, 0], ArrowRight: [.5, 0], ArrowUp: [0, .5], ArrowDown: [0, -.5] }, delta = directions[event.key];
  if (delta) { event.preventDefault(); moveProp(prop.position.x + delta[0], prop.position.z + delta[1]); }
});
$('prop-select').addEventListener('change', () => { state.prop = Number($('prop-select').value); renderProps(); });
for (const id of ['prop-asset', 'prop-x', 'prop-y', 'prop-z', 'prop-yaw']) $(id).addEventListener('change', () => {
  const prop = state.props[state.prop]; if (!prop || !editable()) return;
  if (id === 'prop-asset') { if (!$(id).value.trim()) { renderProps(); return; } prop.assetId = $(id).value.trim(); }
  else if ($(id).value !== '' && Number.isFinite(Number($(id).value))) { if (id === 'prop-yaw') prop.yawDegrees = Number($(id).value); else prop.position[id.slice(-1)] = Number($(id).value); }
  renderProps(); dirtyDraft();
});

function tab(name) {
  for (const candidate of ['operations', 'missions', 'replay']) { const active = candidate === name; $(candidate + '-view').hidden = !active; $('tab-' + candidate).classList.toggle('active', active); $('tab-' + candidate).setAttribute('aria-pressed', String(active)); }
  replay.active(name === 'replay');
}
function submit(id, action) { $(id).addEventListener('submit', event => { event.preventDefault(); run(action); }); }
$('login-form').addEventListener('submit', login);
$('logout').addEventListener('click', logout);
$('refresh').addEventListener('click', () => refresh().then(() => notify('已更新。')).catch(showRefreshError));
$('include-ended').addEventListener('change', () => refresh().catch(showRefreshError));
$('session-select').addEventListener('change', () => selectSession($('session-select').value));
$('launch-mode').addEventListener('change', applyPermissions);
$('launch-room').addEventListener('change', applyPermissions);
$('reload-environment').addEventListener('click', loadEnvironment);
$('reload-enemies').addEventListener('click', loadEnemies);
$('retry-command').addEventListener('click', () => run(sendPending));
document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => run(() => command(button.dataset.command))));
submit('create-session-form', createSession);
submit('join-form', joinPlayer);
submit('environment-form', () => command('SetEnvironment', { environment: environment('live') }, state.environmentSequence));
submit('enemies-form', () => command('SetEnemies', { enemies: enemies('live') }, state.enemiesSequence));
submit('mission-form', saveMission);
$('load-mission').addEventListener('click', () => { loadDraft(); });
$('new-mission').addEventListener('click', () => { if (confirm('清除目前未儲存的草稿並建立新任務？')) resetDraft(); });
$('add-sandbag').addEventListener('click', () => addProp('sandbag'));
$('add-barrel').addEventListener('click', () => addProp('barrel'));
$('rotate-prop').addEventListener('click', () => { if (editable() && state.props[state.prop]) { state.props[state.prop].yawDegrees = (state.props[state.prop].yawDegrees + 15) % 360; renderProps(); dirtyDraft(); } });
$('remove-prop').addEventListener('click', () => { if (editable() && state.prop >= 0) { state.props.splice(state.prop, 1); state.prop = Math.min(state.prop, state.props.length - 1); renderProps(); dirtyDraft(); } });
$('mission-form').addEventListener('input', dirtyDraft);
$('mission-form').addEventListener('change', dirtyDraft);
for (const name of ['operations', 'missions', 'replay']) $('tab-' + name).addEventListener('click', () => tab(name));
window.addEventListener('beforeunload', event => { if (state.pending) { event.preventDefault(); event.returnValue = ''; } });
