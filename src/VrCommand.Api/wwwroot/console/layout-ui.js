const $ = id => document.getElementById(id);
const svgNamespace = 'http://www.w3.org/2000/svg';
const propHalfSizes = new Map([['sandbag', [1, .35]], ['barrel', [.35, .35]]]);
const labels = {
  InvalidProp: '座標或角度不是有效數字', UnsupportedAsset: '目前場地只支援沙包與油桶',
  NotFloorLevel: '物件必須放在地面（Y=0）', OutsideRoom: '旋轉後的包圍盒超出 12 × 12 公尺場地',
  YawOutOfRange: '旋轉角度須在 -360° 至 360°，請輸入等價的單圈角度',
  Overlap: '兩個物件的平面包圍盒重疊', SpawnBlocked: '物件堵住出生位的預留空間',
  EnemySpawnCapacity: '初始敵軍數量超過此配置的出生候選容量'
};
function text(node, value) { node.textContent = value; }
function svg(tag, attributes) {
  const node = document.createElementNS(svgNamespace, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}
// With SVG y = -world z, the simulation's positive yaw is a positive SVG rotation.
const propTransform = prop => `translate(${prop.position.x} ${-prop.position.z}) rotate(${prop.yawDegrees})`;
const box = (halfX, halfZ) => ({ x: -halfX, y: -halfZ, width: 2 * halfX, height: 2 * halfZ });

export function drawLayoutProps(layer, props, selected = null) {
  layer.replaceChildren(...props.map((prop, index) => {
    const group = svg('g', { transform: propTransform(prop), 'data-index': index });
    const name = `物件 ${index + 1} ${prop.assetId}`;
    if (selected !== null) {
      group.dataset.selected = String(index === selected);
      group.setAttribute('role', 'button'); group.setAttribute('tabindex', '0'); group.setAttribute('aria-label', name);
    } else {
      const title = svg('title', {}); text(title, name); group.append(title);
    }
    const halfSize = propHalfSizes.get(prop.assetId);
    if (halfSize) {
      const dimensions = box(...halfSize);
      const shape = prop.assetId === 'barrel' ? svg('circle', { r: halfSize[0], fill: '#658d87' })
        : svg('rect', { ...dimensions, rx: '.08', fill: '#a69b63' });
      const envelope = svg('rect', { ...dimensions,
        fill: 'none', stroke: '#d2dca2', 'stroke-width': '.04', 'stroke-dasharray': '.1 .06', 'data-envelope': prop.assetId });
      group.append(shape, envelope);
    } else {
      group.append(svg('circle', { r: '.28', fill: '#754a40' }));
    }
    const label = svg('text', { y: '.12' }); text(label, index + 1); group.append(label);
    return group;
  }));
}

function drawClearance(prefix, report, props) {
  const toggle = $(prefix + '-layout-show-clearance'), layer = $(prefix + '-layout-clearance');
  toggle.disabled = report?.canStart !== true;
  const visible = !toggle.disabled && toggle.checked;
  $(prefix + '-layout-clearance-legend').hidden = !visible;
  if (!visible) { layer.replaceChildren(); return; }
  const radius = report.playerRadius, room = report.roomHalfSize - radius;
  layer.replaceChildren(svg('rect', { ...box(room, room), class: 'layout-clearance-room' }),
    ...props.flatMap((prop, index) => {
      const halfSize = propHalfSizes.get(prop.assetId);
      if (!halfSize) return [];
      const [halfX, halfZ] = halfSize;
      return [svg('rect', { ...box(halfX + radius, halfZ + radius), transform: propTransform(prop),
        class: 'layout-clearance-prop', 'data-clearance-index': index })];
    }));
}
function accept(report, mode, experienceMode) {
  const profile = experienceMode === 'MR' ? 'mr-room-v1' : 'vr-room-v1';
  if (report?.version !== 1 || !['vr-room-v1', 'mr-room-v1'].includes(report.profile) || report.rulesVersion !== '0.8.0' || report.mode !== mode
    || (experienceMode && report.profile !== profile) || report.roomHalfSize !== 6 || report.playerRadius !== .3
    || !Array.isArray(report.issues) || !Array.isArray(report.invalidProps) || !Array.isArray(report.spawns)) throw new Error('不支援的場地檢查版本或模式。');
  return report;
}
function description(issue) {
  const props = issue.propIndex >= 0 ? `物件 ${issue.propIndex + 1}${issue.otherPropIndex >= 0 ? ` 與 ${issue.otherPropIndex + 1}` : ''}：` : '';
  return props + (labels[issue.code] || '配置不受支援') + (issue.seat >= 0 ? `（出生位 ${issue.seat + 1}）` : '');
}
function routePreview(report) {
  const preview = report?.routePreview;
  if (report?.canStart !== true || preview?.step !== .5 || preview.targetZ !== 0
    || !Array.isArray(preview.seats) || preview.seats.length !== 5) return null;
  for (const [seat, route] of preview.seats.entries()) {
    const spawn = report.spawns.find(value => value.seat === seat);
    const fine = route?.sampleStep === .125;
    if (!spawn || route?.seat !== seat || (!fine && route.sampleStep !== undefined)
      || !Array.isArray(route.path) || route.path.length > (fine ? 7921 : 529)
      || route.path.some(point => !point || ![point.x, point.z].every(value => Number.isFinite(value) && Math.abs(value) <= 5.5))) return null;
    const [start] = route.path;
    if (start && (start.x !== spawn.x || start.z !== spawn.z || route.path.at(-1).z !== preview.targetZ)) return null;
    if (fine && (!start || route.path.some((point, index) => {
      if (index === 0) return false;
      const dx = Math.abs(point.x - route.path[index - 1].x), dz = Math.abs(point.z - route.path[index - 1].z);
      return !((dx === .125 && dz === 0) || (dx === 0 && dz === .125));
    }))) return null;
  }
  return preview.seats;
}
export function mountLayout({ api, epoch, active, editable, draft, selection, changed, selectProp, selectedProp }) {
  let generation = 0, draftSerial = 0, launchSerial = 0, draftTimer, launchTimer;
  let draftKey = '', draftReport = null, launchKey = '', launchReport = null;
  let trial = null;
  const cache = new Map(), savedRequests = new Map();
  function inspectSaved(selected) {
    const key = selected.id + '/' + selected.mode;
    if (cache.has(key)) return Promise.resolve(cache.get(key));
    if (savedRequests.has(key)) return savedRequests.get(key);
    const request = api(`/missions/${selected.id}/layout?mode=${encodeURIComponent(selected.mode)}`)
      .then(value => {
        const report = accept(value, selected.mode, selected.experienceMode);
        if (savedRequests.get(key) === request) cache.set(key, report);
        return report;
      }).finally(() => { if (savedRequests.get(key) === request) savedRequests.delete(key); });
    savedRequests.set(key, request);
    return request;
  }
  function invalidateSaved(id, mode) { const key = id + '/' + mode; cache.delete(key); savedRequests.delete(key); }
  function clearMarks() { for (const prop of $('prop-layer').children) delete prop.dataset.layoutInvalid; }
  function drawRoutes(id, routes) {
    $(id).replaceChildren(...routes.map(route => svg('polyline', {
      points: route.path.map(point => `${point.x},${-point.z}`).join(' '), 'data-sample-step': route.sampleStep ?? .5
    })));
  }
  function drawSpawns(id, report, missing) {
    const blocked = new Set(report?.issues.filter(issue => issue.code === 'SpawnBlocked').map(issue => issue.seat));
    $(id).replaceChildren(...(report?.applies ? report.spawns : []).map(spawn => {
      const group = svg('g', { transform: `translate(${spawn.x} ${-spawn.z})`, 'data-seat': spawn.seat });
      if (missing.includes(spawn.seat + 1)) group.dataset.routeMissing = 'true';
      if (blocked.has(spawn.seat)) group.dataset.spawnBlocked = 'true';
      const circle = svg('circle', { r: report.playerRadius });
      const label = svg('text', { y: '.12' }); text(label, spawn.seat + 1);
      group.append(circle, label); return group;
    }));
  }
  function markInvalid(id, report) {
    const invalid = new Set(report.invalidProps);
    for (const prop of $(id).children) {
      if (invalid.has(Number(prop.dataset.index))) prop.dataset.layoutInvalid = 'true';
      else delete prop.dataset.layoutInvalid;
    }
  }
  function paintTrial() {
    const index = selectedProp();
    const visible = active() && editable() && index >= 0 && routePreview(draftReport)?.some(route => !route.path.length);
    if (!visible || (trial && (trial.key !== draftKey || trial.index !== index))) trial = null;
    $('draft-layout-trial').hidden = !visible;
    $('layout-try-removal').disabled = !visible || !!trial?.pending;
    $('layout-clear-trial').disabled = !trial;
    const routes = trial?.opened ?? [];
    drawRoutes('layout-trial-routes', routes);
    for (const prop of $('prop-layer').children)
      prop.toggleAttribute('data-layout-trial', !!trial?.opened && Number(prop.dataset.index) === index);
    text($('layout-trial-status'), trial?.message ?? (visible ? `可試算移除物件 ${index + 1} 後的通路。` : ''));
  }
  function clearTrial() { trial = null; paintTrial(); }
  async function tryRemoval() {
    if ($('layout-try-removal').disabled) return;
    const index = selectedProp(), body = draft(), baseline = routePreview(draftReport);
    if (!body.props[index] || JSON.stringify(body) !== draftKey || !baseline) return;
    const identity = epoch(), attempt = { key: draftKey, index, pending: true, message: '正在試算移除後的通路…' };
    trial = attempt;
    paintTrial();
    try {
      const report = accept(await api('/mission-layout', 'POST', { ...body, props: body.props.filter((_, position) => position !== index) }), body.mode, body.experienceMode);
      if (trial !== attempt || identity !== epoch()) return;
      const routes = routePreview(report);
      if (!routes || routes.some(route => !route.path.length && baseline[route.seat].path.length)) throw new Error('Invalid trial routes.');
      attempt.opened = routes.filter(route => route.path.length && !baseline[route.seat].path.length);
      attempt.message = attempt.opened.length
        ? `試算移除物件 ${index + 1} 後，出生位 ${attempt.opened.map(route => route.seat + 1).join('、')} 可走到中線。`
        : `試算移除物件 ${index + 1} 後，沒有新增通往中線的路徑。`;
    } catch {
      if (trial === attempt) attempt.message = '通路試算未完成，可重新試算。';
    } finally {
      if (trial === attempt) { attempt.pending = false; paintTrial(); }
    }
  }
  function paint(prefix, report, message) {
    const summary = $(prefix + '-layout-summary'), list = $(prefix + '-layout-issues'); list.replaceChildren();
    const routes = routePreview(report), routeSummary = $(prefix + '-layout-route-summary');
    const missing = routes?.filter(route => !route.path.length).map(route => route.seat + 1) ?? [];
    const fine = routes?.filter(route => route.sampleStep === .125).map(route => route.seat + 1) ?? [];
    routeSummary.hidden = !routes;
    routeSummary.classList.toggle('layout-route-warning', missing.length > 0);
    const coverage = !routes ? '' : missing.length
      ? `未找到通往中線的取樣路徑 · 出生位 ${missing.join('、')}`
      : '五個出生位皆有到中線的取樣路徑。';
    text(routeSummary, fine.length ? coverage + ` · 0.125 公尺取樣 · 出生位 ${fine.join('、')}` : coverage);
    if (prefix === 'draft') {
      drawClearance('draft', report, report?.canStart ? draft().props : []);
      drawRoutes('layout-routes', (routes ?? []).filter(route => route.path.length));
      paintTrial();
    } else {
      const details = $('launch-layout-map-details');
      details.hidden = !report?.applies;
      $('launch-layout-map').setAttribute('viewBox', report?.canStart ? '-7 -7 14 14' : '-11 -11 22 22');
      const props = details.hidden ? [] : selection().props;
      drawLayoutProps($('launch-layout-props'), props);
      drawClearance('launch', report, props);
      drawRoutes('launch-layout-routes', (routes ?? []).filter(route => route.path.length));
      drawSpawns('launch-layout-spawns', report, missing);
      if (report) markInvalid('launch-layout-props', report);
    }
    if (!report) { text(summary, message); summary.dataset.status = 'unknown'; return; }
    summary.dataset.status = !report.applies ? 'not-applicable' : report.canStart ? 'valid' : 'invalid';
    text(summary, !report.applies ? '此場次沒有可用的場地檢查。'
      : report.canStart ? `${report.profile === 'mr-room-v1' ? 'MR 虛擬配置檢查通過，實體場地另行對位' : '場地檢查通過'} · 每房初始敵軍候選容量 ${report.enemyCapacityPerRoom} · 需求 ${report.requestedEnemiesPerRoom}`
        : `場地有 ${report.totalIssueCount} 個問題，新開 VR 場次前須修正。`);
    for (const issue of report.issues) {
      const item = document.createElement('li');
      if (prefix === 'draft' && issue.propIndex >= 0) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'quiet small';
        text(button, description(issue)); button.addEventListener('click', () => selectProp(issue.propIndex)); item.append(button);
      } else text(item, description(issue));
      list.append(item);
    }
    if (report.truncated) { const item = document.createElement('li'); text(item, '僅列出前 128 個問題；圖中已標出所有涉及物件。'); list.append(item); }
    if (prefix === 'draft') {
      markInvalid('prop-layer', report);
      drawSpawns('layout-spawns', report, missing);
    }
  }
  function reset() {
    generation++; draftSerial++; launchSerial++; clearTimeout(draftTimer); clearTimeout(launchTimer);
    draftKey = launchKey = ''; draftReport = launchReport = trial = null; cache.clear(); savedRequests.clear(); clearMarks(); $('layout-spawns').replaceChildren();
    $('launch-layout-map-details').open = false;
    $('draft-layout-show-clearance').checked = $('launch-layout-show-clearance').checked = false;
    paint('draft', null, '修改配置後自動檢查。草稿仍可保存，開場前須修正問題。');
    paint('launch', null, '選取保存的任務版本後檢查場地。');
  }
  function scheduleDraft() {
    if (!active()) return;
    if (!editable()) { clearMarks(); paint('draft', null, '此處為唯讀草稿；可在開場區查看保存版本的場地報告。'); return; }
    const body = draft(), key = JSON.stringify(body);
    if (key === draftKey) { if (draftReport) paint('draft', draftReport); return; }
    draftKey = key; draftReport = null; const serial = ++draftSerial, token = generation, identity = epoch();
    clearTimeout(draftTimer); clearMarks(); $('layout-spawns').replaceChildren(); paint('draft', null, '檢查目前配置中…');
    draftTimer = setTimeout(async () => {
      try {
        const report = accept(await api('/mission-layout', 'POST', body), body.mode, body.experienceMode);
        if (identity !== epoch() || token !== generation || serial !== draftSerial || key !== JSON.stringify(draft())) return;
        draftReport = report; paint('draft', report);
      } catch {
        if (identity !== epoch() || token !== generation || serial !== draftSerial) return;
        draftKey = ''; paint('draft', null, '檢查未完成；請確認物件資料及敵軍數量，或重新整理後再試。');
      }
    }, 180);
  }
  function scheduleLaunch() {
    if (!active()) return;
    const selected = selection(), key = selected.id ? selected.id + '/' + selected.mode : '';
    if (key === launchKey) return;
    launchKey = key; launchReport = null; const serial = ++launchSerial, token = generation, identity = epoch();
    clearTimeout(launchTimer);
    if (!key) { paint('launch', null, '請先選取保存的任務版本。'); changed(); return; }
    if (cache.has(key)) { launchReport = cache.get(key); paint('launch', launchReport); changed(); return; }
    paint('launch', null, '檢查選取版本的場地中…'); changed();
    launchTimer = setTimeout(async () => {
      try {
        const report = await inspectSaved(selected);
        const now = selection();
        if (identity !== epoch() || token !== generation || serial !== launchSerial || now.id + '/' + now.mode !== key) return;
        launchReport = report; paint('launch', report); changed();
      } catch {
        if (identity !== epoch() || token !== generation || serial !== launchSerial) return;
        launchKey = ''; launchReport = null; paint('launch', null, '場地檢查未完成。請確認管理服務版本，重新整理後再試。'); changed();
      }
    }, 100);
  }
  function canLaunch() {
    const current = selection();
    return launchKey === current.id + '/' + current.mode && !!launchReport && (!launchReport.applies || launchReport.canStart === true);
  }
  function rejected(id, mode, report) {
    const key = id + '/' + mode, current = selection();
    if (current.id + '/' + current.mode !== key) return;
    try { accept(report, mode, current.experienceMode); } catch { launchKey = ''; launchReport = null; paint('launch', null, '場地檢查版本已變更，請更新控制台後再開場。'); changed(); return; }
    savedRequests.delete(key); cache.set(key, report);
    launchSerial++; clearTimeout(launchTimer); launchKey = key; launchReport = report; paint('launch', report); changed();
  }
  function recheckDraft() { draftKey = ''; scheduleDraft(); }
  function recheckLaunch(invalidate = true) {
    const current = selection();
    if (invalidate) invalidateSaved(current.id, current.mode);
    launchKey = ''; scheduleLaunch();
  }
  $('layout-try-removal').addEventListener('click', tryRemoval);
  $('layout-clear-trial').addEventListener('click', clearTrial);
  $('draft-layout-show-clearance').addEventListener('change', () => drawClearance('draft', draftReport, draft().props));
  $('launch-layout-show-clearance').addEventListener('change', () => drawClearance('launch', launchReport, selection().props));
  reset(); return { reset, scheduleDraft, scheduleLaunch, canLaunch, rejected, recheckDraft, recheckLaunch, clearTrial, inspectSaved, invalidateSaved };
}
