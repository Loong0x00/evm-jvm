#!/usr/bin/env python3
"""Strict generated-only System.currentTimeMillis source and commitment verifier.

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
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-033e6ff8f"
fixture_parent = stage.parent / "classcount38-byte285489-preflight"
PARENT_DOMAIN = "MC-RAW38-BYTE285489-P2"
DOMAIN = "MC-SYSTEM-TIME-MILLIS1"
PARENT_ENGINE = "4d432d52415733382d4259544532383534383946"
ENGINE = "4d432d53595354454d2d54494d452d4d494c4c49"
PARENT_OWNER = "4d432d52415733382d4259544532383534383950"
OWNER = "4d432d53595354454d2d54494d452d4d494c4c30"
SYSTEM_SHA256 = "d10707987a9b7935e1c87a6a5fc5f574ffbc42f3cd82a629d20291dffa0487bf"
SYSTEM_BYTES = 967


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
    "basis": "033e6ff8f", "parentEvidence": "parent-033e6ff8f",
    "fixtureBasis": "classcount38-byte285489-preflight", "sha256": input_hashes,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == 20
assert len(bytes.fromhex(PARENT_OWNER)) == len(bytes.fromhex(OWNER)) == 20

EXPECTED_SYSTEM_SOURCE = """package java.lang;

import java.io.PrintStream;
import java.util.Properties;

/**
 * Bounded Java 8 System surface for the local guest launch profile.
 * No host or -D property channel is present.
 */
public final class System {
    private static SecurityManager security;
    private static Properties properties;
    public static final PrintStream err;

    private System() {}

    /** Stable LOCAL replay epoch; this is not a host, block, or wall clock. */
    public static long currentTimeMillis() {
        return 0L;
    }

    public static native void arraycopy(
            Object source, int sourcePosition, Object destination,
            int destinationPosition, int length);

    public static SecurityManager getSecurityManager() {
        return security;
    }

    public static String getProperty(String key) {
        if (key.length() == 0) throw new IllegalArgumentException();
        return properties.getProperty(key);
    }

    static {
        properties = new Properties();
        properties.setProperty("java.version", "1.8");
        err = new PrintStream();
    }
}
"""
assert (stage / "bootstrap/java/lang/System.java").read_text() == EXPECTED_SYSTEM_SOURCE
assert json.loads((stage / "bootstrap/pins.json").read_text()) == {
    "reproduction": "javac -source 8 -target 8 -g:none",
    "System": {"source": "java/lang/System.java", "classHex": "java/lang/System.class.hex",
               "bytes": SYSTEM_BYTES, "sha256": SYSTEM_SHA256},
}

# This stub is solely a Java-8 compiler dependency for the already-retained err
# initialization. It is never an input bundle or tracked class artifact.
PRINTSTREAM_SOURCE = """package java.io;
public class PrintStream { public PrintStream() {} }
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
javap = Path("/usr/lib/jvm/java-8-openjdk/bin/javap")
assert javac.is_file() and javap.is_file()
with tempfile.TemporaryDirectory(prefix="system-current-time-millis-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    source = tmp / "src/java/lang/System.java"
    printstream = tmp / "src/java/io/PrintStream.java"
    source.parent.mkdir(parents=True, exist_ok=True)
    printstream.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(EXPECTED_SYSTEM_SOURCE)
    printstream.write_text(PRINTSTREAM_SOURCE)
    output = tmp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, source, printstream], check=True)
    system_class = (output / "java/lang/System.class").read_bytes()
    disassembly = subprocess.run([javap, "-bootclasspath", output, "-classpath", output,
                                  "-c", "-p", "java.lang.System"], text=True,
                                 capture_output=True, check=True).stdout
assert len(system_class) == SYSTEM_BYTES
assert hashlib.sha256(system_class).hexdigest() == SYSTEM_SHA256
assert system_class.hex() == (stage / "bootstrap/java/lang/System.class.hex").read_text().strip()
assert "public static long currentTimeMillis();" in disassembly
clock_code = disassembly.split("public static long currentTimeMillis();", 1)[1].split("public static native void arraycopy", 1)[0]
assert "lconst_0" in clock_code and "lreturn" in clock_code
assert "native long currentTimeMillis" not in disassembly

parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["runtimeBaseline"] == 393157 and parent_pins["engine"]["bytes"] == 393157
assert parent_pins["runtimeCap"] == 393216 and parent_pins["bootstrapCount"] == 91
assert parent_pins["rawLimits"] == [38, 285489] and parent_pins["diagnosticClassBound"] == 129
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14 and parent_pins["maxFrames"] == 128

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
old_comment = "/// @dev Java 8 minimal owned System; only static native arraycopy is exposed."
new_comment = "/// @dev Java 8 owned System; currentTimeMillis is ordinary deterministic long zero and arraycopy remains its sole native."
assert expected_engine.count(old_comment) == 1
expected_engine = expected_engine.replace(old_comment, new_comment)
pattern = r'(function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})'
expected_engine, changed = re.subn(pattern, r'\g<1>' + system_class.hex() + r'\g<2>', expected_engine)
assert changed == 1
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
for fixed in (
    "MAX_RAW_CLASSES = 38;", "MAX_RAW_BYTES = 285489;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "new bytes32[](91)", "new uint256[](14)",
    "return 13;", "uint32(38), uint32(285489)", "h[44] = keccak256(_bootstrapSystem());",
    "h[90] = DBOOT_STACK_TRACE_ELEMENT;", "return keccak256(abi.encode(DBOOT, h));",
):
    assert engine.count(fixed) == 1, fixed
assert engine.count("currentTimeMillis") == 1  # the System image declaration comment only; no new native branch
# _bootstrapObject has a multi-line bytes.concat return, so the direct exact
# source reconstruction above is the complete all-image comparison. Extract the
# replaced System literal separately for a clear image44 witness.
system_literal = re.search(r'function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)";', engine)
assert system_literal and system_literal.group(1) == system_class.hex()

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

# The fixture extension has no host oracle and compiles only trusted source. It
# contains both calls and checks their long values before the int terminal marker.
fixture_addition = '''# The bounded guest clock is an explicit deterministic replay epoch. This has
# no host oracle: the host clock is intentionally not the guest contract. The
# two Java long values must both be ordinary guest zero values before result is
# set, so q1/q7/direct/reopen exercise lconst_0, lreturn and long comparisons.
build("system-current-time-millis", {
    "SystemCurrentTimeMillisMain.java": """public final class SystemCurrentTimeMillisMain {
  static long first;
  static long second;
  static int result;
  public static void main(String[] ignored) {
    first = System.currentTimeMillis();
    second = System.currentTimeMillis();
    if (first != 0L || second != 0L || first != second) throw new Error();
    result = 7;
  }
}
""",
}, ["SystemCurrentTimeMillisMain.class"])

'''
base_fixture = (fixture_parent / "tools/generate_fixtures.py").read_text()
expected_fixture = base_fixture.replace("java-diff-mc-classcount38-byte285489-fixtures-",
                                        "java-diff-mc-system-current-time-millis-fixtures-")
needle = "for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39): count_fixture(\"count-%d\" % count, count)\n"
assert expected_fixture.count(needle) == 1
expected_fixture = expected_fixture.replace(needle, fixture_addition + needle)
fixture = (stage / "tools/generate_fixtures.py").read_text()
assert fixture == expected_fixture

parent_gate = (parent / "generated_gate.py").read_text()
gate = parent_gate
assert gate.count("One generated-only bounded Thread.getStackTrace empty-array and retained acceptance gate.") == 1
gate = gate.replace("One generated-only bounded Thread.getStackTrace empty-array and retained acceptance gate.",
                    "One generated-only deterministic System.currentTimeMillis long-zero and retained acceptance gate.")
gate = gate.replace("root = here.parents[3]", "root = here.parents[4]")
gate = gate.replace("java-diff-mc-classcount38-parent-", "java-diff-mc-system-current-time-millis-build-")
gate = gate.replace("java-diff-mc-classcount38-byte285489-fixtures-", "java-diff-mc-system-current-time-millis-fixtures-")
gate = gate.replace("java-diff-mc-system-current-time-millis-build-gate-", "java-diff-mc-system-current-time-millis-gate-")
gate = gate.replace('"MC-RAW38-BYTE285489-P2"', '"MC-SYSTEM-TIME-MILLIS1"')
gate = gate.replace('assert pins["globalNativeBindings"] == 13 and pins["exceptionKinds"] == 14\n',
                    'assert pins["globalNativeBindings"] == 13 and pins["exceptionKinds"] == 14\n'
                    'assert pins["bootstrapSHA256"]["System"] == "d10707987a9b7935e1c87a6a5fc5f574ffbc42f3cd82a629d20291dffa0487bf"\n')
clock_gate = '''# currentTimeMillis is ordinary Java 8 bytecode in image44: its static active
# use initializes the pre-existing System/PrintStream state, then lconst_0 /
# lreturn supply a stable LOCAL replay epoch. No host, block, or wall-clock
# input is available to this fixture.
def system_current_time_millis_initialized(decoded):
    raw = fixture("system-current-time-millis")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 44]["state"] == states[raw + 83]["state"] == 2
q_equivalent("system-current-time-millis", "system-current-time-millis", system_current_time_millis_initialized)

'''
needle = 'retained("system-err", "system-err", system_initialized)\n\n'
assert gate.count(needle) == 1
gate = gate.replace(needle, needle + clock_gate)
old_limit = '"limitations": "Only raw selected-class capacity changes from accepted 91-image stage: 37 to 38, aggregate raw bytes 282358 to 285489, and read-only checkpoint diagnostic class bound 128 to 129. The 91 ordered bootstrap images, runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, Provider construction, factory, world, or Done input or claim. Parent alone appends/runs genuine StatusData with accelerated replay."'
new_limit = '"limitations": "Only bootstrap image44 java/lang/System changes: currentTimeMillis()J is ordinary Java 8 lconst_0/lreturn and returns deterministic long zero. Existing System initialization/APIs, the 91-image order, runtime-derived root, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."'
assert gate.count(old_limit) == 1
gate = gate.replace(old_limit, new_limit)
assert (stage / "tools/gate.py").read_text() == gate
assert "whole_gate_seconds <= 1200" in gate and "canonical-receipts" in gate

# The root is recalculated from actual source image bytes and the immutable 91
# image order, never accepted as an engine literal.
root_record = json.loads((stage / "root-commitment.json").read_text())
base_root = json.loads((fixture_parent / "root-commitment.json").read_text())
assert root_record["domain"] == DOMAIN and root_record["bootstrapCount"] == 91
assert root_record["order"] == base_root["order"]
expected_leaves = list(base_root["keccak256"])
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir()
leaf_program = 'const {keccak256}=require("js-sha3");let b=[];process.stdin.on("data",x=>b.push(x));process.stdin.on("end",()=>process.stdout.write(keccak256(Buffer.concat(b))))'
system_keccak = subprocess.run(["node", "-e", leaf_program], input=system_class,
    capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout.decode()
expected_leaves[44] = system_keccak
assert root_record["keccak256"] == expected_leaves
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
    expected_bootstrap_sha = dict(parent_pins["bootstrapSHA256"])
    expected_bootstrap_sha["System"] = SYSTEM_SHA256
    expected = {
        "basis": "033e6ff8f", "parentEvidence": "parent-033e6ff8f", "phase": "built",
        "domain": DOMAIN, "runtimeBaseline": 393157, "runtimeCap": 393216,
        "bootstrapCount": 91, "bootstrapSHA256": expected_bootstrap_sha,
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
    "acceptedParent": "parent-033e6ff8f", "fixtureBasis": "classcount38-byte285489-preflight",
    "phase": phase, "domain": DOMAIN, "bootstrapImages": 91,
    "bootstrapRoot": root_record["bootstrapRoot"], "rawLimits": [38, 285489],
    "diagnosticClassBound": 129, "runtimeBaseline": 393157, "runtimeCap": 393216,
    "globalNativeBindings": 13, "maxFrames": 128, "checkpointCap": 1048576,
    "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
