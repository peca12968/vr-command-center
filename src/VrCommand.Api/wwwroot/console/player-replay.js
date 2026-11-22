import { MAX_REPLAY_BYTES, MAX_REPLAY_FILES, MAX_REPLAY_SET_BYTES, playerReplayEventFrames, playerReplayPlayers, readPlayerReplaySet, samePlayerReplaySource, sourcePaused, sourceTransitions } from './player-replay-model.js';
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
function weatherText(packet) {
  return [weatherNames[packet.weather], packet.frame.night ? '夜晚' : '白天', packet.lightning ? '雷電開啟' : '雷電關閉'].join(' · ');
}
let replay, scene, index = 0, cursor = 0, lastTime = 0, animation = 0, epoch = 0;
let speed = 1;
let restartAt = null;
let eventFrames = [], matchingEvents = [];
let replayPlayers = [];
let followedFrames = [];
let currentVolume = null;

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
  followedFrames = [];
  updateFollow(index);
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
  followedFrames = [];
  updateFollow(index);
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

function updateFollow(position) {
  const present = followedFrames.includes(position);
  const missing = followedFrames.length > 0 && !present;
  $('follow-back').hidden = !missing || followedFrames[0] >= position;
  $('follow-next').hidden = !missing || followedFrames.at(-1) <= position;
  const id = follow.value;
  if (!id) return;
  scene.selected = present ? 'p:' + id : '';
  scene.follow = present;
  const status = present ? '' : '這一格沒有原角色，鏡頭停留在目前位置。';
  if (followStatus.textContent !== status) followStatus.textContent = status;
}

function show(next, continuous = false, position) {
  const { packets } = replay;
  const packet = packets[next];
  updateFollow(next);
  scene.show(packet.frame, packets[next - 1]?.frame, packet.events.filter(event => event.hasRay),
    { weather: packet.weather, lightning: packet.lightning }, continuous);
  index = next;
  if (!continuous) cursor = position ?? packet.elapsedMilliseconds;
  timeline.value = index;
  $('back').disabled = index === 0;
  $('next').disabled = index === packets.length - 1;
  $('frame').textContent = `第 ${packet.sequence} 格 · ${sourcePaused(packet) ? '遊戲來源暫停' : phaseNames[packet.frame.phase]}`;
  const clock = recordedClock(replay.header, packet.frame.tick);
  $('clock').textContent = clock;
  $('clock').hidden = !clock;
  $('weather').textContent = weatherText(packet);
  showTime();
  showFrameEvents();
}

function clipSeconds(milliseconds) {
  return (milliseconds / 1000).toFixed(3).replace(/0$/, '');
}

function showTime() {
  const packets = replay.packets, first = packets[0].elapsedMilliseconds;
  $('time').textContent = `片段 ${clipSeconds(Math.floor(cursor - first))} / ${clipSeconds(packets.at(-1).elapsedMilliseconds - first)} 秒`;
}

function openFrame(next, position) {
  pause();
  if (replay && Number.isInteger(next) && next >= 0 && next < replay.packets.length) show(next, false, position);
}

function volumeInfo(value) {
  const match = /^([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}):(\d+):(\d+):(\d+)$/.exec(value ?? '');
  if (!match) throw new Error('請選擇由場館匯出的回放分冊網頁。');
  const [first, last, end] = match.slice(2).map(Number);
  if (![first, last, end].every(Number.isSafeInteger) || first < 1 || last <= first || end < last)
    throw new Error('回放分冊的畫格範圍無效。');
  return { clip: match[1], first, last, end };
}

async function readVolumeFile(file) {
  if (file.size > MAX_REPLAY_SET_BYTES + 2 * 1024 * 1024 + 8192) throw new Error('回放網頁超過分冊容量。');
  const html = await file.text();
  const marker = /<span hidden id="replay-volume" data-volume="([^"<>]{1,110})"><\/span>/.exec(html);
  const volume = volumeInfo(marker?.[1]);
  const files = [];
  // Extract data only. The selected HTML never becomes a document or executes scripts.
  for (const part of html.matchAll(/<script type="application\/json" data-player-replay-part>([^<]+)<\/script>/g)) {
    if (files.length === MAX_REPLAY_FILES) throw new Error('分冊內的片段超過 24 份。');
    files.push(new Blob([part[1]]));
  }
  return { files, volume };
}

async function openReplay(files, embeddedInfo = null, continuing = false) {
  if (!files.length) return;
  const own = ++epoch;
  pause();
  if (!continuing) {
    replay = null;
    currentVolume = null;
    $('view').hidden = true;
    scene?.reset();
  }
  $('file').value = '';
  $('volume-file').value = '';
  message('正在讀取本機回放檔。');
  try {
    let volume = null;
    if (continuing) {
      ({ files, volume } = await readVolumeFile(files[0]));
      if (own !== epoch) return;
      if (!currentVolume || volume.clip !== currentVolume.clip || volume.end !== currentVolume.end ||
          volume.first !== currentVolume.last + 1) throw new Error('請選擇同一片段、從下一格開始的分冊。');
    } else if (embeddedInfo !== null) volume = volumeInfo(embeddedInfo);
    if (files.length > MAX_REPLAY_FILES) throw new Error('請一次選擇最多 24 份回放檔。');
    if (files.some(file => file.size > MAX_REPLAY_BYTES)) throw new Error('回放檔超過 8 MiB。');
    if (files.reduce((size, file) => size + file.size, 0) > MAX_REPLAY_SET_BYTES) throw new Error('所選片段合計超過 64 MiB，請分批開啟。');
    const documents = [];
    for (const file of files) {
      const text = await file.text();
      if (own !== epoch) return;
      documents.push(JSON.parse(text));
    }
    const { replay: candidate, segments } = readPlayerReplaySet(documents);
    if (volume && (candidate.startFrame !== volume.first || candidate.endFrame !== volume.last))
      throw new Error('分冊標示與實際畫格範圍不符。');
    if (continuing && !samePlayerReplaySource(candidate, replay))
      throw new Error('下一冊必須來自同一場錄製與相同房間範圍。');
    if (!scene) {
      const { ReplayScene } = await import('./replay-scene.js');
      if (own !== epoch) return;
      scene = new ReplayScene(canvas, key => { if (!follow.value) scene.select(key); }, clearFollow);
    }
    const previousRoom = continuing ? room.value : null;
    pause();
    loop.checked = false;
    eventKind.value = '';
    frameNumber.value = '';
    seconds.value = '';
    scene.load(candidate.header);
    const rooms = candidate.header.roomIds;
    room.replaceChildren(...rooms.map(id => new Option('房間 ' + id, id)));
    if (rooms.length > 1) room.prepend(new Option('全場俯視', 'all', true, true));
    if (previousRoom !== null) room.value = previousRoom;
    replayPlayers = playerReplayPlayers(candidate.packets);
    showFollowOptions();
    replay = candidate;
    currentVolume = volume;
    $('continuation').hidden = !volume;
    if (volume) {
      $('volume-file').hidden = volume.last === volume.end;
      $('volume-label').textContent = volume.last === volume.end ? '已到最後一冊。'
        : `開啟下一冊（從第 ${volume.last + 1} 格開始）`;
    }
    frameNumber.min = candidate.startFrame;
    frameNumber.max = candidate.endFrame;
    seconds.max = (candidate.packets.at(-1).elapsedMilliseconds - candidate.packets[0].elapsedMilliseconds) / 1000;
    $('title').textContent = segments.length === 1 ? candidate.clipName : `${candidate.missionName} · ${segments.length} 段連播`;
    $('segment').replaceChildren(new Option('選擇片段', ''), ...segments.map(segment =>
      new Option(`${segment.clipName} · 第 ${segment.startFrame}–${segment.endFrame} 格`, segment.startFrame - candidate.startFrame)));
    $('segment-field').hidden = segments.length === 1;
    const source = candidate.header.origin === 'GameServer' ? '遊戲伺服器' : '模擬';
    const scope = candidate.roomId === undefined ? '' : ` · 僅房間 ${candidate.roomId}`;
    $('source').textContent = `${candidate.missionName} · ${source}${scope} · 原畫格 ${candidate.startFrame}–${candidate.endFrame}`;
    const transitions = sourceTransitions(candidate.packets);
    $('transition').replaceChildren(new Option('跳到畫格', ''), ...transitions.map(({ index, suspended }) =>
      new Option(`第 ${candidate.packets[index].sequence} 格 · ${suspended ? '遊戲來源暫停' : '遊戲來源恢復'}`, index)));
    $('transition-field').hidden = transitions.length === 0;
    const environmentOptions = [];
    for (const [i, packet] of candidate.packets.entries()) {
      const previous = candidate.packets[i - 1];
      if (previous && packet.weather === previous.weather && packet.frame.night === previous.frame.night
          && packet.lightning === previous.lightning) continue;
      const elapsed = clipSeconds(packet.elapsedMilliseconds - candidate.packets[0].elapsedMilliseconds);
      environmentOptions.push(new Option(`${elapsed} 秒 · 第 ${packet.sequence} 格 · ${weatherText(packet)}`, i));
    }
    $('environment').replaceChildren(new Option('跳到畫格', ''), ...environmentOptions);
    $('environment-field').hidden = environmentOptions.length < 2;
    timeline.max = candidate.packets.length - 1;
    $('view').hidden = false;
    scene.resize();
    scene.preset('top', room.value);
    updateRoomEvents();
    show(0);
    message(`已載入 ${candidate.packets.length} 格。`);
  } catch (error) {
    if (own !== epoch) return;
    if (!continuing) {
      replay = null;
      $('view').hidden = true;
      scene?.reset();
    }
    message(error instanceof SyntaxError ? '無法讀取 JSON 回放檔。' : error.message, true);
  }
}

$('file').addEventListener('change', () => openReplay(Array.from($('file').files)));
$('volume-file').addEventListener('change', () => openReplay(Array.from($('volume-file').files), null, true));
const embedded = Array.from(document.querySelectorAll('script[type="application/json"][data-player-replay-part]'));
if (embedded.length) {
  const parts = embedded.map(element => new Blob([element.textContent]));
  embedded.forEach(element => element.remove());
  void openReplay(parts, document.getElementById('replay-volume')?.dataset.volume ?? null);
}

function advancePosition(now) {
  const { packets } = replay;
  cursor = Math.min(packets.at(-1).elapsedMilliseconds, cursor + Math.max(0, now - lastTime) * speed);
  lastTime = Math.max(lastTime, now);
  let next = index;
  while (next + 1 < packets.length && packets[next + 1].elapsedMilliseconds <= cursor) next++;
  if (next !== index) show(next, true);
  else showTime();
}

function advance(now) {
  if (restartAt !== null) {
    if (now >= restartAt) {
      show(0);
      lastTime = now;
      restartAt = null;
    }
    animation = requestAnimationFrame(advance);
    return;
  }
  advancePosition(now);
  if (index === replay.packets.length - 1) {
    if (!loop.checked) { pause(); return; }
    scene.weather.pause();
    restartAt = now + loopPauseMilliseconds;
  }
  animation = requestAnimationFrame(advance);
}

$('play').addEventListener('click', () => {
  if (!replay) return;
  if (animation) {
    if (restartAt === null) advancePosition(performance.now());
    pause(); return;
  }
  if (index === replay.packets.length - 1) show(0);
  lastTime = performance.now();
  speed = Number($('speed').value);
  $('play').textContent = '暫停';
  animation = requestAnimationFrame(advance);
});
$('speed').addEventListener('change', () => {
  if (animation && restartAt === null) advancePosition(performance.now());
  speed = Number($('speed').value);
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
for (const select of [$('transition'), $('environment'), $('segment')]) {
  select.addEventListener('change', () => {
    if (select.value !== '') openFrame(Number(select.value));
    select.value = '';
  });
}
room.addEventListener('change', () => {
  if (!replay) return;
  clearFollow();
  showFollowOptions();
  scene.preset('top', room.value);
  updateRoomEvents();
});
follow.addEventListener('change', () => {
  if (!replay) return;
  followedFrames = [];
  if (follow.value) {
    for (const [i, packet] of replay.packets.entries()) {
      if (packet.frame.players.some(player => player.id === follow.value && (room.value === 'all' || player.roomId === Number(room.value))))
        followedFrames.push(i);
    }
  }
  updateFollow(index);
  if (!follow.value) {
    scene.follow = false;
    scene.select('');
    followStatus.textContent = '';
    return;
  }
  if (scene.follow) scene.radius = Math.min(scene.radius, scene.fitRadius(7));
  scene.draw();
});
$('follow-back').addEventListener('click', () => openFrame(followedFrames.findLast(i => i < index)));
$('follow-next').addEventListener('click', () => openFrame(followedFrames.find(i => i > index)));
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
