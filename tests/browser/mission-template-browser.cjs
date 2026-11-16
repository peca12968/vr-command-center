const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomBytes, randomUUID } = require('node:crypto');

module.exports = async function missionTemplateBrowser({ context, api, tokens, directory, root, base, screenshots, check, captureErrors, availablePort, dotnet }) {
  const definition = { name: '  雨夜掩體範本  ', briefing: '第一行\r\n第二行 <掩體>\r\n', durationSeconds: 120,
    environment: { mode: 'VR', weather: 'Rain', timeOfDay: 'Night', lightning: true },
    enemies: { count: 2, behavior: 'Patrol', autoAttack: false },
    props: [{ assetId: 'sandbag', position: { x: 3.5, y: 0, z: 2 }, yawDegrees: 45 },
      { assetId: 'barrel', position: { x: -2.25, y: 0, z: 1.25 }, yawDegrees: 15 }] };
  const original = await api('/missions', 'POST', definition, 'Master', 201);
  const newer = await api(`/missions/${original.id}/revisions`, 'POST',
    { ...definition, name: '較新的任務版本', durationSeconds: 240 }, 'Master', 201, undefined, randomUUID());
  const format = 'vr-command-mission-template';
  const source = await context.newPage();
  captureErrors(source);
  const sourceUrl = `${base}/api/missions/${original.id}/template`;
  let target, service, exit;
  async function login(page, origin, key) {
    await page.bringToFront();
    await page.goto(origin + '/console/');
    await page.locator('#login-key').fill(key);
    await page.locator('#login-form button').click();
    await page.locator('#tab-missions').click();
  }
  const ready = page => page.waitForFunction(() => !document.querySelector('#mission-fields').disabled, null, { polling: 50 });
  try {
    await login(source, base, tokens.Master);
    await source.locator('#edit-mission').selectOption(newer.id);
    await source.locator('#load-mission').click();
    await source.locator('#mission-version').selectOption(original.id);
    await source.locator('#draft-name').fill('另一份未儲存草稿');
    const downloadStarted = source.waitForEvent('download');
    await source.locator('#export-mission-template').click();
    const download = await downloadStarted;
    const file = path.join(screenshots, 'mission-template-original.json');
    await download.saveAs(file);
    const bytes = await fs.readFile(file);
    check(download.suggestedFilename() === `vr-mission-template-${original.id}.json`
      && JSON.stringify(JSON.parse(bytes).definition) === JSON.stringify(original.definition)
      && (await source.locator('#draft-name').inputValue()) === '另一份未儲存草稿',
      'The browser downloads the selected historical version and preserves the current unsaved draft');
    assert.deepEqual(Object.keys(JSON.parse(bytes)).sort(), ['definition', 'format', 'version']);
    assert.equal(JSON.parse(bytes).format, format);
    const deniedExport = await fetch(sourceUrl, { headers: { Authorization: 'Bearer ' + tokens.Room1 } });
    check(deniedExport.status === 403 && !bytes.includes(original.id) && !Object.values(tokens).some(key => bytes.includes(key)),
      'Template export is Master-only and the actual file omits stored identities and credentials');

    const destination = 'http://127.0.0.1:' + await availablePort();
    const master = randomBytes(32).toString('hex'), room = randomBytes(32).toString('hex');
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toLowerCase().startsWith('operatorkeys__')
      && !['operatorkeyfile', 'playerticketsigningkey', 'controlpipetoken'].includes(key.toLowerCase())));
    Object.assign(env, { DataDirectory: path.join(directory, 'template-target-missions'),
      SessionDataDirectory: path.join(directory, 'template-target-sessions'),
      OperatorKeys__Master: master, OperatorKeys__Room1: room, Logging__LogLevel__Default: 'Warning' });
    const dll = process.env.VR_COMMAND_API_DLL || path.join(root, 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll');
    service = spawn(dotnet, [dll, '--urls', destination], { cwd: root, env, windowsHide: true, stdio: 'ignore' });
    exit = new Promise(resolve => { service.once('exit', resolve); service.once('error', resolve); });
    for (let attempt = 0; ; attempt++) {
      try { if ((await fetch(destination + '/health')).ok) break; } catch { /* Wait for this isolated API. */ }
      if (attempt >= 100 || service.exitCode !== null) throw new Error('Template destination API did not start');
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    async function request(route, method = 'GET', body, key = master) {
      return fetch(destination + '/api' + route, { method, headers: { Authorization: 'Bearer ' + key, 'Content-Type': 'application/octet-stream' },
        body: Buffer.isBuffer(body) || body === undefined ? body : JSON.stringify(body) });
    }
    const read = async route => {
      const response = await request(route);
      assert.equal(response.status, 200);
      return response.json();
    };
    const checkFile = '/mission-templates/check-file', envelope = JSON.parse(bytes);
    const missing = structuredClone(envelope);
    delete missing.definition.environment.lightning;
    const invalidFiles = [Buffer.from(bytes.toString('utf8').replace('"version": 1', '"version": 1, "version": 1')),
      missing, { ...envelope, version: 2 }, { ...envelope, ticket: 'unrecognized field' },
      { ...envelope, definition: { ...definition, durationSeconds: 59 } },
      { ...envelope, definition: { ...definition, enemies: { ...definition.enemies, behavior: 0 } } },
      Buffer.alloc(512 * 1024 + 1, 0x20)];
    for (const invalid of invalidFiles) assert.equal((await request(checkFile, 'POST', invalid)).status, 400);
    assert.equal((await request(checkFile, 'POST', bytes, room)).status, 403);
    check((await read('/mission-library')).length === 0 && (await read('/sessions')).length === 0,
      'The destination rejects duplicate, incomplete, unknown, invalid, oversized and Room uploads without creating records');

    target = await context.newPage();
    captureErrors(target);
    await login(target, destination, master);
    const input = target.locator('#mission-template-file'), inspect = target.locator('#check-mission-template');
    const apply = target.locator('#use-mission-template'), preview = target.locator('#mission-template-status');
    await target.locator('#draft-name').fill('目的端未儲存草稿');
    const portableFile = { name: 'mission-template.json', mimeType: 'application/json',
      buffer: Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), bytes]) };
    await input.setInputFiles(portableFile);
    await target.route('**/api/mission-templates/check-file',
      route => route.fulfill({ json: { format, version: 1, definition: {} } }), { times: 1 });
    await inspect.click();
    await target.locator('#notice.error').waitFor();
    await ready(target);
    check(await apply.isDisabled() && (await target.locator('#draft-name').inputValue()) === '目的端未儲存草稿',
      'An incomplete success response cannot offer a template or replace the current draft');
    let release, requested;
    const gate = new Promise(resolve => { release = resolve; }), observed = new Promise(resolve => { requested = resolve; });
    await target.route('**/api/mission-templates/check-file', async route => {
      const response = await route.fetch();
      requested();
      await gate;
      await route.fulfill({ response });
    }, { times: 1 });
    try {
      await inspect.click(); await observed;
      await target.locator('#tab-operations').click();
      await target.locator('#tab-missions').click();
      const delivered = target.waitForResponse('**/api/mission-templates/check-file');
      release(); await delivered; await ready(target);
      check(await apply.isDisabled() && (await preview.innerText()) === '',
        'Leaving the editor invalidates an in-flight template preview even when the editor is reopened before it returns');
    } finally { release(); }
    await input.setInputFiles(portableFile); await inspect.click();
    await preview.filter({ hasText: '120 秒' }).waitFor();
    await ready(target);
    target.once('dialog', dialog => dialog.dismiss());
    await apply.click();
    check((await target.locator('#draft-name').inputValue()) === '目的端未儲存草稿'
      && (await read('/mission-library')).length === 0, 'Preview and cancel preserve the existing draft and keep the new library empty');
    await target.screenshot({ path: path.join(screenshots, 'mission-template-preview.png'), fullPage: true });
    target.once('dialog', dialog => dialog.accept());
    await apply.click();
    check((await target.locator('#draft-name').inputValue()) === definition.name && await target.locator('#prop-layer > g').count() === 2
      && await target.locator('#save-revision').isDisabled() && (await read('/mission-library')).length === 0,
      'Applying a checked file loads the exact fields and objects as a separate unsaved draft');
    await target.locator('#draft-duration').fill('180');
    await target.locator('#prop-x').fill('4.25'); await target.locator('#prop-x').blur();
    const draftExpected = structuredClone(original.definition);
    draftExpected.durationSeconds = 180;
    draftExpected.props[0].position.x = 4.25;
    const draftStarted = target.waitForEvent('download');
    await target.locator('#export-draft-template').click();
    const draftDownload = await draftStarted;
    const draftPath = path.join(screenshots, 'mission-template-draft.json');
    await draftDownload.saveAs(draftPath);
    const draftBytes = await fs.readFile(draftPath);
    const draftFile = JSON.parse(draftBytes);
    check(draftDownload.suggestedFilename() === 'vr-mission-draft.json' && draftFile.format === format && draftFile.version === 1
      && JSON.stringify(draftFile.definition) === JSON.stringify(draftExpected)
      && Object.keys(draftFile).length === 3 && (await read('/mission-library')).length === 0,
      'The local backup preserves draft geometry, changed duration and original text without saving a version');
    await target.locator('#draft-name').fill('準備取回備份');
    await input.setInputFiles({ name: draftDownload.suggestedFilename(), mimeType: 'application/json', buffer: draftBytes });
    await inspect.click(); await preview.filter({ hasText: '180 秒' }).waitFor(); await ready(target);
    target.once('dialog', dialog => dialog.accept()); await apply.click();
    check(await target.locator('#prop-x').inputValue() === '4.25' && await target.locator('#draft-duration').inputValue() === '180'
      && await target.locator('#draft-name').inputValue() === draftExpected.name && (await read('/mission-library')).length === 0,
      'The existing import route restores the downloaded draft and leaves the library untouched');
    await target.locator('#mission-form button[type=submit]').click();
    await target.waitForFunction(() => document.querySelector('#draft-status').textContent.startsWith('已儲存'), null, { polling: 50 });
    const [saved] = await read('/mission-library');
    check(saved.mission.id !== original.id && saved.number === 1 && saved.seriesId === saved.mission.id
      && JSON.stringify(saved.mission.definition) === JSON.stringify(draftExpected),
      'Explicit save creates a new series in the other service and preserves the original text and full definition');
    await target.locator('#tab-operations').click();
    await target.locator('#launch-mode').selectOption('IndependentSet');
    await target.locator('#create-session-form button').click();
    await target.locator('#launch-independent-receipt').waitFor();
    const sessions = (await read('/sessions')).sort((a, b) => a.roomIds[0] - b.roomIds[0]);
    check(sessions.length === 5 && sessions.every((session, index) =>
      session.roomIds[0] === index + 1 && session.roomIds.length === 1 && session.mission.id === saved.mission.id
      && JSON.stringify(session.mission.definition) === JSON.stringify(draftExpected)),
      'All five destination rooms prepare the imported saved definition through the ordinary operator UI');
    for (const session of sessions) {
      const result = await fetch(`${destination}/api/sessions/${session.id}/commands`, {
        method: 'POST', headers: { Authorization: 'Bearer ' + master, 'Content-Type': 'application/json' },
        body: JSON.stringify({ commandId: randomUUID(), action: 'End' })
      });
      assert.equal(result.status, 200);
    }
    check((await read('/sessions')).length === 0 && JSON.stringify((await api('/missions/' + original.id)).definition) === JSON.stringify(original.definition),
      'Target cleanup frees the five rooms and the original saved source remains intact');
    const maximum = await api('/missions', 'POST', { ...definition, name: '測'.repeat(100), briefing: '界'.repeat(10000),
      props: Array.from({ length: 500 }, () => ({ assetId: '箱'.repeat(100),
        position: { x: 3.4e38, y: -3.4e38, z: 3.4e38 }, yawDegrees: -3.4e38 })) }, 'Master', 201);
    const maxFile = Buffer.from(await (await fetch(`${base}/api/missions/${maximum.id}/template`, {
      headers: { Authorization: 'Bearer ' + tokens.Master }
    })).arrayBuffer());
    const maxChecked = await request(checkFile, 'POST', maxFile);
    check(maxFile.length < 512 * 1024 && maxChecked.status === 200
      && JSON.stringify((await maxChecked.json()).definition) === JSON.stringify(maximum.definition),
      'The file limit permits a complete export at the supported text and object counts');
  } finally {
    if (target) await target.close();
    await source.close();
    if (service && service.exitCode === null && service.signalCode === null) service.kill();
    if (exit) await exit;
  }
};
