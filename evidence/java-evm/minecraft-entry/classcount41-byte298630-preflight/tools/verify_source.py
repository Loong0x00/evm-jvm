#!/usr/bin/env python3
"""Pin raw41/298630 to accepted TreeMap SortedMap fresh-empty sources only."""
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
parent = stage.parent / "tree-map-sorted-empty-preflight"
D = "MC-RAW41-BYTE298630-P1"
OLD_D = "MC-TREEMAP-SORTED-P1"
ENGINE = "4d432d52415734312d4259544532393836333045"
OWNER = "4d432d52415734312d425954453239383633304f"
OLD_ENGINE = "4d432d545245454d41502d534f525445442d5031"
OLD_OWNER = "4d432d545245454d41502d534f525445442d4f31"
ENGINE_PIN = {
    "bytes": 391172,
    "initSHA256": "88eb81f7f2204b34e56bc50f8cc26951546d1722204b753787a82efc9be6e5ed",
    "runtimeSHA256": "a31737df26b36914a7843fbb8db67614612c00fde75a6158dea76bb8ee6a23b1",
    "runtimeKeccak256": "a10a2d2980b33b677e71722d74731881bb08aca69dd3cfe2dbde6bec00fd6cce",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "b433447f9ada1be189986903f2e00498873b5fd5164b752987aab91e57293909",
    "runtimeSHA256": "c20fa18b533081d3b20827fcb77e6d16dfaa7fe12f119b096ff6ecddd127bc82",
    "runtimeKeccak256": "da83f5f0f78c7746df0639a594eacbe232c8336dea1815d1275e0d016d9149f2",
}
LIMITS = "76c295f26639188189be9a69e0c4d9ab8f3aaf30197f8874b21d3f916a2d7ddb"
CAPACITY_SHA256 = "8a0526a9055ea66d5c31a9c4f1dc17ad825558768b1363353d93a9e8434d25b4"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


# Both layouts are mechanically the accepted TreeMap SortedMap fresh-empty
# interpreter with only fresh domain/raw count/raw bytes. All 92 bootstrap image
# materializers and all non-capacity interpreter behavior remain byte-identical.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    want = parent_text(relative)
    want = replace_exact(want, OLD_D, D, 9)
    want = replace_exact(want, "MAX_RAW_CLASSES = 40;", "MAX_RAW_CLASSES = 41;")
    want = replace_exact(want, "MAX_RAW_BYTES = 295438;", "MAX_RAW_BYTES = 298630;")
    want = replace_exact(want, "uint32(40), uint32(295438)", "uint32(41), uint32(298630)")
    assert stage_text(relative) == want, relative

# The public EVM coordinator changes only fresh binding identity/code hash,
# fixed array/count guards, aggregate byte guards, and domain.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "61e095cb3845276f7aa58ecd4c9db2a16e588dce7236ca2c2e22c42d8d99046f", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "[40]", "[41]", 4)
want = replace_exact(want, "n > 40", "n > 41")
want = replace_exact(want, "295438", "298630", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# The disposable public-EVM driver receives no transport semantic change:
# only domains, fixed identities/hashes and the two count guards advance.
want = parent_text("tools/Go.txt")
want = replace_exact(want, OLD_D, D, 6)
want = replace_exact(want, OLD_ENGINE, ENGINE)
want = replace_exact(want, OLD_OWNER, OWNER)
want = replace_exact(want, "828583d9a6f751e9795bdb1afc773d7abbee820565e58a72738f85959a5f9080", ENGINE_PIN["runtimeSHA256"])
want = replace_exact(want, "61e095cb3845276f7aa58ecd4c9db2a16e588dce7236ca2c2e22c42d8d99046f", ENGINE_PIN["runtimeKeccak256"])
want = replace_exact(want, "35fff6263ebfbafc93b0fd6cfd0afa6820d8a48727f0035a031c93c62806029d", COORDINATOR_PIN["runtimeKeccak256"])
want = replace_exact(want, "len(m.Decoders) > 40", "len(m.Decoders) > 41")
want = replace_exact(want, "len(parts) > 40", "len(parts) > 41")
assert stage_text("tools/Go.txt") == want

# Generated Java-8 fixtures change only exact capacity labels/counts and their
# local output path; no original/JAR/class/resource input is named or opened.
want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, '"""Create only trusted generated Java-8 TreeMap SortedMap empty and retained controls.',
                     '"""Create only trusted generated Java-8 raw41 boundaries and retained controls.')
want = replace_exact(want, "java-diff-mc-tree-map-sorted-empty-fixtures-", "java-diff-mc-classcount41-byte298630-fixtures-")
want = replace_exact(want, "# Exact raw40 and aggregate-byte boundaries exercise this measured cap lift.",
                     "# Exact raw41 and aggregate-byte boundaries exercise this measured cap lift.")
want = replace_exact(want, "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41)",
                     "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42)")
want = replace_exact(want, 'count_fixture("count-40-295438", 40, 295438)', 'count_fixture("count-41-298630", 41, 298630)')
want = replace_exact(want, 'count_fixture("count-40-295439", 40, 295439)', 'count_fixture("count-41-298631", 41, 298631)')
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    want = replace_exact(parent_text(relative), "classes<=132", "classes<=133")
    assert stage_text(relative) == want, relative

# The gate's retained prefix/suffix are inherited exactly after declared stage
# paths/pins. The focused raw41/raw42 block is separately content-addressed.
old_gate = parent_text("tools/gate.py")
new_gate = stage_text("tools/gate.py")
old_start = old_gate.index("# Exact raw40 is the focused capacity witness")
old_end = old_gate.index("# Retained EnumSet", old_start)
new_start = new_gate.index("# Exact raw41 is the focused capacity witness")
new_end = new_gate.index("# Retained EnumSet", new_start)
want = old_gate[:old_start]
for old, new in (
    ('"""Generated-only TreeMap SortedMap empty and retained bounded-profile gate.', '"""Generated-only raw41/byte298630 capacity and retained TreeMap gate.'),
    ("java-diff-mc-tree-map-sorted-empty-build-", "java-diff-mc-classcount41-byte298630-build-"),
    ("java-diff-mc-tree-map-sorted-empty-fixtures-", "java-diff-mc-classcount41-byte298630-fixtures-"),
    ("java-diff-mc-tree-map-sorted-empty-gate-", "java-diff-mc-classcount41-byte298630-gate-"),
    ('pins["bootstrapCount"] == 92 and pins["rawLimits"] == [40, 295438]', 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [41, 298630]'),
    ('pins["diagnosticClassBound"] == 132 and pins["engine"]["bytes"] <= 393216', 'pins["diagnosticClassBound"] == 133 and pins["engine"]["bytes"] <= 393216'),
    ('head["totalClassBytes"] <= 295438', 'head["totalClassBytes"] <= 298630'),
):
    want = replace_exact(want, old, new)
assert new_gate[:new_start] == want
assert hashlib.sha256(new_gate[new_start:new_end].encode()).hexdigest() == CAPACITY_SHA256
want = old_gate[old_end:]
want = replace_exact(want, '"profile": "MC-TREEMAP-SORTED-P1"', '"profile": "MC-RAW41-BYTE298630-P1"')
want = replace_exact(want,
    '"limitations": "Only existing image85 TreeMap changes: a verified Java-8 abstract-bit strip declares retained image92 SortedMap and exposes concrete fresh isEmpty()==true. No Map put/get/size/clear/containsKey/order/comparator/view/mutation semantics are present; direct and typed put take the exact unsupported AbstractMethodError kind11 after the link, never a map result. Bootstrap count92, diagnostic132, raw40/295438, native13, dynamic runtime-derived ordered root, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory, world, or Done input or claim. Parent alone performs genuine replay."',
    '"limitations": "Only selected raw-class capacity changes from the accepted TreeMap SortedMap fresh-empty stage: raw40/295438/diagnostic132 to raw41/298630/diagnostic133. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, SimpleMessage, provider construction, factory, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay."')
assert new_gate[new_end:] == want

want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned generated TreeMap SortedMap empty evidence."""',
                     '"""Rebuild the pinned generated raw41/byte298630 evidence."""')
want = replace_exact(want, "java-diff-mc-tree-map-sorted-empty-build-", "java-diff-mc-classcount41-byte298630-build-")
assert stage_text("tools/build.py") == want

# Bootstrap material, source and hex images are all exact inherited bytes. The
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

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "2323d952f", "parentEvidence": "tree-map-sorted-empty-preflight", "phase": "built",
                      "domain": D, "runtimeBaseline": 391172, "rawLimits": [41, 298630],
                      "diagnosticClassBound": 133, "address": "0x" + ENGINE, "owner": "0x" + OWNER,
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
                  "diagnosticClassBound": 133, "runtimeBaseline": 391172,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
