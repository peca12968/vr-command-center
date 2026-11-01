import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/camera-ground-target.js', import.meta.url), 'utf8');
const { cameraGroundTarget: locate } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const down = { x: 0, y: -1, z: 0 };

test('A downward perspective ray locates the actual room floor at a fixed viewing height', () => {
  assert.deepEqual(locate({ x: -16, y: 10, z: -3 }, { x: .2, y: -1, z: .4 }, [2]), { roomId: 2, target: [-14, .8, 1] });
});
test('All five world origins and inclusive room edges can be located without rounding', () => {
  for (let room = 1; room <= 5; room++) for (const offset of [-6, .125, 6]) {
    const x = (room - 3) * 14 + offset;
    assert.deepEqual(locate({ x, y: 8, z: 6 }, down, [1, 2, 3, 4, 5]), { roomId: room, target: [x, .8, 6] });
  }
});
test('Absent rooms, the gaps between rooms and outside floor bounds do not produce a target', () => {
  for (const [x, z, rooms] of [[0, 0, [2]], [7, 0, [3, 4]], [0, 6.001, [3]], [-34.001, 0, [1]], [100, 0, [1, 2, 3, 4, 5]]])
    assert.equal(locate({ x, y: 10, z }, down, rooms), null);
});
test('Parallel, upward and below-floor rays never move the observer to a behind-camera intersection', () => {
  for (const y of [0, 1]) assert.equal(locate({ x: 0, y: 10, z: 0 }, { x: 0, y, z: 0 }, [3]), null);
  assert.equal(locate({ x: 0, y: -1, z: 0 }, { x: 0, y: 1, z: 0 }, [3]), null);
});
test('Nonfinite or malformed input and overflowing intersections are rejected', () => {
  for (const value of [NaN, Infinity, '0', undefined]) {
    assert.equal(locate({ x: value, y: 10, z: 0 }, down, [3]), null);
    assert.equal(locate({ x: 0, y: 10, z: 0 }, { ...down, x: value }, [3]), null);
  }
  assert.equal(locate(null, down, [3]), null);
  assert.equal(locate({ x: 0, y: 10, z: 0 }, down, null), null);
  assert.equal(locate({ x: 0, y: 10, z: 0 }, { x: 1, y: -Number.MIN_VALUE, z: 0 }, [3]), null);
});
test('Invalid room identifiers cannot be converted into floor coordinates', () => {
  for (const room of [0, 6, '3', 3.1, NaN]) assert.equal(locate({ x: 0, y: 8, z: 0 }, down, [room]), null);
});
