#!/usr/bin/env python3
"""Verify the measured Object.hashCode addition against accepted P12.

Only the pinned accepted P12 Solidity/bootstrap source and generated stage
sources are read. This verifier does not access original class/JAR/resource,
world, checkpoint, or external/network inputs.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-cd8122975"
object_precedent = stage.parent / "object-get-class-preflight/bootstrap/java/lang/Object.java"
pins = json.loads((stage / "baseline-pins.json").read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def function_block(text, name):
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def function_image(text, name):
    values = re.findall(r'hex"([0-9a-f]+)"', function_block(text, name))
    assert len(values) == 1, (name, len(values))
    return bytes.fromhex(values[0])


def parse_class(data):
    def u1(at): return data[at], at + 1
    def u2(at): return int.from_bytes(data[at:at + 2], "big"), at + 2
    def u4(at): return int.from_bytes(data[at:at + 4], "big"), at + 4

    assert data[:4] == bytes.fromhex("cafebabe")
    minor, major = int.from_bytes(data[4:6], "big"), int.from_bytes(data[6:8], "big")
    count = int.from_bytes(data[8:10], "big")
    cp = [None] * count
    at = 10
    index = 1
    while index < count:
        tag, at = u1(at)
        if tag == 1:
            length, at = u2(at); cp[index] = (tag, data[at:at + length]); at += length
        elif tag in (3, 4):
            cp[index] = (tag, data[at:at + 4]); at += 4
        elif tag in (5, 6):
            cp[index] = (tag, data[at:at + 8]); at += 8; index += 1
        elif tag in (7, 8, 16, 19, 20):
            value, at = u2(at); cp[index] = (tag, value)
        elif tag in (9, 10, 11, 12, 17, 18):
            left, at = u2(at); right, at = u2(at); cp[index] = (tag, left, right)
        elif tag == 15:
            kind, at = u1(at); target, at = u2(at); cp[index] = (tag, kind, target)
        else:
            raise AssertionError(("constant-pool-tag", tag, index))
        index += 1

    def utf(index):
        assert 0 < index < len(cp) and cp[index][0] == 1, index
        return cp[index][1]

    def class_name(index):
        assert 0 < index < len(cp) and cp[index][0] == 7, index
        return utf(cp[index][1])

    access, at = u2(at); this_class, at = u2(at); super_class, at = u2(at)
    interface_count, at = u2(at)
    interfaces = [class_name(int.from_bytes(data[at + 2*i:at + 2*i + 2], "big"))
                  for i in range(interface_count)]
    at += interface_count * 2

    def attrs():
        nonlocal at
        count, at = u2(at); values = []
        for _ in range(count):
            name_index, at = u2(at); length, at = u4(at)
            value = data[at:at + length]; at += length
            values.append((utf(name_index), value))
        return values

    def members():
        nonlocal at
        count, at = u2(at); values = []
        for _ in range(count):
            flags, at = u2(at); name_index, at = u2(at); descriptor_index, at = u2(at)
            values.append({"flags": flags, "name": utf(name_index),
                           "descriptor": utf(descriptor_index), "attributes": attrs()})
        return values

    fields = members(); methods = members(); class_attributes = attrs()
    assert at == len(data), (at, len(data))

    def code(method):
        values = [value for name, value in method["attributes"] if name == b"Code"]
        assert len(values) <= 1, (method["name"], len(values))
        if not values:
            return None
        value = values[0]
        max_stack = int.from_bytes(value[:2], "big")
        max_locals = int.from_bytes(value[2:4], "big")
        length = int.from_bytes(value[4:8], "big")
        bytecode = value[8:8 + length]
        exception_count = int.from_bytes(value[8 + length:10 + length], "big")
        tail = 10 + length + exception_count * 8
        nested_count = int.from_bytes(value[tail:tail + 2], "big")
        nested = []; pos = tail + 2
        for _ in range(nested_count):
            attr_index = int.from_bytes(value[pos:pos + 2], "big")
            attr_length = int.from_bytes(value[pos + 2:pos + 6], "big")
            nested.append((utf(attr_index), value[pos + 6:pos + 6 + attr_length]))
            pos += 6 + attr_length
        assert pos == len(value)
        return {"maxStack": max_stack, "maxLocals": max_locals, "bytecode": bytecode,
                "exceptions": exception_count, "attributes": nested}

    return {"minor": minor, "major": major, "access": access,
            "this": class_name(this_class), "super": class_name(super_class) if super_class else None,
            "interfaces": interfaces, "fields": fields, "methods": methods,
            "classAttributes": class_attributes, "constantPool": cp,
            "utf": utf, "className": class_name, "code": code}


def pascal_constant(name):
    overrides = {
        "ENUMSET": "EnumSet", "ITERABLE": "Iterable", "MATH": "Math",
        "RANDOM": "Random", "THREAD": "Thread", "THREAD_LOCAL": "ThreadLocal",
        "STACK_TRACE_ELEMENT": "StackTraceElement", "PRINT_STREAM": "PrintStream",
        "SECURITY_MANAGER": "SecurityManager",
    }
    tail = name.removeprefix("DBOOT_")
    return "_bootstrap" + overrides.get(tail, "".join(x.title() for x in tail.split("_")))


# Ensure this stage is rooted at the accepted independent P12 artifact, not the
# earlier worker/P10 source. The parent artifacts are immutable tracked evidence.
p12_engine_path = parent / "artifacts/engine/MCEntryInterpreter.sol"
p12_coord_path = parent / "artifacts/coordinator/MCEntryCoordinator.sol"
p12_engine_build = parent / "artifacts/engine/build.js"
p12_coord_build = parent / "artifacts/coordinator/build.js"
p12_driver = parent / "canonical-driver.go.txt"
assert file_sha(p12_engine_path) == pins["engineSourceSHA256"]
assert file_sha(p12_engine_build) == pins["engineBuildSHA256"]
assert file_sha(p12_coord_path) == pins["coordinatorSourceSHA256"]
assert file_sha(p12_coord_build) == pins["coordinatorBuildSHA256"]
assert file_sha(p12_driver) == pins["driverSHA256"]
assert pins["domain"] == "MC-RANDOM-CLASS-P12" and pins["bootstrapCount"] == 97
assert pins["rawLimits"] == [71, 471911] and pins["globalNativeBindings"] == 21
assert pins["stringLocalBinding"] == 12 and pins["diagnosticClassBound"] == 168
assert pins["checkpointCap"] == 1048576 and pins["headCap"] == 32768
assert pins["reserve"] == 25000000 and pins["ordinaryGas"] == 1000000000
assert pins["runtimeCap"] == 393216 and pins["maxFrames"] == 128
assert pins["exceptionKinds"] == 14

old_engine = p12_engine_path.read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
old_image = function_image(old_engine, "_bootstrapObject")
new_image = function_image(engine, "_bootstrapObject")
old_literal = 'return hex"' + old_image.hex() + '";'
new_literal = 'return hex"' + new_image.hex() + '";'
assert old_image != new_image
assert old_engine.count(old_literal) == 1
assert engine == old_engine.replace(old_literal, new_literal)
assert sha(old_image) != sha(new_image)

old_images = {}
new_images = {}
image_pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{.*?return hex"([0-9a-f]+)";'
old_images = dict(re.findall(image_pattern, old_engine, re.S))
new_images = dict(re.findall(image_pattern, engine, re.S))
assert set(old_images) == set(new_images)
assert "_bootstrapObject" in old_images and set(old_images) == set(new_images)
changed_images = [name for name in sorted(old_images) if old_images[name] != new_images[name]]
assert changed_images == ["_bootstrapObject"], changed_images

# Java 8 source and class are exact. Normalize only its comment and the one
# added ordinary method back to the supplied Object.getClass precedent.
old_source = object_precedent.read_text()
expected_old_source = """package java.lang;\n\n/** Java 8 bounded bootstrap Object: only constructor, equals, and getClass. */\npublic class Object {\n    public Object() {}\n    public boolean equals(Object other) { return this == other; }\n    public final native Class<?> getClass();\n}\n"""
assert old_source == expected_old_source
candidate_source = (stage / "bootstrap/java/lang/Object.java").read_text()
expected_candidate = """package java.lang;\n\n/** Java 8 bounded bootstrap Object: constructor, identity hash, equals, and getClass. */\npublic class Object {\n    public Object() {}\n    public boolean equals(Object other) { return this == other; }\n    public int hashCode() { return System.identityHashCode(this); }\n    public final native Class<?> getClass();\n}\n"""
assert candidate_source == expected_candidate
normalized_source = candidate_source.replace(
    "/** Java 8 bounded bootstrap Object: constructor, identity hash, equals, and getClass. */",
    "/** Java 8 bounded bootstrap Object: only constructor, equals, and getClass. */")
normalized_source = normalized_source.replace(
    "    public int hashCode() { return System.identityHashCode(this); }\n", "")
assert normalized_source == old_source

javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="object-hash-code-source-", dir=root / "build") as temporary:
    tmp = Path(temporary); output = tmp / "classes"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output,
                    stage / "bootstrap/java/lang/Object.java"], cwd=root, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    compiled_object = (output / "java/lang/Object.class").read_bytes()
assert compiled_object == new_image
assert (stage / "bootstrap/java/lang/Object.class.hex").read_text().strip() == compiled_object.hex()
assert (stage / "bootstrap/java/lang/Object.sha256").read_text().split()[0] == sha(compiled_object)
assert sha(compiled_object) == "ac898039bbd7f71df4c6553f6156c75465f41c1d1537e99c50a09aeee9eab138"

# The source change is exactly one ordinary public method. Constructor/equals
# Code and the existing final native getClass declaration remain unchanged.
old_object = parse_class(old_image); obj = parse_class(new_image)
assert old_object["major"] == obj["major"] == 52 and obj["minor"] == 0
assert obj["access"] == 0x0021 and obj["this"] == b"java/lang/Object"
assert obj["super"] is None and obj["interfaces"] == [] and obj["fields"] == []
methods = obj["methods"]
assert [(m["flags"], m["name"], m["descriptor"]) for m in methods] == [
    (0x0001, b"<init>", b"()V"),
    (0x0001, b"equals", b"(Ljava/lang/Object;)Z"),
    (0x0001, b"hashCode", b"()I"),
    (0x0111, b"getClass", b"()Ljava/lang/Class;"),
]
old_methods = old_object["methods"]
assert [(m["flags"], m["name"], m["descriptor"]) for m in old_methods] == [
    (0x0001, b"<init>", b"()V"), (0x0001, b"equals", b"(Ljava/lang/Object;)Z"),
    (0x0111, b"getClass", b"()Ljava/lang/Class;"),
]
for old_method in old_methods[:2]:
    new_method = next(m for m in methods if m["name"] == old_method["name"])
    assert old_object["code"](old_method)["bytecode"] == obj["code"](new_method)["bytecode"]
hash_code = obj["code"](methods[2])
assert (hash_code["maxStack"], hash_code["maxLocals"], hash_code["exceptions"],
        hash_code["attributes"]) == (1, 1, 0, [])
# Resolve the invokestatic index from the exact bytecode and require only the
# existing System.identityHashCode(Object) target.
hash_code = obj["code"](methods[2])
assert hash_code["bytecode"][0] == 0x2a and hash_code["bytecode"][1] == 0xb8
assert hash_code["bytecode"][-1] == 0xac and len(hash_code["bytecode"]) == 5
reference = int.from_bytes(hash_code["bytecode"][2:4], "big")
cp = obj["constantPool"]
assert cp[reference][0] == 10
owner_index, name_type_index = cp[reference][1:]
assert obj["className"](owner_index) == b"java/lang/System"
assert cp[name_type_index][0] == 12
name_index, descriptor_index = cp[name_type_index][1:]
assert obj["utf"](name_index) == b"identityHashCode"
assert obj["utf"](descriptor_index) == b"(Ljava/lang/Object;)I"
assert obj["code"](methods[3]) is None

# Existing global binding17 is unchanged and exact; no new binding or dispatch
# case has been added to the interpreter.
assert 'bytes("identityHashCode")' in old_engine and 'return 17;' in old_engine
assert old_engine.count("nativeBinding == 17") == 1
assert engine.count("return 17;") == 1 and engine.count("nativeBinding == 17") == 1
assert b"identityHashCode" in function_image(engine, "_bootstrapSystem")

# Rebuild every ordered root leaf from materialized source, including constants
# that are prehashed in Solidity. Use pinned local Ethereum Keccak, not SHA3.
node = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const k=b=>keccak256(Buffer.from(b,"hex"));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const hashes=x.images.map(v=>v===null?null:k(v));for(let i=0;i<hashes.length;i++)if(x.prehashed[i])hashes[i]=x.prehashed[i];const enc=Buffer.concat([Buffer.from(keccak256(x.domain),"hex"),w(64),w(hashes.length),...hashes.map(h=>Buffer.from(h,"hex"))]);process.stdout.write(JSON.stringify({hashes,root:keccak256(enc)}));'''
env = {**os.environ, "NODE_PATH": str(root / "jvmevm/runtime/node_modules")}
assert (root / "jvmevm/runtime/node_modules/js-sha3").is_dir()

def root_for(source):
    rows = {int(index): rhs.strip() for index, rhs in re.findall(
        r"h\[(\d+)\]\s*=\s*([^;]+);", function_block(source, "_bootstrapRoot"))}
    assert set(rows) == set(range(97))
    constants = {name: value.strip() for name, value in re.findall(
        r"bytes32 private constant (DBOOT_[A-Z_]+)\s*=\s*([^;]+);", source)}
    images, prehashed = [], [None] * 97
    names = []
    for index in range(97):
        rhs = rows[index]
        call = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
        constant = re.fullmatch(r"(DBOOT_[A-Z_]+)", rhs)
        assert bool(call) != bool(constant), (index, rhs)
        if call:
            name = call.group(1); image = function_image(source, name)
            images.append(image.hex()); names.append(name)
        else:
            name = constant.group(1); value = constants[name]
            digest = re.fullmatch(r'hex"([0-9a-f]{64})"', value)
            image_value = re.fullmatch(r'keccak256\(hex"([0-9a-f]+)"\)', value)
            assert bool(digest) != bool(image_value), (name, value[:96])
            if digest:
                images.append(None); prehashed[index] = digest.group(1); names.append(name)
            else:
                image = bytes.fromhex(image_value.group(1))
                images.append(image.hex()); names.append(name)
    data = {"domain": "JVMEVM:" + pins["domain"] + ":BOOTSTRAP:1",
            "images": images, "prehashed": prehashed}
    output = subprocess.run(["node", "-e", node], input=json.dumps(data), text=True,
                           cwd=root, env=env, capture_output=True, check=True)
    report = json.loads(output.stdout)
    assert len(report["hashes"]) == 97 and len(names) == 97
    return report, names

parent_root, parent_leaf_names = root_for(old_engine)
compiled_root, leaf_names = root_for(engine)
assert parent_root["root"] == pins["bootstrapRoot"]
assert parent_leaf_names == leaf_names
assert [i for i, (a, b) in enumerate(zip(parent_root["hashes"], compiled_root["hashes"])) if a != b] == [0]
assert compiled_root["hashes"][0] == subprocess.run(
    ["node", "-e", 'const {keccak256}=require("js-sha3");process.stdout.write(keccak256(Buffer.from(process.argv[1],"hex")))', new_image.hex()],
    cwd=root, env=env, text=True, capture_output=True, check=True).stdout

# The actual build pins are written by build.py after compilation. This
# pre-build verifier records the exact new leaf/root and unchanged boundaries.
report = {
    "result": "PASS", "basis": "accepted independent P12 parent-cd8122975",
    "acceptedEngineSourceSHA256": pins["engineSourceSHA256"],
    "candidateEngineSourceSHA256": file_sha(stage / "engine/MCEntryInterpreter.sol"),
    "normalizedByteExactToP12ExceptObjectImage": True,
    "bootstrapCount": 97, "changedBootstrapIndices": [0],
    "unchangedOtherBootstrapImages": 96,
    "objectImageBytes": len(new_image), "objectImageSHA256": sha(new_image),
    "objectImageKeccak256": compiled_root["hashes"][0],
    "objectSourceSHA256": file_sha(stage / "bootstrap/java/lang/Object.java"),
    "bootstrapRoot": compiled_root["root"], "acceptedP12BootstrapRoot": parent_root["root"],
    "materializedRootLeavesChecked": 97,
    "globalNativeBindings": 21, "stringLocalBinding": 12,
    "rawLimits": [71, 471911], "diagnosticClassBound": 168,
    "checkpointCap": 1048576, "headCap": 32768, "reserve": 25000000,
    "ordinaryGas": 1000000000, "runtimeCapBytes": 393216,
    "maxFrames": 128, "exceptionKinds": 14,
    "identityHashCodeBinding17Preserved": True,
    "packedFloatAndSparseCodecSourceByteExact": True,
    "newObjectHashCode": "public instance ordinary Code: System.identityHashCode(this)",
}

if __import__("sys").argv[1:] == ["--built"]:
    build_pins = json.loads((stage / "build-pins.json").read_text())
    p12_coord = p12_coord_path.read_text()
    p12_driver_text = p12_driver.read_text()
    candidate_engine = json.loads(json.dumps(build_pins["engine"]))
    candidate_coord = json.loads(json.dumps(build_pins["coordinator"]))
    assert candidate_engine["bytes"] <= pins["runtimeCap"]
    assert build_pins["bootstrapRoot"] == compiled_root["root"]
    assert build_pins["changedBootstrapIndices"] == [0]
    assert build_pins["unchangedOtherBootstrapImages"] == 96
    assert build_pins["globalNativeBindings"] == pins["globalNativeBindings"]
    assert build_pins["stringLocalBinding"] == pins["stringLocalBinding"]
    assert build_pins["rawLimits"] == pins["rawLimits"]
    assert build_pins["diagnosticClassBound"] == pins["diagnosticClassBound"]
    assert build_pins["ordinaryGas"] == pins["ordinaryGas"]
    assert build_pins["runtimeCap"] == pins["runtimeCap"]
    assert build_pins["address"] == pins["engineAddress"]
    assert build_pins["owner"] == pins["ownerAddress"]
    assert build_pins["compiler"] == pins["compiler"]
    assert build_pins["sourceVerification"]["bootstrapRoot"] == compiled_root["root"]
    old_engine_keccak = pins["engineRuntimeKeccak256"]
    expected_coordinator = p12_coord.replace(
        old_engine_keccak, candidate_engine["runtimeKeccak256"]
    )
    assert p12_coord.count(old_engine_keccak) == 1
    assert (stage / "coordinator/MCEntryCoordinator.sol").read_text() == expected_coordinator
    expected_driver = p12_driver_text
    for old, new in (
        (pins["engineRuntimeSHA256"], candidate_engine["runtimeSHA256"]),
        ("0x" + old_engine_keccak, "0x" + candidate_engine["runtimeKeccak256"]),
        ("0x" + pins["coordinatorRuntimeKeccak256"],
         "0x" + candidate_coord["runtimeKeccak256"]),
    ):
        assert expected_driver.count(old) == 1
        expected_driver = expected_driver.replace(old, new)
    for pattern, replacement in (
        (r"len\(engineRun\) != " + str(pins["engineBytes"]),
         "len(engineRun) != %d" % candidate_engine["bytes"]),
        (r"len\(run\) != " + str(pins["engineBytes"]),
         "len(run) != %d" % candidate_engine["bytes"]),
    ):
        expected_driver, changed = re.subn(pattern, replacement, expected_driver)
        assert changed == 1
    assert (stage / "tools/Go.txt").read_text() == expected_driver
    report["candidateEngineRuntimeBytes"] = candidate_engine["bytes"]
    report["candidateEngineRuntimeSHA256"] = candidate_engine["runtimeSHA256"]
    report["candidateEngineRuntimeKeccak256"] = candidate_engine["runtimeKeccak256"]
    report["candidateCoordinatorRuntimeBytes"] = candidate_coord["bytes"]
    report["candidateCoordinatorRuntimeSHA256"] = candidate_coord["runtimeSHA256"]
    report["candidateCoordinatorRuntimeKeccak256"] = candidate_coord["runtimeKeccak256"]
    report["candidateDriverSHA256"] = file_sha(stage / "tools/Go.txt")
    report["p12CoordinatorNormalizedToCandidateEnginePin"] = True
    report["p12CanonicalDriverNormalizedToCandidateBuildPins"] = True
elif __import__("sys").argv[1:]:
    raise SystemExit("usage: verify_source.py [--built]")

(stage / "results").mkdir(exist_ok=True)
(stage / "results/source-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
