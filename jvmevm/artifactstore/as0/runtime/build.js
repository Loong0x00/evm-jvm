#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const solc = require('solc');

const expectedVersion = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== expectedVersion) throw new Error(`wrong solc: ${solc.version()}`);
const check = process.argv.length === 3 && process.argv[2] === '--check';
if (process.argv.length !== (check ? 3 : 2)) throw new Error('usage: node build.js [--check]');

const dir = __dirname;
const sourceName = 'AS0ArtifactStore.sol';
const contractName = 'AS0ArtifactStore';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const settings = {
  optimizer: {enabled: true, runs: 200},
  viaIR: true,
  evmVersion: 'cancun',
  metadata: {appendCBOR: false, bytecodeHash: 'none'},
  outputSelection: {'*': {'*': [
    'abi',
    'storageLayout',
    'evm.bytecode.object',
    'evm.bytecode.linkReferences',
    'evm.deployedBytecode.object',
    'evm.deployedBytecode.linkReferences',
    'evm.deployedBytecode.immutableReferences'
  ]}}
};
const output = JSON.parse(solc.compile(JSON.stringify({
  language: 'Solidity',
  sources: {[sourceName]: {content: source}},
  settings
})));
for (const diagnostic of output.errors || []) console.error(diagnostic.formattedMessage);
if ((output.errors || []).some(diagnostic => diagnostic.severity === 'error')) process.exit(1);
const sourceContracts = output.contracts[sourceName];
if (Object.keys(sourceContracts).join(',') !== contractName) {
  throw new Error(`unexpected contract set: ${Object.keys(sourceContracts).join(',')}`);
}
const built = sourceContracts[contractName];
const bytecode = built.evm.bytecode.object.toLowerCase();
const deployedBytecode = built.evm.deployedBytecode.object.toLowerCase();
if (bytecode.length / 2 > 49152) throw new Error('AS0 init code exceeds 49152 bytes');
if (deployedBytecode.length / 2 > 24576) throw new Error('AS0 runtime exceeds 24576 bytes');
if (Object.keys(built.evm.deployedBytecode.immutableReferences || {}).length !== 0) {
  throw new Error('AS0 deployed runtime must have no Solidity immutables');
}
if (Object.keys(built.evm.bytecode.linkReferences || {}).length !== 0 ||
    Object.keys(built.evm.deployedBytecode.linkReferences || {}).length !== 0) {
  throw new Error('AS0 bytecode must have no link references');
}

const key = entry => {
  const ins = (entry.inputs || []).map(input => input.type).join(',');
  if (entry.type === 'constructor') return `constructor(${ins})`;
  return `${entry.type}:${entry.name}(${ins})`;
};
const expectedABI = [
  'constructor(uint32)',
  'error:AS0Error(uint256)',
  'event:PageIssued(uint32,address,uint32,bytes32,bytes32,bytes32)',
  'event:Sealed(uint32,uint32,bytes32)',
  'function:MAX_LENGTH()',
  'function:MAX_PAGES()',
  'function:PAGE_SIZE()',
  'function:append(uint32,bytes,bytes32)',
  'function:chainCommitment()',
  'function:contentCommitment()',
  'function:cursor()',
  'function:declaredLength()',
  'function:isSealed()',
  'function:owner()',
  'function:page(uint256)',
  'function:pageCount()',
  'function:read(uint32,uint32)',
  'function:seal(uint32,bytes32)'
].sort();
const actualABI = built.abi.map(key).sort();
if (JSON.stringify(actualABI) !== JSON.stringify(expectedABI)) {
  throw new Error(`ABI surface differs:\ngot  ${actualABI.join('\n     ')}\nwant ${expectedABI.join('\n     ')}`);
}
const functionShapes = {
  MAX_LENGTH:        {mutability: 'view', inputs: [], outputs: ['uint32']},
  MAX_PAGES:         {mutability: 'view', inputs: [], outputs: ['uint32']},
  PAGE_SIZE:         {mutability: 'view', inputs: [], outputs: ['uint32']},
  append:            {mutability: 'nonpayable', inputs: ['uint32', 'bytes', 'bytes32'], outputs: []},
  chainCommitment:   {mutability: 'view', inputs: [], outputs: ['bytes32']},
  contentCommitment: {mutability: 'view', inputs: [], outputs: ['bytes32']},
  cursor:            {mutability: 'view', inputs: [], outputs: ['uint32']},
  declaredLength:    {mutability: 'view', inputs: [], outputs: ['uint32']},
  isSealed:          {mutability: 'view', inputs: [], outputs: ['bool']},
  owner:             {mutability: 'view', inputs: [], outputs: ['address']},
  page:              {mutability: 'view', inputs: ['uint256'], outputs: ['address', 'bytes32', 'bytes32']},
  pageCount:         {mutability: 'view', inputs: [], outputs: ['uint256']},
  read:              {mutability: 'view', inputs: ['uint32', 'uint32'], outputs: ['bytes']},
  seal:              {mutability: 'nonpayable', inputs: ['uint32', 'bytes32'], outputs: []}
};
for (const entry of built.abi.filter(entry => entry.type === 'function')) {
  const shape = functionShapes[entry.name];
  const inputs = entry.inputs.map(input => input.type);
  const outputs = entry.outputs.map(output => output.type);
  if (!shape || entry.stateMutability !== shape.mutability ||
      JSON.stringify(inputs) !== JSON.stringify(shape.inputs) ||
      JSON.stringify(outputs) !== JSON.stringify(shape.outputs)) {
    throw new Error(`function ABI shape differs: ${entry.name}`);
  }
}
const constructor = built.abi.find(entry => entry.type === 'constructor');
if (constructor.stateMutability !== 'nonpayable' || constructor.inputs.length !== 1 ||
    constructor.inputs[0].name !== 'length' || constructor.inputs[0].type !== 'uint32') {
  throw new Error('constructor ABI shape differs');
}
const error = built.abi.find(entry => entry.type === 'error' && entry.name === 'AS0Error');
if (error.inputs.length !== 1 || error.inputs[0].name !== 'code' || error.inputs[0].type !== 'uint256') {
  throw new Error('AS0Error ABI shape differs');
}
const issued = built.abi.find(entry => entry.type === 'event' && entry.name === 'PageIssued');
if (JSON.stringify(issued.inputs.map(input => input.name)) !== JSON.stringify(
      ['index', 'page', 'length', 'codeHash', 'pageCommitment', 'chainCommitment']) ||
    JSON.stringify(issued.inputs.map(input => input.indexed)) !== JSON.stringify(
      [true, true, false, false, false, false])) {
  throw new Error('PageIssued fields differ');
}
const sealed = built.abi.find(entry => entry.type === 'event' && entry.name === 'Sealed');
if (JSON.stringify(sealed.inputs.map(input => input.name)) !== JSON.stringify(
      ['length', 'pages', 'contentCommitment']) || sealed.inputs.some(input => input.indexed)) {
  throw new Error('Sealed fields differ');
}

const compiler = {
  version: expectedVersion,
  optimizer: {enabled: true, runs: 200},
  viaIR: true,
  evmVersion: 'cancun',
  metadata: {appendCBOR: false, bytecodeHash: 'none'}
};
const artifact = {
  contractName,
  abi: built.abi,
  bytecode,
  deployedBytecode,
  immutableReferences: built.evm.deployedBytecode.immutableReferences || {},
  compiler,
  sourceHashes: {[sourceName]: sha256(source)},
  codeHashes: {
    bytecodeSHA256: sha256(Buffer.from(bytecode, 'hex')),
    deployedBytecodeSHA256: sha256(Buffer.from(deployedBytecode, 'hex'))
  },
  storageLayout: built.storageLayout
};
const files = new Map([
  ['AS0ArtifactStore.init.hex', bytecode + '\n'],
  ['AS0ArtifactStore.runtime.hex', deployedBytecode + '\n'],
  ['AS0ArtifactStore.abi.json', JSON.stringify(built.abi, null, 2) + '\n'],
  [path.join('artifacts', 'AS0ArtifactStore.json'), JSON.stringify(artifact, null, 2) + '\n']
]);
let failed = false;
for (const [relative, contents] of files) {
  const target = path.join(dir, relative);
  if (check) {
    let existing = '';
    try { existing = fs.readFileSync(target, 'utf8'); } catch (_) {}
    if (existing !== contents) {
      console.error(`${relative} differs; run npm run build`);
      failed = true;
    }
  } else {
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, contents);
  }
}
if (check) {
  const expectedArtifacts = ['AS0ArtifactStore.json'];
  let actualArtifacts = [];
  try { actualArtifacts = fs.readdirSync(path.join(dir, 'artifacts')).filter(name => name.endsWith('.json')).sort(); } catch (_) {}
  if (JSON.stringify(actualArtifacts) !== JSON.stringify(expectedArtifacts)) {
    console.error(`artifact set differs: got ${actualArtifacts.join(',')}, want ${expectedArtifacts.join(',')}`);
    failed = true;
  }
}
const summary = {
  compiler: expectedVersion,
  settings: {optimizer: 200, viaIR: true, evmVersion: 'cancun', metadata: false},
  sourceBytes: Buffer.byteLength(source),
  sourceSHA256: sha256(source),
  initBytes: bytecode.length / 2,
  initSHA256: artifact.codeHashes.bytecodeSHA256,
  runtimeBytes: deployedBytecode.length / 2,
  runtimeSHA256: artifact.codeHashes.deployedBytecodeSHA256,
  immutableReferences: 0,
  abiEntries: built.abi.length
};
console.log(JSON.stringify(summary));
if (failed) process.exit(1);
