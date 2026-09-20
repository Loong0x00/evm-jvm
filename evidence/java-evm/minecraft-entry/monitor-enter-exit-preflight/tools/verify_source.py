#!/usr/bin/env python3
"""Strict generated-only monitor opcode source and commitment verifier.

It reads only generated parent evidence and this stage's sources. No original
artifact, JAR, class input, resource, checkpoint, or world is opened.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-886800502"
fixture_parent = stage.parent / "system-current-time-millis-preflight"
PARENT_DOMAIN = "MC-SYSTEM-TIME-MILLIS2"
DOMAIN = "MC-MONITOR-ENTER-EXIT1"
PARENT_ENGINE = "4d432d53595354454d2d54494d452d4d494c4c4a"
ENGINE = "4d432d4d4f4e49544f522d454e5445522d455831"
PARENT_OWNER = "4d432d53595354454d2d54494d452d4d494c4c31"
OWNER = "4d432d4d4f4e49544f522d454e5445522d455830"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


inputs_paths = {
    "artifacts/engine/MCEntryInterpreter.sol": parent / "artifacts/engine/MCEntryInterpreter.sol",
    "artifacts/coordinator/MCEntryCoordinator.sol": parent / "artifacts/coordinator/MCEntryCoordinator.sol",
    "canonical-driver.go.txt": parent / "canonical-driver.go.txt",
    "checkpoint_diagnostic.py": parent / "checkpoint_diagnostic.py",
    "checkpoint_frames.py": parent / "checkpoint_frames.py",
    "verify_receipts.js": parent / "verify_receipts.js",
    "artifacts/engine/build.js": parent / "artifacts/engine/build.js",
    "artifacts/coordinator/build.js": parent / "artifacts/coordinator/build.js",
    "pins.json": parent / "pins.json",
    "generated_gate.py": parent / "generated_gate.py",
    "fixtures/generate_fixtures.py": fixture_parent / "tools/generate_fixtures.py",
    "root-commitment.json": fixture_parent / "root-commitment.json",
}
input_hashes = {name: digest(path) for name, path in inputs_paths.items()}
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "886800502", "parentEvidence": "parent-886800502",
    "fixtureBasis": "system-current-time-millis-preflight", "sha256": input_hashes,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == 20
assert len(bytes.fromhex(PARENT_OWNER)) == len(bytes.fromhex(OWNER)) == 20

parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["runtimeBaseline"] == 393157 and parent_pins["engine"]["bytes"] == 393123
assert parent_pins["runtimeCap"] == 393216 and parent_pins["bootstrapCount"] == 91
assert parent_pins["rawLimits"] == [38, 285489] and parent_pins["diagnosticClassBound"] == 129
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14 and parent_pins["maxFrames"] == 128
assert parent_pins["address"] == "0x" + PARENT_ENGINE and parent_pins["owner"] == "0x" + PARENT_OWNER

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
old_execution = '''            } else if (op == 0xc6 || op == 0xc7) { // ifnull / ifnonnull
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                bool isNull = _payload(f.stack[f.sp - 1]) == 0;
                --f.sp;
                f.pc = ((op == 0xc6) == isNull)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
'''
new_execution = '''            } else if (op >= 0xc2 && op <= 0xc3 || op >= 0xc6 && op <= 0xc7) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                uint256 monitor = f.stack[--f.sp];
                _validatePackedRef(monitor, heapKinds, nextHandle, opPC);
                bool isNull = _payload(monitor) == 0;
                if (op < 0xc6) {
                    if (isNull) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    if (arena.pending.active) continue;
                } else f.pc = ((op == 0xc6) == isNull)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
'''
assert expected_engine.count(old_execution) == 1
expected_engine = expected_engine.replace(old_execution, new_execution)
old_width = '''                || (op >= 0x78 && op <= 0x83) || (op >= 0x85 && op <= 0x98)
                || (op >= 0xac && op <= 0xb1) || op == 0xbe || op == 0xbf
'''
new_width = '''                || (op >= 0x78 && op <= 0x83) || (op >= 0x85 && op <= 0x98)
                || (op >= 0xac && op <= 0xb1) || op == 0xbe || op == 0xbf
                || op == 0xc2 || op == 0xc3
'''
assert expected_engine.count(old_width) == 1
expected_engine = expected_engine.replace(old_width, new_width)
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
# This is the only cleanup: sharing the pre-existing ifnull/ifnonnull pop and
# packed-reference validation with the new monitor pair. Their old paths remain
# byte-for-byte represented by the c6/c7 branch below.
assert engine.count("op >= 0xc2 && op <= 0xc3 || op >= 0xc6 && op <= 0xc7") == 1
assert engine.count("op == 0xc2 || op == 0xc3") == 1  # predecode width only
assert engine.count("if (op < 0xc6)") == 1
assert engine.count("6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,") >= 1
for fixed in (
    "MAX_RAW_CLASSES = 38;", "MAX_RAW_BYTES = 285489;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "new bytes32[](91)", "new uint256[](14)",
    "return 13;", "uint32(38), uint32(285489)", "h[44] = keccak256(_bootstrapSystem());",
    "h[90] = DBOOT_STACK_TRACE_ELEMENT;", "return keccak256(abi.encode(DBOOT, h));",
):
    assert engine.count(fixed) == 1, fixed

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
assert parent_coordinator.count(PARENT_DOMAIN) == 4 and parent_coordinator.count(PARENT_ENGINE) == 1
initial_coordinator = parent_coordinator.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
parent_driver = (parent / "canonical-driver.go.txt").read_text()
assert parent_driver.count(PARENT_DOMAIN) == 6
initial_driver = (parent_driver.replace(PARENT_DOMAIN, DOMAIN)
                  .replace(PARENT_ENGINE, ENGINE).replace(PARENT_OWNER, OWNER))
assert (stage / "tools/checkpoint_diagnostic.py").read_bytes() == (parent / "checkpoint_diagnostic.py").read_bytes()
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()

fixture_addition = '''# monitorenter and monitorexit are emitted by ordinary Java 8 synchronized blocks.
# The nested blocks reenter exactly the same guest reference.  The null block
# must throw catchable guest NPE before its body becomes observable.
build("monitor-enter-exit", {
    "MonitorEnterExitMain.java": """public final class MonitorEnterExitMain {
  static final Object LOCK = new Object();
  static int result;
  static void reenter(Object lock) {
    synchronized (lock) {
      synchronized (lock) {
        if (lock != LOCK) throw new Error();
      }
    }
  }
  public static void main(String[] ignored) {
    reenter(LOCK);
    try {
      synchronized ((Object) null) { throw new Error(); }
    } catch (NullPointerException expected) {
      result = 7;
    }
  }
}
""",
}, ["MonitorEnterExitMain.class"], "MonitorEnterExitMain")
monitor_disassembly = subprocess.run(
    [javap, "-classpath", classes_root / "monitor-enter-exit", "-c", "MonitorEnterExitMain"],
    text=True, capture_output=True, check=True,
).stdout
assert monitor_disassembly.count("monitorenter") == 3
assert monitor_disassembly.count("monitorexit") >= 3

'''
base_fixture = (fixture_parent / "tools/generate_fixtures.py").read_text()
expected_fixture = base_fixture.replace("java-diff-mc-system-current-time-millis-fixtures-",
                                        "java-diff-mc-monitor-enter-exit-fixtures-")
old_tools = '''javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
'''
new_tools = '''javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
javap = Path("/usr/lib/jvm/java-8-openjdk/bin/javap")
assert javac.is_file() and java.is_file() and javap.is_file()
'''
assert expected_fixture.count(old_tools) == 1
expected_fixture = expected_fixture.replace(old_tools, new_tools)
needle = 'for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39): count_fixture("count-%d" % count, count)\n'
assert expected_fixture.count(needle) == 1
expected_fixture = expected_fixture.replace(needle, fixture_addition + needle)
assert (stage / "tools/generate_fixtures.py").read_text() == expected_fixture

parent_gate = (parent / "generated_gate.py").read_text()
gate = parent_gate.replace(PARENT_DOMAIN, DOMAIN)
assert gate.count("One generated-only deterministic System.currentTimeMillis long-zero and retained acceptance gate.") == 1
gate = gate.replace("One generated-only deterministic System.currentTimeMillis long-zero and retained acceptance gate.",
                    "One generated-only bounded monitorenter/monitorexit and retained acceptance gate.")
gate = gate.replace("root = here.parents[3]", "root = here.parents[4]")
assert gate.count("java-diff-mc-system-time-parent-") == 2
gate = gate.replace("java-diff-mc-system-time-parent-", "java-diff-mc-monitor-enter-exit-build-")
assert gate.count("java-diff-mc-monitor-enter-exit-build-gate-") == 1
gate = gate.replace("java-diff-mc-monitor-enter-exit-build-gate-", "java-diff-mc-monitor-enter-exit-gate-")
gate = gate.replace("java-diff-mc-system-current-time-millis-fixtures-", "java-diff-mc-monitor-enter-exit-fixtures-")
monitor_gate = '''# monitorenter/monitorexit have no scheduling or contention state in the bounded
# single-guest-thread profile.  This generated root executes nested reentry,
# both ordinary exits, and a caught null monitorenter.  q1/q7/direct/reopen
# therefore cover each opcode's reference pop and guest-NPE path.
q_equivalent("monitor-enter-exit", "monitor-enter-exit")

'''
needle = 'q_equivalent("system-current-time-millis", "system-current-time-millis", system_current_time_millis_initialized)\n\n'
assert gate.count(needle) == 1
gate = gate.replace(needle, needle + monitor_gate)
old_limit = '"limitations": "Only bootstrap image44 java/lang/System changes: currentTimeMillis()J is ordinary Java 8 lconst_0/lreturn and returns deterministic long zero. Existing System initialization/APIs, the 91-image order, runtime-derived root, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."'
new_limit = '"limitations": "Only monitorenter(0xc2)/monitorexit(0xc3) are added to predecode and execution. They pop one reference; null raises guest NPE; non-null balanced and reentrant operations are bounded single-guest-thread no-ops. No ownership, contention, wait/notify, provider factory, world, or Done claim is made. The 91-image order/runtime-derived root, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."'
assert gate.count(old_limit) == 1
gate = gate.replace(old_limit, new_limit)
assert (stage / "tools/gate.py").read_text() == gate
assert "whole_gate_seconds <= 1200" in gate and "canonical-receipts" in gate

# The root is recalculated from actual source image bytes and the immutable 91
# image order, never accepted as an engine literal. Monitor support changes no
# image leaf.
root_record = json.loads((stage / "root-commitment.json").read_text())
base_root = json.loads((fixture_parent / "root-commitment.json").read_text())
assert root_record["domain"] == DOMAIN and root_record["bootstrapCount"] == 91
assert root_record["order"] == base_root["order"]
assert root_record["keccak256"] == base_root["keccak256"]
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
program = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.keccak256.length),...x.keccak256.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({dboot:d,bootstrapRoot:r}));'''
computed = json.loads(subprocess.run(["node", "-e", program], input=json.dumps(root_record), text=True,
    capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert computed == {"dboot": root_record["dboot"], "bootstrapRoot": root_record["bootstrapRoot"]}
assert root_record["bootstrapRoot"] not in engine

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coordinator
    assert (stage / "tools/Go.txt").read_text() == initial_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    expected = {
        "basis": "886800502", "parentEvidence": "parent-886800502", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393123, "runtimeCap": 393216,
        "bootstrapCount": 91, "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [38, 285489], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 129, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected and pins["engine"]["bytes"] <= 393216
    assert pins["coordinator"]["bytes"] == 5394
    final_coordinator = initial_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == final_coordinator
    final_driver = initial_driver
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert final_driver.count(old) == 1
        final_driver = final_driver.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        final_driver, changed = re.subn(pattern, replacement, final_driver)
        assert changed == 1
    assert (stage / "tools/Go.txt").read_text() == final_driver
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-886800502", "fixtureBasis": "system-current-time-millis-preflight",
    "phase": phase, "domain": DOMAIN, "bootstrapImages": 91,
    "bootstrapRoot": root_record["bootstrapRoot"], "rawLimits": [38, 285489],
    "diagnosticClassBound": 129, "runtimeBaseline": 393123, "runtimeCap": 393216,
    "globalNativeBindings": 13, "maxFrames": 128, "checkpointCap": 1048576,
    "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
