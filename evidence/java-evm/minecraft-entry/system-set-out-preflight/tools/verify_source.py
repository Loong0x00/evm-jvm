#!/usr/bin/env python3
"""Verify the exact canonical System.setOut-only delta before/after local build."""
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
parent = stage.parent / "parent-1b178a6eb"
previous = stage.parent / "system-set-err-preflight"
DOMAIN = "MC-SYSTEM-SET-OUT-001"
PARENT_DOMAIN = "MC-SYSTEM-SET-ERR-002"
ADDRESS = "0x4d432d53595354454d2d5345542d4f55542d3031"
OWNER = "0x4d432d53595354454d2d5345542d4f55542d3032"
SYSTEM_SHA256 = "5cab6f9c8389590025f923fcee698a5ed6797ad86f40bfd2fc7fab2529dcb3a4"
SYSTEM_KECCAK = "c09d592a8765a68f31fd5425e1c4523d0f9038f08dc64e5ae8de71bbe330689c"

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
def replace_once(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)

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
    "basis": "1b178a6eb", "parentEvidence": "parent-1b178a6eb",
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

    /** The VM-owned err and out cells are the only native mutable System statics. */
    public static native void setErr(PrintStream stream);

    /** The native binding mutates only the canonical guest out cell. */
    public static native void setOut(PrintStream stream);

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
for forbidden in ("SecurityManager permission", "System.err.println", "System.out.println", "stdout", "stderr", "Console", "File", "print(", "println("):
    assert forbidden not in source, forbidden
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac"); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="system-set-out-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name); system_src = tmp / "src/java/lang/System.java"; stream_src = tmp / "src/java/io/PrintStream.java"
    system_src.parent.mkdir(parents=True); stream_src.parent.mkdir(parents=True)
    system_src.write_text(source)
    stream_src.write_text((stage / "bootstrap/java/io/PrintStream.java").read_text())
    output = tmp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, system_src, stream_src], check=True)
    system_class = (output / "java/lang/System.class").read_bytes()
assert len(system_class) == 1062 and hashlib.sha256(system_class).hexdigest() == SYSTEM_SHA256
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
    (0x0109, b"setOut", b"(Ljava/io/PrintStream;)V"),
    (0x0009, b"getSecurityManager", b"()Ljava/lang/SecurityManager;"),
    (0x0009, b"getProperty", b"(Ljava/lang/String;)Ljava/lang/String;"), (0x0008, b"<clinit>", b"()V"),
]

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
assert parent_engine.count(PARENT_DOMAIN) == 9
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN)
old_system = literal(expected_engine, "System")
assert hashlib.sha256(bytes.fromhex(old_system)).hexdigest() == json.loads((parent / "pins.json").read_text())["bootstrapSHA256"]["System"]
expected_engine = replace_once(expected_engine, old_system, system_class.hex())
expected_engine = replace_once(expected_engine, '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("setErr"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/io/PrintStream;)V"))) return 15;''', '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("setErr"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/io/PrintStream;)V"))) return 15;
            // Binding16 is the canonical VM-owned System.out mutation only.
            // Raw System replacement is rejected during program preparation;
            // this exact signature has no host output or security path.
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("setOut"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/io/PrintStream;)V"))) return 16;''')
expected_engine = replace_once(expected_engine, '''                && binding != 10 && binding != 11 && binding != 12 && binding != 13
                && binding != 14 && binding != 15 && s.argumentKinds.length != 1)''', '''                && binding != 10 && binding != 11 && binding != 12 && binding != 13
                && binding != 14 && binding != 15 && binding != 16 && s.argumentKinds.length != 1)''')
expected_engine = replace_once(expected_engine, '''            || (binding == 15 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 2
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/io/PrintStream;"))))) {''', '''            || (binding == 15 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 2
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/io/PrintStream;"))))
            || (binding == 16 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 2
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/io/PrintStream;"))))) {''')
helper = '''    /// @dev Locate the only additional VM-mutable System cell from canonical
    /// metadata. The field remains public static final in Java; binding16 is a
    /// narrow interpreter exception, never a generic static write or output path.
    function _canonicalSystemOutField(
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
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("out"))
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
expected_engine = replace_once(expected_engine, "    // A missing profile API is not permission to hide a malformed descriptor.\n", helper + "    // A missing profile API is not permission to hide a malformed descriptor.\n")
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
                    if (nativeBinding == 16) {
                        // invokestatic has already resolved the exact owned native,
                        // initialized System, and checked PrintStream assignability.
                        // Consume the guest ref (including null) and mutate only
                        // canonical System.out; System.err and every other cell are
                        // deliberately untouched.
                        if (initializationState[calleeClass] != 2) revert CallError(4, opPC);
                        uint256 outField = _canonicalSystemOutField(
                            classes, calleeClass, rawClassCount, opPC
                        );
                        staticValues[calleeClass][outField] = f.stack[base];
                        f.sp = base;
                        continue;
                    }
'''
expected_engine = replace_once(expected_engine, '''                    if (nativeBinding == 15) {
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
''', branch)
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == expected_engine
for fixed in ("MAX_RAW_CLASSES = 52;", "MAX_RAW_BYTES = 329162;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "new bytes32[](94)", "new uint256[](14)", "h[44] = keccak256(_bootstrapSystem());", "h[83] = DBOOT_PRINT_STREAM;"):
    assert engine.count(fixed) == 1, fixed
assert engine.count("return 16;") == 1 and engine.count("binding == 16") == 1
assert engine.count("staticValues[calleeClass][outField] = f.stack[base];") == 1
assert "staticValues[calleeClass][3]" not in engine
assert literal(engine, "System") == system_class.hex()
assert hashlib.sha256(bytes.fromhex(literal(engine, "PrintStream"))).hexdigest() == json.loads((parent / "pins.json").read_text())["bootstrapSHA256"]["PrintStream"]

base_root = json.loads((previous / "root-commitment.json").read_text())
record = json.loads((stage / "root-commitment.json").read_text())
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["bootstrapRoot"] == base_root["bootstrapRoot"]
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 94 and record["order"] == base_root["order"]
assert len(record["keccak256"]) == len(base_root["keccak256"]) == 94
assert [i for i, (before, after) in enumerate(zip(base_root["keccak256"], record["keccak256"])) if before != after] == [44]
assert record["keccak256"][44] == SYSTEM_KECCAK
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");let x="";process.stdin.on("data",d=>x+=d);process.stdin.on("end",()=>{let p=JSON.parse(x),u=n=>{let b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b},d=keccak256(Buffer.from("JVMEVM:"+p.domain+":BOOTSTRAP:1")),r=keccak256(Buffer.concat([Buffer.from(d,"hex"),u(64),u(p.leaves.length),...p.leaves.map(v=>Buffer.from(v,"hex"))]));console.log(JSON.stringify({d,r}))})'''
calculated = json.loads(subprocess.run(["node", "-e", node], input=json.dumps({"domain": DOMAIN, "leaves": record["keccak256"]}), text=True, capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node_modules)}).stdout)
assert record["dboot"] == calculated["d"] and record["bootstrapRoot"] == calculated["r"]

initial_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
initial_driver = (parent / "canonical-driver.go.txt").read_text()
if not built:
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == initial_coord
    assert (stage / "tools/Go.txt").read_text() == initial_driver
else:
    pins = json.loads(pins_path.read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"]); bootstrap_sha["System"] = SYSTEM_SHA256
    expected_pins = {"phase": "built", "basis": "1b178a6eb", "parentEvidence": "parent-1b178a6eb/artifacts/{engine,coordinator}/MCEntry*.sol", "domain": DOMAIN, "bootstrapCount": 94, "bootstrapRoot": record["bootstrapRoot"], "bootstrapSHA256": bootstrap_sha, "globalNativeBindings": 16, "stringLocalBinding": 11, "exceptionKinds": 14, "maxFrames": 128, "rawLimits": [52, 329162], "diagnosticClassBound": 146, "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000, "runtimeCap": 393216, "address": ADDRESS, "owner": OWNER, "engine": pins["engine"], "coordinator": pins["coordinator"], "worker": "system-set-out"}
    assert pins == expected_pins == json.loads((stage / "build-pins.json").read_text())
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] == 5394
    expected_coord = initial_coord.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"]).replace(parent_pins["address"][2:], ADDRESS[2:]).replace(parent_pins["domain"], DOMAIN)
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == expected_coord
    expected_driver = initial_driver
    for old, new in ((parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]), ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]), ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]), (parent_pins["address"], ADDRESS), (parent_pins["owner"], OWNER)):
        assert expected_driver.count(old) == 1; expected_driver = expected_driver.replace(old, new)
    assert expected_driver.count(parent_pins["domain"]) == 6
    expected_driver = expected_driver.replace(parent_pins["domain"], DOMAIN)
    for pattern, replacement in ((r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]), (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]), (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"])):
        expected_driver, count = re.subn(pattern, replacement, expected_driver); assert count == 1
    assert (stage / "tools/Go.txt").read_text() == expected_driver

focused = (stage / "tools/generate_focused_fixtures.py").read_text()
for exact in ("SystemSetOutMain", "System.setOut(direct)", "System.setOut(child)", "System.setOut(null)", "System.setOut(original)", "RawSystemSetOutReplacementMain"):
    assert exact in focused, exact
assert "setErr" not in focused and "seterr" not in focused
gate = (stage / "tools/gate.py").read_text()
for exact in ("q_system_set_out()", "_system_set_out_heap", "raw-system-setout", "globalNativeBindings"):
    assert exact in gate, exact
assert "Binding15 resolves exactly public static native System.setOut" not in gate
assert not any(path.suffix in {".class", ".jar", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"phase": "built" if built else "prebuild", "systemBytes": len(system_class), "systemSHA256": SYSTEM_SHA256, "systemKeccak256": SYSTEM_KECCAK, "changedRootLeaves": [44], "bootstrapRoot": record["bootstrapRoot"], "globalNativeBindings": 16}, indent=2))
