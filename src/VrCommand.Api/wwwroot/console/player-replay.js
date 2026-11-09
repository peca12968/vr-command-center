import { MAX_REPLAY_BYTES, readPlayerReplay } from './player-replay-model.js';

const $ = id => document.getElementById('player-replay-' + id);
const timeline = document.getElementById('replay-timeline');
const canvas = document.getElementById('replay-canvas');
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const phaseNames = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
let replay, scene, index = 0, cursor = 0, lastTime = 0, animation = 0, epoch = 0;

function message(text, error = false) {
  $('message').textContent = text;
  $('message').classList.toggle('replay-error', error);
}

function pause() {
  cancelAnimationFrame(animation);
  animation = 0;
  $('play').textContent = '播放';
  scene?.weather.pause();
}

function show(next, continuous = false) {
  const { packets } = replay;
  const packet = packets[next];
  scene.show(packet.frame, packets[next - 1]?.frame, packet.events.filter(event => event.hasRay),
    { weather: packet.weather, lightning: packet.lightning }, continuous);
  index = next;
  if (!continuous) cursor = packet.elapsedMilliseconds;
  timeline.value = index;
  $('back').disabled = index === 0;
  $('next').disabled = index === packets.length - 1;
  $('frame').textContent = `第 ${packet.sequence} 格 · ${phaseNames[packet.frame.phase]}`;
  $('weather').textContent = [weatherNames[packet.weather], packet.frame.night ? '夜晚' : '白天',
    packet.lightning ? '雷電開啟' : '雷電關閉'].join(' · ');
  const first = packets[0].elapsedMilliseconds;
  $('time').textContent = `${((packet.elapsedMilliseconds - first) / 1000).toFixed(2)} / ${((packets.at(-1).elapsedMilliseconds - first) / 1000).toFixed(2)} 秒`;
}

function openFrame(next) {
  pause();
  if (replay && Number.isInteger(next) && next >= 0 && next < replay.packets.length) show(next);
}

$('file').addEventListener('change', async () => {
  const file = $('file').files[0];
  if (!file) return;
  const own = ++epoch;
  pause();
  replay = null;
  $('file').value = '';
  $('view').hidden = true;
  scene?.reset();
  message('正在讀取本機回放檔。');
  try {
    if (file.size > MAX_REPLAY_BYTES) throw new Error('回放檔超過 8 MiB。');
    const candidate = readPlayerReplay(JSON.parse(await file.text()));
    if (own !== epoch) return;
    if (!scene) {
      const { ReplayScene } = await import('./replay-scene.js');
      if (own !== epoch) return;
      scene = new ReplayScene(canvas, key => scene.select(key), () => {});
    }
    scene.load(candidate.header);
    const rooms = candidate.header.roomIds;
    $('room').replaceChildren(...rooms.map(room => new Option('房間 ' + room, room)));
    if (rooms.length > 1) $('room').prepend(new Option('全場俯視', 'all', true, true));
    replay = candidate;
    $('title').textContent = candidate.clipName;
    const source = candidate.header.origin === 'GameServer' ? '遊戲伺服器' : '模擬';
    $('source').textContent = `${candidate.missionName} · ${source} · 原畫格 ${candidate.startFrame}–${candidate.endFrame}`;
    timeline.max = candidate.packets.length - 1;
    $('view').hidden = false;
    scene.resize();
    scene.preset('top', $('room').value);
    show(0);
    message(`已載入 ${candidate.packets.length} 格。`);
  } catch (error) {
    if (own !== epoch) return;
    replay = null;
    $('view').hidden = true;
    scene?.reset();
    message(error instanceof SyntaxError ? '無法讀取 JSON 回放檔。' : error.message, true);
  }
});

function advance(now) {
  const { packets } = replay;
  cursor += Math.min(250, Math.max(0, now - lastTime)) * Number($('speed').value);
  lastTime = now;
  let next = index;
  while (next + 1 < packets.length && packets[next + 1].elapsedMilliseconds <= cursor) next++;
  if (next !== index) show(next, true);
  if (next === packets.length - 1) pause();
  else animation = requestAnimationFrame(advance);
}

$('play').addEventListener('click', () => {
  if (!replay) return;
  if (animation) { pause(); return; }
  if (index === replay.packets.length - 1) show(0);
  lastTime = performance.now();
  $('play').textContent = '暫停';
  animation = requestAnimationFrame(advance);
});
$('back').addEventListener('click', () => openFrame(index - 1));
$('next').addEventListener('click', () => openFrame(index + 1));
timeline.addEventListener('input', () => openFrame(Number(timeline.value)));
$('room').addEventListener('change', () => scene?.preset('top', $('room').value));
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
