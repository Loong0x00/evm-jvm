#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const solc = require('solc');

const dir = __dirname;
const check = process.argv.length === 3 && process.argv[2] === '--check';
if (process.argv.length !== (check ? 3 : 2)) {
  console.error('usage: node build.js [--check]');
  process.exit(2);
}
const expectedVersion = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== expectedVersion) {
  console.error(`wrong solc: got ${solc.version()}, want ${expectedVersion}`);
  process.exit(1);
}
// Closed Solidity-only build input. Guest classes and test catalogues cannot
// influence production bytecode.
const sourceNames = [
  'S2aTypes.sol', 'S2aMetadataPage.sol', 'S2aCodec.sol', 'S2aClassParser.sol',
  'S2aStepModule.sol', 'S2aCoordinator.sol'
];
const sources = {};
const sourceHashes = {};
for (const name of sourceNames) {
  const content = fs.readFileSync(path.join(dir, name), 'utf8');
  sources[name] = {content};
  sourceHashes[name] = crypto.createHash('sha256').update(content).digest('hex');
}
const settings = {
  optimizer: {enabled: true, runs: 200}, evmVersion: 'cancun', viaIR: true,
  metadata: {appendCBOR: false, bytecodeHash: 'none'},
  outputSelection: {'*': {'*': [
    'abi', 'evm.bytecode.object', 'evm.deployedBytecode.object',
    'evm.deployedBytecode.immutableReferences'
  ]}}
};
const output = JSON.parse(solc.compile(JSON.stringify({language:'Solidity', sources, settings})));
for (const d of output.errors || []) if (d.severity === 'error') console.error(d.formattedMessage);
if ((output.errors || []).some(d => d.severity === 'error')) process.exit(1);
const compiler = {
  version: expectedVersion, optimizer: {enabled:true,runs:200}, viaIR:true,
  evmVersion:'cancun', metadata:{appendCBOR:false,bytecodeHash:'none'}
};
const specs = [
  ['S2aMetadataPage.sol','S2aMetadataPage'], ['S2aClassParser.sol','S2aClassParser'],
  ['S2aStepModule.sol','S2aStepModule'], ['S2aCoordinator.sol','S2aCoordinator']
];
const artifactDir = path.join(dir, 'artifacts');
fs.mkdirSync(artifactDir, {recursive:true});
let failed = false;
if (check) {
  const want = specs.map(x => `${x[1]}.json`).sort();
  const got = fs.readdirSync(artifactDir).filter(x => x.endsWith('.json')).sort();
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    console.error(`artifact set differs: got ${got.join(',')}, want ${want.join(',')}`); failed=true;
  }
}
for (const [sourceName, contractName] of specs) {
  const built = output.contracts[sourceName][contractName];
  const artifact = {contractName, abi:built.abi,
    bytecode:built.evm.bytecode.object.toLowerCase(),
    deployedBytecode:built.evm.deployedBytecode.object.toLowerCase(),
    immutableReferences:built.evm.deployedBytecode.immutableReferences || {}, compiler, sourceHashes};
  const encoded = JSON.stringify(artifact,null,2)+'\n';
  const file = path.join(artifactDir, `${contractName}.json`);
  if (check) {
    let old=''; try { old=fs.readFileSync(file,'utf8'); } catch (_) {}
    if (old !== encoded) { console.error(`${contractName} artifact differs; run npm run build`); failed=true; }
  } else fs.writeFileSync(file, encoded);
  const initBytes=artifact.bytecode.length/2, runtimeBytes=artifact.deployedBytecode.length/2;
  const initHash=crypto.createHash('sha256').update(Buffer.from(artifact.bytecode,'hex')).digest('hex');
  const runtimeHash=crypto.createHash('sha256').update(Buffer.from(artifact.deployedBytecode,'hex')).digest('hex');
  const runtimeLimit=contractName === 'S2aClassParser' ? 16384 : 12288;
  if (initBytes > 24576 || runtimeBytes > runtimeLimit) {
    console.error(`${contractName} exceeds S2a size limit: init=${initBytes}, runtime=${runtimeBytes}, runtimeLimit=${runtimeLimit}`); failed=true;
  }
  console.log(`${check?'checked':'wrote'} ${contractName}: init=${initBytes} sha256=${initHash}, runtime=${runtimeBytes} sha256=${runtimeHash}`);
  if (contractName === 'S2aMetadataPage') {
    // Dynamic bytes are ABI-padded to a full word.
    const maxInit=initBytes+64+Math.ceil(8191/32)*32;
    if (maxInit>24576) { console.error(`S2aMetadataPage maximum init exceeds S2a limit: ${maxInit}`); failed=true; }
    console.log(`S2aMetadataPage dynamic maximum: init=${maxInit}, runtime=8192`);
  }
}
if (failed) process.exit(1);
console.log(`solc ${expectedVersion}; optimizer=200 viaIR=true evmVersion=cancun metadata=off`);
