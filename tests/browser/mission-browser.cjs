const { randomUUID } = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs/promises');
const { performance } = require('node:perf_hooks');

module.exports = async function missionBrowser({ page, context, api, tokens, base, mission, session, screenshots, check }) {
  const editor = await context.newPage(); const errors = []; editor.on('pageerror', error => errors.push(error.message));
  // Bounded GET metadata only; no headers, credentials, request bodies or payloads.
  const requests = new Map(), network = [];
  editor.on('request', request => {
    const pathname = new URL(request.url()).pathname;
    if (request.method() !== 'GET' || !/^\/api\/(missions\/|mission-library$|rooms$|sessions$)/.test(pathname) || network.length >= 128) return;
    const row = { path: pathname, startedAtUtc: new Date().toISOString(), startedMilliseconds: performance.now(), status: null, finished: false, failure: null };
    network.push(row); requests.set(request, row);
  });
  editor.on('response', response => { const row = requests.get(response.request()); if (row) row.status = response.status(); });
  function finish(request, failure) {
    const row = requests.get(request); if (!row) return;
    row.finished = true; row.failure = failure; row.elapsedMilliseconds = performance.now() - row.startedMilliseconds;
    requests.delete(request);
  }
  editor.on('requestfinished', request => finish(request, null));
  editor.on('requestfailed', request => finish(request, request.failure()?.errorText || 'Unknown'));
  const revise = (id, body) => api(`/missions/${id}/revisions`, 'POST', body, 'Master', 201, undefined, randomUUID());
  // These predicates inspect DOM state, including while another operator tab is
  // active. Do not depend on that editor receiving an animation frame.
  const waitForDom = (predicate, arg) => editor.waitForFunction(predicate, arg, { polling: 100 });
  async function ready() { await waitForDom(() => !document.querySelector('#mission-fields').disabled); }
  try {
    await editor.bringToFront();
    await editor.goto(base + '/console/'); await editor.locator('#login-key').fill(tokens.Master); await editor.locator('#login-form button').click();
    await editor.locator('#tab-missions').click(); await editor.locator('#edit-mission option').waitFor({ state: 'attached' });
    await editor.locator('#load-mission').click(); await waitForDom(() => document.querySelector('#draft-status').textContent.includes('第 1 版')); await ready();
    check(await editor.locator('#mission-version option').count() === 1 && await editor.locator('#save-revision').isEnabled(), 'Loaded mission identifies revision one and enables saving its next version');
    await editor.locator('#draft-name').fill('夜間防衛修訂 <第二版>'); await editor.locator('#draft-duration').fill('1500');
    await editor.locator('#draft-weather').selectOption('Clear'); await editor.locator('#draft-time').selectOption('Day');
    await editor.locator('#prop-x').fill('4.5'); await editor.locator('#prop-x').blur();
    let loseRevision = true; const attempts = [];
    await editor.route('**/api/missions/*/revisions', async route => {
      attempts.push({ path: new URL(route.request().url()).pathname, body: route.request().postData(), key: route.request().headers()['idempotency-key'] });
      if (loseRevision) { loseRevision = false; await route.fetch(); await route.abort('failed'); } else await route.continue();
    });
    await editor.locator('#save-revision').click(); await editor.locator('#pending-command').waitFor({ state: 'visible' });
    await waitForDom(() => !document.querySelector('#retry-command').disabled);
    check(await editor.locator('#draft-name').isDisabled() && await editor.locator('#load-mission').isDisabled(), 'Lost revision response freezes the original mission request and draft');
    const backupStarted = editor.waitForEvent('download');
    await editor.locator('#export-draft-template').click();
    const backup = await backupStarted;
    const draft = JSON.parse(await fs.readFile(await backup.path(), 'utf8'));
    check(draft.format === 'vr-command-mission-template' && draft.version === 1
      && JSON.stringify(draft.definition) === JSON.stringify(JSON.parse(attempts[0].body))
      && Object.keys(draft).length === 3 && attempts.length === 1 && await editor.locator('#pending-command').isVisible(),
      'A local draft backup preserves the unconfirmed revision body without retrying or clearing the pending write');
    const secondId = (await api(`/missions/${mission.id}/history`)).headId, second = await api('/missions/' + secondId);
    const third = await revise(second.id, { ...second.definition, name: '另一主控的第三版' });
    await editor.locator('#retry-command').click(); await waitForDom(() => document.querySelector('#pending-command').hidden && document.querySelector('#draft-status').textContent.startsWith('已儲存')); await ready();
    check(attempts.length === 2 && JSON.stringify(attempts[0]) === JSON.stringify(attempts[1]) && attempts[0].key,
      'Revision retry preserves its exact parent, definition and durable request ID');
    check(await editor.locator('#draft-name').inputValue() === second.definition.name && (await editor.locator('#draft-status').innerText()).includes('已有第 3 版') && await editor.locator('#save-revision').isDisabled(),
      'Accepted revision retry retains its saved second version even after another operator saves version three');
    check(await editor.locator('#launch-mission').inputValue() === mission.id,
      'Saving and confirming a different revision does not replace the original selected launch version');
    await editor.unroute('**/api/missions/*/revisions');
    await page.locator('#refresh').click(); await page.locator(`#edit-mission option[value="${third.id}"]`).waitFor({ state: 'attached' });
    check(await page.locator('#launch-mission').inputValue() === mission.id && (await page.locator('#launch-mission option:checked').innerText()).includes('歷史'),
      'Catalog refresh retains the explicitly selected launch version instead of silently switching to the new head');
    check(await page.locator('#draft-name').inputValue() === mission.definition.name && await page.locator('#prop-x').inputValue() === '3.5',
      'Background revision refresh preserves the main operator draft and layout');
    check((await api('/sessions/' + session.id)).mission.id === mission.id && JSON.stringify((await api('/missions/' + mission.id)).definition) === JSON.stringify(mission.definition),
      'Running session and original library snapshot remain bound to their unchanged original mission');
    await editor.bringToFront();
    await editor.locator('#load-mission').click(); await waitForDom(() => document.querySelector('#draft-status').textContent.includes('第 3 版') && !document.querySelector('#save-revision').disabled);
    const staleCatalog = await api('/mission-library');
    await editor.route('**/api/mission-library', route => route.fulfill({ json: staleCatalog }));
    await editor.locator('#draft-name').fill('保留這份衝突草稿');
    const fourth = await revise(third.id, { ...third.definition, name: '第四版・伺服器最新版' });
    await editor.locator('#save-revision').click(); await editor.locator('#notice.error').waitFor(); await ready();
    check(await editor.locator('#draft-name').inputValue() === '保留這份衝突草稿' && (await api(`/missions/${mission.id}/history`)).headId === fourth.id,
      'Stale revision is rejected while retaining the operator draft and authoritative newer head');
    editor.once('dialog', dialog => dialog.accept());
    await editor.locator('#load-mission').click(); await waitForDom(() => document.querySelector('#draft-status').textContent.includes('第 4 版') && !document.querySelector('#save-revision').disabled);
    await editor.locator('#refresh').click(); await ready();
    check(await editor.locator('#edit-mission').inputValue() === fourth.id && await editor.locator('#save-revision').isEnabled(),
      'Fresh version history advances the known head and a late stale catalog cannot regress it');
    await editor.unroute('**/api/mission-library'); await editor.locator('#refresh').click();
    await editor.locator(`#edit-mission option[value="${fourth.id}"]`).waitFor({ state: 'attached' });
    const compared = editor.locator('#mission-comparison');
    await editor.locator('#mission-version').selectOption(fourth.id); await editor.locator('#compare-version').click(); await compared.waitFor(); await ready();
    check(await editor.locator('#mission-comparison-table').isHidden() && (await editor.locator('#mission-comparison-summary').innerText()).includes('相同'),
      'Comparing the currently loaded saved version reports no changes');
    await editor.locator('#mission-version').selectOption(mission.id);
    check(await compared.isHidden(), 'Selecting a different saved version clears the old comparison');
    await editor.locator('#draft-briefing').fill('未儲存的簡報 <img src=x onerror=alert(1)>');
    await editor.locator('#add-barrel').click();
    await editor.locator('#compare-version').click(); await compared.waitFor(); await ready();
    const differences = await editor.locator('#mission-comparison-rows tr').evaluateAll(rows => rows.map(row => [...row.cells].map(cell => cell.textContent)));
    check(differences.some(([label, saved, draft]) => label === '任務時間' && saved === `${mission.definition.durationSeconds} 秒` && draft === '1500 秒')
      && differences.some(([label, saved, draft]) => label === '物件 1' && saved.includes('(3.5,') && draft.includes('(4.5,'))
      && differences.some(([label, saved, draft]) => label === `物件 ${mission.definition.props.length + 1}` && saved === '（無物件）' && draft.startsWith('barrel'))
      && differences.some(([label, saved, draft]) => label === '天氣、時段、閃電' && saved.includes('暴風雨') && draft.includes('晴朗'))
      && differences.some(([label, saved, draft]) => label === '任務內容' && saved === mission.definition.briefing && draft.includes('<img src=x'))
      && await compared.locator('img').count() === 0 && await editor.locator('#draft-name').inputValue() === fourth.definition.name,
      'Comparison shows the exact historical duration, layout and literal briefing beside the dirty draft');
    await editor.locator('#draft-briefing').fill('修改草稿後應重做比較');
    check(await compared.isHidden(), 'Editing the draft clears the comparison instead of leaving stale differences');
    await editor.locator('#compare-version').click(); await compared.waitFor(); await ready();
    await editor.setViewportSize({ width: 390, height: 844 });
    check(await editor.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'The comparison fits a mobile viewport');
    await editor.screenshot({ path: path.join(screenshots, 'mission-comparison-mobile.png'), fullPage: true });
    await editor.setViewportSize({ width: 1440, height: 1080 });
    await editor.locator('#launch-compared-version').click();
    check(await editor.locator('#launch-mission').inputValue() === mission.id && await editor.locator('#draft-name').inputValue() === fourth.definition.name
      && await editor.locator('#draft-briefing').inputValue() === '修改草稿後應重做比較',
      'Choosing a compared version for launch retains the different unsaved draft and pins only the exact saved version');
    await editor.locator('#launch-room').selectOption('3');
    await editor.locator('#launch-preview-briefing summary').click();
    check(await editor.locator('#launch-preview').getAttribute('data-mission-id') === mission.id
      && (await editor.locator('#launch-preview-version').innerText()).includes('第 1 版（歷史）')
      && await editor.locator('#launch-preview-rooms').innerText() === '房間 3'
      && await editor.locator('#launch-preview-duration').innerText() === `${mission.definition.durationSeconds} 秒`
      && await editor.locator('#launch-preview-briefing-text').innerText() === mission.definition.briefing,
      'The launch preview uses the saved historical snapshot and room even while the draft contains a different briefing');
    await editor.locator('#create-session-form button').click();
    await waitForDom(() => !document.querySelector('#session-panel').hidden && document.querySelector('#session-phase').textContent.includes('準備'));
    let created = (await api('/sessions')).find(row => row.roomIds.length === 1 && row.roomIds[0] === 3);
    check(created?.mission.id === mission.id && JSON.stringify(created.mission.definition) === JSON.stringify(mission.definition), 'Launching a historical version uses its full original immutable definition');
    await api('/sessions/' + created.id + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    await editor.locator('#tab-missions').click();
    editor.once('dialog', dialog => dialog.accept());
    await editor.locator('#mission-version').selectOption(mission.id); await editor.locator('#load-version').click(); await ready();
    await waitForDom(name => document.querySelector('#draft-name').value === name, mission.definition.name);
    check(await editor.locator('#prop-x').inputValue() === '3.5' && await editor.locator('#save-revision').isDisabled() && await editor.locator('#mission-version option').count() === 4 && await compared.isHidden(),
      'History loads exact old geometry, clears the comparison and prevents a conflicting revision branch');
    await editor.screenshot({ path: path.join(screenshots, 'mission-versions-desktop.png'), fullPage: true });
    await editor.setViewportSize({ width: 390, height: 844 });
    check(await editor.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Version history and both save actions fit a mobile viewport');
    await editor.screenshot({ path: path.join(screenshots, 'mission-versions-mobile.png'), fullPage: true });
    await editor.setViewportSize({ width: 1440, height: 1080 });
    await editor.locator('#launch-version').click();
    check(await editor.locator('#launch-mission').inputValue() === mission.id, 'Historical draft explicitly selects its saved original version for launch');
    await editor.locator('#tab-missions').click(); await editor.locator('#draft-name').fill('從舊版另存的獨立任務');
    let loseCreate = true; const creates = [];
    await editor.route('**/api/missions', async route => {
      if (route.request().method() !== 'POST') { await route.continue(); return; }
      creates.push({ body: route.request().postData(), key: route.request().headers()['idempotency-key'] });
      if (loseCreate) { loseCreate = false; await route.fetch(); await route.abort('failed'); } else await route.continue();
    });
    await editor.locator('#mission-form button[type=submit]').click(); await editor.locator('#pending-command').waitFor({ state: 'visible' });
    const acceptedCopy = (await api('/mission-library')).find(row => row.mission.definition.name === '從舊版另存的獨立任務');
    let loseReadback = true;
    await editor.route(`**/api/missions/${acceptedCopy.mission.id}/version`, async route => {
      if (loseReadback) { loseReadback = false; await route.fulfill({ status: 503, json: { error: 'Readback temporarily unavailable' } }); }
      else await route.continue();
    });
    await waitForDom(() => !document.querySelector('#retry-command').disabled); await editor.locator('#retry-command').click();
    await waitForDom(() => !document.querySelector('#retry-command').disabled && !document.querySelector('#pending-command').hidden);
    check(await editor.locator('#draft-name').isDisabled(), 'Accepted mission save retains its retry receipt when reading version metadata fails');
    await editor.locator('#retry-command').click();
    await waitForDom(() => document.querySelector('#pending-command').hidden && document.querySelector('#draft-status').textContent.startsWith('已儲存')); await ready();
    const heads = await api('/mission-library'), copied = heads.find(row => row.mission.definition.name === '從舊版另存的獨立任務');
    check(heads.length === 2 && copied.number === 1 && copied.seriesId === copied.mission.id && creates.length === 3 && creates.every(row => JSON.stringify(row) === JSON.stringify(creates[0])),
      'Save-as-new retries once into a separate series without duplicating the accepted mission');
    await editor.unroute('**/api/missions'); await editor.locator('#edit-mission').selectOption(fourth.id); await editor.locator('#load-mission').click();
    await waitForDom(() => document.querySelector('#draft-status').textContent.includes('第 4 版')); await ready(); await editor.locator('#launch-version').click();
    await editor.locator('#launch-room').selectOption('3'); await editor.locator('#create-session-form button').click();
    await waitForDom(() => !document.querySelector('#session-panel').hidden && document.querySelector('#session-phase').textContent.includes('準備'));
    created = (await api('/sessions')).find(row => row.roomIds.length === 1 && row.roomIds[0] === 3);
    check(created?.mission.id === fourth.id && created.mission.definition.durationSeconds === 1500 && created.mission.definition.props[0].position.x === 4.5,
      'Latest version launch uses the revised duration, environment and layout');
    await api('/sessions/' + created.id + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    await editor.locator('#tab-missions').click();
    let releaseHistory, historyRequested; const gate = new Promise(resolve => { releaseHistory = resolve; }), observed = new Promise(resolve => { historyRequested = resolve; });
    await editor.route('**/api/missions/*/history', async route => { const response = await route.fetch(); historyRequested(); await gate; await route.fulfill({ response }); });
    await editor.locator('#load-mission').click(); await observed; await editor.locator('#logout').click(); releaseHistory();
    await editor.waitForTimeout(100);
    check(await editor.locator('#mission-history').isHidden() && await editor.locator('#mission-version option').count() === 0 && await editor.locator('#edit-mission option').count() === 0 && await editor.locator('#draft-name').inputValue() === '',
      'Logout clears mission history and a delayed old history response cannot restore the draft');
    await editor.unroute('**/api/missions/*/history');
    await editor.locator('#login-key').fill(tokens.Master); await editor.locator('#login-form button').click();
    await editor.locator('#tab-missions').click(); await editor.locator('#edit-mission').selectOption(fourth.id);
    await editor.locator('#load-mission').click(); await waitForDom(() => document.querySelector('#draft-status').textContent.includes('第 4 版')); await ready();
    await editor.locator('#mission-version').selectOption(mission.id);
    let releaseComparison, comparisonRequested;
    const comparisonGate = new Promise(resolve => { releaseComparison = resolve; });
    const comparisonObserved = new Promise(resolve => { comparisonRequested = resolve; });
    await editor.route(`**/api/missions/${mission.id}/version`, async route => {
      const response = await route.fetch(); comparisonRequested(); await comparisonGate; await route.fulfill({ response });
    });
    try {
      await editor.locator('#compare-version').click(); await comparisonObserved;
      await editor.locator('#logout').click();
      const delivered = editor.waitForResponse(`**/api/missions/${mission.id}/version`);
      releaseComparison(); await delivered;
      await waitForDom(() => document.querySelector('#workspace').hidden && !document.querySelector('#login-form button').disabled);
      check(await compared.evaluate(node => node.hidden) && await editor.locator('#mission-comparison-rows tr').count() === 0,
        'A delayed comparison response from a prior login cannot reopen the comparison or restore private draft data');
    } finally { releaseComparison(); await editor.unroute(`**/api/missions/${mission.id}/version`); }

    await editor.locator('#login-key').fill(tokens.Master); await editor.locator('#login-form button').click();
    await editor.locator('#tab-missions').click(); await editor.locator('#edit-mission').selectOption(fourth.id);
    await editor.locator('#load-mission').click(); await waitForDom(() => document.querySelector('#draft-status').textContent.includes('第 4 版')); await ready();
    await editor.locator('#launch-version').click(); await editor.locator('#tab-missions').click();
    const restore = editor.locator('#restore-compared-version');
    await editor.locator('#compare-version').click(); await compared.waitFor(); await ready();
    check(await restore.isDisabled(), 'The current revision cannot be restored as a historical revision');
    await editor.locator('#draft-name').fill('保留未儲存的任務草稿');
    await editor.locator('#prop-x').fill('5.5'); await editor.locator('#prop-x').blur();
    const undoBeforeRestore = await editor.locator('#prop-history-status').innerText();
    await editor.locator('#mission-version').selectOption(mission.id); await editor.locator('#compare-version').click(); await compared.waitFor(); await ready();
    await editor.setViewportSize({ width: 390, height: 844 });
    check(await restore.isEnabled() && await editor.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'The historical restore action fits the mobile layout');
    await editor.screenshot({ path: path.join(screenshots, 'mission-restore-mobile.png'), fullPage: true });
    await editor.setViewportSize({ width: 1440, height: 1080 });
    editor.once('dialog', dialog => dialog.dismiss());
    await restore.click();
    check((await api(`/missions/${mission.id}/history`)).headId === fourth.id && await editor.locator('#pending-command').isHidden(),
      'Cancelling historical restore makes no library revision or pending request');

    const restoreRequests = [], restoreRoute = '**/api/missions/*/revisions';
    let discardRestoreResponse = false;
    await editor.route(restoreRoute, async route => {
      const request = route.request();
      const attempt = { path: new URL(request.url()).pathname, body: request.postData(), key: request.headers()['idempotency-key'] };
      restoreRequests.push(attempt);
      if (!discardRestoreResponse) { await route.continue(); return; }
      discardRestoreResponse = false;
      attempt.deliveredStatus = (await route.fetch()).status();
      await route.abort('failed');
    });
    try {
      const dialogOpened = editor.waitForEvent('dialog');
      const staleRestore = restore.click();
      const dialog = await dialogOpened;
      let fifth;
      try {
        fifth = await revise(fourth.id, { ...fourth.definition, name: '另一主控在確認期間保存第五版' });
        check(dialog.message().includes('第 1 版') && dialog.message().includes('第 4 版後') && dialog.message().includes('第 5 版'),
          'Restore confirmation displays the selected historical revision, exact parent and expected next revision');
      } finally { await dialog.accept(); await staleRestore; }
      await waitForDom(() => document.querySelector('#notice').textContent.includes('無法接續已確認的任務版本')); await ready();
      check(restoreRequests[0].path.endsWith(`/${fourth.id}/revisions`) && (await api(`/missions/${mission.id}/history`)).headId === fifth.id
        && await editor.locator('#pending-command').isHidden() && await editor.locator('#draft-name').inputValue() === '保留未儲存的任務草稿',
        'A new head during confirmation rejects the exact stale parent and retains the draft');
      await editor.locator('#refresh').click(); await editor.locator(`#edit-mission option[value="${fifth.id}"]`).waitFor({ state: 'attached' }); await ready();
      await editor.screenshot({ path: path.join(screenshots, 'mission-restore-desktop.png'), fullPage: true });
      discardRestoreResponse = true;
      editor.once('dialog', confirmation => confirmation.accept());
      await restore.click();
      await waitForDom(() => !document.querySelector('#pending-command').hidden && !document.querySelector('#retry-command').disabled);
      const sixthId = (await api(`/missions/${mission.id}/history`)).headId;
      const sixth = await api(`/missions/${sixthId}/version`);
      check(restoreRequests[1].deliveredStatus === 201 && sixth.number === 6 && sixth.previousId === fifth.id
        && JSON.stringify(sixth.mission.definition) === JSON.stringify(mission.definition),
        'Restore sends the original complete historical definition and appends it once to the newly confirmed head');
      const seventh = await revise(sixthId, { ...sixth.mission.definition, name: '另一主控在重試前保存第七版' });
      await editor.locator('#retry-command').click();
      await waitForDom(() => document.querySelector('#pending-command').hidden && document.querySelector('#notice').textContent.includes('保存為第 6 版')); await ready();
      const { deliveredStatus, ...firstRestore } = restoreRequests[1];
      const history = await api(`/missions/${mission.id}/history`);
      check(restoreRequests.length === 3 && firstRestore.key && JSON.stringify(restoreRequests[2]) === JSON.stringify(firstRestore)
        && history.headId === seventh.id && history.versions.filter(row => row.number === 6).length === 1,
        'A lost restore response retries the same payload and request ID even after a later revision is saved');
      check(await editor.locator('#draft-name').inputValue() === '保留未儲存的任務草稿' && await editor.locator('#prop-x').inputValue() === '5.5'
        && await editor.locator('#undo-prop').isEnabled() && await editor.locator('#prop-history-status').innerText() === undoBeforeRestore
        && (await editor.locator('#draft-status').innerText()).includes('第 4 版') && await editor.locator('#save-revision').isDisabled(),
        'Restoring a saved version preserves the dirty draft, original base and object undo history');
      const originalSession = await api(`/sessions/${session.id}`);
      check(await editor.locator('#mission-version').inputValue() === sixthId && await editor.locator('#launch-mission').inputValue() === fourth.id
        && originalSession.mission.id === mission.id && JSON.stringify(originalSession.mission.definition) === JSON.stringify(mission.definition),
        'Restore selects the confirmed history entry and preserves the existing launch pin and session snapshot');
    } finally { await editor.unroute(restoreRoute); }
    check(errors.length === 0, 'Mission revision workflow has no uncaught browser script errors');
  } catch (error) {
    const diagnostic = await editor.evaluate(() => ({ visibility: document.visibilityState,
      name: document.querySelector('#draft-name').value, status: document.querySelector('#draft-status').textContent,
      selectedVersion: document.querySelector('#mission-version').value,
      history: document.querySelector('#history-status').textContent, notice: document.querySelector('#notice').textContent })).catch(() => ({ unavailable: true }));
    await fs.writeFile(path.join(screenshots, 'mission-editor-failure.json'), JSON.stringify(diagnostic, null, 2));
    await fs.writeFile(path.join(screenshots, 'mission-editor-network-failure.json'), JSON.stringify({ maximumRecords: 128, records: network, scriptErrors: errors }, null, 2));
    await editor.screenshot({ path: path.join(screenshots, 'mission-editor-failure.png'), fullPage: true, timeout: 5000 }).catch(() => {});
    throw error;
  } finally { await editor.close(); await page.bringToFront(); }
};
