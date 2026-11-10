// Keep the real authenticated response and terminate or stall its body once.
const path = require('node:path');

async function armLiveWatchFault(page, sessionId, kind) {
  await page.evaluate(({ sessionId, kind }) => {
    const original = window.fetch;
    const watch = `/api/sessions/${sessionId}/world/watch`;
    window.fetch = async (...args) => {
      const url = new URL(args[0], location.href);
      if (url.origin !== location.origin || url.pathname !== watch || url.searchParams.get('mode') !== 'live')
        return original(...args);
      window.fetch = original;
      const response = await original(...args);
      const reader = response.body.getReader();
      const signal = args[1].signal;
      let cut = false, settle;
      const held = new Promise(resolve => { settle = resolve; });
      const body = new ReadableStream({
        start(controller) {
          signal.addEventListener('abort', () => {
            if (kind === 'stall' && cut) controller.error(new DOMException('Closed by observer', 'AbortError'));
            settle();
          }, { once: true });
          window.cutLiveWatch = () => {
            cut = true;
            window.cutLiveWatch = null;
            if (kind === 'eof') controller.close();
            void reader.cancel().catch(() => {});
          };
        },
        async pull(controller) {
          const { done, value } = await reader.read();
          if (cut) return held;
          if (done) controller.close();
          else controller.enqueue(value);
        },
        cancel() { settle(); return reader.cancel().catch(() => {}); }
      });
      return new Response(body, { status: response.status, headers: response.headers });
    };
  }, { sessionId, kind });
}

function liveWatches(page, base, sessionId) {
  const requests = [];
  const listener = request => {
    const url = new URL(request.url());
    if (url.origin === base && url.pathname === `/api/sessions/${sessionId}/world/watch` && url.searchParams.get('mode') === 'live')
      requests.push(url.pathname);
  };
  page.on('request', listener);
  return { requests, dispose() { page.off('request', listener); } };
}

async function cutLiveWatch(page) {
  return page.evaluate(() => {
    const sequence = Number(document.querySelector('#world-canvas').dataset.sequence);
    window.cutLiveWatch();
    return sequence;
  });
}

async function openFaultedWatch(page, sessionId, kind) {
  const before = Number(await page.locator('#world-canvas').getAttribute('data-sequence'));
  await armLiveWatchFault(page, sessionId, kind);
  await page.locator('#world-live').click();
  await page.waitForFunction(sequence => typeof window.cutLiveWatch === 'function'
    && Number(document.querySelector('#world-canvas').dataset.sequence) > sequence
    && document.querySelector('#world-freshness').textContent === '正在接收快照', before, { polling: 100 });
}

async function waitForLiveFrame(page, sequence) {
  return page.waitForFunction(after => Number(document.querySelector('#world-canvas').dataset.sequence) > after
    && document.querySelector('#world-freshness').textContent === '正在接收快照', sequence, { timeout: 9000, polling: 100 });
}

async function checkLiveWatch({ page, base, live, api, canvas, screenshots, check, extended }) {
  const sessionId = live.header.sessionId;
  const watches = liveWatches(page, base, sessionId);
  const fixedCamera = await canvas.getAttribute('data-camera');
  const message = page.locator('#world-message');
  const pattern = `**/api/sessions/${sessionId}/world/watch?**`;
  try {
    await openFaultedWatch(page, sessionId, 'eof');
    const lostAt = await cutLiveWatch(page);
    await waitForLiveFrame(page, lostAt);
    check(watches.requests.length === 2 && await canvas.getAttribute('data-camera') === fixedCamera
      && await page.locator('#world-room').inputValue() === '2', 'Live EOF reconnects once to the original recording with room and camera intact');
    if (!extended) return;

    await openFaultedWatch(page, sessionId, 'stall');
    const stalledAt = await cutLiveWatch(page);
    await page.locator('#world-freshness').filter({ hasText: '快照已中斷或過期' }).waitFor();
    check(watches.requests.length === 3 && Number(await canvas.getAttribute('data-sequence')) === stalledAt,
      'Silent live transport first marks the last displayed frame stale');
    await page.screenshot({ path: path.join(screenshots, 'live-watch-stalled.png') });
    await waitForLiveFrame(page, stalledAt);
    check(watches.requests.length === 4 && await canvas.getAttribute('data-camera') === fixedCamera,
      'The heartbeat watchdog reconnects a silent stream without moving the camera');

    await openFaultedWatch(page, sessionId, 'eof');
    const current = await api(`/sessions/${sessionId}/world`);
    const foreign = { ...current, header: { ...current.header, streamId: '00000000-0000-4000-8000-000000000001' } };
    const replyForeign = route => route.fulfill({ status: 200, contentType: 'text/event-stream', body: `event: header\ndata: ${JSON.stringify(foreign)}\n\n` });
    await page.route(pattern, replyForeign);
    try {
      const fencedAt = await cutLiveWatch(page);
      await message.filter({ hasText: '回應的錄製來源不同' }).waitFor();
      check(watches.requests.length === 6 && Number(await canvas.getAttribute('data-sequence')) === fencedAt
        && await page.locator('#world-recording').inputValue() === sessionId, 'A retry with a foreign stream cannot replace the original scene');
    } finally { await page.unroute(pattern, replyForeign); }

    await openFaultedWatch(page, sessionId, 'eof');
    const serviceUnavailable = route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    await page.route(pattern, serviceUnavailable);
    try {
      await cutLiveWatch(page);
      await message.filter({ hasText: '觀戰服務回應 503；可重新連接' }).waitFor();
      check(watches.requests.length === 10 && (await page.locator('#world-freshness').innerText()).includes('過期'),
        'Three consecutive transient failures exhaust the retry budget and leave the frame stale');
    } finally { await page.unroute(pattern, serviceUnavailable); }

    await openFaultedWatch(page, sessionId, 'eof');
    await page.evaluate(() => {
      const note = document.querySelector('#world-message');
      const leave = new MutationObserver(() => {
        if (!note.textContent.includes('正在重新連接')) return;
        leave.disconnect();
        document.querySelector('#tab-operations').click();
      });
      leave.observe(note, { childList: true });
      window.cutLiveWatch();
    });
    await page.locator('#world-player').waitFor({ state: 'hidden' });
    await page.waitForTimeout(1100);
    check(watches.requests.length === 11, 'Leaving observation cancels the queued reconnect');
  } finally { watches.dispose(); }
}

module.exports = { checkLiveWatch, armLiveWatchFault, waitForLiveFrame, cutLiveWatch };
