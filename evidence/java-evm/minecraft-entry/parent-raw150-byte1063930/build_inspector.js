'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),solc=require('solc');
if(!solc.version().startsWith('0.8.30+commit.73712a01'))throw Error('compiler pin');
const src=path.join(__dirname,'BindingMethodInspector.sol'),out=process.argv[2];
if(!out||fs.existsSync(out))throw Error('fresh output JSON required');
const input={language:'Solidity',sources:{'BindingMethodInspector.sol':{content:fs.readFileSync(src,'utf8')}},settings:{viaIR:true,evmVersion:'cancun',optimizer:{enabled:true,runs:1},metadata:{bytecodeHash:'none'},outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object','evm.deployedBytecode.immutableReferences']}}}};
const result=JSON.parse(solc.compile(JSON.stringify(input)));for(const e of result.errors||[]){if(e.severity==='error')throw Error(e.formattedMessage);}
const c=result.contracts['BindingMethodInspector.sol'].BindingMethodInspector;
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify({diagnosticOnly:true,compiler:solc.version(),sourceSHA256:crypto.createHash('sha256').update(fs.readFileSync(src)).digest('hex'),abi:c.abi,immutableReferences:c.evm.deployedBytecode.immutableReferences,bytecode:c.evm.bytecode.object,deployedBytecode:c.evm.deployedBytecode.object},null,2)+'\n');
console.log(JSON.stringify({diagnosticOnly:true,runtimeBytes:c.evm.deployedBytecode.object.length/2}));
