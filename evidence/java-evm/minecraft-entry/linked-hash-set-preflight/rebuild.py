#!/usr/bin/env python3
"""Build only the candidate from generated trusted collection sources."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path(sys.argv[1]).resolve()
assert out.parent==root/'build' and out.name.startswith('java-diff-mc-linked-hash-set-') and not out.exists()
out.mkdir(); (out/'tmp').mkdir(); env=dict(os.environ, TMPDIR=str(out/'tmp'), NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules', PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
    with (out/(label+'.log')).open('w') as f: subprocess.run(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
classes=out/'bootstrap-classes';classes.mkdir()
boot=here/'source/bootstrap'
run('bootstrap-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,*sorted(boot.rglob('*.java'))])
images={x.stem:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((classes/'java/util').glob('*.class'))}
assert set(images)=={'Iterator','Collection','Set','AbstractCollection','AbstractSet','HashSet','LinkedHashSet','HashSetIterator','NoSuchElementException'}
engine=out/'engine';coordinator=out/'coordinator';shutil.copytree(here/'source/engine',engine);shutil.copytree(here/'source/coordinator',coordinator)
run('engine-build',['node',engine/'build.js']); run('coordinator-build',['node',coordinator/'build.js'])
ea=json.loads((engine/'MCEntryInterpreter.json').read_text()); ca=json.loads((coordinator/'MCEntryCoordinator.json').read_text()); size=len(ea['deployedBytecode'])//2
assert 327680 < size <= 393216, size
assert 'MC-LINKED-HASH-SET-PREFLIGHT1' in (engine/'MCEntryInterpreter.sol').read_text()
d=(here/'tools-driver.go.txt').read_text(); (out/'main.go').write_text(d)
run('gofmt',['gofmt','-w',out/'main.go']);run('go-build',['go','build','-trimpath','-o',out/'driver',out/'main.go']);run('go-vet',['go','vet',out/'main.go'])
pins={'basis':'48cd1693560677cd97c9aacc6604fd414c0baace','domain':'MC-LINKED-HASH-SET-PREFLIGHT1','address':'0x4d432d4c48532d505245464c4947485431000001','owner':'0x4d432d4c48532d505245464c4f574e4552000002','runtimeCap':393216,'engine':{'bytes':size,**ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode'])//2,**ca['codeHashes']},'bootstrapSHA256':images,'externalLocalGas':1000000000,'reserve':25000000,'maxFrames':128}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print(json.dumps(pins,indent=2))
