#!/usr/bin/env python3
"""Generated-only overload, reserved-owner, call-kind, bounds and raw-owner negative controls."""
from pathlib import Path
import json,hashlib,os,re,shutil,subprocess,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=ROOT/'build/java-diff-mc-string-valueof-char-build-parent-p57';G=ROOT/'build/java-diff-mc-string-valueof-char-generated-parent-p57';O=ROOT/'build/java-diff-mc-string-valueof-char-refusals-parent-p57-002';assert not O.exists();O.mkdir();D=O/'driver-src';shutil.copytree(G/'driver-src',D);C=O/'classes';C.mkdir();env=dict(os.environ,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local');rows=[]
def run(label,args,timeout=1200):
 t=time.monotonic()
 with(O/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 r={'label':label,'exit':p.returncode,'wallSeconds':time.monotonic()-t,'command':list(map(str,args))};(O/(label+'-process.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);assert p.returncode==0,r
probes={'Int':'String.valueOf(7);','Long':'String.valueOf(7L);','Boolean':'String.valueOf(true);','Float':'String.valueOf(1.0f);','Double':'String.valueOf(1.0);','Object':'String.valueOf((Object)null);','Chars':'String.valueOf(new char[0]);','CharsRange':'String.valueOf(new char[1],0,1);','CopyChars':'String.copyValueOf(new char[0]);','Bounds':"String.valueOf('x').charAt(1);",'Virtual':"String.valueOf(',');"};sources=[]
for suffix,body in probes.items():
 name='ParentCharRefusal'+suffix;p=O/(name+'.java');p.write_text('public class '+name+' {public static void main(String[] args){'+body+'}}\n');sources.append(p)
run('javac',['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-source','8','-target','8','-d',C,*sources]);sets=[];expect={}
for suffix in probes:
 name='ParentCharRefusal'+suffix;data=(C/(name+'.class')).read_bytes()
 if suffix=='Virtual':
  assert data.count(bytes.fromhex('102cb8'))==1;data=data.replace(bytes.fromhex('102cb8'),bytes.fromhex('102cb6'))
 sets.append((name,name,[(name,data)]));expect[name]=('CallError','4')if suffix=='Virtual'else('StringProfileError','2'if suffix=='Bounds'else'1')
# These are generated fixture classfiles, never original class parsing/mutation.
base=(C/'ParentCharRefusalVirtual.class').read_bytes()
def cp_variant(owner=None,descriptor=None,interface=False):
 count=int.from_bytes(base[8:10],'big');at=10;parts=[];idx=1
 while idx<count:
  tag=base[at];at+=1
  if tag==1:
   n=int.from_bytes(base[at:at+2],'big');v=base[at+2:at+2+n];at+=2+n
   if owner and v==b'java/lang/String':v=owner.encode()
   if descriptor and v==b'(C)Ljava/lang/String;':v=descriptor.encode()
   parts.append(bytes([1])+len(v).to_bytes(2,'big')+v)
  else:
   n={3:4,4:4,5:8,6:8,7:2,8:2,9:4,10:4,11:4,12:4,15:3,16:2,18:4}[tag];v=base[at:at+n];at+=n
   # Only the static String reference: the constructor Object Methodref remains10.
   if interface and tag==10 and idx!=1:tag=11
   parts.append(bytes([tag])+v)
   if tag in(5,6):idx+=1
  idx+=1
 return base[:10]+b''.join(parts)+base[at:]
for suffix,data,error,code in [('BadDescriptor',cp_variant(descriptor='(X)Ljava/lang/String;'),'CallError','4'),('StringInterfaceRef',cp_variant(interface=True),'InterfaceError','1'),('ComparableStatic',cp_variant(owner='java/lang/Comparable',interface=True),'StringProfileError','1'),('CharSequenceStatic',cp_variant(owner='java/lang/CharSequence',interface=True),'StringProfileError','1')]:
 label='ParentChar'+suffix;sets.append((label,'ParentCharRefusalVirtual',[('ParentCharRefusalVirtual',data)]));expect[label]=(error,code)
sol=(B/'engine/MCEntryInterpreter.sol').read_text()
for method,binary in [('String','String'),('Comparable','Comparable'),('CharSequence','CharSequence')]:
 data=bytes.fromhex(re.search(r'function _bootstrap'+method+r'\(\) private pure returns \(bytes memory\)\s*\{\s*return hex"([0-9a-f]+)";',sol)[1]);label='raw-'+method;sets.append((label,'ParentCharRefusalInt',[('ParentCharRefusalInt',(C/'ParentCharRefusalInt.class').read_bytes()),('java/lang/'+binary,data)]));expect[label]=('BootstrapProfileError','1')
cases={}
for name,entry,items in sets:
 q=O/'bundles'/name;q.mkdir(parents=True);rs=[]
 for i,(binary,data)in enumerate(items):
  fn=f'{i:03d}.class';(q/fn).write_bytes(data);rs.append({'index':i,'binaryName':binary,'file':fn,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 cases[name]={'entryClass':entry,'rawCount':len(rs),'rawBytes':sum(r['bytes']for r in rs),'rawClasses':rs}
(O/'fixture-manifest.json').write_text(json.dumps({'generatedOnly':True,'cases':cases},indent=2)+'\n');p=D/'evm_driver.go';s=p.read_text().replace('if mode == "parent-small" || mode == "parent-matrix" {','if mode == "parent-refusals" {\n if err=r.parentRefusals();err!=nil{os.Exit(writeFailure(r,err))};return\n }\n if mode == "parent-small" || mode == "parent-matrix" {',1);p.write_text(s)
lines=[]
for name,(error,code)in expect.items():
 fn='runResumedRefusal'if name=='ParentCharRefusalBounds'else'runRejection';q='1'if name=='ParentCharRefusalBounds'else'maxJvm';lines.append('row,err=r.'+fn+'("'+name+'","'+name+'","'+error+'","'+code+'",'+q+',maxInternal);if err!=nil{return err};r.report.Controls=append(r.report.Controls,row)')
(D/'parent_refusals.go').write_text('package main\nimport("path/filepath")\nfunc(r *runner)parentRefusals()error{\nvar row controlReport;var err error\n'+'\n'.join(lines)+'\nr.report.Status="exact char-only permission and all preserved refusal precedences passed";return writeJSON(filepath.Join(r.reportDir,"parent-refusals-summary.json"),r.report)\n}\n');run('go-build',['go','build','-trimpath','-o',O/'driver','./'+str(D.relative_to(ROOT))],600);run('controls',[O/'driver','parent-refusals',B/'engine/MCEntryInterpreter.json',B/'coordinator/MCEntryCoordinator.json',O/'fixture-manifest.json',O,O/'controls','1000000000']);(O/'summary.json').write_text(json.dumps({'status':'PASS','gasBudget':1000000000,'runs':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
