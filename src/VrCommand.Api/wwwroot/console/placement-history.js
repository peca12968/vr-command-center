// Local object edits only. Mission versions, management commands and credentials
// never enter this history. Returned values are detached from retained snapshots.
export function placementHistory({ maxEntries = 50, maxBytes = 2 * 1024 * 1024 } = {}) {
  if (!Number.isInteger(maxEntries) || maxEntries < 1 || !Number.isInteger(maxBytes) || maxBytes < 1) throw new Error('Invalid history bounds');
  let past = [], future = [];
  const encode = value => JSON.stringify({ props: value.props, prop: value.prop });
  const same = (a, b) => JSON.stringify(a.props) === JSON.stringify(b.props);
  const size = entry => entry.bytes;
  function clear() { past = []; future = []; }
  function record(before, after) {
    if (same(before, after)) return;
    const entry = { before: encode(before), after: encode(after) };
    entry.bytes = new TextEncoder().encode(entry.before + entry.after).length;
    // A divergent edit invalidates redo even if a single edit exceeds the budget.
    future = [];
    if (size(entry) > maxBytes) { clear(); return; }
    past.push(entry);
    while (past.length > maxEntries || past.reduce((sum, item) => sum + size(item), 0) > maxBytes) past.shift();
  }
  function travel(current, undo) {
    const from = undo ? past : future, to = undo ? future : past, entry = from.at(-1);
    if (!entry) return null;
    // Fail closed if a caller replaced the document without resetting history.
    if (!same(current, JSON.parse(undo ? entry.after : entry.before))) { clear(); return null; }
    from.pop(); to.push(entry); return JSON.parse(undo ? entry.before : entry.after);
  }
  return { clear, record, undo: current => travel(current, true), redo: current => travel(current, false),
    status: () => ({ undo: past.length, redo: future.length, bytes: [...past, ...future].reduce((sum, item) => sum + size(item), 0) }) };
}
