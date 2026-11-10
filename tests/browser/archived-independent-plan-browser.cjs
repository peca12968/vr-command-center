const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function archivedIndependentPlanBrowser({ context, api, tokens, base, screenshots, check, captureErrors }) {
  const page = await context.newPage();
  captureErrors(page);
  const restore = page.locator('#restore-venue-plan'), batchList = page.locator('#venue-closure-batch');
  const mode = page.locator('#launch-mode'), preview = page.locator('#launch-review-room');
  const create = page.locator('#create-session-form button'), notice = page.locator('#notice');
  const activeIds = new Set();
  const archivePath = id => `/venue/closure/${id}/independent-plan`;
  const selections = () => page.locator('#launch-room-missions-fields select').evaluateAll(fields => fields.map(field => field.value));
  const draft = { name: '結案原任務 A', briefing: '結案前的配置', durationSeconds: 360,
    environment: { mode: 'VR', weather: 'Rain', timeOfDay: 'Night', lightning: false },
    enemies: { count: 2, behavior: 'Hold', autoAttack: false }, props: [] };
  async function login(role) {
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  async function newSession(mode, roomIds, missionId) {
    const session = await api('/sessions', 'POST', { mode, roomIds, missionId }, 'Master', 201);
    activeIds.add(session.id);
    return session;
  }
  async function venueEnd() {
    const { end: targets } = await api('/venue/phase');
    const batch = await api('/venue/phase', 'POST', { action: 'End', targets }, 'Master', 200, undefined, randomUUID());
    for (const target of targets) activeIds.delete(target.sessionId);
    return batch;
  }
  async function end(id) { await api(`/sessions/${id}/commands`, 'POST', { commandId: randomUUID(), action: 'End' }); activeIds.delete(id); }
  try {
    assert.deepEqual(await api('/sessions'), []);
    const vr = await api('/missions', 'POST', draft, 'Master', 201);
    const mrDraft = { ...draft, name: '結案原任務 B', durationSeconds: 440,
      environment: { ...draft.environment, mode: 'MR', weather: 'Storm', lightning: true },
      props: [{ assetId: 'barrel', position: { x: 2, y: 0, z: 1 }, yawDegrees: 45 }] };
    const mr = await api('/missions', 'POST', mrDraft, 'Master', 201);
    const plan = [vr.id, mr.id, vr.id, mr.id, vr.id].map((missionId, index) => ({ roomId: index + 1, missionId }));
    const original = await api('/sessions/independent-set', 'POST', { rooms: plan }, 'Master', 201, undefined, randomUUID());
    for (const session of original.sessions) activeIds.add(session.id);
    const archive = await venueEnd();
    const mrHead = await api(`/missions/${mr.id}/revisions`, 'POST', { ...mrDraft, durationSeconds: 480, props: [] }, 'Master', 201, undefined, randomUUID());
    const linked = await newSession('Linked', [1, 2, 3, 4, 5], vr.id);
    const linkedBatch = await venueEnd();
    await newSession('Independent', [3], vr.id);
    const partialBatch = await venueEnd();
    const oldPlan = await api(archivePath(archive.requestId));
    check(oldPlan.requestId === archive.requestId && oldPlan.rooms.every((room, index) => room.roomId === index + 1
      && room.sessionId === original.sessions[index].id && room.revision.mission.id === plan[index].missionId && room.revision.number === 1)
      && oldPlan.rooms.length === 5 && oldPlan.rooms[1].revision.mission.definition.durationSeconds === 440
      && oldPlan.rooms[1].revision.mission.definition.props.length === 1,
      'Historical read returns the original five room and revision identities after a new revision and room reuse');
    await api(archivePath(archive.requestId), 'GET', undefined, 'Room2', 403);
    await api(archivePath(randomUUID()), 'GET', undefined, 'Master', 404);
    await api(archivePath(linkedBatch.requestId), 'GET', undefined, 'Master', 409);
    await api(archivePath(partialBatch.requestId), 'GET', undefined, 'Master', 409);
    await login('Room2');
    check(await restore.isHidden(), 'Room control cannot read or apply the archived five-room plan');
    const blocker = await newSession('Independent', [4], vr.id);
    await login('Master');
    const rows = page.locator('#venue-closure-rows tr');
    await page.locator('#venue-closure-table').waitFor();
    check(await rows.count() === 1 && await restore.isHidden(), 'The latest partial batch has no five-room restore action');
    await page.locator('#venue-closure-load').click();
    await batchList.selectOption(linkedBatch.requestId);
    await rows.filter({ hasText: '房間 1、2、3、4、5' }).waitFor();
    check(await restore.isHidden() && (await api(`/sessions/${linked.id}`)).state === 'Ended', 'A linked batch has no five-room restore action');

    await page.locator('#tab-missions').click();
    await page.locator('#edit-mission').selectOption(mrHead.id);
    await page.locator('#load-mission').click();
    const duration = page.locator('#draft-duration');
    await page.waitForFunction(() => document.querySelector('#draft-duration').value === '480' && !document.querySelector('#mission-fields').disabled);
    await duration.fill('499');
    await page.locator('#tab-operations').click();
    await batchList.selectOption(archive.requestId);
    await restore.waitFor();
    const archiveRoute = '**/api' + archivePath(archive.requestId);
    await page.route(archiveRoute, async route => {
      const changed = structuredClone(oldPlan);
      changed.rooms[2].sessionId = randomUUID();
      await route.fulfill({ status: 200, json: changed });
    }, { times: 1 });
    await restore.click();
    await notice.filter({ hasText: '無法核對本批五房' }).waitFor();
    check(await mode.inputValue() === 'Independent' && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'A mismatched archived session leaves the preparation mode and occupied room untouched');

    const read = page.waitForResponse(response => response.url() === base + '/api' + archivePath(archive.requestId));
    await restore.click();
    assert.equal((await read).headers()['cache-control'], 'no-store');
    await notice.filter({ hasText: '已套用本批五房' }).waitFor();
    for (const { roomId } of plan) await page.locator(`#launch-room-layout-${roomId}[data-status=valid]`).waitFor();
    check(await mode.inputValue() === 'IndependentSet' && await preview.inputValue() === '1' && await duration.inputValue() === '499'
      && JSON.stringify(await selections()) === JSON.stringify(plan.map(room => room.missionId)) && await create.isDisabled()
      && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'Applying an older batch restores its exact picks and retains the unsaved editor draft while an occupied room blocks creation');
    await preview.selectOption('2');
    await page.locator('#launch-layout-map-details summary').click();
    check((await page.locator('#launch-room-mission-2 option:checked').innerText()).includes('歷史')
      && await page.locator('#launch-preview-duration').innerText() === '440 秒'
      && await page.locator('#launch-layout-props [data-index="0"]').getAttribute('transform') === 'translate(2 -1) rotate(-45)',
      'A restored historical MR room previews its original timing and barrel position');
    await page.locator('#launch-room-missions').screenshot({ path: path.join(screenshots, 'independent-archived-plan.png') });

    await end(blocker.id);
    await page.locator('#refresh').click();
    let confirmation;
    page.once('dialog', async dialog => { confirmation = dialog.message(); await dialog.accept(); });
    await create.click();
    await notice.filter({ hasText: '五個獨立場次已確認' }).waitFor();
    const recreated = (await api('/sessions')).sort((a, b) => a.roomIds[0] - b.roomIds[0]);
    for (const session of recreated) activeIds.add(session.id);
    check(recreated.length === 5 && confirmation.includes('結案原任務 B · 第 1 版 · MR · 440 秒')
      && recreated.every((session, index) => session.id !== original.sessions[index].id && session.state === 'Preparing'
        && session.roomIds[0] === plan[index].roomId && session.mission.id === plan[index].missionId)
      && JSON.stringify(await api(archivePath(archive.requestId))) === JSON.stringify(oldPlan),
      'Explicit confirmation creates five fresh sessions with the archived assignments and preserves the original archive');
  } finally {
    for (const id of activeIds) await end(id);
    await page.close();
  }
};
