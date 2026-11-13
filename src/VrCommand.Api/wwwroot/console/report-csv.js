export function csvReportText(value) {
  return /\p{Cc}|^\p{White_Space}*[=+@-]/u.test(value) ? "'" + value : value;
}

export function csvReportAccuracy(value) {
  return actual => /^(?:0|[1-9]\d{0,2})(?:\.\d{1,2})?$/.test(actual) && Number(actual) === value;
}

export function matchesReportRows(bytes, rows) {
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { return false; }
  if (text[0] !== '\uFEFF') return false;
  // The server quotes every cell, including empty fields and multiline names.
  const field = /"((?:[^"]|"")*)"(,|\r\n)/y;
  field.lastIndex = 1;
  return rows.every(row => row.every((expected, index) => {
    const cell = field.exec(text);
    if (!cell || cell[2] !== (index === row.length - 1 ? '\r\n' : ',')) return false;
    const actual = cell[1].replaceAll('""', '"');
    return typeof expected === 'function' ? expected(actual) : actual === String(expected ?? '');
  })) && field.lastIndex === text.length;
}
