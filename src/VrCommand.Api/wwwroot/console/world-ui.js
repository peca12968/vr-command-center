import { ReplayScene } from './replay-scene.js';
import { mountCameras } from './camera-ui.js';
import { mountWorldCameraForm } from './world-camera-form.js';
import { mountWorldEventSearch } from './world-event-search.js';
import { mountWorldPolicyFrames } from './world-policy-frames.js';
import { mountSavedClips } from './saved-clips-ui.js';
import { mountWorldClipStatistics } from './world-clip-statistics.js';
import { recordedClock } from './mission-clock.js';

const $ = id => document.getElementById(id);
const time = milliseconds => (milliseconds / 1000).toFixed(2) + ' 秒';
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const eventNames = { ShotFired: '玩家射擊', ShotHit: '命中敵軍', EnemyEliminated: '擊殺敵軍', EnemyShot: '敵軍射擊', PlayerDamaged: '玩家受傷', ReloadStarted: '開始換彈', ReloadCompleted: '完成換彈' };
const shortId = id => id && id !== '00000000-0000-0000-0000-000000000000' ? id.slice(0, 8) : '—';
const roomName = room => room === 'all' ? '全部房間' : '房間 ' + room;
const LIVE_RETRY_DELAYS = [500, 1000, 2000];
const LIVE_IDLE_MILLISECONDS = 6000;
const isBeginWitness = witness => witness?.kind === 'tracking-begin' || witness?.kind === 'participation-begin';
const witnessLabels = { enemies: '敵軍', environment: '環境', 'tracking-begin': '追蹤開場', 'participation-begin': '有效姿態開場',
  'pose-interruption': '姿態中斷' };

export function mountWorld(getKey, unauthorized, describeEnemies, canWriteClips) {
  let active = false, scene, controller, epoch = 0, listEpoch = 0, listController, info, frame, geometry = '', mode = '', connected = false, received = 0;
  let connecting = false, stepping = false, savedLimit = null, savedFinished = false;
  let reviewPlayer = null, actors = new Map(), actorInitialized = false;
  let clipStart = null, clipEnd = null, clipPosition = null, clipPlayback = '';
  let eventContextRequest = null;
  let returnLiveSource = null, liveRetryTimer;
  let venueReview = null, venueAnchor = null;
  const cameras = mountCameras(getKey, unauthorized, () => scene, freeView);
  const cameraForm = mountWorldCameraForm(() => scene, freeView);
  const eventSearch = mountWorldEventSearch(response, readFrame, eventNames, () => {
    clearEventContext();
    if (frame) showEvents(frame);
    reviewControls();
  });
  const policyFrames = mountWorldPolicyFrames(response, readFrame);
  const savedClips = mountSavedClips(response, canWriteClips, loadClip);
  const clipStatistics = mountWorldClipStatistics(response);
  function message(text, error = false) { $('world-message').textContent = text; $('world-message').classList.toggle('replay-error', error); }
  function stop() {
    epoch++; clearTimeout(liveRetryTimer); liveRetryTimer = undefined;
    clearEventContext();
    clipStatistics.update(null, false);
    controller?.abort(); controller = null; connected = connecting = stepping = false;
    scene?.weather.pause(); scene?.draw(); $('world-pause').textContent = '繼續回放';
  }
  function stopList() { listEpoch++; listController?.abort(); listController = null; }
  function reset() {
    reviewPlayer = returnLiveSource = null; clearClip(); bindVenueReview(null);
    stop(); stopList(); info = frame = savedLimit = null; savedFinished = false; geometry = ''; mode = ''; cameras.reset(); cameraForm.reset(); reviewControls();
    $('world-recording').replaceChildren(); $('world-player').hidden = true; message('選取已錄製的場次，開始觀戰或回放。');
    recordingControls(); bindRooms([]);
    resetActors(); scene?.reset(); $('world-sound').textContent = '音效：關閉'; $('world-sound').disabled = true;
  }
  async function response(url, signal, { method = 'GET', body } = {}) {
    const key = getKey(); if (!key) throw new Error('請先登入。');
    const result = await fetch(url, { method, body, headers: {
      Authorization: 'Bearer ' + key, ...(body ? { 'Content-Type': 'application/json' } : {})
    }, signal, cache: 'no-store' });
    if (result.status === 401 && !signal?.aborted && getKey() === key) unauthorized();
    if (!result.ok) {
      let error; try { error = await result.json(); } catch { }
      throw Object.assign(new Error(error?.error || '觀戰服務回應 ' + result.status), { status: result.status });
    }
    return result;
  }
  async function refresh(target = null) {
    stopList();
    const request = listEpoch, key = getKey(); if (!active || !key) return;
    const controller = listController = new AbortController();
    const signal = target ? AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]) : controller.signal;
    try {
      const rows = await (await response('/api/world-recordings', signal)).json();
      if (request !== listEpoch || !active || getKey() !== key) return;
      const picker = $('world-recording'), selected = picker.value;
      picker.replaceChildren(...rows.map(row => {
        const option = document.createElement('option'); option.value = row.header.sessionId;
        option.dataset.complete = String(row.complete); option.dataset.accepted = String(row.acceptedSequence);
        option.textContent = `${row.missionName} · 房間 ${row.header.roomIds.join('、')} · ${row.header.origin} · ${row.complete ? '完整' : '錄製未封存'} · ${row.header.sessionId.slice(0, 8)}`;
        return option;
      }));
      if (target) {
        const row = rows.find(item => item.header.sessionId === target.sessionId);
        const begin = isBeginWitness(target.witness) ? target.witness : null;
        const archiveTarget = begin ? { ...target, complete: begin.archiveComplete, throughSequence: begin.archiveThroughSequence } : target;
        if (!row || !matchesTarget(row, archiveTarget)) {
          picker.prepend(new Option('原場次錄製目前無法讀取', ''));
          picker.value = '';
          recordingControls(); reviewControls();
          message('目前無法讀取原場次的錄製。請回到房間與場次重新開啟。', true);
          return;
        }
        picker.value = target.sessionId;
        resetRecording();
        if (target.venue) {
          const rooms = target.venue.rooms.flatMap(room => {
            const recording = rows.find(row => matchesTarget(row, room) && row.header.roomIds.length === 1
              && Number.isFinite(Date.parse(row.header.captureStartedAtUtc)));
            return recording ? [{ ...room, headerKey: JSON.stringify(recording.header) }] : [];
          });
          if (rooms.length > 1 && rooms.some(room => room.sessionId === target.sessionId)) bindVenueReview({ requestId: target.venue.requestId, rooms });
        }
        const limit = target.mode === 'replay' && !target.complete ? target.throughSequence : null;
        const sequence = target.playerId || target.witness ? target.throughSequence : target.mode === 'replay' ? 1 : null;
        const replayTarget = begin ? { ...target, archive: row }
          : target.witness?.kind === 'pose-interruption' ? { ...target, returnToLive: row.complete === false } : target;
        void connect(target.mode, 0, sequence, limit, replayTarget);
        return;
      }
      if (rows.some(row => row.header.sessionId === selected)) picker.value = selected;
      else if (selected) resetRecording();
      recordingControls(); reviewControls();
      if (!rows.length) message('目前沒有可讀取的世界錄製；等待遊戲伺服器開始發送。');
    } catch (error) {
      if (request === listEpoch && active) message(target ? '目前無法讀取原場次的錄製。請回到房間與場次重新開啟。' : error.message, true);
    } finally {
      if (listController === controller) listController = null;
    }
  }
  function matchesTarget(recording, target) {
    if (recording.header?.sessionId !== target.sessionId
      || (target.roomId != null && !recording.header.roomIds?.includes(target.roomId))) return false;
    if (isBeginWitness(target.witness)) {
      const { roomIds } = target.witness;
      if (!Number.isSafeInteger(recording.acceptedSequence) || typeof recording.complete !== 'boolean'
        || recording.header.roomIds?.length !== roomIds.length || !roomIds.every((room, index) => recording.header.roomIds[index] === room)
        || (target.archive && ['origin', 'calibration', 'captureStartedAtUtc'].some(key => recording.header[key] !== target.archive.header[key])))
        return false;
    }
    if (target.mode === 'live') return true;
    return recording.header.streamId === target.streamId && (target.complete
      ? recording.complete === true && recording.acceptedSequence === target.throughSequence
      : recording.acceptedSequence >= target.throughSequence);
  }
  function recordingControls() {
    const selected = $('world-recording').selectedOptions[0];
    $('world-live').disabled = !selected;
    $('world-replay').disabled = !(Number(selected?.dataset.accepted) > 0);
    $('world-replay').textContent = selected?.dataset.complete === 'false' ? '回放已保存片段' : '從頭回放';
  }
  function resetRecording() {
    reviewPlayer = returnLiveSource = null; clearClip(); bindVenueReview(null);
    stop(); cameras.bind(null); cameraForm.reset(); info = frame = savedLimit = null; savedFinished = false; geometry = ''; mode = '';
    bindRooms([]); resetActors(); delete $('world-canvas').dataset.sequence;
    recordingControls(); reviewControls(); $('world-player').hidden = true; message('已切換場次，請開始觀戰或回放。');
  }
  function bindRooms(ids) {
    const rooms = ids.length ? ['all', ...ids.map(String)] : [];
    $('world-room').replaceChildren(...rooms.map(room => {
      const option = document.createElement('option'); option.value = room; option.textContent = roomName(room); return option;
    }));
    const quick = $('world-room-quick');
    quick.hidden = ids.length < 2;
    quick.replaceChildren(...(quick.hidden ? [] : rooms.map(room => {
      const button = document.createElement('button'), title = document.createElement('strong'), count = document.createElement('span');
      button.type = 'button'; button.className = 'quiet'; button.dataset.worldRoom = room;
      button.setAttribute('aria-pressed', String(room === 'all'));
      title.textContent = roomName(room); count.textContent = '等待快照'; button.append(title, count);
      button.addEventListener('click', () => selectRoom(room));
      return button;
    })));
    showStatistics();
  }
  function selectRoom(room, center = true) {
    if (room !== 'all' && !info?.header.roomIds.includes(Number(room))) return;
    clearEventContext();
    $('world-room').value = room;
    const camera = $('world-camera');
    scene?.setAudioRoom(room);
    if (center && scene) {
      if (camera.value === 'overview' || camera.value === 'top') scene.preset(camera.value, room);
      else { scene.focus(room); camera.value = 'free'; }
    }
    for (const button of $('world-room-quick').children)
      button.setAttribute('aria-pressed', String(button.dataset.worldRoom === room));
    if (frame) { showActors(); showEnemyPolicy(); }
    showStatistics();
    if (mode === 'replay' && frame) showEvents(frame);
    reviewControls();
  }
  function freeView() {
    $('world-camera').value = 'free'; selectRoom('all', false);
  }
  function showRoomCounts(packet) {
    for (const button of $('world-room-quick').children) {
      const room = button.dataset.worldRoom;
      const players = packet.frame.players.filter(player => room === 'all' || player.roomId === Number(room));
      const enemies = packet.frame.enemies.filter(enemy => room === 'all' || enemy.roomId === Number(room));
      const count = button.lastElementChild;
      const text = `連線玩家 ${players.filter(player => player.connected).length}/${players.length} · 存活敵軍 ${enemies.filter(enemy => enemy.health > 0).length}/${enemies.length}`;
      if (count.textContent !== text) count.textContent = text;
    }
  }
  function showStatistics() {
    const room = $('world-room').value;
    const players = frame?.statistics.filter(player => (!reviewPlayer || player.playerId === reviewPlayer.id)
      && (room === 'all' || player.roomId === Number(room))) ?? [];
    $('world-statistics-heading').textContent = room && room !== 'all' ? `${roomName(room)} · 此快照已核對的統計` : '此快照已核對的統計';
    $('world-statistics-empty').hidden = !frame || players.length > 0;
    const table = $('world-statistics');
    const previous = new Map(Array.from(table.rows, row => [row.dataset.playerId, row]));
    const visible = new Set(players.map(player => player.playerId));
    for (const [id, row] of previous) if (!visible.has(id)) row.remove();
    let cursor = table.firstElementChild;
    for (const player of players) {
      const key = 'p:' + player.playerId;
      const values = [player.name, player.ammoUsed, player.kills, player.damageTaken, player.hitsReceived, player.accuracyPercent + '%', player.health];
      let row = previous.get(player.playerId);
      if (!row) {
        row = document.createElement('tr');
        row.dataset.playerId = player.playerId;
        for (const value of values) row.insertCell().textContent = value;
        const follow = document.createElement('button');
        follow.type = 'button'; follow.className = 'quiet small'; follow.textContent = '跟隨';
        follow.addEventListener('click', () => {
          if (!active || !frame || !scene || !actors.has(key)) return;
          selectActor(key);
          setCamera('follow');
        });
        row.insertCell().append(follow);
      } else {
        for (const [index, value] of values.entries()) {
          if (row.cells[index].textContent !== String(value)) row.cells[index].textContent = value;
        }
      }
      const follow = row.lastElementChild.firstElementChild;
      const label = `跟隨 ${player.name} · 房間 ${player.roomId} · ${shortId(player.playerId)}`;
      if (follow.getAttribute('aria-label') !== label) follow.setAttribute('aria-label', label);
      const unavailable = !actors.has(key);
      if (follow.disabled !== unavailable) follow.disabled = unavailable;
      if (row !== cursor) table.insertBefore(row, cursor);
      cursor = row.nextElementSibling;
    }
  }
  function canExtendSaved() {
    return active && mode === 'replay' && info?.header.sessionId === $('world-recording').value
      && !returnLiveSource && !info.complete && savedFinished && frame?.packet.sequence === savedLimit;
  }
  function clearClip() { clipStart = clipEnd = clipPosition = null; clipPlayback = ''; }
  function clipControls(idle) {
    const sequence = frame?.packet.sequence;
    $('world-clip-start').disabled = !idle;
    $('world-clip-end').disabled = !idle || !clipStart || sequence <= clipStart.sequence;
    $('world-clip-play').disabled = !idle || !clipEnd;
    $('world-clip-clear').disabled = !idle || !clipStart;
    const label = mark => `第 ${mark.sequence} 格（${time(mark.elapsedMilliseconds)}）`;
    let text = '暫停後可標記兩格，播放會在終點停下。';
    if (clipStart) text = `起點 ${label(clipStart)} · ${clipEnd ? '終點 ' + label(clipEnd) : '請選擇起點之後的一格作為終點'}`;
    if (clipPlayback === 'playing') text += ' · 片段播放中';
    if (clipPlayback === 'paused') text += ' · 片段已暫停';
    if (clipPlayback === 'finished') text += ' · 已到片段終點';
    const note = $('world-clip-status');
    if (note.textContent !== text) note.textContent = text;
  }
  function markClip(end) {
    if ($(end ? 'world-clip-end' : 'world-clip-start').disabled) return;
    const { sequence, elapsedMilliseconds } = frame.packet;
    const mark = { sequence, elapsedMilliseconds };
    if (end) clipEnd = mark;
    else {
      clipStart = mark;
      if (clipEnd && sequence >= clipEnd.sequence) clipEnd = null;
    }
    clipPlayback = ''; reviewControls();
  }
  function playClip(from = clipStart.sequence) {
    return connect('replay', 0, from, clipEnd.sequence, null, true);
  }
  function loadClip(clip) {
    clipStart = { sequence: clip.startFrame, elapsedMilliseconds: clip.startMilliseconds };
    clipEnd = { sequence: clip.endFrame, elapsedMilliseconds: clip.endMilliseconds };
    clipPlayback = ''; reviewControls();
  }
  function replayThroughFrame() {
    return info && Number.isInteger(savedLimit) ? Math.min(savedLimit, info.acceptedSequence) : info?.acceptedSequence;
  }
  function clearEventContext() {
    if (eventContextRequest) {
      eventContextRequest.abort(); eventContextRequest = null; stepping = false;
    }
    $('world-event-context-status').textContent = '';
  }
  async function markEventContext() {
    if ($('world-event-context').disabled) return;
    const { sessionId, streamId } = info.header;
    const { sequence: centerFrame, elapsedMilliseconds } = frame.packet;
    const throughFrame = replayThroughFrame();
    const request = eventContextRequest = new AbortController();
    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(8000)]);
    const note = $('world-event-context-status');
    stepping = true; reviewControls(); note.textContent = '正在核對事件前後的保存畫格…';
    try {
      const query = new URLSearchParams({ centerFrame, throughFrame });
      const value = await (await response(`/api/sessions/${sessionId}/world/frame-context?${query}`, signal)).json();
      if (eventContextRequest !== request) return;
      const { center, start, end } = value;
      const validMark = mark => Number.isSafeInteger(mark?.sequence) && Number.isSafeInteger(mark.elapsedMilliseconds)
        && mark.elapsedMilliseconds >= 0 && mark.sequence >= 1 && mark.sequence <= throughFrame;
      if (value.sessionId !== sessionId || value.streamId !== streamId || value.throughFrame !== throughFrame
        || center?.sequence !== centerFrame || center.elapsedMilliseconds !== elapsedMilliseconds || !validMark(start) || !validMark(end)
        || start.sequence > centerFrame || end.sequence < centerFrame || start.sequence < centerFrame - 149 || end.sequence > centerFrame + 150
        || start.elapsedMilliseconds > elapsedMilliseconds || start.elapsedMilliseconds < elapsedMilliseconds - 5000
        || end.elapsedMilliseconds < elapsedMilliseconds || end.elapsedMilliseconds > elapsedMilliseconds + 5000
        || (start.sequence === centerFrame && start.elapsedMilliseconds !== elapsedMilliseconds)
        || (end.sequence === centerFrame && end.elapsedMilliseconds !== elapsedMilliseconds)) throw new Error('回應的片段範圍不同。');
      if (start.sequence === end.sequence) {
        note.textContent = '事件附近只有一個保存畫格，已保留原標記。';
        return;
      }
      loadClip({ startFrame: start.sequence, startMilliseconds: start.elapsedMilliseconds,
        endFrame: end.sequence, endMilliseconds: end.elapsedMilliseconds });
      note.textContent = `已標記第 ${start.sequence} 至 ${end.sequence} 格，包含事件第 ${centerFrame} 格。`;
    } catch {
      if (eventContextRequest === request) note.textContent = '無法核對事件片段，已保留原標記。';
    } finally {
      if (eventContextRequest === request) { eventContextRequest = null; stepping = false; reviewControls(); }
    }
  }
  function reviewControls() {
    const recent = $('world-recent');
    const canReturn = Boolean(returnLiveSource);
    recent.hidden = mode !== 'live' && !canReturn;
    recent.disabled = !active || (!canReturn && (mode !== 'live' || !connected || !received || !(frame?.packet.sequence > 1)));
    const recentLabel = canReturn ? '返回即時觀戰' : '回看最近 10 秒';
    if (recent.textContent !== recentLabel) recent.textContent = recentLabel;
    const showing = active && mode === 'replay' && info?.header.sessionId === $('world-recording').value && Boolean(frame);
    const idle = showing && !connected && !connecting && !stepping;
    const venueAvailable = showing && info.complete && venueReview?.rooms.some(room => room.sessionId === info.header.sessionId && room.headerKey === geometry);
    $('world-venue-review').hidden = !venueAvailable;
    for (const button of $('world-venue-rooms').children)
      button.disabled = !idle || !venueAvailable || button.dataset.venueSession === info.header.sessionId;
    clipControls(idle);
    const clipRoom = $('world-room').value;
    clipStatistics.update(showing && clipEnd ? { sessionId: info.header.sessionId, streamId: info.header.streamId,
      roomIds: info.header.roomIds, fromFrame: clipStart.sequence, throughFrame: clipEnd.sequence,
      roomId: clipRoom === 'all' ? null : Number(clipRoom), playerId: reviewPlayer?.id ?? null } : null, idle);
    $('world-review').hidden = !showing;
    $('world-frame-back').disabled = !idle || frame.packet.sequence <= 1;
    const throughFrame = replayThroughFrame();
    savedClips.update(showing ? { sessionId: info.header.sessionId, streamId: info.header.streamId, roomIds: info.header.roomIds, throughFrame, complete: info.complete } : null,
      idle, clipEnd ? { startFrame: clipStart.sequence, endFrame: clipEnd.sequence } : null);
    $('world-frame-next').disabled = !idle || frame.packet.sequence >= throughFrame;
    const extend = $('world-frame-extend');
    extend.hidden = !canExtendSaved();
    extend.disabled = extend.hidden || !idle;
    $('world-review-player-scope').hidden = !showing || !reviewPlayer;
    $('world-review-player-name').textContent = reviewPlayer ? `檢討玩家 ${reviewPlayer.name} · ${shortId(reviewPlayer.id)}` : '';
    eventSearch.update(showing ? { sessionId: info.header.sessionId, streamId: info.header.streamId,
      throughFrame, room: $('world-room').value, playerId: reviewPlayer?.id ?? null, frameSequence: frame.packet.sequence, idle } : null);
    $('world-event-context').disabled = !idle || !filteredEvents(frame).length;
    policyFrames.update(showing ? { sessionId: info.header.sessionId, streamId: info.header.streamId,
      throughFrame, room: $('world-room').value, frameSequence: frame.packet.sequence, idle } : null);
  }
  function filteredEvents(value, players = new Map(value.statistics.map(player => [player.playerId.toLowerCase(), player]))) {
    const room = $('world-room').value, kind = eventSearch.kind();
    return value.packet.events.filter(event => (!kind || event.kind === kind)
      && (!reviewPlayer || event.playerId.toLowerCase() === reviewPlayer.id)
      && (room === 'all' || players.get(event.playerId.toLowerCase())?.roomId === Number(room)));
  }
  function showEvents(value) {
    const players = new Map(value.statistics.map(player => [player.playerId.toLowerCase(), player]));
    const rows = filteredEvents(value, players).map(event => {
      const row = document.createElement('tr');
      const player = players.get(event.playerId.toLowerCase());
      for (const text of [event.sequence, eventNames[event.kind] ?? event.kind, player ? `${player.name} · 房間 ${player.roomId}` : shortId(event.playerId),
        shortId(event.enemyId), event.kind === 'PlayerDamaged' ? event.damage : '—']) {
        const cell = document.createElement('td'); cell.textContent = text; row.append(cell);
      }
      return row;
    });
    $('world-events').replaceChildren(...rows);
    $('world-event-table').hidden = !rows.length;
    $('world-no-events').hidden = Boolean(rows.length);
  }
  function replayAt(milliseconds, sequence) {
    const sameRecording = info?.header.sessionId === $('world-recording').value;
    if (mode === 'live' && sameRecording && !info.complete) savedLimit = 'latest';
    return connect('replay', milliseconds, sequence);
  }
  function replayFromCurrent() {
    const sameRecording = info?.header.sessionId === $('world-recording').value;
    const sequence = sameRecording ? frame?.packet.sequence : undefined;
    if (clipPlayback === 'paused' || clipPlayback === 'playing') return playClip(clipPosition);
    return replayAt(0, sequence);
  }
  function openLive() {
    const target = returnLiveSource ? { mode: 'live', sessionId: $('world-recording').value, sourceKey: returnLiveSource } : null;
    returnLiveSource = null;
    bindVenueReview(null);
    return connect('live', 0, null, null, target);
  }
  function retryLive(id, key, sourceKey, request, attempt) {
    if (!sourceKey || info?.complete || attempt >= LIVE_RETRY_DELAYS.length) return false;
    liveRetryTimer = setTimeout(() => {
      if (request === epoch && active && getKey() === key && $('world-recording').value === id)
        void connect('live', 0, null, null, { mode: 'live', sessionId: id, sourceKey }, false, attempt + 1);
    }, LIVE_RETRY_DELAYS[attempt]);
    message(`即時觀戰中斷，正在重新連接（${attempt + 1}/${LIVE_RETRY_DELAYS.length}）。`, true);
    return true;
  }
  function toggleRecent() {
    if ($('world-recent').disabled) return;
    if (returnLiveSource) return openLive();
    const { sequence, elapsedMilliseconds } = frame.packet;
    returnLiveSource = geometry;
    return elapsedMilliseconds <= 10000 ? connect('replay', 0, 1, sequence)
      : connect('replay', elapsedMilliseconds - 10000, null, sequence);
  }
  function status() {
    reviewControls();
    if (!info) return;
    $('world-sound').disabled = info.header.environmentVersion !== 1 && info.header.combatAudioVersion !== 1 || scene?.weather.audio.state === 'loading';
    const audio = scene?.weather.audio.state || 'off';
    $('world-sound').textContent = ({ on: '音效：開啟', off: '音效：關閉', loading: '音效載入中…', error: '音效：重試開啟' })[audio];
    $('world-sound').setAttribute('aria-pressed', String(audio === 'on'));
    const phase = frame ? phases[frame.packet.frame.phase] : '等待第一份快照';
    const clock = recordedClock(info.header, frame?.packet.frame.tick);
    const saved = mode === 'replay' && typeof savedLimit === 'number';
    const enemies = frame?.packet.frame.enemies;
    const enemyCount = enemies ? ` · 敵軍 ${enemies.length} 名（${enemies.filter(enemy => enemy.health > 0).length} 存活）` : '';
    $('world-status').textContent = `${info.header.origin} · ${info.complete ? '錄製已核對封存' : '錄製未封存'}${saved ? ` · 已保存片段至第 ${savedLimit} 格 · 快照階段 ${phase}` : ' · ' + phase}${clock ? ' · ' + clock : ''}${enemyCount}`;
    if (mode === 'live') {
      const captured = info.header.captureStartedAtUtc ? Date.parse(info.header.captureStartedAtUtc) + (frame?.packet.elapsedMilliseconds ?? 0) : NaN;
      const age = Date.now() - captured, unknown = !Number.isFinite(age), clockInvalid = age < -1000;
      const stale = !connected || !received || performance.now() - received > 1500 || age > 1500;
      if (stale || unknown || clockInvalid) { scene?.weather.pause(); scene?.draw(); }
      $('world-freshness').textContent = info.complete ? '場次已封存' : unknown ? '擷取時間未知' : clockInvalid ? '來源時鐘未同步' : stale ? '快照已中斷或過期' : '正在接收快照';
      $('world-freshness').classList.toggle('replay-error', (stale || unknown || clockInvalid) && !info.complete);
    } else {
      const atSavedEnd = saved && savedFinished && frame?.packet.sequence === savedLimit;
      $('world-freshness').textContent = atSavedEnd ? (returnLiveSource ? '已到即時回看尾端' : '已到已保存片段尾端')
        : connected ? '回放中' : '回放已暫停／結束';
      $('world-freshness').classList.remove('replay-error');
      $('world-pause').textContent = connected ? '暫停回放' : '繼續回放';
    }
    if (!connected) { scene?.weather.pause(); scene?.draw(); }
  }
  function resetActors() {
    actors.clear(); actorInitialized = false;
    $('world-actor').replaceChildren(new Option('未選取角色', ''));
    selectActor('');
  }
  function selectActor(key) {
    const choice = actors.get(key);
    if (key && !choice) return;
    const camera = $('world-camera');
    $('world-actor').value = key;
    camera.querySelector('[value=follow]').disabled = !choice;
    if (!choice && camera.value === 'follow') { camera.value = 'free'; if (scene) scene.follow = false; }
    if (scene && scene.selected !== key) scene.select(key);
    const actor = choice?.actor;
    const text = actor ? `${choice.name} · 房間 ${actor.roomId} · 血量 ${actor.health}`
      + (key.startsWith('p:') ? ` · 彈匣 ${actor.magazine}／備彈 ${actor.reserve} · ${actor.connected ? '參戰中' : '未參戰'} · 頭手來源 ${actor.rig.kind}` : '')
      + ` · ${actor.id}` : '可點選目前房間的角色，或從選單選取。';
    const details = $('world-actor-info');
    if (details.textContent !== text) details.textContent = text;
  }
  function setCamera(view) {
    if (!scene) return;
    $('world-camera').value = view;
    if (view === 'follow') { scene.follow = true; scene.draw(); }
    else if (view === 'free') scene.follow = false;
    else scene.preset(view, $('world-room').value);
  }
  function showActors() {
    const picker = $('world-actor'), room = $('world-room').value;
    const visible = actor => room === 'all' || actor.roomId === Number(room);
    const { players, enemies } = frame.packet.frame;
    const stats = new Map(frame.statistics.map(player => [player.playerId, player]));
    actors = new Map();
    for (const actor of players.filter(visible)) {
      const player = stats.get(actor.id);
      actors.set('p:' + actor.id, { actor, name: player?.roomId === actor.roomId ? player.name : '玩家' });
    }
    for (const actor of enemies.filter(visible)) actors.set('e:' + actor.id, { actor, name: '敵軍' });
    const selected = actors.has(picker.value) ? picker.value : actorInitialized ? '' : actors.keys().next().value ?? '';
    actorInitialized ||= actors.size > 0;
    const labels = [...actors].map(([key, { actor, name }]) => [key, `${name} · 房間 ${actor.roomId} · ${shortId(actor.id)}`]);
    if (picker.options.length !== labels.length + 1 || labels.some(([key, label], i) =>
      picker.options[i + 1].value !== key || picker.options[i + 1].textContent !== label))
      picker.replaceChildren(new Option('未選取角色', ''), ...labels.map(([key, label]) => new Option(label, key)));
    selectActor(selected);
  }
  function show(value, single = false) {
    const previous = single ? null : frame?.packet.frame;
    if (frame?.packet.sequence !== value.packet.sequence) clearEventContext();
    frame = value;
    info.durationMilliseconds = Math.max(info.durationMilliseconds, value.packet.elapsedMilliseconds);
    info.acceptedSequence = Math.max(info.acceptedSequence, value.packet.sequence);
    const age = info.header.captureStartedAtUtc ? Date.now() - Date.parse(info.header.captureStartedAtUtc) - value.packet.elapsedMilliseconds : NaN;
    const continuous = connected && (mode === 'replay' || (Number.isFinite(age) && age >= -1000 && age <= 1500));
    showActors();
    scene.show(value.packet.frame, previous, value.packet.events.filter(event => event.hasRay), { weather: value.packet.weather, lightning: value.packet.lightning }, continuous);
    const packet = value.packet;
    $('world-time').textContent = `${time(packet.elapsedMilliseconds)} / ${time(info.durationMilliseconds)} · 幀 ${packet.sequence}`;
    $('world-environment').textContent = `${packet.weather} · ${packet.frame.night ? '夜間' : '日間'} · ${packet.lightning ? '雷電啟用' : '無雷電'}${packet.suspended ? ' · 管理中斷暫停' : ''}`;
    showEnemyPolicy();
    $('world-timeline').max = String(Math.max(info.durationMilliseconds, packet.elapsedMilliseconds, 1)); $('world-timeline').value = String(packet.elapsedMilliseconds);
    showRoomCounts(packet); showStatistics();
    if (mode === 'replay') showEvents(value);
    received = performance.now(); $('world-canvas').dataset.sequence = String(packet.sequence); status();
  }
  function step(offset) { if (frame) return readFrame(frame.packet.sequence + offset); }
  function clearVenueAnchor() {
    venueAnchor = null;
    $('world-venue-message').textContent = '';
  }
  function bindVenueReview(value) {
    venueReview = value;
    clearVenueAnchor();
    $('world-venue-rooms').replaceChildren(...(value?.rooms ?? []).map(room => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'quiet'; button.disabled = true;
      button.dataset.venueSession = room.sessionId; button.dataset.venueAlignRoom = room.roomId;
      button.textContent = `對齊房間 ${room.roomId}`;
      button.addEventListener('click', () => switchVenueRoom(room));
      return button;
    }));
  }
  async function switchVenueRoom(room) {
    const view = venueReview, picker = $('world-recording'), sessionId = picker.value;
    if (!view?.rooms.includes(room) || !active || mode !== 'replay' || !info?.complete || !frame
      || !view.rooms.some(source => source.sessionId === sessionId && source.headerKey === geometry)
      || sessionId !== info.header.sessionId || room.sessionId === sessionId || connected || connecting || stepping) return;
    const anchor = venueAnchor ?? { fromSessionId: sessionId, fromFrame: frame.packet.sequence,
      captured: Date.parse(info.header.captureStartedAtUtc) + frame.packet.elapsedMilliseconds };
    if (!Number.isFinite(anchor.captured)) return;
    controller?.abort(); controller = new AbortController();
    const request = ++epoch, signal = AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]);
    const note = $('world-venue-message');
    stepping = true; reviewControls(); note.textContent = '正在核對同批房間的原擷取時間…';
    try {
      const query = new URLSearchParams({ fromSessionId: anchor.fromSessionId, fromFrame: anchor.fromFrame, roomId: room.roomId });
      const result = await (await response(`/api/venue/closure/${encodeURIComponent(view.requestId)}/replay-at?${query}`, signal)).json();
      if (request !== epoch || !active || venueReview !== view || picker.value !== sessionId) return;
      const recording = result.recording, value = result.frame, packet = value?.packet;
      const captured = Date.parse(recording?.header?.captureStartedAtUtc) + packet?.elapsedMilliseconds;
      const gap = anchor.captured - captured;
      if (result.requestId !== view.requestId || result.fromSessionId !== anchor.fromSessionId || result.fromFrame !== anchor.fromFrame
        || result.roomId !== room.roomId || !recording || !matchesTarget(recording, room) || JSON.stringify(recording.header) !== room.headerKey
        || !Number.isSafeInteger(packet?.sequence) || packet.sequence < 1 || packet.sequence > room.throughSequence
        || !Number.isSafeInteger(recording.durationMilliseconds) || !Number.isSafeInteger(packet.elapsedMilliseconds)
        || packet.elapsedMilliseconds < 0 || packet.elapsedMilliseconds > recording.durationMilliseconds
        || !Array.isArray(packet.frame?.players) || !Array.isArray(packet.frame.enemies) || !Array.isArray(packet.events) || !Array.isArray(value.statistics)
        || (room.sessionId === anchor.fromSessionId && packet.sequence !== anchor.fromFrame)
        || Date.parse(result.capturedAtUtc) !== anchor.captured || Date.parse(result.frameCapturedAtUtc) !== captured || !(gap >= 0 && gap <= 500)
        || ![...picker.options].some(option => option.value === room.sessionId)) throw new Error('Recording or frame differs.');
      picker.value = room.sessionId;
      info = recording; frame = savedLimit = null; savedFinished = false; reviewPlayer = returnLiveSource = null;
      showRecording(room.roomId); recordingControls(); show(value, true);
      venueAnchor = anchor;
      $('world-frame-message').textContent = `已停在第 ${packet.sequence} 格。`;
      note.textContent = `已對齊房間 ${room.roomId} · ${gap ? `畫格早於對照時間 ${gap} 毫秒` : '相同擷取時間'}。`;
    } catch (error) {
      if (request === epoch) note.textContent = error.status === 409
        ? '此房找不到可對齊的封存畫格，已保留目前畫面。'
        : '無法核對同批房間的原錄製，已保留目前畫面。';
    } finally {
      if (request === epoch) { stepping = false; controller = null; reviewControls(); }
    }
  }
  async function readFrame(sequence, stillCurrent = () => true, matches = () => true) {
    const id = $('world-recording').value;
    if (!active || mode !== 'replay' || connected || connecting || stepping || !frame || info.header.sessionId !== id) return false;
    if (sequence < 1 || sequence > info.acceptedSequence || (Number.isInteger(savedLimit) && sequence > savedLimit)) return false;
    clipPlayback = '';
    controller?.abort(); controller = new AbortController();
    const request = ++epoch, signal = AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]);
    stepping = true; reviewControls(); $('world-frame-message').textContent = '正在讀取保存快照…';
    try {
      const value = await (await response(`/api/sessions/${id}/world/frames/${sequence}`, signal)).json();
      if (request !== epoch || !active || id !== $('world-recording').value || !stillCurrent()) return false;
      if (value.packet.sequence !== sequence || !matches(value)) throw new Error('回應的快照不同。');
      clearVenueAnchor(); show(value, true); $('world-frame-message').textContent = `已停在第 ${sequence} 格。`;
      return true;
    } catch (error) {
      if (request === epoch) $('world-frame-message').textContent = '讀取快照失敗，請再試一次。';
      return false;
    } finally {
      if (request === epoch) { stepping = false; controller = null; reviewControls(); }
    }
  }
  async function extendSaved() {
    if (!canExtendSaved() || connecting || connected || stepping) return;
    const { sessionId: id, streamId, origin } = info.header, previous = savedLimit;
    controller = new AbortController();
    const request = ++epoch, signal = AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]);
    const note = $('world-frame-message');
    connecting = true; reviewControls(); note.textContent = '正在檢查新保存的快照…';
    try {
      const latest = await (await response(`/api/sessions/${id}/world`, signal)).json();
      if (request !== epoch || !canExtendSaved()) return;
      const tail = latest.acceptedSequence;
      if (latest.header?.sessionId !== id || latest.header.streamId !== streamId || latest.header.origin !== origin
        || !Number.isSafeInteger(tail) || tail < previous || typeof latest.complete !== 'boolean') throw new Error('保存尾端或錄製來源不符。');
      const selected = $('world-recording').selectedOptions[0];
      selected.dataset.accepted = String(tail); selected.dataset.complete = String(latest.complete); recordingControls();
      if (tail > previous) {
        connect('replay', 0, previous + 1, tail);
      } else {
        info = latest; status();
        note.textContent = latest.complete ? '此錄製已封存，最後一格維持不變。' : '目前沒有新的保存快照。';
      }
    } catch (error) {
      if (request === epoch) note.textContent = '檢查保存尾端失敗，請再試一次。';
    } finally {
      if (request === epoch) { connecting = false; controller = null; reviewControls(); }
    }
  }
  function matchesWitness(packet, target, header) {
    const { kind, setting, population, appliedAtSequence, elapsedMilliseconds, roomIds, inherited } = target.witness;
    if (kind === 'pose-interruption') {
      const { observedSequence, playerIds } = target.witness;
      const frame = packet.frame;
      if (packet.observedSequence !== observedSequence || packet.suspended !== false || frame?.phase !== 'Running'
        || !Array.isArray(frame.players)) return false;
      return playerIds.every(id => {
        const players = frame.players.filter(player => player.id === id && player.roomId === target.roomId);
        return players.length === 1 && Number.isInteger(players[0].health) && players[0].health > 0 && players[0].health <= 100
          && (players[0].connected === false || (players[0].connected === true && players[0].rig?.kind === 'None'));
      });
    }
    if (isBeginWitness(target.witness)) {
      const frame = packet.frame;
      const mr = header.calibration === 'quest-room-mr-v1';
      if (kind === 'participation-begin' && (mr ? header.origin !== 'GameServer' : header.calibration !== 'uncalibrated-vr')) return false;
      const allowSimulated = kind === 'participation-begin' && !mr;
      if (packet.observedSequence !== appliedAtSequence - 1 || packet.elapsedMilliseconds !== elapsedMilliseconds
        || packet.suspended !== false || frame?.phase !== 'Preparing' || frame.tick !== 0
        || !Array.isArray(frame.players) || frame.players.length !== roomIds.length * 5) return false;
      const players = new Set(), counts = new Map(roomIds.map(room => [room, 0]));
      for (const player of frame.players) {
        const id = typeof player?.id === 'string' ? player.id.toLowerCase() : '';
        if (!id || players.has(id) || !counts.has(player.roomId)
          || player.connected !== true || (player.rig?.kind !== 'Tracked' && !(allowSimulated && player.rig?.kind === 'Simulated'))
          || !Number.isInteger(player.health)
          || player.health < 1 || player.health > 100) return false;
        players.add(id);
        counts.set(player.roomId, counts.get(player.roomId) + 1);
      }
      return roomIds.every(room => counts.get(room) === 5);
    }
    if (!Number.isSafeInteger(packet.observedSequence) || packet.observedSequence < setting.appliedAtSequence) return false;
    if (kind === 'environment') return packet.weather === setting.weather && packet.frame.night === (setting.timeOfDay === 'Night')
      && packet.lightning === setting.lightning;
    const enemies = packet.frame.enemies.filter(enemy => enemy.roomId === target.roomId);
    const local = packet.frame.roomEnemyPolicies?.find(row => row.roomId === target.roomId);
    if (typeof inherited === 'boolean' && inherited !== !local) return false;
    const policy = local ?? packet.frame;
    return policy.behavior === setting.behavior && policy.autoAttack === setting.autoAttack
      && enemies.length === population.present && enemies.filter(enemy => enemy.health > 0).length === population.alive;
  }
  function showEnemyPolicy() {
    const packet = frame?.packet.frame, room = $('world-room').value;
    if (!packet) return;
    const local = packet.roomEnemyPolicies?.find(row => row.roomId === Number(room));
    const { behavior, autoAttack } = local ?? packet;
    const overrideRooms = packet.roomEnemyPolicies?.map(row => row.roomId) ?? [];
    $('world-enemy-policy').textContent = ['Hold', 'Patrol', 'Advance'].includes(behavior) && typeof autoAttack === 'boolean'
      ? (local ? `房間 ${room} 策略 · ` : '此快照的敵軍策略 · ') + describeEnemies({ behavior, autoAttack })
        + (room === 'all' && overrideRooms.length ? ` · 分房策略 ${overrideRooms.join('、')}` : '') : '';
  }
  function showRecording(roomId) {
    const key = JSON.stringify(info.header);
    scene ??= new ReplayScene($('world-canvas'), selectActor, () => { $('world-camera').value = 'free'; }, key => actors.has(key));
    $('world-player').hidden = false;
    if (key !== geometry) {
      clearClip();
      scene.load(info.header); geometry = key; frame = null;
      bindRooms(info.header.roomIds); resetActors();
      $('world-camera').value = 'overview';
    }
    if (roomId != null) {
      $('world-camera').value = 'top';
      selectRoom(String(roomId));
    }
    scene.resize(); $('world-name').textContent = info.missionName;
    cameras.bind(info.header.sessionId);
    cameraForm.bind(info.header.sessionId);
    message(`${info.header.origin} · ${info.header.rulesVersion} · ${info.header.assetSet === 'player-fire-v1' ? '軍事掩體／玩家及敵軍射擊效果 v1（依保存射線）' : info.header.assetSet === 'combat-effects-v1' ? '軍事掩體／敵軍射擊閃光及後座 v1（依保存射線）' : info.header.assetSet === 'armed-combatants-v1' ? '軍事掩體／敵軍雙手持槍／換彈 v1（合成姿勢）' : info.header.assetSet === 'weapon-actions-v1' ? '軍事掩體／人形敵軍／換彈動作 v1（合成手套非追蹤）' : info.header.assetSet === 'combatants-v1' ? '軍事掩體／步槍／人形敵軍 v1（命中採粗略包圍盒）' : info.header.assetSet === 'service-rifle-v1' ? '軍事掩體／玩家步槍 v1（命中／碰撞採包圍盒）' : info.header.assetSet === 'field-props-v1' ? '軍事掩體 v1（命中／碰撞採包圍盒）' : '基本幾何素材'} · ${info.header.calibration === 'quest-room-mr-v1' ? 'Quest 3 MR 錄製設定。' : 'VR 未校正。'}頭手來源請見角色資訊。${info.header.environmentVersion === 1 ? '環境聲光 v1 依保存的模擬時間重建，非原始音軌。' : '舊錄製沒有聲光效果版本，僅保留原有光霧顯示。'}`);
    status();
  }
  async function connect(nextMode, milliseconds = 0, sequence = null, replayLimit = savedLimit, target = null, clip = false, liveAttempt = 0) {
    const id = $('world-recording').value, key = getKey(); if (!active || !id || !key) return;
    stop(); mode = nextMode; clearVenueAnchor();
    const expectedGeometry = target?.sourceKey ?? returnLiveSource ?? (clip ? geometry : null);
    clipPlayback = clip ? 'playing' : '';
    clipPosition = clip ? sequence : null;
    const own = controller = new AbortController(), request = epoch;
    const playerReview = Boolean(target?.playerId), witness = target?.witness;
    const witnessLabel = witnessLabels[witness?.kind];
    const signal = playerReview || witness ? AbortSignal.any([own.signal, AbortSignal.timeout(8000)]) : own.signal;
    if (nextMode === 'live') { received = 0; savedLimit = null; savedFinished = false; reviewPlayer = null; clearClip(); }
    const limit = nextMode === 'live' ? null : replayLimit;
    let hasHeader = false, reachedSavedEnd = false, lastSequence = sequence === null ? null : sequence - 1;
    let recentJump = Boolean(target?.sourceKey || returnLiveSource);
    let playerFrame = null, playerComplete = false, witnessFrame = null;
    let lastLiveSequence = liveAttempt ? frame?.packet.sequence ?? 0 : 0;
    let idleTimer, idleExpired = false, transportFailure = false;
    function watchLive() {
      if (nextMode !== 'live') return;
      clearTimeout(idleTimer);
      if (hasHeader && info?.complete) return;
      idleTimer = setTimeout(() => {
        if (request !== epoch || own.signal.aborted || (hasHeader && info?.complete)) return;
        idleExpired = true; own.abort();
      }, LIVE_IDLE_MILLISECONDS);
    }
    connecting = true; reviewControls(); $('world-frame-message').textContent = '';
    message(nextMode === 'live' ? '正在連接即時觀戰…' : '正在讀取已保存快照…');
    watchLive();
    try {
      const position = sequence === null ? `fromMs=${Math.round(milliseconds)}` : `fromFrame=${sequence}`;
      const url = `/api/sessions/${id}/world/watch?mode=${nextMode}&${position}&rate=${$('world-speed').value}${limit === null ? '' : `&throughFrame=${limit}`}`;
      let stream;
      try { stream = await response(url, signal); }
      catch (error) {
        transportFailure = error instanceof TypeError || error.status === 408 || (error.status >= 500 && error.status <= 599);
        throw error;
      }
      if (request !== epoch || !active) return;
      if (!stream.body || !stream.headers.get('content-type')?.startsWith('text/event-stream')) throw new Error('缺少觀戰串流。');
      connected = true; connecting = false; $('world-pause').textContent = mode === 'live' ? '從此刻回放' : '暫停回放';
      const reader = stream.body.getReader(), decoder = new TextDecoder(); let buffer = '';
      try {
        while (true) {
          let chunk;
          try { chunk = await reader.read(); }
          catch (error) { transportFailure = true; throw error; }
          const { done, value } = chunk; if (done) break;
          if (request !== epoch || !active) return;
          buffer += decoder.decode(value, { stream: true });
          if (buffer.length > 2 * 1024 * 1024) throw new Error('觀戰資料超過單份快照限制。');
          let end;
          while ((end = buffer.indexOf('\n\n')) >= 0) {
            const event = buffer.slice(0, end); buffer = buffer.slice(end + 2);
            const lines = event.split('\n'), type = lines.find(line => line.startsWith('event: '))?.slice(7), raw = lines.find(line => line.startsWith('data: '))?.slice(6);
            if (!raw) continue; const data = JSON.parse(raw);
            const sourceRecord = ['header', 'status', 'complete', 'saved-end'].includes(type);
            if (expectedGeometry && (sourceRecord ? JSON.stringify(data.header) !== expectedGeometry : type === 'frame' && !hasHeader))
              throw new Error('回應的錄製來源不同。');
            if (sourceRecord || type === 'frame') watchLive();
            if (type === 'header') {
              if (hasHeader || data.header?.sessionId !== id || (target && !matchesTarget(data, target)))
                throw new Error('回應的錄製場次或來源不同。');
              if (limit !== null) {
                if (!Number.isSafeInteger(data.acceptedSequence) || data.acceptedSequence < 1 || (limit !== 'latest' && limit !== data.acceptedSequence))
                  throw new Error('已保存片段的尾端不符。');
                if (!clip) savedLimit = data.acceptedSequence;
              }
              hasHeader = true;
              if (!clip) { info = data; savedFinished = false; }
              showRecording(target?.roomId);
            } else if (type === 'frame') {
              if (nextMode === 'live') {
                const current = data.packet.sequence;
                if (!hasHeader || !Number.isSafeInteger(current) || current < 1 || current < lastLiveSequence)
                  throw new Error('即時觀戰的快照序號不符。');
                if (current === lastLiveSequence) continue;
                lastLiveSequence = current; liveAttempt = 0;
              }
              if (playerReview) {
                if (!hasHeader || playerFrame || data.packet.sequence !== target.throughSequence
                  || data.packet.frame.phase !== 'Ended' || data.packet.throughCombatSequence !== target.throughCombatSequence)
                  throw new Error('回應的最終快照或戰鬥封存序號不同。');
                playerFrame = data;
                continue;
              }
              if (limit !== null) {
                const current = data.packet.sequence;
                if (!hasHeader || reachedSavedEnd || !Number.isSafeInteger(current) || current < 1 || current > (clip ? limit : savedLimit)
                  || (lastSequence !== null && current !== lastSequence + 1)) throw new Error('已保存片段的快照序號不符。');
                lastSequence = current;
                if (clip) clipPosition = current;
              }
              if (witness) {
                if (witnessFrame || !matchesWitness(data.packet, target, info.header))
                  throw new Error(`回應快照的${witnessLabel}或指令序號不同。`);
                witnessFrame = data;
              } else { show(data, recentJump); recentJump = false; }
            }
            else if (type === 'complete' && playerReview) {
              if (!playerFrame || playerComplete || !matchesTarget(data, target)) throw new Error('回應的世界封存範圍不同。');
              info = data; playerComplete = true;
            }
            else if (type === 'status' || type === 'complete') { if (!clip) { info = data; status(); } }
            else if (type === 'saved-end' && limit !== null) {
              const tail = clip ? limit : savedLimit;
              if (!hasHeader || reachedSavedEnd || data.acceptedSequence !== tail || lastSequence !== tail
                || (witness && !matchesTarget(data, target)))
                throw new Error('已保存片段未完整讀取。');
              reachedSavedEnd = true;
              if (!clip) { info = data; savedFinished = true; }
            }
          }
        }
      } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
      if (request === epoch) {
        if (nextMode === 'live' && (idleExpired || !info?.complete)) {
          transportFailure = true;
          throw new Error('即時觀戰串流已關閉。');
        }
        if (limit !== null && !reachedSavedEnd) throw new Error('尚未讀到已保存片段尾端。');
        if (playerReview && !playerComplete) throw new Error('尚未讀到原場次的封存結尾。');
        connected = false;
        if (clip) clipPlayback = 'finished';
        status();
        if (witness) {
          if (target.archive) {
            info = target.archive;
            savedLimit = info.complete ? null : info.acceptedSequence;
            savedFinished = savedLimit === sequence;
          }
          if (target.returnToLive) returnLiveSource = geometry;
          show(witnessFrame, true);
          let text = `已停在第 ${target.throughSequence} 格的${witnessLabel}快照。`;
          if (witness.kind === 'participation-begin') {
            const players = witnessFrame.packet.frame.players;
            const tracked = players.filter(player => player.rig.kind === 'Tracked').length;
            text += ` 此格追蹤 ${tracked} 席、合成 ${players.length - tracked} 席。`;
          } else if (witness.kind === 'pose-interruption') {
            text += ` 房間 ${target.roomId} · 席位 ${witness.seats.join('、')}。`;
          }
          $('world-frame-message').textContent = text;
        }
        if (playerReview) {
          reviewPlayer = { id: target.playerId, name: target.playerName };
          show(playerFrame, true);
          if (target.latestDamage) void eventSearch.fromLatest('PlayerDamaged', playerFrame, value => filteredEvents(value).length);
          else void eventSearch.fromStart();
        }
      }
    } catch (error) {
      if (request === epoch && (!own.signal.aborted || idleExpired)) {
        if (playerReview || witness) resetRecording();
        if (clip) clipPlayback = '';
        connected = connecting = false; status();
        const original = hasHeader ? geometry : liveAttempt ? expectedGeometry : null;
        if (nextMode === 'live' && (idleExpired || transportFailure) && retryLive(id, key, original, request, liveAttempt)) return;
        message('觀戰已中斷：' + (idleExpired ? '等待即時資料逾時' : error.message) + '；可重新連接。', true);
      }
    } finally { clearTimeout(idleTimer); }
  }
  $('world-refresh').addEventListener('click', () => refresh());
  $('world-sound').addEventListener('click', async () => { if (scene?.weather.version === 1 || scene?.weather.audio.combat.version === 1) { const pending = scene.weather.audio.toggle(); status(); await pending; if (active && getKey()) status(); } });
  $('world-recording').addEventListener('change', resetRecording);
  $('world-live').addEventListener('click', openLive);
  $('world-recent').addEventListener('click', toggleRecent);
  $('world-replay').addEventListener('click', () => {
    returnLiveSource = null;
    savedLimit = $('world-recording').selectedOptions[0]?.dataset.complete === 'false' ? 'latest' : null;
    connect('replay', 0, 1);
  });
  $('world-pause').addEventListener('click', () => {
    if (mode === 'replay' && (connected || clipPlayback === 'playing')) {
      if (clipPlayback === 'playing') clipPlayback = 'paused';
      stop(); status();
    } else replayFromCurrent();
  });
  $('world-frame-back').addEventListener('click', () => step(-1));
  $('world-frame-next').addEventListener('click', () => step(1));
  $('world-frame-extend').addEventListener('click', extendSaved);
  $('world-clip-start').addEventListener('click', () => markClip(false));
  $('world-clip-end').addEventListener('click', () => markClip(true));
  $('world-clip-play').addEventListener('click', () => playClip());
  $('world-clip-clear').addEventListener('click', () => { clearClip(); reviewControls(); });
  $('world-event-context').addEventListener('click', markEventContext);
  $('world-review-clear-player').addEventListener('click', () => {
    clearEventContext();
    reviewPlayer = null;
    if (frame) { showStatistics(); showEvents(frame); }
    reviewControls();
  });
  $('world-timeline').addEventListener('change', () => replayAt(Number($('world-timeline').value)));
  $('world-speed').addEventListener('change', () => { if (mode === 'replay' && clipPlayback !== 'paused' && clipPlayback !== 'finished') replayFromCurrent(); });
  $('world-actor').addEventListener('change', () => selectActor($('world-actor').value));
  $('world-room').addEventListener('change', () => selectRoom($('world-room').value));
  $('world-camera').addEventListener('change', () => setCamera($('world-camera').value));
  setInterval(() => { if (active) status(); }, 500);
  return { reset, active(value, target = null) {
    active = value;
    if (value) {
      if (target) {
        $('world-recording').replaceChildren();
        resetRecording();
        message('正在尋找原場次錄製…');
      }
      void refresh(target);
    } else { returnLiveSource = null; clearClip(); bindVenueReview(null); stop(); stopList(); status(); }
  } };
}
