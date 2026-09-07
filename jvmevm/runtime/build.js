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
const bootstrapSourcePath = path.join(bootstrapDir, 'Object.java');
const bootstrapHexPath = path.join(bootstrapDir, 'Object.class.hex');
const expectedBootstrapSource = 'package java.lang; public class Object { public Object() {} }\n';
const expectedBootstrapHash = 'af9136af3be2c44ce120ac403beccb8b1cc963fc83dc1457e63f8b69dd497fe0';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');

function verifyBootstrap() {
  const bootstrapSource = fs.readFileSync(bootstrapSourcePath, 'utf8');
  if (bootstrapSource !== expectedBootstrapSource) throw new Error('bootstrap Object.java differs from trusted source');
  const checkedHex = fs.readFileSync(bootstrapHexPath, 'utf8').trim().toLowerCase();
  const embedded = source.match(/function _bootstrapObject\(\)[\s\S]*?return hex"([0-9a-f]+)";/);
  if (!embedded || embedded[1] !== checkedHex) throw new Error('embedded bootstrap Object differs from Object.class.hex');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'jvmevm-bootstrap-'));
  try {
    const src = path.join(tmp, 'java', 'lang', 'Object.java');
    const out = path.join(tmp, 'out');
    fs.mkdirSync(path.dirname(src), { recursive: true });
    fs.writeFileSync(src, bootstrapSource);
    childProcess.execFileSync('javac', ['--release', '8', '-g:none', '-Xlint:-options', '-d', out, src], {
      timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']
    });
    const bytes = fs.readFileSync(path.join(out, 'java', 'lang', 'Object.class'));
    const hash = crypto.createHash('sha256').update(bytes).digest('hex');
    if (bytes.length !== 95 || hash !== expectedBootstrapHash || bytes.toString('hex') !== checkedHex) {
      throw new Error(`bootstrap Object mismatch: bytes=${bytes.length} sha256=${hash}`);
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  console.log(`bootstrap Object verified: 95 bytes, sha256=${expectedBootstrapHash}`);
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
