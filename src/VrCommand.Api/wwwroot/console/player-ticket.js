function guidAt(view, offset) {
  const hex = (value, length) => value.toString(16).padStart(length, '0');
  const byte = index => hex(view.getUint8(offset + index), 2);
  return `${hex(view.getUint32(offset, true), 8)}-${hex(view.getUint16(offset + 4, true), 4)}-${hex(view.getUint16(offset + 6, true), 4)}`
    + `-${byte(8)}${byte(9)}-${byte(10)}${byte(11)}${byte(12)}${byte(13)}${byte(14)}${byte(15)}`;
}

export function matchesIssuedPlayerTicket(response, sessionId, player) {
  // The binary v2 scope is compared locally. The game server validates the signature.
  const encoded = typeof response?.ticket === 'string' && /^v2\.([A-Za-z0-9_-]{100})\.[A-Za-z0-9_-]{43}$/.exec(response.ticket);
  const expires = typeof response?.expiresAtUtc === 'string' && Date.parse(response.expiresAtUtc);
  if (!encoded || !Number.isSafeInteger(expires) || expires <= Date.now()) return false;
  const bytes = Uint8Array.from(atob(encoded[1].replaceAll('-', '+').replaceAll('_', '/')), byte => byte.charCodeAt(0));
  const payload = new DataView(bytes.buffer);
  return payload.getUint8(0) === 2 && guidAt(payload, 1) === sessionId && guidAt(payload, 17) === player.id
    && guidAt(payload, 33) === player.admissionId && payload.getUint8(49) === player.roomId && payload.getUint8(50) === player.seat
    && payload.getBigInt64(51) * 1000n === BigInt(expires);
}
