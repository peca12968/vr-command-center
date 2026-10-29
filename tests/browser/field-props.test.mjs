import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { FIELD_PROPS } from '../../src/VrCommand.Api/wwwroot/console/field-props-data.js';
import { fieldPropFactory, supportedAssets } from '../../src/VrCommand.Api/wwwroot/console/field-props.js';

test('Unity and the observer use identical original geometry data', async () => {
  const unity = JSON.parse(await readFile(new URL('../../clients/unity/Assets/VrCommand/Resources/VrCommand/field-props-v1.json', import.meta.url), 'utf8'));
  assert.deepEqual(unity, FIELD_PROPS);
  assert.equal(unity.assetSet, 'field-props-v1'); assert.equal(unity.origin, 'feet'); assert.equal(unity.units, 'metres');
});
test('field props fit the old gameplay envelopes without changing cover dimensions', () => {
  const make = fieldPropFactory();
  for (const [kind, size] of [['Sandbag', [2, .9, .7]], ['Barrel', [.7, 1.2, .7]]]) {
    const mesh = make(kind), box = mesh.geometry.boundingBox;
    const actual = [box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z];
    actual.forEach((n,i) => assert.ok(Math.abs(n - size[i]) < .0001));
    assert.ok(Math.abs(box.min.y) < .0001); assert.ok(mesh.geometry.index.count / 3 <= 400);
    assert.equal(mesh.geometry.getAttribute('position').count, mesh.geometry.getAttribute('color').count);
    mesh.geometry.dispose(); mesh.material.dispose();
  }
});
test('repeated views share geometry and material instead of allocating per prop', () => {
  const make = fieldPropFactory(), a = make('Barrel'), b = make('Barrel'), bags = make('Sandbag');
  assert.equal(a.geometry, b.geometry); assert.equal(a.material, bags.material); assert.notEqual(a.geometry, bags.geometry);
  assert.throws(() => make('UntrustedAssetPath'), /不支援/);
  a.geometry.dispose(); bags.geometry.dispose(); a.material.dispose();
});
test('only explicit supported profiles can select the new appearance', () => {
  for (const value of ['primitives-v1', 'field-props-v1']) assert.ok(supportedAssets(value));
  for (const value of [null, '', 'field-props-v99', '../field-props-v1', undefined]) assert.equal(supportedAssets(value), false);
});
