import { drawLayoutProps, mountLayoutProposal } from './layout-ui.js';

const $ = id => document.getElementById(id);

export function mountPlacementMove({ props, editable, inspect, apply }) {
  const panel = $('prop-move-panel'), list = $('prop-move-list');
  const selection = new Set();
  const inputs = [$('prop-move-x'), $('prop-move-z'), $('prop-move-yaw')];
  const previewLayer = $('prop-move-preview'), status = $('prop-move-status');
  const preview = mountLayoutProposal('move', inspect);
  let moves = [];

  function clearPreview() {
    moves = [];
    preview.clear();
  }

  function paintSelection() {
    const objects = props();
    for (const object of $('prop-layer').children)
      object.toggleAttribute('data-move-selected', panel.open && selection.has(objects[Number(object.dataset.index)]));
    for (const checkbox of list.querySelectorAll('input'))
      checkbox.checked = selection.has(objects[Number(checkbox.dataset.moveIndex)]);
    $('prop-move-selection').textContent = `已選取 ${selection.size} 件物件`;
    $('preview-prop-move').disabled = selection.size === 0;
    $('select-all-prop-move').disabled = selection.size === objects.length;
    $('clear-prop-move-selection').disabled = selection.size === 0;
  }

  function update(rebuild = true) {
    clearPreview();
    const objects = props(), current = new Set(objects);
    for (const prop of selection) if (!current.has(prop)) selection.delete(prop);
    if (panel.open && rebuild) {
      list.replaceChildren(...objects.map((prop, index) => {
        const label = document.createElement('label'), checkbox = document.createElement('input');
        label.className = 'check';
        checkbox.type = 'checkbox'; checkbox.dataset.moveIndex = String(index);
        label.append(checkbox, `${index + 1} · ${prop.assetId}`);
        return label;
      }));
    } else if (!panel.open) list.replaceChildren();
    paintSelection();
  }

  function reset() {
    selection.clear(); panel.open = false;
    inputs.forEach(input => { input.value = '0'; });
    update();
  }

  list.addEventListener('change', event => {
    if (!editable()) return;
    const prop = props()[Number(event.target.dataset.moveIndex)];
    if (!prop) return;
    if (event.target.checked) selection.add(prop); else selection.delete(prop);
    clearPreview(); paintSelection();
  });
  $('select-all-prop-move').addEventListener('click', () => {
    if (!editable()) return;
    props().forEach(prop => selection.add(prop)); clearPreview(); paintSelection();
  });
  $('clear-prop-move-selection').addEventListener('click', () => {
    if (!editable()) return;
    selection.clear(); clearPreview(); paintSelection();
  });
  panel.addEventListener('toggle', () => {
    if (panel.open) $('prop-copy-panel').open = false;
    update();
  });
  inputs.forEach(input => input.addEventListener('input', clearPreview));

  $('preview-prop-move').addEventListener('click', () => {
    if (!editable() || !selection.size) return;
    clearPreview();
    const values = inputs.map(input => input.value.trim()), [x, z, degrees] = values.map(Number);
    if (values.includes('') || ![x, z, degrees].every(Number.isFinite) || Math.abs(degrees) > 360) {
      status.textContent = '請填有效位移及 -360° 至 360° 的角度。'; return;
    }
    const yaw = degrees % 360;
    if (x === 0 && z === 0 && yaw === 0) {
      status.textContent = '位移或有效旋轉至少一項須非零。'; return;
    }
    const selected = props().flatMap((prop, index) => selection.has(prop) ? [{ prop, index }] : []);
    const centerX = selected.reduce((sum, { prop }) => sum + prop.position.x, 0) / selected.length;
    const centerZ = selected.reduce((sum, { prop }) => sum + prop.position.z, 0) / selected.length;
    const quarter = (yaw / 90 + 4) % 4;
    const radians = yaw * Math.PI / 180;
    // Exact quarter-turn coefficients keep axis-aligned coordinates on the map boundary.
    const cos = Number.isInteger(yaw / 90) ? [1, 0, -1, 0][quarter] : Math.cos(radians);
    const sin = Number.isInteger(yaw / 90) ? [0, 1, 0, -1][quarter] : Math.sin(radians);
    const proposed = selected.map(({ prop, index }) => {
      const fromX = prop.position.x - centerX, fromZ = prop.position.z - centerZ;
      return { prop, index, yawDegrees: yaw ? (prop.yawDegrees + yaw) % 360 : prop.yawDegrees,
        position: { ...prop.position,
          x: x + (yaw ? centerX + cos * fromX + sin * fromZ : prop.position.x),
          z: z + (yaw ? centerZ - sin * fromX + cos * fromZ : prop.position.z)
        } };
    });
    if (proposed.some(({ position }) => Math.abs(position.x) > 10 || Math.abs(position.z) > 10)) {
      status.textContent = '至少一件物件的中心超出配置圖的 ±10 公尺範圍。'; return;
    }
    moves = proposed;
    const destinations = new Map(moves.map(({ index, prop, position, yawDegrees }) => [index, { ...prop, position, yawDegrees }]));
    drawLayoutProps(previewLayer, [...destinations.values()], null, [...destinations.keys()]);
    if (yaw) {
      const pivot = document.createElementNS(previewLayer.namespaceURI, 'path');
      pivot.setAttribute('data-rotation-pivot', '');
      pivot.setAttribute('transform', `translate(${centerX} ${-centerZ})`);
      pivot.setAttribute('d', 'M -.22 0 H .22 M 0 -.22 V .22');
      previewLayer.append(pivot);
    }
    void preview.check(props().map((prop, index) => destinations.get(index) ?? prop), `已預覽 ${moves.length} 件物件。`);
  });
  $('apply-prop-move').addEventListener('click', () => {
    if (!editable() || !moves.length || $('apply-prop-move').disabled) return;
    apply(moves);
  });
  return { update, reset, clearPreview };
}
