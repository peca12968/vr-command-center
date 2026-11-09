const rooms = [1, 2, 3, 4, 5];
const guidance = {
  'venue-session-changed': '場次已變更，請重新整理房間與場次。',
  'venue-alignment-unlocked': '請先鎖定本房校正檔。',
  'venue-alignment-mismatch': '校正檔不符，請選擇本房鎖定的原始 JSON。',
  'venue-endpoint-missing': '尚未公布端點，請先啟動本房的遊戲伺服器。',
  'venue-endpoint-loopback': '公布的端點僅能同機使用，請確認本房的場館端點。',
  'venue-endpoint-reused': '端點與另一房相同，獨立場次須使用不同端點。',
  'venue-roster-reused': '名冊與另一房重複，請核對各席玩家。',
  'venue-roster-changed': '名冊已變更，請重新整理後核對五個 Quest 3 席位。'
};

export function mountMrVenueBundle(state, api, download) {
  const $ = name => document.getElementById('mr-venue-' + name);
  const panel = $('panel'), form = $('form'), submit = $('submit'), status = $('status');
  const rows = rooms.map(roomId => {
    const label = document.createElement('label'), input = document.createElement('input');
    const caption = document.createElement('span');
    input.type = 'file'; input.accept = '.json,application/json'; input.id = `mr-venue-alignment-${roomId}`;
    label.append(caption, input); $('files').append(label);
    input.addEventListener('change', () => { status.textContent = ''; update(); });
    return { roomId, input, caption };
  });
  let active = false, target = '', roster = '', generation = 0, pending = false;

  function plan() {
    const { actor, session, selected, sessions, rooms: occupancy } = state();
    if (!active || actor?.role !== 'Master' || session?.id !== selected || session?.environment.mode !== 'MR' || session.state === 'Ended') return null;
    const topology = session.mode;
    const sources = rows.map(({ roomId }) => {
      const id = occupancy.find(room => room.id === roomId)?.sessionId;
      const source = id === session.id ? session : sessions.find(view => view.id === id);
      return source?.mode === topology && source.state !== 'Ended' && source.environment.mode === 'MR'
        && (topology === 'Independent' || source.id === selected) ? source : null;
    });
    const entries = rows.map(({ roomId }, index) => {
      const source = sources[index];
      const players = source?.players.filter(player => player.roomId === roomId && player.headset === 'Quest3') ?? [];
      return { roomId, sessionId: source?.id, hash: source?.roomAlignment?.[`room${roomId}`],
        players: players.map(player => ({ playerId: player.id, admissionId: player.admissionId })) };
    });
    return { topology, entries, target: JSON.stringify([topology, ...entries.map(entry => [entry.sessionId, entry.hash])]),
      roster: JSON.stringify(entries.map(entry => entry.players)), ready: entries.every(entry => entry.hash && entry.players.length === 5) };
  }

  function reset() {
    generation++; pending = false; target = roster = '';
    panel.hidden = true; status.textContent = '';
    for (const { input } of rows) input.value = '';
  }

  function update() {
    const current = plan();
    if (!current) { if (target) reset(); return; }
    if (target !== current.target) { reset(); target = current.target; }
    if (roster !== current.roster) { roster = current.roster; status.textContent = ''; }
    panel.hidden = false;
    $('topology').textContent = current.topology === 'Linked' ? '五房合併場次' : '五個獨立場次';
    const locked = state().busy || !!state().pending || pending;
    for (const [index, { roomId, input, caption }] of rows.entries()) {
      const { sessionId, hash, players } = current.entries[index];
      caption.textContent = `房間 ${roomId} · ${!sessionId ? '等待 MR 場次' : !hash ? '等待鎖定校正檔' : `${players.length}/5 Quest 3 席`}`;
      input.disabled = locked || !hash;
    }
    submit.disabled = locked || !current.ready || rows.some(({ input }) => !input.files.length);
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const current = plan();
    if (submit.disabled || !current?.ready) return;
    const files = rows.map(({ input }) => input.files[0]);
    const bad = files.findIndex(file => !file || file.size < 1 || file.size > 16384);
    if (bad >= 0) { status.textContent = `房間 ${bad + 1} · 請選擇 16 KiB 以內的原始 JSON。`; return; }
    const request = ++generation;
    const applies = () => {
      const live = plan();
      return generation === request && live?.target === current.target && live.roster === current.roster;
    };
    pending = true; status.textContent = '正在產生五房部署包…'; update();
    try {
      const alignments = await Promise.all(files.map(async file => btoa(String.fromCharCode(...new Uint8Array(await file.arrayBuffer())))));
      if (!applies()) return;
      const bundle = await api('/mr-deployment/venue-bundle', 'POST', { topology: current.topology,
        rooms: current.entries.map(({ roomId, sessionId, players }, index) => ({ roomId, sessionId, players, alignmentFile: alignments[index] })) },
      undefined, undefined, 'blob');
      if (!applies()) return;
      if (bundle.type !== 'application/zip') throw new Error('Expected a venue ZIP download.');
      download('quest-mr-venue.zip', bundle);
      status.textContent = '已下載五房部署包。票券有效五分鐘，請依房間與席位個別交付。';
    } catch (error) {
      if (applies()) status.textContent = Object.hasOwn(guidance, error.code) && Number.isInteger(error.roomId)
        ? `房間 ${error.roomId} · ${guidance[error.code]}` : '未能下載部署包，請確認場次與連線後再試。';
    } finally {
      if (generation === request) { pending = false; update(); }
    }
  });

  return { update, active(on) { active = on; if (on) update(); else reset(); } };
}
