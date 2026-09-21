#!/usr/bin/env python3
"""Pin raw48/314425 to accepted generated raw47 sources only."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount47-byte313706-preflight"
D = "MC-RAW48-BYTE314425-P1"
OLD_D = "MC-RAW47-BYTE313706-P1"
ENGINE = "4d432d52415734382d4259544533313434323545"
OWNER = "4d432d52415734382d425954453331343432354f"
OLD_ENGINE = "4d432d52415734372d4259544533313337303645"
OLD_OWNER = "4d432d52415734372d425954453331333730364f"
ENGINE_PIN = {'bytes': 391172, 'initSHA256': '19d21f256ec92c5605f64085ecb5c10f1fdcafca8d4abf65d46695162d678545', 'runtimeSHA256': 'c0d6a3cf0d5478041835eda2e77cb7f7aa6909589d9a9a678c23ee2543d63af2', 'runtimeKeccak256': '8d04b72ed9c83e78ea0a88201f6c7903c3b20c3cdab3830f7fc1e6b6a003f698'}
COORDINATOR_PIN = {'bytes': 5394, 'initSHA256': 'fea08ce0cd72926564fa04347b9d5140910fba051a6cae1f4ab9c3c23f4e9c46', 'runtimeSHA256': '4a87dba2590ab73b6b24d4a36f146d02d4a2830c81a1dde1edf3c2856102f490', 'runtimeKeccak256': '27622589c53ece1b817a0161e60f9340c28836c9913ded65d407ccb044d1d9b2'}
LIMITS = "5f2a06a684fa6b532bf0a971c3e6a7ed1c7f6d493b764bb8b8619d1d795d3dc4"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the accepted raw47 interpreter with only the
# fresh domain, raw class count, aggregate raw bytes, and committed limits.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 47;", "MAX_RAW_CLASSES = 48;")
    want = replace_exact(want, "MAX_RAW_BYTES = 313706;", "MAX_RAW_BYTES = 314425;")
    want = replace_exact(want, "uint32(47), uint32(313706)", "uint32(48), uint32(314425)")
    assert stage_text(relative) == want, relative

# The public EVM coordinator changes only fresh binding identity/code hash,
# fixed array/count guards, aggregate byte guards, and domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "f7d169743620ca56584c8ecb6b3e5f03232de65333cec30155c72ab66b3fff53", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[47]", "[48]", 4)
want = replace_exact(want, "n > 47", "n > 48")
want = replace_exact(want, "313706", "314425", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change: only
# domains, fixed identities/hashes and its two product count guards advance.
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE)
want = replace_exact(want, OLD_OWNER, OWNER)
want = replace_exact(want, "214792301b01c23ac6087cbde365b1a8ecea0322c3fdb5019677647cbceca83b", ENGINE_PIN["runtimeSHA256"])
want = replace_exact(want, "f7d169743620ca56584c8ecb6b3e5f03232de65333cec30155c72ab66b3fff53", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "93a31acdebd684548d18f3cbdbdf5a875762d08de66e193a1d23a558b803b216", COORDINATOR_PIN["runtimeKeccak256"])
want = replace_exact(want, "len(m.Decoders) > 47", "len(m.Decoders) > 48")
want = replace_exact(want, "len(parts) > 47", "len(parts) > 48")
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures change only exact capacity labels/counts and their
# local output path; no original/JAR/class/resource input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "raw47", "raw48", 2)
want = replace_exact(want, "classcount47-byte313706", "classcount48-byte314425")
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49)")
want = replace_exact(want, 'count_fixture("count-47-313706", 47, 313706)', 'count_fixture("count-48-314425", 48, 314425)')
want = replace_exact(want, 'count_fixture("count-47-313707", 47, 313707)', 'count_fixture("count-48-314426", 48, 314426)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=139", "classes<=140")
    assert stage_text(relative) == want, relative

# The capacity gate remains the accepted retained corpus plus an independently
# generated raw48/raw49 and exact-byte boundary witness. Rebuild its expected
# source mechanically to prevent unrelated behavior changes.
def expected_gate(text):
    text = replace_exact(text, "classcount47-byte313706", "classcount48-byte314425", 3)
    text = replace_exact(text, OLD_D, D)
    text = replace_exact(text, "313707", "314426", 8)
    text = replace_exact(text, "313706", "314425", 12)
    text = replace_exact(text, "raw48", "RAW48_REFUSAL", 13)
    text = replace_exact(text, "raw47", "raw48", 4)
    text = replace_exact(text, "RAW48_REFUSAL", "raw49", 13)
    text = replace_exact(text, "Raw48 is independently refused", "Raw49 is independently refused")
    text = replace_exact(text, "count-48", "COUNT48_REFUSAL", 6)
    text = replace_exact(text, "count-47", "count-48", 7)
    text = replace_exact(text, "COUNT48_REFUSAL", "count-49", 6)
    text = replace_exact(text, 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [47, 314425]',
                         'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [48, 314425]')
    text = replace_exact(text, 'pins["diagnosticClassBound"] == 139 and pins["engine"]["bytes"] <= 393216',
                         'pins["diagnosticClassBound"] == 140 and pins["engine"]["bytes"] <= 393216')
    old_driver = """assert source.count("len(m.Decoders) > 47") == 1 and source.count("len(parts) > 47") == 1
    source = (source.replace("len(m.Decoders) > 47", "len(m.Decoders) > 48")
                    .replace("len(parts) > 47", "len(parts) > 48"))"""
    new_driver = """assert source.count("len(m.Decoders) > 48") == 1 and source.count("len(parts) > 48") == 1
    source = (source.replace("len(m.Decoders) > 48", "len(m.Decoders) > 49")
                    .replace("len(parts) > 48", "len(parts) > 49"))"""
    text = replace_exact(text, old_driver, new_driver)
    old_probe = """assert text.count("[47]") == 4 and text.count("n > 47") == 1
probe_source.write_text(text.replace("[47]", "[48]").replace("n > 47", "n > 48"))"""
    new_probe = """assert text.count("[48]") == 4 and text.count("n > 48") == 1
probe_source.write_text(text.replace("[48]", "[49]").replace("n > 48", "n > 49"))"""
    text = replace_exact(text, old_probe, new_probe)
    text = replace_exact(text, 'words(refusal) == ["1", "48"]', 'words(refusal) == ["1", "49"]')
    text = replace_exact(text, 'spec["bindingCount"] == 47', 'spec["bindingCount"] == 48')
    old_limit = "Only selected raw-class capacity changes from the accepted raw46/byte311898 stage: raw46/311898/diagnostic138 to raw48/314425/diagnostic139. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns the genuine append and class/factory execution or accelerated replay."
    new_limit = "Only selected raw-class capacity changes from the accepted raw47/byte313706 stage: raw47/313706/diagnostic139 to raw48/314425/diagnostic140. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns the genuine append and class/factory execution or accelerated replay."
    return replace_exact(text, old_limit, new_limit)

assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '\"\"\"Rebuild the pinned generated raw47/byte313706 evidence.\"\"\"',
                     '\"\"\"Rebuild the pinned generated raw48/byte314425 evidence.\"\"\"')
want = replace_exact(want, "classcount47-byte313706", "classcount48-byte314425")
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
limits = [48, 314425, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "2c58aa8a1", "parentEvidence": "classcount47-byte313706-preflight", "phase": "built",
                      "domain": D, "runtimeBaseline": 391172, "rawLimits": [48, 314425],
                      "diagnosticClassBound": 140, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
                  "diagnosticClassBound": 140, "runtimeBaseline": 391172,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
