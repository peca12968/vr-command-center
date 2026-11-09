const guidance = {
  'vr-venue-session-missing': '等待本房的 VR 場次',
  'vr-venue-session-changed': '場次已更換',
  'vr-venue-topology-changed': '房間模式已變更',
  'vr-venue-endpoint-missing': '等待遊戲伺服器公布端點',
  'vr-venue-endpoint-reused': '獨立房間使用了相同端點',
  'vr-venue-source-changed': '遊戲來源已變更',
  'vr-venue-roster-incomplete': '等待本房五個席位',
  'vr-venue-roster-changed': '玩家入場名冊已變更',
  'vr-venue-roster-reused': '玩家或入場資料與另一房重複'
};

export function mountVrVenueTickets(state, api, download) {
  const $ = name => document.getElementById('vr-venue-' + name);
  const panel = $('panel'), read = $('read'), issue = $('issue'), rows = $('rooms'), status = $('status');
  const previewRoute = '/vr-deployment/venue';
  let active = false, generation = 0, pending = false, preview = null, version = '';

  function rosterVersion() {
    const { rooms, sessions, epoch } = state();
    return JSON.stringify([epoch, ...rooms.map(room => {
      const source = sessions.find(session => session.id === room.sessionId);
      return [room.id, room.sessionId, source?.environment.mode, source?.mode,
        source?.players.filter(player => player.roomId === room.id).map(player => [player.id, player.admissionId, player.seat])];
    })]);
  }

  function clear(message = '') {
    generation++; pending = false; preview = null; version = '';
    rows.replaceChildren(); status.textContent = message;
  }

  function update() {
    const { actor, busy, pending: command } = state();
    panel.hidden = !active || actor?.role !== 'Master';
    if (panel.hidden && (pending || preview)) clear();
    if (version && rosterVersion() !== version) clear('房間或名冊已變更，請重新讀取五房名冊。');
    read.disabled = panel.hidden || busy || !!command || pending;
    issue.disabled = read.disabled || !preview?.ready;
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
    clear();
    const request = begin('正在讀取五房名冊與端點…');
    try {
      const value = await api(previewRoute);
      if (!request.current()) return;
      if (!Array.isArray(value?.rooms) || value.rooms.length !== 5 || value.rooms.some(room => !Array.isArray(room.seats)))
        throw new Error('Invalid venue preview');
      preview = value;
      for (const room of value.rooms) {
        const item = document.createElement('li'), destination = room.endpoint;
        const endpoint = destination ? `${destination.address}:${destination.port}${destination.address.startsWith('127.') ? '（僅本機）' : ''}` : '端點未公布';
        const seats = room.seats.map(seat => `${seat.number} ${seat.name}`).join('、');
        const note = room.problem ? ' · ' + (guidance[room.problem] ?? '需重新讀取') : '';
        item.textContent = `房間 ${room.roomId} · ${room.missionName ?? '未準備 VR 場次'} · ${endpoint} · ${room.seats.length}/5 席${seats ? ' · ' + seats : ''}${note}`;
        rows.append(item);
      }
      status.textContent = value.ready ? `${value.topology === 'Linked' ? '五房合併' : '五房獨立'} · 已讀取 25 席，請核對後配票。` : '請確認各房列出的條件，再重新讀取。';
    } catch {
      if (request.current()) status.textContent = '無法讀取五房名冊，請重試。';
    } finally { request.finish(); }
  });

  issue.addEventListener('click', async () => {
    if (issue.disabled || !preview?.ready || rosterVersion() !== version) { update(); return; }
    const body = { topology: preview.topology, rooms: preview.rooms.map(room => ({
      roomId: room.roomId, sessionId: room.sessionId, streamId: room.endpoint.streamId,
      players: room.seats.map(({ playerId, admissionId }) => ({ playerId, admissionId }))
    })) };
    const request = begin('正在核對名冊並產生 25 份連線檔…');
    try {
      const zip = await api(previewRoute + '-bundle', 'POST', body, undefined, undefined, 'blob');
      if (!request.current()) return;
      if (zip.type !== 'application/zip') throw new Error('Invalid venue archive');
      download('vr-venue-connections.zip', zip);
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
