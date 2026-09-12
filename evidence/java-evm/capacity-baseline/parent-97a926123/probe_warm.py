#!/usr/bin/env python3
"""Actual uncorrected same-session cache refusal; no copied private Session state."""
from pathlib import Path
import json,os,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();assert not out.exists();out.mkdir(parents=True)
proto=Path(sys.argv[2]).resolve();env=dict(os.environ,TMPDIR=str(out/'tmp'));(out/'tmp').mkdir();classes=out/'classes';classes.mkdir()
src=root/'evidence/java-evm/capacity-baseline/preflight'
subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',str(classes)]+[str(p) for p in sorted((src/'fixtures').glob('Base*.java'))],env=env,check=True)
zp=out/'base4.zip'
with zipfile.ZipFile(zp,'w') as z:
 for p in sorted(classes.glob('*.class')):
  i=zipfile.ZipInfo(p.name,(1980,1,1,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
s=(src/'capacity_driver.go.txt').read_text().replace('build/java-diff-mc-capacity-proto-smoke',str(proto.relative_to(root)))
s=s.replace('if *command == "setup" {','if *command == "setup" || *command=="warm" {',1)
needle='''		write(map[string]interface{}{"command": "setup",'''
insert='''        if *command=="warm" {
          before:=head(s);r,err:=s.Start(pkg,0,"run",[]int32{7},4096,4096,ordinaryGas);after:=head(s)
          write(map[string]interface{}{"command":"warm","error":fmt.Sprint(err),"gas":r.GasUsed,"schema":r.Slice.Schema,"checkpointBytes":len(r.Checkpoint),"logs":len(r.Logs),"revertData":fmt.Sprintf("0x%x",r.RevertData),"before":before.StateRoot,"after":after.StateRoot,"epoch":after.Java.Epoch})
          return
        }
'''
assert needle in s;s=s.replace(needle,insert+needle,1)
(out/'main.go').write_text(s);subprocess.run(['gofmt','-w',str(out/'main.go')],check=True)
subprocess.run(['go','build','-o',str(out/'driver'),str(out/'main.go')],cwd=root,env=env,check=True)
with (out/'warm.json').open('w') as f:subprocess.run([str(out/'driver'),'-command','warm','-dir',str(out/'world'),'-zip',str(zp),'-names','Base0,Base1,Base2,Base3'],env=env,stdout=f,check=True)
w=json.loads((out/'warm.json').read_text());assert w['error']=='cb0: engine checkpoint event differs from slice' and w['schema']==0 and w['checkpointBytes']==0 and w['logs']==0 and w['revertData']=='0x' and w['gas']>0 and w['before']==w['after'] and w['epoch']==0,w
with (out/'fresh-process.json').open('w') as f:subprocess.run([str(out/'driver'),'-command','slice','-dir',str(out/'world'),'-length',str(zp.stat().st_size),'-mode','7'],env=env,stdout=f,check=True)
r=json.loads((out/'fresh-process.json').read_text());assert r['result']==54 and r['epoch']==1 and r['lifecycle']==2 and not r['reopenedEngineInstalled'],r
print(json.dumps({'warm':w,'newProcessSucceeds':r,'interpretation':'The copied Session retained old MC-CB0/vm/v1 cache domain; fresh Open derives the actual new-domain instance from Head. Warm successful EVM candidate was correctly refused/unpublished by Go event validation, not EVM revert.'},indent=2))
