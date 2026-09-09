#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const solc = require('solc');
const expectedVersion = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== expectedVersion) throw new Error(`wrong solc: ${solc.version()}`);
const check = process.argv.length === 3 && process.argv[2] === '--check';
if (process.argv.length !== (check ? 3 : 2)) throw new Error('usage: node build.js [--check]');
const dir = __dirname;
const sourceName = 'LC0Interpreter.sol';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const input = {
  language: 'Solidity', sources: {[sourceName]: {content: source}},
  settings: {
    optimizer: {enabled: true, runs: 200}, viaIR: true,
    evmVersion: 'cancun', metadata: {appendCBOR: false, bytecodeHash: 'none'},
    outputSelection: {'*': {'*': ['abi','evm.deployedBytecode.object']}}
  }
};
const output = JSON.parse(solc.compile(JSON.stringify(input)));
for (const e of output.errors || []) console.error(e.formattedMessage);
if ((output.errors || []).some(e => e.severity === 'error')) process.exit(1);
const c = output.contracts[sourceName].LC0Interpreter;
const hex = c.evm.deployedBytecode.object.toLowerCase();
if (Buffer.from(hex, 'hex').length > 256 * 1024) throw new Error('LC0 runtime exceeds 256 KiB');
const runtimePath = path.join(dir, 'LC0Interpreter.runtime.hex');
const abiPath = path.join(dir, 'LC0Interpreter.abi.json');
const abi = JSON.stringify(c.abi, null, 2) + '\n';
const manifestPath = path.join(dir, 'artifacts', 'LC0Interpreter.json');
const manifest = JSON.stringify({
  contractName: 'LC0Interpreter', abi: c.abi, deployedBytecode: hex,
  compiler: {version: expectedVersion, optimizer: {enabled: true, runs: 200}, viaIR: true,
    evmVersion: 'cancun', metadata: {appendCBOR: false, bytecodeHash: 'none'}},
  sourceHashes: {[sourceName]: crypto.createHash('sha256').update(source).digest('hex')},
}, null, 2) + '\n';
if (check) {
  if (fs.readFileSync(runtimePath, 'utf8').trim() !== hex) throw new Error('runtime artifact differs');
  if (fs.readFileSync(abiPath, 'utf8') !== abi) throw new Error('ABI artifact differs');
  if (fs.readFileSync(manifestPath, 'utf8') !== manifest) throw new Error('combined artifact/provenance differs');
} else {
  fs.writeFileSync(runtimePath, hex + '\n'); fs.writeFileSync(abiPath, abi);
  fs.mkdirSync(path.dirname(manifestPath), {recursive: true});
  fs.writeFileSync(manifestPath, manifest);
}
console.log(JSON.stringify({compiler: solc.version(), runtimeBytes: hex.length/2,
  runtimeSHA256: crypto.createHash('sha256').update(Buffer.from(hex,'hex')).digest('hex'),
  settings: {optimizer: 200, viaIR: true, evmVersion: 'cancun', metadata: false}}));
