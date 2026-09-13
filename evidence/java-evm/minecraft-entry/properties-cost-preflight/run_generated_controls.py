#!/usr/bin/env python3
"""Generated-only ON/OFF observer controls using the public AS0->ZI0->DI0 route.

The driver is copied to a fresh ignored build directory before compilation.  The
only guest inputs are javac --release-8-equivalent generated fixture sources in
this directory; neither original artifacts nor host Java execution are opened.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
PARENT=ROOT/'evidence/java-evm/minecraft-entry/parent-c24d374bc'
STAMP=time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
OUT=ROOT/'build'/f'java-diff-mc-properties-cost-{STAMP}'
DEADLINE=20*60

def run(cmd, log, env, until):
    left=until-time.monotonic()
    if left <= 0: raise RuntimeError('whole 20-minute group deadline expired')
    with log.open('ab') as f: subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT, env=env, timeout=left)

def selected_head(world):
    h=json.loads((world/'durable-head.json').read_text())
    return {k:h[k] for k in ('engineCodeHash','coordinatorCodeHash','lifecycle','epoch','checkpointRoot','machineRoot','vfsRoot','jvmSteps','internalSteps','outcome','javaKind','javaRef','runtimeCodeHash')}

def report(world, name): return world.parent/'reports'/world.name/name
def receipt(world, name):
    x=json.loads(report(world,name).read_text())
    return {k:(x.get('gas', x.get('gasUsed')) if k=='gas' else x.get(k)) for k in ('gas','selector','revertHex','rootBefore','rootAfter','rootUnchanged','checkpointBytes')}

def once(name, source, quantum, observer, until):
    case=OUT/f'{name}-{"on" if observer else "off"}'
    case.mkdir(); classes=case/'classes'; classes.mkdir()
    env=os.environ.copy(); env['TMPDIR']=str(case/'tmp'); Path(env['TMPDIR']).mkdir()
    env['MC_ENTRY_BINDINGS']=source.stem+'.class'
    if observer: env['MC_PROPERTIES_COST_OBSERVER']='1'
    else: env.pop('MC_PROPERTIES_COST_OBSERVER',None)
    run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-d',str(classes),str(source)],case/'javac.log',env,until)
    archive=case/'fixture.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
        info=zipfile.ZipInfo(source.stem+'.class',(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.external_attr=0o100600<<16
        z.writestr(info,(classes/(source.stem+'.class')).read_bytes())
    world=case/'world'; common=[str(world),str(PARENT/'coordinator/MCEntryCoordinator.json'),str(PARENT/'engine/MCEntryInterpreter.json'),str(archive),str(quantum)]
    run([str(OUT/'properties-cost-observer'),'setup-chain',*common],case/'setup.log',env,until)
    refusal=report(world,'start-refusal.json')
    if refusal.exists():
        return {'kind':'refusal','failure':receipt(world,'start-refusal.json'),'head':selected_head(world),'observerFiles':sorted(x.name for x in (world.parent/'reports'/world.name).glob('observer-*.json'))}
    run([str(OUT/'properties-cost-observer'),'finish',*common],case/'finish.log',env,until)
    run([str(OUT/'properties-cost-observer'),'verify',*common],case/'verify.log',env,until)
    return {'kind':'terminal','head':selected_head(world),'lastSlice':receipt(world,sorted(x.name for x in (world.parent/'reports'/world.name).glob('slice-*.json'))[-1]),'observerFiles':sorted(x.name for x in (world.parent/'reports'/world.name).glob('observer-*.json'))}

def main():
    OUT.mkdir(parents=True); until=time.monotonic()+DEADLINE
    env=os.environ.copy(); env['TMPDIR']=str(OUT/'tmp'); Path(env['TMPDIR']).mkdir()
    source=HERE/'driver/properties_cost_observer_driver.go.txt'; go=OUT/'properties_cost_observer_driver.go'; shutil.copyfile(source,go)
    run(['go','build','-o',str(OUT/'properties-cost-observer'),str(go)],OUT/'go-build.log',env,until)
    construction=HERE/'fixtures/PropertiesConstructionProbe.java'; big=HERE/'fixtures/BigPropertiesProbe.java'
    results={}
    for label, src, q, expected in [('construction-q7',construction,7,'terminal'),('big-properties-direct',big,4096,'refusal')]:
        results[label]={}
        for on in (False,True): results[label]['on' if on else 'off']=once(label,src,q,on,until)
        if {k:v for k,v in results[label]['off'].items() if k != 'observerFiles'} != {k:v for k,v in results[label]['on'].items() if k != 'observerFiles'}: raise RuntimeError(f'observer changed public result for {label}')
        if results[label]['off']['kind'] != expected: raise RuntimeError(f'{label}: expected {expected}')
    # The exact compact records are safe to archive: hashes/roots/ABI reverts only,
    # no world database, checkpoint bytes, class bytes, ZIP, or EVM memory.
    summary={'format':'MC-PROPERTIES-COST-GENERATED-CONTROLS-1','out':str(OUT),'engineKeccak':'eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7','results':results}
    (HERE/'runs/generated-controls-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
