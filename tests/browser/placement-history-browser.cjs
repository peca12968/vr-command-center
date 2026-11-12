const path = require('node:path');
const fs = require('node:fs/promises');

module.exports = async ({ context, api, tokens, base, mission, screenshots, check }) => {
  const page = await context.newPage(), errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const props = [{ assetId: 'sandbag', position: { x: 1, y: 0, z: 3 }, yawDegrees: 45 },
    { assetId: 'barrel', position: { x: -2, y: 0, z: 1 }, yawDegrees: 0 }];
  const saved = await api('/missions', 'POST', { ...mission.definition, name: '配置復原・原版本', props }, 'Master', 201);
  const rowProp = { assetId: 'sandbag', position: { x: -3.5, y: 0, z: 2.125 }, yawDegrees: 12.5 };
  const rowSaved = await api('/missions', 'POST', { ...mission.definition, name: '成列配置・原版本',
    enemies: { count: 1, behavior: 'Hold', autoAttack: false }, props: [rowProp] }, 'Master', 201);
  const wait = fn => page.waitForFunction(fn, null, { polling: 100 });
  const status = () => page.locator('#prop-history-status').innerText();
  async function field(id, value) { await page.locator('#' + id).fill(String(value)); await page.locator('#' + id).blur(); }
  async function undo() { await page.locator('#undo-prop').click(); }
  async function redo() { await page.locator('#redo-prop').click(); }
  async function load(id, discard = false) {
    await page.locator('#edit-mission').selectOption(id);
    if (discard) page.once('dialog', dialog => dialog.accept());
    await page.locator('#load-mission').click();
    await wait(() => !document.querySelector('#mission-fields').disabled && document.querySelector('#prop-history-status').textContent.includes('可復原 0'));
  }
  let releaseSave = () => {};
  try {
    await page.goto(base + '/console/'); await page.bringToFront();
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click(); await page.locator(`#edit-mission option[value="${saved.id}"]`).waitFor({ state: 'attached' });
    await load(saved.id);
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled(), 'Loading a saved placement starts a new empty local history');
    await page.locator('#prop-select').selectOption('0'); await field('prop-x', 2.25);
    check((await status()).includes('可復原 1') && await page.locator('#prop-x').inputValue() === '2.25', 'A numeric inspector edit records its exact unsnapped coordinate');
    await undo(); check(await page.locator('#prop-x').inputValue() === '1' && (await status()).includes('可重做 1'), 'Undo restores the original saved coordinate');
    await redo(); check(await page.locator('#prop-x').inputValue() === '2.25', 'Redo restores the exact coordinate rather than a rounded map point');
    await page.locator('#rotate-prop').click(); await undo();
    check(await page.locator('#prop-yaw').inputValue() === '45', 'Undo restores rotation independently of the earlier translation');
    // Invalid and no-op inspector changes must not discard redo.
    await field('prop-x', 2.25); await field('prop-x', '');
    check((await status()).includes('可重做 1') && await page.locator('#prop-x').inputValue() === '2.25', 'Invalid and unchanged fields preserve redo and leave placement unchanged');
    await page.locator('#prop-select').selectOption('1'); await page.locator('#remove-prop').click();
    check(await page.locator('#prop-layer [data-index]').count() === 1 && await page.locator('#redo-prop').isDisabled(), 'A new delete after undo clears the discarded redo branch');
    await undo();
    check(await page.locator('#prop-layer [data-index]').count() === 2 && await page.locator('#prop-select').inputValue() === '1' && await page.locator('#prop-asset').inputValue() === 'barrel', 'Undo restores deleted object order and selection');
    await page.locator('#add-sandbag').click(); await undo(); await redo();
    check(await page.locator('#prop-layer [data-index]').count() === 3 && await page.locator('#prop-select').inputValue() === '2', 'Add, undo and redo retain the exact new object and selection');
    await load(saved.id, true); await page.locator('#prop-select').selectOption('0');
    await page.locator('#prop-layer [data-index="0"]').focus(); await page.keyboard.press('ArrowRight');
    check((await status()).includes('可復原 1') && await page.locator('#prop-x').inputValue() === '1.5', 'Arrow movement from a keyboard-focused object retains focus until its history step closes');
    await undo();
    await page.locator('#layout-map').scrollIntoViewIfNeeded();
    const coords = await page.locator('#layout-map').evaluate(svg => [[1, -3], [3, -2]].map(([x, y]) => {
      const p = svg.createSVGPoint(); p.x = x; p.y = y; const q = p.matrixTransform(svg.getScreenCTM()); return { x: q.x, y: q.y };
    }));
    await page.mouse.move(coords[0].x, coords[0].y); await page.mouse.down(); await page.mouse.move(coords[1].x, coords[1].y, { steps: 12 }); await page.mouse.up();
    check((await status()).includes('可復原 1') && await page.locator('#prop-x').inputValue() === '3' && await page.locator('#prop-z').inputValue() === '2', 'A real twelve-update pointer drag is one history step');
    await undo(); check(await page.locator('#prop-x').inputValue() === '1' && await page.locator('#prop-z').inputValue() === '3', 'One undo restores both original axes of the complete drag');
    await page.locator('#layout-map').focus(); await page.keyboard.press('Control+y');
    check(await page.locator('#prop-x').inputValue() === '3', 'Focused map Control+Y redoes the pointer gesture');
    await page.keyboard.down('ArrowRight'); await page.keyboard.down('ArrowRight'); await page.keyboard.down('ArrowRight'); await page.keyboard.up('ArrowRight');
    check((await status()).includes('可復原 2') && await page.locator('#prop-x').inputValue() === '4.5', 'Repeated keydown events until keyup form a single keyboard move');
    await page.keyboard.press('Control+z');
    check(await page.locator('#prop-x').inputValue() === '3' && (await status()).includes('可重做 1'), 'Focused map Control+Z restores the entire held-arrow move');
    await page.keyboard.press('Control+Shift+z'); check(await page.locator('#prop-x').inputValue() === '4.5', 'Focused map Control+Shift+Z redoes the held-arrow move');
    await page.keyboard.down('ArrowLeft'); await page.locator('#draft-name').focus(); await page.keyboard.up('ArrowLeft');
    await undo(); check(await page.locator('#prop-x').inputValue() === '4.5', 'Losing map focus closes the active keyboard gesture');
    const beforeTyping = await status(); await page.locator('#draft-briefing').fill('文字編輯獨立於物件復原'); await page.locator('#draft-briefing').press('Control+z');
    check(await status() === beforeTyping && await page.locator('#prop-x').inputValue() === '4.5', 'Text-field undo never invokes object history');
    await page.locator('#layout-map').focus(); await page.keyboard.press('Control+z'); // x3
    await field('prop-x', 3.125); await field('prop-yaw', 47.5);
    check(await page.locator('#mission-form').evaluate(form => form.checkValidity()), 'Exact finite coordinates and angles can be submitted without rounding to the map increments');
    // Save the restored geometry as a new immutable version through the normal UI.
    const requested = page.waitForRequest(request => request.method() === 'POST' && request.url() === `${base}/api/missions/${saved.id}/revisions`);
    const gate = new Promise(resolve => { releaseSave = resolve; });
    await page.route(`**/api/missions/${saved.id}/revisions`, async route => { await gate; await route.continue(); });
    await page.locator('#save-revision').click(); await requested;
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled(), 'Saving locks both history controls while the original revision request is pending');
    const pendingLogout = page.waitForEvent('dialog', { timeout: 5000 }).then(async dialog => {
      const warned = dialog.type() === 'confirm' && dialog.message().includes('重試資料');
      await dialog.dismiss();
      return warned;
    });
    await page.locator('#logout').click();
    check(await pendingLogout && await page.locator('#workspace').isVisible() && await page.locator('#draft-name').isDisabled(),
      'Cancelling logout during an in-flight save keeps the authenticated draft locked until its response');
    await page.locator('#layout-map').focus(); await page.keyboard.press('Control+z');
    check(await page.locator('#prop-x').inputValue() === '3.125', 'Map shortcut cannot mutate a draft during its pending save');
    releaseSave(); await wait(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const history = await api(`/missions/${saved.id}/history`), revised = await api(`/missions/${history.headId}`);
    check(revised.definition.props[0].position.x === 3.125 && revised.definition.props[0].position.z === 2
      && revised.definition.props[0].yawDegrees === 47.5 && JSON.stringify((await api(`/missions/${saved.id}`)).definition.props) === JSON.stringify(props),
      'Normal revision save preserves exact position and yaw while leaving the original mission immutable');
    await undo();
    check((await page.locator('#draft-status').innerText()).startsWith('尚未儲存的修改') && (await api(`/missions/${history.headId}`)).definition.props[0].yawDegrees === 47.5, 'Undo after a confirmed save only changes the dirty local draft, never the saved version');
    await page.screenshot({ path: path.join(screenshots, 'placement-history-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'History controls remain inside the mobile editor viewport');
    await page.screenshot({ path: path.join(screenshots, 'placement-history-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1080 }); await load(history.headId, true);
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled() && await page.locator('#prop-x').inputValue() === '3.125'
      && await page.locator('#prop-yaw').inputValue() === '47.5', 'Reloading the current mission clears both previous branches and restores its saved precision');
    await load(rowSaved.id);
    await page.locator('#prop-select').selectOption('0');
    const loadedRowStatus = await page.locator('#draft-status').innerText();
    await page.locator('#prop-copy-panel summary').click();
    const preview = () => page.locator('#preview-prop-copy').click();
    const ghosts = page.locator('#prop-copy-preview [data-index]');
    const objects = page.locator('#prop-layer [data-index]');
    const apply = page.locator('#apply-prop-copy');
    const copyStatus = page.locator('#prop-copy-status');
    await field('prop-copy-count', 21); await preview();
    check(await apply.isDisabled() && await ghosts.count() === 0 && (await page.locator('#prop-copy-status').innerText()).includes('1 至 20'),
      'Row preview rejects a count beyond twenty without placing any copies');
    await field('prop-copy-count', 2); await field('prop-copy-x', 0); await preview();
    check(await apply.isDisabled() && await ghosts.count() === 0, 'A zero displacement cannot preview stacked copies');
    await field('prop-copy-x', 10); await preview();
    check(await apply.isDisabled() && (await page.locator('#prop-copy-status').innerText()).includes('超出配置圖'), 'An out-of-map row is rejected as a whole');
    await field('prop-copy-x', 0.25); await preview();
    await copyStatus.filter({ hasText: '預覽配置有' }).waitFor();
    check((await ghosts.locator('text').allTextContents()).join() === '2,3'
      && await page.locator('#prop-copy-preview [data-layout-invalid="true"]').count() === 2
      && (await page.locator('#prop-copy-issues').innerText()).includes('物件 1 與 2')
      && await objects.count() === 1 && await page.locator('#undo-prop').isDisabled(),
      'The original layout service detects overlapping copies before they alter the draft or undo history');
    await field('prop-copy-x', 2.375); await field('prop-copy-z', 0.125); await preview();
    await copyStatus.filter({ hasText: '預覽場地檢查通過' }).waitFor();
    check(await ghosts.count() === 2 && await objects.count() === 1 && await page.locator('#undo-prop').isDisabled()
      && (await page.locator('#draft-status').innerText()) === loadedRowStatus && !(await apply.isDisabled()),
      'Two translucent copies preview without changing the saved draft, selection history, or actual objects');
    await page.screenshot({ path: path.join(screenshots, 'placement-row-preview.png'), fullPage: true });
    await field('prop-copy-z', '');
    check(await ghosts.count() === 0 && await apply.isDisabled() && await page.locator('#mission-form').evaluate(form => form.checkValidity()),
      'Editing a preview parameter discards its ghosts and a blank offset does not invalidate the mission form');
    await field('prop-copy-z', 0.125); await preview(); await apply.click();
    check(await ghosts.count() === 0 && await objects.count() === 3 && await page.locator('#prop-select').inputValue() === '2'
      && (await status()).includes('可復原 1'), 'Applying a preview adds the full row and selects its last object in one history step');
    await undo();
    check(await objects.count() === 1 && await page.locator('#prop-select').inputValue() === '0', 'One undo removes all copies and restores the source selection');
    await redo();
    check(await objects.count() === 3 && await page.locator('#prop-x').inputValue() === '1.25' && await page.locator('#prop-z').inputValue() === '2.375'
      && await page.locator('#prop-yaw').inputValue() === '12.5', 'One redo restores the full row with its original angle and unsnapped offsets');
    await page.locator('#save-revision').click();
    await wait(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const rowHistory = await api(`/missions/${rowSaved.id}/history`);
    const expectedRow = [rowProp, { ...rowProp, position: { x: -1.125, y: 0, z: 2.25 } }, { ...rowProp, position: { x: 1.25, y: 0, z: 2.375 } }];
    const rowMatches = props => JSON.stringify(props) === JSON.stringify(expectedRow);
    check(rowHistory.headId !== rowSaved.id && rowMatches((await api(`/missions/${rowHistory.headId}`)).definition.props)
      && (await api(`/missions/${rowSaved.id}`)).definition.props.length === 1, 'The immutable row revision stores the exact geometry and the original retains one object');
    await load(rowHistory.headId);
    check(await objects.count() === 3 && await page.locator('#undo-prop').isDisabled(), 'Reload shows all saved row objects in a fresh local history');
    await page.locator('#mission-version').selectOption(rowHistory.headId);
    const templateDownload = page.waitForEvent('download');
    await page.locator('#export-mission-template').click();
    const rowTemplate = path.join(screenshots, 'placement-row-template.json');
    await (await templateDownload).saveAs(rowTemplate);
    check(rowMatches(JSON.parse(await fs.readFile(rowTemplate, 'utf8')).definition.props), 'Actual saved-version template download retains every row position and angle');

    await page.locator('#prop-move-panel summary').click();
    const moveSelection = index => page.locator(`[data-move-index="${index}"]`);
    const movePreview = page.locator('#preview-prop-move'), moveApply = page.locator('#apply-prop-move');
    const moveGhosts = page.locator('#prop-move-preview [data-index]');
    const moveStatus = page.locator('#prop-move-status');
    const selectedObjects = page.locator('#prop-layer [data-move-selected]');
    const beforeMove = await page.locator('#draft-status').innerText();
    await page.locator('#select-all-prop-move').click();
    check(await selectedObjects.count() === 3 && await page.locator('#prop-move-list input:checked').count() === 3,
      'Select all marks the same three objects on the map and in the batch list');
    await page.locator('#clear-prop-move-selection').click();
    check(await selectedObjects.count() === 0 && await movePreview.isDisabled(), 'Clearing selection removes all map marks and disables preview');
    await moveSelection(0).check(); await moveSelection(2).check();
    await movePreview.click();
    check(await moveApply.isDisabled() && await moveGhosts.count() === 0
      && (await page.locator('#prop-move-status').innerText()).includes('至少一項須非零'), 'Batch translation rejects a zero displacement');
    await field('prop-move-x', 9); await movePreview.click();
    check(await moveApply.isDisabled() && await moveGhosts.count() === 0 && (await page.locator('#prop-move-status').innerText()).includes('超出配置圖'),
      'One object outside the map rejects the entire batch preview');
    await field('prop-move-x', 4.5); await movePreview.click();
    await moveStatus.filter({ hasText: '預覽配置有' }).waitFor();
    check(await page.locator('#prop-move-preview [data-index="2"][data-layout-invalid="true"]').count() === 1
      && (await page.locator('#prop-move-issues').innerText()).includes('物件 3：旋轉後的包圍盒超出')
      && await objects.count() === 3 && await page.locator('#undo-prop').isDisabled(),
      'An in-map destination with an out-of-room footprint is marked before a batch move can change the draft');
    await page.locator('#layout-map').screenshot({ path: path.join(screenshots, 'placement-proposal-outside-room.png') });

    const layoutRoute = '**/api/mission-layout';
    let release, reportReady, handled, started = false;
    const held = new Promise(resolve => { release = resolve; });
    const ready = new Promise(resolve => { reportReady = resolve; });
    const done = new Promise(resolve => { handled = resolve; });
    const isOldProposal = request => request.url() === base + '/api/mission-layout'
      && request.postDataJSON()?.props[2]?.position.x === 5.75;
    const holdInvalid = async route => {
      if (!isOldProposal(route.request())) return route.continue();
      started = true;
      try {
        const response = await route.fetch();
        reportReady(null);
        await held;
        await route.fulfill({ response });
        handled(null);
      } catch (error) { reportReady(error); handled(error); }
    };
    await page.route(layoutRoute, holdInvalid);
    try {
      const requested = page.waitForRequest(isOldProposal, { timeout: 5000 });
      await movePreview.click();
      await requested;
      const error = await ready;
      if (error) throw error;
      check(await moveApply.isDisabled(), 'A pending proposal check leaves Apply disabled');
      await field('prop-move-x', 0.25); await field('prop-move-z', 0.5); await movePreview.click();
      await moveStatus.filter({ hasText: '預覽場地檢查通過' }).waitFor();
    } finally {
      release();
      const error = started ? await done : null;
      await page.unroute(layoutRoute, holdInvalid);
      if (error) throw error;
    }
    check((await moveStatus.innerText()).includes('預覽場地檢查通過') && await page.locator('#prop-move-issues li').count() === 0,
      'A held invalid proposal response cannot replace the newer valid geometry or warnings');
    const failProposal = route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    await page.route(layoutRoute, failProposal);
    try {
      await movePreview.click();
      await moveStatus.filter({ hasText: '預覽檢查未完成' }).waitFor();
      check(await moveApply.isEnabled() && await page.locator('#undo-prop').isDisabled(),
        'A failed check is visible and still permits local draft editing');
    } finally { await page.unroute(layoutRoute, failProposal); }
    await field('prop-move-x', 0.25); await field('prop-move-z', 0.5); await movePreview.click();
    await moveStatus.filter({ hasText: '預覽場地檢查通過' }).waitFor();
    const previewNumbers = await moveGhosts.locator('text').allTextContents();
    check(await moveGhosts.count() === 2 && previewNumbers.join(',') === '1,3'
      && await objects.count() === 3 && await page.locator('#undo-prop').isDisabled() && (await page.locator('#draft-status').innerText()) === beforeMove,
      'Preview keeps original numbering, geometry and edit history while showing the two destinations');
    await page.locator('#layout-map').screenshot({ path: path.join(screenshots, 'placement-batch-move-map.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.locator('#prop-move-panel').evaluate(panel => panel.scrollWidth <= panel.clientWidth + 1), 'Batch move controls fit the mobile editor');
    await page.setViewportSize({ width: 1440, height: 1080 });
    await moveSelection(2).uncheck();
    check(await moveApply.isDisabled() && await moveGhosts.count() === 0, 'Changing the group invalidates the displayed destinations');
    await moveSelection(2).check(); await movePreview.click();
    await page.locator('#tab-operations').click(); await page.locator('#tab-missions').click();
    check(await moveGhosts.count() === 0 && await page.locator('#prop-move-list input:checked').count() === 0,
      'Leaving the mission editor clears the pending group and its preview');
    await page.locator('#prop-move-panel summary').click();
    await moveSelection(0).check(); await moveSelection(2).check();
    await field('prop-move-x', 0.25); await field('prop-move-z', 0.5); await movePreview.click(); await moveApply.click();
    const moved = [
      { ...expectedRow[0], position: { x: -3.25, y: 0, z: 2.625 } }, expectedRow[1],
      { ...expectedRow[2], position: { x: 1.5, y: 0, z: 2.875 } }
    ];
    const expectedTransforms = expected => expected.map(prop => `translate(${prop.position.x} ${-prop.position.z}) rotate(${prop.yawDegrees})`).join('|');
    const transforms = () => objects.evaluateAll(nodes => nodes.map(node => node.getAttribute('transform')).join('|'));
    check(await transforms() === expectedTransforms(moved) && (await status()).includes('可復原 1') && await moveGhosts.count() === 0,
      'One batch edit moves only the selected objects, preserving order and exact unsnapped geometry');
    await undo();
    check(await transforms() === expectedTransforms(expectedRow), 'A single undo restores every original position');
    await redo();
    check(await transforms() === expectedTransforms(moved), 'A single redo restores the complete batch translation');
    await page.locator('#save-revision').click();
    await wait(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const batchHead = (await api(`/missions/${rowSaved.id}/history`)).headId;
    check(JSON.stringify((await api(`/missions/${batchHead}`)).definition.props) === JSON.stringify(moved)
      && rowMatches((await api(`/missions/${rowHistory.headId}`)).definition.props),
      'The batch revision stores only the confirmed geometry and keeps the previous version immutable');
    await load(batchHead);
    check(await transforms() === expectedTransforms(moved) && await page.locator('#undo-prop').isDisabled(),
      'Reload shows the complete batch geometry and starts a fresh undo history');
    await page.locator('#mission-version').selectOption(batchHead);
    const batchExport = page.waitForEvent('download');
    await page.locator('#export-mission-template').click();
    const batchTemplate = path.join(screenshots, 'placement-batch-move-template.json');
    await (await batchExport).saveAs(batchTemplate);
    check(JSON.stringify(JSON.parse(await fs.readFile(batchTemplate, 'utf8')).definition.props) === JSON.stringify(moved),
      'The exported mission contains the exact new batch geometry for the game server');

    await page.locator('#prop-move-panel summary').click();
    await moveSelection(0).check();
    const pivot = page.locator('#prop-move-preview [data-rotation-pivot]');
    await field('prop-move-yaw', -22.5); await movePreview.click();
    check(await moveGhosts.getAttribute('transform') === 'translate(-3.25 -2.625) rotate(-10)'
      && await pivot.getAttribute('transform') === 'translate(-3.25 -2.625)',
      'A single selected object turns in place with a fractional negative angle');
    await field('prop-move-yaw', 361); await movePreview.click();
    check(await moveApply.isDisabled() && await moveGhosts.count() === 0 && await pivot.count() === 0,
      'An out-of-range angle clears the pending geometry and blocks apply');
    await moveSelection(2).check();
    await field('prop-move-yaw', 90); await field('prop-move-x', 0.5); await field('prop-move-z', -0.75);
    await movePreview.click();
    const rotated = [
      { ...moved[0], position: { x: -0.5, y: 0, z: 4.375 }, yawDegrees: 102.5 }, moved[1],
      { ...moved[2], position: { x: -0.25, y: 0, z: -0.375 }, yawDegrees: 102.5 }
    ];
    check(await moveGhosts.evaluateAll(nodes => nodes.map(node => node.getAttribute('transform')).join('|'))
      === expectedTransforms([rotated[0], rotated[2]]) && await pivot.getAttribute('transform') === 'translate(-0.875 -2.75)'
      && await transforms() === expectedTransforms(moved) && await page.locator('#undo-prop').isDisabled(),
      'The preview turns clockwise around the original center, then applies the room-local offset without editing the draft');
    await page.locator('#layout-map').screenshot({ path: path.join(screenshots, 'placement-batch-rotation-map.png') });
    await moveApply.click();
    check(await transforms() === expectedTransforms(rotated) && (await status()).includes('可復原 1') && await pivot.count() === 0,
      'Batch rotation and translation update only the selected positions and facings in one history step');
    await undo();
    check(await transforms() === expectedTransforms(moved), 'One undo restores every original position and angle');
    await redo();
    check(await transforms() === expectedTransforms(rotated), 'One redo restores the complete rotated layout');
    await page.locator('#save-revision').click();
    await wait(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const rotatedHead = (await api(`/missions/${rowSaved.id}/history`)).headId;
    check(JSON.stringify((await api(`/missions/${rotatedHead}`)).definition.props) === JSON.stringify(rotated)
      && JSON.stringify((await api(`/missions/${batchHead}`)).definition.props) === JSON.stringify(moved),
      'The rotated revision retains exact geometry and leaves its source version unchanged');
    await load(rotatedHead);
    await page.locator('#mission-version').selectOption(rotatedHead);
    const rotationExport = page.waitForEvent('download');
    await page.locator('#export-mission-template').click();
    const rotationTemplate = path.join(screenshots, 'placement-batch-rotation-template.json');
    await (await rotationExport).saveAs(rotationTemplate);
    check(await transforms() === expectedTransforms(rotated)
      && JSON.stringify(JSON.parse(await fs.readFile(rotationTemplate, 'utf8')).definition.props) === JSON.stringify(rotated),
      'Reloaded and exported task both retain the rotated layout for the game server');

    await page.locator('#rotate-prop').click(); page.once('dialog', dialog => dialog.accept()); await page.locator('#new-mission').click();
    check(await page.locator('#prop-layer [data-index]').count() === 0 && await page.locator('#undo-prop').isDisabled(), 'A new mission cannot undo into a different mission document');
    await page.locator('#add-barrel').click(); page.once('dialog', dialog => dialog.accept()); await page.locator('#logout').click();
    await page.locator('#login-key').fill(tokens.Room1); await page.locator('#login-form button').click(); await page.locator('#tab-missions').click();
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled() && await page.locator('#prop-layer [data-index]').count() === 0, 'Logout and a room-controller login clear history and preserve the read-only editor');
    check(errors.length === 0, 'Placement history workflow has no uncaught browser errors');
  } catch (error) { await page.screenshot({ path: path.join(screenshots, 'placement-history-failure.png'), fullPage: true }).catch(() => {}); throw error; }
  finally { releaseSave(); await page.close(); }
};
