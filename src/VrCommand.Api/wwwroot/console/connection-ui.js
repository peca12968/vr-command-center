export function validDestination(address, port) {
  if (typeof address !== 'string' || !/^(?:\d{1,3}\.){3}\d{1,3}$/.test(address)) return false;
  const octets = address.split('.');
  return octets.every(part => String(Number(part)) === part && Number(part) <= 255)
    && Number(octets[0]) > 0 && Number(octets[0]) < 224
    && Number.isInteger(port) && port >= 1024 && port <= 65535;
}

export function validEndpoint(value, session) {
  return !!session && value?.version === 1 && value.sessionId === session.id && typeof value.streamId === 'string' && value.streamId.length > 0
    && value.streamId === session.combatStream?.streamId
    && validDestination(value.address, value.port) && typeof value.sessionEnded === 'boolean';
}

export function mountConnections(getState, unauthorized) {
  const address = document.getElementById('game-address'), port = document.getElementById('game-port');
  const status = document.getElementById('connection-endpoint-status'), apply = document.getElementById('apply-connection-endpoint');
  let active = false, identity = '', generation = 0, controller, attempted = -Infinity, value, revision = 0, applied = '', message = '';
  for (const field of [address, port]) field.addEventListener('input', () => { revision++; });
  function stop() { generation++; controller?.abort(); controller = null; }
  function reset() { stop(); identity = ''; attempted = -Infinity; value = null; revision = 0; applied = ''; message = ''; address.value = ''; port.value = '7777'; render(); }
  function use() { address.value = value.address; port.value = String(value.port); applied = value.streamId; }
  function render() {
    const state = getState(), valid = validEndpoint(value, state.session);
    const ended = state.session?.state === 'Ended' || value?.sessionEnded === true;
    apply.disabled = !valid || ended || state.busy || !state.actor;
    status.textContent = valid ? `來源公布：${value.address}:${value.port}${ended ? ' · 場次已結束' : value.address.startsWith('127.') ? ' · 僅供同機連線' : ' · 玩家須能連到此地址'}`
      : message || '等待場次的遊戲來源公布連線設定；也可手動輸入。';
    if (valid && !ended && !revision && applied !== value.streamId) use();
  }
  apply.addEventListener('click', () => { if (!apply.disabled) { use(); revision++; } });
  async function poll() {
    const state = getState(); if (!active || !state.actor || state.session?.id !== state.selected || !state.selected || controller || document.visibilityState !== 'visible') return;
    const id = state.selected, epoch = state.epoch, key = state.key, request = generation, own = new AbortController(); controller = own; attempted = performance.now();
    const current = () => request === generation && active && getState().selected === id && getState().epoch === epoch && getState().key === key;
    const timeout = setTimeout(() => own.abort(), 5000);
    try {
      const response = await fetch(`/api/sessions/${id}/connection-endpoint`, { headers: { Authorization: 'Bearer ' + key }, signal: own.signal, cache: 'no-store' });
      if (!current()) return;
      if (response.status === 401) { unauthorized(); return; }
      if (response.status === 404) { value = null; message = '尚未公布場次連線設定；可由操作員手動輸入地址與埠號。'; return; }
      if (!response.ok) throw Error('Endpoint unavailable');
      const body = await response.json(); if (!current()) return;
      value = body; message = validEndpoint(value, getState().session) ? '' : '連線設定尚未對上本次遊戲來源，等待更新。';
    } catch { if (current()) { value = null; message = '連線設定未確認，正在重試；保留手動輸入。'; } }
    finally { clearTimeout(timeout); if (controller === own) controller = null; if (current()) render(); }
  }
  function update() {
    const state = getState(), next = state.actor && state.session?.id === state.selected ? state.epoch + '/' + state.selected : '';
    if (next !== identity) { reset(); identity = next; }
    render(); if (active && performance.now() - attempted >= 2000) void poll();
  }
  setInterval(() => { if (active) update(); }, 500);
  return { reset, update, active(on) { active = on; if (!on) stop(); else update(); } };
}
