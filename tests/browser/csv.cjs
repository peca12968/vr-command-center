// Independent reader for downloaded CSV evidence, including embedded CR/LF and doubled quotes.
module.exports = function readCsv(bytes) {
  const text = bytes.toString('utf8').replace(/^\uFEFF/, '');
  const rows = []; let row = [], field = '', quoted = false;
  for (let index = 0; index < text.length; index++) {
    const character = text[index];
    if (character === '"') {
      if (quoted && text[index + 1] === '"') { field += '"'; index++; }
      else quoted = !quoted;
    } else if (!quoted && character === ',') { row.push(field); field = ''; }
    else if (!quoted && character === '\r' && text[index + 1] === '\n') {
      row.push(field); rows.push(row); row = []; field = ''; index++;
    } else field += character;
  }
  if (quoted || row.length || field) throw new Error('Incomplete CSV');
  const columns = rows.shift();
  if (!columns?.length || new Set(columns).size !== columns.length) throw new Error('Invalid CSV columns');
  return rows.map(cells => {
    if (cells.length !== columns.length) throw new Error('Invalid CSV row width');
    return Object.fromEntries(columns.map((column, index) => [column, cells[index]]));
  });
};
