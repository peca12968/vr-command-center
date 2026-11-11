import { drawLayoutProps } from './layout-ui.js';

const $ = id => document.getElementById(id);

export function mountPlacementMove({ props, editable, apply }) {
  const panel = $('prop-move-panel'), list = $('prop-move-list');
  const selection = new Set();
  const inputs = [$('prop-move-x'), $('prop-move-z')];
  const previewLayer = $('prop-move-preview'), status = $('prop-move-status');
  let moves = [];

  function clearPreview() {
    moves = [];
    previewLayer.replaceChildren();
    $('apply-prop-move').disabled = true;
    status.textContent = '';
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
    const values = inputs.map(input => input.value.trim()), [x, z] = values.map(Number);
    if (values.includes('') || !Number.isFinite(x) || !Number.isFinite(z) || (x === 0 && z === 0)) {
      status.textContent = '請填有效位移，X 和 Z 至少一項須非零。'; return;
    }
    const proposed = props().flatMap((prop, index) => selection.has(prop) ? [{ prop, index, position: {
      ...prop.position, x: prop.position.x + x, z: prop.position.z + z
    } }] : []);
    if (proposed.some(({ position }) => Math.abs(position.x) > 10 || Math.abs(position.z) > 10)) {
      status.textContent = '至少一件物件的中心超出配置圖的 ±10 公尺範圍。'; return;
    }
    moves = proposed;
    drawLayoutProps(previewLayer, moves.map(({ prop, position }) => ({ ...prop, position })), null, moves.map(move => move.index));
    status.textContent = `已預覽 ${moves.length} 件物件。`;
    $('apply-prop-move').disabled = false;
  });
  $('apply-prop-move').addEventListener('click', () => {
    if (!editable() || !moves.length) return;
    apply(moves);
  });
  return { update, reset };
}
