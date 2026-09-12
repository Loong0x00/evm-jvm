#!/usr/bin/env python3
"""Fresh-output verifier for the owned MR0 COPY Session only."""
import base64, hashlib, json, pathlib, sys

ENGINE_SHA = "5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875"
ENGINE_KECCAK = "2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f"
COORD_KECCAK = "06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c"

def die(s): raise SystemExit("FAIL: " + s)
def load(p):
    try: return json.loads(p.read_text())
    except Exception as e: die(f"{p}: {e}")
def dec(v): return base64.b64decode(v) if isinstance(v,str) else bytes(v)
def artifact(p, source, runtime_len, sha=None, keccak=None):
    a=load(p); r=bytes.fromhex(a['deployedBytecode'].removeprefix('0x'))
    if len(r)!=runtime_len: die(f"runtime length {p}")
    if sha and hashlib.sha256(r).hexdigest()!=sha: die(f"runtime SHA {p}")
    if keccak and a['codeHashes']['runtimeKeccak256'].lower()!=keccak: die(f"runtime Keccak {p}")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=a['sourceHashes'].get(source.name): die(f"source pin {p}")
    return a

def world(out, fixture, q, expected):
    name=f'{fixture}-q{q}'; d=out/name; report=out/'reports'/name
    m=load(d/'durable-head.json')
    if (d/'STORE-FORMAT').read_text()!='MR0-SESSION-COPY-1\n': die(f'marker {name}')
    if m['stage']!='final-reopened' or (m['lifecycle'],m['outcome'])!=expected[:2]: die(f'lifecycle {name}')
    if m['result']!=0 or (m['jvmSteps'],m['internalSteps'])!=expected[2:4]: die(f'steps {name}')
    if m['engineCodeHash'].lower()!='0x'+ENGINE_KECCAK or m['coordinatorCodeHash'].lower()!='0x'+COORD_KECCAK: die(f'code pin {name}')
    if m['engineNonce']!=0 or not m['packageRoot'] or not m['instanceId']: die(f'route identity {name}')
    if any(m[x].lower()=='0x'+'00'*32 for x in ('checkpointRoot','machineRoot','vfsRoot','seedRoot','artifactRoot','configRoot','runtimeCodeHash')): die(f'head roots {name}')
    if m['runtimeCodeHash'].lower()!='0x'+ENGINE_KECCAK: die(f'head runtime {name}')
    if m['counters']['maxGas']>100_000_000 or m['counters']['timeoutCancels']!=0 or m['counters']['maxCallMs']>30_000: die(f'call bounds {name}')
    if any(n>4096 for n in m['counters']['actualDI0ReadSizes']): die(f'DI0 paging {name}')
    cp=d/'checkpoints'/(m['checkpointSHA256']+'.bin')
    if not cp.is_file() or hashlib.sha256(cp.read_bytes()).hexdigest()!=m['checkpointSHA256']: die(f'checkpoint blob {name}')
    if len(cp.read_bytes())>1048576: die(f'checkpoint size {name}')
    wr=load(report/'world-report.json')
    if wr['engineHeadEpoch']!=m['epoch'] or wr['engineHeadLifecycle']!=m['lifecycle'] or wr['engineHeadOwner'].lower()!=m['coordinator'].lower(): die(f'EVM head reopen {name}')
    receipts=list(report.glob('process-*.json'))
    if len(receipts)!=3 or len({load(x)['pid'] for x in receipts})!=3: die(f'external process receipts {name}')
    slices=sorted(report.glob('slice-*.json'))
    if len(slices)!=m['slices']: die(f'per-slice receipts {name}')
    for receipt in slices:
        r=load(receipt)
        if r['gasUsed']>100_000_000 or r['elapsedMS']>30_000 or not r['outerABI'].startswith('0x') or r['checkpointSHA256']!=m['checkpointSHA256'] and r['epoch']==m['epoch'] or len(r['nestedLogs'])!=1: die(f'per-slice bounds/event {name}')
    # Direct terminal exception has an open/close finish with no manifest rewrite;
    # that is not a missing external process and must not be fabricated.
    if fixture=='exception' and q==4096 and len(m['processPids'])!=2: die(f'direct exception manifest PID semantics {name}')
    return m,cp.read_bytes()

def main():
    if len(sys.argv)!=2: die('usage: strict_verify.py fresh ignored output')
    out=pathlib.Path(sys.argv[1]).resolve()
    if not out.is_dir() or not out.name.startswith('java-diff-mc-main-root-session-'): die('refuse output path')
    artifact(out/'artifacts/engine/MR0MainInterpreter.json',out/'artifacts/engine/MR0MainInterpreter.sol',294795,ENGINE_SHA,ENGINE_KECCAK)
    artifact(out/'artifacts/coordinator/MR0MainCoordinator.json',out/'artifacts/coordinator/MR0MainCoordinator.sol',3547,None,COORD_KECCAK)
    cases={'positive':(2,2,319,3),'rebind':(2,2,7,2),'rebind-new':(2,2,24,2),'exception':(3,3,18,5)}
    result={}
    for fixture,want in cases.items():
        worlds=[world(out,fixture,q,want) for q in (1,7,4096)]
        heads=[(m['lifecycle'],m['outcome'],m['result'],m['jvmSteps'],m['internalSteps'],m['javaKind'],m.get('javaRef',0),m.get('javaClass','')) for m,_ in worlds]
        if heads[0]!=heads[1] or heads[0]!=heads[2]: die(f'quantum guest result {fixture}')
        # The engine's fixed envelope may differ by epoch; opaque machine tail is
        # transport-owned and must be byte-identical across q1/q7/direct.
        if len(worlds[0][1])<280 or any(cp[280:]!=worlds[0][1][280:] for _,cp in worlds[1:]): die(f'opaque terminal payload {fixture}')
        if worlds[0][0]['epoch']<=worlds[1][0]['epoch']: die(f'actual q1 slicing {fixture}')
        result[fixture]=[m['epoch'] for m,_ in worlds]
    e=worlds=None
    print(json.dumps({'ok':True,'worlds':12,'epochs':result,'engineRuntimeBytes':294795,'coordinatorRuntimeBytes':3547},sort_keys=True))
if __name__=='__main__': main()
