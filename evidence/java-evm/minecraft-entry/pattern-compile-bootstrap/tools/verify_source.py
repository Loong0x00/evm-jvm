#!/usr/bin/env python3
"""Verify the append-only P36 Pattern compiler delta against only the P35 snapshot."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/pattern-source-base-p35"
PINS = json.loads((STAGE / "pins.json").read_text())
JDK = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JDK / "bin/javac"
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


def materialized_image(source: str, name: str) -> bytes:
    match = re.search(
        rf'function _bootstrap{name}\(\) private pure returns \(bytes memory\) \{{ return hex"([0-9a-f]+)"; \}}',
        source,
    )
    assert match, f"missing exact _bootstrap{name} materializer"
    return bytes.fromhex(match.group(1))


def build_images() -> dict[str, bytes]:
    assert JAVAC.is_file() and RTJAR.is_file(), "pinned JDK 8 is unavailable"
    with tempfile.TemporaryDirectory(prefix="pattern-p36-images-") as temp_name:
        temp = Path(temp_name)
        stripped = temp / "rt.jar"
        shutil.copyfile(RTJAR, stripped)
        subprocess.run(
            ["zip", "-q", "-d", str(stripped), "java/util/regex/Pattern.class",
             "java/util/regex/PatternSyntaxException.class"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output = temp / "classes"
        output.mkdir()
        subprocess.run(
            [str(JAVAC), "-g:none", "-bootclasspath", str(stripped), "-source", "8", "-target", "8",
             "-d", str(output), str(STAGE / "bootstrap/java/util/regex/Pattern.java"),
             str(STAGE / "bootstrap/java/util/regex/PatternSyntaxException.java")],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        return {
            "Pattern": (output / "java/util/regex/Pattern.class").read_bytes(),
            "PatternSyntaxException": (output / "java/util/regex/PatternSyntaxException.class").read_bytes(),
        }


def expected_engine(base: str, pattern_bytes: bytes, syntax_bytes: bytes) -> str:
    expected = base.replace("JVMEVM:MC-HASHMAP-DEFAULT-P35", "JVMEVM:MC-PATTERN-COMPILE-P36")
    assert expected != base
    expected = replace_once(expected, "bytes32[] memory h = new bytes32[](101);",
                            "bytes32[] memory h = new bytes32[](103);")
    expected = replace_once(
        expected,
        "        h[100] = DBOOT_HASHMAP;\n        return keccak256(abi.encode(DBOOT, h));",
        "        h[100] = DBOOT_HASHMAP;\n"
        "        // Pattern compiler and syntax exception append after every prior image.\n"
        "        h[101] = keccak256(_bootstrapPattern());\n"
        "        h[102] = keccak256(_bootstrapPatternSyntaxException());\n"
        "        return keccak256(abi.encode(DBOOT, h));",
    )
    expected = replace_once(expected, "uint256 count = inputCount + 95 + (suppliedObject ? 0 : 1)",
                            "uint256 count = inputCount + 97 + (suppliedObject ? 0 : 1)")
    expected = replace_once(
        expected,
        "                || _isReservedLocaleClass(users[i])\n"
        "                || _isNamedClass(users[i], bytes(\"java/util/Random\"))) {",
        "                || _isReservedLocaleClass(users[i]) || _isReservedRegexClass(users[i])\n"
        "                || _isNamedClass(users[i], bytes(\"java/util/Random\"))) {",
    )
    expected = replace_once(
        expected,
        "    function _isReservedSystemClass(ClassInfo memory c) private pure returns (bool) {",
        "    function _isReservedRegexClass(ClassInfo memory c) private pure returns (bool) {\n"
        "        return _isNamedClass(c, bytes(\"java/util/regex/Pattern\"))\n"
        "            || _isNamedClass(c, bytes(\"java/util/regex/PatternSyntaxException\"));\n"
        "    }\n\n"
        "    function _isReservedSystemClass(ClassInfo memory c) private pure returns (bool) {",
    )
    expected = replace_once(
        expected,
        "        // HashMap is appended as image101, without shifting any accepted slot.\n"
        "        p.classes[classSlot + 61].data = _bootstrapHashMap();",
        "        // HashMap remains image101; Pattern and its syntax exception append after it.\n"
        "        p.classes[classSlot + 61].data = _bootstrapHashMap();\n"
        "        p.classes[classSlot + 62].data = _bootstrapPattern();\n"
        "        p.classes[classSlot + 63].data = _bootstrapPatternSyntaxException();",
    )
    old_close = "\n}\n"
    assert expected.endswith(old_close)
    expected = expected[:-len(old_close)] + "\n\n"
    expected += "    /// @dev Append-only genuine Java 8 Pattern compiler image.\n"
    expected += "    function _bootstrapPattern() private pure returns (bytes memory) { return hex\"" + pattern_bytes.hex() + "\"; }\n"
    expected += "    /// @dev Append-only genuine Java 8 PatternSyntaxException compiler image.\n"
    expected += "    function _bootstrapPatternSyntaxException() private pure returns (bytes memory) { return hex\"" + syntax_bytes.hex() + "\"; }\n}\n"
    return expected


def main() -> None:
    manifest_path = BASE / "SOURCE_MANIFEST.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert sha(manifest_bytes) == PINS["sourceBase"]["sourceManifestSHA256"]
    assert manifest["sourceOnly"] is True
    assert manifest["noOriginalJarClassesResourcesWorldsCheckpointsReceiptsOrBindingLists"] is True
    assert manifest["acceptedSourceCommit"] == PINS["sourceBase"]["acceptedSourceCommit"]
    assert manifest["profile"] == PINS["sourceBase"]["profile"]
    for row in manifest["files"]:
        path = BASE / row["path"]
        assert path.is_file(), row["path"]
        data = path.read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]

    base_pins = json.loads((BASE / "pins.json").read_text())
    assert base_pins["profile"] == "MC-HASHMAP-DEFAULT-P35"
    assert base_pins["bootstrapCount"] == 101
    assert base_pins["bootstrapRoot"] == PINS["sourceBase"]["bootstrapRoot"]
    base_engine_path = BASE / "engine/MCEntryInterpreter.sol"
    base_coord_path = BASE / "coordinator/MCEntryCoordinator.sol"
    base_engine = base_engine_path.read_text()
    base_coord = base_coord_path.read_text()
    assert sha(base_engine_path.read_bytes()) == PINS["sourceBase"]["engineSourceSHA256"]
    assert sha(base_coord_path.read_bytes()) == PINS["sourceBase"]["coordinatorSourceSHA256"]
    assert sha((BASE / "engine/build.js").read_bytes()) == sha((STAGE / "engine/build.js").read_bytes())
    assert sha((BASE / "coordinator/build.js").read_bytes()) == sha((STAGE / "coordinator/build.js").read_bytes())

    images = build_images()
    expected_image_pins = {row["binaryName"].rsplit(".", 1)[-1]: row for row in PINS["bootstrap"]["newImages"]}
    current_engine = (STAGE / "engine/MCEntryInterpreter.sol").read_text()
    for name, image in images.items():
        row = expected_image_pins[name]
        assert len(image) == row["bytes"] and sha(image) == row["sha256"] and keccak(image) == row["keccak256"]
        assert materialized_image(current_engine, name) == image, f"{name} materializer differs from fresh Java 8 classfile"
    assert sha((STAGE / "bootstrap/java/util/regex/Pattern.java").read_bytes()) == PINS["patternSourceSHA256"]
    assert sha((STAGE / "bootstrap/java/util/regex/PatternSyntaxException.java").read_bytes()) == PINS["patternSyntaxExceptionSourceSHA256"]

    expected = expected_engine(base_engine, images["Pattern"], images["PatternSyntaxException"])
    assert current_engine == expected, "engine source differs beyond the frozen append-only P35->P36 delta"
    base_abi = json.loads((BASE / "engine/MCEntryInterpreter.json").read_text())["abi"]
    current_artifact = json.loads((STAGE / "engine/MCEntryInterpreter.json").read_text())
    assert current_artifact["abi"] == base_abi, "engine external ABI changed"
    assert sha((STAGE / "engine/MCEntryInterpreter.sol").read_bytes()) == PINS["engineSourceSHA256"]

    expected_coord = base_coord.replace("MC-HASHMAP-DEFAULT-P35", "MC-PATTERN-COMPILE-P36")
    expected_coord = replace_once(expected_coord, base_pins["engine"]["runtimeKeccak256"],
                                  PINS["engineRuntimeKeccak256"])
    current_coord = (STAGE / "coordinator/MCEntryCoordinator.sol").read_text()
    assert current_coord == expected_coord, "coordinator source differs beyond P36 engine-hash/domain binding"
    base_coord_abi = json.loads((BASE / "coordinator/MCEntryCoordinator.json").read_text())["abi"]
    current_coord_artifact = json.loads((STAGE / "coordinator/MCEntryCoordinator.json").read_text())
    assert current_coord_artifact["abi"] == base_coord_abi, "coordinator ABI changed"
    assert sha((STAGE / "coordinator/MCEntryCoordinator.sol").read_bytes()) == PINS["coordinatorSourceSHA256"]

    sys.path.insert(0, str(STAGE / "reference"))
    import p35_root_helper
    env = dict(os.environ, NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    old_root = p35_root_helper.root_record(base_engine, "JVMEVM:MC-HASHMAP-DEFAULT-P35:BOOTSTRAP:1", ROOT, env)
    new_root = p35_root_helper.root_record(current_engine, "JVMEVM:MC-PATTERN-COMPILE-P36:BOOTSTRAP:1", ROOT, env)
    assert old_root["root"] == PINS["sourceBase"]["bootstrapRoot"]
    assert new_root["root"] == PINS["bootstrap"]["root"]
    assert old_root["leaves"] == new_root["leaves"][:101], "P35 bootstrap leaves/order changed"
    assert len(new_root["leaves"]) == 103

    out = {
        "status": "PASS",
        "profile": PINS["profile"],
        "sourceBase": "P35 source-only snapshot; no original JAR/class/resource/world/checkpoint used",
        "baseSourceManifestSHA256": sha(manifest_bytes),
        "baseEngineSourceSHA256": sha(base_engine_path.read_bytes()),
        "engineSourceSHA256": sha((STAGE / "engine/MCEntryInterpreter.sol").read_bytes()),
        "coordinatorSourceSHA256": sha((STAGE / "coordinator/MCEntryCoordinator.sol").read_bytes()),
        "bootstrapRoot": new_root["root"],
        "bootstrapCount": len(new_root["leaves"]),
        "p35LeavesPreserved": 101,
        "newImages": [{"name": name, "bytes": len(data), "sha256": sha(data), "keccak256": keccak(data)}
                      for name, data in images.items()],
        "engineABIUnchanged": True,
        "coordinatorABIUnchanged": True,
        "newNativeBindings": 0,
    }
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
