#!/usr/bin/env python3
"""Parent source-only build/generated replay/original18 in ONE monitored group."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
here=Path(__file__).resolve().parent;root=here.parents[3];src=here.parent/'classcount-preflight';old=here.parent/'parent-f780f1a13'
out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-classcount-') and not out.exists();out.mkdir();(out/'tmp').mkdir()
build=root/'build/java-diff-mc-classcount-parent-build-6748eb593';fixtures=root/'build/java-diff-mc-classcount-parent-fixtures-6748eb593';worlds=root/'build/java-diff-mc-classcount-parent-worlds-6748eb593';official=root/'build/java-diff-mc-classcount-parent-official18-6748eb593'
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'),PYTHONDONTWRITEBYTECODE='1')
def run(label,args):
 with (out/(label+'.log')).open('w') as f:
  p=subprocess.Popen(list(map(str,args)),cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);rc=p.wait()
 (out/(label+'-process.json')).write_text(json.dumps({'pid':p.pid,'exit':rc,'command':list(map(str,args))})+'\n');assert rc==0,(label,rc)
# Independent entire-engine mechanical equality, not a grep-only source guard.
a=(old/'engine/MCEntryInterpreter.sol').read_text().replace('MC-ARRAYCOPY-PARENT1','MC-CLASSCOUNT24-PREFLIGHT1').replace('MAX_RAW_CLASSES = 16;','MAX_RAW_CLASSES = 24;').replace('uint32(16), uint32(262144)','uint32(24), uint32(262144)')
assert a==(src/'engine/MCEntryInterpreter.sol').read_text()
run('source-guard',[sys.executable,src/'verify_source.py'])
run('source-build',[sys.executable,src/'build.py',build])
for kind,name in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 assert json.loads((build/kind/(name+'.json')).read_text())==json.loads((src/'actual-gate-20260913/artifacts'/kind/(name+'.json')).read_text()),kind
run('fixtures-java8',[sys.executable,src/'generate-fixtures.py',fixtures])
# Parent outer watchdog owns compilation AND replay. Remove nested session escape;
# the inner observer also reads/kills the actual inherited process group.
gate=(src/'gate.py').read_text().replace(',start_new_session=True','').replace('group_rss(p.pid)','group_rss(os.getpgid(p.pid))').replace('os.killpg(p.pid,signal.SIGKILL)','os.killpg(os.getpgid(p.pid),signal.SIGKILL)')
assert 'start_new_session=True' not in gate
# Materialize beside no source files: rewrite only read-only diagnostic location.
gate=gate.replace("here=Path(__file__).resolve().parent",'here=Path('+repr(str(src))+')')
(out/'gate.py').write_text(gate)
run('generated-gate',[sys.executable,out/'gate.py',build,fixtures,worlds])
b=json.loads((worlds/'reports/boundary-25/boundary25-refusal.json').read_text());assert b['revertHex']=='0xab23ed08'+'0'*63+'2' and b['rootBefore']==b['rootAfter']
labels=['world-%d-q%d'%(n,q) for n in (17,18,24) for q in (1,7,4096)]
run('verify-generated',[ 'node',old/'verify_receipts.js',build,worlds,*labels])
# Reconstruct original transport separately from the parent's known bounded source.
pins=json.loads((build/'pins.json').read_text());s=(old/'executed_bounded_driver.go.txt').read_text()
for a,b in [('7ccbbc5da13ebc7a3eddf46fd76061e8fd4ee8f070705c387a23c884a42570f7',pins['engine']['runtimeSHA256']),('0325b00519b2213c8baeda0b1246ac03852ae38e97ef2c4301f48224fb15d9df',pins['engine']['runtimeKeccak256']),('2936a42058eca016ad73933c1485d1e4d16da13d1020b4d2aeb3cea7bf9e3a39',pins['coordinator']['runtimeKeccak256']),('0x4d434152524159434f5059504152454e54000001',pins['address']),('MC-ARRAYCOPY-PARENT1','MC-CLASSCOUNT24-PREFLIGHT1'),('len(m.Decoders) > 16','len(m.Decoders) > 24'),('len(parts) > 16','len(parts) > 24')]:
 assert a in s,a;s=s.replace(a,b)
s=s.replace('MC-CLASSCOUNT24-PREFLIGHT1-BOUNDED-1','MC-CLASSCOUNT24-PARENT-BOUNDED-1')
execution=out/'original-execution';execution.mkdir()
for kind in ('engine','coordinator'):shutil.copytree(build/kind,execution/kind)
shutil.copy2(build/'pins.json',execution/'pins.json');(execution/'main.go').write_text(s)
run('original-driver-build',['go','build','-trimpath','-o',execution/'driver',execution/'main.go'])
run('original-driver-vet',['go','vet',execution/'main.go'])
run('original18',[sys.executable,here/'frontier.py',execution,official,'/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar',here/'official18-bindings.json',7])
run('verify-original18',['node',old/'verify_original.js',official,'official',execution])
run('verify-original18-all',['node',old/'verify_receipts.js',execution,official,'official'])
print('PASS parent source-only build, fresh generated gate and next original18 frontier')
