#!/usr/bin/env python3
"""Verify the bounded TreeMap SortedMap-isEmpty delta from generated evidence only.

The sole semantic change is bootstrap image85: Java 8 compiles an abstract
TreeMap<K,V> implementing retained SortedMap<K,V>; this verifier strips only
ACC_ABSTRACT from that class-file header.  The resulting nonabstract guest image
has exactly <init>()V and concrete isEmpty()Z=true.  No original artifact, JAR,
class, resource, provider, world, or Minecraft input is opened or named.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "sorted-map-link-preflight"
OLD = "MC-SORTEDMAP-LINK-P1"
DOMAIN = "MC-TREEMAP-SORTED-P1"
OLD_ENGINE = "4d432d534f525445444d41502d4c494e4b2d5031"
ENGINE = "4d432d545245454d41502d534f525445442d5031"
OLD_OWNER = "4d432d534f525445444d41502d4c494e4b2d4f31"
OWNER = "4d432d545245454d41502d534f525445442d4f31"
TREE_SHA256 = "fea296c4b5c54dbd9b66c490cafe8cf30316158b44933afe61c97542cbcbc3f3"
TREE_KECCAK = "02089b8947a73c400cf727b9a5f06bb3c6c8806a36e8dc463cbea5e96641333b"
ENGINE_PIN = {
    "bytes": 391172,
    "initSHA256": "26eac221ead5783dba27f61a084c1cda9d8956ac48615bda512c976db6ba7ec1",
    "runtimeSHA256": "828583d9a6f751e9795bdb1afc773d7abbee820565e58a72738f85959a5f9080",
    "runtimeKeccak256": "61e095cb3845276f7aa58ecd4c9db2a16e588dce7236ca2c2e22c42d8d99046f",
}
COORDINATOR_PIN = {
    "bytes": 5394,
    "initSHA256": "4366fe30618b2f862bfab9dce5e29a251aa4988ce7efd556794470aa78519418",
    "runtimeSHA256": "13b33343d16c40c7f0cde640f3fe11b2e85bc0ef7d1bbdba15af3c227f1718f8",
    "runtimeKeccak256": "35fff6263ebfbafc93b0fd6cfd0afa6820d8a48727f0035a031c93c62806029d",
}


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:80], text.count(old), count)
    return text.replace(old, new)


def parent_text(rel):
    return (parent / rel).read_text()


def stage_text(rel):
    return (stage / rel).read_text()


def engine_expected(text, tree_hex):
    text = replace_exact(text, OLD, DOMAIN, 9)
    replacements = [
        ('''        // TreeMap remains at its accepted slot; WeakReference appends after all 86 images.
        h[85] = keccak256(_bootstrapTreeMap());''', '''        // TreeMap remains at slot85 with its measured SortedMap link and only
        // concrete fresh-empty isEmpty() surface; WeakReference remains slot86.
        h[85] = keccak256(_bootstrapTreeMap());'''),
        ('''    // TreeMap is an append-only constructor image. It deliberately has no
    // SortedMap/NavigableMap or mutation surface before a measured use.
    function _appendTreeMapBootstrap(ClassInfo[] memory classes, uint256 at) private pure {
''', '''    // TreeMap is the existing bounded image: it links SortedMap and exposes
    // only a concrete fresh-empty isEmpty() beside its no-arg constructor.
    // No Map mutation, ordering, comparator, or view surface is present.
    function _appendTreeMapBootstrap(ClassInfo[] memory classes, uint256 at) private pure {
'''),
        ('''        // TreeMap remains at slot85; the outlined helper preserves WeakReference
        // at86, Iterable at87, ThreadLocal at88, then appends Math at89.
''', '''        // TreeMap stays at slot85 with only its SortedMap type-link and empty
        // isEmpty; the outlined helper preserves WeakReference at86, Iterable
        // at87, ThreadLocal at88, then appends Math at89.
'''),
        ('''        // SortedMap appends after the immutable 91-image tail; TreeMap remains
        // a constructor-only Object subclass and does not implement it.
''', '''        // SortedMap remains image92. TreeMap's existing slot85 declares this
        // exact interface and concretely supplies only isEmpty().
'''),
        ('''    // Java 8 javac -source 8 -target 8 -g:none: public Object subclass with
    // exactly the public no-arg constructor. No Map/SortedMap interface or API.
    function _bootstrapTreeMap() private pure returns (bytes memory) { return hex"cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100116a6176612f7574696c2f547265654d61700100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"; }''', '''    // This Java-8-built image is nonabstract only after its verified class-file
    // ACC_ABSTRACT strip. It declares SortedMap and has exactly <init>()V plus
    // concrete isEmpty()Z=true; no Map mutation/order/view API is present.
    function _bootstrapTreeMap() private pure returns (bytes memory) { return hex"%s"; }''' % tree_hex),
    ]
    for old, new in replacements:
        text = replace_exact(text, old, new)
    return text


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, n):
        assert 0 <= n <= len(self.data) - self.pos
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out

    def u1(self): return self.take(1)[0]
    def u2(self): return int.from_bytes(self.take(2), "big")
    def u4(self): return int.from_bytes(self.take(4), "big")


def parse_class(data):
    r = Reader(data)
    assert r.take(4) == b"\xca\xfe\xba\xbe" and r.u2() == 0 and r.u2() == 52
    cp_count = r.u2()
    cp = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = r.u1()
        if tag == 1:
            cp[i] = (tag, r.take(r.u2()))
        elif tag in (3, 4):
            cp[i] = (tag, r.take(4))
        elif tag in (5, 6):
            cp[i] = (tag, r.take(8)); i += 1
        elif tag in (7, 8, 16):
            cp[i] = (tag, r.u2().to_bytes(2, "big"))
        elif tag in (9, 10, 11, 12, 18):
            cp[i] = (tag, r.take(4))
        elif tag == 15:
            cp[i] = (tag, r.take(3))
        else:
            raise AssertionError(("constant-pool tag", tag, i))
        i += 1

    def utf(index):
        assert 0 < index < cp_count and cp[index][0] == 1
        return cp[index][1].decode("ascii")

    def cls(index):
        assert 0 < index < cp_count and cp[index][0] == 7
        return utf(int.from_bytes(cp[index][1], "big"))

    flags_offset = r.pos
    flags, this_class, super_class = r.u2(), r.u2(), r.u2()
    interfaces = [r.u2() for _ in range(r.u2())]

    def attributes():
        out = []
        for _ in range(r.u2()):
            name = utf(r.u2())
            out.append((name, r.take(r.u4())))
        return out

    def member():
        access, name, descriptor = r.u2(), utf(r.u2()), utf(r.u2())
        return {"access": access, "name": name, "descriptor": descriptor,
                "attributes": attributes()}

    fields = [member() for _ in range(r.u2())]
    methods = [member() for _ in range(r.u2())]
    class_attributes = attributes()
    assert r.pos == len(data)
    return {"flagsOffset": flags_offset, "flags": flags, "this": cls(this_class),
            "super": cls(super_class), "interfaces": [cls(x) for x in interfaces],
            "fields": fields, "methods": methods, "attributes": class_attributes}


def code(member):
    values = [value for name, value in member["attributes"] if name == "Code"]
    assert len(values) == 1
    r = Reader(values[0])
    stack, locals_, n = r.u2(), r.u2(), r.u4()
    body = r.take(n)
    r.take(r.u2() * 8)
    for _ in range(r.u2()):
        r.take(2); r.take(r.u4())
    assert r.pos == len(values[0])
    return stack, locals_, body


source = stage_text("bootstrap/java/util/TreeMap.java")
assert source == """package java.util;
public abstract class TreeMap<K,V> implements SortedMap<K,V> {
  public TreeMap() {}
  public boolean isEmpty() { return true; }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="tree-map-sorted-empty-verify-", dir=root / "build") as temp:
    temp = Path(temp)
    src = temp / "java/util/TreeMap.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = temp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    compiled = (out / "java/util/TreeMap.class").read_bytes()
compiled_info = parse_class(compiled)
assert compiled_info["flags"] == 0x0421
assert compiled_info["this"] == "java/util/TreeMap"
assert compiled_info["super"] == "java/lang/Object"
assert compiled_info["interfaces"] == ["java/util/SortedMap"]
assert not compiled_info["fields"]
assert [(m["access"], m["name"], m["descriptor"]) for m in compiled_info["methods"]] == [
    (0x0001, "<init>", "()V"), (0x0001, "isEmpty", "()Z")]
assert code(compiled_info["methods"][0]) == (1, 1, bytes.fromhex("2ab70001b1"))
assert code(compiled_info["methods"][1]) == (1, 1, bytes.fromhex("04ac"))
image = bytearray(compiled)
struct.pack_into(">H", image, compiled_info["flagsOffset"], compiled_info["flags"] & ~0x0400)
assert sum(a != b for a, b in zip(compiled, image)) == 1
stripped = bytes(image)
info = parse_class(stripped)
assert info["flags"] == 0x0021 and info["this"] == compiled_info["this"]
assert info["super"] == compiled_info["super"] and info["interfaces"] == compiled_info["interfaces"]
assert info["fields"] == compiled_info["fields"] and info["methods"] == compiled_info["methods"]
assert hashlib.sha256(stripped).hexdigest() == TREE_SHA256 and len(stripped) == 315
assert stripped.hex() == stage_text("bootstrap/java/util/TreeMap.class.hex").strip()
for forbidden in (b"put", b"get", b"size", b"clear", b"containsKey", b"comparator", b"entrySet", b"NavigableMap"):
    assert forbidden not in stripped, forbidden

for rel in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    assert stage_text(rel) == engine_expected(parent_text(rel), stripped.hex()), rel

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = replace_exact(coordinator, OLD, DOMAIN, 4)
coordinator = replace_exact(coordinator, OLD_ENGINE, ENGINE)
coordinator = replace_exact(coordinator, "e182203ef090da0dcc30998cced1cbc4c8216cdee52a35350d36ed8cc91cfb5e", ENGINE_PIN["runtimeKeccak256"])
assert stage_text("coordinator/MCEntryCoordinator.sol") == coordinator

transport = parent_text("tools/Go.txt")
transport = replace_exact(transport, OLD, DOMAIN, 6)
for old, new, count in (
    ("5561a5e26e51bee5afd67d6f665dc769cc0639c9ae297273e3df1a8a58f26ebc", ENGINE_PIN["runtimeSHA256"], 1),
    ("e182203ef090da0dcc30998cced1cbc4c8216cdee52a35350d36ed8cc91cfb5e", ENGINE_PIN["runtimeKeccak256"], 1),
    ("4d0c2bc3b7f5f139b2a26befc9fc1c248f8ea88af29ec5cbd056cc14589b7bc0", COORDINATOR_PIN["runtimeKeccak256"], 1),
    (OLD_ENGINE, ENGINE, 1), (OLD_OWNER, OWNER, 1), ("390931", "391172", 2),
):
    transport = replace_exact(transport, old, new, count)
assert stage_text("tools/Go.txt") == transport

expected_build = parent_text("tools/build.py")
expected_build = replace_exact(expected_build, "SortedMap link", "TreeMap SortedMap empty")
expected_build = replace_exact(expected_build, "sorted-map-link", "tree-map-sorted-empty")
assert stage_text("tools/build.py") == expected_build

fixtures = parent_text("tools/generate_fixtures.py")
fixtures = replace_exact(fixtures, "SortedMap link", "TreeMap SortedMap empty")
fixtures = replace_exact(fixtures, "java-diff-mc-sorted-map-link-fixtures-", "java-diff-mc-tree-map-sorted-empty-fixtures-")
fixtures = replace_exact(fixtures, '''# TreeMap is deliberately an Object-only constructor image. This positive probe
# proves real guest allocation, non-null results, and stable object identity; it
# does not call Map, SortedMap, ordering, or mutation APIs.
''', '''# TreeMap has the measured SortedMap type-link but this retained positive probe
# remains limited to real guest allocation, non-null results, and stable identity.
# It does not call any Map, ordering, comparator, view, or mutation API.
''')
fixtures = replace_exact(fixtures, '''}, ["TreeMapConstructorMain.class"], "TreeMapConstructorMain")

# This root has no TreeMap symbol use; the appended image must not initialize.
''', '''}, ["TreeMapConstructorMain.class"], "TreeMapConstructorMain")

# The exact new bounded surface is a fresh TreeMap assigned to SortedMap and
# invoked only through SortedMap.isEmpty(). Both independent fresh instances must
# report true. It deliberately uses no other Map/SortedMap method or ordering API.
build("treemap-sorted-empty", {
    "TreeMapSortedEmptyMain.java": """import java.util.SortedMap;
import java.util.TreeMap;
public final class TreeMapSortedEmptyMain {
  static SortedMap stable;
  static int result;
  public static void main(String[] ignored) {
    SortedMap first = new TreeMap();
    SortedMap second = new TreeMap();
    if (!first.isEmpty() || !second.isEmpty() || first == second) throw new Error();
    stable = first;
    if (!stable.isEmpty() || stable != first) throw new Error();
    result = 7;
  }
}
""",
}, ["TreeMapSortedEmptyMain.class"], "TreeMapSortedEmptyMain")

# This root has no TreeMap symbol use; the appended image must not initialize.
''')
fixtures = replace_exact(fixtures, '''# This historical interface-call form names SortedMap and invokes its inherited
# Map.put slot after ordinary TreeMap construction. SortedMap is now linkable, but
# TreeMap still implements neither Map nor SortedMap, so the exact unsupported
# receiver refusal must remain atomic rather than fabricate a map mutation.
''', '''# This historical interface-call form names SortedMap and invokes its inherited
# Map.put slot after ordinary TreeMap construction. TreeMap now passes the exact
# SortedMap receiver type-link, but it declares no put method, so lookup must
# terminate with the exact unsupported AbstractMethodError outcome, never a mutation.
''')
assert stage_text("tools/generate_fixtures.py") == fixtures

gate = parent_text("tools/gate.py")
gate = replace_exact(gate, "SortedMap link", "TreeMap SortedMap empty")
for old, new in (
    ("java-diff-mc-sorted-map-link-build-", "java-diff-mc-tree-map-sorted-empty-build-"),
    ("java-diff-mc-sorted-map-link-fixtures-", "java-diff-mc-tree-map-sorted-empty-fixtures-"),
    ("java-diff-mc-sorted-map-link-gate-", "java-diff-mc-tree-map-sorted-empty-gate-"),
):
    gate = replace_exact(gate, old, new)
gate = replace_exact(gate, '''# TreeMap is an ordinary guest Object subclass with a public no-arg constructor.
# The generated Java program checks two distinct non-null allocations and a
# stable alias, without using any ordering or map operation.
''', '''# TreeMap retains its ordinary guest construction and identity properties. This
# retained probe uses no Map mutation, ordering, comparator, view, or extra API.
''')
gate = replace_exact(gate, '''a = retained("treemap", "treemap", treemap_initialized)
assert a is None

# A no-use root leaves the appended constructor-only image uninitialized.
''', '''a = retained("treemap", "treemap", treemap_initialized)
assert a is None

# The focused positive is the sole new semantic surface: a fresh TreeMap passes
# the SortedMap receiver type-link and its concrete isEmpty() returns true.
# q1/q7/direct/reopen must preserve its terminal machine and opaque payload.
def treemap_sorted_empty_initialized(decoded):
    raw = fixture("treemap-sorted-empty")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 85]["state"] == 2
q_equivalent("treemap-sorted-empty", "treemap-sorted-empty", treemap_sorted_empty_initialized)

# A no-use root leaves the bounded TreeMap image uninitialized.
''')
gate = replace_exact(gate, '''# TreeMap is not a Map or SortedMap implementation. Both generated controls run
# a real TreeMap constructor first, then must stop through an EVM refusal; no
# fabricated mutation result, interface assignment, or Java terminal is allowed.
def omitted_refusal(label, expected_selector, expected_words=None, expected_missing=None):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == expected_selector and refusal["rootUnchanged"], refusal
    if expected_words is not None:
        assert words(refusal) == expected_words, refusal
    if expected_missing is not None:
        assert refusal["diagnostic"]["name"] == expected_missing, refusal
    rows[label] = refusal

# The virtual put member is absent from the constructor-only image: CallError
# code3 at the source invocation PC13 is retained as an EVM refusal, not a Map
# result or a synthetic Java exception.
omitted_refusal("treemap-mutation-omitted", "0xd631c3a4", ["3", "13"])
# SortedMap now resolves its inherited Map.put declaration, but constructor-only
# TreeMap implements neither interface. The exact receiver refusal is pinned after
# a real constructor; it is neither a missing class nor a fabricated mutation.
omitted_refusal("treemap-sortedmap-omitted", "0xfe0674d5", ["2", "13"])
''', '''# TreeMap deliberately declares no put. Once its exact SortedMap edge is linked,
# Java virtual/interface resolution reaches retained abstract Map.put and produces
# the existing catchable AbstractMethodError kind11. This is the measured honest
# unsupported mutation outcome: neither call returns a map value or creates a
# fake mutation, and no EVM method implementation is added.
def omitted_abstract_method(label):
    world = out / ("world-" + label)
    run(label + "-unsupported", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    started = failure(world, "start.json")
    terminal = started["slice"]
    assert terminal["lifecycle"] == terminal["outcome"] == 3
    assert terminal["javaKind"] == 11 and terminal["javaRef"] == 8
    assert terminal["totalJvmSteps"] == 12 and terminal["totalInternalSteps"] == 3
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 3
    assert head["javaKind"] == 11 and head["javaRef"] == 8
    assert head["jvmSteps"] == 12 and head["internalSteps"] == 3
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == fixture(label)["bindingCount"] + 92
    assert decoded["javaKind"] == 11 and decoded["javaRef"] == 8
    run(label + "-reopen", [driver, "verify", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    rows[label] = {"unsupportedJavaKind": head["javaKind"],
                   "unsupportedJavaRef": head["javaRef"],
                   "jvmSteps": head["jvmSteps"], "internalSteps": head["internalSteps"],
                   "checkpointSHA256": head["checkpointSHA256"]}
omitted_abstract_method("treemap-mutation-omitted")
omitted_abstract_method("treemap-sortedmap-omitted")
''')
gate = replace_exact(gate, '''summary = {"profile": "MC-SORTEDMAP-LINK-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only the bootstrap link tail changes from 91 to 92 images and the read-only diagnostic class bound from131 to132. SortedMap is a generated empty interface extending the retained Map image; raw40/295438, native13, dynamic runtime-derived ordered root, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory, world, or Done input or claim. Parent alone performs genuine replay."}
''', '''summary = {"profile": "MC-TREEMAP-SORTED-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only existing image85 TreeMap changes: a verified Java-8 abstract-bit strip declares retained image92 SortedMap and exposes concrete fresh isEmpty()==true. No Map put/get/size/clear/containsKey/order/comparator/view/mutation semantics are present; direct and typed put take the exact unsupported AbstractMethodError kind11 after the link, never a map result. Bootstrap count92, diagnostic132, raw40/295438, native13, dynamic runtime-derived ordered root, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory, world, or Done input or claim. Parent alone performs genuine replay."}
''')
assert stage_text("tools/gate.py") == gate

for rel in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py", "tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert stage_text(rel) == parent_text(rel), rel

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "09d3a4d9e", "parentEvidence": "sorted-map-link-preflight", "phase": "built",
                      "domain": DOMAIN, "runtimeBaseline": 390931, "address": "0x" + ENGINE,
                      "owner": "0x" + OWNER, "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN})
expected_pins["bootstrapSHA256"]["TreeMap"] = TREE_SHA256
assert pins == expected_pins
assert pins["bootstrapCount"] == 92 and pins["diagnosticClassBound"] == 132
assert pins["rawLimits"] == [40, 295438] and pins["globalNativeBindings"] == 13
assert pins["runtimeBaseline"] == 390931 and pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216

record = json.loads(stage_text("root-commitment.json"))
parent_record = json.loads(parent_text("root-commitment.json"))
assert record["order"] == parent_record["order"] and len(record["order"]) == 92
assert record["keccak256"] == parent_record["keccak256"][:85] + [TREE_KECCAK] + parent_record["keccak256"][86:]
node = root / "jvmevm/runtime/node_modules"
env = {**os.environ, "NODE_PATH": str(node)}
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1"], cwd=root, env=env, text=True))
assert record == {**parent_record, "domain": DOMAIN, "dboot": actual["d"], "bootstrapRoot": actual["r"],
                  "keccak256": record["keccak256"]}

assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "domain": DOMAIN, "bootstrapImages": 92,
                  "changedImage": {"name": "TreeMap", "bytes": len(stripped), "sha256": TREE_SHA256,
                                   "keccak256": TREE_KECCAK, "abstractBitStripped": True},
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 132, "runtimeBaseline": 390931,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
