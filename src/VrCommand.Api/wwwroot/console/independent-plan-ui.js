import { savedRoomLayoutMap, validateLayoutReport } from './layout-ui.js';

const $ = id => document.getElementById(id);

export function mountIndependentPlan({ available, catalog, pinned, common, climateText, enemyText, inspect, invalidate, changed }) {
  const toggle = $('launch-room-missions-toggle'), panel = $('launch-room-missions'), preview = $('launch-review-room');
  const overview = $('launch-room-layouts'), maps = $('launch-room-layouts-grid');
  let choices = new Map(), optionKey = '';
  const rows = Array.from({ length: 5 }, (_, index) => {
    const roomId = index + 1, label = document.createElement('label'), select = document.createElement('select');
    const status = document.createElement('span');
    select.id = 'launch-room-mission-' + roomId;
    label.htmlFor = select.id; label.textContent = '房間 ' + roomId;
    status.className = 'hint'; status.id = 'launch-room-layout-' + roomId;
    select.setAttribute('aria-describedby', status.id);
    label.append(select, status); $('launch-room-missions-fields').append(label);
    preview.add(new Option('房間 ' + roomId, String(roomId)));
    const card = document.createElement('article'), title = document.createElement('h4');
    const version = document.createElement('p'), mapStatus = document.createElement('p'), map = document.createElement('div');
    const detail = document.createElement('button');
    card.dataset.roomLayoutPreview = String(roomId);
    title.textContent = '房間 ' + roomId;
    mapStatus.className = 'hint';
    detail.type = 'button'; detail.className = 'quiet small'; detail.textContent = '查看詳細檢查';
    detail.setAttribute('aria-label', `查看房間 ${roomId} 的詳細場地檢查`);
    card.append(title, version, mapStatus, map, detail); maps.append(card);
    const row = { roomId, select, status, current: null, card, version, mapStatus, map, detail };
    detail.addEventListener('click', () => {
      if (!enabled() || !overview.open || !row.current?.report?.applies) return;
      preview.value = String(roomId);
      changed();
      const fullMap = $('launch-layout-map-details');
      fullMap.open = true;
      fullMap.querySelector('summary').focus();
    });
    select.addEventListener('change', () => {
      if (!enabled()) return;
      assign(row, choices.get(select.value));
      preview.value = String(roomId);
      changed();
    });
    return row;
  });
  const enabled = () => available() && toggle.checked;
  const previewRow = () => rows[Number(preview.value) - 1];
  function renderMaps() {
    if (!overview.open || !enabled()) return;
    for (const row of rows) {
      const { revision, report, state = 'empty' } = row.current ?? {};
      const id = revision?.mission.id ?? '';
      row.version.textContent = row.select.selectedOptions[0]?.textContent ?? '';
      row.mapStatus.textContent = row.status.textContent;
      row.mapStatus.dataset.status = state;
      row.card.dataset.missionId = id;
      if (row.mapReport === report && row.mapMission === id) continue;
      row.mapReport = report; row.mapMission = id;
      row.detail.disabled = !report?.applies;
      row.map.replaceChildren(...(report?.applies ? [savedRoomLayoutMap(row.roomId, revision.mission.definition.props, report)] : []));
    }
  }
  function render() {
    const visible = enabled();
    $('launch-room-missions-option').hidden = !available();
    $('launch-common-mission').hidden = visible;
    $('launch-mission').required = !visible;
    panel.hidden = !visible;
    overview.hidden = !visible;
    if (!visible) overview.open = false;
    if (!visible) return;
    const heads = catalog();
    choices = new Map([...heads, pinned(), ...rows.map(row => row.current?.revision)].filter(Boolean)
      .map(revision => [revision.mission.id, revision]));
    const options = [...choices].map(([id, revision]) => [id, `${revision.mission.definition.name} · 第 ${revision.number} 版${heads.some(head => head.seriesId === revision.seriesId && head.number > revision.number) ? '（歷史）' : ''}`]);
    const key = JSON.stringify(options);
    for (const row of rows) {
      if (key !== optionKey || !row.select.options.length)
        row.select.replaceChildren(new Option('請選取保存版本', ''), ...options.map(([id, label]) => new Option(label, id)));
      row.select.value = row.current?.revision.mission.id ?? '';
      row.select.title = row.select.selectedOptions[0]?.textContent ?? '';
      const state = row.current?.state ?? 'empty';
      row.status.dataset.status = state;
      const definition = row.current?.revision.mission.definition;
      const layoutStatus = { empty: '尚未選取', pending: '正在檢查場地…', valid: '場地檢查通過',
        invalid: '場地配置未通過，請查看本房預覽', error: '場地檢查未完成，可重新檢查' }[state];
      row.status.textContent = definition
        ? `${definition.environment.mode} · ${definition.durationSeconds} 秒 · ${climateText(definition.environment)} · ${enemyText(definition.enemies)} · ${layoutStatus}` : layoutStatus;
    }
    optionKey = key;
    renderMaps();
  }
  function assign(row, revision) {
    if (!revision) { row.current = null; return; }
    const assignment = row.current = { revision, state: 'pending' };
    void inspect(revision).then(report => {
      assignment.report = report;
      assignment.state = report.applies && report.canStart === true ? 'valid' : 'invalid';
    }, () => { assignment.state = 'error'; }).then(() => { if (row.current === assignment && enabled()) changed(); });
  }
  function setRevision(revision) {
    if (!enabled()) return;
    assign(previewRow(), revision); changed();
  }
  toggle.addEventListener('change', () => {
    if (enabled() && rows.every(row => !row.current)) {
      const revision = common();
      for (const row of rows) assign(row, revision);
    }
    changed();
  });
  preview.addEventListener('change', changed);
  overview.addEventListener('toggle', renderMaps);
  return {
    render, enabled, setRevision,
    restoreRooms(replacements) {
      if (!available()) return;
      const wasShared = !enabled(), shared = wasShared ? common() : null;
      toggle.checked = true;
      preview.value = String(replacements.keys().next().value);
      for (const id of new Set([...replacements.values()].map(revision => revision.mission.id))) invalidate(id);
      for (const row of rows) {
        if (replacements.has(row.roomId)) assign(row, replacements.get(row.roomId));
        else if (wasShared) assign(row, shared);
      }
      changed();
    },
    restore(revisions) {
      toggle.checked = true;
      preview.value = '1';
      for (const id of new Set(revisions.map(revision => revision.mission.id))) invalidate(id);
      for (const [index, row] of rows.entries()) assign(row, revisions[index]);
      changed();
    },
    preview: () => ({ roomId: previewRow().roomId, revision: previewRow().current?.revision }),
    ready: () => rows.every(row => row.current?.state === 'valid'),
    revisions: () => rows.map(row => row.current?.revision),
    reject(roomId, layout) {
      const row = roomId ? rows[roomId - 1] : previewRow();
      if (!enabled() || !row?.current) return;
      const { mission } = row.current.revision;
      let report;
      try { report = validateLayoutReport(layout, 'Independent', mission.definition.environment.mode); }
      catch { /* Keep launch blocked if the rejection report cannot be drawn. */ }
      const id = mission.id;
      for (const assigned of rows) if (assigned.current?.revision.mission.id === id)
        assigned.current = { revision: assigned.current.revision, report, state: 'invalid' };
      preview.value = String(row.roomId);
      return id;
    },
    recheck() {
      const ids = new Set(rows.flatMap(row => row.current ? [row.current.revision.mission.id] : []));
      for (const id of ids) invalidate(id);
      for (const row of rows) if (row.current) assign(row, row.current.revision);
    },
    reset() {
      toggle.checked = false; preview.value = '1'; choices.clear(); optionKey = '';
      for (const row of rows) {
        row.current = null; row.select.replaceChildren(); row.status.textContent = '';
        row.version.textContent = ''; row.mapStatus.textContent = '';
        delete row.card.dataset.missionId;
        delete row.mapStatus.dataset.status;
        row.detail.disabled = true;
        row.map.replaceChildren(); row.mapReport = row.mapMission = undefined;
      }
      render();
    }
  };
}
