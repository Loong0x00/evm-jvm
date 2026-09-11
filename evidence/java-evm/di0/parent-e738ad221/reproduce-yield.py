#!/usr/bin/env python3
"""Rebuild/replay parent refinement into a NEW disposable workspace; no archive writes."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent
repo=here.parents[3]
base=here.parent/'budget-preflight'; source=here/'yield'
w=Path(sys.argv[1]).resolve()
w.mkdir(parents=True,exist_ok=False)
def copy(src,name): (w/name).write_bytes(src.read_bytes())
copy(source/'DI0OutputPages.sol','DI0Inflate.sol')
copy(source/'replay.go.txt','replay.go')
for n in ('compile.js','persistence.go','trees.go'):copy(base/(n+'.txt'),n)
copy(here/'headers64/source.go.txt','headers64.go')
for n in ('long-trees.go','long-performance.go'):copy(source/(n+'.txt'),n)
(w/'tree-base.go').write_text((w/'replay.go').read_text().replace('func main() {','func originalMain() {',1))
env=os.environ.copy();env['NODE_PATH']=str(repo/'jvmevm/runtime/node_modules')
def run(args,out=None,extra=None):
 e=env.copy();e.update(extra or {})
 if out:
  with (w/out).open('w') as f:subprocess.run(args,cwd=w,env=e,stdout=f,check=True)
 else:subprocess.run(args,cwd=w,env=e,check=True)
run(['node','compile.js'])
pin=json.loads((source/'artifact-summary.json').read_text())
assert hashlib.sha256((w/'DI0Inflate.json').read_bytes()).hexdigest()==pin['artifactSHA256']
for exe,files in {
 'replay':['replay.go','persistence.go'],
 'trees':['tree-base.go','persistence.go','trees.go'],
 'headers64':['tree-base.go','persistence.go','headers64.go'],
 'long-performance':['tree-base.go','persistence.go','long-trees.go','long-performance.go']}.items():
 run(['go','build','-trimpath','-o',exe]+files)
run(['./replay','DI0Inflate.json'],'execution-report.json')
for name in ('trees','headers64'):
 d=w/(name+'-out');d.mkdir()
 run(['./'+name],name+'-evm.json',{'DI0_ARTIFACT':str(w/'DI0Inflate.json'),'DI0_TREE_OUT':str(d)})
run(['./long-performance','DI0Inflate.json'],'long-performance-report.json')
(w/'java8').mkdir()
run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-d','java8',str(base/'InflateOracle.java')])
for name in ('trees','headers64'):
 run(['/usr/lib/jvm/java-8-openjdk/bin/java','-Xms16m','-Xmx256m','-XX:MaxMetaspaceSize=128m','-Xss1m','-cp','java8','InflateOracle',str(w/(name+'-out')/'generated')],name+'-java8.json')

def load(n):return json.loads((w/n).read_text())
r=load('execution-report.json')
ok={'verified-EVM-output','expected-EVM-rejection','expected-constructor-rejection'}
assert len(r['Results'])==37 and all(x['Outcome'] in ok for x in r['Results'])
assert r['Controls']['allExactSelectors'] and r['QEquality']['equal']
assert r['OOG']['postWriteProof'] and r['OOG']['publishRolledBack'] and r['OOG']['publishRetrySameChild']
assert r['Persistence']['successfulDurablePublications']==60 and r['Persistence']['distinctChildPIDs']
assert r['Persistence']['dynamicCacheFreshProcesses']['distinctChildPIDs']
assert all(x['verified'] for x in r['Persistence']['dynamicCacheFreshProcesses']['freshProcessStages'])
for name,n in [('trees',29),('headers64',4)]:
 rows=load(name+'-evm.json');j=load(name+'-java8.json');assert j['javaVersion']=='1.8.0_504'
 js={x['name']:x for x in j['fixtures']};assert len(rows)==n and len(js)==n
 for row in rows:
  e=row['EVM'];a=js[row['Name']];assert e['Outcome'] in ok and e['Gas']['StepMax']<100000000
  if e['Outcome']=='verified-EVM-output':
   assert not a['inflaterError'] and a['finished'] and a['remaining']==0
   assert not a['zipFileError'] and not a['zipInputStreamError']
   assert a['plainBytes']==e['Plain']==a['zipFileBytes']==a['zipInputStreamBytes']
  else:assert e['Error']!=0 and a['inflaterError'] and a['zipFileError'] and a['zipInputStreamError']
  if name=='headers64':assert e['Outcome']=='verified-EVM-output' and e['Work']==128
r=load('long-performance-report.json');assert r['artifactSHA']==pin['artifactSHA256']
assert r['allEqual'] and r['allCallsBelow100M'] and len(r['pairs'])==6 and len(r['sweeps'])==5
assert all(x['equal'] for x in r['pairs'])
assert all(x['allEqual'] and x['quantums']==128 and x['maxStepGas']<100000000 for x in r['sweeps'])
print('FRESH STRICT PASS: pinned rebuild;37/29/4 cases+Java8;6 pairs/5 complete sweeps;durability and changed-write rollback')
