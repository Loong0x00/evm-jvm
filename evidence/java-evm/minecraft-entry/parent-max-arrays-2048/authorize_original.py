#!/usr/bin/env python3
"""Build separate gas-only LOCAL uint64-max original replay driver; retain canonical1B."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
build,out=map(lambda s:Path(s).resolve(),sys.argv[1:3]);assert build.parent==out.parent==ROOT/'build' and not out.exists()
s=(build/'main.go').read_text();old='const ordinaryGas = uint64(1_000_000_000)';new='const ordinaryGas = ^uint64(0)';assert s.count(old)==1
changes=[(old,new),('"LOCAL1B-USER-AUTHORIZED"','"LOCAL-U64MAX-USER-AUTHORIZED"'),('if smaller > budget {\n\t\t\t\tpanic("not a smaller slice")','if smaller > 4096 {\n\t\t\t\tpanic("slice exceeds engine bound")'),('case "resume-one-q1":\n\t\tdoResumeBudget(os.Args[2], os.Args[3], true, 1)','case "resume-one-q1":\n\t\tdoResumeBudget(os.Args[2], os.Args[3], true, 1)\n\tcase "resume-one-qn":\n\t\tdoResumeBudget(os.Args[2], os.Args[3], true, q)')]
for a,b in changes:
 assert s.count(a)==(2 if a=='"LOCAL1B-USER-AUTHORIZED"' else 1),(a,s.count(a));s=s.replace(a,b)
assert 'return 30 * time.Second' in s
out.mkdir()
for d in ('engine','coordinator'):shutil.copytree(build/d,out/d)
shutil.copy2(build/'pins.json',out/'pins.json');(out/'main.go').write_text(s)
env=dict(os.environ,GOPROXY='off',GOSUMDB='off')
for args in (['gofmt','-w',out/'main.go'],['go','build','-trimpath','-o',out/'driver',out/'main.go'],['go','vet',out/'main.go']):subprocess.run(list(map(str,args)),cwd=ROOT,env=env,check=True)
# A normalization proof: no driver logic other than authorized budget/CLI changes.
t=(out/'main.go').read_text()
for a,b in reversed(changes):
 assert t.count(b)==(2 if a=='"LOCAL1B-USER-AUTHORIZED"' else 1);t=t.replace(b,a)
assert t==(build/'main.go').read_text()
a={'gas':'18446744073709551615','scope':'LOCAL unchanged-original-only, never generated gates','watchdogSeconds':30,'maxJvmQuantum':4096,'canonicalSourceSHA256':hashlib.sha256((build/'main.go').read_bytes()).hexdigest(),'authorizedSourceSHA256':hashlib.sha256((out/'main.go').read_bytes()).hexdigest(),'driverNormalizedExact':True,'engineRuntimeSHA256':json.load(open(build/'pins.json'))['engine']['runtimeSHA256']}
(out/'authorization.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps(a,indent=2))
