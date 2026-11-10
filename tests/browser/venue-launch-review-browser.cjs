const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const route = '/venue/server-launch-review';
const panel = '#venue-launch-review', input = panel + '-file', button = panel + '-check', summary = panel + '-summary';
const rows = panel + '-rooms li';

async function login(page, base, token) {
  await page.goto(base + '/console/');
  await page.locator('#login-key').fill(token);
  await page.locator('#login-form button').click();
  await page.locator('#rooms .room-card').first().waitFor();
}

async function checkSelected(page) {
  const result = page.waitForResponse(response => response.url().endsWith('/api' + route) && response.request().method() === 'POST');
  await page.locator(button).click();
  return result;
}

function projected(body) {
  assert.deepEqual(Object.keys(body).sort(), ['instanceId', 'launchId', 'servers', 'topology', 'version']);
  for (const server of body.servers) {
    assert.deepEqual(Object.keys(server).sort(), ['roomIds', 'sessionId', 'streamId', 'udp']);
    if (server.udp) assert.deepEqual(Object.keys(server.udp).sort(), ['bindAddress', 'port']);
  }
}

async function choose(page, value) {
  await page.locator(input).setInputFiles({ name: 'launcher-result.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(value)) });
}

async function checkVenueLaunchReview({ context, api, tokens, base, screenshots, check, captureErrors, instanceId }) {
  const page = await context.newPage();
  captureErrors(page);
  const launchId = randomUUID(), streamId = randomUUID();
  const mission = await api('/missions', 'POST', { name: 'Launch review fixture', briefing: '', durationSeconds: 600,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201);
  const roomIds = [1, 2, 3, 4, 5];
  const session = await api('/sessions', 'POST', { missionId: mission.id, mode: 'Linked', roomIds }, 'Master', 201);
  const sessionPath = '/sessions/' + session.id;
  const raw = { schemaVersion: 1, status: 'venue-incomplete', complete: false, readyPublished: false, instanceId,
    venueLaunchId: launchId, topology: 'Linked', sourceAttachment: 'unconfirmed', endpointPublication: 'not-attempted',
    publicationError: 'PRIVATE_FIXTURE_MESSAGE',
    servers: [{ roomIds, result: { sessionId: session.id, streamId: null, udpBinding: null, childPid: 123,
      workDirectory: 'C:/PRIVATE_FIXTURE_DIRECTORY', gameServerKey: 'PRIVATE_FIXTURE_VALUE' } }] };
  const requests = [];
  page.on('request', request => { if (request.url().endsWith('/api' + route)) requests.push(request.postDataJSON()); });
  let release;
  try {
    const target = { version: 1, instanceId, launchId, topology: 'Linked', servers: [{ roomIds, sessionId: session.id, streamId: null, udp: null }] };
    await api(route, 'POST', target, 'Room1', 403);
    await api(route, 'POST', target, 'GameServer', 403);
    await login(page, base, tokens.Room1);
    check(await page.locator(panel).isHidden(), 'Only the master can open the original launch review');
    await login(page, base, tokens.Master);
    await page.locator(panel + ' summary').click();
    await choose(page, { ...raw, readyPublished: true });
    await page.locator(button).click();
    await page.locator(summary).filter({ hasText: '請選擇 64 KiB' }).waitFor();
    check(!requests.length && await page.locator(rows).count() === 0, 'Completed and unsupported reports stay local');
    await choose(page, { ...raw, instanceId: randomUUID() });
    assert.equal((await checkSelected(page)).status(), 409);
    await page.locator(summary).filter({ hasText: '另一個管理實例' }).waitFor();
    check(await page.locator(rows).count() === 0, 'A different instance cannot show a valid room result');
    await choose(page, raw);
    const unbound = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '場次尚未登記來源' }).waitFor();
    projected(requests.at(-1));
    assert.deepEqual(requests.at(-1), target);
    check(unbound.instanceVerified
      && unbound.servers[0].phase === 'Preparing' && (await page.locator(rows).textContent()).includes(session.id),
      'The browser sends only original identities, and shows the exact unbound Preparing session');

    await api('/venue/combat-streams', 'PUT', { version: 1, launchId, topology: 'Linked',
      servers: [{ sessionId: session.id, streamId, origin: 'Simulation', expectedSequence: session.sequence }] }, 'GameServer');
    const before = await api(sessionPath);
    const attached = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '尚未公告端點' }).waitFor();
    check(attached.servers[0].streamId === streamId && (await page.locator(rows).textContent()).includes('已登記本批來源')
      && JSON.stringify(await api(sessionPath)) === JSON.stringify(before), 'An original source can be present without an endpoint and without a new event');
    await page.locator(panel).screenshot({ path: path.join(screenshots, 'venue-launch-review-source.png') });

    await choose(page, { ...raw, venueLaunchId: randomUUID() });
    const foreign = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '已登記其他來源' }).waitFor();
    check(foreign.servers[0].streamId === null && !(await page.locator(rows).textContent()).includes(streamId),
      'A mismatched launch does not identify another source as the original');
    await api(sessionPath, 'DELETE', undefined, 'Master', 204);
    await choose(page, raw);
    const ended = await (await checkSelected(page)).json();
    await page.locator(rows).filter({ hasText: '已結束' }).waitFor();
    check(ended.servers[0].phase === 'Ended' && ended.servers[0].streamId === streamId,
      'A closed original session remains available for review');

    let received;
    const observed = new Promise(resolve => { received = resolve; });
    const held = new Promise(resolve => { release = resolve; });
    await page.route('**/api' + route, async handler => { received(); await held; await handler.continue(); });
    await page.locator(button).click();
    await observed;
    await page.locator('#tab-missions').click();
    const late = page.waitForResponse('**/api' + route);
    release();
    await late;
    await page.locator('#tab-operations').click();
    check(await page.locator(input).inputValue() === '' && await page.locator(rows).count() === 0
      && await page.locator(summary).textContent() === '', 'Leaving operations discards the file and ignores the held response');
  } finally {
    release?.();
    await page.close();
    const current = await api(sessionPath);
    if (current.state !== 'Ended') await api(sessionPath, 'DELETE', undefined, 'Master', 204);
  }
}

module.exports = { checkVenueLaunchReview };

if (require.main === module) {
  (async () => {
    const { chromium } = require('playwright');
    const inputChunks = [];
    for await (const chunk of process.stdin) inputChunks.push(chunk);
    const { base, token, reportPath, expected, output } = JSON.parse(Buffer.concat(inputChunks).toString('utf8'));
    assert.match(base, /^http:[/][/]127[.]0[.]0[.]1:[0-9]+$/);
    const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_SERVER_PLAN_CHROMIUM });
    try {
      const page = await browser.newPage();
      await login(page, base, token);
      await page.locator(panel + ' summary').click();
      await page.locator(input).setInputFiles(reportPath);
      const response = await checkSelected(page);
      assert.equal(response.status(), 200);
      projected(response.request().postDataJSON());
      const review = await response.json();
      assert.equal(review.instanceVerified, true);
      assert.equal(review.servers.length, expected.length);
      for (const [index, fields] of expected.entries())
        for (const [key, value] of Object.entries(fields)) assert.deepEqual(review.servers[index][key], value);
      await page.locator(rows).nth(expected.length - 1).waitFor();
      assert.match(await page.locator(summary).textContent(), /管理實例相符/);
      await fs.writeFile(output, JSON.stringify(review, null, 2) + '\n', { flag: 'wx' });
    } finally { await browser.close(); }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
