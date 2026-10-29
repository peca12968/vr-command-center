import * as THREE from './vendor/three/three.module.js';
import { SERVICE_RIFLE } from './service-rifle-data.js';

export const RIFLE_ASSETS = 'service-rifle-v1';
export function rifleGeometry(source = SERVICE_RIFLE) {
  const d = source.mesh;
  if (source.assetSet !== RIFLE_ASSETS || source.units !== 'metres' || source.origin !== 'muzzle' || source.forward !== '+Z'
    || d?.kind !== 'ServiceRifle' || !Array.isArray(d.positions) || !d.positions.length || d.positions.length % 3
    || d.positions.length > 6000 || d.normals?.length !== d.positions.length || d.colors?.length !== d.positions.length / 3 * 4
    || !d.triangles?.length || d.triangles.length % 3 || d.triangles.length > 1800) throw new Error('Invalid rifle geometry');
  const rgb = [], vertices = d.positions.length / 3;
  for (let i = 0; i < vertices; i++) {
    const p = d.positions.slice(i * 3, i * 3 + 3), n = d.normals.slice(i * 3, i * 3 + 3), c = d.colors.slice(i * 4, i * 4 + 4);
    if (!p.every(Number.isFinite) || Math.hypot(...p) > 3 || !n.every(Number.isFinite) || Math.abs(Math.hypot(...n) - 1) > .001
      || !c.every(Number.isFinite) || c.some(v => v < 0 || v > 1) || c[3] !== 1) throw new Error('Invalid rifle vertex');
    rgb.push(...c.slice(0, 3));
  }
  if (d.triangles.some(i => !Number.isInteger(i) || i < 0 || i >= vertices)) throw new Error('Invalid rifle triangle');
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(d.positions, 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(d.normals, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(rgb, 3)); geometry.setIndex(d.triangles);
  geometry.computeBoundingBox(); geometry.computeBoundingSphere();
  const b = geometry.boundingBox, size = b.getSize(new THREE.Vector3());
  if (b.max.z > .0001 || b.min.z < -.8 || size.z < .6 || size.x > .2 || size.y > .5) { geometry.dispose(); throw new Error('Invalid rifle muzzle anchor'); }
  // Actor removal must retain this mesh while another actor uses the pool.
  geometry.userData.serviceRifleShared = true; return geometry;
}
export function serviceRifleFactory() {
  const geometry = rifleGeometry();
  return { triangles: geometry.index.count / 3, create() { return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .8, vertexColors: true })); },
    dispose() { geometry.dispose(); } };
}
export function placeRifle(mesh, player, root) {
  const forward = new THREE.Vector3(player.forward.x, player.forward.y, player.forward.z).normalize();
  mesh.position.set(player.muzzle.x - root.x, player.muzzle.y - root.y, player.muzzle.z - root.z);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), forward);
  const r = player.rig?.kind !== 'None' && player.rig?.rightRotation;
  if (r) {
    const q = new THREE.Quaternion(r.x, r.y, r.z, r.w);
    // Older / externally generated rigs can omit matching roll. Their accepted
    // shot direction remains authoritative; never point a barrel away from it.
    if (new THREE.Vector3(0, 0, 1).applyQuaternion(q).dot(forward) > .99999) mesh.quaternion.copy(q);
  }
}
