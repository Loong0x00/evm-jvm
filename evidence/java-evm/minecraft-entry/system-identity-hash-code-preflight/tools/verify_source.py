#!/usr/bin/env python3
"""Verify the one-binding System.identityHashCode delta from raw70 capacity.

Only checked-in stage sources, the prior generated capacity stage, and locally
compiled Java-8 bootstrap source are read. No original/JAR/external class,
resource, network, or provider input is opened or evaluated.
"""
from pathlib import Path
import copy
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
parent = stage.parent / "classcount70-byte464925-preflight"
assert len(sys.argv) == 3 and sys.argv[1] == "--built"
assert Path(sys.argv[2]).resolve() == stage / "build-pins.json"

DOMAIN = "MC-SYSTEM-IDENTITY-HASH-P1"
OLD_DOMAIN = "MC-STRING-LOWER-LOCALE-P2"
SYSTEM_SHA256 = "6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564"
SYSTEM_KECCAK = "1850d01a1f91f51d1e7e8e82de2f92ceb319a879d52b77f8892b237e5188eef3"
ROOT = "6fbfed767949708bacc0aebb58173f63c46bfd0b84cb0c5ac3a15f461c8a4a77"
ENGINE = {
    "bytes": 380017,
    "initSHA256": "c9e415cbe7de764340e112ff74ce145e4f533b5f117530f2f85bd9e50b15c730",
    "runtimeSHA256": "e49f015dfa4712e864e54d35a56a7bd2a81c54b3ccfe6a5f6dbc5e6179841d2c",
    "runtimeKeccak256": "9c0a28736c5f76856a776f10b3ca7b0d0ae1d0e5956a73cb610c8e3e669ce0dd",
}
COORDINATOR = {
    "bytes": 5394,
    "initSHA256": "1025297a5dd9290da5ff77dbbd9c9b421481b9e28f9e7281c0326ef067e6d025",
    "runtimeSHA256": "e1f303928862914957ddfd53f2e0481fd8626efa95882cc78c899c95d9e3a0c1",
    "runtimeKeccak256": "22ca65e89aba1db7ed358923e4f4b98e8632a4ca29356678ffdf939c67439b47",
}
ADDRESS = "0x4d432d53595354454d2d4944454e544954593137"
OWNER = "0x4d432d53595354454d2d4944454e544954593138"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(text, old, new, count=1):
    actual = text.count(old)
    assert actual == count, (old[:96], actual, count)
    return text.replace(old, new)


def function_image(text, function):
    start = text.index("function " + function + "(")
    end = text.find("\n    function ", start + 1)
    values = re.findall(r'hex"([0-9a-f]+)"', text[start:end if end >= 0 else len(text)])
    assert len(values) == 1, (function, len(values))
    return bytes.fromhex(values[0])


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
            for _ in range(attrs):
                _, at = u2(at); size, at = u4(at); at += size
            result.append((flags, utf(name), utf(desc)))
        return result
    fields = members(); methods = members(); attrs, at = u2(at)
    for _ in range(attrs):
        _, at = u2(at); size, at = u4(at); at += size
    assert at == len(data)
    return {"count": count, "access": access, "fields": fields, "methods": methods}


parent_pins = json.loads((parent / "build-pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
assert parent_pins["rawLimits"] == [70, 464925]
assert parent_pins["diagnosticClassBound"] == 166 and parent_pins["bootstrapCount"] == 96
assert parent_pins["globalNativeBindings"] == 16 and parent_pins["stringLocalBinding"] == 12
assert parent_pins["bootstrapRoot"] == "39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18"
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({
    "basis": "classcount70-byte464925-preflight",
    "parentEvidence": "classcount70-byte464925-preflight/{engine,coordinator,tools,build-pins,root-commitment}",
    "domain": DOMAIN, "bootstrapRoot": ROOT, "globalNativeBindings": 17,
    "address": ADDRESS, "owner": OWNER, "engine": ENGINE, "coordinator": COORDINATOR,
    "worker": "system-identity-hash-code",
    "system": {"slot": 44, "bytes": 1113, "sha256": SYSTEM_SHA256,
        "keccak256": SYSTEM_KECCAK,
        "surface": "currentTimeMillis, arraycopy, setErr, setOut, getSecurityManager, getProperty, and exact native identityHashCode(Object) only",
        "java8": "javac -source 8 -target 8 -g:none"},
})
expected_pins["bootstrapSHA256"] = dict(parent_pins["bootstrapSHA256"])
expected_pins["bootstrapSHA256"]["System"] = SYSTEM_SHA256
assert pins == expected_pins
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128

# The exact Java 8 input extends only the canonical System declaration by the
# one public static native method. PrintStream is a checked-in compile-only
# dependency and its emitted image must remain the parent's exact leaf.
source = (stage / "bootstrap/java/lang/System.java").read_text()
expected_source = """package java.lang;

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

    /** Returns the stable VM-owned guest handle for this reference, or zero for null. */
    public static native int identityHashCode(Object value);

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
assert source == expected_source
for forbidden in ("hashCode()", "Object.hashCode", "synchronized", "gc(", "Console", "File"):
    assert forbidden not in source, forbidden
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac"); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="system-identity-hash-verify-", dir=root / "build") as name:
    tmp = Path(name); system_src = tmp / "src/java/lang/System.java"; stream_src = tmp / "src/java/io/PrintStream.java"
    system_src.parent.mkdir(parents=True); stream_src.parent.mkdir(parents=True)
    system_src.write_text(source); stream_src.write_text((stage / "bootstrap/java/io/PrintStream.java").read_text())
    output = tmp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, system_src, stream_src], check=True)
    system_class = (output / "java/lang/System.class").read_bytes()
assert len(system_class) == 1113 and sha(stage / "bootstrap/java/lang/System.class.hex") != ""
assert hashlib.sha256(system_class).hexdigest() == SYSTEM_SHA256
assert system_class.hex() == "".join((stage / "bootstrap/java/lang/System.class.hex").read_text().split())
assert (stage / "bootstrap/java/lang/System.sha256").read_text().split()[0] == SYSTEM_SHA256
assert hashlib.sha256(function_image((parent / "engine/MCEntryInterpreter.sol").read_text(), "_bootstrapPrintStream")).hexdigest() == parent_pins["bootstrapSHA256"]["PrintStream"]
info = class_info(system_class)
assert info["access"] == 0x31
assert info["fields"] == [
    (0x000a, b"security", b"Ljava/lang/SecurityManager;"),
    (0x000a, b"properties", b"Ljava/util/Properties;"),
    (0x0019, b"err", b"Ljava/io/PrintStream;"),
    (0x0019, b"out", b"Ljava/io/PrintStream;"),
]
assert info["methods"] == [
    (0x0002, b"<init>", b"()V"), (0x0009, b"currentTimeMillis", b"()J"),
    (0x0109, b"arraycopy", b"(Ljava/lang/Object;ILjava/lang/Object;II)V"),
    (0x0109, b"identityHashCode", b"(Ljava/lang/Object;)I"),
    (0x0109, b"setErr", b"(Ljava/io/PrintStream;)V"),
    (0x0109, b"setOut", b"(Ljava/io/PrintStream;)V"),
    (0x0009, b"getSecurityManager", b"()Ljava/lang/SecurityManager;"),
    (0x0009, b"getProperty", b"(Ljava/lang/String;)Ljava/lang/String;"), (0x0008, b"<clinit>", b"()V"),
]

# Reconstruct every allowed semantic/source adjustment exactly from the frozen
# raw70 source: stage domain, the System image, binding17 recognition/signature,
# and its read-only static dispatch. No other interpreter behavior is admitted.
parent_engine = (parent / "engine/MCEntryInterpreter.sol").read_text()
engine = exact(parent_engine, OLD_DOMAIN, DOMAIN, 9)
old_system = function_image(engine, "_bootstrapSystem").hex()
assert hashlib.sha256(bytes.fromhex(old_system)).hexdigest() == parent_pins["bootstrapSHA256"]["System"]
engine = exact(engine, old_system, system_class.hex())
old = '''            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("setOut"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/io/PrintStream;)V"))) return 16;
'''
new = old + '''            // Binding17 returns only the already-valid guest handle as an int.
            // It neither invokes Object.hashCode nor allocates or mutates guest state.
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("identityHashCode"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/Object;)I"))) return 17;
'''
engine = exact(engine, old, new)
engine = exact(engine,
    '''                && binding != 14 && binding != 15 && binding != 16 && s.argumentKinds.length != 1)''',
    '''                && binding != 14 && binding != 15 && binding != 16 && binding != 17
                && s.argumentKinds.length != 1)''')
engine = exact(engine,
    '''            || (binding == 16 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 2
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/io/PrintStream;"))))) {''',
    '''            || (binding == 16 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 2
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/io/PrintStream;"))))
            || (binding == 17 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 1
                || s.returnSubtype != uint8(bytes1("I"))
                || !_equalsLiteral(c.data, s.argumentTypeOffsets[0], s.argumentTypeLengths[0],
                    bytes("Ljava/lang/Object;"))))) {''')
old = '''                    if (nativeBinding == 16) {
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
new = old + '''                    if (nativeBinding == 17) {
                        // Argument shape/assignability was checked above. Validate the
                        // exact packed guest reference again before exposing its stable
                        // low uint32 handle; zero maps to Java's required zero result.
                        // This reads only the existing heap frontier: no host identity,
                        // hashCode dispatch, allocation, initialization or mutation.
                        _validatePackedRef(f.stack[base], heapKinds, nextHandle, opPC);
                        f.stack[base] = _packInt(uint32(_payload(f.stack[base])));
                        f.sp = base + 1;
                        continue;
                    }
'''
engine = exact(engine, old, new)
assert (stage / "engine/MCEntryInterpreter.sol").read_text() == engine
assert "return 17;" in engine and engine.count("nativeBinding == 17") == 1
assert engine.count("_validatePackedRef(f.stack[base], heapKinds, nextHandle, opPC);") == 1
native_start = engine.index("function _nativeBinding")
native_end = engine.index("function _canonicalSystemErrField", native_start)
assert 'bytes("hashCode")' not in engine[native_start:native_end] and "hashCode dispatch" in engine
for fixed in ("MAX_RAW_CLASSES = 70;", "MAX_RAW_BYTES = 464925;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;", "new bytes32[](96)", "new uint256[](14)"):
    assert engine.count(fixed) == 1, fixed

# Independently enumerate the ordered bootstrap images from actual Solidity.
def root_leaves(text):
    body = text[text.index("function _bootstrapRoot"):text.index("function _prepare")]
    assignments = re.findall(r'h\[(\d+)\] = (?:keccak256\()?(?:(_[A-Za-z0-9]+)\(\)|(DBOOT_[A-Z_]+))(?:\))?;', body)
    assert len(assignments) == 96 and [int(index) for index, _, _ in assignments] == list(range(96))
    leaves = []
    for _, function, constant in assignments:
        if function:
            leaves.append({"image": function_image(text, function).hex()})
        else:
            at = text.index("bytes32 private constant " + constant)
            declaration = text[at:text.index(";", at)]
            folded = re.search(r'keccak256\(hex"([0-9a-f]+)"\)', declaration)
            literal = re.search(r'= hex"([0-9a-f]+)"', declaration)
            assert folded or literal, constant
            leaves.append({"image": folded.group(1)} if folded else {"hash": literal.group(1)})
    return leaves

parent_leaves, leaves = root_leaves(parent_engine), root_leaves(engine)
node_modules = root / "jvmevm/runtime/node_modules"; assert node_modules.is_dir()
node = '''const{keccak256}=require("js-sha3");const p=JSON.parse(process.argv[1]),w=x=>x.padStart(64,"0"),h=p.l.map(x=>x.image?keccak256(Buffer.from(x.image,"hex")):x.hash),d=keccak256("JVMEVM:"+p.d+":BOOTSTRAP:1"),r=keccak256(Buffer.from(w(d)+w("40")+w(h.length.toString(16))+h.map(w).join(""),"hex"));console.log(JSON.stringify({dboot:d,keccak256:h,bootstrapRoot:r}));'''
calculated = json.loads(subprocess.check_output(["node", "-e", node, json.dumps({"d": DOMAIN, "l": leaves})], cwd=root, env={**os.environ, "NODE_PATH": str(node_modules)}, text=True))
record = json.loads((stage / "root-commitment.json").read_text())
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 96
assert record["order"] == json.loads((parent / "root-commitment.json").read_text())["order"]
assert record["dboot"] == calculated["dboot"] and record["keccak256"] == calculated["keccak256"] and record["bootstrapRoot"] == calculated["bootstrapRoot"] == ROOT
changed = [index for index, (before, after) in enumerate(zip(root_leaves(parent_engine), leaves)) if before != after]
assert changed == [44] and calculated["keccak256"][44] == SYSTEM_KECCAK
assert hashlib.sha256(function_image(engine, "_bootstrapString")).hexdigest() == pins["string"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapLocale")).hexdigest() == pins["locale"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapMapEntry")).hexdigest() == pins["mapEntry"]["sha256"]
assert hashlib.sha256(function_image(engine, "_bootstrapInteger")).hexdigest() == pins["integer"]["sha256"]

# Coordinator and driver receive only the rebuilt engine identity plus their
# independent local domain/address identities. Capacity and checkpoint guards
# are byte-for-byte retained.
parent_coord = (parent / "coordinator/MCEntryCoordinator.sol").read_text()
coord = exact(parent_coord, OLD_DOMAIN, DOMAIN, 4)
coord = exact(coord, parent_pins["engine"]["runtimeKeccak256"], ENGINE["runtimeKeccak256"])
coord = exact(coord, parent_pins["address"][2:], ADDRESS[2:])
assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == coord
parent_go = (parent / "tools/Go.txt").read_text()
go = exact(parent_go, OLD_DOMAIN, DOMAIN, 6)
go = exact(go, parent_pins["engine"]["runtimeSHA256"], ENGINE["runtimeSHA256"])
go = exact(go, "0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + ENGINE["runtimeKeccak256"])
go = exact(go, "0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + COORDINATOR["runtimeKeccak256"])
go = exact(go, parent_pins["address"], ADDRESS)
go = exact(go, parent_pins["owner"], OWNER)
go = exact(go, "379383", "380017", 2)
assert (stage / "tools/Go.txt").read_text() == go
for name in ("engine/build.js", "coordinator/build.js"):
    assert (stage / name).read_bytes() == (parent / name).read_bytes(), name
for name in ("checkpoint_frames.py", "verify_receipts.js"):
    assert (stage / "tools" / name).read_bytes() == (parent / "tools" / name).read_bytes(), name
checkpoint = (stage / "tools/checkpoint_diagnostic.py").read_text()
assert "classes<=166" in checkpoint and "nextHandle" in checkpoint and "diagnostic transport metadata only" in checkpoint

fixtures = (stage / "tools/generate_fixtures.py").read_text()
for fragment in ("identity-hash", "identity-no-mutation-control", "identityHashCode", "object-hashcode-omitted", "system-general-omitted", "raw-system-replacement", "retained-system-out-err", "count_fixture(\"count-70\", 70)"):
    assert fragment in fixtures, fragment
gate = (stage / "tools/gate.py").read_text()
for fragment in ("globalNativeBindings\"] == 17", "identity_state", "identity-no-mutation-control", "raw-system-replacement", "object-hashcode-omitted", "system-general-omitted", "count-70-464925", "<= 1200"):
    assert fragment in gate, fragment
assert not any(path.suffix in {".class", ".jar", ".zip"} for path in stage.rglob("*"))

print(json.dumps({
    "basis": pins["basis"], "systemSHA256": SYSTEM_SHA256, "systemKeccak256": SYSTEM_KECCAK,
    "changedBootstrapLeaves": changed, "bootstrapRoot": ROOT, "globalNativeBindings": 17,
    "stringLocalBinding": 12, "rawLimits": pins["rawLimits"], "diagnosticClassBound": 166,
    "verification": "exact-System-image-and-binding17+independent-96-leaf-root+non-System-images+generated-input-only",
}, indent=2))
