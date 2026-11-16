export function recordedPointInRoom(point, roomId, radius) {
  // Match the server's single-precision positions and room bounds.
  const center = (roomId - 3) * 14, bound = Math.fround(radius);
  return Number.isFinite(point?.x) && Number.isFinite(point?.z)
    && Math.abs(Math.fround(Math.fround(point.x) - center)) <= bound && Math.abs(Math.fround(point.z)) <= bound;
}
