#!/usr/bin/env python3
"""Verify the one-image Java 8 Integer.rotateLeft change against accepted P14.

Only tracked generated sources and accepted P14 engine source are read. This
never opens any original Minecraft JAR/class/resource/world/checkpoint.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
p14 = stage.parent / "parent-8e40809d5"
base_stage = stage.parent / "integer-highest-one-bit-preflight"
DOMAIN = "MC-RANDOM-CLASS-P15"
ADDRESS = "0x4d432d52414e444f4d2d434c4153532d50310032"
OWNER = "0x4d432d52414e444f4d2d434c4153532d50310033"
BASE_SOURCE_SHA256 = "4edda4cdc6164e56f9d4318a5982f5051551223b543db5feb6243d393721ed75"
BASE_RAW_CLASS_SHA256 = "5aecdfd705734accb46f71c9c242673ee739c8cf0a582b35ae2e1121ee15948f"
BASE_IMAGE_SHA256 = "5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd"
BASE_IMAGE_BYTES = 2039
BASE_IMAGE_REMOVED_STACKMAP_BYTES = 61
INTEGER_RAW_CLASS_SHA256 = "b78cfcc5bc34fe9e968506ddd545c77690bedda5912d4ce6ad2619e1917e9a00"
INTEGER_IMAGE_SHA256 = "8c166273089342e5bd5fba6a6c79b861d2a823a8941307a71695374b510def22"
INTEGER_IMAGE_BYTES = 2087
INTEGER_IMAGE_REMOVED_STACKMAP_BYTES = 61
P14_ROOT = "933655dee86af8a5b7e05a0664ae62cd37b8db830f5b4525198ff09d4b33064f"
P14_ENGINE_SHA256 = "405da4cd752973ff9ead61294a89931b703b8deee14fcce85a248076b38ccaa6"
P14_COORDINATOR_SHA256 = "82b4d786a169c8b955521679a4f3f1e5678ab8306107de1c6478c5973f930846"
P14_DRIVER_SHA256 = "10ce9031d62b8fd4fce2f55c068bbaf0eccfe06960a8c562de7c76d00d079023"
P14_ENGINE_BUILD_SHA256 = "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d"
P14_COORDINATOR_BUILD_SHA256 = "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e"
NPM_PINS = {"package.json": "1befdd3ffec8f47c79d52e344a976b20d2187a8f69cd5f747a9ca3408c208d43",
            "package-lock.json": "93e057f7e9ac9f1c6bf43cb1aae4d7e62309b24dd51dfe0e07973264a2cf78be"}
ENGINE = {"bytes": 389579, "initSHA256": "bef5229c54dd97fbc71a786422857101ef2d8bb1226ae1bf13293b021173cc2a", "runtimeSHA256": "825a3b32880e297ffed17f6d07f82578dad2eb8fb8ded015ffa26e95d21568da", "runtimeKeccak256": "d913e77cfd7223b5de4cec5c37ae47d8360bd2e82bb9077ba3a7a4d54b3671f3"}
COORDINATOR = {"bytes": 5394, "initSHA256": "5d9de12d6d73759a4095e471afbef98a2710da6e1a812b98ff228179ac436b61", "runtimeSHA256": "9361ccd3e2ee3e0dad0c246180fca13b002c741ec15db1d09695e315435279f5", "runtimeKeccak256": "48666b2824cce6cfbc557ae3b87bc455d9a95bed8239eecbd39f87b72acf2729"}
PARENT_SOURCE_HASHES = {
    "artifacts/engine/MCEntryInterpreter.sol": P14_ENGINE_SHA256,
    "artifacts/coordinator/MCEntryCoordinator.sol": P14_COORDINATOR_SHA256,
    "canonical-driver.go.txt": P14_DRIVER_SHA256,
    "artifacts/engine/build.js": P14_ENGINE_BUILD_SHA256,
    "artifacts/coordinator/build.js": P14_COORDINATOR_BUILD_SHA256,
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def source_function(text, name):
    start = text.index("    function " + name + "(")
    end = text.find("\n    function ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def function_image(text, name):
    values = re.findall(r'hex"([0-9a-f]+)"', source_function(text, name))
    assert len(values) == 1, (name, len(values))
    return bytes.fromhex(values[0])


def keccak_hex(data_hex):
    node_path = os.environ.get("NODE_PATH", str(root / "jvmevm/runtime/node_modules"))
    script = 'const {keccak256}=require("js-sha3");process.stdout.write(keccak256(Buffer.from(process.argv[1],"hex")));'
    return subprocess.check_output(["node", "-e", script, data_hex], text=True,
                                   env={**os.environ, "NODE_PATH": node_path})


def root_commitment(domain, hashes):
    node_path = os.environ.get("NODE_PATH", str(root / "jvmevm/runtime/node_modules"))
    script = r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.hashes.length),...x.hashes.map(v=>Buffer.from(v,"hex"))]));process.stdout.write(JSON.stringify({domainHash:d,bootstrapRoot:r}));'''
    return json.loads(subprocess.check_output(["node", "-e", script], input=json.dumps({"domain": domain, "hashes": hashes}), text=True,
                                             env={**os.environ, "NODE_PATH": node_path}))


def leaves(source):
    root_start = source.index("    function _bootstrapRoot()")
    root_body = source[root_start:]
    root_body = root_body[:root_body.index("\n    function ", 1)]
    assignments = {int(index): rhs.strip() for index, rhs in re.findall(r"h\[(\d+)\]\s*=\s*([^;]+);", root_body)}
    assert set(assignments) == set(range(97)), (len(assignments), sorted(assignments))
    values = []
    for index in range(97):
        rhs = assignments[index]
        image_function = re.fullmatch(r"keccak256\((_bootstrap\w+)\(\)\)", rhs)
        if image_function:
            name = image_function.group(1)
            image = function_image(source, name)
            values.append((name.removeprefix("_bootstrap"), keccak_hex(image.hex())))
            continue
        assert re.fullmatch(r"DBOOT_[A-Z0-9_]+", rhs), (index, rhs)
        declaration = re.search(r"bytes32 private constant " + re.escape(rhs) + r"\s*=\s*([^;]+);", source)
        assert declaration, (index, rhs)
        expression = declaration.group(1).strip()
        literal = re.fullmatch(r'hex"([0-9a-f]+)"', expression)
        if literal:
            value = literal.group(1)
        else:
            image = re.fullmatch(r'keccak256\(hex"([0-9a-f]+)"\)', expression)
            assert image, (index, rhs, expression[:100])
            value = keccak_hex(image.group(1))
        assert len(value) == 64, (index, rhs, len(value))
        values.append((rhs, value))
    return values


assert len(sys.argv) == 2 and sys.argv[1] in ("--compute", "--check")
for relative, expected in PARENT_SOURCE_HASHES.items():
    assert file_sha(p14 / relative) == expected, relative
for relative, expected in NPM_PINS.items():
    assert file_sha(root / "jvmevm/runtime" / relative) == expected, relative
base_source_path = base_stage / "bootstrap/java/lang/Integer.java"
base_source = base_source_path.read_text()
assert file_sha(base_source_path) == BASE_SOURCE_SHA256
assert file_sha(stage / "tools/strip_stackmap.py") == "f23929307f6b2e4c7c568160133d122149543f0821c8d15cc4a39b19e3c9f8be"
base_java = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
base_javap = Path("/usr/lib/jvm/java-8-openjdk/bin/javap")
assert base_java.is_file() and base_javap.is_file()
spec_source = """  public static int rotateLeft(int i, int distance) {
    return (i << distance) | (i >>> -distance);
  }
"""
candidate_source = (stage / "bootstrap/java/lang/Integer.java").read_text()
assert base_source.endswith("}\n")
assert candidate_source == base_source[:-2] + spec_source + "}\n"
assert candidate_source.count("rotateLeft") == 1

# Verify the pre-edit source image first: compile the accepted Integer source with
# the pinned Java 8 compiler, remove only its existing Code-local StackMapTable,
# and compare every remaining byte against accepted P14 bootstrap index70.
p14_engine = (p14 / "artifacts/engine/MCEntryInterpreter.sol").read_text()
p14_integer = function_image(p14_engine, "_bootstrapInteger")
assert len(p14_integer) == BASE_IMAGE_BYTES and sha(p14_integer) == BASE_IMAGE_SHA256
strip_spec = __import__("importlib.util").util.spec_from_file_location("rotate_strip_stackmap", stage / "tools/strip_stackmap.py")
strip_module = __import__("importlib.util").util.module_from_spec(strip_spec); strip_spec.loader.exec_module(strip_module)
(root / "build").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="mc-rotate-left-java8-image-", dir=root / "build") as temporary:
    work = Path(temporary); before_classes = work / "before"; after_classes = work / "after"
    before_classes.mkdir(); after_classes.mkdir()
    subprocess.run([base_java, "-source", "8", "-target", "8", "-g:none", "-d", before_classes, base_source_path], cwd=root, check=True)
    before_raw = (before_classes / "java/lang/Integer.class").read_bytes()
    before_image, before_removed = strip_module.strip_stackmap(before_raw)
    assert before_image == p14_integer, "pre-change compiled Java8 Integer must byte-match accepted P14 image70"
    assert len(before_raw) == 2100 and sha(before_raw) == BASE_RAW_CLASS_SHA256
    assert before_removed == BASE_IMAGE_REMOVED_STACKMAP_BYTES
    subprocess.run([base_java, "-source", "8", "-target", "8", "-g:none", "-d", after_classes, stage / "bootstrap/java/lang/Integer.java"], cwd=root, check=True)
    candidate_raw = (after_classes / "java/lang/Integer.class").read_bytes()
    candidate_image, removed = strip_module.strip_stackmap(candidate_raw)
    verbose = subprocess.check_output([base_javap, "-verbose", after_classes / "java/lang/Integer.class"], text=True)
assert len(candidate_raw) == 2148 and sha(candidate_raw) == INTEGER_RAW_CLASS_SHA256
assert removed == INTEGER_IMAGE_REMOVED_STACKMAP_BYTES
assert len(candidate_image) == INTEGER_IMAGE_BYTES and sha(candidate_image) == INTEGER_IMAGE_SHA256
assert (stage / "bootstrap/java/lang/Integer.class.hex").read_text().strip() == candidate_image.hex()
method = verbose.split("public static int rotateLeft(int, int);", 1)[1].split("public int compareTo(java.lang.Object);", 1)[0]
for token in ("descriptor: (II)I", "flags: ACC_PUBLIC, ACC_STATIC", "ishl", "ineg", "iushr", "ior", "ireturn"):
    assert token in method, token
for token in ("ishl", "ineg", "iushr", "ior", "ireturn"):
    assert method.count(token) == 1, (token, method.count(token))
assert "ishr" not in method and "lshl" not in method and "lushr" not in method

p14_leaves = leaves(p14_engine)
assert root_commitment("MC-RANDOM-CLASS-P14", [value for _, value in p14_leaves])["bootstrapRoot"] == P14_ROOT
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
old_literal = 'return hex"' + p14_integer.hex() + '";'
new_literal = 'return hex"' + candidate_image.hex() + '";'
assert p14_engine.count(old_literal) == 1
expected_engine = p14_engine.replace("MC-RANDOM-CLASS-P14", DOMAIN)
assert expected_engine.count("MC-RANDOM-CLASS-P15") == 9
expected_engine = expected_engine.replace(old_literal, new_literal)
assert engine == expected_engine, "engine may change only profile domain and Integer image70"
p14_values = [value for _, value in p14_leaves]
current_leaves = leaves(engine)
current_values = [value for _, value in current_leaves]
assert [i for i, (old, new) in enumerate(zip(p14_values, current_values)) if old != new] == [70]
assert current_leaves[0][0] == "Object" and current_values[0] == p14_values[0]
assert current_leaves[70] == ("Integer", keccak_hex(candidate_image.hex()))
calculated_root = root_commitment(DOMAIN, current_values)
root_record = {
    "schema": 1, "basis": "parent-8e40809d5", "domain": DOMAIN,
    "order": [name for name, _ in current_leaves], "keccak256": current_values,
    "integer": {"slot": 70, "bytes": len(candidate_image), "sha256": sha(candidate_image), "keccak256": current_leaves[70][1]},
    **calculated_root,
}
if sys.argv[1] == "--check":
    expected_root = json.loads((stage / "root-commitment.json").read_text())
    assert expected_root == root_record
    pins = json.loads((stage / "build-pins.json").read_text())
    assert pins["bootstrapRoot"] == calculated_root["bootstrapRoot"]
    assert pins["domain"] == DOMAIN and pins["basis"] == "parent-8e40809d5"
    assert pins["changedBootstrapIndices"] == [70] and pins["unchangedOtherBootstrapImages"] == 96
    assert pins["integer"] == root_record["integer"]
    assert pins["object"] == {"slot": 0, "bytes": len(function_image(p14_engine, "_bootstrapObject")),
                               "sha256": sha(function_image(p14_engine, "_bootstrapObject")), "keccak256": p14_values[0]}
    assert pins["rawLimits"] == [71, 471911] and pins["diagnosticClassBound"] == 168
    assert pins["globalNativeBindings"] == 21 and pins["stringLocalBinding"] == 12
    assert pins["exceptionKinds"] == 14 and pins["maxFrames"] == 128
    assert pins["checkpointCap"] == 1048576 and pins["headCap"] == 32768 and pins["reserve"] == 25_000_000
    assert pins["ordinaryGas"] == 1_000_000_000 and pins["runtimeCap"] == 393216
    assert pins["address"] == ADDRESS and pins["owner"] == OWNER
    assert pins["engine"] == ENGINE and pins["coordinator"] == COORDINATOR
    coordinator_source = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
    p14_coordinator = (p14 / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
    expected_coordinator = p14_coordinator.replace("MC-RANDOM-CLASS-P14", DOMAIN)
    expected_coordinator = expected_coordinator.replace("4d432d52414e444f4d2d434c4153532d50310030", ADDRESS[2:])
    expected_coordinator = expected_coordinator.replace("c795b8394fd59085132e60149c6a4269f5d0dd6fd0fce87d24c21c5fceafbce6", ENGINE["runtimeKeccak256"])
    assert coordinator_source == expected_coordinator
    p14_pins = json.loads((p14 / "artifacts/parent-build-pins.json").read_text())
    driver = (stage / "tools/Go.txt").read_text()
    expected_driver = (p14 / "canonical-driver.go.txt").read_text().replace("MC-RANDOM-CLASS-P14", DOMAIN)
    expected_driver = expected_driver.replace(p14_pins["address"], ADDRESS).replace(p14_pins["owner"], OWNER)
    for name, value in (("immutableEngineSHA256", ENGINE["runtimeSHA256"]),
                        ("immutableEngineKeccak", "0x" + ENGINE["runtimeKeccak256"]),
                        ("immutableCoordinatorKeccak", "0x" + COORDINATOR["runtimeKeccak256"])):
        expected_driver, count = re.subn(r"(const " + name + r" = \")[^\"]+(\"\n)", r"\g<1>" + value + r"\g<2>", expected_driver)
        assert count == 1, name
    for name, value in (("engineRun", ENGINE["bytes"]), ("coordRun", COORDINATOR["bytes"]), ("run", ENGINE["bytes"])):
        expected_driver, count = re.subn(r"(len\(" + name + r"\) != )\d+", r"\g<1>" + str(value), expected_driver)
        assert count == 1, name
    assert driver == expected_driver
    for relative, expected in (("engine/build.js", P14_ENGINE_BUILD_SHA256), ("coordinator/build.js", P14_COORDINATOR_BUILD_SHA256)):
        assert file_sha(stage / relative) == expected
    assert file_sha(stage / "tools/checkpoint_diagnostic.py") == "23cb8683a3bb831cc8dd1882dbeee5c4d676d143ec67204ead2e30d5be8d50ce"
    assert file_sha(stage / "tools/checkpoint_frames.py") == "ab4182dcdd5f9b1b82fed96315e746fb54ed082ab8e47bbcef0d5fa37410582e"
    assert file_sha(stage / "tools/verify_receipts.js") == "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df"
    assert not any(path.suffix in {".jar", ".zip", ".class"} for path in stage.rglob("*"))
print(json.dumps({"phase": "compute" if sys.argv[1] == "--compute" else "source-verified",
                  "domain": DOMAIN, "p14IntegerImageSHA256": BASE_IMAGE_SHA256,
                  "p14IntegerCompiledPrechangeByteMatch": True,
                  "integerImage": root_record["integer"], "root": calculated_root,
                  "materializedLeaves": len(current_leaves), "changedImageSlots": [70],
                  "runtime": ENGINE["bytes"]}, indent=2))
