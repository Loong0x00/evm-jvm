#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
old=Path(sys.argv[1]);fresh=Path(sys.argv[2])
def state(w,label):
 h=json.loads((w/label/'durable-head.json').read_text());cp=(w/label/'checkpoints'/(h['checkpointSHA256']+'.bin')).read_bytes();return h,cp[280:]
a,ao=state(old,'q1');b,bo=state(fresh,'q7');assert a['lifecycle']==b['lifecycle']==2 and a['jvmSteps']==b['jvmSteps']==4174 and a['internalSteps']==b['internalSteps']==29 and a['machineRoot']==b['machineRoot'] and ao==bo
print(json.dumps({'existingSuccessfulQ1':{'epoch':a['epoch'],'java':a['jvmSteps'],'internal':a['internalSteps']},'freshQ7':{'epoch':b['epoch']},'machineRoot':a['machineRoot'],'opaqueSHA256':hashlib.sha256(ao).hexdigest()},indent=2))
