// Exercise the actual single-file player without a web server.
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { resolve } = require('node:path');
const { mkdtemp, readFile, rm, writeFile } = require('node:fs/promises');
const { tmpdir } = require('node:os');
const { chromium } = require('playwright');

function fixture() {
  const zero = { x: 0, y: 0, z: 0 }, rotation = { ...zero, w: 1 };
  const players = [1, 5].map(roomId => {
    const head = { x: (roomId - 3) * 14, y: 1.6, z: 0 };
    return { roomId, id: `00000000-0000-0000-0000-00000000000${roomId}`, head,
      forward: { ...zero, z: 1 }, muzzle: head, health: 100, rig: { kind: 'None', left: head, right: head,
        headRotation: rotation, leftRotation: rotation, rightRotation: rotation } };
  });
  // Room 1's event occurs after its player has left the clip's visible roster.
  const packets = [[], [players[1]], [players[0], players[1]]].map((owners, index) => ({
    sequence: 10 + index, elapsedMilliseconds: 500 + index * 200, weather: 'Clear', lightning: false,
    frame: { tick: 10 + index, phase: 'Running', visibility: 'Clear', night: false,
      players: index ? players.slice(1) : players, enemies: [] },
    events: owners.map(player => ({ playerId: player.id, kind: 'ShotHit', hasRay: false })),
  }));
  return { playerReplayVersion: 1, missionName: '五房驗證', clipName: '跨房事件', startFrame: 10, endFrame: 12,
    header: { schemaVersion: 1, environmentVersion: 1, rulesVersion: '0.8.0', origin: 'Simulation',
      sessionId: players[0].id, streamId: players[1].id, roomIds: [1, 2, 3, 4, 5], props: [] }, packets };
}

async function checkSparsePlayback(browser, url) {
  const page = await browser.newPage();
  try {
    await page.clock.install({ time: new Date('2026-01-01T00:00:00Z') });
    await page.clock.pauseAt(new Date('2026-01-01T00:00:01Z'));
    await page.goto(url);
    const clip = fixture();
    clip.header.missionClockVersion = 1;
    clip.header.missionDurationSeconds = 60;
    clip.packets.forEach((packet, i) => {
      packet.elapsedMilliseconds = [5000, 8000, 10000][i];
      packet.frame.tick = 20 * i;
    });
    const control = name => page.locator('#player-replay-' + name);
    const toggle = () => control('play').evaluate(button => button.click());
    await control('file').setInputFiles({ name: 'sparse.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(clip)) });
    await control('message').filter({ hasText: '已載入 3 格' }).waitFor();
    await control('seconds').fill('0.75');
    await control('seek').evaluate(form => form.requestSubmit());
    await toggle();
    await page.clock.fastForward(1250);
    assert.equal(await control('time').innerText(), '片段 2.00 / 5.00 秒', 'Playback time must advance between recorded frames');
    assert.match(await control('frame').innerText(), /第 10 格/);
    assert.match(await control('clock').innerText(), /活動時間 00:00/);
    await toggle();
    await page.clock.fastForward(2500);
    assert.equal(await control('time').innerText(), '片段 2.00 / 5.00 秒');
    await control('speed').selectOption('2');
    await toggle();
    await page.clock.fastForward(625);
    assert.equal(await control('time').innerText(), '片段 3.25 / 5.00 秒');
    assert.match(await control('frame').innerText(), /第 11 格/);
    assert.match(await control('clock').innerText(), /活動時間 00:01/);
    // Account for the time before a speed change and before pause, even without an animation frame.
    await page.clock.runFor(5);
    await control('speed').selectOption('.5');
    await page.clock.runFor(4);
    await toggle();
    assert.equal(await control('time').innerText(), '片段 3.262 / 5.00 秒');
    await toggle();
    await page.clock.fastForward(4000);
    assert.equal(await control('play').innerText(), '播放');
    assert.equal(await control('time').innerText(), '片段 5.00 / 5.00 秒');
    assert.match(await control('frame').innerText(), /第 12 格/);
    console.log('PASS: sparse replay time, frozen recorded clock, playback-rate changes, pause and exact ending');
  } finally { await page.close(); }
}

async function checkVolumeContinuity(browser, templatePath) {
  const page = await browser.newPage();
  const directory = await mkdtemp(resolve(tmpdir(), 'vr-replay-volume-'));
  try {
    const template = await readFile(templatePath, 'utf8');
    const first = fixture(), player = first.packets[0].frame.players[1];
    const other = { ...player, id: '00000000-0000-0000-0000-000000000099' };
    const volume = (start, packets, clipStart = 10) => {
      const part = { ...first, startFrame: start, endFrame: start + packets.length - 1, packets };
      const marker = `<span hidden id="replay-volume" data-volume="${first.header.sessionId}:${start}:${part.endFrame}:21"></span>`;
      const origin = clipStart === null ? '' : `<span hidden id="replay-clip-start">${clipStart}</span>`;
      return template.replace('<!--player-replay-data-->', () => marker + origin +
        '<script type="application/json" data-player-replay-part>' + JSON.stringify(part) + '</script>');
    };
    const path = resolve(directory, 'first.html');
    const suspended = p => ({ ...p, suspended: true, frame: { ...p.frame, phase: 'Paused' } });
    const storm = p => ({ ...p, weather: 'Storm', lightning: true, frame: { ...p.frame, night: true, visibility: 'Storm' } });
    const firstPackets = [storm(first.packets[0]), first.packets[1], suspended(first.packets[2])];
    await writeFile(path, volume(10, firstPackets));
    const packet = (sequence, elapsedMilliseconds, tick, players) => ({ ...first.packets[0], sequence, elapsedMilliseconds,
      frame: { ...first.packets[0].frame, tick, players }, events: [] });
    const nextPackets = [packet(13, 900, 12, [other]), packet(14, 1100, 13, [other, player]), suspended(packet(15, 1300, 14, [player]))].map(storm);
    const field = name => page.locator('#player-replay-' + name);
    const camera = () => page.locator('#replay-canvas').getAttribute('data-camera');
    const choose = async (start, packets, input = 'volume-file', clipStart = 10) => {
      await field(input).setInputFiles({ name: 'renamed.html', mimeType: 'text/html', buffer: Buffer.from(volume(start, packets, clipStart)) });
      await page.waitForFunction(() => !document.querySelector('#player-replay-message').textContent.includes('正在讀取'));
    };
    await page.goto(pathToFileURL(path).href);
    await field('room').selectOption('5');
    await field('follow').selectOption(player.id);
    assert.ok(await field('previous').isHidden(), 'The saved clip begins at frame 10');
    const initialCamera = await camera();
    // The viewer is on frame 10. Both checks must compare against the last frame (12).
    for (const change of [{ elapsedMilliseconds: 899 }, { frame: { ...nextPackets[0].frame, tick: 11 } }]) {
      await choose(13, [{ ...nextPackets[0], ...change }, ...nextPackets.slice(1)]);
      assert.match(await field('message').innerText(), /早於本冊末格/);
      assert.match(await field('frame').innerText(), /第 10 格/);
      assert.equal(await camera(), initialCamera);
      assert.equal(await field('follow').inputValue(), player.id);
    }
    await choose(13, nextPackets);
    assert.match(await field('frame').innerText(), /第 13 格/);
    assert.equal(await camera(), initialCamera);
    assert.ok(await field('environment-field').isVisible(), 'Show the storm that starts on the first frame of the next volume');
    assert.match(await field('environment').locator('option[value="0"]').innerText(), /第 13 格.*暴風雨.*夜晚.*雷電開啟/);
    assert.match(await field('transition').locator('option[value="0"]').innerText(), /遊戲來源恢復/);
    await field('next').click();
    await field('environment').selectOption('0');
    assert.match(await field('frame').innerText(), /第 13 格/);
    assert.equal(await field('room').inputValue(), '5');
    assert.equal(await field('follow').inputValue(), player.id);
    await field('follow-next').click();
    assert.match(await field('frame').innerText(), /第 14 格/);
    assert.equal(await field('follow-status').innerText(), '');
    await choose(13, nextPackets, 'previous-file');
    assert.match(await field('message').innerText(), /本冊前一格/);
    await choose(10, [firstPackets[0], firstPackets[1], { ...firstPackets[2], elapsedMilliseconds: 901 }], 'previous-file');
    assert.match(await field('message').innerText(), /晚於本冊首格/);
    assert.match(await field('frame').innerText(), /第 14 格/);
    await choose(10, firstPackets, 'previous-file', 9);
    assert.match(await field('message').innerText(), /本冊前一格/);
    await choose(10, firstPackets, 'previous-file', null);
    assert.match(await field('frame').innerText(), /第 12 格/);
    assert.equal(await field('room').inputValue(), '5');
    assert.equal(await field('follow').inputValue(), player.id);
    assert.ok(await field('previous').isHidden(), 'Retain the known clip start when reading an older volume');
    await choose(13, nextPackets);
    await field('follow-next').click();
    const followingCamera = await camera();
    await choose(16, [16, 17, 18].map(n => suspended(storm(packet(n, n * 100, n, [other])))));
    assert.ok(await field('environment-field').isHidden());
    assert.ok(await field('transition-field').isHidden(), 'Continuing the same source pause must not report a second pause');
    assert.match(await field('frame').innerText(), /第 16 格/);
    assert.equal(await field('follow').inputValue(), '');
    assert.match(await field('follow-status').innerText(), /沒有在本冊出現/);
    assert.equal(await camera(), followingCamera);
    await page.locator('#replay-canvas').press('ArrowRight');
    const freeCamera = await camera();
    assert.notEqual(freeCamera, followingCamera);
    await choose(19, [19, 20, 21].map(n => packet(n, n * 100, n, [other])));
    assert.match(await field('frame').innerText(), /第 19 格/);
    assert.equal(await camera(), freeCamera);
    assert.equal(await field('volume-label').innerText(), '已到最後一冊。');
    assert.ok(await field('previous').isVisible());
    console.log('PASS: four consecutive volumes preserve the camera and follow the original player across a gap');
  } finally {
    await page.close();
    await rm(directory, { recursive: true, force: true });
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    await checkVolumeContinuity(browser, resolve(process.argv[2]));
    await checkSparsePlayback(browser, pathToFileURL(resolve(process.argv[2])).href);
    const page = await browser.newPage();
    const errors = [], network = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
    await page.goto(pathToFileURL(resolve(process.argv[2])).href);
    const control = name => page.locator('#player-replay-' + name);
    const clip = fixture();
    const load = async () => {
      await control('file').setInputFiles({ name: 'clip.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(clip)) });
      await control('message').filter({ hasText: '已載入 3 格' }).waitFor();
    };
    await load();
    assert.ok(await control('activity-seek').isHidden(), 'Legacy recordings have no mission clock');
    const activityClip = structuredClone(clip);
    Object.assign(activityClip.header, { missionClockVersion: 1, missionDurationSeconds: 60 });
    activityClip.endFrame = 13;
    activityClip.packets.push(structuredClone(activityClip.packets.at(-1)));
    activityClip.packets.forEach((packet, i) => {
      packet.sequence = 10 + i;
      packet.elapsedMilliseconds = 1000 + 500 * i;
      packet.frame.tick = [100, 101, 101, 110][i];
      if (i === 2) packet.frame.phase = 'Paused';
    });
    await control('file').setInputFiles({ name: 'activity.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(activityClip)) });
    await control('activity-seek').waitFor();
    const activity = control('activity-seconds');
    assert.equal(await activity.getAttribute('min'), '5');
    assert.equal(await activity.getAttribute('max'), '5.5');
    await control('room').selectOption('5');
    await control('follow').selectOption(clip.packets[1].frame.players[0].id);
    for (const [target, sequence] of [['5.5', 13], ['5.05', 11], ['5.10', 13], ['5', 10], ['4', 10], ['6', 10]]) {
      await activity.fill(target);
      await activity.press('Enter');
      assert.match(await control('frame').innerText(), new RegExp('第 ' + sequence + ' 格'));
      assert.equal(await control('room').inputValue(), '5');
      assert.equal(await control('follow').inputValue(), clip.packets[1].frame.players[0].id);
    }
    await load();
    assert.ok(await control('activity-seek').isHidden());
    console.log('PASS: recorded activity time, paused duplicate ticks, sparse samples, clip boundaries and legacy files');
    assert.ok(await control('environment-field').isHidden());
    assert.equal(await control('event-count').innerText(), '2 個事件畫格');
    await control('event-kind').selectOption('ShotHit');
    await control('room').selectOption('1');
    assert.equal(await control('event-count').innerText(), '1 個事件畫格');
    await control('event-next').click();
    assert.match(await control('frame').innerText(), /第 12 格/);
    const gap = fixture();
    gap.clipName = '玩家再次入鏡';
    gap.endFrame = 15;
    gap.packets = [1, 0, 1, 1, 0, 1].map((source, index) => {
      const packet = structuredClone(gap.packets[source]);
      packet.frame.tick = packet.sequence = 10 + index;
      packet.elapsedMilliseconds = [0, 100, 200, 200, 200, 8000][index];
      return packet;
    });
    await control('file').setInputFiles({ name: 'gap.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(gap)) });
    await control('title').filter({ hasText: gap.clipName }).waitFor();
    await control('room').selectOption('1');
    const followed = gap.packets[1].frame.players[0].id;
    await control('follow').selectOption(followed);
    assert.ok(await control('follow-back').isHidden());
    await control('follow-next').evaluate(button => {
      document.getElementById('player-replay-play').click();
      button.click();
    });
    assert.equal(await control('play').innerText(), '播放');
    assert.match(await control('frame').innerText(), /第 11 格/);
    assert.ok(await control('follow-next').isHidden());
    await control('next').click();
    assert.ok(await control('follow-back').isVisible() && await control('follow-next').isVisible());
    await control('follow-next').click();
    assert.match(await control('frame').innerText(), /第 14 格/);
    await control('back').click();
    await control('follow-back').click();
    assert.match(await control('frame').innerText(), /第 11 格/);
    assert.equal(await control('follow').inputValue(), followed);
    assert.equal(await control('room').inputValue(), '1');
    await control('number').fill('15');
    await control('jump').getByRole('button').click();
    assert.ok(await control('follow-next').isHidden() && await control('follow-back').isVisible());
    await control('room').selectOption('5');
    assert.ok(await control('follow-next').isHidden() && await control('follow-back').isHidden());
    const seek = async value => {
      await control('seconds').fill(value);
      await control('seek').getByRole('button').click();
    };
    const timed = fixture();
    timed.clipName = '不等間距的時間定位';
    timed.endFrame = 14;
    timed.packets = [30001, 30103, 30103, 32222, 33337].map((elapsedMilliseconds, index) => ({
      ...structuredClone(timed.packets[1]), sequence: 10 + index, elapsedMilliseconds
    }));
    for (const [index, packet] of timed.packets.entries()) {
      if (index >= 1) packet.weather = 'Rain';
      packet.frame.night = index >= 2;
      packet.lightning = index >= 3;
    }
    await control('file').setInputFiles({ name: 'timed.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(timed)) });
    await control('message').filter({ hasText: '已載入 5 格' }).waitFor();
    assert.equal(await control('seconds').getAttribute('max'), '3.336');
    await control('room').selectOption('5');
    await control('follow').selectOption(timed.packets[0].frame.players[0].id);
    const weatherMenu = control('environment');
    assert.deepEqual(await weatherMenu.locator('option').allTextContents(), [
      '跳到畫格', '0.00 秒 · 第 10 格 · 晴朗 · 白天 · 雷電關閉', '0.102 秒 · 第 11 格 · 下雨 · 白天 · 雷電關閉',
      '0.102 秒 · 第 12 格 · 下雨 · 夜晚 · 雷電關閉', '2.221 秒 · 第 13 格 · 下雨 · 夜晚 · 雷電開啟'
    ]);
    await control('play').click();
    for (const index of [2, 1, 3, 0]) {
      const option = await weatherMenu.locator(`option[value="${index}"]`).innerText();
      await weatherMenu.selectOption(String(index));
      assert.ok((await control('frame').innerText()).includes(`第 ${10 + index} 格`));
      assert.ok(option.endsWith(await control('weather').innerText()));
      assert.equal(await control('play').innerText(), '播放');
      assert.equal(await control('room').inputValue(), '5');
      assert.equal(await control('follow').inputValue(), timed.packets[0].frame.players[0].id);
    }
    await seek('0');
    assert.match(await control('frame').innerText(), /第 10 格/);
    await control('play').click();
    await seek('0.102');
    assert.match(await control('frame').innerText(), /第 12 格/);
    assert.equal(await control('play').innerText(), '播放');
    await seek('2.220');
    assert.match(await control('frame').innerText(), /第 12 格/);
    assert.match(await control('time').innerText(), /2\.22 \/ 3\.336/);
    await control('play').evaluate(async button => {
      button.click();
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      button.click();
    });
    assert.match(await control('frame').innerText(), /第 13 格/);
    await seek('2.221');
    assert.match(await control('frame').innerText(), /第 13 格/);
    assert.match(await control('time').innerText(), /2\.221 \/ 3\.336/);
    for (const value of ['3.337', '-0.001', '0.0005', '']) {
      await seek(value);
      assert.equal(await control('seconds').evaluate(input => input.validity.valid), false);
      assert.match(await control('frame').innerText(), /第 13 格/);
    }
    await seek('3.336');
    assert.match(await control('frame').innerText(), /第 14 格/);
    assert.equal(await control('room').inputValue(), '5');
    assert.equal(await control('follow').inputValue(), timed.packets[0].frame.players[0].id);
    const instant = structuredClone(timed);
    instant.clipName = '同一毫秒的片段';
    for (const packet of instant.packets) packet.elapsedMilliseconds = 777;
    await control('file').setInputFiles({ name: 'instant.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(instant)) });
    await control('title').filter({ hasText: instant.clipName }).waitFor();
    assert.equal(await control('seconds').getAttribute('max'), '0');
    await seek('0');
    assert.match(await control('frame').innerText(), /第 14 格/);
    await control('back').click();
    assert.match(await control('frame').innerText(), /第 13 格/);
    await load();
    assert.equal(await control('seconds').inputValue(), '');
    assert.ok(await control('environment-field').isHidden());
    assert.equal(await control('seconds').getAttribute('max'), '0.4');
    const long = fixture();
    const frame = long.packets[0];
    const batch = Array.from({ length: 310 }, (_, i) => ({
      ...frame, frame: { ...frame.frame, tick: i }, sequence: 100 + i, elapsedMilliseconds: 6000 + 50 * i
    }));
    const part = (name, start, end) => ({ ...long, clipName: name, startFrame: batch[start].sequence,
      endFrame: batch[end].sequence, packets: batch.slice(start, end + 1) });
    const firstPart = part('上半場', 0, 155), lastPart = part('下半場', 155, 309);
    const chooseParts = (...parts) => control('file').setInputFiles(parts.map((data, i) =>
      ({ name: `clip-${i}.json`, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(data)) })));
    await chooseParts(lastPart, firstPart);
    await control('message').filter({ hasText: '已載入 310 格' }).waitFor();
    assert.deepEqual(await control('segment').locator('option').allTextContents(),
      ['選擇片段', '上半場 · 第 100–255 格', '下半場 · 第 255–409 格']);
    await control('room').selectOption('1');
    await control('follow').selectOption(frame.frame.players[0].id);
    await control('segment').selectOption('155');
    assert.match(await control('frame').innerText(), /第 255 格/);
    await control('back').click();
    await control('play').click();
    await page.waitForFunction(() => Number(document.getElementById('replay-timeline').value) >= 156);
    await control('play').click();
    assert.equal(await control('follow').inputValue(), frame.frame.players[0].id);
    assert.equal(await control('room').inputValue(), '1');
    await seek('15.450');
    assert.match(await control('frame').innerText(), /第 409 格/);
    await chooseParts(part('起點', 0, 2), lastPart);
    await control('message').filter({ hasText: '缺少第 103 至 254 格' }).waitFor();
    assert.ok(await control('view').isHidden());
    await load();
    assert.ok(await control('segment-field').isHidden());
    await control('room').selectOption('1'); await control('event-next').click();
    assert.match(await control('event-frame').innerText(), /1 筆/);
    await control('room').selectOption('5');
    await control('event-back').click();
    assert.match(await control('frame').innerText(), /第 11 格/);
    await control('room').selectOption('3');
    assert.ok(await control('event-back').isDisabled() && await control('event-next').isDisabled());
    assert.ok(await control('event-frame').isHidden());
    await control('room').selectOption('all');
    await control('event-next').click();
    assert.match(await control('event-frame').innerText(), /2 筆/);
    const departedEvent = '00000000-0000-0000-0000-000000000010';
    clip.packets[0].frame.players.shift();
    clip.packets[2].events[0].eventId = departedEvent;
    clip.eventRooms = { [departedEvent]: 1 };
    await load();
    await control('room').selectOption('1');
    assert.ok(await control('follow').isDisabled());
    await control('event-next').click();
    assert.match(await control('frame').innerText(), /第 12 格/);
    assert.match(await control('event-frame').innerText(), /1 筆/);
    delete clip.eventRooms;
    clip.playerReplayVersion = 2;
    clip.roomId = 1;
    clip.header.roomIds = [1];
    for (const packet of clip.packets) packet.frame.players = [];
    clip.packets[1].events = [];
    clip.packets[2].events.splice(1);
    await load();
    await control('event-next').click();
    assert.match(await control('frame').innerText(), /第 12 格/);
    if (process.argv[3]) {
      await control('file').setInputFiles(resolve(process.argv[3]));
      await control('message').filter({ hasText: '已載入 2 格' }).waitFor();
      for (const selected of ['1', '5']) {
        await control('room').selectOption(selected);
        assert.equal(await control('event-count').innerText(), '1 個事件畫格');
        assert.match(await control('event-frame').innerText(), /玩家受傷 1 筆/);
        assert.equal(await control('follow').isDisabled(), selected === '1');
      }
      await control('room').selectOption('all');
      assert.match(await control('event-frame').innerText(), /玩家受傷 2 筆/);
      await seek(await control('seconds').getAttribute('max'));
      assert.ok(await control('next').isDisabled());
    }
    if (process.argv[4]) {
      const conditions = [
        ['linked', '暴風雨 · 夜晚 · 雷電開啟', 640],
        ['room-1', '下雨 · 白天 · 雷電關閉', 64], ['room-2', '下雨 · 白天 · 雷電關閉', 64],
        ['room-3', '暴風雨 · 夜晚 · 雷電開啟', 128], ['room-4', '濃霧 · 夜晚 · 雷電關閉', 0],
        ['room-5', '暴風雨 · 夜晚 · 雷電開啟', 128]
      ];
      const canvas = page.locator('#replay-canvas');
      for (const [name, label, rain] of conditions) {
        await control('file').setInputFiles(resolve(process.argv[4], name + '.json'));
        await control('title').filter({ hasText: name }).waitFor();
        assert.equal(await weatherMenu.locator('option').count(), 3);
        assert.equal(await control('weather').innerText(), '晴朗 · 白天 · 雷電關閉');
        assert.equal(await canvas.getAttribute('data-rain-count'), '0');
        await weatherMenu.selectOption('2');
        assert.match(await control('frame').innerText(), /第 3 格/);
        assert.equal(await control('weather').innerText(), label);
        assert.equal(await canvas.getAttribute('data-rain-count'), String(rain));
        await weatherMenu.selectOption('0');
        assert.equal(await control('weather').innerText(), '晴朗 · 白天 · 雷電關閉');
      }
      console.log('PASS: opening all six API exports, selecting environment changes and restoring the initial weather');
    }
    if (process.argv[5]) {
      const partFile = (scope, name) => resolve(process.argv[5], scope + '-' + name + '.json');
      for (const scope of ['full', 'room']) {
        await control('file').setInputFiles([partFile(scope, 'last'), partFile(scope, 'first')]);
        await control('message').filter({ hasText: '已載入 310 格' }).waitFor();
        await control('segment').selectOption('159');
        assert.match(await control('frame').innerText(), /第 160 格/);
        await control('next').click();
        assert.match(await control('frame').innerText(), /第 161 格/);
        assert.equal(await control('room').locator('option').count(), scope === 'full' ? 6 : 1);
        await seek(await control('seconds').getAttribute('max'));
        assert.match(await control('frame').innerText(), /第 310 格/);
      }
      await control('file').setInputFiles([partFile('full', 'first'), partFile('room', 'last')]);
      await control('message').filter({ hasText: '相同房間範圍' }).waitFor();
      assert.ok(await control('view').isHidden());
      console.log('PASS: consecutive sealed exports in full venue and room scope; mixed scopes refused');
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log('PASS: offline five-room events, nearest recorded player appearances, scoped reload and millisecond time seeking with irregular and duplicate timestamps');
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
