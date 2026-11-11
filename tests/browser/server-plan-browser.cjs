const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const route = '/venue/server-plan';
const panel = '#venue-server-plan';
const ports = '#venue-server-ports input';
const issue = '#venue-server-download';
const status = '#venue-server-status';

async function login(page, base, token) {
  await page.goto(base + '/console/');
  await page.locator('#login-key').fill(token);
  await page.locator('#login-form button').click();
  await page.locator('#rooms .room-card').first().waitFor();
}

async function open(page) {
  await page.locator(panel + ' summary').click();
  await page.locator('#venue-server-read').click();
  await page.locator('#venue-server-rooms li').nth(4).waitFor();
}

async function fill(page, plan) {
  await page.locator('#venue-server-instance').fill(plan.controlInstance);
  await page.locator('#venue-server-address').fill(plan.address);
  await page.locator('#venue-server-bind').fill(plan.listenAddress);
  assert.equal(await page.locator(ports).count(), plan.servers.length);
  for (const [index, server] of plan.servers.entries()) await page.locator(ports).nth(index).fill(String(server.port));
}

async function download(page, filename, expected) {
  const [file] = await Promise.all([page.waitForEvent('download'), page.locator(issue).click()]);
  assert.equal(file.suggestedFilename(), 'vr-command-venue-server-plan.json');
  await file.saveAs(filename);
  assert.deepEqual(JSON.parse(await fs.readFile(filename, 'utf8')), expected);
}

async function checkServerPlan({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage(), active = new Set();
  captureErrors(page);
  const requests = [];
  page.on('request', request => { if (request.url().endsWith(route)) requests.push([request.method(), request.postData()]); });
  const state = id => '/sessions/' + id;
  const command = (id, action, fields = {}) => api(state(id) + '/commands', 'POST', { commandId: randomUUID(), action, ...fields });
  const mission = mode => api('/missions', 'POST', {
    name: mode + ' server-plan fixture', briefing: '', durationSeconds: 600,
    environment: { mode, weather: 'Clear', timeOfDay: 'Day', lightning: false }, enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: []
  }, 'Master', 201);
  const create = async (saved, mode, roomIds) => {
    const session = await api('/sessions', 'POST', { missionId: saved.id, mode, roomIds }, 'Master', 201);
    active.add(session.id);
    return session;
  };
  const end = async id => { await command(id, 'End'); active.delete(id); };
  const shape = (topology, sessions) => ({ version: 4, controlInstance: 'C:\\Private Venue\\control\\control-instance.json', topology,
    address: '192.168.1.10', listenAddress: '0.0.0.0',
    servers: sessions.map((session, index) => ({ sessionId: session.id, sessionSequence: session.sequence,
      missionId: session.mission.id, roomIds: session.roomIds, port: 18800 + index })) });
  try {
    await api(route, 'GET', undefined, 'Room1', 403);
    await api(route, 'GET', undefined, 'GameServer', 403);
    await login(page, base, tokens.Room1);
    check(await page.locator(panel).isHidden(), 'Room controller and GameServer cannot access the venue server plan');
    const vacant = await api(route);
    check(!vacant.ready && vacant.topology === null && vacant.rooms.length === 5
      && vacant.rooms.every(room => room.state === 'missing-session' && room.sessionId === null), 'Vacant rooms have no launch identity');

    const vr = await mission('VR'), mr = await mission('MR');
    const independent = [];
    for (const room of [1, 2, 3, 4, 5]) independent.push(await create(room === 3 ? mr : vr, 'Independent', [room]));
    await login(page, base, tokens.Master);
    await open(page);
    check(await page.locator('#venue-server-form').isHidden()
      && (await page.locator('#venue-server-rooms li').nth(2).textContent()).includes('等待鎖定 MR 校正'),
      'A mixed venue exposes the exact MR room waiting for a lock and cannot download');
    await command(independent[2].id, 'SetRoomAlignment', { roomAlignment: { room3: 'a'.repeat(64) } });
    independent[2] = await api(state(independent[2].id));
    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-form').waitFor();
    const independentPlan = shape('Independent', independent);
    await fill(page, independentPlan);
    await page.locator('#venue-server-instance').fill('control-instance.json');
    check(await page.locator(issue).isDisabled(), 'Plan export rejects a relative management instance path');
    await page.locator('#venue-server-instance').fill(independentPlan.controlInstance);
    await page.locator(ports).nth(4).fill(String(independentPlan.servers[0].port));
    check(await page.locator(issue).isDisabled(), 'Independent export refuses duplicate UDP ports');
    await page.locator(ports).nth(4).fill(String(independentPlan.servers[4].port));
    await page.locator('#venue-server-bind').fill('192.168.1.11');
    check(await page.locator(issue).isDisabled(), 'An explicit bind address must match the advertised address');
    await page.locator('#venue-server-bind').fill(independentPlan.listenAddress);
    const before = await api('/sessions');
    await download(page, path.join(screenshots, 'independent-venue-server-plan.json'), independentPlan);
    check(JSON.stringify(await api('/sessions')) === JSON.stringify(before)
      && requests.length > 0 && requests.every(([method, body]) => method === 'GET' && body === null),
      'Actual download retains the five room revisions and mission IDs without exposing credentials or sending the local path to management');
    await page.locator(panel).screenshot({ path: path.join(screenshots, 'venue-server-plan.png') });

    const unexpected = [];
    page.on('download', file => unexpected.push(file.suggestedFilename()));
    await command(independent[4].id, 'SetEnvironment', { environment: { ...independent[4].environment, weather: 'Rain' } });
    await page.locator(issue).click();
    await page.locator(status).filter({ hasText: '場次狀態已變更' }).waitFor();
    check(await page.locator('#venue-server-form').isHidden() && !unexpected.length
      && (await page.locator(status).textContent()).includes('房間 5'),
      'A configuration revision identifies the changed room and cancels the stale export');

    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-form').waitFor();
    const revisedIndependent = shape('Independent', await Promise.all(independent.map(session => api(state(session.id)))));
    check((await page.locator(ports).evaluateAll(inputs => inputs.map(input => Number(input.value))))
      .every((port, index) => port === revisedIndependent.servers[index].port),
      'Rereading after a stale export restores the five explicit room ports');
    await download(page, path.join(screenshots, 'revised-independent-venue-server-plan.json'), revisedIndependent);
    check(unexpected.length === 1, 'The revised plan uses the new revision and the original explicit ports');
    await api(state(independent[4].id) + '/combat-stream', 'POST', { streamId: randomUUID(), origin: 'Simulation' }, 'GameServer');
    await page.locator(issue).click();
    await page.locator(status).filter({ hasText: '場次狀態已變更' }).waitFor();
    check(await page.locator('#venue-server-form').isHidden() && unexpected.length === 1,
      'A source attached between preview and download cancels the stale export');
    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-rooms li').nth(4).filter({ hasText: '已附掛遊戲來源' }).waitFor();
    check(await page.locator('#venue-server-form').isHidden(), 'An unavailable preview cannot download a saved port draft');
    for (const session of independent) await end(session.id);

    const linked = await create(vr, 'Linked', [1, 2, 3, 4, 5]);
    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-form').waitFor();
    const linkedPlan = shape('Linked', [linked]);
    check(await page.locator(ports).first().inputValue() === '7777', 'Linked and Independent use separate port drafts');
    linkedPlan.servers[0].port = 19341;
    await fill(page, linkedPlan);
    await page.locator(ports).first().fill('');
    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-form').waitFor();
    check(await page.locator(ports).first().inputValue() === '' && await page.locator(issue).isDisabled(),
      'Rereading an explicitly cleared port does not silently substitute the default');
    await page.locator(ports).first().fill(String(linkedPlan.servers[0].port));
    await download(page, path.join(screenshots, 'linked-venue-server-plan.json'), linkedPlan);
    check(await page.locator(ports).count() === 1 && unexpected.length === 2,
      'A Linked venue downloads one port and one exact session revision for all five original rooms');
    await end(linked.id);
    const replacement = [];
    for (const room of [1, 2, 3, 4, 5]) replacement.push(await create(vr, 'Independent', [room]));
    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-form').waitFor();
    check((await page.locator(ports).evaluateAll(inputs => inputs.map(input => input.value))).join(',') === '18800,18801,18802,18803,18804',
      'Returning to Independent restores its original room ports, even after an unavailable preview');
    await download(page, path.join(screenshots, 'replacement-venue-server-plan.json'), shape('Independent', replacement));
    await page.locator('#tab-missions').click();
    await page.locator('#tab-operations').click();
    await page.locator(panel + ' summary').click();
    check(await page.locator('#venue-server-instance').inputValue() === '' && await page.locator('#venue-server-form').isHidden(),
      'Leaving operations discards the local path and the selected plan');
    await page.locator('#venue-server-read').click();
    await page.locator('#venue-server-form').waitFor();
    check((await page.locator(ports).evaluateAll(inputs => inputs.map(input => input.value))).join(',') === '7777,7778,7779,7780,7781',
      'Leaving operations clears the port drafts together with the plan');
  } finally {
    await page.close();
    for (const id of active) await end(id);
  }
}

module.exports = { checkServerPlan };

async function prepareRoomLayouts(page, missions, output) {
  await page.locator('#launch-mode').selectOption('IndependentSet');
  await page.locator('#launch-room-missions-toggle').check();
  for (const [index, mission] of missions.entries())
    await page.locator(`#launch-room-mission-${index + 1}`).selectOption(mission.id);
  const overview = page.locator('#launch-room-layouts');
  await overview.locator('summary').click();
  const previews = [];
  for (const [index, mission] of missions.entries()) {
    const roomId = index + 1, card = overview.locator(`[data-room-layout-preview="${roomId}"]`);
    await card.locator('[data-status=valid]').waitFor();
    const transforms = await card.locator('.room-layout-props [data-index]').evaluateAll(nodes => nodes.map(node => node.getAttribute('transform')));
    assert.equal(await card.getAttribute('data-mission-id'), mission.id);
    assert.equal(await card.locator('.room-layout-spawns [data-seat]').count(), 5);
    assert.deepEqual(transforms, mission.definition.props.map(prop =>
      `translate(${prop.position.x} ${-prop.position.z}) rotate(${prop.yawDegrees})`));
    previews.push({ roomId, missionId: mission.id, transforms });
  }
  await overview.screenshot({ path: path.join(path.dirname(output), 'native-independent-room-layouts.png') });
  const response = page.waitForResponse(reply => new URL(reply.url()).pathname === '/api/sessions/independent-set'
    && reply.request().method() === 'POST');
  const confirmation = page.waitForEvent('dialog').then(async dialog => {
    const text = dialog.message();
    await dialog.accept();
    return text;
  });
  await page.locator('#create-session-form button[type=submit]').click();
  const accepted = await response;
  assert.equal(accepted.status(), 201);
  const confirmationText = await confirmation;
  assert(previews.every(({ roomId }, index) => confirmationText.includes(`房間 ${roomId}　${missions[index].definition.name}`)));
  assert.deepEqual(accepted.request().postDataJSON(), { rooms: previews.map(({ roomId, missionId }) => ({ roomId, missionId })) });
  const prepared = await accepted.json(), requestId = accepted.request().headers()['idempotency-key'];
  assert.match(requestId, /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/);
  await page.locator('#launch-independent-receipt-rows tr').last().waitFor();
  await fs.writeFile(output, JSON.stringify({ previews, requestId, prepared }, null, 2), { flag: 'wx' });
}

if (require.main === module) {
  (async () => {
    const { chromium } = require('playwright');
    const input = [];
    for await (const chunk of process.stdin) input.push(chunk);
    const { base, token, plan, missions, output } = JSON.parse(Buffer.concat(input).toString('utf8'));
    assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
    const browser = await chromium.launch({ headless: true, executablePath: process.env.VR_SERVER_PLAN_CHROMIUM });
    try {
      const page = await browser.newPage({ acceptDownloads: true });
      await login(page, base, token);
      if (missions) await prepareRoomLayouts(page, missions, output);
      else {
        await open(page);
        await fill(page, plan);
        await page.locator('#venue-server-read').click();
        await page.locator('#venue-server-form').waitFor();
        await download(page, output, plan);
      }
    } finally { await browser.close(); }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
