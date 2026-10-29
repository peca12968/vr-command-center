const assert = require('node:assert/strict');
const path = require('node:path');

// Visible controls and real browser input only; no scene globals or injected poses.
module.exports = async function cameraControls({ page, check, screenshots }) {
  const canvas = page.locator('#world-canvas');
  const field = name => page.locator('#world-camera-' + name);
  const camera = async () => (await canvas.getAttribute('data-camera')).split(',').map(Number);
  const close = (a, b) => a.length === b.length && a.every((value, i) => Math.abs(value - b[i]) < .02);
  const mutations = [], record = request => {
    if (request.url().includes('/api/') && !['GET', 'HEAD'].includes(request.method())) mutations.push(request.method());
  };
  page.on('request', record);
  try {
    await page.locator('#world-camera-read').click();
    const x = Number(await field('x').inputValue());
    for (const [name, value] of [['x', x], ['y', 1.25], ['z', .4], ['azimuth', 45], ['elevation', 45], ['distance', 12]]) await field(name).fill(String(value));
    await page.locator('#world-camera-apply').click();
    const precise = await camera();
    check(close(precise, [x + 6, 1.25 + 12 / Math.sqrt(2), .4 - 6]) && await page.locator('#world-camera').inputValue() === 'free',
      'Numeric target, degree angles and distance place the real rendered camera at the requested world position');
    await page.locator('#world-camera-read').click();
    check(Math.abs(Number(await field('azimuth').inputValue()) - 45) < 1e-9 && Math.abs(Number(await field('elevation').inputValue()) - 45) < 1e-9,
      'Reading the current camera returns degrees and target without changing the view');
    await page.screenshot({ path: path.join(screenshots, 'world-camera-precise.png'), fullPage: true });
    const sequence = Number(await canvas.getAttribute('data-sequence'));
    await field('x').fill('23.25');
    await page.waitForFunction(before => Number(document.querySelector('#world-canvas').dataset.sequence) > before, sequence);
    check(await field('x').inputValue() === '23.25' && close(await camera(), precise), 'Incoming live frames preserve the operator camera draft and do not apply it automatically');
    for (const [name, value] of [['x', ''], ['x', '121'], ['distance', '1'], ['elevation', '0']]) {
      await page.locator('#world-camera-read').click(); await field(name).fill(value); await page.locator('#world-camera-apply').click();
      check(await page.locator('#world-camera-message').evaluate(node => node.classList.contains('replay-error')) && close(await camera(), precise),
        'Invalid camera input leaves the rendered view unchanged: ' + name + '=' + value);
    }
    await page.locator('#world-camera-read').click();
    async function changed(label, action) {
      await canvas.scrollIntoViewIfNeeded(); const before = await camera(); await action();
      const after = await camera(); check(after.every(Number.isFinite) && !close(before, after), label);
    }
    async function drag(button, shift = false) {
      const bounds = await canvas.boundingBox(); assert.ok(bounds);
      const x = bounds.x + bounds.width / 2, y = bounds.y + bounds.height / 2;
      await page.mouse.move(x, y); if (shift) await page.keyboard.down('Shift');
      try { await page.mouse.down({ button }); await page.mouse.move(x + 55, y + 25, { steps: 6 }); await page.mouse.up({ button }); }
      finally { if (shift) await page.keyboard.up('Shift'); }
    }
    await changed('Actual left drag rotates the streamed-world observer camera', () => drag('left'));
    await changed('Actual right drag pans the streamed-world observer camera', () => drag('right'));
    await changed('Shift plus left drag also pans the observer camera', () => drag('left', true));
    await changed('Wheel input zooms the rendered world camera', async () => { const b = await canvas.boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.wheel(0, 180); await page.waitForTimeout(100); });
    await changed('Focused arrow key pans the observer camera', () => canvas.press('ArrowRight'));
    await changed('Focused plus key zooms the observer camera', () => canvas.press('Shift+Equal'));
    await changed('Focused minus key zooms the observer camera', () => canvas.press('Minus'));
    check(mutations.length === 0, 'Camera edits and gestures do not send management mutations or consume player admissions');
    await page.screenshot({ path: path.join(screenshots, 'world-camera-gestures.png'), fullPage: true });
    await page.locator('#world-camera-apply').click();
    check(close(await camera(), precise), 'Reapplying the numeric draft restores its requested view after pointer gestures');
  } finally { page.off('request', record); }
};
