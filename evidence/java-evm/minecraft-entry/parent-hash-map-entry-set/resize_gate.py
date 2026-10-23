#!/usr/bin/env python3
"""Generated-only independent resize view test, finite measured budgets."""
from pathlib import Path
import json,hashlib,os,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-entry-set-build-parent-p47-v2';O=ROOT/'build/java-diff-mc-entry-set-resize-parent-p47-v2';assert not O.exists();O.mkdir();C=O/'classes';C.mkdir();D=O/'driver-src';shutil.copytree(ROOT/'build/java-diff-mc-entry-set-generated-parent-p47/driver-src',D);env=dict(os.environ,GOPROXY='off',GOSUMDB='off');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 row={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(row,indent=2)+'\n');rows.append(row);return row
assert run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,H/'ParentEntrySetSmoke.java',H/'ParentEntrySetResize.java'])['exit']==0
assert run('java8-oracle',['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',C,'ParentEntrySetResize'])['exit']==0
bundle=O/'bundles/ParentEntrySetResize';bundle.mkdir(parents=True);rs=[]
for i,p in enumerate([C/'ParentEntrySetResize.class',C/'ParentEntrySetSmoke.class',C/'ParentEntrySetSmoke$Key.class']):
 data=p.read_bytes();name=f'{i:03d}.class';(bundle/name).write_bytes(data);rs.append({'index':i,'binaryName':p.stem,'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
case={'entryClass':'ParentEntrySetResize','rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs};(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':{'ParentEntrySetResize':case}},indent=2)+'\n')
p=D/'parent_gate.go';s=p.read_text().replace('fixture:="ParentEntrySetSmoke";quanta:=[]uint64{7,1}','fixture:="ParentEntrySetResize";quanta:=[]uint64{4096,65536}').replace('fixture="ParentEntrySetWide"','fixture="ParentEntrySetResize"');p.write_text(s);assert run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))])['exit']==0
for attempt in range(1,7):
 gas=1000000000*(2**(attempt-1));report=O/f'parent-resize-attempt-{attempt}';args=[O/'driver','parent-small',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,report,str(gas)];row=run(f'parent-resize-attempt-{attempt}',args);row['gasBudget']=gas
 if row['exit']==0:
  assert run('reopen',[args[0],'reopen',*args[2:]])['exit']==0;break
 assert json.load(open(report/'gate-failure.json'))['failure']['classification']=='test-only-gas-budget'
else:raise AssertionError('finite retries exhausted')
(O/'summary.json').write_text(json.dumps({'status':'PASS','generatedOnly':True,'stockJava8Oracle':True,'runs':rows,'successfulAttempt':attempt,'successfulGasBudget':gas},indent=2)+'\n');print(json.dumps({'status':'PASS','attempt':attempt,'gasBudget':gas,'rows':rows},indent=2))
