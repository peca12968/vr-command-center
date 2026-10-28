const $ = id => document.getElementById(id);

export function mountCameras(getKey, unauthorized, getScene, recalled) {
  let session = null, rows = [], pending = null, loading = false, sending = false, epoch = 0, reader;
  function message(text, error = false) { $('camera-message').textContent = text; $('camera-message').classList.toggle('replay-error', error); }
  function controls() {
    $('camera-save').disabled = !session || loading || !!pending;
    $('camera-name').disabled = !!pending;
    $('camera-positions').disabled = loading || !rows.length;
    $('camera-recall').disabled = loading || !rows.length;
    $('camera-remove').disabled = loading || !rows.length || !!pending;
    $('camera-refresh').disabled = !session || loading || !!pending;
    $('camera-retry').hidden = !pending || sending;
    $('world-recording').disabled = !!pending;
  }
  function options(selected = $('camera-positions').value) {
    $('camera-positions').replaceChildren(...rows.map(row => {
      const option = document.createElement('option'); option.value = row.id; option.textContent = row.name; return option;
    }));
    if (rows.some(row => row.id === selected)) $('camera-positions').value = selected;
    controls();
  }
  async function request(path, init = {}) {
    const key = getKey(); if (!key) throw new Error('請先登入。');
    const timeout = AbortSignal.timeout(10000), signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
    const response = await fetch(path, { ...init, signal, headers: { Authorization: 'Bearer ' + key, ...(init.body ? { 'Content-Type': 'application/json' } : {}) }, cache: 'no-store' });
    if (response.status === 401 && key === getKey()) unauthorized();
    if (!response.ok) {
      let body; try { body = await response.json(); } catch { }
      const error = new Error(body?.error || '鏡頭服務回應 ' + response.status); error.status = response.status; throw error;
    }
    if (response.status === 204) return null;
    try { return await response.json(); }
    catch { throw new Error('鏡頭服務回應不完整，請重試確認結果。'); }
  }
  async function refresh(selected) {
    if (!session || pending) return;
    const current = ++epoch; reader?.abort(); reader = new AbortController(); loading = true; controls();
    try {
      const result = await request(`/api/sessions/${session}/world/cameras`, { signal: reader.signal });
      if (current !== epoch) return;
      rows = result; options(selected); message(rows.length ? `已保存 ${rows.length} 個鏡頭位置。` : '尚未保存鏡頭位置，先調整視角再命名保存。');
      return true;
    } catch (error) { if (current === epoch && error.name !== 'AbortError') message(error.message, true); }
    finally { if (current === epoch) { loading = false; controls(); } }
  }
  async function send() {
    if (!pending || sending) return;
    const operation = pending, current = epoch; sending = true; controls();
    message('正在保存鏡頭設定…');
    try {
      const result = await request(operation.path, { method: operation.method, body: operation.body });
      if (current !== epoch || pending !== operation) return;
      pending = null; sending = false;
      const refreshed = await refresh(result?.deleted ? undefined : result?.id);
      if (refreshed && result?.deleted) message('這個位置已被其他視窗移除；重試沒有將它重新建立。');
    } catch (error) {
      if (current !== epoch || pending !== operation) return;
      sending = false;
      if (error.status >= 400 && error.status < 500) pending = null;
      message(pending ? '結果尚未確認，請按「重試確認結果」；會沿用原鏡頭位置。' : error.message, true); controls();
    }
  }
  $('camera-save').addEventListener('click', () => {
    const scene = getScene(), name = $('camera-name').value.trim();
    if (!session || !scene || pending || loading) return;
    if (!name || name.length > 60) { message('請輸入 1–60 字的位置名稱。', true); return; }
    pending = { method: 'PUT', path: `/api/sessions/${session}/world/cameras/${crypto.randomUUID()}`, body: JSON.stringify({ name, view: scene.view() }) };
    send();
  });
  $('camera-remove').addEventListener('click', () => {
    const selected = $('camera-positions').value;
    if (!session || !selected || pending || loading) return;
    pending = { method: 'DELETE', path: `/api/sessions/${session}/world/cameras/${selected}` }; send();
  });
  $('camera-recall').addEventListener('click', () => {
    const row = rows.find(row => row.id === $('camera-positions').value);
    if (!row || loading) return;
    getScene()?.restoreView(row.view); recalled(); message(`已切換至「${row.name}」。`);
  });
  $('camera-refresh').addEventListener('click', () => refresh());
  $('camera-retry').addEventListener('click', send);
  controls();
  return {
    bind(id) {
      if (pending || session === id) return;
      epoch++; reader?.abort(); session = id; rows = []; loading = false; $('camera-name').value = ''; options();
      message(''); if (id) refresh();
    },
    reset() { epoch++; reader?.abort(); session = null; rows = []; pending = null; loading = sending = false; $('camera-name').value = ''; options(); message(''); }
  };
}
