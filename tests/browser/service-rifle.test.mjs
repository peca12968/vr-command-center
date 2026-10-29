import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import * as THREE from '../../src/VrCommand.Api/wwwroot/console/vendor/three/three.module.js';
import { SERVICE_RIFLE } from '../../src/VrCommand.Api/wwwroot/console/service-rifle-data.js';
import { rifleGeometry, serviceRifleFactory, placeRifle } from '../../src/VrCommand.Api/wwwroot/console/service-rifle.js';

test('rifle geometry is identical to the frozen Unity resource, with finite outward faces', async () => {
  const bytes = await readFile(new URL('../../clients/unity/Assets/VrCommand/Resources/VrCommand/service-rifle-v1.json', import.meta.url));
  assert.deepEqual(JSON.parse(bytes), SERVICE_RIFLE);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), 'b054b9780b19104c6ff33a2384df15e9e4f6e2c73293297c4f70e2dd0d8eda25');
  const g = rifleGeometry(), p = g.getAttribute('position'), n = g.getAttribute('normal'), indices = g.index;
  try {
    assert.equal(indices.count / 3, 264); assert.ok(Math.abs(g.boundingBox.max.z) < .00001);
    for (let i = 0; i < indices.count; i += 3) {
      const a = new THREE.Vector3().fromBufferAttribute(p, indices.getX(i)), b = new THREE.Vector3().fromBufferAttribute(p, indices.getX(i + 1)), c = new THREE.Vector3().fromBufferAttribute(p, indices.getX(i + 2));
      assert.ok(b.sub(a).cross(c.sub(a)).dot(new THREE.Vector3().fromBufferAttribute(n, indices.getX(i))) > .0000001);
    }
  } finally { g.dispose(); }
});
test('muzzle tip, shot direction and matching recorded roll survive a room-relative view', () => {
  const pool = serviceRifleFactory(), rifle = pool.create(), room = new THREE.Group(); room.position.set(-28, 0, 0); room.add(rifle);
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(.2, .7, .4)), direction = new THREE.Vector3(0, 0, 1).applyQuaternion(q);
  const player = { muzzle: { x: -27.7, y: 1.3, z: .4 }, forward: direction, rig: { kind: 'Simulated', rightRotation: q } };
  try {
    placeRifle(rifle, player, room.position); room.updateMatrixWorld(true);
    assert.ok(rifle.localToWorld(new THREE.Vector3()).distanceTo(new THREE.Vector3(-27.7, 1.3, .4)) < .00001);
    assert.ok(rifle.quaternion.angleTo(q) < .00001); assert.deepEqual(rifle.scale.toArray(), [1, 1, 1]);
    player.rig.rightRotation = { x: 0, y: 0, z: 0, w: 1 }; placeRifle(rifle, player, room.position);
    assert.ok(new THREE.Vector3(0, 0, 1).applyQuaternion(rifle.quaternion).distanceTo(direction) < .00001);
    delete player.rig; placeRifle(rifle, player, room.position);
    assert.ok(new THREE.Vector3(0, 0, 1).applyQuaternion(rifle.quaternion).distanceTo(direction) < .00001);
  } finally { rifle.material.dispose(); pool.dispose(); }
});
test('shared geometry keeps independent fading materials and an explicit scene lifetime', () => {
  const pool = serviceRifleFactory(), a = pool.create(), b = pool.create();
  assert.equal(a.geometry, b.geometry); assert.notEqual(a.material, b.material);
  a.material.opacity = .25; assert.equal(b.material.opacity, 1);
  let disposals = 0; b.geometry.addEventListener('dispose', () => disposals++);
  a.material.dispose(); assert.equal(disposals, 0); pool.dispose(); assert.equal(disposals, 1); b.material.dispose();
});
test('unsupported rifle metadata, invalid triangles and non-finite vertices fail before rendering', () => {
  for (const mutate of [d => d.origin = 'grip', d => d.mesh.triangles[0] = 999999, d => d.mesh.positions[0] = NaN,
    d => d.mesh.positions[2] = .5, d => d.mesh.colors[0] = -1, d => d.mesh.normals[0] = 99]) {
    const data = structuredClone(SERVICE_RIFLE); mutate(data); assert.throws(() => rifleGeometry(data));
  }
});
