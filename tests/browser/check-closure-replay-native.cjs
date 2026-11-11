const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const { base, token, roomId, recording, output } = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const { sessionId, streamId } = recording.header;
  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    await page.locator('#include-ended').check();
    await page.locator('#session-select').selectOption(sessionId);
    const reply = page.waitForResponse(response => new URL(response.url()).pathname === `/api/sessions/${sessionId}/world/watch`);
    await page.getByRole('button', { name: '回放原場次', exact: true }).and(page.locator('#open-closure-replay')).click();
    const response = await reply;
    assert.equal(response.status(), 200);
    const query = new URL(response.url()).searchParams;
    assert.equal(query.get('mode'), 'replay');
    assert.equal(query.get('fromFrame'), '1');
    assert.equal(query.get('observerRoomId'), String(roomId));
    assert.equal(query.has('throughFrame'), false);
    const records = (await response.text()).trim().split('\n\n').map(block => {
      const lines = block.split('\n');
      return { event: lines.find(line => line.startsWith('event: '))?.slice(7),
        data: JSON.parse(lines.find(line => line.startsWith('data: ')).slice(6)) };
    });
    const first = records[0], last = records.at(-1);
    assert.equal(first.event, 'header');
    assert.equal(last.event, 'complete');
    for (const { data } of [first, last]) {
      assert.equal(data.header.sessionId, sessionId);
      assert.equal(data.header.streamId, streamId);
      assert.equal(data.acceptedSequence, recording.acceptedSequence);
      assert.equal(data.complete, true);
      assert.equal(data.observerRoomId, roomId);
      assert(data.header.props.length > 0 && data.header.props.every(prop => prop.roomId === roomId));
    }
    const frames = records.filter(row => row.event === 'frame').map(row => row.data);
    assert.equal(frames.length, recording.acceptedSequence);
    assert(frames.some(({ packet }) => packet.frame.players.length && packet.frame.enemies.length));
    for (const [index, { packet, statistics, observerRoomId }] of frames.entries()) {
      assert.equal(observerRoomId, roomId);
      assert.equal(packet.sequence, index + 1);
      assert([...packet.frame.players, ...packet.frame.enemies, ...statistics].every(row => row.roomId === roomId));
    }
    assert.equal(frames.at(-1).packet.frame.phase, 'Ended');
    const canvas = page.locator('#world-canvas');
    await page.waitForFunction(tail => Number(document.querySelector('#world-canvas').dataset.sequence) === tail,
      recording.acceptedSequence, { polling: 100 });
    assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
    assert.deepEqual(await page.locator('#world-room option').evaluateAll(options => options.map(option => option.value)), [String(roomId)]);
    assert.equal(await page.locator('#world-camera').inputValue(), 'top');
    assert.match(await page.locator('#world-status').innerText(), new RegExp(`僅接收房間 ${roomId}`));
    assert.equal(await canvas.getAttribute('data-sequence'), String(recording.acceptedSequence));
    assert.deepEqual(errors, []);
    await page.locator('#world-player').screenshot({ path: path.join(path.dirname(output), path.basename(output, '.json') + '.png') });
    await fs.writeFile(output, JSON.stringify({ sessionId, streamId, roomId, fromFrame: frames[0].packet.sequence,
      throughFrame: frames.at(-1).packet.sequence, complete: true, projectedFrames: frames.length,
      visibleRooms: [roomId], terminalPhase: frames.at(-1).packet.frame.phase }, null, 2), { flag: 'wx' });
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
