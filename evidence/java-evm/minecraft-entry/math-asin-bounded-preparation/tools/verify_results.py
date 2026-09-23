#!/usr/bin/env python3
"""Verify archived generated-only asin EVM outputs, receipts, and hashes."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, zipfile
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
archive=stage/'results/generated-gate-v1'
read=lambda n:json.loads((archive/n).read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
pins=read('build-pins.json'); summary=read('gate-summary.json'); proof=read('proof.json')
source=read('source-invariants.json'); commitment=read('root-commitment.json'); base=read('baseline-pins.json')
manifest=read('manifest.json'); fixture_summary=read('fixtures/summary.json')
assert summary['profile']==proof['profile']==manifest['profile']=='MC-RANDOM-CLASS-P2-MATH-ASIN-BOUNDED-Q120'
assert summary['generatedOnly'] and pins['bootstrapCount']==proof['bootstrapCount']==97
assert pins['globalNativeBindings']==proof['globalNativeBindings']==20 and pins['stringLocalBinding']==proof['stringLocalBinding']==12
assert pins['rawLimits']==proof['rawLimits']==[71,471911] and pins['diagnosticClassBound']==proof['diagnosticClassBound']==168
assert pins['runtimeCap']==proof['runtimeCapBytes']==393216
assert pins['engine']['bytes']==summary['engineBytes']==proof['engineBytes']<=393216
assert summary['wholeGateSeconds']==manifest['gateSeconds']<=manifest['limitSeconds']==1200
assert summary['canonicalReceipts']['verifiedReceipts']==proof['canonicalReceipts']
assert pins['bootstrapRoot']==summary['bootstrapRoot']==proof['bootstrapRoot']==commitment['bootstrapRoot']==source['bootstrapRoot']
assert source['changedBootstrapIndices']==[89] and source['changedBootstrapImages']==['Math']
assert source['globalNativeBindings']==20 and source['stringLocalBinding']==12
assert source['rawLimits']==[71,471911] and source['mathImageBytes']==304
assert source['mathImageSHA256']==pins['math']['sha256'] and source['mathImageKeccak256']==pins['math']['keccak256']
assert source['previousMathImageSHA256']==base['baselineMathSHA256']
assert source['previousSourceDerivedRoot']==base['bootstrapRoot']
assert commitment['priorSourceDerivedRoot']==base['bootstrapRoot'] and commitment['changedIndices']==[89]
assert commitment['priorHistoricalP1PinRoot']=='7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887'
assert commitment['historicalP1PinMatchesSourceDerivedRoot'] is False
assert base['baselineMathSHA256']=='da512cb22203c78ff49b4e8ae13075081c60a89e79897cb65d5581a391adea60'
assert source['kernel']['seriesLastN']==128 and source['kernel']['sqrtRounds']==120
assert source['kernel']['externalMath'] is False and source['kernel']['lookupTable'] is False
assert proof['retainedSqrtQ1Q7Direct'] and proof['sparseQ1Q7Direct']
math_bytes=bytes.fromhex((archive/'bootstrap/Math.class.hex').read_text().strip())
assert len(math_bytes)==pins['math']['bytes']==304 and sha(math_bytes)==pins['math']['sha256']
assert (archive/'bootstrap/Math.sha256').read_text().strip()==sha(math_bytes)
assert (archive/'bootstrap/Math.java').read_bytes()==(stage/'bootstrap/java/lang/Math.java').read_bytes()
assert source['candidateEngineSourceSHA256']==manifest['candidateEngineSourceSHA256']
assert source['baselineEngineSourceSHA256']==manifest['baselineEngineSourceSHA256']
assert manifest['engineRuntimeSHA256']==pins['engine']['runtimeSHA256'] and manifest['engineRuntimeKeccak256']==pins['engine']['runtimeKeccak256']
engine=bytes.fromhex((archive/'artifacts/engine-runtime.hex').read_text().strip())
coordinator=bytes.fromhex((archive/'artifacts/coordinator-runtime.hex').read_text().strip())
assert len(engine)==pins['engine']['bytes'] and sha(engine)==pins['engine']['runtimeSHA256']
assert len(coordinator)==pins['coordinator']['bytes']==5394 and sha(coordinator)==pins['coordinator']['runtimeSHA256']
node='const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(x.map(v=>keccak256(Buffer.from(v,"hex")))));'
env={**os.environ,'NODE_PATH':str(root/'jvmevm/runtime/node_modules')}
keccaks=json.loads(subprocess.run(['node','-e',node],input=json.dumps([engine.hex(),coordinator.hex()]),cwd=root,env=env,text=True,capture_output=True,check=True).stdout)
assert keccaks==[pins['engine']['runtimeKeccak256'],pins['coordinator']['runtimeKeccak256']]
assert fixture_summary['generatedOnly']
for label,row in fixture_summary['fixtures'].items():
 bundle=archive/('fixtures/'+label+'.zip'); assert sha(bundle.read_bytes())==row['zipSHA256']
 with zipfile.ZipFile(bundle) as z:
  assert set(z.namelist())==set(row['entries'])
  for name,digest in row['classSHA256'].items(): assert sha(z.read(name))==digest and len(z.read(name))==row['classBytes'][name]
assert summary['q120TestOnlyModel']['supportedRows']==17066
assert summary['q120TestOnlyModel']['maxBinary64ULPDistanceFromJava8']==1
assert summary['q120TestOnlyModel']['binary64BitMismatchCount']==472
assert summary['q120TestOnlyModel']['floatCastBitMismatchCount']==0
assert summary['q120TestOnlyModel']['oracleSamplesSHA256']=='827279a72a83c80392da8dccd38bc94d3d1ff5f4e4cec4199cf228f5d60ca0e6'
# Exact checkpoint decoder inspects durable guest statics, not host program output.
spec=importlib.util.spec_from_file_location('verifyAsinCheckpoint',here/'checkpoint_diagnostic.py')
diagnostic=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostic)
MASK=(1<<64)-1
def ordered(x):return (~x&MASK) if x>>63 else x|(1<<63)
def check_math_world(label,quantum,kind):
 world='world-'+label+'-q'+str(quantum);head=read('heads/'+world+'.json');cp=(archive/'checkpoints'/(world+'.bin')).read_bytes()
 assert sha(cp)==head['checkpointSHA256'];decoded=diagnostic.inspect(cp)
 vectors=read('fixtures/'+label+'.json')[kind]; values={r['fieldIndex']:int(r['packedValue'],16) for r in decoded['initialization'][0]['staticValues']}; n=len(vectors)
 assert decoded['lifecycle']==head['lifecycle']==2 and len(values)==2*n+1
 for i,v in enumerate(vectors):
  got=values[i]&MASK;want=int(v['javaDoubleRaw'],16)
  assert abs(ordered(got)-ordered(want))<=1,(world,v['name'],hex(got),hex(want))
  assert values[n+i]&0xffffffff==int(v['javaFloatRaw'],16),(world,v['name'])
  if 'zero' in v['name']:assert got==want
  if v['name']=='one':assert got==0x3ff921fb54442d18
  if v['name']=='negative-one':assert got==0xbff921fb54442d18
 assert values[2*n]&0xffffffff==7
for label,key in (('math-asin-bounded-edges','asinVectors'),('math-sin-bounded-edges','sinVectors'),('math-sin-bounded-grid','sinVectors')):
 rows=summary['results'][label]; assert set(rows)=={'q1','q7','direct'};base_row=rows['q1']
 for quantum,k in ((1,'q1'),(7,'q7'),(4096,'direct')):
  row=rows[k]
  for field in ('machineRoot','opaquePayloadSHA256','jvmSteps','internalSteps','lifecycle','javaKind'):assert row[field]==base_row[field]
  assert row['world']=='world-'+label+'-q'+str(quantum)
  archived_head=read('heads/'+row['world']+'.json');assert archived_head['machineRoot']==row['machineRoot']
  check_math_world(label,quantum,key)
  recs=sorted((archive/'receipts'/row['world']).glob('slice-*.json'));assert len(recs)==archived_head['epoch']
  for rp in recs:
   r=json.loads(rp.read_text());assert r['gasUsed']>0 and r['elapsedMS']<=30000
   cps=list((archive/'checkpoints'/row['world']).glob(rp.stem+'-*.bin'));assert len(cps)==1
   blob=cps[0].read_bytes();assert sha(blob)==r['checkpointSHA256'] and len(blob)==r['checkpointBytes']
# Atomic unsupported Math.asin receipts preserve the last durable Head and publish no child checkpoint.
for label in ('math-asin-above-bound-refusal','math-asin-below-negative-bound-refusal','math-asin-nan-refusal','math-asin-positive-infinity-refusal','math-asin-negative-infinity-refusal'):
 for quantum,k in ((1,'q1'),(7,'q7'),(4096,'direct')):
  row=summary['results'][label][k];assert row['selector']=='0xe309722e' and row['uint256Words'][0]=='1' and row['rootUnchanged'] and row['checkpointBytes']==0
  head_name=label+'-q'+str(quantum)+'.json';head=read('heads/'+head_name);receipt=read('refusals/'+head_name)
  assert receipt['durableHeadUnchanged'] and receipt['durableHeadSHA256Before']==receipt['durableHeadSHA256After']
  assert sha((archive/'heads'/head_name).read_bytes())==receipt['durableHeadSHA256After']
# Old sparse encoding, malformed refusal, raw71/471911 and sqrt are retained evidence.
assert summary['results']['count-71']['q1']['machineRoot']==summary['results']['count-71']['q7']['machineRoot']
large=summary['results']['byte-471911']
assert large['allClassBytesRead'] and large['classification']=='EXPECTED_LOCAL1B_OUT_OF_GAS_NOT_CHECKPOINT_CAP_ACCEPTANCE'
assert large['localCeilingProbe']['selector']=='0x' and large['localCeilingProbe']['executionBudget']=='LOCAL1B-USER-AUTHORIZED'
assert summary['results']['byte-471912']['selector']=='0xab23ed08'
for name,row in summary['results']['sparse-malformed-refusals'].items():
 receipt=read('refusals/'+name+'.json');assert receipt['rootUnchanged'] and receipt['headUnchanged']
assert proof['canonicalReceipts']>0 and summary['canonicalReceipts']['verifiedReceipts']==proof['canonicalReceipts']
# Every archived file is hash-pinned; enforce exact no-overwrite manifest inventory.
for rel,digest in manifest['files'].items():assert sha((archive/rel).read_bytes())==digest,rel
checks=(archive/'SHA256SUMS').read_text().splitlines()
for line in checks:
 digest,rel=line.split('  ',1);assert sha((archive/rel).read_bytes())==digest,rel
# A fresh Java-8 BigInteger run independently replays the test-only numerical
# model and reproduces the original oracle summary/mismatch file byte-for-byte.
java_model=stage/'results/independent-java-q120-v1'; java_summary=json.loads((java_model/'summary.json').read_text())
java_provenance=json.loads((java_model/'provenance.json').read_text())
assert java_summary['supported_inputs']==17066 and java_summary['refused_controls']==11
assert java_summary['double_raw_mismatches']==472 and java_summary['float_cast_raw_mismatches']==0
assert java_summary['sqrt_floor_random_checks']==4096 and java_summary['q120_to_binary64_nearest_checks']==4110
assert java_provenance['reproducedExistingOracleOutputsByteForByte'] is True
assert java_provenance['oracleSamplesSHA256']==summary['q120TestOnlyModel']['oracleSamplesSHA256']
for line in (java_model/'SHA256SUMS').read_text().splitlines():
 digest,rel=line.split('  ',1);assert sha((java_model/rel).read_bytes())==digest,rel
for line in (stage/'results/SHA256SUMS').read_text().splitlines():
 digest,rel=line.split('  ',1);assert sha((stage/'results'/rel).read_bytes())==digest,rel
print(json.dumps({'result':'PASS','profile':summary['profile'],'engineBytes':len(engine),'bootstrapRoot':pins['bootstrapRoot'],'asinVectors':len(read('fixtures/math-asin-bounded-edges.json')['asinVectors']),'asinCanonicalReceipts':sum(len(list((archive/'receipts'/('world-math-asin-bounded-edges-q'+str(q))).glob('slice-*.json'))) for q in (1,7,4096)),'totalCanonicalReceipts':proof['canonicalReceipts'],'wholeGateSeconds':summary['wholeGateSeconds'],'manifestFiles':len(manifest['files']),'javaQ120SqrtChecks':java_summary['sqrt_floor_random_checks'],'javaQ120ConversionChecks':java_summary['q120_to_binary64_nearest_checks']},indent=2))
