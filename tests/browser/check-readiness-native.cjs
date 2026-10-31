// Real control UI reading this fixture's actual native Unity world, without mocked readiness.
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
async function main() {
  const file = path.resolve(process.argv[2] || '');
  const directory = path.dirname(file);
  assert.equal(path.dirname(directory), path.join(root, 'artifacts', 'desktop-readiness'));
  assert.match(path.basename(directory), /^\d{8}-\d{6}-[a-f0-9]{8}$/); assert.equal(path.basename(file), 'ready.json');
  const ready = JSON.parse(await fs.readFile(file, 'utf8')), url = new URL(ready.baseUrl);
  assert.equal(ready.source, 'Simulation'); assert.equal(ready.headsets, 0); assert.equal(path.resolve(ready.directory), directory);
  assert.equal(url.hostname, '127.0.0.1'); assert.equal(url.protocol, 'http:'); assert.notEqual(url.port, '5080');
  assert.ok(!url.username && !url.password && !url.search && !url.hash && url.pathname === '/');
  const keys = JSON.parse(await fs.readFile(path.join(directory, 'keys.json'), 'utf8')).OperatorKeys;
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  let checks = 0; const findings = [];
  function check(value, message) { assert.ok(value, message); findings.push(message); checks++; console.log('PASS:', message); }
  const marker = name => fs.writeFile(path.join(directory, name + '.done'), 'Observed real native-backed control UI\n', { flag: 'wx' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } }); const errors = [];
  page.on('pageerror', error => errors.push(error.message)); page.setDefaultTimeout(20000);
  async function stage(name) {
    for (let i = 0; i < 160; i++) {
      const value = JSON.parse(await fs.readFile(path.join(directory, 'stage.json'), 'utf8'));
      if (value.stage === name) return value;
      if (value.stage === 'failed') throw Error('Native fixture failed');
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    throw Error('Native fixture did not reach ' + name);
  }
  try {
    await page.goto(ready.baseUrl + '/console/'); await page.locator('#login-key').fill(keys.Master); await page.locator('#login-form button').click();
    await page.locator('#session-select').selectOption(ready.sessionId);
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    check((await page.locator('#readiness-summary').innerText()).includes('Simulation') && (await page.locator('#roster').innerText()).includes('合成姿態'), 'Two real accepted Unity rigs appear as synthetic participation');
    await page.screenshot({ path: path.join(directory, 'readiness-connected.png'), fullPage: true }); await marker('connected-seen');
    await stage('native-peer-offline');
    await page.waitForFunction(id => document.querySelector(`[data-readiness-player="${id}"]`).textContent.includes('姿態未就緒'), ready.peerId);
    check(await page.locator('#roster .ready-player').count() === 1, 'Owned native peer exit clears only its own green state');
    await page.screenshot({ path: path.join(directory, 'readiness-disconnected.png'), fullPage: true }); await marker('disconnected-seen');
    const changed = await stage('native-readmitted');
    await page.locator('#refresh').click();
    await page.waitForFunction(({ id, admission }) => document.querySelector(`[data-readiness-player="${id}"]`)?.dataset.admission === admission, { id: ready.peerId, admission: changed.admissionId });
    check(changed.admissionId !== ready.oldAdmission && !await page.locator(`[data-readiness-player="${ready.peerId}"]`).evaluate(node => node.classList.contains('ready-player')), 'Same player ID with a replacement admission stays unready before its new process starts');
    await marker('readmitted-seen'); await stage('native-reconnected');
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    check(await page.locator(`[data-readiness-player="${ready.peerId}"]`).getAttribute('data-admission') === changed.admissionId, 'New native peer restores participation for its own new admission');
    await page.locator('[data-command=Begin]').click(); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '執行中');
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    check((await page.locator('#readiness-summary').innerText()).includes('2 / 2'), 'Running snapshot remains tied to both current admissions');
    await page.locator('[data-command=Pause]').click(); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已暫停');
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 2);
    check((await page.locator('#readiness-summary').innerText()).includes('正在接收'), 'Explicit pause retains valid pose snapshots without claiming active combat');
    await page.screenshot({ path: path.join(directory, 'readiness-paused.png'), fullPage: true });
    await page.locator('#include-ended').check();
    page.once('dialog', dialog => dialog.accept());
    await page.locator('[data-command=End]').click(); await page.waitForFunction(() => document.querySelector('#session-phase').textContent === '已結束');
    await page.waitForFunction(() => document.querySelectorAll('#roster .ready-player').length === 0 && document.querySelector('#readiness-summary').textContent.includes('場次已結束'));
    check(true, 'End immediately removes participation before requiring final world delivery');
    await page.screenshot({ path: path.join(directory, 'readiness-ended.png'), fullPage: true });
    check(errors.length === 0 && await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && !document.cookie), 'Real native-backed readiness has no script errors or persisted operator credential');
    await fs.writeFile(path.join(directory, 'browser-checks.json'), JSON.stringify({ complete: true, checks, findings, scope: 'Chromium SwiftShader control UI / actual same-host headless Unity Simulation; no headsets' }, null, 2));
    await marker('ended-seen');
  } catch (error) { await page.screenshot({ path: path.join(directory, 'readiness-failure.png'), fullPage: true }).catch(() => {}); throw error; }
  finally { await browser.close(); }
  console.log('PASS: ' + checks + ' actual native-backed readiness UI checks');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
