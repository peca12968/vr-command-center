import { maxRosterCsvBytes, readVenueRosterCsv, venueRosterCsvTemplate } from './venue-roster-csv.js';

export function mountVenueRoster({ getState, canRegister, uuid, download, register }) {
  const panel = document.getElementById('venue-roster-admissions');
  const table = document.getElementById('venue-roster-seats');
  const submit = document.getElementById('venue-roster-register');
  const status = document.getElementById('venue-roster-status');
  const fileInput = document.getElementById('venue-roster-csv');
  const importButton = document.getElementById('venue-roster-import');
  const importStatus = document.getElementById('venue-roster-import-status');
  const template = document.getElementById('venue-roster-template');
  let reading = null;
  const rows = Array.from({ length: 25 }, (_, index) => {
    const roomId = Math.floor(index / 5) + 1, seat = index % 5;
    const tr = table.insertRow();
    const label = `房間 ${roomId} · 第 ${seat + 1} 席`;
    const name = document.createElement('input'), headset = document.createElement('select');
    name.type = 'text'; name.maxLength = 80; name.autocomplete = 'off';
    name.disabled = headset.disabled = true;
    name.setAttribute('aria-label', `${label} 玩家名稱`);
    headset.setAttribute('aria-label', `${label} 頭盔`);
    headset.add(new Option('Meta Quest 3', 'Quest3'));
    headset.add(new Option('VIVE XR', 'ViveXr'));
    tr.dataset.venueRosterSeat = `${roomId}/${seat + 1}`;
    tr.insertCell().textContent = label;
    tr.insertCell().append(name);
    tr.insertCell().append(headset);
    const detail = tr.insertCell();
    const row = { roomId, seat, name, headset, detail, target: '', valid: false };
    name.addEventListener('input', () => {
      if (!name.value.trim()) row.target = '';
      else if (!row.target) row.target = currentSession(row)?.id ?? '';
      render();
    });
    headset.addEventListener('change', render);
    return row;
  });

  function currentSession(row) {
    const { rooms, sessions } = getState();
    const id = rooms.find(room => room.id === row.roomId)?.sessionId;
    return sessions.find(session => session.id === id && session.state === 'Preparing');
  }

  function occupant(session, row) {
    return session?.players.find(player => player.roomId === row.roomId && player.seat === row.seat);
  }

  function render() {
    panel.hidden = !canRegister();
    if (panel.hidden || !panel.open) return;
    const { busy, pending } = getState(), locked = busy || !!pending;
    fileInput.disabled = locked || !!reading;
    importButton.disabled = fileInput.disabled || !fileInput.files.length;
    const drafts = rows.filter(row => row.name.value.trim());
    for (const row of rows) {
      const session = currentSession(row);
      const occupied = occupant(session, row);
      const draft = !!row.name.value.trim();
      const mr = session?.environment.mode === 'MR';
      const available = !!session && !occupied;
      const stale = draft && (!row.target || row.target !== session?.id);
      row.name.disabled = locked || (!available && !draft);
      row.headset.disabled = locked || !available;
      row.headset.options[1].disabled = mr;
      if (occupied && !draft) row.headset.value = occupied.headset;
      else if (mr && !draft) row.headset.value = 'Quest3';
      row.valid = available && !stale && (!mr || row.headset.value === 'Quest3');
      row.detail.textContent = stale ? '原場次已變更，請清空名稱後重新輸入。'
        : occupied ? `已登記 ${occupied.name}` : !session ? '等待準備場次'
          : mr && row.headset.value !== 'Quest3' ? 'MR 席位使用 Quest 3' : '空席';
    }
    submit.disabled = locked || !!reading || !drafts.length || drafts.some(row => !row.valid);
  }

  async function importCsv() {
    render();
    const file = fileInput.files[0];
    if (panel.hidden || !panel.open || importButton.disabled || !file) return;
    const targets = rows.map(row => currentSession(row)?.id);
    const operation = { epoch: getState().epoch };
    const current = () => reading === operation && canRegister() && panel.open && getState().epoch === operation.epoch
      && !panel.closest('[hidden]') && fileInput.files[0] === file;
    reading = operation;
    importStatus.textContent = '';
    render();
    try {
      if (file.size > maxRosterCsvBytes) throw new Error('名冊 CSV 不得超過 16 KiB。');
      const bytes = await file.arrayBuffer();
      if (!current()) return;
      if (getState().busy || getState().pending) throw new Error('請先確認目前操作，再帶入名冊 CSV。');
      let csv;
      try { csv = new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
      catch { throw new Error('請將名冊 CSV 儲存為 UTF-8。'); }
      const assignments = readVenueRosterCsv(csv).map(entry => {
        const index = (entry.roomId - 1) * 5 + entry.seat;
        const row = rows[index], session = currentSession(row);
        const label = `CSV 第 ${entry.lineNumber} 列（房間 ${row.roomId} · 第 ${row.seat + 1} 席）`;
        if (!session || session.id !== targets[index]) throw new Error(`${label}沒有原準備場次。`);
        if (occupant(session, row)) throw new Error(`${label}已登記玩家。`);
        if (row.name.value.trim()) throw new Error(`${label}已有名冊草稿。`);
        if (session.environment.mode === 'MR' && entry.headset !== 'Quest3')
          throw new Error(`${label}的 MR 席位須使用 Quest 3。`);
        return { row, entry, sessionId: session.id };
      });
      for (const { row, entry, sessionId } of assignments) {
        row.name.value = entry.name;
        row.headset.value = entry.headset;
        row.target = sessionId;
      }
      fileInput.value = '';
      importStatus.textContent = `已帶入 ${assignments.length} 席草稿。核對後再登記。`;
    } catch (error) {
      if (current()) importStatus.textContent = `${error.message} 未帶入任何席位。`;
    } finally {
      if (reading === operation) {
        reading = null;
        render();
      }
    }
  }

  panel.addEventListener('toggle', () => {
    if (!panel.open) reading = null;
    render();
  });
  template.addEventListener('click', () => {
    if (canRegister()) download('venue-roster-template.csv', new Blob([venueRosterCsvTemplate()], { type: 'text/csv;charset=utf-8' }));
  });
  fileInput.addEventListener('change', () => { importStatus.textContent = ''; render(); });
  importButton.addEventListener('click', importCsv);
  submit.addEventListener('click', () => {
    render();
    if (panel.hidden || !panel.open || submit.disabled) return;
    const drafts = rows.filter(row => row.name.value.trim());
    if (!confirm(`將 ${drafts.length} 位玩家加入指定場次與席位？`)) return;
    const seats = drafts.map(row => ({ sessionId: row.target, requestId: uuid(), playerId: uuid(), name: row.name.value.trim(),
      roomId: row.roomId, seat: row.seat, headset: row.headset.value }));
    register(seats);
  });
  return {
    render,
    accepted(seats) {
      for (const { roomId, seat } of seats) {
        const row = rows[(roomId - 1) * 5 + seat];
        row.name.value = row.target = '';
      }
      status.textContent = `已登記 ${seats.length} 席。`;
    },
    reset() {
      reading = null;
      panel.open = false;
      for (const row of rows) {
        row.name.value = row.target = '';
        row.headset.value = 'Quest3';
      }
      fileInput.value = importStatus.textContent = '';
      status.textContent = '';
    }
  };
}
