const $ = id => document.getElementById(id);
const hashPattern = /^[a-f0-9]{64}$/;
const fileLimit = 16 * 1024;
const text = (node, value) => { if (node.textContent !== value) node.textContent = value; };

export function mountAlignmentPins({ state, checkFile, pin }) {
  const panel = $('mr-alignment-pins'), rooms = $('mr-alignment-rooms');
  const form = $('mr-alignment-form'), submit = $('mr-alignment-submit'), summary = $('mr-alignment-summary');
  let active = false, target = null;
  const rows = new Map();

  function reset() {
    target = null;
    rows.clear();
    rooms.replaceChildren();
    panel.hidden = true;
  }

  function current() {
    const value = state(), session = value.session;
    return active && value.actor?.role === 'Master' && session && session.id === value.selected && session.environment.mode === 'MR'
      ? session : null;
  }

  function editable(session) {
    return session?.state === 'Preparing' && !session.combatStream && !session.roomAlignment;
  }

  function createRow(room) {
    const row = document.createElement('li'), label = document.createElement('label');
    const title = document.createElement('strong'), input = document.createElement('input');
    const status = document.createElement('p'), digest = document.createElement('code');
    title.textContent = `房間 ${room}`;
    input.type = 'file'; input.accept = '.json,application/json'; input.id = `mr-alignment-file-${room}`;
    input.setAttribute('aria-describedby', `mr-alignment-status-${room}`);
    status.id = `mr-alignment-status-${room}`; status.className = 'hint'; status.setAttribute('role', 'status');
    label.append(title, input);
    row.append(label, status, digest); rooms.append(row);
    const entry = { input, status, digest, draft: null };
    rows.set(room, entry);
    input.addEventListener('change', () => validate(room, entry));
  }

  function update() {
    const session = current();
    if (!session) { if (target) reset(); return; }
    if (target !== session.id) {
      reset(); target = session.id;
      for (const room of session.roomIds) createRow(room);
    }
    panel.hidden = false;
    const editing = editable(session), locked = state().busy || !!state().pending;
    let checked = 0;
    for (const [room, row] of rows) {
      if (!editing && row.draft) { row.draft = null; row.input.value = ''; }
      const stored = session.roomAlignment?.[`room${room}`];
      const pinned = hashPattern.test(stored ?? '');
      const draftHash = row.draft?.hash;
      if (draftHash) checked++;
      row.input.hidden = !editing;
      row.input.disabled = !editing || locked;
      text(row.status, pinned ? '已鎖定' : row.draft?.status || (editing ? '尚未選擇校正檔' : '未鎖定'));
      text(row.digest, pinned ? stored : draftHash || '');
      row.digest.hidden = !row.digest.textContent;
    }
    text(summary, editing ? `已核對 ${checked}／${rows.size} 房。鎖定後請用這些原始檔案部署頭盔。`
      : session.roomAlignment ? (session.state === 'Preparing' && !session.combatStream
        ? '校正檔已鎖定，可依場次設定啟動伺服器。' : '下方為本場各房已鎖定的校正檔。')
      : '此場次已綁定遊戲來源或離開準備階段。請建立新場次以鎖定校正檔。');
    submit.hidden = !editing;
    submit.disabled = !editing || locked || checked !== rows.size || !rows.size;
  }

  async function validate(room, entry) {
    const session = current(), file = entry.input.files[0];
    if (!editable(session) || state().busy || state().pending || rows.get(room) !== entry) return;
    if (!file) { entry.draft = null; update(); return; }
    const draft = { status: '正在核對原始檔案…' };
    entry.draft = draft;
    const applies = () => current()?.id === session.id && rows.get(room) === entry && entry.draft === draft;
    try {
      if (file.size < 1 || file.size > fileLimit) { draft.status = '請選擇 1 至 16,384 位元組的校正 JSON。'; return; }
      update();
      const result = await checkFile(file);
      if (!applies()) return;
      if (result?.roomId !== room) { draft.status = `此檔案屬於房間 ${result?.roomId ?? '未知'}。`; return; }
      if (!hashPattern.test(result.sha256 ?? '')) { draft.status = '校正檔核對結果不完整。'; return; }
      draft.hash = result.sha256;
      draft.status = '已核對，可鎖定';
    } catch (error) {
      if (applies()) draft.status = error.status === 400 ? '校正檔未通過核對。請使用原始的房間校正 JSON。' : '無法完成校正檔核對，請重新選檔。';
    } finally { if (applies()) update(); }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const session = current();
    if (submit.disabled || !editable(session)) return;
    if (!confirm(`鎖定場次「${session.mission.definition.name}」的房間 ${session.roomIds.join('、')} 校正檔？變更檔案需建立新場次。`)) return;
    const pins = Object.fromEntries([...rows].map(([room, row]) => [`room${room}`, row.draft.hash]));
    pin(session.id, pins, session.sequence);
  });

  return { update, reset, active(on) { active = on; update(); } };
}
