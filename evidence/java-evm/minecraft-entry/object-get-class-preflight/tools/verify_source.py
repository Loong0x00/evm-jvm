#!/usr/bin/env python3
"""Strict source verifier for bounded Object.getClass binding13.

It consumes only accepted raw32 parent evidence and the local generated-only
stage source. It never opens an original artifact, JAR, class, resource,
checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-5f01fbbdf"

PARENT_FILES = {
    "pins.json": "e1f304d08f69f82be99f61f90ce886c4c05465d877a66600b1bc218f89506ba2",
    "artifacts/engine/MCEntryInterpreter.sol": "7dacd6b654b1d9effda786c80dc45968f9cec16faae3bb57ca6dc31ab2d2ae6a",
    "artifacts/coordinator/MCEntryCoordinator.sol": "fe8ea5c534df90f69831578ebe391b7db309de0041275d795b107c5eab06d7a7",
    "executed-driver.go.txt": "77d12cec2832f4b872690c90c481b87cb88ad6fb4d9c958b5e27d50bec9671e9",
    "checkpoint_diagnostic.py": "53ffb820a44df128a8f684a985d5d05a281a1e7ac04158faa9f11a78ba187fa0",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
PARENT_DOMAIN = "MC-CLASSCOUNT32-P32"
DOMAIN = "MC-OBJECT-GET-CLASS-P1"
PARENT_ENGINE = "4d432d434c415353434f554e5433322d50333201"
ENGINE = "4d432d4f424a4543542d474554434c4153535031"
PARENT_OWNER = "4d432d434c415353434f554e5433322d4f333302"
OWNER = "4d432d4f424a4543542d474554434c4153534f31"
OBJECT_SOURCE = """package java.lang;

/** Java 8 bounded bootstrap Object: only constructor, equals, and getClass. */
public class Object {
    public Object() {}
    public boolean equals(Object other) { return this == other; }
    public final native Class<?> getClass();
}
"""
OBJECT_HEX = (
    "cafebabe00000034000d07000c0100063c696e69743e010003282956010004436f6465"
    "010006657175616c73010015284c6a6176612f6c616e672f4f626a6563743b295a"
    "01000d537461636b4d61705461626c65010008676574436c61737301001328294c"
    "6a6176612f6c616e672f436c6173733b0100095369676e61747572650100162829"
    "4c6a6176612f6c616e672f436c6173733c2a3e3b0100106a6176612f6c616e672f"
    "4f626a656374002100010000000000000003000100020003000100040000000d0000"
    "000100000001b1000000000001000500060001000400000022000200020000000b2a"
    "2ba6000704a7000403ac000000010007000000050002094001011100080009000100"
    "0a00000002000b0000"
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstraps(text):
    pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{.*?return hex"([0-9a-f]+)";'
    return dict(re.findall(pattern, text, flags=re.S))


def replace_one(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    text = text.replace(PARENT_DOMAIN, DOMAIN)
    text = replace_one(text, '''        if (_isNamedClass(c, bytes("java/lang/Float"))) {
''', '''        if (_isNamedClass(c, bytes("java/lang/Object"))) {
            // Binding13 is only the bootstrap Object getClass declaration.  The
            // virtual call site additionally rejects a raw Object replacement,
            // so a user-supplied same-named class can never obtain this native.
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("getClass"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("()Ljava/lang/Class;"))) return 13;
        } else if (_isNamedClass(c, bytes("java/lang/Float"))) {
''')
    text = replace_one(text, '''        // Binding11 is the sole public instance Class native. It has no Code and
        // is intentionally separate from private static Class primitives 9/10.
        if (binding == 11) {
            if (access != 0x0101 || _methodCodeCount(meta) != 0) revert CallError(4, callPC);
            return;
        }
''', '''        // Binding11 is the sole public instance Class native. Binding13 is
        // Object.getClass: both have no Code, but Object requires Java's final
        // modifier so similarly-shaped raw replacements cannot widen the surface.
        if (binding == 11) {
            if (access != 0x0101 || _methodCodeCount(meta) != 0) revert CallError(4, callPC);
            return;
        }
        if (binding == 13) {
            if (access != 0x0111 || _methodCodeCount(meta) != 0) revert CallError(4, callPC);
            return;
        }
''')
    text = replace_one(text, '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && binding != 12
                && s.argumentKinds.length != 1)
''', '''        if ((binding != 5 && binding != 6 && binding != 7 && binding != 8 && binding != 9
                && binding != 10 && binding != 11 && binding != 12 && binding != 13
                && s.argumentKinds.length != 1)
''')
    text = replace_one(text, '''            || (binding == 12 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 3))) {
''', '''            || (binding == 12 && (s.argumentKinds.length != 1
                || s.argumentKinds[0] != KIND_REF || s.returnKind != 3))
            || (binding == 13 && (s.argumentKinds.length != 0 || s.returnKind != 3
                || !_equalsLiteral(c.data, s.returnTypeOffset, s.returnTypeLength,
                    bytes("Ljava/lang/Class;"))))) {
''')
    text = replace_one(text, '''                if (classNativeBinding != 0 && classNativeBinding != 11) revert CallError(4, opPC);
                if (!_selectionLoaded(selected, calleeClass, callee)) {
                    Selected memory loadedTarget = stringBinding != 0
                        ? _loadStringNativeCallee(classes[calleeClass], callee, opPC, calleeClass)
                        : (classNativeBinding == 11
                            ? _loadNativeCallee(classes[calleeClass], callee, opPC)
                            : _loadVirtualCallee(classes[calleeClass], callee, opPC, calleeClass));
''', '''                if (classNativeBinding != 0 && classNativeBinding != 11
                    && classNativeBinding != 13) revert CallError(4, opPC);
                // Binding13 belongs to bootstrap slot0 only. A raw Object
                // replacement may retain ordinary Code, but can never claim the
                // profile native by matching its name and descriptor.
                if (classNativeBinding == 13 && calleeClass < rawClassCount) {
                    revert CallError(4, opPC);
                }
                if (!_selectionLoaded(selected, calleeClass, callee)) {
                    Selected memory loadedTarget = stringBinding != 0
                        ? _loadStringNativeCallee(classes[calleeClass], callee, opPC, calleeClass)
                        : ((classNativeBinding == 11 || classNativeBinding == 13)
                            ? _loadNativeCallee(classes[calleeClass], callee, opPC)
                            : _loadVirtualCallee(classes[calleeClass], callee, opPC, calleeClass));
''')
    text = replace_one(text, '''                    continue;
                }
                if (stringBinding != 0) {
''', '''                    continue;
                }
                if (classNativeBinding == 13) {
                    // Object.getClass is neither active use nor reflection.  It
                    // only exposes the existing canonical guest Class mirror for
                    // the already-allocated receiver dynamic class.  Arrays were
                    // rejected above; Class receivers must themselves be the
                    // validated canonical mirrors, never forged Class objects.
                    if (dynamicClass == arena.classClass) {
                        _canonicalClassMirrorTarget(
                            arena, classes, rawClassCount, loaderClass, handle,
                            parentLinks, hierarchyState, opPC
                        );
                    }
                    (uint256 mirror, bool oom) = _classMirrorForTarget(
                        arena, classes, dynamicClass, rawClassCount, loaderClass,
                        parentLinks, hierarchyState, opPC
                    );
                    if (oom) {
                        f.sp = base;
                        nextHandle = _raiseJava(
                            7, opPC, arena, classes, objectHeap, heapKinds,
                            heapClasses, arrayLeafTypes, parentLinks,
                            hierarchyState, nextHandle
                        );
                        continue;
                    }
                    // The shared allocator owns the first raw loader, mirror and
                    // name allocations; publish its exact arena frontier only on
                    // success. It never initializes the dynamic target.
                    nextHandle = arena.nextHandle;
                    arrayHeap = arena.heap.arrayHeap; objectHeap = arena.heap.objectHeap;
                    arrayLeafTypes = arena.heap.metadata; heapKinds = arrayLeafTypes;
                    heapClasses = arena.heap.classes; arrayRanks = arena.heap.ranks;
                    f.stack[base] = _packRef(uint32(mirror));
                    f.sp = base + 1;
                    continue;
                }
                if (stringBinding != 0) {
''')
    text = replace_one(text, '''    function _bootstrapObject() private pure returns (bytes memory) {
        return hex"cafebabe0000003400090700020100106a6176612f6c616e672f4f626a6563740100063c696e69743e010003282956010004436f6465010006657175616c73010015284c6a6176612f6c616e672f4f626a6563743b295a01000d537461636b4d61705461626c65002100010000000000000002000100030004000100050000000d0000000100000001b1000000000001000600070001000500000022000200020000000b2a2ba6000704a7000403ac0000000100080000000500020940010000";
    }
''', '''    function _bootstrapObject() private pure returns (bytes memory) {
        // Java 8 -g:none source is kept beside this stage at
        // bootstrap/java/lang/Object.java. Slot0 alone changes: constructor and
        // identity equals bytecode remain accepted, getClass is public final native.
        return hex"%s";
    }
''' % OBJECT_HEX)
    return text


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 3 and text.count(PARENT_ENGINE) == 1
    return text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 5 and text.count("0x" + PARENT_ENGINE) == 1
    assert text.count("0x" + PARENT_OWNER) == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER))


def final_driver(text, pins, parent_pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != 4145", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != 387394", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != 387394", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "parent-5f01fbbdf", "parentEvidence": "parent-5f01fbbdf", "sha256": inputs,
}
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 86
assert parent_pins["rawLimits"] == [32, 262144]
assert parent_pins["diagnosticClassBound"] == 118
assert parent_pins["engine"]["bytes"] == 387394
assert parent_pins["coordinator"]["bytes"] == 4145
assert parent_pins["globalNativeBindings"] == 12
assert parent_pins["exceptionKinds"] == 14

assert (stage / "bootstrap/java/lang/Object.java").read_text() == OBJECT_SOURCE
assert (stage / "bootstrap/java/lang/Object.class.hex").read_text() == OBJECT_HEX + "\n"
assert hashlib.sha256(bytes.fromhex(OBJECT_HEX)).hexdigest() == "9e86081e4b58c8cc62f9ae0fa0e8a724e853c5b4875a3f9cd2bf03e26594c1e7"

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine(parent_engine)
parent_images = bootstraps(parent_engine)
images = bootstraps(engine)
assert len(parent_images) == len(images) == 86
assert set(parent_images) == set(images)
for name, image in parent_images.items():
    if name == "_bootstrapObject":
        assert image != OBJECT_HEX and images[name] == OBJECT_HEX
    else:
        assert images[name] == image, name
for fixed in (
    "MAX_RAW_CLASSES = 32;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](86)", "new uint256[](14)", "uint32[11] memory limits",
    "uint32(32), uint32(262144)",
):
    assert engine.count(fixed) == 1, fixed
assert engine.count("return 13;") == 1
assert "access != 0x0111" in engine and "calleeClass < rawClassCount" in engine
assert "_classMirrorForTarget(\n                        arena, classes, dynamicClass" in engine

parent_coordinator = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator(parent_coordinator)
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[32]") == 4 and coordinator.count("n > 32") == 1
assert "262144" in coordinator

parent_driver = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver(parent_driver)
assert driver.count(DOMAIN) == 5 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 32") == 1 and driver.count("len(parts) > 32") == 1
assert (stage / "tools/checkpoint_diagnostic.py").read_bytes() == (parent / "checkpoint_diagnostic.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

prebuild = sys.argv[1:] == ["--prebuild"]
pins_path = stage / "pins.json"
if prebuild:
    assert not pins_path.exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    pins = json.loads(pins_path.read_text())
    bootstrap_sha = dict(parent_pins["bootstrapSHA256"])
    bootstrap_sha["Object"] = hashlib.sha256(bytes.fromhex(OBJECT_HEX)).hexdigest()
    expected_pins = {
        "basis": "parent-5f01fbbdf", "parentEvidence": "parent-5f01fbbdf", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 86,
        "bootstrapSHA256": bootstrap_sha,
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [32, 262144], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 118, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(
        parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"]
    )
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-5f01fbbdf", "parentInputsVerified": len(inputs), "phase": phase,
    "domain": DOMAIN, "bootstrapImages": 86, "replacedBootstrapSlot": 0,
    "unchangedBootstrapImages": 85, "rawLimits": [32, 262144],
    "diagnosticClassBound": 118, "globalNativeBindings": 13,
    "stringLocalBinding": 10, "exceptionKinds": 14, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
