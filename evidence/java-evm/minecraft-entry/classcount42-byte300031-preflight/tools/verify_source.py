#!/usr/bin/env python3
"""Pin raw42/300031 to accepted generated raw41 sources only."""
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount41-byte298630-preflight"
D = "MC-RAW42-BYTE300031-P1"
OLD_D = "MC-RAW41-BYTE298630-P1"
ENGINE = "4d432d52415734322d4259544533303030333145"
OWNER = "4d432d52415734322d425954453330303033314f"
OLD_ENGINE = "4d432d52415734312d4259544532393836333045"
OLD_OWNER = "4d432d52415734312d425954453239383633304f"
ENGINE_PIN = {
    "bytes": 391172,
    "initSHA256": "24f2a98bdb9912ebab402652ea8e16bc3322ed8d61cf26e11f8abfdebd52d480",
    "runtimeSHA256": "f014a62a704c5b5e08140f76b9bd3c282e00793b592ee317176cefd75aad582f",
    "runtimeKeccak256": "4fe44f4b28366948897fb06dbbbc1f48c6b69b9438b1c5f79b7a72b20cc84652",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "365fa6efdb9cd09a7c6329ecbfa9213d8ca6a640a7826c042da623541c2f459c",
    "runtimeSHA256": "d019f8e78c362cec400fa2454e25473f36b826aaca00bc35ac87d582adaf6485",
    "runtimeKeccak256": "8a7d267168aadb3a15905746c878feb9febed865aa049a7ca2a8c3be6e780ccf",
}
LIMITS = "9e6360811b4968660bf0499e784f3cc26554a36559059ead3ebac2a39153fdfe"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the accepted raw41 interpreter with only the
# fresh domain, raw class count, aggregate raw bytes, and committed limits.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 41;", "MAX_RAW_CLASSES = 42;")
    want = replace_exact(want, "MAX_RAW_BYTES = 298630;", "MAX_RAW_BYTES = 300031;")
    want = replace_exact(want, "uint32(41), uint32(298630)", "uint32(42), uint32(300031)")
    assert stage_text(relative) == want, relative

# The public EVM coordinator changes only fresh binding identity/code hash,
# fixed array/count guards, aggregate byte guards, and domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "a10a2d2980b33b677e71722d74731881bb08aca69dd3cfe2dbde6bec00fd6cce", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[41]", "[42]", 4)
want = replace_exact(want, "n > 41", "n > 42")
want = replace_exact(want, "298630", "300031", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change: only
# domains, fixed identities/hashes and its two product count guards advance.
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE)
want = replace_exact(want, OLD_OWNER, OWNER)
want = replace_exact(want, "a31737df26b36914a7843fbb8db67614612c00fde75a6158dea76bb8ee6a23b1", ENGINE_PIN["runtimeSHA256"])
want = replace_exact(want, "a10a2d2980b33b677e71722d74731881bb08aca69dd3cfe2dbde6bec00fd6cce", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "da83f5f0f78c7746df0639a594eacbe232c8336dea1815d1275e0d016d9149f2", COORDINATOR_PIN["runtimeKeccak256"])
want = replace_exact(want, "len(m.Decoders) > 41", "len(m.Decoders) > 42")
want = replace_exact(want, "len(parts) > 41", "len(parts) > 42")
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures change only exact capacity labels/counts and their
# local output path; no original/JAR/class/resource input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "raw41", "raw42", 2)
want = replace_exact(want, "classcount41-byte298630", "classcount42-byte300031")
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43)")
want = replace_exact(want, 'count_fixture("count-41-298630", 41, 298630)', 'count_fixture("count-42-300031", 42, 300031)')
want = replace_exact(want, 'count_fixture("count-41-298631", 41, 298631)', 'count_fixture("count-42-300032", 42, 300032)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=133", "classes<=134")
    assert stage_text(relative) == want, relative

# The capacity gate remains the accepted retained corpus plus an independently
# generated raw42/raw43 and exact-byte boundary witness. Rebuild its expected
# source mechanically to prevent unrelated behavior changes.
def expected_gate(text):
    text = replace_exact(text, "classcount41-byte298630", "classcount42-byte300031", 3)
    text = replace_exact(text, OLD_D, D)
    text = replace_exact(text, "298631", "300032", 8)
    text = replace_exact(text, "298630", "300031", 12)
    text = replace_exact(text, "raw42", "RAW42_REFUSAL", 13)
    text = replace_exact(text, "raw41", "raw42", 4)
    text = replace_exact(text, "RAW42_REFUSAL", "raw43", 13)
    text = replace_exact(text, "Raw42 is independently refused", "Raw43 is independently refused")
    text = replace_exact(text, "count-42", "COUNT42_REFUSAL", 6)
    text = replace_exact(text, "count-41", "count-42", 7)
    text = replace_exact(text, "COUNT42_REFUSAL", "count-43", 6)
    text = replace_exact(text, 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [41, 300031]',
                         'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [42, 300031]')
    text = replace_exact(text, 'pins["diagnosticClassBound"] == 133 and pins["engine"]["bytes"] <= 393216',
                         'pins["diagnosticClassBound"] == 134 and pins["engine"]["bytes"] <= 393216')
    old_driver = '''assert source.count("len(m.Decoders) > 41") == 1 and source.count("len(parts) > 41") == 1
    source = (source.replace("len(m.Decoders) > 41", "len(m.Decoders) > 42")
                    .replace("len(parts) > 41", "len(parts) > 42"))'''
    new_driver = '''assert source.count("len(m.Decoders) > 42") == 1 and source.count("len(parts) > 42") == 1
    source = (source.replace("len(m.Decoders) > 42", "len(m.Decoders) > 43")
                    .replace("len(parts) > 42", "len(parts) > 43"))'''
    text = replace_exact(text, old_driver, new_driver)
    old_probe = '''assert text.count("[41]") == 4 and text.count("n > 41") == 1
probe_source.write_text(text.replace("[41]", "[42]").replace("n > 41", "n > 42"))'''
    new_probe = '''assert text.count("[42]") == 4 and text.count("n > 42") == 1
probe_source.write_text(text.replace("[42]", "[43]").replace("n > 42", "n > 43"))'''
    text = replace_exact(text, old_probe, new_probe)
    text = replace_exact(text, 'words(refusal) == ["1", "42"]', 'words(refusal) == ["1", "43"]')
    text = replace_exact(text, 'spec["bindingCount"] == 41', 'spec["bindingCount"] == 42')
    old_limit = "Only selected raw-class capacity changes from the accepted TreeMap SortedMap fresh-empty stage: raw40/295438/diagnostic132 to raw42/300031/diagnostic133. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, SimpleMessage, provider construction, factory, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay."
    new_limit = "Only selected raw-class capacity changes from the accepted raw41/byte298630 stage: raw41/298630/diagnostic133 to raw42/300031/diagnostic134. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, SimpleMessage, SimpleLoggerContextFactory, provider construction, factory execution, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay."
    return replace_exact(text, old_limit, new_limit)

assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned generated raw41/byte298630 evidence."""',
                     '"""Rebuild the pinned generated raw42/byte300031 evidence."""')
want = replace_exact(want, "classcount41-byte298630", "classcount42-byte300031")
assert stage_text("tools/build.py") == want

# Bootstrap material, source and hex images are exact inherited bytes. The
# ordered root is recomputed under only the fresh DBOOT domain, never folded.
for file in sorted((parent / "bootstrap").rglob("*")):
    if file.is_file():
        rel = file.relative_to(parent)
        assert (stage / rel).read_bytes() == file.read_bytes(), rel
record = json.loads(stage_text("root-commitment.json"))
parent_record = json.loads(parent_text("root-commitment.json"))
node = root / "jvmevm/runtime/node_modules"
env = {**os.environ, "NODE_PATH": str(node)}
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + D + ":BOOTSTRAP:1"], cwd=root, env=env, text=True))
assert record == {**parent_record, "domain": D, "dboot": actual["d"], "bootstrapRoot": actual["r"]}
limits = [42, 300031, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "806561af7", "parentEvidence": "classcount41-byte298630-preflight", "phase": "built",
                      "domain": D, "runtimeBaseline": 391172, "rawLimits": [42, 300031],
                      "diagnosticClassBound": 134, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
                      "limitsCommitment": LIMITS, "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN})
assert pins == expected_pins
assert pins["bootstrapCount"] == 92 and pins["globalNativeBindings"] == 13
assert pins["runtimeBaseline"] == 391172 and pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert stage_text("tools/strip_stackmap.py") == parent_text("tools/strip_stackmap.py")
assert stage_text("tools/verify_receipts.js") == parent_text("tools/verify_receipts.js")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "domain": D, "bootstrapImages": 92,
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 134, "runtimeBaseline": 391172,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
