const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const [descriptor, output] = process.argv.slice(2);
  const { base, masterKey, batch } = JSON.parse(await fs.readFile(descriptor, 'utf8'));
  const original = batch.sessions.flatMap(session => session.roomIds.map(room => ({ room, ...session })))
    .sort((a, b) => a.room - b.room);
  assert.deepEqual(original.map(row => row.room), [1, 2, 3, 4, 5]);
  assert.equal(batch.behavior, 'Advance');
  assert.equal(batch.autoAttack, false);
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  let evidence;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.name));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(masterKey);
    await page.locator('#login-form button').click();
    const panel = page.locator('#venue-enemy-batch');
    await page.waitForFunction(() => document.querySelector('#venue-enemy-batch-summary').textContent.includes('5 / 5 房已確認'),
      null, { polling: 100 });
    assert.match(await panel.locator('p').innerText(), /推進 · 自動攻擊關閉/);
    const rendered = await panel.locator('[data-enemy-batch-state="Applied"]').allTextContents();
    assert.equal(rendered.length, 5);
    for (const [index, row] of original.entries()) {
      assert.ok(rendered[index].includes(`房間 ${row.room} · 原命令 ${row.appliedAtSequence} · 全場目標 ${row.targetCount} 名`));
    }
    await panel.screenshot({ path: path.join(output, 'batch.png') });
    const room = original[3], route = `/api/sessions/${room.sessionId}/world`;
    const watch = page.waitForResponse(response => new URL(response.url()).pathname === route + '/watch');
    await panel.locator('[data-enemy-batch-room="4"]').getByRole('button', { name: '檢視敵軍快照' }).click();
    const response = await watch;
    assert.equal(response.status(), 200);
    const query = new URL(response.url()).searchParams;
    assert.equal(query.get('mode'), 'replay');
    assert.equal(query.get('throughFrame'), query.get('fromFrame'));
    const frame = Number(query.get('fromFrame'));
    await page.locator('#world-frame-message').filter({ hasText: `已停在第 ${frame} 格的敵軍快照` }).waitFor();
    assert.equal(await page.locator('#world-room').inputValue(), '4');
    assert.equal(await page.locator('#world-camera').inputValue(), 'top');
    const saved = await page.request.get(base + route + '/frames/' + frame, { headers: { Authorization: 'Bearer ' + masterKey } });
    assert.equal(saved.status(), 200);
    const { packet } = await saved.json();
    assert.ok(packet.observedSequence >= room.appliedAtSequence);
    assert.equal(packet.frame.behavior, batch.behavior);
    assert.equal(packet.frame.autoAttack, batch.autoAttack);
    assert.deepEqual(errors, []);
    await page.locator('#world-viewport').screenshot({ path: path.join(output, 'room-4-witness.png') });
    evidence = { complete: true, requestId: batch.requestId, rooms: original.map(({ room, sessionId, appliedAtSequence }) => ({ room, sessionId, appliedAtSequence })),
      witness: { room: room.room, sessionId: room.sessionId, frame, observedSequence: packet.observedSequence } };
  } finally { await browser.close(); }
  await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify(evidence, null, 2), { flag: 'wx' });
}

main().catch(error => { console.error(error.name + ': ' + error.message); process.exitCode = 1; });
