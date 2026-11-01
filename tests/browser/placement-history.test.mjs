import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/placement-history.js', import.meta.url), 'utf8');
const { placementHistory } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const state = (x = 0, prop = 0) => ({ props: [{ assetId: '沙包', position: { x, y: 0, z: 2 }, yawDegrees: 45 }], prop });

test('Undo and redo restore exact placement and selection without retaining caller references', () => {
  const history = placementHistory(), a = state(), b = state(3, -1);
  history.record(a, b); a.props[0].position.x = 99; b.props.length = 0;
  const original = history.undo(state(3)); assert.deepEqual(original, state()); original.props[0].yawDegrees = 0;
  assert.deepEqual(history.redo(state()), state(3, -1)); assert.deepEqual(history.undo(state(3)), state());
});
test('A new edit after undo invalidates redo; selection-only and no-op gestures retain redo', () => {
  const history = placementHistory(); history.record(state(), state(1)); history.undo(state(1));
  history.record(state(), state(0, -1)); assert.equal(history.status().redo, 1);
  history.record(state(), state(2)); assert.equal(history.status().redo, 0); assert.deepEqual(history.undo(state(2)), state());
});
test('History remains bounded across undo and redo, evicting the oldest whole edits', () => {
  const history = placementHistory({ maxEntries: 2 });
  for (let i = 0; i < 4; i++) history.record(state(i), state(i + 1));
  assert.deepEqual(history.undo(state(4)), state(3)); assert.deepEqual(history.undo(state(3)), state(2));
  assert.equal(history.undo(state(2)), null); assert.equal(history.status().redo, 2);
  history.redo(state(2)); assert.equal(history.status().undo, 1);
});
test('UTF8 snapshot budget includes both directions and rejects an oversized edit without stale redo', () => {
  const sample = placementHistory(); sample.record(state(), state(1)); const bytes = sample.status().bytes;
  const history = placementHistory({ maxBytes: bytes }); history.record(state(), state(1)); history.record(state(1), state(2));
  assert.equal(history.status().undo, 1); assert.ok(history.status().bytes <= bytes);
  history.undo(state(2)); const large = state(2); large.props[0].assetId = '軍'.repeat(bytes);
  history.record(state(1), large); assert.deepEqual(history.status(), { undo: 0, redo: 0, bytes: 0 });
});
test('A different document cannot receive history from the previous document', () => {
  const history = placementHistory(); history.record(state(), state(1));
  assert.equal(history.undo(state(9)), null); assert.equal(history.status().undo, 0);
  history.record(state(), state(1)); history.clear(); assert.equal(history.undo(state(1)), null);
});
test('A 500-object placement edit is fully restored, including removed middle indexes', () => {
  const a = { props: Array.from({ length: 500 }, (_, i) => state(i).props[0]), prop: 250 }, b = structuredClone(a);
  b.props.splice(250, 1); b.prop = 249; const history = placementHistory(); history.record(a, b);
  assert.deepEqual(history.undo(b), a); assert.deepEqual(history.redo(a), b);
});
