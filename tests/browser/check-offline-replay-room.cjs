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
    assert.equal(await control('event-count').innerText(), '2 個事件畫格');
    await control('event-kind').selectOption('ShotHit');
    await control('room').selectOption('1');
    assert.equal(await control('event-count').innerText(), '1 個事件畫格');
    await control('event-next').click();
    assert.match(await control('frame').innerText(), /第 12 格/);
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
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log('PASS: offline five-room event navigation, shared frame counts, departed player, empty room and scoped reload');
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
