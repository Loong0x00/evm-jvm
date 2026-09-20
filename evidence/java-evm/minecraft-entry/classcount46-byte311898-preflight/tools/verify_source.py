#!/usr/bin/env python3
"""Pin raw46/311898 to accepted generated raw45 sources only."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount45-byte306227-preflight"
D = "MC-RAW46-BYTE311898-P1"
OLD_D = "MC-RAW45-BYTE306227-P1"
ENGINE = "4d432d52415734362d4259544533313138393845"
OWNER = "4d432d52415734362d425954453331313839384f"
OLD_ENGINE = "4d432d52415734352d4259544533303632323745"
OLD_OWNER = "4d432d52415734352d425954453330363232374f"
ENGINE_PIN = {
    "bytes": 391172,
    "initSHA256": "8be16cc351c4a59ea2978d314dfbe5eea674c21ef958028a0c724a656d881251",
    "runtimeSHA256": "5b72a6a43ec7dc206d4b8d7c1f587d1a75a5b1d628417647a6594d4b698d26ed",
    "runtimeKeccak256": "8e5a65e87cb98ea0a8649193f5dd42df8d78e00cfbe91cad5700fee17bd63805",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "6a5ef823692222ee849b05b708a40657eb70fe426c61fc4a96d16f24445ecacb",
    "runtimeSHA256": "57f13abedd312e16a6f640e1ff539623cfdc79b068c218e509cac9ca1bb5d9a2",
    "runtimeKeccak256": "b8d640a7ab599ac4d7ff7c0fc197431d69848a0842e6b257dda978e6b812ac22",
}
LIMITS = "9b162678fd084f20afb87df9844c058dd8654cb52975c71e1436b3ce14dd82a6"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the accepted raw45 interpreter with only the
# fresh domain, raw class count, aggregate raw bytes, and committed limits.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 45;", "MAX_RAW_CLASSES = 46;")
    want = replace_exact(want, "MAX_RAW_BYTES = 306227;", "MAX_RAW_BYTES = 311898;")
    want = replace_exact(want, "uint32(45), uint32(306227)", "uint32(46), uint32(311898)")
    assert stage_text(relative) == want, relative

# The public EVM coordinator changes only fresh binding identity/code hash,
# fixed array/count guards, aggregate byte guards, and domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "80c183d136e94c4c171beac3edb738ec71ad32aa08bff281b6e93e04d5480bc9", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[45]", "[46]", 4)
want = replace_exact(want, "n > 45", "n > 46")
want = replace_exact(want, "306227", "311898", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change: only
# domains, fixed identities/hashes and its two product count guards advance.
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE)
want = replace_exact(want, OLD_OWNER, OWNER)
want = replace_exact(want, "0f73f578c5f57b4288d279b51e6fc956abef1f9bdb82bbea6dfd2d8aad446dca", ENGINE_PIN["runtimeSHA256"])
want = replace_exact(want, "80c183d136e94c4c171beac3edb738ec71ad32aa08bff281b6e93e04d5480bc9", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "3e61625fbc8a085e1afdf5e9ccbf1a0ebe01d733df5a4c20de89e3e277433d84", COORDINATOR_PIN["runtimeKeccak256"])
want = replace_exact(want, "len(m.Decoders) > 45", "len(m.Decoders) > 46")
want = replace_exact(want, "len(parts) > 45", "len(parts) > 46")
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures change only exact capacity labels/counts and their
# local output path; no original/JAR/class/resource input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "raw45", "raw46", 2)
want = replace_exact(want, "classcount45-byte306227", "classcount46-byte311898")
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47)")
want = replace_exact(want, 'count_fixture("count-45-306227", 45, 306227)', 'count_fixture("count-46-311898", 46, 311898)')
want = replace_exact(want, 'count_fixture("count-45-306228", 45, 306228)', 'count_fixture("count-46-311899", 46, 311899)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=137", "classes<=138")
    assert stage_text(relative) == want, relative

# The capacity gate remains the accepted retained corpus plus an independently
# generated raw46/raw47 and exact-byte boundary witness. Rebuild its expected
# source mechanically to prevent unrelated behavior changes.
def expected_gate(text):
    text = replace_exact(text, "classcount45-byte306227", "classcount46-byte311898", 3)
    text = replace_exact(text, OLD_D, D)
    text = replace_exact(text, "306228", "311899", 8)
    text = replace_exact(text, "306227", "311898", 12)
    text = replace_exact(text, "raw46", "RAW46_REFUSAL", 13)
    text = replace_exact(text, "raw45", "raw46", 4)
    text = replace_exact(text, "RAW46_REFUSAL", "raw47", 13)
    text = replace_exact(text, "Raw46 is independently refused", "Raw47 is independently refused")
    text = replace_exact(text, "count-46", "COUNT46_REFUSAL", 6)
    text = replace_exact(text, "count-45", "count-46", 7)
    text = replace_exact(text, "COUNT46_REFUSAL", "count-47", 6)
    text = replace_exact(text, 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [45, 311898]',
                         'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [46, 311898]')
    text = replace_exact(text, 'pins["diagnosticClassBound"] == 137 and pins["engine"]["bytes"] <= 393216',
                         'pins["diagnosticClassBound"] == 138 and pins["engine"]["bytes"] <= 393216')
    old_driver = '''assert source.count("len(m.Decoders) > 45") == 1 and source.count("len(parts) > 45") == 1
    source = (source.replace("len(m.Decoders) > 45", "len(m.Decoders) > 46")
                    .replace("len(parts) > 45", "len(parts) > 46"))'''
    new_driver = '''assert source.count("len(m.Decoders) > 46") == 1 and source.count("len(parts) > 46") == 1
    source = (source.replace("len(m.Decoders) > 46", "len(m.Decoders) > 47")
                    .replace("len(parts) > 46", "len(parts) > 47"))'''
    text = replace_exact(text, old_driver, new_driver)
    old_probe = '''assert text.count("[45]") == 4 and text.count("n > 45") == 1
probe_source.write_text(text.replace("[45]", "[46]").replace("n > 45", "n > 46"))'''
    new_probe = '''assert text.count("[46]") == 4 and text.count("n > 46") == 1
probe_source.write_text(text.replace("[46]", "[47]").replace("n > 46", "n > 47"))'''
    text = replace_exact(text, old_probe, new_probe)
    text = replace_exact(text, 'words(refusal) == ["1", "46"]', 'words(refusal) == ["1", "47"]')
    text = replace_exact(text, 'spec["bindingCount"] == 45', 'spec["bindingCount"] == 46')
    old_limit = "Only selected raw-class capacity changes from the accepted raw44/byte305539 stage: raw44/305539/diagnostic136 to raw46/311898/diagnostic137. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, LoggerContext, provider construction, factory execution, world, or Done input or claim. Parent alone appends the genuine interface and performs genuine class/factory execution and accelerated replay."
    new_limit = "Only selected raw-class capacity changes from the accepted raw45/byte306227 stage: raw45/306227/diagnostic137 to raw46/311898/diagnostic138. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns the genuine append and class/factory execution or accelerated replay."
    return replace_exact(text, old_limit, new_limit)

assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '\"\"\"Rebuild the pinned generated raw45/byte306227 evidence.\"\"\"',
                     '\"\"\"Rebuild the pinned generated raw46/byte311898 evidence.\"\"\"')
want = replace_exact(want, "classcount45-byte306227", "classcount46-byte311898")
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
limits = [46, 311898, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "db2653e21", "parentEvidence": "classcount45-byte306227-preflight", "phase": "built",
                      "domain": D, "runtimeBaseline": 391172, "rawLimits": [46, 311898],
                      "diagnosticClassBound": 138, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
                  "diagnosticClassBound": 138, "runtimeBaseline": 391172,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
