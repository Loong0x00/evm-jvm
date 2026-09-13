#!/usr/bin/env python3
"""Rebuild the isolated 24/262144 class-count COPY from captured parent inputs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys

here=Path(__file__).resolve().parent
root=here.parents[3]
out=Path(sys.argv[1]).resolve()
assert out.parent == root/'build' and out.name.startswith('java-diff-mc-classcount-') and not out.exists()
out.mkdir(); (out/'tmp').mkdir()
node_path=Path('/home/user/evm-jvm/geth/jvmevm/runtime/node_modules')
assert node_path.is_dir()
env=dict(os.environ, TMPDIR=str(out/'tmp'), NODE_PATH=str(node_path), PYTHONDONTWRITEBYTECODE='1')
for kind,name in (('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')):
    d=out/kind; d.mkdir()
    shutil.copy2(here/kind/(name+'.sol'),d/(name+'.sol'))
    shutil.copy2(here/kind/'build.js',d/'build.js')
    if kind == 'coordinator':
        # Coordinator source carries the fresh engine pin; no cross-code pin is accepted.
        source=(d/(name+'.sol')).read_text()
        assert source.count(engine['codeHashes']['runtimeKeccak256']) == 1
    with (out/(kind+'-build.log')).open('w') as log:
        subprocess.run(['node',str(d/'build.js')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    artifact=json.loads((d/(name+'.json')).read_text())
    if kind == 'engine': engine=artifact
    else: coordinator=artifact
# The captured bounded parent transport now has explicit fresh pins and 24 count checks.
driver=(here/'executed_bounded_driver.go.txt').read_text()
for pin in (engine['codeHashes']['runtimeSHA256'], engine['codeHashes']['runtimeKeccak256'], coordinator['codeHashes']['runtimeKeccak256'], str(len(engine['deployedBytecode'])//2), str(len(coordinator['deployedBytecode'])//2)):
    assert pin in driver,pin
main=out/'main.go'; main.write_text(driver)
for command in (['gofmt','-w',str(main)],['go','build','-trimpath','-o',str(out/'driver'),str(main)],['go','vet',str(main)]):
    subprocess.run(command,cwd=root,env=env,check=True)
pins={'profile':'MC-CLASSCOUNT24-PREFLIGHT1','address':'0x4d43434c415353434f554e543234000000000001','rawClassCount':24,'rawByteCount':262144,
      'engine':{'bytes':len(engine['deployedBytecode'])//2,**engine['codeHashes']},
      'coordinator':{'bytes':len(coordinator['deployedBytecode'])//2,**coordinator['codeHashes']}}
(out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print((out/'pins.json').read_text(),end='')
