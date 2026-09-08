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
  },
  {
    name: 'Float', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public final class Float { private Float() {} public static native float intBitsToFloat(int bits); public static native int floatToRawIntBits(float value); }\n',
    bytes: 197, hash: '437d784b11d0b632017a94cc2c0d99b35cd93c39f49b98b0660e4316d9960dd4'
  },
  {
    name: 'Double', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public final class Double { private Double() {} public static native double longBitsToDouble(long bits); public static native long doubleToRawLongBits(double value); }\n',
    bytes: 202, hash: 'd9ac93be34df21e1ec5872e307f67b1301c0606c1ccd57ee6a61030b0aa45363'
  }
,
  {
    name: 'Throwable', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class Throwable implements java.io.Serializable {}\n',
    bytes: 162, hash: '785b24daa1fb0d459f0bdaefafdedc2657a068afd11f72bcf9bb9009285b39ba'
  },
  {
    name: 'Error', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class Error extends Throwable {}\n',
    bytes: 133, hash: '17c5ca84f07e432aadbcebb2bc455cc3c45643074a3678f0dc10a4058b3eb3af'
  },
  {
    name: 'VirtualMachineError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public abstract class VirtualMachineError extends Error {}\n',
    bytes: 143, hash: '5d642ae5c82224f1591dc542933a229b17f0db1ae72affe32b8b99d4f18523ee'
  },
  {
    name: 'StackOverflowError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class StackOverflowError extends VirtualMachineError {}\n',
    bytes: 156, hash: 'fccb08bbd1cfe883b6144aa55509123e94de269371e94d7365ea1ad7821bd13d'
  },
  {
    name: 'OutOfMemoryError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class OutOfMemoryError extends VirtualMachineError {}\n',
    bytes: 154, hash: '96ede0eb8b6318503da363809b13ac9a7b33d99edaa69ed1c075fcab70ffe241'
  },
  {
    name: 'LinkageError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class LinkageError extends Error {}\n',
    bytes: 136, hash: 'eeb36cd0d4771d3bccd8f5d5839c140a44d1e12ac94a0cda4d79f4aa64bb6f11'
  },
  {
    name: 'ExceptionInInitializerError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class ExceptionInInitializerError extends LinkageError {}\n',
    bytes: 158, hash: 'b75ab46b8cdb7b2e7117176e3e11a52f439018c81e2e5f8662b3eafb4fcd57f7'
  },
  {
    name: 'IncompatibleClassChangeError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class IncompatibleClassChangeError extends LinkageError {}\n',
    bytes: 159, hash: '30129372d01781ee244be4ca0920d1f50e934f640f50b7fbb975673e6a8f1b6d'
  },
  {
    name: 'NoClassDefFoundError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class NoClassDefFoundError extends LinkageError {}\n',
    bytes: 151, hash: '32060804295c79139e095a9efa9a6633f96be11ef6971f848f891473811f883f'
  },
  {
    name: 'AbstractMethodError', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class AbstractMethodError extends IncompatibleClassChangeError {}\n',
    bytes: 166, hash: '877fbe3a7d637c386f08400a34cfe7c265a3ed66b384f8eac958e2ff78f88ca6'
  },
  {
    name: 'Exception', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class Exception extends Throwable {}\n',
    bytes: 137, hash: '7c3af1164ae24429df64c0e2b40f13d4ff44f313ddf41263a84227930a274715'
  },
  {
    name: 'RuntimeException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class RuntimeException extends Exception {}\n',
    bytes: 144, hash: 'fb43c3b06c92c52d97957d80cc75c39a4b026d6bc94c11d4f126575406cdefad'
  },
  {
    name: 'ArithmeticException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class ArithmeticException extends RuntimeException {}\n',
    bytes: 154, hash: '7d8aa035041464b3c175a642b129747f3345ed4e7df87232971968c9125ceecf'
  },
  {
    name: 'NullPointerException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class NullPointerException extends RuntimeException {}\n',
    bytes: 155, hash: '7eef86618751a918ba17f6249289e386dbcee4305ddb3a5b30d721e603ca70b8'
  },
  {
    name: 'NegativeArraySizeException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class NegativeArraySizeException extends RuntimeException {}\n',
    bytes: 161, hash: '56c402963e50be92fcf1d2808684c6ec7686c890975c06fcca33177a70e442cb'
  },
  {
    name: 'ClassCastException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class ClassCastException extends RuntimeException {}\n',
    bytes: 153, hash: '0e3883f17eb9a46d99e977879bf408be11f9418bf3902b7ea0884f57ea72b654'
  },
  {
    name: 'ArrayStoreException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class ArrayStoreException extends RuntimeException {}\n',
    bytes: 154, hash: 'bbe8ba14a08a545da205a070b6965b2875815b1b9bd0474312fd4de4e7483ffd'
  },
  {
    name: 'IndexOutOfBoundsException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class IndexOutOfBoundsException extends RuntimeException {}\n',
    bytes: 160, hash: '057576b458d9581f2a1b49fd9055947038adeab15132541372a137cf89c723d1'
  },
  {
    name: 'ArrayIndexOutOfBoundsException', packagePath: ['java', 'lang'],
    expectedSource: 'package java.lang; public class ArrayIndexOutOfBoundsException extends IndexOutOfBoundsException {}\n',
    bytes: 174, hash: '2309a8d0ad31f094867d449013000340f2b22e412d7cb770f93fbc05a8439c99'
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
