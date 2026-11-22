import { MAX_REPLAY_BYTES, playerReplayEventFrames, playerReplayPlayers, readPlayerReplay, sourcePaused, sourceTransitions } from './player-replay-model.js';
import { recordedClock } from './mission-clock.js';
import { eventNames } from './world-event-names.js';

const $ = id => document.getElementById('player-replay-' + id);
const timeline = document.getElementById('replay-timeline');
const canvas = document.getElementById('replay-canvas');
const loop = $('loop');
const frameNumber = $('number');
const seconds = $('seconds');
const eventKind = $('event-kind');
const room = $('room'), follow = $('follow'), followStatus = $('follow-status');
for (const [kind, label] of Object.entries(eventNames)) eventKind.add(new Option(label, kind));
const loopPauseMilliseconds = 300;
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const phaseNames = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
let replay, scene, index = 0, cursor = 0, lastTime = 0, animation = 0, epoch = 0;
let restartAt = null;
let eventFrames = [], matchingEvents = [];
let replayPlayers = [];

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
  $('event-count').textContent = matchingEvents.length ? `${matchingEvents.length} 個事件畫格` : '目前範圍沒有符合的戰鬥事件。';
  showFrameEvents();
}

function clearFollow() {
  if (!follow.value) return;
  follow.value = '';
  followStatus.textContent = '';
  scene.follow = false;
  scene.select('');
}

function showFollowOptions() {
  const selectedRoom = room.value;
  const options = replayPlayers.filter(player => selectedRoom === 'all' || player.roomId === Number(selectedRoom));
  follow.replaceChildren(new Option('不跟隨', ''), ...options.map(({ id, roomId, number }) =>
    new Option(`房間 ${roomId} · 玩家 ${number}`, id)));
  follow.disabled = options.length === 0;
  followStatus.textContent = options.length ? '' : '這個範圍沒有玩家。';
}

function updateRoomEvents() {
  // Single-room exports already contain the room's events, including players who left before the clip.
  const ids = replay.header.roomIds.length > 1 && room.value !== 'all'
    ? new Set(replayPlayers.filter(player => player.roomId === Number(room.value)).map(player => player.id))
    : null;
  eventFrames = playerReplayEventFrames(replay.packets, ids, Number(room.value), replay.eventRooms);
  filterEvents();
}

function updateFollow(frame) {
  const id = follow.value;
  if (!id) return;
  const present = frame.players.some(player => player.id === id && (room.value === 'all' || player.roomId === Number(room.value)));
  scene.selected = present ? 'p:' + id : '';
  scene.follow = present;
  const status = present ? '' : '這一格沒有原角色，鏡頭停留在目前位置。';
  if (followStatus.textContent !== status) followStatus.textContent = status;
}

function show(next, continuous = false, position) {
  const { packets } = replay;
  const packet = packets[next];
  const elapsed = position ?? packet.elapsedMilliseconds;
  updateFollow(packet.frame);
  scene.show(packet.frame, packets[next - 1]?.frame, packet.events.filter(event => event.hasRay),
    { weather: packet.weather, lightning: packet.lightning }, continuous);
  index = next;
  if (!continuous) cursor = elapsed;
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
  $('time').textContent = `片段 ${clipSeconds(elapsed - first)} / ${clipSeconds(packets.at(-1).elapsedMilliseconds - first)} 秒`;
  showFrameEvents();
}

function clipSeconds(milliseconds) {
  return (milliseconds / 1000).toFixed(3).replace(/0$/, '');
}

function openFrame(next, position) {
  pause();
  if (replay && Number.isInteger(next) && next >= 0 && next < replay.packets.length) show(next, false, position);
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
  seconds.value = '';
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
      scene = new ReplayScene(canvas, key => { if (!follow.value) scene.select(key); }, clearFollow);
    }
    scene.load(candidate.header);
    const rooms = candidate.header.roomIds;
    room.replaceChildren(...rooms.map(id => new Option('房間 ' + id, id)));
    if (rooms.length > 1) room.prepend(new Option('全場俯視', 'all', true, true));
    replayPlayers = playerReplayPlayers(candidate.packets);
    showFollowOptions();
    replay = candidate;
    frameNumber.min = candidate.startFrame;
    frameNumber.max = candidate.endFrame;
    seconds.max = (candidate.packets.at(-1).elapsedMilliseconds - candidate.packets[0].elapsedMilliseconds) / 1000;
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
    scene.preset('top', room.value);
    updateRoomEvents();
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
$('seek').addEventListener('submit', event => {
  event.preventDefault();
  if (!replay || !seconds.validity.valid) return;
  const packets = replay.packets;
  const target = packets[0].elapsedMilliseconds + Math.round(seconds.valueAsNumber * 1000);
  const after = packets.findIndex(packet => packet.elapsedMilliseconds > target);
  openFrame(after === -1 ? packets.length - 1 : after - 1, target);
  seconds.focus();
});
loop.addEventListener('change', () => { if (!loop.checked && restartAt !== null) pause(); });
timeline.addEventListener('input', () => openFrame(Number(timeline.value)));
$('transition').addEventListener('change', event => {
  if (event.target.value !== '') openFrame(Number(event.target.value));
  event.target.value = '';
});
room.addEventListener('change', () => {
  if (!replay) return;
  clearFollow();
  showFollowOptions();
  scene.preset('top', room.value);
  updateRoomEvents();
});
follow.addEventListener('change', () => {
  if (!replay) return;
  if (!follow.value) {
    scene.follow = false;
    scene.select('');
    followStatus.textContent = '';
    return;
  }
  updateFollow(replay.packets[index].frame);
  if (scene.follow) scene.radius = Math.min(scene.radius, scene.fitRadius(7));
  scene.draw();
});
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
