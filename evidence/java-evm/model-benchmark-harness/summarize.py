#!/usr/bin/env python3
from pathlib import Path
import json,statistics,sys
p=Path(sys.argv[1]); rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def ns(x):return int(x['monotonicNs'])
req={}
for x in rows:
 n=x.get('request')
 if n is not None:req.setdefault(n,{'request':n})
 if x['event']=='provider_request':req[n]['start']=ns(x);req[n]['payloadBytes']=x['payloadBytes'];req[n]['payloadSHA256']=x['payloadSHA256'];req[n]['wireThinking']=x.get('wireThinking');req[n]['wireReasoningEffort']=x.get('wireReasoningEffort')
 elif x['event']=='provider_response_headers':req[n].setdefault('headers',ns(x));req[n].setdefault('httpStatuses',[]).append(x['status'])
 elif x['event']=='first_stream':req[n].setdefault('first'+x['category'].title(),ns(x))
 elif x['event']=='stream_delta':
  req[n]['streamUtf8Bytes']=req[n].get('streamUtf8Bytes',0)+x['utf8Bytes'];req[n]['streamChars']=req[n].get('streamChars',0)+x['chars']
 elif x['event']=='assistant_end':req[n]['end']=ns(x);req[n]['usage']=x.get('usage') or {};req[n]['stopReason']=x.get('stopReason')
for q in req.values():
 if 'start' in q:
  for k in ('Any','Reasoning','Action'):
   if 'first'+k in q:q['ttf'+k+'Ms']=(q['first'+k]-q['start'])/1e6
  if 'headers'in q:q['headersMs']=(q['headers']-q['start'])/1e6
 if 'end'in q and 'firstAny'in q:
  q['streamSeconds']=(q['end']-q['firstAny'])/1e9
  out=(q.get('usage') or {}).get('output',0) or 0
  q['providerOutputTokensPerSecond']=out/q['streamSeconds'] if q['streamSeconds']>0 else None
  q['utf8BytesPerSecond']=q.get('streamUtf8Bytes',0)/q['streamSeconds'] if q['streamSeconds']>0 else None
usage={'input':0,'output':0,'cacheRead':0,'cacheWrite':0,'totalTokens':0}
for q in req.values():
 for k in usage:usage[k]+=(q.get('usage') or {}).get(k,0) or 0
first=next((ns(x) for x in rows if x['event']=='agent_start'),ns(rows[0]));last=next((ns(x) for x in reversed(rows) if x['event']=='agent_end'),ns(rows[-1]))
toolstarts={};toolDur=[];toolErrors=0
for x in rows:
 if x['event']=='tool_start':toolstarts[x['toolCallId']]=ns(x)
 elif x['event']=='tool_end':
  if x['toolCallId'] in toolstarts:toolDur.append((ns(x)-toolstarts[x['toolCallId']])/1e9)
  toolErrors+=bool(x.get('isError'))
def vals(k):return [q[k] for q in req.values() if q.get(k) is not None]
summary={'schema':1,'metricsFile':str(p),'requests':len(req),'wallSeconds':(last-first)/1e9,'usage':usage,'ttft':{k:{'valuesMs':vals(k),'medianMs':statistics.median(vals(k)) if vals(k) else None,'maxMs':max(vals(k)) if vals(k) else None} for k in ('ttfAnyMs','ttfReasoningMs','ttfActionMs','headersMs')},'generation':{'aggregateProviderOutputTokensPerSecond':usage['output']/sum(vals('streamSeconds')) if sum(vals('streamSeconds'))>0 else None,'aggregateUtf8BytesPerSecond':sum(q.get('streamUtf8Bytes',0) for q in req.values())/sum(vals('streamSeconds')) if sum(vals('streamSeconds'))>0 else None,'streamSeconds':sum(vals('streamSeconds'))},'tools':{'calls':len(toolDur),'errors':toolErrors,'summedSeconds':sum(toolDur)},'requestDetails':list(req.values())}
out=Path(sys.argv[2]) if len(sys.argv)>2 else p.with_suffix('.summary.json');out.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n');print(json.dumps(summary,indent=2,ensure_ascii=False))
