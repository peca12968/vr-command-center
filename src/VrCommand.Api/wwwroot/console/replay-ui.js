import { MAX_RECORDING_BYTES, validateRecording, frameAtTime } from './replay-model.js';
const $ = id => document.getElementById(id);
const phaseNames = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const visibilityNames = { Clear: '晴朗', Fog: '濃霧', Storm: '暴風雨' };

export function mountReplay() {
  let recording = null, index = 0, cursor = 0, playing = false, active = false, lastNow = performance.now(), scene = null, loadEpoch = 0;
  function message(text, error = false) { $('replay-message').textContent = text; $('replay-message').classList.toggle('replay-error', error); }
  function pause() { playing = false; $('replay-play').textContent = '播放'; scene?.weather.pause(); }
  function soundState() { const on=scene?.weather.audio.state==='on';$('replay-sound').textContent=on?'音效：開啟':'音效：關閉';$('replay-sound').setAttribute('aria-pressed',String(on)); }
  async function load(text, epoch) {
    if (epoch !== loadEpoch) return;
    pause();
    try {
      if (new TextEncoder().encode(text).byteLength > MAX_RECORDING_BYTES) throw new Error('檔案超過 25 MB。');
      const candidate = validateRecording(JSON.parse(text));
      if (!scene) { const { ReplayScene } = await import('./replay-scene.js'); if (epoch !== loadEpoch) return; scene = new ReplayScene($('replay-canvas'), selectActor, () => { $('replay-camera').value = 'free'; }); }
      if (epoch !== loadEpoch) return;
      recording = candidate; index = 0; cursor = 0;
      $('replay-player').hidden = false; $('replay-name').textContent = recording.data.mission.definition.name;
      $('replay-description').textContent = recording.data.mission.definition.briefing;
      const rooms = recording.data.roomIds;
      $('replay-room').replaceChildren(...rooms.map(room => { const option = document.createElement('option'); option.value = room; option.textContent = '房間 ' + room; return option; }));
      const actorOptions = new Map();
      for (const identity of recording.data.statistics.players) actorOptions.set('p:' + identity.playerId, '玩家 · ' + identity.name);
      for (const frame of recording.data.frames) for (const enemy of frame.enemies) if (!actorOptions.has('e:' + enemy.id)) actorOptions.set('e:' + enemy.id, '敵軍 · ' + enemy.id.slice(0, 8));
      $('replay-actor').replaceChildren(...[...actorOptions].map(([key, name]) => { const option = document.createElement('option'); option.value = key; option.textContent = name; return option; }));
      $('replay-timeline').max = recording.data.frames.length - 1; $('replay-camera').value = 'overview';
      scene.load(recording.data); scene.selected = $('replay-actor').value;
      $('replay-sound').disabled=recording.data.environmentVersion!==1&&recording.data.combatAudioVersion!==1;
      soundState();
      show(0); scene.resize();
      message(`已載入 ${recording.data.frames.length} 份快照、${recording.data.events.length} 筆事件；結束統計核對一致。`);
    } catch (error) { if (epoch === loadEpoch) message(error instanceof SyntaxError ? '無法讀取 JSON 紀錄。' : '無法載入：' + error.message, true); }
  }
  function show(nextIndex, keepTime = false) {
    if (!recording) return;
    index = Math.max(0, Math.min(recording.data.frames.length - 1, nextIndex));
    const frame = recording.data.frames[index];
    if (!keepTime) cursor = frame.tick * recording.data.tickSeconds;
    $('replay-timeline').value = index;
    $('replay-time').textContent = `${(frame.tick * recording.data.tickSeconds).toFixed(2)} / ${recording.duration.toFixed(2)} 秒`;
    $('replay-tick').textContent = `快照 ${index + 1}/${recording.data.frames.length} · tick ${frame.tick} · 事件 #${frame.throughSequence}`;
    $('replay-phase').textContent = phaseNames[frame.phase];
    $('replay-environment').textContent = `${frame.night ? '夜晚' : '白天'} · ${visibilityNames[frame.visibility]} · ${{ Hold: '守備', Patrol: '巡邏', Advance: '推進' }[frame.behavior]} · ${frame.autoAttack ? '自動攻擊' : '停止自動攻擊'}`;
    const traces = recording.data.events.filter(event => event.sequence <= frame.throughSequence && frame.tick - event.tick <= 6 && ['ShotFired', 'EnemyShot'].includes(event.kind));
    scene.show(frame, recording.data.frames[Math.max(0, index - 1)], traces,undefined,keepTime&&playing&&active&&document.visibilityState==='visible');
    $('replay-canvas').dataset.frame = index;
    $('replay-statistics').replaceChildren(...recording.frameStatistics[index].map(player => {
      const row = document.createElement('tr');
      for (const value of [player.name, player.ammoUsed, player.kills, player.damageTaken, player.hitsReceived, player.accuracyPercent + '%', player.health]) { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); }
      return row;
    }));
    actorInfo();
  }
  function actorInfo() {
    if (!recording) return;
    const frame = recording.data.frames[index], key = $('replay-actor').value, id = key.slice(2);
    const actor = key.startsWith('p:') ? frame.players.find(p => p.id === id) : frame.enemies.find(e => e.id === id);
    if (!actor) { $('replay-actor-info').textContent = '此角色在所選快照中尚未出現或已離開。'; return; }
    const position = actor.head || actor.feet;
    $('replay-actor-info').textContent = `房間 ${actor.roomId} · 血量 ${actor.health} · 位置 (${position.x.toFixed(2)}, ${position.y.toFixed(2)}, ${position.z.toFixed(2)})` + (actor.magazine !== undefined ? ` · 彈匣 ${actor.magazine}／備彈 ${actor.reserve}` : '');
  }
  function selectActor(key) { $('replay-actor').value = key; scene?.select(key); actorInfo(); }
  $('replay-example').addEventListener('click', async () => {
    const epoch = ++loadEpoch; pause();
    $('replay-example').disabled = true;
    try { const response = await fetch('./examples/simulation.json', { cache: 'no-store' }); if (!response.ok) throw new Error('範例讀取失敗。'); await load(await response.text(), epoch); }
    catch (error) { if (epoch === loadEpoch) message(error.message, true); }
    finally { $('replay-example').disabled = false; }
  });
  $('replay-file').addEventListener('change', async () => {
    const file = $('replay-file').files[0];
    if (!file) return;
    const epoch = ++loadEpoch; pause();
    if (file.size > MAX_RECORDING_BYTES) { message('檔案超過 25 MB。', true); return; }
    try { await load(await file.text(), epoch); } catch { if (epoch === loadEpoch) message('無法讀取本機檔案。', true); }
    $('replay-file').value = '';
  });
  $('replay-play').addEventListener('click', () => {
    if (!recording) return;
    if (playing) pause();
    else { if (cursor >= recording.duration) show(0); playing = true; lastNow = performance.now(); $('replay-play').textContent = '暫停'; }
  });
  $('replay-sound').addEventListener('click',async()=>{if(!scene)return;const epoch=loadEpoch;await scene.weather.audio.toggle();if(epoch===loadEpoch)soundState();});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState!=='visible')scene?.weather.pause();});
  $('replay-timeline').addEventListener('input', () => { pause(); show(Number($('replay-timeline').value)); });
  $('replay-back').addEventListener('click', () => { pause(); show(index - 1); });
  $('replay-next').addEventListener('click', () => { pause(); show(index + 1); });
  $('replay-actor').addEventListener('change', () => selectActor($('replay-actor').value));
  $('replay-room').addEventListener('change', () => { $('replay-camera').value = 'free'; scene?.focus($('replay-room').value); });
  $('replay-camera').addEventListener('change', () => {
    const mode = $('replay-camera').value;
    if (!scene) return;
    if (mode === 'follow') { scene.follow = true; scene.draw(); }
    else if (mode !== 'free') scene.preset(mode);
    else scene.follow = false;
  });
  function loop(now) {
    if (playing && active && recording && document.visibilityState === 'visible') {
      cursor = Math.min(recording.duration, cursor + Math.max(0, Math.min(.25, (now - lastNow) / 1000)) * Number($('replay-speed').value));
      const next = frameAtTime(recording.data.frames, cursor, recording.data.tickSeconds);
      if (next !== index) show(next, true);
      if (cursor >= recording.duration) pause();
    }
    lastNow = now; requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  return {
    active(value) { active = value; if (!value) pause(); else if (scene) requestAnimationFrame(() => scene.resize()); },
    reset() { loadEpoch++; pause(); recording = null; index = 0; cursor = 0; $('replay-player').hidden = true; $('replay-file').value = ''; $('replay-statistics').replaceChildren(); $('replay-name').textContent = ''; $('replay-description').textContent = ''; $('replay-actor-info').textContent = ''; $('replay-actor').replaceChildren(); scene?.reset();soundState();$('replay-sound').disabled=true; message('請載入範例或選擇模擬紀錄。'); }
  };
}
