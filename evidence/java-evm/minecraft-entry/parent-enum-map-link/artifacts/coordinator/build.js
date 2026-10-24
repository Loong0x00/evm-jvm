'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const solc = require('solc');
const { keccak256 } = require('js-sha3');
const VERSION = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== VERSION) throw new Error(`solc mismatch: ${solc.version()}`);
const dir = __dirname;
const sourceName = 'MCEntryCoordinator.sol';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const output = JSON.parse(solc.compile(JSON.stringify({
  language: 'Solidity',
  sources: { [sourceName]: { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    viaIR: true,
    evmVersion: 'cancun',
    metadata: { appendCBOR: false, bytecodeHash: 'none' },
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object', 'storageLayout'] } },
  },
})));
for (const e of output.errors || []) console.error(e.formattedMessage);
if ((output.errors || []).some((e) => e.severity === 'error')) process.exit(1);
const contract = output.contracts[sourceName].MCEntryCoordinator;
const init = contract.evm.bytecode.object.toLowerCase();
const runtime = contract.evm.deployedBytecode.object.toLowerCase();
if (runtime.length / 2 > 24576) throw new Error(`coordinator exceeds EIP170: ${runtime.length / 2}`);
const artifact = {
  contractName: 'MCEntryCoordinator',
  abi: contract.abi,
  bytecode: init,
  deployedBytecode: runtime,
  compiler: {
    version: VERSION,
    optimizer: { enabled: true, runs: 200 },
    viaIR: true,
    evmVersion: 'cancun',
    metadata: { appendCBOR: false, bytecodeHash: 'none' },
  },
  sourceHashes: { [sourceName]: sha(source) },
  codeHashes: {
    initSHA256: sha(Buffer.from(init, 'hex')),
    runtimeSHA256: sha(Buffer.from(runtime, 'hex')),
    runtimeKeccak256: keccak256(Buffer.from(runtime, 'hex')),
  },
  storageLayout: contract.storageLayout,
};
for (const [name, data] of Object.entries({
  'MCEntryCoordinator.init.hex': `${init}\n`,
  'MCEntryCoordinator.runtime.hex': `${runtime}\n`,
  'MCEntryCoordinator.abi.json': `${JSON.stringify(contract.abi, null, 2)}\n`,
  'MCEntryCoordinator.json': `${JSON.stringify(artifact, null, 2)}\n`,
})) fs.writeFileSync(path.join(dir, name), data);
console.log(JSON.stringify({
  compiler: VERSION,
  sourceSHA256: sha(source),
  initBytes: init.length / 2,
  runtimeBytes: runtime.length / 2,
  runtimeSHA256: artifact.codeHashes.runtimeSHA256,
  runtimeKeccak256: artifact.codeHashes.runtimeKeccak256,
  abiEntries: contract.abi.length,
}, null, 2));
