const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const { validateConfig, validateRequest } = require('./active-operator-ui.cjs');
const root = path.resolve(__dirname, '../..');
const file = path.join(root, 'artifacts/desktop-active/20261101-120000-1234abcd/active-ui-config.json');
const config = () => ({ source: 'Simulation', headsets: 0, baseUrl: 'http://127.0.0.1:54321', sessionId: '11111111-2222-3333-4444-555555555555' });
const request = () => ({ request: 1, sessionId: config().sessionId, environment: { mode: 'VR', weather: 'Storm', timeOfDay: 'Night', lightning: true }, behavior: 'Hold' });
test('active console only binds its owned Simulation fixture directory', () => {
  assert.equal(validateConfig(file, config()), path.dirname(file));
  for (const name of ['keys.json', '../active-ui-config.json']) assert.throws(() => validateConfig(path.join(path.dirname(file), name), config()));
  assert.throws(() => validateConfig(path.join(root, 'artifacts/desktop-venue/20261101-120000-1234abcd/active-ui-config.json'), config()));
});
test('active console refuses formal, remote, credential and ambiguous endpoints', () => {
  for (const baseUrl of ['http://127.0.0.1:5080', 'https://127.0.0.1:54321', 'http://localhost:54321', 'http://192.168.1.3:54321',
    'http://user:secret@127.0.0.1:54321', 'http://127.1:54321', 'http://127.0.0.1:54321/', 'http://127.0.0.1:54321/console/', 'http://127.0.0.1:54321/?key=x', 'http://127.0.0.1:54321/#key'])
    assert.throws(() => validateConfig(file, { ...config(), baseUrl }));
});
test('headset or unknown-source metadata cannot authorize a UI companion', () => {
  for (const fields of [{ source: 'Tracked' }, { headsets: null }, { headsets: 1 }, { sessionId: '' }]) assert.throws(() => validateConfig(file, { ...config(), ...fields }));
});
test('only the next bounded same-session UI request is accepted', () => {
  validateRequest(request(), config().sessionId, 1);
  for (const fields of [{ request: 0 }, { request: 2 }, { sessionId: 'another' }]) assert.throws(() => validateRequest({ ...request(), ...fields }, config().sessionId, 1));
  assert.throws(() => validateRequest({ ...request(), request: 4 }, config().sessionId, 4));
});
test('UI requests cannot smuggle coordinates, new modes or unknown AI policy', () => {
  for (const fields of [{ mode: 'MR' }, { weather: 'Snow' }, { lightning: 1 }, { timeOfDay: 'Unknown' }, { position: { x: 10 } }])
    assert.throws(() => validateRequest({ ...request(), environment: { ...request().environment, ...fields } }, config().sessionId, 1));
  assert.throws(() => validateRequest({ ...request(), behavior: 'Injected' }, config().sessionId, 1));
});
