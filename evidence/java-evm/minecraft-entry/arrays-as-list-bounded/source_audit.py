#!/usr/bin/env python3
"""Source-only, pinned-prefix and program-slot audit for this candidate."""
import hashlib, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent
BASE = ROOT.parent / "arrays-as-list-source-base-p55"
source = (ROOT / "engine/MCEntryInterpreter.sol").read_text()
base_source = (BASE / "engine/MCEntryInterpreter.sol").read_text()
for rel in ("engine/MCEntryInterpreter.json", "coordinator/MCEntryCoordinator.json"):
    current = json.loads((ROOT/rel).read_text())
    base = json.loads((BASE/rel).read_text())
    assert current["abi"] == base["abi"], f"ABI changed: {rel}"
    assert current["storageLayout"] == base["storageLayout"], f"storage layout changed: {rel}"
manifest = json.loads((BASE / "source-manifest.json").read_text())
for rel, pin in manifest["files"].items():
    b=(BASE/rel).read_bytes()
    assert len(b)==pin["bytes"] and hashlib.sha256(b).hexdigest()==pin["sha256"], rel
assert manifest["worktreeBase"] == "41b88053bc7c3d55e33c0679e981bb27ab9821e7"
assert manifest["acceptedGuestCodeCommit"] == "a056cbcd113c800f0d34159617d27b2eef55c8a4"
# All six pre-existing hierarchy source files are byte-identical.
for rel in ("bootstrap/java/util/Collection.java", "bootstrap/java/util/AbstractCollection.java",
            "bootstrap/java/util/AbstractList.java", "bootstrap/java/util/Iterator.java",
            "bootstrap/java/util/List.java", "bootstrap/java/util/RandomAccess.java"):
    assert (ROOT/rel).read_bytes()==(BASE/rel).read_bytes(), rel
# Every pre-existing bootstrap provider remains byte-identical; only profile domain
# constants, root count, append placement and the three new providers are changed.
def providers(s):
    bodies=re.findall(r'(function _bootstrap\w+\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \})',s)
    return {re.match(r'function (_bootstrap\w+)',body).group(1):body for body in bodies}
old,new=providers(base_source),providers(source)
for name,body in old.items():
    assert new.get(name)==body, f"existing bootstrap image changed: {name}"
assert "new bytes32[](123)" in source
# Preserve the entire old ordered 120-leaf commitment program byte-for-byte.
def root_rows(s):
    body=s[s.index("    function _bootstrapRoot("):]
    body=body[:body.index("\n    function ",1)]
    return {int(i):rhs.strip() for i,rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);",body)}
old_rows,new_rows=root_rows(base_source),root_rows(source)
assert all(old_rows[i]==new_rows[i] for i in range(120)), "old bootstrap commitment order changed"
assert set(new_rows)==set(range(123))
# Existing 13-field canonical config encoder and limits are preserved exactly.
def section(s,start,end): return s[s.index(start):s.index(end,s.index(start))]
assert section(source,"    struct ConfigRootEncoding {","    }") == section(base_source,"    struct ConfigRootEncoding {","    }")
assert section(source,"    function _configRoot(","    function _bootstrapRoot(") == section(base_source,"    function _configRoot(","    function _bootstrapRoot(")
for constant in ("MAX_RAW_CLASSES = 150", "MAX_RAW_BYTES = 1063930", "MAX_ARRAYS = 8192",
                 "MAX_ARRAY_LENGTH = 65536", "MAX_ARRAY_ELEMENTS = 262144", "MAX_OBJECTS = 4096",
                 "MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS", "MAX_FRAMES = 128"):
    assert constant in source, constant
# Actual slot assembly: old 105..115 unchanged; P55 terminal leaves relocated exactly
# three slots; new Arrays images occupy 120..122. These are generated class placements,
# not an arithmetic-only class-count argument.
for slot, provider in ((110,"_bootstrapHashMapEntrySet"),(111,"_bootstrapHashMapEntryIterator"),
                       (112,"_bootstrapConcurrentModificationException"),(113,"_bootstrapLinkedHashMap"),
                       (114,"_bootstrapListIterator"),(115,"_bootstrapArrayListItr")):
    assert f"p.classes[classSlot + {slot-39}].data = {provider}();" in source, (slot,provider)
for delta, provider in ((18,"_bootstrapFunction"),(17,"_bootstrapNavigableMap"),(16,"_bootstrapComparator"),
                        (15,"_bootstrapSortedSet"),(14,"_bootstrapNavigableSet"),(7,"_bootstrapReflectArray"),
                        (6,"_bootstrapCollections"),(5,"_bootstrapSingletonList"),(4,"_bootstrapSingletonIterator"),
                        (3,"_bootstrapArrays"),(2,"_bootstrapArraysArrayList"),(1,"_bootstrapArraysArrayIterator")):
    assert f"p.classes[count - {delta}] = _parseBundleClass({provider}());" in source
for i, name in ((120,"Arrays"),(121,"Arrays$ArrayList"),(122,"Arrays$ArrayIterator")):
    p=ROOT/f"build/classes-v3/java/util/{name}.class"
    data=p.read_bytes()
    assert data[:4]==bytes.fromhex("cafebabe") and int.from_bytes(data[6:8],"big")==52
    fn={"Arrays":"_bootstrapArrays","Arrays$ArrayList":"_bootstrapArraysArrayList","Arrays$ArrayIterator":"_bootstrapArraysArrayIterator"}[name]
    embedded=re.search(rf"function {fn}\(\) private pure returns \(bytes memory\) \{{ return hex\"([0-9a-f]+)\"; \}}",source).group(1)
    assert bytes.fromhex(embedded)==data
# Required erasure and explicit native refusal guards.
assert "public static <T> List asList(T... array)" in (ROOT/"bootstrap/java/util/Arrays.java").read_text()
assert "public native boolean add(Object value);" in (ROOT/"bootstrap/java/util/Arrays.java").read_text()
assert "public native void remove();" in (ROOT/"bootstrap/java/util/Arrays$ArrayIterator.java").read_text()
assert "Arrays$1" not in source and "Arrays$1" not in " ".join(p.name for p in (ROOT/"build/classes-v3/java/util").glob("*.class"))
# Program class vector boundary at the measured maximum is 150 raw + 123 bootstrap;
# helper iterator is actual class index 272 in that assembly.
assert 150+123==273 and 150+122==272
print(json.dumps({"sourceBaseFiles":len(manifest["files"]),"oldJavaSourceExact":6,"oldBootstrapProvidersExact":len(old),
                  "bootstrapCount":123,"rawMaximum":150,"assembledClassCountAtRawMaximum":273,
                  "newBootstrapSlots":{"Arrays":120,"Arrays$ArrayList":121,"Arrays$ArrayIterator":122},
                  "maximumRawHelperClassIndex":272,"canonicalConfigEncoding":"byte-identical"},indent=2))
