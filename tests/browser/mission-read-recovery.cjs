const { randomUUID } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');

// Real HTTP + shipped browser UI. Only this isolated page's catalog GET is faulted.
module.exports = async function missionReadRecovery({ context, api, tokens, base, screenshots, check }) {
  const first = await api('/missions', 'POST', { name: '讀取恢復・原始任務', briefing: '保留原任務版本內容', durationSeconds: 60,
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false }, props: [] }, 'Master', 201, undefined, randomUUID());
  const second = await api(`/missions/${first.id}/revisions`, 'POST', { ...first.definition, name: '讀取恢復・第二版', durationSeconds: 120 }, 'Master', 201, undefined, randomUUID());
  const page = await context.newPage(), errors = [], requests = []; let requestsTruncated = false;
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith('/api/missions')) {
      if (requests.length >= 256) requestsTruncated = true;
      else requests.push({ method: request.method(), path: pathname });
    }
  });
  const wait = (fn, arg) => page.waitForFunction(fn, arg, { polling: 100 });
  const draft = async name => { await wait(value => document.querySelector('#draft-name').value === value && !document.querySelector('#mission-fields').disabled, name); };
  const mutations = () => requests.filter(row => row.method !== 'GET').length;
  const reads = () => requests.filter(row => /\/(history|version)$/.test(row.path)).length;
  async function decision(action, accept, type = 'confirm') {
    const result = page.waitForEvent('dialog', { timeout: 5000 }).then(async dialog => {
      const actualType = dialog.type();
      if (accept) await dialog.accept(); else await dialog.dismiss();
      return actualType;
    });
    const [actualType] = await Promise.all([result, action()]);
    return actualType === type;
  }
  const click = id => () => page.locator('#' + id).click();
  async function failRefresh(action, status = 503) {
    let release, observed, timer;
    const gate = new Promise(resolve => { release = resolve; });
    const requested = new Promise((resolve, reject) => { observed = resolve; timer = setTimeout(() => reject(new Error('Catalog fault was not requested')), 5000); });
    await page.route('**/api/mission-library', async route => {
      observed(); await gate;
      if (status === 0) await route.abort('failed');
      else await route.fulfill({ status, json: { error: 'Catalog temporarily unavailable' } });
    });
    try {
      await page.locator('#refresh').click(); await requested; clearTimeout(timer);
      await action(release);
    } finally {
      release(); clearTimeout(timer);
      await page.unrouteAll({ behavior: 'wait' });
    }
  }
  try {
    await page.bringToFront(); await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click(); await page.locator(`#edit-mission option[value="${second.id}"]`).waitFor({ state: 'attached' });
    await page.locator('#edit-mission').selectOption(second.id); await page.locator('#load-mission').click(); await draft(second.definition.name);
    const initialMutations = mutations();
    await page.locator('#draft-name').fill('未儲存的開場草稿');
    await page.locator('#add-barrel').click();
    await page.locator('#mission-version').selectOption(first.id);
    const beforeCancel = reads();
    const dirtyIntact = async () => await page.locator('#draft-name').inputValue() === '未儲存的開場草稿'
      && await page.locator('#prop-layer [data-index]').count() === 1
      && await page.locator('#undo-prop').isEnabled();
    for (const id of ['load-mission', 'load-version', 'new-mission', 'logout']) {
      check(await decision(click(id), false) && await dirtyIntact() && reads() === beforeCancel && mutations() === initialMutations,
        `Cancelling ${id} preserves the dirty name, layout and undo history without reading or saving a mission`);
    }
    check(await decision(() => page.evaluate(() => { setTimeout(() => location.reload(), 0); }), false, 'beforeunload') && await dirtyIntact(),
      'Cancelling a real browser reload keeps the unsaved mission in the authenticated editor');
    await page.route(`**/api/missions/${first.id}/history`, route => route.fulfill({ status: 503, json: { error: 'Dirty draft load temporarily unavailable' } }));
    await decision(click('load-version'), true);
    await wait(() => document.querySelector('#notice').textContent === 'Dirty draft load temporarily unavailable' && !document.querySelector('#mission-fields').disabled);
    check(await dirtyIntact(), 'A confirmed historical load that fails leaves the dirty draft and its undo history available');
    await page.unrouteAll({ behavior: 'wait' });
    check(await decision(click('load-version'), true), 'Confirming historical load permits an explicit replacement');
    await draft(first.definition.name);
    check(await page.locator('#prop-layer [data-index]').count() === 0 && await page.locator('#undo-prop').isDisabled(),
      'A successful historical load replaces the draft with the exact saved layout and clears its local undo history');
    await page.locator('#load-mission').click(); await draft(second.definition.name);
    await failRefresh(async release => {
      await page.locator('#mission-version').selectOption(first.id); await page.locator('#load-version').click();
      check(await page.locator('#draft-name').isDisabled() && await page.locator('#draft-name').inputValue() === second.definition.name,
        'A mission read waits for the in-flight catalog without prematurely replacing the draft');
      release(); await draft(first.definition.name);
      check(await page.locator('#draft-duration').inputValue() === '60' && await page.locator('#save-revision').isDisabled() && mutations() === initialMutations,
        'A failed background catalog does not cancel an explicit historical read or create a mutation');
      check((await page.locator('#notice').innerText()).includes('列表') && await page.locator('#notice').evaluate(node => node.classList.contains('error')),
        'A recovered mission read still warns that the background list was not refreshed');
    });
    await failRefresh(async release => {
      await page.locator('#load-mission').click(); release(); await draft(second.definition.name);
      check(await page.locator('#draft-duration').inputValue() === '120' && await page.locator('#save-revision').isEnabled() && mutations() === initialMutations,
        'Explicit latest-version read independently recovers the exact saved definition after catalog failure');
    });
    await failRefresh(async release => {
      await page.locator('#mission-version').selectOption(first.id); await page.locator('#load-version').click(); release(); await draft(first.definition.name);
      check(await page.locator('#draft-duration').inputValue() === '60' && mutations() === initialMutations,
        'A catalog transport failure also permits a fresh explicit mission read without replaying writes');
    }, 0);
    await page.locator('#load-mission').click(); await draft(second.definition.name);
    await page.route(`**/api/missions/${first.id}/history`, route => route.fulfill({ status: 503, json: { error: 'Selected history unavailable' } }));
    await page.locator('#mission-version').selectOption(first.id); await page.locator('#load-version').click();
    await wait(() => document.querySelector('#notice').textContent === 'Selected history unavailable' && !document.querySelector('#mission-fields').disabled);
    check(await page.locator('#draft-name').inputValue() === second.definition.name && mutations() === initialMutations,
      'Failure of the selected mission history preserves the prior draft and never substitutes cached contents');
    await page.unrouteAll({ behavior: 'wait' });
    await page.locator('#draft-name').fill('未提交的新修訂');
    await failRefresh(async release => {
      await page.locator('#save-revision').click(); release();
      await wait(() => !document.querySelector('#mission-fields').disabled && document.querySelector('#notice').classList.contains('error'));
      check(mutations() === initialMutations && await page.locator('#draft-name').inputValue() === '未提交的新修訂',
        'Mission writes keep their original refresh failure fence and do not silently inherit read recovery');
    });
    await failRefresh(async release => {
      const before = reads(); await page.locator('#mission-version').selectOption(first.id); await decision(click('load-version'), true); release();
      await wait(() => !document.querySelector('#mission-fields').disabled && document.querySelector('#notice').textContent.includes('沒有此操作權限'));
      check(reads() === before && await page.locator('#draft-name').inputValue() === '未提交的新修訂',
        'A forbidden background response cannot authorize an independent read or replace the retained draft');
    }, 403);
    await page.screenshot({ path: path.join(screenshots, 'mission-read-recovery.png'), fullPage: true });
    await failRefresh(async release => {
      const before = reads(); await decision(click('load-version'), true); release();
      await wait(() => document.querySelector('#workspace').hidden && document.querySelector('#mission-version').options.length === 0);
      check(reads() === before && await page.locator('#draft-name').inputValue() === '',
        'An unauthorized background response logs out instead of falling back to an old mission read');
    }, 401);
    await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click(); await page.locator(`#edit-mission option[value="${second.id}"]`).waitFor({ state: 'attached' });
    await page.locator('#edit-mission').selectOption(second.id); await page.locator('#load-mission').click(); await draft(second.definition.name);
    await failRefresh(async release => {
      await page.locator('#mission-version').selectOption(first.id); await page.locator('#load-version').click();
      const before = reads(); await page.locator('#logout').click(); release();
      await wait(() => document.querySelector('#workspace').hidden && document.querySelector('#mission-version').options.length === 0);
      // The next login waits until the old read's finally unlocks the login button.
      await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
      await page.locator('#tab-missions').waitFor({ state: 'visible' });
      check(reads() === before && await page.locator('#draft-name').inputValue() === '' && await page.locator('#mission-history').isHidden(),
        'Logout cancels the queued independent read before any old mission request or draft restoration');
    });
    let latest = second;
    for (let number = 3; number <= 22; number++) latest = await api(`/missions/${latest.id}/revisions`, 'POST', { ...first.definition, name: `讀取恢復・第${number}版` }, 'Master', 201, undefined, randomUUID());
    await page.locator('#tab-missions').click(); await page.locator('#refresh').click(); await page.locator(`#edit-mission option[value="${latest.id}"]`).waitFor({ state: 'attached' });
    await page.locator('#edit-mission').selectOption(latest.id); await page.locator('#load-mission').click(); await draft(latest.definition.name);
    check(await page.locator('#mission-version option').count() === 20 && await page.locator('#more-versions').isEnabled(),
      'A real twenty-row history page retains its authoritative continuation boundary');
    await failRefresh(async release => {
      await page.locator('#more-versions').click(); release();
      await wait(() => document.querySelector('#mission-version').options.length === 22 && document.querySelector('#more-versions').disabled);
      check(await page.locator('#draft-name').inputValue() === latest.definition.name && await page.locator(`#mission-version option[value="${first.id}"]`).count() === 1 && mutations() === initialMutations,
        'History pagination independently recovers its exact next page without reloading the draft or mutating missions');
    });
    await page.reload();
    check(await page.locator('#login-panel').isVisible(), 'A clean draft allows reload without requiring discard confirmation');
    check(!requestsTruncated && errors.length === 0, 'Mission read recovery retains complete bounded request metadata and has no uncaught browser errors');
  } catch (error) {
    const state = await page.evaluate(() => ({ name: document.querySelector('#draft-name').value, notice: document.querySelector('#notice').textContent,
      version: document.querySelector('#mission-version').value, locked: document.querySelector('#mission-fields').disabled })).catch(() => null);
    await fs.writeFile(path.join(screenshots, 'mission-read-recovery-failure.json'), JSON.stringify({ state, requests, requestsTruncated, errors }, null, 2));
    await page.screenshot({ path: path.join(screenshots, 'mission-read-recovery-failure.png'), fullPage: true, timeout: 5000 }).catch(() => {});
    throw error;
  } finally { await page.close(); }
};
