import { mountWorld } from './world-ui.js';
import { mountReplay } from './replay-ui.js';
import { drawLayoutProps, mountLayout, mountLayoutProposal, savedRoomLayoutMap } from './layout-ui.js';
import { mountIndependentPlan } from './independent-plan-ui.js';
import { mountAlignment } from './alignment-ui.js';
import { mountAlignmentPins } from './alignment-pins-ui.js';
import { mountSeatDeployment } from './seat-deployment-ui.js';
import { mountMrVenueBundle } from './mr-venue-bundle-ui.js';
import { mountVrVenueTickets } from './vr-venue-tickets-ui.js';
import { mountVenueServerPlan } from './venue-server-plan-ui.js';
import { mountVenueLaunchReview } from './venue-launch-review-ui.js';
import { mountVenueHardwareReview } from './venue-hardware-review-ui.js';
import { mountVenueRoster } from './venue-roster-ui.js';
import { mountVenueSettingScope } from './venue-setting-scope-ui.js';
import { mountOperatorNetwork } from './operator-network-ui.js';
import { mountReport, mountVenueReport, venueScoreFields } from './report-ui.js';
import { encodeDepartedPlayersCsv, matchesDebriefCsv } from './report-csv.js';
import { mountVenueHistory } from './venue-history-ui.js';
import { mountVenueDebriefSeats } from './venue-debrief-ui.js';
import { beginSeatLabels, encodeVenueBeginCsv, mountReadiness, mountRoomReadiness, usesTrackedVrStart,
  venueBeginRejection, venueBeginSeatState } from './readiness-ui.js';
import { mountConnections, validDestination } from './connection-ui.js';
import { mountClosure } from './closure-ui.js';
import { placementHistory } from './placement-history.js';
import { mountPlacementMove } from './placement-move.js';
import { verifyBlobSha256 } from './file-integrity.js';
import { matchesIssuedPlayerTicket } from './player-ticket.js';
const replay = mountReplay();
const $ = id => document.getElementById(id);
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const behaviorNames = { Hold: '守備', Patrol: '巡邏', Advance: '推進' };
const archiveNames = { NoSource: '沒有遊戲來源', Missing: '尚無錄製紀錄', Waiting: '等待封存', SourceMismatch: '來源尚未對上', Sealed: '已封存' };
const archiveId = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const venueMissionRooms = [1, 2, 3, 4, 5];
const venueMissionFileLimit = 4096;
const missionTemplateFormat = 'vr-command-mission-template';
const missionTemplateFileLimit = 512 * 1024;
let venueMissionReview = null;
let venueMissionMaps = null;
let savedVenuePlans = null;
const state = { key: '', actor: null, epoch: 0, busy: false, refreshPromise: null, rooms: [], venue: null, venuePhaseBlob: null, missions: [], catalog: [], launchPinned: null, history: null, draftBase: null, draftChanged: false, draftSavedAt: '', sessions: [], session: null, selected: null, pending: null, props: [], prop: -1, settingRevisions: null };
const liveSettingDrafts = { environment: null, enemies: null };
let comparedVersion = null;
let checkedTemplate = null, templateEpoch = 0, loadedText = null;
let draftLoad = null;
const objectHistory = placementHistory();
const world = mountWorld(() => state.key, logout, venueEnemyText, master, download);
const report = mountReport(() => state, logout, () => { renderStatistics(); closure.update(); });
const venueReport = mountVenueReport(() => state, logout, download);
const venueHistory = mountVenueHistory(api, selectVenueClosure);
const venueDebrief = mountVenueDebriefSeats(() => state, logout, download, openClosurePlayerReplay);
const readiness = mountReadiness(() => state, logout, () => Number($('roster-room').value) || null);
const roomReadiness = mountRoomReadiness(() => state, logout, applyVenuePermissions, venueClimateText, venueEnemyText, target => {
  if (!state.busy && !state.pending) tab('world', target);
});
const connections = mountConnections(() => state, logout, updateRoomTicketButtons);
const closure = mountClosure(() => state, logout, openSessionReview, report);
const alignment = mountAlignment(api, download);
const seatDeployments = ['VR', 'MR'].map(mode => mountSeatDeployment(() => state, api, mode));
const mrVenue = mountMrVenueBundle(() => state, api, download, roomReadiness.ticketDestination);
const vrVenue = mountVrVenueTickets(() => state, api, download, roomReadiness.ticketSourceLive);
const venueServerPlan = mountVenueServerPlan(() => state, api, download);
const venueLaunchReview = mountVenueLaunchReview(() => state, api, selectSession, focusRoster, roomReadiness.reviewedBegin,
  target => tab('world', target), openReviewedVenueClosure);
const venueHardwareReview = mountVenueHardwareReview(() => state, master, api, download);
const venueRoster = mountVenueRoster({ getState: () => state, canRegister: master, uuid, download, register: seats => run(async () => {
  state.pending = { kind: 'venue-roster-join', path: '/venue/roster-admissions', method: 'POST', body: { seats } };
  await sendPending();
}) });
const venueSettingScopes = {
  SetEnvironment: mountVenueSettingScope('environment', '環境', applyVenuePermissions),
  SetEnemies: mountVenueSettingScope('enemies', '敵軍策略', applyVenuePermissions)
};
const operatorNetwork = mountOperatorNetwork(() => state, api, download, uuid);
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
  selection: () => {
    const { revision } = launchPlan();
    const definition = revision?.mission.definition;
    return { id: revision?.mission.id ?? '', mode: launchLayoutMode(), experienceMode: definition?.environment.mode, props: definition?.props ?? [] };
  }, changed: applyPermissions,
  selectProp: index => { if (!state.props[index]) return; finishPropGesture(); state.prop = index; renderProps(); $('prop-select').focus(); } });
const roomPlan = mountIndependentPlan({
  available: () => master() && $('launch-mode').value === 'IndependentSet',
  catalog: () => state.catalog, pinned: () => state.launchPinned, common: commonLaunchRevision,
  climateText: venueClimateText, enemyText: missionEnemyText,
  inspect: revision => placement.inspectSaved({ id: revision.mission.id, mode: 'Independent', experienceMode: revision.mission.definition.environment.mode }),
  invalidate: id => placement.invalidateSaved(id, 'Independent'),
  changed: () => { placement.scheduleLaunch(); applyPermissions(); }
});
let timer;
let selectionEpoch = 0, venueClosureEpoch = 0, operationsViewEpoch = 0;
let venueSettingReview = 0;
let archivedPlan = null;
let confirmedVenueBegin = null, confirmedVenueEnd = null;
let departureReview = null;
let roomEnemyDraft = null, roomEnemyPolicySequences = null;

function notify(message, error = false, reviews = []) {
  const notice = $('notice');
  notice.textContent = message;
  notice.classList.toggle('error', error);
  notice.hidden = !message;
  if (!reviews.length || !master()) return;
  const epoch = state.epoch;
  const actions = element('div', '', 'button-row');
  for (const target of reviews) {
    const button = element('button', `檢視房間 ${target.roomId} 開場受阻快照`, 'quiet small');
    button.type = 'button';
    button.addEventListener('click', () => {
      if (state.epoch === epoch && master() && !state.busy && !state.pending && notice.contains(button)) tab('world', target);
    });
    actions.append(button);
  }
  notice.append(actions);
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

async function readTicketArchive(response, request, signal, room) {
  const limit = 256 * 1024;
  try {
    const digest = /^sha-256=:([A-Za-z0-9+/]{43}=):$/.exec(response.headers.get('Repr-Digest') ?? '')?.[1];
    if (!digest || response.headers.get('X-VrCommand-Archive-Request') !== request
      || response.headers.get('Content-Type')?.split(';', 1)[0].trim() !== 'application/zip'
      || Number(response.headers.get('Content-Length')) > limit) throw new Error();
    const file = await response.blob();
    if (file.size < 1 || file.size > limit) throw new Error();
    await verifyBlobSha256(file, digest, signal);
    return file;
  } catch {
    if (room) throw Object.assign(new Error('無法核對本房連線檔的原始內容，請重新配票。'), { code: 'room-archive-unverified' });
    throw Object.assign(new Error('無法核對五房連線檔的原始內容，請重新配票。'), { code: 'venue-archive-unverified' });
  }
}

async function api(path, method = 'GET', body, requestId, admissionId, responseType = 'json', requestSignal) {
  const controller = new AbortController(), epoch = state.epoch;
  const signal = requestSignal ? AbortSignal.any([requestSignal, controller.signal]) : controller.signal;
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const binary = body instanceof Blob;
    const roomArchive = responseType === 'room-ticket-archive';
    const archiveRequest = roomArchive || responseType === 'venue-ticket-archive' ? uuid() : null;
    const response = await fetch('/api' + path, { method, headers: { Authorization: 'Bearer ' + state.key, 'Content-Type': binary ? 'application/octet-stream' : 'application/json', ...(requestId ? { 'Idempotency-Key': requestId } : {}), ...(admissionId ? { 'If-Match-Admission': admissionId } : {}), ...(archiveRequest ? { 'X-VrCommand-Archive-Request': archiveRequest } : {}) }, body: binary || body === undefined ? body : JSON.stringify(body), signal, cache: 'no-store' });
    if (epoch !== state.epoch) throw new Error('登入狀態已變更，已忽略舊回應。');
    const content = archiveRequest && response.ok ? await readTicketArchive(response, archiveRequest, signal, roomArchive)
      : responseType === 'blob' && response.ok ? await response.blob() : await response.text();
    requestSignal?.throwIfAborted();
    if (epoch !== state.epoch) throw new Error('登入狀態已變更，已忽略舊回應。');
    if (!response.ok) {
      let message = '操作未完成，請重新整理後確認。', layout, code, maxCount, roomIds, roomId, seat, workstationIssues, blockedRooms, reviews;
      try { const data = JSON.parse(content); message = data.error || message; layout = data.layout; code = data.code; maxCount = data.maxCount; roomIds = data.roomIds; roomId = data.roomId; seat = data.seat;
        if (code === 'operator-network-witnesses-rejected') workstationIssues = data.issues;
        if (code === 'venue-begin-not-ready') blockedRooms = data.blockedRooms;
      } catch { /* Non-domain errors have no stable JSON contract. */ }
      if (response.status === 401) { logout(); message = '憑證無效或已更換，請重新登入。'; }
      if (response.status === 403) message = '目前身分沒有此操作權限。';
      if (response.status === 409) {
        if (code === 'mr-readiness-required') message = 'MR 場次尚未就緒。請查看「MR 開場檢查」，並確認等候中的 Quest 3 玩家已完成場地對位。';
        else if (code === 'venue-roster-seat-conflict') {
          const scope = venueMissionRooms.includes(roomId) && Number.isInteger(seat) && seat >= 0 && seat < 5
            ? `房間 ${roomId} 的第 ${seat + 1} 席` : '原選定的席位';
          message = `${scope}已變更，本批皆未登記。請重新整理並核對。`;
        }
        else if (code === 'mr-resume-readiness-required') message = 'MR 場次尚未符合繼續條件。請查看「MR 繼續檢查」。';
        else if (code === 'mr-tracking-pause-no-witness') message = '目前未確認本房仍有追蹤中斷。請查看最新追蹤狀態。';
        else if (code === 'vr-participation-pause-no-witness') message = '目前未確認本房仍有姿態中斷。請查看最新參戰狀態。';
        else if (code === 'vr-participation-resume-not-ready') message = '暫停中的席位尚未確認恢復。請查看房卡等待的席位。';
        else if (code === 'tracked-vr-start-not-ready') message = 'VR 追蹤開場尚未就緒。請確認名冊中的每一席都有最新的追蹤姿態。';
        else if (code === 'mr-alignment-required') message = '請由主控鎖定 MR 校正檔後再配票。';
        else if (code === 'ticket-source-unavailable') message = '原遊戲來源暫未更新，配票已暫停。請查看房卡的連線狀態。';
        else if (code === 'ticket-endpoint-mismatch') message = '整房配票須使用原公告端點。請按「套用場次連線設定」後再下載。';
        else if (code === 'independent-rooms-occupied' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 使用中，五場都未建立。請確認房間狀態後再試。`;
        else if (code === 'venue-phase-changed') {
          const scope = Array.isArray(roomIds) && roomIds.length > 0 && roomIds.length <= 5
            && roomIds.every((id, index) => Number.isInteger(id) && id >= 1 && id <= 5 && (!index || id > roomIds[index - 1]))
            ? `房間 ${roomIds.join('、')} 的場次狀態已變更` : '全館場次狀態已變更';
          message = `${scope}，本批命令未套用。請重新整理後確認房間。`;
        }
        else if (code === 'room-enemy-policy-changed') message = '本房敵軍策略已變更。草稿仍保留，請載入目前策略再編輯。';
        else if (code === 'setting-revision-changed') message = '場次設定已變更。草稿仍保留，請載入目前設定再編輯。';
        else if (code === 'venue-pause-not-observed' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 尚未回傳有效的暫停快照，本批場次維持暫停。`;
        else if (code === 'venue-resume-not-ready' && Array.isArray(roomIds)) message = `房間 ${roomIds.join('、')} 的 MR 追蹤尚未就緒，本批場次維持暫停。`;
        else if (code === 'venue-begin-not-ready') {
          const fences = path === '/venue/phase' && method === 'POST' && body?.action === 'Begin' ? body.targets : [];
          ({ message, reviews } = venueBeginRejection(roomIds, blockedRooms, fences, state.rooms));
        }
        else message = path.startsWith('/missions') ? '任務版本已變更或原請求內容不一致；草稿仍保留，可載入最新版或另存新任務。' : '場次狀態或名額已變更，請重新整理並確認後再操作。';
      }
      if (layout) message = Number.isInteger(roomId) ? `房間 ${roomId} 的場地未通過檢查，五場都未建立。請修正並保存新版本。`
        : '場地配置未通過檢查，請修正並保存新版本後再開場。';
      if (code === 'enemy-capacity-exceeded' && Number.isInteger(maxCount)) message = `此場地最多可設定 ${maxCount} 名敵軍。請調低目標數量後再套用。`;
      const error = new Error(message); error.status = response.status; error.layout = layout; error.code = code; error.roomId = roomId;
      error.workstationIssues = workstationIssues; error.beginReviews = reviews; throw error;
    }
    if (responseType === 'blob' || archiveRequest) return content;
    const result = content ? JSON.parse(content) : null;
    if (responseType === 'mission-save' && (!archiveId.test(result?.id) || response.headers.get('Location') !== '/api/missions/' + result.id))
      throw new MissionVersionMismatch();
    return result;
  } finally { clearTimeout(timeout); }
}
async function run(action, independentRead = false, signal) {
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
    if (signal?.aborted || epoch !== state.epoch || !state.actor) return;
    await action();
    if (!signal?.aborted && refreshFailed && epoch === state.epoch && state.actor) notify('已讀取任務；背景列表更新失敗，請稍後重新整理。', true);
  }
  catch (error) {
    if (signal?.aborted) return;
    const message = error.status || error instanceof MissionVersionMismatch || error.code === 'room-archive-unverified'
      ? error.message : '連線或操作結果未確認，請重新整理查看。';
    notify(message + (state.pending && !error.status ? ' 可使用「重試確認結果」確認原命令。' : ''), true, error.beginReviews);
  }
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
  draftLoad?.abort();
  roomEnemyDraft = roomEnemyPolicySequences = null;
  state.settingRevisions = liveSettingDrafts.environment = liveSettingDrafts.enemies = null;
  selectionEpoch++;
  venueClosureEpoch++;
  report.reset(); state.statistics = null;
  closure.active(false); closure.reset();
  alignment.reset();
  clearMissionComparison();
  clearMissionTemplate(); loadedText = null;
  alignmentPins.active(false);
  seatDeployments.forEach(panel => panel.active(false));
  mrVenue.active(false);
  vrVenue.active(false);
  venueServerPlan.active(false);
  venueLaunchReview.active(false);
  venueHardwareReview.active(false);
  operatorNetwork.active(false);
  replay.active(false); replay.reset(); world.active(false); world.reset(); readiness.active(false); readiness.reset(); roomReadiness.active(false); connections.active(false); connections.reset();
  state.epoch++; state.key = ''; state.actor = null; state.selected = null; state.session = null; state.pending = null;
  setVenuePhase(null);
  state.rooms = []; state.missions = []; state.catalog = []; state.launchPinned = null; state.history = null; state.draftBase = null; state.draftChanged = false; state.draftSavedAt = ''; state.sessions = []; state.refreshPromise = null;
  $('mission-search').value = '';
  $('mission-search-status').hidden = true;
  $('mission-search-status').textContent = '';
  $('venue-full-tracking').checked = false;
  $('venue-full-participation').checked = false;
  $('venue-begin-size').value = '5';
  $('roster-room').value = '';
  delete $('roster-room').dataset.preferred;
  renderVenueBegin([], false);
  confirmedVenueBegin = null;
  renderConfirmedVenueBegin(true);
  confirmedVenueEnd = null;
  venueHistory.reset(); renderVenueClosure(null);
  state.props = []; state.prop = -1; clearPropHistory(); propMove.reset();
  roomPlan.reset(); placement.reset();
  clearVenueMissionFile();
  venueRoster.reset();
  savedVenuePlans = null;
  $('saved-venue-mission-plans').open = false;
  $('venue-plan-name').value = $('venue-plan-status').textContent = '';
  $('saved-venue-plan').replaceChildren();
  renderIndependentReceipt();
  clearInterval(timer);
  $('workspace').hidden = true; $('login-panel').hidden = false; $('logout').hidden = true;
  $('identity').textContent = '尚未登入'; $('login-key').value = '';
  $('rooms').replaceChildren(); $('roster').replaceChildren(); $('statistics').replaceChildren(); $('event-list').replaceChildren();
  $('statistics-scope').hidden = true; $('statistics-scope-status').textContent = '';
  $('ticket-room').replaceChildren(); delete $('ticket-room').dataset.session;
  $('venue-environment-form').reset();
  Object.values(venueSettingScopes).forEach(scope => scope.reset());
  $('venue-enemies-form').reset();
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
function setVenuePhase(snapshot) {
  state.venue = snapshot?.plan ?? null;
  state.venuePhaseBlob = snapshot?.blob ?? null;
}
function refresh() {
  if (!state.actor || state.pending) return Promise.resolve();
  if (state.refreshPromise) return state.refreshPromise;
  const epoch = state.epoch;
  const pending = refreshData(epoch).catch(error => {
    if (epoch === state.epoch) { closure.invalidate(); setVenuePhase(null); applyVenuePermissions(); renderVenueClosure(null); }
    throw error;
  }).finally(() => { if (state.refreshPromise === pending) state.refreshPromise = null; });
  state.refreshPromise = pending;
  return pending;
}
async function refreshData(epoch) {
  const selection = selectionEpoch, includeEnded = $('include-ended').checked;
  const closureSelection = venueClosureEpoch, batchId = venueHistory.selected();
  const current = () => epoch === state.epoch && selection === selectionEpoch && includeEnded === $('include-ended').checked;
  const venueRead = master() ? api('/venue/phase', 'GET', undefined, undefined, undefined, 'blob')
    .then(async blob => ({ blob, plan: JSON.parse(await blob.text()) }))
    .catch(error => { if (error.status === 401) throw error; return null; }) : null;
  const venueClosureRead = master() ? api((batchId ? '/venue/closure/' + batchId : '/venue/closure') + '?includeScores=true&includeDebriefReceipts=true')
    .catch(error => { if (error.status === 401) throw error; return null; }) : null;
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
  setVenuePhase(venue);
  state.rooms = rooms; state.catalog = heads; state.missions = heads.map(row => row.mission); state.sessions = sessions;
  if (closureSelection === venueClosureEpoch)
    renderVenueClosure(batchId && venueClosure?.batch?.requestId !== batchId ? null : venueClosure);
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
  venueHardwareReview.update();
  const selected = state.selected, previous = state.session;
  if (selected) {
    const { session, statistics, recentEvents, roomEnemyPolicySequences: policySequences, settingRevisions } = await api('/sessions/' + selected + '/overview');
    if (!current() || selected !== state.selected) return;
    state.session = session;
    roomEnemyPolicySequences = policySequences;
    state.settingRevisions = settingRevisions;
    if (previous?.id !== session.id) { loadLiveSetting('environment'); loadLiveSetting('enemies'); loadClock(); }
    renderSession(statistics, recentEvents);
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
      const endpoint = element('p', '連線端點未確認', 'hint');
      endpoint.dataset.roomEndpoint = room.id;
      const clock = element('p', '活動時間未確認', 'hint room-clock');
      clock.dataset.roomClock = room.id;
      const phase = element('p', '', 'hint room-venue-phase');
      phase.dataset.roomVenuePhase = room.id;
      phase.hidden = true;
      const mrPause = element('p', '', 'hint');
      mrPause.dataset.roomMrPause = room.id;
      mrPause.hidden = true;
      const vrPause = element('p', '', 'hint');
      vrPause.dataset.roomVrPause = room.id;
      vrPause.hidden = true;
      const environment = element('p', '', 'hint');
      environment.dataset.roomEnvironment = room.id;
      environment.hidden = true;
      const enemies = element('p', '', 'hint');
      enemies.dataset.roomEnemies = room.id;
      enemies.hidden = true;
      card.append(status, endpoint, clock, phase, mrPause, vrPause, environment, enemies);
    }
    const button = element('button', room.sessionId ? '查看場次' : '選擇此房間', 'quiet small');
    button.type = 'button'; button.disabled = state.busy || !!state.pending;
    button.addEventListener('click', () => { if (room.sessionId) selectSession(room.sessionId); else { $('launch-room').value = String(room.id); $('launch-mode').value = 'Independent'; placement.scheduleLaunch(); applyPermissions(); $('launch-mission').focus(); } });
    const actions = element('div', undefined, 'button-row');
    actions.append(button);
    if (room.sessionId) {
      const watch = element('button', '即時觀戰', 'quiet small');
      watch.type = 'button'; watch.disabled = button.disabled; watch.dataset.watchRoom = room.id;
      watch.addEventListener('click', () => {
        if (state.busy || state.pending || !state.rooms.some(row => row.id === room.id && row.sessionId === room.sessionId)) return;
        tab('world', { mode: 'live', sessionId: room.sessionId, roomId: room.id });
      });
      actions.append(watch);
      if (session?.mode === 'Linked' && state.actor?.role === 'RoomController' && state.actor.roomId === room.id) {
        const ownWatch = element('button', '僅接收本房資料', 'quiet small');
        ownWatch.type = 'button'; ownWatch.disabled = button.disabled; ownWatch.dataset.watchRoomOnly = room.id;
        ownWatch.addEventListener('click', () => {
          if (state.busy || state.pending || !state.rooms.some(row => row.id === room.id && row.sessionId === room.sessionId)) return;
          tab('world', { mode: 'live', sessionId: room.sessionId, roomId: room.id, observerRoomId: room.id });
        });
        actions.append(ownWatch);
      }
      const poseFrame = element('button', '檢視姿態中斷快照', 'quiet small');
      poseFrame.type = 'button'; poseFrame.hidden = true; poseFrame.disabled = true;
      poseFrame.dataset.roomPoseFrame = room.id;
      poseFrame.addEventListener('click', () => {
        if (state.busy || state.pending) return;
        const target = roomReadiness.poseFrame(room.id);
        if (target?.sessionId === room.sessionId) tab('world', target);
      });
      actions.append(poseFrame);
      const vr = session?.environment?.mode === 'VR';
      const pause = element('button', session?.mode === 'Linked' ? '暫停五房合併場次' : vr ? '暫停本房檢查席位' : '暫停本房重新對位', 'quiet small');
      pause.type = 'button'; pause.hidden = true; pause.disabled = true;
      pause.dataset[vr ? 'roomVrParticipationPause' : 'roomMrTrackingPause'] = room.id;
      pause.addEventListener('click', () => pauseParticipation(room.id, room.sessionId, vr ? 'VR' : 'MR'));
      actions.append(pause);
      if (vr) {
        const resume = element('button', session.mode === 'Linked' ? '確認恢復後繼續五房' : '確認恢復後繼續本房', 'quiet small');
        resume.type = 'button'; resume.hidden = true; resume.disabled = true;
        resume.dataset.roomVrResume = room.id;
        resume.addEventListener('click', () => resumeVrParticipation(room.id, room.sessionId));
        actions.append(resume);
      }
      for (const [kind, label] of [['environment', '檢視環境快照'], ['enemies', '檢視敵軍快照']]) {
        const snapshot = element('button', label, 'quiet small');
        snapshot.type = 'button'; snapshot.disabled = button.disabled; snapshot.hidden = true;
        snapshot.setAttribute(`data-room-${kind}-frame`, room.id);
        snapshot.addEventListener('click', () => {
          if (state.busy || state.pending) return;
          const target = roomReadiness.settingFrame(room.id, kind);
          if (target?.sessionId === room.sessionId) tab('world', target);
        });
        actions.append(snapshot);
      }
    }
    card.append(actions); return card;
  }));
  roomReadiness.update();
}
function resetSelection(id, rosterRoom = '') {
  roomEnemyDraft = roomEnemyPolicySequences = null;
  state.settingRevisions = liveSettingDrafts.environment = liveSettingDrafts.enemies = null;
  report.reset(); readiness.reset(); connections.reset(); state.statistics = null; state.selected = id; state.session = null;
  closure.reset();
  alignmentPins.reset();
  seatDeployments.forEach(panel => panel.reset());
  $('statistics-scope').hidden = true; $('statistics-scope-status').textContent = '';
  $('session-panel').hidden = true;
  $('roster-room').value = '';
  $('roster-room').dataset.preferred = rosterRoom;
}
async function selectSession(id, rosterRoom = '') {
  if (state.pending || state.busy) { notify('請先確認目前命令的結果。', true); return; }
  const selection = ++selectionEpoch, epoch = state.epoch;
  resetSelection(id, rosterRoom);
  if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* Refresh below reports errors. */ } }
  if (selection !== selectionEpoch || epoch !== state.epoch) return;
  try { await refresh(); } catch (error) { showRefreshError(error); }
}
function focusRoster(sessionId, roomId, seat = null) {
  if ($('operations-view').hidden || state.session?.id !== sessionId || $('roster-room').value !== String(roomId)) return false;
  const target = seat === null ? $('roster-title')
    : $('roster').querySelector(`[data-roster-room="${roomId}"][data-roster-seat="${seat}"]:not([hidden])`);
  if (!target) return false;
  target.scrollIntoView({ block: seat === null ? 'start' : 'center' });
  target.focus({ preventScroll: true });
  return true;
}
function commonLaunchRevision() {
  const missionId = $('launch-mission').value;
  return state.catalog.find(row => row.mission.id === missionId)
    ?? (state.launchPinned?.mission.id === missionId ? state.launchPinned : null);
}
function configuredVenueRevisions(mode) {
  const common = commonLaunchRevision();
  if (mode === 'Independent') {
    const room = Number($('launch-room').value);
    return venueMissionRooms.map(roomId => roomId === room ? common : null);
  }
  return roomPlan.enabled() ? roomPlan.revisions() : venueMissionRooms.map(() => common);
}
function venueMissionSelection() {
  const mode = $('launch-mode').value;
  if (mode !== 'Linked' && mode !== 'IndependentSet') return null;
  const revisions = configuredVenueRevisions(mode);
  if (revisions.some(revision => !revision)) return null;
  return { schemaVersion: 1, mode, rooms: venueMissionRooms.map((roomId, index) => ({
    roomId, missionId: revisions[index].mission.id
  })) };
}
function parseVenueMissionFile(text) {
  const plan = JSON.parse(text);
  const exactKeys = (object, keys) => object && Object.keys(object).length === keys.length
    && keys.every(key => Object.hasOwn(object, key));
  if (!exactKeys(plan, ['schemaVersion', 'mode', 'rooms']) || plan.schemaVersion !== 1
    || !['Linked', 'IndependentSet'].includes(plan.mode) || !Array.isArray(plan.rooms)
    || plan.rooms.length !== venueMissionRooms.length) throw new Error();
  const rooms = [...plan.rooms].sort((a, b) => a?.roomId - b?.roomId);
  if (!rooms.every((row, index) => exactKeys(row, ['roomId', 'missionId']) && row.roomId === venueMissionRooms[index]
    && typeof row.missionId === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(row.missionId))) throw new Error();
  const ids = rooms.map(room => room.missionId.toLowerCase());
  if (plan.mode === 'Linked' && new Set(ids).size !== 1) throw new Error();
  return { mode: plan.mode, ids };
}
function validSavedVenuePlan(row) {
  const plan = row?.plan;
  return typeof row?.id === 'string' && archiveId.test(row.id) && typeof row.createdAtUtc === 'string'
    && Number.isFinite(Date.parse(row.createdAtUtc)) && typeof plan?.name === 'string' && !!plan.name.trim()
    && ['Linked', 'IndependentSet'].includes(plan.mode) && Array.isArray(plan.missionIds)
    && plan.missionIds.length === venueMissionRooms.length && plan.missionIds.every(id => typeof id === 'string' && archiveId.test(id))
    && (plan.mode !== 'Linked' || new Set(plan.missionIds).size === 1);
}
function matchesVenuePlan(actual, expected) {
  return actual.name === expected.name && actual.mode === expected.mode
    && actual.missionIds.every((id, index) => id === expected.missionIds[index]);
}
function renderSavedVenuePlans(selectedId = $('saved-venue-plan').value) {
  const select = $('saved-venue-plan');
  select.replaceChildren(new Option('選擇已保存的配置', ''), ...(savedVenuePlans ?? []).map(({ id, createdAtUtc, plan }) => {
    const mode = plan.mode === 'Linked' ? '五房全連線' : '五房各自獨立';
    return new Option(`${plan.name} · ${mode} · ${new Date(createdAtUtc).toLocaleString('zh-TW')}`, id);
  }));
  if (savedVenuePlans?.some(row => row.id === selectedId)) select.value = selectedId;
}
async function refreshSavedVenuePlans() {
  if ($('refresh-venue-plans').disabled || !$('saved-venue-mission-plans').open) return;
  const epoch = state.epoch;
  await run(async () => {
    const rows = await api('/venue/mission-plans');
    if (epoch !== state.epoch) return;
    if (!Array.isArray(rows) || !rows.every(validSavedVenuePlan) || new Set(rows.map(row => row.id)).size !== rows.length)
      throw new MissionVersionMismatch('無法核對已保存的五房配置。');
    savedVenuePlans = rows;
    renderSavedVenuePlans();
    if (venueMissionReview?.saved) clearVenueMissionReview();
    $('venue-plan-status').textContent = rows.length ? '' : '尚無已保存的五房配置。';
  }, true);
}
async function readVenueMissionRevisions(ids) {
  const unique = [...new Set(ids)];
  const results = await Promise.allSettled(unique.map(async id => {
    const revision = await api(`/missions/${id}/version`);
    if (!validLaunchRevision(revision) || revision.mission.id !== id) throw new Error();
    return revision;
  }));
  const versions = new Map(results.map((result, index) => [unique[index], result.status === 'fulfilled' ? result.value : null]));
  return ids.map(id => versions.get(id));
}
async function loadSavedVenuePlan(previewOnly) {
  const saved = savedVenuePlans?.find(row => row.id === $('saved-venue-plan').value);
  const status = $('venue-plan-status');
  if (!saved || $(previewOnly ? 'preview-venue-plan' : 'load-venue-plan').disabled) return;
  const epoch = state.epoch, view = operationsViewEpoch;
  const current = () => state.epoch === epoch && operationsViewEpoch === view && master()
    && $('saved-venue-mission-plans').open && $('saved-venue-plan').value === saved.id;
  clearVenueMissionReview();
  status.textContent = '';
  await run(async () => {
    if (!current()) return;
    const original = await api(`/venue/mission-plans/${saved.id}`);
    if (!current()) return;
    if (!validSavedVenuePlan(original) || original.id !== saved.id || original.createdAtUtc !== saved.createdAtUtc
      || !matchesVenuePlan(original.plan, saved.plan))
      throw new MissionVersionMismatch('無法核對原五房配置。已保留目前準備選擇，請更新清單後再試。');
    const revisions = await readVenueMissionRevisions(original.plan.missionIds);
    if (!current()) return;
    const missing = venueMissionRooms.filter(room => !revisions[room - 1]);
    if (missing.length)
      throw new MissionVersionMismatch(`無法核對房間 ${missing.join('、')} 的原任務版本，已保留目前準備選擇。`);
    if (previewOnly) {
      status.textContent = '正在核對保存配置的場地…';
      if (await previewVenueMissionRevisions({ saved }, original.plan.mode, revisions, current))
        status.textContent = `已核對「${original.plan.name}」。確認後可載入配置。`;
      return;
    }
    applyVenueMissionRevisions(original.plan.mode, revisions);
    status.textContent = `已載入「${original.plan.name}」。請核對場地，再建立準備場次。`;
  }, true);
}
function saveVenuePlan() {
  if ($('save-venue-plan').disabled) return;
  const selected = venueMissionSelection(), name = $('venue-plan-name').value.trim();
  if (!selected || !name) return;
  if (/[\u0000-\u001f\u007f-\u009f]/u.test(name)) {
    $('venue-plan-status').textContent = '配置名稱含有無法使用的控制字元。';
    return;
  }
  const body = { name, mode: selected.mode, missionIds: selected.rooms.map(room => room.missionId) };
  void run(async () => {
    state.pending = { kind: 'venue-plan-save', path: '/venue/mission-plans', method: 'POST', requestId: uuid(), body };
    await sendPending();
  });
}
function renderVenueMissionReview() {
  const review = venueMissionReview, panel = $('venue-missions-review'), list = $('venue-missions-review-rows');
  const applySelected = $('use-selected-venue-mission-rooms');
  panel.hidden = !review || !master();
  $('venue-mission-comparison').hidden = panel.hidden;
  const mode = $('launch-mode');
  const canSelect = !panel.hidden && mode.value === 'IndependentSet' && review.mode === 'IndependentSet';
  if (!canSelect) review?.selectedRooms.clear();
  applySelected.hidden = !canSelect;
  applySelected.disabled = true;
  if (panel.hidden) {
    $('venue-missions-review-summary').textContent = '';
    list.replaceChildren();
    renderVenueMissionMaps();
    return;
  }
  const current = configuredVenueRevisions(mode.value);
  const locked = state.busy || !!state.pending;
  const focusedRoom = document.activeElement?.dataset.venueMissionFileRoom;
  const modeName = value => [...mode.options].find(option => option.value === value)?.textContent ?? '';
  const source = review.saved ? '保存配置' : '檔案';
  $('venue-missions-incoming-title').textContent = `${source}指定`;
  $('venue-missions-layout-title').textContent = `${source}版本場地`;
  const changes = current.filter((revision, index) => revision?.mission.id !== review.revisions[index].mission.id).length;
  $('venue-missions-review-summary').textContent = `目前為${modeName(mode.value)}，${source}指定${modeName(review.mode)}。版本不同 ${changes} 房。`;
  function label(revision) {
    if (!revision) return '尚未指定';
    const { definition } = revision.mission;
    const historical = state.catalog.some(head => head.seriesId === revision.seriesId && head.number > revision.number);
    const summary = element('div', `${definition.name} · 第 ${revision.number} 版${historical ? '（歷史）' : ''} · ${definition.environment.mode} · ${definition.durationSeconds} 秒`);
    summary.append(element('div', venueClimateText(definition.environment), 'hint mission-file-climate'),
      element('div', missionEnemyText(definition.enemies), 'hint mission-file-enemies'));
    return summary;
  }
  list.replaceChildren(...venueMissionRooms.map((roomId, index) => {
    const original = current[index], incoming = review.revisions[index];
    const previousId = original?.mission.id ?? '', incomingId = incoming.mission.id;
    const layout = review.layouts.get(incomingId);
    const layoutText = !layout ? '暫未核對' : layout.applies && layout.canStart ? '檢查通過' : '配置須修正';
    const roomLabel = `房間 ${roomId}`;
    let roomCell = roomLabel;
    if (previousId === incomingId) review.selectedRooms.delete(roomId);
    if (canSelect) {
      const select = element('input'), choice = element('label', null, 'check');
      select.type = 'checkbox'; select.disabled = locked || previousId === incomingId;
      select.dataset.venueMissionFileRoom = String(roomId);
      select.setAttribute('aria-label', `勾選房間 ${roomId} 的${source}版本`);
      select.checked = review.selectedRooms.has(roomId);
      select.addEventListener('change', () => {
        if (select.checked) review.selectedRooms.add(roomId); else review.selectedRooms.delete(roomId);
        applySelected.disabled = !review.selectedRooms.size;
      });
      choice.append(select, roomLabel);
      roomCell = choice;
    }
    const entry = row([roomCell, label(original), label(incoming), layoutText]);
    entry.dataset.currentMission = previousId;
    entry.dataset.fileMission = incomingId;
    entry.dataset.changed = String(previousId !== incomingId);
    entry.cells[3].dataset.status = !layout ? 'unknown' : layout.applies && layout.canStart ? 'valid' : 'invalid';
    return entry;
  }));
  if (canSelect) {
    applySelected.disabled = locked || !review.selectedRooms.size;
    if (focusedRoom) list.querySelector(`[data-venue-mission-file-room="${focusedRoom}"]`)?.focus();
  }
  renderVenueMissionMaps(review, current, mode.value);
}
function renderVenueMissionMaps(review, current, mode) {
  const panel = $('venue-missions-maps'), grid = $('venue-missions-maps-grid'), picker = $('venue-missions-map-room');
  const applyRoom = $('use-venue-mission-room');
  applyRoom.hidden = review?.mode !== 'IndependentSet' || mode !== 'IndependentSet';
  applyRoom.disabled = true;
  panel.hidden = !review;
  if (!review) {
    venueMissionMaps = null;
    picker.value = '1'; grid.replaceChildren();
    return;
  }
  const room = Number(picker.value);
  const original = current[room - 1], incoming = review.revisions[room - 1];
  const source = review.saved ? '保存配置' : '檔案';
  if (!applyRoom.hidden) {
    applyRoom.textContent = `套用房間 ${room} 的${source}版本`;
    applyRoom.disabled = state.busy || !!state.pending || original?.mission.id === incoming.mission.id;
  }
  const key = `${room}/${mode}/${original?.mission?.id ?? ''}`;
  if (venueMissionMaps?.review === review && venueMissionMaps.key === key) return;
  const comparison = venueMissionMaps = { review, key };
  function drawCard(card, title, revision, report, waiting = false) {
    const heading = element('h4', title);
    if (!revision) { card.replaceChildren(heading, element('p', '本房尚未指定任務。', 'hint')); return; }
    if (!validLaunchRevision(revision)) { card.replaceChildren(heading, element('p', '無法核對保存版本。', 'hint')); return; }
    const { mission, number } = revision;
    const { name, environment, props } = mission.definition;
    card.dataset.missionId = mission.id;
    const map = savedRoomLayoutMap(room, props, report);
    map.setAttribute('aria-label', `房間 ${room} · ${title}的場地配置`);
    const status = waiting ? '正在核對場地及出生位…' : !report?.applies ? '未取得可核對的場地及出生位。'
      : report.canStart ? '場地檢查通過。' : `場地有 ${report.totalIssueCount} 個問題。`;
    card.replaceChildren(heading, element('p', `${name} · 第 ${number} 版 · ${environment.mode} · ${props.length} 件物件`),
      element('p', status, 'hint'), map);
  }
  const before = element('article'), after = element('article');
  before.dataset.source = 'current'; after.dataset.source = 'file';
  drawCard(before, '目前準備', original, null, !!original);
  drawCard(after, `${source}指定`, incoming, review.layouts.get(incoming.mission.id));
  grid.replaceChildren(before, after);
  if (validLaunchRevision(original)) {
    const { mission } = original;
    void placement.inspectSaved({ id: mission.id, mode: mode === 'Linked' ? 'Linked' : 'Independent',
      experienceMode: mission.definition.environment.mode }).catch(() => null).then(report => {
      if (venueMissionMaps === comparison && master()) drawCard(before, '目前準備', original, report);
    });
  }
}
function clearVenueMissionReview() {
  venueMissionReview = null;
  renderVenueMissionReview();
}
async function previewVenueMissionRevisions(source, mode, revisions, current) {
  const originals = new Map(revisions.map(revision => [revision.mission.id, revision]));
  const inspections = await Promise.allSettled([...originals].map(([id, revision]) => placement.inspectSaved({ id,
    mode: mode === 'Linked' ? 'Linked' : 'Independent', experienceMode: revision.mission.definition.environment.mode })));
  if (!current()) return false;
  const layouts = new Map([...originals.keys()].map((id, index) => [id,
    inspections[index].status === 'fulfilled' ? inspections[index].value : null]));
  venueMissionReview = { ...source, mode, revisions, layouts, selectedRooms: new Set() };
  $(source.saved ? 'saved-venue-mission-plans' : 'launch-mission-file-panel').append($('venue-mission-comparison'));
  return true;
}
function clearVenueMissionFile() {
  $('venue-missions-file').value = '';
  $('preview-venue-missions').disabled = true;
  $('load-venue-missions').disabled = true;
  $('venue-missions-file-status').textContent = '';
  $('launch-mission-file-panel').open = false;
  clearVenueMissionReview();
}
function validLaunchRevision(revision) {
  const definition = revision?.mission?.definition;
  const env = definition?.environment;
  const enemies = definition?.enemies;
  return !!revision?.mission?.id && Number.isSafeInteger(revision.number) && revision.number > 0
    && typeof definition?.name === 'string' && Number.isSafeInteger(definition.durationSeconds)
    && ['VR', 'MR'].includes(env?.mode) && Object.hasOwn(weatherNames, env.weather)
    && ['Day', 'Night'].includes(env.timeOfDay) && typeof env.lightning === 'boolean'
    && Number.isSafeInteger(enemies?.count) && enemies.count >= 0 && enemies.count <= 100
    && Object.hasOwn(behaviorNames, enemies.behavior) && typeof enemies.autoAttack === 'boolean'
    && Array.isArray(definition.props) && definition.props.length <= 500
    && definition.props.every(prop => typeof prop?.assetId === 'string' && prop.position
      && [prop.position.x, prop.position.y, prop.position.z, prop.yawDegrees].every(Number.isFinite));
}
function applyVenueMissionRevisions(mode, revisions) {
  $('launch-mode').value = mode;
  if (mode === 'IndependentSet') {
    roomPlan.restore(revisions);
  } else {
    pinLaunchRevision(revisions[0]);
  }
}
function pinLaunchRevision(revision) {
  state.launchPinned = revision;
  missionOptions(revision.mission.id);
  placement.recheckLaunch();
}
async function prepareFromSession() {
  const session = state.session, epoch = state.epoch, selection = selectionEpoch, view = operationsViewEpoch;
  if ($('prepare-from-session').disabled || !manages(session) || session.state !== 'Ended') return;
  const id = session.mission.id;
  const current = () => state.epoch === epoch && selectionEpoch === selection && operationsViewEpoch === view
    && state.session?.id === session.id && state.session.state === 'Ended' && manages();
  let prepared = false;
  await run(async () => {
    if (!current()) return;
    const revision = await api(`/missions/${id}/version`);
    if (!current()) return;
    if (!validLaunchRevision(revision) || revision.mission.id !== id) {
      notify('無法核對原場次的任務版本，已保留目前的準備選擇。', true);
      return;
    }
    $('launch-mode').value = session.mode;
    if (session.mode === 'Independent') $('launch-room').value = String(session.roomIds[0]);
    pinLaunchRevision(revision);
    prepared = true;
    notify('已選用原場次的任務版本。請核對場地，再建立準備場次。');
  }, true);
  if (prepared && current()) $('launch-mission').focus();
}
async function loadVenueMissionFile(previewOnly) {
  const input = $('venue-missions-file'), file = input.files[0], status = $('venue-missions-file-status');
  const epoch = state.epoch, view = operationsViewEpoch;
  if (!file || $(previewOnly ? 'preview-venue-missions' : 'load-venue-missions').disabled) return;
  const current = () => master() && state.epoch === epoch && operationsViewEpoch === view && input.files[0] === file;
  clearVenueMissionReview();
  status.textContent = '正在核對配置檔內的任務版本…';
  await run(async () => {
    if (!current()) return;
    let plan;
    try {
      if (!file.size || file.size > venueMissionFileLimit) throw new Error();
      plan = parseVenueMissionFile(await file.text());
    } catch {
      if (current()) status.textContent = '配置格式不符。請選擇 4 KiB 以內的五房任務配置 JSON。';
      return;
    }
    if (!current()) return;
    const assigned = await readVenueMissionRevisions(plan.ids);
    if (!current()) return;
    const rooms = venueMissionRooms.filter(room => !assigned[room - 1]);
    if (rooms.length) {
      status.textContent = `無法核對房間 ${rooms.join('、')} 的任務版本，已保留目前配置。請確認任務庫含有原保存版本。`;
      return;
    }
    if (previewOnly) {
      status.textContent = '正在核對檔案版本的場地…';
      if (await previewVenueMissionRevisions({ file }, plan.mode, assigned, current))
        status.textContent = '已核對檔案版本。確認後可載入配置。';
      return;
    }
    applyVenueMissionRevisions(plan.mode, assigned);
    status.textContent = '已載入五房任務配置。請核對場地，再建立準備場次。';
  }, true);
}
function useVenueMissionRooms(rooms) {
  const review = venueMissionReview;
  if (!master() || state.busy || state.pending || review?.mode !== 'IndependentSet' || $('launch-mode').value !== 'IndependentSet') return;
  if (review.saved ? !$('saved-venue-mission-plans').open || $('saved-venue-plan').value !== review.saved.id
    || !savedVenuePlans?.includes(review.saved) : review.file !== $('venue-missions-file').files[0]) return;
  const original = configuredVenueRevisions('IndependentSet');
  const changedRooms = venueMissionRooms.filter(room => rooms.includes(room)
    && original[room - 1]?.mission.id !== review.revisions[room - 1].mission.id);
  if (!changedRooms.length) return;
  const picker = $('venue-missions-map-room');
  picker.value = String(changedRooms[0]);
  roomPlan.restoreRooms(new Map(changedRooms.map(room => [room, review.revisions[room - 1]])));
  $(review.saved ? 'venue-plan-status' : 'venue-missions-file-status').textContent =
    `已套用房間 ${changedRooms.join('、')} 的任務版本。請核對場地，再建立準備場次。`;
  picker.focus();
}
function launchPlan() {
  const mode = $('launch-mode').value, mixed = roomPlan.enabled();
  const preview = mixed ? roomPlan.preview() : null;
  const revision = mixed ? preview.revision : commonLaunchRevision();
  const roomIds = mode === 'Independent' ? [Number($('launch-room').value)] : [1, 2, 3, 4, 5];
  const rooms = roomIds.map(id => state.rooms.find(room => room.id === id && ownsRoom(id)));
  const authorized = master() || (mode === 'Independent' && state.actor?.role === 'RoomController');
  return { revision, rooms, mixed, previewRoom: preview?.roomId, available: authorized && rooms.every(room => room && !room.sessionId),
    body: { missionId: revision?.mission.id ?? '', mode, roomIds } };
}
function renderLaunchPreview(plan) {
  const { revision, rooms, mixed, previewRoom, body } = plan, preview = $('launch-preview');
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
  const shownRooms = mixed ? rooms.filter(room => room?.id === previewRoom) : rooms;
  $('launch-preview-rooms').textContent = shownRooms.length && shownRooms.every(Boolean)
    ? shownRooms.map(room => `房間 ${room.id}${room.sessionId ? '（使用中）' : ''}`).join('、') : '尚無可用的房間資訊';
  $('launch-preview-duration').textContent = `${durationSeconds} 秒`;
  $('launch-preview-environment').textContent = `${env.mode} · ${venueClimateText(env)}`;
  $('launch-preview-enemies').textContent = `${mixed ? '本房' : body.mode === 'IndependentSet' ? '各場' : '全場'} ${missionEnemyText(enemy)}`;
  const sandbags = props.filter(prop => prop.assetId === 'sandbag').length;
  const barrels = props.filter(prop => prop.assetId === 'barrel').length;
  $('launch-preview-props').textContent = `每房 ${props.length} 件 · 沙包 ${sandbags} · 油桶 ${barrels}`;
  $('launch-preview-briefing-text').textContent = briefing || '此任務未填寫簡報。';
}
function applyPermissions() {
  if (!state.actor) return;
  const session = state.session, ended = session?.state === 'Ended', locked = state.busy || !!state.pending;
  const prepare = $('prepare-from-session');
  prepare.hidden = !ended || !manages(session);
  prepare.disabled = locked || prepare.hidden;
  applyVenuePermissions();
  venueRoster.render();
  $('create-fields').disabled = locked || state.actor.role === 'GameServer';
  $('launch-room').disabled = $('launch-mode').value !== 'Independent';
  roomPlan.render();
  const selectedVenue = venueMissionSelection();
  $('saved-venue-mission-plans').hidden = !master();
  $('venue-plan-name').disabled = $('refresh-venue-plans').disabled = locked || !master();
  $('save-venue-plan').disabled = locked || !master() || !selectedVenue || !$('venue-plan-name').value.trim();
  $('saved-venue-plan').disabled = locked || !master() || !savedVenuePlans?.length;
  $('preview-venue-plan').disabled = $('load-venue-plan').disabled = $('saved-venue-plan').disabled || !$('saved-venue-plan').value;
  $('launch-mission-file-panel').hidden = !master();
  $('download-venue-missions').disabled = locked || !master() || !selectedVenue;
  $('venue-missions-file').disabled = locked || !master();
  $('preview-venue-missions').disabled = $('load-venue-missions').disabled = locked || !master() || !$('venue-missions-file').files.length;
  renderVenueMissionReview();
  const plan = launchPlan();
  renderLaunchPreview(plan);
  const create = $('create-session-form').querySelector('button');
  create.textContent = plan.body.mode === 'IndependentSet' ? '建立五個準備場次' : '建立準備場次';
  create.disabled = locked || !plan.revision || !plan.available || !placement.canLaunch() || (plan.mixed && !roomPlan.ready());
  $('mission-fields').disabled = locked || !master();
  renderPropHistory();
  $('load-mission').disabled = locked || !$('edit-mission').value; $('new-mission').disabled = locked || !master();
  $('launch-selected-mission').disabled = locked || !$('edit-mission').value;
  $('edit-mission').disabled = locked;
  $('mission-search').disabled = locked;
  $('mission-version').disabled = locked || !state.history;
  $('load-version').disabled = locked || !state.history;
  $('export-mission-template').hidden = !master();
  $('export-mission-template').disabled = locked || !master() || !$('mission-version').value;
  $('mission-template-panel').hidden = !master();
  $('mission-template-file').disabled = locked || !master();
  $('export-draft-template').disabled = !canExportDraftTemplate();
  $('check-mission-template').disabled = locked || !master() || !$('mission-template-file').files.length;
  $('use-mission-template').disabled = locked || !master() || !checkedTemplate;
  $('compare-version').disabled = locked || !state.history || !$('mission-version').value;
  $('launch-compared-version').disabled = locked || !comparedVersion;
  $('restore-compared-version').hidden = !master();
  $('restore-compared-version').disabled = locked || !master() || !restoreParent();
  $('more-versions').disabled = locked || !state.history?.nextBefore;
  $('launch-version').disabled = locked || !state.draftBase;
  $('save-revision').disabled = locked || !master() || !state.draftBase || state.draftBase.number !== knownHeadNumber(state.draftBase.seriesId);
  $('merge-mission-head').disabled = locked || !master();
  for (const kind of ['environment', 'enemies']) {
    $(kind + '-fields').disabled = locked || !manages() || ended || !session;
    $(kind + '-form').querySelector('button[type=submit]').disabled = !liveSettingDrafts[kind]?.sequence;
  }
  renderRoomEnemyPolicy();
  $('clock-fields').disabled = locked || !manages() || session?.state !== 'Preparing' || session?.combatStream?.missionClockVersion !== 1;
  $('join-fields').disabled = locked || session?.state !== 'Preparing';
  const mixedReality = session?.environment.mode === 'MR';
  $('player-headset').querySelector('option[value="ViveXr"]').disabled = mixedReality;
  if (mixedReality) $('player-headset').value = 'Quest3';
  $('ticket-fields').disabled = locked || ended || !session;
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
    if (action === 'Begin') {
      const label = usesTrackedVrStart(session) ? '確認追蹤並開始' : '開始任務';
      if (button.textContent !== label) button.textContent = label;
    }
  }
  $('pending-command').hidden = !state.pending;
  $('retry-command').disabled = state.busy;
  $('session-select').disabled = locked;
  $('include-ended').disabled = locked;
  $('refresh').disabled = !!state.pending;
  document.querySelectorAll('.room-card button:not([data-room-vr-resume])').forEach(button => { button.disabled = locked; });
  if (locked) document.querySelectorAll('[data-room-vr-resume]').forEach(button => { button.disabled = true; });
  document.querySelectorAll('[data-player-action=remove]').forEach(button => {
    const room = Number(button.dataset.playerRoom);
    button.disabled = locked || ended || !ownsRoom(room);
  });
  alignmentPins.update();
  seatDeployments.forEach(panel => panel.update());
  mrVenue.update();
}
function renderRoomEnemyPolicy(reload = false) {
  const session = state.session, panel = $('room-enemies-panel'), picker = $('room-enemies-room');
  panel.hidden = session?.mode !== 'Linked' || session.state === 'Ended' || session.combatStream?.roomEnemyPolicyVersion !== 1;
  if (panel.hidden) { roomEnemyDraft = null; return; }
  const rooms = session.roomIds.filter(room => ownsRoom(room));
  const scope = JSON.stringify([session.id, rooms]);
  if (picker.dataset.scope !== scope) {
    fillOptions('room-enemies-room', rooms.map(room => [room, `房間 ${room}`]));
    picker.dataset.scope = scope;
  }
  const room = Number(picker.value), policy = session.roomEnemyPolicies?.find(value => value.roomId === room);
  const settings = policy ?? session.enemies, key = session.id + '/' + room;
  const sequence = roomEnemyPolicySequences?.[room];
  const available = Number.isSafeInteger(sequence) && sequence > 0 && sequence <= session.sequence;
  if (available && (reload || roomEnemyDraft?.key !== key)) {
    roomEnemyDraft = { key, sequence };
    $('room-enemies-behavior').value = settings.behavior;
    $('room-enemies-auto').checked = settings.autoAttack;
    $('room-enemies-inherit').checked = !policy;
  }
  $('room-enemies-current').textContent = `房間 ${room} · ${policy ? '本房策略' : '沿用全場'} · ${behaviorNames[settings.behavior]} · 自動攻擊${settings.autoAttack ? '開啟' : '關閉'}`;
  const draft = roomEnemyDraft?.key === key ? roomEnemyDraft : null;
  const stale = draft?.conflicted || draft?.sequence !== sequence;
  const status = $('room-enemies-draft');
  status.textContent = !available ? '尚未取得本房策略版本。請載入目前策略。'
    : stale ? '本房策略已有更新，已保留草稿。載入目前策略會取代草稿。' : '';
  status.hidden = !status.textContent;
  $('room-enemies-fields').disabled = !room || state.busy || !!state.pending;
  $('room-enemies-inherit').disabled = !available;
  $('room-enemies-behavior').disabled = $('room-enemies-auto').disabled = !available || $('room-enemies-inherit').checked;
  $('room-enemies-apply').disabled = !available || stale;
}
function venueTargets(action) {
  const rows = state.venue?.[{ SetEnvironment: 'environment', SetEnemies: 'enemies' }[action] ?? action.toLowerCase()];
  return Array.isArray(rows) && rows.length <= 5 && rows.every(row => typeof row?.sessionId === 'string'
    && Number.isSafeInteger(row.phaseSinceSequence) && row.phaseSinceSequence > 0 && Array.isArray(row.roomIds)
    && (action !== 'Begin' || (Number.isSafeInteger(row.sessionSequence) && row.sessionSequence >= row.phaseSinceSequence))
    && (action !== 'SetEnvironment' || (Number.isSafeInteger(row.environmentSinceSequence) && row.environmentSinceSequence > 0))
    && (action !== 'SetEnemies' || (Number.isSafeInteger(row.enemiesSinceSequence) && row.enemiesSinceSequence > 0
      && (row.roomEnemiesSinceSequence === undefined || (Number.isSafeInteger(row.roomEnemiesSinceSequence)
        && row.roomEnemiesSinceSequence > row.enemiesSinceSequence))
      && (row.roomEnemyOverrideRoomIds === undefined || (Array.isArray(row.roomEnemyOverrideRoomIds)
        && row.roomEnemyOverrideRoomIds.length <= 5 && row.roomEnemyOverrideRoomIds.every(id => row.roomIds.includes(id))))))
    && row.roomIds.length > 0 && row.roomIds.every(id => Number.isInteger(id) && id >= 1 && id <= 5)) ? rows : [];
}
function venueRoomText(targets) { return targets.flatMap(row => row.roomIds).sort((a, b) => a - b).join('、'); }
function venueEnemyOverrides(targets) {
  return targets.flatMap(row => row.roomEnemyOverrideRoomIds ?? []).sort((a, b) => a - b).join('、');
}
function venueClimateText({ weather, timeOfDay, lightning }) {
  return `${weatherNames[weather]} · ${timeOfDay === 'Night' ? '夜晚' : '白天'} · ${lightning ? '閃電開啟' : '閃電關閉'}`;
}
function venueEnemyText({ behavior, autoAttack }) {
  return `${behaviorNames[behavior]} · ${autoAttack ? '自動攻擊開啟' : '自動攻擊關閉'}`;
}
function missionEnemyText(enemies) {
  return `${enemies.count} 名 · ${venueEnemyText(enemies)}`;
}
function settingBatchRoom(kind, batch, session, room) {
  if (session.state === 'Ended') return { status: 'Ended', text: '原場次已結束' };
  const enemy = kind === 'enemies', current = roomReadiness.settingStatus(room, kind, session.sessionId);
  if (session.state === 'Superseded' || (enemy && session.supersededRoomIds?.includes(room))
    || current?.setting.appliedAtSequence > session.appliedAtSequence)
    return { status: 'Superseded', text: enemy ? '已被較新的敵軍設定覆寫' : '已被較新的環境設定覆寫' };
  if (!current?.target || !current.venue || current.setting.appliedAtSequence !== session.appliedAtSequence
    || (enemy ? current.setting.behavior !== batch.behavior || current.setting.autoAttack !== batch.autoAttack
      || current.targetCount !== session.targetCount : current.setting.weather !== batch.weather
      || current.setting.timeOfDay !== batch.timeOfDay || current.setting.lightning !== batch.lightning))
    return { status: 'Waiting', text: '遊戲端待確認' };
  const text = enemy ? `遊戲端已套用 · 在場 ${current.population.present} 名、存活 ${current.population.alive} 名` : '遊戲端已套用';
  return { status: 'Applied', text,
    target: current.target };
}
async function openOriginalVenueSetting(kind, batch, session, roomId) {
  const request = ++venueSettingReview, epoch = state.epoch, view = operationsViewEpoch;
  const enemy = kind === 'enemies', key = enemy ? 'latestEnemies' : 'latestEnvironment', label = enemy ? '敵軍' : '環境';
  const current = () => master() && !state.busy && !state.pending && state.epoch === epoch && operationsViewEpoch === view
    && request === venueSettingReview && state.venue?.[key]?.requestId === batch.requestId;
  if (!current()) return;
  try {
    const scope = enemy ? `?roomId=${roomId}` : '';
    const original = await api(`/sessions/${session.sessionId}/world/venue-${kind}/${batch.requestId}${scope}`);
    if (!current()) return;
    const { streamId, worldSequence, appliedAtSequence, observedSequence, supersededAtSequence } = original;
    if (original.sessionId !== session.sessionId || original.requestId !== batch.requestId || appliedAtSequence !== session.appliedAtSequence
      || typeof streamId !== 'string' || !Array.isArray(original.roomIds) || !original.roomIds.includes(roomId)
      || (enemy && original.roomId !== roomId))
      throw new Error('Original venue setting changed');
    if (worldSequence === null) { notify(`原錄製中找不到套用這筆${label}指令的有效執行畫格。`, true); return; }
    if (!Number.isSafeInteger(worldSequence) || worldSequence < 1) throw new Error('Invalid saved frame');
    if (!Number.isSafeInteger(observedSequence) || observedSequence < appliedAtSequence
      || (supersededAtSequence !== undefined && (!Number.isSafeInteger(supersededAtSequence) || observedSequence >= supersededAtSequence)))
      throw new Error('Original setting revision differs');
    const { weather, timeOfDay, lightning, behavior, autoAttack } = batch;
    const witness = { kind, exactObserved: true, observedSequence,
      setting: enemy ? { appliedAtSequence, behavior, autoAttack }
      : { appliedAtSequence, weather, timeOfDay, lightning } };
    if (enemy) {
      const rows = original.enemyPopulations;
      const matching = Array.isArray(rows) && rows.length === 1 ? rows.filter(row => row?.roomId === roomId) : [];
      const population = matching.length === 1 ? matching[0] : null;
      if (!Number.isInteger(population?.present) || population.present < 0 || population.present > 100
        || !Number.isInteger(population.alive) || population.alive < 0 || population.alive > population.present)
        throw new Error('Invalid original enemy population');
      witness.population = population;
    }
    notify('');
    tab('world', { mode: 'replay', sessionId: session.sessionId, roomId, streamId, complete: false,
      throughSequence: worldSequence, witness });
  } catch {
    if (current()) notify(`無法讀取這筆指令的原${label}畫格。`, true);
  }
}
function renderVenueSettingBatch(locked, kind) {
  const enemy = kind === 'enemies', name = enemy ? 'enemy' : 'environment';
  const id = 'venue-' + name + '-batch', key = enemy ? 'latestEnemies' : 'latestEnvironment';
  const panel = $(id), list = $(id + '-rooms'), summary = $(id + '-summary');
  const batch = master() ? state.venue?.[key] : null;
  const valid = typeof batch?.requestId === 'string' && Number.isFinite(Date.parse(batch.recordedAtUtc))
    && (enemy ? Object.hasOwn(behaviorNames, batch.behavior) && typeof batch.autoAttack === 'boolean'
      : Object.hasOwn(weatherNames, batch.weather) && ['Day', 'Night'].includes(batch.timeOfDay) && typeof batch.lightning === 'boolean')
    && Array.isArray(batch.sessions) && batch.sessions.length > 0 && batch.sessions.length <= 5
    && batch.sessions.every(session => typeof session?.sessionId === 'string' && ['Current', 'Superseded', 'Ended'].includes(session.state)
      && Number.isSafeInteger(session.appliedAtSequence) && session.appliedAtSequence > 0
      && (!enemy || (Number.isInteger(session.targetCount) && session.targetCount >= 0 && session.targetCount <= 100))
      && Array.isArray(session.roomIds) && session.roomIds.length > 0
      && session.roomIds.length <= 5 && session.roomIds.every(room => Number.isInteger(room) && room >= 1 && room <= 5)
      && (!enemy || session.supersededRoomIds === undefined || (Array.isArray(session.supersededRoomIds)
        && session.supersededRoomIds.length <= session.roomIds.length
        && new Set(session.supersededRoomIds).size === session.supersededRoomIds.length
        && session.supersededRoomIds.every(room => session.roomIds.includes(room)))))
    && (!enemy || batch.roomIds === undefined || (Array.isArray(batch.roomIds)
      && batch.sessions.every(session => session.roomIds.length === 1)
      && JSON.stringify(batch.roomIds) === JSON.stringify(batch.sessions.flatMap(session => session.roomIds).sort((a, b) => a - b))));
  const rows = valid ? batch.sessions.flatMap(session => session.roomIds.map(room => ({ room, session, ...settingBatchRoom(kind, batch, session, room) })))
    .sort((a, b) => a.room - b.room) : [];
  panel.hidden = !rows.length || new Set(rows.map(row => row.room)).size !== rows.length;
  $(id + '-download').disabled = locked || panel.hidden || !state.venuePhaseBlob;
  const text = panel.hidden ? '' : `${enemy ? venueEnemyText(batch) : venueClimateText(batch)} · ${rows.filter(row => row.status === 'Applied').length} / ${rows.length} 房已確認`;
  if (summary.textContent !== text) summary.textContent = text;
  const signature = panel.hidden ? '' : JSON.stringify([batch.requestId, locked, rows.map(({ room, session, status, text }) =>
    [room, session.sessionId, session.appliedAtSequence, session.targetCount, status, text])]);
  if (list.dataset.rows === signature) return;
  list.dataset.rows = signature;
  list.replaceChildren(...(panel.hidden ? [] : rows.map(({ room, session, status, text, target }) => {
    const item = element('li');
    item.setAttribute(`data-${name}-batch-room`, room);
    item.setAttribute(`data-${name}-batch-state`, status);
    const count = enemy ? ` · 全場目標 ${session.targetCount} 名` : '';
    item.append(element('span', `房間 ${room} · 原命令 ${session.appliedAtSequence}${count} · ${text}`));
    if (target) {
      const button = element('button', enemy ? '檢視敵軍快照' : '檢視環境快照', 'quiet small');
      button.type = 'button'; button.disabled = locked;
      button.addEventListener('click', () => {
        const current = state.venue?.[key];
        if (!master() || state.busy || state.pending || current?.requestId !== batch.requestId) return;
        const latest = current.sessions?.find(row => row.sessionId === session.sessionId && row.roomIds?.includes(room));
        if (latest?.appliedAtSequence !== session.appliedAtSequence) return;
        const original = settingBatchRoom(kind, current, latest, room).target;
        if (original) tab('world', original);
      });
      item.append(button);
    } else if (['Superseded', 'Ended'].includes(status)) {
      const button = element('button', enemy ? '查找原敵軍畫格' : '查找原環境畫格', 'quiet small');
      button.type = 'button'; button.disabled = locked;
      button.addEventListener('click', () => openOriginalVenueSetting(kind, batch, session, room));
      item.append(button);
    }
    return item;
  })));
}
function venueBeginPolicy() {
  if ($('venue-full-tracking').checked) return 'tracking';
  return $('venue-full-participation').checked ? 'participation' : 'normal';
}
function venueBeginSize(policy) {
  return policy === 'normal' ? 5 : Number($('venue-begin-size').value);
}
function venueBeginRows(targets, policy, playersPerRoom) {
  const rows = targets.flatMap(target => {
    const session = state.sessions.find(session => session.id === target.sessionId
      && session.state === 'Preparing' && session.sequence === target.sessionSequence);
    return target.roomIds.map(roomId => {
      const row = { roomId, sessionId: target.sessionId, sessionSequence: target.sessionSequence,
        ...roomReadiness.venueBegin(target, roomId, policy, playersPerRoom) };
      const original = session && state.rooms.some(room => room.id === roomId && room.sessionId === session.id);
      if (original) {
        row.mode = session.environment.mode;
        if (row.mode === 'MR') row.alignment = /^[a-f0-9]{64}$/.test(session.roomAlignment?.[`room${roomId}`] ?? '')
          ? '已鎖定校正檔' : '校正檔尚未鎖定';
      }
      if (policy !== 'normal' && original) {
        const occupied = new Set(session.players.filter(player => player.roomId === roomId).map(player => player.seat));
        row.seats = Array.from({ length: 5 }, (_, index) => {
          if (index >= playersPerRoom) return occupied.has(index) ? 'OutsideStage' : 'NotInStage';
          if (!occupied.has(index)) return 'Vacant';
          const status = venueBeginSeatState(row, index);
          return status === 'Vacant' ? 'Unknown' : status;
        });
      }
      return row;
    });
  });
  if (policy !== 'normal' && rows.length) {
    for (const roomId of [1, 2, 3, 4, 5])
      if (!rows.some(row => row.roomId === roomId)) rows.push({ roomId, state: 'NotPreparing', text: '尚無準備中的目標場次' });
  }
  return rows.sort((a, b) => a.roomId - b.roomId);
}

const reviewableBeginSeatStates = new Set(['AwaitingAdmission', 'WaitingRevision', 'AwaitingPose', 'PoseUnavailable',
  'Eliminated', 'NeedsTracking', 'OutsideStage']);
let vacantBeginSelection = 0;

function isOriginalBeginRoom({ sessionId, sessionSequence, roomId }) {
  return venueTargets('Begin').some(target => target.sessionId === sessionId
    && target.sessionSequence === sessionSequence && target.roomIds.includes(roomId));
}

async function openVenueRoster(row, seat = null) {
  const { sessionId, sessionSequence, roomId } = row;
  if (!master() || state.busy || state.pending || $('operations-view').hidden) return;
  const changed = () => notify(seat === null ? '原房間的準備名冊已變更。請重新核對全館開場清單。'
    : '原席位的準備名冊已變更。請重新核對全館開場清單。', true);
  if (!isOriginalBeginRoom(row)) { changed(); return; }
  const epoch = state.epoch, view = operationsViewEpoch, selection = selectionEpoch + 1;
  await selectSession(sessionId, String(roomId));
  if (!master() || state.epoch !== epoch || operationsViewEpoch !== view || selectionEpoch !== selection) return;
  if (!isOriginalBeginRoom(row) || state.session?.sequence !== sessionSequence || state.session.state !== 'Preparing'
    || !focusRoster(sessionId, roomId, seat)) changed();
}

async function openVacantBeginSeat(row, seat) {
  if (!master() || state.busy || state.pending || $('operations-view').hidden) return;
  const request = ++vacantBeginSelection, epoch = state.epoch, view = operationsViewEpoch, selection = selectionEpoch;
  const current = () => request === vacantBeginSelection && state.epoch === epoch && view === operationsViewEpoch
    && selection === selectionEpoch && master() && !state.busy && !state.pending
    && venueBeginPolicy() !== 'normal' && seat <= venueBeginSize(venueBeginPolicy());
  try {
    if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* Read the roster again below. */ } }
    if (!current()) return;
    await refresh();
    if (!current()) return;
    if (isOriginalBeginRoom(row) && venueRoster.focusVacant({ ...row, seat })) return;
  } catch { /* Leave the original draft in place. */ }
  if (current()) notify('原空席已變更或無法確認。請重新核對全館開場清單。', true);
}

async function openVenueAlignment(row) {
  if (!master() || state.busy || state.pending || $('operations-view').hidden || !isOriginalBeginRoom(row)) return;
  const epoch = state.epoch, view = operationsViewEpoch;
  let selection = selectionEpoch;
  if (state.session?.id !== row.sessionId) {
    selection++;
    await selectSession(row.sessionId, String(row.roomId));
  }
  if (!master() || state.epoch !== epoch || operationsViewEpoch !== view || selectionEpoch !== selection) return;
  if (!isOriginalBeginRoom(row) || state.session?.id !== row.sessionId || state.session.sequence !== row.sessionSequence
      || state.session.environment.mode !== 'MR' || $('mr-alignment-pins').hidden) {
    notify('原 MR 場次已變更，請重新核對全館開場清單。', true);
    return;
  }
  const file = $(`mr-alignment-file-${row.roomId}`);
  const target = file && !file.hidden && !file.disabled ? file : $('mr-alignment-title');
  target.scrollIntoView({ block: 'center' });
  target.focus({ preventScroll: true });
}

function renderVenueBegin(targets, waiting, policy, playersPerRoom) {
  const summary = $('venue-begin-evidence'), list = $('venue-begin-rooms');
  const rows = venueBeginRows(targets, policy, playersPerRoom);
  summary.hidden = list.hidden = !rows.length;
  const message = !rows.length ? '' : `準備開始房間 ${venueRoomText(targets)} · `
    + (waiting ? '仍有開場條件待確認，請查看各房狀態。' : '目標場次已就緒。');
  if (summary.textContent !== message) summary.textContent = message;
  const locked = state.busy || !!state.pending;
  const signature = JSON.stringify([rows, locked]);
  if (list.dataset.rows === signature) return;
  list.dataset.rows = signature;
  list.replaceChildren(...rows.map(row => {
    const { roomId, sessionId, state: status, text, origin, mode, alignment } = row;
    const item = element('li', `房間 ${roomId} · ${text}` + (mode ? ` · ${mode}` : '')
      + (alignment ? ` · ${alignment}` : '') + (origin ? ` · 錄製來源 ${origin}` : ''));
    item.dataset.beginRoom = roomId;
    item.dataset.beginState = status;
    if (sessionId) {
      const button = element('button', '查看名冊', 'quiet small');
      button.type = 'button'; button.disabled = locked;
      button.setAttribute('aria-label', `查看房間 ${roomId} 名冊`);
      button.addEventListener('click', () => void openVenueRoster(row));
      item.append(' ', button);
    }
    if (mode === 'MR') {
      const button = element('button', '查看 MR 校正', 'quiet small');
      button.type = 'button'; button.disabled = locked;
      button.setAttribute('aria-label', `查看房間 ${roomId} MR 校正`);
      button.addEventListener('click', () => void openVenueAlignment(row));
      item.append(' ', button);
    }
    return item;
  }));
  const matrix = $('venue-begin-seats');
  matrix.hidden = !rows.some(row => row.seats);
  $('venue-begin-seat-rows').replaceChildren(...(matrix.hidden ? [] : rows.map(row => {
    const tr = element('tr');
    tr.dataset.beginSeatRoom = row.roomId;
    const room = element('th', `房間 ${row.roomId}`);
    room.scope = 'row';
    tr.append(room);
    for (let index = 0; index < 5; index++) {
      const status = venueBeginSeatState(row, index);
      const cell = element('td', beginSeatLabels[status]);
      cell.dataset.beginSeat = index + 1;
      cell.dataset.seatState = status;
      cell.classList.toggle('ready-player', status === 'Tracked' || status === 'Simulated');
      const vacant = status === 'Vacant' && policy !== 'normal' && index < playersPerRoom;
      if (row.sessionId && (vacant || reviewableBeginSeatStates.has(status))) {
        const button = element('button', beginSeatLabels[status], 'quiet small');
        button.type = 'button'; button.disabled = locked;
        button.setAttribute('aria-label', vacant ? `填寫房間 ${row.roomId} 第 ${index + 1} 席名冊`
          : `查看房間 ${row.roomId} 第 ${index + 1} 席名冊：${beginSeatLabels[status]}`);
        button.addEventListener('click', () => vacant ? void openVacantBeginSeat(row, index + 1) : void openVenueRoster(row, index + 1));
        cell.replaceChildren(button);
      }
      tr.append(cell);
    }
    return tr;
  })));
}
function renderConfirmedVenueBegin(locked) {
  const panel = $('venue-begin-observe'), list = $('venue-begin-observe-rooms');
  const begin = master() ? confirmedVenueBegin : null;
  panel.hidden = !begin;
  const rows = begin?.sessions.flatMap(original => original.roomIds.map(roomId => {
    const room = state.rooms.find(row => row.id === roomId);
    const target = roomReadiness.begunRoomObservation(original, roomId);
    const status = target ? '遊戲端已套用開場' : room && room.sessionId !== original.sessionId ? '原場次已離開此房'
      : state.sessions.find(session => session.id === original.sessionId)?.state === 'Paused' ? '原場次已暫停' : '等待原遊戲畫面';
    return { roomId, original, status, available: !!target };
  })).sort((a, b) => a.roomId - b.roomId) ?? [];
  const signature = JSON.stringify([begin?.requestId, locked, rows]);
  if (list.dataset.rows === signature) return;
  list.dataset.rows = signature;
  list.replaceChildren(...rows.map(({ roomId, original, status, available }) => {
    const item = element('li', `房間 ${roomId} · ${status}`);
    const watch = element('button', '即時觀戰', 'quiet small');
    watch.type = 'button';
    watch.disabled = locked || !available;
    watch.setAttribute('aria-label', `觀戰本次開場房間 ${roomId}`);
    watch.addEventListener('click', () => {
      if (!master() || begin !== confirmedVenueBegin || $('operations-view').hidden || state.busy || state.pending) return;
      const target = roomReadiness.begunRoomObservation(original, roomId);
      if (target) tab('world', target);
    });
    item.append(' ', watch);
    return item;
  }));
}
function applyVenuePermissions() {
  updateRoomTicketButtons();
  $('venue-phase').hidden = !master();
  const begin = master() ? venueTargets('Begin') : [], pause = venueTargets('Pause'), resume = venueTargets('Resume'), end = venueTargets('End');
  const locked = state.busy || !!state.pending || !master();
  $('export-venue-environment').disabled = locked;
  const originalRoster = begin.some(target => state.session?.state === 'Preparing' && state.session.id === target.sessionId
    && state.session.sequence === target.sessionSequence);
  $('roster-return-begin').hidden = !originalRoster;
  $('roster-return-begin').disabled = locked;
  $('venue-roster-return-begin').hidden = !begin.length;
  $('venue-roster-return-begin').disabled = locked;
  venueHistory.update(!locked);
  $('venue-closure-open-end').hidden = !master() || !confirmedVenueEnd;
  $('venue-closure-open-end').disabled = locked || !confirmedVenueEnd;
  $('restore-venue-plan').disabled = locked || !archivedPlan;
  mrVenue.update();
  vrVenue.update();
  venueServerPlan.update();
  venueLaunchReview.update();
  const policy = venueBeginPolicy();
  const playersPerRoom = venueBeginSize(policy);
  const starting = (policy !== 'normal' && begin.flatMap(target => target.roomIds).length !== 5)
    || begin.some(target => !roomReadiness.venueReady(target, 'Begin', policy, playersPerRoom));
  const waiting = resume.filter(target => !roomReadiness.venueReady(target));
  $('venue-full-tracking').disabled = locked || !begin.length;
  $('venue-full-participation').disabled = locked || !begin.length;
  $('venue-begin-size-field').hidden = policy === 'normal';
  $('venue-begin-size').disabled = locked || !begin.length || policy === 'normal';
  $('venue-begin').disabled = locked || !begin.length || starting;
  $('venue-begin-export').hidden = !begin.length;
  $('venue-begin-export').disabled = locked || !begin.length;
  $('venue-pause').disabled = locked || !pause.length;
  $('venue-resume').disabled = locked || !resume.length || !!waiting.length;
  $('venue-end').disabled = locked || !end.length;
  for (const [panel, action] of [['venue-environment', 'SetEnvironment'], ['venue-enemies', 'SetEnemies']]) {
    const allTargets = venueTargets(action);
    const { targets, reason } = venueSettingScopes[action].update(allTargets, locked);
    $(panel).hidden = !master();
    $(panel + '-fields').disabled = locked || !allTargets.length;
    const overridden = action === 'SetEnemies' ? venueEnemyOverrides(targets) : '';
    const targetText = targets.length ? `適用房間 ${venueRoomText(targets)} · ${targets.length} 個執行中場次。`
      + (overridden ? `套用時會清除房間 ${overridden} 的分房策略。` : '') : reason ?? '等待執行中場次。';
    if ($(panel + '-targets').textContent !== targetText) $(panel + '-targets').textContent = targetText;
  }
  renderVenueSettingBatch(locked, 'environment');
  renderVenueSettingBatch(locked, 'enemies');
  const describe = targets => targets.length ? '房間 ' + venueRoomText(targets) : '無';
  $('venue-end-targets').hidden = !end.length;
  $('venue-end-targets').textContent = end.length ? `可結束 ${describe(end)} · 包含準備、執行與暫停的場次。` : '';
  renderVenueBegin(begin, starting, policy, playersPerRoom);
  renderConfirmedVenueBegin(locked);
  $('venue-phase-targets').textContent = state.venue ? `可暫停 ${describe(pause)} · 可繼續 ${describe(resume)}` : '等待房間狀態。';
  const evidence = $('venue-phase-evidence');
  evidence.hidden = !resume.length;
  const message = waiting.length ? `等候房間 ${venueRoomText(waiting)} 的遊戲端確認或 MR 追蹤。` : '目標房間的暫停快照已確認。';
  if (evidence.textContent !== message) evidence.textContent = message;
  const list = $('venue-resume-rooms');
  const rows = resume.flatMap(target => target.roomIds.map(room => ({ room, ...roomReadiness.venueResume(target, room) })))
    .sort((left, right) => left.room - right.room);
  list.hidden = !rows.length;
  const signature = JSON.stringify(rows.map(({ room, state, text }) => [room, state, text]));
  if (list.dataset.rows !== signature) {
    list.dataset.rows = signature;
    list.replaceChildren(...rows.map(({ room, state, text }) => {
      const item = element('li', `房間 ${room} · ${text}`);
      item.dataset.resumeRoom = room;
      item.dataset.resumeState = state;
      return item;
    }));
  }
}

async function downloadVenueBeginChecklist() {
  if (!master() || $('venue-begin-export').disabled || $('operations-view').hidden) return;
  const epoch = state.epoch, view = operationsViewEpoch, policy = venueBeginPolicy();
  const playersPerRoom = venueBeginSize(policy);
  const targets = venueTargets('Begin');
  const signature = JSON.stringify(targets);
  const current = () => master() && state.epoch === epoch && operationsViewEpoch === view && !state.pending
    && !$('operations-view').hidden && document.visibilityState === 'visible';
  const sameScope = () => policy === venueBeginPolicy() && playersPerRoom === venueBeginSize(policy)
    && signature === JSON.stringify(venueTargets('Begin'));
  await run(async () => {
    if (!current()) return;
    await refresh();
    if (!current()) return;
    const read = sameScope() && await roomReadiness.recheck();
    if (!current()) return;
    const rows = read && sameScope() ? venueBeginRows(targets, policy, playersPerRoom) : [];
    if (!rows.length || rows.length > 5 || new Set(rows.map(row => row.roomId)).size !== rows.length
      || rows.some(row => row.state === 'Updating')) {
      notify('開場狀態無法確認或已變更。請核對目前房間，再下載清單。', true);
      return;
    }
    const timestamp = new Date().toISOString();
    download('vr-command-venue-begin-v1.csv', new Blob([encodeVenueBeginCsv(rows, policy, timestamp)], { type: 'text/csv;charset=utf-8' }));
  });
}
async function venuePhase(action, { environment, enemyPolicy, beginView } = {}) {
  const epoch = state.epoch;
  const currentBegin = () => epoch === state.epoch && master() && !state.pending && beginView === operationsViewEpoch
    && !$('operations-view').hidden && document.visibilityState === 'visible';
  if (!master() || state.pending || (action === 'Begin' && !currentBegin())) return;
  const allTargets = venueTargets(action);
  const { targets, roomIds } = venueSettingScopes[action]?.selection(allTargets) ?? { targets: allTargets };
  const policy = action === 'Begin' ? venueBeginPolicy() : 'normal';
  const playersPerRoom = venueBeginSize(policy);
  if (!targets.length || (policy !== 'normal' && targets.flatMap(target => target.roomIds).length !== 5)
    || (['Begin', 'Resume'].includes(action) && targets.some(target => !roomReadiness.venueReady(target, action, policy, playersPerRoom)))) return;
  const beginRooms = action === 'Begin' ? new Map(targets.map(target => [target.sessionId, { roomIds: target.roomIds,
    streamId: state.sessions.find(session => session.id === target.sessionId && session.sequence === target.sessionSequence)?.combatStream?.streamId ?? null }])) : null;
  const verb = { Begin: '開始', Pause: '暫停', Resume: '繼續', End: '結束', SetEnvironment: '設定環境給', SetEnemies: '設定敵軍策略給' }[action];
  const details = environment ? venueClimateText(environment) : enemyPolicy ? venueEnemyText(enemyPolicy) : '';
  const overridden = enemyPolicy ? venueEnemyOverrides(targets) : '';
  const opening = { normal: '', tracking: `\n須全館 ${playersPerRoom * 5} 席追蹤就緒。`,
    participation: `\n須全館 ${playersPerRoom * 5} 席已連線且姿態有效。` }[policy];
  const message = `${verb}房間 ${venueRoomText(targets)} 的 ${targets.length} 個場次？`
    + opening + (details ? '\n' + details : '') + (overridden ? `\n套用時會清除房間 ${overridden} 的分房策略。` : '');
  if (!confirm(action === 'End' ? message + '\n包含尚未開始的準備場次。結束後無法繼續原場次。' : message)) return;
  if (action === 'Begin') {
    const updated = await roomReadiness.recheck();
    if (!currentBegin()) return;
    if (!updated) {
      notify('無法取得最新開場狀態。請重新整理後再確認。', true);
      return;
    }
    if (policy !== venueBeginPolicy() || playersPerRoom !== venueBeginSize(policy)
      || targets.some(target => !roomReadiness.venueReady(target, action, policy, playersPerRoom))) {
      const rosterNeedsRefresh = targets.some(target => target.roomIds.some(roomId =>
        roomReadiness.venueBegin(target, roomId, policy, playersPerRoom).state === 'Updating'));
      if (rosterNeedsRefresh) {
        try { await refresh(); }
        catch {
          if (currentBegin()) notify('開場條件已變更，無法讀取目前名冊。請重新整理後再確認。', true);
          return;
        }
      }
      if (currentBegin()) notify('開場條件已變更。請核對各房最新狀態後再確認。', true);
      return;
    }
  }
  state.pending = { kind: 'venue-phase', path: '/venue/phase', method: 'POST', requestId: uuid(),
    ...(beginRooms ? { beginRooms } : {}),
    ...(action === 'End' ? { endRooms: new Map(targets.map(target => [target.sessionId, target.roomIds])) } : {}),
    body: { action, targets: targets.map(({ sessionId, phaseSinceSequence, sessionSequence, environmentSinceSequence, enemiesSinceSequence,
      roomEnemiesSinceSequence }) => ({ sessionId, phaseSinceSequence, sessionSequence, environmentSinceSequence, enemiesSinceSequence,
      roomEnemiesSinceSequence })), environment, enemyPolicy,
      ...(roomIds ? { roomIds } : {}),
      ...(playersPerRoom !== 5 ? { playersPerRoom } : {}),
      ...(policy === 'tracking' ? { requireFullTracking: true } : {}),
      ...(policy === 'participation' ? { requireFullParticipation: true } : {}) } };
  await sendPending();
}
async function selectVenueClosure() {
  const request = ++venueClosureEpoch, epoch = state.epoch;
  renderVenueClosure(null, true);
  if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* The selected batch is read below. */ } }
  if (request === venueClosureEpoch && epoch === state.epoch) await refresh().catch(showRefreshError);
}

async function openConfirmedVenueEnd() {
  const end = confirmedVenueEnd;
  if (!end || !master() || state.busy || state.pending || $('operations-view').hidden) return;
  const request = ++venueClosureEpoch, epoch = state.epoch, view = operationsViewEpoch;
  const current = () => confirmedVenueEnd === end && state.epoch === epoch && view === operationsViewEpoch
    && request === venueClosureEpoch && master() && !state.busy && !state.pending;
  try {
    const report = await api(`/venue/closure/${end.requestId}?includeScores=true&includeDebriefReceipts=true`);
    if (!current()) return;
    const batch = report?.batch;
    if (batch?.requestId !== end.requestId || !Array.isArray(batch.sessions) || batch.sessions.length !== end.sessions.length
      || !end.sessions.every(target => batch.sessions.some(row => row?.sessionId === target.sessionId
        && row.appliedAtSequence === target.appliedAtSequence && Array.isArray(row.roomIds)
        && row.roomIds.length === target.roomIds.length && row.roomIds.every((room, index) => room === target.roomIds[index]))))
      throw new Error('Closure differs from the confirmed End');
    if (!venueHistory.selectOriginal(end.requestId)) return;
    venueClosureEpoch++;
    renderVenueClosure(report);
    notify('已開啟本次結束批次。');
    $('venue-closure-title').focus();
  } catch {
    if (current()) notify('無法核對本次結束批次。請再按一次「查看本次結束批次」。', true);
  }
}

async function openReviewedVenueClosure(id, targets, stillCurrent) {
  const selection = venueClosureEpoch, view = operationsViewEpoch, epoch = state.epoch;
  const current = () => stillCurrent() && master() && !state.busy && !state.pending && state.epoch === epoch
    && venueClosureEpoch === selection && operationsViewEpoch === view;
  if (!current()) return;
  try {
    const report = await api(`/venue/closure/${id}?includeScores=true&includeDebriefReceipts=true`);
    if (!current()) return;
    const batch = report?.batch;
    if (batch?.requestId !== id || !Array.isArray(batch.sessions) || batch.sessions.length !== targets.length
      || !targets.every(target => batch.sessions.some(row => row?.sessionId === target.sessionId
        && Array.isArray(row.roomIds) && row.roomIds.join(',') === target.roomIds.join(',')
        && row.combat === 'Sealed' && row.world === 'Sealed' && row.replay?.streamId === target.streamId
        && row.replay.throughSequence === target.seal.worldSequence)))
      throw new Error('Original closure differs');
    if (!venueHistory.selectOriginal(id)) return;
    venueClosureEpoch++;
    renderVenueClosure(report);
    $('venue-closure-title').focus();
  } catch {
    if (current()) notify('無法確認原批次戰績與回條。請重新核對結束報告。', true);
  }
}

function openSessionReview(target) {
  const epoch = state.epoch, selection = selectionEpoch, roomId = report.roomId();
  tab('world', target.playerId ? { ...target, returnToScores: { label: '返回任務統計',
    action: () => returnToSessionScores(target, roomId, epoch, selection) } } : target);
}

async function returnToSessionScores(target, roomId, epoch, selection) {
  if (!state.actor || state.epoch !== epoch || state.busy || state.pending) return;
  tab('operations');
  const view = operationsViewEpoch;
  const current = () => state.epoch === epoch && operationsViewEpoch === view && selectionEpoch === selection
    && state.selected === target.sessionId && report.roomId() === roomId && !state.busy && !state.pending;
  try {
    await refresh();
    if (!current()) return;
    const { session, statistics } = state, picker = $('player-review-select');
    if (picker.value && picker.value !== target.playerId) return;
    if (session?.state !== 'Ended' || session.id !== target.sessionId || session.combatStream?.streamId !== target.streamId
      || session.combatStream.sealed !== true || session.combatStream.acceptedSequence !== target.throughCombatSequence
      || statistics?.sessionId !== session.id || statistics.throughSequence !== session.sequence || statistics.pendingTelemetry !== false
      || picker.disabled || ![...picker.options].some(option => option.value === target.playerId))
      throw new Error('Original session statistics differ');
    picker.value = target.playerId;
    closure.update();
    picker.focus();
  } catch {
    if (current()) notify('無法確認原玩家的任務統計。請重新核對場次。', true);
  }
}

function openClosurePlayerReplay(target, origin) {
  const epoch = state.epoch;
  tab('world', { ...target, returnToScores: { label: '返回原批次戰績',
    action: () => returnToClosureScores(target, origin, epoch) } });
}

async function returnToClosureScores(target, origin, epoch) {
  if (!master() || state.epoch !== epoch || state.busy || state.pending) return;
  tab('operations');
  const selection = venueClosureEpoch, view = operationsViewEpoch;
  const current = () => master() && state.epoch === epoch && !state.busy && !state.pending
    && venueClosureEpoch === selection && operationsViewEpoch === view;
  try {
    const report = await api(`/venue/closure/${origin.batchId}?includeScores=true&includeDebriefReceipts=true`);
    if (!current()) return;
    const batch = report?.batch;
    const session = batch?.requestId === origin.batchId && Array.isArray(batch.sessions)
      ? batch.sessions.find(row => row?.sessionId === target.sessionId && row.roomIds?.includes(target.roomId)) : null;
    if (session?.combat !== 'Sealed' || session.world !== 'Sealed' || session.replay?.streamId !== target.streamId
      || session.replay.throughSequence !== target.throughSequence) throw new Error('Original closure differs');
    const departure = origin.departed ? venueDepartureScope(batch, session) : null;
    if (origin.departed && !departure) throw new Error('Original departure differs');
    if (!venueHistory.selectOriginal(origin.batchId)) return;
    venueClosureEpoch++;
    renderVenueClosure(report);
    $('venue-closure-title').focus();
    if (departure) await openVenueDepartures(batch, session, departure, target.playerId);
    else venueDebrief.resume(origin.roomId, origin.onlyMissing, target.playerId);
  } catch {
    if (current()) notify('無法確認原批次戰績。可從全館收尾重新選取。', true);
  }
}

async function restoreVenuePlan() {
  const plan = archivedPlan, epoch = state.epoch, selection = venueClosureEpoch, view = operationsViewEpoch;
  if (!plan || $('restore-venue-plan').disabled) return;
  const linked = plan.mode === 'Linked';
  const current = () => master() && state.epoch === epoch && venueClosureEpoch === selection
    && operationsViewEpoch === view && archivedPlan?.requestId === plan.requestId && archivedPlan.mode === plan.mode;
  const matchesSession = (row, original) => row?.sessionId === original.sessionId
    && validLaunchRevision(row.revision) && archiveId.test(original.missionId)
    && row.revision.mission.id === original.missionId && row.revision.mission.definition.name === original.missionName;
  let restored = false;
  await run(async () => {
    if (!current()) return;
    const result = await api(`/venue/closure/${encodeURIComponent(plan.requestId)}/${linked ? 'linked-plan' : 'independent-plan'}`);
    if (!current()) return;
    const matches = result?.requestId === plan.requestId && (linked
      ? Array.isArray(result.roomIds) && result.roomIds.length === 5
        && result.roomIds.every((room, index) => room === index + 1) && matchesSession(result, plan.sessions[0])
      : Array.isArray(result.rooms) && result.rooms.length === plan.sessions.length
        && result.rooms.every((room, index) => room?.roomId === index + 1 && matchesSession(room, plan.sessions[index])));
    if (!matches) {
      notify('無法核對本批五房的原任務版本，已保留目前的準備選擇。', true);
      return;
    }
    applyVenueMissionRevisions(plan.mode, linked ? [result.revision] : result.rooms.map(room => room.revision));
    restored = true;
    notify('已套用本批五房的原任務版本。請核對各房場地，再建立準備場次。');
  });
  if (restored && current()) $(linked ? 'launch-mission' : 'launch-review-room').focus();
}

function venueDepartureScope(batch, session) {
  const replay = session.replay;
  if (!archiveId.test(batch.requestId) || !archiveId.test(session.sessionId) || !archiveId.test(replay?.streamId)
    || session.combat !== 'Sealed' || session.world !== 'Sealed' || session.fieldEvidenceReady !== true
    || !Number.isSafeInteger(session.rosterDepartureCount) || session.rosterDepartureCount < 1
    || !Number.isSafeInteger(session.appliedAtSequence) || session.appliedAtSequence < 3
    || !Number.isSafeInteger(replay.throughSequence) || replay.throughSequence < 1) return null;
  return JSON.stringify([batch.requestId, session.sessionId, session.roomIds, session.appliedAtSequence,
    replay.streamId, replay.throughSequence, session.rosterDepartureCount]);
}

function closeVenueDepartures() {
  departureReview?.csvController?.abort();
  departureReview = null;
  $('venue-departed-export').hidden = true;
  $('venue-departed-export').onclick = null;
  $('venue-departed-players').hidden = $('venue-departed-table').hidden = true;
  $('venue-departed-rows').replaceChildren();
  $('venue-departed-status').textContent = '';
}

async function downloadVenueDeparture(request, player, current) {
  if (!current() || state.busy || state.pending || request.csvController) return;
  const { playerId, room } = player, controller = new AbortController();
  request.csvController = controller;
  const timeout = setTimeout(() => controller.abort(), 8000);
  const status = $('venue-departed-status');
  const buttons = $('venue-departed-rows').querySelectorAll('[data-venue-departed-csv]');
  for (const button of buttons) button.disabled = true;
  status.textContent = '正在下載原封存戰績…';
  try {
    const response = await fetch(`/api/sessions/${room.sessionId}/players/${playerId}/report.csv`, {
      headers: { Authorization: 'Bearer ' + state.key }, cache: 'no-store', signal: controller.signal
    });
    if (!current()) return;
    if (response.status === 401) { logout(); return; }
    const filename = `vr-command-report-v1-${room.sessionId}-player-${playerId}.csv`;
    const type = response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase();
    const name = response.headers.get('Content-Disposition')?.match(/^attachment;\s*filename="?([^";\s]+)"?(?:;|$)/i)?.[1];
    if (!response.ok || type !== 'text/csv' || name !== filename) throw new Error('Report mismatch');
    const blob = await response.blob();
    if (!current()) return;
    if (blob.size < 1 || blob.size > 16 * 1024) throw new Error('Report size mismatch');
    const bytes = await blob.arrayBuffer();
    if (!current()) return;
    if (controller.signal.aborted || !matchesDebriefCsv(bytes, player)) throw new Error('Archive mismatch');
    download(filename, blob);
    status.textContent = '已下載離場玩家的原封存戰績。';
  } catch { if (current()) status.textContent = '暫時無法下載原封存戰績，可重新下載。'; }
  finally {
    clearTimeout(timeout);
    if (current()) {
      request.csvController = null;
      for (const button of buttons) button.disabled = false;
    }
  }
}

async function openVenueDepartures(batch, session, scope, focusPlayer = null) {
  if (!master() || state.busy || state.pending) return;
  closeVenueDepartures();
  const request = { scope, epoch: state.epoch };
  departureReview = request;
  const current = () => departureReview === request && master() && state.epoch === request.epoch;
  const status = $('venue-departed-status');
  $('venue-departed-players').hidden = false;
  $('venue-departed-title').focus();
  status.textContent = '正在讀取離場玩家的原封存戰績…';
  try {
    const body = await api(`/venue/closure/${batch.requestId}/sessions/${session.sessionId}/departed-players`);
    if (!current()) return;
    const scores = venueScoreFields.slice(1);
    if (body?.requestId !== batch.requestId || body.sessionId !== session.sessionId
      || body.streamId !== session.replay.streamId || body.worldSequence !== session.replay.throughSequence
      || body.endedAtSequence !== session.appliedAtSequence || !Number.isSafeInteger(body.finalStreamSequence)
      || !Number.isSafeInteger(body.throughSequence) || body.throughSequence < body.endedAtSequence
      || body.finalStreamSequence < 0 || !Array.isArray(body.players) || body.players.length !== session.rosterDepartureCount
      || new Set(body.players.map(player => player?.statistics?.playerId)).size !== body.players.length
      || new Set(body.players.map(player => player?.admissionId)).size !== body.players.length
      || !body.players.every(player => {
        const score = player?.statistics;
        return score && archiveId.test(score.playerId) && typeof score.name === 'string' && session.roomIds.includes(score.roomId)
          && archiveId.test(player.admissionId) && Number.isInteger(player.seat) && player.seat >= 0 && player.seat < 5
          && Number.isSafeInteger(player.joinedAtSequence) && player.joinedAtSequence >= 2
          && Number.isSafeInteger(player.leftAtSequence) && player.joinedAtSequence < player.leftAtSequence && player.leftAtSequence < body.endedAtSequence
          && scores.every(key => Number.isSafeInteger(score[key]) && score[key] >= 0) && score.shotsHit <= score.ammoUsed
          && Number.isFinite(score.accuracyPercent) && score.accuracyPercent >= 0 && score.accuracyPercent <= 100
          && Number.isInteger(score.health) && score.health >= 0 && score.health <= 100;
      })) throw new Error('Archive mismatch');
    $('venue-departed-rows').replaceChildren(...body.players.map(({ statistics: player, seat, joinedAtSequence, leftAtSequence }) => {
      const csv = element('button', '下載 CSV', 'quiet small');
      csv.type = 'button';
      csv.dataset.venueDepartedCsv = player.playerId;
      csv.setAttribute('aria-label', `下載房間 ${player.roomId} ${player.name} 的個人戰績 CSV`);
      csv.addEventListener('click', () => downloadVenueDeparture(request, { playerId: player.playerId, name: player.name,
        room: { sessionId: body.sessionId, streamId: body.streamId, roomId: player.roomId },
        throughSequence: body.throughSequence, throughCombatSequence: body.finalStreamSequence, score: player }, current));
      const replay = element('button', '個人回放', 'quiet small');
      replay.type = 'button';
      replay.dataset.venueDepartedReplay = player.playerId;
      replay.setAttribute('aria-label', `開啟房間 ${player.roomId} ${player.name} 的個人回放`);
      function openReplay(latestDamage) {
        if (!current() || state.busy || state.pending) return;
        openClosurePlayerReplay({ mode: 'replay', complete: true, sessionId: body.sessionId, streamId: body.streamId,
          roomId: player.roomId, throughSequence: body.worldSequence, throughCombatSequence: body.finalStreamSequence,
          playerId: player.playerId, playerName: player.name, playerScore: player, latestDamage },
        { batchId: batch.requestId, departed: true });
      }
      replay.addEventListener('click', () => openReplay(false));
      const actions = element('div', '', 'button-row');
      actions.append(replay);
      if (player.hitsReceived > 0) {
        const damage = element('button', '跳到最近中彈', 'quiet small');
        damage.type = 'button';
        damage.setAttribute('aria-label', `跳到房間 ${player.roomId} ${player.name} 最近中彈`);
        damage.addEventListener('click', () => openReplay(true));
        actions.append(damage);
      }
      return row([player.roomId, seat + 1, player.name, `${joinedAtSequence} → ${leftAtSequence}`,
        ...scores.map(key => player[key]), `${player.accuracyPercent}%`, player.health, csv, actions]);
    }));
    status.textContent = '';
    $('venue-departed-table').hidden = false;
    $('venue-departed-export').hidden = false;
    $('venue-departed-export').onclick = () => {
      if (current()) download(`vr-command-departed-${body.requestId}-${body.sessionId}.csv`,
        new Blob([encodeDepartedPlayersCsv(body)], { type: 'text/csv;charset=utf-8' }));
    };
    if (archiveId.test(focusPlayer ?? ''))
      $('venue-departed-rows').querySelector(`[data-venue-departed-replay="${focusPlayer}"]`)?.focus();
  } catch { if (current()) status.textContent = '暫時無法確認離場玩家戰績，可重新開啟。'; }
}

function renderVenueClosure(report, loading = false) {
  const panel = $('venue-closure'), batch = report?.batch;
  const signature = master() ? JSON.stringify([venueHistory.selected(), report, loading]) : '';
  if (panel.dataset.report === signature) return;
  panel.dataset.report = signature;
  panel.hidden = !master();
  const restore = $('restore-venue-plan');
  archivedPlan = null;
  restore.hidden = restore.disabled = true;
  const rows = $('venue-closure-rows');
  rows.replaceChildren();
  $('venue-closure-table').hidden = true;
  $('venue-score-table').hidden = true;
  $('venue-score-rows').replaceChildren();
  if (panel.hidden) { closeVenueDepartures(); venueReport.update(null); venueDebrief.update(null); $('venue-closure-summary').textContent = ''; return; }
  if (loading || batch === null) {
    closeVenueDepartures();
    venueReport.update(null); venueDebrief.update(null);
    $('venue-closure-summary').textContent = loading ? '正在讀取選定的結束批次…' : '目前沒有已結束的全館批次。';
    return;
  }
  if (!Array.isArray(batch?.sessions) || !batch.sessions.length || batch.sessions.length > 5
    || !Number.isFinite(Date.parse(batch.recordedAtUtc))
    || batch.sessions.some(session => typeof session?.sessionId !== 'string' || typeof session.missionName !== 'string'
      || !Array.isArray(session.roomIds) || !session.roomIds.length || session.roomIds.length > 5
      || !session.roomIds.every(id => Number.isInteger(id) && id >= 1 && id <= 5)
      || !Object.hasOwn(archiveNames, session.combat) || !Object.hasOwn(archiveNames, session.world))) {
    closeVenueDepartures();
    venueReport.update(null); venueDebrief.update(null);
    $('venue-closure-summary').textContent = '暫時無法確認全館封存狀態。';
    return;
  }
  if (departureReview && !batch.sessions.some(session => venueDepartureScope(batch, session) === departureReview.scope)) closeVenueDepartures();
  $('venue-closure-summary').textContent = `${new Date(batch.recordedAtUtc).toLocaleString('zh-TW')} · 請等遊戲伺服器完成玩家戰績傳送與收尾。`;
  const sessions = [...batch.sessions].sort((a, b) => a.roomIds[0] - b.roomIds[0]);
  const receipts = venueDebriefRooms(batch, report.debriefReceipts);
  venueDebrief.update(batch, receipts);
  const replayRooms = sessions.filter(session => session.roomIds.length === 1 && session.world === 'Sealed'
    && typeof session.replay?.streamId === 'string' && Number.isSafeInteger(session.replay.throughSequence)
    && session.replay.throughSequence > 0).map(session => ({ roomId: session.roomIds[0], sessionId: session.sessionId,
    streamId: session.replay.streamId, throughSequence: session.replay.throughSequence, complete: true, mode: 'replay' }));
  const venue = replayRooms.length > 1 && typeof batch.requestId === 'string' ? { requestId: batch.requestId, rooms: replayRooms } : null;
  const linkedPlan = sessions.length === 1 && sessions[0].roomIds.length === 5
    && sessions[0].roomIds.every((room, index) => room === index + 1);
  const independentPlan = sessions.length === 5
    && sessions.every((session, index) => session.roomIds.length === 1 && session.roomIds[0] === index + 1)
    && new Set(sessions.map(session => session.sessionId)).size === 5;
  if (typeof batch.requestId === 'string' && (linkedPlan || independentPlan)) {
    archivedPlan = { requestId: batch.requestId, mode: linkedPlan ? 'Linked' : 'IndependentSet',
      sessions: sessions.map(({ sessionId, missionId, missionName }) => ({ sessionId, missionId, missionName })) };
    restore.hidden = false;
    restore.disabled = state.busy || !!state.pending;
  }
  for (const session of batch.sessions) {
    const button = element('button', '查看場次', 'quiet small');
    button.type = 'button';
    button.addEventListener('click', () => {
      if (!master() || state.busy || state.pending) return;
      $('include-ended').checked = true;
      void selectSession(session.sessionId);
    });
    const actions = element('div', undefined, 'button-row');
    actions.append(button);
    const replay = session.replay;
    if (['Waiting', 'Sealed'].includes(session.world) && typeof replay?.streamId === 'string'
      && Number.isSafeInteger(replay.throughSequence) && replay.throughSequence > 0) {
      const complete = session.world === 'Sealed';
      const open = element('button', complete ? '回放原場次' : '回放已保存片段', 'quiet small');
      open.type = 'button'; open.dataset.venueReplay = session.sessionId;
      open.addEventListener('click', () => {
        if (!master() || state.busy || state.pending) return;
        tab('world', { mode: 'replay', sessionId: session.sessionId, streamId: replay.streamId, complete,
          throughSequence: replay.throughSequence, roomId: session.roomIds.length === 1 ? session.roomIds[0] : null,
          venue: complete && session.roomIds.length === 1 ? venue : null });
      });
      actions.append(open);
      const departureScope = venueDepartureScope(batch, session);
      if (departureScope) {
        const departures = element('button', `查看離場玩家戰績（${session.rosterDepartureCount}）`, 'quiet small');
        departures.type = 'button';
        departures.addEventListener('click', () => void openVenueDepartures(batch, session, departureScope));
        actions.append(departures);
      }
      const { trackingBegin, participationBegin } = session;
      const begin = trackingBegin && participationBegin ? null : trackingBegin ?? participationBegin;
      const participation = begin === participationBegin;
      const anchor = begin?.frame;
      if (typeof begin?.requestId === 'string' && begin.requestId !== batch.requestId
        && (begin.playersPerRoom === undefined || [1, 2].includes(begin.playersPerRoom))
        && Number.isSafeInteger(begin.appliedAtSequence) && begin.appliedAtSequence > 1 && begin.appliedAtSequence < session.appliedAtSequence
        && anchor?.streamId === replay.streamId && Number.isSafeInteger(anchor.worldSequence)
        && anchor.worldSequence > 0 && anchor.worldSequence <= replay.throughSequence
        && Number.isSafeInteger(anchor.elapsedMilliseconds) && anchor.elapsedMilliseconds >= 0) {
        const witness = element('button', participation ? '回看有效姿態開場' : '回看追蹤開場', 'quiet small');
        witness.type = 'button';
        witness.dataset[participation ? 'venueParticipationBegin' : 'venueTrackingBegin'] = session.sessionId;
        witness.title = `原開場畫格 ${anchor.worldSequence}`;
        witness.addEventListener('click', () => {
          if (!master() || state.busy || state.pending) return;
          tab('world', { mode: 'replay', sessionId: session.sessionId, streamId: replay.streamId, complete: false,
            throughSequence: anchor.worldSequence, roomId: session.roomIds.length === 1 ? session.roomIds[0] : null,
            venue: complete && session.roomIds.length === 1 ? venue : null,
            witness: { kind: participation ? 'participation-begin' : 'tracking-begin',
              requestId: begin.requestId, appliedAtSequence: begin.appliedAtSequence, elapsedMilliseconds: anchor.elapsedMilliseconds,
              roomIds: session.roomIds, playersPerRoom: begin.playersPerRoom, archiveComplete: complete, archiveThroughSequence: replay.throughSequence } });
        });
        actions.append(witness);
      }
    }
    const debrief = element('div');
    for (const roomId of session.roomIds) {
      const count = receipts.get(roomId);
      let text = session.world === 'NoSource' ? '沒有遊戲來源' : session.world === 'SourceMismatch' ? '來源待核對'
        : session.combat !== 'Sealed' || session.world !== 'Sealed' ? '等待雙封存' : '回條狀態未取得';
      if (count?.confirmedCount != null) text = count.rosterCount === 0 ? '名冊無玩家'
        : `已確認 ${count.confirmedCount}／${count.rosterCount} 席`
          + (count.confirmedCount < count.rosterCount ? ` · ${count.rosterCount - count.confirmedCount} 席未確認` : '');
      const status = element('div', session.roomIds.length > 1 ? `房間 ${roomId} · ${text}` : text);
      status.dataset.venueDebriefRoom = roomId;
      debrief.append(status);
      if (venueDebrief.available(roomId)) {
        const seats = element('button', '查看席位', 'quiet small');
        seats.type = 'button'; seats.dataset.venueDebriefSeats = roomId;
        seats.setAttribute('aria-label', `查看房間 ${roomId} 的戰績回條`);
        seats.addEventListener('click', () => venueDebrief.open(roomId));
        debrief.append(seats);
      }
    }
    const result = row([`房間 ${session.roomIds.join('、')}`, session.missionName, archiveNames[session.combat], archiveNames[session.world], debrief, actions]);
    result.dataset.venueClosureSession = session.sessionId;
    rows.append(result);
  }
  $('venue-closure-table').hidden = false;
  const battle = renderVenueScores(batch, report.scores, report.readyRoomScores);
  venueReport.update(batch, battle?.totals, receipts, battle?.rooms);
}
function venueDebriefRooms(batch, summary) {
  if (!summary || typeof batch.requestId !== 'string' || summary.requestId !== batch.requestId
    || !Array.isArray(summary.rooms)) return new Map();
  const expected = new Map(batch.sessions.flatMap(session => session.roomIds.map(room => [room, session])));
  const rooms = new Map();
  if (summary.rooms.length !== expected.size) return rooms;
  for (const room of summary.rooms) {
    const session = expected.get(room?.roomId);
    if (!session || session.sessionId !== room.sessionId || rooms.has(room.roomId)
      || !Number.isInteger(room.rosterCount) || room.rosterCount < 0 || room.rosterCount > 5) return new Map();
    const sealed = session.combat === 'Sealed' && session.world === 'Sealed';
    if (sealed ? !Number.isInteger(room.confirmedCount) || room.confirmedCount < 0 || room.confirmedCount > room.rosterCount
      : room.confirmedCount !== null) return new Map();
    rooms.set(room.roomId, room);
  }
  return rooms;
}
function renderVenueScores(batch, scores, readyScores) {
  const ready = session => ['Sealed', 'NoSource'].includes(session.combat);
  const partial = batch.sessions.some(session => !ready(session));
  if (partial ? scores != null : readyScores != null) return;
  const data = partial ? readyScores : scores;
  if (!data || typeof batch.requestId !== 'string' || data.requestId !== batch.requestId || !Array.isArray(data.rooms)) return;
  const allRooms = batch.sessions.flatMap(session => session.roomIds.map(id => [id, session]));
  if (new Set(allRooms.map(([id]) => id)).size !== allRooms.length) return;
  const expected = new Map(allRooms.filter(([, session]) => ready(session)).map(([id, session]) => [id, session.sessionId]));
  const actual = new Map(data.rooms.map(score => [score?.roomId, score]));
  const keys = venueScoreFields;
  const identity = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
  const valid = totals => totals && keys.every(key => Number.isSafeInteger(totals[key]) && totals[key] >= 0)
    && Number.isFinite(totals.accuracyPercent) && totals.accuracyPercent >= 0 && totals.accuracyPercent <= 100;
  if (data.rooms.length !== expected.size || actual.size !== expected.size
    || (partial ? Object.hasOwn(data, 'total') : !valid(data.total))
    || data.rooms.some(score => !Number.isInteger(score?.roomId) || score.roomId < 1 || score.roomId > 5
      || !identity.test(score.sessionId) || expected.get(score.roomId) !== score.sessionId
      || !valid(score.totals))) return;
  const scoreRow = (label, totals) => row([label, ...keys.map(key => totals[key]), totals.accuracyPercent + '%']);
  const ordered = [...actual.values()].sort((a, b) => a.roomId - b.roomId);
  const rows = allRooms.sort(([a], [b]) => a - b).map(([id]) => {
    const label = '房間 ' + id, score = actual.get(id);
    const item = score ? scoreRow(label, score.totals) : row([label, '等待戰鬥封存']);
    if (score) {
      const downloadRoom = element('button', '下載 CSV', 'quiet small');
      downloadRoom.type = 'button'; downloadRoom.dataset.venueRoomReport = id;
      downloadRoom.setAttribute('aria-label', `下載房間 ${id} 的原批次戰績 CSV`);
      item.insertCell().append(downloadRoom);
    } else item.lastElementChild.colSpan = keys.length + 2;
    item.dataset.venueScoreRoom = id;
    return item;
  });
  if (!partial) {
    const total = scoreRow('本批合計', scores.total);
    total.insertCell();
    rows.push(total);
  }
  $('venue-score-rows').replaceChildren(...rows);
  $('venue-score-table').hidden = false;
  return { rooms: ordered, totals: partial ? null : { ...scores, rooms: ordered } };
}
function row(cells) { const tr = element('tr'); for (const value of cells) { const td = element('td'); if (value instanceof Node) td.append(value); else td.textContent = value; tr.append(td); } return tr; }
function emptyTable(id, columns, message) { const tr = element('tr'), td = element('td', message, 'empty-cell'); td.colSpan = columns; tr.append(td); $(id).replaceChildren(tr); }
function renderStatistics() {
  const linked = state.session?.mode === 'Linked';
  const room = report.roomId(), players = report.players();
  $('statistics-scope').hidden = !linked;
  $('statistics-room-column').hidden = !linked;
  const status = $('statistics-scope-status');
  const text = linked ? `${room === null ? '全場' : '房間 ' + room} · ${players.length} 名玩家戰績` : '';
  if (status.textContent !== text) status.textContent = text;
  const rows = players.map(player => row([player.name, player.ammoUsed, player.kills, player.damageTaken,
    player.hitsReceived, player.accuracyPercent + '%', player.health, ...(linked ? [player.roomId] : [])]));
  if (rows.length) $('statistics').replaceChildren(...rows);
  else emptyTable('statistics', linked ? 8 : 7, room === null ? '加入玩家後顯示統計' : '此房尚無玩家戰績');
}
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
  const rosterRoom = $('roster-room'), rosterFilter = $('roster-room-filter');
  const visibleRooms = session.roomIds.filter(ownsRoom);
  fillOptions('roster-room', [['', '全部房間'], ...visibleRooms.map(id => [String(id), `房間 ${id}`])],
    rosterRoom.dataset.preferred ?? rosterRoom.value);
  delete rosterRoom.dataset.preferred;
  rosterFilter.hidden = visibleRooms.length < 2;
  const focused = document.activeElement;
  const focusedAdmission = focused?.matches('#roster [data-roster-seat]')
    ? focused.querySelector('[data-admission]')?.dataset.admission : null;
  $('roster').replaceChildren(...session.players.map(player => {
    const actions = element('div', undefined, 'button-row');
    for (const [kind, label, action, cls] of [['ticket', '下載連線檔', () => downloadTicket(player), 'secondary'], ['remove', '移除', () => removePlayer(player), 'danger']]) {
      const button = element('button', label, cls + ' small'); button.type = 'button'; button.dataset.playerRoom = player.roomId;
      button.dataset.playerAction = kind;
      button.addEventListener('click', () => runSession(action)); actions.append(button);
    }
    const participation = element('span', '等待本次入場同步'); participation.dataset.readinessPlayer = player.id; participation.dataset.admission = player.admissionId;
    const item = row([player.name, `${player.roomId} / ${player.seat + 1}`, player.headset === 'Quest3' ? 'Quest 3' : 'VIVE XR', participation, actions]);
    item.dataset.rosterRoom = player.roomId;
    item.dataset.rosterSeat = player.seat + 1;
    item.tabIndex = -1;
    return item;
  }));
  if (!session.players.length) emptyTable('roster', 5, '尚未加入玩家');
  filterRoster();
  if (archiveId.test(focusedAdmission ?? '')) {
    $('roster').querySelector(`tr:not([hidden]) [data-admission="${focusedAdmission}"]`)?.closest('tr')?.focus({ preventScroll: true });
  }
  connections.update();
  $('statistics-origin').textContent = statistics.origin === 'Simulation' ? '模擬資料' : statistics.origin === 'GameServer' ? '遊戲伺服器回報' : '尚無戰鬥資料';
  $('telemetry-status').hidden = !session.combatStream;
  $('telemetry-status').textContent = statistics.pendingTelemetry ? '已要求結束；等待遊戲伺服器補送事件並封存，統計尚未確認完整。'
    : session.combatStream?.sealed ? '戰鬥事件已全部確認並封存。' : '戰鬥資料接收中；目前統計將隨資料更新。';
  renderStatistics();
  const eventNames = { Created: '建立場次', PlayerJoined: '玩家加入', PlayerLeft: '玩家離開', ControlApplied: '套用控制命令', CombatRecorded: '戰鬥事件', CombatStreamOpened: '綁定戰鬥來源', StreamCombatRecorded: '接收戰鬥事件', CombatStreamSealed: '戰鬥事件封存' };
  $('event-list').replaceChildren(...events.slice().reverse().map(event => {
    const item = element('li'); item.append(element('span', time(event.recordedAtUtc), 'event-time'), element('span', `#${event.sequence} ${eventNames[event.kind] || event.kind}`), element('span', event.actor?.id || '舊版紀錄', 'event-actor')); return item;
  }));
}
function filterRoster() {
  const room = $('roster-room').value;
  let shown = 0;
  for (const item of $('roster').querySelectorAll('[data-roster-room]')) {
    item.hidden = !!room && item.dataset.rosterRoom !== room;
    if (!item.hidden) shown++;
  }
  $('roster-filter-empty').hidden = !room || shown !== 0 || !state.session?.players.length;
  const capacity = room ? 5 : (state.session?.roomIds.length ?? 0) * 5;
  $('player-count').textContent = (room ? `房間 ${room} · ` : '') + `${shown} / ${capacity} 人（名冊）`;
  updateRoomTicketButtons();
  readiness.update();
}
function roomTicketSource(session, roomId) {
  return roomReadiness.ticketDestination(state.rooms.find(room => room.id === roomId), session);
}
function roomTicketProblem(session, roomId, destination) {
  const source = roomTicketSource(session, roomId);
  if (source?.live == null) return '';
  const { address, port } = source.endpoint;
  if (!source.live) return `公告端點 ${address}:${port} · 遊戲來源暫未確認，暫停配票。`;
  return destination && (address !== destination.address || port !== destination.port)
    ? `公告端點為 ${address}:${port}。請套用場次連線設定。` : '';
}
function updateRoomTicketButtons() {
  const session = state.session, roomId = Number($('roster-room').value), selectedRoom = Number($('ticket-room').value);
  const button = $('download-roster-room-tickets');
  const status = $('roster-ticket-destination');
  const destination = configuredTicketDestination();
  const locked = state.busy || !!state.pending;
  const sources = new Map(session?.roomIds.map(id => [id, roomTicketSource(session, id)]));
  for (const seat of $('roster').querySelectorAll('[data-player-action=ticket]')) {
    const room = Number(seat.dataset.playerRoom), source = sources.get(room);
    seat.disabled = locked || !ownsRoom(room) || !canIssueTicket(session, room) || source?.live === false;
    seat.title = source?.live === false ? '原遊戲來源暫未確認，暫停配票。'
      : source?.live === true ? `使用公告端點 ${source.endpoint.address}:${source.endpoint.port}` : '';
  }
  $('download-room-tickets').disabled = locked || !selectedRoom || !canIssueTicket(session, selectedRoom)
    || !!roomTicketProblem(session, selectedRoom, destination);
  button.hidden = !session?.roomIds.includes(roomId) || !ownsRoom(roomId);
  const problem = button.hidden ? '' : roomTicketProblem(session, roomId, destination);
  button.disabled = button.hidden || locked || !canIssueTicket(session, roomId)
    || !destination || !!problem || !session.players.some(player => player.roomId === roomId);
  if (!button.hidden) button.textContent = `下載房間 ${roomId} 連線檔 ZIP`;
  status.hidden = button.hidden;
  const text = button.hidden ? '' : problem || (destination ? `配票端點 ${destination.address}:${destination.port}`
    : '請先設定下方的遊戲伺服器 IPv4 與連線埠。');
  if (status.textContent !== text) status.textContent = text;
}
$('roster-room').addEventListener('change', filterRoster);
for (const id of ['game-address', 'game-port']) $(id).addEventListener('input', updateRoomTicketButtons);
function environment(prefix) { return { mode: prefix === 'live' ? state.session.environment.mode : $('draft-mode').value, weather: $(prefix + '-weather').value, timeOfDay: $(prefix + '-time').value, lightning: $(prefix + '-lightning').checked }; }
function enemies(prefix) { return { count: Number($(prefix + '-count').value), behavior: $(prefix + '-behavior').value, autoAttack: $(prefix + '-auto-attack').checked }; }
function setEnvironment(prefix, value) { $(prefix + '-mode').value = value.mode; $(prefix + '-weather').value = value.weather; $(prefix + '-time').value = value.timeOfDay; $(prefix + '-lightning').checked = value.lightning; }
function setEnemies(prefix, value) { $(prefix + '-count').value = value.count; $(prefix + '-behavior').value = value.behavior; $(prefix + '-auto-attack').checked = value.autoAttack; }
function loadLiveSetting(kind) {
  if (!state.session) return;
  const sequence = state.settingRevisions?.[kind];
  if (kind === 'environment') setEnvironment('live', state.session.environment);
  else setEnemies('live', state.session.enemies);
  liveSettingDrafts[kind] = { edited: false, sequence: Number.isSafeInteger(sequence) && sequence > 0 && sequence <= state.session.sequence ? sequence : null };
}
function applyLiveSetting(kind, action, value) {
  const expectedSettingSequence = liveSettingDrafts[kind]?.sequence;
  if (expectedSettingSequence) return command(action, { [kind]: value, expectedSettingSequence }, null);
}
function loadClock() { if (state.session) { $('clock-auto-end').checked = state.session.missionClock?.autoEnd === true; state.clockSequence = state.session.sequence; } }
function matchesPreparedSession(session, mode, roomIds, expected) {
  const mission = session?.mission;
  if (!archiveId.test(session?.id) || session.mode !== mode || !Array.isArray(session.roomIds)
    || session.roomIds.length !== roomIds.length || !roomIds.every((roomId, index) => session.roomIds[index] === roomId)
    || mission?.id !== expected.id || mission.schemaVersion !== expected.schemaVersion || mission.createdAtUtc !== expected.createdAtUtc)
    return false;
  return matchesMissionDefinition(mission.definition, expected.definition);
}
function matchesMissionDefinition(actual, original, coordinatesMatch = (saved, expected) => saved === expected) {
  return actual?.name === original.name && actual.briefing === original.briefing && actual.durationSeconds === original.durationSeconds
    && ['mode', 'weather', 'timeOfDay', 'lightning'].every(field => actual.environment?.[field] === original.environment[field])
    && ['count', 'behavior', 'autoAttack'].every(field => actual.enemies?.[field] === original.enemies[field])
    && Array.isArray(actual.props) && actual.props.length === original.props.length
    && original.props.every((prop, index) => matchesMissionProp(actual.props[index], prop, coordinatesMatch));
}
function matchesMissionProp(saved, draft, coordinatesMatch) {
  return saved && draft && saved.assetId === draft.assetId && coordinatesMatch(saved.yawDegrees, draft.yawDegrees)
    && ['x', 'y', 'z'].every(axis => coordinatesMatch(saved.position?.[axis], draft.position[axis]));
}
// The API stores positions and angles as Single and may return a shorter decimal spelling.
function matchesSavedCoordinate(saved, expected) {
  const stored = Math.fround(expected);
  return Number.isFinite(expected) && Number.isFinite(saved) && Number.isFinite(stored) && Math.fround(saved) === stored;
}
function renderIndependentReceipt(sessions = [], versions = []) {
  const rows = sessions.map((session, index) => {
    const row = element('tr'), title = element('th', `房間 ${index + 1}`);
    const { name, durationSeconds, environment, enemies } = session.mission.definition;
    title.scope = 'row'; row.dataset.missionId = session.mission.id;
    row.append(title, element('td', `${name} · 第 ${versions[index].number} 版`), element('td', `${environment.mode} · ${durationSeconds} 秒`),
      element('td', venueClimateText(environment)), element('td', missionEnemyText(enemies)), element('td', session.id));
    return row;
  });
  $('launch-independent-receipt-rows').replaceChildren(...rows);
  $('launch-independent-receipt').hidden = rows.length === 0;
}
async function createSession() {
  if (state.pending) return;
  const plan = launchPlan();
  if (plan.mixed && !roomPlan.ready()) { notify('請先選取五房各自的保存版本並完成場地檢查。', true); return; }
  if (!placement.canLaunch()) { placement.scheduleLaunch(); notify('請先完成保存版本的場地檢查，再建立新場次。', true); return; }
  if (!plan.revision || !plan.available) { notify('請選取已保存的任務及空閒房間。', true); return; }
  const independentSet = plan.body.mode === 'IndependentSet';
  const revisions = plan.mixed ? roomPlan.revisions() : independentSet ? plan.body.roomIds.map(() => plan.revision) : [plan.revision];
  const versions = structuredClone(revisions.map(({ mission, number }) => ({ mission, number })));
  if (plan.mixed) {
    const summary = versions.map(({ mission, number }, index) => {
      const { name, environment, enemies, durationSeconds } = mission.definition;
      return `房間 ${index + 1}　${name} · 第 ${number} 版 · ${environment.mode} · ${durationSeconds} 秒 · ${venueClimateText(environment)} · ${missionEnemyText(enemies)}`;
    });
    if (!confirm(`依下列保存版本建立五個獨立準備場次？\n\n${summary.join('\n')}`)) return;
  }
  state.pending = { kind: independentSet ? 'create-set' : 'create', path: independentSet ? '/sessions/independent-set' : '/sessions',
    method: 'POST', requestId: uuid(), versions, body: plan.mixed ? { rooms: versions.map(({ mission }, index) => ({ roomId: index + 1, missionId: mission.id })) }
      : independentSet ? { missionId: plan.body.missionId } : plan.body };
  await sendPending();
}
async function command(action, extra = {}, expectedSequence = state.session.sequence) {
  if (state.pending) return;
  if (action === 'End' && !confirm(`結束房間 ${state.session.roomIds.join('、')} 的場次「${state.session.mission.definition.name}」並釋放房間？歷史與統計會保留。`)) return;
  state.pending = { kind: 'command', path: '/sessions/' + state.session.id + '/commands', method: 'POST', body: { commandId: uuid(), action, expectedSequence, ...extra } };
  await sendPending();
}
function pauseParticipation(roomId, sessionId, mode) {
  const target = roomReadiness.trackingPause(roomId, mode);
  if (state.busy || state.pending || target?.sessionId !== sessionId) return;
  const reason = mode === 'VR' ? '姿態中斷' : '追蹤中斷';
  const action = target.linked ? '暫停五房合併場次，讓所有房間一起暫停'
    : mode === 'VR' ? '暫停本房檢查席位' : '暫停本房進行重新對位';
  const scope = `房間 ${roomId} 的${reason}已確認。要${action}嗎？`;
  if (!confirm(scope)) return;
  void run(async () => {
    if (state.pending || !state.rooms.some(room => room.id === roomId && room.sessionId === sessionId)) return;
    const field = mode === 'VR' ? 'vrParticipationRoomId' : 'mrTrackingRoomId';
    state.pending = { kind: 'participation-pause', path: `/sessions/${sessionId}/commands`, method: 'POST', sessionId, mode,
      body: { commandId: uuid(), action: 'Pause', expectedSequence: target.sequence, [field]: roomId } };
    await sendPending();
  });
}
function resumeVrParticipation(roomId, sessionId) {
  const target = roomReadiness.vrResume(roomId);
  if (state.busy || state.pending || target?.sessionId !== sessionId) return;
  if (!confirm(target.linked ? '五房的存活席位姿態已確認。要一起繼續合併場次嗎？'
    : `房間 ${roomId} 的存活席位姿態已確認。要繼續本房嗎？`)) return;
  void run(async () => {
    if (state.pending || !state.rooms.some(room => room.id === roomId && room.sessionId === sessionId)) return;
    state.pending = { kind: 'participation-resume', path: `/sessions/${sessionId}/commands`, method: 'POST', sessionId,
      body: { commandId: uuid(), action: 'Resume', expectedSequence: target.sequence } };
    await sendPending();
  });
}
async function sendPending() {
  const pending = state.pending, epoch = state.epoch;
  if (!pending) return;
  try {
    const missionSave = pending.kind === 'mission-create' || pending.kind === 'mission-revise';
    const response = await api(pending.path, pending.method, pending.body, pending.requestId, pending.admissionId, missionSave ? 'mission-save' : 'json');
    if (state.pending !== pending) return;
    if (pending.kind === 'command' && pending.body.action === 'SetRoomAlignment' &&
        (response?.commandId !== pending.body.commandId || `/sessions/${response?.session?.id}/commands` !== pending.path
          || typeof response?.duplicate !== 'boolean' || response.appliedAtSequence !== pending.body.expectedSequence + 1
          || !Number.isSafeInteger(response.session.sequence) || response.session.sequence < response.appliedAtSequence
          || venueMissionRooms.some(room => {
            const key = `room${room}`;
            return (response.session.roomAlignment?.[key] ?? null) !== (pending.body.roomAlignment[key] ?? null);
          }))) throw new Error('Incomplete room alignment receipt');
    const roomPolicy = pending.body?.roomEnemyPolicy;
    const expectedSetting = pending.body?.expectedSettingSequence ?? roomPolicy?.expectedPolicySequence;
    if (expectedSetting != null) {
      const sequence = response?.appliedAtSequence, session = response?.session?.id;
      if (response?.commandId !== pending.body.commandId || '/sessions/' + session + '/commands' !== pending.path
        || !Number.isSafeInteger(sequence) || sequence <= expectedSetting)
        throw new Error('Setting command receipt mismatch');
      if (roomPolicy && roomEnemyDraft?.key === session + '/' + roomPolicy.roomId) roomEnemyDraft.sequence = sequence;
    }
    if (missionSave) {
      if ((pending.accepted && response.id !== pending.accepted) || response.schemaVersion !== 1 || !Number.isFinite(Date.parse(response.createdAtUtc))
        || !matchesMissionDefinition(response.definition, pending.body, matchesSavedCoordinate)) throw new MissionVersionMismatch();
      pending.accepted = response.id;
      const selectedLaunch = commonLaunchRevision();
      const parent = pending.parent;
      const revision = await api(`/missions/${response.id}/version`);
      if (epoch !== state.epoch) return;
      requireMissionVersion(revision, response.id, parent?.seriesId ?? response.id, (parent?.number ?? 0) + 1);
      if (revision.previousId !== (parent?.mission.id ?? null) || revision.mission.schemaVersion !== response.schemaVersion
        || revision.mission.createdAtUtc !== response.createdAtUtc || !matchesMissionDefinition(revision.mission.definition, response.definition))
        throw new MissionVersionMismatch();
      const history = await api(`/missions/${response.id}/history`);
      if (epoch !== state.epoch) return;
      requireMissionHistory(history, revision.seriesId, revision.number);
      await refreshData(epoch);
      if (epoch !== state.epoch) return;
      if (!await rememberHead(history, epoch)) return;
      if (!pending.restoredFrom) {
        state.draftBase = revision; state.draftChanged = false; state.draftSavedAt = response.createdAtUtc;
      }
      state.history = history;
      clearMissionComparison();
      state.launchPinned = selectedLaunch ?? (pending.restoredFrom ? null : revision);
      const head = state.catalog.find(row => row.seriesId === revision.seriesId);
      const resetSearch = head && !matchesMissionSearch(head, missionSearchQuery());
      if (resetSearch) $('mission-search').value = '';
      renderHistory(response.id); missionOptions(state.launchPinned?.mission.id, head?.mission.id ?? history.headId); draftStatus();
      state.pending = null;
      const savedMessage = pending.restoredFrom ? `已將第 ${pending.restoredFrom} 版內容保存為第 ${revision.number} 版。`
        : '任務保存已確認，原版本與既有場次保持不變。可選擇此版本開場。';
      notify(savedMessage + (resetSearch ? ' 已清除搜尋，任務清單已選取此任務的最新版。' : '')); return;
    }
    if (pending.kind === 'venue-plan-save') {
      if (!validSavedVenuePlan(response) || response.id !== pending.requestId || !matchesVenuePlan(response.plan, pending.body))
        throw new MissionVersionMismatch('無法核對五房配置的保存回條。可使用「重試確認結果」確認原配置。');
      savedVenuePlans = [response, ...(savedVenuePlans ?? []).filter(row => row.id !== response.id)];
      renderSavedVenuePlans(response.id);
      if (venueMissionReview?.saved) clearVenueMissionReview();
      $('venue-plan-name').value = '';
      $('venue-plan-status').textContent = `已保存「${response.plan.name}」。`;
      state.pending = null;
      notify('已確認五房配置保存。');
      return;
    }
    if (pending.kind === 'venue-roster-join') {
      const { seats } = pending.body, rows = response?.admissions;
      if (typeof response?.duplicate !== 'boolean' || !Array.isArray(rows) || rows.length !== seats.length
          || rows.some((row, index) => {
            const seat = seats[index], player = row?.player;
            return row?.sessionId !== seat.sessionId || row?.requestId !== seat.requestId
              || !Number.isSafeInteger(row.appliedAtSequence) || row.appliedAtSequence < 2
              || player?.id !== seat.playerId || player?.name !== seat.name || player?.roomId !== seat.roomId
              || player?.seat !== seat.seat || player?.headset !== seat.headset || !archiveId.test(player?.admissionId);
          }) || new Set(rows.map(row => row.player.admissionId)).size !== rows.length)
        throw new MissionVersionMismatch('無法核對名冊登記回條。可使用「重試確認結果」確認原席位。');
      venueRoster.accepted(seats);
      state.pending = null;
      await refresh();
      if (state.epoch === epoch) notify(`已確認登記 ${seats.length} 位玩家。`);
      return;
    }
    if (pending.kind === 'create-set') {
      const sessions = response?.sessions;
      if (!Array.isArray(sessions) || sessions.length !== 5 || new Set(sessions.map(session => session?.id)).size !== 5
          || sessions.some((session, index) => !matchesPreparedSession(session, 'Independent', [index + 1], pending.versions[index].mission)))
        throw new MissionVersionMismatch('五房回條與原選定的任務或房間不符，建立結果未確認。');
      renderIndependentReceipt(sessions, pending.versions);
      $('include-ended').checked = sessions.some(session => session.state === 'Ended');
      resetSelection((sessions.find(session => session.state !== 'Ended') ?? sessions[0]).id);
    }
    if (pending.kind === 'create' && !matchesPreparedSession(response, pending.body.mode, pending.body.roomIds, pending.versions[0].mission))
      throw new MissionVersionMismatch('場次回條與原選定的任務或房間不符，建立結果未確認。');
    if (pending.kind === 'venue-phase') {
      const targets = pending.body.targets;
      if (response?.requestId !== pending.requestId || response.action !== pending.body.action || typeof response.duplicate !== 'boolean'
          || ['requireFullTracking', 'requireFullParticipation'].some(policy =>
            (response[policy] === undefined ? false : response[policy]) !== (pending.body[policy] ?? false))
          || response.playersPerRoom !== pending.body.playersPerRoom
          || (pending.body.action === 'SetEnemies' && JSON.stringify(response.roomIds) !== JSON.stringify(pending.body.roomIds))
          || !Array.isArray(response.sessions) || response.sessions.length !== targets.length
          || targets.some(target => !response.sessions.some(row => row?.sessionId === target.sessionId
            && Number.isSafeInteger(row.appliedAtSequence) && (pending.body.action === 'Begin'
              ? row.appliedAtSequence === target.sessionSequence + 1
              : row.appliedAtSequence > Math.max(target.phaseSinceSequence, target.environmentSinceSequence ?? 0, target.enemiesSinceSequence ?? 0)))))
        throw new Error('Incomplete venue phase receipt');
    }
    if (['participation-pause', 'participation-resume'].includes(pending.kind) && (response?.commandId !== pending.body.commandId
        || response.session?.id !== pending.sessionId || typeof response.duplicate !== 'boolean'
        || response.appliedAtSequence !== pending.body.expectedSequence + 1
        || !Number.isSafeInteger(response.session.sequence) || response.session.sequence < response.appliedAtSequence))
      throw new Error('Incomplete participation transition receipt');
    state.pending = null;
    if (pending.kind === 'create') { $('include-ended').checked = response.state === 'Ended'; resetSelection(response.id); }
    if (pending.kind === 'command' && pending.body.action === 'End' && response.session.state === 'Ended') $('include-ended').checked = true;
    const venueBegun = pending.kind === 'venue-phase' && pending.body.action === 'Begin';
    if (venueBegun) confirmedVenueBegin = { requestId: pending.requestId, sessions: response.sessions.map(({ sessionId, appliedAtSequence }) =>
      ({ sessionId, appliedAtSequence, ...pending.beginRooms.get(sessionId) })) };
    const venueEnded = pending.kind === 'venue-phase' && pending.body.action === 'End';
    if (venueEnded) {
      $('include-ended').checked = true;
      confirmedVenueEnd = { requestId: pending.requestId, sessions: response.sessions.map(({ sessionId, appliedAtSequence }) =>
        ({ sessionId, appliedAtSequence, roomIds: pending.endRooms.get(sessionId) })) };
    }
    if (pending.kind === 'join') $('player-name').value = '';
    try { await refresh(); }
    catch (error) {
      if ((!venueEnded && !venueBegun) || state.epoch !== epoch) throw error;
      notify(venueEnded ? '全館結束已記錄。場次清單暫未更新，可查看本次結束批次。'
        : '全館管理命令已確認。場次清單暫未更新，本次開場觀戰會等待核對原場次。', true);
      return;
    }
    if (pending.kind === 'participation-pause') {
      notify(pending.mode === 'VR' ? '管理端已接受席位檢查暫停。請從房卡確認遊戲端已套用。'
        : '管理端已接受重新對位暫停。請從房卡確認遊戲端已套用。');
      return;
    }
    if (pending.kind === 'participation-resume') {
      notify('管理端已接受繼續。請從房卡確認最新執行中姿態。');
      return;
    }
    const action = pending.kind === 'command' ? pending.body.action : null;
    if (!liveSettingDrafts.environment?.edited || action === 'SetEnvironment') loadLiveSetting('environment');
    if (!liveSettingDrafts.enemies?.edited || action === 'SetEnemies') loadLiveSetting('enemies');
    loadClock();
    notify(venueEnded ? '全館結束已記錄。可查看本次結束批次。'
      : { create: '場次建立結果已確認。請核對目前狀態，再加入玩家及開始任務。', 'create-set': '五個獨立場次已確認。請由各房核對名冊及準備狀態。', join: '玩家加入操作已確認，請核對目前名冊；尚不代表頭盔在線。', leave: '玩家移出操作已確認，請核對目前名冊。', command: '控制命令已確認。', 'venue-phase': '全館管理命令已確認。可從各房快照核對遊戲端套用狀態。' }[pending.kind]);
  } catch (error) {
    if (error.code === 'room-enemy-policy-changed' && roomEnemyDraft) roomEnemyDraft.conflicted = true;
    if (pending.kind === 'create' && error.layout) placement.rejected(pending.body.missionId, pending.body.mode, error.layout);
    if (pending.kind === 'create-set' && error.layout) {
      const id = pending.body.rooms ? roomPlan.reject(error.roomId, error.layout) : pending.body.missionId;
      if (id) placement.rejected(id, 'Independent', error.layout);
    }
    if (state.pending === pending && !pending.accepted && error.status >= 400 && error.status < 500) {
      state.pending = null;
      if (pending.kind === 'venue-phase') setVenuePhase(null);
      if (pending.restoredFrom && error.status === 409)
        error.message = '無法接續已確認的任務版本。草稿已保留，請重新整理並核對最新版本後再試。';
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
function configuredTicketDestination() {
  const address = $('game-address').value.trim(), port = Number($('game-port').value);
  return validDestination(address, port) ? { address, port } : null;
}
function ticketDestination() {
  const destination = configuredTicketDestination();
  if (!destination) {
    notify('請輸入完整 IPv4 位址（例如 192.168.1.100）及 1024–65535 的連線埠。', true);
    return null;
  }
  return destination;
}
async function confirmTicketRoster(session, roomId, players, { wholeRoom = false, view }) {
  const applies = () => view === operationsViewEpoch && !$('operations-view').hidden
    && state.selected === session.id && state.session?.id === session.id && ownsRoom(roomId);
  if (!applies()) return false;
  const current = await api('/sessions/' + session.id);
  if (!applies()) return false;
  const roster = current.players.filter(player => player.roomId === roomId);
  if (current.id !== session.id || current.state === 'Ended' || current.environment.mode !== session.environment.mode
      || current.combatStream?.streamId !== session.combatStream?.streamId
      || current.roomAlignment?.[`room${roomId}`] !== session.roomAlignment?.[`room${roomId}`]
      || (wholeRoom && roster.length !== players.length)
      || !players.every(player => roster.some(row => row.id === player.id && row.admissionId === player.admissionId && row.seat === player.seat))) {
    notify('場次或名冊已變更，未下載連線檔。請重新整理後再配票。', true);
    return false;
  }
  return true;
}
async function downloadTicket(player) {
  const session = state.session;
  if (!canIssueTicket(session, player.roomId) || !ownsRoom(player.roomId)) return;
  if (!player.admissionId) throw new Error('控制台與 API 版本不一致，請更新服務並重新整理。');
  const source = roomTicketSource(session, player.roomId);
  if (source?.live === false) return;
  const managed = source?.live === true;
  const fallback = managed ? null : ticketDestination();
  if (!managed && !fallback) return;
  const view = operationsViewEpoch;
  const ticket = await api(`/sessions/${session.id}/players/${player.id}/join-ticket`, 'POST', undefined, undefined, player.admissionId);
  if (!matchesIssuedPlayerTicket(ticket, session.id, player)) {
    notify('無法核對本席原入場或票券效期，未下載連線檔。請重新配票。', true);
    return;
  }
  const destination = ticket.endpoint ?? fallback;
  if (!validDestination(destination?.address, destination?.port)
      || (managed && (destination.address !== source.endpoint.address || destination.port !== source.endpoint.port)))
    throw new Error('Published ticket destination does not match the current game source.');
  const config = { role: 'Client', address: destination.address, port: destination.port, joinTicket: ticket.ticket };
  if (session.environment.mode === 'MR') {
    if (ticket.roomAlignmentSha256 !== session.roomAlignment[`room${player.roomId}`])
      throw new Error('MR 連線檔的校正雜湊與目前場次不符。');
    config.roomAlignmentSha256 = ticket.roomAlignmentSha256;
  }
  if (!await confirmTicketRoster(session, player.roomId, [player], { view })) return;
  if (Date.parse(ticket.expiresAtUtc) <= Date.now()) { notify('票券已到期，請重新配票。', true); return; }
  download(`quest-player-${player.id}.json`, new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' }));
  notify(`玩家連線檔已產生，有效至 ${time(ticket.expiresAtUtc)}。請將各自檔案配置到對應玩家端。`);
}
function downloadRoomTickets(roomId) {
  const session = state.session;
  if (!canIssueTicket(session, roomId) || !ownsRoom(roomId) || !session.roomIds.includes(roomId)) return;
  const destination = ticketDestination();
  if (!destination) return;
  const problem = roomTicketProblem(session, roomId, destination);
  if (problem) { notify(problem, true); return; }
  const players = session.players.filter(player => player.roomId === roomId);
  if (!players.length) return;
  const admissions = players.map(player => ({ playerId: player.id, admissionId: player.admissionId }));
  const view = operationsViewEpoch;
  void runSession(async () => {
    const bundle = await api(`/sessions/${session.id}/rooms/${roomId}/join-ticket-bundle`, 'POST',
      { ...destination, players: admissions }, undefined, undefined, 'room-ticket-archive');
    if (!await confirmTicketRoster(session, roomId, players, { wholeRoom: true, view })) return;
    download(`room-${String(roomId).padStart(2, '0')}-connections.zip`, bundle);
    notify(`房間 ${roomId} 的 ${players.length} 份連線檔已產生。請按檔名席位個別交付，票券有效五分鐘。`);
  });
}

function resetDraft() {
  placement.clearTrial();
  propMove.reset();
  clearMissionComparison();
  clearMissionTemplate(); loadedText = null;
  $('mission-form').reset(); state.props = []; state.prop = -1; state.draftBase = null; state.draftChanged = false; state.draftSavedAt = ''; state.history = null;
  clearPropHistory();
  renderProps(); renderHistory(); draftStatus(); applyPermissions();
}
function confirmDraftDiscard(action) {
  return !state.draftChanged || confirm(`${action}將捨棄尚未儲存的任務修改。確定繼續？`);
}
function missionOptions(launch, edit) {
  const entries = state.catalog.map(row => [row.mission.id, `${row.mission.definition.name} · 第 ${row.number} 版`]);
  const pinned = state.launchPinned;
  const launchEntries = pinned && !entries.some(([id]) => id === pinned.mission.id) ? [...entries, [pinned.mission.id, `${pinned.mission.definition.name} · 第 ${pinned.number} 版（歷史）`]] : entries;
  fillOptions('launch-mission', launchEntries.length ? launchEntries : [['', '請先儲存任務']], launch);
  editMissionOptions(edit);
  placement.scheduleLaunch();
}
function missionSearchQuery() { return $('mission-search').value.trim().toLowerCase(); }
function matchesMissionSearch(row, query) {
  return !query || [row.mission.definition.name, row.mission.definition.briefing].some(text => text.toLowerCase().includes(query));
}
function editMissionOptions(selected, searchEdited = false) {
  const query = missionSearchQuery();
  const matches = state.catalog.filter(row => matchesMissionSearch(row, query));
  const entries = matches.map(row => [row.mission.id, `${row.mission.definition.name} · 第 ${row.number} 版`]);
  const select = $('edit-mission'), preferred = selected ?? select.value;
  // A refresh can rename the selected series out of the search while other results remain.
  const needsChoice = !searchEdited && (preferred ? !matches.some(row => row.mission.id === preferred)
    : select.selectedOptions[0]?.disabled);
  const empty = query ? '沒有符合的任務' : '尚無儲存任務';
  if (needsChoice || !entries.length) entries.unshift(['', entries.length ? '請重新選取任務' : empty]);
  fillOptions('edit-mission', entries, needsChoice ? '' : preferred);
  if (needsChoice) select.options[0].disabled = true;
  $('mission-search-status').hidden = !query;
  $('mission-search-status').textContent = query ? `找到 ${matches.length} 項任務，共 ${state.catalog.length} 項` : '';
}
function knownHeadNumber(seriesId) {
  return Math.max(state.catalog.find(row => row.seriesId === seriesId)?.number || 0, state.history?.seriesId === seriesId ? state.history.headNumber : 0);
}
class MissionVersionMismatch extends Error {
  constructor(message = '任務版本核對不符，已保留目前草稿。') { super(message); }
}
function requireMissionVersion(revision, id, seriesId, number) {
  if (!revision?.mission || revision.mission.id !== id || revision.seriesId !== seriesId || revision.number !== number
    || !readableMissionDefinition(revision.mission.definition))
    throw new MissionVersionMismatch();
}
function readableMissionDefinition(draft) {
  const env = draft?.environment, enemies = draft?.enemies;
  const coordinate = value => Number.isFinite(value) && Number.isFinite(Math.fround(value));
  return typeof draft?.name === 'string' && draft.name.length > 0 && draft.name.length <= 100
    && typeof draft.briefing === 'string' && draft.briefing.length <= 10000
    && Number.isInteger(draft.durationSeconds) && draft.durationSeconds >= 60 && draft.durationSeconds <= 14400
    && ['VR', 'MR'].includes(env?.mode) && typeof env.weather === 'string' && Object.hasOwn(weatherNames, env.weather)
    && ['Day', 'Night'].includes(env.timeOfDay) && typeof env.lightning === 'boolean'
    && Number.isInteger(enemies?.count) && enemies.count >= 0 && enemies.count <= 100
    && typeof enemies.behavior === 'string' && Object.hasOwn(behaviorNames, enemies.behavior) && typeof enemies.autoAttack === 'boolean'
    && Array.isArray(draft.props) && draft.props.length <= 500 && draft.props.every(prop => typeof prop?.assetId === 'string'
      && prop.assetId.length > 0 && prop.assetId.length <= 100
      && coordinate(prop.yawDegrees) && ['x', 'y', 'z'].every(axis => coordinate(prop.position?.[axis])));
}
function requireMissionHistory(history, seriesId, minimum) {
  if (history?.seriesId !== seriesId || typeof history.headId !== 'string' || !history.headId
    || !Number.isSafeInteger(history.headNumber) || history.headNumber < minimum || !Array.isArray(history.versions))
    throw new MissionVersionMismatch();
}
async function rememberHead(history, epoch, signal) {
  const index = state.catalog.findIndex(row => row.seriesId === history.seriesId), known = state.catalog[index];
  if (known && known.number >= history.headNumber) return epoch === state.epoch && !signal?.aborted;
  const revision = await api(`/missions/${encodeURIComponent(history.headId)}/version`, 'GET', undefined, undefined, undefined, 'json', signal);
  if (signal?.aborted || epoch !== state.epoch) return false;
  requireMissionVersion(revision, history.headId, history.seriesId, history.headNumber);
  const currentIndex = state.catalog.findIndex(row => row.seriesId === history.seriesId), current = state.catalog[currentIndex];
  if (current && current.number >= revision.number) return true;
  if (current?.mission.id === $('launch-mission').value) state.launchPinned = current;
  if (currentIndex < 0) state.catalog.push(revision); else state.catalog[currentIndex] = revision;
  state.missions = state.catalog.map(row => row.mission); return true;
}
function draftStatus() {
  const base = state.draftBase;
  const canMerge = master() && state.draftChanged && base && knownHeadNumber(base.seriesId) > base.number;
  $('merge-mission-head').hidden = !canMerge;
  let text = state.draftChanged ? '尚未儲存的修改' : state.draftSavedAt ? '已儲存於 ' + time(state.draftSavedAt) : base ? '已載入草稿' : '尚未儲存的草稿';
  if (base) {
    text += ` · 基於「${base.mission.definition.name}」第 ${base.number} 版`;
    const latest = knownHeadNumber(base.seriesId);
    if (latest > base.number) text += canMerge ? ` · 已有第 ${latest} 版，可合併到草稿或另存新任務`
      : ` · 已有第 ${latest} 版，修訂前請載入最新版，或另存新任務`;
  }
  $('draft-status').textContent = text;
}
function renderHistory(selected) {
  const history = state.history;
  $('mission-history').hidden = !history;
  fillOptions('mission-version', history ? [...history.versions].sort((a, b) => b.number - a.number).map(row => [row.id, `第 ${row.number} 版 · ${row.name} · ${new Date(row.createdAtUtc).toLocaleString('zh-TW')}`]) : [], selected);
  if (comparedVersion && comparedVersion.mission.id !== $('mission-version').value) clearMissionComparison();
  $('history-status').textContent = history ? `已讀取 ${history.versions.length} 版 · 本次查詢最新第 ${history.headNumber} 版` : '';
}
function requestDraft(version, mode = 'latest') {
  if (state.busy || $('missions-view').hidden) return;
  const request = draftLoad = new AbortController();
  void run(() => loadDraft(version, mode, request.signal), true, request.signal).finally(() => {
    if (draftLoad === request) draftLoad = null;
  });
}

async function loadDraft({ id, seriesId, number }, mode, signal) {
  const epoch = state.epoch;
  const older = mode === 'selected';
  const history = await api(`/missions/${id}/history`, 'GET', undefined, undefined, undefined, 'json', signal);
  if (signal.aborted || epoch !== state.epoch) return;
  requireMissionHistory(history, seriesId, number);
  const targetId = older ? id : history.headId;
  const revision = await api(`/missions/${encodeURIComponent(targetId)}/version`, 'GET', undefined, undefined, undefined, 'json', signal);
  if (signal.aborted || epoch !== state.epoch) return;
  requireMissionVersion(revision, targetId, seriesId, older ? number : history.headNumber);
  if (!await rememberHead(history, epoch, signal) || signal.aborted || epoch !== state.epoch) return;
  const mission = revision.mission;
  let draft = mission.definition, keepProps = false;
  if (mode === 'merge') {
    const base = state.draftBase;
    if (base?.mission.id !== id || revision.number <= base.number || knownHeadNumber(seriesId) !== revision.number)
      throw new MissionVersionMismatch();
    const local = draftDefinition(), merged = mergeMissionDraft(base.mission.definition, local, draft);
    if (merged.conflicts.length) {
      state.history = history; renderHistory(mission.id); draftStatus();
      notify(`雙方對「${merged.conflicts.join('、')}」的修改不同。可按「與目前草稿比較」查看第 ${revision.number} 版，或另存新任務。`, true);
      return;
    }
    draft = merged.definition;
    keepProps = draft.props === local.props;
  }
  fillDraft(draft, keepProps);
  state.draftBase = revision; state.draftChanged = mode === 'merge' && !matchesMissionDefinition(mission.definition, draft, matchesSavedCoordinate);
  state.draftSavedAt = ''; state.history = history;
  if (!history.versions.some(row => row.id === mission.id)) history.versions.push({ id: mission.id, number: revision.number, name: draft.name, createdAtUtc: mission.createdAtUtc });
  renderProps(); renderHistory(mission.id); missionOptions(undefined, history.headId); draftStatus();
  if (mode === 'merge') notify(state.draftChanged ? `草稿已合併第 ${revision.number} 版，核對後可保存為下一版。`
    : `目前修改已包含在第 ${revision.number} 版中。`);
}
function mergeMissionDraft(base, local, latest) {
  const conflicts = [];
  function choose(label, original, edited, published, equal = (a, b) => a === b) {
    if (equal(edited, published)) return edited;
    if (equal(edited, original)) return published;
    if (!equal(published, original)) conflicts.push(label);
    return edited;
  }
  const definition = structuredClone(latest);
  for (const [key, label] of Object.entries({ name: '任務名稱', briefing: '任務內容', durationSeconds: '任務時間' }))
    definition[key] = choose(label, base[key], local[key], latest[key]);
  const groups = { environment: { mode: '環境模式', weather: '天氣', timeOfDay: '日夜', lightning: '雷電' },
    enemies: { count: '敵軍數量', behavior: '敵軍行為', autoAttack: '自動攻擊' } };
  for (const [group, fields] of Object.entries(groups))
    for (const [key, label] of Object.entries(fields))
      definition[group][key] = choose(label, base[group][key], local[group][key], latest[group][key]);
  // Props have no stable IDs. Preserve ordering and compare the entire layout at saved precision.
  definition.props = choose('場景物件', base.props, local.props, latest.props,
    (a, b) => a.length === b.length && a.every((prop, i) => matchesMissionProp(prop, b[i], matchesSavedCoordinate)));
  return { definition, conflicts };
}
function fillDraft(draft, keepProps = false) {
  placement.clearTrial(); clearMissionComparison();
  closeTemplateComparison();
  propMove.reset();
  $('draft-name').value = draft.name; $('draft-briefing').value = draft.briefing; $('draft-duration').value = draft.durationSeconds;
  // Text controls normalize line endings. Keep the source text until that field is edited.
  loadedText = {
    name: { value: draft.name, shown: $('draft-name').value },
    briefing: { value: draft.briefing, shown: $('draft-briefing').value }
  };
  setEnvironment('draft', draft.environment); setEnemies('draft', draft.enemies);
  if (!keepProps) {
    state.props = structuredClone(draft.props); state.prop = state.props.length ? 0 : -1; clearPropHistory();
  }
}
function clearMissionTemplate(keepFile = false) {
  templateEpoch++; checkedTemplate = null;
  closeTemplateComparison();
  $('template-comparison').hidden = true;
  if (!keepFile) {
    $('mission-template-file').value = '';
    $('check-mission-template').disabled = true;
  }
  $('use-mission-template').disabled = true;
  $('mission-template-status').textContent = '';
}
async function checkMissionTemplate(file, epoch) {
  if (epoch !== templateEpoch) return;
  const result = await api('/mission-templates/check-file', 'POST', file);
  if (epoch !== templateEpoch || $('missions-view').hidden) return;
  const draft = result?.definition;
  if (result?.format !== missionTemplateFormat || result.version !== 1 || !readableMissionDefinition(draft))
    throw new MissionVersionMismatch('任務範本回應內容不完整或格式有誤，已保留目前草稿。');
  checkedTemplate = draft;
  $('template-comparison').hidden = false;
  $('mission-template-status').textContent = `「${draft.name}」 · ${draft.environment.mode} · ${draft.durationSeconds} 秒 · ${venueClimateText(draft.environment)} · ${missionEnemyText(draft.enemies)} · ${draft.props.length} 件物件。可載入為新草稿。`;
}
function useMissionTemplate() {
  if (!editable() || !checkedTemplate || !confirmDraftDiscard('載入任務範本')) return;
  const draft = checkedTemplate;
  fillDraft(draft);
  state.draftBase = null; state.draftChanged = true; state.draftSavedAt = ''; state.history = null;
  clearMissionTemplate(); renderProps(); renderHistory(); draftStatus(); applyPermissions();
  notify('已載入範本。核對場地及任務內容後，可儲存為新任務。');
}
function draftDefinition() {
  const name = $('draft-name').value, briefing = $('draft-briefing').value;
  return { name: loadedText?.name?.shown === name ? loadedText.name.value : name.trim(),
    briefing: loadedText?.briefing?.shown === briefing ? loadedText.briefing.value : briefing,
    durationSeconds: Number($('draft-duration').value),
    environment: environment('draft'), enemies: enemies('draft'), props: structuredClone(state.props) };
}
function canExportDraftTemplate() {
  return master() && !state.busy && (!state.pending
    || (['mission-create', 'mission-revise'].includes(state.pending.kind) && state.pending.restoredFrom === undefined));
}
function exportDraftTemplate() {
  if (!canExportDraftTemplate() || (!state.pending && !$('mission-form').reportValidity())) return;
  const definition = state.pending?.body ?? draftDefinition();
  if (!definition.name.trim()) { notify('請先輸入任務名稱。', true); return; }
  const invalid = definition.props.findIndex(prop => !prop.assetId.trim() || prop.assetId.length > 100
    || ![prop.position.x, prop.position.y, prop.position.z, prop.yawDegrees].every(value => Number.isFinite(Math.fround(value))));
  if (invalid !== -1) { notify(`請先修正物件 ${invalid + 1} 的素材代碼或座標。`, true); return; }
  const blob = new Blob([JSON.stringify({ format: missionTemplateFormat, version: 1, definition }, null, 2)], { type: 'application/json' });
  if (blob.size > missionTemplateFileLimit) { notify('草稿範本超過 512 KiB，請減少文字或物件。', true); return; }
  download('vr-mission-draft.json', blob);
  notify('已下載草稿範本。');
}
function clearMissionComparison() {
  if (!comparedVersion) return;
  comparedVersion = null;
  $('mission-comparison').hidden = true;
  $('mission-comparison-summary').textContent = '';
  $('mission-comparison-rows').replaceChildren();
  $('launch-compared-version').disabled = true;
  $('restore-compared-version').disabled = true;
}
async function compareMissionVersion(id) {
  const epoch = state.epoch, series = state.history?.seriesId;
  const selected = state.history?.versions.find(row => row.id === id);
  if (!selected) return;
  const revision = await api(`/missions/${id}/version`);
  if (epoch !== state.epoch || series !== state.history?.seriesId || id !== $('mission-version').value) return;
  requireMissionVersion(revision, id, series, selected.number);
  const saved = revision.mission.definition;
  const rows = missionDifferenceRows(saved, draftDefinition());
  comparedVersion = revision;
  $('mission-comparison-summary').textContent = `「${saved.name}」第 ${revision.number} 版 · ${rows.length ? `${rows.length} 項差異` : '與目前草稿相同'}`;
  $('mission-comparison-rows').replaceChildren(...rows);
  $('mission-comparison-table').hidden = rows.length === 0;
  $('mission-comparison').hidden = false;
}
function missionDifferenceRows(saved, draft) {
  const rows = [];
  function add(label, before, after) {
    if (before === after) return;
    const row = element('tr'), title = element('th', label);
    title.scope = 'row'; row.append(title);
    for (const value of [before, after]) {
      const cell = element('td'); cell.append(element('div', value === '' ? '（空白）' : value, 'briefing')); row.append(cell);
    }
    rows.push(row);
  }
  add('任務名稱', saved.name, draft.name);
  add('任務內容', saved.briefing, draft.briefing);
  add('任務時間', `${saved.durationSeconds} 秒`, `${draft.durationSeconds} 秒`);
  add('環境模式', saved.environment.mode, draft.environment.mode);
  add('天氣、時段、閃電', venueClimateText(saved.environment), venueClimateText(draft.environment));
  add('敵軍設定', missionEnemyText(saved.enemies), missionEnemyText(draft.enemies));
  const propText = prop => prop ? `${prop.assetId} · (${prop.position.x}, ${prop.position.y}, ${prop.position.z}) m · ${prop.yawDegrees}°` : '（無物件）';
  for (let index = 0; index < Math.max(saved.props.length, draft.props.length); index++) {
    const original = saved.props[index], edited = draft.props[index];
    if (!matchesMissionProp(original, edited, matchesSavedCoordinate))
      add(`物件 ${index + 1}`, propText(original), propText(edited));
  }
  return rows;
}
function closeTemplateComparison() {
  $('template-comparison').open = false;
  $('template-comparison-rows').replaceChildren();
  $('template-comparison-status').textContent = '';
  $('template-comparison-table').hidden = true;
}
function restoreParent() {
  if (!comparedVersion) return null;
  return state.catalog.find(row => row.seriesId === comparedVersion.seriesId && row.number > comparedVersion.number) ?? null;
}
async function saveMission(revise = false) {
  if (state.pending || (revise && !state.draftBase)) return;
  clearPropCopies(); propMove.clearPreview();
  const parent = revise ? state.draftBase : null;
  state.pending = { kind: revise ? 'mission-revise' : 'mission-create', parent,
    path: parent ? `/missions/${parent.mission.id}/revisions` : '/missions', method: 'POST', requestId: uuid(),
    body: draftDefinition() };
  await sendPending();
}
function renderProps(updateInspector = true) {
  clearPropCopies();
  renderPropHistory();
  drawLayoutProps($('prop-layer'), state.props, state.prop);
  propMove.update(updateInspector);
  placement.scheduleDraft();
  if (!updateInspector) return;
  fillOptions('prop-select', state.props.length ? state.props.map((p, i) => [String(i), `${i + 1} · ${p.assetId}`]) : [['', '尚無物件']], String(state.prop));
  $('prop-inspector').hidden = state.prop < 0;
  const prop = state.props[state.prop];
  if (prop) { $('prop-asset').value = prop.assetId; for (const axis of ['x', 'y', 'z']) $('prop-' + axis).value = prop.position[axis]; $('prop-yaw').value = prop.yawDegrees; }
}
function editable() { return master() && !state.busy && !state.pending; }
function dirtyDraft() {
  state.draftChanged = true; clearMissionComparison();
  if ($('template-comparison').open) closeTemplateComparison();
  draftStatus(); placement.scheduleDraft();
}
let propGesture = null;
let propCopies = [];
const maxProps = 500;
const copyProposal = mountLayoutProposal('copy', placement.inspectProposal);
const propMove = mountPlacementMove({ props: () => state.props, editable, inspect: placement.inspectProposal,
  apply: moves => editProp(() => {
    for (const { prop, position, yawDegrees } of moves) Object.assign(prop, { position, yawDegrees });
  }) });
function clearPropCopies() {
  propCopies = [];
  copyProposal.clear();
}
function previewPropCopies() {
  const prop = state.props[state.prop];
  if (!editable() || !prop) return;
  clearPropCopies();
  const values = ['prop-copy-count', 'prop-copy-x', 'prop-copy-z'].map(id => $(id).value.trim());
  const [count, dx, dz] = values.map(Number), status = $('prop-copy-status');
  if (values.some(value => value === '') || !Number.isInteger(count) || count < 1 || count > 20
    || !Number.isFinite(dx) || !Number.isFinite(dz) || (dx === 0 && dz === 0)) {
    status.textContent = '請填 1 至 20 份及有效位移，X 和 Z 至少一項須非零。';
    return;
  }
  if (state.props.length + count > maxProps) { status.textContent = '最多可放置 500 個物件。'; return; }
  const copies = Array.from({ length: count }, (_, index) => ({ ...prop, position: {
    x: prop.position.x + dx * (index + 1), y: prop.position.y, z: prop.position.z + dz * (index + 1)
  } }));
  if (copies.some(({ position }) => Math.abs(position.x) > 10 || Math.abs(position.z) > 10)) {
    status.textContent = '預覽中心超出配置圖的 ±10 公尺範圍。';
    return;
  }
  propCopies = copies;
  drawLayoutProps($('prop-copy-preview'), copies, null, copies.map((_, index) => state.props.length + index));
  void copyProposal.check([...state.props, ...copies], `已預覽 ${copies.length} 份。`);
}
function applyPropCopies() {
  if (!editable() || !propCopies.length || $('apply-prop-copy').disabled) return;
  editProp(() => { state.props.push(...propCopies); state.prop = state.props.length - 1; });
}
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
  if (state.props.length >= maxProps) { notify('最多可放置 500 個物件。', true); return; }
  editProp(() => { state.props.push({ assetId, position: { x: 0, y: 0, z: 0 }, yawDegrees: 0 }); state.prop = state.props.length - 1; });
}
function mapCoordinate(value) { return Math.max(-10, Math.min(10, value)); }
function dragCoordinate(value) { return Math.round(mapCoordinate(value) * 2) / 2; }
function moveProp(x, z) {
  const prop = state.props[state.prop];
  if (!prop || !editable() || (prop.position.x === x && prop.position.z === z)) return;
  prop.position.x = x;
  prop.position.z = z;
  renderProps(false);
  $('prop-x').value = x;
  $('prop-z').value = z;
  dirtyDraft();
}
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
$('layout-map').addEventListener('pointermove', event => {
  if (!dragging) return;
  const point = mapPoint(event);
  moveProp(dragCoordinate(point.x + offset.x), dragCoordinate(point.z + offset.z));
});
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
  const directions = { ArrowLeft: [-.5, 0], ArrowRight: [.5, 0], ArrowUp: [0, .5], ArrowDown: [0, -.5] }, delta = directions[event.key];
  if (!delta || event.ctrlKey || event.metaKey || event.altKey || !editable()) return;
  const index = target ? Number(target.dataset.index) : state.prop;
  const prop = state.props[index];
  if (!prop) return;
  event.preventDefault();
  $('layout-map').focus();
  if (index !== state.prop) {
    finishPropGesture();
    state.prop = index;
    renderProps();
  }
  beginPropGesture();
  const { x, z } = prop.position;
  moveProp(delta[0] ? mapCoordinate(x + delta[0]) : x, delta[1] ? mapCoordinate(z + delta[1]) : z);
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

function tab(name, worldTarget = null) {
  if (name !== 'operations') { operationsViewEpoch++; clearVenueMissionFile(); closeVenueDepartures(); }
  if (name !== 'missions') { draftLoad?.abort(); placement.clearTrial(); clearMissionTemplate(); clearPropCopies(); propMove.reset(); }
  finishPropGesture();
  $('world-return-venue-begin').hidden = !(name === 'world' && master() && worldTarget?.witness?.kind === 'blocked-begin');
  const trackingReturn = $('world-return-tracking');
  const trackingRoom = name === 'world' && master() && worldTarget?.returnToTracking ? worldTarget.roomId : null;
  trackingReturn.hidden = trackingRoom == null;
  if (trackingRoom == null) delete trackingReturn.dataset.roomId;
  else trackingReturn.dataset.roomId = trackingRoom;
  for (const candidate of ['operations', 'missions', 'replay', 'world']) { const active = candidate === name; $(candidate + '-view').hidden = !active; $('tab-' + candidate).classList.toggle('active', active); $('tab-' + candidate).setAttribute('aria-pressed', String(active)); }
  replay.active(name === 'replay'); world.active(name === 'world', worldTarget); readiness.active(name === 'operations'); connections.active(name === 'operations');
  roomReadiness.active(name === 'operations');
  closure.active(name === 'operations');
  venueDebrief.active(name === 'operations');
  venueReport.active(name === 'operations');
  alignment.active(name === 'missions' && master());
  alignmentPins.active(name === 'operations');
  seatDeployments.forEach(panel => panel.active(name === 'operations'));
  mrVenue.active(name === 'operations');
  vrVenue.active(name === 'operations');
  venueServerPlan.active(name === 'operations');
  venueLaunchReview.active(name === 'operations');
  venueHardwareReview.active(name === 'operations');
  operatorNetwork.active(name === 'operations');
}
$('world-return-venue-begin').addEventListener('click', () => {
  if (!master() || $('world-view').hidden || $('world-return-venue-begin').hidden) return;
  tab('operations');
  $('venue-phase-title').focus();
});
for (const id of ['roster-return-begin', 'venue-roster-return-begin']) {
  $(id).addEventListener('click', () => {
    if (!master() || $('operations-view').hidden || $(id).hidden || $(id).disabled) return;
    $('venue-phase-title').focus();
  });
}
$('world-return-tracking').addEventListener('click', () => {
  const button = $('world-return-tracking');
  if (!master() || $('world-view').hidden || button.hidden) return;
  const room = world.verifiedRoom() ?? Number(button.dataset.roomId);
  tab('operations');
  const tracking = $('venue-live-tracking');
  const target = tracking.hidden ? $('tab-operations')
    : [...$('venue-live-tracking-rooms').children].find(row => Number(row.dataset.liveTrackingRoom) === room)
      ?? $('venue-live-tracking-title');
  target.focus();
});
function submit(id, action, execute = run) { $(id).addEventListener('submit', event => { event.preventDefault(); execute(action); }); }
$('venue-departed-close').addEventListener('click', closeVenueDepartures);
$('login-form').addEventListener('submit', login);
$('logout').addEventListener('click', () => {
  const pendingMission = state.pending?.kind === 'mission-create' || state.pending?.kind === 'mission-revise';
  if (state.pending?.kind === 'venue-roster-join') {
    if (confirm('名冊登記結果尚未確認。登出會清除重試資料，確定登出？')) logout();
    return;
  }
  if (state.pending?.kind === 'venue-plan-save') {
    if (confirm('五房配置的保存結果尚未確認。登出會清除目前的草稿和重試資料。確定登出？')) logout();
    return;
  }
  if (pendingMission ? confirm('任務儲存結果尚未確認。登出會清除目前的草稿和重試資料。確定登出？') : confirmDraftDiscard('登出')) logout();
});
$('refresh').addEventListener('click', () => refresh().then(() => notify('已更新。')).catch(showRefreshError));
$('include-ended').addEventListener('change', async () => {
  const epoch = state.epoch;
  if (state.refreshPromise) { try { await state.refreshPromise; } catch { /* Refresh below reports errors. */ } }
  if (epoch === state.epoch) await refresh().catch(showRefreshError);
});
$('session-select').addEventListener('change', () => selectSession($('session-select').value));
$('prepare-from-session').addEventListener('click', prepareFromSession);
$('launch-mode').addEventListener('change', () => { placement.scheduleLaunch(); applyPermissions(); });
$('launch-mission').addEventListener('change', () => { placement.scheduleLaunch(); applyPermissions(); });
$('launch-room').addEventListener('change', applyPermissions);
$('saved-venue-mission-plans').addEventListener('toggle', () => {
  if (!$('saved-venue-mission-plans').open && venueMissionReview?.saved) clearVenueMissionReview();
  if (savedVenuePlans === null) void refreshSavedVenuePlans();
});
$('refresh-venue-plans').addEventListener('click', refreshSavedVenuePlans);
$('saved-venue-plan').addEventListener('change', () => {
  if (venueMissionReview?.saved) clearVenueMissionReview();
  $('venue-plan-status').textContent = '';
  applyPermissions();
});
$('preview-venue-plan').addEventListener('click', () => loadSavedVenuePlan(true));
$('load-venue-plan').addEventListener('click', () => loadSavedVenuePlan(false));
$('venue-plan-name').addEventListener('input', applyPermissions);
$('save-venue-plan').addEventListener('click', saveVenuePlan);
$('venue-missions-file').addEventListener('change', () => {
  $('venue-missions-file-status').textContent = ''; clearVenueMissionReview(); applyPermissions();
});
$('preview-venue-missions').addEventListener('click', () => loadVenueMissionFile(true));
$('venue-missions-map-room').addEventListener('change', renderVenueMissionReview);
$('load-venue-missions').addEventListener('click', () => loadVenueMissionFile(false));
$('use-venue-mission-room').addEventListener('click', () => useVenueMissionRooms([Number($('venue-missions-map-room').value)]));
$('use-selected-venue-mission-rooms').addEventListener('click', () => useVenueMissionRooms([...(venueMissionReview?.selectedRooms ?? [])]));
$('download-venue-missions').addEventListener('click', () => {
  const plan = venueMissionSelection();
  if ($('download-venue-missions').disabled || !plan) return;
  const filename = plan.mode === 'Linked' ? 'vr-venue-missions-linked.json' : 'vr-venue-missions-independent.json';
  download(filename, new Blob([JSON.stringify(plan, null, 2) + '\n'], { type: 'application/json' }));
});
for (const kind of ['environment', 'enemies']) {
  $('reload-' + kind).addEventListener('click', () => runSession(async () => {
    await refresh();
    loadLiveSetting(kind);
  }));
  $(kind + '-form').addEventListener('input', () => {
    if (liveSettingDrafts[kind]) liveSettingDrafts[kind].edited = true;
  });
}
$('retry-command').addEventListener('click', () => run(sendPending));
$('venue-begin').addEventListener('click', () => {
  const beginView = operationsViewEpoch;
  run(() => venuePhase('Begin', { beginView }));
});
$('venue-begin-export').addEventListener('click', downloadVenueBeginChecklist);
$('export-venue-environment').addEventListener('click', () => {
  if (!master() || state.pending) return;
  const epoch = state.epoch, view = operationsViewEpoch;
  void run(async () => {
    const data = await api('/venue/hardware-environment');
    if (state.epoch !== epoch || operationsViewEpoch !== view || !master()) return;
    if (data?.version !== 1 || !Number.isFinite(Date.parse(data.checkedAtUtc))
      || data.rooms?.length !== venueMissionRooms.length || !venueMissionRooms.every((id, index) => data.rooms[index]?.roomId === id))
      throw new Error('Unexpected venue environment response');
    download('vr-command-venue-environment.json', new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' }));
  }, true);
});
$('venue-begin-size').addEventListener('change', applyVenuePermissions);
for (const [id, other] of [['venue-full-tracking', 'venue-full-participation'], ['venue-full-participation', 'venue-full-tracking']]) {
  $(id).addEventListener('change', () => {
    if ($(id).checked) $(other).checked = false;
    applyVenuePermissions();
  });
}
$('venue-pause').addEventListener('click', () => run(() => venuePhase('Pause')));
$('venue-resume').addEventListener('click', () => run(() => venuePhase('Resume')));
$('venue-end').addEventListener('click', () => run(() => venuePhase('End')));
$('venue-closure-open-end').addEventListener('click', openConfirmedVenueEnd);
$('restore-venue-plan').addEventListener('click', restoreVenuePlan);
for (const [name, key] of [['environment', 'latestEnvironment'], ['enemy', 'latestEnemies']]) {
  const button = $('venue-' + name + '-batch-download');
  button.addEventListener('click', () => {
    const batch = state.venue?.[key];
    if (!master() || state.busy || state.pending || button.disabled || !batch || !state.venuePhaseBlob) return;
    download(`vr-command-venue-${name}-${batch.requestId}.json`, state.venuePhaseBlob);
  });
}
submit('venue-environment-form', () => venuePhase('SetEnvironment', { environment: {
  weather: $('venue-weather').value, timeOfDay: $('venue-time').value, lightning: $('venue-lightning').checked
} }));
submit('venue-enemies-form', () => venuePhase('SetEnemies', { enemyPolicy: {
  behavior: $('venue-behavior').value, autoAttack: $('venue-auto-attack').checked
} }));
$('download-room-tickets').addEventListener('click', () => downloadRoomTickets(Number($('ticket-room').value)));
$('download-roster-room-tickets').addEventListener('click', () => downloadRoomTickets(Number($('roster-room').value)));
$('ticket-room').addEventListener('change', applyPermissions);
document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => runSession(() => {
  const action = button.dataset.command;
  return command(action, action === 'Begin' && usesTrackedVrStart(state.session) ? { requireTrackedStart: true } : {});
})));
submit('create-session-form', createSession);
submit('join-form', joinPlayer, runSession);
submit('environment-form', () => applyLiveSetting('environment', 'SetEnvironment', environment('live')), runSession);
submit('enemies-form', () => applyLiveSetting('enemies', 'SetEnemies', enemies('live')), runSession);
$('room-enemies-room').addEventListener('change', () => renderRoomEnemyPolicy(true));
$('room-enemies-reload').addEventListener('click', () => runSession(async () => {
  await refresh();
  renderRoomEnemyPolicy(true);
}));
$('room-enemies-inherit').addEventListener('change', () => renderRoomEnemyPolicy());
submit('room-enemies-form', () => {
  if ($('room-enemies-panel').hidden || state.session.combatStream?.roomEnemyPolicyVersion !== 1) return;
  const roomId = Number($('room-enemies-room').value);
  if (!ownsRoom(roomId) || !state.session.roomIds.includes(roomId)) return;
  if ($('room-enemies-apply').disabled || !roomEnemyDraft) return;
  const policy = $('room-enemies-inherit').checked ? null
    : { behavior: $('room-enemies-behavior').value, autoAttack: $('room-enemies-auto').checked };
  return command('SetRoomEnemies', { roomEnemyPolicy: { roomId, policy, expectedPolicySequence: roomEnemyDraft.sequence } }, null);
}, runSession);
submit('clock-form', () => command('SetMissionClock', { missionClock: { autoEnd: $('clock-auto-end').checked } }, state.clockSequence), runSession);
$('reload-clock').addEventListener('click', loadClock);
$('clock-auto-end').addEventListener('change', () => { state.clockSequence = state.session?.sequence; });
submit('mission-form', saveMission);
$('mission-search').addEventListener('input', () => {
  editMissionOptions(undefined, true);
  applyPermissions();
});
$('edit-mission').addEventListener('change', applyPermissions);
$('launch-selected-mission').addEventListener('click', () => {
  pinLaunchVersion(state.catalog.find(row => row.mission.id === $('edit-mission').value));
});
$('load-mission').addEventListener('click', () => {
  const id = $('edit-mission').value;
  const selected = state.catalog.find(row => row.mission.id === id);
  if (selected && confirmDraftDiscard('載入最新版'))
    requestDraft({ id, seriesId: selected.seriesId, number: selected.number });
});
$('load-version').addEventListener('click', () => {
  const id = $('mission-version').value;
  const history = state.history, selected = history?.versions.find(row => row.id === id);
  if (selected && confirmDraftDiscard('載入選取版本'))
    requestDraft({ id, seriesId: history.seriesId, number: selected.number }, 'selected');
});
$('export-mission-template').addEventListener('click', () => {
  const id = $('mission-version').value, epoch = state.epoch, view = templateEpoch;
  if (!editable() || !id) return;
  run(async () => {
    if (view !== templateEpoch) return;
    const file = await api(`/missions/${id}/template`, 'GET', undefined, undefined, undefined, 'blob');
    if (epoch !== state.epoch || view !== templateEpoch || id !== $('mission-version').value) return;
    if (file.type !== 'application/json') throw new Error('Expected a mission template file.');
    download(`vr-mission-template-${id}.json`, file);
  }, true);
});
$('mission-template-file').addEventListener('change', () => { clearMissionTemplate(true); applyPermissions(); });
$('export-draft-template').addEventListener('click', exportDraftTemplate);
$('check-mission-template').addEventListener('click', () => {
  const file = $('mission-template-file').files[0];
  if (!editable() || !file) return;
  clearMissionTemplate(true);
  if (!file.size || file.size > missionTemplateFileLimit) { notify('請選擇 512 KiB 以內的任務範本 JSON。', true); applyPermissions(); return; }
  const epoch = templateEpoch;
  run(() => checkMissionTemplate(file, epoch));
});
$('use-mission-template').addEventListener('click', useMissionTemplate);
$('template-comparison').addEventListener('toggle', () => {
  if (!$('template-comparison').open || !checkedTemplate || !master()) return;
  const rows = missionDifferenceRows(checkedTemplate, draftDefinition());
  $('template-comparison-rows').replaceChildren(...rows);
  $('template-comparison-table').hidden = rows.length === 0;
  $('template-comparison-status').textContent = rows.length ? `${rows.length} 項差異，物件按清單順序比較。` : '範本與目前草稿相同。';
});
$('mission-version').addEventListener('change', clearMissionComparison);
$('compare-version').addEventListener('click', () => {
  const id = $('mission-version').value;
  if (id) run(() => compareMissionVersion(id), true);
});
$('more-versions').addEventListener('click', () => run(async () => {
  if (!state.history?.nextBefore) return;
  const previous = state.history, epoch = state.epoch;
  const page = await api(`/missions/${previous.seriesId}/history?before=${previous.nextBefore}`);
  if (epoch !== state.epoch || state.history !== previous) return;
  requireMissionHistory(page, previous.seriesId, previous.headNumber);
  const versions = new Map([...previous.versions, ...page.versions].map(row => [row.number, row]));
  let newest = page;
  if (page.headId !== previous.headId) {
    newest = await api(`/missions/${previous.seriesId}/history`);
    if (epoch !== state.epoch || state.history !== previous) return;
    requireMissionHistory(newest, previous.seriesId, page.headNumber);
    if (!newest.versions.some(row => row.id === newest.headId && row.number === newest.headNumber))
      throw new MissionVersionMismatch();
    const edit = state.catalog.find(row => row.mission.id === $('edit-mission').value);
    if (!await rememberHead(newest, epoch) || state.history !== previous) return;
    for (const row of newest.versions) versions.set(row.number, row);
    const selected = state.catalog.find(row => row.seriesId === edit?.seriesId);
    missionOptions(undefined, selected?.mission.id);
  }
  // A concurrent burst of revisions can leave a gap between the newest page and the pages already read.
  let oldest = newest.headNumber;
  while (versions.has(oldest - 1)) oldest--;
  state.history = { ...newest, versions: [...versions.values()], nextBefore: oldest > 1 ? oldest : null };
  renderHistory(); draftStatus();
}, true));
$('save-revision').addEventListener('click', () => { if ($('mission-form').reportValidity()) run(() => saveMission(true)); });
$('merge-mission-head').addEventListener('click', () => {
  const base = state.draftBase;
  if (editable() && state.draftChanged && base && knownHeadNumber(base.seriesId) > base.number && $('mission-form').reportValidity())
    requestDraft({ id: base.mission.id, seriesId: base.seriesId, number: base.number }, 'merge');
});
function pinLaunchVersion(revision) {
  if (!revision || state.pending || state.busy) return;
  state.launchPinned = revision; missionOptions(revision.mission.id); tab('operations');
  const room = roomPlan.enabled() ? roomPlan.preview().roomId : null;
  if (room) roomPlan.setRevision(revision);
  notify(room ? `已為房間 ${room} 選取保存的第 ${revision.number} 版；未儲存的草稿修改不會套用。`
    : `已選取保存的第 ${revision.number} 版開場；未儲存的草稿修改不會套用。`);
}
$('launch-version').addEventListener('click', () => pinLaunchVersion(state.draftBase));
$('launch-compared-version').addEventListener('click', () => pinLaunchVersion(comparedVersion));
$('restore-compared-version').addEventListener('click', () => {
  const parent = restoreParent(), source = comparedVersion;
  if (!master() || state.busy || state.pending || !parent) return;
  if (!confirm(`將「${source.mission.definition.name}」第 ${source.number} 版的內容接在第 ${parent.number} 版後，保存為第 ${parent.number + 1} 版？目前草稿會保留。`)) return;
  const body = structuredClone(source.mission.definition);
  run(async () => {
    state.pending = { kind: 'mission-revise', parent, restoredFrom: source.number,
      path: `/missions/${parent.mission.id}/revisions`, method: 'POST', requestId: uuid(), body };
    await sendPending();
  });
});
$('new-mission').addEventListener('click', () => { if (confirmDraftDiscard('建立新草稿')) resetDraft(); });
$('add-sandbag').addEventListener('click', () => addProp('sandbag'));
$('add-barrel').addEventListener('click', () => addProp('barrel'));
$('preview-prop-copy').addEventListener('click', previewPropCopies);
$('apply-prop-copy').addEventListener('click', applyPropCopies);
for (const event of ['input', 'change']) $('prop-copy-panel').addEventListener(event, clearPropCopies);
for (const id of ['draft-mode', 'draft-count', 'layout-session-mode']) for (const event of ['input', 'change']) {
  $(id).addEventListener(event, () => { clearPropCopies(); propMove.clearPreview(); });
}
$('prop-copy-panel').addEventListener('toggle', () => {
  if ($('prop-copy-panel').open) $('prop-move-panel').open = false;
  else clearPropCopies();
});
$('rotate-prop').addEventListener('click', () => { if (state.props[state.prop]) editProp(() => { state.props[state.prop].yawDegrees = (state.props[state.prop].yawDegrees + 15) % 360; }); });
$('remove-prop').addEventListener('click', () => { if (state.prop >= 0) editProp(() => { state.props.splice(state.prop, 1); state.prop = Math.min(state.prop, state.props.length - 1); }); });
for (const type of ['input', 'change']) $('mission-form').addEventListener(type, event => {
  if (loadedText && event.target.id === 'draft-name') loadedText.name = null;
  if (loadedText && event.target.id === 'draft-briefing') loadedText.briefing = null;
  if (!['layout-session-mode', 'prop-select', 'draft-layout-show-clearance'].includes(event.target.id)
    && !event.target.closest('#prop-copy-panel, #prop-move-panel')) dirtyDraft();
});
$('layout-session-mode').addEventListener('change', () => placement.scheduleDraft());
$('layout-recheck-draft').addEventListener('click', () => placement.recheckDraft());
$('layout-recheck-launch').addEventListener('click', () => {
  const mixed = roomPlan.enabled();
  if (mixed) roomPlan.recheck();
  placement.recheckLaunch(!mixed);
});
for (const name of ['operations', 'missions', 'replay', 'world']) $('tab-' + name).addEventListener('click', () => tab(name));
window.addEventListener('beforeunload', event => { if (state.pending || state.draftChanged) { event.preventDefault(); event.returnValue = ''; } });
