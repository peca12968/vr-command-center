const { randomUUID } = require('node:crypto');
const path = require('node:path');

module.exports = async function layoutBrowser({ context, api, tokens, base, mission, screenshots, check }) {
  const editor = await context.newPage(), errors = [];
  editor.on('pageerror', error => errors.push(error.message));
  const prop = (assetId, x, z, yawDegrees = 0) => ({ assetId, position: { x, y: 0, z }, yawDegrees });
  const bad = await api('/missions', 'POST', { ...mission.definition, name: '場地檢查・可修正草稿',
    enemies: { ...mission.definition.enemies, count: 0 },
    props: [prop('barrel', 0, -3), prop('sandbag', 5.5, 2, 45), prop('barrel', 2, 2), prop('barrel', 2, 2)] }, 'Master', 201);
  const barricade = await api('/missions', 'POST', { ...mission.definition, name: '場地通路・連續沙包',
    props: [...[-5, -3, -1, 1, 3, 5].map(x => prop('sandbag', x, -1)), prop('barrel', 4, 3)] }, 'Master', 201);
  const mr = await api('/missions', 'POST', { ...mission.definition, name: 'MR 開場檢查',
    environment: { ...mission.definition.environment, mode: 'MR' }, props: [] }, 'Master', 201);
  const status = (prefix, value) => editor.waitForFunction(({ prefix, value }) => document.querySelector(`#${prefix}-layout-summary`).dataset.status === value, { prefix, value });
  async function set(id, value) { await editor.locator('#' + id).fill(String(value)); await editor.locator('#' + id).blur(); }
  async function launch(id) { await editor.locator('#launch-mission').selectOption(id); }
  try {
    await editor.goto(base + '/console/'); await editor.locator('#login-key').fill(tokens.Master); await editor.locator('#login-form button').click();
    await editor.locator('#tab-missions').click(); await editor.locator(`#edit-mission option[value="${bad.id}"]`).waitFor({ state: 'attached' });
    await editor.locator('#edit-mission').selectOption(bad.id); await editor.locator('#load-mission').click(); await status('draft', 'invalid');
    check(await editor.locator('#prop-layer [data-layout-invalid=true]').count() === 4 && await editor.locator('#layout-spawns circle').count() === 5,
      'Layout preflight marks every overlapping, outside-room and spawn-blocking prop with all five real spawn spaces');
    const issues = await editor.locator('#draft-layout-issues').innerText();
    check(issues.includes('重疊') && issues.includes('超出') && issues.includes('出生位 3'), 'Draft report explains rotated bounds, pair overlap and the exact blocked seat');
    await editor.locator('#draft-layout-issues button').filter({ hasText: '超出' }).first().click();
    check(await editor.locator('#prop-select').inputValue() === '1', 'Clicking a placement issue selects its actual object in the inspector');
    await editor.screenshot({ path: path.join(screenshots, 'layout-invalid-desktop.png'), fullPage: true });
    await editor.setViewportSize({ width: 390, height: 844 });
    check(await editor.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Placement reports and controls fit a mobile viewport');
    await editor.screenshot({ path: path.join(screenshots, 'layout-invalid-mobile.png'), fullPage: true }); await editor.setViewportSize({ width: 1440, height: 1080 });
    await editor.locator('#draft-name').fill('無效配置仍可另存'); await editor.locator('#mission-form button[type=submit]').click();
    await editor.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存'));
    const saved = (await api('/mission-library')).find(row => row.mission.definition.name === '無效配置仍可另存').mission;
    check(JSON.stringify(saved.definition.props) === JSON.stringify(bad.definition.props), 'An invalid layout can still be saved without losing the editable draft');
    await editor.locator('#launch-version').click(); await status('launch', 'invalid');
    check(await editor.locator('#create-session-form button').isDisabled() && !(await api('/sessions')).some(row => row.mission.id === saved.id),
      'Saved invalid mission remains selectable but cannot reserve a new VR room');
    await editor.locator('#launch-layout-map-details summary').click();
    check(await editor.locator('#launch-layout-props [data-layout-invalid=true]').count() === 4
      && await editor.locator('#launch-layout-spawns [data-seat="2"][data-spawn-blocked]').isVisible()
      && await editor.locator('#launch-layout-routes polyline').count() === 0
      && await editor.locator('#launch-layout-props [role=button]').count() === 0,
      'Saved invalid map identifies its original props and blocked spawn without edit controls or fabricated paths');
    await editor.locator('#tab-missions').click();
    await editor.locator('#prop-select').selectOption('0'); await set('prop-z', 0);
    await editor.locator('#prop-select').selectOption('1'); await set('prop-x', 4);
    await editor.locator('#prop-select').selectOption('3'); await set('prop-x', -2); await status('draft', 'valid');
    check(await editor.locator('#prop-layer [data-layout-invalid=true]').count() === 0 && await editor.locator('#layout-spawns circle').count() === 5,
      'Correcting the draft clears invalid markings while retaining the authoritative spawn margins');
    check(await editor.locator('#create-session-form button').isDisabled(), 'A corrected unsaved draft cannot approve its invalid saved launch version');
    check(await editor.locator('#launch-layout-props [data-index="0"]').getAttribute('transform') === 'translate(0 3) rotate(0)'
      && await editor.locator('#prop-layer [data-index="0"]').getAttribute('transform') === 'translate(0 0) rotate(0)',
      'The saved map keeps its original prop while an unsaved draft moves the same prop');
    await editor.locator('#save-revision').click(); await editor.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const fixedId = (await api(`/missions/${saved.id}/history`)).headId;
    await editor.locator('#launch-version').click(); await status('launch', 'valid'); await editor.locator('#launch-room').selectOption('3');
    check(await editor.locator('#create-session-form button').isEnabled() && (await api(`/missions/${saved.id}/layout`)).canStart === false,
      'Saving a corrected revision enables that exact version while the immutable old version remains invalid');
    const fixedLayout = await api(`/missions/${fixedId}/layout`);
    check(await editor.locator('#launch-layout-props [data-index="0"]').getAttribute('transform') === 'translate(0 0) rotate(0)'
      && await editor.locator('#launch-layout-props [data-layout-invalid]').count() === 0
      && await editor.locator('#launch-layout-spawns circle').count() === 5
      && await editor.locator('#launch-layout-routes polyline').count() === fixedLayout.routePreview.seats.filter(seat => seat.path.length).length,
      'Selecting the corrected saved revision changes the map, spawns and route overlay together');
    await editor.setViewportSize({ width: 390, height: 844 });
    check(await editor.locator('#launch-layout-map').isVisible()
      && await editor.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      'The opened saved map fits a 390-pixel console');
    await editor.locator('#launch-layout-map-details').screenshot({ path: path.join(screenshots, 'layout-saved-mobile.png') });
    await editor.setViewportSize({ width: 1440, height: 1080 });
    await editor.screenshot({ path: path.join(screenshots, 'layout-valid-launch.png'), fullPage: true });
    // Hold one valid result, switch selection, then deliver the obsolete result.
    let release, observed; let held = false;
    const gate = new Promise(resolve => { release = resolve; }), requested = new Promise(resolve => { observed = resolve; });
    const savedPattern = `**/api/missions/${fixedId}/layout?*`;
    await editor.route(savedPattern, async route => { const response = await route.fetch(); if (!held) { held = true; observed(); await gate; } await route.fulfill({ response }); });
    await editor.locator('#layout-recheck-launch').click(); await requested; await launch(bad.id); await status('launch', 'invalid');
    release(); await editor.waitForTimeout(150);
    check(await editor.locator('#launch-layout-summary').getAttribute('data-status') === 'invalid' && await editor.locator('#create-session-form button').isDisabled(),
      'A delayed valid preflight cannot approve a different selected mission');
    check(await editor.locator('#launch-layout-props [data-layout-invalid]').count() === 4
      && await editor.locator('#launch-layout-routes polyline').count() === 0,
      'A delayed report cannot replace another saved version’s map overlays');
    await editor.unroute(savedPattern);
    const dense = await api('/missions', 'POST', { ...mission.definition, name: '依模式核對初始敵軍', enemies: { ...mission.definition.enemies, count: 100 },
      props: [2, 4].flatMap(z => [-3, -1, 1, 3].map(x => prop('sandbag', x, z))) }, 'Master', 201);
    await editor.locator('#refresh').click(); await editor.locator(`#launch-mission option[value="${dense.id}"]`).waitFor({ state: 'attached' }); await launch(dense.id); await status('launch', 'invalid');
    check((await editor.locator('#launch-layout-issues').innerText()).includes('初始敵軍'), 'Independent launch rejects an initial enemy count above the actual candidate grid capacity');
    await editor.locator('#launch-mode').selectOption('Linked'); await status('launch', 'valid');
    check((await editor.locator('#launch-layout-summary').innerText()).includes('需求 20'), 'Linked preflight recalculates the per-room demand instead of reusing the independent result');
    await editor.locator('#launch-mode').selectOption('Independent'); await launch(fixedId); await status('launch', 'valid');
    await editor.route(savedPattern, async route => { const response = await route.fetch(); const report = await response.json(); await route.fulfill({ json: { ...report, version: 999 } }); });
    await editor.locator('#layout-recheck-launch').click(); await editor.waitForFunction(() => document.querySelector('#launch-layout-summary').textContent.includes('未完成'));
    check(await editor.locator('#create-session-form button').isDisabled(), 'Unknown preflight versions fail closed instead of enabling launch');
    check(!await editor.locator('#launch-layout-map-details').isVisible() && await editor.locator('#launch-layout-props [data-index]').count() === 0,
      'An unrecognized report clears the saved map');
    await editor.unroute(savedPattern); await editor.locator('#layout-recheck-launch').click(); await status('launch', 'valid');
    // A late valid draft response must not repaint red props as valid.
    await editor.locator('#tab-missions').click(); let releaseDraft, observedDraft; let heldDraft = false;
    const draftGate = new Promise(resolve => { releaseDraft = resolve; }), draftRequested = new Promise(resolve => { observedDraft = resolve; });
    await editor.route('**/api/mission-layout', async route => { const response = await route.fetch(); if (!heldDraft) { heldDraft = true; observedDraft(); await draftGate; } await route.fulfill({ response }); });
    await editor.locator('#layout-recheck-draft').click(); await draftRequested; await editor.locator('#prop-select').selectOption('1'); await set('prop-x', 5.5); await status('draft', 'invalid');
    releaseDraft(); await editor.waitForTimeout(150);
    check(await editor.locator('#draft-layout-summary').getAttribute('data-status') === 'invalid' && await editor.locator('#prop-layer [data-index="1"]').getAttribute('data-layout-invalid') === 'true',
      'A late report for an older draft cannot clear current invalid markings');
    await editor.unroute('**/api/mission-layout');
    await editor.locator('#edit-mission').selectOption(barricade.id);
    editor.once('dialog', dialog => dialog.accept());
    await editor.locator('#load-mission').click();
    await editor.locator('#draft-layout-route-summary').filter({ hasText: '未找到通往中線' }).waitFor();
    check(await editor.locator('#layout-spawns [data-route-missing]').count() === 5 && await editor.locator('#layout-routes polyline').count() === 0,
      'A saved full-width barricade highlights all five isolated spawn samples without fabricating routes');
    await editor.screenshot({ path: path.join(screenshots, 'layout-route-isolated.png'), fullPage: true });
    await editor.locator('#launch-version').click();
    await editor.locator('#launch-layout-route-summary').filter({ hasText: '未找到通往中線' }).waitFor();
    check(await editor.locator('#create-session-form button').isEnabled(), 'A sampled route warning on a saved mission leaves its intentional barricade startable');
    check(await editor.locator('#launch-layout-spawns [data-route-missing]').count() === 5
      && await editor.locator('#launch-layout-routes polyline').count() === 0,
      'The startable saved barricade marks all five missing sample routes on the launch map');
    await editor.locator('#tab-missions').click();
    const trial = editor.locator('#layout-try-removal'), trialStatus = editor.locator('#layout-trial-status');
    const original = await editor.locator('#draft-status').innerText();
    await editor.locator('#prop-select').selectOption('6');
    await trial.click();
    await trialStatus.filter({ hasText: '沒有新增通往中線' }).waitFor();
    check(await editor.locator('#layout-trial-routes polyline').count() === 0,
      'Trying an unrelated barrel leaves the five barricaded routes closed');
    await editor.locator('#prop-select').selectOption('3');
    await trial.click();
    await trialStatus.filter({ hasText: '出生位 1、2、3、4、5 可走到中線' }).waitFor();
    const trialView = await editor.evaluate(() => ({
      paths: document.querySelectorAll('#layout-trial-routes polyline').length,
      blocked: document.querySelectorAll('#layout-spawns [data-route-missing]').length,
      props: document.querySelectorAll('#prop-layer [data-index]').length,
      ghost: document.querySelector('#prop-layer [data-layout-trial]')?.dataset.index,
      draft: document.querySelector('#draft-status').textContent
    }));
    check(trialView.paths === 5 && trialView.blocked === 5 && trialView.props === 7
      && trialView.ghost === '3' && trialView.draft === original,
      'Removing a wall segment in the trial draws five separate paths while keeping the actual draft unchanged');
    await editor.screenshot({ path: path.join(screenshots, 'layout-removal-trial.png'), fullPage: true });
    await editor.locator('#layout-clear-trial').click();
    check(await editor.locator('#layout-trial-routes polyline').count() === 0
      && await editor.locator('#prop-layer [data-layout-trial]').count() === 0,
      'Clearing the trial restores the original view without editing an object');
    let releaseTrial, requestedTrial;
    const trialGate = new Promise(resolve => { releaseTrial = resolve; });
    const trialRequested = new Promise(resolve => { requestedTrial = resolve; });
    let deliverTrial;
    const trialDelivered = new Promise(resolve => { deliverTrial = resolve; });
    const holdTrial = async route => {
      try {
        const response = await route.fetch();
        requestedTrial();
        await trialGate;
        await route.fulfill({ response });
        deliverTrial(true);
      } catch { requestedTrial(); deliverTrial(false); }
    };
    await editor.route('**/api/mission-layout', holdTrial);
    try {
      await trial.click();
      await trialRequested;
      await editor.locator('#prop-select').selectOption('6');
    } finally {
      releaseTrial();
      await trialDelivered;
      await editor.unroute('**/api/mission-layout', holdTrial);
    }
    check(await trialDelivered && await trialStatus.innerText() === '可試算移除物件 7 後的通路。'
      && await editor.locator('#layout-trial-routes polyline').count() === 0,
      'A delivered trial for an older object selection cannot draw paths for the new selection');
    await editor.locator('#prop-select').selectOption('3');
    await editor.locator('#remove-prop').click();
    await editor.locator('#draft-layout-route-summary').filter({ hasText: '五個出生位皆有' }).waitFor();
    check(await editor.locator('#layout-routes polyline').count() === 5 && await editor.locator('#layout-spawns [data-route-missing]').count() === 0,
      'Removing the center bag draws five routes and clears the isolated spawn markings');
    await editor.screenshot({ path: path.join(screenshots, 'layout-route-opening.png'), fullPage: true });
    await editor.locator('#save-revision').click();
    await editor.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const openedId = (await api(`/missions/${barricade.id}/history`)).headId;
    await editor.locator('#launch-version').click();
    await editor.locator('#launch-layout-route-summary').filter({ hasText: '五個出生位皆有' }).waitFor();
    check(await editor.locator('#launch-mission').inputValue() === openedId && (await api(`/missions/${barricade.id}/layout`)).routePreview.seats.every(seat => !seat.path.length),
      'Saving an opening updates only the new revision and its matching launch preview');
    await editor.locator('#tab-missions').click();
    await editor.locator('#new-mission').click();
    const narrowName = '場地通路・偏移窄缺口';
    await editor.locator('#draft-name').fill(narrowName);
    const narrow = [-4.75, -2.75, -1.4, .75, 2.75, 4.75].map(x => prop(x === -1.4 ? 'barrel' : 'sandbag', x, -1));
    for (const { assetId, position } of narrow) {
      await editor.locator('#add-' + assetId).click();
      await set('prop-x', position.x); await set('prop-z', position.z);
    }
    await editor.locator('#draft-layout-route-summary').filter({ hasText: '0.125 公尺取樣' }).waitFor();
    const fineDraft = await editor.locator('#layout-routes polyline[data-sample-step="0.125"]').evaluateAll(lines => lines.map(line => line.getAttribute('points')));
    check(fineDraft.length === 5 && await editor.locator('#layout-spawns [data-route-missing]').count() === 0,
      'The editable offset gap shows five refined routes and no missing seat markers');
    await editor.screenshot({ path: path.join(screenshots, 'layout-fine-opening.png'), fullPage: true });
    await editor.locator('#mission-form button[type=submit]').click();
    await editor.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const fine = (await api('/mission-library')).find(row => row.mission.definition.name === narrowName).mission;
    const fineReport = await api(`/missions/${fine.id}/layout`);
    await editor.locator('#launch-version').click();
    await editor.locator('#launch-layout-route-summary').filter({ hasText: '0.125 公尺取樣' }).waitFor();
    const fineSaved = await editor.locator('#launch-layout-routes polyline[data-sample-step="0.125"]').evaluateAll(lines => lines.map(line => line.getAttribute('points')));
    check(await editor.locator('#launch-mission').inputValue() === fine.id
      && JSON.stringify(fine.definition.props) === JSON.stringify(narrow)
      && JSON.stringify(fineSaved) === JSON.stringify(fineDraft)
      && fineReport.routePreview.seats.every(route => route.sampleStep === .125 && route.path.at(-1).z === 0),
      'Saving the decimal geometry yields identical refined paths in the launch map and saved mission report');
    await editor.locator('#tab-operations').click();
    const vacant = (await api('/rooms')).find(room => !room.sessionId);
    await editor.locator('#launch-mode').selectOption('Independent');
    await editor.locator('#launch-room').selectOption(String(vacant.id));
    await launch(mr.id);
    await editor.locator('#launch-layout-summary').filter({ hasText: 'MR 虛擬配置檢查通過' }).waitFor();
    const created = editor.waitForResponse(response => response.url().endsWith('/api/sessions')
      && response.request().method() === 'POST' && response.status() === 201);
    await editor.locator('#create-session-form button').click();
    const mixed = await (await created).json();
    try {
      await editor.locator('#mr-start-requirement').waitFor();
      const controls = await editor.evaluate(() => ({
        modeLocked: document.querySelector('#live-mode').disabled,
        viveLocked: document.querySelector('#player-headset option[value=ViveXr]').disabled,
        headset: document.querySelector('#player-headset').value
      }));
      check(mixed.environment.mode === 'MR' && controls.modeLocked && controls.viveLocked && controls.headset === 'Quest3',
        'Operator creates the saved MR mode and sees the locked mode, Quest roster and tracking requirement ' + JSON.stringify(controls));
      await editor.locator('#player-name').fill('Quest readiness fixture');
      await editor.locator('#join-form button').click();
      await editor.waitForFunction(() => !document.querySelector('[data-command=Begin]').disabled);
      const rejected = editor.waitForResponse(response => response.url().endsWith(`/api/sessions/${mixed.id}/commands`)
        && response.request().method() === 'POST' && response.status() === 409);
      await editor.locator('[data-command=Begin]').click(); await rejected;
      await editor.locator('#notice').filter({ hasText: 'MR 場次尚未就緒' }).waitFor();
      const state = await api(`/sessions/${mixed.id}`);
      check(state.state === 'Preparing' && state.players.length === 1 && state.players[0].headset === 'Quest3',
        'MR Begin without a fresh tracked pose leaves the original roster and Preparing phase intact');
      await editor.screenshot({ path: path.join(screenshots, 'layout-mr-start-gate.png'), fullPage: true });
    } finally {
      await api(`/sessions/${mixed.id}/commands`, 'POST', { action: 'End', commandId: randomUUID() });
    }
    const compact = await api('/missions', 'POST', { ...dense.definition, name: '場中敵軍容量',
      enemies: { ...dense.definition.enemies, count: 2 } }, 'Master', 201);
    const active = await api('/sessions', 'POST', { missionId: compact.id, mode: 'Independent', roomIds: [vacant.id] }, 'Master', 201);
    try {
      await editor.locator('#refresh').click();
      await editor.locator('#session-select').selectOption(active.id);
      await editor.locator('#live-enemies').filter({ hasText: '目標 2 名' }).waitFor();
      await editor.locator('#live-count').fill('85');
      const refused = editor.waitForResponse(response => response.url().endsWith(`/api/sessions/${active.id}/commands`)
        && response.request().method() === 'POST' && response.status() === 400);
      await editor.locator('#enemies-form button[type=submit]').click(); await refused;
      await editor.locator('#notice').filter({ hasText: '此場地最多可設定 84 名敵軍' }).waitFor();
      const unchanged = await api(`/sessions/${active.id}`);
      check(unchanged.sequence === active.sequence && unchanged.enemies.count === 2 && await editor.locator('#live-count').inputValue() === '85',
        'An excessive reinforcement preserves the operator draft and existing target and explains the actual limit');
      await editor.screenshot({ path: path.join(screenshots, 'layout-enemy-capacity.png'), fullPage: true });
      await editor.locator('#live-count').fill('84');
      await editor.locator('#enemies-form button[type=submit]').click();
      await editor.locator('#live-enemies').filter({ hasText: '目標 84 名' }).waitFor();
      check((await api(`/sessions/${active.id}`)).enemies.count === 84, 'The exact capacity can be submitted from the same operator form');
    } finally {
      await api(`/sessions/${active.id}/commands`, 'POST', { action: 'End', commandId: randomUUID() });
    }
    await launch(openedId);
    let releaseLogout, observedLogout;
    const logoutGate = new Promise(resolve => { releaseLogout = resolve; }), logoutRequested = new Promise(resolve => { observedLogout = resolve; });
    await editor.route(`**/api/missions/${openedId}/layout?*`, async route => { const response = await route.fetch(); observedLogout(); await logoutGate; await route.fulfill({ response }); });
    await editor.locator('#tab-operations').click(); await editor.locator('#layout-recheck-launch').click(); await logoutRequested; await editor.locator('#logout').click(); releaseLogout(); await editor.waitForTimeout(150);
    check(await editor.locator('#launch-layout-summary').getAttribute('data-status') === 'unknown' && await editor.locator('#layout-spawns circle').count() === 0,
      'Logout clears preflight approvals and ignores an old authenticated response');
    check(errors.length === 0, 'Placement validation workflow has no uncaught browser errors');
  } catch (error) { await editor.screenshot({ path: path.join(screenshots, 'layout-failure.png'), fullPage: true }).catch(() => {}); throw error; }
  finally { await editor.close(); }
};
