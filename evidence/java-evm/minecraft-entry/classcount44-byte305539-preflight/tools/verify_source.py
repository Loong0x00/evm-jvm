#!/usr/bin/env python3
"""Pin raw44/305539 to accepted generated raw43 sources only."""
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
parent = stage.parent / "classcount43-byte300534-preflight"
D = "MC-RAW44-BYTE305539-P1"
OLD_D = "MC-RAW43-BYTE300534-P1"
ENGINE = "4d432d52415734342d4259544533303535333945"
OWNER = "4d432d52415734342d425954453330353533394f"
OLD_ENGINE = "4d432d52415734332d4259544533303035333445"
OLD_OWNER = "4d432d52415734332d425954453330303533344f"
ENGINE_PIN = {
    "bytes": 391172,
    "initSHA256": "5fb23df97ceb23b1640b0097b656c6c4f815c805aaf34c9518f372482e70d5ab",
    "runtimeSHA256": "c673a487dd3717289734504d5d64aee18f04e28cc96b8a0337f8becc621c42ff",
    "runtimeKeccak256": "fb121320080a753d7ec1dfb3817b37da40eb932b021f450023590b0b6c514544",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "638af3e7d99dd0d5ff1259c42fec778fd5ef83193f7ee3adcc3bcc20f7205115",
    "runtimeSHA256": "dc79fdb65575956fc84e3a13f43aa33e1c41f0fb7ddfd241d95d4b41a1718428",
    "runtimeKeccak256": "7033794fe08924882bd0159658798d704e047b819609f512b67f57db77d680c2",
}
LIMITS = "92b10e366ea3a3118d1965d65496bf9acd192d67cb1f864d1d839a7162903049"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the accepted raw43 interpreter with only the
# fresh domain, raw class count, aggregate raw bytes, and committed limits.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 43;", "MAX_RAW_CLASSES = 44;")
    want = replace_exact(want, "MAX_RAW_BYTES = 300534;", "MAX_RAW_BYTES = 305539;")
    want = replace_exact(want, "uint32(43), uint32(300534)", "uint32(44), uint32(305539)")
    assert stage_text(relative) == want, relative

# The public EVM coordinator changes only fresh binding identity/code hash,
# fixed array/count guards, aggregate byte guards, and domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "aecd47da21b001fbc593317cf588abdca465f6af5a2d30455da6f56e1f1c1066", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[43]", "[44]", 4)
want = replace_exact(want, "n > 43", "n > 44")
want = replace_exact(want, "300534", "305539", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change: only
# domains, fixed identities/hashes and its two product count guards advance.
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE)
want = replace_exact(want, OLD_OWNER, OWNER)
want = replace_exact(want, "27d9e6224cc4a8911388d17d0ba5cd0de012955a8fd2f3a5dc2edec8c83bdf31", ENGINE_PIN["runtimeSHA256"])
want = replace_exact(want, "aecd47da21b001fbc593317cf588abdca465f6af5a2d30455da6f56e1f1c1066", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "15965336f4b728de92d364a7af5d5a30a6b2afc2d3a5ecece7b488bdeee70c87", COORDINATOR_PIN["runtimeKeccak256"])
want = replace_exact(want, "len(m.Decoders) > 43", "len(m.Decoders) > 44")
want = replace_exact(want, "len(parts) > 43", "len(parts) > 44")
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures change only exact capacity labels/counts and their
# local output path; no original/JAR/class/resource input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "raw43", "raw44", 2)
want = replace_exact(want, "classcount43-byte300534", "classcount44-byte305539")
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45)")
want = replace_exact(want, 'count_fixture("count-43-300534", 43, 300534)', 'count_fixture("count-44-305539", 44, 305539)')
want = replace_exact(want, 'count_fixture("count-43-300535", 43, 300535)', 'count_fixture("count-44-305540", 44, 305540)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=135", "classes<=136")
    assert stage_text(relative) == want, relative

# The capacity gate remains the accepted retained corpus plus an independently
# generated raw44/raw45 and exact-byte boundary witness. Rebuild its expected
# source mechanically to prevent unrelated behavior changes.
def expected_gate(text):
    text = replace_exact(text, "classcount43-byte300534", "classcount44-byte305539", 3)
    text = replace_exact(text, OLD_D, D)
    text = replace_exact(text, "300535", "305540", 8)
    text = replace_exact(text, "300534", "305539", 12)
    text = replace_exact(text, "raw44", "RAW44_REFUSAL", 13)
    text = replace_exact(text, "raw43", "raw44", 4)
    text = replace_exact(text, "RAW44_REFUSAL", "raw45", 13)
    text = replace_exact(text, "Raw44 is independently refused", "Raw45 is independently refused")
    text = replace_exact(text, "count-44", "COUNT44_REFUSAL", 6)
    text = replace_exact(text, "count-43", "count-44", 7)
    text = replace_exact(text, "COUNT44_REFUSAL", "count-45", 6)
    text = replace_exact(text, 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [43, 305539]',
                         'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [44, 305539]')
    text = replace_exact(text, 'pins["diagnosticClassBound"] == 135 and pins["engine"]["bytes"] <= 393216',
                         'pins["diagnosticClassBound"] == 136 and pins["engine"]["bytes"] <= 393216')
    old_driver = '''assert source.count("len(m.Decoders) > 43") == 1 and source.count("len(parts) > 43") == 1
    source = (source.replace("len(m.Decoders) > 43", "len(m.Decoders) > 44")
                    .replace("len(parts) > 43", "len(parts) > 44"))'''
    new_driver = '''assert source.count("len(m.Decoders) > 44") == 1 and source.count("len(parts) > 44") == 1
    source = (source.replace("len(m.Decoders) > 44", "len(m.Decoders) > 45")
                    .replace("len(parts) > 44", "len(parts) > 45"))'''
    text = replace_exact(text, old_driver, new_driver)
    old_probe = '''assert text.count("[43]") == 4 and text.count("n > 43") == 1
probe_source.write_text(text.replace("[43]", "[44]").replace("n > 43", "n > 44"))'''
    new_probe = '''assert text.count("[44]") == 4 and text.count("n > 44") == 1
probe_source.write_text(text.replace("[44]", "[45]").replace("n > 44", "n > 45"))'''
    text = replace_exact(text, old_probe, new_probe)
    text = replace_exact(text, 'words(refusal) == ["1", "44"]', 'words(refusal) == ["1", "45"]')
    text = replace_exact(text, 'spec["bindingCount"] == 43', 'spec["bindingCount"] == 44')
    old_limit = "Only selected raw-class capacity changes from the accepted raw42/byte300031 stage: raw42/300031/diagnostic134 to raw44/305539/diagnostic135. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, LoggerContextFactory, provider construction, factory execution, world, or Done input or claim. Parent alone appends the genuine interface and performs genuine class/factory execution and accelerated replay."
    new_limit = "Only selected raw-class capacity changes from the accepted raw43/byte300534 stage: raw43/300534/diagnostic135 to raw44/305539/diagnostic136. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, SimpleLoggerContext, provider construction, factory execution, world, or Done input or claim. Parent alone appends the genuine logger context and performs genuine class/factory execution and accelerated replay."
    return replace_exact(text, old_limit, new_limit)

assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned generated raw43/byte300534 evidence."""',
                     '"""Rebuild the pinned generated raw44/byte305539 evidence."""')
want = replace_exact(want, "classcount43-byte300534", "classcount44-byte305539")
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
limits = [44, 305539, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "9af383370", "parentEvidence": "classcount43-byte300534-preflight", "phase": "built",
                      "domain": D, "runtimeBaseline": 391172, "rawLimits": [44, 305539],
                      "diagnosticClassBound": 136, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
                  "diagnosticClassBound": 136, "runtimeBaseline": 391172,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
