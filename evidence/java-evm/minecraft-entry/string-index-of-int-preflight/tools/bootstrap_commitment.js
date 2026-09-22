'use strict';
// Independently fold the ordered bootstrap commitment with the pinned local
// Ethereum Keccak implementation. This reads no Java input or execution state.
const fs = require('fs');
const assert = require('assert');
const { keccak256 } = require('js-sha3');

const [enginePath, parentPath, rootPath, stringPath] = process.argv.slice(2);
assert(enginePath && parentPath && rootPath && stringPath);
const engine = fs.readFileSync(enginePath, 'utf8');
const parent = JSON.parse(fs.readFileSync(parentPath, 'utf8'));
const root = JSON.parse(fs.readFileSync(rootPath, 'utf8'));
const image = Buffer.from(fs.readFileSync(stringPath, 'utf8').trim(), 'hex');
assert(image.length > 0);
const section = engine.slice(engine.indexOf('function _bootstrapString()'));
const match = section.match(/return hex"([0-9a-f]+)";/);
assert(match && Buffer.from(match[1], 'hex').equals(image));
assert.equal(parent.bootstrapCount, 95);
assert.equal(parent.keccak256.length, 95);
assert.equal(root.bootstrapCount, 95);
assert.equal(root.keccak256.length, 95);
assert.equal(root.dboot, parent.dboot);
assert.deepEqual(root.order, parent.order);
const leaf = keccak256(image);
for (let index = 0; index < 95; index++) {
  if (index === 26) assert.equal(root.keccak256[index], leaf);
  else assert.equal(root.keccak256[index], parent.keccak256[index]);
}
const packed = Buffer.concat([
  Buffer.from(root.dboot, 'hex'),
  ...root.keccak256.map(value => Buffer.from(value, 'hex')),
]);
const bootstrapRoot = keccak256(packed);
assert.equal(root.bootstrapRoot, bootstrapRoot);
console.log(JSON.stringify({
  bootstrapCount: 95,
  changedSlot: 26,
  parentStringKeccak256: parent.keccak256[26],
  stringKeccak256: leaf,
  bootstrapRoot,
  unchangedLeaves: 94,
  scope: 'ordered bootstrap image/root verification only; no class or resource execution authority',
}, null, 2));
