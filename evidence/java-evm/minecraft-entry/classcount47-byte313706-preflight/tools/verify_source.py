#!/usr/bin/env python3
"""Pin raw47/313706 to accepted generated raw46 sources only."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount46-byte311898-preflight"
D = "MC-RAW47-BYTE313706-P1"
OLD_D = "MC-RAW46-BYTE311898-P1"
ENGINE = "4d432d52415734372d4259544533313337303645"
OWNER = "4d432d52415734372d425954453331333730364f"
OLD_ENGINE = "4d432d52415734362d4259544533313138393845"
OLD_OWNER = "4d432d52415734362d425954453331313839384f"
ENGINE_PIN = {
    "bytes": 391172,
    "initSHA256": "8a8aaa5b037cd35ce7641ffc2392c10b8e27172be1ede227f43900f58ed4b646",
    "runtimeSHA256": "214792301b01c23ac6087cbde365b1a8ecea0322c3fdb5019677647cbceca83b",
    "runtimeKeccak256": "f7d169743620ca56584c8ecb6b3e5f03232de65333cec30155c72ab66b3fff53",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "b55401c7e39180f2e009f77e0c68e544dc4ecf055383f67d1fa5904c3d6b0dc7",
    "runtimeSHA256": "9a19ad974381c39bdecb6ca0b8f7cec7142f1f2310336f5031a6e7e0fcc62936",
    "runtimeKeccak256": "93a31acdebd684548d18f3cbdbdf5a875762d08de66e193a1d23a558b803b216",
}
LIMITS = "06001a95eec33dc6360af393be709108d85bb6df0e8136212b7b40177e9b1a95"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the accepted raw46 interpreter with only the
# fresh domain, raw class count, aggregate raw bytes, and committed limits.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 46;", "MAX_RAW_CLASSES = 47;")
    want = replace_exact(want, "MAX_RAW_BYTES = 311898;", "MAX_RAW_BYTES = 313706;")
    want = replace_exact(want, "uint32(46), uint32(311898)", "uint32(47), uint32(313706)")
    assert stage_text(relative) == want, relative

# The public EVM coordinator changes only fresh binding identity/code hash,
# fixed array/count guards, aggregate byte guards, and domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "8e5a65e87cb98ea0a8649193f5dd42df8d78e00cfbe91cad5700fee17bd63805", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[46]", "[47]", 4)
want = replace_exact(want, "n > 46", "n > 47")
want = replace_exact(want, "311898", "313706", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change: only
# domains, fixed identities/hashes and its two product count guards advance.
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE)
want = replace_exact(want, OLD_OWNER, OWNER)
want = replace_exact(want, "5b72a6a43ec7dc206d4b8d7c1f587d1a75a5b1d628417647a6594d4b698d26ed", ENGINE_PIN["runtimeSHA256"])
want = replace_exact(want, "8e5a65e87cb98ea0a8649193f5dd42df8d78e00cfbe91cad5700fee17bd63805", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "b8d640a7ab599ac4d7ff7c0fc197431d69848a0842e6b257dda978e6b812ac22", COORDINATOR_PIN["runtimeKeccak256"])
want = replace_exact(want, "len(m.Decoders) > 46", "len(m.Decoders) > 47")
want = replace_exact(want, "len(parts) > 46", "len(parts) > 47")
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures change only exact capacity labels/counts and their
# local output path; no original/JAR/class/resource input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "raw46", "raw47", 2)
want = replace_exact(want, "classcount46-byte311898", "classcount47-byte313706")
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48)")
want = replace_exact(want, 'count_fixture("count-46-311898", 46, 311898)', 'count_fixture("count-47-313706", 47, 313706)')
want = replace_exact(want, 'count_fixture("count-46-311899", 46, 311899)', 'count_fixture("count-47-313707", 47, 313707)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=138", "classes<=139")
    assert stage_text(relative) == want, relative

# The capacity gate remains the accepted retained corpus plus an independently
# generated raw47/raw48 and exact-byte boundary witness. Rebuild its expected
# source mechanically to prevent unrelated behavior changes.
def expected_gate(text):
    text = replace_exact(text, "classcount46-byte311898", "classcount47-byte313706", 3)
    text = replace_exact(text, OLD_D, D)
    text = replace_exact(text, "311899", "313707", 8)
    text = replace_exact(text, "311898", "313706", 12)
    text = replace_exact(text, "raw47", "RAW47_REFUSAL", 13)
    text = replace_exact(text, "raw46", "raw47", 4)
    text = replace_exact(text, "RAW47_REFUSAL", "raw48", 13)
    text = replace_exact(text, "Raw47 is independently refused", "Raw48 is independently refused")
    text = replace_exact(text, "count-47", "COUNT47_REFUSAL", 6)
    text = replace_exact(text, "count-46", "count-47", 7)
    text = replace_exact(text, "COUNT47_REFUSAL", "count-48", 6)
    text = replace_exact(text, 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [46, 313706]',
                         'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [47, 313706]')
    text = replace_exact(text, 'pins["diagnosticClassBound"] == 138 and pins["engine"]["bytes"] <= 393216',
                         'pins["diagnosticClassBound"] == 139 and pins["engine"]["bytes"] <= 393216')
    old_driver = '''assert source.count("len(m.Decoders) > 46") == 1 and source.count("len(parts) > 46") == 1
    source = (source.replace("len(m.Decoders) > 46", "len(m.Decoders) > 47")
                    .replace("len(parts) > 46", "len(parts) > 47"))'''
    new_driver = '''assert source.count("len(m.Decoders) > 47") == 1 and source.count("len(parts) > 47") == 1
    source = (source.replace("len(m.Decoders) > 47", "len(m.Decoders) > 48")
                    .replace("len(parts) > 47", "len(parts) > 48"))'''
    text = replace_exact(text, old_driver, new_driver)
    old_probe = '''assert text.count("[46]") == 4 and text.count("n > 46") == 1
probe_source.write_text(text.replace("[46]", "[47]").replace("n > 46", "n > 47"))'''
    new_probe = '''assert text.count("[47]") == 4 and text.count("n > 47") == 1
probe_source.write_text(text.replace("[47]", "[48]").replace("n > 47", "n > 48"))'''
    text = replace_exact(text, old_probe, new_probe)
    text = replace_exact(text, 'words(refusal) == ["1", "47"]', 'words(refusal) == ["1", "48"]')
    text = replace_exact(text, 'spec["bindingCount"] == 46', 'spec["bindingCount"] == 47')
    old_limit = "Only selected raw-class capacity changes from the accepted raw45/byte306227 stage: raw45/306227/diagnostic137 to raw47/313706/diagnostic138. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns the genuine append and class/factory execution or accelerated replay."
    new_limit = "Only selected raw-class capacity changes from the accepted raw46/byte311898 stage: raw46/311898/diagnostic138 to raw47/313706/diagnostic139. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns the genuine append and class/factory execution or accelerated replay."
    return replace_exact(text, old_limit, new_limit)

assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '\"\"\"Rebuild the pinned generated raw46/byte311898 evidence.\"\"\"',
                     '\"\"\"Rebuild the pinned generated raw47/byte313706 evidence.\"\"\"')
want = replace_exact(want, "classcount46-byte311898", "classcount47-byte313706")
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
limits = [47, 313706, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "974b3f109", "parentEvidence": "classcount46-byte311898-preflight", "phase": "built",
                      "domain": D, "runtimeBaseline": 391172, "rawLimits": [47, 313706],
                      "diagnosticClassBound": 139, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
                  "diagnosticClassBound": 139, "runtimeBaseline": 391172,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
