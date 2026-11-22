// Exercise the actual single-file player without a web server.
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { resolve } = require('node:path');
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

async function main() {
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
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
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log('PASS: offline five-room events, nearest recorded player appearances, scoped reload and millisecond time seeking with irregular and duplicate timestamps');
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
