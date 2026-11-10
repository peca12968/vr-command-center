import { formatClock } from './mission-clock.js';
import { validEndpoint } from './connection-ui.js';

const labels = { NoRecording: '等待遊戲來源', WaitingFrame: '等待第一份快照', UnknownCaptureTime: '擷取時間未知', ClockSkew: '來源時鐘未同步',
  Stale: '快照已過期', Suspended: '管理連線中斷', PhasePending: '等待階段同步', Ended: '場次已結束', Fresh: '正在接收',
  AwaitingAdmission: '等待本次入場同步', AwaitingPose: '等待姿態', PoseUnavailable: '姿態未就緒／中斷', Eliminated: '已淘汰',
  Participating: '姿態有效', Updating: '正在更新入場狀態', Unavailable: '參戰狀態未確認' };

const beginSeatStates = new Set(['AwaitingAdmission', 'AwaitingPose', 'PoseUnavailable', 'Eliminated', 'Tracked', 'Simulated']);

function venueBeginSeats(details, registered, capacity, trackedRequired) {
  const seats = details?.seats;
  if (!Array.isArray(seats) || seats.length !== registered || !seats.every((row, index) => Number.isInteger(row?.seat)
    && row.seat >= 1 && row.seat <= capacity && (index === 0 || seats[index - 1].seat < row.seat)
    && (details.state === 'WaitingRevision' ? ['AwaitingAdmission', 'WaitingRevision'].includes(row.state)
      : beginSeatStates.has(row.state)))) return null;
  const occupied = new Map(seats.map(row => [row.seat, row.state]));
  return Array.from({ length: capacity }, (_, index) => {
    const state = occupied.get(index + 1) ?? 'Vacant';
    return state === 'Simulated' && trackedRequired ? 'NeedsTracking' : state;
  });
}

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
    + (endpoint.address.startsWith('127.') ? ' · 僅同機' : '')
    + (row.ticketSourceLive === false ? ' · 遊戲來源暫未確認，暫停配票' : '');
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
  let state = applied ? 'Applied' : source === 'Fresh' ? 'PhasePending' : source;
  let detail = applied ? '' : labels[state];
  if (applied && phase.action === 'Pause') {
    state = ready ? 'Ready' : 'WaitingTracking';
    detail = ready ? '可繼續' : '等候 MR 追蹤';
    const mr = phase.mrResume;
    if (!ready && session.environment?.mode === 'MR' && mr?.state === 'WaitingRevision') {
      state = 'WaitingRevision'; detail = '等候最新名冊及設定同步';
    } else if (!ready && session.environment?.mode === 'MR' && mr?.state === 'WaitingProfile') {
      state = 'WaitingProfile'; detail = '等候 Quest 3 MR 遊戲來源';
    } else if (!ready && session.environment?.mode === 'MR' && mr?.state === 'WaitingPlayers'
      && Array.isArray(mr.waitingSeats) && mr.waitingSeats.length <= row.registered
      && mr.waitingSeats.every((seat, index, seats) => Number.isInteger(seat) && seat >= 1 && seat <= room.capacity
        && (index === 0 || seats[index - 1] < seat))) {
      if (mr.waitingSeats.length) {
        state = 'WaitingPlayers'; detail = `等候席位 ${mr.waitingSeats.join('、')} 的追蹤`;
      } else if (session.mode === 'Linked') {
        state = 'WaitingLinkedRooms'; detail = (row.registered ? '本房席位就緒' : '本房無登記席位') + ' · 等候同場其他房間';
      }
    }
  }
  const text = `${verb}${applied ? '已套用' : '待確認'}` + (detail ? ` · ${detail}` : '');
  return { applied, ready, action: phase.action, sequence: phase.appliedAtSequence, state, text };
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
  const ready = simulatedReady + trackedReady;
  const counts = living => `${ready} / ${living} 姿態有效 · 合成 ${simulatedReady} · 追蹤 ${trackedReady}`;
  if (session.environment?.mode !== 'VR' || !['Preparing', 'Running'].includes(session.state))
    return { source, ready, text: counts(row.registered) };
  if (!row.vrParticipation) return session.state === 'Preparing' ? { source, ready, text: counts(row.registered) }
    : { source: 'PhasePending', text: labels.PhasePending };
  const { awaitingAdmission, awaitingPose, eliminated } = row.vrParticipation;
  const lists = [awaitingAdmission, awaitingPose, eliminated];
  if (lists.some(seats => !Array.isArray(seats) || seats.length > room.capacity))
    return { source: 'Unavailable', text: labels.Unavailable };
  const seats = lists.flat();
  if (seats.some(seat => !Number.isInteger(seat) || seat < 1 || seat > room.capacity)
    || new Set(seats).size !== seats.length || seats.length + ready !== row.registered)
    return { source: 'Unavailable', text: labels.Unavailable };
  const attention = awaitingAdmission.length + awaitingPose.length > 0;
  const text = [counts(row.registered - eliminated.length),
    awaitingAdmission.length ? `入場待同步席位 ${awaitingAdmission.join('、')}` : '',
    awaitingPose.length ? `姿態待確認席位 ${awaitingPose.join('、')}` : '',
    eliminated.length ? `已淘汰席位 ${eliminated.join('、')}` : ''].filter(Boolean).join(' · ');
  return { source, ready: attention ? 0 : ready, attention, text };
}

function mayManageRoom(room, session, actor) {
  return session?.roomIds?.includes(room.id)
    && (actor?.role === 'Master' || (actor?.role === 'RoomController' && actor.roomId === room.id
      && session.mode === 'Independent' && session.roomIds.length === 1));
}
export function roomPoseFrameTarget(report, room, session, elapsed, actor) {
  if (session?.state !== 'Running' || !session.roomIds?.includes(room.id)
    || !(actor?.role === 'Master' || (actor?.role === 'RoomController' && actor.roomId === room.id))) return null;
  const row = roomReadinessRow(report, room, session), pose = row?.poseInterruption;
  if (!pose || sourceAt(row, elapsed) !== 'Fresh' || typeof pose.streamId !== 'string' || !pose.streamId
    || pose.streamId !== session.combatStream?.streamId || !Number.isSafeInteger(pose.worldSequence) || pose.worldSequence < 1
    || !Number.isSafeInteger(pose.observedSequence) || pose.observedSequence < 1 || pose.observedSequence > row.sessionSequence
    || !Array.isArray(pose.seats) || !pose.seats.length || pose.seats.length > row.registered
    || !Array.isArray(session.players)) return null;
  const players = pose.seats.map(seat => session.players.filter(player => player.roomId === room.id && player.seat + 1 === seat));
  if (pose.seats.some((seat, index, seats) => !Number.isInteger(seat) || seat < 1 || seat > room.capacity
    || (index > 0 && seats[index - 1] >= seat)) || players.some(matches => matches.length !== 1 || typeof matches[0].id !== 'string'
    || !matches[0].id) || new Set(players.map(matches => matches[0].id)).size !== players.length) return null;
  return { mode: 'replay', sessionId: session.id, roomId: room.id, streamId: pose.streamId, complete: false,
    throughSequence: pose.worldSequence, witness: { kind: 'pose-interruption', observedSequence: pose.observedSequence,
      seats: pose.seats, playerIds: players.map(matches => matches[0].id) } };
}

export function roomMrTrackingPauseTarget(report, room, session, elapsed, actor) {
  if (session?.state !== 'Running' || !mayManageRoom(room, session, actor) || session.environment?.mode !== 'MR'
    || session.combatStream?.origin !== 'GameServer') return null;
  const row = roomReadinessRow(report, room, session);
  if (row?.mrTrackingPauseAvailable !== true || !roomReadinessView(report, room, session, elapsed).attention) return null;
  return { sessionId: session.id, sequence: row.sessionSequence, linked: session.mode === 'Linked' };
}
export function roomVrParticipationPauseTarget(report, room, session, elapsed, actor) {
  if (session?.state !== 'Running' || !mayManageRoom(room, session, actor) || session.environment?.mode !== 'VR'
    || !session.combatStream) return null;
  const row = roomReadinessRow(report, room, session);
  if (row?.vrParticipationPauseAvailable !== true || !roomReadinessView(report, room, session, elapsed).attention
    || !row.vrParticipation?.awaitingPose?.length) return null;
  return { sessionId: session.id, sequence: row.sessionSequence, linked: session.mode === 'Linked' };
}

export function roomMrPauseView(report, room, session, elapsed, unavailable = false) {
  if (session?.state !== 'Paused' || session.environment?.mode !== 'MR') return null;
  const row = roomReadinessRow(report, room, session);
  const pause = row?.mrPause;
  if (!Number.isSafeInteger(pause?.appliedAtSequence) || pause.appliedAtSequence < 1 || pause.appliedAtSequence > row.sessionSequence)
    return 'MR 暫停待確認';
  const source = unavailable ? 'Unavailable' : sourceAt(row, elapsed);
  return source === 'Fresh' && Number.isSafeInteger(pause.worldSequence) && pause.worldSequence > 0
    ? 'MR 暫停已套用' : `MR 暫停待確認 · ${source === 'Fresh' ? '等待階段同步' : labels[source]}`;
}
function roomVrPauseView(report, room, session, elapsed, unavailable) {
  if (session?.state !== 'Paused' || session.environment?.mode !== 'VR') return null;
  const row = roomReadinessRow(report, room, session), pause = row?.vrPause;
  if (!session.roomIds?.includes(pause?.triggerRoomId) || !Number.isSafeInteger(pause.appliedAtSequence)
    || pause.appliedAtSequence < 1 || pause.appliedAtSequence > row.sessionSequence) return null;
  const applied = !unavailable && sourceAt(row, elapsed) === 'Fresh'
    && Number.isSafeInteger(pause.worldSequence) && pause.worldSequence > 0;
  const seats = pause.waitingSeats;
  const hasRoster = applied && Array.isArray(seats) && seats.length <= room.capacity
    && new Set(seats).size === seats.length && seats.every(seat => Number.isInteger(seat) && seat >= 1 && seat <= room.capacity);
  const text = `房間 ${pause.triggerRoomId} 姿態中斷 · VR 暫停${applied ? '已套用' : '待確認'}`
    + (!applied ? '' : !hasRoster ? ' · 等待最新名冊畫格' : seats.length ? ` · 等候席位 ${seats.join('、')}` : ' · 本房席位已確認');
  return { text, triggerRoomId: pause.triggerRoomId, ready: hasRoster && seats.length === 0 && pause.readyToResume === true,
    attention: !hasRoster || seats.length > 0, sequence: row.sessionSequence };
}

export function venueTrackingRow(report, room, session, elapsed) {
  if (!room.sessionId) return { state: 'Idle', text: '空房' };
  if (session?.id !== room.sessionId) return { state: 'Updating', text: labels.Updating };
  if (session?.state === 'Preparing') return { state: 'Preparing', text: '尚未開場' };
  if (session?.state === 'Paused') return { state: 'Paused', text: '場次暫停' };
  const row = roomReadinessRow(report, room, session);
  if (!row || session.state !== 'Running')
    return { state: 'Updating', text: labels.Updating };
  const source = sourceAt(row, elapsed);
  if (source !== 'Fresh') return { state: source, text: labels[source] };
  const tracking = row.venueTracking;
  if (!tracking) return { state: 'WaitingRevision', text: '等待遊戲端確認最新場次狀態' };
  const { trackedSeats, simulatedSeats, waitingSeats, eliminatedSeats } = tracking;
  const lists = [trackedSeats, simulatedSeats, waitingSeats, eliminatedSeats];
  if (lists.some(seats => !Array.isArray(seats) || seats.length > room.capacity)
    || !Array.isArray(session.players)) return { state: 'Unavailable', text: labels.Unavailable };
  const expected = new Set(session.players.filter(player => player.roomId === room.id).map(player => player.seat + 1));
  const seats = lists.flat();
  if (seats.length !== row.registered || seats.length !== expected.size || new Set(seats).size !== seats.length
    || seats.some(seat => !Number.isInteger(seat) || seat < 1 || seat > room.capacity || !expected.has(seat))
    || trackedSeats.length !== row.trackedReady || simulatedSeats.length !== row.simulatedReady)
    return { state: 'Unavailable', text: labels.Unavailable };
  const vacant = Array.from({ length: room.capacity }, (_, index) => index + 1).filter(seat => !expected.has(seat));
  const details = [
    [simulatedSeats, '合成席位'], [waitingSeats, '待確認席位'], [eliminatedSeats, '已淘汰席位'], [vacant, '未編列席位']
  ].filter(([items]) => items.length).map(([items, label]) => `${label} ${items.join('、')}`);
  const tracked = trackedSeats.length;
  return { state: tracked === room.capacity ? 'Ready' : 'Incomplete', tracked,
    text: [`追蹤 ${tracked} / ${room.capacity} 席`, ...details].join(' · ') };
}

export function mountRoomReadiness(getState, unauthorized, venueUpdated, describeClimate, describeEnemies) {
  let active = false, controller, report, started = 0, attempted = -Infinity, failed = false;
  function settingView(room, session, elapsed, kind) {
    if (!active || !room || !['Running', 'Paused'].includes(session?.state)) return null;
    const row = roomReadinessRow(report, room, session), evidence = row?.[kind];
    const setting = evidence?.setting;
    if (!setting || typeof evidence.venue !== 'boolean') return null;
    const enemy = kind === 'enemies';
    if (enemy ? !['Hold', 'Patrol', 'Advance'].includes(setting.behavior) || typeof setting.autoAttack !== 'boolean'
        || !Number.isInteger(evidence.targetCount) || evidence.targetCount < 0 || evidence.targetCount > 100
      : !['Clear', 'Rain', 'Fog', 'Storm'].includes(setting.weather) || !['Day', 'Night'].includes(setting.timeOfDay)
        || typeof setting.lightning !== 'boolean') return null;
    const inherited = enemy && typeof evidence.inherited === 'boolean' ? evidence.inherited : undefined;
    const label = inherited === true ? '本房恢復沿用全場策略' : inherited === false ? '本房敵軍策略'
      : (evidence.venue ? '全館' : '場次') + (enemy ? '敵軍策略' : '環境');
    const details = enemy ? describeEnemies(setting) + ` · 全場目標 ${evidence.targetCount} 名` : describeClimate(setting);
    const view = roomVenueSettingView(row, setting, elapsed, failed, label, details);
    if (!view) return null;
    const counts = evidence.population;
    const population = enemy && view.applied && Number.isInteger(counts?.present) && counts.present >= 0 && counts.present <= 100
      && Number.isInteger(counts.alive) && counts.alive >= 0 && counts.alive <= counts.present ? counts : null;
    const target = view.applied && (!enemy || population) && typeof evidence.streamId === 'string' && evidence.streamId === session.combatStream?.streamId
      ? { mode: 'replay', sessionId: session.id, roomId: room.id, streamId: evidence.streamId, complete: false,
        throughSequence: setting.worldSequence, witness: { kind, setting, population, inherited } }
      : null;
    const text = population ? view.text + ` · 本房在場 ${population.present} 名、存活 ${population.alive} 名` : view.text;
    return { ...view, text, venue: evidence.venue, target, setting, population, targetCount: evidence.targetCount };
  }
  function settingStatus(roomId, kind, sessionId = null) {
    const { rooms, sessions } = getState(), room = rooms.find(row => row.id === roomId);
    if (sessionId !== null && room?.sessionId !== sessionId) return null;
    return settingView(room, sessions.find(row => row.id === room?.sessionId), performance.now() - started, kind);
  }
  function settingFrame(roomId, kind) {
    return settingStatus(roomId, kind)?.target;
  }
  function poseFrame(roomId) {
    const { rooms, sessions, actor } = getState(), room = rooms.find(row => row.id === roomId);
    if (!active || failed || !room || document.visibilityState !== 'visible') return null;
    return roomPoseFrameTarget(report, room, sessions.find(row => row.id === room.sessionId), performance.now() - started, actor);
  }
  function trackingPause(roomId, mode) {
    const { rooms, sessions, actor } = getState();
    const room = rooms.find(row => row.id === roomId);
    if (!active || failed || !room || document.visibilityState !== 'visible') return null;
    const target = mode === 'VR' ? roomVrParticipationPauseTarget : roomMrTrackingPauseTarget;
    return target(report, room, sessions.find(row => row.id === room.sessionId), performance.now() - started, actor);
  }
  function vrResume(roomId) {
    const { rooms, sessions, actor } = getState(), room = rooms.find(row => row.id === roomId);
    if (!active || failed || !room || document.visibilityState !== 'visible') return null;
    const session = sessions.find(row => row.id === room.sessionId);
    const recovery = roomVrPauseView(report, room, session, performance.now() - started, false);
    return recovery?.ready && recovery.triggerRoomId === roomId && mayManageRoom(room, session, actor)
      ? { sessionId: session.id, sequence: recovery.sequence, linked: session.mode === 'Linked' } : null;
  }
  function venueBegin(target, roomId, policy = 'normal') {
    let seats = null;
    const waiting = (state, text) => ({ state, text, ready: false, seats });
    if (failed) return waiting('Unavailable', '無法確認，正在重試');
    const { rooms, sessions } = getState();
    const room = rooms.find(row => row.id === roomId && row.sessionId === target.sessionId);
    const session = sessions.find(row => row.id === target.sessionId);
    const row = active && room && session?.state === 'Preparing' ? roomReadinessRow(report, room, session) : null;
    if (!row || row.sessionSequence !== target.sessionSequence) return waiting('Updating', '等待核對目前場次與名冊');
    const details = row.venueBegin;
    if (details?.state === 'EmptyRoster') {
      if (row.registered === 0) seats = venueBeginSeats(details, 0, room.capacity, false);
      return waiting('EmptyRoster', session.mode === 'Linked' ? '五房共用場次尚無玩家' : '名冊尚無玩家');
    }
    const source = sourceAt(row, performance.now() - started);
    if (source !== 'Fresh') return waiting(source, labels[source]);
    const mr = session.environment.mode === 'MR';
    const empty = '本房未編列席位';
    const requireTracking = policy === 'tracking';
    if (['Ready', 'WaitingPlayers', 'WaitingRevision'].includes(details?.state))
      seats = venueBeginSeats(details, row.registered, room.capacity, mr || requireTracking);
    if (policy !== 'normal' && details?.state !== 'WaitingRevision' && details?.state !== 'WaitingProfile') {
      const ready = mr || requireTracking ? row.trackedReady : row.trackedReady + row.simulatedReady;
      if (row.registered !== room.capacity || ready !== room.capacity)
        return waiting(requireTracking ? 'WaitingFullTracking' : 'WaitingFullParticipation',
          `名冊 ${row.registered}/${room.capacity} 席 · ${requireTracking ? '追蹤' : '有效姿態'} ${ready}/${room.capacity} 席`);
    }
    if (row.venueBeginReady === true)
      return { state: 'Ready', text: row.registered ? `${row.registered} 席${mr || requireTracking ? '追蹤' : '姿態'}就緒` : empty, ready: true, seats };
    if (details?.state === 'WaitingRevision') return waiting('WaitingRevision', '等待遊戲端同步最新設定與名冊');
    if (details?.state === 'WaitingProfile') return waiting('WaitingProfile', '等待支援 Quest 3 MR 的遊戲來源');
    if (details?.state === 'WaitingPlayers' && Array.isArray(details.waitingSeats) && details.waitingSeats.length <= row.registered
      && details.waitingSeats.every((seat, index, seats) => Number.isInteger(seat) && seat >= 1 && seat <= room.capacity
        && (index === 0 || seats[index - 1] < seat))) {
      const waitingSeats = details.waitingSeats;
      if (waitingSeats.length) return waiting('WaitingPlayers', `等候席位 ${waitingSeats.join('、')} 的${mr ? '追蹤' : '姿態'}`);
      return waiting('WaitingLinkedRooms', (row.registered ? '本房席位就緒' : empty) + ' · 等候同場其他房間');
    }
    return waiting('Unavailable', '開場條件尚未確認');
  }
  function venueReady(target, action, policy = 'normal') {
    if (action === 'Begin') return policy !== 'normal'
      ? target.roomIds.every(room => venueBegin(target, room, policy).ready)
      : venueBegin(target, target.roomIds[0]).ready;
    return venueResume(target, target.roomIds[0]).ready;
  }
  function venueResume(target, roomId) {
    const waiting = { ready: false, state: 'Updating', text: '等待目前場次的暫停確認' };
    if (!active || failed) return waiting;
    const { rooms, sessions } = getState();
    const room = rooms.find(row => row.id === roomId && row.sessionId === target.sessionId);
    const session = sessions.find(row => row.id === target.sessionId);
    if (!room || !session) return waiting;
    const elapsed = performance.now() - started;
    const venue = roomVenuePhaseView(report, room, session, elapsed);
    return venue?.action === 'Pause' && venue.sequence === target.phaseSinceSequence ? venue : waiting;
  }
  function renderVenueTracking(rooms, sessions, actor, elapsed) {
    const panel = document.getElementById('venue-live-tracking');
    const summary = document.getElementById('venue-live-tracking-summary');
    const list = document.getElementById('venue-live-tracking-rooms');
    const scoped = rooms.map(room => ({ room, session: sessions.find(session => session.id === room.sessionId) }));
    panel.hidden = !active || document.visibilityState !== 'visible' || actor?.role !== 'Master'
      || !scoped.some(row => row.session?.state === 'Running');
    const rows = panel.hidden ? [] : scoped.map(({ room, session }) => ({ room: room.id,
      ...venueTrackingRow(failed ? null : report, room, session, elapsed) }));
    const tracked = rows.reduce((total, row) => total + (row.tracked ?? 0), 0);
    const confirmed = rows.filter(row => row.tracked !== undefined).length;
    const text = panel.hidden ? '' : confirmed === 0 ? '等待各房可確認的執行中快照。'
      : `各房最新快照 · 追蹤 ${tracked} / 25 席 · ${confirmed} / 5 房有確認資料`;
    if (summary.textContent !== text) summary.textContent = text;
    const signature = JSON.stringify(rows);
    if (list.dataset.rows === signature) return;
    list.dataset.rows = signature;
    list.replaceChildren(...rows.map(row => {
      const item = document.createElement('li');
      item.dataset.liveTrackingRoom = row.room;
      item.dataset.liveTrackingState = row.state;
      item.textContent = `房間 ${row.room} · ${row.text}`;
      if (row.state === 'Incomplete') item.classList.add('tracking-attention');
      return item;
    }));
  }
  function render() {
    const { rooms, sessions, actor, busy, pending } = getState();
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
      const mrPause = cell.parentElement.querySelector('[data-room-mr-pause]');
      const pause = roomMrPauseView(report, room, session, elapsed, failed);
      mrPause.hidden = !pause;
      mrPause.textContent = pause ?? '';
      mrPause.classList.toggle('tracking-attention', !!pause && pause.startsWith('MR 暫停待確認'));
      const vrPause = cell.parentElement.querySelector('[data-room-vr-pause]');
      const vrStatus = roomVrPauseView(report, room, session, elapsed, failed);
      vrPause.hidden = !vrStatus;
      vrPause.textContent = vrStatus?.text ?? '';
      vrPause.classList.toggle('tracking-attention', !!vrStatus?.attention);
      const resumeButton = cell.parentElement.querySelector('[data-room-vr-resume]');
      if (resumeButton) {
        resumeButton.hidden = vrStatus?.triggerRoomId !== room.id || !mayManageRoom(room, session, actor);
        resumeButton.disabled = resumeButton.hidden || !active || failed || !vrStatus?.ready || busy || !!pending;
      }
      const pauseButton = cell.parentElement.querySelector('[data-room-mr-tracking-pause], [data-room-vr-participation-pause]');
      const target = active && !failed && (session?.environment?.mode === 'VR' ? roomVrParticipationPauseTarget
        : roomMrTrackingPauseTarget)(report, room, session, elapsed, actor);
      pauseButton.hidden = !target;
      pauseButton.disabled = !target || busy || !!pending;
      const poseButton = cell.parentElement.querySelector('[data-room-pose-frame]');
      const pose = active && !failed && roomPoseFrameTarget(report, room, session, elapsed, actor);
      poseButton.hidden = !pose;
      poseButton.disabled = !pose || busy || !!pending;
      poseButton.title = pose ? `席位 ${pose.witness.seats.join('、')} · 原畫格 ${pose.throughSequence}` : '';
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
      for (const [kind, venueAttribute] of [['environment', 'roomVenueEnvironment'], ['enemies', 'roomVenueEnemies']]) {
        const setting = settingView(room, session, elapsed, kind);
        const settingCell = cell.parentElement.querySelector(`[data-room-${kind}]`);
        if (setting?.venue) settingCell.dataset[venueAttribute] = room.id;
        else delete settingCell.dataset[venueAttribute];
        cell.parentElement.querySelector(`[data-room-${kind}-frame]`).hidden = !setting?.target;
        settingCell.hidden = !setting;
        settingCell.textContent = setting?.text ?? '';
        settingCell.classList.toggle('tracking-attention', !!setting && !setting.applied);
      }
    }
    renderVenueTracking(rooms, sessions, actor, elapsed);
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
  return { update, venueReady, venueBegin, venueResume, settingFrame, settingStatus, trackingPause, vrResume, poseFrame,
    active(value) { active = value; if (value) update(); else reset(); } };
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
