const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, output] = process.argv.slice(2);
  const { base, key, sessionId, roomId, seat, linked, action } = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.ok(['Pause', 'Resume'].includes(action));
  const resuming = action === 'Resume';
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(key);
    await page.locator('#login-form button').click();
    const control = resuming ? 'data-room-vr-resume' : 'data-room-vr-participation-pause';
    const button = page.locator(`[${control}="${roomId}"]`);
    const status = page.locator(`[data-room-vr-pause="${roomId}"]`);
    if (resuming) await status.filter({ hasText: '本房席位已確認' }).waitFor();
    else await page.locator(`[data-room-readiness="${roomId}"]`).filter({ hasText: `姿態待確認席位 ${seat}` }).waitFor();
    await button.waitFor();
    assert.equal(await page.locator(`[${control}]:visible`).count(), 1);
    if (resuming) {
      await page.waitForFunction(room => document.querySelector(`[data-room-vr-resume="${room}"]`)?.disabled === false, roomId);
      await button.screenshot({ path: path.join(path.dirname(output), path.basename(output, '.json') + '-ready.png') });
    }
    const response = page.waitForResponse(reply => reply.url() === base + `/api/sessions/${sessionId}/commands` && reply.request().method() === 'POST');
    const confirmed = page.waitForEvent('dialog').then(async dialog => {
      assert.match(dialog.message(), resuming ? linked ? /一起繼續合併場次/ : /繼續本房/
        : linked ? /所有房間一起暫停/ : /暫停本房檢查席位/);
      await dialog.accept();
    });
    await button.click(); await confirmed;
    const accepted = await response;
    const request = accepted.request().postDataJSON(), receipt = await accepted.json();
    assert.equal(accepted.status(), 200);
    assert.equal(request.action, action);
    if (!resuming) assert.equal(request.vrParticipationRoomId, roomId);
    assert.equal(receipt.commandId, request.commandId);
    assert.equal(receipt.session.id, sessionId);
    assert.equal(receipt.session.state, resuming ? 'Running' : 'Paused');
    assert.equal(receipt.appliedAtSequence, request.expectedSequence + 1);
    if (resuming) {
      await status.waitFor({ state: 'hidden' });
      await page.locator(`[data-room-readiness="${roomId}"][data-source-state="Fresh"]`)
        .filter({ hasText: '5 / 5 姿態有效' }).waitFor();
    } else {
      await status.filter({ hasText: 'VR 暫停已套用' }).waitFor();
      assert.match(await status.textContent(), new RegExp(`房間 ${roomId} 姿態中斷`));
      assert.equal(await page.locator('[data-room-vr-pause]:visible').count(), linked ? 5 : 1);
    }
    assert.deepEqual(errors, []);
    await page.locator('#rooms').screenshot({ path: path.join(path.dirname(output), path.basename(output, '.json') + '.png') });
    await fs.writeFile(output, JSON.stringify({ sessionId, roomId, seat, appliedAtSequence: receipt.appliedAtSequence }, null, 2), { flag: 'wx' });
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.name + ': native VR participation pause failed'); process.exitCode = 1; });
