#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const solc = require('solc');
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
const check = process.argv.includes('--check');
const runtimePath = path.join(dir, 'LC0Interpreter.runtime.hex');
const abiPath = path.join(dir, 'LC0Interpreter.abi.json');
const abi = JSON.stringify(c.abi, null, 2) + '\n';
if (check) {
  if (fs.readFileSync(runtimePath, 'utf8').trim() !== hex) throw new Error('runtime artifact differs');
  if (fs.readFileSync(abiPath, 'utf8') !== abi) throw new Error('ABI artifact differs');
} else {
  fs.writeFileSync(runtimePath, hex + '\n'); fs.writeFileSync(abiPath, abi);
}
console.log(JSON.stringify({compiler: solc.version(), runtimeBytes: hex.length/2,
  runtimeSHA256: crypto.createHash('sha256').update(Buffer.from(hex,'hex')).digest('hex'),
  settings: {optimizer: 200, viaIR: true, evmVersion: 'cancun', metadata: false}}));
