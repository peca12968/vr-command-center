const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { execFile, spawn } = require('node:child_process');
const { promisify } = require('node:util');

const execute = promisify(execFile);

module.exports = async function environmentBrowser({ page, api, tokens, directory, root, base, screenshots, check }) {
  const previousSessions = new Set((await api('/world-recordings')).map(row => row.header.sessionId));
  const keys = path.join(directory, 'environment-keys.json'), recording = path.join(directory, 'environment.ndjson');
  await fs.writeFile(keys, JSON.stringify({ OperatorKeys: tokens }));
  const relay = process.env.VR_COMMAND_WORLD_RELAY_DLL || path.join(root, 'tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll');
  const child = spawn('dotnet', [relay, '--recording', recording, '--base-url', base, '--key-file', keys, '--demo-room', '4', '--seconds', '12', '--environment-demo', 'true'], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '', error = ''; child.stdout.on('data', bytes => { output += bytes.toString(); }); child.stderr.on('data', bytes => { error += bytes.toString(); });
  const finished = new Promise(resolve => child.once('exit', code => resolve(code)));
  try {
    let info;
    for (let attempt = 0; attempt < 150; attempt++) {
      info = (await api('/world-recordings')).find(row => !previousSessions.has(row.header.sessionId) && row.header.roomIds.includes(4) && row.acceptedSequence > 3);
      if (info) break;
      if (child.exitCode !== null) throw new Error('Environment source exited: ' + error.slice(-300));
      await page.waitForTimeout(50);
    }
    if (!info) throw new Error('Environment source did not publish its first frames');
    await page.locator('#tab-world').click(); await page.locator('#world-refresh').click();
    await page.locator(`#world-recording option[value="${info.header.sessionId}"]`).waitFor({ state: 'attached' });
    await page.locator('#world-recording').selectOption(info.header.sessionId); await page.locator('#world-live').click();
    const canvas = page.locator('#world-canvas');
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.rainCount === '128');
    await fs.writeFile(path.join(screenshots, 'weather-first-rain.json'), JSON.stringify(await canvas.evaluate(node => ({ ...node.dataset })), null, 2));
    // Rain also exists during lightning. Wait for the non-flash night state
    // before asserting its regular sun intensity; do not alter cue timing.
    const nightHandle = await page.waitForFunction(id => {
      const state = document.querySelector('#world-canvas').dataset;
      const message = document.querySelector('#world-message').textContent;
      return document.querySelector('#world-recording').value === id && state.rainCount === '128' && state.weatherFlash === 'false' && state.weatherSun === '0.08' && message.includes('非原始音軌')
        ? { ...state, message, recording: id } : false;
    }, info.header.sessionId);
    const night = await nightHandle.jsonValue(); await nightHandle.dispose();
    await fs.writeFile(path.join(screenshots, 'weather-night-assertion.json'), JSON.stringify({ info, previousSessions: [...previousSessions], night }, null, 2));
    check(info.header.environmentVersion === 1 && night.message.includes('非原始音軌') && night.weatherSun === '0.08',
      'Native versioned weather reaches a real night/rain rendering without claiming an original audio recording');
    check(await canvas.getAttribute('data-weather-audio') !== 'on' && await page.locator('#world-sound').getAttribute('aria-pressed') === 'false', 'Weather audio remains off before an explicit user gesture');
    const rainTick = await canvas.getAttribute('data-weather-tick');
    await page.waitForFunction(tick => document.querySelector('#world-canvas').dataset.weatherTick !== tick, rainTick);
    check(await canvas.getAttribute('data-weather-fog') === '0.02', 'Storm drops and fog advance from received authoritative simulation ticks');
    for (const name of ['rain-loop.wav', 'thunder.wav']) {
      const response = await fetch(base + '/console/audio/' + name), served = Buffer.from(await response.arrayBuffer());
      const canonical = await fs.readFile(path.join(root, 'clients/unity/Assets/VrCommand/Audio', name));
      check(response.ok && served.equals(canonical), 'Browser serves the exact canonical Unity PCM asset: ' + name);
    }
    await page.locator('#world-sound').click();
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.weatherAudio === 'on' && Number(document.querySelector('#world-canvas').dataset.weatherAudioPeak) > .00001);
    check(true, 'Explicit sound enable drives a nonzero real Web Audio output graph');
    await page.screenshot({ path: path.join(screenshots, 'world-environment-rain-night.png'), fullPage: true });
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.weatherFlash === 'true', null, { timeout: 20000 });
    check(Number(await canvas.getAttribute('data-weather-sun')) > 2, 'Lightning renders at the received v1 strike clock boundary');
    await page.waitForFunction(() => Number(document.querySelector('#world-canvas').dataset.thunderCount) === 1, null, { timeout: 8000 });
    check(true, 'Observed lightning produces one delayed thunder cue through Web Audio');
    const code = await finished; if (code !== 0) throw new Error('Environment source failed: ' + error.slice(-300));
    const result = JSON.parse(output); check(result.complete, 'Environment source completes and seals its actual world archive');
    const frames = (await fs.readFile(recording, 'utf8')).trim().split('\n').map(line => JSON.parse(line)).filter(row => row.type === 'frame').map(row => row.payload);
    const flash = frames.find(frame => frame.frame.tick === 140), thunder = frames.find(frame => frame.frame.tick === 180);
    await page.locator('#world-speed').selectOption('0.25');
    await page.locator('#world-timeline').evaluate((input, value) => { input.value = String(value); input.dispatchEvent(new Event('change', { bubbles: true })); }, flash.elapsedMilliseconds);
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.weatherTick === '140' && document.querySelector('#world-canvas').dataset.weatherFlash === 'true');
    check(true, 'Persisted replay reconstructs the same lightning window from its recorded tick');
    const beforeSeek = await canvas.getAttribute('data-thunder-count');
    await page.locator('#world-timeline').evaluate((input, value) => { input.value = String(value); input.dispatchEvent(new Event('change', { bubbles: true })); }, thunder.elapsedMilliseconds);
    await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.weatherTick === '180');
    check(await canvas.getAttribute('data-thunder-count') === beforeSeek, 'Seeking directly to an old thunder boundary never plays a catch-up burst');
    await page.locator('#world-pause').click(); const paused = await canvas.getAttribute('data-weather-tick'); await page.waitForTimeout(200);
    check(await canvas.getAttribute('data-weather-tick') === paused && await canvas.getAttribute('data-weather-flash') === 'false', 'Replay pause freezes rain and clears any held flash');
    await page.locator('#world-sound').click(); check(await page.locator('#world-sound').getAttribute('aria-pressed') === 'false', 'Sound can be explicitly disabled after replay without changing the archive');
    const policyRoute = `/sessions/${info.header.sessionId}/world/policy-frames`;
    const expected = frames.filter((frame, index) => {
      if (index === 0) return true;
      const previous = frames[index - 1];
      return ['phase', 'behavior', 'night', 'autoAttack'].some(key => frame.frame[key] !== previous.frame[key])
        || ['weather', 'lightning'].some(key => frame[key] !== previous[key]);
    });
    const policyPage = await api(policyRoute + `?throughFrame=${frames.at(-1).sequence}`, 'GET', undefined, 'Room4');
    check(policyPage.frames.map(row => row.frameSequence).join(',') === expected.map(frame => frame.sequence).join(',')
      && policyPage.frames[0].policy.weather === 'Storm' && policyPage.frames[0].policy.night && policyPage.frames[0].policy.lightning
      && !policyPage.frames.some(row => row.changes.includes('environment')),
      'Scoped policy lookup retains the original weather and omits the repeated unchanged setting');
    await page.locator('#world-room').selectOption('4');
    await page.locator('#world-camera').selectOption('top');
    const lookup = page.waitForResponse(response => {
      const url = new URL(response.url());
      return url.pathname.endsWith(policyRoute) && url.searchParams.get('includeEnemyRoster') === 'true'
        && url.searchParams.get('roomId') === '4';
    });
    await page.locator('#world-policy-start').click();
    const rosterPage = await (await lookup).json();
    const results = page.locator('#world-policy-results');
    const change = policyPage.frames.find(row => row.changes.includes('phase') && row.policy.phase === 'Paused');
    const target = results.locator(`[data-frame-sequence="${change.frameSequence}"]`);
    await target.waitFor();
    check(await results.getByRole('button').count() === expected.length && (await results.innerText()).includes('暴風雨／夜晚／閃電開啟'),
      'Paused replay renders the actual weather policy and the original transition frames');
    const enemies = frames[change.frameSequence - 1].frame.enemies.filter(enemy => enemy.roomId === 4);
    const alive = enemies.filter(enemy => enemy.health > 0).length;
    check(rosterPage.roomId === 4 && rosterPage.frames.find(row => row.frameSequence === change.frameSequence)
      .enemyRoster.enemyIds.join(',') === enemies.map(enemy => enemy.id).sort().join(',')
      && (await target.locator('..').innerText()).includes(`房間 4 · 在場 ${enemies.length}／存活 ${alive}`),
      'Paused replay uses the selected room and renders the original roster and living count');
    const priorSequence = await canvas.getAttribute('data-sequence');
    await page.route(`**/world/frames/${change.frameSequence}`, async route => {
      const response = await route.fetch();
      const json = await response.json();
      json.packet.frame.enemies = enemies.length ? json.packet.frame.enemies.filter(enemy => enemy.roomId !== 4)
        : [...json.packet.frame.enemies, { id: '00000000-0000-0000-0000-000000000001', roomId: 4, health: 100 }];
      await route.fulfill({ response, json });
    }, { times: 1 });
    await target.click();
    await page.locator('#world-frame-message').filter({ hasText: '讀取快照失敗' }).waitFor();
    check(await canvas.getAttribute('data-sequence') === priorSequence
      && await page.locator('#world-camera').inputValue() === 'top',
      'A mismatched room roster leaves the displayed snapshot and camera in place');
    await target.click();
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${change.frameSequence} 格` }).waitFor();
    check(await canvas.getAttribute('data-sequence') === String(change.frameSequence)
      && await page.locator('#world-room').inputValue() === '4' && await page.locator('#world-camera').inputValue() === 'top',
      'Selecting a policy transition jumps to its original frame and retains the selected room camera');
    await page.locator('#world-policy-here').click();
    await page.locator('#world-policy-status').filter({ hasText: `已查閱第 ${change.frameSequence} 至` }).waitFor();
    check(await results.getByRole('button').first().getAttribute('data-frame-sequence') === String(change.frameSequence),
      'The current-frame policy cursor includes a transition on the selected frame');
    await results.screenshot({ path: path.join(screenshots, 'world-policy-frames.png') });
    await page.locator('#world-room').selectOption('all');
    check(await results.getByRole('button').count() === 0, 'Changing the observation room clears the prior roster results');
    await page.evaluate(() => {
      const original = window.fetch; window.restoreEnvironmentFetch = () => { window.fetch = original; };
      window.fetch = async (...args) => {
        const response = await original(...args);
        if (!String(args[0]).includes('/world/watch') || !response.ok) return response;
        let buffer = ''; const decoder = new TextDecoder(), encoder = new TextEncoder();
        const body = response.body.pipeThrough(new TransformStream({ transform(bytes, controller) {
          buffer += decoder.decode(bytes, { stream: true }); let end;
          while ((end = buffer.indexOf('\n\n')) >= 0) {
            let block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
            if (/^event: (header|status|complete)\n/.test(block)) {
              const value = JSON.parse(block.split('\ndata: ')[1]); delete value.header.environmentVersion;
              block = block.split('\ndata: ')[0] + '\ndata: ' + JSON.stringify(value);
            }
            controller.enqueue(encoder.encode(block + '\n\n'));
          }
        } }));
        return new Response(body, { status: response.status, headers: response.headers });
      };
    });
    await page.locator('#world-replay').click(); await page.waitForFunction(() => document.querySelector('#world-canvas').dataset.environmentVersion === '0');
    check(await page.locator('#world-sound').isDisabled() && await canvas.getAttribute('data-rain-count') === '0' && (await page.locator('#world-message').innerText()).includes('舊錄製'),
      'Legacy response metadata keeps old lighting and disables invented rain/audio presentation');
    await page.evaluate(() => window.restoreEnvironmentFetch());
    await page.locator('#tab-operations').click();
    check(await results.getByRole('button').count() === 0 && await page.locator('#world-policy-start').isDisabled(),
      'Leaving the replay clears the policy results and disables archived jumps');

    const changedRecording = path.join(directory, 'environment-policy-change.ndjson');
    const { stdout } = await execute('dotnet', [relay, '--recording', changedRecording, '--base-url', base, '--key-file', keys,
      '--demo-room', '4', '--seconds', '1'], { cwd: root, windowsHide: true, timeout: 30000 });
    const changed = JSON.parse(stdout);
    assert.equal(changed.complete, true);
    const changedFrames = (await fs.readFile(changedRecording, 'utf8')).trim().split('\n').map(line => JSON.parse(line))
      .filter(row => row.type === 'frame').map(row => row.payload);
    const storm = changedFrames.find(row => row.weather === 'Storm');
    assert(storm?.frame.night && storm.lightning);
    await page.locator('#tab-world').click();
    await page.locator('#world-refresh').click();
    await page.locator('#world-recording').selectOption(changed.sessionId);
    await page.locator('#world-replay').click();
    await page.waitForFunction(() => !document.querySelector('#world-policy-start').disabled);
    await page.locator('#world-room').selectOption('4');
    await page.locator('#world-camera').selectOption('top');
    const filter = page.locator('#world-policy-change');
    const policyStatus = page.locator('#world-policy-status');
    await filter.selectOption('environment');
    await page.locator('#world-policy-start').click();
    const savedStorm = results.locator(`[data-frame-sequence="${storm.sequence}"]`);
    await savedStorm.waitFor();
    check(await results.getByRole('button').count() === 1 && (await results.innerText()).includes('暴風雨／夜晚／閃電開啟'),
      'The environment filter finds the original saved storm without the initial state or phase changes');
    await results.screenshot({ path: path.join(screenshots, 'world-policy-environment-only.png') });

    const previousFrame = await canvas.getAttribute('data-sequence');
    await page.route(`**/world/frames/${storm.sequence}`, async route => {
      const response = await route.fetch();
      const json = await response.json();
      json.packet.lightning = false;
      await route.fulfill({ response, json });
    }, { times: 1 });
    await savedStorm.click();
    await page.locator('#world-frame-message').filter({ hasText: '讀取快照失敗' }).waitFor();
    check(await canvas.getAttribute('data-sequence') === previousFrame && await page.locator('#world-camera').inputValue() === 'top',
      'A frame with mismatched lightning leaves the displayed snapshot and camera unchanged');
    await savedStorm.click();
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${storm.sequence} 格` }).waitFor();
    check(await canvas.getAttribute('data-sequence') === String(storm.sequence) && await page.locator('#world-room').inputValue() === '4',
      'The matching environment frame opens in the original selected room');

    await filter.selectOption('phase');
    check(await results.getByRole('button').count() === 0 && await page.locator('#world-policy-next').isDisabled(),
      'Changing the policy kind clears the previous results and cursor');
    await page.route('**/world/policy-frames?*change=phase', async route => {
      const response = await route.fetch();
      const json = await response.json();
      json.change = 'environment';
      await route.fulfill({ response, json });
    }, { times: 1 });
    await page.locator('#world-policy-start').click();
    await policyStatus.filter({ hasText: '無法查閱設定切換' }).waitFor();
    check(await results.getByRole('button').count() === 0, 'The browser refuses a policy page for a different requested kind');
    await page.locator('#world-policy-start').click();
    await results.getByRole('button').last().waitFor();
    check(await results.getByRole('button').count() === 3 && (await results.getByRole('button').allTextContents()).every(text => text.includes('場次階段')),
      'The phase filter independently returns the original Begin, Pause and End transitions');
  } finally {
    if (child.exitCode === null && child.signalCode === null) { child.kill(); await finished; }
  }
};
