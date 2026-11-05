const $ = id => document.getElementById(id);
const names = ['A', 'B', 'C'];
const point = value => `(${value.x.toFixed(3)}, ${value.z.toFixed(3)})`;

export function mountAlignment(api, download) {
  const form = $('alignment-form'), run = $('alignment-run'), save = $('alignment-download');
  const summary = $('alignment-summary'), details = $('alignment-details'), results = $('alignment-results');
  let generation = 0, report = null;

  function invalidate(text = '輸入三個標記的量測值後開始核對。') {
    generation++;
    report = null;
    run.disabled = false;
    save.disabled = true;
    summary.textContent = text;
    details.hidden = true;
    results.replaceChildren();
  }

  function readPoint(marker, space) {
    const key = `alignment-${marker.toLowerCase()}-${space}`;
    return { x: $(key + '-x').valueAsNumber, z: $(key + '-z').valueAsNumber };
  }

  form.addEventListener('input', () => invalidate());
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (form.hidden || run.disabled) return;
    invalidate('正在核對標記…');
    const request = generation;
    const roomId = Number($('alignment-room').value);
    const markers = names.map(marker => ({ room: readPoint(marker, 'room'), tracking: readPoint(marker, 'tracking') }));
    run.disabled = true;
    try {
      const value = await api('/room-alignment', 'POST', { roomId, markers });
      if (request !== generation || form.hidden) return;
      if (value?.version !== 1 || value.profile !== 'room-floor-alignment-v1' || value.roomId !== roomId)
        throw new Error('校正回應與本次選取的房間不符。');
      report = value;
      summary.textContent = value.withinTolerance ? '三個標記均在 5 公分容許誤差內。' : '至少一個標記超過 5 公分，請核對標記順序與量測值。';
      $('alignment-transform').textContent = `房間 ${roomId} · 房間在全館的原點 ${point(value.roomOrigin)} 公尺 · 旋轉 ${value.yawDegrees.toFixed(2)}° · 房間內位移 ${point(value.translation)} 公尺`;
      for (const marker of value.markers) {
        const row = results.insertRow();
        for (const text of [marker.name, point(marker.room), point(marker.mappedRoom), `${(marker.errorMeters * 100).toFixed(2)} 公分`])
          row.insertCell().textContent = text;
      }
      details.hidden = false;
      save.disabled = !value.withinTolerance;
    } catch (error) {
      if (request === generation) summary.textContent = error.status === 400 ? '請核對座標範圍。A、B 以及遊戲標記 C 到 A、B 連線的距離均須至少 0.5 公尺。'
        : error.message || '無法核對校正資料。';
    } finally {
      if (request === generation) run.disabled = false;
    }
  });

  save.addEventListener('click', () => {
    if (form.hidden || !report?.withinTolerance) return;
    download(`room-${report.roomId}-floor-alignment.json`, new Blob([JSON.stringify(report, null, 2) + '\n'], { type: 'application/json' }));
  });

  return {
    active(on) { form.hidden = !on; if (!on) invalidate(); },
    reset() { form.reset(); form.hidden = true; invalidate(); }
  };
}
