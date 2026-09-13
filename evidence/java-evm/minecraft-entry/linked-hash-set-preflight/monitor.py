#!/usr/bin/env python3
"""Bounded whole-gate RSS observer; sums the persistent process tree, without resets."""
from pathlib import Path
import json,os,signal,subprocess,sys,time
root=Path(__file__).resolve().parents[4]; script=Path(__file__).resolve().parent/'run.sh'; tag=sys.argv[1]; log=Path(sys.argv[2]); limit=1200; cap=4*1024*1024
with log.open('w') as f:
 p=subprocess.Popen([script,tag],cwd=root,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',NODE_PATH='/home/user/evm-jvm/geth/jvmevm/runtime/node_modules'))
 started=time.monotonic();peak=0;samples=0;reason='exit'
 while p.poll() is None:
  rows=subprocess.check_output(['ps','-eo','pid=,ppid=,rss='],text=True)
  info={}
  for row in rows.splitlines():
   try: pid,ppid,rss=map(int,row.split());info[pid]=(ppid,rss)
   except ValueError: pass
  live={p.pid};changed=True
  while changed:
   changed=False
   for pid,(ppid,rss) in info.items():
    if ppid in live and pid not in live:live.add(pid);changed=True
  rss=sum(info[x][1] for x in live if x in info);peak=max(peak,rss);samples+=1
  if rss>cap or time.monotonic()-started>limit:
   reason='rss-cap' if rss>cap else 'timeout';os.killpg(p.pid,signal.SIGKILL);break
  time.sleep(.05)
 rc=p.wait();result={'exit':rc,'reason':reason,'elapsedSeconds':time.monotonic()-started,'peakTreeRSSBytes':peak*1024,'samples':samples,'limits':{'seconds':limit,'rssBytes':cap*1024}}
print(json.dumps(result,indent=2)); Path(str(log)+'.monitor.json').write_text(json.dumps(result,indent=2)+'\n');sys.exit(0 if rc==0 and reason=='exit' else 1)
