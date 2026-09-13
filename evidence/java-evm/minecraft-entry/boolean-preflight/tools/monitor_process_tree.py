#!/usr/bin/env python3
"""Measure RSS for one bounded generated-only child process tree."""
import json, os, signal, subprocess, sys, time
out=sys.argv[1]; command=sys.argv[2:]; start=time.monotonic(); p=subprocess.Popen(command,start_new_session=True)
peak=0; samples=0; limit_reason=None
max_seconds=20*60; max_rss=4*1024*1024*1024
def children(pid):
    todo=[pid]; got=[]
    while todo:
        q=todo.pop()
        try: kids=[int(x) for x in open(f'/proc/{q}/task/{q}/children').read().split()]
        except OSError: kids=[]
        got.append(q); todo.extend(kids)
    return got
while p.poll() is None:
    rss=0
    for q in children(p.pid):
        try:
            for line in open(f'/proc/{q}/status'):
                if line.startswith('VmRSS:'): rss+=int(line.split()[1])*1024; break
        except OSError: pass
    peak=max(peak,rss); samples+=1
    if time.monotonic()-start > max_seconds or rss > max_rss:
        limit_reason = 'elapsed' if time.monotonic()-start > max_seconds else 'rss'
        os.killpg(p.pid, signal.SIGKILL)
        break
    time.sleep(.02)
rc=p.wait(); json.dump({'exit':rc,'elapsedSeconds':time.monotonic()-start,'wholeProcessTreePeakRSSBytes':peak,'samples':samples,'maxSeconds':max_seconds,'maxWholeProcessTreeRSSBytes':max_rss,'limitReason':limit_reason,'command':command},open(out,'w'),indent=2); print(open(out).read()); sys.exit(rc if limit_reason is None else 124)
