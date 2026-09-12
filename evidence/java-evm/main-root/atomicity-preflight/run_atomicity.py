#!/usr/bin/env python3
"""Public MR0 atomic-publication reproducer; output must be a fresh ignored path."""
from pathlib import Path
import hashlib, json, os, shutil, signal, stat, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "evidence/java-evm/main-root/session-preflight"
POINTS_PRE = [
    "checkpoint-before-create", "checkpoint-after-write", "checkpoint-after-sync",
    "checkpoint-after-rename", "checkpoint-after-dirsync", "trie-after-sync",
    "manifest-before-create", "manifest-after-write", "manifest-after-sync",
]
POINTS_POST = ["manifest-after-rename", "manifest-after-dirsync"]

def run(out, label, argv, env=None, cwd=None):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), **(env or {}))
    p = subprocess.Popen(argv, cwd=cwd or ROOT, env=env, start_new_session=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    peak = 0; began = time.monotonic()
    while p.poll() is None:
        if time.monotonic()-began > 1200:
            os.killpg(p.pid, signal.SIGKILL); raise RuntimeError("20-minute watchdog")
        total = 0
        for line in subprocess.check_output(["ps", "-eo", "pid=,pgid=,rss="], text=True).splitlines():
            fields=line.split()
            if len(fields)==3 and int(fields[1]) == p.pid: total += int(fields[2])*1024
        peak=max(peak,total); time.sleep(.05)
    text = p.stdout.read(); (out/(label+".log")).write_text(text)
    (out/(label+".watchdog.json")).write_text(json.dumps({"pid":p.pid,"processGroup":p.pid,"wholeGroupPeakRSSBytes":peak,"exit":p.returncode,"timeoutSeconds":1200},indent=2)+"\n")
    if p.returncode: raise RuntimeError(f"{label}: exit {p.returncode}; see log")

def head(world): return (world/"durable-head.json").read_bytes()
def manifest(world): return json.loads(head(world))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def report(out, world, name): return json.loads((out/"reports"/world.name/name).read_text())

def setup(out, exe, n):
    w=out/f"world-{n}"; run(out,f"{n}-setup",[str(exe),"setup-chain",str(w),str(out/"artifacts/coordinator/MR0MainCoordinator.json"),str(out/"artifacts/engine/MR0MainInterpreter.json"),str(out/"fixtures/positive.zip"),"1"]); return w

def assert_failure_receipt(r):
    assert r["revertHex"] == "0x" and r["uint256Words"] == [] and r["gas"] > 0
    assert r["checkpointBytes"] == 0 and not r["candidateHead"] and not r["candidateCheckpoint"] and not r["candidateRoot"]

def main():
    if len(sys.argv)!=2: raise SystemExit("usage: run_atomicity.py build/java-diff-mc-main-root-atomicity-NAME")
    out=Path(sys.argv[1]).resolve()
    if not str(out).startswith(str(ROOT/"build/java-diff-mc-main-root-atomicity-")) or out.exists(): raise SystemExit("refuse nonfresh ignored atomicity output")
    out.mkdir(parents=True); (out/"tmp").mkdir(); (out/"artifacts/engine").mkdir(parents=True); (out/"artifacts/coordinator").mkdir()
    # These immutable JSON artifacts are validated again by the public binary's
    # exact SHA256/Keccak pins; no Solidity source is modified or compiled here.
    shutil.copy2(SOURCE/"artifacts/engine/MR0MainInterpreter.json",out/"artifacts/engine")
    shutil.copy2(SOURCE/"artifacts/coordinator/MR0MainCoordinator.json",out/"artifacts/coordinator")
    shutil.copy2(ROOT/"evidence/java-evm/main-root/atomicity-preflight/transport/atomicity_session.go.txt",out/"main.go")
    run(out,"go-build",["go","build","-o","mr0-atomicity","."],cwd=out)
    run(out,"fixture-build",["python3",str(ROOT/"evidence/java-evm/main-root/atomicity-preflight/fixtures/generate-positive-exception.py"),str(out/"fixtures")])
    exe=out/"mr0-atomicity"; common=[str(out/"artifacts/coordinator/MR0MainCoordinator.json"),str(out/"artifacts/engine/MR0MainInterpreter.json"),str(out/"fixtures/positive.zip"),"1"]
    results=[]
    for point in POINTS_PRE:
        w=setup(out,exe,point); b=head(w); m=manifest(w); cp=w/"checkpoints"/(m["checkpointSHA256"]+".bin"); oldcp=sha(cp)
        run(out,point+"-same-session",[str(exe),"atomicity-retry",str(w),*common],{"MR0_ATOMICITY_TESTING":"1","MR0_ATOMICITY_FAULT":point})
        rr=report(out,w,"atomicity-retry.json"); assert rr["sameSession"] and rr["priorHeadBytesIdentical"] and rr["failedOutputEmpty"] and rr["failedLogsEmpty"]
        assert sha(cp)==oldcp
        run(out,point+"-reopen",[str(exe),"verify",str(w),*common]); results.append({"point":point,"prepublicationHeadByteIdentical":True,"sameSessionRetry":True})
    for point in POINTS_POST:
        w=setup(out,exe,point); b=head(w); before=manifest(w)
        run(out,point+"-public",[str(exe),"atomicity-resume",str(w),*common],{"MR0_ATOMICITY_TESTING":"1","MR0_ATOMICITY_FAULT":point})
        r=report(out,w,"resume-refusal.json"); assert_failure_receipt(r); after=manifest(w)
        assert b != head(w) and after["epoch"] == before["epoch"]+1 and r["rootAfter"] != r["rootBefore"]
        run(out,point+"-fresh-reopen",[str(exe),"verify",str(w),*common]); results.append({"point":point,"postRenamePoisonFreshReopen":True})
    # Actual OS EACCES, not a failpoint: public ResumeMain must leave exact Head
    # bytes and the old child untouched, then a normal public retry must work.
    w=setup(out,exe,"os-eacces"); b=head(w); m=manifest(w); cp=w/"checkpoints"/(m["checkpointSHA256"]+".bin"); oldcp=sha(cp); mode=stat.S_IMODE((w/"checkpoints").stat().st_mode)
    os.chmod(w/"checkpoints",0o500)
    try: run(out,"os-eacces-public",[str(exe),"atomicity-resume",str(w),*common])
    finally: os.chmod(w/"checkpoints",mode)
    r=report(out,w,"resume-refusal.json"); assert_failure_receipt(r); assert "permission denied" in r["error"] and b==head(w) and sha(cp)==oldcp
    run(out,"os-eacces-public-retry",[str(exe),"atomicity-resume",str(w),*common]); run(out,"os-eacces-fresh-reopen",[str(exe),"verify",str(w),*common]); results.append({"point":"actual-os-checkpoint-EACCES","priorHeadByteIdentical":True,"oldCheckpointUnchanged":True,"publicRetryAndFreshReopen":True})
    # Existing Head read-only plus parent directory non-writable exercises the
    # real manifest-create boundary after an otherwise successful EVM slice.
    w=setup(out,exe,"os-manifest"); b=head(w); m=manifest(w); cp=w/"checkpoints"/(m["checkpointSHA256"]+".bin"); oldcp=sha(cp); dmode=stat.S_IMODE(w.stat().st_mode); hmode=stat.S_IMODE((w/"durable-head.json").stat().st_mode)
    os.chmod(w/"durable-head.json",0o400); os.chmod(w,0o500)
    try: run(out,"os-manifest-public",[str(exe),"atomicity-resume",str(w),*common])
    finally: os.chmod(w,dmode); os.chmod(w/"durable-head.json",hmode)
    r=report(out,w,"resume-refusal.json"); assert_failure_receipt(r); assert b==head(w) and sha(cp)==oldcp
    run(out,"os-manifest-public-retry",[str(exe),"atomicity-resume",str(w),*common]); run(out,"os-manifest-fresh-reopen",[str(exe),"verify",str(w),*common]); results.append({"point":"actual-os-manifest-dir-EACCES","priorHeadByteIdentical":True,"oldCheckpointUnchanged":True})
    (out/"atomicity-summary.json").write_text(json.dumps({"baseCommit":"2dfc3c95c","points":results,"engineSHA256":"5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875","engineKeccak":"0x2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f","coordinatorKeccak":"0x06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c"},indent=2)+"\n")
if __name__ == "__main__": main()
