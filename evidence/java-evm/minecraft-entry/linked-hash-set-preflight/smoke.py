#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent; root=here.parents[3]; build=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); assert not out.exists();out.mkdir();(out/'tmp').mkdir();classes=out/'classes';classes.mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules')
def call(label,args,e=env):
 with (out/(label+'.log')).open('w') as f:p=subprocess.Popen(list(map(str,args)),cwd=root,env=e,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,here/'fixtures/LinkedHashSetProbe.java',here/'fixtures/LinkedHashSetHostOracle.java'])
call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'LinkedHashSetHostOracle'])
z=out/'linked-hash-set.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
 x=zipfile.ZipInfo('LinkedHashSetProbe.class',(1980,1,1,0,0,0));x.compress_type=zipfile.ZIP_DEFLATED;f.writestr(x,(classes/'LinkedHashSetProbe.class').read_bytes())
 x=zipfile.ZipInfo('LinkedHashSetProbe$Equal.class',(1980,1,1,0,0,0));x.compress_type=zipfile.ZIP_DEFLATED;f.writestr(x,(classes/'LinkedHashSetProbe$Equal.class').read_bytes())
base=None; rows={}
for q in (1,7,4096):
 w=out/('q%d'%q); e=dict(env,MC_ENTRY_BINDINGS='LinkedHashSetProbe.class,LinkedHashSetProbe$Equal.class');args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
 for mode in ('setup-chain','finish','verify'):call('q%d-%s'%(q,mode),[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2,h
 cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();
 import importlib.util
 spec=importlib.util.spec_from_file_location('lhs_checkpoint',here/'checkpoint_frames.py'); d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d); diag=d.inspect(cp); (w/'checkpoint-diagnostic.json').write_text(json.dumps(diag,indent=2)+'\n'); values=next(x['staticValues'] for x in diag['initialization'] if x['classIndex']==0); assert int(values[-1]['packedValue'],16)&((1<<64)-1)==631,values
 current=(h['machineRoot'],cp[280:]);base=current if base is None else base;assert current==base
 rows['q%d'%q]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}
# Every owned bootstrap name rejects caller replacement before execution, including helper and interfaces.
rep=here/'fixtures/replacements'
for source in sorted((rep/'java/util').glob('*.java')):
    name=source.stem; d=out/('replacement-'+name); d.mkdir()
    call('replacement-build-'+name,['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',d,here/'fixtures/ReservedCollectionReplacementMain.java',source])
    rz=d/'replacement.zip'
    with zipfile.ZipFile(rz,'w',zipfile.ZIP_DEFLATED) as f:
        for n in ('ReservedCollectionReplacementMain.class','java/util/'+name+'.class'):
            x=zipfile.ZipInfo(n,(1980,1,1,0,0,0));x.compress_type=zipfile.ZIP_DEFLATED;f.writestr(x,(d/n).read_bytes())
    rw=out/('replacement-world-'+name); e=dict(env,MC_ENTRY_BINDINGS='ReservedCollectionReplacementMain.class,java/util/'+name+'.class')
    call('replacement-start-'+name,[build/'driver','setup-chain',rw,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',rz,4096],e)
    refusal=json.loads((out/'reports'/('replacement-world-'+name)/'start-refusal.json').read_text()); assert refusal['rootBefore']==refusal['rootAfter'],refusal
# A method outside the deliberately small collection surface reaches the interpreter's normal unsupported-member refusal.
d=out/'unsupported-remove';d.mkdir();call('unsupported-remove-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',d,here/'fixtures/UnsupportedRemoveProbe.java'])
rz=d/'remove.zip'
with zipfile.ZipFile(rz,'w',zipfile.ZIP_DEFLATED) as f:
    x=zipfile.ZipInfo('UnsupportedRemoveProbe.class',(1980,1,1,0,0,0));x.compress_type=zipfile.ZIP_DEFLATED;f.writestr(x,(d/'UnsupportedRemoveProbe.class').read_bytes())
e=dict(env,MC_ENTRY_BINDINGS='UnsupportedRemoveProbe.class');call('unsupported-remove-start',[build/'driver','setup-chain',out/'unsupported-remove-world',build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',rz,4096],e)
refusal=json.loads((out/'reports'/'unsupported-remove-world'/'start-refusal.json').read_text());assert refusal['rootBefore']==refusal['rootAfter'],refusal
rows['unsupportedRemove']=refusal
# q1 state is re-opened by the independent verify process above; canonical receipts verify all three worlds.
call('canonical',['node',here/'verify_receipts.js',build,out,1,'q1','q7','q4096'])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))
