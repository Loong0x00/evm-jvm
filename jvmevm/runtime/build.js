#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const solc = require('solc');

const dir = __dirname;
const sourceName = 'JVMSubsetInterpreter.sol';
const artifactPath = path.join(dir, 'JVMSubsetInterpreter.runtime.hex');
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const input = {
  language: 'Solidity',
  sources: { [sourceName]: { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    evmVersion: 'cancun',
    viaIR: true,
    metadata: { appendCBOR: false, bytecodeHash: 'none' },
    outputSelection: { '*': { '*': ['abi', 'evm.deployedBytecode.object'] } }
  }
};
const output = JSON.parse(solc.compile(JSON.stringify(input)));
const errors = (output.errors || []).filter(e => e.severity === 'error');
if (errors.length) {
  for (const e of output.errors) console.error(e.formattedMessage);
  process.exit(1);
}
const contract = output.contracts[sourceName].JVMSubsetInterpreter;
const hex = contract.evm.deployedBytecode.object.toLowerCase() + '\n';
const hash = crypto.createHash('sha256').update(Buffer.from(hex.trim(), 'hex')).digest('hex');
if (process.argv.includes('--check')) {
  let existing;
  try { existing = fs.readFileSync(artifactPath, 'utf8'); } catch (_) { existing = ''; }
  if (existing !== hex) {
    console.error('runtime artifact differs; run npm run build');
    process.exit(1);
  }
  console.log(`artifact matches solc ${solc.version()}: sha256=${hash}`);
} else {
  fs.writeFileSync(artifactPath, hex);
  console.log(`wrote ${path.basename(artifactPath)} (${hex.trim().length / 2} bytes, sha256=${hash})`);
  console.log(`solc ${solc.version()}, optimizer runs=200, viaIR=true, evmVersion=cancun, metadata disabled`);
}
