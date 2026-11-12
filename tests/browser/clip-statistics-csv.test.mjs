import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const code = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/world-clip-statistics.js', import.meta.url), 'utf8');
const { matchesClipCsv } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const header = '"reportVersion","rowType","sessionId","streamId","fromFrame","throughFrame","reportRoomId","reportPlayerId","playerId","playerName","playerRoomId","ammoUsed","shotsHit","matchedShots","kills","hitsReceived","damageTaken","accuracyPercent"\r\n';
const report = { sessionId: 'session', streamId: 'stream', fromFrame: 7, throughFrame: 11, roomId: 2, playerId: 'player',
  players: [{ playerId: 'player', name: '  =名"稱\r\n', roomId: 2, ammoUsed: 2, shotsHit: 1, matchedShots: 1,
    kills: 0, hitsReceived: 2, damageTaken: 40, accuracyPercent: 50 }] };
const csv = '\uFEFF' + header + '"1","Player","session","stream","7","11","2","player","player","\'  =名""稱\r\n","2","2","1","1","0","2","40","50.00"\r\n';

test('Matches the verified scoped rows and preserves quoted Unicode, line breaks and spreadsheet text protection', () => {
  assert(matchesClipCsv(Buffer.from(csv), report));
  for (const [original, substitution] of [['"session"', '"other"'], ['"stream"', '"other"'],
    ['"7","11","2"', '"7","12","2"'], ['"7","11","2"', '"7","11","3"'], ['"player","player"', '"other","player"'],
    ['"40"', '"41"'], ['"50.00"', '"5e1"'], ['"50.00"', '""'], ["'  =名", '  =名']]) {
    assert(!matchesClipCsv(Buffer.from(csv.replace(original, substitution)), report));
  }
  assert(!matchesClipCsv(Buffer.from(csv + csv.slice(1 + header.length)), report));
  assert(!matchesClipCsv(Buffer.from(csv.slice(1)), report));
  assert(!matchesClipCsv(Buffer.from(csv.slice(0, -2)), report));
  assert(!matchesClipCsv(Uint8Array.of(239, 187, 191, 255), report));
});

test('An empty clip retains its original recording scope and contains no player fields', () => {
  const empty = { ...report, roomId: null, playerId: null, players: [] };
  const prefix = '\uFEFF' + header + '"1","Clip","session","stream","7","11","",""';
  const body = prefix + ',""'.repeat(10) + '\r\n';
  assert(matchesClipCsv(Buffer.from(body), empty));
  assert(!matchesClipCsv(Buffer.from(prefix + ',""' + ',"0"' + ',""'.repeat(8) + '\r\n'), empty));
  assert(!matchesClipCsv(Buffer.from(body.replace('"11","",""', '"11","2",""')), empty));
});
