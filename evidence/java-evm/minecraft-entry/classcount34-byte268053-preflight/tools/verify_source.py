#!/usr/bin/env python3
"""Strict generated-only source invariants for raw34 / byte268053.

The accepted Iterable parent ``parent-cc433baf7`` is the sole runtime source
basis. Fixture and gate sources derive from its accepted generated-only
Iterable gate; no original artifact, JAR, class, resource, checkpoint, or world
is opened by this verifier.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-cc433baf7"
fixture_parent = stage.parent / "iterable-link-preflight"

PARENT_FILES = {
    "pins.json": "a5e0bdebd26d5c1d4c3fd0d282f5773933478f204f2ebce26f6d9308d4a563fb",
    "artifacts/engine/MCEntryInterpreter.sol": "3805414986d4ebd3fcc3a8f5317d0e545b7f661992d0e4f4844b49d6b095c76f",
    "artifacts/coordinator/MCEntryCoordinator.sol": "5957d36cf4def7477aaeb857cf7efacad67a0fe6c4a39e01f408ba3f4c5bfcfe",
    "executed-driver.go.txt": "4ff48e1aa7f6ec76750211170fe6db0ee8575b93da060c8af26082efccf1c483",
    "checkpoint_diagnostic.py": "7e443062657b8a1a703874153452374f0112760bf1f8199931cb91f0a0e6d598",
    "checkpoint_frames.py": "7e443062657b8a1a703874153452374f0112760bf1f8199931cb91f0a0e6d598",
    "verify_receipts.js": "edf8e487b586877107543ad6f1597185ca817414cd1f160f986dff8db8fff181",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
}
FIXTURE_PARENT_FILES = {
    "tools/generate_fixtures.py": "972322ef57235e45f37d59f234df7e6015504b03aa652e547efac7db1104edc7",
    "tools/gate.py": "1ed3fb73f2f46714efe4466a485fe7da32062ae2c65cbbfd33c452519c3357c1",
}
PARENT_DOMAIN = "MC-ITERABLE-LINK-P2"
DOMAIN = "MC-CLASSCOUNT34-BYTE268053-P1"
PARENT_ENGINE = "4d432d4954455241424c452d4c494e4b2d503200"
ENGINE = "4d432d434333342d42593236383035332d454e47"
PARENT_OWNER = "4d432d4954455241424c452d4c494e4b2d4f3200"
OWNER = "4d432d434333342d42593236383035332d4f574e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initial_engine(text):
    assert text.count(PARENT_DOMAIN) == 9
    assert text.count("MAX_RAW_CLASSES = 33;") == 1
    assert text.count("MAX_RAW_BYTES = 262158;") == 1
    assert text.count("uint32(33), uint32(262158)") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("MAX_RAW_CLASSES = 33;", "MAX_RAW_CLASSES = 34;")
            .replace("MAX_RAW_BYTES = 262158;", "MAX_RAW_BYTES = 268053;")
            .replace("uint32(33), uint32(262158)", "uint32(34), uint32(268053)"))


def initial_coordinator(text):
    assert text.count(PARENT_DOMAIN) == 4 and text.count(PARENT_ENGINE) == 1
    assert text.count("[33]") == 4 and text.count("n > 33") == 1
    assert text.count("262158") == 2
    return (text.replace(PARENT_DOMAIN, DOMAIN).replace(PARENT_ENGINE, ENGINE)
            .replace("[33]", "[34]").replace("n > 33", "n > 34")
            .replace("262158", "268053"))


def initial_driver(text):
    assert text.count(PARENT_DOMAIN) == 6
    assert text.count("0x" + PARENT_ENGINE) == text.count("0x" + PARENT_OWNER) == 1
    assert text.count("len(m.Decoders) > 33") == text.count("len(parts) > 33") == 1
    return (text.replace(PARENT_DOMAIN, DOMAIN)
            .replace("0x" + PARENT_ENGINE, "0x" + ENGINE)
            .replace("0x" + PARENT_OWNER, "0x" + OWNER)
            .replace("len(m.Decoders) > 33", "len(m.Decoders) > 34")
            .replace("len(parts) > 33", "len(parts) > 34"))


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
    assert text.count("java-diff-mc-iterable-link-fixtures-") == 1
    assert text.count("for count in (29, 30, 31, 32, 33, 34): count_fixture(\"count-%d\" % count, count)") == 1
    assert text.count("count_fixture(\"count-33-262158\", 33, 262158)") == 1
    assert text.count("count_fixture(\"count-33-262159\", 33, 262159)") == 1
    return (text.replace("Iterable linkage and retained gates", "raw34 / byte268053 and retained gates")
            .replace("java-diff-mc-iterable-link-fixtures-", "java-diff-mc-classcount34-byte268053-fixtures-")
            .replace("# Exact raw33 and aggregate-byte boundaries exercise this measured cap lift.",
                     "# Exact raw34 and aggregate-byte boundaries exercise this measured cap lift.")
            .replace("for count in (29, 30, 31, 32, 33, 34): count_fixture(\"count-%d\" % count, count)",
                     "for count in (29, 30, 31, 32, 33, 34, 35): count_fixture(\"count-%d\" % count, count)")
            .replace("count_fixture(\"count-33-262158\", 33, 262158)",
                     "count_fixture(\"count-34-268053\", 34, 268053)")
            .replace("count_fixture(\"count-33-262159\", 33, 262159)",
                     "count_fixture(\"count-34-268054\", 34, 268054)"))


def assert_aggregate_fixture_derivative(actual, baseline):
    """Pin all retained fixture sources while permitting only the necessary
    two-class padding change for the larger aggregate boundary."""
    begin = "def count_source(count, pads=()):"
    end = "# The focused image has only valueOf(int):"
    assert actual[:actual.index(begin)] == baseline[:baseline.index(begin)]
    assert actual[actual.index(end):] == baseline[baseline.index(end):]
    block = actual[actual.index(begin):actual.index(end)]
    assert "def tail_source(index, pads=()):" in block
    assert "Tail01 is otherwise an unchanged ordinary tail." in block
    assert "need <= 6 * 65000" in block
    assert "allocations = [need // 6" in block
    assert "max(path.stat().st_size for path in classes.glob(\"*.class\")) <= 262144" in block
    assert '"classBytes": {name: (classes / name).stat().st_size for name in entries}' in block
    assert "need <= 5 * 65000" not in block
    assert "compile(pads=())" not in block


def expected_gate(text):
    assert text.count("java-diff-mc-iterable-link-build-") == 1
    assert text.count("java-diff-mc-iterable-link-fixtures-") == 1
    assert text.count("java-diff-mc-iterable-link-gate-") == 1
    assert text.count('pins["rawLimits"] == [33, 262158]') == 1
    assert text.count('pins["diagnosticClassBound"] == 121') == 1
    assert text.count('head["totalClassBytes"] <= 262158') == 1
    start = text.index("# Exact raw33 is retained as the capacity witness")
    end = text.index("# Retained EnumSet", start)
    capacity = text[start:end]
    # Shift only the parent capacity witness and its disposable one-layer
    # widenings: 33->34, 34->35, 262158->268053, 262159->268054.
    capacity = capacity.replace("262159", "268054").replace("262158", "268053")
    capacity = capacity.replace("34", "35").replace("33", "34")
    capacity = capacity.replace("# Exact raw34 is retained as the capacity witness",
                                "# Exact raw34 is the focused capacity witness")
    text = text[:start] + capacity + text[end:]
    old_summary = '''summary = {"profile": "MC-ITERABLE-LINK-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only existing java/util/Collection is replaced to extend appended java/lang/Iterable, whose sole method is Iterator iterator(). Raw33/262158, the preceding 87 bootstrap positions other than Collection, native13, diagnostic121, selected-resource count1/4096, Properties/String/WeakReference pipeline, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. No forEach, spliterator, Consumer, Spliterator, stream, mutation expansion, host collection/iterator fallback, original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim is present."}'''
    new_summary = '''summary = {"profile": "MC-CLASSCOUNT34-BYTE268053-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only raw selected-class capacity changes from accepted Iterable parent: 33 to 34, aggregate raw bytes 262158 to 268053, and checkpoint diagnostic class bound 121 to 122. All 88 bootstrap images, global natives13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, Provider construction, factory, world, or Done input or claim."}'''
    assert text.count(old_summary) == 1
    result = (text.replace("Iterable linkage and retained acceptance gate", "raw34 / byte268053 and retained acceptance gate")
              .replace("java-diff-mc-iterable-link-build-", "java-diff-mc-classcount34-byte268053-build-")
              .replace("java-diff-mc-iterable-link-fixtures-", "java-diff-mc-classcount34-byte268053-fixtures-")
              .replace("java-diff-mc-iterable-link-gate-", "java-diff-mc-classcount34-byte268053-gate-")
              .replace('pins["rawLimits"] == [33, 262158]', 'pins["rawLimits"] == [34, 268053]')
              .replace('pins["diagnosticClassBound"] == 121', 'pins["diagnosticClassBound"] == 122')
              .replace('head["totalClassBytes"] <= 262158', 'head["totalClassBytes"] <= 268053')
              .replace(old_summary, new_summary))
    marker = "# Exactly 268053 raw bytes is admitted by the coordinator and reaches the\n"
    witness = '''# Both aggregate witnesses remain legal individual DI0 inputs; the test reaches
# the raw-package guard rather than an unrelated per-class transport refusal.
for label, total in (("count-34-268053", 268053), ("count-34-268054", 268054)):
    spec = fixture(label)
    assert spec["bindingCount"] == 34 and spec["totalClassBytes"] == total
    assert max(spec["classBytes"].values()) <= 262144

'''
    assert result.count(marker) == 1
    return result.replace(marker, witness + marker)


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
fixture_inputs = {name: digest(fixture_parent / name) for name in FIXTURE_PARENT_FILES}
assert fixture_inputs == FIXTURE_PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "6032de1ac", "parentEvidence": "parent-cc433baf7", "sha256": inputs,
    "fixtureBasis": "iterable-link-preflight", "fixtureSHA256": fixture_inputs,
}
assert len(DOMAIN) == 29 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["domain"] == PARENT_DOMAIN
assert parent_pins["bootstrapCount"] == 88
assert parent_pins["rawLimits"] == [33, 262158]
assert parent_pins["diagnosticClassBound"] == 121
assert parent_pins["engine"]["bytes"] == 393060
assert parent_pins["coordinator"]["bytes"] == 5394
assert parent_pins["globalNativeBindings"] == 13
assert parent_pins["stringLocalBinding"] == 10
assert parent_pins["exceptionKinds"] == 14

engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
assert engine == initial_engine((parent / "artifacts/engine/MCEntryInterpreter.sol").read_text())
for fixed in (
    "MAX_RAW_CLASSES = 34;", "MAX_RAW_BYTES = 268053;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new bytes32[](88)", "new uint256[](14)", "return 13;", "uint32[11] memory limits",
    "uint32(34), uint32(268053)", "MAX_ARRAY_ELEMENTS = 262144;",
    "MAX_EXCEPTION_FIELD_SLOTS = 262144;", "h[87] = DBOOT_ITERABLE;",
):
    assert engine.count(fixed) == 1, fixed

coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
preliminary_coordinator = initial_coordinator((parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text())
assert coordinator.count(DOMAIN) == 4 and coordinator.count(ENGINE) == 1
assert coordinator.count("[34]") == 4 and coordinator.count("n > 34") == 1
assert coordinator.count("if (size == 0 || size > 268053)") == 1
assert coordinator.count("if (uint256(total) + size > 268053)") == 1

driver = (stage / "tools/Go.txt").read_text()
preliminary_driver = initial_driver((parent / "executed-driver.go.txt").read_text())
assert driver.count(DOMAIN) == 6 and driver.count(ENGINE) == driver.count(OWNER) == 1
assert driver.count("len(m.Decoders) > 34") == driver.count("len(parts) > 34") == 1
assert (stage / "tools/checkpoint_diagnostic.py").read_text() == (parent / "checkpoint_diagnostic.py").read_text().replace("classes<=121", "classes<=122")
assert (stage / "tools/checkpoint_frames.py").read_bytes() == (parent / "checkpoint_frames.py").read_bytes()
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")
fixture_baseline = expected_fixtures((fixture_parent / "tools/generate_fixtures.py").read_text())
assert_aggregate_fixture_derivative((stage / "tools/generate_fixtures.py").read_text(), fixture_baseline)
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
        "basis": "6032de1ac", "parentEvidence": "parent-cc433baf7", "phase": "built",
        "domain": DOMAIN, "runtimeCap": 393216, "bootstrapCount": 88,
        "bootstrapSHA256": parent_pins["bootstrapSHA256"],
        "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
        "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
        "rawLimits": [34, 268053], "checkpointCap": 1048576, "headCap": 32768,
        "diagnosticClassBound": 122, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
        "limitsCommitment": parent_pins["limitsCommitment"], "compiler": parent_pins["compiler"],
        "engine": pins["engine"], "coordinator": pins["coordinator"],
    }
    assert pins == expected_pins
    assert pins["engine"]["bytes"] <= 393216 and pins["coordinator"]["bytes"] <= 24576
    assert coordinator == preliminary_coordinator.replace(parent_pins["engine"]["runtimeKeccak256"], pins["engine"]["runtimeKeccak256"])
    assert driver == final_driver(preliminary_driver, pins, parent_pins)
    persistent = stage / "build-pins.json"
    assert persistent.is_file() and json.loads(persistent.read_text()) == pins
    phase = "built"

print(json.dumps({
    "acceptedParent": "parent-cc433baf7", "parentInputsVerified": len(inputs),
    "fixtureInputsVerified": len(fixture_inputs), "phase": phase, "domain": DOMAIN,
    "bootstrapImages": 88, "unchangedBootstrapImages": 88,
    "rawLimits": [34, 268053], "diagnosticClassBound": 122,
    "globalNativeBindings": 13, "stringLocalBinding": 10, "exceptionKinds": 14,
    "selectedResource": {"count": 1, "bytes": 4096}, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
}, indent=2))
