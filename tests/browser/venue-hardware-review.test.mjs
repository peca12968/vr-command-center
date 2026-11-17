import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isVenueHardwareReview } from '../../src/VrCommand.Api/wwwroot/console/venue-hardware-review.js';

function review(mode = 'Independent') {
  return { version: 1, verified: true, rehearsalComplete: true, mode, bindingManifestSha256: 'a'.repeat(64),
    configurationsVerified: true, simulatedHardwareOnly: true, physicalDeliveryConfirmed: false,
    rooms: Array.from({ length: 5 }, (_, index) => ({ roomId: index + 1,
      sessionId: `${mode === 'Independent' ? index + 1 : 1}0000000-0000-0000-0000-000000000000`,
      exitCode: 0, error: null, termination: 'operator-stop', acknowledged: 2, cancelled: 1, mockFailed: 0,
      seats: [{ seat: 0, acknowledged: 2, cancelled: 0, mockFailed: 0 }, { seat: 4, acknowledged: 0, cancelled: 1, mockFailed: 0 }] })) };
}

test('accepts independent, linked and legacy room-only summaries with the original counts', () => {
  assert(isVenueHardwareReview(review()));
  assert(isVenueHardwareReview(review('Linked')));
  const legacy = review();
  legacy.configurationsVerified = false;
  for (const room of legacy.rooms) room.seats = null;
  assert(isVenueHardwareReview(legacy));
});

test('accepts an incomplete verified review with a failed room and a room missing its report', () => {
  const failed = review();
  failed.rehearsalComplete = false;
  Object.assign(failed.rooms[2], { exitCode: 1, termination: 'binding-mismatch' });
  Object.assign(failed.rooms[4], { exitCode: 1, termination: null, error: 'InvalidOperationException',
    acknowledged: null, cancelled: null, mockFailed: null, seats: null });
  assert(isVenueHardwareReview(failed));
});

test('shows an incomplete review when a room stopped without an attachment', () => {
  const report = review();
  report.rehearsalComplete = false;
  Object.assign(report.rooms[1], { exitCode: 1, termination: 'duration', acknowledged: 0, cancelled: 0 });
  for (const seat of report.rooms[1].seats) Object.assign(seat, { acknowledged: 0, cancelled: 0 });
  assert(isVenueHardwareReview(report));
});

test('rejects physical claims, mixed linked sessions, duplicate seats and inconsistent totals', () => {
  for (const invalid of [
    report => { report.physicalDeliveryConfirmed = true; },
    report => { report.simulatedHardwareOnly = false; },
    report => { report.verified = false; },
    report => { report.mode = 'Linked'; },
    report => { report.rooms[1].roomId = 1; },
    report => { report.rooms[1].seats[1].seat = 0; },
    report => { report.rooms[1].acknowledged = 1; },
    report => { report.rooms[0].mockFailed = Infinity; },
    report => { report.rehearsalComplete = false; },
    report => { report.rooms[0].termination = 'binding-mismatch'; },
    report => { report.rooms[0].termination = 'unknown'; }
  ]) {
    const report = review();
    invalid(report);
    assert.equal(isVenueHardwareReview(report), false);
  }
});

test('source evidence accounts for all attempted signals and accepts older summaries', () => {
  const report = review();
  Object.assign(report, { attemptIdentitiesVerified: true, sourceEventsVerified: true, sourceSignalsVerified: 15 });
  assert(isVenueHardwareReview(report));
  for (const invalid of [
    { sourceSignalsVerified: 10 }, { sourceSignalsVerified: undefined }, { sourceEventsVerified: false },
    { sourceEventsVerified: undefined }, { attemptIdentitiesVerified: undefined }
  ]) assert.equal(isVenueHardwareReview({ ...report, ...invalid }), false);
  assert(isVenueHardwareReview({ ...report, sourceEventsVerified: false, sourceSignalsVerified: 0 }));
  assert(isVenueHardwareReview({ ...report, sourceEventsVerified: undefined, sourceSignalsVerified: undefined }));
});
