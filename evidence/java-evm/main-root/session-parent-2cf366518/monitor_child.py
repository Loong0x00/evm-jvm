#!/usr/bin/env python3
"""Task-only RSS calibration, never Java/EVM execution input."""
import json,os,time
b=bytearray(96*1024*1024)
for i in range(0,len(b),4096):b[i]=1
print(json.dumps({'pid':os.getpid(),'processGroup':os.getpgrp(),'allocatedBytes':len(b)}),flush=True)
time.sleep(1.4)
