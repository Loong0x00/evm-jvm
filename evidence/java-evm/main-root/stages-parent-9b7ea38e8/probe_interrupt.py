#!/usr/bin/env python3
"""Exit immediately AFTER a successful durable publication, then use only public reopen."""
from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'))
s=(root/'evidence/java-evm/main-root/stages-preflight/transport/mr0_stages_session.go.txt').read_text();needle='e.m.Counters.CommitMS += time.Since(start).Milliseconds()';assert s.count(needle)==1;s=s.replace(needle,needle+'\nif os.Getenv("MR0_PARENT_EXIT_AFTER_COMMIT")=="1" {os.Exit(75)}')
p=out/'main.go';p.write_text(s);exe=out/'driver';subprocess.run(['go','build','-o',str(exe),str(p)],cwd=root,env=env,check=True)
a=root/'evidence/java-evm/main-root/session-preflight/artifacts';z=root/'evidence/java-evm/main-root/session-preflight/results/final3/fixtures/positive.zip'
results={}
for case,target in [('input','as0-input'),('index','index-scan')]:
 w=out/case;args=[str(w),str(a/'coordinator/MR0MainCoordinator.json'),str(a/'engine/MR0MainInterpreter.json'),str(z),'1']
 def run(label,mode,crash=False):
  e=dict(env)
  if crash:e['MR0_PARENT_EXIT_AFTER_COMMIT']='1'
  with (out/(case+'-'+label+'.log')).open('w') as f:
   p=subprocess.Popen([str(exe),mode]+args,cwd=root,env=e,stdout=f,stderr=subprocess.STDOUT);code=p.wait()
  (out/(case+'-'+label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':code,'mode':mode,'afterDurableCommitExit':crash})+'\n');return code
 assert run('factory','factory-initial')==0
 if case=='index':assert run('input','as0-input')==0
 before=(w/'durable-head.json').read_bytes();(out/(case+'-before.json')).write_bytes(before)
 assert run('interrupted',target,True)==75
 after=(w/'durable-head.json').read_bytes();(out/(case+'-after.json')).write_bytes(after);assert before!=after
 retry=run('retry',target);assert retry!=0
 results[case]={'before':json.loads(before),'published':json.loads(after),'retryExit':retry}
(out/'report.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({k:{'publishedPhase':v['published']['phase'],'index':v['published']['index'],'retryExit':v['retryExit']} for k,v in results.items()},indent=2))
