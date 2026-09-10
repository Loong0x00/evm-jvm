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
const sourceName = 'ZI0ZipIndex.sol';
const contractName = 'ZI0ZipIndex';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const keccak256 = value => {
  // solc ships the same pinned js-sha3 dependency used by this build tree.
  const {keccak256} = require('js-sha3');
  return keccak256(value);
};
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
const contractSet = Object.keys(sourceContracts).sort();
if (JSON.stringify(contractSet) !== JSON.stringify(['IAS0ZI0', contractName].sort())) {
  throw new Error(`unexpected contract set: ${contractSet.join(',')}`);
}
const built = sourceContracts[contractName];
const bytecode = built.evm.bytecode.object.toLowerCase();
const deployedBytecode = built.evm.deployedBytecode.object.toLowerCase();
if (bytecode.length / 2 + 64 > 49152) throw new Error('ZI0 complete init code with constructor args exceeds 49152 bytes');
if (deployedBytecode.length / 2 > 24576) throw new Error('ZI0 runtime exceeds 24576 bytes');
if (Object.keys(built.evm.deployedBytecode.immutableReferences || {}).length !== 0) {
  throw new Error('ZI0 deployed runtime must have no Solidity immutables');
}
if (Object.keys(built.evm.bytecode.linkReferences || {}).length !== 0 ||
    Object.keys(built.evm.deployedBytecode.linkReferences || {}).length !== 0) {
  throw new Error('ZI0 bytecode must have no link references');
}

const key = entry => {
  const inputs = (entry.inputs || []).map(input => input.type).join(',');
  if (entry.type === 'constructor') return `constructor(${inputs})`;
  return `${entry.type}:${entry.name}(${inputs})`;
};
const expectedABI = [
  'constructor(address,bytes32)',
  'error:ZI0Error(uint256)',
  'function:discover()',
  'function:scan(uint32,uint32,bytes32,uint16)',
  'function:finish(uint32,uint32,bytes32)',
  'function:entry(uint32)',
  'function:lookup(bytes)',
  'function:owner()',
  'function:store()',
  'function:content()',
  'function:length()',
  'function:phase()',
  'function:eocd()',
  'function:cdOffset()',
  'function:cdSize()',
  'function:count()',
  'function:nextEntry()',
  'function:cdCursor()',
  'function:rolling()',
  'function:finalRoot()'
].sort();
const actualABI = built.abi.map(key).sort();
if (JSON.stringify(actualABI) !== JSON.stringify(expectedABI)) {
  throw new Error(`ABI surface differs:\ngot  ${actualABI.join('\n     ')}\nwant ${expectedABI.join('\n     ')}`);
}
const functionShapes = {
  discover:   {mutability: 'nonpayable', inputs: [], inputNames: [], outputs: [], outputNames: []},
  scan:       {mutability: 'nonpayable', inputs: ['uint32', 'uint32', 'bytes32', 'uint16'], inputNames: ['expectedEntry', 'expectedCursor', 'expectedRolling', 'units'], outputs: [], outputNames: []},
  finish:     {mutability: 'nonpayable', inputs: ['uint32', 'uint32', 'bytes32'], inputNames: ['expectedCount', 'expectedCursor', 'expectedRolling'], outputs: [], outputNames: []},
  entry:      {mutability: 'view', inputs: ['uint32'], inputNames: ['index'], outputs: ['bytes', 'bytes32'], outputNames: ['rawName', 'packedRecord']},
  lookup:     {mutability: 'view', inputs: ['bytes'], inputNames: ['rawName'], outputs: ['bool', 'uint32', 'bytes32'], outputNames: ['found', 'index', 'packedRecord']},
  owner:      {mutability: 'view', inputs: [], inputNames: [], outputs: ['address'], outputNames: ['']},
  store:      {mutability: 'view', inputs: [], inputNames: [], outputs: ['address'], outputNames: ['']},
  content:    {mutability: 'view', inputs: [], inputNames: [], outputs: ['bytes32'], outputNames: ['']},
  length:     {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  phase:      {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint8'], outputNames: ['']},
  eocd:       {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  cdOffset:   {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  cdSize:     {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  count:      {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  nextEntry:  {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  cdCursor:   {mutability: 'view', inputs: [], inputNames: [], outputs: ['uint32'], outputNames: ['']},
  rolling:    {mutability: 'view', inputs: [], inputNames: [], outputs: ['bytes32'], outputNames: ['']},
  finalRoot:  {mutability: 'view', inputs: [], inputNames: [], outputs: ['bytes32'], outputNames: ['']}
};
for (const entry of built.abi.filter(entry => entry.type === 'function')) {
  const shape = functionShapes[entry.name];
  const inputs = entry.inputs.map(input => input.type);
  const inputNames = entry.inputs.map(input => input.name);
  const outputs = entry.outputs.map(output => output.type);
  const outputNames = entry.outputs.map(output => output.name);
  if (!shape || entry.stateMutability !== shape.mutability ||
      JSON.stringify(inputs) !== JSON.stringify(shape.inputs) ||
      JSON.stringify(inputNames) !== JSON.stringify(shape.inputNames) ||
      JSON.stringify(outputs) !== JSON.stringify(shape.outputs) ||
      JSON.stringify(outputNames) !== JSON.stringify(shape.outputNames)) {
    throw new Error(`function ABI shape differs: ${entry.name}`);
  }
}
const constructor = built.abi.find(entry => entry.type === 'constructor');
if (constructor.stateMutability !== 'nonpayable' ||
    JSON.stringify(constructor.inputs.map(input => input.type)) !== JSON.stringify(['address', 'bytes32']) ||
    JSON.stringify(constructor.inputs.map(input => input.name)) !== JSON.stringify(['sealedAS0', 'assertedContent'])) {
  throw new Error('constructor ABI shape differs');
}
const error = built.abi.find(entry => entry.type === 'error' && entry.name === 'ZI0Error');
if (error.inputs.length !== 1 || error.inputs[0].name !== 'code' || error.inputs[0].type !== 'uint256') {
  throw new Error('ZI0Error ABI shape differs');
}
if (built.abi.some(entry => entry.type === 'event' || entry.type === 'fallback' || entry.type === 'receive')) {
  throw new Error('ZI0 must have no events, fallback, or receive');
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
    deployedBytecodeSHA256: sha256(Buffer.from(deployedBytecode, 'hex')),
    deployedBytecodeKeccak256: keccak256(Buffer.from(deployedBytecode, 'hex'))
  },
  dependencyPins: {
    AS0RuntimeCodeKeccak256: 'c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896'
  },
  limits: {
    archiveBytes: 33554432,
    as0PageBytes: 8192,
    as0ReadBytes: 4096,
    entries: 32768,
    centralDirectoryBytes: 4194304,
    rawNameBytes: 256,
    extraBytes: 1024,
    commentBytes: 1024,
    scanUnits: 64,
    eocdTailBytes: 65557,
    runtimeBytes: 24576,
    completeInitBytes: 49152
  },
  storageLayout: built.storageLayout
};
const files = new Map([
  ['ZI0ZipIndex.init.hex', bytecode + '\n'],
  ['ZI0ZipIndex.runtime.hex', deployedBytecode + '\n'],
  ['ZI0ZipIndex.abi.json', JSON.stringify(built.abi, null, 2) + '\n'],
  [path.join('combinedartifacts', 'ZI0ZipIndex.json'), JSON.stringify(artifact, null, 2) + '\n']
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
  const expectedArtifacts = ['ZI0ZipIndex.json'];
  let actualArtifacts = [];
  try {
    actualArtifacts = fs.readdirSync(path.join(dir, 'combinedartifacts')).filter(name => name.endsWith('.json')).sort();
  } catch (_) {}
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
  completeInitBytes: bytecode.length / 2 + 64,
  initSHA256: artifact.codeHashes.bytecodeSHA256,
  runtimeBytes: deployedBytecode.length / 2,
  runtimeSHA256: artifact.codeHashes.deployedBytecodeSHA256,
  runtimeKeccak256: artifact.codeHashes.deployedBytecodeKeccak256,
  immutableReferences: 0,
  abiEntries: built.abi.length,
  functions: built.abi.filter(entry => entry.type === 'function').length
};
console.log(JSON.stringify(summary));
if (failed) process.exit(1);
