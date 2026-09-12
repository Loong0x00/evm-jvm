#!/usr/bin/env python3
"""Deliberately malformed generated class + wrong arity: preserve refusal precedence."""
from pathlib import Path
import importlib.util,json,os,struct,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[4];proto=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
(out/'OrderProbe.java').write_text('public class OrderProbe { public static int run(int x,int y){return x+y;} }\n')
subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',str(out),str(out/'OrderProbe.java')],env=env,check=True)
sys.dont_write_bytecode=True
raw=(out/'OrderProbe.class').read_bytes();spec=importlib.util.spec_from_file_location('testFixtureParser',root/'evidence/java-evm/capacity-baseline/fixture-completion/generate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
p,utf=mod.cp_end_and_utf8(raw);p+=6;p+=2+2*mod.u2(raw,p)
for group in ('fields','methods'):
 count=mod.u2(raw,p);p+=2
 for _ in range(count):
  ni=mod.u2(raw,p+2);attrs=mod.u2(raw,p+6);p+=8
  for a in range(attrs):
   ai=mod.u2(raw,p);n=mod.u4(raw,p+2);p+=6
   if group=='methods' and utf[ni]=='run' and utf[ai]=='Code':offset=p+8
   p+=n
bad=bytearray(raw);bad[offset]=0xff
for name,b in [('valid',raw),('bad',bad)]:
 z=out/(name+'.zip')
 with zipfile.ZipFile(z,'w') as f:
  i=zipfile.ZipInfo('OrderProbe.class',(1980,1,1,0,0,0));f.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
records={}
for profile in ('baseline','optimized'):
 exe=proto/profile/'driver'
 for name in ('valid','bad'):
  world=out/(profile+'-'+name);z=out/(name+'.zip')
  for command,args in [('setup',['-zip',str(z),'-names','OrderProbe']),('slice',['-length',str(z.stat().st_size)])]:
   path=out/(profile+'-'+name+'-'+command+'.json')
   with path.open('w') as f:subprocess.run([str(exe),'-command',command,'-dir',str(world)]+args,env=env,stdout=f,check=True,timeout=32)
  r=json.loads(path.read_text());assert 'error' in r and r['beforeRoot']==r['afterRoot'] and r['logs']==0 and r['checkpointBytes']==0
  records[profile+'-'+name]={'revert':r['rawRevert'],'error':r['error'],'gas':r['gas']}
method9='0x166ac6c3'+'0'*63+'9'
assert records['baseline-valid']['revert']==records['baseline-bad']['revert']==records['optimized-valid']['revert']==method9
# First run MUST expose the candidate difference; fixed run may require --fixed.
if '--fixed' in sys.argv:assert records['optimized-bad']['revert']==method9
else:assert records['optimized-bad']['revert']!=method9
(out/'report.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
