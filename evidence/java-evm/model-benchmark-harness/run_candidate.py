#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,resource,signal,subprocess,sys,time
if len(sys.argv)!=5:raise SystemExit('usage: run_candidate.py WORKTREE MODEL TASK_FILE OUT_RELATIVE')
cwd=Path(sys.argv[1]).resolve();model=sys.argv[2];task=Path(sys.argv[3]).resolve();out=cwd/sys.argv[4]
assert (cwd/'.git').exists() and task.is_file() and out.resolve().is_relative_to(cwd);out.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent;metrics=out/'metrics.jsonl';events=out/'pi-events.jsonl';stderr=out/'pi-stderr.log';prompt=task.read_text();thinking=os.environ.get('PI_BENCH_THINKING','max')
worker='''You are an isolated benchmark candidate working on one bounded task. Stay inside the current working directory; do not inspect sibling or parent worktrees. Do not delegate. Preserve unrelated changes. Obey the task's original-artifact restrictions. Work autonomously, run proportionate verification, and leave a concise BENCHMARK_RESULT.md with Result, Files Changed, Verification, and Remaining Uncertainty. Do not identify or discuss your model.'''
cmd=['pi','--mode','json','--no-session','--approve','--model',model,'--thinking',thinking,'--tools','read,bash,edit,write','--extension',str(root/'metrics.ts'),'--append-system-prompt',worker,'-p',prompt]
env=dict(os.environ,PI_BENCH_METRICS_FILE=str(metrics),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root.parents[2]/'jvmevm/runtime/node_modules'));limit=int(os.environ.get('PI_BENCH_TIMEOUT_SECONDS','1200'));start=time.monotonic();timedOut=False;interruptedSignal=None
def descendants(pid):
 rows=subprocess.run(['ps','-eo','pid=,ppid='],text=True,capture_output=True,check=True).stdout.splitlines();children={}
 for row in rows:
  a,b=map(int,row.split());children.setdefault(b,[]).append(a)
 out=[];stack=list(children.get(pid,[]))
 while stack:
  x=stack.pop();out.append(x);stack.extend(children.get(x,[]))
 return out
def terminate_group(p):
 for child in reversed(descendants(p.pid)):
  try:os.kill(child,signal.SIGTERM)
  except ProcessLookupError:pass
 try:os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:return p.wait(timeout=15)
 except subprocess.TimeoutExpired:
  for child in reversed(descendants(p.pid)):
   try:os.kill(child,signal.SIGKILL)
   except ProcessLookupError:pass
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  return p.wait()
class WrapperInterrupted(Exception):pass
def interrupted(signum,frame):
 global interruptedSignal
 interruptedSignal=signum;raise WrapperInterrupted()
with events.open('wb') as fo,stderr.open('wb') as fe:
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=fo,stderr=fe,start_new_session=True)
 oldHandlers={s:signal.signal(s,interrupted) for s in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT)}
 try:
  try:code=p.wait(timeout=limit)
  except subprocess.TimeoutExpired:timedOut=True;code=terminate_group(p)
  except WrapperInterrupted:code=terminate_group(p)
 finally:
  for s,h in oldHandlers.items():signal.signal(s,h)
r=resource.getrusage(resource.RUSAGE_CHILDREN);run={'schema':1,'cwd':str(cwd),'model':model,'thinking':thinking,'taskSHA256':hashlib.sha256(task.read_bytes()).hexdigest(),'taskBytes':task.stat().st_size,'commandWithoutPrompt':cmd[:-1]+['<TASK>'],'exit':code,'timedOut':timedOut,'interruptedSignal':interruptedSignal,'timeoutSeconds':limit,'wallSeconds':time.monotonic()-start,'maxChildRSSKiB':r.ru_maxrss,'childUserSeconds':r.ru_utime,'childSystemSeconds':r.ru_stime};(out/'run.json').write_text(json.dumps(run,indent=2)+'\n')
if metrics.exists():subprocess.run([sys.executable,root/'summarize.py',metrics,out/'metrics-summary.json'],cwd=cwd,check=True,stdout=subprocess.DEVNULL)
print(json.dumps(run,indent=2));raise SystemExit(124 if timedOut else code)
