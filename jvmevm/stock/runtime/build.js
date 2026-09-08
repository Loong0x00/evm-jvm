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

// The compiler input is deliberately closed over this Solidity-only list. In
// particular, fixture/class/result files can never affect production artifacts.
const sourceNames = [
  'ArtifactPage.sol',
  'StockTypes.sol',
  'TinyJvmStepModule.sol',
  'VMCoordinator.sol'
];
const sources = {};
const sourceHashes = {};
for (const name of sourceNames) {
  const content = fs.readFileSync(path.join(dir, name), 'utf8');
  sources[name] = { content };
  sourceHashes[name] = crypto.createHash('sha256').update(content).digest('hex');
}

const settings = {
  optimizer: { enabled: true, runs: 200 },
  evmVersion: 'cancun',
  viaIR: true,
  metadata: { appendCBOR: false, bytecodeHash: 'none' },
  outputSelection: {
    '*': {
      '*': [
        'abi',
        'evm.bytecode.object',
        'evm.deployedBytecode.object',
        'evm.deployedBytecode.immutableReferences'
      ]
    }
  }
};
const output = JSON.parse(solc.compile(JSON.stringify({ language: 'Solidity', sources, settings })));
for (const diagnostic of output.errors || []) {
  if (diagnostic.severity === 'error') console.error(diagnostic.formattedMessage);
}
if ((output.errors || []).some((x) => x.severity === 'error')) process.exit(1);

const compiler = {
  version: expectedVersion,
  optimizer: { enabled: true, runs: 200 },
  viaIR: true,
  evmVersion: 'cancun',
  metadata: { appendCBOR: false, bytecodeHash: 'none' }
};
const specs = [
  ['ArtifactPage.sol', 'ArtifactPage'],
  ['TinyJvmStepModule.sol', 'TinyJvmStepModule'],
  ['VMCoordinator.sol', 'VMCoordinator']
];
const artifactDir = path.join(dir, 'artifacts');
fs.mkdirSync(artifactDir, { recursive: true });
let failed = false;
if (check) {
  const want = specs.map(([, name]) => `${name}.json`).sort();
  const got = fs.readdirSync(artifactDir).filter((name) => name.endsWith('.json')).sort();
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    console.error(`artifact set differs: got ${got.join(',')}, want ${want.join(',')}`);
    failed = true;
  }
}
for (const [sourceName, contractName] of specs) {
  const built = output.contracts[sourceName][contractName];
  const artifact = {
    contractName,
    abi: built.abi,
    bytecode: built.evm.bytecode.object.toLowerCase(),
    deployedBytecode: built.evm.deployedBytecode.object.toLowerCase(),
    immutableReferences: built.evm.deployedBytecode.immutableReferences || {},
    compiler,
    sourceHashes
  };
  const encoded = JSON.stringify(artifact, null, 2) + '\n';
  const artifactPath = path.join(artifactDir, `${contractName}.json`);
  if (check) {
    let existing = '';
    try { existing = fs.readFileSync(artifactPath, 'utf8'); } catch (_) {}
    if (existing !== encoded) {
      console.error(`${contractName} artifact differs; run npm run build`);
      failed = true;
      continue;
    }
  } else {
    fs.writeFileSync(artifactPath, encoded);
  }
  const initBytes = artifact.bytecode.length / 2;
  const runtimeBytes = artifact.deployedBytecode.length / 2;
  const initHash = crypto.createHash('sha256').update(Buffer.from(artifact.bytecode, 'hex')).digest('hex');
  const runtimeHash = crypto.createHash('sha256').update(Buffer.from(artifact.deployedBytecode, 'hex')).digest('hex');
  if (initBytes > 24576 || runtimeBytes > 12288) {
    console.error(`${contractName} exceeds S0 size limit: init=${initBytes}, runtime=${runtimeBytes}`);
    failed = true;
  }
  console.log(`${check ? 'checked' : 'wrote'} ${contractName}: init=${initBytes} sha256=${initHash}, runtime=${runtimeBytes} sha256=${runtimeHash}`);
  if (contractName === 'ArtifactPage') {
    // bytes constructor ABI: offset + length + the maximum 4096-byte payload.
    const maxPageInit = initBytes + 64 + 4096;
    if (maxPageInit > 24576 || 4097 > 12288) {
      console.error(`ArtifactPage maximum deployment exceeds S0 size limit: init=${maxPageInit}, runtime=4097`);
      failed = true;
    }
    console.log(`ArtifactPage dynamic maximum: init=${maxPageInit}, runtime=4097 (STOP + 4096-byte payload)`);
  }
}
if (failed) process.exit(1);
console.log(`solc ${expectedVersion}; optimizer=200 viaIR=true evmVersion=cancun metadata=off`);
