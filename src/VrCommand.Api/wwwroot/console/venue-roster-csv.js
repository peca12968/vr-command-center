export const maxRosterCsvBytes = 16 * 1024;
const columns = ['room', 'seat', 'name', 'headset'];

function readFields(line, number) {
  const field = /"((?:[^"]|"")*)"|([^",]*)/y;
  const result = [];
  let offset = 0;
  for (const [index] of columns.entries()) {
    field.lastIndex = offset;
    const match = field.exec(line);
    const end = field.lastIndex;
    if (!match || (index < columns.length - 1 ? line[end] !== ',' : end !== line.length))
      throw new Error(`CSV 第 ${number} 列格式錯誤，請核對逗號及雙引號。`);
    result.push(match[1] === undefined ? match[2] : match[1].replaceAll('""', '"'));
    offset = end + 1;
  }
  return result;
}

export function readVenueRosterCsv(text) {
  const [header, ...lines] = text.replace(/^\uFEFF/, '').split(/\r\n|\n|\r/);
  if (readFields(header, 1).some((field, index) => field !== columns[index]))
    throw new Error('CSV 欄名須依序為 room、seat、name、headset。');
  const entries = [];
  const seen = new Set();
  for (const [index, line] of lines.entries()) {
    if (!line.trim()) continue;
    const lineNumber = index + 2;
    const [roomText, seatText, name, headset] = readFields(line, lineNumber).map(field => field.trim());
    if (!/^[1-5]$/.test(roomText) || !/^[1-5]$/.test(seatText))
      throw new Error(`CSV 第 ${lineNumber} 列的房號及席號須為 1 至 5。`);
    if (!['Quest3', 'ViveXr'].includes(headset))
      throw new Error(`CSV 第 ${lineNumber} 列的頭盔須填 Quest3 或 ViveXr。`);
    const key = `${roomText}/${seatText}`;
    if (seen.has(key)) throw new Error(`CSV 第 ${lineNumber} 列的房間及席位重複。`);
    seen.add(key);
    if (name.length > 80 || /[\u0000-\u001f\u007f-\u009f]/u.test(name))
      throw new Error(`CSV 第 ${lineNumber} 列的玩家名稱須為 80 字元以內的單行文字。`);
    if (name) entries.push({ roomId: Number(roomText), seat: Number(seatText) - 1, name, headset, lineNumber });
  }
  if (!entries.length) throw new Error('CSV 沒有可帶入的玩家名稱。');
  return entries;
}

export function venueRosterCsvTemplate() {
  const seats = Array.from({ length: 25 }, (_, index) => `${Math.floor(index / 5) + 1},${index % 5 + 1},,Quest3`);
  return '\uFEFF' + [columns.join(','), ...seats, ''].join('\r\n');
}
