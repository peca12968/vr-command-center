const phaseNames = { Preparing: '準備中', Running: '執行中', Paused: '已暫停', Ended: '已結束' };
const weatherNames = { Clear: '晴朗', Rain: '下雨', Fog: '濃霧', Storm: '暴風雨' };
const behaviorNames = { Hold: '固守', Patrol: '巡邏', Advance: '推進' };
const changeNames = { initial: '首格狀態', phase: '場次階段', environment: '環境', enemies: '敵軍策略', 'enemy-roster': '敵軍增減' };
const enemyId = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;

function matchesRoster(value, elapsed, roomId, roster) {
  if (value?.packet?.elapsedMilliseconds !== elapsed || !Array.isArray(value.packet.frame?.enemies)) return false;
  const enemies = value.packet.frame.enemies.filter(enemy => roomId === null || enemy.roomId === roomId);
  const ids = enemies.map(enemy => enemy.id).sort();
  return ids.length === roster.enemyIds.length && ids.every((id, index) => id === roster.enemyIds[index])
    && enemies.filter(enemy => enemy.health > 0).length === roster.alive;
}

function matchesPolicy(value, roomId, policy) {
  const packet = value?.packet, frame = packet?.frame;
  if (!frame) return false;
  const local = roomId === null ? null : frame.roomEnemyPolicies?.find(row => row.roomId === roomId);
  return (frame.phase ?? 'Preparing') === policy.phase && (packet.weather ?? 'Clear') === policy.weather
    && (frame.night ?? false) === policy.night && (packet.lightning ?? false) === policy.lightning
    && (local?.behavior ?? frame.behavior ?? 'Hold') === policy.behavior
    && (local?.autoAttack ?? frame.autoAttack ?? false) === policy.autoAttack;
}

function validatePolicyHit({ frameSequence, elapsedMilliseconds, policy, changes, enemyRoster }, changeKind, lower, upper) {
  if (!Number.isSafeInteger(frameSequence) || frameSequence < lower || frameSequence > upper
      || !Number.isSafeInteger(elapsedMilliseconds) || elapsedMilliseconds < 0 || !Array.isArray(changes) || changes.length === 0
      || changes.some(change => !Object.hasOwn(changeNames, change)) || (changeKind !== null && !changes.includes(changeKind)) || !policy
      || !Object.hasOwn(phaseNames, policy.phase) || !Object.hasOwn(weatherNames, policy.weather) || !Object.hasOwn(behaviorNames, policy.behavior)
      || [policy.night, policy.lightning, policy.autoAttack].some(value => typeof value !== 'boolean')) throw new Error('設定畫格不符。');
  const { enemyIds, alive, added, removed } = enemyRoster ?? {};
  if (!Array.isArray(enemyIds) || enemyIds.length > 100 || enemyIds.some((id, index) => typeof id !== 'string'
      || !enemyId.test(id) || (index > 0 && enemyIds[index - 1] >= id))
    || [alive, added, removed].some(count => !Number.isSafeInteger(count) || count < 0 || count > 100)
    || alive > enemyIds.length || added > enemyIds.length || changes.includes('enemy-roster') !== (added + removed > 0))
    throw new Error('敵軍快照不符。');
}

export function mountWorldPolicyFrames(response, jump) {
  const filter = document.getElementById('world-policy-change');
  const start = document.getElementById('world-policy-start');
  const here = document.getElementById('world-policy-here');
  const next = document.getElementById('world-policy-next');
  const previousChange = document.getElementById('world-policy-previous-change');
  const nextChange = document.getElementById('world-policy-next-change');
  const results = document.getElementById('world-policy-results');
  const status = document.getElementById('world-policy-status');
  let scope, scopeKey = '', generation = 0, cursor, pending;

  function controls() {
    const idle = scope?.idle && !pending;
    filter.disabled = !scope?.idle;
    start.disabled = here.disabled = !idle;
    next.disabled = !idle || cursor == null;
    previousChange.disabled = !idle || scope.frameSequence <= 1;
    nextChange.disabled = !idle || scope.frameSequence >= scope.throughFrame;
    for (const button of results.querySelectorAll('button')) button.disabled = !idle;
  }

  function update(value) {
    if (!value) filter.value = '';
    const key = value ? JSON.stringify([value.sessionId, value.streamId, value.throughFrame, value.room, filter.value]) : '';
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
    const { sessionId, streamId, throughFrame, room } = scope;
    const roomId = room === 'all' ? null : Number(room);
    const changeKind = filter.value || null;
    const request = new AbortController(), requestedGeneration = generation;
    pending = request;
    controls();
    status.textContent = '正在查閱已保存的設定…';
    try {
      const signal = AbortSignal.any([request.signal, AbortSignal.timeout(8000)]);
      const query = new URLSearchParams({ afterFrame, throughFrame, includeEnemyRoster: 'true' });
      if (roomId !== null) query.set('roomId', String(roomId));
      if (changeKind !== null) query.set('change', changeKind);
      const value = await (await response(`/api/sessions/${sessionId}/world/policy-frames?${query}`, signal)).json();
      if (pending !== request) return;
      const end = value.scannedThroughFrame;
      if (value.sessionId !== sessionId || value.streamId !== streamId || value.throughFrame !== throughFrame || value.afterFrame !== afterFrame
          || value.includeEnemyRoster !== true || (value.roomId ?? null) !== roomId || (value.change ?? null) !== changeKind
          || !Number.isSafeInteger(end) || end <= afterFrame || end > Math.min(throughFrame, afterFrame + 1024)
          || value.nextAfterFrame !== (end < throughFrame ? end : null) || !Array.isArray(value.frames) || value.frames.length > 24)
        throw new Error('錄製範圍不符。');
      let previous = afterFrame;
      const rows = value.frames.map(hit => {
        validatePolicyHit(hit, changeKind, previous + 1, end);
        const { frameSequence, elapsedMilliseconds, policy, changes, enemyRoster } = hit;
        const { enemyIds, alive, added, removed } = enemyRoster;
        previous = frameSequence;
        const row = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'quiet';
        button.dataset.frameSequence = String(frameSequence);
        button.textContent = `第 ${frameSequence} 格 · ${(elapsedMilliseconds / 1000).toFixed(2)} 秒 · ${changes.map(change => changeNames[change]).join('、')}`;
        button.addEventListener('click', () => jump(frameSequence, () => generation === requestedGeneration,
          frame => matchesPolicy(frame, roomId, policy) && matchesRoster(frame, elapsedMilliseconds, roomId, enemyRoster)));
        const summary = document.createElement('span');
        summary.className = 'hint';
        const rosterSummary = `${roomId === null ? '全場' : `房間 ${roomId}`} · 在場 ${enemyIds.length}／存活 ${alive}`
          + (added || removed ? `／增援 ${added}／撤除 ${removed}` : '');
        summary.textContent = ` ${phaseNames[policy.phase]} · ${weatherNames[policy.weather]}／${policy.night ? '夜晚' : '白天'}／閃電${policy.lightning ? '開啟' : '關閉'} · ${behaviorNames[policy.behavior]}／自動攻擊${policy.autoAttack ? '開啟' : '關閉'} · ${rosterSummary}`;
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

  async function navigate(direction, includeCurrent = false) {
    if (!scope?.idle || pending) return;
    const { sessionId, streamId, throughFrame, room, frameSequence } = scope;
    const roomId = room === 'all' ? null : Number(room), changeKind = filter.value || null;
    const reverse = direction === 'previous', limit = reverse ? 1 : throughFrame;
    if (frameSequence === limit && !includeCurrent) return;
    const request = new AbortController(), requestedGeneration = generation;
    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(30000)]);
    const query = new URLSearchParams({ throughFrame, direction, includeEnemyRoster: 'true' });
    if (roomId !== null) query.set('roomId', String(roomId));
    if (changeKind !== null) query.set('change', changeKind);
    pending = request;
    controls();
    status.textContent = '正在尋找相鄰的設定畫格…';
    let from = frameSequence, includeFrom = includeCurrent;
    try {
      for (;;) {
        query.set('fromFrame', String(from));
        if (includeFrom) query.set('includeFrom', 'true');
        else query.delete('includeFrom');
        const value = await (await response(`/api/sessions/${sessionId}/world/policy-neighbor?${query}`, signal)).json();
        if (pending !== request || scope.frameSequence !== frameSequence) return;
        const scanned = value.scannedToFrame;
        const boundary = reverse ? Math.max(1, from - (includeFrom ? 1023 : 1024)) : Math.min(throughFrame, from + 1024);
        if (value.sessionId !== sessionId || value.streamId !== streamId || value.throughFrame !== throughFrame
            || value.fromFrame !== from || value.direction !== direction || value.includeEnemyRoster !== true
            || (value.includeFrom ?? false) !== includeFrom
            || value.roomId !== roomId || value.change !== changeKind || !Number.isSafeInteger(scanned)
            || (reverse ? scanned < boundary || scanned > (includeFrom ? from : from - 1) : scanned > boundary || scanned <= from))
          throw new Error('回應的設定搜尋範圍不同。');
        if (value.frame !== null) {
          validatePolicyHit(value.frame, changeKind, scanned, scanned);
          if (value.nextFromFrame !== null) throw new Error('回應的設定搜尋游標不同。');
          const { elapsedMilliseconds, policy, enemyRoster } = value.frame;
          pending = null;
          const jumped = await jump(scanned, () => generation === requestedGeneration && scope?.frameSequence === frameSequence,
            frame => matchesPolicy(frame, roomId, policy) && matchesRoster(frame, elapsedMilliseconds, roomId, enemyRoster));
          if (generation === requestedGeneration && !pending && scope?.frameSequence === (jumped ? scanned : frameSequence))
            status.textContent = jumped ? `已跳到第 ${scanned} 格。` : '讀取設定畫格失敗，請再試一次。';
          return;
        }
        if (scanned !== boundary || value.nextFromFrame !== (scanned === limit ? null : scanned))
          throw new Error('回應的設定搜尋游標不同。');
        if (scanned === limit) {
          status.textContent = includeCurrent ? '保存範圍內沒有符合條件的設定畫格。' : '保存範圍內沒有其他符合條件的設定畫格。';
          return;
        }
        from = scanned;
        includeFrom = false;
      }
    } catch {
      if (pending === request) status.textContent = '尋找設定畫格失敗，請再試一次。';
    } finally {
      if (pending === request) { pending = null; controls(); }
    }
  }

  function fromLatest(change) {
    if (!scope?.idle) return;
    filter.value = change;
    update(scope);
    return navigate('previous', true);
  }

  filter.addEventListener('change', () => update(scope));
  start.addEventListener('click', () => read(0));
  here.addEventListener('click', () => read(scope.frameSequence - 1));
  next.addEventListener('click', () => read(cursor));
  previousChange.addEventListener('click', () => navigate('previous'));
  nextChange.addEventListener('click', () => navigate('next'));
  return { update, fromLatest };
}
