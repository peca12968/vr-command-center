export function mountReport(current, unauthorized) {
  const button = document.getElementById('export-report'), status = document.getElementById('report-status');
  let generation = 0, controller = null, availability = null;
  const ready = value => value.actor && value.session?.state === 'Ended' &&
    value.statistics?.sessionId === value.session.id && value.statistics.throughSequence === value.session.sequence &&
    !value.statistics.pendingTelemetry;
  function update() {
    const value = current();
    button.disabled = !!controller || !ready(value);
    const next = ready(value) ? '戰鬥統計已完成，可下載 CSV（含離場玩家）。'
      : value.session?.state === 'Ended' ? '等待戰鬥資料確認封存後才可匯出。' : '結束任務並完成戰鬥封存後可匯出。';
    if (!controller && next !== availability) status.textContent = next;
    availability = next;
  }
  function reset() { generation++; controller?.abort(); controller = null; availability = null; status.textContent = ''; button.disabled = true; }
  button.addEventListener('click', async () => {
    const value = current();
    if (controller || !ready(value)) return;
    const attempt = ++generation, epoch = value.epoch, id = value.session.id;
    const active = () => attempt === generation && current().epoch === epoch && current().session?.id === id;
    const request = new AbortController(); controller = request;
    const timeout = setTimeout(() => request.abort(), 8000);
    button.disabled = true; status.textContent = '正在下載最終報表…';
    try {
      const response = await fetch(`/api/sessions/${id}/report.csv`, {
        headers: { Authorization: 'Bearer ' + value.key }, cache: 'no-store', signal: request.signal
      });
      if (!active()) return;
      if (!response.ok) {
        if (response.status === 401) { unauthorized(); return; }
        throw new Error(response.status === 409 ? '任務或戰鬥封存尚未完成，請更新後再匯出。'
          : response.status === 403 ? '目前身分沒有此場次的報表權限。' : '報表下載失敗，請更新後重試。');
      }
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== 'text/csv') throw new Error('報表格式不符，請更新後重試。');
      const blob = await response.blob();
      if (!active()) return;
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      try {
        link.href = url; link.download = `vr-command-report-v1-${id}.csv`; document.body.append(link); link.click();
      } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
      status.textContent = '最終報表已下載；來源與封存序號列於 CSV。';
    } catch (error) {
      if (active()) status.textContent = request.signal.aborted ? '下載逾時或已中止，可重新下載。' : error.message;
    } finally {
      clearTimeout(timeout);
      if (attempt === generation) { controller = null; button.disabled = !ready(current()); }
    }
  });
  return { update, reset };
}
