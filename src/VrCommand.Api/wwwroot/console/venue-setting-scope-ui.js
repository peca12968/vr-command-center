export function mountVenueSettingScope(setting, label, changed) {
  const scope = document.getElementById(`venue-${setting}-scope`);
  const group = document.getElementById(`venue-${setting}-rooms`);
  const button = document.getElementById(`venue-apply-${setting}`);
  const picked = new Map();
  let running = [];
  const roomTarget = (targets, room) => targets.find(target => target.roomIds.length === 1 && target.roomIds[0] === room);
  const checkboxes = Array.from({ length: 5 }, (_, index) => {
    const room = index + 1, label = document.createElement('label'), input = document.createElement('input');
    input.type = 'checkbox'; input.value = String(room); input.disabled = true;
    label.className = 'check';
    label.append(input, `房間 ${room}`); group.append(label);
    input.addEventListener('change', () => {
      const target = roomTarget(running, room);
      if (input.checked && target) picked.set(room, target.sessionId);
      else picked.delete(room);
      changed();
    });
    return input;
  });
  scope.addEventListener('change', () => { picked.clear(); changed(); });

  function selection(targets) {
    if (scope.value !== 'rooms') return { targets };
    if (targets.some(target => target.roomIds.length > 1))
      return { targets: [], reason: `合併場次共用${label}，請改選「所有執行中場次」。` };
    const roomIds = [...picked.keys()].sort((a, b) => a - b);
    if (!roomIds.length) return { targets: [], reason: '請勾選要調整的獨立房間。' };
    const chosen = roomIds.map(room => roomTarget(targets, room));
    const stale = roomIds.filter((room, index) => chosen[index]?.sessionId !== picked.get(room));
    if (stale.length) return { targets: [], reason: `房間 ${stale.join('、')} 的場次已變更，請取消勾選後重新選擇。` };
    return { targets: chosen, roomIds };
  }

  return {
    selection,
    update(targets, locked) {
      running = targets;
      const linked = targets.some(target => target.roomIds.length > 1);
      scope.querySelector('[value="rooms"]').disabled = linked;
      group.hidden = scope.value !== 'rooms' || linked;
      for (const input of checkboxes) {
        const room = Number(input.value);
        input.checked = picked.has(room);
        input.disabled = locked || (!input.checked && !roomTarget(targets, room));
      }
      const selected = selection(targets);
      button.disabled = locked || !selected.targets.length;
      return selected;
    },
    reset() { picked.clear(); running = []; }
  };
}
