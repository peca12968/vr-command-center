import { isVenueHardwareReview, terminationLabels } from './venue-hardware-review.js';

const maxReviewBytes = 16 * 1024;
const $ = id => document.getElementById('venue-hardware-review-' + id);

export function mountVenueHardwareReview(getState, master) {
  const panel = $('panel'), file = $('file'), message = $('message');
  const results = $('results'), rooms = $('rooms'), picker = $('room'), seats = $('seats');
  let active = false, review = null, readEpoch = 0;

  function showSeats() {
    const selected = review?.rooms.find(room => room.roomId === Number(picker.value));
    seats.replaceChildren();
    $('seat-table').hidden = !selected?.seats;
    $('seat-status').textContent = selected?.seats ? '' : '此房沒有逐席核對結果。';
    for (const row of selected?.seats ?? []) {
      const line = seats.insertRow();
      for (const value of [row.seat + 1, row.acknowledged, row.cancelled, row.mockFailed])
        line.insertCell().textContent = value;
    }
  }

  function matchRooms() {
    if (!review) return;
    const current = new Map(getState().rooms.map(room => [room.id, room.sessionId]));
    const matches = review.rooms.filter(room => current.get(room.roomId) === room.sessionId).length;
    $('matches').textContent = `目前場次與報告相符 ${matches} / 5 房。`;
    for (const row of rooms.rows) {
      const source = review.rooms[Number(row.dataset.reviewRoom) - 1];
      const currentId = current.get(source.roomId);
      row.lastElementChild.textContent = currentId === source.sessionId ? '場次相符' : currentId ? '目前為另一場次' : '目前無場次';
    }
  }

  function showReview() {
    results.hidden = !review;
    rooms.replaceChildren();
    picker.replaceChildren();
    seats.replaceChildren();
    if (!review) {
      $('summary').textContent = $('matches').textContent = $('seat-status').textContent = '';
      $('seat-table').hidden = true;
      return;
    }
    const mode = review.mode === 'Linked' ? '五房合併' : '五房獨立';
    $('summary').textContent = `${mode} · 排演${review.rehearsalComplete ? '完成' : '未完成'} · ${review.configurationsVerified ? '含設定核對' : '僅房間總數'}`;
    for (const item of review.rooms) {
      const line = rooms.insertRow();
      line.dataset.reviewRoom = item.roomId;
      const result = item.error ? `未產生報告（${item.error}）` : terminationLabels[item.termination];
      for (const value of [item.roomId, item.sessionId.slice(0, 8), item.exitCode === 0 ? '完成' : '未完成', result,
        item.acknowledged ?? '—', item.cancelled ?? '—', item.mockFailed ?? '—', ''])
        line.insertCell().textContent = value;
      line.cells[1].title = item.sessionId;
      picker.add(new Option(`房間 ${item.roomId}`, item.roomId));
    }
    matchRooms();
    const failed = review.rooms.find(room => room.exitCode !== 0);
    if (failed) picker.value = String(failed.roomId);
    showSeats();
  }

  file.addEventListener('change', async () => {
    const input = file.files[0], own = ++readEpoch;
    review = null;
    showReview();
    message.textContent = '';
    if (!input || !active || !master()) return;
    const current = () => own === readEpoch && active && master();
    try {
      if (!input.size || input.size > maxReviewBytes) throw new Error();
      const candidate = JSON.parse(await input.text());
      if (!current()) return;
      if (!isVenueHardwareReview(candidate)) throw new Error();
      review = candidate;
      showReview();
    } catch {
      if (current()) message.textContent = '請選擇模擬器核對工具輸出的五房 JSON 摘要（16 KiB 以內）。';
    }
  });
  picker.addEventListener('change', showSeats);

  return {
    active(value) {
      active = value;
      panel.hidden = !active || !master();
      if (!active || !master()) {
        readEpoch++;
        panel.open = false;
        review = null;
        file.value = message.textContent = '';
        showReview();
      }
    },
    update: matchRooms
  };
}
