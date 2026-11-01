const path = require('node:path');

module.exports = async ({ context, api, tokens, base, mission, screenshots, check }) => {
  const page = await context.newPage(), errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const props = [{ assetId: 'sandbag', position: { x: 1, y: 0, z: 3 }, yawDegrees: 45 },
    { assetId: 'barrel', position: { x: -2, y: 0, z: 1 }, yawDegrees: 0 }];
  const saved = await api('/missions', 'POST', { ...mission.definition, name: '配置復原・原版本', props }, 'Master', 201);
  const wait = fn => page.waitForFunction(fn, null, { polling: 100 });
  const status = () => page.locator('#prop-history-status').innerText();
  async function field(id, value) { await page.locator('#' + id).fill(String(value)); await page.locator('#' + id).blur(); }
  async function undo() { await page.locator('#undo-prop').click(); }
  async function redo() { await page.locator('#redo-prop').click(); }
  async function load(id) {
    await page.locator('#edit-mission').selectOption(id); await page.locator('#load-mission').click();
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
    await load(saved.id); await page.locator('#prop-select').selectOption('0');
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
    // Save the restored geometry as a new immutable version through the normal UI.
    const requested = page.waitForRequest(request => request.method() === 'POST' && request.url() === `${base}/api/missions/${saved.id}/revisions`);
    const gate = new Promise(resolve => { releaseSave = resolve; });
    await page.route(`**/api/missions/${saved.id}/revisions`, async route => { await gate; await route.continue(); });
    await page.locator('#save-revision').click(); await requested;
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled(), 'Saving locks both history controls while the original revision request is pending');
    await page.locator('#layout-map').focus(); await page.keyboard.press('Control+z');
    check(await page.locator('#prop-x').inputValue() === '3', 'Map shortcut cannot mutate a draft during its pending save');
    releaseSave(); await wait(() => document.querySelector('#draft-status').textContent.startsWith('已儲存') && !document.querySelector('#mission-fields').disabled);
    const history = await api(`/missions/${saved.id}/history`), revised = await api(`/missions/${history.headId}`);
    check(revised.definition.props[0].position.x === 3 && revised.definition.props[0].position.z === 2 && JSON.stringify((await api(`/missions/${saved.id}`)).definition.props) === JSON.stringify(props), 'Normal revision save persists the restored placement and leaves the original mission immutable');
    await undo();
    check((await page.locator('#draft-status').innerText()).startsWith('尚未儲存的修改') && (await api(`/missions/${history.headId}`)).definition.props[0].position.x === 3, 'Undo after a confirmed save only changes the dirty local draft, never the saved version');
    await page.screenshot({ path: path.join(screenshots, 'placement-history-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'History controls remain inside the mobile editor viewport');
    await page.screenshot({ path: path.join(screenshots, 'placement-history-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1080 }); await load(history.headId);
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled() && await page.locator('#prop-x').inputValue() === '3', 'Reloading the current mission clears both previous branches and uses its actual latest version');
    await page.locator('#rotate-prop').click(); page.once('dialog', dialog => dialog.accept()); await page.locator('#new-mission').click();
    check(await page.locator('#prop-layer [data-index]').count() === 0 && await page.locator('#undo-prop').isDisabled(), 'A new mission cannot undo into a different mission document');
    await page.locator('#add-barrel').click(); await page.locator('#logout').click();
    await page.locator('#login-key').fill(tokens.Room1); await page.locator('#login-form button').click(); await page.locator('#tab-missions').click();
    check(await page.locator('#undo-prop').isDisabled() && await page.locator('#redo-prop').isDisabled() && await page.locator('#prop-layer [data-index]').count() === 0, 'Logout and a room-controller login clear history and preserve the read-only editor');
    check(errors.length === 0, 'Placement history workflow has no uncaught browser errors');
  } catch (error) { await page.screenshot({ path: path.join(screenshots, 'placement-history-failure.png'), fullPage: true }).catch(() => {}); throw error; }
  finally { releaseSave(); await page.close(); }
};
