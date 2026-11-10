const assert = require('node:assert/strict');
const { createHash, X509Certificate } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const [httpsOrigin, httpOrigin, leafPath, output] = process.argv.slice(2);
const keys = JSON.parse(process.env.VR_COMMAND_OPERATOR_BROWSER_KEYS);
delete process.env.VR_COMMAND_OPERATOR_BROWSER_KEYS;
const roles = ['master', 'room1', 'room2', 'room3', 'room4', 'room5'];
const verifyRoute = '**/api/operator-network/verify';
const file = (name, value) => ({ name, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(value)) });

async function main() {
  const certificate = new X509Certificate(await fs.readFile(leafPath));
  const pin = createHash('sha256').update(certificate.publicKey.export({ type: 'spki', format: 'der' })).digest('base64');
  const browser = await chromium.launch({ args: [`--ignore-certificate-errors-spki-list=${pin}`, '--no-proxy-server'] });
  const context = await browser.newContext({ viewport: { width: 390, height: 850 } });
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  const findings = [], errors = [];
  page.on('pageerror', error => errors.push(error.name));
  function check(condition, description) {
    assert.ok(condition, description);
    findings.push(description);
    console.log('PASS: ' + description);
  }
  async function login(origin, role) {
    await page.goto(origin + '/console/');
    await page.locator('#login-key').fill(keys[role]);
    await page.locator('#login-form button').click();
    await page.locator('#rooms .room-card').first().waitFor();
  }
  const panel = page.locator('#operator-network'), status = page.locator('#operator-network-status');
  const challengeInput = page.locator('#operator-network-challenge'), issue = page.locator('#operator-network-issue');
  const inventoryInput = page.locator('#operator-network-inventory'), receiptsInput = page.locator('#operator-network-receipts');
  const verify = page.locator('#operator-network-verify'), result = page.locator('#operator-network-result > li');
  async function open() { await panel.locator('summary').click(); }
  async function waitStatus(phrase) { await status.filter({ hasText: phrase }).waitFor(); }
  let complete = false;
  try {
    await login(httpOrigin, 'master');
    check(await panel.count() === 1 && await panel.isHidden(), 'Workstation controls are hidden on the actual local HTTP listener');

    await login(httpsOrigin, 'master');
    await open();
    check(await page.evaluate(() => window.isSecureContext) && await issue.isDisabled() && await verify.isDisabled(),
      'Actual HTTPS opens the workstation controls with no challenge or files selected');
    await page.locator('#operator-network-generate').click();
    const challenge = await challengeInput.inputValue();
    check(/^[a-f0-9-]{36}$/.test(challenge) && await issue.isEnabled() && await verify.isDisabled(),
      'Master generates a challenge and can request only its own witness without files');

    const witnessFiles = [];
    const venue = new URL(httpsOrigin);
    for (const [index, role] of roles.entries()) {
      if (index) {
        await login(httpsOrigin, role);
        await open();
        assert.ok(await page.locator('#operator-network-master').isHidden());
        assert.ok(await page.locator('#operator-network-generate').isHidden());
        await challengeInput.fill(challenge);
      }
      const response = page.waitForResponse(value => value.url().endsWith('/operator-network/witness?challenge=' + challenge));
      const download = page.waitForEvent('download');
      await issue.click();
      const actual = await response;
      const receipt = await download;
      assert.equal(actual.status(), 200);
      assert.equal(actual.headers()['cache-control'], 'no-store');
      assert.equal(receipt.suggestedFilename(), `vr-workstation-${role}-${challenge}.json`);
      const bytes = await fs.readFile(await receipt.path());
      const value = JSON.parse(bytes);
      check(JSON.stringify(value) === JSON.stringify(await actual.json()) && value.workstation === index && value.challenge === challenge
        && value.source === venue.hostname && value.listener === venue.hostname && value.port === Number(venue.port)
        && !Object.values(keys).some(key => bytes.includes(key)), `Actual ${role} browser downloads only its signed role and the real same-PC TCP source`);
      witnessFiles.push(file(role + '.json', value));
    }
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Room workstation controls fit a 390-pixel viewport');

    await page.locator('#logout').click();
    check(await panel.isHidden() && await challengeInput.inputValue() === '' && await result.count() === 0,
      'Logout clears the challenge and previous workstation view');
    await login(httpsOrigin, 'master');
    await open();
    await challengeInput.fill(challenge);
    const inventory = { masterAddress: venue.hostname, roomAddresses: ['10.211.54.11', '10.211.54.12', '10.211.54.13', '10.211.54.14', '10.211.54.15'] };
    await inventoryInput.setInputFiles(file('inventory.json', inventory));
    let posts = 0;
    page.on('request', request => { if (request.url().endsWith('/operator-network/verify')) posts++; });
    await receiptsInput.setInputFiles([...witnessFiles.slice(0, 5), witnessFiles[0]]);
    await verify.click();
    await waitStatus('每檔上限');
    check(posts === 0 && await result.count() === 0, 'Duplicate roles are rejected locally before submitting a workstation bundle');

    const mixed = [...witnessFiles.slice(0, 5), file('cli-room5.json', {
      schemaVersion: 1, complete: true, networkWitness: JSON.parse(witnessFiles[5].buffer), ignored: 'local-only fixture'
    })].reverse();
    await receiptsInput.setInputFiles(mixed);
    const rejected = page.waitForResponse(value => value.url().endsWith('/operator-network/verify'));
    await verify.click();
    const failure = await rejected;
    await waitStatus('管理服務未確認');
    const request = failure.request().postDataJSON();
    check(failure.status() === 400 && posts === 1 && await result.count() === 0
      && request.witnesses.every((witness, index) => JSON.stringify(witness) === JSON.stringify(JSON.parse(witnessFiles[index].buffer)))
      && !failure.request().postData().includes('local-only fixture'), 'Shuffled browser and CLI-format receipts submit only signed fields and fail the real same-PC source check');

    const expected = [inventory.masterAddress, ...inventory.roomAddresses];
    const reply = { challenge, listener: venue.hostname, port: Number(venue.port), workstationAddresses: expected };
    const synthetic = witnessFiles.map((entry, index) => file(entry.name, { ...JSON.parse(entry.buffer), source: expected[index] }));
    await receiptsInput.setInputFiles(synthetic);
    const altered = route => route.fulfill({ json: { ...reply, workstationAddresses: [...expected].reverse() } });
    await page.route(verifyRoute, altered);
    await verify.click();
    await waitStatus('管理服務未確認');
    check(await result.count() === 0, 'An altered success response cannot display the wrong workstation addresses');
    await page.unroute(verifyRoute, altered);

    const accepted = route => route.fulfill({ json: reply });
    await page.route(verifyRoute, accepted);
    await verify.click();
    await waitStatus('本輪已核對六台');
    check((await result.allTextContents()).map(line => line.split(' · ')[1]).join(',') === expected.join(','),
      'An explicitly simulated successful response renders the master and five rooms in inventory order');
    await panel.screenshot({ path: path.join(output, 'workstation-browser-synthetic-success.png') });
    await page.unroute(verifyRoute, accepted);

    let captured, release;
    const started = new Promise(resolve => { captured = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    const held = async route => { captured(); await gate; await route.fulfill({ json: reply }); };
    await page.route(verifyRoute, held);
    try {
      await verify.click();
      await started;
      await page.locator('#tab-missions').click();
      await page.locator('#tab-operations').click();
      await open();
      const response = page.waitForResponse(value => value.url().endsWith('/operator-network/verify'));
      release();
      const delivered = await response;
      assert.equal(delivered.status(), 200);
      await delivered.finished();
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
      check(await result.count() === 0 && await status.innerText() === '' && await verify.isDisabled()
        && await challengeInput.inputValue() === '' && await receiptsInput.evaluate(input => input.files.length) === 0,
        'Leaving the operations tab clears local files and ignores a delivered old verification');
    } finally {
      release();
      await page.unroute(verifyRoute, held);
    }
    check(errors.length === 0, 'Workstation workflow has no uncaught browser errors');
    complete = true;
  } finally {
    await browser.close();
    await fs.writeFile(path.join(output, 'workstation-browser-checks.json'), JSON.stringify({ complete, findings,
      scope: 'Packaged HTTPS on one Windows PC. Six actual witness downloads and real same-PC rejection. Positive verification UI uses synthetic receipts and response.' }, null, 2));
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
