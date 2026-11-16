export function mountVenueRoster({ getState, canRegister, uuid, register }) {
  const panel = document.getElementById('venue-roster-admissions');
  const table = document.getElementById('venue-roster-seats');
  const submit = document.getElementById('venue-roster-register');
  const status = document.getElementById('venue-roster-status');
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

  function render() {
    panel.hidden = !canRegister();
    if (panel.hidden || !panel.open) return;
    const { busy, pending } = getState(), locked = busy || !!pending;
    const drafts = rows.filter(row => row.name.value.trim());
    for (const row of rows) {
      const session = currentSession(row);
      const occupied = session?.players.find(player => player.roomId === row.roomId && player.seat === row.seat);
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
    submit.disabled = locked || !drafts.length || drafts.some(row => !row.valid);
  }

  panel.addEventListener('toggle', render);
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
      panel.open = false;
      for (const row of rows) {
        row.name.value = row.target = '';
        row.headset.value = 'Quest3';
      }
      status.textContent = '';
    }
  };
}
