import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../../src/VrCommand.Api/wwwroot/console/connection-ui.js', import.meta.url), 'utf8');
const { validEndpoint } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const session = { id: 'session', combatStream: { streamId: 'stream' } };
const endpoint = { version: 1, sessionId: 'session', streamId: 'stream', address: '127.0.0.1', port: 17777, sessionEnded: false };
test('Published connection settings must belong to the selected session and stream', () => {
  assert.equal(validEndpoint(endpoint, session), true);
  for (const change of [{ version: 2 }, { sessionId: 'other' }, { streamId: 'other' }]) assert.equal(validEndpoint({ ...endpoint, ...change }, session), false);
  assert.equal(validEndpoint(endpoint, null), false); assert.equal(validEndpoint(endpoint, { id: 'session' }), false);
  assert.equal(validEndpoint({ ...endpoint, streamId: undefined }, { id: 'session' }), false);
});
test('Endpoint v1 accepts canonical unicast IPv4, not URL or wildcard destinations', () => {
  for (const address of ['192.168.1.100', '10.0.0.5']) assert.equal(validEndpoint({ ...endpoint, address }, session), true);
  for (const address of ['0.0.0.0', '224.0.0.1', '255.255.255.255', '127.1', '127.0.0.01', 'localhost', 'https://127.0.0.1', '::1', ' 127.0.0.1']) assert.equal(validEndpoint({ ...endpoint, address }, session), false);
});
test('Endpoint ports and ended metadata retain explicit contract types', () => {
  for (const port of [1023, 65536, 17777.1, '17777']) assert.equal(validEndpoint({ ...endpoint, port }, session), false);
  assert.equal(validEndpoint({ ...endpoint, sessionEnded: true }, session), true);
  assert.equal(validEndpoint({ ...endpoint, sessionEnded: undefined }, session), false);
});
