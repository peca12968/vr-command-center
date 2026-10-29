import { ReplayScene } from './replay-scene.js';
import { mountCameras } from './camera-ui.js';
import { mountWorldCameraForm } from './world-camera-form.js';

const $ = id => document.getElementById(id);
const time = milliseconds => (milliseconds / 1000).toFixed(2) + ' 秒';
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };

export function mountWorld(getKey, unauthorized) {
  let active = false, scene, controller, epoch = 0, listEpoch = 0, info, frame, previous, geometry = '', mode = '', connected = false, received = 0;
  const cameras = mountCameras(getKey, unauthorized, () => scene, () => { $('world-camera').value = 'free'; $('world-room').value = 'all'; });
  const cameraForm = mountWorldCameraForm(() => scene, () => { $('world-camera').value = 'free'; $('world-room').value = 'all'; });
  function message(text, error = false) { $('world-message').textContent = text; $('world-message').classList.toggle('replay-error', error); }
  function stop() { epoch++; controller?.abort(); controller = null; connected = false; scene?.weather.pause(); scene?.draw(); $('world-pause').textContent = '繼續回放'; }
  function reset() {
    stop(); listEpoch++; info = frame = previous = null; geometry = ''; mode = ''; cameras.reset(); cameraForm.reset();
    $('world-recording').replaceChildren(); $('world-player').hidden = true; message('選取已錄製的場次，開始觀戰或回放。');
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
        option.textContent = `${row.missionName} · 房間 ${row.header.roomIds.join('、')} · ${row.header.origin} · ${row.complete ? '完整' : '錄製未封存'} · ${row.header.sessionId.slice(0, 8)}`;
        return option;
      }));
      if (rows.some(row => row.header.sessionId === selected)) $('world-recording').value = selected;
      for (const id of ['world-live', 'world-replay']) $(id).disabled = !rows.length;
      if (!rows.length) message('目前沒有可讀取的世界錄製；等待遊戲伺服器開始發送。');
    } catch (error) { if (request === listEpoch && active) message(error.message, true); }
  }
  function status() {
    if (!info) return;
    $('world-sound').disabled = info.header.environmentVersion !== 1 || scene?.weather.audio.state === 'loading';
    const audio = scene?.weather.audio.state || 'off';
    $('world-sound').textContent = ({ on: '音效：開啟', off: '音效：關閉', loading: '音效載入中…', error: '音效：重試開啟' })[audio];
    $('world-sound').setAttribute('aria-pressed', String(audio === 'on'));
    const phase = frame ? phases[frame.packet.frame.phase] : '等待第一份快照';
    $('world-status').textContent = `${info.header.origin} · ${info.complete ? '錄製已核對封存' : '錄製未封存'} · ${phase}`;
    if (mode === 'live') {
      const captured = info.header.captureStartedAtUtc ? Date.parse(info.header.captureStartedAtUtc) + (frame?.packet.elapsedMilliseconds ?? 0) : NaN;
      const age = Date.now() - captured, unknown = !Number.isFinite(age), clockInvalid = age < -1000;
      const stale = !connected || !received || performance.now() - received > 1500 || age > 1500;
      if (stale || unknown || clockInvalid) { scene?.weather.pause(); scene?.draw(); }
      $('world-freshness').textContent = info.complete ? '場次已封存' : unknown ? '擷取時間未知' : clockInvalid ? '來源時鐘未同步' : stale ? '快照已中斷或過期' : '正在接收快照';
      $('world-freshness').classList.toggle('replay-error', (stale || unknown || clockInvalid) && !info.complete);
    } else { $('world-freshness').textContent = connected ? '回放中' : '回放已暫停／結束'; $('world-pause').textContent = connected ? '暫停回放' : '繼續回放'; }
    if (!connected) { scene?.weather.pause(); scene?.draw(); }
  }
  function selectActor(key) { $('world-actor').value = key; scene?.select(key); actorInfo(); }
  function actorInfo() {
    if (!frame) return;
    const key = $('world-actor').value, [type, id] = key.split(':');
    const actor = (type === 'p' ? frame.packet.frame.players : frame.packet.frame.enemies).find(value => value.id === id);
    $('world-actor-info').textContent = actor ? `房間 ${actor.roomId} · 血量 ${actor.health}${type === 'p' ? ` · 彈匣 ${actor.magazine}／備彈 ${actor.reserve} · ${actor.connected ? '參戰中' : '未參戰'} · 頭手來源 ${actor.rig.kind}` : ' · 敵軍'} · ${id}` : '可點選場景中的角色，或從選單選取。';
  }
  function show(value) {
    previous = frame?.packet.frame; frame = value;
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
    $('world-statistics').replaceChildren(...value.statistics.map(player => {
      const row = document.createElement('tr');
      for (const text of [player.name, player.ammoUsed, player.kills, player.damageTaken, player.hitsReceived, player.accuracyPercent + '%', player.health]) { const cell = document.createElement('td'); cell.textContent = text; row.append(cell); }
      return row;
    }));
    received = performance.now(); $('world-canvas').dataset.sequence = String(packet.sequence); status();
  }
  async function connect(nextMode, milliseconds = 0) {
    const id = $('world-recording').value; if (!active || !id) return;
    stop(); mode = nextMode; controller = new AbortController(); const request = epoch, signal = controller.signal;
    message(nextMode === 'live' ? '正在連接即時觀戰…' : '正在讀取已保存快照…');
    try {
      const url = `/api/sessions/${id}/world/watch?mode=${nextMode}&fromMs=${Math.round(milliseconds)}&rate=${$('world-speed').value}`;
      const stream = await response(url, signal);
      if (request !== epoch || !active) return;
      if (!stream.body || !stream.headers.get('content-type')?.startsWith('text/event-stream')) throw new Error('缺少觀戰串流。');
      connected = true; $('world-pause').textContent = mode === 'live' ? '從此刻回放' : '暫停回放';
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
              info = data;
              scene ??= new ReplayScene($('world-canvas'), selectActor, () => { $('world-camera').value = 'free'; });
              const key = JSON.stringify(info.header);
              if (key !== geometry) {
                scene.load(info.header); geometry = key; frame = previous = null;
                $('world-room').replaceChildren(...['all', ...info.header.roomIds].map(room => { const option = document.createElement('option'); option.value = room; option.textContent = room === 'all' ? '全部房間' : '房間 ' + room; return option; }));
                $('world-camera').value = 'overview';
              }
              $('world-player').hidden = false; scene.resize(); $('world-name').textContent = info.missionName;
              cameras.bind(info.header.sessionId);
              cameraForm.bind(info.header.sessionId);
              message(`${info.header.origin} · ${info.header.rulesVersion} · ${info.header.assetSet === 'field-props-v1' ? '軍事掩體 v1（命中／碰撞採包圍盒）' : '基本幾何素材'} · VR 未校正。${info.header.origin === 'Simulation' ? '此場次使用合成頭手資料，無頭盔連接。' : '頭手來源請見角色資訊。'}${info.header.environmentVersion === 1 ? '環境聲光 v1 依保存的模擬時間重建，非原始音軌。' : '舊錄製沒有聲光效果版本，僅保留原有光霧顯示。'}`);
              status();
            } else if (type === 'frame') show(data);
            else if (type === 'status' || type === 'complete') { info = data; status(); }
          }
        }
      } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
      if (request === epoch) { connected = false; status(); }
    } catch (error) { if (request === epoch && !signal.aborted) { connected = false; message('觀戰已中斷：' + error.message + '；可重新連接。', true); status(); } }
  }
  $('world-refresh').addEventListener('click', refresh);
  $('world-sound').addEventListener('click', async () => { if (scene?.weather.version === 1) { const pending = scene.weather.audio.toggle(); status(); await pending; if (active && getKey()) status(); } });
  $('world-recording').addEventListener('change', () => { stop(); cameras.bind(null); cameraForm.reset(); info = frame = previous = null; $('world-player').hidden = true; message('已切換場次，請開始觀戰或回放。'); });
  $('world-live').addEventListener('click', () => connect('live'));
  $('world-replay').addEventListener('click', () => connect('replay'));
  $('world-pause').addEventListener('click', () => { if (mode === 'replay' && connected) { stop(); status(); } else connect('replay', frame?.packet.elapsedMilliseconds ?? 0); });
  $('world-timeline').addEventListener('change', () => connect('replay', Number($('world-timeline').value)));
  $('world-speed').addEventListener('change', () => { if (mode === 'replay') connect('replay', frame?.packet.elapsedMilliseconds ?? 0); });
  $('world-actor').addEventListener('change', () => selectActor($('world-actor').value));
  $('world-room').addEventListener('change', () => { scene?.focus($('world-room').value); $('world-camera').value = 'free'; });
  $('world-camera').addEventListener('change', () => { const view = $('world-camera').value; if (!scene) return; if (view === 'follow') { scene.follow = true; scene.draw(); } else if (view === 'free') scene.follow = false; else scene.preset(view); });
  setInterval(() => { if (active) status(); }, 500);
  return { reset, active(value) { active = value; if (value) refresh(); else { stop(); listEpoch++; status(); } } };
}
