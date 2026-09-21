#!/usr/bin/env python3
"""Pin generated raw50/324338 to the generated raw49 source stage only."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount49-byte322481-preflight"
D = "MC-RAW50-BYTE324338-P1"
OLD_D = "MC-RAW49-BYTE322481-P1"
ENGINE = "4d432d52415735302d4259544533323433333845"
OWNER = "4d432d52415735302d425954453332343333384f"
OLD_ENGINE = "4d432d52415734392d4259544533323234383145"
OLD_OWNER = "4d432d52415734392d425954453332323438314f"
ENGINE_PIN = {"bytes": 391507, "initSHA256": "3814ec50bdf31fad688a4860d510e45b48d7fd9a2ecd33d10c51e82868f83b32", "runtimeSHA256": "944590f82f2f20a9a295b7950c9163221ca260e0675099369a86df6b4086f24e", "runtimeKeccak256": "908b5e3ac6cd7ed1743cd6ea87ffe2557bcbe51b22fd8728d05c3d9f0609310a"}
COORDINATOR_PIN = {"bytes": 5394, "initSHA256": "e0b00df8861edc02d691d4f9c8e4b2dfd01abcb526c1d68971cdab83d1336a3f", "runtimeSHA256": "02a1828f0f43a2c2e57ed5f6223cb34f1a1ff9fce3536b10e4ae9dd1c0e16dcd", "runtimeKeccak256": "596906f79fd7c9a526532112b98601e48e4d3f44ee6224356506073318ad9447"}
LIMITS = "b9bc6dc95e7de777dd6e512f44131177e4741934f18d2d25f7ba506ad1594b9c"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the generated raw49 interpreter with only the
# fresh domain, exact raw capacities, and committed limits tuple changed.
def expected_engine(text):
    text = replace_exact(text, OLD_D, D, 9)
    text = replace_exact(text, "MAX_RAW_CLASSES = 49;", "MAX_RAW_CLASSES = 50;")
    text = replace_exact(text, "MAX_RAW_BYTES = 322481;", "MAX_RAW_BYTES = 324338;")
    return replace_exact(text, "uint32(49), uint32(322481)", "uint32(50), uint32(324338)")


for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    assert stage_text(relative) == expected_engine(parent_text(relative)), relative

# Coordinator semantics remain byte-for-byte inherited apart from its fresh
# EVM binding/hash, four fixed arrays, guards, byte limits, and package domains.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "adf3f488d988d0b60b5555c8a8ac797f9f033cc07a7f57cd2e2853d8472b3789", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[49]", "[50]", 4)
want = replace_exact(want, "n > 49", "n > 50")
want = replace_exact(want, "322481", "324338", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The EVM transport changes only domain/identity/hash pins and the two product
# count guards. No host class interpretation or fallback is introduced.
want = parent_text("tools/Go.txt")
for old, new, count in (
    (OLD_D, D, 6), (OLD_OWNER, OWNER, 1), (OLD_ENGINE, ENGINE, 1),
    ("4bd4abf1432957891613758d21ef0122c701027e0f554ce4616cb1836baa8907", ENGINE_PIN["runtimeSHA256"], 1),
    ("0xadf3f488d988d0b60b5555c8a8ac797f9f033cc07a7f57cd2e2853d8472b3789", "0x" + ENGINE_PIN["runtimeKeccak256"], 1),
    ("0x50e3f2e1e6420d5648afbb101f68b53756986c5acfc89a2cbbdc28a52ca151ad", "0x" + COORDINATOR_PIN["runtimeKeccak256"], 1),
    ("len(m.Decoders) > 49", "len(m.Decoders) > 50", 1),
    ("len(parts) > 49", "len(parts) > 50", 1),
):
    want = replace_exact(want, old, new, count)
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures preserve the corpus; only the exact raw50/raw51
# and aggregate 324338/324339 capacity witnesses advance.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "java-diff-mc-classcount49-byte322481-fixtures-", "java-diff-mc-classcount50-byte324338-fixtures-")
want = replace_exact(want, "# Exact raw49 and aggregate-byte boundaries exercise this measured cap lift.", "# Exact raw50 and aggregate-byte boundaries exercise this measured cap lift.")
want = replace_exact(want,
    "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50)",
    "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51)")
want = replace_exact(want, 'count_fixture("count-49-322481", 49, 322481)', 'count_fixture("count-50-324338", 50, 324338)')
want = replace_exact(want, 'count_fixture("count-49-322482", 49, 322482)', 'count_fixture("count-50-324339", 50, 324339)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    assert stage_text(relative) == replace_exact(parent_text(relative), "classes<=142", "classes<=143"), relative


def expected_gate(text):
    text = replace_exact(text, "java-diff-mc-classcount49-byte322481-build-", "java-diff-mc-classcount50-byte324338-build-")
    text = replace_exact(text, "java-diff-mc-classcount49-byte322481-fixtures-", "java-diff-mc-classcount50-byte324338-fixtures-")
    text = replace_exact(text, "java-diff-mc-classcount49-byte322481-gate-", "java-diff-mc-classcount50-byte324338-gate-")
    text = replace_exact(text, "[49, 322481]", "[50, 324338]")
    text = replace_exact(text, 'diagnosticClassBound"] == 142', 'diagnosticClassBound"] == 143')
    text = replace_exact(text, 'head["totalClassBytes"] <= 322481', 'head["totalClassBytes"] <= 324338')
    start = text.index("# Exact raw49 is the focused capacity witness:")
    end = text.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    block = text[start:end]
    block = replace_exact(block, "raw49", "__RAW49__", 2)
    block = replace_exact(block, "raw50", "raw51", 13)
    block = replace_exact(block, "__RAW49__", "raw50", 2)
    block = replace_exact(block, "count-49-322481", "__BYTE_FIT__", 3)
    block = replace_exact(block, "count-49-322482", "__BYTE_OVER__", 3)
    block = replace_exact(block, "count-49", "__COUNT49__", 1)
    block = replace_exact(block, "count-50", "count-51", 6)
    block = replace_exact(block, "__COUNT49__", "count-50", 1)
    block = replace_exact(block, "__BYTE_FIT__", "count-50-324338", 3)
    block = replace_exact(block, "__BYTE_OVER__", "count-50-324339", 3)
    block = replace_exact(block, '''assert source.count("len(m.Decoders) > 49") == 1 and source.count("len(parts) > 49") == 1
    source = (source.replace("len(m.Decoders) > 49", "len(m.Decoders) > 50")
                    .replace("len(parts) > 49", "len(parts) > 50"))''', '''assert source.count("len(m.Decoders) > 50") == 1 and source.count("len(parts) > 50") == 1
    source = (source.replace("len(m.Decoders) > 50", "len(m.Decoders) > 51")
                    .replace("len(parts) > 50", "len(parts) > 51"))''')
    block = replace_exact(block, '''assert text.count("[49]") == 4 and text.count("n > 49") == 1
probe_source.write_text(text.replace("[49]", "[50]").replace("n > 49", "n > 50"))''', '''assert text.count("[50]") == 4 and text.count("n > 50") == 1
probe_source.write_text(text.replace("[50]", "[51]").replace("n > 50", "n > 51"))''')
    block = replace_exact(block, '["1", "50"]', '["1", "51"]')
    block = replace_exact(block, 'bindingCount"] == 49', 'bindingCount"] == 50')
    block = replace_exact(block, "322481", "__BYTES_OLD__", 5)
    block = replace_exact(block, "322482", "324339", 5)
    block = replace_exact(block, "__BYTES_OLD__", "324338", 5)
    block = replace_exact(block, "Raw50 is independently refused", "Raw51 is independently refused")
    text = text[:start] + block + text[end:]
    text = replace_exact(text, OLD_D, D)
    old = "Only selected raw-class capacity changes from accepted equalsIgnoreCase evidence: raw48/314425/diagnostic141 to raw49/322481/diagnostic142. All 93 ordered bootstrap images and bytes, including String.equalsIgnoreCase at root-leaf26 and Objects image93, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and the runtime-derived ordered root remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine ReflectionUtil append and class/factory execution or accelerated replay."
    new = "Only selected raw-class capacity changes from raw49 evidence: raw49/322481/diagnostic142 to raw50/324338/diagnostic143. All 93 ordered bootstrap images and bytes, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and the runtime-derived ordered root remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine ReflectionUtil$PrivateSecurityManager append and class/factory execution or accelerated replay."
    return replace_exact(text, old, new)


assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned generated raw49/byte322481 evidence."""', '"""Rebuild the pinned generated raw50/byte324338 evidence."""')
want = replace_exact(want, "java-diff-mc-classcount49-byte322481-build-", "java-diff-mc-classcount50-byte324338-build-")
assert stage_text("tools/build.py") == want
for relative in ("tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert stage_text(relative) == parent_text(relative), relative

# Bootstrap source/hex material and ordered leaves are inherited exact bytes;
# only DBOOT and the dynamically-derived root receive the fresh domain.
for file in sorted((parent / "bootstrap").rglob("*")):
    if file.is_file():
        rel = file.relative_to(parent)
        assert (stage / rel).read_bytes() == file.read_bytes(), rel
record = json.loads(stage_text("root-commitment.json"))
parent_record = json.loads(parent_text("root-commitment.json"))
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
env = {**os.environ, "NODE_PATH": str(node)}
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + D + ":BOOTSTRAP:1"], cwd=root, env=env, text=True))
assert record == {**parent_record, "domain": D, "dboot": actual["d"], "bootstrapRoot": actual["r"]}
limits = [50, 324338, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "ba37d249b", "parentEvidence": "classcount49-byte322481-preflight", "phase": "built", "domain": D,
                      "runtimeBaseline": 391507, "rawLimits": [50, 324338], "diagnosticClassBound": 143,
                      "address": "0x" + ENGINE, "owner": "0x" + OWNER, "limitsCommitment": LIMITS,
                      "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN})
assert pins == expected_pins
assert pins["bootstrapCount"] == 93 and pins["globalNativeBindings"] == 13
assert pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["runtimeBaseline"] == pins["engine"]["bytes"] == 391507 and pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000
assert pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768
assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert "raw50" in stage_text("README.md") and "raw51" in stage_text("README.md")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "basis": "ba37d249b", "domain": D, "bootstrapImages": 93,
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 143, "runtimeBaseline": 391507,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
