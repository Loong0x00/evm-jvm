#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,zipfile
h=Path(__file__).resolve().parent;r=h.parents[3];b=Path(sys.argv[1]).resolve();o=Path(sys.argv[2]).resolve();assert b.parent==r/'build' and o.parent==r/'build' and not o.exists();o.mkdir();(o/'src').mkdir();(o/'classes').mkdir();(o/'tmp').mkdir();rows={};cmds=[]
def build(label,src,names,host=True):
 d=o/'src'/label;c=o/'classes'/label;d.mkdir();c.mkdir()
 for n,x in src.items():
  p=d/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(x)
 subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',c,*sorted(d.rglob('*.java'))],check=True)
 if host:subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',c,names[0][:-6]],check=True)
 z=o/(label+'.zip')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_STORED) as f:
  for n in names:i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_STORED;f.writestr(i,(c/n).read_bytes())
 (o/(label+'.json')).write_text(json.dumps({'entries':names,'sha256':hashlib.sha256(z.read_bytes()).hexdigest()},indent=2)+'\n');return z
positive=build('positive',{'EnumSetMain.java':'''import java.util.*; public final class EnumSetMain { static int result; public static void main(String[] x) { EnumSet<FocusLevel> s=FocusLevel.ALL; if(s.size()!=3)throw new Error(); Iterator<FocusLevel> i=s.iterator();int v=0;while(i.hasNext())v=v*10+i.next().ordinal();if(v!=12||i.hasNext())throw new Error();try{i.next();throw new Error();}catch(NoSuchElementException ok){result=7;}if(result!=7)throw new Error(); }}''','FocusLevel.java':'''import java.util.EnumSet; enum FocusLevel { LOW,MID,HIGH; static final EnumSet<FocusLevel> ALL=EnumSet.allOf(FocusLevel.class); }'''},['EnumSetMain.class','FocusLevel.class'])
errors=build('errors',{'EnumSetErrorMain.java':'''import java.util.EnumSet; public final class EnumSetErrorMain { static int result; public static void main(String[] x){try{EnumSet.allOf(null);}catch(NullPointerException e){result+=1;}try{EnumSet.allOf((Class)String.class);}catch(ClassCastException e){result+=2;}if(result!=3)throw new Error();}}'''},['EnumSetErrorMain.class'])
failed=build('failed',{'FailedEnumMain.java':'''import java.util.EnumSet; public final class FailedEnumMain { static int result; public static void main(String[] x){try{FailingLevel.touch();}catch(ExceptionInInitializerError e){result+=1;}try{EnumSet.allOf(FailingLevel.class);}catch(NoClassDefFoundError e){result+=2;}if(result!=3)throw new Error();}}''','FailingLevel.java':'''enum FailingLevel { A,B; static int boom=fail(); static int fail(){throw new RuntimeException();} static void touch(){} }'''},['FailedEnumMain.class','FailingLevel.class'])
uninit=build('uninit',{'UninitMain.java':'''import java.util.EnumSet; public final class UninitMain { public static void main(String[] x){EnumSet.allOf(OtherLevel.class);} }''','OtherLevel.java':'enum OtherLevel { A,B }'},['UninitMain.class','OtherLevel.class'],False)
raw=build('raw-replacement',{'ReplacementMain.java':'public final class ReplacementMain { public static void main(String[] x){} }','java/util/EnumSet.java':'package java.util; public final class EnumSet {}'},['ReplacementMain.class','java/util/EnumSet.class'],False)
driver=b/'driver';coord=b/'coordinator/MCEntryCoordinator.json';engine=b/'engine/MCEntryInterpreter.json'
def call(label,args,names,expect=0):
 e=dict(os.environ,TMPDIR=str(o/'tmp'),PYTHONDONTWRITEBYTECODE='1',MC_ENTRY_BINDINGS=','.join(names));t=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=r,env=e,capture_output=True,text=True,timeout=1200);cmds.append({'label':label,'exit':p.returncode,'seconds':time.monotonic()-t});(o/(label+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==expect,(label,p.returncode)
def report(w,n):return json.loads((w.parent/'reports'/w.name/n).read_text())
def finish(label,z,names,q):
 w=o/label;call(label+'-start',[driver,'setup-chain',w,coord,engine,z,str(q)],names);call(label+'-finish',[driver,'finish',w,coord,engine,z,str(q)],names);call(label+'-reopen',[driver,'verify',w,coord,engine,z,str(q)],names);h=json.loads((w/'durable-head.json').read_text());cp=(w/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();return {'machineRoot':h['machineRoot'],'opaque':hashlib.sha256(cp[280:]).hexdigest(),'java':h['jvmSteps'],'internal':h['internalSteps'],'epoch':h['epoch']}
for fixture,z,names in [('positive',positive,['EnumSetMain.class','FocusLevel.class']),('errors',errors,['EnumSetErrorMain.class']),('failed',failed,['FailedEnumMain.class','FailingLevel.class'])]:
 base=None
 for tag,q in [('q1',1),('q7',7),('direct',4096)]:
  x=finish(fixture+'-'+tag,z,names,q);rows[fixture+'/'+tag]=x
  if base is None:base=x
  else:assert (x['machineRoot'],x['opaque'],x['java'],x['internal'])==(base['machineRoot'],base['opaque'],base['java'],base['internal'])
w=o/'uninit-world';call('uninit-start',[driver,'setup-chain',w,coord,engine,uninit,'4096'],['UninitMain.class','OtherLevel.class']);f=report(w,'start-refusal.json');assert f['rootUnchanged'];rows['uninitialized-bounded-refusal']=f
w=o/'raw-world';call('raw-start',[driver,'setup-chain',w,coord,engine,raw,'4096'],['ReplacementMain.class','java/util/EnumSet.class']);f=report(w,'start-refusal.json');assert f['selector']=='0x6a23ad80' and list(map(str,f['uint256Words']))==['1','1'] and f['rootUnchanged'];rows['raw-replacement']=f
(o/'summary.json').write_text(json.dumps({'profile':'MC-ENUM-SET-PARENT2','results':rows,'commands':cmds},indent=2)+'\n');print(json.dumps(rows,indent=2))
