const path = require('node:path');

// Use shipped controls and actual pointer input; never access a scene global.
module.exports = async function groundControls({ page, check, screenshots, room = 2 }) {
  const canvas = page.locator('#world-canvas');
  const field = name => page.locator('#world-camera-' + name);
  const names = ['x', 'y', 'z', 'azimuth', 'elevation', 'distance'];
  const origin = (room - 3) * 14;
  await page.locator('#world-camera-read').click();
  const original = await Promise.all(names.map(name => field(name).inputValue()));
  async function apply(values) {
    for (const [index, name] of names.entries()) await field(name).fill(String(values[index]));
    await page.locator('#world-camera-apply').click();
  }
  async function locate() {
    await canvas.scrollIntoViewIfNeeded(); const b = await canvas.boundingBox();
    await page.mouse.dblclick(b.x + b.width * .6, b.y + b.height * .5);
  }
  const mutations = [], record = request => {
    if (request.url().includes('/api/') && !['GET', 'HEAD'].includes(request.method())) mutations.push(request.method());
  };
  page.on('request', record);
  try {
    await apply([origin, .8, 0, 0, 80, 12]);
    await field('x').fill(String(origin + .25));
    const before = await canvas.getAttribute('data-camera');
    await locate();
    check(await canvas.getAttribute('data-camera') !== before && await page.locator('#world-camera').inputValue() === 'free'
      && await field('x').inputValue() === String(origin + .25), 'Double-clicking a real room relocates the observer without applying or overwriting the numeric draft');
    await page.locator('#world-camera-read').click();
    const values = await Promise.all(names.map(async name => Number(await field(name).inputValue())));
    check(values[0] < origin - .1 && values[0] >= origin - 6 && Math.abs(values[2]) <= 6 && values[1] === .8
      && Math.abs(values[3]) < 1e-9 && Math.abs(values[4] - 80) < 1e-9 && values[5] === 12,
      'Ground projection uses the room world origin and retains the current camera angle and distance');
    await page.screenshot({ path: path.join(screenshots, 'world-camera-ground.png'), fullPage: true });
    await page.locator('#world-camera').selectOption('follow');
    await locate();
    check(await page.locator('#world-camera').inputValue() === 'free', 'Locating a room floor explicitly releases follow mode');
    await apply([100, .8, 0, 0, 80, 12]);
    const outside = await canvas.getAttribute('data-camera');
    await locate();
    check(await canvas.getAttribute('data-camera') === outside, 'Double-clicking outside recorded rooms leaves the camera unchanged');
    check(mutations.length === 0, 'Floor relocation is a local observer operation and sends no management writes');
  } finally {
    page.off('request', record); await apply(original);
  }
};
