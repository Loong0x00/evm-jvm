const fs=require('fs'),solc=require('solc');
if(solc.version()!=='0.8.30+commit.73712a01.Emscripten.clang')throw new Error('compiler version');
const source=fs.readFileSync(__dirname+'/SharedWorldCoordinator.sol','utf8');
const input={language:'Solidity',sources:{'SharedWorldCoordinator.sol':{content:source}},settings:{optimizer:{enabled:true,runs:200},viaIR:true,evmVersion:'cancun',metadata:{appendCBOR:false,bytecodeHash:'none'},outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}}};
const out=JSON.parse(solc.compile(JSON.stringify(input)));if(out.errors){for(const e of out.errors)console.error(e.formattedMessage);if(out.errors.some(e=>e.severity==='error'))process.exit(1)}
const c=out.contracts['SharedWorldCoordinator.sol'].SharedWorldCoordinator;
const crypto=require('crypto'),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const init=Buffer.from(c.evm.bytecode.object,'hex'),runtime=Buffer.from(c.evm.deployedBytecode.object,'hex');
const doc={contract:'SharedWorldCoordinator',compiler:solc.version(),settings:{optimizer:200,viaIR:true,evmVersion:'cancun',appendCBOR:false,bytecodeHash:'none'},sourceSHA256:sha(Buffer.from(source)),abi:c.abi,bytecode:c.evm.bytecode.object,deployedBytecode:c.evm.deployedBytecode.object,initBytes:init.length,runtimeBytes:runtime.length,initSHA256:sha(init),runtimeSHA256:sha(runtime)};
const p=process.argv[2];fs.mkdirSync(require('path').dirname(p),{recursive:true});fs.writeFileSync(p,JSON.stringify(doc,null,2)+'\n');console.log(JSON.stringify({compiler:doc.compiler,sourceSHA256:doc.sourceSHA256,initBytes:doc.initBytes,runtimeBytes:doc.runtimeBytes,initSHA256:doc.initSHA256,runtimeSHA256:doc.runtimeSHA256}));
