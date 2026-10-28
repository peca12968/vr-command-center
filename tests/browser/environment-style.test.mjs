import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const source = await readFile(path.join(root, 'src/VrCommand.Api/wwwroot/console/environment-style.js'), 'utf8');
const { environmentStyle, rainPoint, EnvironmentCueTracker } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const native = JSON.parse(execFileSync('dotnet', [process.env.VR_COMMAND_CHECKS_DLL || path.join(root, 'tests/VrCommand.Checks/bin/Release/net10.0/VrCommand.Checks.dll'), '--weather-vectors'], { encoding: 'utf8', windowsHide: true }));
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < .0001, `${actual} differs from native ${expected}`);

test('browser presentation agrees with compiled shared C# profiles at clock boundaries', () => {
  for (const row of native.profiles) {
    const result = environmentStyle(row.tick, row.weather, row.night, row.lightning, row.phase);
    for (const key of ['rain', 'fog', 'sun', 'ambient']) near(result[key], row[key]);
    row.sky.forEach((value, index) => near(result.sky[index], value));
    assert.equal(result.flash, row.flash); assert.equal(result.running, row.running);
  }
});
test('five room rain coordinates agree with native generation', () => {
  for (const row of native.rainPoints) { const result = rainPoint(row.room, row.index, row.tick); for (const key of ['x', 'y', 'z']) near(result[key], row[key]); }
});
test('observed strike tracker agrees with compiled native cue sequence', () => {
  const tracker = new EnvironmentCueTracker();
  for (const row of native.cues) assert.equal(tracker.advance(row.tick, 'Storm', true, true, 'Running'), row.sound);
});
test('seeks, initial joins and long gaps never cause an old thunder burst', () => {
  const tracker = new EnvironmentCueTracker(); assert.equal(tracker.advance(180, 'Storm', true, true, 'Running'), false);
  tracker.reset(); tracker.advance(140, 'Storm', true, true, 'Running'); assert.equal(tracker.advance(180, 'Storm', true, true, 'Running'), false);
  tracker.advance(100, 'Storm', true, true, 'Running'); assert.equal(tracker.advance(180, 'Storm', true, true, 'Running'), false);
});
test('unsupported policies and unbounded geometry fail closed', () => {
  assert.throws(() => environmentStyle(-1, 'Clear', false, false, 'Running'));
  assert.throws(() => environmentStyle(0, 'Snow', false, false, 'Running'));
  assert.throws(() => rainPoint(6, 0, 0)); assert.throws(() => rainPoint(1, 128, 0));
});
