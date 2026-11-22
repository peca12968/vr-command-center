import { MAX_REPLAY_BYTES, MAX_REPLAY_FRAMES, MAX_REPLAY_FILES, MAX_REPLAY_SET_BYTES, readPlayerReplay } from './player-replay-model.js';

const $ = id => document.getElementById('saved-clip-' + id);
const isId = value => typeof value === 'string' && /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(value);

function validClip(clip, streamId) {
  return isId(clip?.id) && clip.streamId === streamId && typeof clip.name === 'string'
    && clip.name.length > 0 && clip.name.length <= 60 && typeof clip.deleted === 'boolean'
    && Number.isSafeInteger(clip.startFrame) && clip.startFrame > 0
    && Number.isSafeInteger(clip.endFrame) && clip.endFrame > clip.startFrame
    && Number.isSafeInteger(clip.startMilliseconds) && clip.startMilliseconds >= 0
    && Number.isSafeInteger(clip.endMilliseconds) && clip.endMilliseconds >= clip.startMilliseconds;
}

export function mountSavedClips(request, canWrite, load, download) {
  let scope = null, idle = false, draft = null, rows = [], pending = null, work = null;
  const select = $('select'), name = $('name'), exportRoom = $('export-room');
  const offlinePlayer = $('offline-player'), exportZip = $('export-zip');
  let checkedOfflinePlayer = false;
  const selected = () => rows.find(clip => clip.id === select.value);
  const route = () => `/api/sessions/${scope.sessionId}/world/clips`;
  function message(text, error = false) {
    $('message').textContent = text;
    $('message').classList.toggle('replay-error', error);
  }
  function controls() {
    const row = selected();
    $('edit').hidden = !canWrite();
    name.disabled = !idle || !!work || !!pending;
    select.disabled = !rows.length || !!work;
    $('load').disabled = !idle || !!work || !row || row.endFrame > scope.throughFrame;
    $('outside').hidden = !row || row.endFrame <= scope.throughFrame;
    $('refresh').disabled = !scope || !!work || !!pending;
    $('save').disabled = !idle || !draft || !!work || !!pending;
    $('remove').disabled = !idle || !row || !!work || !!pending;
    const exportable = idle && row && !work && !pending && scope.complete && row.endFrame <= scope.throughFrame;
    const frames = row ? row.endFrame - row.startFrame + 1 : 0;
    $('export').disabled = !exportable || frames > MAX_REPLAY_FRAMES;
    exportZip.hidden = offlinePlayer.hidden;
    exportZip.disabled = exportZip.hidden || !exportable || frames > MAX_REPLAY_FRAMES * MAX_REPLAY_FILES;
    exportRoom.disabled = $('export').disabled && exportZip.disabled;
    $('retry').hidden = !pending || !!work;
  }
  function options(preferred = select.value) {
    select.replaceChildren(...rows.map(clip => new Option(
      `${clip.name} · 第 ${clip.startFrame}–${clip.endFrame} 格`, clip.id)));
    if (rows.some(clip => clip.id === preferred)) select.value = preferred;
  }
  async function sync(operation = null) {
    if (!scope || work) return;
    const { sessionId, streamId } = scope;
    const path = route(), own = work = new AbortController();
    const signal = () => AbortSignal.any([own.signal, AbortSignal.timeout(8000)]);
    let preferred = select.value, result = '', confirmed = false;
    controls(); message(operation ? '正在確認操作…' : '正在讀取已保存片段…');
    try {
      if (operation) {
        const response = await request(path + '/' + operation.id, signal(), operation);
        if (work !== own) return;
        if (operation.method === 'PUT') {
          const clip = await response.json();
          if (work !== own) return;
          if (!validClip(clip, streamId) || clip.id !== operation.id
            || ['name', 'startFrame', 'endFrame'].some(key => clip[key] !== operation.draft[key]))
            throw new Error('保存回覆與原片段不符。');
          preferred = clip.deleted ? '' : clip.id;
          if (name.value.trim() === operation.draft.name) name.value = '';
          result = clip.deleted ? '此片段已被移除，重試未重新建立。' : '已保存片段。';
        } else {
          if (response.status !== 204) throw new Error('移除回覆不完整。');
          result = '已移除片段。';
        }
        confirmed = true; pending = null; rows = []; options();
      }
      const reply = await (await request(path, signal())).json();
      if (work !== own) return;
      if (reply?.sessionId !== sessionId || reply.streamId !== streamId || !Array.isArray(reply.clips) || reply.clips.length > 24
        || reply.clips.some(clip => !validClip(clip, streamId) || clip.deleted)
        || new Set(reply.clips.map(clip => clip.id)).size !== reply.clips.length)
        throw new Error('回覆的錄製來源或片段不符。');
      rows = reply.clips; options(preferred);
      message(result || (rows.length ? `已讀取 ${rows.length} 段保存片段。` : '這份錄製目前沒有保存片段。'));
    } catch (error) {
      if (work !== own) return;
      if (!confirmed && operation && error.status >= 400 && error.status < 500 && error.status !== 408) pending = null;
      message(pending ? '結果尚未確認，請重試原操作。' : confirmed ? result + '請重新讀取片段清單。' : error.message, true);
    } finally {
      if (work === own) { work = null; controls(); }
    }
  }
  $('refresh').addEventListener('click', () => sync());
  select.addEventListener('change', controls);
  $('load').addEventListener('click', () => {
    if ($('load').disabled) return;
    const clip = selected();
    load(clip);
    message(`已載入「${clip.name}」的起訖標記。`);
  });
  async function exportClip(zip) {
    if ((zip ? exportZip : $('export')).disabled || !canWrite()) return;
    const clip = selected(), { sessionId, streamId, roomIds } = scope;
    const room = Number(exportRoom.value) || null, expectedRooms = room === null ? roomIds : [room];
    const extension = zip ? 'zip' : 'json';
    const suffix = room === null ? '' : '-room-' + String(room).padStart(2, '0');
    const filename = `vr-command-replay-${clip.id}${suffix}.${extension}`;
    const path = `${route()}/${clip.id}/player-replay.${extension}${room === null ? '' : '?roomId=' + room}`;
    const own = work = new AbortController();
    controls();
    try {
      const segmented = zip && clip.endFrame - clip.startFrame >= MAX_REPLAY_FRAMES;
      const response = await request(path, AbortSignal.any([own.signal, AbortSignal.timeout(segmented ? 90000 : 15000)]));
      if (response.status !== 200 || response.headers.get('content-type')?.split(';')[0].trim() !== (zip ? 'application/zip' : 'application/json'))
        throw new Error('無法讀取片段檔案。');
      if (zip && !response.headers.get('content-disposition')?.split(';').some(part => part.trim() === 'filename=' + filename))
        throw new Error('下載回覆的回放 ZIP 名稱不符。');
      const file = await response.blob();
      if (!file.size || file.size > (zip ? MAX_REPLAY_SET_BYTES + 3 * 1024 * 1024 : MAX_REPLAY_BYTES)) throw new Error('回放檔案大小不符。');
      if (!zip) {
        const replay = readPlayerReplay(JSON.parse(await file.text()));
        if (replay.header.sessionId !== sessionId || replay.header.streamId !== streamId
          || replay.clipName !== clip.name || replay.startFrame !== clip.startFrame || replay.endFrame !== clip.endFrame
          || (room === null ? replay.playerReplayVersion !== 1 : replay.roomId !== room)
          || replay.header.roomIds.length !== expectedRooms.length
          || expectedRooms.some((id, index) => id !== replay.header.roomIds[index]))
          throw new Error('下載回覆的錄製來源或範圍不符。');
      }
      if (work !== own) return;
      download(filename, file);
      message(`已下載「${clip.name}」的${room === null ? '玩家' : '房間 ' + room + ' '}回放${zip ? ' ZIP' : '檔'}。`);
    } catch (error) {
      if (work === own) message(error.message, true);
    } finally {
      if (work === own) { work = null; controls(); }
    }
  }
  $('export').addEventListener('click', () => exportClip(false));
  exportZip.addEventListener('click', () => exportClip(true));
  $('save').addEventListener('click', () => {
    if ($('save').disabled || !canWrite()) return;
    const title = name.value.trim();
    if (!title || title.length > 60) { message('請輸入 1–60 字的片段名稱。', true); return; }
    const body = { streamId: scope.streamId, name: title, ...draft };
    pending = { id: crypto.randomUUID(), method: 'PUT', body: JSON.stringify(body), draft: body };
    void sync(pending);
  });
  $('remove').addEventListener('click', () => {
    if ($('remove').disabled || !canWrite() || !confirm('移除這段保存片段？')) return;
    pending = { id: selected().id, method: 'DELETE' };
    void sync(pending);
  });
  $('retry').addEventListener('click', () => { if (pending && canWrite()) void sync(pending); });
  return {
    update(next, enabled, range) {
      const changed = next?.sessionId !== scope?.sessionId || next?.streamId !== scope?.streamId;
      scope = next; idle = enabled; draft = range;
      if (changed) {
        work?.abort(); work = pending = null; rows = []; name.value = ''; options(); message('');
        $('export-room-field').hidden = !(scope?.roomIds.length > 1);
        exportRoom.replaceChildren(new Option('全場', ''), ...(scope?.roomIds ?? []).map(room => new Option('房間 ' + room, room)));
        if (scope) {
          void sync();
          if (!checkedOfflinePlayer) {
            checkedOfflinePlayer = true;
            fetch(offlinePlayer.href, { method: 'HEAD', cache: 'no-store', signal: AbortSignal.timeout(8000) })
              .then(response => {
                offlinePlayer.hidden = !response.ok || !response.headers.get('Content-Disposition')?.startsWith('attachment;');
                if (response.status !== 404 && !response.ok) checkedOfflinePlayer = false;
                controls();
              })
              .catch(() => { checkedOfflinePlayer = false; });
          }
        }
      }
      controls();
    }
  };
}
