import { validDestination } from './connection-ui.js';

const messages = {
  'connection-invalid': '連線檔格式不符。請重新下載本席的連線 JSON。',
  'ticket-invalid': '票券無效、已過期或來自其他場次。請重新下載本席的連線檔。',
  'wrong-seat': '連線檔屬於其他房間或席位。請使用本席的連線檔。',
  'admission-changed': '此席已更換入場名額。請重新下載本席的連線檔。',
  'endpoint-unpublished': '遊戲來源尚未公告端點。請等待公告後重新核對。',
  'source-stale': '原遊戲來源尚無近期有效畫格。請等候來源更新後重新核對。',
  'connection-hash-mismatch': '連線檔的校正雜湊與本場鎖定值不符。請重新下載本席的連線檔。',
  'alignment-invalid': '校正檔內容無法核對。請選擇原始的房間校正 JSON。',
  'alignment-wrong-room': '校正檔屬於其他房間。請選擇本房鎖定的原始檔。',
  'alignment-hash-mismatch': '校正檔的原始位元組與鎖定版本不符。請換回本房鎖定的原始檔。'
};

export function mountSeatDeployment(state, api, mode) {
  const mr = mode === 'MR';
  const $ = id => document.getElementById(mode.toLowerCase() + '-deployment-' + id);
  const panel = $('panel'), form = $('form'), seat = $('seat'), connection = $('connection'), alignment = $('alignment');
  const submit = $('submit'), status = $('status');
  let active = false, sessionId, players = [], optionsKey = '', generation = 0, pending = false, expiryTimer;
  const selected = () => players.find(player => player.admissionId === seat.value);
  const seatLabel = player => `房間 ${player.roomId}／第 ${player.seat + 1} 席`;
  const say = message => { if (status.textContent !== message) status.textContent = message; };

  function clearResult() {
    generation++; pending = false; clearTimeout(expiryTimer);
    say(mr ? '請選擇席位與本次交付的兩份原始 JSON。' : '請選擇席位與本次交付的原始連線 JSON。');
  }
  function clearFiles() {
    connection.value = '';
    if (alignment) alignment.value = '';
    clearResult();
  }
  function reset() {
    sessionId = undefined; players = []; optionsKey = '';
    seat.replaceChildren(); clearFiles(); panel.hidden = true;
  }
  function update() {
    const { actor, session, selected: target, busy, pending: command } = state();
    if (!active || !actor || session?.id !== target || session?.environment.mode !== mode || session.state === 'Ended') {
      if (sessionId) reset();
      return;
    }
    if (sessionId !== session.id) { reset(); sessionId = session.id; }
    players = session.players.filter(player => (!mr || (player.headset === 'Quest3' && session.roomAlignment?.[`room${player.roomId}`]))
      && (actor.role === 'Master' || (actor.role === 'RoomController' && actor.roomId === player.roomId)))
      .sort((a, b) => a.roomId - b.roomId || a.seat - b.seat);
    const key = JSON.stringify(players.map(player => [player.admissionId, player.roomId, player.seat, player.name]));
    if (key !== optionsKey) {
      const previous = seat.value;
      seat.replaceChildren(new Option('請選擇要核對的席位', ''), ...players.map(player => new Option(`${seatLabel(player)} · ${player.name}`, player.admissionId)));
      if (players.some(player => player.admissionId === previous)) seat.value = previous;
      else clearFiles();
      optionsKey = key;
    }
    panel.hidden = players.length === 0;
    connection.disabled = !selected();
    if (alignment) alignment.disabled = connection.disabled;
    submit.disabled = busy || !!command || pending || !selected() || !connection.files.length || (mr && !alignment.files.length);
  }

  seat.addEventListener('change', () => { clearFiles(); update(); });
  for (const input of [connection, alignment].filter(Boolean)) input.addEventListener('change', () => { clearResult(); update(); });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const player = selected();
    if (submit.disabled || !player) return;
    const configFile = connection.files[0], alignmentFile = alignment?.files[0], label = seatLabel(player);
    if (configFile.size < 1 || configFile.size > 2048 || (mr && (alignmentFile.size < 1 || alignmentFile.size > 16384))) {
      say(`${label} · ${mr ? '連線檔上限 2 KiB，校正檔上限 16 KiB。請選擇兩份有內容的 JSON。' : '請選擇有內容且不超過 2 KiB 的連線 JSON。'}`);
      return;
    }
    const request = ++generation, id = sessionId;
    const applies = () => generation === request && active && state().selected === id && selected()?.admissionId === player.admissionId;
    const encode = async file => btoa(String.fromCharCode(...new Uint8Array(await file.arrayBuffer())));
    clearTimeout(expiryTimer); pending = true; say(`${label} · 正在核對…`); update();
    try {
      const [connectionFile, originalAlignment] = await Promise.all([encode(configFile), mr ? encode(alignmentFile) : undefined]);
      if (!applies()) return;
      const route = mr ? 'deployment-check' : 'vr-connection-check';
      const result = await api(`/sessions/${id}/rooms/${player.roomId}/players/${player.id}/${route}`, 'POST',
        { connectionFile, alignmentFile: originalAlignment }, undefined, mr ? undefined : player.admissionId);
      if (!applies()) return;
      if (result?.roomId !== player.roomId || result.seat !== player.seat) throw new Error('Unexpected deployment check seat');
      if (result.status === 'matched') {
        const expires = Date.parse(result.expiresAtUtc);
        if (!Number.isFinite(expires)) throw new Error('Missing deployment check expiry');
        let match = '連線檔與校正檔相符。';
        if (!mr) {
          if (!validDestination(result.address, result.port)) throw new Error('Missing verified VR endpoint');
          const local = result.address.startsWith('127.') ? '（僅同機）' : '';
          match = `連線檔與席位、公告端點相符。${result.address}:${result.port}${local}。`;
        }
        const remaining = expires - Date.now();
        const expired = () => say(`${label} · 票券已到期，請重新下載本席的連線檔。`);
        if (remaining <= 0) expired();
        else {
          say(`${label} · ${match}票券有效至 ${new Date(expires).toLocaleTimeString('zh-TW', { hour12: false })}。`);
          expiryTimer = setTimeout(() => { if (applies()) expired(); }, Math.min(remaining, 300000));
        }
      } else if (!mr && result.status === 'endpoint-mismatch' && validDestination(result.address, result.port))
        say(`${label} · 連線檔與公告端點不符。目前為 ${result.address}:${result.port}，請重新下載。`);
      else if (Object.hasOwn(messages, result.status)) say(`${label} · ${messages[result.status]}`);
      else throw new Error('Unknown deployment check result');
    } catch (error) {
      if (applies()) say(`${label} · ${error.status === 404 || error.status === 409
        ? '場次或名冊已變更。請重新整理後再核對。' : '未能完成核對，請確認連線後再試。'}`);
    } finally {
      if (applies()) { pending = false; update(); }
    }
  });

  return { reset, update, active(on) { active = on; if (on) update(); else reset(); } };
}
