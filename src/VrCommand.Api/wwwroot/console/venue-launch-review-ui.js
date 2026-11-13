import { validDestination } from './connection-ui.js';
import { beginSeatLabels } from './readiness-ui.js';

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
const sealStates = { matched: '雙封存序號相符', pending: '管理端尚未完成雙封存', mismatch: '原錄製來源或封存序號不符' };

function projectSeal(result, roomIds, launchId) {
  const { schemaVersion, status, complete, childExited, cleanupCompleted, sessionId, streamId, finalWorld, finalCombatStream } = result;
  const header = finalWorld?.header;
  const worldSequence = finalWorld?.acceptedSequence, combatSequence = finalCombatStream?.acceptedSequence;
  if (schemaVersion !== 1 || status !== 'sealed-stopped' || complete !== true || childExited !== true || cleanupCompleted !== true
      || finalWorld?.complete !== true || finalCombatStream?.sealed !== true || header?.schemaVersion !== 1
      || header.sessionId !== sessionId || header.streamId !== streamId || finalCombatStream.streamId !== streamId
      || finalCombatStream.venueLaunchId !== launchId || !['Simulation', 'GameServer'].includes(header.origin)
      || header.origin !== finalCombatStream.origin || !Array.isArray(header.roomIds) || header.roomIds.join(',') !== roomIds.join(',')
      || !Number.isSafeInteger(worldSequence) || worldSequence < 1 || !Number.isSafeInteger(combatSequence) || combatSequence < 0)
    throw new Error('Invalid sealed report');
  return { origin: header.origin, combatSequence, worldSequence };
}

function projectReport(value) {
  const { schemaVersion, status, complete, readyPublished, instanceId, venueLaunchId, topology,
    sourceAttachment, endpointPublication, servers } = value ?? {};
  const ready = status === 'venue-ready';
  const terminal = status === 'venue-sealed-stopped';
  if (schemaVersion !== 1 || !isId(instanceId) || !['Independent', 'Linked'].includes(topology)
      || !Array.isArray(servers) || servers.length !== (topology === 'Linked' ? 1 : 5))
    throw new Error('Invalid venue report');
  if (terminal && (complete !== true || readyPublished !== true || !isId(venueLaunchId)
      || sourceAttachment !== 'confirmed' || endpointPublication !== 'confirmed')) throw new Error('Invalid sealed venue');
  if (!ready && !terminal && (status !== 'venue-incomplete' || complete !== false || readyPublished !== false || !isId(venueLaunchId)
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
    if (terminal) {
      if (!isId(streamId)) throw new Error('Missing original source');
      return { sessionId, roomIds: [...roomIds].sort(), streamId, udp: null, seal: projectSeal(result, roomIds, venueLaunchId) };
    }
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
  return { version: ready ? 2 : terminal ? 3 : 1, instanceId, launchId: ready ? null : venueLaunchId, topology, servers: targets };
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
        || (request.version === 3 && (row.endpointState !== 'not-checked'
          || (row.sourceState === 'original-source' ? !Object.hasOwn(sealStates, row.sealState) : row.sealState !== undefined)
          || (row.sealState === 'matched' && row.phase !== 'Ended')))
        || (request.version === 2 && row.endpointState === 'published'
          && (row.endpointAddress !== target.udp.address || row.endpointPort !== target.udp.port || row.addressMatched !== true))
        || (['published', 'endpoint-mismatch'].includes(row.endpointState)
          && !validDestination(row.endpointAddress, row.endpointPort)))
      throw new Error('Invalid room review');
  });
  return value;
}

export function mountVenueLaunchReview(getState, api, selectSession, focusRoster, reviewedBegin, openReplay) {
  const $ = suffix => document.getElementById('venue-launch-review-' + suffix);
  const panel = document.getElementById('venue-launch-review'), file = $('file'), button = $('check');
  let active = false, pending = false, opening = false, generation = 0, seatViews = [];
  const isCurrent = (attempt, epoch) => attempt === generation && epoch === getState().epoch && active
    && getState().actor?.role === 'Master';
  function update() {
    const state = getState();
    panel.hidden = !active || state.actor?.role !== 'Master';
    file.disabled = panel.hidden || state.busy || !!state.pending || pending || opening;
    button.disabled = file.disabled || file.files.length !== 1;
    for (const shortcut of $('rooms').querySelectorAll('button')) shortcut.disabled = file.disabled;
    if (panel.hidden) return;
    for (const { row, roomId, status } of seatViews) {
      const view = reviewedBegin(row, roomId);
      const groups = new Map();
      for (const [index, seat] of (view.seats ?? []).entries()) {
        if (!groups.has(seat)) groups.set(seat, []);
        groups.get(seat).push(index + 1);
      }
      const text = groups.size ? [...groups].map(([seat, numbers]) => `${beginSeatLabels[seat]} ${numbers.join('、')}`).join(' · ') : view.text;
      if (status.textContent !== text) status.textContent = text;
    }
  }
  function clear() {
    seatViews = [];
    $('summary').textContent = '';
    $('roster-status').textContent = '';
    $('rooms').replaceChildren();
  }
  async function openRoster(row, roomId) {
    const attempt = generation, epoch = getState().epoch;
    const current = () => isCurrent(attempt, epoch);
    const matches = session => session?.id === row.sessionId && session.roomIds?.includes(roomId)
      && session.state !== 'Ended' && session.combatStream?.streamId === row.streamId;
    opening = true;
    update();
    $('roster-status').textContent = '正在核對原場次名冊…';
    try {
      const session = await api(`/sessions/${row.sessionId}`);
      if (!current()) return;
      if (!matches(session)) throw new Error('Original source is no longer active');
      const { busy, pending } = getState();
      if (busy || pending) {
        $('roster-status').textContent = '請先確認目前命令的結果，再開啟名冊。';
        return;
      }
      await selectSession(row.sessionId, String(roomId));
      if (!current()) return;
      if (!matches(getState().session) || !focusRoster(row.sessionId, roomId)) throw new Error('Original roster selection changed');
      $('roster-status').textContent = `已開啟房間 ${roomId} 的原場次名冊。`;
    } catch {
      if (current()) $('roster-status').textContent = '無法開啟原場次名冊。請重新核對就緒檔。';
    } finally {
      if (current()) { opening = false; update(); }
    }
  }
  function show(review, request) {
    const allUnbound = review.servers.every(row => row.phase === 'Preparing' && row.sourceState === 'unbound');
    const allLive = review.servers.every(row => row.phase === 'Preparing' && row.sourceState === 'original-source'
      && row.endpointState === 'published' && row.recentSource === true);
    const allSealed = review.servers.every(row => row.sealState === 'matched');
    const summary = review.version === 3 ? (allSealed ? '五房原戰鬥與回放封存序號均相符。' : '請查看各房的原來源與封存結果。')
      : review.version === 2 && allLive && review.instanceVerified ? '取樣時五房原端點皆相符，並收到近期來源快照。'
      : allUnbound ? '原場次取樣時均在準備中且尚未登記來源。' : '已核對原場次。請查看各房來源與端點狀態。';
    const instance = review.instanceVerified ? '管理實例相符。' : '此管理服務未提供實例識別，已按原場次識別比對。';
    $('summary').textContent = `${instance}${summary} 取樣時間 ${new Date(review.observedAtUtc).toLocaleString('zh-TW')}。`;
    $('rooms').replaceChildren(...review.servers.map((row, index) => {
      const li = document.createElement('li');
      li.className = 'venue-launch-review-row';
      const endpoint = row.endpointAddress === null ? '' : ` · ${row.endpointAddress}:${row.endpointPort}`;
      const stream = row.streamId === null ? '' : ` · 來源 ${row.streamId}`;
      const address = endpoint && row.addressMatched === null ? ' · 報告無可比對的公告位址' : '';
      const recent = row.recentSource === null ? '' : row.recentSource ? ' · 有近期來源快照' : ' · 尚無近期來源快照';
      const detail = document.createElement('span');
      const evidence = review.version === 3 ? (sealStates[row.sealState] ?? '無法核對原封存')
        : `${endpointStates[row.endpointState]}${endpoint}${address}${recent}`;
      detail.textContent = `房間 ${row.roomIds.join('、')} · ${row.sessionId}${row.phase === null ? '' : ' · ' + phases[row.phase]} · ${sourceStates[row.sourceState]}${stream} · ${evidence}`;
      li.append(detail);
      if (review.version === 3 && review.instanceVerified && row.sealState === 'matched') {
        const { origin, worldSequence } = request.servers[index].seal;
        const actions = document.createElement('div');
        actions.className = 'button-row';
        for (const roomId of row.roomIds) {
          const shortcut = document.createElement('button');
          shortcut.type = 'button';
          shortcut.className = 'quiet small';
          shortcut.dataset.launchReviewReplay = roomId;
          shortcut.textContent = `回放房間 ${roomId}`;
          shortcut.addEventListener('click', () => {
            if (!shortcut.disabled && shortcut.isConnected)
              openReplay({ mode: 'replay', complete: true, sessionId: row.sessionId, streamId: row.streamId,
                origin, throughSequence: worldSequence, roomId });
          });
          actions.append(shortcut);
        }
        li.append(actions);
      }
      if (review.version === 2 && review.instanceVerified && row.sourceState === 'original-source'
          && row.endpointState === 'published' && ['Preparing', 'Running', 'Paused'].includes(row.phase)) {
        const actions = document.createElement('div');
        actions.className = 'button-row';
        for (const roomId of row.roomIds) {
          const shortcut = document.createElement('button');
          shortcut.type = 'button';
          shortcut.className = 'quiet small';
          shortcut.dataset.launchReviewRoster = roomId;
          shortcut.textContent = `查看房間 ${roomId} 名冊`;
          shortcut.addEventListener('click', () => { if (!shortcut.disabled) void openRoster(row, roomId); });
          if (row.phase === 'Preparing') {
            const item = document.createElement('div');
            item.className = 'venue-launch-room-readiness';
            const status = document.createElement('p');
            status.className = 'hint';
            status.dataset.launchReviewSeats = roomId;
            item.append(shortcut, status);
            seatViews.push({ row, roomId, status });
            actions.append(item);
          } else actions.append(shortcut);
        }
        li.append(actions);
      }
      return li;
    }));
  }
  file.addEventListener('change', () => {
    generation++; pending = false; clear(); update();
  });
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const selected = file.files[0], attempt = ++generation, epoch = getState().epoch;
    const current = () => isCurrent(attempt, epoch);
    pending = true; clear(); update();
    $('summary').textContent = '正在讀取啟動報告…';
    try {
      let request;
      try {
        if (!selected.size || selected.size > 65536) throw new Error('Invalid report size');
        request = projectReport(JSON.parse(await selected.text()));
      } catch {
        if (current()) $('summary').textContent = '請選擇 64 KiB 內的全館就緒檔、正常結束報告或含未確認狀態的第四版啟動報告。';
        return;
      }
      if (!current()) return;
      const review = verifyReply(await api('/venue/server-launch-review', 'POST', request), request);
      if (current()) show(review, request);
    } catch (error) {
      if (current()) $('summary').textContent = error.code === 'venue-launch-instance-mismatch'
        ? '報告屬於另一個管理實例。' : '無法核對原場次，請確認管理連線後重試。';
    } finally {
      if (current()) { pending = false; update(); }
    }
  });
  return { update, active(on) {
    active = on;
    if (!on) { generation++; pending = opening = false; file.value = ''; clear(); panel.open = false; }
    update();
  } };
}
