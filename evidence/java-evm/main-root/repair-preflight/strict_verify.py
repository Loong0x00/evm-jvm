#!/usr/bin/env python3
"""Strict verifier for a freshly generated MR0 repair world.

This intentionally takes an ignored output directory, not this archive.  It checks
actual pipeline records, artifacts, checkpoint bytes and cross-quantum guest
outcomes; archived JSON alone is never an input to a successful verification.
"""
import base64, hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED_COMPILER = {
    "version": "0.8.30+commit.73712a01.Emscripten.clang",
    "optimizer": {"enabled": True, "runs": 200}, "viaIR": True,
    "evmVersion": "cancun", "metadata": {"appendCBOR": False, "bytecodeHash": "none"},
}

def die(message):
    raise SystemExit("FAIL: " + message)
def load(path):
    try: return json.loads(path.read_text())
    except Exception as exc: die(f"{path}: {exc}")
def b64(value):
    return base64.b64decode(value) if isinstance(value, str) else bytes(value)
def artifact(path, source, max_runtime):
    a = load(path)
    if a.get("compiler") != EXPECTED_COMPILER: die(f"compiler pin: {path}")
    runtime = bytes.fromhex(a["deployedBytecode"].removeprefix("0x"))
    init = bytes.fromhex(a["bytecode"].removeprefix("0x"))
    if len(runtime) > max_runtime: die(f"runtime cap: {path}")
    if hashlib.sha256(runtime).hexdigest() != a["codeHashes"]["runtimeSHA256"]: die(f"runtime sha: {path}")
    if hashlib.sha256(init).hexdigest() != a["codeHashes"]["initSHA256"]: die(f"init sha: {path}")
    if hashlib.sha256(source.read_bytes()).hexdigest() != a["sourceHashes"].get(source.name): die(f"source pin: {path}")
    return a

def world(out, name, lifecycle, outcome, steps, internal, java_class=b""):
    d = out / name
    m = load(d / "durable-head.json")
    w = load(d / "world-report.json")
    if not (d / "STORE-FORMAT").read_text().strip() == "MR0-REPAIR-PREFLIGHT-1": die(f"format: {name}")
    if m["stage"] != "final-reopened" or m["lifecycle"] != lifecycle or m["outcome"] != outcome: die(f"terminal tag: {name}")
    if m["result"] != 0 or m["jvmSteps"] != steps or m["internalSteps"] != internal: die(f"reserved result/steps: {name}")
    if b64(m["javaClass"]) != java_class: die(f"dynamic Java class: {name}")
    if m["javaKind"] != 0: die(f"unexpected Java kind: {name}")
    if w["engineHeadOwner"] != m["coordinator"] or w["engineHeadEpoch"] != m["epoch"] or w["engineHeadLifecycle"] != lifecycle: die(f"reopened engine head: {name}")
    cp = d / "checkpoints" / (m["checkpointSHA256"] + ".bin")
    if not cp.is_file() or hashlib.sha256(cp.read_bytes()).hexdigest() != m["checkpointSHA256"]: die(f"terminal checkpoint: {name}")
    if len(cp.read_bytes()) > 1 << 20: die(f"checkpoint cap: {name}")
    if len(m.get("processPids", [])) < 3 or w.get("finalReopenPID") not in m["processPids"]: die(f"new-process evidence: {name}")
    c = m["counters"]
    if c["maxGas"] > 100_000_000 or any(n > 4096 for n in c["actualDI0ReadSizes"]): die(f"call/read limits: {name}")
    # AS0, ZI0, one DI0 controller per resource and the coordinator are top-level
    # ordinary CREATEs; the AS0 implementation's paged creates are traced inside.
    if c["ordinaryCreates"] != 3 + len(m["decoders"]) or c["actualNestedCreateOpcodes"] != 2 + len(m["decoders"]): die(f"ordinary CREATE route: {name}")
    if (d / "start-refusal.json").exists() or (d / "resume-refusal.json").exists(): die(f"unexpected refusal: {name}")
    if not (d / "direct-evm-failure.json").is_file(): die(f"missing rollback probe: {name}")
    return m

def main():
    if len(sys.argv) != 2: die("usage: strict_verify.py fresh-ignored-output")
    out = pathlib.Path(sys.argv[1]).resolve()
    if not out.name.startswith("java-diff-mc-main-root-repair-") or not out.is_dir(): die("refuse non-fresh MR0 repair output")
    engine = artifact(out / "artifacts/engine/MR0MainInterpreter.json", out / "artifacts/engine/MR0MainInterpreter.sol", 320 * 1024)
    coord = artifact(out / "artifacts/coordinator/MR0MainCoordinator.json", out / "artifacts/coordinator/MR0MainCoordinator.sol", 24576)
    if ("0x" + engine["codeHashes"]["runtimeKeccak256"]) not in (load(out / n / "durable-head.json")["engineCodeHash"] for n in ("positive-q1", "positive-q7")): die("engine EVM code pin")
    if ("0x" + coord["codeHashes"]["runtimeKeccak256"]) not in (load(out / n / "durable-head.json")["coordinatorCodeHash"] for n in ("positive-q1", "positive-q7")): die("coordinator EVM code pin")
    pairs = {}
    for prefix, lc, oc, steps, internal, cls in [
        ("positive", 2, 2, 319, 3, b""), ("rebind", 2, 2, 7, 2, b""),
        ("rebind-new", 2, 2, 24, 2, b""),
        ("exception", 3, 3, 18, 5, b"java/lang/RuntimeException"),
    ]:
        a = world(out, prefix+"-q1", lc, oc, steps, internal, cls)
        b = world(out, prefix+"-q7", lc, oc, steps, internal, cls)
        if (a["lifecycle"], a["outcome"], a["result"], a["jvmSteps"], a["internalSteps"], a["javaKind"], a["javaClass"]) != (b["lifecycle"], b["outcome"], b["result"], b["jvmSteps"], b["internalSteps"], b["javaKind"], b["javaClass"]): die("q1/q7 guest result divergence: " + prefix)
        pairs[prefix] = [a["epoch"], b["epoch"]]
    if pairs["positive"][0] <= pairs["positive"][1]: die("positive did not actually slice differently")
    print(json.dumps({"ok": True, "worlds": 8, "q1q7Epochs": pairs,
                      "engineRuntimeBytes": len(bytes.fromhex(engine["deployedBytecode"])),
                      "coordinatorRuntimeBytes": len(bytes.fromhex(coord["deployedBytecode"]))}, sort_keys=True))
if __name__ == "__main__": main()
