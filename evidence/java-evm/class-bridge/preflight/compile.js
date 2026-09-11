#!/usr/bin/env node
'use strict';
const fs=require('fs'), path=require('path'), crypto=require('crypto');
const moduleRoot=process.env.CLASS_BRIDGE_NODE_MODULES;
if(!moduleRoot) throw new Error('CLASS_BRIDGE_NODE_MODULES is required');
const solc=require(path.join(moduleRoot,'solc'));
if(solc.version()!=='0.8.30+commit.73712a01.Emscripten.clang') throw new Error('wrong solc '+solc.version());
const dir=__dirname, source=fs.readFileSync(path.join(dir,'ClassBridge.sol'),'utf8');
const input={language:'Solidity',sources:{'ClassBridge.sol':{content:source}},settings:{optimizer:{enabled:true,runs:200},viaIR:true,evmVersion:'cancun',metadata:{appendCBOR:false,bytecodeHash:'none'},outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}}};
const output=JSON.parse(solc.compile(JSON.stringify(input)));
for(const e of output.errors||[]) if(e.severity==='error') throw new Error(e.formattedMessage);
const c=output.contracts['ClassBridge.sol'].ClassBridge;
const artifact={contractName:'ClassBridge',compiler:solc.version(),settings:input.settings,abi:c.abi,bytecode:c.evm.bytecode.object,deployedBytecode:c.evm.deployedBytecode.object,sourceSHA256:crypto.createHash('sha256').update(source).digest('hex')};
const out=process.argv[2]; if(!out) throw new Error('usage: compile.js OUT.json');
fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,JSON.stringify(artifact,null,2)+'\n');
const init=Buffer.from(artifact.bytecode,'hex'), runtime=Buffer.from(artifact.deployedBytecode,'hex');
console.log(JSON.stringify({compiler:artifact.compiler,initBytes:init.length,runtimeBytes:runtime.length,initSHA256:crypto.createHash('sha256').update(init).digest('hex'),runtimeSHA256:crypto.createHash('sha256').update(runtime).digest('hex'),sourceSHA256:artifact.sourceSHA256},null,2));
