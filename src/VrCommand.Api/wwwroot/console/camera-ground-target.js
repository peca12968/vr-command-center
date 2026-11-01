// The observer camera targets the room floor, independently of combat collision
// or visible actor meshes. Empty space between rooms is not a room floor.
export function cameraGroundTarget(origin, direction, roomIds) {
  if (!origin || !direction || !Array.isArray(roomIds)
    || ![origin.x, origin.y, origin.z, direction.x, direction.y, direction.z].every(Number.isFinite)
    || origin.y < 0 || direction.y >= 0) return null;
  const distance = -origin.y / direction.y;
  const x = origin.x + distance * direction.x, z = origin.z + distance * direction.z;
  if (!Number.isFinite(x) || !Number.isFinite(z)) return null;
  const roomId = roomIds.find(id => Number.isInteger(id) && id >= 1 && id <= 5
    && Math.abs(x - (id - 3) * 14) <= 6 && Math.abs(z) <= 6);
  return roomId === undefined ? null : { roomId, target: [x, .8, z] };
}
