#!/usr/bin/env node
'use strict';

const crypto=require('crypto');
const fs=require('fs');
const path=require('path');
const solc=require('solc');
const dir=__dirname;
const check=process.argv.length===3&&process.argv[2]==='--check';
if(process.argv.length!==(check?3:2)){console.error('usage: node build.js [--check]');process.exit(2);}
const expectedVersion='0.8.30+commit.73712a01.Emscripten.clang';
if(solc.version()!==expectedVersion){console.error(`wrong solc: got ${solc.version()}, want ${expectedVersion}`);process.exit(1);}
const sourceNames=['S2bTypes.sol','S2bMetadataPage.sol','S2bAnalyzeModule.sol','S2bClassLinker.sol'];
const sources={},sourceHashes={};
for(const name of sourceNames){const content=fs.readFileSync(path.join(dir,name),'utf8');sources[name]={content};sourceHashes[name]=crypto.createHash('sha256').update(content).digest('hex');}
const settings={optimizer:{enabled:true,runs:200},evmVersion:'cancun',viaIR:true,metadata:{appendCBOR:false,bytecodeHash:'none'},outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object','evm.deployedBytecode.immutableReferences']}}};
const output=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,settings})));
for(const d of output.errors||[])if(d.severity==='error')console.error(d.formattedMessage);
if((output.errors||[]).some(d=>d.severity==='error'))process.exit(1);
const compiler={version:expectedVersion,optimizer:{enabled:true,runs:200},viaIR:true,evmVersion:'cancun',metadata:{appendCBOR:false,bytecodeHash:'none'}};
const specs=[['S2bMetadataPage.sol','S2bMetadataPage'],['S2bAnalyzeModule.sol','S2bAnalyzeModule'],['S2bClassLinker.sol','S2bClassLinker']];
const artifactDir=path.join(dir,'artifacts');fs.mkdirSync(artifactDir,{recursive:true});let failed=false;
if(check){const want=specs.map(x=>`${x[1]}.json`).sort();const got=fs.readdirSync(artifactDir).filter(x=>x.endsWith('.json')).sort();if(JSON.stringify(got)!==JSON.stringify(want)){console.error(`artifact set differs: got ${got.join(',')}, want ${want.join(',')}`);failed=true;}}
for(const [sourceName,contractName] of specs){const built=output.contracts[sourceName][contractName];const artifact={contractName,abi:built.abi,bytecode:built.evm.bytecode.object.toLowerCase(),deployedBytecode:built.evm.deployedBytecode.object.toLowerCase(),immutableReferences:built.evm.deployedBytecode.immutableReferences||{},compiler,sourceHashes};const encoded=JSON.stringify(artifact,null,2)+'\n';const file=path.join(artifactDir,`${contractName}.json`);if(check){let old='';try{old=fs.readFileSync(file,'utf8');}catch(_){}if(old!==encoded){console.error(`${contractName} artifact differs; run npm run build`);failed=true;}}else fs.writeFileSync(file,encoded);
 const initBytes=artifact.bytecode.length/2,runtimeBytes=artifact.deployedBytecode.length/2;const initHash=crypto.createHash('sha256').update(Buffer.from(artifact.bytecode,'hex')).digest('hex');const runtimeHash=crypto.createHash('sha256').update(Buffer.from(artifact.deployedBytecode,'hex')).digest('hex');const runtimeLimit=contractName==='S2bAnalyzeModule'?20480:12288;let maxInit=initBytes;if(contractName==='S2bMetadataPage')maxInit+=64+Math.ceil(8191/32)*32;if(contractName==='S2bClassLinker')maxInit+=96;
 if(maxInit>24576||runtimeBytes>runtimeLimit){console.error(`${contractName} exceeds S2b-L size limit: init=${initBytes}, maxInit=${maxInit}, runtime=${runtimeBytes}, runtimeLimit=${runtimeLimit}`);failed=true;}
 console.log(`${check?'checked':'wrote'} ${contractName}: init=${initBytes} maxInit=${maxInit} sha256=${initHash}, runtime=${runtimeBytes} sha256=${runtimeHash}`);
}
if(failed)process.exit(1);console.log(`solc ${expectedVersion}; optimizer=200 viaIR=true evmVersion=cancun metadata=off`);
