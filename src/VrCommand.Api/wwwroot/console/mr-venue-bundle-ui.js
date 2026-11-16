import { roomTicketDestination } from './readiness-ui.js';

const rooms = [1, 2, 3, 4, 5];
const guidance = {
  'venue-session-changed': '場次已變更，請重新整理房間與場次。',
  'venue-alignment-unlocked': '請先鎖定本房校正檔。',
  'venue-alignment-mismatch': '校正檔不符，請選擇本房鎖定的原始 JSON。',
  'venue-endpoint-missing': '尚未公布端點，請先啟動本房的遊戲伺服器。',
  'venue-endpoint-stale': '等待原遊戲來源更新，暫停配票。',
  'venue-endpoint-loopback': '公布的端點僅能同機使用，請確認本房的場館端點。',
  'venue-endpoint-reused': '端點與另一房相同，獨立場次須使用不同端點。',
  'venue-source-changed': '原遊戲端點已變更或暫未確認。',
  'venue-roster-reused': '名冊與另一房重複，請核對各席玩家。',
  'venue-roster-changed': '名冊已變更，請重新整理後核對五個 Quest 3 席位。'
};

function destinationProblem(destination) {
  if (!destination) return 'venue-endpoint-missing';
  if (destination.endpoint.address.startsWith('127.')) return 'venue-endpoint-loopback';
  return destination.live === false ? 'venue-endpoint-stale' : null;
}

export function mountMrVenueBundle(state, api, download, ticketDestination) {
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

  function plan(latestSessions) {
    const { actor, session, selected, sessions, rooms: occupancy } = state();
    if (!active || actor?.role !== 'Master' || session?.id !== selected || session?.environment.mode !== 'MR' || session.state === 'Ended') return null;
    const topology = session.mode;
    const entries = rows.map(({ roomId }) => {
      const room = occupancy.find(room => room.id === roomId);
      const id = room?.sessionId;
      const source = latestSessions ? latestSessions.find(view => view.id === id)
        : id === session.id ? session : sessions.find(view => view.id === id);
      if (source?.mode !== topology || source.state === 'Ended' || source.environment.mode !== 'MR'
          || (topology === 'Linked' && source.id !== selected)) return { roomId, players: [] };
      const players = source.players.filter(player => player.roomId === roomId && player.headset === 'Quest3');
      return { roomId, room, source, sessionId: source.id, hash: source.roomAlignment?.[`room${roomId}`],
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
    let endpointsReady = true;
    for (const [index, { roomId, input, caption }] of rows.entries()) {
      const { room, source, hash, players } = current.entries[index];
      const destination = ticketDestination(room, source), problem = destinationProblem(destination);
      endpointsReady &&= !problem;
      const endpoint = destination?.endpoint;
      const captionText = `房間 ${roomId} · ${!source ? '等待 MR 場次' : !hash ? '等待鎖定校正檔' : `${players.length}/5 Quest 3 席`}`
        + (endpoint ? ` · UDP ${endpoint.address}:${endpoint.port}` : '') + (source && problem ? ` · ${guidance[problem]}` : '');
      if (caption.textContent !== captionText) caption.textContent = captionText;
      input.disabled = locked || !hash;
    }
    submit.disabled = locked || !current.ready || !endpointsReady || rows.some(({ input }) => !input.files.length);
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const current = plan();
    if (submit.disabled || !current?.ready) return;
    const destinations = current.entries.map(({ room, source }) => ticketDestination(room, source));
    if (destinations.some(destinationProblem)) { update(); return; }
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
      undefined, undefined, 'venue-ticket-archive');
      if (!applies()) return;
      const latest = plan(await api('/sessions'));
      if (!applies()) return;
      if (!latest?.ready || latest.target !== current.target || latest.roster !== current.roster) {
        status.textContent = '場次或名冊已變更，未下載部署包。請重新整理後核對五個房間。';
        return;
      }
      const began = performance.now();
      const readiness = await api('/rooms/readiness');
      if (!applies()) return;
      for (const [index, { roomId, room, source }] of latest.entries.entries()) {
        const destination = roomTicketDestination(readiness, room, source, performance.now() - began);
        const endpoint = destination?.endpoint, original = destinations[index].endpoint;
        const problem = destinationProblem(destination) || (endpoint.streamId !== original.streamId
          || endpoint.address !== original.address || endpoint.port !== original.port ? 'venue-source-changed' : null);
        if (problem) {
          status.textContent = `房間 ${roomId} · ${guidance[problem]} 未下載部署包。`;
          return;
        }
      }
      download('quest-mr-venue.zip', bundle);
      status.textContent = '已下載五房部署包。票券有效五分鐘，請依房間與席位個別交付。';
    } catch (error) {
      if (applies()) status.textContent = error.code === 'venue-archive-unverified' ? error.message : Object.hasOwn(guidance, error.code) && Number.isInteger(error.roomId)
        ? `房間 ${error.roomId} · ${guidance[error.code]}` : '未能下載部署包，請確認場次與連線後再試。';
    } finally {
      if (generation === request) { pending = false; update(); }
    }
  });

  return { update, active(on) { active = on; if (on) update(); else reset(); } };
}
