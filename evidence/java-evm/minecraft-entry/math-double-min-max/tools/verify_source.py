#!/usr/bin/env python3
"""Prove the sole semantic delta is Java 8 guest Math.min/max(double)."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
PINS = json.loads((STAGE / "pins.json").read_text())
BASE_COMMIT = PINS["baseCommit"]
BASE_STAGE = "evidence/java-evm/minecraft-entry/identity-hash-map-int-constructor"
JDK = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JDK / "bin/javac"
RTJAR = JDK / "jre/lib/rt.jar"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{BASE_STAGE}/{path}"], cwd=ROOT)


def keccak(data: bytes) -> str:
    env = dict(os.environ, NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    return subprocess.check_output(
        ["node", "-e", "const {keccak256}=require('js-sha3');process.stdout.write(keccak256(Buffer.from(process.argv[1],'hex')));", data.hex()],
        cwd=ROOT, env=env, text=True,
    ).strip()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (count, old[:100])
    return text.replace(old, new, 1)


def parse_methods(data: bytes) -> dict[tuple[str, str], tuple[int, bytes | None]]:
    if data[:8] != bytes.fromhex("cafebabe00000034"):
        raise AssertionError("Math class is not Java 8 version 52")
    at = 8
    cp_count = struct.unpack_from(">H", data, at)[0]
    at += 2
    cp: list[object | None] = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = data[at]
        at += 1
        if tag == 1:
            length = struct.unpack_from(">H", data, at)[0]
            at += 2
            cp[i] = data[at:at + length].decode("utf-8")
            at += length
        elif tag in (3, 4):
            cp[i] = data[at:at + 4]
            at += 4
        elif tag in (5, 6):
            cp[i] = data[at:at + 8]
            at += 8
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = struct.unpack_from(">H", data, at)[0]
            at += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = struct.unpack_from(">HH", data, at)
            at += 4
        elif tag == 15:
            cp[i] = data[at:at + 3]
            at += 3
        else:
            raise AssertionError(f"unsupported Math constant-pool tag {tag}")
        i += 1

    at += 6  # access_flags, this_class, super_class
    interface_count = struct.unpack_from(">H", data, at)[0]
    at += 2 + interface_count * 2
    field_count = struct.unpack_from(">H", data, at)[0]
    at += 2
    for _ in range(field_count):
        at += 6
        attributes = struct.unpack_from(">H", data, at)[0]
        at += 2
        for _ in range(attributes):
            length = struct.unpack_from(">I", data, at + 2)[0]
            at += 6 + length

    methods: dict[tuple[str, str], tuple[int, bytes | None]] = {}
    method_count = struct.unpack_from(">H", data, at)[0]
    at += 2
    for _ in range(method_count):
        access, name_index, descriptor_index = struct.unpack_from(">HHH", data, at)
        at += 6
        name, descriptor = cp[name_index], cp[descriptor_index]
        attributes = struct.unpack_from(">H", data, at)[0]
        at += 2
        code = None
        for _ in range(attributes):
            name_index = struct.unpack_from(">H", data, at)[0]
            length = struct.unpack_from(">I", data, at + 2)[0]
            start = at + 6
            if cp[name_index] == "Code":
                code_length = struct.unpack_from(">I", data, start + 4)[0]
                code = data[start + 8:start + 8 + code_length]
            at = start + length
        key = (str(name), str(descriptor))
        assert key not in methods, key
        methods[key] = (access, code)
    return methods


assert BASE_COMMIT == "471d5bfaeb311598cde2e8b2372536af76d2be48"
base_engine = git_blob("engine/MCEntryInterpreter.sol").decode()
engine_path = STAGE / "engine/MCEntryInterpreter.sol"
engine = engine_path.read_text()
assert sha(base_engine.encode()) == PINS["baseEngineSourceSHA256"] == "039abb41a3c9ce6d6ed330449ba629ab8deb283a890be421f96ca8275fc48499"
base_coordinator = git_blob("coordinator/MCEntryCoordinator.sol").decode()
assert sha(base_coordinator.encode()) == PINS["baseCoordinatorSourceSHA256"]

# The exact Java image is rebuilt only by the pinned local JDK 8 compiler.
with tempfile.TemporaryDirectory(prefix="math-double-image-") as temp:
    temp = Path(temp)
    stripped = temp / "rt.jar"
    shutil.copyfile(RTJAR, stripped)
    subprocess.run(["zip", "-q", "-d", str(stripped), "java/lang/Math.class"],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = temp / "classes"
    output.mkdir()
    subprocess.run([str(JAVAC), "-g:none", "-bootclasspath", str(stripped), "-source", "8", "-target", "8",
                    "-d", str(output), str(STAGE / "bootstrap/java/lang/Math.java")],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    image = (output / "java/lang/Math.class").read_bytes()
assert len(image) == PINS["mathBootstrapBytes"]
assert sha(image) == PINS["mathBootstrapSHA256"]
assert keccak(image) == PINS["mathBootstrapKeccak256"]

old_match = re.search(r'function _bootstrapMath\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}', base_engine)
new_match = re.search(r'function _bootstrapMath\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}', engine)
assert old_match and new_match
old_image = bytes.fromhex(old_match.group(1))
assert sha(old_image) == PINS["baseMathBootstrapSHA256"]
assert bytes.fromhex(new_match.group(1)) == image

old_methods, new_methods = parse_methods(old_image), parse_methods(image)
assert set(old_methods).issubset(new_methods)
for key, old_method in old_methods.items():
    assert new_methods[key] == old_method, f"prior Math method bytecode/access changed: {key}"
added = set(new_methods) - set(old_methods)
assert added == {("min", "(DD)D"), ("max", "(DD)D")}, added
for key in added:
    access, code = new_methods[key]
    assert access == 0x0009 and code, (key, access, code)
old_native = {name for (name, desc), (access, code) in old_methods.items() if access & 0x0100}
new_native = {name for (name, desc), (access, code) in new_methods.items() if access & 0x0100}
assert old_native == new_native == {"sqrt", "sin", "asin", "cos"}

# All materialized append images except the measured Math image are identical.
def materialized_images(source: str) -> dict[str, bytes]:
    rows = re.findall(
        r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}',
        source,
    )
    return {name: bytes.fromhex(blob) for name, blob in rows}
base_images, current_images = materialized_images(base_engine), materialized_images(engine)
assert set(base_images) == set(current_images)
assert base_images["_bootstrapMath"] == old_image
assert current_images["_bootstrapMath"] == image
for name in base_images:
    if name != "_bootstrapMath":
        assert base_images[name] == current_images[name], name

old_hash = keccak(old_image)
new_hash = keccak(image)
expected_engine = replace_once(base_engine, f'bytes32 private constant DBOOT_MATH = hex"{old_hash}";',
                               f'bytes32 private constant DBOOT_MATH = hex"{new_hash}";')
expected_engine = replace_once(
    expected_engine,
    old_match.group(0),
    new_match.group(0),
)
assert engine == expected_engine, "engine differs beyond exact Math image and its actual root leaf"
assert f'bytes32 private constant DBOOT_MATH = hex"{new_hash}";' in engine
assert "h[89] = DBOOT_MATH;" in engine
assert "bytes32[] memory h = new bytes32[](100);" in engine
assert "p.classes[classSlot + 50].data = _bootstrapMath();" in engine
assert "MAX_RAW_CLASSES = 150" in engine and "MAX_RAW_BYTES = 1063930" in engine
assert "MAX_CHECKPOINT_BYTES = 1048576" in engine
assert "uint32(150), uint32(1063930)," in engine and "uint32(1048576)" in engine
assert PINS["bootstrapCount"] == 100 and PINS["globalNativeBindings"] == 21
assert PINS["stringLocalBinding"] == 12
assert PINS["runtimeCapBytes"] == PINS["checkpointCapBytes"] == 1048576
assert PINS["rawClassLimit"] == 150 and PINS["rawByteLimit"] == 1063930
assert PINS["newNativeBindings"] == 0
math_source = (STAGE / "bootstrap/java/lang/Math.java").read_text()
assert sha(math_source.encode()) == PINS["mathBootstrapJavaSourceSHA256"]
assert sha((STAGE / "fixtures/src/MathDoubleMinMax.template").read_bytes()) == PINS["mathFixtureTemplateSHA256"]
assert "if (a != a) return a;" in math_source and "if (b != b) return b;" in math_source
assert "if (1.0d / a < 0.0d) return a;" in math_source
assert "if (1.0d / b > 0.0d) return b;" in math_source
assert "public static double min(double a, double b)" in math_source
assert "public static double max(double a, double b)" in math_source
assert "Math.abs" not in math_source and "native double min" not in math_source and "native double max" not in math_source

# The coordinator has only the authenticated codehash refresh required by the
# newly compiled LOCAL engine; its ordinary CREATE transport is otherwise exact.
old_runtime_hash = PINS["baseEngineRuntimeKeccak256"]
expected_coordinator = replace_once(base_coordinator, old_runtime_hash, PINS["engineRuntimeKeccak256"])
coordinator = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
assert coordinator == expected_coordinator
assert sha(engine.encode()) == PINS["engineSourceSHA256"]
assert sha(coordinator.encode()) == PINS["coordinatorSourceSHA256"]

# Preserve every inherited Java bootstrap/tool fixture source other than the
# one explicit Math regression extension; new fixture source is append-only.
for folder in ("bootstrap/java/util", "bootstrap/stub"):
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE_COMMIT, f"{BASE_STAGE}/{folder}"], cwd=ROOT, text=True
    ).splitlines()
    for row in names:
        relative = row.removeprefix(f"{BASE_STAGE}/")
        assert (STAGE / relative).read_bytes() == git_blob(relative), relative
old_fixtures = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", BASE_COMMIT, f"{BASE_STAGE}/fixtures/src"], cwd=ROOT, text=True
).splitlines()
for row in old_fixtures:
    relative = row.removeprefix(f"{BASE_STAGE}/")
    if relative.endswith("fixtures/src/ArrayListMathObjectInteger.java"):
        old_fixture = git_blob(relative).decode()
        new_fixture = (STAGE / relative).read_text()
        expected_fixture = replace_once(
            old_fixture,
            '        if (Math.max(-42, 17) != 17 || Math.min(-42, 17) != -42) throw new AssertionError("Math max/min");',
            '        if (Math.max(-42, 17) != 17 || Math.min(-42, 17) != -42) throw new AssertionError("Math int max/min");\n'
            '        if (Double.doubleToRawLongBits(Math.sqrt(4.0d)) != 0x4000000000000000L) throw new AssertionError("Math.sqrt control");\n'
            '        if (Double.doubleToRawLongBits(Math.sin(0.0d)) != 0L) throw new AssertionError("Math.sin control");\n'
            '        if (Double.doubleToRawLongBits(Math.asin(0.0d)) != 0L) throw new AssertionError("Math.asin control");\n'
            '        if (Double.doubleToRawLongBits(Math.cos(0.0d)) != 0x3ff0000000000000L) throw new AssertionError("Math.cos control");',
        )
        assert new_fixture == expected_fixture
    else:
        assert (STAGE / relative).read_bytes() == git_blob(relative), relative

print(json.dumps({
    "baseCommit": BASE_COMMIT,
    "baseEngineSourceSHA256": sha(base_engine.encode()),
    "engineSourceSHA256": sha(engine.encode()),
    "mathClassBytes": len(image), "mathClassSHA256": sha(image),
    "mathClassKeccak256": new_hash, "priorMathMethodCodeIdentity": True,
    "newOrdinaryMethods": ["min(DD)D", "max(DD)D"],
    "newNativeBindings": 0, "materializedBootstrapCount": 100,
    "allOtherBootstrapImagesIdentical": True,
    "runtimeCapBytes": 1048576, "checkpointCapBytes": 1048576,
    "rawClassLimit": 150, "rawByteLimit": 1063930,
}, indent=2))
