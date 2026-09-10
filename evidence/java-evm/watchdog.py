import json,os,signal,subprocess,sys,time
from pathlib import Path
log,summary,*cmd=sys.argv[1:]
start=time.monotonic();peak=0;reason=None
with open(log,'wb') as out:
 p=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  rss=0
  for f in Path('/proc').glob('[0-9]*/stat'):
   try:
    tail=f.read_text().rsplit(')',1)[1].split()
    if int(tail[2])!=p.pid:continue
    rss+=int(tail[21])*os.sysconf('SC_PAGE_SIZE')
   except (OSError,ValueError,IndexError):pass
  peak=max(peak,rss)
  if rss>4*1024**3 or time.monotonic()-start>1200:
   reason='rss' if rss>4*1024**3 else 'wall'
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   break
  time.sleep(.1)
 rc=p.wait()
Path(summary).write_text(json.dumps(dict(command=cmd,exit=rc,elapsed=time.monotonic()-start,peakGroupRSS=peak,limit=reason),indent=2)+'\n')
sys.exit(rc if 0<=rc<256 else 1)
