#!/usr/bin/env python3
"""Parent candidate rebuild, quota repair, measured320 cap then LOCAL384 if needed."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'class-defining-loader-preflight';basis=here.parent/'parent-cc0c40e71';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-class-defining-loader-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args,check=True):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if check:assert p.returncode==0,(label,p.returncode)
 return p.returncode
# Rebuild all changed/new Java images from source.
classes=out/'bootstrap-classes';classes.mkdir();boot=src/'bootstrap/java/lang';run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,boot/'Class.java',boot/'ClassLoader.java',boot/'VMClassLoader.java'])
for n,want,size in [('Class','4e13134b8f82af8fb51b268f92fea91ccf3ed731b1adcb24eddc66b1889913bd',440),('ClassLoader','df3b18c48b514343c2dcf9d025afd714027e319db03174c8f831215645f39e8b',136),('VMClassLoader','936fc65d33d3b2f7d9c2267b8e62c42e58c8135b35d6e4d08f65daec831cf944',143)]:
 raw=(classes/('java/lang/'+n+'.class')).read_bytes();assert len(raw)==size and hashlib.sha256(raw).hexdigest()==want and raw==(src/('artifacts/bootstrap/java/lang/'+n+'.class')).read_bytes()
# Independently source-build exact worker candidate under original320 cap.
ce=out/'candidate-engine';shutil.copytree(src/'artifacts/engine',ce);run('candidate-engine-build',['node',ce/'build.js']);candidate=json.loads((ce/'MCEntryInterpreter.json').read_text());assert candidate==json.loads((src/'artifacts/engine/MCEntryInterpreter.json').read_text()) and len(candidate['deployedBytecode'])//2==327658
# Restore unrelated formatting of unchanged class-name decoder, then fix the
# pool-hit quota hole: raw first mirror needs loader+mirror (2), not only1.
cs=(ce/'MCEntryInterpreter.sol').read_text();bs=(basis/'engine/MCEntryInterpreter.sol').read_text()
def function(text,name,nextname):
 a=text.index('    function '+name);b=text.index('    function '+nextname,a);return a,b,text[a:b]
a,b,oldfmt=function(bs,'_classNameUnits(','_classMirrorMatches(');x,y,_=function(cs,'_classNameUnits(','_classMirrorMatches(');cs=cs[:x]+oldfmt+cs[y:]
assert cs.count('MC-CLASS-DEFINING-LOADER-PREFLIGHT1')==9;cs=cs.replace('MC-CLASS-DEFINING-LOADER-PREFLIGHT1','MC-CLASS-DEFINING-LOADER-PARENT1')
old='''        uint256 fields = arena.classDefaults.length;
        bool needLoader = raw && loader == 0;
        if (arena.ordinaryObjectCount >= MAX_OBJECTS || fields > MAX_OBJECT_FIELDS || fields > MAX_OBJECT_FIELD_SLOTS - arena.ordinaryFieldSlots || arena.nextHandle >= MAX_HANDLES) return (0, true);
        (uint256 nameRef, bool stringOOM) = _internStringUnits(arena, classes, name, parentLinks, hierarchyState, needLoader ? 2 : 1, fields);'''
new='''        uint256 fields = arena.classDefaults.length;
        bool needLoader = raw && loader == 0;
        uint256 reserveObjects = needLoader ? 2 : 1;
        if (arena.ordinaryObjectCount > MAX_OBJECTS - reserveObjects
            || fields > MAX_OBJECT_FIELDS
            || fields > MAX_OBJECT_FIELD_SLOTS - arena.ordinaryFieldSlots
            || arena.nextHandle > MAX_HANDLES - reserveObjects) return (0, true);
        (uint256 nameRef, bool stringOOM) = _internStringUnits(
            arena, classes, name, parentLinks, hierarchyState, reserveObjects, fields
        );'''
assert cs.count(old)==1;cs=cs.replace(old,new)
# The appended VM-owned subtype must be non-overridable just like ClassLoader.
old='''    function _isReservedClassLoaderClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/ClassLoader"));
    }'''
new='''    function _isReservedClassLoaderClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/ClassLoader"))
            || _isNamedClass(c, bytes("java/lang/VMClassLoader"));
    }'''
assert cs.count(old)==1;cs=cs.replace(old,new)
repair320=out/'repair320-engine';shutil.copytree(src/'artifacts/engine',repair320);(repair320/'MCEntryInterpreter.sol').write_text(cs);rc=run('repair-320-cap',['node',repair320/'build.js'],False)
# A pass stays320. A failure is retained, then same source is compiled under a
# separately labelled LOCAL384 build guard, never an accepted-cap amendment.
if rc==0:
 final=repair320;cap=327680;capResult='pass'
else:
 log=(out/'repair-320-cap.log').read_text();assert 'runtime >320KiB' in log
 final=out/'repair384-engine';shutil.copytree(repair320,final);p=final/'build.js';s=p.read_text();assert s.count('>320*1024')==1;p.write_text(s.replace('>320*1024','>384*1024'))
 run('repair-384-build',['node',final/'build.js']);cap=393216;capResult='failed-preserved-then-LOCAL384'
ea=json.loads((final/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert size<=cap and (rc==0 or size>327680)
# New coordinator/pins for repaired source.
co=out/'coordinator';shutil.copytree(src/'artifacts/coordinator',co);s=(co/'MCEntryCoordinator.sol').read_text().replace('MC-CLASS-DEFINING-LOADER-PREFLIGHT1','MC-CLASS-DEFINING-LOADER-PARENT1').replace('d611ea952478718292318848a363cbe828f3fb2f91da54241bc9c7885a8e8a94',ea['codeHashes']['runtimeKeccak256']);s,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d4445464c4f414445522d504152454e5401"));',s);assert n==1;(co/'MCEntryCoordinator.sol').write_text(s);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text())
# Parent-verified authorized1B driver, not worker generated report tooling.
driver=(basis/'executed_driver.go.txt').read_text()
for a,b in [('MC-THREAD-CONTEXT-PREFLIGHT1','MC-CLASS-DEFINING-LOADER-PARENT1'),('d11b3725ba5151fbfc12011a5df87741cd3c80114eaafb1e056157736b8ea86c',ea['codeHashes']['runtimeSHA256']),('ca811ec4bf1be44d6a8a6469d38543cb8ba89b21c93589ba07338c1ed5b7f0df',ea['codeHashes']['runtimeKeccak256']),('7c16213411499ea7fd34fc4da229122e244bbf937a8d76a3e1ef96bddc01852a',ca['codeHashes']['runtimeKeccak256']),('326052',str(size)),('0x4d432d5448524541442d434f4e544558542d3031','0x4d432d4445464c4f414445522d504152454e5401'),('0x4d432d5448524541442d4354582d4f574e455202','0x4d432d4445464c4f41442d4f574e455200000002'),('0x4d432d5448524541442d4354582d4f5448455203','0x4d432d4445464c4f41442d4f5448455200000003')]:assert a in driver,a;driver=driver.replace(a,b)
# Use final artifacts at conventional paths.
shutil.copytree(final,out/'engine');(out/'main.go').write_text(driver)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
pins={'address':'0x4d432d4445464c4f414445522d504152454e5401','owner':'0x4d432d4445464c4f41442d4f574e455200000002','domain':'MC-CLASS-DEFINING-LOADER-PARENT1','candidate320Bytes':327658,'repair320Result':capResult,'runtimeCap':cap,'ClassSHA256':'4e13134b8f82af8fb51b268f92fea91ccf3ed731b1adcb24eddc66b1889913bd','VMClassLoaderSHA256':'936fc65d33d3b2f7d9c2267b8e62c42e58c8135b35d6e4d08f65daec831cf944','engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print((out/'pins.json').read_text())
