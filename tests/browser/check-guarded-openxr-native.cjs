const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');
const { chromium } = require('playwright');

const readyText = '1 / 1 席追蹤就緒。開始時會再核對最新畫格。';
const lostText = '0 / 1 席追蹤就緒。請查看名冊中的追蹤狀態。';
let token;

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const config = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  const { base, sessionId, revision, output } = config;
  token = config.token;
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  const session = `/api/sessions/${sessionId}`;
  const file = name => path.join(output, name);
  async function save(step, value) {
    const name = `console-${step}.json`;
    const data = JSON.stringify(value, null, 2);
    if (data.includes(token)) throw new Error('Credential in console evidence');
    await fs.writeFile(file(name + '.tmp'), data + '\n', { flag: 'wx' });
    await fs.rename(file(name + '.tmp'), file(name));
  }
  async function waitForEvidence(name, timeout) {
    const deadline = performance.now() + timeout;
    while (performance.now() < deadline) {
      try {
        await fs.access(file('console-stop.request'));
        throw new Error('Console stopped by fixture');
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      try {
        return JSON.parse(await fs.readFile(file(name), 'utf8'));
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      await delay(100);
    }
    throw new Error('Timed out waiting for ' + name);
  }

  const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_CLOSURE_CHROMIUM,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/console/', { timeout: 15000 });
    await page.locator('#login-key').fill(token);
    await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(sessionId);
    const status = page.locator('#tracked-vr-start-status');
    const start = page.getByRole('button', { name: '確認追蹤並開始', exact: true });
    const ready = status.and(page.getByText(readyText, { exact: true }));
    const lost = status.and(page.getByText(lostText, { exact: true }));

    async function clickBegin(expectedStatus) {
      const [reply] = await Promise.all([
        page.waitForResponse(item => item.url() === base + session + '/commands'
          && item.request().method() === 'POST' && item.request().postDataJSON().action === 'Begin'),
        start.click(),
      ]);
      const intent = reply.request().postDataJSON(), response = await reply.json();
      assert.equal(reply.status(), expectedStatus);
      assert.equal(intent.expectedSequence, revision);
      assert.equal(intent.requireTrackedStart, true);
      return { intent, response, status: reply.status() };
    }

    await ready.waitFor();
    await save('ready', { sessionId, status: readyText });
    await lost.waitFor();
    const refused = await clickBegin(409);
    assert.equal(refused.response.code, 'tracked-vr-start-not-ready');
    const notice = page.locator('#notice').filter({ hasText: 'VR 追蹤開場尚未就緒' });
    await notice.waitFor();
    await notice.screenshot({ path: file('console-tracking-lost.png'), animations: 'disabled' });
    await save('rejected', { ...refused, trackedStatus: lostText });

    await waitForEvidence('tracking-recovered.json', 25000);
    await ready.waitFor();
    const accepted = await clickBegin(200);
    assert.equal(accepted.response.session.state, 'Running');
    assert.equal(accepted.response.session.id, sessionId);
    assert.equal(accepted.response.commandId, accepted.intent.commandId);
    await save('accepted', { ...accepted, trackedStatus: readyText });

    const { worldSequence, closedFrames } = await waitForEvidence('console-replay-request.json', 55000);
    await page.locator('#include-ended').check();
    await page.locator('#session-select').selectOption(sessionId);
    const replay = page.getByRole('button', { name: '回看本場追蹤開場', exact: true });
    await replay.waitFor();
    const [reply] = await Promise.all([
      page.waitForResponse(item => new URL(item.url()).pathname === session + '/world/watch'
        && new URL(item.url()).searchParams.get('mode') === 'replay'),
      replay.click(),
    ]);
    assert.equal(reply.status(), 200);
    const query = new URL(reply.url()).searchParams;
    assert.equal(query.get('fromFrame'), String(worldSequence));
    assert.equal(query.get('throughFrame'), String(worldSequence));
    // An independent recording already has one room, without an explicit observer projection.
    const witness = await fetch(reply.url(), { headers: { Authorization: 'Bearer ' + token },
      signal: AbortSignal.timeout(8000) });
    assert.equal(witness.status, 200);
    const messages = (await witness.text()).trim().split(/\r?\n\r?\n/).map(message => {
      const lines = message.split(/\r?\n/);
      return { event: lines.find(line => line.startsWith('event: '))?.slice(7),
        data: JSON.parse(lines.find(line => line.startsWith('data: ')).slice(6)) };
    });
    const dataMessages = messages.filter(message => message.event !== 'status');
    assert.deepEqual(dataMessages.map(message => message.event), ['header', 'frame', 'saved-end']);
    const [header, frame, end] = dataMessages;
    const { packet } = frame.data;
    for (const { data } of [header, end]) {
      assert.equal(data.header.sessionId, sessionId);
      assert.deepEqual(data.header.roomIds, [1]);
      assert.equal(data.acceptedSequence, worldSequence);
      assert.equal(data.complete, false);
    }
    assert.equal(packet.sequence, worldSequence);
    const original = page.locator(`#world-canvas[data-sequence="${worldSequence}"]`);
    await original.waitFor();
    assert.equal(await page.locator('#world-recording').inputValue(), sessionId);
    assert.equal(await page.locator('#world-room').inputValue(), '1');
    assert.equal(await page.locator('#world-camera').inputValue(), 'top');
    await page.locator('#world-player').screenshot({ path: file('console-original-opening.png'), animations: 'disabled' });

    assert(worldSequence < closedFrames);
    await page.locator('#world-frame-next').click();
    await page.locator(`#world-canvas[data-sequence="${worldSequence + 1}"]`).waitFor();
    await page.locator('#world-begin-original').click();
    await original.waitFor();
    assert.deepEqual(errors, []);
    await save('replay', { sessionId, frameSequence: Number(await original.getAttribute('data-sequence')),
      adjacentFrame: worldSequence + 1, closedFrames, replayRequest: Object.fromEntries(query), roomId: 1, camera: 'top',
      streamId: header.data.header.streamId, packet });
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  const message = String(error.stack ?? error);
  process.stderr.write((token ? message.replaceAll(token, '[redacted]') : message) + '\n');
  process.exitCode = 1;
});
