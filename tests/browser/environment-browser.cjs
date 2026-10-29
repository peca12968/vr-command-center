const fs = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');

module.exports = async function environmentBrowser({ page, api, tokens, directory, root, base, screenshots, check }) {
  const keys = path.join(directory, 'environment-keys.json'), recording = path.join(directory, 'environment.ndjson');
  await fs.writeFile(keys, JSON.stringify({ OperatorKeys: tokens }));
  const relay = process.env.VR_COMMAND_WORLD_RELAY_DLL || path.join(root, 'tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll');
  const child = spawn('dotnet', [relay, '--recording', recording, '--base-url', base, '--key-file', keys, '--demo-room', '4', '--seconds', '12', '--environment-demo', 'true'], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '', error = ''; child.stdout.on('data', bytes => { output += bytes.toString(); }); child.stderr.on('data', bytes => { error += bytes.toString(); });
  const finished = new Promise(resolve => child.once('exit', code => resolve(code)));
  try {
    let info;
    for (let attempt = 0; attempt < 150; attempt++) {
      info = (await api('/world-recordings')).find(row => row.header.roomIds.includes(4) && row.acceptedSequence > 3);
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
    await page.waitForFunction(() => {
      const state = document.querySelector('#world-canvas').dataset;
      return state.rainCount === '128' && state.weatherFlash === 'false' && state.weatherSun === '0.08';
    });
    check(info.header.environmentVersion === 1 && (await page.locator('#world-message').innerText()).includes('非原始音軌') && await canvas.getAttribute('data-weather-sun') === '0.08',
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
  } finally {
    if (child.exitCode === null && child.signalCode === null) { child.kill(); await finished; }
  }
};
