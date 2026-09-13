#!/usr/bin/env python3
"""Parent exact system-loader native build: enforce320 failure then LOCAL384."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'system-classloader-preflight';basis=here.parent/'parent-102911980';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-system-classloader-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args,check=True):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if check:assert p.returncode==0,(label,p.returncode)
 return p.returncode
classes=out/'bootstrap-classes';classes.mkdir();source=src/'bootstrap/java/lang/ClassLoader.java';run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,source]);image=(classes/'java/lang/ClassLoader.class').read_bytes();assert len(image)==195 and hashlib.sha256(image).hexdigest()=='9a2d38f5b25e30aee6f0b494d23bba28aeb686ea8e338a21616b8ac6a6118f86'
# Preserve semantic source, restore unrelated decoder formatting, isolate all domains.
s=(src/'source/engine/MCEntryInterpreter.sol').read_text();bs=(basis/'engine/MCEntryInterpreter.sol').read_text()
def fn(t,a,b):x=t.index('    function '+a);y=t.index('    function '+b,x);return x,y,t[x:y]
x,y,orig=fn(bs,'_classNameUnits(','_classMirrorMatches(');a,b,_=fn(s,'_classNameUnits(','_classMirrorMatches(');s=s[:a]+orig+s[b:]
assert s.count('MC-SYSTEM-CLASSLOADER-PREFLIGHT1')==9;s=s.replace('MC-SYSTEM-CLASSLOADER-PREFLIGHT1','MC-SYSTEM-CLASSLOADER-PARENT1')
# Exact native surface and prior semantics guards.
assert s.count('return 6;')==1 and 'binding == 6 && (uint16(meta) != 0x0109' in s and 'f.sp = _push(f.stack, base, _packRef(uint32(loader)), opPC);' in s and 'if (malformed || loader == 0) revert LC0StateError(7, 0);' in s
eng320=out/'engine320';shutil.copytree(src/'source/engine',eng320);(eng320/'MCEntryInterpreter.sol').write_text(s);rc=run('engine-320-cap',['node',eng320/'build.js'],False);assert rc!=0 and 'runtime >320KiB' in (out/'engine-320-cap.log').read_text()
engine=out/'engine';shutil.copytree(eng320,engine);p=engine/'build.js';x=p.read_text();assert x.count('>320*1024')==1;p.write_text(x.replace('>320*1024','>384*1024'));run('engine-384-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert 327680<size<=393216
co=out/'coordinator';shutil.copytree(src/'source/coordinator',co);x=(co/'MCEntryCoordinator.sol').read_text().replace('MC-SYSTEM-CLASSLOADER-PREFLIGHT1','MC-SYSTEM-CLASSLOADER-PARENT1').replace('dbbd4e3ec0d7346164b514671918ee8410b08947568977b34a1eec7663475211',ea['codeHashes']['runtimeKeccak256']);x,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d5359534c4f414445522d504152454e5401"));',x);assert n==1;(co/'MCEntryCoordinator.sol').write_text(x);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text())
driver=(basis/'executed_driver.go.txt').read_text()
for a,b in [('MC-CLASS-DEFINING-LOADER-PARENT1','MC-SYSTEM-CLASSLOADER-PARENT1'),('34150d673860288d41228bfcde5804cff60fc4d89c755c84eff1f179242b0bfd',ea['codeHashes']['runtimeSHA256']),('a34de6dbd33d3a4bdf323e61c9a2ce4d7abe8529d0b18eae2a5ae0874d628489',ea['codeHashes']['runtimeKeccak256']),('e308d1c42c8c34c764b872f377d041abca9995e2f00331731e8340d50db2f586',ca['codeHashes']['runtimeKeccak256']),('327266',str(size)),('0x4d432d4445464c4f414445522d504152454e5401','0x4d432d5359534c4f414445522d504152454e5401'),('0x4d432d4445464c4f41442d4f574e455200000002','0x4d432d5359534c4f41442d4f574e455200000002'),('0x4d432d4445464c4f41442d4f5448455200000003','0x4d432d5359534c4f41442d4f5448455200000003')]:assert a in driver,a;driver=driver.replace(a,b)
(out/'main.go').write_text(driver)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
pins={'address':'0x4d432d5359534c4f414445522d504152454e5401','owner':'0x4d432d5359534c4f41442d4f574e455200000002','domain':'MC-SYSTEM-CLASSLOADER-PARENT1','ClassLoaderSHA256':hashlib.sha256(image).hexdigest(),'cap320':'failed-preserved','runtimeCap':393216,'priorSemanticsPreserved':True,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print((out/'pins.json').read_text())
