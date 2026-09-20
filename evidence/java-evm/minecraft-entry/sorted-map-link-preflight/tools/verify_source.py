#!/usr/bin/env python3
"""Pin the bounded generated SortedMap link to raw40 source evidence only.

The sole semantic delta is image92: an empty Java-8 SortedMap<K,V> extending
Map<K,V>. No original artifact/JAR/class/resource/world is read or named.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount40-byte295438-preflight"
OLD = "MC-RAW40-BYTE295438-P1"
DOMAIN = "MC-SORTEDMAP-LINK-P1"
OLD_ENGINE = "4d432d52415734302d4259544532393534333845"
ENGINE = "4d432d534f525445444d41502d4c494e4b2d5031"
OLD_OWNER = "4d432d52415734302d425954453239353433384f"
OWNER = "4d432d534f525445444d41502d4c494e4b2d4f31"
ENGINE_PIN = {
    "bytes": 390931,
    "initSHA256": "438bec6e55819bf4d61fb3b1d69dc684904ea7175783c18d6b38c7789f0dbc93",
    "runtimeSHA256": "5561a5e26e51bee5afd67d6f665dc769cc0639c9ae297273e3df1a8a58f26ebc",
    "runtimeKeccak256": "e182203ef090da0dcc30998cced1cbc4c8216cdee52a35350d36ed8cc91cfb5e",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "50b9e8d4d4dc6edf04c647c14311ac8c31324dcdb143285410c4ec2ad32a5afc",
    "runtimeSHA256": "d1d890771affcd29d872b8de677f54c8ccc598a665431efbac56fb70d440793b",
    "runtimeKeccak256": "4d0c2bc3b7f5f139b2a26befc9fc1c248f8ea88af29ec5cbd056cc14589b7bc0",
}
SORTED_SHA256 = "c59e7d5cb3219d4fe2844d720a5f74158c8760d58f34ab3d8bb8d81ba8bb9b06"
SORTED_KECCAK = "9f2e90ef68a7cfdb4342f9a357586b495708fab72835cc091a2ff8b506a5ff70"
DBOOT = "86fc42072b13ced7553db7a1096420a230bb63a322fa406c0bbeaa6d0add6940"
ROOT = "d7dd6b101c64ad66314e7d36dc5e36ea20e60369d31dd89a3edce39a9c04a308"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)


def parent_text(rel):
    return (parent / rel).read_text()


def stage_text(rel):
    return (stage / rel).read_text()


def engine_expected(text, sorted_hex):
    text = replace_exact(text, OLD, DOMAIN, 9)
    text = replace_exact(text, "new bytes32[](91)", "new bytes32[](92)")
    text = replace_exact(text, '''        // StackTraceElement appends as the canonical leaf of Thread's empty array.
        h[90] = DBOOT_STACK_TRACE_ELEMENT;
        return keccak256(abi.encode(DBOOT, h));''', '''        // StackTraceElement remains the canonical leaf of Thread's empty array.
        h[90] = DBOOT_STACK_TRACE_ELEMENT;
        // SortedMap is the bounded final append: a link-only interface edge to Map.
        h[91] = keccak256(_bootstrapSortedMap());
        return keccak256(abi.encode(DBOOT, h));''')
    text = replace_exact(text, "uint256 count = inputCount + 85 + (suppliedObject ? 0 : 1)",
                         "uint256 count = inputCount + 86 + (suppliedObject ? 0 : 1)")
    text = replace_exact(text, '''        p.classes[classSlot + 50].data = _bootstrapMath();
        p.classes[classSlot + 51].data = _bootstrapStackTraceElement();
    }''', '''        p.classes[classSlot + 50].data = _bootstrapMath();
        p.classes[classSlot + 51].data = _bootstrapStackTraceElement();
        // SortedMap appends after the immutable 91-image tail; TreeMap remains
        // a constructor-only Object subclass and does not implement it.
        p.classes[classSlot + 52].data = _bootstrapSortedMap();
    }''')
    text = replace_exact(text, '''            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"))
            || _isNamedClass(c, bytes("java/util/TreeMap"));''', '''            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"))
            || _isNamedClass(c, bytes("java/util/TreeMap"))
            || _isNamedClass(c, bytes("java/util/SortedMap"));''')
    marker = re.search(r'    function _bootstrapTreeMap\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}\n', text)
    assert marker and text.count("_bootstrapSortedMap") == 2
    text = text[:marker.end()] + '    function _bootstrapSortedMap() private pure returns (bytes memory) { return hex"' + sorted_hex + '"; }\n' + text[marker.end():]
    assert text.count("_bootstrapSortedMap") == 3
    return text


javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
source = stage_text("bootstrap/java/util/SortedMap.java")
assert source == """package java.util;
public interface SortedMap<K,V> extends Map<K,V> {}
"""
with tempfile.TemporaryDirectory(prefix="sorted-map-link-verify-", dir=root / "build") as temp:
    temp = Path(temp)
    src = temp / "java/util/SortedMap.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = temp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/util/SortedMap.class").read_bytes()
assert len(image) == 198 and hashlib.sha256(image).hexdigest() == SORTED_SHA256
assert image.hex() == stage_text("bootstrap/java/util/SortedMap.class.hex").strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"java/util/SortedMap", b"java/util/Map", b"Signature"):
    assert required in image, required
for forbidden in (b"put", b"get", b"firstKey", b"lastKey", b"comparator", b"entrySet", b"NavigableMap"):
    assert forbidden not in image, forbidden

for rel in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    assert stage_text(rel) == engine_expected(parent_text(rel), image.hex()), rel

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = replace_exact(coordinator, OLD, DOMAIN, 4)
coordinator = replace_exact(coordinator, OLD_ENGINE, ENGINE)
coordinator = replace_exact(coordinator, "f7a15c5035c21493cf7e274f36853cd776194db69c3a460e484bd5eab91dbb83", ENGINE_PIN["runtimeKeccak256"])
assert stage_text("coordinator/MCEntryCoordinator.sol") == coordinator

transport = parent_text("tools/Go.txt")
transport = replace_exact(transport, OLD, DOMAIN, 6)
for old, new in (("09a01488a2c16d08c97a630e350aeb871afe373f76d0a3ab13cff1194a2d8e54", ENGINE_PIN["runtimeSHA256"]),
                 ("0xf7a15c5035c21493cf7e274f36853cd776194db69c3a460e484bd5eab91dbb83", "0x" + ENGINE_PIN["runtimeKeccak256"]),
                 ("0x9644f4cfefacecf765ed180fde65057a18c71d0d2909d737dfb387082b78ccd8", "0x" + COORDINATOR_PIN["runtimeKeccak256"]),
                 (OLD_ENGINE, ENGINE), (OLD_OWNER, OWNER),
                 ("len(engineRun) != 389150", "len(engineRun) != 390931"),
                 ("len(run) != 389150", "len(run) != 390931")):
    transport = replace_exact(transport, old, new)
assert "MC-SORTEDMAP-LINK-P1-BOUNDED-1" in transport
assert stage_text("tools/Go.txt") == transport

for rel in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    assert stage_text(rel) == replace_exact(parent_text(rel), "classes<=131", "classes<=132"), rel

expected_build = parent_text("tools/build.py")
expected_build = replace_exact(expected_build, "raw40/byte295438", "SortedMap link")
expected_build = replace_exact(expected_build, "classcount40-byte295438", "sorted-map-link")
assert stage_text("tools/build.py") == expected_build

fixtures = parent_text("tools/generate_fixtures.py")
fixtures = replace_exact(fixtures, "Create only trusted generated Java-8 raw40 boundaries and retained controls.", "Create only trusted generated Java-8 SortedMap link and retained controls.")
fixtures = replace_exact(fixtures, "classcount40-byte295438", "sorted-map-link")
fixtures = replace_exact(fixtures, "bootstrap_count=91", "bootstrap_count=92")
# This raw Object fixture supplies image0, so its conditional bootstrap count
# also advances by one with the new append tail.
fixtures = replace_exact(fixtures, "bootstrap_count=90", "bootstrap_count=91")
fixtures = replace_exact(fixtures, '"bootstrapCount": 91', '"bootstrapCount": 92')
fixtures = replace_exact(fixtures, '''# This separately names the absent SortedMap interface and invokes its mutation
# slot after ordinary TreeMap construction. It must report the missing interface,
# not claim TreeMap implements it.
''', '''# This historical interface-call form names SortedMap and invokes its inherited
# Map.put slot after ordinary TreeMap construction. SortedMap is now linkable, but
# TreeMap still implements neither Map nor SortedMap, so the exact unsupported
# receiver refusal must remain atomic rather than fabricate a map mutation.
''')
fixtures = replace_exact(fixtures, '''}, ["TreeMapSortedMapOmittedMain.class"])

build("system-uninitialized", {''', '''}, ["TreeMapSortedMapOmittedMain.class"])

# SortedMap is a bootstrap-owned empty Java-8 interface extending Map. This is
# link-only: checkcast on null resolves its exact interface edge without active
# initialization, construction, mutation, ordering, views, or comparators.
build("sortedmap-link-null", {
    "SortedMapLinkNullMain.java": """import java.util.SortedMap;
public final class SortedMapLinkNullMain {
  static SortedMap saved;
  static int result;
  public static void main(String[] ignored) {
    SortedMap local = (SortedMap) null;
    if (local != null) throw new Error();
    saved = local;
    if (saved != null) throw new Error();
    result = 7;
  }
}
""",
}, ["SortedMapLinkNullMain.class"], "SortedMapLinkNullMain")

# Bootstrap ownership rejects replacement before any link or guest execution.
build("raw-sortedmap", {
    "RawSortedMapReplacementMain.java": "public final class RawSortedMapReplacementMain { public static void main(String[] ignored) {} }\\n",
    "java/util/SortedMap.java": "package java.util; public interface SortedMap<K,V> extends Map<K,V> {}\\n",
}, ["RawSortedMapReplacementMain.class", "java/util/SortedMap.class"])

build("system-uninitialized", {''')
assert stage_text("tools/generate_fixtures.py") == fixtures

gate = parent_text("tools/gate.py")
gate = replace_exact(gate, "Generated-only raw40/byte295438 capacity and retained dynamic-Throwable gate.", "Generated-only SortedMap link and retained bounded-profile gate.")
gate = replace_exact(gate, "classcount40-byte295438", "sorted-map-link", 3)
gate = replace_exact(gate, 'pins["bootstrapCount"] == 91 and pins["rawLimits"] == [40, 295438]', 'pins["bootstrapCount"] == 92 and pins["rawLimits"] == [40, 295438]')
gate = replace_exact(gate, 'pins["diagnosticClassBound"] == 131', 'pins["diagnosticClassBound"] == 132')
gate = replace_exact(gate, "bootstrap_count=91", "bootstrap_count=92")
gate = replace_exact(gate, "raw_count + 91", "raw_count + 92")
gate = replace_exact(gate, 'decoded["classCount"] - 91', 'decoded["classCount"] - 92', 2)
gate = replace_exact(gate, 'assert pins["bootstrapSHA256"]["Math"] == "e51d3e61920e9f33267ac3cb4dc2c70289d1c5fd43eb0bf6efdbbb1721c21356"\n', 'assert pins["bootstrapSHA256"]["Math"] == "e51d3e61920e9f33267ac3cb4dc2c70289d1c5fd43eb0bf6efdbbb1721c21356"\nassert pins["bootstrapSHA256"]["SortedMap"] == "' + SORTED_SHA256 + '"\n')
gate = replace_exact(gate, '''# The interface-call form resolves its explicit SortedMap owner and reports a
# canonical missing-class diagnostic rather than silently accepting assignment.
omitted_refusal("treemap-sortedmap-omitted", "0x555db429", expected_missing="java/util/SortedMap")
''', '''# SortedMap now resolves its inherited Map.put declaration, but constructor-only
# TreeMap implements neither interface. The exact receiver refusal is pinned after
# a real constructor; it is neither a missing class nor a fabricated mutation.
omitted_refusal("treemap-sortedmap-omitted", "0xfe0674d5", ["2", "13"])

# The only new positive surface is class linkage. A null checkcast resolves the
# empty SortedMap->Map edge while leaving the interface uninitialized; q1/q7/
# direct/reopen must retain the same complete checkpoint payload.
def sortedmap_link_uninitialized(decoded):
    raw = fixture("sortedmap-link-null")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert raw + 91 not in states
q_equivalent("sortedmap-link-null", "sortedmap-link-null", sortedmap_link_uninitialized)

# A raw class cannot replace the owned link-only interface.
world = out / "world-raw-sortedmap"
run("raw-sortedmap-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-sortedmap.zip", "4096"], "raw-sortedmap")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-sortedmap"] = refusal
''')
gate = replace_exact(gate, '"profile": "MC-RAW40-BYTE295438-P1"', '"profile": "MC-SORTEDMAP-LINK-P1"')
gate = replace_exact(gate, "Only selected raw-class capacity changes from raw39/294891/diagnostic130 to raw40/295438/diagnostic131. All 91 ordered bootstrap images and bytes, including dynamic image5 Throwable and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, ReusableMessage, provider construction, factory, world, or Done input or claim. Parent alone appends the genuine class and performs accelerated replay.", "Only the bootstrap link tail changes from 91 to 92 images and the read-only diagnostic class bound from131 to132. SortedMap is a generated empty interface extending the retained Map image; raw40/295438, native13, dynamic runtime-derived ordered root, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory, world, or Done input or claim. Parent alone performs genuine replay.")
assert stage_text("tools/gate.py") == gate

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
assert pins["basis"] == "4e2489003" and pins["parentEvidence"] == "classcount40-byte295438-preflight"
assert pins["domain"] == DOMAIN and pins["runtimeBaseline"] == 389150 and pins["runtimeCap"] == 393216
assert pins["bootstrapCount"] == 92 and pins["bootstrapSHA256"] == {**parent_pins["bootstrapSHA256"], "SortedMap": SORTED_SHA256}
assert pins["globalNativeBindings"] == 13 and pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14
assert pins["maxFrames"] == 128 and pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000
assert pins["rawLimits"] == [40, 295438] and pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768
assert pins["diagnosticClassBound"] == 132 and pins["address"] == "0x" + ENGINE and pins["owner"] == "0x" + OWNER
assert pins["limitsCommitment"] == parent_pins["limitsCommitment"] and pins["compiler"] == parent_pins["compiler"]
assert pins["engine"] == ENGINE_PIN and pins["coordinator"] == COORDINATOR_PIN

record = json.loads(stage_text("root-commitment.json"))
parent_record = json.loads(parent_text("root-commitment.json"))
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 92 and record["dboot"] == DBOOT and record["bootstrapRoot"] == ROOT
assert record["order"] == parent_record["order"] + ["SortedMap"]
assert record["keccak256"] == parent_record["keccak256"] + [SORTED_KECCAK]
node = root / "jvmevm/runtime/node_modules"
env = {**os.environ, "NODE_PATH": str(node)}
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1"], cwd=root, env=env, text=True))
assert actual == {"d": DBOOT, "r": ROOT}

assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "domain": DOMAIN, "bootstrapImages": 92,
                  "bootstrapRoot": ROOT, "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 132, "runtimeBaseline": 389150,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
