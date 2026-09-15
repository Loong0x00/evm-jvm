#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,resource,subprocess,sys,time
if len(sys.argv)!=5:raise SystemExit('usage: run_candidate.py WORKTREE MODEL TASK_FILE OUT_RELATIVE')
cwd=Path(sys.argv[1]).resolve();model=sys.argv[2];task=Path(sys.argv[3]).resolve();out=cwd/sys.argv[4]
assert (cwd/'.git').exists() and task.is_file() and out.resolve().is_relative_to(cwd);out.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent;metrics=out/'metrics.jsonl';events=out/'pi-events.jsonl';stderr=out/'pi-stderr.log';prompt=task.read_text();thinking=os.environ.get('PI_BENCH_THINKING','max')
worker='''You are an isolated benchmark candidate working on one bounded task. Stay inside the current working directory; do not inspect sibling or parent worktrees. Do not delegate. Preserve unrelated changes. Obey the task's original-artifact restrictions. Work autonomously, run proportionate verification, and leave a concise BENCHMARK_RESULT.md with Result, Files Changed, Verification, and Remaining Uncertainty. Do not identify or discuss your model.'''
cmd=['pi','--mode','json','--no-session','--approve','--model',model,'--thinking',thinking,'--tools','read,bash,edit,write','--extension',str(root/'metrics.ts'),'--append-system-prompt',worker,'-p',prompt]
env=dict(os.environ,PI_BENCH_METRICS_FILE=str(metrics),PYTHONDONTWRITEBYTECODE='1');start=time.monotonic();timedOut=False
with events.open('wb') as fo,stderr.open('wb') as fe:
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=fo,stderr=fe,start_new_session=True)
 try:code=p.wait(timeout=3600)
 except subprocess.TimeoutExpired:
  timedOut=True;os.killpg(p.pid,15)
  try:code=p.wait(timeout=15)
  except subprocess.TimeoutExpired:os.killpg(p.pid,9);code=p.wait()
r=resource.getrusage(resource.RUSAGE_CHILDREN);run={'schema':1,'cwd':str(cwd),'model':model,'thinking':thinking,'taskSHA256':hashlib.sha256(task.read_bytes()).hexdigest(),'taskBytes':task.stat().st_size,'commandWithoutPrompt':cmd[:-1]+['<TASK>'],'exit':code,'timedOut':timedOut,'wallSeconds':time.monotonic()-start,'maxChildRSSKiB':r.ru_maxrss,'childUserSeconds':r.ru_utime,'childSystemSeconds':r.ru_stime};(out/'run.json').write_text(json.dumps(run,indent=2)+'\n')
if metrics.exists():subprocess.run([sys.executable,root/'summarize.py',metrics,out/'metrics-summary.json'],cwd=cwd,check=True,stdout=subprocess.DEVNULL)
print(json.dumps(run,indent=2));raise SystemExit(124 if timedOut else code)
