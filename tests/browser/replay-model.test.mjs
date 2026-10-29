import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateRecording, frameAtTime } from '../../src/VrCommand.Api/wwwroot/console/replay-model.js';
const sample = JSON.parse(await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/examples/simulation.json', import.meta.url), 'utf8'));
function invalid(edit, pattern) { const value = structuredClone(sample); edit(value); assert.throws(() => validateRecording(value), pattern); }

test('actual geometric recording reconstructs final and intermediate statistics', () => {
  const recording = validateRecording(sample);
  assert.equal(recording.duration, 10.4);
  assert.equal(recording.frameStatistics[0][0].ammoUsed, 0);
  const firstShot = sample.frames.findIndex(frame => frame.throughSequence === 1);
  assert.equal(recording.frameStatistics[firstShot][0].ammoUsed, 1);
  assert.equal(recording.frameStatistics[firstShot][0].health, 100);
  assert.equal(recording.frameStatistics.at(-1)[0].accuracyPercent, 66.67);
  assert.equal(recording.frameStatistics.at(-1)[0].health, 80);
});
test('time lookup selects the final state for equal ticks and clamps to the last frame', () => {
  const expected = sample.frames.findLastIndex(frame => frame.tick === 4);
  assert.equal(frameAtTime(sample.frames, .2, sample.tickSeconds), expected);
  assert.equal(frameAtTime(sample.frames, 100, sample.tickSeconds), sample.frames.length - 1);
});
test('legacy and unknown recording profiles are rejected', () => invalid(data => { data.schemaVersion = 1; }, /schema 2/));
test('old exports retain their appearance while new exports may opt in explicitly', () => {
  assert.doesNotThrow(() => validateRecording(structuredClone(sample)));
  const value = structuredClone(sample); value.assetSet = 'field-props-v1'; assert.doesNotThrow(() => validateRecording(value));
});
test('unknown or null appearance profiles cannot silently downgrade to old art', () => {
  invalid(data => { data.assetSet = 'field-props-v99'; }, /素材/);
  invalid(data => { data.assetSet = null; }, /素材/);
});
test('sequence gaps cannot masquerade as complete recordings', () => invalid(data => { data.events[1].sequence = 5; }, /序號/));
test('snapshot health must agree with accepted damage events', () => invalid(data => { data.frames[0].players[0].health = 80; }, /不一致/));
test('final report cannot disagree with the world event stream', () => invalid(data => { data.statistics.players[0].kills = 99; }, /結束統計/));
test('muzzle poses cannot contain non-finite coordinates', () => invalid(data => { data.frames[0].players[0].muzzle.x = Infinity; }, /姿態/));
test('ray distance is read from the record and must be bounded', () => invalid(data => { data.events[0].distance = 9000; }, /射線/));
test('enemy hit cannot be attached to a recorded cover collision', () => invalid(data => { const shot = data.events.find(event => event.kind === 'ShotFired' && event.hit === 'Enemy'); shot.hit = 'Cover'; shot.targetId = data.props[0].id; }, /射線不符/));
test('damage requires an associated enemy shot', () => invalid(data => { data.events.find(event => event.kind === 'PlayerDamaged').enemyId = data.frames.at(-1).enemies[1].id; }, /敵軍射線/));
test('unfinished and oversized frame collections are rejected', () => {
  invalid(data => { data.frames.at(-1).phase = 'Running'; }, /結束快照/);
  invalid(data => { data.frames = Array(20001).fill(data.frames[0]); }, /快照數量/);
});
test('recording text is data and is not interpreted or used as an object key', () => {
  const data = structuredClone(sample); data.mission.definition.name = '<img src=x onerror="window.bad=true">';
  assert.equal(validateRecording(data).data.mission.definition.name, data.mission.definition.name);
});
