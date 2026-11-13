import { validDestination } from './connection-ui.js';

const guid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const isId = value => typeof value === 'string' && guid.test(value) && value !== '00000000-0000-0000-0000-000000000000';
const rooms = [1, 2, 3, 4, 5];
const phases = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const sourceStates = {
  'missing-session': '此管理服務找不到原場次',
  'room-mismatch': '原場次的房間或模式不符',
  unbound: '場次尚未登記來源',
  'different-source': '已登記其他來源',
  'original-source': '已登記本批來源'
};
const endpointStates = {
  'not-checked': '端點未比對',
  'not-published': '尚未公告端點',
  'endpoint-mismatch': '公告端點與報告不符',
  published: '管理端已保存端點'
};

function projectReport(value) {
  const { schemaVersion, status, complete, readyPublished, instanceId, venueLaunchId, topology,
    sourceAttachment, endpointPublication, servers } = value ?? {};
  const ready = status === 'venue-ready';
  if (schemaVersion !== 1 || !isId(instanceId) || !['Independent', 'Linked'].includes(topology)
      || !Array.isArray(servers) || servers.length !== (topology === 'Linked' ? 1 : 5))
    throw new Error('Invalid venue report');
  if (!ready && (status !== 'venue-incomplete' || complete !== false || readyPublished !== false || !isId(venueLaunchId)
      || !['not-attempted', 'rejected', 'confirmed', 'unconfirmed'].includes(sourceAttachment)
      || !['not-attempted', 'confirmed', 'unconfirmed'].includes(endpointPublication)
      || ![sourceAttachment, endpointPublication].includes('unconfirmed')
      || (sourceAttachment === 'unconfirmed' && endpointPublication !== 'not-attempted')
      || (endpointPublication === 'unconfirmed' && sourceAttachment !== 'confirmed')))
    throw new Error('Invalid launch report');
  const roomCount = topology === 'Linked' ? 5 : 1;
  const targets = servers.map(row => {
    const { roomIds } = row ?? {};
    const result = ready ? row?.ready : row?.result;
    const { sessionId, streamId, udpBinding, childPid, address, port } = result ?? {};
    if (!Array.isArray(roomIds) || roomIds.length !== roomCount || !roomIds.every(id => rooms.includes(id))
        || !isId(sessionId) || (streamId !== null && !isId(streamId)))
      throw new Error('Invalid venue server');
    let udp = null;
    if (udpBinding !== null) {
      if (!udpBinding || !isId(streamId) || !Number.isInteger(childPid) || childPid < 1 || udpBinding.processId !== childPid
          || !validDestination(udpBinding.address === '0.0.0.0' ? '127.0.0.1' : udpBinding.address, udpBinding.port))
        throw new Error('Invalid UDP evidence');
      udp = { bindAddress: udpBinding.address, port: udpBinding.port };
    }
    if (endpointPublication === 'unconfirmed' && !udp) throw new Error('Missing UDP evidence');
    if (ready) {
      if (result.schemaVersion !== 1 || result.status !== 'ready' || !udp || !validDestination(address, port)
          || port !== udp.port || !['0.0.0.0', address].includes(udp.bindAddress)) throw new Error('Invalid ready endpoint');
      udp.address = address;
    }
    return { sessionId, roomIds: [...roomIds].sort(), streamId, udp };
  }).sort((a, b) => a.roomIds[0] - b.roomIds[0]);
  if (new Set(targets.map(row => row.sessionId)).size !== targets.length
      || targets.flatMap(row => row.roomIds).join(',') !== rooms.join(','))
    throw new Error('Invalid room coverage');
  return { version: ready ? 2 : 1, instanceId, launchId: ready ? null : venueLaunchId, topology, servers: targets };
}

function verifyReply(value, request) {
  if (value?.version !== request.version || value.launchId !== request.launchId || value.topology !== request.topology
      || typeof value.instanceVerified !== 'boolean' || typeof value.observedAtUtc !== 'string'
      || !Number.isFinite(Date.parse(value.observedAtUtc)) || !Array.isArray(value.servers)
      || value.servers.length !== request.servers.length)
    throw new Error('Invalid launch review');
  value.servers.forEach((row, index) => {
    const target = request.servers[index];
    if (row?.sessionId !== target.sessionId || !Array.isArray(row.roomIds) || row.roomIds.join(',') !== target.roomIds.join(',')
        || !Object.hasOwn(sourceStates, row.sourceState) || !Object.hasOwn(endpointStates, row.endpointState)
        || (row.phase !== null && !Object.hasOwn(phases, row.phase)) || ![true, false, null].includes(row.recentSource)
        || ![true, false, null].includes(row.addressMatched)
        || (row.sourceState === 'original-source' ? !isId(row.streamId) : row.streamId !== null)
        || (row.sourceState === 'original-source' && target.streamId !== null && row.streamId !== target.streamId)
        || (request.version === 2 && row.endpointState === 'published'
          && (row.endpointAddress !== target.udp.address || row.endpointPort !== target.udp.port || row.addressMatched !== true))
        || (['published', 'endpoint-mismatch'].includes(row.endpointState)
          && !validDestination(row.endpointAddress, row.endpointPort)))
      throw new Error('Invalid room review');
  });
  return value;
}

export function mountVenueLaunchReview(getState, api) {
  const $ = suffix => document.getElementById('venue-launch-review-' + suffix);
  const panel = document.getElementById('venue-launch-review'), file = $('file'), button = $('check');
  let active = false, pending = false, generation = 0;
  function update() {
    const state = getState();
    panel.hidden = !active || state.actor?.role !== 'Master';
    file.disabled = panel.hidden || state.busy || !!state.pending || pending;
    button.disabled = file.disabled || file.files.length !== 1;
  }
  function clear() {
    $('summary').textContent = '';
    $('rooms').replaceChildren();
  }
  function show(review) {
    const allUnbound = review.servers.every(row => row.phase === 'Preparing' && row.sourceState === 'unbound');
    const allLive = review.servers.every(row => row.phase === 'Preparing' && row.sourceState === 'original-source'
      && row.endpointState === 'published' && row.recentSource === true);
    const summary = review.version === 2 && allLive && review.instanceVerified ? '取樣時五房原端點皆相符，並收到近期來源快照。'
      : allUnbound ? '原場次取樣時均在準備中且尚未登記來源。' : '已核對原場次。請查看各房來源與端點狀態。';
    const instance = review.instanceVerified ? '管理實例相符。' : '此管理服務未提供實例識別，已按原場次識別比對。';
    $('summary').textContent = `${instance}${summary} 取樣時間 ${new Date(review.observedAtUtc).toLocaleString('zh-TW')}。`;
    $('rooms').replaceChildren(...review.servers.map(row => {
      const li = document.createElement('li');
      const endpoint = row.endpointAddress === null ? '' : ` · ${row.endpointAddress}:${row.endpointPort}`;
      const stream = row.streamId === null ? '' : ` · 來源 ${row.streamId}`;
      const address = endpoint && row.addressMatched === null ? ' · 報告無可比對的公告位址' : '';
      const recent = row.recentSource === null ? '' : row.recentSource ? ' · 有近期來源快照' : ' · 尚無近期來源快照';
      li.textContent = `房間 ${row.roomIds.join('、')} · ${row.sessionId}${row.phase === null ? '' : ' · ' + phases[row.phase]} · ${sourceStates[row.sourceState]}${stream} · ${endpointStates[row.endpointState]}${endpoint}${address}${recent}`;
      return li;
    }));
  }
  file.addEventListener('change', () => {
    generation++; pending = false; clear(); update();
  });
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const selected = file.files[0], attempt = ++generation, epoch = getState().epoch;
    const current = () => attempt === generation && epoch === getState().epoch && active && getState().actor?.role === 'Master';
    pending = true; clear(); update();
    $('summary').textContent = '正在讀取啟動報告…';
    try {
      let request;
      try {
        if (!selected.size || selected.size > 65536) throw new Error('Invalid report size');
        request = projectReport(JSON.parse(await selected.text()));
      } catch {
        if (current()) $('summary').textContent = '請選擇 64 KiB 內的全館就緒檔，或含未確認狀態的第四版啟動報告。';
        return;
      }
      if (!current()) return;
      const review = verifyReply(await api('/venue/server-launch-review', 'POST', request), request);
      if (current()) show(review);
    } catch (error) {
      if (current()) $('summary').textContent = error.code === 'venue-launch-instance-mismatch'
        ? '報告屬於另一個管理實例。' : '無法核對原場次，請確認管理連線後重試。';
    } finally {
      if (current()) { pending = false; update(); }
    }
  });
  return { update, active(on) {
    active = on;
    if (!on) { generation++; pending = false; file.value = ''; clear(); panel.open = false; }
    update();
  } };
}
