const assert = require('node:assert/strict');

module.exports = async function missionPlacementPrecision({ context, api, tokens, base }) {
  const page = await context.newPage();
  const input = id => page.locator('#' + id);
  const field = async (id, number) => {
    await input(id).fill(String(number));
    await input(id).blur();
  };
  const compare = async () => {
    await input('compare-version').click();
    await input('mission-comparison').waitFor();
    return input('mission-comparison-rows').locator('tr').count();
  };
  try {
    await page.goto(base + '/console/');
    await input('login-key').fill(tokens.Master);
    await page.locator('#login-form button').click();
    await input('tab-missions').click();
    await input('draft-name').fill('小數座標回讀');
    await input('add-barrel').click();
    const values = { x: 1.123456789123, y: 0.123456789123, z: -2.123456789123, yaw: 47.123456789123 };
    for (const [axis, value] of Object.entries(values)) await field('prop-' + axis, value);
    await page.locator('#mission-form button[type=submit]').click();
    await input('draft-status').filter({ hasText: '已儲存於' }).waitFor();
    const id = await input('mission-version').inputValue();
    const saved = (await api('/missions/' + id)).definition.props[0];
    for (const [axis, value] of Object.entries(values)) {
      const actual = axis === 'yaw' ? saved.yawDegrees : saved.position[axis];
      assert.notEqual(actual, value);
      assert.equal(Math.fround(actual), Math.fround(value));
      assert.equal(await input('prop-' + axis).inputValue(), String(value));
    }
    assert.equal(await compare(), 0, 'The just-saved geometry must compare equal at stored precision');
    // Exactly one representable Single above the stored X. A fixed epsilon would miss this change.
    const bits = new DataView(new ArrayBuffer(4));
    bits.setFloat32(0, saved.position.x);
    bits.setUint32(0, bits.getUint32(0) + 1);
    const changed = bits.getFloat32(0);
    await field('prop-x', changed);
    assert.equal(await compare(), 1);
    assert.ok((await input('mission-comparison-rows').innerText()).includes(String(changed)));
    await input('undo-prop').click();
    assert.equal(await compare(), 0);
    page.once('dialog', dialog => dialog.accept());
    await input('load-mission').click();
    await page.waitForFunction(value => document.querySelector('#prop-x').value === String(value), saved.position.x);
    for (const axis of Object.keys(values)) {
      assert.equal(await input('prop-' + axis).inputValue(), String(axis === 'yaw' ? saved.yawDegrees : saved.position[axis]));
    }
    assert.equal(await compare(), 0);
    // The elevated barrel is valid in a draft. Place it on the floor for the playable revision.
    await field('prop-y', 0);
    assert.equal(await compare(), 1);
    const map = input('layout-map');
    await field('prop-x', 9.875);
    await map.press('ArrowRight');
    assert.equal(await input('prop-x').inputValue(), '10');
    assert.equal(await input('prop-z').inputValue(), String(saved.position.z), 'Horizontal movement must preserve Z');
    const atEdge = await input('prop-history-status').textContent();
    await map.press('ArrowRight');
    assert.equal(await input('prop-history-status').textContent(), atEdge);
    await input('undo-prop').click();
    assert.equal(await input('prop-x').inputValue(), '9.875');
    await field('prop-x', 1.125);
    await map.press('ArrowLeft');
    assert.equal(await input('prop-x').inputValue(), '0.625');
    await map.press('ArrowUp');
    assert.equal(await input('prop-z').inputValue(), String(saved.position.z + 0.5));
    assert.equal(await input('prop-x').inputValue(), '0.625', 'Vertical movement must preserve X');
    await input('undo-prop').click();
    assert.equal(await input('prop-z').inputValue(), String(saved.position.z));
    await input('redo-prop').click();
    await input('add-sandbag').click();
    await field('prop-x', -2.125);
    await field('prop-z', 1.25);
    await input('prop-select').selectOption('0');
    const first = page.locator('#prop-layer [data-index="0"]');
    const second = page.locator('#prop-layer [data-index="1"]');
    await first.focus();
    await page.keyboard.press('Tab');
    assert.ok(await second.evaluate(node => node === document.activeElement));
    await page.keyboard.down('ArrowRight');
    await page.keyboard.down('ArrowRight');
    await page.keyboard.up('ArrowRight');
    assert.equal(await input('prop-select').inputValue(), '1', 'Arrow keys must move the object with keyboard focus');
    assert.equal(await input('prop-x').inputValue(), '-1.125');
    await input('undo-prop').click();
    assert.equal(await input('prop-x').inputValue(), '-2.125');
    await input('redo-prop').click();
    assert.equal(await input('prop-x').inputValue(), '-1.125');
    await input('save-revision').click();
    await page.waitForFunction(original => document.querySelector('#mission-version').value !== original
      && document.querySelector('#draft-status').textContent.startsWith('已儲存於'), id);
    const playable = await input('mission-version').inputValue();
    const [revised, moved] = (await api('/missions/' + playable)).definition.props;
    assert.deepEqual(moved, { assetId: 'sandbag', position: { x: -1.125, y: 0, z: 1.25 }, yawDegrees: 0 });
    assert.equal(Math.fround(revised.position.z), Math.fround(saved.position.z + 0.5));
    assert.deepEqual(revised, { ...saved, position: { x: 0.625, y: 0, z: revised.position.z } });
    assert.deepEqual((await api('/missions/' + id)).definition.props[0], saved);
    assert.equal(await compare(), 0);
    await input('launch-compared-version').click();
    assert.equal(await input('launch-preview').getAttribute('data-mission-id'), playable);
    return playable;
  } finally { await page.close(); }
};
