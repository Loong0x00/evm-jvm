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
const sourceName = 'DI0Resource.sol';
const contractName = 'DI0Resource';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const {keccak256} = require('js-sha3');
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
  language: 'Solidity', sources: {[sourceName]: {content: source}}, settings
})));
for (const diagnostic of output.errors || []) console.error(diagnostic.formattedMessage);
if ((output.errors || []).some(diagnostic => diagnostic.severity === 'error')) process.exit(1);
const sourceContracts = output.contracts[sourceName];
const contractSet = Object.keys(sourceContracts).sort();
if (JSON.stringify(contractSet) !== JSON.stringify(['IDI0AS0', 'IDI0ZI0', contractName].sort())) {
  throw new Error(`unexpected contract set: ${contractSet.join(',')}`);
}
const built = sourceContracts[contractName];
const bytecode = built.evm.bytecode.object.toLowerCase();
const deployedBytecode = built.evm.deployedBytecode.object.toLowerCase();
// address + bytes32 + dynamic offset + dynamic length + the maximum 256-byte rawName.
const maximumConstructorArguments = 384;
if (bytecode.length / 2 + maximumConstructorArguments > 49152) {
  throw new Error('DI0 complete init code with maximum constructor args exceeds 49152 bytes');
}
if (deployedBytecode.length / 2 > 24576) throw new Error('DI0 runtime exceeds 24576 bytes');
if (Object.keys(built.evm.deployedBytecode.immutableReferences || {}).length !== 0) {
  throw new Error('DI0 deployed runtime must have no Solidity immutables');
}
if (Object.keys(built.evm.bytecode.linkReferences || {}).length !== 0 ||
    Object.keys(built.evm.deployedBytecode.linkReferences || {}).length !== 0) {
  throw new Error('DI0 bytecode must have no link references');
}

const key = entry => {
  const inputs = (entry.inputs || []).map(input => input.type).join(',');
  if (entry.type === 'constructor') return `constructor(${inputs})`;
  return `${entry.type}:${entry.name}(${inputs})`;
};
const expectedABI = [
  'constructor(address,bytes32,bytes)',
  'error:DI0Error(uint256)',
  'function:step(uint32,uint16)',
  'function:publish(uint8,bytes32,uint8)',
  'function:read(uint32,uint32)',
  'function:page(uint8)',
  'function:owner()', 'function:index()', 'function:store()',
  'function:indexRoot()', 'function:content()', 'function:packedRecord()', 'function:nameHash()',
  'function:binding()', 'function:outputRolling()', 'function:publicationRolling()', 'function:finalRoot()',
  'function:entryIndex()', 'function:dataStart()', 'function:compressedSize()', 'function:plainSize()',
  'function:expectedCRC()', 'function:outputCount()', 'function:inputByte()', 'function:work()',
  'function:crc()', 'function:pendingLength()', 'function:pendingDistance()',
  'function:inputBit()', 'function:method()', 'function:phase()', 'function:blockMode()',
  'function:blockFinal()', 'function:fixedBlock()', 'function:publishedPages()'
].sort();
const actualABI = built.abi.map(key).sort();
if (JSON.stringify(actualABI) !== JSON.stringify(expectedABI)) {
  throw new Error(`ABI surface differs:\ngot  ${actualABI.join('\n     ')}\nwant ${expectedABI.join('\n     ')}`);
}
const functionShapes = {
  step: {mutability: 'nonpayable', inputs: ['uint32','uint16'], inputNames: ['expectedWork','units'], outputs: [], outputNames: []},
  publish: {mutability: 'nonpayable', inputs: ['uint8','bytes32','uint8'], inputNames: ['expectedPage','expectedRolling','units'], outputs: [], outputNames: []},
  read: {mutability: 'view', inputs: ['uint32','uint32'], inputNames: ['offset','length'], outputs: ['bytes'], outputNames: ['out']},
  page: {mutability: 'view', inputs: ['uint8'], inputNames: ['at'], outputs: ['address','bytes32','bytes32','uint32'], outputNames: ['pageAddress','codeHash','pageCommitment','length']}
};
const scalarTypes = {
  owner:'address', index:'address', store:'address',
  indexRoot:'bytes32', content:'bytes32', packedRecord:'bytes32', nameHash:'bytes32', binding:'bytes32',
  outputRolling:'bytes32', publicationRolling:'bytes32', finalRoot:'bytes32',
  entryIndex:'uint32', dataStart:'uint32', compressedSize:'uint32', plainSize:'uint32', expectedCRC:'uint32',
  outputCount:'uint32', inputByte:'uint32', work:'uint32', crc:'uint32',
  pendingLength:'uint16', pendingDistance:'uint16', inputBit:'uint8', method:'uint8', phase:'uint8', blockMode:'uint8',
  blockFinal:'bool', fixedBlock:'bool', publishedPages:'uint8'
};
for (const [name, type] of Object.entries(scalarTypes)) {
  functionShapes[name] = {mutability:'view', inputs:[], inputNames:[], outputs:[type], outputNames:['']};
}
for (const entry of built.abi.filter(entry => entry.type === 'function')) {
  const shape = functionShapes[entry.name];
  const actual = {
    mutability: entry.stateMutability,
    inputs: entry.inputs.map(input => input.type), inputNames: entry.inputs.map(input => input.name),
    outputs: entry.outputs.map(output => output.type), outputNames: entry.outputs.map(output => output.name)
  };
  if (!shape || JSON.stringify(actual) !== JSON.stringify(shape)) {
    throw new Error(`function ABI shape differs: ${entry.name}: ${JSON.stringify(actual)}`);
  }
}
const constructor = built.abi.find(entry => entry.type === 'constructor');
if (constructor.stateMutability !== 'nonpayable' ||
    JSON.stringify(constructor.inputs.map(input => input.type)) !== JSON.stringify(['address','bytes32','bytes']) ||
    JSON.stringify(constructor.inputs.map(input => input.name)) !== JSON.stringify(['finalIndex','assertedIndexRoot','rawName'])) {
  throw new Error('constructor ABI shape differs');
}
const error = built.abi.find(entry => entry.type === 'error' && entry.name === 'DI0Error');
if (error.inputs.length !== 1 || error.inputs[0].name !== 'code' || error.inputs[0].type !== 'uint256') {
  throw new Error('DI0Error ABI shape differs');
}
if (built.abi.some(entry => entry.type === 'event' || entry.type === 'fallback' || entry.type === 'receive')) {
  throw new Error('DI0 must have no events, fallback, or receive');
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
    AS0RuntimeCodeKeccak256: 'c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896',
    ZI0RuntimeCodeKeccak256: '0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77'
  },
  limits: {
    archiveBytes: 33554432,
    as0PageBytes: 8192,
    as0ReadBytes: 4096,
    rawNameBytes: 256,
    outputBytes: 262144,
    historyBytes: 32768,
    copyBytes: 32,
    outputPageBytes: 8192,
    outputPages: 32,
    readBytes: 4096,
    stepUnits: 128,
    publishUnits: 1,
    stepReserveGas: 25000000,
    runtimeBytes: 24576,
    completeInitBytes: 49152
  },
  storageLayout: built.storageLayout
};
const files = new Map([
  ['DI0Resource.init.hex', bytecode + '\n'],
  ['DI0Resource.runtime.hex', deployedBytecode + '\n'],
  ['DI0Resource.abi.json', JSON.stringify(built.abi, null, 2) + '\n'],
  [path.join('combinedartifacts', 'DI0Resource.json'), JSON.stringify(artifact, null, 2) + '\n']
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
  const expectedArtifacts = ['DI0Resource.json'];
  let actualArtifacts = [];
  try { actualArtifacts = fs.readdirSync(path.join(dir, 'combinedartifacts')).filter(name => name.endsWith('.json')).sort(); } catch (_) {}
  if (JSON.stringify(actualArtifacts) !== JSON.stringify(expectedArtifacts)) {
    console.error(`artifact set differs: got ${actualArtifacts.join(',')}, want ${expectedArtifacts.join(',')}`);
    failed = true;
  }
}
const summary = {
  compiler: expectedVersion,
  settings: {optimizer: 200, viaIR: true, evmVersion: 'cancun', metadata: false},
  sourceBytes: Buffer.byteLength(source), sourceSHA256: sha256(source),
  initBytes: bytecode.length / 2,
  maximumConstructorArgumentBytes: maximumConstructorArguments,
  maximumCompleteInitBytes: bytecode.length / 2 + maximumConstructorArguments,
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
