#!/usr/bin/env python3
"""Archive a fresh isolated Java BigInteger Q120 cross-check without overwriting."""
from pathlib import Path
import hashlib, json, shutil, sys
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
assert len(sys.argv)==2
run=Path(sys.argv[1]).resolve(); assert run.parent==root/'build' and run.name.startswith('java-diff-mc-math-asin-q120-java-check-')
oracle=root/'evidence/java-evm/minecraft-entry/math-asin-independent-oracle'
source=oracle/'src/Q120AsinProbe.java'; samples=oracle/'results/samples.tsv'
dest=stage/'results/independent-java-q120-v1'; assert not dest.exists()
for name in ('summary.json','mismatches.tsv','run-summary.txt'): assert (run/name).is_file()
assert (run/'summary.json').read_bytes()==(oracle/'results/q120-summary.json').read_bytes()
assert (run/'mismatches.tsv').read_bytes()==(oracle/'results/mismatches.tsv').read_bytes()
summary=json.loads((run/'summary.json').read_text())
assert summary['supported_inputs']==17066 and summary['refused_controls']==11
assert summary['double_raw_mismatches']==472 and summary['float_cast_raw_mismatches']==0
assert summary['sqrt_floor_random_checks']==4096 and summary['q120_to_binary64_nearest_checks']==4110
assert summary['signed_256_bound']=='every observed absolute intermediate < 2^255'
dest.mkdir()
for name in ('summary.json','mismatches.tsv','run-summary.txt'): shutil.copyfile(run/name,dest/name)
provenance={'role':'TEST-ONLY Java BigInteger numerical cross-check; no guest execution authority','source':'evidence/java-evm/minecraft-entry/math-asin-independent-oracle/src/Q120AsinProbe.java','sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'oracleSamples':'evidence/java-evm/minecraft-entry/math-asin-independent-oracle/results/samples.tsv','oracleSamplesSHA256':hashlib.sha256(samples.read_bytes()).hexdigest(),'jdk8Environment':(oracle/'results/jdk8-environment.txt').read_text(),'reproducedExistingOracleOutputsByteForByte':True,'commands':['/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -encoding UTF-8 -d <fresh-build-dir>/classes '+str(source.relative_to(root)),'/usr/lib/jvm/java-8-openjdk/bin/java -cp <fresh-build-dir>/classes Q120AsinProbe '+str(samples.relative_to(root))+' <fresh-build-dir>/mismatches.tsv <fresh-build-dir>/summary.json'],'summary':summary}
(dest/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(p for p in dest.rglob('*') if p.is_file())
(dest/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(dest).as_posix()+'\n' for p in files))
results=stage/'results'; paths=sorted(p for p in results.rglob('*') if p.is_file() and p!=results/'SHA256SUMS')
(results/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(results).as_posix()+'\n' for p in paths))
print(json.dumps({'archive':str(dest),'summarySHA256':sha(dest/'summary.json'),'files':len(files),'resultsSHA256SUMS':str(results/'SHA256SUMS')},indent=2))
