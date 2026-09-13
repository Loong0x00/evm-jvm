'use strict';
// READ-ONLY source metadata build. It neither writes nor deploys the interpreter.
const fs = require('fs'), path = require('path'), crypto = require('crypto'), zlib = require('zlib');
const solc = require('solc'); const {keccak256} = require('js-sha3');
const here = __dirname;
const engineDir = path.resolve(here, '../../parent-c24d374bc/engine');
const sourceName = 'MCEntryInterpreter.sol';
const sourcePath = path.join(engineDir, sourceName);
const expectedPath = path.join(engineDir, 'MCEntryInterpreter.runtime.hex');
const compiler = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== compiler) throw new Error(`solc ${solc.version()}`);
const source = fs.readFileSync(sourcePath, 'utf8');
const settings = {
  optimizer: {enabled: true, runs: 200}, viaIR: true, evmVersion: 'cancun',
  metadata: {appendCBOR: false, bytecodeHash: 'none'},
  outputSelection: {'*': {'': ['ast'], '*': [
    'evm.deployedBytecode.object', 'evm.deployedBytecode.sourceMap',
    'evm.deployedBytecode.generatedSources', 'evm.deployedBytecode.functionDebugData',
    'evm.deployedBytecode.opcodes', 'irOptimized'
  ]}}
};
const input = {language: 'Solidity', sources: {[sourceName]: {content: source}}, settings};
const output = JSON.parse(solc.compile(JSON.stringify(input)));
for (const e of output.errors || []) process.stderr.write(e.formattedMessage);
if ((output.errors || []).some(e => e.severity === 'error')) process.exit(1);
const c = output.contracts[sourceName].MCEntryInterpreter;
const runtime = c.evm.deployedBytecode.object.toLowerCase();
const expected = fs.readFileSync(expectedPath, 'utf8').trim().toLowerCase();
if (runtime !== expected) throw new Error(`runtime mismatch: got ${runtime.length/2}, expected ${expected.length/2}`);
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const metadata = {
  format: 'MC-PROPERTIES-COST-METADATA-1', sourcePath: 'parent-c24d374bc/engine/MCEntryInterpreter.sol',
  compiler, settings, sourceSHA256: sha(source), runtimeBytes: runtime.length/2,
  runtimeSHA256: sha(Buffer.from(runtime, 'hex')), runtimeKeccak256: keccak256(Buffer.from(runtime, 'hex')),
  exactRuntimeEquality: true, ast: output.sources[sourceName].ast,
  deployedSourceMap: c.evm.deployedBytecode.sourceMap,
  generatedSources: c.evm.deployedBytecode.generatedSources,
  functionDebugData: c.evm.deployedBytecode.functionDebugData,
  opcodes: c.evm.deployedBytecode.opcodes, irOptimized: c.irOptimized
};
fs.writeFileSync(path.join(here, 'MCEntryInterpreter.debug.json.gz'), zlib.gzipSync(JSON.stringify(metadata), {level: 9}));
fs.writeFileSync(path.join(here, 'build-summary.json'), JSON.stringify({
  format: metadata.format, compiler, settings, sourceSHA256: metadata.sourceSHA256,
  runtimeBytes: metadata.runtimeBytes, runtimeSHA256: metadata.runtimeSHA256,
  runtimeKeccak256: metadata.runtimeKeccak256, exactRuntimeEquality: true,
  sourceMapEntries: metadata.deployedSourceMap.split(';').length,
  generatedSourceCount: metadata.generatedSources.length,
  functionDebugDataCount: Object.keys(metadata.functionDebugData).length
}, null, 2)+'\n');
