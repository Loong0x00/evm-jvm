#!/usr/bin/env python3
"""Verify the exact System.setErr-only source delta before/after local build."""
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
parent = stage.parent / "parent-88245dfff"
previous = stage.parent / "print-stream-output-stream-constructor-preflight"
DOMAIN = "MC-SYSTEM-SET-ERR-001"
PARENT_DOMAIN = "MC-PRINT-STREAM-OUTPUT-STREAM-CONSTRUCTOR-002"
ADDRESS = "0x4d432d53595354454d2d5345542d4552522d3031"
OWNER = "0x4d432d53595354454d2d5345542d4552522d3032"
SYSTEM_SHA256 = "b0dc61b8862cffb3b9cf0f4eae6e5cefa42809e1300d2f7a39885dd78f366d18"
SYSTEM_KECCAK = "305612913df08fe0b767c219af013c3d7e161a30a0ac7079defe1d4dd1aeae8d"

assert len(sys.argv) in (2, 3) and sys.argv[1] in ("--prebuild", "--built")
built = sys.argv[1] == "--built"
if built:
    assert len(sys.argv) == 3
    pins_path = Path(sys.argv[2]).resolve()
else:
    assert len(sys.argv) == 2 and not (stage / "build-pins.json").exists()

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def literal(text, name):
    found = re.search(r"function _bootstrap" + re.escape(name) + r"\(\) private pure returns \(bytes memory\) \{ return hex\"([0-9a-f]+)\"; \}", text)
    assert found, name
    return found.group(1)

def class_info(data):
    def u2(at): return int.from_bytes(data[at:at + 2], "big"), at + 2
    def u4(at): return int.from_bytes(data[at:at + 4], "big"), at + 4
    assert data[:8] == bytes.fromhex("cafebabe00000034")
    at = 8; count, at = u2(at); cp = [None] * count; i = 1
    while i < count:
        tag = data[at]; at += 1
        if tag == 1:
            n, at = u2(at); cp[i] = (tag, data[at:at + n]); at += n
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; i += 1
        elif tag in (7, 8, 16, 19, 20): value, at = u2(at); cp[i] = (tag, value)
        elif tag in (9, 10, 11, 12, 18):
            left, at = u2(at); right, at = u2(at); cp[i] = (tag, left, right)
        elif tag == 15: at += 3
        else: raise AssertionError(("constant-pool-tag", tag))
        i += 1
    def utf(index): assert cp[index][0] == 1; return cp[index][1]
    access, at = u2(at); this, at = u2(at); super_, at = u2(at)
    interfaces, at = u2(at); at += interfaces * 2
    def members():
        nonlocal at
        amount, at = u2(at); result = []
        for _ in range(amount):
            flags, at = u2(at); name, at = u2(at); desc, at = u2(at); attrs, at = u2(at)
            values = []
            for _ in range(attrs):
                attr_name, at = u2(at); size, at = u4(at); values.append((utf(attr_name), data[at:at + size])); at += size
            result.append((flags, utf(name), utf(desc), values))
        return result
    fields = members(); methods = members(); attrs, at = u2(at)
    for _ in range(attrs):
        _, at = u2(at); size, at = u4(at); at += size
    assert at == len(data)
    return {"count": count, "access": access, "fields": fields, "methods": methods}

inputs = {
    "artifacts/engine/MCEntryInterpreter.sol": parent / "artifacts/engine/MCEntryInterpreter.sol",
    "artifacts/coordinator/MCEntryCoordinator.sol": parent / "artifacts/coordinator/MCEntryCoordinator.sol",
    "canonical-driver.go.txt": parent / "canonical-driver.go.txt",
    "checkpoint_diagnostic.py": parent / "checkpoint_diagnostic.py",
    "checkpoint_frames.py": parent / "checkpoint_frames.py",
    "verify_receipts.js": parent / "verify_receipts.js",
    "generated_gate.py": parent / "generated_gate.py",
    "pins.json": parent / "pins.json",
    "artifacts/engine/build.js": parent / "artifacts/engine/build.js",
    "artifacts/coordinator/build.js": parent / "artifacts/coordinator/build.js",
}
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "88245dfff", "parentEvidence": "parent-88245dfff",
    "sha256": {name: sha(path) for name, path in inputs.items()},
}
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / name).read_bytes(), name

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
    public static final PrintStream out;

    private System() {}

    /** Stable LOCAL replay epoch; this is not a host, block, or wall clock. */
    public static long currentTimeMillis() {
        return 0L;
    }

    public static native void arraycopy(
            Object source, int sourcePosition, Object destination,
            int destinationPosition, int length);

    /** The VM-owned err cell is the sole native mutable System static. */
    public static native void setErr(PrintStream stream);

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
        out = new PrintStream();
    }
}
"""
source = (stage / "bootstrap/java/lang/System.java").read_text()
assert source == EXPECTED_SYSTEM_SOURCE
for forbidden in ("setOut", "SecurityManager permission", "System.err.println", "System.out.println", "stdout", "stderr", "Console", "File"):
    assert forbidden not in source, forbidden
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac"); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="system-set-err-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name); system_src = tmp / "src/java/lang/System.java"; stream_src = tmp / "src/java/io/PrintStream.java"
    system_src.parent.mkdir(parents=True); stream_src.parent.mkdir(parents=True)
    system_src.write_text(source)
    stream_src.write_text((stage / "bootstrap/java/io/PrintStream.java").read_text())
    output = tmp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, system_src, stream_src], check=True)
    system_class = (output / "java/lang/System.class").read_bytes()
assert len(system_class) == 1045 and hashlib.sha256(system_class).hexdigest() == SYSTEM_SHA256
assert system_class.hex() == "".join((stage / "bootstrap/java/lang/System.class.hex").read_text().split())
info = class_info(system_class)
assert info["access"] == 0x31
assert [(x[0], x[1], x[2]) for x in info["fields"]] == [
    (0x000a, b"security", b"Ljava/lang/SecurityManager;"),
    (0x000a, b"properties", b"Ljava/util/Properties;"),
    (0x0019, b"err", b"Ljava/io/PrintStream;"),
    (0x0019, b"out", b"Ljava/io/PrintStream;"),
]
assert [(x[0], x[1], x[2]) for x in info["methods"]] == [
    (0x0002, b"<init>", b"()V"), (0x0009, b"currentTimeMillis", b"()J"),
    (0x0109, b"arraycopy", b"(Ljava/lang/Object;ILjava/lang/Object;II)V"),
    (0x0109, b"setErr", b"(Ljava/io/PrintStream;)V"),
    (0x0009, b"getSecurityManager", b"()Ljava/lang/SecurityManager;"),
    (0x0009, b"getProperty", b"(Ljava/lang/String;)Ljava/lang/String;"), (0x0008, b"<clinit>", b"()V"),
]

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
old_system = literal(expected_engine, "System")
assert hashlib.sha256(bytes.fromhex(old_system)).hexdigest() == json.loads((parent / "pins.json").read_text())["bootstrapSHA256"]["System"]
expected_engine = expected_engine.replace(old_system, system_class.hex())
old = '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("arraycopy"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/Object;ILjava/lang/Object;II)V"))) return 5;'''
new = '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("arraycopy"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/Object;ILjava/lang/Object;II)V"))) return 5;
            // Binding15 is the one canonical VM-owned System static mutation.
            // Raw System replacement is rejected during program preparation;
            // this exact signature cannot grant a host output or security path.
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("setErr"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/io/PrintStream;)V"))) return 15;'''
assert expected_engine.count(old) == 1; expected_engine = expected_engine.replace(old, new)
old = '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && binding != 12 && binding != 13
                && binding != 14 && s.argumentKinds.length != 1)'''
new = '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && binding != 12 && binding != 13
                && binding != 14 && binding != 15 && s.argumentKinds.length != 1)'''
assert expected_engine.count(old) == 1; expected_engine = expected_engine.replace(old, new)
old = '''            || (binding == 14 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("[Ljava/lang/StackTraceElement;"))))) {'''
new = '''            || (binding == 14 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("[Ljava/lang/StackTraceElement;"))))
            || (binding == 15 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 2
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/io/PrintStream;"))))) {'''
assert expected_engine.count(old) == 1; expected_engine = expected_engine.replace(old, new)
needle = '''    // A missing profile API is not permission to hide a malformed descriptor.
'''
helper = '''    /// @dev Locate the only VM-mutable System cell from canonical metadata. The
    /// field remains public static final in Java; this native binding is the
    /// single interpreter exception and never exposes a generic static write.
    function _canonicalSystemErrField(
        ClassInfo[] memory classes, uint256 systemClass, uint256 rawClassCount, uint256 pc
    ) private pure returns (uint256 field) {
        if (systemClass < rawClassCount || systemClass >= classes.length
            || !_isNamedClass(classes[systemClass], bytes("java/lang/System"))) {
            revert CallError(4, pc);
        }
        uint256 found;
        ClassInfo memory c = classes[systemClass];
        for (uint256 i; i < c.fields.length; ++i) {
            FieldInfo memory candidate = c.fields[i];
            (uint256 nameOffset, uint256 nameLength) = _utf(c.cp[candidate.nameIndex]);
            (uint256 descriptorOffset, uint256 descriptorLength) =
                _utf(c.cp[candidate.descriptorIndex]);
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("err"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("Ljava/io/PrintStream;"))) {
                if (found != 0 || candidate.accessFlags != 0x0019) revert CallError(4, pc);
                found = i + 1;
            }
        }
        if (found == 0) revert CallError(4, pc);
        return found - 1;
    }

'''
assert expected_engine.count(needle) == 1; expected_engine = expected_engine.replace(needle, helper + needle)
needle = '''                    if (nativeBinding == 6) {
                        uint256 loader = _systemClassLoader(
'''
branch = '''                    if (nativeBinding == 15) {
                        // invokestatic has already resolved the exact owned native,
                        // initialized System, and checked PrintStream assignability.
                        // Consume the guest ref (including null) and mutate only
                        // canonical System.err; System.out and every other cell are
                        // deliberately untouched.
                        if (initializationState[calleeClass] != 2) revert CallError(4, opPC);
                        uint256 errField = _canonicalSystemErrField(
                            classes, calleeClass, rawClassCount, opPC
                        );
                        staticValues[calleeClass][errField] = f.stack[base];
                        f.sp = base;
                        continue;
                    }
                    if (nativeBinding == 6) {
                        uint256 loader = _systemClassLoader(
'''
assert expected_engine.count(needle) == 1; expected_engine = expected_engine.replace(needle, branch)
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
for fixed in ("MAX_RAW_CLASSES = 52;", "MAX_RAW_BYTES = 329162;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "new bytes32[](94)", "new uint256[](14)", "h[44] = keccak256(_bootstrapSystem());", "h[83] = DBOOT_PRINT_STREAM;"):
    assert engine.count(fixed) == 1, fixed
assert engine.count("return 15;") == 1 and engine.count("binding == 15") == 1
assert engine.count("staticValues[calleeClass][errField] = f.stack[base];") == 1
assert "staticValues[calleeClass][3]" not in engine and "setOut" not in engine
assert literal(engine, "System") == system_class.hex()
assert hashlib.sha256(bytes.fromhex(literal(engine, "PrintStream"))).hexdigest() == json.loads((parent / "pins.json").read_text())["bootstrapSHA256"]["PrintStream"]

base_root = json.loads((previous / "root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 94 and record["order"] == base_root["order"]
assert len(record["keccak256"]) == len(base_root["keccak256"]) == 94
assert [i for i, (before, after) in enumerate(zip(base_root["keccak256"], record["keccak256"])) if before != after] == [44]
assert record["keccak256"][44] == SYSTEM_KECCAK
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");let x="";process.stdin.on("data",d=>x+=d);process.stdin.on("end",()=>{let p=JSON.parse(x),u=n=>{let b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b},d=keccak256(Buffer.from("JVMEVM:"+p.domain+":BOOTSTRAP:1")),r=keccak256(Buffer.concat([Buffer.from(d,"hex"),u(64),u(p.leaves.length),...p.leaves.map(v=>Buffer.from(v,"hex"))]));console.log(JSON.stringify({d,r}))})'''
calculated = json.loads(subprocess.run(["node", "-e", node], input=json.dumps({"domain": DOMAIN, "leaves": record["keccak256"]}), text=True, capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert record["dboot"] == calculated["d"] and record["bootstrapRoot"] == calculated["r"]

parent_pins = json.loads((parent / "pins.json").read_text())
initial_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
initial_driver = (parent / "canonical-driver.go.txt").read_text()
if not built:
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coord
    assert (stage / "tools/Go.txt").read_text() == initial_driver
else:
    pins = json.loads(pins_path.read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"]); bootstrap_sha["System"] = SYSTEM_SHA256
    expected_pins = {"phase": "built", "basis": "88245dfff", "parentEvidence": "parent-88245dfff/artifacts/{engine,coordinator}/MCEntry*.sol", "domain": DOMAIN, "bootstrapCount": 94, "bootstrapRoot": record["bootstrapRoot"], "bootstrapSHA256": bootstrap_sha, "globalNativeBindings": 15, "stringLocalBinding": 11, "exceptionKinds": 14, "maxFrames": 128, "rawLimits": [52, 329162], "diagnosticClassBound": 146, "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000, "runtimeCap": 393216, "address": ADDRESS, "owner": OWNER, "engine": pins["engine"], "coordinator": pins["coordinator"], "worker": "system-set-err"}
    assert pins == expected_pins == json.loads((stage / "build-pins.json").read_text())
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] == 5394
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coord.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"]).replace(parent_pins["address"][2:], ADDRESS[2:]).replace(parent_pins["domain"], DOMAIN)
    expected_driver = initial_driver
    for old, new in ((parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]), ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]), ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]), (parent_pins["address"], ADDRESS), (parent_pins["owner"], OWNER)):
        assert expected_driver.count(old) == 1; expected_driver = expected_driver.replace(old, new)
    assert expected_driver.count(parent_pins["domain"]) == 6
    expected_driver = expected_driver.replace(parent_pins["domain"], DOMAIN)
    for pattern, replacement in ((r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]), (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]), (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"])):
        expected_driver, count = re.subn(pattern, replacement, expected_driver); assert count == 1
    assert (stage / "tools/Go.txt").read_text() == expected_driver

focused = (stage / "tools/generate_focused_fixtures.py").read_text()
for exact in ("SystemSetErrMain", "System.setErr(direct)", "System.setErr(child)", "System.setErr(null)", "System.setErr(original)", "RawSystemSetErrReplacementMain"):
    assert exact in focused, exact
gate = (stage / "tools/gate.py").read_text()
for exact in ("q_system_set_err()", "_system_set_err_heap", "raw-system-seterr", "globalNativeBindings"):
    assert exact in gate, exact
assert not any(path.suffix in {".class", ".jar", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"phase": "built" if built else "prebuild", "systemBytes": len(system_class), "systemSHA256": SYSTEM_SHA256, "systemKeccak256": SYSTEM_KECCAK, "changedRootLeaves": [44], "bootstrapRoot": record["bootstrapRoot"], "globalNativeBindings": 15}, indent=2))
