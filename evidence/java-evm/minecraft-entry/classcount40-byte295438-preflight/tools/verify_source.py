#!/usr/bin/env python3
"""Pin the generated raw40 delta to the raw39/byte294891 source stage."""
from pathlib import Path
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount39-byte294891-preflight"
D = "MC-RAW40-BYTE295438-P1"
OLD_D = "MC-RAW39-BYTE294891-P1"
ENGINE = "4d432d52415734302d4259544532393534333845"
OWNER = "4d432d52415734302d425954453239353433384f"
OLD_ENGINE = "4d432d52415733392d4259544532393438393145"
OLD_OWNER = "4d432d52415733392d425954453239343839314f"
ENGINE_PIN = {
    "bytes": 389150,
    "initSHA256": "9b6d66ea8bea67d06357f2b25381a5ad675786aa5980d0cf4f22841ab4194d9e",
    "runtimeSHA256": "09a01488a2c16d08c97a630e350aeb871afe373f76d0a3ab13cff1194a2d8e54",
    "runtimeKeccak256": "f7a15c5035c21493cf7e274f36853cd776194db69c3a460e484bd5eab91dbb83",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "bd8cdfcf37579b57bcd2026d41b1ec42968996de8560d86a8055310ddc3ab68a",
    "runtimeSHA256": "5653c29a9a6236428c077f4f6489c64a39f18dccde461feaafaa5cc3250874d5",
    "runtimeKeccak256": "9644f4cfefacecf765ed180fde65057a18c71d0d2909d737dfb387082b78ccd8",
}


def replace_exact(text, old, new, count):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both interpreter layouts are mechanically raw39 with only a fresh domain and
# the measured raw count/aggregate byte limits. All 91 bootstrap image bytes,
# including image5 Throwable, remain byte-for-byte inherited.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 39;", "MAX_RAW_CLASSES = 40;", 1)
    want = replace_exact(want, "MAX_RAW_BYTES = 294891;", "MAX_RAW_BYTES = 295438;", 1)
    want = replace_exact(want, "uint32(39), uint32(294891)", "uint32(40), uint32(295438)", 1)
    assert stage_text(relative) == want, relative

# Only fresh binding identity/code hash, fixed count arrays/guard, aggregate
# byte guard, and domain change in the public coordinator.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"', 1)
want = replace_exact(want, 'hex"6a620bfa05bf59aff5112b5fe3e3b149546b041e192f3b559f9c7dd4a4449695"',
                     'hex"' + ENGINE_PIN["runtimeKeccak256"] + '"', 1)
want = replace_exact(want, "[39]", "[40]", 4)
want = replace_exact(want, "n > 39", "n > 40", 1)
want = replace_exact(want, "size > 294891", "size > 295438", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change: only
# its domain, anchor identities/hashes and both count guards advance one step.
parent_pins = json.loads((parent / "build-pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE, 1)
want = replace_exact(want, OLD_OWNER, OWNER, 1)
want = replace_exact(want, parent_pins["engine"]["runtimeSHA256"], ENGINE_PIN["runtimeSHA256"], 1)
want = replace_exact(want, parent_pins["engine"]["runtimeKeccak256"], ENGINE_PIN["runtimeKeccak256"], 1)
want = replace_exact(want, parent_pins["coordinator"]["runtimeKeccak256"], COORDINATOR_PIN["runtimeKeccak256"], 1)
want = replace_exact(want, "len(m.Decoders) > 39", "len(m.Decoders) > 40", 1)
want = replace_exact(want, "len(parts) > 39", "len(parts) > 40", 1)
assert stage_text("tools/Go.txt") == want

# Generated fixtures add exactly the raw41 refusal and raw40 aggregate-byte
# witnesses. No original input names or files occur in this source.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "raw39 boundaries", "raw40 boundaries", 1)
want = replace_exact(want, "java-diff-mc-classcount39-byte294891-fixtures-",
                     "java-diff-mc-classcount40-byte295438-fixtures-", 1)
want = replace_exact(want, "# Exact raw39 and aggregate-byte boundaries exercise this measured cap lift.",
                     "# Exact raw40 and aggregate-byte boundaries exercise this measured cap lift.", 1)
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41)", 1)
want = replace_exact(want, 'count_fixture("count-39-294891", 39, 294891)',
                     'count_fixture("count-40-295438", 40, 295438)', 1)
want = replace_exact(want, 'count_fixture("count-39-294892", 39, 294892)',
                     'count_fixture("count-40-295439", 40, 295439)', 1)
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=130", "classes<=131", 1)
    assert stage_text(relative) == want, relative

# The unchanged retained-gate prefix/suffix are byte-exact after declared pin
# changes. The focused capacity block is separately content-addressed.
old_gate = parent_text("tools/gate.py")
new_gate = stage_text("tools/gate.py")
old_start = old_gate.index("# Exact raw39 is the focused capacity witness")
old_end = old_gate.index("# Retained EnumSet", old_start)
new_start = new_gate.index("# Exact raw40 is the focused capacity witness")
new_end = new_gate.index("# Retained EnumSet", new_start)
want = old_gate[:old_start]
for old, new in (
    ('"""Generated-only raw39/byte294891 capacity and retained dynamic-Throwable gate.', '"""Generated-only raw40/byte295438 capacity and retained dynamic-Throwable gate.'),
    ("java-diff-mc-classcount39-byte294891-build-", "java-diff-mc-classcount40-byte295438-build-"),
    ("java-diff-mc-classcount39-byte294891-fixtures-", "java-diff-mc-classcount40-byte295438-fixtures-"),
    ("java-diff-mc-classcount39-byte294891-gate-", "java-diff-mc-classcount40-byte295438-gate-"),
    ('pins["bootstrapCount"] == 91 and pins["rawLimits"] == [39, 294891]', 'pins["bootstrapCount"] == 91 and pins["rawLimits"] == [40, 295438]'),
    ('pins["diagnosticClassBound"] == 130', 'pins["diagnosticClassBound"] == 131'),
    ('head["totalClassBytes"] <= 294891', 'head["totalClassBytes"] <= 295438'),
):
    want = replace_exact(want, old, new, 1)
assert new_gate[:new_start] == want
capacity_hash = hashlib.sha256(new_gate[new_start:new_end].encode()).hexdigest()
assert capacity_hash == "cb8edc0c52d7c2471550b6393b1306a66126f95d9e5a6672ae5a1a9bc8c11ba5", capacity_hash
old_suffix = old_gate[old_end:]
new_suffix = new_gate[new_end:]
want = replace_exact(old_suffix, '"profile": "MC-RAW39-BYTE294891-P1"', '"profile": "MC-RAW40-BYTE295438-P1"', 1)
old_limits = "Only selected raw-class capacity changes from the accepted dynamic Throwable message-sink stage: raw38/285489/diagnostic129 to raw39/294891/diagnostic130. All 91 ordered bootstrap images and bytes, including dynamic image5 Throwable and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, ReusableParameterizedMessage, provider construction, factory, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay."
new_limits = "Only selected raw-class capacity changes from raw39/294891/diagnostic130 to raw40/295438/diagnostic131. All 91 ordered bootstrap images and bytes, including dynamic image5 Throwable and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, ReusableMessage, provider construction, factory, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay."
want = replace_exact(want, old_limits, new_limits, 1)
assert new_suffix == want

want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned generated raw39/byte294891 evidence."""',
                     '"""Rebuild the pinned generated raw40/byte295438 evidence."""', 1)
want = replace_exact(want, "java-diff-mc-classcount39-byte294891-build-",
                     "java-diff-mc-classcount40-byte295438-build-", 1)
assert stage_text("tools/build.py") == want

# Bootstrap sources/images and their ordered leaf hashes are retained. The
# root is recomputed from the new DBOOT domain; it is not folded into source.
for file in sorted((parent / "bootstrap").rglob("*")):
    if file.is_file():
        relative = file.relative_to(parent)
        assert (stage / relative).read_bytes() == file.read_bytes(), relative
record = json.loads((stage / "root-commitment.json").read_text())
base_root = json.loads((parent / "root-commitment.json").read_text())
assert record["domain"] == D and record["bootstrapCount"] == 91
assert record["keccak256"] == base_root["keccak256"] and record["order"] == base_root["order"]
assert record["dboot"] == "ecbcfff8f5bf3cc79914767c02951be069656dc3c399cb7fe4429d1b1b25b19a"
assert record["bootstrapRoot"] == "5e564b084add9fce889d92e5c081b8dfcc0b39cb34f6445f99465cc83670f6e0"
assert pins["basis"] == "23ed15203" and pins["parentEvidence"] == "classcount39-byte294891-preflight"
assert pins["domain"] == D and pins["runtimeBaseline"] == 389150 and pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 91 and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]
assert pins["globalNativeBindings"] == 13 and pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14
assert pins["maxFrames"] == 128 and pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000
assert pins["rawLimits"] == [40, 295438] and pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768
assert pins["diagnosticClassBound"] == 131 and pins["address"] == "0x" + ENGINE and pins["owner"] == "0x" + OWNER
assert pins["limitsCommitment"] == "18d9d7cf87bfcce04e1e5a9180f7ecd00781a7c3de4abdb6ef8f7226ba610d51"
assert pins["compiler"] == parent_pins["compiler"] and pins["engine"] == ENGINE_PIN and pins["coordinator"] == COORDINATOR_PIN
assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "domain": D, "bootstrapImages": 91,
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 131, "runtimeBaseline": 389150,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
