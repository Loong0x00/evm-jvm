#!/usr/bin/env python3
"""Ordinary-1B generated-only gates for the P24 raw72/q65536 LOCAL amendment."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.dont_write_bytecode = True

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parents[3]
if len(sys.argv) != 4:
    raise SystemExit("usage: gate.py BUILD_DIR FIXTURE_DIR OUT_DIR")
BUILD, FIXTURES, OUT = (Path(x).resolve() for x in sys.argv[1:])
assert BUILD.parent == FIXTURES.parent == OUT.parent == ROOT / "build"
assert BUILD.name.startswith("java-diff-mc-raw72-q65536-build-")
assert FIXTURES.name.startswith("java-diff-mc-raw72-q65536-fixtures-")
assert OUT.name.startswith("java-diff-mc-raw72-q65536-gate-") and not OUT.exists()
pins = json.loads((BUILD / "pins.json").read_text())
fixture_meta = json.loads((FIXTURES / "fixtures.json").read_text())
assert pins["rawLimits"] == [72, 513384] and pins["maxJvmSteps"] == 65536 and pins["maxInternalSteps"] == 4096
assert pins["bootstrapCount"] == 97 and pins["bootstrapRoot"] == "e5fd9b703bccd28948443e9027362ea6ff9f46a4f4d53f88c523fa4a8b5d75e6"
assert fixture_meta["hostGuestExecution"] is False
assert fixture_meta["raw71"]["bindingCount"] == 71 and fixture_meta["raw72"]["bindingCount"] == 72
assert fixture_meta["raw73"]["bindingCount"] == 73
assert fixture_meta["byteWitnesses"]["513384"]["totalClassBytes"] == 513384
assert fixture_meta["byteWitnesses"]["513385"]["totalClassBytes"] == 513385
assert max(fixture_meta["byteWitnesses"]["513384"]["classBytes"].values()) <= 262144
assert max(fixture_meta["byteWitnesses"]["513385"]["classBytes"].values()) <= 262144

OUT.mkdir()
(OUT / "logs").mkdir()
(OUT / "tmp").mkdir()
worlds = OUT / "worlds"
worlds.mkdir()
started = time.monotonic()
deadline = started + 1200
commands: list[dict] = []
world_labels: list[str] = []
ordinary_gas = 1_000_000_000
coord_art = STAGE / "coordinator/MCEntryCoordinator.json"
engine_art = STAGE / "engine/MCEntryInterpreter.json"
driver = BUILD / "driver"
node_modules = ROOT / "jvmevm/runtime/node_modules"
base_env = {
    **os.environ,
    "TMPDIR": str(OUT / "tmp"),
    "NODE_PATH": str(node_modules),
    "PYTHONDONTWRITEBYTECODE": "1",
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "GOTOOLCHAIN": "local",
}


def remaining() -> int:
    left = int(deadline - time.monotonic())
    assert left > 0, "ordinary generated gate exceeded1200s"
    return left


def execute(label: str, command: list[str], env: dict[str, str], expect: int = 0) -> dict:
    limit = min(1200, remaining())
    begin = time.monotonic()
    log = OUT / "logs" / f"{label}.log"
    with log.open("w") as stream:
        try:
            proc = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=limit)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = -999
    row = {"label": label, "command": command, "exit": code,
           "expectedExit": expect, "wallSeconds": time.monotonic() - begin,
           "watchdogSeconds": limit}
    commands.append(row)
    (OUT / "logs" / f"{label}.json").write_text(json.dumps(row, indent=2) + "\n")
    if code != expect:
        raise RuntimeError(f"{label} exit {code}, expected {expect}; see {log}")
    return row


def env_for(bindings: str) -> dict[str, str]:
    env = dict(base_env)
    env["MC_ENTRY_BINDINGS"] = bindings
    env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    env.pop("MC_ENTRY_EXPECTED_CLASS_BYTES", None)
    return env


def run_world(label: str, fixture: str, q: int, bindings_file: str) -> dict:
    assert label not in world_labels
    world_labels.append(label)
    world = worlds / label
    zip_path = FIXTURES / fixture
    env = env_for((FIXTURES / bindings_file).read_text().strip())
    args = [str(driver), "setup-chain", str(world), str(coord_art), str(engine_art), str(zip_path), str(q)]
    execute(label + "-setup", args, env)
    execute(label + "-finish", [str(driver), "finish", str(world), str(coord_art), str(engine_art), str(zip_path), str(q)], env)
    execute(label + "-reopen", [str(driver), "verify", str(world), str(coord_art), str(engine_art), str(zip_path), str(q)], env)
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    fixture_key = {"raw71.zip": "raw71", "raw72.zip": "raw72", "quantum-loop.zip": "quantumLoop"}[fixture]
    expected_fixture = fixture_meta[fixture_key]
    assert head["totalClassBytes"] == expected_fixture["totalClassBytes"]
    assert head["engineCodeHash"] == "0x" + pins["engine"]["runtimeKeccak256"]
    assert head["coordinatorCodeHash"] == "0x" + pins["coordinator"]["runtimeKeccak256"]
    cp_path = world / "checkpoints" / (head["checkpointSHA256"] + ".bin")
    cp = cp_path.read_bytes()
    assert hashlib.sha256(cp).hexdigest() == head["checkpointSHA256"]
    assert len(cp) <= 1 << 20
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("raw72_checkpoint_diagnostic", STAGE / "tools/checkpoint_diagnostic.py")
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    diagnostic = module.inspect(cp)
    expected_raw = expected_fixture["bindingCount"]
    assert diagnostic["classCount"] == expected_raw + 97
    assert diagnostic["lifecycle"] == head["lifecycle"]
    assert diagnostic["javaSteps"] == head["jvmSteps"]
    assert diagnostic["internalSteps"] == head["internalSteps"]
    return {
        "label": label, "quantum": q, "rawCount": expected_raw,
        "classCountIncludingBootstrap": diagnostic["classCount"],
        "epoch": head["epoch"], "lifecycle": head["lifecycle"],
        "result": head["result"], "javaKind": head["javaKind"],
        "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"],
        "machineRoot": head["machineRoot"], "vfsRoot": head["vfsRoot"],
        "checkpointRoot": head["checkpointRoot"], "checkpointSHA256": head["checkpointSHA256"],
        "opaquePayloadSHA256": hashlib.sha256(cp[280:]).hexdigest(),
        "checkpointBytes": len(cp), "heapCounts": diagnostic["heapCounts"],
        "counterReceiptCount": len(list((worlds / "reports" / label).glob("slice-*.json"))),
        "verifiedReopen": True,
    }


def compare_quantums(label: str, snapshots: list[dict]) -> None:
    baseline = snapshots[0]
    fields = ("machineRoot", "vfsRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps",
              "lifecycle", "result", "javaKind", "checkpointBytes", "heapCounts")
    for value in snapshots[1:]:
        for field in fields:
            assert value[field] == baseline[field], (label, field, value[field], baseline[field])


# Retain the pre-amendment raw71 positive controls at q1/q7/q4096, then exercise
# the newly admitted raw72 minimal bundle through the same ordinary path.
snapshots: dict[str, list[dict]] = {}
for raw_label, fixture, bindings in (
    ("raw71", "raw71.zip", "bindings-raw71.txt"),
    ("raw72", "raw72.zip", "bindings-raw72.txt"),
):
    rows = []
    for q in (1, 7, 4096):
        rows.append(run_world(f"{raw_label}-q{q}", fixture, q, bindings))
    compare_quantums(raw_label, rows)
    snapshots[raw_label] = rows

# Successful direct EVM execution for 72 raw classes and a separate exact max-byte
# positive witness. The latter uses only generated class-level opaque padding.
small_direct = OUT / "engine-direct-raw72"
execute("engine-direct-raw72", [str(driver), "engine-small-start", str(small_direct), str(coord_art),
                                 str(engine_art), str(FIXTURES / "raw72.zip"), "4096"],
        env_for((FIXTURES / "bindings-raw72.txt").read_text().strip()))
small_direct_result = json.loads((small_direct / "engine-direct-raw72.json").read_text())
assert small_direct_result["status"] == "positive-terminal" and small_direct_result["headMatchesResult"]
assert small_direct_result["rawClasses"] == 72 and small_direct_result["totalClassBytes"] == 9778

byte_engine = OUT / "engine-byte-513384"
execute("engine-byte-513384", [str(driver), "engine-capacity-start", str(byte_engine), str(coord_art),
                               str(engine_art), str(FIXTURES / "raw72-513384.zip"), "65536"],
        env_for((FIXTURES / "bindings-raw72.txt").read_text().strip()))
byte_engine_result = json.loads((byte_engine / "engine-byte-513384.json").read_text())
assert byte_engine_result["status"] == "positive-terminal" and byte_engine_result["totalClassBytes"] == 513384
assert byte_engine_result["gasUsed"] < ordinary_gas and byte_engine_result["lifecycle"] == 2

# 4096 is a retained control while q65536 must commit >4096 Java instructions in
# one successful, watchdog-bounded slice. Compare full MR01 machine payloads and
# terminal result/state counters, not epoch-specific outer envelope bytes.
loop_rows = []
for q in (4096, 65536):
    loop_rows.append(run_world(f"quantum-loop-q{q}", "quantum-loop.zip", q, "bindings-quantum-loop.txt"))
q4, q65 = loop_rows
assert q65["epoch"] == 1 and q65["jvmSteps"] > 4096
assert q65["jvmSteps"] <= 65536 and q65["internalSteps"] <= 4096
assert q4["jvmSteps"] == q65["jvmSteps"] and q4["internalSteps"] == q65["internalSteps"]
for field in ("machineRoot", "vfsRoot", "opaquePayloadSHA256", "lifecycle", "result", "javaKind", "heapCounts"):
    assert q4[field] == q65[field], (field, q4[field], q65[field])
last = json.loads((worlds / "reports" / "quantum-loop-q65536" /
                   f"slice-{q65['epoch']:020d}.json").read_text())
assert last["slice"]["executedJvmSteps"] > 4096 and last["elapsedMS"] <= 30000
assert last["suppliedGas"] == ordinary_gas and last["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
assert last["gasUsed"] <= ordinary_gas

# Coordinator-side raw73 refusal, exact aggregate byte cap positive, and one-byte
# overflow. Each constructor attempt is isolated in its own fresh EVM world.
raw73_world = worlds / "coordinator-raw73"
execute("coordinator-raw73", [str(driver), "boundary-raw73", str(raw73_world), str(coord_art), str(engine_art),
                              str(FIXTURES / "raw73.zip"), "1"],
        env_for((FIXTURES / "bindings-raw73.txt").read_text().strip()))
raw73_receipt = json.loads((worlds / "reports/coordinator-raw73/coordinator-raw73.json").read_text())
assert raw73_receipt["uint256Words"] == ["2"] and raw73_receipt["rootUnchanged"] is True
assert raw73_receipt["checkpointBytes"] == 0 and raw73_receipt["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"

byte_coord = {}
for total in (513384, 513385):
    world = worlds / f"coordinator-byte-{total}"
    env = env_for((FIXTURES / "bindings-raw72.txt").read_text().strip())
    env["MC_ENTRY_EXPECTED_CLASS_BYTES"] = str(total)
    execute(f"coordinator-byte-{total}", [str(driver), "boundary-bytes", str(world), str(coord_art), str(engine_art),
                                           str(FIXTURES / f"raw72-{total}.zip"), "1"], env)
    if total == 513384:
        row = json.loads((world / "coordinator-byte-513384.json").read_text())
        assert row["status"] == "constructor-positive" and row["classCount"] == 72
        assert row["totalClassBytes"] == 513384 and row["rootChangedBySuccessfulCreate"] is True
        byte_coord[str(total)] = row
    else:
        row = json.loads((worlds / "reports" / f"coordinator-byte-{total}" / f"coordinator-byte-{total}.json").read_text())
        assert row["uint256Words"] == ["12"] and row["rootUnchanged"] is True
        assert row["checkpointBytes"] == 0 and row["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
        byte_coord[str(total)] = row

# The normal host/driver path refuses raw73 before creating a world; separate
# explicit EVM boundary modes above intentionally bypass that host guard only to
# measure the genuine coordinator and engine errors.
driver_guard_world = worlds / "driver-raw73-must-not-exist"
driver_guard_env = env_for((FIXTURES / "bindings-raw73.txt").read_text().strip())
driver_guard = execute("driver-raw73-guard", [str(driver), "setup-chain", str(driver_guard_world), str(coord_art),
                                             str(engine_art), str(FIXTURES / "raw73.zip"), "1"],
                       driver_guard_env, expect=2)
assert not driver_guard_world.exists()
assert "binding count" in (OUT / "logs/driver-raw73-guard.log").read_text()

# Engine-side typed, root/log atomic refusals cover raw count, raw byte overflow,
# q65537, zero JVM/internal budgets and maxInternal>4096.
engine_refusals = {}
for probe, binding_file, zip_file, quantum in (
    ("raw73", "bindings-raw73.txt", "raw73.zip", "1"),
    ("bytes513385", "bindings-raw72.txt", "raw72-513385.zip", "1"),
    ("jvm65537", None, "quantum-loop.zip", "1"),
    ("jvm0", None, "quantum-loop.zip", "1"),
    ("internal0", None, "quantum-loop.zip", "1"),
    ("internal4097", None, "quantum-loop.zip", "1"),
):
    env = env_for((FIXTURES / binding_file).read_text().strip()) if binding_file else dict(base_env)
    env["TMPDIR"] = str(OUT / "tmp")
    world = OUT / f"engine-{probe}"
    execute(f"engine-{probe}", [str(driver), "engine-probe", str(world), str(coord_art), str(engine_art),
                                 str(FIXTURES / zip_file), quantum, probe], env)
    row = json.loads((world / "engine-probe.json").read_text())
    assert row["status"] == "typed-atomic-refusal" and row["rootUnchanged"] and row["logsUnchanged"]
    if probe in ("raw73", "bytes513385"):
        assert row["error"] == "LinkError" and row["code"] == 1
        assert row["detail"] == (73 if probe == "raw73" else 513385)
    else:
        assert row["error"] == "LC0ControlError" and row["code"] == 6
    assert row["checkpointBytes"] == 0 and row["executionBudget"] == "LOCAL1B-USER-AUTHORIZED"
    engine_refusals[probe] = row

# Independent observer re-encodes nested ABI/events and all exact resource reads
# for every public coordinator slice at ordinary1B. It does not inspect original
# classfiles or use the host JVM.
labels = [f"raw{raw}-q{q}" for raw in (71, 72) for q in (1, 7, 4096)] + [
    "quantum-loop-q4096", "quantum-loop-q65536"]
verify_env = dict(base_env)
verify = subprocess.run(["node", str(STAGE / "tools/verify_receipts.js"), str(BUILD), str(worlds), "1", *labels],
                        cwd=ROOT, env=verify_env, text=True, capture_output=True,
                        timeout=min(120, remaining()), check=True)
(OUT / "receipt-verification.json").write_text(verify.stdout)

summary = {
    "schema": 1,
    "status": "generated-local-gates-passed",
    "scope": "P24 raw72 and maxJvmSteps65536 LOCAL amendment only; no original Java/Minecraft execution",
    "ordinaryGas": ordinary_gas,
    "wholeGateWallSeconds": time.monotonic() - started,
    "wholeGateLimitSeconds": 1200,
    "callWatchdogMs": 30000,
    "buildPins": str(BUILD / "pins.json"),
    "fixturePins": str(FIXTURES / "fixtures.json"),
    "worlds": snapshots,
    "directEngineRaw72": small_direct_result,
    "engineExact513384": byte_engine_result,
    "coordinatorRaw73": raw73_receipt,
    "coordinatorByteWitnesses": byte_coord,
    "quantumEquivalence": {
        "q4096": q4, "q65536": q65,
        "q65536ExecutedJvmStepsInSingleSlice": last["slice"]["executedJvmSteps"],
        "sameTerminalMR01Payload": q4["opaquePayloadSHA256"] == q65["opaquePayloadSHA256"],
        "sameMachineRoot": q4["machineRoot"] == q65["machineRoot"],
        "sameResultsAndCounters": (q4["jvmSteps"], q4["internalSteps"], q4["result"], q4["javaKind"], q4["lifecycle"])
            == (q65["jvmSteps"], q65["internalSteps"], q65["result"], q65["javaKind"], q65["lifecycle"]),
    },
    "driverRaw73Guard": {"exit": driver_guard["exit"], "worldAbsent": not driver_guard_world.exists()},
    "engineRefusals": engine_refusals,
    "receiptVerification": json.loads(verify.stdout),
    "commands": commands,
    "inputs": {
        "raw71ZipSHA256": fixture_meta["raw71"]["zipSHA256"],
        "raw72ZipSHA256": fixture_meta["raw72"]["zipSHA256"],
        "raw73ZipSHA256": fixture_meta["raw73"]["zipSHA256"],
        "quantumLoopZipSHA256": fixture_meta["quantumLoop"]["zipSHA256"],
        "byte513384ZipSHA256": fixture_meta["byteWitnesses"]["513384"]["zipSHA256"],
        "byte513385ZipSHA256": fixture_meta["byteWitnesses"]["513385"]["zipSHA256"],
        "hostGeneratedOnly": True,
        "hostGuestExecution": False,
    },
    "unverified": ["parent independent source rebuild/replay", "untouched original72 binding replay", "Minecraft readiness"],
}
assert summary["wholeGateWallSeconds"] <= 1200
(OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"status": summary["status"], "wallSeconds": summary["wholeGateWallSeconds"],
                  "coordinatorReceipts": summary["receiptVerification"]["verifiedReceipts"],
                  "rawLimits": pins["rawLimits"], "q65536ExecutedJvmSteps": last["slice"]["executedJvmSteps"]}, indent=2))
