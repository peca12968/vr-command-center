const assert = require('node:assert/strict');
const { createHash, randomUUID } = require('node:crypto');

module.exports = async function seatTicketScopeBrowser({ context, api, tokens, base, check, captureErrors }) {
  const draft = { name: '同席重連票券核對', briefing: '', durationSeconds: 180, props: [],
    environment: { mode: 'VR', weather: 'Clear', timeOfDay: 'Day', lightning: false },
    enemies: { count: 0, behavior: 'Hold', autoAttack: false } };
  const vr = await api('/missions', 'POST', draft, 'Master', 201);
  const mr = await api('/missions', 'POST', { ...draft, environment: { ...draft.environment, mode: 'MR' } }, 'Master', 201);
  for (const mode of ['Linked', 'Independent']) {
    await verifyReceipt(mode);
  }

  async function verifyReceipt(mode) {
    const page = await context.newPage();
    captureErrors(page);
    const notice = page.locator('#notice'), selection = page.locator('#session-select');
    const roomId = 4, isMr = mode === 'Independent', pin = 'a'.repeat(64), role = isMr ? 'Room4' : 'Master';
    const address = '192.0.2.80', port = 17777;
    const sessions = [];
    const end = session => api(`/sessions/${session.id}/commands`, 'POST', { action: 'End', commandId: randomUUID() });
    const select = id => selection.selectOption(id);
    const files = [];
    const onDownload = file => files.push(file);
    page.on('download', onDownload);
    try {
      assert.deepEqual(await api('/sessions'), []);
      const rooms = [1, 2, 3, 4, 5];
      if (isMr) {
        const result = await api('/sessions/independent-set', 'POST',
          { rooms: rooms.map(room => ({ roomId: room, missionId: room === roomId ? mr.id : vr.id })) }, 'Master', 201, undefined, randomUUID());
        sessions.push(...result.sessions);
      } else sessions.push(await api('/sessions', 'POST', { mode, missionId: vr.id, roomIds: rooms }, 'Master', 201));
      const session = sessions.find(item => item.roomIds.includes(roomId));
      const route = `/sessions/${session.id}`;
      if (isMr) await api(route + '/commands', 'POST', { action: 'SetRoomAlignment', commandId: randomUUID(),
        expectedSequence: session.sequence, roomAlignment: { room4: pin } });
      const roster = await api('/venue/roster-admissions', 'POST', { seats: rooms.flatMap(room => Array.from({ length: 5 }, (_, seat) => ({
        sessionId: sessions.find(item => item.roomIds.includes(room)).id, roomId: room, seat,
        playerId: randomUUID(), requestId: randomUUID(), name: `${mode} ${room} 席 ${seat + 1}`, headset: 'Quest3'
      }))) });
      const players = roster.admissions.filter(row => row.player.roomId === roomId).map(row => row.player);
      const issue = player => api(route + `/players/${player.id}/join-ticket`, 'POST', undefined, role, 200, player.admissionId);
      const otherSeat = await issue(players[2]), oldSeat = await issue(players[0]);
      const old = players[0];
      await api(route + `/players/${old.id}`, 'DELETE', undefined, role, 204, old.admissionId, randomUUID());
      const joined = await api(route + '/players', 'POST', { playerId: old.id, roomId, name: old.name, headset: 'Quest3' }, role);
      const player = joined.players.find(row => row.id === old.id);
      assert.equal(player.seat, old.seat);
      assert.notEqual(player.admissionId, old.admissionId);
      const valid = await issue(player);
      if (!isMr) await api(route + '/commands', 'POST', { action: 'Begin', commandId: randomUUID() });
      await page.goto(base + '/console/');
      await page.locator('#login-key').fill(tokens[role]);
      await page.locator('#login-form button').click();
      await selection.locator(`option[value="${session.id}"]`).waitFor({ state: 'attached' });
      await select(session.id);
      await page.locator('#game-address').fill(address);
      await page.locator('#game-port').fill(String(port));
      await page.locator('#ticket-room').selectOption(String(roomId));
      const seat = page.locator(`#roster [data-roster-room="${roomId}"][data-roster-seat="${player.seat + 1}"] [data-player-action=ticket]`);
      const roomButton = page.locator('#download-room-tickets');
      const seatPath = base + '/api' + route + `/players/${player.id}/join-ticket`;
      const roomPath = base + '/api' + route + `/rooms/${roomId}/join-ticket-bundle`;

      async function blocked(url, button, replace, message) {
        const prior = files.length;
        await page.route(url, replace, { times: 1 });
        const read = page.waitForResponse(response => response.url() === url && response.request().method() === 'POST');
        await button.click();
        await read;
        await page.waitForFunction(() => !document.querySelector('#session-select').disabled);
        return (await notice.innerText()).includes(message) && files.length === prior;
      }
      for (const [label, reply] of [['other seat', otherSeat], ['superseded admission', oldSeat],
        ['mismatched expiry', { ...valid, expiresAtUtc: new Date(Date.parse(valid.expiresAtUtc) + 1000).toISOString() }]]) {
        check(await blocked(seatPath, seat, request => request.fulfill({ status: 200, json: reply }), '無法核對本席原入場或票券效期'),
          `${mode} discards the ${label} response without giving the selected player a file`);
      }
      const filePromise = page.waitForEvent('download');
      await seat.click();
      const seatFile = await filePromise;
      const chunks = [];
      for await (const chunk of await seatFile.createReadStream()) chunks.push(chunk);
      const config = JSON.parse(Buffer.concat(chunks));
      const admitted = await api('/player-tickets/validate', 'POST', { sessionId: session.id, ticket: config.joinTicket, protocolVersion: 2 }, 'GameServer');
      check(admitted.admissionId === player.admissionId && admitted.seat === player.seat && admitted.roomId === roomId
        && config.address === address && config.port === port && config.roomAlignmentSha256 === (isMr ? pin : undefined),
      `${mode} downloads the original admission and endpoint, with the correct MR pin when applicable`);
      await seatFile.delete();

      const roomDownload = page.waitForEvent('download');
      const roomReply = page.waitForResponse(response => response.url() === roomPath && response.request().method() === 'POST');
      await roomButton.click();
      const initial = await roomDownload, initialResponse = await roomReply;
      const headers = await initialResponse.allHeaders(), body = await initialResponse.body();
      const requestHeader = 'x-vrcommand-archive-request';
      assert.equal(initial.suggestedFilename(), 'room-04-connections.zip');
      assert.equal(headers['repr-digest'], `sha-256=:${createHash('sha256').update(body).digest('base64')}:`);
      assert.equal(headers[requestHeader], initialResponse.request().headers()[requestHeader]);
      assert(headers[requestHeader]);
      await initial.delete();
      await page.waitForFunction(() => !document.querySelector('#session-select').disabled);
      if (!isMr) {
        await page.locator('#ticket-room').selectOption('3');
        const otherFile = page.waitForEvent('download');
        const otherReply = page.waitForResponse(response => response.url() === base + '/api' + route + '/rooms/3/join-ticket-bundle'
          && response.request().method() === 'POST');
        await roomButton.click();
        const file = await otherFile, response = await otherReply;
        assert.equal(file.suggestedFilename(), 'room-03-connections.zip');
        const otherHeaders = await response.allHeaders(), otherBody = await response.body();
        await file.delete();
        await page.locator('#ticket-room').selectOption(String(roomId));
        check(await blocked(roomPath, roomButton, request => request.fulfill({ status: 200, headers: otherHeaders, body: otherBody }),
          '無法核對本房連線檔'), 'Linked rejects an authentic archive from another room');
      }
      check(await blocked(roomPath, roomButton, request => request.fulfill({ status: 200, headers, body }), '無法核對本房連線檔'),
        `${mode} rejects the original ZIP replayed against a different room download request`);
      const changed = Buffer.from(body);
      changed[20] ^= 1;
      check(await blocked(roomPath, roomButton, request => request.fulfill({ status: 200,
        headers: { ...headers, [requestHeader]: request.request().headers()[requestHeader] }, body: changed }), '無法核對本房連線檔'),
        `${mode} rejects a changed ZIP even when the response carries the current request identifier`);
      const recovery = page.waitForEvent('download');
      await roomButton.click();
      const recovered = await recovery;
      check(recovered.suggestedFilename() === 'room-04-connections.zip', `${mode} room ZIP downloads normally after a fresh verification`);
      await recovered.delete();
    } finally {
      await page.close();
      for (const session of sessions) await end(session);
    }
  }
};
