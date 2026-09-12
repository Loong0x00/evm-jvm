#!/usr/bin/env python3
"""Bound a disposable command by wall time and sampled Linux process-group RSS."""
import json,os,signal,subprocess,sys,time
out=os.path.abspath(sys.argv[1]); command=sys.argv[2:]
assert command and not os.path.exists(out)
started=time.monotonic(); p=subprocess.Popen(command,preexec_fn=os.setsid,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
peak=0; samples=0; killed=None
while p.poll() is None:
    rss=0
    for ent in os.listdir('/proc'):
        if not ent.isdigit(): continue
        try:
            f=open('/proc/'+ent+'/stat').read().split()
            # /proc stat: process group field is index 4; RSS pages is index 23.
            if int(f[4])==p.pid: rss+=int(f[23])*os.sysconf('SC_PAGE_SIZE')
        except (OSError,ValueError,IndexError): pass
    peak=max(peak,rss);samples+=1
    elapsed=time.monotonic()-started
    if elapsed>1200 or rss>4*1024**3:
        killed='timeout' if elapsed>1200 else 'rss-limit'; os.killpg(p.pid,signal.SIGKILL)
    time.sleep(.2)
stdout,_=p.communicate()
record={'command':command,'exit':p.returncode,'wallSeconds':time.monotonic()-started,
        'sampledPeakProcessGroupRSS':peak,'samples':samples,'limitSeconds':1200,
        'limitBytes':4*1024**3,'killed':killed}
open(out,'w').write(stdout+'\nWATCHDOG='+json.dumps(record,sort_keys=True)+'\n')
print(json.dumps(record))
if p.returncode or killed: raise SystemExit(1)
