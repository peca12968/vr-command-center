import { validDestination } from './connection-ui.js';

const roomStates = {
  'missing-session': '尚未準備場次',
  'not-preparing': '場次已離開準備階段',
  'source-bound': '已附掛遊戲來源',
  'alignment-unlocked': '等待鎖定 MR 校正',
  ready: '可交給啟動器'
};
const guid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;

function parsePreview(value) {
  const { topology, ready, rooms } = value ?? {};
  if (![null, 'Independent', 'Linked'].includes(topology) || typeof ready !== 'boolean' || !Array.isArray(rooms) || rooms.length !== 5)
    throw new Error('Invalid venue preview');
  const rows = rooms.map(({ roomId, sessionId, sessionSequence, missionId, missionName, experienceMode, state }, index) => {
    if (roomId !== index + 1 || !Object.hasOwn(roomStates, state)) throw new Error('Invalid venue room');
    if (state === 'missing-session') {
      if ([sessionId, sessionSequence, missionId, missionName, experienceMode].some(field => field !== null))
        throw new Error('Invalid vacant room');
    } else if (!guid.test(sessionId) || !guid.test(missionId) || !Number.isSafeInteger(sessionSequence) || sessionSequence < 1
      || typeof missionName !== 'string' || missionName.length === 0 || missionName.length > 100 || !['VR', 'MR'].includes(experienceMode)) {
      throw new Error('Invalid venue session');
    }
    return { roomId, sessionId, sessionSequence, missionId, missionName, experienceMode, state };
  });
  const sessions = new Set(rows.map(room => room.sessionId));
  const first = rows[0];
  if ((topology === 'Linked' && (sessions.has(null) || sessions.size !== 1 || rows.some(room =>
      room.sessionSequence !== first.sessionSequence || room.missionId !== first.missionId)))
      || (topology === 'Independent' && (sessions.has(null) || sessions.size !== 5))
      || ready !== (topology !== null && rows.every(room => room.state === 'ready')))
    throw new Error('Invalid venue topology');
  return { topology, ready, rooms: rows };
}

function instancePath(value) {
  const path = value.trim().replaceAll('/', '\\');
  if (!/^[A-Za-z]:\\/.test(path) || /[<>:"|?*\u0000-\u001f]/.test(path.slice(3))) return null;
  const segments = path.slice(3).split('\\');
  if (segments.at(-1).toLowerCase() !== 'control-instance.json'
      || segments.some(segment => !segment || /[. ]$/.test(segment))) return null;
  return path;
}

export function mountVenueServerPlan(getState, api, download) {
  const $ = name => document.getElementById('venue-server-' + name);
  const panel = document.getElementById('venue-server-plan'), form = $('form'), fields = $('fields');
  const instance = $('instance'), address = $('address'), bind = $('bind'), ports = $('ports');
  const portDrafts = new Map();
  let active = false, generation = 0, pending = false, preview = null;

  function plan() {
    if (!preview?.ready) return null;
    const controlInstance = instancePath(instance.value), advertised = address.value.trim();
    const listenAddress = bind.value.trim() || advertised;
    if (!controlInstance || !validDestination(advertised, 7777) || ![advertised, '0.0.0.0'].includes(listenAddress)) return null;
    const inputs = [...ports.querySelectorAll('input')];
    if (inputs.some(input => !/^[1-9]\d{3,4}$/.test(input.value) || !validDestination(advertised, Number(input.value)))) return null;
    const values = inputs.map(input => Number(input.value));
    if (new Set(values).size !== values.length) return null;
    const server = ({ sessionId, sessionSequence, missionId }, roomIds, port) => ({
      sessionId, sessionSequence, missionId, roomIds, port
    });
    const servers = preview.topology === 'Linked'
      ? [server(preview.rooms[0], preview.rooms.map(room => room.roomId), values[0])]
      : preview.rooms.map((room, index) => server(room, [room.roomId], values[index]));
    return { version: 4, controlInstance, topology: preview.topology, address: advertised, listenAddress, servers };
  }

  function update() {
    const { actor, busy, pending: command } = getState();
    panel.hidden = !active || actor?.role !== 'Master';
    $('read').disabled = panel.hidden || busy || !!command || pending;
    fields.disabled = $('read').disabled;
    form.hidden = !preview?.ready;
    $('download').disabled = fields.disabled || !plan();
  }

  function resetPreview() {
    if (preview?.ready) portDrafts.set(preview.topology, [...ports.querySelectorAll('input')].map(input => input.value));
    preview = null;
    $('rooms').replaceChildren();
    ports.replaceChildren();
  }

  function show(value) {
    preview = value;
    $('rooms').replaceChildren(...value.rooms.map(room => {
      const li = document.createElement('li');
      const mission = room.sessionId ? ` · ${room.experienceMode} · ${room.missionName} · ${room.sessionId}` : '';
      li.textContent = `房間 ${room.roomId} · ${roomStates[room.state]}${mission}`;
      return li;
    }));
    const targets = value.topology === 'Linked' ? ['合併場次'] : value.rooms.map(room => `房間 ${room.roomId}`);
    const savedPorts = portDrafts.get(value.topology);
    ports.replaceChildren(...(value.ready ? targets.map((name, index) => {
      const label = document.createElement('label'), input = document.createElement('input');
      label.textContent = `${name} UDP 埠`;
      input.type = 'number'; input.min = '1024'; input.max = '65535'; input.required = true;
      input.value = savedPorts?.[index] ?? String(7777 + index);
      label.append(input);
      return label;
    }) : []));
    $('status').textContent = value.ready
      ? `${value.topology === 'Linked' ? '五房合併' : '五房獨立'} · 請核對路徑、IPv4 與 UDP 埠，下載前會再次確認原場次。`
      : '等待五房場次全部符合啟動條件。';
  }

  function begin(message) {
    const epoch = getState().epoch, attempt = ++generation;
    pending = true;
    $('status').textContent = message;
    update();
    return {
      current: () => generation === attempt && getState().epoch === epoch && !panel.hidden,
      finish() { if (generation === attempt) { pending = false; update(); } }
    };
  }

  $('read').addEventListener('click', async () => {
    if ($('read').disabled) return;
    resetPreview();
    const request = begin('正在讀取五房場次…');
    try {
      const value = parsePreview(await api('/venue/server-plan'));
      if (request.current()) show(value);
    } catch {
      if (request.current()) $('status').textContent = '無法讀取五房場次，請重試。';
    } finally { request.finish(); }
  });

  form.addEventListener('input', update);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const value = plan();
    if ($('download').disabled || !value) return;
    const expected = preview;
    const request = begin('正在重新核對原場次…');
    try {
      const current = parsePreview(await api('/venue/server-plan'));
      if (!request.current()) return;
      if (JSON.stringify(current) !== JSON.stringify(expected)) {
        const changed = current.rooms.filter((room, index) => JSON.stringify(room) !== JSON.stringify(expected.rooms[index]))
          .map(room => room.roomId);
        resetPreview();
        const scope = changed.length ? `（房間 ${changed.join('、')}）` : '';
        $('status').textContent = `場次狀態已變更${scope}，請重新讀取五房場次。已保留本頁輸入的 UDP 埠。`;
        return;
      }
      download('vr-command-venue-server-plan.json', new Blob([JSON.stringify(value, null, 2) + '\n'], { type: 'application/json' }));
      $('status').textContent = '已下載整批來源登記計畫。請使用 Windows 啟動器 1.15 以上版本。場次有變更時請重新讀取並下載。';
    } catch {
      if (request.current()) {
        resetPreview();
        $('status').textContent = '無法確認原場次，請重新讀取五房場次。';
      }
    } finally { request.finish(); }
  });

  return { update, active(on) {
    active = on;
    if (!on) {
      generation++; pending = false;
      resetPreview(); portDrafts.clear(); form.reset(); panel.open = false;
      $('status').textContent = '';
    }
    update();
  } };
}
