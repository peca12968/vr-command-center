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

function privateAddressKind(address) {
  if (!validDestination(address, 7777)) return null;
  const [first, second] = address.split('.').map(Number);
  if (first === 127) return 'loopback';
  if (first === 10 || first === 172 && second >= 16 && second <= 31 || first === 192 && second === 168) return 'lan';
  return null;
}

function parseSeatInventory(value) {
  if (value?.version !== 1 || !Array.isArray(value.seats) || Object.keys(value).length !== 2
      || value.seats.length < 5 || value.seats.length > 25) throw new Error('Invalid seat inventory');
  const seen = new Set(), counts = [0, 0, 0, 0, 0], kinds = new Set();
  const seats = value.seats.map(row => {
    const { roomId, seat, address } = row;
    const kind = privateAddressKind(address), key = roomId * 10 + seat;
    if (Object.keys(row).length !== 3 || !Number.isInteger(roomId) || roomId < 1 || roomId > 5
        || !Number.isInteger(seat) || seat < 1 || seat > 5 || !kind || seen.has(key)) throw new Error('Invalid seat');
    seen.add(key);
    counts[roomId - 1]++;
    kinds.add(kind);
    return { roomId, seat, address };
  });
  if (!counts.every(count => count === counts[0]) || kinds.size !== 1) throw new Error('Invalid coverage');
  seats.sort((left, right) => left.roomId - right.roomId || left.seat - right.seat);
  return { seats, kind: kinds.values().next().value };
}

export function mountVenueServerPlan(getState, api, download) {
  const $ = name => document.getElementById('venue-server-' + name);
  const panel = document.getElementById('venue-server-plan'), form = $('form'), fields = $('fields');
  const instance = $('instance'), address = $('address'), bind = $('bind'), ports = $('ports');
  const seatFile = $('seat-addresses'), networkDownload = $('network-download'), networkStatus = $('network-status');
  const otherIps = $('other-ips');
  const portDrafts = new Map();
  let active = false, generation = 0, pending = false, preview = null;
  let seatRead = 0, seatsPending = false, inventory = null, inventoryError = '';

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
    const current = plan();
    const network = networkPlan(current);
    $('download').disabled = fields.disabled || !current;
    networkDownload.disabled = fields.disabled || seatsPending || !network.payload;
    networkStatus.textContent = seatsPending ? '正在讀取席位 IPv4 表…' : inventoryError;
    if (inventory) {
      const count = `已讀取五房共 ${inventory.seats.length} 席。`;
      networkStatus.textContent = count + (network.error ? ' ' + network.error
        : network.payload?.serverIps ? ' 將核對逐席直連及全部伺服器位址。' : '');
    }
  }

  function networkPlan(current) {
    if (!current || !inventory) return {};
    if (current.address !== current.listenAddress || privateAddressKind(current.address) !== inventory.kind)
      return { error: 'UDP 預檢需要具體綁定位址，並使用同類型的私有網路或本機 IPv4。' };
    const payload = { version: 1, mode: current.topology,
      endpoints: current.servers.map(({ roomIds, port }) => ({ roomIds, address: current.address, port })),
      sources: inventory.seats };
    const extra = otherIps.value.split('\n').map(line => line.trim()).filter(Boolean);
    if (!extra.length) return { payload };
    const serverIps = new Set([current.address, ...extra]);
    if (extra.length > 127 || serverIps.size !== extra.length + 1 || inventory.kind !== 'lan'
        || extra.some(value => !privateAddressKind(value)))
      return { error: '請逐行填寫有效且不重複的伺服器 IPv4，公告位址會自動加入。玩家及遊戲端點須使用私有網路。' };
    const seatsByAddress = new Map();
    for (const { roomId, seat, address } of inventory.seats) {
      if (!seatsByAddress.has(address)) seatsByAddress.set(address, []);
      seatsByAddress.get(address).push(`房間 ${roomId} 席位 ${seat}`);
    }
    const collisions = [], shared = [];
    for (const [value, seats] of seatsByAddress) {
      if (serverIps.has(value)) collisions.push(...seats);
      if (seats.length > 1) shared.push(seats.join('、'));
    }
    if (collisions.length || shared.length) return { error: [
      collisions.length ? `席位與伺服器位址衝突：${collisions.join('、')}。` : '',
      shared.length ? `席位共用玩家 IPv4：${shared.join('；')}。` : ''
    ].filter(Boolean).join(' ') };
    const numeric = value => value.split('.').reduce((total, octet) => total * 256 + Number(octet), 0);
    payload.serverIps = [...serverIps].sort((left, right) => numeric(left) - numeric(right));
    return { payload };
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

  seatFile.addEventListener('change', async () => {
    const file = seatFile.files[0], attempt = ++seatRead;
    inventory = null;
    inventoryError = '';
    seatsPending = !!file;
    update();
    if (!file) return;
    try {
      if (file.size > 32768) throw new Error('Seat inventory too large');
      const parsed = parseSeatInventory(JSON.parse(await file.text()));
      if (attempt === seatRead) inventory = parsed;
    } catch {
      if (attempt === seatRead) inventoryError = '無法讀取席位 IPv4 表。請確認五房席數相同、席位無重複，且使用同類型 IPv4。';
    } finally {
      if (attempt === seatRead) { seatsPending = false; update(); }
    }
  });
  form.addEventListener('input', update);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const value = plan();
    const wantsNetwork = event.submitter === networkDownload;
    const payload = wantsNetwork ? networkPlan(value).payload : value;
    if ((wantsNetwork ? networkDownload : $('download')).disabled || !payload) return;
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
      const name = wantsNetwork ? 'vr-command-venue-network.json' : 'vr-command-venue-server-plan.json';
      download(name, new Blob([JSON.stringify(payload, null, 2) + '\n'], { type: 'application/json' }));
      $('status').textContent = wantsNetwork ? '已下載 UDP 預檢網路清單。'
        : '已下載整批來源登記計畫。請使用 Windows 啟動器 1.15 以上版本。場次有變更時請重新讀取並下載。';
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
      seatRead++; seatsPending = false; inventory = null; inventoryError = '';
      resetPreview(); portDrafts.clear(); form.reset(); panel.open = false;
      $('status').textContent = '';
    }
    update();
  } };
}
