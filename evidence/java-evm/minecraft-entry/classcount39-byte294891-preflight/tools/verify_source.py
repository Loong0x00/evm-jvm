#!/usr/bin/env python3
"""Pin the raw39 delta to the accepted dynamic-Throwable source stage."""
from pathlib import Path
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "throwable-print-stack-trace-preflight"
D = "MC-RAW39-BYTE294891-P1"
OLD_D = "MC-THROWABLE-PRINT-001"
ENGINE = "4d432d52415733392d4259544532393438393145"
OWNER = "4d432d52415733392d425954453239343839314f"
OLD_ENGINE = "4d432d5448524f5741424c452d5052494e542d31"
OLD_OWNER = "4d432d5448524f5741424c452d5052494e542d32"
ENGINE_PIN = {
    "bytes": 389150,
    "initSHA256": "85060bb9c8017b3b08c847abbeebc7763706ca47ff35426a110669dfde68380d",
    "runtimeSHA256": "f0d70bb38950a5cd5e4db8430dc6dc0f860ba865e6b73ae5925b95b0af2eeb34",
    "runtimeKeccak256": "6a620bfa05bf59aff5112b5fe3e3b149546b041e192f3b559f9c7dd4a4449695",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "e0d6d40856b37be96a0ba045f047a997a914e50bc5243ed3f276eacdce6a4343",
    "runtimeSHA256": "b27a59d6a7bf0ddb5d172cb71a0f2c817ec5901b12eff8d2f100932de075abab",
    "runtimeKeccak256": "316ea29a825605f697fe7d1de1e34a3b4b96fc9ee20f5e30c3e184bc9b202c16",
}

def replace_exact(text, old, new, count):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)

def parent_text(relative):
    return (parent / relative).read_text()

def stage_text(relative):
    return (stage / relative).read_text()

# The two interpreter layouts are mechanically the accepted dynamic-Throwable
# sources with just the new domain and raw package limits. In particular, all
# 91 bootstrap materializers—including image5 Throwable—remain byte-for-byte.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 38;", "MAX_RAW_CLASSES = 39;", 1)
    want = replace_exact(want, "MAX_RAW_BYTES = 285489;", "MAX_RAW_BYTES = 294891;", 1)
    want = replace_exact(want, "uint32(38), uint32(285489)", "uint32(39), uint32(294891)", 1)
    assert stage_text(relative) == want, relative

# Coordinator changes are exactly its new fixed arrays/constructor guards plus
# the independently rebuilt engine address/code hash and fresh domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"', 1)
want = replace_exact(want, 'hex"809bbcb06332ac40cc774390022348257438f6e043228e2d810ee44c126edd57"',
                     'hex"' + ENGINE_PIN["runtimeKeccak256"] + '"', 1)
want = replace_exact(want, "[38]", "[39]", 4)
want = replace_exact(want, "n > 38", "n > 39", 1)
want = replace_exact(want, "size > 285489", "size > 294891", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The public-EVM disposable driver has only its domain, fixed addresses/code
# hashes and the two count guards adjusted; no transport semantics are changed.
parent_pins = json.loads((parent / "build-pins.json").read_text())
pins = json.loads((stage / "build-pins.json").read_text())
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE, 1)
want = replace_exact(want, OLD_OWNER, OWNER, 1)
want = replace_exact(want, parent_pins["engine"]["runtimeSHA256"], ENGINE_PIN["runtimeSHA256"], 1)
want = replace_exact(want, parent_pins["engine"]["runtimeKeccak256"], ENGINE_PIN["runtimeKeccak256"], 1)
want = replace_exact(want, parent_pins["coordinator"]["runtimeKeccak256"], COORDINATOR_PIN["runtimeKeccak256"], 1)
want = replace_exact(want, "len(m.Decoders) > 38", "len(m.Decoders) > 39", 1)
want = replace_exact(want, "len(parts) > 38", "len(parts) > 39", 1)
assert stage_text("tools/Go.txt") == want

# Generated fixture changes add the 40-class refusal and the exact raw39 byte
# witnesses; no external input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, '"""Create only trusted generated Java-8 PrintStream.println(String)/print(char) fixtures and retained gates.',
                     '"""Create only trusted generated Java-8 raw39 boundaries and retained controls.', 1)
want = replace_exact(want, "java-diff-mc-throwable-print-stack-trace-fixtures-",
                     "java-diff-mc-classcount39-byte294891-fixtures-", 1)
want = replace_exact(want, "# Exact raw38 and aggregate-byte boundaries exercise this measured cap lift.",
                     "# Exact raw39 and aggregate-byte boundaries exercise this measured cap lift.", 1)
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40)", 1)
want = replace_exact(want, 'count_fixture("count-38-285489", 38, 285489)',
                     'count_fixture("count-39-294891", 39, 294891)', 1)
want = replace_exact(want, 'count_fixture("count-38-285490", 38, 285490)',
                     'count_fixture("count-39-294892", 39, 294892)', 1)
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=129", "classes<=130", 1)
    assert stage_text(relative) == want, relative

# The retained gate's unchanged prefix/suffix are byte-exact after its declared
# path/pin changes. Its focused capacity block is separately hash-pinned.
old_gate = parent_text("tools/gate.py")
new_gate = stage_text("tools/gate.py")
old_start = old_gate.index("# Exact raw38 is the focused capacity witness")
old_end = old_gate.index("# Retained EnumSet", old_start)
new_start = new_gate.index("# Exact raw39 is the focused capacity witness")
new_end = new_gate.index("# Retained EnumSet", new_start)
want = old_gate[:old_start]
for old, new in (
    ('"""One generated-only bounded PrintStream.println(String)/print(char) and retained acceptance gate.', '"""Generated-only raw39/byte294891 capacity and retained dynamic-Throwable gate.'),
    ("java-diff-mc-throwable-print-stack-trace-build-", "java-diff-mc-classcount39-byte294891-build-"),
    ("java-diff-mc-throwable-print-stack-trace-fixtures-", "java-diff-mc-classcount39-byte294891-fixtures-"),
    ("java-diff-mc-throwable-print-stack-trace-gate-", "java-diff-mc-classcount39-byte294891-gate-"),
    ('pins["bootstrapCount"] == 91 and pins["rawLimits"] == [38, 285489]', 'pins["bootstrapCount"] == 91 and pins["rawLimits"] == [39, 294891]'),
    ('pins["diagnosticClassBound"] == 129', 'pins["diagnosticClassBound"] == 130'),
    ('head["totalClassBytes"] <= 285489', 'head["totalClassBytes"] <= 294891'),
):
    want = replace_exact(want, old, new, 1)
assert new_gate[:new_start] == want
capacity_hash = hashlib.sha256(new_gate[new_start:new_end].encode()).hexdigest()
assert capacity_hash == "288132bd10ae2fc9b4f510ae67401a2f29a5a6d3788d6636f8d2bfefcf42fb74", capacity_hash
old_suffix = old_gate[old_end:]
new_suffix = new_gate[new_end:]
old_summary = '"profile": "MC-THROWABLE-PRINT-001"'
new_summary = '"profile": "MC-RAW39-BYTE294891-P1"'
want = replace_exact(old_suffix, old_summary, new_summary, 1)
old_limits = "Only bootstrap image5 java/lang/Throwable changes: its retained constructors/getMessage/getCause use the exact compact Java-8 Code, while printStackTrace(PrintStream) calls the retained PrintStream.println(String) sink only for a non-null detailMessage. Null writes nothing, including with a null PrintStream argument. There is no class name, stack frame, cause, suppressed-exception, encoding, or host-output behavior. h[0] and every unchanged historical leaf remain runtime-derived; h[5] is still keccak256(_bootstrapThrowable()) over exact bytes, with no DBOOT_THROWABLE or folded whole root. The selected image layout uses a statically unreachable fixed-length recursive guard solely to keep the exact image literal materialized once; 657 cannot equal uint256.max. The 91-image order, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."
new_limits = "Only selected raw-class capacity changes from the accepted dynamic Throwable message-sink stage: raw38/285489/diagnostic129 to raw39/294891/diagnostic130. All 91 ordered bootstrap images and bytes, including dynamic image5 Throwable and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, ReusableParameterizedMessage, provider construction, factory, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay."
want = replace_exact(want, old_limits, new_limits, 1)
assert new_suffix == want

# Build script is source-pinned too.
want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned dynamic-root Throwable printStackTrace evidence."""',
                     '"""Rebuild the pinned generated raw39/byte294891 evidence."""', 1)
want = replace_exact(want, "java-diff-mc-throwable-print-stack-trace-build-",
                     "java-diff-mc-classcount39-byte294891-build-", 1)
assert stage_text("tools/build.py") == want

# Bootstrap files and the ordered image hashes are unchanged from the dynamic
# Throwable stage. Only DBOOT/domain changes the derived root value.
for file in sorted((parent / "bootstrap").rglob("*")):
    if file.is_file():
        relative = file.relative_to(parent)
        assert (stage / relative).read_bytes() == file.read_bytes(), relative
record = json.loads((stage / "root-commitment.json").read_text())
base_root = json.loads((parent / "root-commitment.json").read_text())
assert record["domain"] == D and record["bootstrapCount"] == 91
assert record["keccak256"] == base_root["keccak256"] and record["order"] == base_root["order"]
assert record["dboot"] == "bebf21f60c45b7afa1da81c00d4b71a68e83c24260382503f6888649e1f9b637"
assert record["bootstrapRoot"] == "531df01c78166a5af2956bd3f560c11547cbd2b36bc906368bdb5829660a81ec"
assert pins["basis"] == "c7a69daef" and pins["parentEvidence"] == "throwable-print-stack-trace-preflight"
assert pins["domain"] == D and pins["runtimeBaseline"] == 389150 and pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 91 and pins["bootstrapSHA256"] == parent_pins["bootstrapSHA256"]
assert pins["globalNativeBindings"] == 13 and pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14
assert pins["maxFrames"] == 128 and pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000
assert pins["rawLimits"] == [39, 294891] and pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768
assert pins["diagnosticClassBound"] == 130 and pins["address"] == "0x" + ENGINE and pins["owner"] == "0x" + OWNER
assert pins["limitsCommitment"] == "0e567f34859ef528954e781c688147dd1cb0e5b6514f161917158a0c032c0e2f"
assert pins["compiler"] == parent_pins["compiler"] and pins["engine"] == ENGINE_PIN and pins["coordinator"] == COORDINATOR_PIN
assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "domain": D, "bootstrapImages": 91,
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 130, "runtimeBaseline": 389150,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
