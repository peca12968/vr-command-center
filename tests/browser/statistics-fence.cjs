const fs = require('node:fs/promises');
const path = require('node:path');

// Hold a genuine earlier GET response while the remaining reports commit.
// No fabricated statistics, repeated writes, headers or credential capture.
module.exports = async function statisticsFence({ page, api, base, session, playerId, shotId, enemyId, reportId, screenshots, check }) {
  const detail = base + '/api/sessions/' + session.id;
  // Keep the separate reads controllable so this regression also fails against the previous shipped console.
  const routePattern = url => [detail, detail + '/statistics', detail + '/overview'].includes(url.href);
  let oldResponse, captured, releaseOld, releaseFresh;
  const capture = new Promise(resolve => { captured = resolve; });
  const oldGate = new Promise(resolve => { releaseOld = resolve; });
  const freshGate = new Promise(resolve => { releaseFresh = resolve; });
  let first = true;
  const intercept = async route => {
    if (route.request().method() !== 'GET') return route.continue();
    if (route.request().url() === detail) { await oldGate; return route.continue(); }
    if (!first) { await freshGate; return route.continue(); }
    first = false;
    const response = await route.fetch();
    if (response.status() !== 200) throw new Error('Controlled earlier statistics GET was not accepted');
    const read = await response.json();
    oldResponse = read.statistics ?? read; captured();
    await oldGate; await route.fulfill({ response });
  };
  const dispose = async () => { releaseOld(); releaseFresh(); await page.unroute(routePattern, intercept); };
  try {
    await api('/sessions/' + session.id + '/combat', 'POST', { reportId: reportId(), origin: 'Simulation', playerId, kind: 'ShotFired', shotId }, 'GameServer');
    await page.route(routePattern, intercept);
    await page.locator('#refresh').click();
    let timer;
    try { await Promise.race([capture, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Statistics read was not captured within 30000ms')), 30000); })]); }
    finally { clearTimeout(timer); }
    for (const report of [{ kind: 'ShotHit', shotId, enemyId }, { kind: 'EnemyEliminated', shotId, enemyId }, { kind: 'PlayerDamaged', damage: 20 }])
      await api('/sessions/' + session.id + '/combat', 'POST', { reportId: reportId(), origin: 'Simulation', playerId, ...report }, 'GameServer');
    const accepted = await api('/sessions/' + session.id);
    releaseOld();
    await page.waitForFunction(() => {
      const row = [...document.querySelectorAll('#statistics tr')].find(row => row.cells[0]?.textContent === 'Alpha 01');
      return document.querySelector('#statistics-origin').textContent === '模擬資料' && row && [...row.cells].map(cell => cell.textContent).join('|') === 'Alpha 01|1|0|0|0|0%|100';
    }, undefined, { polling: 100 });
    const partial = await page.evaluate(() => ({ origin: document.querySelector('#statistics-origin').textContent,
      session: document.querySelector('#session-meta').textContent,
      events: [...document.querySelectorAll('#event-list li')].map(item => item.textContent),
      rows: [...document.querySelectorAll('#statistics tr')].map(row => [...row.cells].map(cell => cell.textContent)), notice: document.querySelector('#notice').textContent }));
    await fs.writeFile(path.join(screenshots, 'statistics-origin-fence.json'), JSON.stringify({ complete: true, sessionId: session.id,
      earlierStatisticsSequence: oldResponse.throughSequence, acceptedSessionSequence: accepted.sequence, partial,
      scope: 'A genuine earlier read after ShotFired, released after all four reports committed.' }, null, 2));
    check(partial.session.endsWith('序號 ' + oldResponse.throughSequence) && partial.events[0]?.includes('#' + oldResponse.throughSequence + ' '),
      'Held battle totals, session revision and latest displayed event belong to the same captured sequence');
    return { partial, acceptedSequence: accepted.sequence, release: releaseFresh, dispose };
  } catch (error) { await dispose(); throw error; }
};
