#!/usr/bin/env python3
"""Parent loadClass build; preserve frontier publication and map mirror quota to guest OOM."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];cand=here.parent/'classloader-loadclass-preflight';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-classloader-loadclass-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();(out/'bootstrap-classes').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args,check=True):
 with (out/(label+'.log')).open('w') as f:p=subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if check:assert p.returncode==0,(label,p.returncode)
 return p.returncode
run('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',out/'bootstrap-classes',cand/'bootstrap/java/lang/ClassLoader.java']);loader=(out/'bootstrap-classes/java/lang/ClassLoader.class').read_bytes();assert len(loader)==777 and hashlib.sha256(loader).hexdigest()=='2642b16dc68706079058f50f2b08544328c495a23217740499d4bb897ae69e3d';run('javap',['/usr/lib/jvm/java-8-openjdk/bin/javap','-classpath',out/'bootstrap-classes','-c','-p','-s','java.lang.ClassLoader'])
s=(cand/'engine/MCEntryInterpreter.sol').read_text();assert s.count('MC-CLASSLOADER-LOADCLASS1')==9 and 'nextHandle = arena.nextHandle;' in s
# Parent correction: shared allocator's quota signal is Java OOM, as on ldc, not a control-state revert.
old='''                        uint256 mirror = _loadClassByBinaryName(
                            arena, classes, _payload(f.stack[base]), rawClassCount,
                            loaderClass, parentLinks, hierarchyState, opPC
                        );
                        // Lookup can intern the binary name and create the first''';new='''                        (uint256 mirror, bool oom) = _loadClassByBinaryName(
                            arena, classes, _payload(f.stack[base]), rawClassCount,
                            loaderClass, parentLinks, hierarchyState, opPC
                        );
                        if (oom) {
                            f.sp = base;
                            nextHandle = _raiseJava(
                                7, opPC, arena, classes, objectHeap, heapKinds,
                                heapClasses, arrayLeafTypes, parentLinks,
                                hierarchyState, nextHandle
                            );
                            continue;
                        }
                        // Lookup can intern the binary name and create the first''';assert s.count(old)==1;s=s.replace(old,new)
old=''') private pure returns (uint256 mirror) {
        uint64[] memory wanted = _stringUnits(arena, stringRef, pc);''';new=''') private pure returns (uint256 mirror, bool oom) {
        uint64[] memory wanted = _stringUnits(arena, stringRef, pc);''';assert s.count(old)==1;s=s.replace(old,new);old='''        bool oom;
        (mirror, oom) = _classMirrorForTarget(
            arena, classes, target, rawClassCount, loaderClass, parentLinks, hierarchyState, pc
        );
        if (oom) revert LC0StateError(7, pc);''';new='''        return _classMirrorForTarget(
            arena, classes, target, rawClassCount, loaderClass, parentLinks, hierarchyState, pc
        );''';assert s.count(old)==1;s=s.replace(old,new);s=s.replace('MC-CLASSLOADER-LOADCLASS1','MC-CLASSLOADER-LOADCLASS-PARENT1')
engine=out/'engine';shutil.copytree(cand/'engine',engine);(engine/'MCEntryInterpreter.sol').write_text(s);run('engine-build',['node',engine/'build.js']);ea=json.loads((engine/'MCEntryInterpreter.json').read_text());size=len(ea['deployedBytecode'])//2;assert 352122<size<=393216
co=out/'coordinator';shutil.copytree(cand/'coordinator',co);p=co/'MCEntryCoordinator.sol';x=p.read_text();assert x.count('MC-CLASSLOADER-LOADCLASS1')==3;x=x.replace('MC-CLASSLOADER-LOADCLASS1','MC-CLASSLOADER-LOADCLASS-PARENT1');x,n=re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"4d432d4c4f4144434c4153532d504152454e5401"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"'+ea['codeHashes']['runtimeKeccak256']+'";',x);assert n==1;p.write_text(x);run('coordinator-build',['node',co/'build.js']);ca=json.loads((co/'MCEntryCoordinator.json').read_text());wp=json.loads((cand/'pins.json').read_text());d=(cand/'tools/driver.go.txt').read_text()
for a,b in [('MC-CLASSLOADER-LOADCLASS1','MC-CLASSLOADER-LOADCLASS-PARENT1'),(wp['engine']['runtimeSHA256'],ea['codeHashes']['runtimeSHA256']),(wp['engine']['runtimeKeccak256'],ea['codeHashes']['runtimeKeccak256']),(wp['coordinator']['runtimeKeccak256'],ca['codeHashes']['runtimeKeccak256']),(str(wp['engine']['bytes']),str(size)),('0x4d432d434c4f4144434c415353504152454e5401','0x4d432d4c4f4144434c4153532d504152454e5401'),('0x4d432d434f4144434c4153534f574e4552000002','0x4d432d4c4f4144434c4153532d4f574e45520002'),('0x4d432d434f4144434c4153534f54484552000003','0x4d432d4c4f4144434c4153532d4f544845520003')]:assert a in d,a;d=d.replace(a,b)
(out/'main.go').write_text(d)
for label,args in (('gofmt',['gofmt','-w',out/'main.go']),('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']),('go-vet',['go','vet',out/'main.go'])):run(label,args)
result={'basis':'e078bb2c6','parentRepair':'map shared class-mirror quota signal to existing guest OOM kind7; retain worker frontier/heap publication','domain':'MC-CLASSLOADER-LOADCLASS-PARENT1','address':'0x4d432d4c4f4144434c4153532d504152454e5401','owner':'0x4d432d4c4f4144434c4153532d4f574e45520002','runtimeCap':393216,'accepted320Unchanged':True,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'ClassLoader':{'bytes':len(loader),'sha256':hashlib.sha256(loader).hexdigest()},'bootstrapCount':66,'nativeBindings':8,'externalLocalGas':1000000000,'resourceLookupGas':1000000,'reserve':25000000,'maxFrames':128,'rawLimits':[24,262144]};(out/'pins.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
