const fs=require('fs'), solc=require('/home/user/evm-jvm/geth/jvmevm/runtime/node_modules/solc');
const p='build/java-diff-mc-zi0-persistence-preflight/ZI0Persistent.sol';
const input={language:'Solidity',sources:{'ZI0Persistent.sol':{content:fs.readFileSync(p,'utf8')}},settings:{optimizer:{enabled:true,runs:200},viaIR:true,evmVersion:'cancun',metadata:{appendCBOR:false,bytecodeHash:'none'},outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}}};
const out=JSON.parse(solc.compile(JSON.stringify(input)));if(out.errors){for(const e of out.errors) console.error(e.formattedMessage);if(out.errors.some(e=>e.severity==='error'))process.exit(1)}
const c=out.contracts['ZI0Persistent.sol'].ZI0Persistent;fs.writeFileSync('build/java-diff-mc-zi0-persistence-preflight/prototype.json',JSON.stringify({abi:c.abi,bytecode:'0x'+c.evm.bytecode.object,runtime:'0x'+c.evm.deployedBytecode.object},null,2));
