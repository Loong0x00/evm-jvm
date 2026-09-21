#!/usr/bin/env python3
"""Pin image94 SecurityManager to the generated raw50 source stage only."""
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
parent = stage.parent / "classcount50-byte324338-preflight"
D = "MC-SECURITY-MANAGER-LINK-P1"
OLD_D = "MC-RAW50-BYTE324338-P1"
ENGINE = "4d432d5345434d47522d4c494e4b2d50312d4558"
OWNER = "4d432d5345434d47522d4c494e4b2d50312d4f58"
OLD_ENGINE = "4d432d52415735302d4259544533323433333845"
OLD_OWNER = "4d432d52415735302d425954453332343333384f"
SECURITY_HEX = "cafebabe00000034000a0a000300070700080700090100063c696e69743e010003282956010004436f64650c000400050100196a6176612f6c616e672f53656375726974794d616e616765720100106a6176612f6c616e672f4f626a656374002100020003000000000001000100040005000100060000001100010001000000052ab70001b1000000000000"
SECURITY_SHA = "b17c1eae93a5c88fb4970628c6b1fc1ec34d7a7485bc80fe810a3b16c4ff0bcb"
SECURITY_KECCAK = "057ca3fbcb2390bdc0d8a6bd4f9a942b378525c0dca258dff442b04e7b526a28"
ENGINE_PIN = {"bytes": 393007, "initSHA256": "e3e5accb202fc8c7255d235ce57a9808cdc6f7becd0a9fbd6bb13b3671f77957", "runtimeSHA256": "0d3ffeddf4f72a01e9217ee5036edd92fe8eb3c8c244fd844570424e980540de", "runtimeKeccak256": "000acfffdb361795ad92e975c8165d01a8d3bcb8da22914d560a6adc42e38f40"}
COORDINATOR_PIN = {"bytes": 5392, "initSHA256": "791438267ccbefe09bbb140e10260f609d9d8f43ee189ddd2e91f65fa7c3bda7", "runtimeSHA256": "0f2932c4ee6767e3a449fcee438fa08a59ee385a543b31ff06fa0b16e879873c", "runtimeKeccak256": "d74312afbfbb77510697e6f09a5f9417bdb3b0454e82dc104b3f61562f60b1ad"}
LIMITS = "b9bc6dc95e7de777dd6e512f44131177e4741934f18d2d25f7ba506ad1594b9c"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def parent_text(relative):
    return (parent / relative).read_text()


def stage_text(relative):
    return (stage / relative).read_text()


def expected_engine(text):
    text = replace_exact(text, OLD_D, D, 9)
    text = replace_exact(text, '    bytes32 private constant DBOOT_THREAD_LOCAL = hex"93a0007b6336f667890f5afa2b01572278a7e39ab93b2faf1095e054317f538a";\n', '    bytes32 private constant DBOOT_THREAD_LOCAL = hex"93a0007b6336f667890f5afa2b01572278a7e39ab93b2faf1095e054317f538a";\n    // Image94 commitment keeps the constrained runtime below its fixed LOCAL cap.\n    bytes32 private constant DBOOT_SECURITY_MANAGER = hex"' + SECURITY_KECCAK + '";\n')
    text = replace_exact(text, "bytes32[] memory h = new bytes32[](93);", "bytes32[] memory h = new bytes32[](94);")
    text = replace_exact(text, '''        // SortedMap remains image92; Objects is the bounded final image93.
        h[91] = keccak256(_bootstrapSortedMap());
        h[92] = keccak256(_bootstrapObjects());''', '''        // SortedMap remains image92; Objects remains image93.
        h[91] = keccak256(_bootstrapSortedMap());
        h[92] = keccak256(_bootstrapObjects());
        // SecurityManager is append-only image94 with only Object-chaining construction.
        h[93] = DBOOT_SECURITY_MANAGER;''')
    text = replace_exact(text, '''                || _isReservedQueueClass(users[i])
                || _isReservedEnumClass(users[i])) {''', '''                || _isReservedQueueClass(users[i])
                || _isReservedEnumClass(users[i])
                || _isReservedSecurityManagerClass(users[i])) {''')
    text = replace_exact(text, "uint256 count = inputCount + 87 + (suppliedObject ? 0 : 1)", "uint256 count = inputCount + 88 + (suppliedObject ? 0 : 1)")
    text = replace_exact(text, '''    function _isReservedPrivilegedActionClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/security/PrivilegedAction"));
    }
''', '''    function _isReservedPrivilegedActionClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/security/PrivilegedAction"));
    }

    // Image94 is interpreter-owned so raw bundles cannot replace even its
    // deliberately minimal construction/type-link surface.
    function _isReservedSecurityManagerClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/SecurityManager"));
    }
''')
    text = replace_exact(text, '''        // Objects is image93: only requireNonNull(Object,String) is present.
        p.classes[classSlot + 53].data = _bootstrapObjects();''', '''        // Objects remains image93: only requireNonNull(Object,String) is present.
        p.classes[classSlot + 53].data = _bootstrapObjects();
        // SecurityManager image94 exposes only public Object-chaining <init>().
        p.classes[classSlot + 54].data = _bootstrapSecurityManager();''')
    marker = "    function _bootstrapObjects() private pure returns (bytes memory) {"
    at = text.index(marker)
    line_end = text.index("\n", at) + 1
    return text[:line_end] + "    // Image94 has no fields, checks, policy, native, or other member.\n    function _bootstrapSecurityManager() private pure returns (bytes memory) { return hex\"" + SECURITY_HEX + "\"; }\n" + text[line_end:]


# The only interpreter delta is the append-only image94 family, its bootstrap
# reservation, size-preserving commitment, and fresh local identity domains.
for relative in ("engine/MCEntryInterpreter.sol", "engine/pre-layout-MCEntryInterpreter.sol"):
    assert stage_text(relative) == expected_engine(parent_text(relative)), relative

# Coordinator semantics remain byte-for-byte inherited apart from the fresh
# EVM binding/hash and package domains; raw50/324338 guards and arrays stay fixed.
want = parent_text("coordinator/MCEntryCoordinator.sol")
want = replace_exact(want, OLD_D, D, 4)
want = replace_exact(want, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
want = replace_exact(want, "908b5e3ac6cd7ed1743cd6ea87ffe2557bcbe51b22fd8728d05c3d9f0609310a", ENGINE_PIN["runtimeKeccak256"])
assert stage_text("coordinator/MCEntryCoordinator.sol") == want

# No host class interpretation changes: transport only receives fresh local
# domains/addresses and rebuilt engine/coordinator commitments.
want = parent_text("tools/Go.txt")
for old, new, count in (
    (OLD_D, D, 6), (OLD_OWNER, OWNER, 1), (OLD_ENGINE, ENGINE, 1),
    ("944590f82f2f20a9a295b7950c9163221ca260e0675099369a86df6b4086f24e", ENGINE_PIN["runtimeSHA256"], 1),
    ("0x908b5e3ac6cd7ed1743cd6ea87ffe2557bcbe51b22fd8728d05c3d9f0609310a", "0x" + ENGINE_PIN["runtimeKeccak256"], 1),
    ("0x596906f79fd7c9a526532112b98601e48e4d3f44ee6224356506073318ad9447", "0x" + COORDINATOR_PIN["runtimeKeccak256"], 1),
    ("len(engineRun) != 391507", "len(engineRun) != 393007", 1),
    ("len(coordRun) != 5394", "len(coordRun) != 5392", 1),
    ("len(run) != 391507", "len(run) != 393007", 1),
):
    want = replace_exact(want, old, new, count)
assert stage_text("tools/Go.txt") == want

SECURITY_FIXTURES = '''# Image94 is public no-arg construction only.  This fixture exercises normal
# allocation, Object assignment, and a checkcast type-link without naming any
# security, policy, context, permission, installation, or host surface.
build("security-manager-construction", {
    "SecurityManagerConstructionMain.java": """public final class SecurityManagerConstructionMain {
  static SecurityManager saved;
  static int result;
  public static void main(String[] ignored) {
    SecurityManager first = new SecurityManager();
    SecurityManager second = new SecurityManager();
    Object asObject = first;
    SecurityManager restored = (SecurityManager) asObject;
    if (first == null || second == null || first == second || restored != first) throw new Error();
    saved = restored;
    if (saved != first || saved == second) throw new Error();
    result = 7;
  }
}
""",
}, ["SecurityManagerConstructionMain.class"])

# A no-use root keeps the appended image uninitialized.
build("security-manager-uninitialized", {
    "SecurityManagerUninitializedMain.java": """public final class SecurityManagerUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["SecurityManagerUninitializedMain.class"], "SecurityManagerUninitializedMain")

# Bootstrap ownership rejects a raw substitute before parser execution.
build("raw-security-manager", {
    "RawSecurityManagerReplacementMain.java": "public final class RawSecurityManagerReplacementMain { public static void main(String[] ignored) {} }\\n",
    "java/lang/SecurityManager.java": "package java.lang; public class SecurityManager { public SecurityManager() {} }\\n",
}, ["RawSecurityManagerReplacementMain.class", "java/lang/SecurityManager.class"])

# Representative platform API omission: the constructor is the full image94
# surface.  This source compiles against Java 8 but is never host-executed.
build("security-manager-api-omitted", {
    "SecurityManagerApiOmittedMain.java": """public final class SecurityManagerApiOmittedMain {
  public static void main(String[] ignored) { new SecurityManager().getSecurityContext(); }
}
""",
}, ["SecurityManagerApiOmittedMain.class"])

'''

want = parent_text("tools/generate_fixtures.py")
want = replace_exact(want, "java-diff-mc-classcount50-byte324338-fixtures-", "java-diff-mc-security-manager-link-fixtures-")
want = replace_exact(want, "bootstrap_count=93", "bootstrap_count=94")
want = replace_exact(want, "bootstrap_count=92", "bootstrap_count=93")
want = replace_exact(want, '"bootstrapCount": 93', '"bootstrapCount": 94')
needle = 'for count in (29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51): count_fixture("count-%d" % count, count)\n'
assert want.count(needle) == 1
want = want.replace(needle, SECURITY_FIXTURES + needle)
assert stage_text("tools/generate_fixtures.py") == want

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    assert stage_text(relative) == replace_exact(parent_text(relative), "classes<=143", "classes<=144"), relative

SECURITY_GATE = '''# Image94 contains only public Object-chaining construction.  The ordinary
# generated root verifies fresh identity and concrete Object/checkcast type-link;
# q1/q7/direct/reopen must agree on full terminal state.
def security_manager_initialized(decoded, label):
    raw = fixture(label)["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 93]["state"] == 2
q_equivalent("security-manager-construction", "security-manager-construction",
             lambda decoded: security_manager_initialized(decoded, "security-manager-construction"))

# A root without the name must leave the append-only image dormant.
security_manager_noinit = finish("security-manager-uninitialized", "security-manager-uninitialized", 4096)
world = out / security_manager_noinit["world"]
_, _, decoded = terminal(world, fixture("security-manager-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("security-manager-uninitialized")["bindingCount"] + 93 not in states
rows["security-manager-uninitialized"] = security_manager_noinit

# Raw replacement is refused before any guest instruction or checkpoint.
world = out / "world-raw-security-manager"
run("raw-security-manager-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-security-manager.zip", "4096"], "raw-security-manager")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-security-manager"] = refusal

# The representative inherited Java SE method is absent: this must be ordinary
# missing-member resolution, never a fabricated policy/context/security API.
world = out / "world-security-manager-api-omitted"
run("security-manager-api-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "security-manager-api-omitted.zip", "4096"], "security-manager-api-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows["security-manager-api-omitted"] = refusal

'''


def expected_gate(text):
    text = replace_exact(text, "java-diff-mc-classcount50-byte324338-build-", "java-diff-mc-security-manager-link-build-")
    text = replace_exact(text, "java-diff-mc-classcount50-byte324338-fixtures-", "java-diff-mc-security-manager-link-fixtures-")
    text = replace_exact(text, "java-diff-mc-classcount50-byte324338-gate-", "java-diff-mc-security-manager-link-gate-")
    text = replace_exact(text, 'bootstrapCount"] == 93', 'bootstrapCount"] == 94')
    text = replace_exact(text, 'diagnosticClassBound"] == 143', 'diagnosticClassBound"] == 144')
    text = replace_exact(text, "bootstrap_count=93", "bootstrap_count=94")
    text = replace_exact(text, "raw_count + 93", "raw_count + 94")
    text = replace_exact(text, 'decoded["classCount"] - 93', 'decoded["classCount"] - 94', 2)
    text = replace_exact(text, 'fixture(label)["bindingCount"] + 93', 'fixture(label)["bindingCount"] + 94')
    objects = 'assert pins["bootstrapSHA256"]["Objects"] == "fc87c7bfe18107225d3682238f8c1a07d0e66d737f1d26f95edc7d7f9a7698df"\n'
    text = replace_exact(text, objects, objects + 'assert pins["bootstrapSHA256"]["SecurityManager"] == "' + SECURITY_SHA + '"\n')
    marker = "# Exact raw50 is the focused capacity witness: all q1/q7/direct/reopen\n"
    text = replace_exact(text, marker, SECURITY_GATE + marker)
    old_summary = '''summary = {"profile": "MC-RAW50-BYTE324338-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only selected raw-class capacity changes from raw49 evidence: raw49/322481/diagnostic142 to raw50/324338/diagnostic143. All 93 ordered bootstrap images and bytes, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and the runtime-derived ordered root remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine ReflectionUtil$PrivateSecurityManager append and class/factory execution or accelerated replay."}'''
    new_summary = '''summary = {"profile": "MC-SECURITY-MANAGER-LINK-P1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Image94 adds only java/lang/SecurityManager public no-arg Object-chaining construction. The prior 93 ordered bootstrap leaves and all raw50/324338/native13/limits/toolchain semantics remain pinned; only image94 has its independently verified root commitment to retain the fixed runtime cap. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine replay."}'''
    return replace_exact(text, old_summary, new_summary)


assert stage_text("tools/gate.py") == expected_gate(parent_text("tools/gate.py"))

want = parent_text("tools/build.py")
want = replace_exact(want, '"""Rebuild the pinned generated raw50/byte324338 evidence."""', '"""Rebuild the pinned generated image94 SecurityManager evidence."""')
want = replace_exact(want, "java-diff-mc-classcount50-byte324338-build-", "java-diff-mc-security-manager-link-build-")
assert stage_text("tools/build.py") == want
for relative in ("tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert stage_text(relative) == parent_text(relative), relative

# Image94 is generated locally with the pinned Java 8 compiler. Its source and
# class bytes prove one public no-arg Object-chaining constructor and no fields
# or additional methods; no external/original class is read.
source = stage / "bootstrap/java/lang/SecurityManager.java"
hex_file = stage / "bootstrap/java/lang/SecurityManager.class.hex"
assert source.read_text() == '''package java.lang;

/** Bounded bootstrap: public no-arg construction only. */
public class SecurityManager {
    public SecurityManager() {}
}
'''
assert hex_file.read_text().strip() == SECURITY_HEX
with tempfile.TemporaryDirectory(prefix="security-manager-image94-", dir=root / "build") as tmp:
    tmp = Path(tmp)
    classes = tmp / "classes"
    classes.mkdir()
    javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
    assert javac.is_file()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, source], check=True)
    data = (classes / "java/lang/SecurityManager.class").read_bytes()
assert data.hex() == SECURITY_HEX and len(data) == 140 and hashlib.sha256(data).hexdigest() == SECURITY_SHA
# Exact classfile shape: access public/super, Object direct superclass, no fields,
# and exactly <init>()V. This is a read-only byte assertion, not host execution.
assert data[:8] == bytes.fromhex("cafebabe00000034")
assert data.count(b"SecurityManager") == 1 and b"checkPermission" not in data and b"getClassContext" not in data

record = json.loads(stage_text("root-commitment.json"))
parent_record = json.loads(parent_text("root-commitment.json"))
assert record["domain"] == D and record["bootstrapCount"] == 94
assert record["order"] == parent_record["order"] + ["SecurityManager"]
assert record["keccak256"] == parent_record["keccak256"] + [SECURITY_KECCAK]
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", script, ",".join(record["keccak256"]), "JVMEVM:" + D + ":BOOTSTRAP:1"], cwd=root / "jvmevm/runtime", text=True))
assert record["dboot"] == actual["d"] and record["bootstrapRoot"] == actual["r"]
limits = [50, 324338, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root / "jvmevm/runtime", text=True).strip() == LIMITS

parent_pins = json.loads(parent_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "86c2bb3fa", "parentEvidence": "classcount50-byte324338-preflight", "phase": "built", "domain": D,
                      "runtimeBaseline": 391507, "bootstrapCount": 94, "diagnosticClassBound": 144,
                      "address": "0x" + ENGINE, "owner": "0x" + OWNER,
                      "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN})
expected_pins["bootstrapSHA256"]["SecurityManager"] = SECURITY_SHA
assert pins == expected_pins
assert pins["rawLimits"] == [50, 324338] and pins["limitsCommitment"] == LIMITS
assert pins["globalNativeBindings"] == 13 and pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
assert pins["runtimeBaseline"] == 391507 and pins["engine"]["bytes"] == 393007 <= pins["runtimeCap"] == 393216
assert pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000 and pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768
assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt") and ENGINE_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "basis": "86c2bb3fa", "domain": D, "bootstrapImages": 94,
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 144, "runtimeBaseline": 391507,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
