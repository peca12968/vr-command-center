const guidance = {
  'vr-venue-session-missing': '等待本房的 VR 場次',
  'vr-venue-session-changed': '場次已更換',
  'vr-venue-topology-changed': '房間模式已變更',
  'vr-venue-endpoint-missing': '等待遊戲伺服器公布端點',
  'vr-venue-endpoint-stale': '等待原遊戲來源更新，暫停配票',
  'vr-venue-endpoint-reused': '獨立房間使用了相同端點',
  'vr-venue-source-changed': '遊戲來源已變更',
  'vr-venue-roster-incomplete': '等待本房五個席位',
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

export function mountVrVenueTickets(state, api, download) {
  const $ = name => document.getElementById('vr-venue-' + name);
  const panel = $('panel'), read = $('read'), issue = $('issue'), rows = $('rooms'), status = $('status');
  const files = $('files');
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

  function update() {
    const { actor, busy, pending: command } = state();
    panel.hidden = !active || actor?.role !== 'Master';
    if (panel.hidden && (pending || preview)) clear();
    if (version && rosterVersion() !== version) clear('房間或名冊已變更，請重新讀取五房名冊。');
    $('title').textContent = mixedVenue() ? 'VR／MR 混合五房配票' : 'VR 五房配票';
    read.disabled = panel.hidden || busy || !!command || pending;
    const inputs = [...files.querySelectorAll('input')];
    for (const input of inputs) input.disabled = read.disabled;
    issue.disabled = read.disabled || !preview?.ready || inputs.some(input => !input.files.length);
  }

  function begin(message) {
    version = rosterVersion();
    const attempt = ++generation;
    pending = true; status.textContent = message; update();
    return { current: () => generation === attempt && version === rosterVersion(),
      finish() { if (generation === attempt) { pending = false; update(); } } };
  }

  read.addEventListener('click', async () => {
    if (read.disabled) return;
    const mixed = mixedVenue();
    clear();
    const request = begin('正在讀取五房名冊與端點…');
    try {
      const value = await api(mixed ? '/mixed-deployment/venue' : '/vr-deployment/venue');
      if (!request.current()) return;
      if (!Array.isArray(value?.rooms) || value.rooms.length !== 5 || value.rooms.some(room => !Array.isArray(room.seats)))
        throw new Error('Invalid venue preview');
      preview = { ...value, mixed };
      for (const room of value.rooms) {
        const item = document.createElement('li'), destination = room.endpoint;
        const endpoint = destination ? `${destination.address}:${destination.port}${destination.address.startsWith('127.') ? '（僅本機）' : ''}` : '端點未公布';
        const seats = room.seats.map(seat => `${seat.number} ${seat.name}`).join('、');
        const note = room.problem ? ' · ' + (guidance[room.problem] ?? '需重新讀取') : '';
        item.textContent = `房間 ${room.roomId}${mixed && room.mode ? ' · ' + room.mode : ''} · ${room.missionName ?? '未準備場次'} · ${endpoint} · ${room.seats.length}/5 席${seats ? ' · ' + seats : ''}${note}`;
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
      status.textContent = value.ready ? `${mixed ? 'VR／MR 混合獨立場' : value.topology === 'Linked' ? '五房合併' : '五房獨立'} · 已讀取 25 席，請核對後配票。` : '請確認各房列出的條件，再重新讀取。';
    } catch {
      if (request.current()) status.textContent = '無法讀取五房名冊，請重試。';
    } finally { request.finish(); }
  });

  issue.addEventListener('click', async () => {
    if (issue.disabled || !preview?.ready || rosterVersion() !== version) { update(); return; }
    const { mixed, rooms: confirmedRooms, topology } = preview;
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
    const request = begin('正在核對名冊並產生 25 份連線檔…');
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
      const route = mixed ? '/mixed-deployment/venue' : '/vr-deployment/venue';
      const zip = await api(route + '-bundle', 'POST', body, undefined, undefined, 'blob');
      if (!request.current()) return;
      if (zip.type !== 'application/zip') throw new Error('Invalid venue archive');
      const current = await api(route);
      if (!request.current()) return;
      if (!current?.ready || current.topology !== topology || JSON.stringify(current.rooms) !== JSON.stringify(confirmedRooms)) {
        clear('場次、端點或名冊已變更，未下載連線檔。請重新讀取五房名冊。');
        update(); return;
      }
      download(mixed ? 'vr-mr-venue-deployment.zip' : 'vr-venue-connections.zip', zip);
      status.textContent = '已下載五房連線檔。票券有效五分鐘，請依房間與席位個別交付。';
    } catch (error) {
      if (request.current()) {
        const reason = Object.hasOwn(guidance, error.code) && Number.isInteger(error.roomId)
          ? `房間 ${error.roomId} · ${guidance[error.code]}。請重新讀取五房名冊。` : '無法下載五房連線檔，請重新讀取後重試。';
        clear(reason); update();
      }
    } finally { request.finish(); }
  });

  return { update, active(on) { active = on; if (!on) clear(); update(); } };
}
