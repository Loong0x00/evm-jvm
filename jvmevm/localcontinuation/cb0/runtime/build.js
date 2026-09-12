#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const solc = require('solc');
const {keccak256} = require('js-sha3');

const expectedVersion = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== expectedVersion) throw new Error(`wrong solc: ${solc.version()}`);
const check = process.argv.length === 3 && process.argv[2] === '--check';
if (process.argv.length !== (check ? 3 : 2)) throw new Error('usage: node build.js [--check]');

const dir = __dirname;
const sourceName = 'CB0ClassCoordinator.sol';
const contractName = 'CB0ClassCoordinator';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const settings = {
  optimizer: {enabled: true, runs: 200}, viaIR: true, evmVersion: 'cancun',
  metadata: {appendCBOR: false, bytecodeHash: 'none'},
  outputSelection: {'*': {'*': [
    'abi', 'storageLayout', 'evm.bytecode.object', 'evm.bytecode.linkReferences',
    'evm.deployedBytecode.object', 'evm.deployedBytecode.linkReferences',
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
if (JSON.stringify(contractSet) !== JSON.stringify([contractName])) {
  throw new Error(`unexpected contract set: ${contractSet.join(',')}`);
}
const built = sourceContracts[contractName];
const bytecode = built.evm.bytecode.object.toLowerCase();
const deployedBytecode = built.evm.deployedBytecode.object.toLowerCase();
const maximumConstructorArguments = 2016;
if (bytecode.length / 2 + maximumConstructorArguments > 49152) {
  throw new Error('CB0 complete init code with maximum constructor args exceeds 49152 bytes');
}
if (deployedBytecode.length / 2 > 24576) throw new Error('CB0 runtime exceeds 24576 bytes');
if (Object.keys(built.evm.deployedBytecode.immutableReferences || {}).length !== 0) {
  throw new Error('CB0 deployed runtime must have no Solidity immutables');
}
if (Object.keys(built.evm.bytecode.linkReferences || {}).length !== 0 ||
    Object.keys(built.evm.deployedBytecode.linkReferences || {}).length !== 0) {
  throw new Error('CB0 bytecode must have no link references');
}

const key = entry => {
  const inputs = (entry.inputs || []).map(input => input.type).join(',');
  if (entry.type === 'constructor') return `constructor(${inputs})`;
  return `${entry.type}:${entry.name}(${inputs})`;
};
const expectedABI = [
  'constructor(address,bytes32,address[],bytes[],bytes32[],bytes32[],bytes32)',
  'error:CB0Error(uint256)',
  'function:owner()', 'function:finalIndex()', 'function:finalIndexRoot()',
  'function:packageRoot()', 'function:instanceId()', 'function:totalClassBytes()',
  'function:classCount()', 'function:classBinding(uint8)',
  'function:start(bytes32,uint8,string,int32[],uint64,uint32)',
  'function:resume(bytes32,uint64,bytes32,bytes,uint64,uint32)'
].sort();
const actualABI = built.abi.map(key).sort();
if (JSON.stringify(actualABI) !== JSON.stringify(expectedABI)) {
  throw new Error(`ABI surface differs:\ngot  ${actualABI.join('\n     ')}\nwant ${expectedABI.join('\n     ')}`);
}
const shapes = {
  owner: {mutability:'view', inputs:[], inputNames:[], outputs:['address'], outputNames:['']},
  finalIndex: {mutability:'view', inputs:[], inputNames:[], outputs:['address'], outputNames:['']},
  finalIndexRoot: {mutability:'view', inputs:[], inputNames:[], outputs:['bytes32'], outputNames:['']},
  packageRoot: {mutability:'view', inputs:[], inputNames:[], outputs:['bytes32'], outputNames:['']},
  instanceId: {mutability:'view', inputs:[], inputNames:[], outputs:['bytes32'], outputNames:['']},
  totalClassBytes: {mutability:'view', inputs:[], inputNames:[], outputs:['uint32'], outputNames:['']},
  classCount: {mutability:'view', inputs:[], inputNames:[], outputs:['uint8'], outputNames:['']},
  classBinding: {mutability:'view', inputs:['uint8'], inputNames:['at'], outputs:['address','bytes','bytes32','uint32'], outputNames:['decoder','rawName','resourceRoot','classSize']},
  start: {mutability:'nonpayable', inputs:['bytes32','uint8','string','int32[]','uint64','uint32'], inputNames:['assertedPackageRoot','entryAt','entry','args','maxJvmSteps','maxInternalSteps'], outputs:['bytes'], outputNames:['engineReturn']},
  resume: {mutability:'nonpayable', inputs:['bytes32','uint64','bytes32','bytes','uint64','uint32'], inputNames:['assertedPackageRoot','expectedEpoch','expectedCheckpointRoot','checkpoint','maxJvmSteps','maxInternalSteps'], outputs:['bytes'], outputNames:['engineReturn']}
};
for (const entry of built.abi.filter(entry => entry.type === 'function')) {
  const actual = {mutability:entry.stateMutability, inputs:entry.inputs.map(i => i.type), inputNames:entry.inputs.map(i => i.name), outputs:entry.outputs.map(o => o.type), outputNames:entry.outputs.map(o => o.name)};
  if (!shapes[entry.name] || JSON.stringify(actual) !== JSON.stringify(shapes[entry.name])) {
    throw new Error(`function ABI shape differs: ${entry.name}: ${JSON.stringify(actual)}`);
  }
}
const constructor = built.abi.find(entry => entry.type === 'constructor');
if (constructor.stateMutability !== 'nonpayable' ||
    JSON.stringify(constructor.inputs.map(i => i.type)) !== JSON.stringify(['address','bytes32','address[]','bytes[]','bytes32[]','bytes32[]','bytes32']) ||
    JSON.stringify(constructor.inputs.map(i => i.name)) !== JSON.stringify(['fixedOwner','fixedInstanceSalt','fixedDecoders','fixedRawNames','assertedIndexRoots','assertedResourceRoots','assertedPackageRoot'])) {
  throw new Error('constructor ABI shape differs');
}
const error = built.abi.find(entry => entry.type === 'error' && entry.name === 'CB0Error');
if (!error || error.inputs.length !== 1 || error.inputs[0].name !== 'code' || error.inputs[0].type !== 'uint256') throw new Error('CB0Error ABI shape differs');
if (built.abi.some(entry => entry.type === 'event' || entry.type === 'fallback' || entry.type === 'receive')) throw new Error('CB0 must have no events, fallback, or receive');

const compiler = {version:expectedVersion, optimizer:{enabled:true,runs:200}, viaIR:true, evmVersion:'cancun', metadata:{appendCBOR:false,bytecodeHash:'none'}};
const artifact = {
  contractName, abi:built.abi, bytecode, deployedBytecode,
  immutableReferences: built.evm.deployedBytecode.immutableReferences || {}, compiler,
  sourceHashes: {[sourceName]: sha256(source)},
  codeHashes: {
    bytecodeSHA256: sha256(Buffer.from(bytecode, 'hex')),
    deployedBytecodeSHA256: sha256(Buffer.from(deployedBytecode, 'hex')),
    deployedBytecodeKeccak256: keccak256(Buffer.from(deployedBytecode, 'hex'))
  },
  dependencyPins: {
    AS0RuntimeCodeKeccak256:'c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896',
    ZI0RuntimeCodeKeccak256:'0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77',
    DI0RuntimeCodeKeccak256:'946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37',
    VFS0aRuntimeCodeKeccak256:'e7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84',
    VFS0aAddress:'4a564d45564d564653304152554e54494d450001'
  },
  limits: {
    archiveBytes:33554432, resources:4, classBytes:65536, rawNameBytes:256,
    resourceReadBytes:4096, checkpointBytes:1048576, jvmUnits:4096,
    internalUnits:4096, engineRuntimeBytes:327680, runtimeBytes:24576,
    completeInitBytes:49152, seedFiles:0
  }, storageLayout: built.storageLayout
};
const files = new Map([
  ['CB0ClassCoordinator.init.hex', bytecode + '\n'],
  ['CB0ClassCoordinator.runtime.hex', deployedBytecode + '\n'],
  ['CB0ClassCoordinator.abi.json', JSON.stringify(built.abi, null, 2) + '\n'],
  [path.join('combinedartifacts', 'CB0ClassCoordinator.json'), JSON.stringify(artifact, null, 2) + '\n']
]);
let failed = false;
for (const [relative, contents] of files) {
  const target = path.join(dir, relative);
  if (check) {
    let existing = ''; try { existing = fs.readFileSync(target, 'utf8'); } catch (_) {}
    if (existing !== contents) { console.error(`${relative} differs; run npm run build`); failed = true; }
  } else { fs.mkdirSync(path.dirname(target), {recursive:true}); fs.writeFileSync(target, contents); }
}
if (check) {
  let actual = []; try { actual = fs.readdirSync(path.join(dir, 'combinedartifacts')).filter(n => n.endsWith('.json')).sort(); } catch (_) {}
  if (JSON.stringify(actual) !== JSON.stringify(['CB0ClassCoordinator.json'])) { console.error(`artifact set differs: got ${actual.join(',')}`); failed = true; }
}
console.log(JSON.stringify({
  compiler:expectedVersion, settings:{optimizer:200,viaIR:true,evmVersion:'cancun',metadata:false},
  sourceBytes:Buffer.byteLength(source), sourceSHA256:sha256(source),
  initBytes:bytecode.length / 2, maximumConstructorArgumentBytes:maximumConstructorArguments,
  maximumCompleteInitBytes:bytecode.length / 2 + maximumConstructorArguments,
  initSHA256:artifact.codeHashes.bytecodeSHA256, runtimeBytes:deployedBytecode.length / 2,
  runtimeSHA256:artifact.codeHashes.deployedBytecodeSHA256,
  runtimeKeccak256:artifact.codeHashes.deployedBytecodeKeccak256,
  immutableReferences:Object.keys(artifact.immutableReferences).length,
  abiEntries:built.abi.length, functions:built.abi.filter(e => e.type === 'function').length
}));
if (failed) process.exit(1);
