const fs = require('node:fs/promises');
const path = require('node:path');

module.exports = async function rifleBrowser({ context, tokens, base, root, screenshots, check }) {
  const page = await context.newPage(), errors = []; page.on('pageerror', error => errors.push(error.message));
  const sample = JSON.parse(await fs.readFile(path.join(root, 'src/VrCommand.Api/wwwroot/console/examples/simulation.json'), 'utf8'));
  async function load(profile) {
    const value = structuredClone(sample); value.assetSet = profile;
    await page.locator('#replay-file').setInputFiles({ name: profile + '.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(value)) });
    await page.waitForFunction(profile => document.querySelector('#replay-canvas').dataset.assetSet === profile && Number(document.querySelector('#replay-canvas').dataset.triangles) > 0, profile);
    return Number(await page.locator('#replay-canvas').getAttribute('data-triangles'));
  }
  try {
    await page.goto(base + '/console/'); await page.locator('#login-key').fill(tokens.Master); await page.locator('#login-form button').click();
    await page.locator('#tab-replay').click(); const old = await load('field-props-v1');
    check(await page.locator('#replay-canvas').getAttribute('data-rifle-triangles') === '0', 'Retained field-prop recordings keep their original simple weapon appearance');
    const current = await load('service-rifle-v1');
    const players = sample.frames[0].players, handMarkers = players.filter(p => p.rig && p.rig.kind !== 'None').length;
    check(current - old === players.length * (264 - 12) - handMarkers * 12
      && Number(await page.locator('#replay-canvas').getAttribute('data-rifle-count')) === players.length,
      'Real WebGL rendering uses the new 264-triangle player rifle while retaining identical cover and bodies');
    await page.screenshot({ path: path.join(screenshots, 'service-rifle-replay.png'), fullPage: true });
    await page.locator('#replay-camera').selectOption('follow'); await page.locator('#replay-canvas').hover(); await page.mouse.wheel(0, -1200);
    await page.screenshot({ path: path.join(screenshots, 'service-rifle-closeup.png'), fullPage: true });
    await page.locator('#replay-timeline').focus(); await page.locator('#replay-timeline').press('End');
    check(await page.locator('#replay-canvas').getAttribute('data-asset-set') === 'service-rifle-v1'
      && (await page.locator('#replay-statistics tr td').allTextContents()).join('|') === 'Quest3-Simulation|3|1|20|1|66.67%|80',
      'New rifle appearance preserves the recorded final combat result and seek behavior');
    for (const profile of ['primitives-v1', 'service-rifle-v1', 'field-props-v1', 'service-rifle-v1']) await load(profile);
    check(await page.locator('#replay-canvas').getAttribute('data-rifle-triangles') === '264' && errors.length === 0,
      'Repeated old/new recording switches release the previous scene and keep the new weapon renderable without script errors');
  } catch (error) { await page.screenshot({ path: path.join(screenshots, 'service-rifle-failure.png'), fullPage: true }).catch(() => {}); throw error; }
  finally { await page.close(); }
};
