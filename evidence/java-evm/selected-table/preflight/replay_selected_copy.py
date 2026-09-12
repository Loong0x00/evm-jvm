#!/usr/bin/env python3
"""Drive opaque whole-ZIP worlds through isolated selected-table COPY. Fixture metadata is TEST assertions, not execution parsing."""
from pathlib import Path
import json,os,subprocess,sys
proto=Path(sys.argv[1]).resolve();fixtures=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();assert not out.exists();out.mkdir(parents=True);(out/'tmp').mkdir()
env=dict(os.environ,TMPDIR=str(out/'tmp'));meta=json.loads((fixtures/'metadata.json').read_text());cases={x['name']:x for x in meta['fixtures']};worlds=[]
def call(profile,dest,argv,timeout=32):
 dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('w') as f, dest.with_suffix('.stderr').open('w') as err:
  subprocess.run([str(proto/profile/'driver')]+list(map(str,argv)),env=env,stdout=f,stderr=err,timeout=timeout,check=True)
 return json.loads(dest.read_text())
for profile in ('baseline','optimized'):call(profile,out/(profile+'-maxargs.json'),['-command','maxargs'])
def run(label,fixture,profile='optimized',q=4096,mode=7,refusal=None,warm=False,memory=False,pubfail=False):
 c=cases[fixture];d=out/label;d.mkdir();world=d/'world';zp=fixtures/'zips'/c['zip']['name'];names=','.join(c['knownNames']);length=c['zip']['bytes']
 info={'label':label,'fixture':fixture,'profile':profile,'quantum':q,'mode':mode,'expectedSetupRefusal':refusal,'warm':warm,'memory':memory,'publicationFault':pubfail};worlds.append(info)
 args=['-command','warm' if warm else 'setup','-zip',zp,'-names',names,'-dir',world,'-mode',mode,'-quantum',q]
 if memory:args+=['-memory']
 first=call(profile,d/'setup.json',args,120)
 if refusal:
  assert first['command']=='setup-refusal',(label,first);return
 assert first['command']==('java' if warm else 'setup') and 'error' not in first,(label,first)
 if warm:
  if not memory:call(profile,d/'terminal.json',['-command','terminal','-dir',world,'-length',length])
  return
 for n in range(1,257):
  r=call(profile,d/f'java-{n}.json',['-command','slice','-dir',world,'-length',length,'-mode',mode,'-quantum',q])
  assert 'error' not in r,(label,r)
  if pubfail and n==1:
   assert r['slice']['Lifecycle']==1
   bad=call(profile,d/'publication-failure.json',['-command','slice','-dir',world,'-length',length,'-mode',mode,'-quantum',q,'-publication-failure'])
   assert 'error' in bad and bad['rawRevert']=='0x' and bad['beforeRoot']==bad['afterRoot']==r['afterRoot'],(label,bad)
  if r['slice']['Lifecycle']!=1:break
 else:raise AssertionError('finite slice limit')
 call(profile,d/'terminal.json',['-command','terminal','-dir',world,'-length',length])
# Direct baseline comparison; old profile remains an unchanged public API.
run('old4','baseline4-exact','baseline');run('new4','baseline4-exact')
run('warm4','baseline4-exact',warm=True);run('memory4','baseline4-exact',warm=True,memory=True)
for n in (4,5,6,8):run('chain'+str(n),'chain'+str(n))
run('chain8-q7','chain8',q=7);run('chain8-input19','chain8',mode=19)
run('exact8','capacity8-exact');run('exact8-q7','capacity8-exact',q=7)
run('big','big-method-rich');run('big-q7','big-method-rich',q=7);run('big-publication','big-method-rich',q=7,pubfail=True)
run('old-big','big-method-rich','baseline',refusal='coordinator11')
run('old5','chain5','baseline',refusal='decoderCount4');run('new9','chain9',refusal='decoderCount8')
run('old65536','aggregate65536','baseline');run('old65537','aggregate65537','baseline',refusal='coordinator12')
for n in (65536,65537,262144):run('aggregate'+str(n),'aggregate'+str(n))
run('aggregate262145','aggregate262145',refusal='coordinator12')
(out/'worlds.json').write_text(json.dumps(worlds,indent=2)+'\n')
print(json.dumps({'worlds':len(worlds),'fixtures':len(cases),'out':str(out)},indent=2))
