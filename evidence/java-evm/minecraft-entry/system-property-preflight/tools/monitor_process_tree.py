#!/usr/bin/env python3
"""Measure RSS for a bounded generated-only child process tree."""
import json,os,subprocess,sys,time
out=sys.argv[1]; command=sys.argv[2:]; start=time.monotonic(); p=subprocess.Popen(command,start_new_session=True)
peak=0; samples=0
def children(pid):
 todo=[pid]; got=[]
 while todo:
  q=todo.pop(); path=f'/proc/{q}/task/{q}/children'
  try:kids=[int(x) for x in open(path).read().split()]
  except OSError:kids=[]
  got.append(q); todo.extend(kids)
 return got
while p.poll() is None:
 rss=0
 for q in children(p.pid):
  try:
   for line in open(f'/proc/{q}/status'):
    if line.startswith('VmRSS:'): rss+=int(line.split()[1])*1024; break
  except OSError: pass
 peak=max(peak,rss); samples+=1; time.sleep(.02)
rc=p.wait(); json.dump({'exit':rc,'elapsedSeconds':time.monotonic()-start,'wholeProcessTreePeakRSSBytes':peak,'samples':samples,'command':command},open(out,'w'),indent=2); print(open(out).read()); sys.exit(rc)
