import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readVenueRosterCsv, venueRosterCsvTemplate } from '../../src/VrCommand.Api/wwwroot/console/venue-roster-csv.js';

const header = 'room,seat,name,headset';

test('imports quoted Chinese names, comma, escaped quotes, BOM and blank seat rows', () => {
  const csv = '\uFEFF"room","seat","name","headset"\r\n5,3,"隊員, 陳""一""",ViveXr\r\n1,4,,Quest3\r\n\r\n1,5,林二,Quest3\r\n';
  assert.deepEqual(readVenueRosterCsv(csv), [
    { roomId: 5, seat: 2, name: '隊員, 陳"一"', headset: 'ViveXr', lineNumber: 2 },
    { roomId: 1, seat: 4, name: '林二', headset: 'Quest3', lineNumber: 5 }
  ]);
});

test('the editable UTF-8 template enumerates every seat once', () => {
  const template = venueRosterCsvTemplate();
  assert(template.startsWith('\uFEFF' + header + '\r\n'));
  assert.throws(() => readVenueRosterCsv(template), /沒有可帶入/);
  const populated = template.replaceAll(',,Quest3', ',玩家,Quest3');
  assert.deepEqual(readVenueRosterCsv(populated).map(({ roomId, seat }) => [roomId, seat]),
    Array.from({ length: 25 }, (_, index) => [Math.floor(index / 5) + 1, index % 5]));
});

test('rejects wrong columns, repeated seats, non-1-based slots and unsupported devices', () => {
  assert.throws(() => readVenueRosterCsv('seat,room,name,headset\n1,2,玩家,Quest3'), /欄名/);
  assert.throws(() => readVenueRosterCsv(header + '\n1,1,,Quest3\n1,1,玩家,ViveXr'), /第 3 列.*重複/);
  assert.throws(() => readVenueRosterCsv(header + '\n2,0,玩家,Quest3'), /第 2 列.*1 至 5/);
  assert.throws(() => readVenueRosterCsv(header + '\n1,1,玩家,Quest2'), /第 2 列.*頭盔/);
});

test('rejects extra or missing fields, broken quotes, multiline or overlong names', () => {
  const invalid = ['1,1,玩家,Quest3,extra', '1,1,玩家', '1,1,"玩家"x,Quest3', '1,1,"玩家,Quest3',
    '1,1,"第一行\n第二行",Quest3'];
  for (const row of invalid)
    assert.throws(() => readVenueRosterCsv(header + '\n' + row), /第 2 列格式錯誤/);
  assert.throws(() => readVenueRosterCsv(header + '\n1,1,' + '甲'.repeat(81) + ',Quest3'), /80 字元/);
  assert.throws(() => readVenueRosterCsv(header + '\n1,1,甲\u0000乙,Quest3'), /單行文字/);
});
