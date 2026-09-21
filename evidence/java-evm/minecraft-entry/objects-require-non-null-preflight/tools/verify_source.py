#!/usr/bin/env python3
'''Verify the exact generated-only image93 Objects.requireNonNull delta.

This verifier accepts no original artifact/JAR/class/resource/world input.  It
rebuilds the one checked-in Java-8 source image and mechanically derives both
interpreter layouts from raw48 generated evidence.
'''
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "classcount48-byte314425-preflight"
OLD = "MC-RAW48-BYTE314425-P1"
DOMAIN = "MC-OBJECTS-REQUIRE-NON-NULL-P1"
OLD_ENGINE = "4d432d52415734382d4259544533313434323545"
ENGINE = "4d432d4f424a454354532d5245514e4e2d393350"
OLD_OWNER = "4d432d52415734382d425954453331343432354f"
OWNER = "4d432d4f424a454354532d5245514e4e2d39334f"
OBJECTS_SHA256 = "fc87c7bfe18107225d3682238f8c1a07d0e66d737f1d26f95edc7d7f9a7698df"
OBJECTS_KECCAK = "4d1dd5f4b93cc63aab9df47a0c83c68d969867162c49ac106292c5832a8638a3"
ENGINE_PIN = {"bytes": 390985, "initSHA256": "937766226d0782aa441ac91f376858bce9cfe13720a5ad98ab0079fcd6e3507e", "runtimeSHA256": "6f3f9dd1ae1dbac37fb20423b64f3ce83ef406d0cefbe1c069eba7b5dc4d9b4d", "runtimeKeccak256": "1767996b5436be6c2b763dec84ddbfd9b63e4b40a0252c41adf598c26d7ab864"}
COORDINATOR_PIN = {"bytes": 5394, "initSHA256": "c3c345930f3affe5d16b721369d7b16ddfbc635699e03a947b5aac33865b13ea", "runtimeSHA256": "c93ac3add92bae58896ab3167d7bf2e2581fb052040f4b17d5108f64d8c3b49f", "runtimeKeccak256": "a836de09bb8adfa4aff13c83ade6e38672a93d7f27003f3fbea594ea5a4b8c0a"}


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:100], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative): return (parent / relative).read_text()
def stage_text(relative): return (stage / relative).read_text()

OBJECT_SOURCE = '''package java.util;

public final class Objects {
    private Objects() {}

    public static <T> T requireNonNull(T value, String message) {
        if (value == null) throw new NullPointerException();
        return value;
    }
}
'''
assert stage_text("bootstrap/java/util/Objects.java") == OBJECT_SOURCE
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="objects-require-non-null-verify-", dir=root / "build") as temp:
    temp = Path(temp); src = temp / "java/util/Objects.java"; src.parent.mkdir(parents=True)
    src.write_text(OBJECT_SOURCE); out = temp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/util/Objects.class").read_bytes()
assert len(image) == 385 and hashlib.sha256(image).hexdigest() == OBJECTS_SHA256
assert image.hex() == stage_text("bootstrap/java/util/Objects.class.hex").strip()
assert image[:8] == bytes.fromhex("cafebabe00000034")
for required in (b"java/util/Objects", b"requireNonNull", b"(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;", b"java/lang/NullPointerException", b"Signature"):
    assert required in image, required
for forbidden in (b"requireNonNullElse", b"requireNonNullElseGet", b"isNull", b"nonNull", b"deepEquals", b"hashCode", b"toString", b"equals"):
    assert forbidden not in image, forbidden


def engine_expected(text, objects_hex):
    text = replace_exact(text, OLD, DOMAIN, 9)
    text = replace_exact(text, "new bytes32[](92)", "new bytes32[](93)")
    text = replace_exact(text, '''        // SortedMap is the bounded final append: a link-only interface edge to Map.
        h[91] = keccak256(_bootstrapSortedMap());
        return keccak256(abi.encode(DBOOT, h));''', '''        // SortedMap remains image92; Objects is the bounded final image93.
        h[91] = keccak256(_bootstrapSortedMap());
        h[92] = keccak256(_bootstrapObjects());
        return keccak256(abi.encode(DBOOT, h));''')
    text = replace_exact(text, "uint256 count = inputCount + 86 + (suppliedObject ? 0 : 1)", "uint256 count = inputCount + 87 + (suppliedObject ? 0 : 1)")
    text = replace_exact(text, '''        // SortedMap remains image92. TreeMap's existing slot85 declares this
        // exact interface and concretely supplies only isEmpty().
        p.classes[classSlot + 52].data = _bootstrapSortedMap();
    }''', '''        // SortedMap remains image92. TreeMap's existing slot85 declares this
        // exact interface and concretely supplies only isEmpty().
        p.classes[classSlot + 52].data = _bootstrapSortedMap();
        // Objects is image93: only requireNonNull(Object,String) is present.
        p.classes[classSlot + 53].data = _bootstrapObjects();
    }''')
    text = replace_exact(text, '''            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"))
            || _isNamedClass(c, bytes("java/util/TreeMap"))
            || _isNamedClass(c, bytes("java/util/SortedMap"));''', '''            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"))
            || _isNamedClass(c, bytes("java/util/TreeMap"))
            || _isNamedClass(c, bytes("java/util/SortedMap"))
            || _isNamedClass(c, bytes("java/util/Objects"));''')
    sorted_map = '    function _bootstrapSortedMap() private pure returns (bytes memory) { return hex"cafebabe0000003400090700060700070700080100095369676e61747572650100533c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b4c6a6176612f7574696c2f4d61703c544b3b54563b3e3b0100136a6176612f7574696c2f536f727465644d61700100106a6176612f6c616e672f4f626a65637401000d6a6176612f7574696c2f4d6170060100010002000100030000000000010004000000020005"; }\n'
    objects = sorted_map + '    // Java 8 utility image: private constructor and exactly requireNonNull(Object,String).\n    // The retained NPE supplies only ()V, so the message is deliberately not retained.\n    function _bootstrapObjects() private pure returns (bytes memory) { return hex"' + objects_hex + '"; }\n'
    text = replace_exact(text, sorted_map, objects)
    assert text.count("_bootstrapObjects") == 3
    return text

for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    assert stage_text(relative) == engine_expected(parent_text(relative), image.hex()), relative

coordinator = parent_text("coordinator/MCEntryCoordinator.sol")
coordinator = replace_exact(coordinator, OLD, DOMAIN, 4)
coordinator = replace_exact(coordinator, OLD_ENGINE, ENGINE)
coordinator = replace_exact(coordinator, "8d04b72ed9c83e78ea0a88201f6c7903c3b20c3cdab3830f7fc1e6b6a003f698", ENGINE_PIN["runtimeKeccak256"])
assert stage_text("coordinator/MCEntryCoordinator.sol") == coordinator

transport = parent_text("tools/Go.txt")
for old, new in ((OLD, DOMAIN), (OLD_OWNER, OWNER), (OLD_ENGINE, ENGINE),
                 ("c0d6a3cf0d5478041835eda2e77cb7f7aa6909589d9a9a678c23ee2543d63af2", ENGINE_PIN["runtimeSHA256"]),
                 ("0x8d04b72ed9c83e78ea0a88201f6c7903c3b20c3cdab3830f7fc1e6b6a003f698", "0x" + ENGINE_PIN["runtimeKeccak256"]),
                 ("0x27622589c53ece1b817a0161e60f9340c28836c9913ded65d407ccb044d1d9b2", "0x" + COORDINATOR_PIN["runtimeKeccak256"]),
                 ("len(engineRun) != 391172", "len(engineRun) != 390985"), ("len(run) != 391172", "len(run) != 390985")):
    assert old in transport, old
    transport = transport.replace(old, new)
assert stage_text("tools/Go.txt") == transport

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    assert stage_text(relative) == replace_exact(parent_text(relative), "classes<=140", "classes<=141"), relative
assert stage_text("tools/strip_stackmap.py") == parent_text("tools/strip_stackmap.py")
assert stage_text("tools/verify_receipts.js") == parent_text("tools/verify_receipts.js")

OBJECT_FIXTURES = '# Image93 is exactly Objects.requireNonNull(Object,String).  The non-null\n# result must be the original guest reference.  The literal message exists only\n# as a call argument; this probe does not inspect or retain NPE messages.\nbuild("objects-require-non-null", {\n    "ObjectsRequireNonNullMain.java": """import java.util.Objects;\npublic final class ObjectsRequireNonNullMain {\n  static Object saved;\n  static int result;\n  public static void main(String[] ignored) {\n    Object value = new Object();\n    saved = Objects.requireNonNull(value, "factory");\n    if (saved != value) throw new Error();\n    Object again = Objects.requireNonNull(saved, (String) null);\n    if (again != value || saved != again) throw new Error();\n    result = 7;\n  }\n}\n""",\n}, ["ObjectsRequireNonNullMain.class"], "ObjectsRequireNonNullMain")\n\n# The only null surface is a catchable guest NPE.  No message getter, String\n# retention, or NPE(String) constructor is named or asserted.\nbuild("objects-require-non-null-null", {\n    "ObjectsRequireNonNullNullMain.java": """import java.util.Objects;\npublic final class ObjectsRequireNonNullNullMain {\n  static int result;\n  public static void main(String[] ignored) {\n    try { Objects.requireNonNull(null, "factory"); throw new Error(); }\n    catch (NullPointerException expected) { result = 7; }\n  }\n}\n""",\n}, ["ObjectsRequireNonNullNullMain.class"], "ObjectsRequireNonNullNullMain")\n\n# A no-use root must not initialize the append-only image93.\nbuild("objects-require-non-null-uninitialized", {\n    "ObjectsRequireNonNullUninitializedMain.java": """public final class ObjectsRequireNonNullUninitializedMain {\n  static int result;\n  public static void main(String[] ignored) { result = 7; }\n}\n""",\n}, ["ObjectsRequireNonNullUninitializedMain.class"], "ObjectsRequireNonNullUninitializedMain")\n\n# Bootstrap ownership rejects a raw replacement before guest execution.\nbuild("raw-objects", {\n    "RawObjectsReplacementMain.java": "public final class RawObjectsReplacementMain { public static void main(String[] ignored) {} }\\n",\n    "java/util/Objects.java": "package java.util; public final class Objects { private Objects() {} public static <T> T requireNonNull(T value, String message) { return value; } }\\n",\n}, ["RawObjectsReplacementMain.class", "java/util/Objects.class"])\n\n# The one-argument overload is deliberately absent; this generated control must\n# link-fail rather than broaden Objects beyond the requested descriptor.\nbuild("objects-require-non-null-onearg-omitted", {\n    "ObjectsRequireNonNullOneArgOmittedMain.java": """import java.util.Objects;\npublic final class ObjectsRequireNonNullOneArgOmittedMain {\n  public static void main(String[] ignored) { Objects.requireNonNull(new Object()); }\n}\n""",\n}, ["ObjectsRequireNonNullOneArgOmittedMain.class"])\n\n'
generated = parent_text("tools/generate_fixtures.py")
generated = replace_exact(generated, "classcount48-byte314425", "objects-require-non-null")
generated = replace_exact(generated, "Create only trusted generated Java-8 raw48 boundaries and retained controls.", "Create only trusted generated Java-8 Objects.requireNonNull and retained controls.")
generated = replace_exact(generated, "bootstrap_count=92", "bootstrap_count=93")
generated = replace_exact(generated, "bootstrap_count=91", "bootstrap_count=92")
generated = replace_exact(generated, '"bootstrapCount": 92', '"bootstrapCount": 93')
count_marker = 'for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49): count_fixture("count-%d" % count, count)\n'
assert generated.count(count_marker) == 1
generated = generated.replace(count_marker, OBJECT_FIXTURES + count_marker)
assert stage_text("tools/generate_fixtures.py") == generated

OBJECT_GATE = '# Image93 has only Objects.requireNonNull(Object,String).  The generated\n# positive root compares the returned reference to the original guest object;\n# q1/q7/direct/reopen must preserve exact identity and full checkpoint payload.\ndef objects_require_non_null_initialized(decoded, label):\n    raw = fixture(label)["bindingCount"]\n    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}\n    assert states[raw + 92]["state"] == 2\nq_equivalent("objects-require-non-null", "objects-require-non-null",\n             lambda decoded: objects_require_non_null_initialized(decoded, "objects-require-non-null"))\n\n# The null path catches only guest NullPointerException.  It deliberately does\n# not invoke a message getter or a String-taking NPE constructor, and makes no\n# message-retention assertion.\nq_equivalent("objects-require-non-null-null", "objects-require-non-null-null",\n             lambda decoded: objects_require_non_null_initialized(decoded, "objects-require-non-null-null"))\n\n# A no-use root keeps the new tail image uninitialized.\nobjects_noinit = finish("objects-require-non-null-uninitialized", "objects-require-non-null-uninitialized", 4096)\nworld = out / objects_noinit["world"]\n_, _, decoded = terminal(world, fixture("objects-require-non-null-uninitialized")["bindingCount"])\nstates = {entry["classIndex"]: entry for entry in decoded["initialization"]}\nassert fixture("objects-require-non-null-uninitialized")["bindingCount"] + 92 not in states\nrows["objects-require-non-null-uninitialized"] = objects_noinit\n\n# Bootstrap ownership rejects a raw Objects image before instruction execution.\nworld = out / "world-raw-objects"\nrun("raw-objects-replacement", [driver, "setup-chain", world, coordinator, engine,\n    fixtures / "raw-objects.zip", "4096"], "raw-objects")\nrefusal = failure(world, "start-refusal.json")\nassert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]\nrows["raw-objects"] = refusal\n\n# The one-argument overload is not part of image93 and must resolve to the\n# ordinary missing-member refusal, never an expanded Objects API.\nworld = out / "world-objects-require-non-null-onearg-omitted"\nrun("objects-require-non-null-onearg-omitted", [driver, "setup-chain", world, coordinator, engine,\n    fixtures / "objects-require-non-null-onearg-omitted.zip", "4096"], "objects-require-non-null-onearg-omitted")\nrefusal = failure(world, "start-refusal.json")\nassert refusal["selector"] == "0xd631c3a4" and words(refusal) == ["3", "7"] and refusal["rootUnchanged"]\nrows["objects-require-non-null-onearg-omitted"] = refusal\n\n'
gate = parent_text("tools/gate.py")
for old, new, count in (("Generated-only raw48/byte314425 capacity and retained TreeMap gate.", "Generated-only Objects.requireNonNull(Object,String) and retained gate.", 1),
                        ("classcount48-byte314425", "objects-require-non-null", 3),
                        ('pins["bootstrapCount"] == 92 and pins["rawLimits"] == [48, 314425]', 'pins["bootstrapCount"] == 93 and pins["rawLimits"] == [48, 314425]', 1),
                        ('pins["diagnosticClassBound"] == 140 and pins["engine"]["bytes"] <= 393216', 'pins["diagnosticClassBound"] == 141 and pins["engine"]["bytes"] <= 393216', 1),
                        ("bootstrap_count=92", "bootstrap_count=93", 1), ("raw_count + 92", "raw_count + 93", 1),
                        ('decoded["classCount"] - 92', 'decoded["classCount"] - 93', 2),
                        ('fixture(label)["bindingCount"] + 92', 'fixture(label)["bindingCount"] + 93', 1),
                        ('"profile": "MC-RAW48-BYTE314425-P1"', '"profile": "MC-OBJECTS-REQUIRE-NON-NULL-P1"', 1)):
    gate = replace_exact(gate, old, new, count)
needle = 'assert pins["bootstrapSHA256"]["SortedMap"] == "c59e7d5cb3219d4fe2844d720a5f74158c8760d58f34ab3d8bb8d81ba8bb9b06"\n'
gate = replace_exact(gate, needle, needle + 'assert pins["bootstrapSHA256"]["Objects"] == "' + OBJECTS_SHA256 + '"\n')
gate_marker = '# Exact raw48 is the focused capacity witness: all q1/q7/direct/reopen\n'
gate = replace_exact(gate, gate_marker, OBJECT_GATE + gate_marker)
old_limit = 'Only selected raw-class capacity changes from the accepted raw47/byte313706 stage: raw47/313706/diagnostic139 to raw48/314425/diagnostic140. All 92 ordered bootstrap images and bytes, including TreeMap SortedMap.isEmpty and its runtime-derived root, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns the genuine append and class/factory execution or accelerated replay.'
new_limit = 'Only image93, generated Java-8 java/util/Objects, and the read-only diagnostic class bound change: bootstrap count92 to93 and diagnostic140 to141. Objects exposes only private construction and requireNonNull(Object,String), returns the exact non-null reference, and throws a guest NullPointerException for null without a message-retention claim. Raw48/314425, native13, the runtime-derived ordered root, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine replay.'
gate = replace_exact(gate, old_limit, new_limit)
assert stage_text("tools/gate.py") == gate

pins = json.loads(stage_text("build-pins.json")); parent_pins = json.loads(parent_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "2fba6526e", "parentEvidence": "classcount48-byte314425-preflight", "phase": "built", "domain": DOMAIN, "runtimeBaseline": 391172, "bootstrapCount": 93, "diagnosticClassBound": 141, "address": "0x" + ENGINE, "owner": "0x" + OWNER, "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN})
expected_pins["bootstrapSHA256"]["Objects"] = OBJECTS_SHA256
assert pins == expected_pins
assert pins["rawLimits"] == [48, 314425] and pins["globalNativeBindings"] == 13 and pins["stringLocalBinding"] == 10
assert pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128 and pins["runtimeCap"] == 393216
assert pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000 and pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768

record = json.loads(stage_text("root-commitment.json")); parent_record = json.loads(parent_text("root-commitment.json"))
assert record["domain"] == DOMAIN and record["bootstrapCount"] == 93
assert record["order"] == parent_record["order"] + ["Objects"]
assert record["keccak256"] == parent_record["keccak256"] + [OBJECTS_KECCAK]
node = root / "jvmevm/runtime/node_modules"; assert node.is_dir()
env = {**os.environ, "NODE_PATH": str(node)}
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + DOMAIN + ":BOOTSTRAP:1"], cwd=root, env=env, text=True))
assert actual == {"d": record["dboot"], "r": record["bootstrapRoot"]}
assert len(record["keccak256"]) == len(record["order"]) == 93

for relative in ("tools/build.py",):
    text = stage_text(relative)
    for required in ("verify_source.py", "MCEntryInterpreter", "MCEntryCoordinator", "objects-require-non-null", "go-build", "go-vet"):
        assert required in text, (relative, required)
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "domain": DOMAIN, "bootstrapImages": 93, "bootstrapRoot": record["bootstrapRoot"], "objectsSHA256": OBJECTS_SHA256, "rawLimits": pins["rawLimits"], "diagnosticClassBound": 141, "runtimeBaseline": 391172, "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216, "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
