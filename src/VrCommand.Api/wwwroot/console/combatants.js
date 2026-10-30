import * as THREE from './vendor/three/three.module.js';
import { COMBATANTS } from './combatants-data.js';

export const COMBATANT_ASSETS = 'combatants-v1';
export function enemyPose(forward, walking, tick) {
  if (!forward || ![forward.x, forward.y, forward.z].every(Number.isFinite) || Math.abs(Math.hypot(forward.x, forward.y, forward.z) - 1) > .01
    || !Number.isSafeInteger(tick) || tick < 0 || tick > 1728000 || typeof walking !== 'boolean') throw new Error('Invalid enemy presentation');
  return { yaw: Math.atan2(forward.x, forward.z) * 180 / Math.PI,
    pitch: Math.max(-45, Math.min(45, -Math.asin(Math.max(-1, Math.min(1, forward.y))) * 180 / Math.PI)),
    stride: walking ? Math.sin((tick % 12) * Math.PI / 6) * 18 : 0 };
}
export function opponentGeometry(part) {
  if (!part?.positions?.length || part.positions.length % 3 || part.positions.length > 6000 || part.normals?.length !== part.positions.length
    || part.colors?.length !== part.positions.length / 3 * 4 || !part.triangles?.length || part.triangles.length % 3 || part.triangles.length > 1800) throw new Error('Invalid opponent arrays');
  const rgb = [], count = part.positions.length / 3;
  for (let i = 0; i < count; i++) {
    const p = part.positions.slice(i * 3, i * 3 + 3), n = part.normals.slice(i * 3, i * 3 + 3), c = part.colors.slice(i * 4, i * 4 + 4);
    if (![...p,...n,...c].every(Number.isFinite) || Math.hypot(...p) > 3 || Math.abs(Math.hypot(...n) - 1) > .001 || c.some(v => v < 0 || v > 1) || c[3] !== 1) throw new Error('Invalid opponent vertex');
    rgb.push(...c.slice(0, 3));
  }
  if (part.triangles.some(i => !Number.isInteger(i) || i < 0 || i >= count)) throw new Error('Invalid opponent triangle');
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(part.positions, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(part.normals, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(rgb, 3)); g.setIndex(part.triangles);
  g.computeBoundingBox(); g.computeBoundingSphere(); g.userData.enemyModelShared = true; return g;
}
export function opponentFactory(data = COMBATANTS) {
  if (data?.assetSet !== COMBATANT_ASSETS || data.units !== 'metres' || data.origin !== 'feet' || data.forward !== '+Z' || data.enemyPresentationVersion !== 1
    || data.parts?.length !== 3 || data.parts.some((p,i) => p?.kind !== ['Torso','Head','Leg'][i])
    || [data.headPivot,data.leftHip,data.rightHip].some(p => !Array.isArray(p) || p.length !== 3 || p.some(v => !Number.isFinite(v) || Math.abs(v) > 2))) throw new Error('Invalid opponent metadata');
  const geometries = []; let disposed = false;
  try { for (const part of data.parts) geometries.push(opponentGeometry(part)); } catch (error) { for (const g of geometries) g.dispose(); throw error; }
  const part = (root, index, position, material) => { const mesh = new THREE.Mesh(geometries[index], material); mesh.position.fromArray(position); root.add(mesh); return mesh; };
  return { triangles: geometries[0].index.count / 3 + geometries[1].index.count / 3 + geometries[2].index.count / 3 * 2,
    create() {
      if (disposed) throw new Error('Opponent pool is disposed');
      const group = new THREE.Group(), material = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .85, vertexColors: true });
      return { group, body: part(group, 0, [0,0,0], material), head: part(group, 1, data.headPivot, material),
        leftLeg: part(group, 2, data.leftHip, material), rightLeg: part(group, 2, data.rightHip, material), model: true, enemy: true };
    }, dispose() { if (!disposed) { disposed = true; for (const g of geometries) g.dispose(); } } };
}
export function poseOpponent(actor, enemy, tick) {
  if (!enemy.hasPresentation) throw new Error('Missing recorded opponent pose');
  const pose = enemyPose(enemy.forward, enemy.walking, tick), rad = Math.PI / 180;
  actor.group.rotation.y = pose.yaw * rad; actor.head.rotation.x = pose.pitch * rad;
  actor.leftLeg.rotation.x = pose.stride * rad; actor.rightLeg.rotation.x = -pose.stride * rad;
}
