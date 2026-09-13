'use strict';
// Independent canonical ABI re-encoding + event/checkpoint/counter verification.
// Only public successful receipts; no Java/class/ZIP evaluation or trace recovery.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert'),{keccak256}=require('js-sha3');
const [build,worlds,...labels]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p,'utf8')),pins=read(build+'/pins.json');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),word=n=>BigInt.asUintN(256,BigInt(n)).toString(16).padStart(64,'0');
const bytes=b=>word(b.length)+b.toString('hex').padEnd(Math.ceil(b.length/32)*64,'0');
const fields=['schema','lifecycle','outcome','epoch','checkpointRoot','machineStateRoot','totalJvmSteps','totalInternalSteps','executedJvmSteps','executedInternalSteps','result','javaKind','javaRef','javaClass','vfsStateRoot','inodeCount','descriptorCount','logicalFileBytes'];
let total=0;const summary={};
for(const label of labels){
 const d=path.join(worlds,label),m=read(d+'/durable-head.json'),rep=path.join(worlds,'reports',label);let j=0,i=0,n=0,peakGas=0,last;
 assert.equal(m.engineCodeHash,'0x'+pins.engine.runtimeKeccak256);assert.equal(m.coordinatorCodeHash,'0x'+pins.coordinator.runtimeKeccak256);assert.equal(m.engine,pins.address);assert.equal(m.engineNonce,0);
 for(const file of fs.readdirSync(rep).filter(n=>/^slice-\d+\.json$/.test(n)).sort()){
  const r=read(rep+'/'+file),s=r.slice,cp=fs.readFileSync(d+'/checkpoints/'+r.checkpointSHA256+'.bin');last=r;++n;++total;
  assert.equal(n,r.epoch);assert.equal(n,s.epoch);assert.equal(sha(cp),r.checkpointSHA256);assert.equal('0x'+keccak256(cp),s.checkpointRoot);assert.equal(cp.length,r.checkpointBytes);assert(cp.length<=1048576);assert.equal(s.schema,1);assert.equal(s.result,0);
  assert.equal(j+s.executedJvmSteps,s.totalJvmSteps);assert.equal(i+s.executedInternalSteps,s.totalInternalSteps);j=s.totalJvmSteps;i=s.totalInternalSteps;assert(s.executedJvmSteps<=m.quantum);assert(r.gasUsed>0&&r.gasUsed<=100000000&&r.elapsedMS<=30000);peakGas=Math.max(peakGas,r.gasUsed);
  const jc=Buffer.from(s.javaClass,'base64'),tuple=fields.map((f,k)=>word(k===13?18*32:s[f])).join('')+bytes(jc);
  const inner=word(64)+word(64+tuple.length/2)+tuple+bytes(cp),outer='0x'+word(32)+bytes(Buffer.from(inner,'hex'));assert.equal(r.outerABI,outer,'canonical nested ABI');
  assert.equal(r.nestedLogs.length,1);const l=r.nestedLogs[0];assert.equal(l.address.toLowerCase(),pins.address);assert.deepEqual(l.topics,['0x'+keccak256('CheckpointCommitted(bytes32,uint64,bytes32,bytes32,bytes32,uint8,uint64,uint64)'),m.instanceId,'0x'+word(n)]);
  assert.equal(l.data,'0x'+[s.checkpointRoot.slice(2),s.machineStateRoot.slice(2),s.vfsStateRoot.slice(2),word(s.lifecycle),word(j),word(i)].join(''));
  let at=0;for(let k=0;k<m.decoders.length;k++){for(let off=0;off<m.classSizes[k];off+=4096){const x=r.resourceReadReceipts[at++],want=Math.min(4096,m.classSizes[k]-off);assert.equal(x.To.toLowerCase(),m.decoders[k]);assert.equal(x.Offset,off);assert.equal(x.Requested,want);assert.equal(x.Returned,want);assert(x.Success);}}assert.equal(at,r.resourceReadReceipts.length);
 }
 assert.equal(n,m.epoch);assert.equal(j,m.jvmSteps);assert.equal(i,m.internalSteps);
 if(last){assert.equal(last.checkpointSHA256,m.checkpointSHA256);for(const [a,b] of [['lifecycle','lifecycle'],['outcome','outcome'],['checkpointRoot','checkpointRoot'],['machineStateRoot','machineRoot'],['vfsStateRoot','vfsRoot']])assert.equal(last.slice[a],m[b]);}
 summary[label]={receipts:n,java:j,internal:i,peakGas,lifecycle:m.lifecycle};
}
console.log(JSON.stringify({verifiedReceipts:total,summary,scope:'canonical nested ABI/events/CP hashes/counter chains/read ranges, not full Session acceptance'},null,2));
