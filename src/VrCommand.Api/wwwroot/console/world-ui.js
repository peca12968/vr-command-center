import { ReplayScene } from './replay-scene.js';
import { mountCameras } from './camera-ui.js';
import { mountWorldCameraForm } from './world-camera-form.js';
import { recordedClock } from './mission-clock.js';

const $ = id => document.getElementById(id);
const time = milliseconds => (milliseconds / 1000).toFixed(2) + ' 秒';
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const eventNames = { ShotFired: '玩家射擊', ShotHit: '命中敵軍', EnemyEliminated: '擊殺敵軍', EnemyShot: '敵軍射擊', PlayerDamaged: '玩家受傷', ReloadStarted: '開始換彈', ReloadCompleted: '完成換彈' };
const shortId = id => id && id !== '00000000-0000-0000-0000-000000000000' ? id.slice(0, 8) : '—';
const roomName = room => room === 'all' ? '全部房間' : '房間 ' + room;

export function mountWorld(getKey, unauthorized) {
  let active = false, scene, controller, epoch = 0, listEpoch = 0, info, frame, geometry = '', mode = '', connected = false, received = 0;
  let connecting = false, stepping = false, savedLimit = null, savedFinished = false;
  const cameras = mountCameras(getKey, unauthorized, () => scene, freeView);
  const cameraForm = mountWorldCameraForm(() => scene, freeView);
  function message(text, error = false) { $('world-message').textContent = text; $('world-message').classList.toggle('replay-error', error); }
  function stop() { epoch++; controller?.abort(); controller = null; connected = connecting = stepping = false; scene?.weather.pause(); scene?.draw(); $('world-pause').textContent = '繼續回放'; }
  function reset() {
    stop(); listEpoch++; info = frame = savedLimit = null; savedFinished = false; geometry = ''; mode = ''; cameras.reset(); cameraForm.reset(); reviewControls();
    $('world-recording').replaceChildren(); $('world-player').hidden = true; message('選取已錄製的場次，開始觀戰或回放。');
    recordingControls(); bindRooms([]);
    scene?.reset(); $('world-sound').textContent = '音效：關閉'; $('world-sound').disabled = true;
  }
  async function response(url, signal) {
    const key = getKey(); if (!key) throw new Error('請先登入。');
    const result = await fetch(url, { headers: { Authorization: 'Bearer ' + key }, signal, cache: 'no-store' });
    if (result.status === 401 && getKey() === key) unauthorized();
    if (!result.ok) { let error; try { error = await result.json(); } catch { } throw new Error(error?.error || '觀戰服務回應 ' + result.status); }
    return result;
  }
  async function refresh() {
    const request = ++listEpoch, key = getKey(); if (!active || !key) return;
    try {
      const rows = await (await response('/api/world-recordings')).json();
      if (request !== listEpoch || !active || getKey() !== key) return;
      const selected = $('world-recording').value;
      $('world-recording').replaceChildren(...rows.map(row => {
        const option = document.createElement('option'); option.value = row.header.sessionId;
        option.dataset.complete = String(row.complete); option.dataset.accepted = String(row.acceptedSequence);
        option.textContent = `${row.missionName} · 房間 ${row.header.roomIds.join('、')} · ${row.header.origin} · ${row.complete ? '完整' : '錄製未封存'} · ${row.header.sessionId.slice(0, 8)}`;
        return option;
      }));
      if (rows.some(row => row.header.sessionId === selected)) $('world-recording').value = selected;
      else if (selected) resetRecording();
      recordingControls(); reviewControls();
      if (!rows.length) message('目前沒有可讀取的世界錄製；等待遊戲伺服器開始發送。');
    } catch (error) { if (request === listEpoch && active) message(error.message, true); }
  }
  function recordingControls() {
    const selected = $('world-recording').selectedOptions[0];
    $('world-live').disabled = !selected;
    $('world-replay').disabled = !(Number(selected?.dataset.accepted) > 0);
    $('world-replay').textContent = selected?.dataset.complete === 'false' ? '回放已保存片段' : '從頭回放';
  }
  function resetRecording() {
    stop(); cameras.bind(null); cameraForm.reset(); info = frame = savedLimit = null; savedFinished = false; geometry = ''; mode = '';
    bindRooms([]);
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
    $('world-room').value = room;
    const camera = $('world-camera');
    scene?.setAudioRoom(room);
    if (center && scene) {
      if (camera.value === 'overview' || camera.value === 'top') scene.preset(camera.value, room);
      else { scene.focus(room); camera.value = 'free'; }
    }
    for (const button of $('world-room-quick').children)
      button.setAttribute('aria-pressed', String(button.dataset.worldRoom === room));
    showStatistics();
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
    const players = frame?.statistics.filter(player => room === 'all' || player.roomId === Number(room)) ?? [];
    $('world-statistics-heading').textContent = room && room !== 'all' ? `${roomName(room)} · 此快照已核對的統計` : '此快照已核對的統計';
    $('world-statistics-empty').hidden = !frame || players.length > 0;
    $('world-statistics').replaceChildren(...players.map(player => {
      const row = document.createElement('tr');
      for (const text of [player.name, player.ammoUsed, player.kills, player.damageTaken, player.hitsReceived, player.accuracyPercent + '%', player.health]) {
        const cell = document.createElement('td'); cell.textContent = text; row.append(cell);
      }
      return row;
    }));
  }
  function canExtendSaved() {
    return active && mode === 'replay' && info?.header.sessionId === $('world-recording').value
      && !info.complete && savedFinished && frame?.packet.sequence === savedLimit;
  }
  function reviewControls() {
    const showing = active && mode === 'replay' && info?.header.sessionId === $('world-recording').value && Boolean(frame);
    const idle = showing && !connected && !connecting && !stepping;
    $('world-review').hidden = !showing;
    $('world-frame-back').disabled = !idle || frame.packet.sequence <= 1;
    $('world-frame-next').disabled = !idle || frame.packet.sequence >= info.acceptedSequence;
    const extend = $('world-frame-extend');
    extend.hidden = !canExtendSaved();
    extend.disabled = extend.hidden || !idle;
  }
  function showEvents(value) {
    const players = new Map(value.statistics.map(player => [player.playerId, player]));
    const rows = value.packet.events.map(event => {
      const row = document.createElement('tr');
      const player = players.get(event.playerId);
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
    return replayAt(0, sequence);
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
      $('world-freshness').textContent = atSavedEnd ? '已到已保存片段尾端' : connected ? '回放中' : '回放已暫停／結束';
      $('world-freshness').classList.remove('replay-error');
      $('world-pause').textContent = connected ? '暫停回放' : '繼續回放';
    }
    if (!connected) { scene?.weather.pause(); scene?.draw(); }
  }
  function selectActor(key) { $('world-actor').value = key; scene?.select(key); actorInfo(); }
  function actorInfo() {
    if (!frame) return;
    const key = $('world-actor').value, [type, id] = key.split(':');
    const actor = (type === 'p' ? frame.packet.frame.players : frame.packet.frame.enemies).find(value => value.id === id);
    $('world-actor-info').textContent = actor ? `房間 ${actor.roomId} · 血量 ${actor.health}${type === 'p' ? ` · 彈匣 ${actor.magazine}／備彈 ${actor.reserve} · ${actor.connected ? '參戰中' : '未參戰'} · 頭手來源 ${actor.rig.kind}` : ' · 敵軍'} · ${id}` : '可點選場景中的角色，或從選單選取。';
  }
  function show(value, single = false) {
    const previous = single ? null : frame?.packet.frame;
    frame = value;
    info.durationMilliseconds = Math.max(info.durationMilliseconds, value.packet.elapsedMilliseconds);
    info.acceptedSequence = Math.max(info.acceptedSequence, value.packet.sequence);
    const age = info.header.captureStartedAtUtc ? Date.now() - Date.parse(info.header.captureStartedAtUtc) - value.packet.elapsedMilliseconds : NaN;
    const continuous = connected && (mode === 'replay' || (Number.isFinite(age) && age >= -1000 && age <= 1500));
    scene.show(value.packet.frame, previous, value.packet.events.filter(event => event.hasRay), { weather: value.packet.weather, lightning: value.packet.lightning }, continuous);
    const selected = $('world-actor').value;
    const actors = [...value.packet.frame.players.map(player => ['p:' + player.id, `玩家 · 房間 ${player.roomId} · ${player.id.slice(0, 8)}`]), ...value.packet.frame.enemies.map(enemy => ['e:' + enemy.id, `敵軍 · 房間 ${enemy.roomId} · ${enemy.id.slice(0, 8)}`])];
    $('world-actor').replaceChildren(...actors.map(([id, name]) => { const option = document.createElement('option'); option.value = id; option.textContent = name; return option; }));
    if (actors.some(([id]) => id === selected)) $('world-actor').value = selected;
    scene.select($('world-actor').value); actorInfo();
    const packet = value.packet;
    $('world-time').textContent = `${time(packet.elapsedMilliseconds)} / ${time(info.durationMilliseconds)} · 幀 ${packet.sequence}`;
    $('world-environment').textContent = `${packet.weather} · ${packet.frame.night ? '夜間' : '日間'} · ${packet.lightning ? '雷電啟用' : '無雷電'}${packet.suspended ? ' · 管理中斷暫停' : ''}`;
    $('world-timeline').max = String(Math.max(info.durationMilliseconds, packet.elapsedMilliseconds, 1)); $('world-timeline').value = String(packet.elapsedMilliseconds);
    showRoomCounts(packet); showStatistics();
    if (mode === 'replay') showEvents(value);
    received = performance.now(); $('world-canvas').dataset.sequence = String(packet.sequence); status();
  }
  async function step(offset) {
    const id = $('world-recording').value;
    if (!active || mode !== 'replay' || connected || connecting || stepping || !frame || info.header.sessionId !== id) return;
    const sequence = frame.packet.sequence + offset;
    if (sequence < 1 || sequence > info.acceptedSequence) return;
    controller?.abort(); controller = new AbortController();
    const request = ++epoch, signal = AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]);
    stepping = true; reviewControls(); $('world-frame-message').textContent = '正在讀取保存快照…';
    try {
      const value = await (await response(`/api/sessions/${id}/world/frames/${sequence}`, signal)).json();
      if (request !== epoch || !active || id !== $('world-recording').value) return;
      if (value.packet.sequence !== sequence) throw new Error('回應的快照序號不同。');
      show(value, true); $('world-frame-message').textContent = `已停在第 ${sequence} 格。`;
    } catch (error) {
      if (request === epoch) $('world-frame-message').textContent = '讀取快照失敗，請再試一次。';
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
  async function connect(nextMode, milliseconds = 0, sequence = null, replayLimit = savedLimit) {
    const id = $('world-recording').value; if (!active || !id) return;
    stop(); mode = nextMode; controller = new AbortController(); const request = epoch, signal = controller.signal;
    if (nextMode === 'live') { savedLimit = null; savedFinished = false; }
    const limit = nextMode === 'live' ? null : replayLimit;
    let hasHeader = false, reachedSavedEnd = false, lastSequence = sequence === null ? null : sequence - 1;
    connecting = true; reviewControls(); $('world-frame-message').textContent = '';
    message(nextMode === 'live' ? '正在連接即時觀戰…' : '正在讀取已保存快照…');
    try {
      const position = sequence === null ? `fromMs=${Math.round(milliseconds)}` : `fromFrame=${sequence}`;
      const url = `/api/sessions/${id}/world/watch?mode=${nextMode}&${position}&rate=${$('world-speed').value}${limit === null ? '' : `&throughFrame=${limit}`}`;
      const stream = await response(url, signal);
      if (request !== epoch || !active) return;
      if (!stream.body || !stream.headers.get('content-type')?.startsWith('text/event-stream')) throw new Error('缺少觀戰串流。');
      connected = true; connecting = false; $('world-pause').textContent = mode === 'live' ? '從此刻回放' : '暫停回放';
      const reader = stream.body.getReader(), decoder = new TextDecoder(); let buffer = '';
      try {
        while (true) {
          const { done, value } = await reader.read(); if (done) break;
          if (request !== epoch || !active) return;
          buffer += decoder.decode(value, { stream: true });
          if (buffer.length > 2 * 1024 * 1024) throw new Error('觀戰資料超過單份快照限制。');
          let end;
          while ((end = buffer.indexOf('\n\n')) >= 0) {
            const event = buffer.slice(0, end); buffer = buffer.slice(end + 2);
            const lines = event.split('\n'), type = lines.find(line => line.startsWith('event: '))?.slice(7), raw = lines.find(line => line.startsWith('data: '))?.slice(6);
            if (!raw) continue; const data = JSON.parse(raw);
            if (type === 'header') {
              if (hasHeader || data.header?.sessionId !== id) throw new Error('回應的錄製場次不同。');
              if (limit !== null) {
                if (!Number.isSafeInteger(data.acceptedSequence) || data.acceptedSequence < 1 || (limit !== 'latest' && limit !== data.acceptedSequence))
                  throw new Error('已保存片段的尾端不符。');
                savedLimit = data.acceptedSequence;
              }
              hasHeader = true; savedFinished = false;
              info = data;
              scene ??= new ReplayScene($('world-canvas'), selectActor, () => { $('world-camera').value = 'free'; });
              const key = JSON.stringify(info.header);
              if (key !== geometry) {
                scene.load(info.header); geometry = key; frame = null;
                bindRooms(info.header.roomIds);
                $('world-camera').value = 'overview';
              }
              $('world-player').hidden = false; scene.resize(); $('world-name').textContent = info.missionName;
              cameras.bind(info.header.sessionId);
              cameraForm.bind(info.header.sessionId);
              message(`${info.header.origin} · ${info.header.rulesVersion} · ${info.header.assetSet === 'player-fire-v1' ? '軍事掩體／玩家及敵軍射擊效果 v1（依保存射線）' : info.header.assetSet === 'combat-effects-v1' ? '軍事掩體／敵軍射擊閃光及後座 v1（依保存射線）' : info.header.assetSet === 'armed-combatants-v1' ? '軍事掩體／敵軍雙手持槍／換彈 v1（合成姿勢）' : info.header.assetSet === 'weapon-actions-v1' ? '軍事掩體／人形敵軍／換彈動作 v1（合成手套非追蹤）' : info.header.assetSet === 'combatants-v1' ? '軍事掩體／步槍／人形敵軍 v1（命中採粗略包圍盒）' : info.header.assetSet === 'service-rifle-v1' ? '軍事掩體／玩家步槍 v1（命中／碰撞採包圍盒）' : info.header.assetSet === 'field-props-v1' ? '軍事掩體 v1（命中／碰撞採包圍盒）' : '基本幾何素材'} · VR 未校正。${info.header.origin === 'Simulation' ? '此場次使用合成頭手資料，無頭盔連接。' : '頭手來源請見角色資訊。'}${info.header.environmentVersion === 1 ? '環境聲光 v1 依保存的模擬時間重建，非原始音軌。' : '舊錄製沒有聲光效果版本，僅保留原有光霧顯示。'}`);
              status();
            } else if (type === 'frame') {
              if (limit !== null) {
                const current = data.packet.sequence;
                if (!hasHeader || reachedSavedEnd || !Number.isSafeInteger(current) || current < 1 || current > savedLimit
                  || (lastSequence !== null && current !== lastSequence + 1)) throw new Error('已保存片段的快照序號不符。');
                lastSequence = current;
              }
              show(data);
            }
            else if (type === 'status' || type === 'complete') { info = data; status(); }
            else if (type === 'saved-end' && limit !== null) {
              if (!hasHeader || data.acceptedSequence !== savedLimit || lastSequence !== savedLimit) throw new Error('已保存片段未完整讀取。');
              info = data; reachedSavedEnd = savedFinished = true;
            }
          }
        }
      } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
      if (request === epoch) {
        if (limit !== null && !reachedSavedEnd) throw new Error('尚未讀到已保存片段尾端。');
        connected = false; status();
      }
    } catch (error) { if (request === epoch && !signal.aborted) { connected = connecting = false; message('觀戰已中斷：' + error.message + '；可重新連接。', true); status(); } }
  }
  $('world-refresh').addEventListener('click', refresh);
  $('world-sound').addEventListener('click', async () => { if (scene?.weather.version === 1 || scene?.weather.audio.combat.version === 1) { const pending = scene.weather.audio.toggle(); status(); await pending; if (active && getKey()) status(); } });
  $('world-recording').addEventListener('change', resetRecording);
  $('world-live').addEventListener('click', () => connect('live'));
  $('world-replay').addEventListener('click', () => {
    savedLimit = $('world-recording').selectedOptions[0]?.dataset.complete === 'false' ? 'latest' : null;
    connect('replay', 0, 1);
  });
  $('world-pause').addEventListener('click', () => { if (mode === 'replay' && connected) { stop(); status(); } else replayFromCurrent(); });
  $('world-frame-back').addEventListener('click', () => step(-1));
  $('world-frame-next').addEventListener('click', () => step(1));
  $('world-frame-extend').addEventListener('click', extendSaved);
  $('world-timeline').addEventListener('change', () => replayAt(Number($('world-timeline').value)));
  $('world-speed').addEventListener('change', () => { if (mode === 'replay') replayFromCurrent(); });
  $('world-actor').addEventListener('change', () => selectActor($('world-actor').value));
  $('world-room').addEventListener('change', () => selectRoom($('world-room').value));
  $('world-camera').addEventListener('change', () => { const view = $('world-camera').value; if (!scene) return; if (view === 'follow') { scene.follow = true; scene.draw(); } else if (view === 'free') scene.follow = false; else scene.preset(view, $('world-room').value); });
  setInterval(() => { if (active) status(); }, 500);
  return { reset, active(value) { active = value; if (value) refresh(); else { stop(); listEpoch++; status(); } } };
}
