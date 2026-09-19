#!/usr/bin/env python3
"""Strict generated-only source invariants for raw37 / byte282358.

The accepted raw36 generated capacity stage is the sole source basis. This
verifier never opens an original artifact, JAR, class, resource, checkpoint, or
world.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount36-byte281175-preflight"

PARENT_FILES = {
    "engine/MCEntryInterpreter.sol": "673c77e07f9046d554610951a95334128b0636532dce74d1eeb2d405ee643f61",
    "coordinator/MCEntryCoordinator.sol": "aaab3834461c0f5a71812a5c8ea31e0b6ef07820909ab9f106bd7426674f122c",
    "tools/Go.txt": "f7c862142299fd34123273a8ff728e8d52ff9820edfc9a7b4e576fa226bb113e",
    "tools/checkpoint_diagnostic.py": "2cbb66b173e5e401d36137c1cc5781c4e0f14403d70b58fa5a6a20ab3fd5f972",
    "tools/checkpoint_frames.py": "2cbb66b173e5e401d36137c1cc5781c4e0f14403d70b58fa5a6a20ab3fd5f972",
    "tools/verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "tools/generate_fixtures.py": "edf5ff366a7049b1fde97cbbfdd5bbebeb430203cf0ea0650cc1518ab9830a8a",
    "tools/gate.py": "727366fa24b7332a250f67a8fcb39675f52d9b3fbe78370fa4e56a2bebfe4e12",
}
PARENT_DOMAIN = "MC-RAW36-BYTE281175-P1"
DOMAIN = "MC-RAW37-BYTE282358-P1"
PARENT_ENGINE = "4d432d52415733362d4259544532383131373545"
ENGINE = "4d432d52415733372d4259544532383233353845"
PARENT_OWNER = "4d432d52415733362d425954453238313137354f"
OWNER = "4d432d52415733372d425954453238323335384f"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("MAX_RAW_CLASSES = 36;") == 1
    assert text.count("MAX_RAW_BYTES = 281175;") == 1
    assert text.count("uint32(36), uint32(281175)") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 36;", "MAX_RAW_CLASSES = 37;")
            .replace("MAX_RAW_BYTES = 281175;", "MAX_RAW_BYTES = 282358;")
            .replace("uint32(36), uint32(281175)", "uint32(37), uint32(282358)"))


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    assert text.count("[36]") == 4 and text.count("n > 36") == 1
    assert text.count("281175") == 6
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace("[36]", "[37]").replace("n > 36", "n > 37")
            .replace("281175", "282358"))


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count("0x" + PARENT_ENGINE) == text.count("0x" + PARENT_OWNER) == 1
    assert text.count("len(m.Decoders) > 36") == text.count("len(parts) > 36") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("len(m.Decoders) > 36", "len(m.Decoders) > 37")
            .replace("len(parts) > 36", "len(parts) > 37"))


def final_driver(text, pins, parent_pins):
    for old, new in (
        (parent_pins["engine"]["runtimeSHA256"], pins["engine"]["runtimeSHA256"]),
        ("0x" + parent_pins["engine"]["runtimeKeccak256"], "0x" + pins["engine"]["runtimeKeccak256"]),
        ("0x" + parent_pins["coordinator"]["runtimeKeccak256"], "0x" + pins["coordinator"]["runtimeKeccak256"]),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    for pattern, replacement in (
        (r"len\(coordRun\) != \d+", "len(coordRun) != %d" % pins["coordinator"]["bytes"]),
        (r"len\(engineRun\) != \d+", "len(engineRun) != %d" % pins["engine"]["bytes"]),
        (r"len\(run\) != \d+", "len(run) != %d" % pins["engine"]["bytes"]),
    ):
        text, changed = re.subn(pattern, replacement, text)
        assert changed == 1, (pattern, changed)
    return text


def expected_fixtures(text):
    text = once(text, "raw36 / byte281175", "raw37 / byte282358")
    text = once(text, "java-diff-mc-classcount36-byte281175-fixtures-", "java-diff-mc-classcount37-byte282358-fixtures-")
    text = once(text, "# Exact raw36 and aggregate-byte boundaries exercise this measured cap lift.", "# Exact raw37 and aggregate-byte boundaries exercise this measured cap lift.")
    text = once(text, "for count in (29, 30, 31, 32, 33, 34, 35, 36, 37): count_fixture(\"count-%d\" % count, count)", "for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38): count_fixture(\"count-%d\" % count, count)")
    text = once(text, "count_fixture(\"count-36-281175\", 36, 281175)", "count_fixture(\"count-37-282358\", 37, 282358)")
    return once(text, "count_fixture(\"count-36-281176\", 36, 281176)", "count_fixture(\"count-37-282359\", 37, 282359)")


def expected_gate(text):
    text = once(text, "raw36 / byte281175", "raw37 / byte282358")
    text = once(text, "java-diff-mc-classcount36-byte281175-build-", "java-diff-mc-classcount37-byte282358-build-")
    text = once(text, "java-diff-mc-classcount36-byte281175-fixtures-", "java-diff-mc-classcount37-byte282358-fixtures-")
    text = once(text, "java-diff-mc-classcount36-byte281175-gate-", "java-diff-mc-classcount37-byte282358-gate-")
    text = once(text, 'pins["rawLimits"] == [36, 281175]', 'pins["rawLimits"] == [37, 282358]')
    text = once(text, 'pins["diagnosticClassBound"] == 126', 'pins["diagnosticClassBound"] == 127')
    text = once(text, 'head["totalClassBytes"] <= 281175', 'head["totalClassBytes"] <= 282358')
    start = text.index("# Exact raw36 is the focused capacity witness:")
    end = text.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    capacity = text[start:end]
    capacity = once(capacity, '''assert source.count("len(m.Decoders) > 36") == 1 and source.count("len(parts) > 36") == 1
    source = (source.replace("len(m.Decoders) > 36", "len(m.Decoders) > 37")
                    .replace("len(parts) > 36", "len(parts) > 37"))''', '''assert source.count("len(m.Decoders) > 37") == 1 and source.count("len(parts) > 37") == 1
    source = (source.replace("len(m.Decoders) > 37", "len(m.Decoders) > 38")
                    .replace("len(parts) > 37", "len(parts) > 38"))''')
    capacity = once(capacity, '''assert text.count("[36]") == 4 and text.count("n > 36") == 1
probe_source.write_text(text.replace("[36]", "[37]").replace("n > 36", "n > 37"))''', '''assert text.count("[37]") == 4 and text.count("n > 37") == 1
probe_source.write_text(text.replace("[37]", "[38]").replace("n > 37", "n > 38"))''')
    assert capacity.count("Raw37") == 1 and capacity.count("raw37") == 13
    capacity = capacity.replace("Raw37", "Raw38").replace("raw37", "raw38")
    assert capacity.count("raw36") == 2
    capacity = capacity.replace("raw36", "raw37")
    assert capacity.count("281175") == capacity.count("281176") == 8
    capacity = capacity.replace("281176", "282359").replace("281175", "282358")
    assert capacity.count("count-37") == 6 and capacity.count("count-36") == 7
    capacity = capacity.replace("count-37", "count-38").replace("count-36", "count-37")
    capacity = once(capacity, 'spec["bindingCount"] == 36', 'spec["bindingCount"] == 37')
    capacity = once(capacity, '["1", "37"]', '["1", "38"]')
    text = text[:start] + capacity + text[end:]
    old_summary = '''summary = {"profile": "MC-RAW36-BYTE281175-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted Math parent: 35 to 36, aggregate raw bytes 268379 to 281175, and read-only checkpoint diagnostic class bound 125 to 126. All 90 bootstrap images and bytes/positions, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    new_summary = '''summary = {"profile": "MC-RAW37-BYTE282358-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted raw36: 36 to 37, aggregate raw bytes 281175 to 282358, and read-only checkpoint diagnostic class bound 126 to 127. All 90 bootstrap images and bytes/positions, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusMessage, Provider construction, factory, world, or Done input or claim."}'''
    return once(text, old_summary, new_summary)


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "9c0ebbb5f", "parentEvidence": "classcount36-byte281175-preflight", "sha256": inputs,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(PARENT_ENGINE)) == len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "build-pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [36, 281175]
assert parent_pins["diagnosticClassBound"] == 126 and parent_pins["engine"]["bytes"] == 393208
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine((parent / "engine/MCEntryInterpreter.sol").read_text())
for fixed in (
    "MAX_RAW_CLASSES = 37;", "MAX_RAW_BYTES = 282358;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](90)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(37), uint32(282358)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[89] = DBOOT_MATH;",
    "p.classes[classSlot + 50].data = _bootstrapMath();",
):
    assert engine.count(fixed) == 1, fixed

coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator((parent / "coordinator/MCEntryCoordinator.sol").read_text())
assert coordinator.count("[37]") == 4 and coordinator.count("n > 37") == 1
assert coordinator.count("if (size == 0 || size > 282358)") == 1
assert coordinator.count("if (uint256(total) + size > 282358)") == 1

driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver((parent / "tools/Go.txt").read_text())
assert driver.count("len(m.Decoders) > 37") == driver.count("len(parts) > 37") == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == (parent / "tools" / name).read_text().replace("classes<=126", "classes<=127")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "tools/verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == PARENT_FILES["engine/build.js"]
assert digest(stage / "coordinator/build.js") == PARENT_FILES["coordinator/build.js"]
assert (stage / "tools/generate_fixtures.py").read_text() == expected_fixtures((parent / "tools/generate_fixtures.py").read_text())
assert (stage / "tools/gate.py").read_text() == expected_gate((parent / "tools/gate.py").read_text())

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator and driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    expected_pins = {
        "basis": "9c0ebbb5f", "parentEvidence": "classcount36-byte281175-preflight", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 90,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [37, 282358], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 127, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] == parent_pins["engine"]["bytes"] == 393208
    assert pins["engine"]["bytes"] <= 393216
    assert pins["coordinator"]["bytes"] == parent_pins["coordinator"]["bytes"] == 5394
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "classcount36-byte281175-preflight", "parentInputsVerified": len(inputs),
    "phase": phase, "domain": DOMAIN, "bootstrapImages": 90,
    "rawLimits": [37, 282358], "diagnosticClassBound": 127,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "runtimeBaseline": 393208,
    "runtimeCap": 393216, "address": "0x" + ENGINE,
}, indent=2))
