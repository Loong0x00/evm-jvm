#!/usr/bin/env python3
"""Generated-only constructor/access and raw-owner refusal controls. No EnumMap data object fabricated."""
from pathlib import Path
import json,hashlib,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-enum-map-link-build-parent-p58-002';G=ROOT/'build/java-diff-mc-enum-map-link-generated-parent-p58';O=ROOT/'build/java-diff-mc-enum-map-link-refusals-parent-p58-002';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
sources=[];probes={'Class':'new EnumMap((Class)null);','Map':'new EnumMap((Map)null);','Copy':'new EnumMap((EnumMap)null);'}
for suffix,body in probes.items():
 name='ParentEnumCtor'+suffix;p=O/(name+'.java');p.write_text('import java.util.*;public class '+name+'{public static void main(String[]a){'+body+'}}\n');sources.append(p)
run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources]);sets=[];expect={}
for suffix in probes:
 name='ParentEnumCtor'+suffix;sets.append((name,name,[(name,(C/(name+'.class')).read_bytes())]));expect[name]=('CallError','3')
# Mutation applies only to the generated test class, never any original payload.
b=(C/'ParentEnumCtorClass.class').read_bytes();needle=b'(Ljava/lang/Class;)V';assert b.count(needle)==1;b=b.replace(len(needle).to_bytes(2,'big')+needle,bytes.fromhex('0003')+b'()V');b,n=re.subn(bytes.fromhex('5901c0')+b'..'+bytes.fromhex('b7'),bytes.fromhex('5900000000b7'),b);assert n==1;sets.append(('private-noarg','ParentEnumCtorClass',[('ParentEnumCtorClass',b)]));expect['private-noarg']=('CallError','4')
sol=(B/'engine/MCEntryInterpreter.sol').read_text();data=bytes.fromhex(re.search(r'function _bootstrapEnumMap\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',sol)[1]);sets.append(('raw-EnumMap','ParentEnumCtorClass',[('ParentEnumCtorClass',(C/'ParentEnumCtorClass.class').read_bytes()),('java/util/EnumMap',data)]));expect['raw-EnumMap']=('BootstrapProfileError','1');cases={}
for name,entry,items in sets:
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,(binary,data)in enumerate(items):
  fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text().replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals" {\n if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-matrix" {',1);p.write_text(s);lines=[]
for name,(error,code)in expect.items():lines.append('row,err=r.runRejection("'+name+'","'+name+'","'+error+'","'+code+'",maxJvm,maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)')
(D/'parent_refusals.go').write_text('package main\nimport("path/filepath")\nfunc(r *runner)parentRefusals()error{\nvar row controlReport;var err error\n'+'\n'.join(lines)+'\nr.report.Status="all public constructor overloads/private access/raw replacement atomically refused; no EnumMap data-instance claim";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)\n}\n');run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows,'dataAPIGuardsSourceAuditOnlyNoNonnullEnumMapInstanceAdmitted':True},indent=2)+'\n');print(json.dumps(rows,indent=2))
