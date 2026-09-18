#!/usr/bin/env python3
"""Strict generated-only source invariants for raw36 / byte281175.

The accepted Math parent ``parent-3af172306`` is the sole runtime source basis.
Fixture and gate sources derive only from its generated Math gate. This verifier
never opens an original artifact, JAR, class, resource, checkpoint, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-3af172306"
fixture_parent = stage.parent / "math-int-min-max-preflight"

PARENT_FILES = {
    "pins.json": "743a86482cb234f98694a09d2b43976c833ed9b32438c80be9103fd9b43c7b69",
    "artifacts/engine/MCEntryInterpreter.sol": "d35b169f22b0cf87a6fba0f3544e239086123c6d579da637525501779252e188",
    "artifacts/coordinator/MCEntryCoordinator.sol": "9cbe1f791fdf2d7bbadf8abf2b873d925dff437cde715f7f14ee339fb7e91bdf",
    "executed-driver.go.txt": "a4d7fdffb6375237fc67f0529b91253d3e0619ce1b159e97872ed793da4bbd7f",
    "checkpoint_diagnostic.py": "e1cccc255cf860b0a65fe296305f8bc8d7139992a9a7f997e7cccb727ae48a24",
    "checkpoint_frames.py": "e1cccc255cf860b0a65fe296305f8bc8d7139992a9a7f997e7cccb727ae48a24",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
FIXTURE_PARENT_FILES = {
    "tools/generate_fixtures.py": "015fc3cc441616b939c356ae2cd467db3e1dcb688f377b32efd01fb8bcff4147",
    "tools/gate.py": "d6aad93547a3a3b503f7f473d4ff3dcc226a7308c56f5a22be6d3af0f2461ad4",
}
PARENT_DOMAIN = "MC-MATH-INT-MIN-MAX-P2"
DOMAIN = "MC-RAW36-BYTE281175-P1"
PARENT_ENGINE = "4d432d4d4154482d494e542d4d494e2d4d415846"
ENGINE = "4d432d52415733362d4259544532383131373545"
PARENT_OWNER = "4d432d4d4154482d494e542d4d494e2d4d415850"
OWNER = "4d432d52415733362d425954453238313137354f"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("MAX_RAW_CLASSES = 35;") == 1
    assert text.count("MAX_RAW_BYTES = 268379;") == 1
    assert text.count("uint32(35), uint32(268379)") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 35;", "MAX_RAW_CLASSES = 36;")
            .replace("MAX_RAW_BYTES = 268379;", "MAX_RAW_BYTES = 281175;")
            .replace("uint32(35), uint32(268379)", "uint32(36), uint32(281175)"))


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    assert text.count("[35]") == 4 and text.count("n > 35") == 1
    assert text.count("268379") == 2
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace("[35]", "[36]").replace("n > 35", "n > 36")
            .replace("268379", "281175"))


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count("0x" + PARENT_ENGINE) == text.count("0x" + PARENT_OWNER) == 1
    assert text.count("len(m.Decoders) > 35") == text.count("len(parts) > 35") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("len(m.Decoders) > 35", "len(m.Decoders) > 36")
            .replace("len(parts) > 35", "len(parts) > 36"))


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
    assert text.count("java-diff-mc-math-int-min-max-fixtures-") == 1
    assert text.count("for count in (29, 30, 31, 32, 33, 34, 35, 36): count_fixture(\"count-%d\" % count, count)") == 1
    assert text.count("count_fixture(\"count-35-268379\", 35, 268379)") == 1
    assert text.count("count_fixture(\"count-35-268380\", 35, 268380)") == 1
    return (text.replace("Create only trusted generated Java-8 fixtures for Math int min/max and retained gates.",
                         "Create only trusted generated Java-8 fixtures for raw36 / byte281175 and retained gates.")
            .replace("java-diff-mc-math-int-min-max-fixtures-", "java-diff-mc-classcount36-byte281175-fixtures-")
            .replace("# Exact raw35 and aggregate-byte boundaries exercise this measured cap lift.",
                     "# Exact raw36 and aggregate-byte boundaries exercise this measured cap lift.")
            .replace("for count in (29, 30, 31, 32, 33, 34, 35, 36): count_fixture(\"count-%d\" % count, count)",
                     "for count in (29, 30, 31, 32, 33, 34, 35, 36, 37): count_fixture(\"count-%d\" % count, count)")
            .replace("count_fixture(\"count-35-268379\", 35, 268379)",
                     "count_fixture(\"count-36-281175\", 36, 281175)")
            .replace("count_fixture(\"count-35-268380\", 35, 268380)",
                     "count_fixture(\"count-36-281176\", 36, 281176)"))


def expected_gate(text):
    assert text.count("java-diff-mc-math-int-min-max-build-") == 1
    assert text.count("java-diff-mc-math-int-min-max-fixtures-") == 1
    assert text.count("java-diff-mc-math-int-min-max-gate-") == 1
    assert text.count('pins["rawLimits"] == [35, 268379]') == 1
    assert text.count('pins["diagnosticClassBound"] == 125') == 1
    assert text.count('head["totalClassBytes"] <= 268379') == 1
    result = (text.replace("One generated-only Math int min/max and retained acceptance gate.",
                           "One generated-only raw36 / byte281175 and retained acceptance gate.")
              .replace("java-diff-mc-math-int-min-max-build-", "java-diff-mc-classcount36-byte281175-build-")
              .replace("java-diff-mc-math-int-min-max-fixtures-", "java-diff-mc-classcount36-byte281175-fixtures-")
              .replace("java-diff-mc-math-int-min-max-gate-", "java-diff-mc-classcount36-byte281175-gate-")
              .replace('pins["rawLimits"] == [35, 268379]', 'pins["rawLimits"] == [36, 281175]')
              .replace('pins["diagnosticClassBound"] == 125', 'pins["diagnosticClassBound"] == 126')
              .replace('head["totalClassBytes"] <= 268379', 'head["totalClassBytes"] <= 281175'))
    start = result.index("# Exact raw35 is the focused capacity witness:")
    end = result.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    capacity = result[start:end]
    assert capacity.count("raw35") == 2 and capacity.count("raw36") == 13
    assert capacity.count("268379") == capacity.count("268380") == 8
    assert capacity.count("[35]") == 2 and capacity.count("n > 35") == 2
    # The product driver now admits 36, while its disposable coordinator probe
    # admits 37 solely to prove the unchanged engine guard.  Rewrite these
    # transitions before renaming the old raw36 negative witness to raw37.
    old_driver = '''    assert source.count("len(m.Decoders) > 35") == 1 and source.count("len(parts) > 35") == 1
    source = (source.replace("len(m.Decoders) > 35", "len(m.Decoders) > 36")
                    .replace("len(parts) > 35", "len(parts) > 36"))'''
    new_driver = '''    assert source.count("len(m.Decoders) > 36") == 1 and source.count("len(parts) > 36") == 1
    source = (source.replace("len(m.Decoders) > 36", "len(m.Decoders) > 37")
                    .replace("len(parts) > 36", "len(parts) > 37"))'''
    assert capacity.count(old_driver) == 1
    capacity = capacity.replace(old_driver, new_driver)
    old_probe = '''assert text.count("[35]") == 4 and text.count("n > 35") == 1
probe_source.write_text(text.replace("[35]", "[36]").replace("n > 35", "n > 36"))'''
    new_probe = '''assert text.count("[36]") == 4 and text.count("n > 36") == 1
probe_source.write_text(text.replace("[36]", "[37]").replace("n > 36", "n > 37"))'''
    assert capacity.count(old_probe) == 1
    capacity = capacity.replace(old_probe, new_probe)
    # Rewrite raw36 first so the old refusal becomes raw37; the old raw35
    # positive witness then becomes the new raw36 accepted boundary.
    capacity = capacity.replace("Raw36", "Raw37").replace("raw36", "raw37")
    capacity = capacity.replace("Raw35", "Raw36").replace("raw35", "raw36")
    capacity = capacity.replace("268380", "281176").replace("268379", "281175")
    capacity = capacity.replace("count-36", "count-37").replace("count-35", "count-36")
    capacity = capacity.replace('spec["bindingCount"] == 35', 'spec["bindingCount"] == 36')
    capacity = capacity.replace('["1", "36"]', '["1", "37"]')
    result = result[:start] + capacity + result[end:]
    old_summary = '''summary = {"profile": "MC-MATH-INT-MIN-MAX-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only Java8 java/lang/Math private constructor plus ordinary static int max/min append at bootstrap index89 and the read-only diagnostic class bound changes 124 to 125 from accepted ThreadLocal parent. Raw35/268379, all prior 89 image bytes/positions, natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. No long, floating, abs, round, random, or exact-arithmetic API is supplied. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    new_summary = '''summary = {"profile": "MC-RAW36-BYTE281175-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted Math parent: 35 to 36, aggregate raw bytes 268379 to 281175, and read-only checkpoint diagnostic class bound 125 to 126. All 90 bootstrap images and bytes/positions, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    assert result.count(old_summary) == 1
    return result.replace(old_summary, new_summary)


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
fixture_inputs = {name: digest(fixture_parent / name) for name in FIXTURE_PARENT_FILES}
assert fixture_inputs == FIXTURE_PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "bf2040618", "parentEvidence": "parent-3af172306", "fixtureBasis": "math-int-min-max-preflight",
    "sha256": inputs, "fixtureSHA256": fixture_inputs,
}
assert len(PARENT_DOMAIN) == len(DOMAIN) == 22
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 90 and parent_pins["rawLimits"] == [35, 268379]
assert parent_pins["diagnosticClassBound"] == 125 and parent_pins["engine"]["bytes"] == 393208
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13 and parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine((parent / "artifacts/engine/MCEntryInterpreter.sol").read_text())
for fixed in (
    "MAX_RAW_CLASSES = 36;", "MAX_RAW_BYTES = 281175;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](90)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(36), uint32(281175)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[89] = DBOOT_MATH;",
    "p.classes[classSlot + 50].data = _bootstrapMath();",
):
    assert engine.count(fixed) == 1, fixed

coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator((parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text())
assert coordinator.count("[36]") == 4 and coordinator.count("n > 36") == 1
assert coordinator.count("if (size == 0 || size > 281175)") == 1
assert coordinator.count("if (uint256(total) + size > 281175)") == 1

driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver((parent / "executed-driver.go.txt").read_text())
assert driver.count("len(m.Decoders) > 36") == driver.count("len(parts) > 36") == 1
for name in ("checkpoint_diagnostic.py", "checkpoint_frames.py"):
    assert (stage / "tools" / name).read_text() == (parent / name).read_text().replace("classes<=125", "classes<=126")
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == PARENT_FILES["artifacts/engine/build.js"]
assert digest(stage / "coordinator/build.js") == PARENT_FILES["artifacts/coordinator/build.js"]
assert (stage / "tools/generate_fixtures.py").read_text() == expected_fixtures((fixture_parent / "tools/generate_fixtures.py").read_text())
assert (stage / "tools/gate.py").read_text() == expected_gate((fixture_parent / "tools/gate.py").read_text())

args = sys.argv[1:]
if args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator and driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(args) == 2 and args[0] == "--built"
    pins = json.loads(Path(args[1]).read_text())
    expected_pins = {
        "basis": "bf2040618", "parentEvidence": "parent-3af172306", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 90,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [36, 281175], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 126, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["engine"]["bytes"] <= parent_pins["engine"]["bytes"] + 8
    assert pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    assert json.loads((stage / "build-pins.json").read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-3af172306", "parentInputsVerified": len(inputs),
    "fixtureInputsVerified": len(fixture_inputs), "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 90, "rawLimits": [36, 281175], "diagnosticClassBound": 126,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
