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
  const linkedPath = id => `/venue/closure/${id}/linked-plan`;
  const selections = () => page.locator('#launch-room-missions-fields select').evaluateAll(fields => fields.map(field => field.value));
  async function restoreSubstitutedVersion(route, response) {
    await page.route(route, request => request.fulfill({ status: 200, json: response }), { times: 1 });
    const read = page.waitForResponse(reply => reply.url().endsWith(route.slice(2)));
    await restore.click();
    await read;
    await page.waitForFunction(() => !document.querySelector('#restore-venue-plan').disabled);
    assert.match(await notice.innerText(), /無法核對本批五房/);
  }
  const draft = { name: '結案原任務 A', briefing: '結案前的配置', durationSeconds: 360,
    environment: { mode: 'VR', weather: 'Rain', timeOfDay: 'Night', lightning: false },
    enemies: { count: 2, behavior: 'Hold', autoAttack: false },
    props: [{ assetId: 'sandbag', position: { x: -2, y: 0, z: 2 }, yawDegrees: 30 }] };
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
    const vrHead = await api(`/missions/${vr.id}/revisions`, 'POST', { ...draft, durationSeconds: 700, props: [] }, 'Master', 201, undefined, randomUUID());
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
    const linkedPlan = await api(linkedPath(linkedBatch.requestId));
    assert.equal(linkedPlan.requestId, linkedBatch.requestId);
    assert.equal(linkedPlan.sessionId, linked.id);
    assert.deepEqual(linkedPlan.roomIds, [1, 2, 3, 4, 5]);
    assert.equal(linkedPlan.revision.number, 1);
    assert.deepEqual(linkedPlan.revision.mission, vr);
    await api(linkedPath(linkedBatch.requestId), 'GET', undefined, 'Room2', 403);
    await api(linkedPath(archive.requestId), 'GET', undefined, 'Master', 409);
    await api(linkedPath(partialBatch.requestId), 'GET', undefined, 'Master', 409);
    await api(linkedPath(randomUUID()), 'GET', undefined, 'Master', 404);
    const closurePath = id => `/venue/closure/${id}`;
    const originalVersions = async id => (await api(closurePath(id))).batch.sessions.map(({ sessionId, missionId }) => [sessionId, missionId]);
    assert.deepEqual(await originalVersions(archive.requestId), original.sessions.map((session, index) => [session.id, plan[index].missionId]));
    assert.deepEqual(await originalVersions(linkedBatch.requestId), [[linked.id, vr.id]]);
    check(true, 'Both closure shapes advertise the original immutable version from each persisted session');
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
    check(await restore.isVisible() && (await api(`/sessions/${linked.id}`)).state === 'Ended',
      'A complete historical Linked batch offers its original saved mission');

    await page.locator('#tab-missions').click();
    await page.locator('#edit-mission').selectOption(mrHead.id);
    await page.locator('#load-mission').click();
    const duration = page.locator('#draft-duration');
    await page.waitForFunction(() => document.querySelector('#draft-duration').value === '480' && !document.querySelector('#mission-fields').disabled);
    await duration.fill('499');
    await page.locator('#tab-operations').click();
    const linkedRoute = '**/api' + linkedPath(linkedBatch.requestId);
    await page.route(linkedRoute, route => route.fulfill({ status: 200, json: { ...linkedPlan, roomIds: [1, 2, 3, 4, 4] } }), { times: 1 });
    await restore.click();
    await notice.filter({ hasText: '無法核對本批五房' }).waitFor();
    check(await mode.inputValue() === 'Independent' && await duration.inputValue() === '499',
      'A malformed Linked response leaves the current launch mode and dirty draft intact');
    const vrReplacement = await api(`/missions/${vrHead.id}/version`);
    assert.equal(vrReplacement.mission.definition.name, linkedPlan.revision.mission.definition.name);
    assert.notEqual(vrReplacement.mission.id, linkedPlan.revision.mission.id);
    await restoreSubstitutedVersion(linkedRoute, { ...linkedPlan, revision: vrReplacement });
    check(await mode.inputValue() === 'Independent' && await duration.inputValue() === '499',
      'Linked restore rejects a valid newer revision with the original name and retains the preparation mode and editor draft');
    const linkedRead = page.waitForResponse(response => response.url() === base + '/api' + linkedPath(linkedBatch.requestId));
    await restore.click();
    assert.equal((await linkedRead).headers()['cache-control'], 'no-store');
    await notice.filter({ hasText: '已套用本批五房' }).waitFor();
    await page.locator('#launch-layout-summary[data-status=valid]').waitFor();
    const mission = page.locator('#launch-mission');
    check(await mode.inputValue() === 'Linked' && await mission.inputValue() === vr.id && await duration.inputValue() === '499'
      && (await mission.locator('option:checked').innerText()).includes('歷史')
      && await page.locator('#launch-preview-duration').innerText() === '360 秒'
      && (await page.locator('#launch-preview-environment').innerText()).includes('下雨')
      && await page.locator('#launch-layout-props [data-index="0"]').getAttribute('transform') === 'translate(-2 -2) rotate(30)'
      && await create.isDisabled() && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'Linked restore pins the original duration, weather and cover while leaving the occupied room and draft alone');
    await page.locator('#launch-preview').screenshot({ path: path.join(screenshots, 'linked-archived-plan.png') });
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
    check(await mode.inputValue() === 'Linked' && (await api('/sessions')).map(session => session.id).join() === blocker.id,
      'A mismatched archived session leaves the preparation mode and occupied room untouched');
    const changed = structuredClone(oldPlan);
    changed.rooms[3].revision = await api(`/missions/${mrHead.id}/version`);
    assert.equal(changed.rooms[3].revision.mission.definition.name, oldPlan.rooms[3].revision.mission.definition.name);
    assert.notEqual(changed.rooms[3].revision.mission.id, oldPlan.rooms[3].revision.mission.id);
    await restoreSubstitutedVersion(archiveRoute, changed);
    check(await mode.inputValue() === 'Linked' && await mission.inputValue() === vr.id && await duration.inputValue() === '499',
      'One valid same-name replacement among five original rooms rejects the entire restore and retains the previous launch selection');

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
      && await page.locator('#launch-layout-props [data-index="0"]').getAttribute('transform') === 'translate(2 -1) rotate(45)',
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
    for (const session of recreated) await end(session.id);
    await page.locator('#refresh').click();
    await batchList.selectOption(linkedBatch.requestId);
    await restore.click();
    await notice.filter({ hasText: '已套用本批五房' }).waitFor();
    await create.click();
    await notice.filter({ hasText: '場次建立結果已確認' }).waitFor();
    const [newLinked] = await api('/sessions');
    activeIds.add(newLinked.id);
    check(newLinked.id !== linked.id && newLinked.mode === 'Linked' && newLinked.state === 'Preparing'
      && newLinked.roomIds.join() === '1,2,3,4,5' && newLinked.mission.id === vr.id && await duration.inputValue() === '499'
      && JSON.stringify(await api(linkedPath(linkedBatch.requestId))) === JSON.stringify(linkedPlan),
      'The original Linked mission creates a new five-room session without rewriting the archived mission or the draft');
  } finally {
    for (const id of activeIds) await end(id);
    await page.close();
  }
};
