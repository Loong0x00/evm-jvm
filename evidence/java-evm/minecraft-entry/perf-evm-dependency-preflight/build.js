'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const base = path.resolve(__dirname, '../../../../jvmevm/runtime/node_modules');
const solc = require(path.join(base, 'solc'));
const { keccak256 } = require(path.join(base, 'js-sha3'));
const version = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== version) throw new Error(`solc mismatch: ${solc.version()}`);
const sourcePath = path.join(__dirname, 'BindingMethodInspector.sol');
const source = fs.readFileSync(sourcePath, 'utf8');
const outputPath = path.join(__dirname, 'BindingMethodInspector.json');
const input = {
  language: 'Solidity',
  sources: { 'BindingMethodInspector.sol': { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 1 },
    viaIR: true,
    evmVersion: 'cancun',
    metadata: { appendCBOR: false, bytecodeHash: 'none' },
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object', 'evm.deployedBytecode.immutableReferences'] } },
  },
};
const compiled = JSON.parse(solc.compile(JSON.stringify(input)));
for (const e of compiled.errors || []) if (e.severity === 'error') throw new Error(e.formattedMessage);
const c = compiled.contracts['BindingMethodInspector.sol'].BindingMethodInspector;
const init = c.evm.bytecode.object.toLowerCase();
const runtime = c.evm.deployedBytecode.object.toLowerCase();
const sha256 = (data) => crypto.createHash('sha256').update(data).digest('hex');
const artifact = {
  diagnosticOnly: true,
  sourceSHA256: sha256(Buffer.from(source)),
  compiler: { version, optimizer: { enabled: true, runs: 1 }, viaIR: true, evmVersion: 'cancun', metadata: { appendCBOR: false, bytecodeHash: 'none' } },
  abi: c.abi,
  immutableReferences: c.evm.deployedBytecode.immutableReferences,
  bytecode: init,
  deployedBytecode: runtime,
  codeHashes: {
    initSHA256: sha256(Buffer.from(init, 'hex')),
    runtimeSHA256: sha256(Buffer.from(runtime, 'hex')),
    runtimeKeccak256: keccak256(Buffer.from(runtime, 'hex')),
  },
  initBytes: init.length / 2,
  runtimeBytes: runtime.length / 2,
};
const rendered = JSON.stringify(artifact, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (!fs.existsSync(outputPath) || fs.readFileSync(outputPath, 'utf8') !== rendered) throw new Error('generated artifact differs from committed artifact');
} else {
  if (fs.existsSync(outputPath) && !process.argv.includes('--replace')) throw new Error('artifact exists; use --replace only for an intentional source rebuild');
  fs.writeFileSync(outputPath, rendered);
}
console.log(JSON.stringify({ compiler: version, sourceSHA256: artifact.sourceSHA256, initBytes: artifact.initBytes, runtimeBytes: artifact.runtimeBytes, runtimeSHA256: artifact.codeHashes.runtimeSHA256, runtimeKeccak256: artifact.codeHashes.runtimeKeccak256 }, null, 2));
