const id = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const emptyId = '00000000-0000-0000-0000-000000000000';
const counts = ['acknowledged', 'cancelled', 'mockFailed'];
const finished = ['duration', 'ended', 'operator-stop', 'operator-room-stop'];
export const terminationLabels = Object.freeze({
  duration: '排演時間到期', ended: '原場次已結束', 'operator-stop': '主控停止排演',
  'operator-room-stop': '操作員停止本房', 'attempt-limit': '達模擬嘗試上限', 'binding-mismatch': '入場與原綁定不符',
  'management-refused': '管理服務拒絕', 'management-invalid-response': '管理回覆格式錯誤'
});

function validCounts(row) {
  return counts.every(key => Number.isSafeInteger(row[key]) && row[key] >= 0)
    && counts.reduce((sum, key) => sum + row[key], 0) <= 32768;
}

function validRoom(row, index, configurationsVerified) {
  if (row?.roomId !== index + 1 || typeof row.sessionId !== 'string' || !id.test(row.sessionId)
      || row.sessionId === emptyId || ![0, 1].includes(row.exitCode)) return false;
  if (row.error != null) return row.exitCode === 1 && typeof row.error === 'string' && /^[a-zA-Z0-9]{1,64}$/.test(row.error)
    && row.termination == null && row.seats == null && counts.every(key => row[key] == null);
  if (typeof row.termination !== 'string' || !Object.hasOwn(terminationLabels, row.termination)
      || (row.exitCode === 0 && !finished.includes(row.termination)) || !validCounts(row)) return false;
  if (!configurationsVerified) return row.seats == null;
  return Array.isArray(row.seats) && row.seats.length >= 1 && row.seats.length <= 5
    && row.seats.every((seat, index) => seat && Number.isInteger(seat.seat) && seat.seat >= 0 && seat.seat <= 4
      && (index === 0 || seat.seat > row.seats[index - 1].seat) && validCounts(seat))
    && counts.every(key => row.seats.reduce((sum, seat) => sum + seat[key], 0) === row[key]);
}

export function isVenueHardwareReview(report) {
  return report?.version === 1 && report.verified === true && report.simulatedHardwareOnly === true
    && report.physicalDeliveryConfirmed === false && typeof report.rehearsalComplete === 'boolean'
    && typeof report.configurationsVerified === 'boolean' && ['Independent', 'Linked'].includes(report.mode)
    && typeof report.bindingManifestSha256 === 'string' && /^[0-9a-f]{64}$/.test(report.bindingManifestSha256)
    && Array.isArray(report.rooms) && report.rooms.length === 5
    && report.rooms.every((room, index) => validRoom(room, index, report.configurationsVerified))
    && report.rehearsalComplete === report.rooms.every(room => room.exitCode === 0)
    && new Set(report.rooms.map(room => room.sessionId)).size === (report.mode === 'Linked' ? 1 : 5);
}
