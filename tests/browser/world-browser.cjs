const fs = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomUUID } = require('node:crypto');

module.exports = async function worldBrowser({ page, context, api, tokens, directory, root, base, screenshots, check }) {
  const keys = path.join(directory, 'world-keys.json'); await fs.writeFile(keys, JSON.stringify({ OperatorKeys: tokens }));
  const relay = process.env.VR_COMMAND_WORLD_RELAY_DLL || path.join(root, 'tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll');
  const children = [];
  function demo(name, seconds) {
    const child = spawn('dotnet', [relay, '--recording', path.join(directory, name + '.ndjson'), '--base-url', base, '--key-file', keys, '--demo-room', '2', '--seconds', String(seconds)], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '', error = ''; child.stdout.on('data', data => { output += data.toString(); }); child.stderr.on('data', data => { error += data.toString(); });
    const finished = new Promise(resolve => child.once('exit', code => resolve({ code, output, error }))); children.push(child);
    return { child, finished };
  }
  try {
    await page.setViewportSize({ width: 1440, height: 1080 });
    await page.locator('#tab-world').click(); await page.waitForFunction(() => document.querySelector('#world-message').textContent.includes('目前沒有'));
    check((await page.locator('#world-message').innerText()).includes('目前沒有'), 'World viewer reports an empty archive without inventing a recording');
    const source = demo('interrupted-world', 30);
    // Test credentials stay in this fixture's Node process, never window properties or storage.
    let entries;
    for (let attempt = 0; attempt < 100; attempt++) {
      entries = await api('/world-recordings');
      if (entries.some(info => info.acceptedSequence > 5)) break;
      if (source.child.exitCode !== null) throw new Error('World source exited: ' + (await source.finished).error);
      await page.waitForTimeout(50);
    }
    const live = entries[0];
    await page.locator('#world-refresh').click(); await page.locator('#world-recording option').waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(live.header.sessionId); await page.locator('#world-live').click();
    const canvas = page.locator('#world-canvas');
    await page.waitForFunction(() => Number(document.querySelector('#world-canvas').dataset.sequence) > 5 && Number(document.querySelector('#world-canvas').dataset.triangles) > 0);
    check((await page.locator('#world-status').innerText()).includes('Simulation') && (await page.locator('#world-message').innerText()).includes('無頭盔連接'), 'Real streamed world displays its simulation provenance and asset limits');
    check((await page.locator('#world-freshness').innerText()) === '正在接收快照' && (await page.locator('#world-actor-info').innerText()).includes('Simulated'), 'Live viewer distinguishes fresh snapshots and synthetic head/hand data');
    const before = Number(await canvas.getAttribute('data-sequence'));
    await page.waitForFunction(sequence => Number(document.querySelector('#world-canvas').dataset.sequence) > sequence, before);
    check((await page.locator('#world-statistics tr td').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80', 'Streamed per-frame combat statistics match the authoritative report prefix');
    const camera = await canvas.getAttribute('data-camera'); await page.locator('#world-camera').selectOption('top');
    check(await canvas.getAttribute('data-camera') !== camera, 'Streamed world supports the god-view camera preset');
    await page.locator('#world-camera').selectOption('follow');
    await page.screenshot({ path: path.join(screenshots, 'world-live.png'), fullPage: true });
    check((await api('/sessions/' + live.header.sessionId)).players.length === 1, 'Observation creates no extra player seat');
    source.child.kill(); await source.finished;
    await page.waitForFunction(() => document.querySelector('#world-freshness').textContent.includes('過期'));
    check((await page.locator('#world-status').innerText()).includes('未封存'), 'Stopped source becomes visibly stale while its archive remains incomplete');
    await page.screenshot({ path: path.join(screenshots, 'world-stale.png'), fullPage: true });
    await api('/sessions/' + live.header.sessionId + '/commands', 'POST', { commandId: randomUUID(), action: 'End' });
    const completeSource = demo('complete-world', 1), result = await completeSource.finished;
    check(result.code === 0, 'Native simulation produces a second complete persisted world: ' + result.error.slice(-300));
    const completed = JSON.parse(result.output);
    await page.locator('#world-refresh').click(); await page.locator(`#world-recording option[value="${completed.sessionId}"]`).waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(completed.sessionId); await page.locator('#world-replay').click();
    await page.locator('#world-player').waitFor(); await page.locator('#world-speed').selectOption('4');
    await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('已結束') && document.querySelector('#world-status').textContent.includes('核對封存'));
    check((await page.locator('#world-statistics tr td').allTextContents()).join('|') === 'World Simulation|2|1|20|1|100%|80' && (await page.locator('#world-environment').innerText()).includes('Storm'), 'Persisted replay reaches the exact final statistics and recorded environment');
    await page.locator('#world-speed').selectOption('0.25');
    await page.locator('#world-timeline').evaluate(input => { input.value = '0'; input.dispatchEvent(new Event('change', { bubbles: true })); });
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.sequence === '1');
    await page.locator('#world-pause').click();
    const paused = await canvas.getAttribute('data-sequence'); await page.waitForTimeout(150);
    check(await canvas.getAttribute('data-sequence') === paused, 'Replay seek reads indexed early state and pause holds the current frame');
    await page.locator('#world-timeline').evaluate(input => { input.value = input.max; input.dispatchEvent(new Event('change', { bubbles: true })); });
    await page.waitForFunction(() => document.querySelector('#world-status').textContent.includes('已結束'));
    await page.locator('#world-camera').selectOption('overview');
    await page.setViewportSize({ width: 390, height: 844 }); await page.waitForTimeout(100);
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1) && (await canvas.boundingBox()).width > 280, 'Streamed world controls and canvas fit a mobile viewport');
    await page.screenshot({ path: path.join(screenshots, 'world-replay-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1080 });
    const other = await context.newPage(); await other.goto(base + '/console/'); await other.locator('#login-key').fill(tokens.Room1); await other.locator('#login-form button').click();
    await other.locator('#tab-world').click(); await other.waitForFunction(() => document.querySelector('#world-message').textContent.includes('目前沒有'));
    check(await other.locator('#world-recording option').count() === 0, 'Room-scoped observer list reveals no foreign world'); await other.close();
    await page.locator('#tab-operations').click();
    check(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && !document.cookie), 'Streaming preserves memory-only credentials');
  } finally {
    for (const child of children) if (child.exitCode === null && child.signalCode === null) { const exited = new Promise(resolve => child.once('exit', resolve)); child.kill(); await exited; }
  }
};
