#!/usr/bin/env python3
"""Fresh parent source rebuild + generated-only public-EVM whole gate. Wrap in watchdog."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;worker=root/'evidence/java-evm/selected-table/preflight';out=Path(sys.argv[1]).resolve();proto=out.with_name(out.name+'-proto');assert not out.exists() and not proto.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
def run(log,cmd):
 with (out/(log+'.log')).open('w') as f:subprocess.run(list(map(str,cmd)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
py=sys.executable
run('build',[py,here/'rebuild.py',proto,'--root-order','--direct-read'])
pins=json.loads((proto/'selected-pins.json').read_text());assert pins['engineRuntimeSHA256']=='9369af312aae789eb9a778ba4458a639e7f7a9ccbab461c127f7f06b4caa8702'
run('fixtures',[py,root/'evidence/java-evm/capacity-baseline/fixture-completion/generate.py',out/'fixtures'])
run('matrix',[py,worker/'replay_selected_copy.py',proto,out/'fixtures',out/'matrix'])
run('matrix-verify',[py,worker/'verify_selected_copy.py',out/'fixtures',out/'matrix'])
run('order',[py,here/'probe_order.py',proto,out/'order','--fixed'])
run('alias',[py,here/'alias_replay.py',proto,out/'alias'])
run('density',[py,here/'density.py',proto,out/'density'])
run('negative',[py,here/'negative_replay.py',proto,out/'fixtures',out/'negative'])
run('observer-build',[py,here/'add_memory_observer.py',proto])
run('memory',[py,here/'memory_replay.py',proto,out/'fixtures',out/'density',out/'memory'])
# Traced vs untraced fresh replay equality includes receipts/Head/CP, not merely results.
for label,reference in [('padded',out/'matrix/aggregate262144/java-1.json'),('big',out/'matrix/big/java-1.json'),('density',out/'density/ordinary.json')]:
 a=json.loads(reference.read_text());b=json.loads((out/('memory/'+label+'-slice.json')).read_text())
 for k in ('budget','quantum','gas','beforeRoot','afterRoot','beforeEpoch','beforeCheckpointRoot','head','slice','receiptRoot','rawRevert','logs','checkpointBytes','checkpointSHA256'):assert a[k]==b[k],(label,k)
# Strict density chain/caps/counters: no implicit1B rescue exists in parent recipe.
d=json.loads((out/'density/report.json').read_text());assert d['boundary'] is None and d['aggregate']==181969
for q,rows in [(4096,[d['ordinary']])]+[(q,d['ordinarySliced'][str(q)]) for q in (1,7)]:
 before=json.loads((out/'density/setup.json').read_text())['head']['StateRoot'];total=0
 assert len(rows)=={4096:1,1:20,7:3}[q]
 for n,r in enumerate(rows,1):
  s=r['slice'];assert 'error' not in r and r['budget']==100000000 and r['quantum']==q and 0<r['gas']<=100000000 and r['wallSeconds']<=30
  assert r['beforeRoot']==before and r['receiptRoot']==r['afterRoot']!=before;before=r['afterRoot']
  assert r['logs']==1 and s['Epoch']==n and 0<s['ExecutedJvmSteps']<=q and s['TotalJvmSteps']==total+s['ExecutedJvmSteps'];total=s['TotalJvmSteps']
  assert len(r['trace']['reads'])==47 and all(x['requested']==x['returned'] and x['success'] and 0<x['returned']<=4096 for x in r['trace']['reads'])
 assert total==20 and rows[-1]['slice']['Result']==23 and rows[-1]['slice']['Lifecycle']==2
run('accepted-cb0-regression',['go','test','-count=1','./jvmevm/localcontinuation/cb0'])
protected=subprocess.check_output(['git','diff','ba28a4ad6','--','jvmevm','core','params','consensus','eth','Makefile'],cwd=root);assert not protected
(out/'protected.diff').write_bytes(protected)
(out/'summary.json').write_text(json.dumps({'pins':pins,'matrix':json.loads((out/'matrix-verify.log').read_text()),'alias':json.loads((out/'alias/report.json').read_text()),'memory':json.loads((out/'memory/report.json').read_text()),'density':{'gas':d['ordinary']['gas'],'q1Slices':20,'q7Slices':3},'scope':'generated COPY preflight only; accepted4/65536 unchanged; no original Minecraft'},indent=2)+'\n')
print('PASS: fresh source, pin, matrix, order, alias, CAS/tamper, density, allocations/memory, traced equivalence, accepted CB0 regression')
