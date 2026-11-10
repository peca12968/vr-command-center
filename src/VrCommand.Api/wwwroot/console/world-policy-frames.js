const phaseNames = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const behaviorNames = { Hold: '固守', Patrol: '巡邏', Advance: '推進' };
const changeNames = { initial: '首格狀態', phase: '場次階段', environment: '環境', enemies: '敵軍策略' };

export function mountWorldPolicyFrames(response, jump) {
  const start = document.getElementById('world-policy-start');
  const here = document.getElementById('world-policy-here');
  const next = document.getElementById('world-policy-next');
  const results = document.getElementById('world-policy-results');
  const status = document.getElementById('world-policy-status');
  let scope, scopeKey = '', generation = 0, cursor, pending;

  function controls() {
    const idle = scope?.idle && !pending;
    start.disabled = here.disabled = !idle;
    next.disabled = !idle || cursor == null;
    for (const button of results.querySelectorAll('button')) button.disabled = !idle;
  }

  function update(value) {
    const key = value ? JSON.stringify([value.sessionId, value.streamId, value.throughFrame]) : '';
    const changed = key !== scopeKey;
    scope = value;
    if (pending && (changed || !scope?.idle)) {
      pending.abort();
      pending = null;
      status.textContent = '回放暫停後可重新查閱。';
    }
    if (changed) {
      scopeKey = key;
      generation++;
      cursor = null;
      results.replaceChildren();
      status.textContent = '';
    }
    controls();
  }

  async function read(afterFrame) {
    if (!scope?.idle || pending) return;
    const { sessionId, streamId, throughFrame } = scope;
    const request = new AbortController(), requestedGeneration = generation;
    pending = request;
    controls();
    status.textContent = '正在查閱已保存的設定…';
    try {
      const signal = AbortSignal.any([request.signal, AbortSignal.timeout(8000)]);
      const query = new URLSearchParams({ afterFrame, throughFrame });
      const value = await (await response(`/api/sessions/${sessionId}/world/policy-frames?${query}`, signal)).json();
      if (pending !== request) return;
      const end = value.scannedThroughFrame;
      if (value.sessionId !== sessionId || value.streamId !== streamId || value.throughFrame !== throughFrame || value.afterFrame !== afterFrame
          || !Number.isSafeInteger(end) || end <= afterFrame || end > Math.min(throughFrame, afterFrame + 1024)
          || value.nextAfterFrame !== (end < throughFrame ? end : null) || !Array.isArray(value.frames) || value.frames.length > 24)
        throw new Error('錄製範圍不符。');
      let previous = afterFrame;
      const rows = value.frames.map(({ frameSequence, elapsedMilliseconds, policy, changes }) => {
        if (!Number.isSafeInteger(frameSequence) || frameSequence <= previous || frameSequence > end
            || !Number.isSafeInteger(elapsedMilliseconds) || elapsedMilliseconds < 0 || !Array.isArray(changes) || changes.length === 0
            || changes.some(change => !Object.hasOwn(changeNames, change)) || !policy
            || !Object.hasOwn(phaseNames, policy.phase) || !Object.hasOwn(weatherNames, policy.weather) || !Object.hasOwn(behaviorNames, policy.behavior)
            || [policy.night, policy.lightning, policy.autoAttack].some(value => typeof value !== 'boolean')) throw new Error('設定畫格不符。');
        previous = frameSequence;
        const row = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'quiet';
        button.dataset.frameSequence = String(frameSequence);
        button.textContent = `第 ${frameSequence} 格 · ${(elapsedMilliseconds / 1000).toFixed(2)} 秒 · ${changes.map(change => changeNames[change]).join('、')}`;
        button.addEventListener('click', () => jump(frameSequence, () => generation === requestedGeneration));
        const summary = document.createElement('span');
        summary.className = 'hint';
        summary.textContent = ` ${phaseNames[policy.phase]} · ${weatherNames[policy.weather]}／${policy.night ? '夜晚' : '白天'}／閃電${policy.lightning ? '開啟' : '關閉'} · ${behaviorNames[policy.behavior]}／自動攻擊${policy.autoAttack ? '開啟' : '關閉'}`;
        row.append(button, summary);
        return row;
      });
      cursor = value.nextAfterFrame;
      results.replaceChildren(...rows);
      status.textContent = `已查閱第 ${afterFrame + 1} 至 ${end} 格，找到 ${rows.length} 格。${cursor == null ? '已到保存範圍尾端。' : '可查閱後續設定。'}`;
    } catch {
      if (pending === request) status.textContent = '無法查閱設定切換，請再試一次。';
    } finally {
      if (pending === request) { pending = null; controls(); }
    }
  }

  start.addEventListener('click', () => read(0));
  here.addEventListener('click', () => read(scope.frameSequence - 1));
  next.addEventListener('click', () => read(cursor));
  return { update };
}
