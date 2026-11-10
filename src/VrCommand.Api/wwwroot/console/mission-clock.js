export const formatClock = seconds => `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
export const missionTicksPerSecond = 20;

// Recorded authoritative simulation ticks; never extrapolate from browser / UTC time.
export function recordedClock(header, tick) {
  const duration = header?.missionDurationSeconds;
  if (header?.missionClockVersion !== 1 || !Number.isInteger(duration) || duration < 60 || duration > 14400 || !Number.isSafeInteger(tick) || tick < 0) return '';
  return `活動時間 ${formatClock(Math.floor(tick / missionTicksPerSecond))} / 計畫 ${formatClock(duration)}`;
}
