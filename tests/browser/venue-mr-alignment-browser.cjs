const assert = require('node:assert/strict');
const { createHash, randomUUID } = require('node:crypto');

module.exports = async function venueMrAlignmentBrowser({ context, api, tokens, base, check, captureErrors }) {
  const pending = new Set();
  const page = await context.newPage();
  captureErrors(page);
  const submit = page.locator('#mr-alignment-submit'), title = page.locator('#mr-alignment-title');
  const row = room => page.locator(`[data-begin-room="${room}"]`);
  const input = room => page.locator(`#mr-alignment-file-${room}`);
  const status = room => page.locator(`#mr-alignment-status-${room}`);
  const viewRoom = room => row(room).getByRole('button', { name: `查看房間 ${room} MR 校正` }).click();
  const sha = bytes => createHash('sha256').update(bytes).digest('hex');
  async function calibration(roomId, offset = 1) {
    const markers = [[-2, -2], [2, -2], [-2, 2]].map(([x, z]) => ({ room: { x, z }, tracking: { x: x + offset, z } }));
    const report = await api('/room-alignment', 'POST', { roomId, markers });
    return Buffer.from('\ufeff' + JSON.stringify(report, null, 2).replaceAll('\n', '\r\n') + '\r\n');
  }
  const put = (room, buffer) => input(room).setInputFiles({ name: `mr-${room}.json`, mimeType: 'application/json', buffer });
  const ready = room => status(room).filter({ hasText: '已核對，可鎖定' }).waitFor();
  async function end(id) {
    await api(`/sessions/${id}/commands`, 'POST', { action: 'End', commandId: randomUUID() });
    pending.delete(id);
  }
  try {
    assert.deepEqual(await api('/sessions'), []);
    const draft = { name: '五房 MR 校正核對', briefing: '原始房間配置', durationSeconds: 180, props: [],
      environment: { mode: 'MR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
      enemies: { count: 0, behavior: 'Hold', autoAttack: false } };
    const mr = await api('/missions', 'POST', draft, 'Master', 201);
    const vr = await api('/missions', 'POST', { ...draft, environment: { ...draft.environment, mode: 'VR' } }, 'Master', 201);
    const rooms = [1, 2, 3, 4, 5].map(roomId => ({ roomId, missionId: [2, 4].includes(roomId) ? mr.id : vr.id }));
    const { sessions } = await api('/sessions/independent-set', 'POST', { rooms }, 'Master', 201, undefined, randomUUID());
    sessions.forEach(session => pending.add(session.id));
    const second = sessions.find(session => session.roomIds[0] === 2);
    const fourth = sessions.find(session => session.roomIds[0] === 4);
    const [good, other] = await Promise.all([calibration(2), calibration(2, 2)]);
    assert.notEqual(sha(good), sha(other));
    await page.goto(base + '/console/');
    await page.locator('#login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await row(5).waitFor();
    await page.locator('#session-select').selectOption(second.id);
    await input(2).waitFor();
    const checkFilePath = base + '/api/room-alignment/check-file';
    await page.route(checkFilePath, route => route.fulfill({ status: 200, json: { roomId: 2, sha256: sha(other) } }), { times: 1 });
    await put(2, good);
    await status(2).filter({ hasText: /原始內容與核對結果不符|已核對，可鎖定/ }).waitFor();
    check(await submit.isDisabled() && (await api(`/sessions/${second.id}`)).roomAlignment == null,
      'A hash for a different valid calibration from the same room cannot enable locking');
    check((await row(1).innerText()).includes('· VR') && (await row(2).innerText()).includes('· MR · 校正檔尚未鎖定')
      && (await row(4).innerText()).includes('· MR · 校正檔尚未鎖定') && await row(1).getByRole('button', { name: /MR 校正/ }).count() === 0,
      'The mixed venue identifies both MR rooms and their missing pins before game servers start');
    await viewRoom(4);
    await page.waitForFunction(() => document.activeElement?.id === 'mr-alignment-file-4');
    check(await page.locator('#session-select').inputValue() === fourth.id, 'The venue link opens the exact independent MR room and focuses its file field');
    await viewRoom(2);
    await input(2).waitFor();
    await put(2, good);
    await ready(2);
    await viewRoom(2);
    check(await submit.isEnabled() && await input(2).evaluate(node => node.files.length === 1),
      'Reopening the original room preserves the verified raw file, including BOM and CRLF');
    const path = `/sessions/${second.id}/commands`;
    let sent;
    await page.route(base + '/api' + path, async route => {
      sent = route.request().postDataJSON();
      const original = await api(path, 'POST', sent);
      original.session.roomAlignment.room2 = sha(other);
      await route.fulfill({ status: 200, json: original });
    }, { times: 1 });
    page.once('dialog', dialog => dialog.accept());
    await submit.click();
    await page.locator('#pending-command').waitFor();
    check(sent.roomAlignment.room2 === sha(good) && await submit.isDisabled() && !(await row(2).innerText()).includes('· 已鎖定校正檔'),
      'An altered confirmation preserves the original lock command for retry');
    const retried = page.waitForResponse(response => response.url() === base + '/api' + path && response.request().method() === 'POST');
    await page.locator('#retry-command').click();
    const retry = await retried;
    assert.deepEqual(retry.request().postDataJSON(), sent);
    assert.equal((await retry.json()).duplicate, true);
    await row(2).filter({ hasText: '已鎖定校正檔' }).waitFor();
    const current = await api(`/sessions/${second.id}`);
    const events = await api(`/sessions/${second.id}/events`);
    check(current.roomAlignment.room2 === sha(good) && events.filter(event => event.payload.action === 'SetRoomAlignment').length === 1
      && (await api(`/sessions/${fourth.id}`)).roomAlignment == null, 'Retry confirms exactly one commit of the original file and leaves the other MR room unpinned');
    await viewRoom(2);
    await page.waitForFunction(() => document.activeElement?.id === 'mr-alignment-title');
    check(await input(2).isHidden() && await title.isVisible(), 'A locked room opens its read-only calibration details');
    for (const id of pending) await end(id);
    const linked = await api('/sessions', 'POST', { missionId: mr.id, roomIds: [1, 2, 3, 4, 5], mode: 'Linked' }, 'Master', 201);
    pending.add(linked.id);
    await page.locator('#refresh').click();
    await row(2).filter({ hasText: '校正檔尚未鎖定' }).waitFor();
    await viewRoom(2);
    await input(2).waitFor();
    await put(2, good);
    await ready(2);
    await viewRoom(4);
    await page.waitForFunction(() => document.activeElement?.id === 'mr-alignment-file-4');
    check(await page.locator('#session-select').inputValue() === linked.id && await input(2).evaluate(node => node.files.length === 1)
      && await submit.isDisabled(), 'Linked MR can navigate to a different room without discarding the calibration already checked for another room');
  } finally {
    for (const id of pending) await end(id);
    await page.close();
  }
};
