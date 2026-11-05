const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

module.exports = async function alignmentBrowser({ page, api, base, tokens, screenshots, check }) {
  const request = {
    roomId: 5,
    markers: [
      { room: { x: -2, z: -2 }, tracking: { x: -1, z: -3 } },
      { room: { x: 2, z: -2 }, tracking: { x: -1, z: 1 } },
      { room: { x: -2, z: 2 }, tracking: { x: -5, z: -3 } }
    ]
  };
  const before = await api('/missions');
  const expected = await api('/room-alignment', 'POST', request);
  await api('/room-alignment', 'POST', request, 'Room1', 403);
  await api('/room-alignment', 'POST', request, 'GameServer', 403);
  await api('/room-alignment', 'POST', { ...request, markers: request.markers.slice(0, 2) }, 'Master', 400);
  const missing = structuredClone(request); delete missing.markers[0].tracking.x;
  const rejected = await fetch(base + '/api/room-alignment', { method: 'POST', body: JSON.stringify(missing),
    headers: { Authorization: 'Bearer ' + tokens.Master, 'Content-Type': 'application/json' } });
  assert.equal(rejected.status, 400);
  await rejected.arrayBuffer();
  check(expected.withinTolerance && expected.yawDegrees === 90 && expected.roomOrigin.x === 28,
    'Actual alignment API enforces Master role, requires all coordinates, and uses the canonical room origin');
  await page.locator('#alignment-room').selectOption('5');
  for (const [index, name] of ['a', 'b', 'c'].entries()) {
    for (const axis of ['x', 'z'])
      await page.locator(`#alignment-${name}-tracking-${axis}`).fill(String(request.markers[index].tracking[axis]));
  }
  const save = page.locator('#alignment-download');
  check(await save.isDisabled(), 'Alignment export starts locked until the submitted measurements are checked');
  await page.locator('#alignment-run').click();
  await page.waitForFunction(() => !document.querySelector('#alignment-download').disabled);
  check((await page.locator('#alignment-transform').innerText()).includes('旋轉 90.00°') && await page.locator('#alignment-results tr').count() === 3,
    'Operator sees the physical-to-room transform and all three measurement errors');
  const download = page.waitForEvent('download'); await save.click();
  const file = await download;
  const filename = file.suggestedFilename();
  assert.equal(filename, 'room-5-floor-alignment.json');
  const destination = path.join(screenshots, filename);
  await file.saveAs(destination);
  assert.deepEqual(JSON.parse(await fs.readFile(destination, 'utf8')), expected);
  check(true, 'The exported alignment JSON retains exactly the checked room, points, transform and tolerance');
  await page.locator('#alignment-form').scrollIntoViewIfNeeded();
  await page.locator('#alignment-form').screenshot({ path: path.join(screenshots, 'room-floor-alignment.png') });
  await page.locator('#alignment-c-tracking-x').fill('3');
  check(await save.isDisabled() && await page.locator('#alignment-details').isHidden(), 'Editing a tracking point invalidates the previously checked export immediately');
  await page.locator('#alignment-run').click();
  await page.waitForFunction(() => document.querySelector('#alignment-summary').textContent.includes('超過'));
  check(await save.isDisabled() && (await page.locator('#alignment-results tr').last().innerText()).includes('800.00'),
    'An independently mirrored C measurement reports its original error and cannot be exported');
  await page.setViewportSize({ width: 390, height: 844 });
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'The alignment form stays within the mobile viewport');
  await page.setViewportSize({ width: 1440, height: 1080 });
  await page.locator('#tab-operations').click();
  check(await page.locator('#alignment-form').isHidden(), 'Leaving the editor hides and invalidates alignment results');
  await page.locator('#tab-missions').click();
  assert.deepEqual(await api('/missions'), before);
  check(await save.isDisabled(), 'Alignment checks and export preserve the mission catalog');
};
