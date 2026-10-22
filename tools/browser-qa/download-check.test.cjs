"use strict";
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {webcrypto, createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {checkDownload, bindChecker} = require('../../docs/assets/download-check.js');
const root = path.resolve(__dirname, '../..');
const card = JSON.parse(fs.readFileSync(path.join(root, 'run_card.json')));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const fixtures = ['submission_file', 'zip_file'].map(field => fs.readFileSync(path.join(root, card[field])));
const manifest = fixtures.map((bytes, i) => ({kind: i ? 'ZIP' : 'TIFF', bytes: bytes.length, sha256: sha(bytes)}));
const asFile = bytes => ({size: bytes.length, arrayBuffer: async () => Uint8Array.from(bytes).buffer});

for (let i = 0; i < 2; i++) test('published ' + manifest[i].kind + ' matches but never approves submission', async () => {
  const result = await checkDownload(asFile(fixtures[i]), manifest, webcrypto);
  assert.equal(result.state, 'match');
  assert.equal(result.sha256, manifest[i].sha256);
  assert.equal(result.submission_approved, false);
  assert.match(result.message, /Identity is not an R1–R8 format PASS or portal acceptance/);
});

test('same-size changed content does not match', async () => {
  const bytes = Buffer.from(fixtures[0]); bytes[500] ^= 1;
  const result = await checkDownload(asFile(bytes), manifest, webcrypto);
  assert.equal(result.state, 'unknown'); assert.equal(result.matched, false);
});
test('unknown sizes including enormous files are rejected before reading', async () => {
  for (const size of [0, -1, 1, NaN, Infinity, '137299', true, 2 ** 40]) {
    const file = {size, arrayBuffer: () => {throw new Error('must not read');}};
    const result = await checkDownload(file, manifest, webcrypto);
    assert.equal(result.state, 'unknown'); assert.equal(result.submission_approved, false);
  }
});
test('invalid or missing manifest fails closed', async () => {
  for (const value of [null, {}, [], [manifest[0]], [manifest[0], manifest[0]],
    [{...manifest[0], bytes: true}, manifest[1]],
    [{...manifest[0], sha256: 'z'.repeat(64)}, manifest[1]],
    [{...manifest[0], bytes: 2 ** 40}, manifest[1]]]) {
    assert.equal((await checkDownload(asFile(fixtures[0]), value, webcrypto)).state, 'unverified');
  }
});
test('no file resets the check without approval', async () => {
  const result = await checkDownload(null, manifest, webcrypto);
  assert.equal(result.state, 'idle'); assert.equal(result.submission_approved, false);
});
test('missing WebCrypto fails closed', async () => {
  for (const crypto of [null, {}, {subtle: {}}, {subtle: {digest: 'not a function'}}]) {
    assert.equal((await checkDownload(asFile(fixtures[0]), manifest, crypto)).state, 'unverified');
  }
});
test('read failures and truncated buffers fail closed', async () => {
  for (const arrayBuffer of [async () => {throw new Error('private filename');},
    async () => new ArrayBuffer(1), async () => 'not a buffer']) {
    const result = await checkDownload({size: fixtures[0].length, arrayBuffer}, manifest, webcrypto);
    assert.equal(result.state, 'unverified'); assert(!result.message.includes('private filename'));
  }
});
test('hashing failure fails closed', async () => {
  const crypto = {subtle: {digest: async () => {throw new Error('hash failure');}}};
  assert.equal((await checkDownload(asFile(fixtures[0]), manifest, crypto)).state, 'unverified');
});

function panelFixture(rawManifest = JSON.stringify(manifest)) {
  const handlers = {};
  const input = {files: [], addEventListener: (event, handler) => {handlers[event] = handler;}};
  const output = {dataset: {}, textContent: ''};
  const attrs = {};
  const panel = {dataset: {downloadManifest: rawManifest},
    querySelector: selector => selector === 'input[type=file]' ? input : output,
    setAttribute: (name, value) => {attrs[name] = value;}};
  return {panel, input, output, attrs, handlers};
}
test('late completion cannot replace a newer selection or reset', async () => {
  const f = panelFixture();
  let resolveFirst;
  bindChecker(f.panel, file => file === 'first' ? new Promise(resolve => {resolveFirst = resolve;}) :
    Promise.resolve({state: 'idle', message: 'reset'}));
  f.input.files = ['first']; const first = f.handlers.change();
  assert.equal(f.attrs['aria-busy'], 'true');
  f.input.files = []; await f.handlers.change();
  resolveFirst({state: 'match', message: 'stale match'}); await first;
  assert.equal(f.output.dataset.state, 'idle'); assert.equal(f.output.textContent, 'reset');
  assert.equal(f.attrs['aria-busy'], 'false');
});
test('bad manifest JSON is a visible refusal, not an unhandled error', async () => {
  const f = panelFixture('{'); bindChecker(f.panel); await f.handlers.change();
  assert.equal(f.output.dataset.state, 'unverified'); assert.equal(f.attrs['aria-busy'], 'false');
});
test('unexpected checker errors clear busy state and refuse', async () => {
  const f = panelFixture(); bindChecker(f.panel, async () => {throw new Error('unexpected');});
  await f.handlers.change(); assert.equal(f.output.dataset.state, 'unverified');
  assert.equal(f.attrs['aria-busy'], 'false');
});
