#!/usr/bin/env python3
"""Parent generated collection+prior-blocker q1/q7/direct/reopen and refusals."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,zipfile
here=Path(__file__).resolve().parent;root=here.parents[3];cand=here.parent/'linked-hash-set-preflight';build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();classes=out/'classes';classes.mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def call(label,args,e=None):
 with (out/(label+'.log')).open('w') as f:p=subprocess.Popen(list(map(str,args)),cwd=root,env=e or env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
call('java8-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',classes,here/'ParentLinkedHashSetProbe.java',here/'ParentLinkedHashSetHostOracle.java']);call('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',classes,'ParentLinkedHashSetHostOracle'])
def jar(name,base,names):
 p=out/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(base/n).read_bytes())
 return p
names=['ParentLinkedHashSetProbe.class','ParentLinkedHashSetProbe$Equal.class','ParentLinkedHashSetProbe$Old.class','ParentLinkedHashSetProbe$New.class','ParentLinkedHashSetProbe$StringAction.class'];z=jar('parent-linked-hash-set.zip',classes,names);spec=importlib.util.spec_from_file_location('d',cand/'checkpoint_frames.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);baseline=None;rows={}
for q in (1,7,4096):
 label='q'+str(q);w=out/label;e=dict(env,MC_ENTRY_BINDINGS=','.join(names));args=[w,build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',z,q]
 for suffix,mode in (('start','setup-chain'),('finish','finish'),('reopen','verify')):call(label+'-'+suffix,[build/'driver',mode,*args],e)
 h=json.loads((w/'durable-head.json').read_text());assert h['lifecycle']==h['outcome']==2;cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();diag=d.inspect(cp);(w/'checkpoint-diagnostic.json').write_text(json.dumps(diag,indent=2)+'\n');vals=next(x['staticValues'] for x in diag['initialization'] if x['classIndex']==0);assert (int(vals[-1]['packedValue'],16)&((1<<64)-1))==733
 current=(h['machineRoot'],cp[280:]);
 if baseline is None:baseline=current
 else:assert current==baseline
 rows[label]={'epoch':h['epoch'],'jvmSteps':h['jvmSteps'],'internalSteps':h['internalSteps'],'machineRoot':h['machineRoot'],'opaqueSHA256':hashlib.sha256(cp[280:]).hexdigest()}
# Exact reservation for all nine owned names.
for source in sorted((cand/'fixtures/replacements/java/util').glob('*.java')):
 name=source.stem;cd=out/('replacement-'+name);cd.mkdir();call('replace-build-'+name,['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',cd,cand/'fixtures/ReservedCollectionReplacementMain.java',source]);rz=jar('replacement-'+name+'.zip',cd,['ReservedCollectionReplacementMain.class','java/util/'+name+'.class']);e=dict(env,MC_ENTRY_BINDINGS='ReservedCollectionReplacementMain.class,java/util/'+name+'.class');call('replace-start-'+name,[build/'driver','setup-chain',out/('replacement-world-'+name),build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',rz,4096],e);r=json.loads((out/'reports'/('replacement-world-'+name)/'start-refusal.json').read_text());assert r['selector']=='0x6a23ad80' and r['uint256Words']==['1','1'] and r['rootBefore']==r['rootAfter']
# remove remains genuinely absent.
cd=out/'remove';cd.mkdir();call('remove-build',['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-bootclasspath','/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar','-d',cd,cand/'fixtures/UnsupportedRemoveProbe.java']);rz=jar('remove.zip',cd,['UnsupportedRemoveProbe.class']);e=dict(env,MC_ENTRY_BINDINGS='UnsupportedRemoveProbe.class');call('remove-start',[build/'driver','setup-chain',out/'remove-world',build/'coordinator/MCEntryCoordinator.json',build/'engine/MCEntryInterpreter.json',rz,4096],e);r=json.loads((out/'reports/remove-world/start-refusal.json').read_text());assert r['selector']=='0xd631c3a4' and r['uint256Words']==['3','8'] and r['rootBefore']==r['rootAfter'];rows['unsupportedRemove']=r
call('canonical',['node',cand/'verify_receipts.js',build,out,1,'q1','q7','q4096']);(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
