import * as THREE from './vendor/three/three.module.js';
import { FIELD_PROPS } from './field-props-data.js';

export const LEGACY_ASSETS = 'primitives-v1';
export const FIELD_ASSETS = 'field-props-v1';
export function supportedAssets(value) { return value === LEGACY_ASSETS || value === FIELD_ASSETS; }

// One cached geometry per kind and one vertex-colour material per scene load.
// Positions and winding use the same world axes as the recorded rigs / rays.
export function fieldPropFactory() {
  const geometries = new Map();
  const material = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .85, vertexColors: true });
  return kind => {
    if (!geometries.has(kind)) {
      const data = FIELD_PROPS.props.find(value => value.kind === kind);
      if (!data) throw new Error('不支援的軍事掩體素材。');
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(data.positions, 3));
      geometry.setAttribute('normal', new THREE.Float32BufferAttribute(data.normals, 3));
      const rgb = []; for (let i = 0; i < data.colors.length; i += 4) rgb.push(...data.colors.slice(i, i + 3));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(rgb, 3));
      geometry.setIndex(data.triangles); geometry.computeBoundingBox(); geometry.computeBoundingSphere();
      geometries.set(kind, geometry);
    }
    return new THREE.Mesh(geometries.get(kind), material);
  };
}
