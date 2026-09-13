'use strict';
// READ-ONLY EVM receipt/cryptographic verification. No JVM/class/ZIP evaluation.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert');
const {keccak256}=require('js-sha3');const b=process.argv[2],d=path.join(b,'official9');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));const m=read(path.join(d,'durable-head.json'));const r=read(path.join(b,'reports/official9/slice-00000000000000000001.json'));const s=r.slice;
const cp=fs.readFileSync(path.join(d,'checkpoints',r.checkpointSHA256+'.bin'));const sha=x=>crypto.createHash('sha256').update(x).digest('hex');const word=x=>BigInt(x).toString(16).padStart(64,'0');
assert.equal(sha(cp),r.checkpointSHA256);assert.equal('0x'+keccak256(cp),s.checkpointRoot);assert.equal(cp.length,r.checkpointBytes);assert(cp.length<=1048576);
assert.equal(s.schema,1);assert.equal(s.epoch,1);assert.equal(s.lifecycle,1);assert.equal(s.outcome,1);assert.equal(s.result,0);assert.equal(s.totalJvmSteps,1);assert.equal(s.totalInternalSteps,3);assert.equal(s.javaRef,0);
assert.equal(m.checkpointRoot,s.checkpointRoot);assert.equal(m.machineRoot,s.machineStateRoot);assert.equal(m.vfsRoot,s.vfsStateRoot);assert.equal(m.epoch,1);assert.equal(m.engineNonce,0);
assert.equal(m.engineCodeHash,'0x9d4fdaec87e8e21f243f4cc994da134646311f02cc0141da649085e2c5ada61c');assert.equal(m.coordinatorCodeHash,'0x1d08028ae55a3a43471cdc417ba48ba7900ba70b29398d2e15ef58d6044df694');
assert.equal(r.nestedLogs.length,1);const l=r.nestedLogs[0];assert.equal(l.address.toLowerCase(),'0x4d43454e545259454e47494e4500000000000001');assert.deepEqual(l.topics,['0x'+keccak256('CheckpointCommitted(bytes32,uint64,bytes32,bytes32,bytes32,uint8,uint64,uint64)'),m.instanceId,'0x'+word(1)]);
assert.equal(l.data,'0x'+[s.checkpointRoot.slice(2),s.machineStateRoot.slice(2),s.vfsStateRoot.slice(2),word(s.lifecycle),word(s.totalJvmSteps),word(s.totalInternalSteps)].join(''));
let i=0;for(let n=0;n<m.decoders.length;n++){for(let offset=0;offset<m.classSizes[n];offset+=4096){const x=r.resourceReadReceipts[i++],want=Math.min(4096,m.classSizes[n]-offset);assert.equal(x.To.toLowerCase(),m.decoders[n]);assert.equal(x.Offset,offset);assert.equal(x.Requested,want);assert.equal(x.Returned,want);assert(x.Success);}}assert.equal(i,r.resourceReadReceipts.length);
const hs=Object.fromEntries(Object.entries(r.resourceHashes).map(([k,v])=>[k.toLowerCase(),v]));assert.equal(hs[m.decoders[0]],'246e7916fde4261e776c4beb17c5b7e84a80948c5ce60abf1e8011ca88288b0f');assert.equal(hs[m.decoders[6]],'50f32a2e94cccb7d7e6e2c2898e3b116e4026b47eed5710056a1b09c0199ba45');
console.log(JSON.stringify({ok:true,originalClassBytes:m.totalClassBytes,actualReadFragments:i,gas:r.gasUsed,checkpointBytes:cp.length,checkpointSHA256:r.checkpointSHA256,checkpointRoot:s.checkpointRoot,javaSteps:s.totalJvmSteps,scope:'successful original-entry initialization step, not main-body/Done'},null,2));
