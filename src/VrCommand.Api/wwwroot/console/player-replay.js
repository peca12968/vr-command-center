import { MAX_REPLAY_BYTES, playerReplayEventFrames, readPlayerReplay, sourcePaused, sourceTransitions } from './player-replay-model.js';
import { recordedClock } from './mission-clock.js';
import { eventNames } from './world-event-names.js';

const $ = id => document.getElementById('player-replay-' + id);
const timeline = document.getElementById('replay-timeline');
const canvas = document.getElementById('replay-canvas');
const loop = $('loop');
const frameNumber = $('number');
const eventKind = $('event-kind');
for (const [kind, label] of Object.entries(eventNames)) eventKind.add(new Option(label, kind));
const loopPauseMilliseconds = 300;
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const phaseNames = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
let replay, scene, index = 0, cursor = 0, lastTime = 0, animation = 0, epoch = 0;
let restartAt = null;
let eventFrames = [], matchingEvents = [];

function message(text, error = false) {
  $('message').textContent = text;
  $('message').classList.toggle('replay-error', error);
}

function pause() {
  cancelAnimationFrame(animation);
  animation = 0;
  restartAt = null;
  $('play').textContent = '播放';
  scene?.weather.pause();
}

function adjacentEvent(forward) {
  if (forward) return matchingEvents.find(row => row.index > index);
  for (let cursor = matchingEvents.length - 1; cursor >= 0; cursor--) {
    if (matchingEvents[cursor].index < index) return matchingEvents[cursor];
  }
}

function showFrameEvents() {
  $('event-back').disabled = !adjacentEvent(false);
  $('event-next').disabled = !adjacentEvent(true);
  const counts = matchingEvents.find(row => row.index === index)?.counts;
  const summary = Object.entries(counts ?? {}).filter(([kind]) => !eventKind.value || kind === eventKind.value)
    .map(([kind, count]) => `${eventNames[kind]} ${count} 筆`);
  $('event-frame').textContent = summary.join(' · ');
  $('event-frame').hidden = summary.length === 0;
}

function filterEvents() {
  matchingEvents = eventKind.value ? eventFrames.filter(row => row.counts[eventKind.value]) : eventFrames;
  eventKind.disabled = eventFrames.length === 0;
  $('event-count').textContent = matchingEvents.length ? `${matchingEvents.length} 個事件畫格` : '片段內沒有符合的戰鬥事件。';
  showFrameEvents();
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
  $('frame').textContent = `第 ${packet.sequence} 格 · ${sourcePaused(packet) ? '遊戲來源暫停' : phaseNames[packet.frame.phase]}`;
  const clock = recordedClock(replay.header, packet.frame.tick);
  $('clock').textContent = clock;
  $('clock').hidden = !clock;
  $('weather').textContent = [weatherNames[packet.weather], packet.frame.night ? '夜晚' : '白天',
    packet.lightning ? '雷電開啟' : '雷電關閉'].join(' · ');
  const first = packets[0].elapsedMilliseconds;
  $('time').textContent = `片段 ${((packet.elapsedMilliseconds - first) / 1000).toFixed(2)} / ${((packets.at(-1).elapsedMilliseconds - first) / 1000).toFixed(2)} 秒`;
  showFrameEvents();
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
  loop.checked = false;
  eventKind.value = '';
  frameNumber.value = '';
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
    frameNumber.min = candidate.startFrame;
    frameNumber.max = candidate.endFrame;
    $('title').textContent = candidate.clipName;
    const source = candidate.header.origin === 'GameServer' ? '遊戲伺服器' : '模擬';
    const scope = candidate.roomId === undefined ? '' : ` · 僅房間 ${candidate.roomId}`;
    $('source').textContent = `${candidate.missionName} · ${source}${scope} · 原畫格 ${candidate.startFrame}–${candidate.endFrame}`;
    const transitions = sourceTransitions(candidate.packets);
    $('transition').replaceChildren(new Option('跳到畫格', ''), ...transitions.map(({ index, suspended }) =>
      new Option(`第 ${candidate.packets[index].sequence} 格 · ${suspended ? '遊戲來源暫停' : '遊戲來源恢復'}`, index)));
    $('transition-field').hidden = transitions.length === 0;
    timeline.max = candidate.packets.length - 1;
    $('view').hidden = false;
    scene.resize();
    scene.preset('top', $('room').value);
    eventFrames = playerReplayEventFrames(candidate.packets);
    filterEvents();
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
  if (restartAt !== null) {
    if (now >= restartAt) {
      show(0);
      lastTime = now;
      restartAt = null;
    }
    animation = requestAnimationFrame(advance);
    return;
  }
  cursor += Math.min(250, Math.max(0, now - lastTime)) * Number($('speed').value);
  lastTime = now;
  let next = index;
  while (next + 1 < packets.length && packets[next + 1].elapsedMilliseconds <= cursor) next++;
  if (next !== index) show(next, true);
  if (next === packets.length - 1) {
    if (!loop.checked) { pause(); return; }
    scene.weather.pause();
    restartAt = now + loopPauseMilliseconds;
  }
  animation = requestAnimationFrame(advance);
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
eventKind.addEventListener('change', filterEvents);
$('event-back').addEventListener('click', () => openFrame(adjacentEvent(false)?.index));
$('event-next').addEventListener('click', () => openFrame(adjacentEvent(true)?.index));
$('jump').addEventListener('submit', event => {
  event.preventDefault();
  const sequence = frameNumber.valueAsNumber;
  if (!replay || !Number.isSafeInteger(sequence) || sequence < replay.startFrame || sequence > replay.endFrame) return;
  openFrame(sequence - replay.startFrame);
  frameNumber.focus();
});
loop.addEventListener('change', () => { if (!loop.checked && restartAt !== null) pause(); });
timeline.addEventListener('input', () => openFrame(Number(timeline.value)));
$('transition').addEventListener('change', event => {
  if (event.target.value !== '') openFrame(Number(event.target.value));
  event.target.value = '';
});
$('room').addEventListener('change', () => scene?.preset('top', $('room').value));
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
