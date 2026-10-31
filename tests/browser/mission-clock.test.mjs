import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/mission-clock.js', import.meta.url), 'utf8');
const { recordedClock } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
test('Recorded clock uses source ticks including a paused or final boundary', () => {
  const header = { missionClockVersion: 1, missionDurationSeconds: 60 };
  assert.equal(recordedClock(header, 399), '活動時間 00:19 / 計畫 01:00');
  assert.equal(recordedClock(header, 400), '活動時間 00:20 / 計畫 01:00');
  assert.equal(recordedClock(header, 1200), '活動時間 01:00 / 計畫 01:00');
  assert.equal(recordedClock(header, 1220), '活動時間 01:01 / 計畫 01:00');
});
test('Old, future or invalid recording clocks do not fabricate time', () => {
  for (const header of [{}, { missionClockVersion: 0, missionDurationSeconds: 60 }, { missionClockVersion: 2, missionDurationSeconds: 60 }, { missionClockVersion: 1, missionDurationSeconds: 59 }]) assert.equal(recordedClock(header, 20), '');
  for (const tick of [undefined, -1, 1.5, Infinity]) assert.equal(recordedClock({ missionClockVersion: 1, missionDurationSeconds: 60 }, tick), '');
});
