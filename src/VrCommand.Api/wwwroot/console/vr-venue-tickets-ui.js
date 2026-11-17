const guidance = {
  'vr-venue-session-missing': '等待本房的 VR 場次',
  'vr-venue-session-changed': '場次已更換',
  'vr-venue-topology-changed': '房間模式已變更',
  'vr-venue-endpoint-missing': '等待遊戲伺服器公布端點',
  'vr-venue-endpoint-stale': '等待原遊戲來源更新，暫停配票',
  'vr-venue-endpoint-reused': '獨立房間使用了相同端點',
  'vr-venue-source-changed': '遊戲來源已變更',
  'vr-venue-roster-incomplete': '本房名冊與選取席數不符',
  'vr-venue-roster-changed': '玩家入場名冊已變更',
  'vr-venue-roster-reused': '玩家或入場資料與另一房重複',
  'venue-session-changed': '場次已更換',
  'venue-endpoint-missing': '等待遊戲伺服器公布端點',
  'venue-endpoint-stale': '等待原遊戲來源更新，暫停配票',
  'venue-endpoint-loopback': '端點僅能同機使用',
  'venue-endpoint-reused': '獨立房間使用了相同端點',
  'venue-source-changed': '遊戲來源已變更',
  'venue-roster-changed': '等待本房五席並核對最新名冊',
  'venue-roster-reused': '玩家或入場資料與另一房重複',
  'venue-alignment-unlocked': '等待鎖定本房校正檔',
  'venue-alignment-mismatch': '請選擇本房鎖定的原始校正檔'
};

const staleProblems = new Set(['vr-venue-endpoint-stale', 'venue-endpoint-stale']);
const roomScope = rooms => JSON.stringify(rooms.map(({ ticketSourceLive, problem, ...scope }) => scope));

export function mountVrVenueTickets(state, api, download, ticketSourceLive) {
  const $ = name => document.getElementById('vr-venue-' + name);
  const panel = $('panel'), read = $('read'), issue = $('issue'), rows = $('rooms'), status = $('status');
  const files = $('files'), size = $('size');
  let active = false, generation = 0, pending = false, preview = null, version = '';

  function roomSources() {
    const { rooms, sessions } = state();
    return rooms.map(room => [room, sessions.find(session => session.id === room.sessionId)]);
  }
  function mixedVenue() {
    const sources = roomSources();
    return sources.length === 5 && sources.every(([, source]) => source?.mode === 'Independent' && source.state !== 'Ended')
      && new Set(sources.map(([, source]) => source.environment.mode)).size === 2;
  }
  function rosterVersion() {
    return JSON.stringify([state().epoch, ...roomSources().map(([room, source]) => {
      return [room.id, room.sessionId, source?.environment.mode, source?.mode, source?.roomAlignment?.[`room${room.id}`],
        source?.players.filter(player => player.roomId === room.id).map(player => [player.id, player.admissionId, player.seat, player.headset])];
    })]);
  }

  function clear(message = '') {
    generation++; pending = false; preview = null; version = '';
    rows.replaceChildren(); files.replaceChildren(); files.hidden = true; status.textContent = message;
  }

  function roomProblem(room) {
    if (room.problem && !staleProblems.has(room.problem)) return room.problem;
    if (typeof room.ticketSourceLive !== 'boolean') return room.problem;
    return ticketSourceLive(room.roomId, room.sessionId, room.endpoint) ? null
      : preview.mixed ? 'venue-endpoint-stale' : 'vr-venue-endpoint-stale';
  }

  function update() {
    const { actor, busy, pending: command } = state();
    panel.hidden = !active || actor?.role !== 'Master';
    if (panel.hidden && (pending || preview)) clear();
    if (version && rosterVersion() !== version) clear('房間或名冊已變更，請重新讀取五房名冊。');
    const mixed = mixedVenue();
    $('title').textContent = mixed ? 'VR／MR 混合五房配票' : 'VR 五房配票';
    $('size-field').hidden = mixed;
    read.disabled = panel.hidden || busy || !!command || pending;
    size.disabled = mixed || read.disabled;
    const inputs = [...files.querySelectorAll('input')];
    for (const input of inputs) input.disabled = read.disabled;
    const problems = preview?.rooms.map(roomProblem) ?? [];
    const ready = preview && (preview.ready || preview.rooms.some(room => staleProblems.has(room.problem))) && problems.every(problem => !problem);
    for (const [index, problem] of problems.entries()) {
      const note = problem ? ' · ' + (guidance[problem] ?? '需重新讀取') : '';
      const item = rows.children[index]?.lastElementChild;
      if (item && item.textContent !== note) item.textContent = note;
    }
    if (!pending && preview?.showStatus) {
      const mode = preview.mixed ? 'VR／MR 混合獨立場' : preview.topology === 'Linked' ? '五房合併' : '五房獨立';
      const message = ready ? `${mode} · 已讀取 ${5 * preview.playersPerRoom} 席，請核對後配票。`
        : problems.some(problem => staleProblems.has(problem)) ? '請確認各房列出的條件，原遊戲來源恢復後可繼續配票。'
          : '請確認各房列出的條件，再重新讀取。';
      if (status.textContent !== message) status.textContent = message;
    }
    issue.disabled = read.disabled || !ready || inputs.some(input => !input.files.length);
  }

  function begin(message) {
    version = rosterVersion();
    const attempt = ++generation;
    pending = true; status.textContent = message; update();
    return { current: () => generation === attempt && version === rosterVersion(),
      finish() { if (generation === attempt) { pending = false; update(); } } };
  }

  size.addEventListener('change', () => { clear('請依選取席數重新讀取五房名冊。'); update(); });

  read.addEventListener('click', async () => {
    if (read.disabled) return;
    const mixed = mixedVenue(), playersPerRoom = mixed ? 5 : Number(size.value);
    const route = mixed ? '/mixed-deployment/venue' : '/vr-deployment/venue';
    const query = playersPerRoom === 5 ? '' : `?playersPerRoom=${playersPerRoom}`;
    clear();
    const request = begin('正在讀取五房名冊與端點…');
    try {
      const value = await api(route + query);
      if (!request.current()) return;
      if (!Array.isArray(value?.rooms) || value.rooms.length !== 5 || value.rooms.some(room => !Array.isArray(room.seats)))
        throw new Error('Invalid venue preview');
      preview = { ...value, mixed, playersPerRoom, route, query, showStatus: true };
      for (const room of value.rooms) {
        const item = document.createElement('li'), destination = room.endpoint;
        const endpoint = destination ? `${destination.address}:${destination.port}${destination.address.startsWith('127.') ? '（僅本機）' : ''}` : '端點未公布';
        const seats = room.seats.map(seat => `${seat.number} ${seat.name}`).join('、');
        item.textContent = `房間 ${room.roomId}${mixed && room.mode ? ' · ' + room.mode : ''} · ${room.missionName ?? '未準備場次'} · ${endpoint} · ${room.seats.length}/${playersPerRoom} 席${seats ? ' · ' + seats : ''}`;
        item.append(document.createElement('span'));
        rows.append(item);
        if (mixed && room.mode === 'MR' && room.alignmentSha256) {
          const label = document.createElement('label'), input = document.createElement('input');
          input.type = 'file'; input.accept = '.json,application/json'; input.id = `mixed-venue-alignment-${room.roomId}`;
          input.addEventListener('change', update);
          label.htmlFor = input.id; label.textContent = `房間 ${room.roomId} 的原始校正 JSON`;
          label.append(input); files.append(label);
        }
      }
      files.hidden = files.children.length === 0;
    } catch {
      if (request.current()) status.textContent = '無法讀取五房名冊，請重試。';
    } finally { request.finish(); }
  });

  issue.addEventListener('click', async () => {
    if (issue.disabled || !preview || preview.rooms.some(roomProblem) || rosterVersion() !== version) { update(); return; }
    const { mixed, rooms: confirmedRooms, topology, playersPerRoom, route, query } = preview;
    const confirmations = mixed ? confirmedRooms.filter(room => room.mode === 'MR').map(room => [
      room.roomId, document.getElementById(`mixed-venue-alignment-${room.roomId}`)?.files[0]
    ]) : [];
    const bad = confirmations.find(([, file]) => !file || file.size < 1 || file.size > 16384);
    if (bad) { status.textContent = `房間 ${bad[0]} · 請選擇 16 KiB 以內的原始 JSON。`; return; }
    const body = { rooms: confirmedRooms.map(room => ({
      roomId: room.roomId, sessionId: room.sessionId, streamId: room.endpoint.streamId,
      players: room.seats.map(({ playerId, admissionId }) => ({ playerId, admissionId }))
    })) };
    if (!mixed) body.topology = topology;
    if (playersPerRoom !== 5) body.playersPerRoom = playersPerRoom;
    preview.showStatus = false;
    const request = begin(`正在核對名冊並產生 ${5 * playersPerRoom} 份連線檔…`);
    try {
      if (mixed) {
        const alignments = new Map(await Promise.all(confirmations.map(async ([roomId, file]) => [
          roomId, btoa(String.fromCharCode(...new Uint8Array(await file.arrayBuffer())))
        ])));
        if (!request.current()) return;
        for (const [index, room] of confirmedRooms.entries()) {
          body.rooms[index].mode = room.mode;
          if (alignments.has(room.roomId)) body.rooms[index].alignmentFile = alignments.get(room.roomId);
        }
      }
      const zip = await api(route + '-bundle', 'POST', body, undefined, undefined, 'venue-ticket-archive');
      if (!request.current()) return;
      const current = await api(route + query);
      if (!request.current()) return;
      if (!current?.ready || current.topology !== topology || !Array.isArray(current.rooms) || roomScope(current.rooms) !== roomScope(confirmedRooms)) {
        clear('場次、端點或名冊已變更，未下載連線檔。請重新讀取五房名冊。');
        update(); return;
      }
      download(mixed ? 'vr-mr-venue-deployment.zip' : 'vr-venue-connections.zip', zip);
      status.textContent = '已下載五房連線檔。票券有效五分鐘，請依房間與席位個別交付。';
    } catch (error) {
      if (request.current()) {
        const reason = error.code === 'venue-archive-unverified' ? error.message : Object.hasOwn(guidance, error.code) && Number.isInteger(error.roomId)
          ? `房間 ${error.roomId} · ${guidance[error.code]}。請重新讀取五房名冊。` : '無法下載五房連線檔，請重新讀取後重試。';
        clear(reason); update();
      }
    } finally { request.finish(); }
  });

  return { update, active(on) { active = on; if (!on) clear(); update(); } };
}
