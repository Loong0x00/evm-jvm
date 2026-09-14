#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time
out=pathlib.Path(sys.argv[1]); cmd=sys.argv[2:]; out.parent.mkdir(parents=True,exist_ok=True)
p=subprocess.Popen(cmd, start_new_session=True)
peak=0
while p.poll() is None:
    try:
        rss=int(open('/proc/%d/status'%p.pid).read().split('VmRSS:')[1].split()[0])*1024
        peak=max(peak,rss)
    except (FileNotFoundError,IndexError): pass
    time.sleep(.01)
rc=p.wait()
out.write_text(json.dumps({'command':cmd,'exit':rc,'peakRSSBytes':peak,'timeoutSeconds':1200,'pid':p.pid},indent=2)+'\n')
sys.exit(rc)
