#!/usr/bin/env python3
"""Rebuild and prove the append-only Java 8 HashMap() P35 source delta."""
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
BASE = ROOT / "evidence/java-evm/minecraft-entry/performance-base-p34"
PINS = json.loads((STAGE / "pins.json").read_text())
JDK = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JDK / "bin/javac"
JAVA = JDK / "bin/java"
RTJAR = JDK / "jre/lib/rt.jar"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def keccak(data: bytes) -> str:
    env = dict(os.environ, NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    return subprocess.check_output(
        ["node", "-e", "const{keccak256}=require('js-sha3');process.stdout.write(keccak256(Buffer.from(process.argv[1],'hex')));", data.hex()],
        cwd=ROOT, env=env, text=True,
    ).strip()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (count, old[:140])
    return text.replace(old, new, 1)


def u2(data: bytes, at: int) -> int:
    return struct.unpack_from(">H", data, at)[0]


def u4(data: bytes, at: int) -> int:
    return struct.unpack_from(">I", data, at)[0]


def parse_hashmap_class(data: bytes) -> dict[str, object]:
    """Minimal exact parser for class structure, fields, methods and ConstantValue."""
    assert data[:8] == bytes.fromhex("cafebabe00000034"), "HashMap image must be Java 8 version 52"
    at = 8
    cp_count = u2(data, at)
    at += 2
    cp: list[object | None] = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = data[at]
        at += 1
        if tag == 1:
            length = u2(data, at)
            at += 2
            cp[i] = data[at:at + length].decode("utf-8")
            at += length
        elif tag in (3, 4):
            cp[i] = (tag, data[at:at + 4])
            at += 4
        elif tag in (5, 6):
            cp[i] = (tag, data[at:at + 8])
            at += 8
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = (tag, u2(data, at))
            at += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (tag, u2(data, at), u2(data, at + 2))
            at += 4
        elif tag == 15:
            cp[i] = (tag, data[at], u2(data, at + 1))
            at += 3
        else:
            raise AssertionError(f"unsupported classfile constant-pool tag {tag}")
        i += 1

    def utf(index: int) -> str:
        value = cp[index]
        assert isinstance(value, str), (index, value)
        return value

    def class_name(index: int) -> str:
        value = cp[index]
        assert isinstance(value, tuple) and value[0] == 7
        return utf(value[1])

    def member_ref(index: int) -> tuple[str, str, str, int]:
        value = cp[index]
        assert isinstance(value, tuple) and value[0] in (9, 10, 11), (index, value)
        owner = class_name(value[1])
        nt = cp[value[2]]
        assert isinstance(nt, tuple) and nt[0] == 12
        return owner, utf(nt[1]), utf(nt[2]), value[0]

    access = u2(data, at)
    this_index, super_index = u2(data, at + 2), u2(data, at + 4)
    at += 6
    interface_count = u2(data, at)
    at += 2
    interfaces = [class_name(u2(data, at + 2 * n)) for n in range(interface_count)]
    at += interface_count * 2

    fields: dict[tuple[str, str], dict[str, object]] = {}
    field_count = u2(data, at)
    at += 2
    for _ in range(field_count):
        field_access, name_index, desc_index = u2(data, at), u2(data, at + 2), u2(data, at + 4)
        at += 6
        attr_count = u2(data, at)
        at += 2
        constant = None
        for _ in range(attr_count):
            attr_name = utf(u2(data, at))
            length = u4(data, at + 2)
            start = at + 6
            payload = data[start:start + length]
            if attr_name == "ConstantValue":
                assert length == 2
                constant = u2(payload, 0)
            at = start + length
        key = (utf(name_index), utf(desc_index))
        assert key not in fields
        fields[key] = {"access": field_access, "constant": constant}

    methods: dict[tuple[str, str], dict[str, object]] = {}
    method_count = u2(data, at)
    at += 2
    for _ in range(method_count):
        method_access, name_index, desc_index = u2(data, at), u2(data, at + 2), u2(data, at + 4)
        at += 6
        attr_count = u2(data, at)
        at += 2
        code = None
        for _ in range(attr_count):
            attr_name = utf(u2(data, at))
            length = u4(data, at + 2)
            start = at + 6
            if attr_name == "Code":
                code_length = u4(data, start + 4)
                code = data[start + 8:start + 8 + code_length]
                assert len(code) == code_length
            at = start + length
        key = (utf(name_index), utf(desc_index))
        assert key not in methods
        methods[key] = {"access": method_access, "code": code}

    attrs: dict[str, bytes] = {}
    attr_count = u2(data, at)
    at += 2
    for _ in range(attr_count):
        attr_name = utf(u2(data, at))
        length = u4(data, at + 2)
        start = at + 6
        attrs[attr_name] = data[start:start + length]
        at = start + length
    assert at == len(data), f"unexpected {len(data) - at} trailing classfile bytes"

    class_signature = None
    if "Signature" in attrs:
        assert len(attrs["Signature"]) == 2
        class_signature = utf(u2(attrs["Signature"], 0))
    return {
        "access": access,
        "name": class_name(this_index),
        "super": class_name(super_index),
        "interfaces": interfaces,
        "fields": fields,
        "methods": methods,
        "attrs": attrs,
        "signature": class_signature,
        "cp": cp,
        "utf": utf,
        "member_ref": member_ref,
    }


def build_image() -> bytes:
    with tempfile.TemporaryDirectory(prefix="hashmap-p35-image-") as temp_name:
        temp = Path(temp_name)
        stripped = temp / "rt.jar"
        shutil.copyfile(RTJAR, stripped)
        subprocess.run(["zip", "-q", "-d", str(stripped), "java/util/HashMap.class"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = temp / "classes"
        output.mkdir()
        subprocess.run([str(JAVAC), "-g:none", "-bootclasspath", str(stripped), "-source", "8", "-target", "8",
                        "-d", str(output), str(STAGE / "bootstrap/java/util/HashMap.java")],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return (output / "java/util/HashMap.class").read_bytes()


def root_from_leaves(leaves: list[str]) -> str:
    assert len(leaves) == 101
    domain = bytes.fromhex(keccak(b"JVMEVM:MC-CHECKPOINT-2M-P34:BOOTSTRAP:1"))
    word = lambda n: n.to_bytes(32, "big")
    encoded = domain + word(64) + word(len(leaves)) + b"".join(bytes.fromhex(x) for x in leaves)
    return keccak(encoded)


def main() -> None:
    manifest = json.loads((BASE / "SOURCE_MANIFEST.json").read_text())
    assert manifest["sourceOnly"] and manifest["acceptedProfile"] == "MC-CHECKPOINT-2M-P34"
    for row in manifest["files"]:
        path = BASE / row["path"]
        if path.is_file():
            data = path.read_bytes()
            assert sha(data) == row["sha256"] and len(data) == row["bytes"], row["path"]
    base_pins = json.loads((BASE / "pins.json").read_text())
    assert base_pins["profile"] == "MC-CHECKPOINT-2M-P34" and base_pins["bootstrapCount"] == 100
    base_engine = (BASE / "engine/MCEntryInterpreter.sol").read_text()
    base_coordinator = (BASE / "coordinator/MCEntryCoordinator.sol").read_text()
    assert sha(base_engine.encode()) == PINS["baseEngineSourceSHA256"]
    assert sha(base_coordinator.encode()) == PINS["baseCoordinatorSourceSHA256"]
    assert sha((BASE / "engine/build.js").read_bytes()) == PINS["baseEngineBuildSHA256"]
    assert sha((BASE / "coordinator/build.js").read_bytes()) == PINS["baseCoordinatorBuildSHA256"]

    image = build_image()
    assert len(image) == PINS["hashMapBootstrapBytes"]
    assert sha(image) == PINS["hashMapBootstrapSHA256"]
    image_hash = keccak(image)
    assert image_hash == PINS["hashMapBootstrapKeccak256"]
    if PINS.get("hashMapJavaSourceSHA256"):
        assert sha((STAGE / "bootstrap/java/util/HashMap.java").read_bytes()) == PINS["hashMapJavaSourceSHA256"]

    # Prove the exact source delta against the explicit frozen P34 snapshot.
    expected = base_engine
    expected = replace_once(expected,
        'bytes32 private constant DBOOT = keccak256("JVMEVM:MC-CHECKPOINT-2M-P34:BOOTSTRAP:1");',
        'bytes32 private constant DBOOT = keccak256("JVMEVM:MC-CHECKPOINT-2M-P34:BOOTSTRAP:1");\n'
        f'    bytes32 private constant DBOOT_HASHMAP = hex"{image_hash}";')
    expected = replace_once(expected,
        "        bytes32[] memory h = new bytes32[](100);",
        "        bytes32[] memory h = new bytes32[](101);")
    expected = replace_once(expected,
        "        // IdentityHashMap is the sole new image; every prior root slot is unchanged.\n"
        "        h[99] = keccak256(_bootstrapIdentityHashMap());\n"
        "        return keccak256(abi.encode(DBOOT, h));",
        "        // IdentityHashMap remains append-only image100; its existing root slot is unchanged.\n"
        "        h[99] = keccak256(_bootstrapIdentityHashMap());\n"
        "        // HashMap is append-only image101; every prior bootstrap leaf/order remains pinned.\n"
        "        h[100] = DBOOT_HASHMAP;\n"
        "        return keccak256(abi.encode(DBOOT, h));")
    expected = replace_once(expected,
        "uint256 count = inputCount + 94 + (suppliedObject ? 0 : 1)",
        "uint256 count = inputCount + 95 + (suppliedObject ? 0 : 1)")
    expected = replace_once(expected,
        '            || _isNamedClass(c, bytes("java/util/IdentityHashMap"));',
        '            || _isNamedClass(c, bytes("java/util/IdentityHashMap"))\n'
        '            || _isNamedClass(c, bytes("java/util/HashMap"));')
    expected = replace_once(expected,
        "        // IdentityHashMap appends as image100 without shifting any prior slot.\n"
        "        p.classes[classSlot + 60].data = _bootstrapIdentityHashMap();\n"
        "    }",
        "        // IdentityHashMap remains at image100 without shifting any prior slot.\n"
        "        p.classes[classSlot + 60].data = _bootstrapIdentityHashMap();\n"
        "        // HashMap is appended as image101, without shifting any accepted slot.\n"
        "        p.classes[classSlot + 61].data = _bootstrapHashMap();\n"
        "    }")
    hashmap_function = (
        "    /// @dev Java 8 HashMap constructor/state subset, image101; exact image generated by pinned JDK 8.\n"
        "    function _bootstrapHashMap() private pure returns (bytes memory) { return hex\""
        + image.hex() + "\"; }"
    )
    identity_function = re.search(
        r'    function _bootstrapIdentityHashMap\(\) private pure returns \(bytes memory\) \{ return hex"[0-9a-f]+"; \}',
        expected,
    )
    assert identity_function
    expected = replace_once(expected, identity_function.group(0), identity_function.group(0) + "\n\n\n" + hashmap_function)
    engine_path = STAGE / "engine/MCEntryInterpreter.sol"
    engine = engine_path.read_text()
    assert engine == expected, "engine changes exceed the exact append-only P34 HashMap source delta"

    coordinator_path = STAGE / "coordinator/MCEntryCoordinator.sol"
    coordinator = coordinator_path.read_text()
    expected_coordinator = replace_once(
        base_coordinator,
        f'bytes32 private constant ENGINE_CODEHASH = hex"{PINS["baseEngineRuntimeKeccak256"]}";',
        f'bytes32 private constant ENGINE_CODEHASH = hex"{PINS["engineRuntimeKeccak256"]}";'
    )
    assert coordinator == expected_coordinator, "coordinator may only pin the paired P35 engine codehash"

    # Every existing materialized bootstrap image stays byte-for-byte unchanged.
    image_re = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}'
    old_images = {name: bytes.fromhex(blob) for name, blob in re.findall(image_re, base_engine)}
    new_images = {name: bytes.fromhex(blob) for name, blob in re.findall(image_re, engine)}
    assert set(new_images) == set(old_images) | {"_bootstrapHashMap"}
    for name, old in old_images.items():
        assert new_images[name] == old, f"preexisting bootstrap bytes changed: {name}"
    assert new_images["_bootstrapHashMap"] == image

    # Old leaves are pinned in their exact old order; only the new final leaf is appended.
    old_leaves = base_pins["orderedBootstrapLeaves"]
    assert len(old_leaves) == 100 and old_leaves[-1] == PINS["baseIdentityHashMapKeccak256"]
    leaves = old_leaves + [image_hash]
    assert leaves[:100] == old_leaves
    root = root_from_leaves(leaves)
    assert root == PINS["bootstrapRoot"]
    assert base_pins["bootstrapRoot"] == PINS["baseBootstrapRoot"]
    assert len(leaves) == PINS["bootstrapCount"] == 101
    assert image_hash in engine and f'h[100] = DBOOT_HASHMAP;' in engine

    # Parse the exact class image and pin its Java 8 structural/behavioral contract.
    cls = parse_hashmap_class(image)
    assert cls["access"] == 0x0021
    assert cls["name"] == "java/util/HashMap"
    assert cls["super"] == "java/util/AbstractMap"
    assert cls["interfaces"] == ["java/util/Map", "java/lang/Cloneable", "java/io/Serializable"]
    assert cls["signature"] == (
        "<K:Ljava/lang/Object;V:Ljava/lang/Object;>Ljava/util/AbstractMap<TK;TV;>;"
        "Ljava/util/Map<TK;TV;>;Ljava/lang/Cloneable;Ljava/io/Serializable;"
    )
    fields = cls["fields"]
    expected_fields = {
        ("serialVersionUID", "J"): (0x001A, 0x0507DAC1C31660D1),
        ("DEFAULT_INITIAL_CAPACITY", "I"): (0x0018, 16),
        ("MAXIMUM_CAPACITY", "I"): (0x0018, 0x40000000),
        ("DEFAULT_LOAD_FACTOR", "F"): (0x0018, 0x3F400000),
        ("TREEIFY_THRESHOLD", "I"): (0x0018, 8),
        ("UNTREEIFY_THRESHOLD", "I"): (0x0018, 6),
        ("MIN_TREEIFY_CAPACITY", "I"): (0x0018, 64),
        ("table", "[Ljava/util/HashMap$Node;"): (0x0080, None),
        ("entrySet", "Ljava/util/Set;"): (0x0080, None),
        ("size", "I"): (0x0080, None),
        ("modCount", "I"): (0x0080, None),
        ("threshold", "I"): (0x0000, None),
        ("loadFactor", "F"): (0x0010, None),
    }
    assert set(fields) == set(expected_fields), (set(fields) ^ set(expected_fields))
    for key, (want_access, want_value) in expected_fields.items():
        field = fields[key]
        assert field["access"] == want_access, (key, field)
        if want_value is None:
            assert field["constant"] is None, (key, field)
        else:
            constant_index = field["constant"]
            cp = cls["cp"][constant_index]
            assert isinstance(cp, tuple) and cp[0] == (5 if key[1] == "J" else 4 if key[1] == "F" else 3)
            raw = int.from_bytes(cp[1], "big")
            assert raw == want_value, (key, hex(raw), hex(want_value))
    methods = cls["methods"]
    expected_native = {
        ("containsKey", "(Ljava/lang/Object;)Z"),
        ("containsValue", "(Ljava/lang/Object;)Z"),
        ("get", "(Ljava/lang/Object;)Ljava/lang/Object;"),
        ("put", "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;"),
        ("putAll", "(Ljava/util/Map;)V"),
        ("remove", "(Ljava/lang/Object;)Ljava/lang/Object;"),
        ("clear", "()V"),
        ("keySet", "()Ljava/util/Set;"),
        ("values", "()Ljava/util/Collection;"),
        ("entrySet", "()Ljava/util/Set;"),
        ("equals", "(Ljava/lang/Object;)Z"),
        ("hashCode", "()I"),
        ("clone", "()Ljava/lang/Object;"),
        ("getOrDefault", "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;"),
        ("forEach", "(Ljava/util/function/BiConsumer;)V"),
        ("replaceAll", "(Ljava/util/function/BiFunction;)V"),
        ("putIfAbsent", "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;"),
        ("remove", "(Ljava/lang/Object;Ljava/lang/Object;)Z"),
        ("replace", "(Ljava/lang/Object;Ljava/lang/Object;Ljava/lang/Object;)Z"),
        ("replace", "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;"),
        ("computeIfAbsent", "(Ljava/lang/Object;Ljava/util/function/Function;)Ljava/lang/Object;"),
        ("computeIfPresent", "(Ljava/lang/Object;Ljava/util/function/BiFunction;)Ljava/lang/Object;"),
        ("compute", "(Ljava/lang/Object;Ljava/util/function/BiFunction;)Ljava/lang/Object;"),
        ("merge", "(Ljava/lang/Object;Ljava/lang/Object;Ljava/util/function/BiFunction;)Ljava/lang/Object;"),
    }
    native = {key for key, method in methods.items() if method["access"] & 0x0100}
    concrete = {key for key, method in methods.items() if method["code"] is not None}
    assert native == expected_native, native ^ expected_native
    assert concrete == {("<init>", "()V"), ("size", "()I"), ("isEmpty", "()Z")}, concrete
    assert all(method["code"] is None for key, method in methods.items() if key in native)
    assert "<clinit>" not in {name for name, _ in methods}
    assert "InnerClasses" in cls["attrs"]

    ctor = methods[("<init>", "()V")]["code"]
    size = methods[("size", "()I")]["code"]
    empty = methods[("isEmpty", "()Z")]["code"]
    assert isinstance(ctor, bytes) and isinstance(size, bytes) and isinstance(empty, bytes)
    assert ctor[0] == 0x2A and ctor[1] == 0xB7
    parent_ref = cls["member_ref"](u2(ctor, 2))
    assert parent_ref == ("java/util/AbstractMap", "<init>", "()V", 10)
    assert ctor[4] == 0x2A and ctor[5] == 0x12
    float_cp = cls["cp"][ctor[6]]
    assert isinstance(float_cp, tuple) and float_cp == (4, bytes.fromhex("3f400000"))
    assert ctor[7] == 0xB5 and cls["member_ref"](u2(ctor, 8)) == (
        "java/util/HashMap", "loadFactor", "F", 9)
    assert ctor[-1] == 0xB1 and 0xBC not in ctor and 0xBD not in ctor and 0xBB not in ctor
    assert size[0] == 0x2A and size[1] == 0xB4 and cls["member_ref"](u2(size, 2)) == (
        "java/util/HashMap", "size", "I", 9) and size[-1] == 0xAC
    assert empty[0] == 0x2A and empty[1] == 0xB4 and cls["member_ref"](u2(empty, 2)) == (
        "java/util/HashMap", "size", "I", 9)
    assert empty[4:] == bytes.fromhex("9a000704a7000403ac")

    # The JDK 8 reflection oracle checks the real constructor's private state; no server/original code is loaded.
    javac_version = subprocess.check_output([str(JAVAC), "-version"], text=True, stderr=subprocess.STDOUT).strip()
    with tempfile.TemporaryDirectory(prefix="hashmap-p35-oracle-") as temp_name:
        temp = Path(temp_name)
        subprocess.run([str(JAVAC), "-source", "8", "-target", "8", "-d", str(temp),
                        str(STAGE / "tools/HashMapJdk8ReflectionOracle.java")],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        oracle = subprocess.check_output([str(JAVA), "-cp", str(temp), "HashMapJdk8ReflectionOracle"], text=True)
    pinned_oracle = (STAGE / "jdk8-reflection-oracle.txt").read_text()
    assert oracle == pinned_oracle
    assert sha(oracle.encode()) == PINS["jdk8OracleSHA256"]

    print(json.dumps({
        "status": "PASS",
        "baseline": "authorized P34 source snapshot",
        "unchangedPriorBootstrapImages": len(old_images),
        "bootstrapCount": len(leaves),
        "bootstrapRoot": root,
        "hashMap": {"binaryName": cls["name"], "bytes": len(image), "sha256": sha(image), "keccak256": image_hash,
                    "super": cls["super"], "interfaces": cls["interfaces"], "nativeRefusals": len(native)},
        "jdk8OracleSHA256": sha(oracle.encode()),
        "jdk8Compiler": javac_version,
        "engineSourceSHA256": sha(engine.encode()),
        "coordinatorSourceSHA256": sha(coordinator.encode()),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
