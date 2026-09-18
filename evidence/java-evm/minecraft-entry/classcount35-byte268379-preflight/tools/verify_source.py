#!/usr/bin/env python3
"""Strict generated-only source invariants for raw35 / byte268379.

The accepted raw34 parent ``parent-be5f9998e`` is the sole runtime source
basis. Fixture and gate sources derive only from the accepted generated-only
raw34 capacity gate; no original artifact, JAR, class, resource, checkpoint, or
world is opened by this verifier.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-be5f9998e"
fixture_parent = stage.parent / "classcount34-byte268053-preflight"

PARENT_FILES = {
    "pins.json": "4af7efe6c1f568287e704f0e9079fdccf4c6deafe7d3d389757e08385999a19c",
    "artifacts/engine/MCEntryInterpreter.sol": "ffe34cde797e5512547cd696f6d9eb93769873e93cfcd86f95a59d97ef24b09c",
    "artifacts/coordinator/MCEntryCoordinator.sol": "b85adb37cbc71f131d9aca6b7c64cee6e70a8573f391ba0aa9a673c34c5b6af6",
    "executed-driver.go.txt": "f47f8296e36f8bfc61cef5d6204eb934e974cb6903bebbcf0b506a6811d2c942",
    "checkpoint_diagnostic.py": "1c52e995cd77f0cfb1676b121f107e272e71e9bac4aa74173588ef9e430a721d",
    "checkpoint_frames.py": "1c52e995cd77f0cfb1676b121f107e272e71e9bac4aa74173588ef9e430a721d",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
FIXTURE_PARENT_FILES = {
    "tools/generate_fixtures.py": "21b04a8b3b865b3383e592c6ba11384bdd1272a97b6351c4c632398fbd0573e1",
    "tools/gate.py": "8526b0ad3312c55b58f7c153f46efb415bf034f33c2a95219c18bd04f887656b",
}
PARENT_DOMAIN = "MC-CLASSCOUNT34-BYTE268053-P2"
DOMAIN = "MC-CLASSCOUNT35-BYTE268379-P1"
PARENT_ENGINE = "4d432d434333342d42593236383035332d454e48"
ENGINE = "4d432d434333352d42593236383337392d454e47"
PARENT_OWNER = "4d432d434333342d42593236383035332d4f574f"
OWNER = "4d432d434333352d42593236383337392d4f574e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("MAX_RAW_CLASSES = 34;") == 1
    assert text.count("MAX_RAW_BYTES = 268053;") == 1
    assert text.count("uint32(34), uint32(268053)") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 34;", "MAX_RAW_CLASSES = 35;")
            .replace("MAX_RAW_BYTES = 268053;", "MAX_RAW_BYTES = 268379;")
            .replace("uint32(34), uint32(268053)", "uint32(35), uint32(268379)"))


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    assert text.count("[34]") == 4 and text.count("n > 34") == 1
    assert text.count("268053") == 6
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace("[34]", "[35]").replace("n > 34", "n > 35")
            .replace("268053", "268379"))


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count("0x" + PARENT_ENGINE) == text.count("0x" + PARENT_OWNER) == 1
    assert text.count("len(m.Decoders) > 34") == text.count("len(parts) > 34") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("len(m.Decoders) > 34", "len(m.Decoders) > 35")
            .replace("len(parts) > 34", "len(parts) > 35"))


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
    assert text.count("java-diff-mc-classcount34-byte268053-fixtures-") == 1
    assert text.count("for count in (29, 30, 31, 32, 33, 34, 35): count_fixture(\"count-%d\" % count, count)") == 1
    assert text.count("count_fixture(\"count-34-268053\", 34, 268053)") == 1
    assert text.count("count_fixture(\"count-34-268054\", 34, 268054)") == 1
    return (text.replace("Create only trusted generated Java-8 fixtures for raw34 / byte268053 and retained gates.",
                         "Create only trusted generated Java-8 fixtures for raw35 / byte268379 and retained gates.")
            .replace("java-diff-mc-classcount34-byte268053-fixtures-", "java-diff-mc-classcount35-byte268379-fixtures-")
            .replace("# Exact raw34 and aggregate-byte boundaries exercise this measured cap lift.",
                     "# Exact raw35 and aggregate-byte boundaries exercise this measured cap lift.")
            .replace("for count in (29, 30, 31, 32, 33, 34, 35): count_fixture(\"count-%d\" % count, count)",
                     "for count in (29, 30, 31, 32, 33, 34, 35, 36): count_fixture(\"count-%d\" % count, count)")
            .replace("count_fixture(\"count-34-268053\", 34, 268053)",
                     "count_fixture(\"count-35-268379\", 35, 268379)")
            .replace("count_fixture(\"count-34-268054\", 34, 268054)",
                     "count_fixture(\"count-35-268380\", 35, 268380)"))


def expected_gate(text):
    assert text.count("java-diff-mc-classcount34-byte268053-build-") == 1
    assert text.count("java-diff-mc-classcount34-byte268053-fixtures-") == 1
    assert text.count("java-diff-mc-classcount34-byte268053-gate-") == 1
    assert text.count('pins["rawLimits"] == [34, 268053]') == 1
    assert text.count('pins["diagnosticClassBound"] == 122') == 1
    assert text.count('head["totalClassBytes"] <= 268053') == 1
    start = text.index("# Exact raw34 is the focused capacity witness")
    end = text.index("# Retained EnumSet", start)
    capacity = text[start:end]
    assert capacity.count("268054") == capacity.count("268053") == 8
    capacity = capacity.replace("268054", "268380").replace("268053", "268379")
    capacity = capacity.replace("35", "36").replace("34", "35")
    text = text[:start] + capacity + text[end:]
    old_summary = '''summary = {"profile": "MC-CLASSCOUNT34-BYTE268053-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted Iterable parent: 33 to 34, aggregate raw bytes 262158 to 268053, and checkpoint diagnostic class bound 121 to 122. All 88 bootstrap images, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    new_summary = '''summary = {"profile": "MC-CLASSCOUNT35-BYTE268379-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted raw34 parent: 34 to 35, aggregate raw bytes 268053 to 268379, and checkpoint diagnostic class bound 122 to 123. All 88 bootstrap images, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    assert text.count(old_summary) == 1
    return (text.replace("One generated-only raw34 / byte268053 and retained acceptance gate.",
                         "One generated-only raw35 / byte268379 and retained acceptance gate.")
            .replace("java-diff-mc-classcount34-byte268053-build-", "java-diff-mc-classcount35-byte268379-build-")
            .replace("java-diff-mc-classcount34-byte268053-fixtures-", "java-diff-mc-classcount35-byte268379-fixtures-")
            .replace("java-diff-mc-classcount34-byte268053-gate-", "java-diff-mc-classcount35-byte268379-gate-")
            .replace('pins["rawLimits"] == [34, 268053]', 'pins["rawLimits"] == [35, 268379]')
            .replace('pins["diagnosticClassBound"] == 122', 'pins["diagnosticClassBound"] == 123')
            .replace('head["totalClassBytes"] <= 268053', 'head["totalClassBytes"] <= 268379')
            .replace(old_summary, new_summary))


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
fixture_inputs = {name: digest(fixture_parent / name) for name in FIXTURE_PARENT_FILES}
assert fixture_inputs == FIXTURE_PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "e93b2a170", "parentEvidence": "parent-be5f9998e", "sha256": inputs,
    "fixtureBasis": "classcount34-byte268053-preflight", "fixtureSHA256": fixture_inputs,
}
assert len(DOMAIN) == 29 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 88
assert parent_pins["rawLimits"] == [34, 268053]
assert parent_pins["diagnosticClassBound"] == 122
assert parent_pins["engine"]["bytes"] == 393060
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine((parent / "artifacts/engine/MCEntryInterpreter.sol").read_text())
for fixed in (
    "MAX_RAW_CLASSES = 35;", "MAX_RAW_BYTES = 268379;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](88)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(35), uint32(268379)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[87] = DBOOT_ITERABLE;",
):
    assert engine.count(fixed) == 1, fixed

coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator((parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text())
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
assert coordinator.count("[35]") == 4 and coordinator.count("n > 35") == 1
assert coordinator.count("if (size == 0 || size > 268379)") == 1
assert coordinator.count("if (uint256(total) + size > 268379)") == 1

driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver((parent / "executed-driver.go.txt").read_text())
assert driver.count(DOMAIN) == 6 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 35") == driver.count("len(parts) > 35") == 1
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == (parent / "checkpoint_diagnostic.py").read_text().replace("classes<=122", "classes<=123")
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")
assert (stage / "tools/generate_fixtures.py").read_text() == expected_fixtures((fixture_parent / "tools/generate_fixtures.py").read_text())
assert (stage / "tools/gate.py").read_text() == expected_gate((fixture_parent / "tools/gate.py").read_text())

expected_args = sys.argv[1:]
if expected_args == ["--prebuild"]:
    assert not (stage / "build-pins.json").exists()
    assert coordinator == preliminary_coordinator
    assert driver == preliminary_driver
    phase = "prebuild"
else:
    assert len(expected_args) == 2 and expected_args[0] == "--built"
    pins = json.loads(Path(expected_args[1]).read_text())
    expected_pins = {
        "basis": "e93b2a170", "parentEvidence": "parent-be5f9998e", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 88,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [35, 268379], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 123, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and 393216 - pins["engine"]["bytes"] == 156
    assert pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    persistent = stage / "build-pins.json"
    assert persistent.is_file() and json.loads(persistent.read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-be5f9998e", "parentInputsVerified": len(inputs),
    "fixtureInputsVerified": len(fixture_inputs), "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 88, "unchangedBootstrapImages": 88,
    "rawLimits": [35, 268379], "diagnosticClassBound": 123,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
