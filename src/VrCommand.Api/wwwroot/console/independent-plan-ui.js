const $ = id => document.getElementById(id);

export function mountIndependentPlan({ available, catalog, pinned, common, inspect, invalidate, changed }) {
  const toggle = $('launch-room-missions-toggle'), panel = $('launch-room-missions'), preview = $('launch-review-room');
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
    const row = { roomId, select, status, current: null };
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
  function render() {
    const visible = enabled();
    $('launch-room-missions-option').hidden = !available();
    $('launch-common-mission').hidden = visible;
    $('launch-mission').required = !visible;
    panel.hidden = !visible;
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
      row.status.textContent = definition ? `${definition.environment.mode} · ${definition.durationSeconds} 秒 · ${layoutStatus}` : layoutStatus;
    }
    optionKey = key;
  }
  function assign(row, revision) {
    if (!revision) { row.current = null; return; }
    const assignment = row.current = { revision, state: 'pending' };
    void inspect(revision).then(report => {
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
  return {
    render, enabled, setRevision,
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
    reject(roomId) {
      const row = roomId ? rows[roomId - 1] : previewRow();
      if (!enabled() || !row?.current) return;
      const id = row.current.revision.mission.id;
      for (const assigned of rows) if (assigned.current?.revision.mission.id === id)
        assigned.current = { revision: assigned.current.revision, state: 'invalid' };
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
      for (const row of rows) { row.current = null; row.select.replaceChildren(); row.status.textContent = ''; }
      render();
    }
  };
}
