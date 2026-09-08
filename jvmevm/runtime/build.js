#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');
const childProcess = require('child_process');
const solc = require('solc');

const dir = __dirname;
const sourceName = 'JVMSubsetInterpreter.sol';
const artifactPath = path.join(dir, 'JVMSubsetInterpreter.runtime.hex');
const bootstrapDir = path.join(dir, 'bootstrap');
const bootstraps = [
  {
    name: 'Object', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class Object { public Object() {} }\n',
    bytes: 95, hash: 'af9136af3be2c44ce120ac403beccb8b1cc963fc83dc1457e63f8b69dd497fe0'
  },
  {
    name: 'Cloneable', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public interface Cloneable {}\n',
    bytes: 71, hash: '07930c21cec8dfc8a031c04590af290511e2be6dbae7ad1282a2cfa00a06c457'
  },
  {
    name: 'Serializable', packagePath: ['java', 'io'],
    expectedSource: 'package java.io; public interface Serializable {}\n',
    bytes: 72, hash: '90bd3c397ef8d1f81a72b59b80c6a96ac158ac9fc97c95851d246eff8e66a70a'
  }
];
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');

function verifyBootstrap() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'jvmevm-bootstrap-'));
  try {
    const out = path.join(tmp, 'out');
    const sourcePaths = [];
    for (const spec of bootstraps) {
      const bootstrapSource = fs.readFileSync(path.join(bootstrapDir, `${spec.name}.java`), 'utf8');
      if (bootstrapSource !== spec.expectedSource) {
        throw new Error(`bootstrap ${spec.name}.java differs from trusted source`);
      }
      const checkedHex = fs.readFileSync(path.join(bootstrapDir, `${spec.name}.class.hex`), 'utf8').trim().toLowerCase();
      const embedded = source.match(new RegExp(`function _bootstrap${spec.name}\\(\\)[\\s\\S]*?return hex"([0-9a-f]+)";`));
      if (!embedded || embedded[1] !== checkedHex) {
        throw new Error(`embedded bootstrap ${spec.name} differs from ${spec.name}.class.hex`);
      }
      const src = path.join(tmp, ...spec.packagePath, `${spec.name}.java`);
      fs.mkdirSync(path.dirname(src), { recursive: true });
      fs.writeFileSync(src, bootstrapSource);
      sourcePaths.push(src);
    }
    childProcess.execFileSync('javac', ['--release', '8', '-g:none', '-Xlint:-options', '-d', out, ...sourcePaths], {
      timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']
    });
    for (const spec of bootstraps) {
      const bytes = fs.readFileSync(path.join(out, ...spec.packagePath, `${spec.name}.class`));
      const checkedHex = fs.readFileSync(path.join(bootstrapDir, `${spec.name}.class.hex`), 'utf8').trim().toLowerCase();
      const hash = crypto.createHash('sha256').update(bytes).digest('hex');
      if (bytes.length !== spec.bytes || hash !== spec.hash || bytes.toString('hex') !== checkedHex) {
        throw new Error(`bootstrap ${spec.name} mismatch: bytes=${bytes.length} sha256=${hash}`);
      }
      console.log(`bootstrap ${spec.name} verified: ${spec.bytes} bytes, sha256=${spec.hash}`);
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

try { verifyBootstrap(); } catch (e) {
  console.error(e.message || e);
  process.exit(1);
}

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
