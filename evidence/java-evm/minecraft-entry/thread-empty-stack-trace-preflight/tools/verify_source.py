#!/usr/bin/env python3
"""Strict source pins for bounded Thread.getStackTrace empty arrays.

The only guest-image changes from accepted parent-bd1760569 are Thread slot50
and append-only StackTraceElement slot90. The sole engine layout cleanup folds
the private _execute bundleMode argument, whose two and only callers pass true,
into the one static invocation path. No external ABI, limit, or commitment is
removed or changed.
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
parent = stage.parent / "parent-bd1760569"

PARENT = {
    "artifacts/engine/MCEntryInterpreter.sol": "993589815d381149f8edb250d640ca57b31e34c0e6a75b98cd82a1c060118e7c",
    "artifacts/coordinator/MCEntryCoordinator.sol": "85439482cc63de524139d313b3096b9916ab05704147c4855d4d66b49c2a2bbe",
    "canonical-driver.go.txt": "fe55d5901ce93c74b755c67f3163e7f18e6e43b592d5b2f58550183c7b02e6aa",
    "checkpoint_diagnostic.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "checkpoint_frames.py": "1b80a529f8831b6b53f3be3ddbeb530df058f24f177b712de59cc76482e4509b",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
PARENT_DOMAIN = "MC-SB-CHARSEQ-RANGE0-Q"
DOMAIN = "MC-THREAD-EMPTY-TRACE0"
PARENT_ENGINE = "4d432d53422d434841525345512d52414e474532"
PARENT_OWNER = "4d432d53422d434841525345512d52414e474533"
ENGINE = "4d432d5448524541442d54524143452d454e4730"
OWNER = "4d432d5448524541442d54524143452d4f574e30"
THREAD_SHA256 = "7cd2263dd09f01a4e0d69601c0db63704eadf5461709f3b93b718352589163fd"
STACK_TRACE_ELEMENT_SHA256 = "93235091dce65ab80a51b88fc294533e0a65bc2eefe0c02d052892bcde103a3c"
ROOT = "c8f6dad01aaba24b276dd90b4b4bf84ca74c9ae0586612bffa675f66fe7001fe"

THREAD_SOURCE = """package java.lang;

/** Single guest current thread; no scheduler, host callback, or loader installation. */
public final class Thread {
    private static final Thread CURRENT = new Thread();
    private ClassLoader contextClassLoader;

    private Thread() { super(); }

    public static Thread currentThread() { return CURRENT; }

    public ClassLoader getContextClassLoader() { return contextClassLoader; }

    /** Bounded optional-caller-location surface: no guest frame snapshots are exposed. */
    public StackTraceElement[] getStackTrace() { return new StackTraceElement[0]; }
}
"""
STACK_TRACE_ELEMENT_SOURCE = """package java.lang;

/** Canonical empty-array leaf only; element construction and APIs are absent. */
public final class StackTraceElement {
    private StackTraceElement() {}
}
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_images(text):
    result = {}
    for name, image in re.findall(
        r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{[\s\S]*?return hex\"([0-9a-f]+)\";",
        text,
        re.S,
    ):
        assert name not in result
        result[name] = image
    return result


def root_rows(text):
    begin = text.index("    function _bootstrapRoot() private pure returns (bytes32) {")
    end = text.index("\n    function _prepare(", begin)
    rows = re.findall(r"h\[(\d+)\] = ([^;]+);", text[begin:end])
    return rows, text[begin:end]


def root_order(rows):
    special = {"DBOOT_ENUMSET": "EnumSet", "DBOOT_ITERABLE": "Iterable", "DBOOT_MATH": "Math", "DBOOT_THREAD": "Thread", "DBOOT_THREAD_LOCAL": "ThreadLocal", "DBOOT_STACK_TRACE_ELEMENT": "StackTraceElement"}
    result = []
    for _, value in rows:
        found = re.search(r"_bootstrap(\w+)\(\)", value)
        result.append(found.group(1) if found else special[value.strip()])
    return result


def commitment(images, order):
    node_modules = root / "jvmevm/runtime/node_modules"
    assert node_modules.is_dir(), "refusing shared or network Node dependencies"
    payload = {"domain": DOMAIN, "images": [images["_bootstrap" + name] for name in order]}
    script = r'''const fs=require("fs"),{keccak256}=require("js-sha3");
const x=JSON.parse(fs.readFileSync(0,"utf8"));const word=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};
const h=x.images.map(v=>keccak256(Buffer.from(v,"hex")));const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));
process.stdout.write(JSON.stringify({dboot:d,root:keccak256(Buffer.concat([Buffer.from(d,"hex"),word(64),word(h.length),...h.map(v=>Buffer.from(v,"hex"))])),hashes:h}));'''
    result = subprocess.run(
        ["node", "-e", script], input=json.dumps(payload), text=True, capture_output=True, check=True,
        env={**os.environ, "NODE_PATH": str(node_modules)},
    )
    return json.loads(result.stdout)


inputs = {name: digest(parent / name) for name in PARENT}
assert inputs == PARENT
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "bd1760569", "parentEvidence": "parent-bd1760569", "sha256": inputs,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(PARENT_OWNER)) == 20
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["engine"]["bytes"] == 393185 and parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [37, 282358]
assert parent_pins["diagnosticClassBound"] == 127 and parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10 and parent_pins["exceptionKinds"] == 14

assert (stage / "bootstrap/java/lang/Thread.java").read_text() == THREAD_SOURCE
assert (stage / "bootstrap/java/lang/StackTraceElement.java").read_text() == STACK_TRACE_ELEMENT_SOURCE
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="thread-empty-stack-trace-verify-", dir=root / "build") as temp_name:
    temp = Path(temp_name)
    source_dir = temp / "java/lang"; source_dir.mkdir(parents=True)
    (source_dir / "Thread.java").write_text(THREAD_SOURCE)
    (source_dir / "StackTraceElement.java").write_text(STACK_TRACE_ELEMENT_SOURCE)
    out = temp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out,
                    source_dir / "Thread.java", source_dir / "StackTraceElement.java"], check=True)
    thread_image = (out / "java/lang/Thread.class").read_bytes()
    stack_image = (out / "java/lang/StackTraceElement.class").read_bytes()
assert len(thread_image) == 565 and hashlib.sha256(thread_image).hexdigest() == THREAD_SHA256
assert len(stack_image) == 142 and hashlib.sha256(stack_image).hexdigest() == STACK_TRACE_ELEMENT_SHA256
assert thread_image.hex() == (stage / "bootstrap/java/lang/Thread.class.hex").read_text().strip()
assert stack_image.hex() == (stage / "bootstrap/java/lang/StackTraceElement.class.hex").read_text().strip()
assert b"getStackTrace" in thread_image and b"[Ljava/lang/StackTraceElement;" in thread_image
assert b"start" not in thread_image and b"sleep" not in thread_image and b"run" not in thread_image
assert b"getClassName" not in stack_image and b"getMethodName" not in stack_image
assert b"(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)V" not in stack_image

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent_images = source_images(parent_engine)
assert len(bytes.fromhex(parent_images["_bootstrapThread"])) == 450
expected_engine = parent_engine.replace(PARENT_DOMAIN, DOMAIN).replace(parent_images["_bootstrapThread"], thread_image.hex())
for old, new in (
    ("bytes32[] memory h = new bytes32[](90);", "bytes32[] memory h = new bytes32[](91);"),
    ("""        h[89] = DBOOT_MATH;
        return keccak256(abi.encode(DBOOT, h));""", """        h[89] = DBOOT_MATH;
        h[90] = keccak256(_bootstrapStackTraceElement());
        return keccak256(abi.encode(DBOOT, h));"""),
    ("uint256 count = inputCount + 84 + (suppliedObject ? 0 : 1)", "uint256 count = inputCount + 85 + (suppliedObject ? 0 : 1)"),
    ("""        return _isNamedClass(c, bytes("java/lang/Thread"))
            || _isNamedClass(c, bytes("java/lang/ThreadLocal"))""", """        return _isNamedClass(c, bytes("java/lang/Thread"))
            || _isNamedClass(c, bytes("java/lang/StackTraceElement"))
            || _isNamedClass(c, bytes("java/lang/ThreadLocal"))"""),
    ("""        // Math remains the final append-only slot89; isolate its image materialization
        // after pinned metadata assignments to retain the fixed LOCAL384 code layout.
        p.classes[classSlot + 50].data = _bootstrapMath();
    }

    function _bootstrapReflectiveOperationException()""", """        p.classes[classSlot + 50].data = _bootstrapMath();
        p.classes[classSlot + 51].data = _bootstrapStackTraceElement();
    }

    function _bootstrapReflectiveOperationException()"""),
    ("""    function _bootstrapThread() private pure returns (bytes memory) { return hex\"%s\"; }

    /// @dev Minimal Java 8 Properties family""" % thread_image.hex(), """    function _bootstrapThread() private pure returns (bytes memory) { return hex\"%s\"; }

    function _bootstrapStackTraceElement() private pure returns (bytes memory) { return hex\"%s\"; }

    /// @dev Minimal Java 8 Properties family""" % (thread_image.hex(), stack_image.hex())),
    # _execute never reads rootMethod or throwableBootstrapAt: both were
    # mechanically threaded through the two private callers only. Drop them
    # while retaining the literal-true bundleMode behavior exactly.
    ("""            p.rootClass, p.rootMethod, true, p.throwableBootstrapAt, p.rawClassCount, p.loaderClass,""", """            p.rootClass, true, p.rawClassCount, p.loaderClass,"""),
    ("""        uint256 rootClass,
        uint256 root,
        bool bundleMode,
        uint256 throwableBootstrapAt,""", """        uint256 rootClass,
        bool bundleMode,"""),
    # _allocateMultiArray similarly never reads the heapKinds parameter.
    ("""                    arrayHeap, heapKinds, arrayRanks, arrayLeafTypes,""", """                    arrayHeap, arrayRanks, arrayLeafTypes,"""),
    ("""        uint64[][] memory arrayHeap, uint256[] memory heapKinds,
        uint8[] memory arrayRanks, uint256[] memory arrayLeafTypes,""", """        uint64[][] memory arrayHeap, uint8[] memory arrayRanks, uint256[] memory arrayLeafTypes,"""),
):
    count = 2 if old.startswith("            p.rootClass") else 1
    assert expected_engine.count(old) == count, old[:80]
    expected_engine = expected_engine.replace(old, new)
# Constant expressions below are exactly the corresponding materialized image
# hashes. They are only compiler-layout cleanup; _bootstrapRoot remains derived.
for old, new in (
    ("""    bytes32 private constant DBOOT_ITERABLE = keccak256(hex\"cafebabe00000034000a0700080700090100086974657261746f7201001628294c6a6176612f7574696c2f4974657261746f723b0100095369676e617475726501001b28294c6a6176612f7574696c2f4974657261746f723c54543b3e3b0100283c543a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b0100126a6176612f6c616e672f4974657261626c650100106a6176612f6c616e672f4f626a6563740601000100020000000000010401000300040001000500000002000600010005000000020007\");""", """    bytes32 private constant DBOOT_ITERABLE = keccak256(hex\"cafebabe00000034000a0700080700090100086974657261746f7201001628294c6a6176612f7574696c2f4974657261746f723b0100095369676e617475726501001b28294c6a6176612f7574696c2f4974657261746f723c54543b3e3b0100283c543a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b0100126a6176612f6c616e672f4974657261626c650100106a6176612f6c616e672f4f626a6563740601000100020000000000010401000300040001000500000002000600010005000000020007\");
    // Exact hashes of the two materialized Java 8 images below. The ordered root remains derived at runtime.
    bytes32 private constant DBOOT_THREAD = hex\"5b69bdf77be902d446ec0bf3a58c69bff4db5e1255558b7d92f8a29cc7a74ae6\";
    bytes32 private constant DBOOT_STACK_TRACE_ELEMENT = hex\"352c22e6449ab24ec8b39389c0b7ad9cf19d8b19263d5d81ab205447b137619e\";
    bytes32 private constant DBOOT_THREAD_LOCAL = hex\"93a0007b6336f667890f5afa2b01572278a7e39ab93b2faf1095e054317f538a\";"""),
    ("h[50] = keccak256(_bootstrapThread());", "h[50] = DBOOT_THREAD;"),
    ("h[88] = keccak256(_bootstrapThreadLocal());", "h[88] = DBOOT_THREAD_LOCAL;"),
    ("""        h[90] = keccak256(_bootstrapStackTraceElement());""", """        // StackTraceElement appends as the canonical leaf of Thread's empty array.
        h[90] = DBOOT_STACK_TRACE_ELEMENT;"""),
    ("""        p.classes[classSlot + 50].data = _bootstrapMath();
        p.classes[classSlot + 51].data = _bootstrapStackTraceElement();""", """        // Math remains at slot89 and StackTraceElement appends at slot90 as
        // Thread.getStackTrace's canonical empty-array leaf.
        p.classes[classSlot + 50].data = _bootstrapMath();
        p.classes[classSlot + 51].data = _bootstrapStackTraceElement();"""),
    ("""    function _bootstrapStackTraceElement() private pure returns (bytes memory) { return hex\"%s\"; }""" % stack_image.hex(), """    // Java 8 Object subclass kept only as Thread.getStackTrace's array leaf.
    // The private no-arg constructor and all element APIs are intentionally absent.
    function _bootstrapStackTraceElement() private pure returns (bytes memory) { return hex\"%s\"; }""" % stack_image.hex()),
):
    assert expected_engine.count(old) == 1, old[:80]
    expected_engine = expected_engine.replace(old, new)
assert engine == expected_engine
images = source_images(engine)
assert set(images) == set(parent_images) | {"_bootstrapStackTraceElement"}
for name, old in parent_images.items():
    assert images[name] == (thread_image.hex() if name == "_bootstrapThread" else old), name
assert images["_bootstrapStackTraceElement"] == stack_image.hex()
parent_rows, _ = root_rows(parent_engine)
rows, root_source = root_rows(engine)
assert len(parent_rows) == 90 and [int(i) for i, _ in parent_rows] == list(range(90))
assert len(rows) == 91 and [int(i) for i, _ in rows] == list(range(91))
assert root_order(rows)[:90] == root_order(parent_rows) and root_order(rows)[50] == "Thread" and root_order(rows)[90] == "StackTraceElement"
assert "return keccak256(abi.encode(DBOOT, h));" in root_source and ROOT not in engine
for fixed in (
    "MAX_RAW_CLASSES = 37;", "MAX_RAW_BYTES = 282358;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "return 13;", "new uint256[](14)",
    "uint32(37), uint32(282358)",
):
    assert engine.count(fixed) == 1, fixed
record = commitment(images, root_order(rows))
root_record = json.loads((stage / "root-commitment.json").read_text())
assert record["root"] == ROOT == root_record["bootstrapRoot"]
assert record["dboot"] == root_record["dboot"] and record["hashes"] == root_record["keccak256"]
assert root_record["domain"] == DOMAIN and root_record["bootstrapCount"] == 91 and root_record["order"] == root_order(rows)
assert root_record["thread"] == {"slot": 50, "bytes": 565, "sha256": THREAD_SHA256, "keccak256": record["hashes"][50]}
assert root_record["stackTraceElement"] == {"slot": 90, "bytes": 142, "sha256": STACK_TRACE_ELEMENT_SHA256, "keccak256": record["hashes"][90]}

coordinator_parent = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = coordinator_parent.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
driver_parent = (parent / "canonical-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = driver_parent.replace(PARENT_DOMAIN, DOMAIN).replace("0x" + PARENT_ENGINE, "0x" + ENGINE).replace("0x" + PARENT_OWNER, "0x" + OWNER)
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
assert driver.count(DOMAIN) == 6 and driver.count("0x" + ENGINE) == 1 and driver.count("0x" + OWNER) == 1
for stage_name, parent_name in (("checkpoint_diagnostic.py", "checkpoint_diagnostic.py"), ("checkpoint_frames.py", "checkpoint_frames.py")):
    expected_tool = (parent / parent_name).read_text().replace("classes<=127", "classes<=128")
    assert (stage / "tools" / stage_name).read_text() == expected_tool
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
for stage_name, parent_name in (("engine/build.js", "artifacts/engine/build.js"), ("coordinator/build.js", "artifacts/coordinator/build.js")):
    assert (stage / stage_name).read_bytes() == (parent / parent_name).read_bytes()
for script_name in ("generate_fixtures.py", "gate.py"):
    script = (stage / "tools" / script_name).read_text()
    assert "original" in script and "MinecraftServer" not in script
fixtures_source = (stage / "tools/generate_fixtures.py").read_text()
gate_source = (stage / "tools/gate.py").read_text()
for label in ("thread-empty-stack-trace", "thread-empty-stack-trace-uninitialized", "raw-stacktraceelement", "stacktraceelement-constructor-omitted", "stacktraceelement-method-omitted"):
    assert '"' + label + '"' in fixtures_source
assert 'bootstrap_count=91' in fixtures_source and '"bootstrapCount": 91' in fixtures_source
assert 'q_equivalent("thread-empty-stack-trace", "thread-empty-stack-trace", thread_empty_stack_trace_initialized)' in gate_source
assert 'raw + 90 not in states' in gate_source
assert 'raw-stacktraceelement-replacement' in gate_source and 'stacktraceelement-method-omitted' in gate_source
assert 'pins["bootstrapCount"] == 91' in gate_source and 'pins["diagnosticClassBound"] == 128' in gate_source

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert coordinator == expected_coordinator and driver == expected_driver
    assert not (stage / "build-pins.json").exists()
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    expected = {
        "basis": "bd1760569", "parentEvidence": "parent-bd1760569", "phase": "built", "domain": DOMAIN,
        "runtimeBaseline": 393185, "runtimeCap": 393216, "bootstrapCount": 91,
        "bootstrapSHA256": {**parent_pins["bootstrapSHA256"], "Thread": THREAD_SHA256, "StackTraceElement": STACK_TRACE_ELEMENT_SHA256},
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14, "maxFrames": 128,
        "externalLocalGas": 1000000000, "reserve": 25000000, "rawLimits": [37, 282358],
        "checkpointCap": 1048576, "headCap": 32768, "diagnosticClassBound": 128,
        "address": "0x" + ENGINE, "owner": "0x" + OWNER, "limitsCommitment": parent_pins["limitsCommitment"],
        "compiler": parent_pins["compiler"], "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] == 5394
    assert coordinator == expected_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    final_driver = expected_driver
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
    assert driver == final_driver and json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-bd1760569", "phase": phase, "domain": DOMAIN, "bootstrapImages": 91,
    "thread": {"slot": 50, "bytes": 565, "sha256": THREAD_SHA256},
    "stackTraceElement": {"slot": 90, "bytes": 142, "sha256": STACK_TRACE_ELEMENT_SHA256},
    "bootstrapRoot": ROOT, "rawLimits": [37, 282358], "diagnosticClassBound": 128,
    "runtimeBaseline": 393185, "runtimeCap": 393216, "globalNativeBindings": 13, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
