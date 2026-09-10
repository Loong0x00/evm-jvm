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
const sourceName = 'String0Interpreter.sol';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const bootstrapSourceName = 'bootstrap/java/lang/String.java';
const bootstrapHexName = 'bootstrap/java/lang/String.class.hex';
const bootstrapSource = fs.readFileSync(path.join(dir, bootstrapSourceName), 'utf8');
const bootstrapHexText = fs.readFileSync(path.join(dir, bootstrapHexName), 'utf8').trim().toLowerCase();
if (!/^[0-9a-f]+$/.test(bootstrapHexText) || bootstrapHexText.length % 2 !== 0) {
  throw new Error('malformed String.class.hex');
}
const bootstrapBytes = Buffer.from(bootstrapHexText, 'hex');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const expectedBootstrapSourceHash = '95542f5d4b869cc96ee395c322f8368a275fe3338ae60c7810afded6d4b81f2e';
const expectedBootstrapClassHash = '7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad';
if (sha256(bootstrapSource) !== expectedBootstrapSourceHash
    || bootstrapBytes.length !== 984 || sha256(bootstrapBytes) !== expectedBootstrapClassHash) {
  throw new Error('pinned SC0 String bootstrap differs');
}
const embedded = source.match(/function _bootstrapString\(\)[\s\S]*?return hex"([0-9a-f]+)";/);
if (!embedded || embedded[1] !== bootstrapHexText) {
  throw new Error('embedded Solidity String image differs from pinned class hex');
}
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
const c = output.contracts[sourceName].String0Interpreter;
const hex = c.evm.deployedBytecode.object.toLowerCase();
if (Buffer.from(hex, 'hex').length > 256 * 1024) throw new Error('SC0 runtime exceeds 256 KiB');
const runtimePath = path.join(dir, 'String0Interpreter.runtime.hex');
const abiPath = path.join(dir, 'String0Interpreter.abi.json');
const abi = JSON.stringify(c.abi, null, 2) + '\n';
const manifestPath = path.join(dir, 'artifacts', 'String0Interpreter.json');
const manifest = JSON.stringify({
  contractName: 'String0Interpreter', abi: c.abi, deployedBytecode: hex,
  compiler: {version: expectedVersion, optimizer: {enabled: true, runs: 200}, viaIR: true,
    evmVersion: 'cancun', metadata: {appendCBOR: false, bytecodeHash: 'none'}},
  sourceHashes: {[sourceName]: sha256(source)},
  bootstrap: {
    source: bootstrapSourceName, sourceSHA256: sha256(bootstrapSource),
    classHex: bootstrapHexName, classBytes: bootstrapBytes.length,
    classSHA256: sha256(bootstrapBytes), reproduction: 'javac --release 8 -g:none'
  },
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
