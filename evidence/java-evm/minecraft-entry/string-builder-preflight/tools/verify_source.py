#!/usr/bin/env python3
"""Strict source-only reverse verifier for bounded StringBuilder image85.

It reads only the accepted parent-89928ece8 evidence and this stage's generated
Java-8 source.  It never opens an original artifact, class, resource, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-89928ece8"

PARENT_FILES = {
    "pins.json": "2ecb1e4fadf2d3eb17d446a7da4fd594b8eb7deda52af7c750f387a35f6c69b1",
    "artifacts/engine/MCEntryInterpreter.sol": "e3d49790b68fa819afbd413c186d95e3820c42fc80cadb601e4fcd0d4ba3ec9f",
    "artifacts/coordinator/MCEntryCoordinator.sol": "b73a6d5cdbba27c5f23e2fbb70e2c5e034cd08e27eb49c190b8c2221ef09fdd9",
    "executed-driver.go.txt": "8dba8844ead0a13c53acbc339c90645cbab23a685feb02e12e135c4b6fa1f898",
    "checkpoint_frames.py": "531725f61002845d6821ef11a95163e188d3ee463526ca8119c2b9c5ec43e38a",
    "verify_receipts.js": "7356b4a018554ab421bbae7e7934e83a528c59cd1ba28a894e1e9f302272cc2e",
}
OLD_DOMAIN = "MC-SYSTEM-ERR-PRNT2"
DOMAIN = "MC-STRING-BUILDER-P1"
OLD_ENGINE = "4d432d53595354454d2d4552522d50524e543200"
ENGINE = "4d432d535452494e472d4255494c4445522d5031"
OLD_OWNER = "4d432d53595354454d2d4552522d4f574e523200"
OWNER = "4d432d535452494e472d4255494c4445522d4f31"
PARENT_RUNTIME_SHA = "15e17e3d6ad5674f30bc6daa64f88609d1376021ed79168e5cbc19afc83a0f6e"
PARENT_RUNTIME_KECCAK = "fcdbb9f1ff129f17085127e6b4713ae41f8d8fd00a538d958ac0ad6863b616fc"
PARENT_COORDINATOR_KECCAK = "0372a7d0bf067705f86a72e7168485bfb1da856ac1212905a64b8f27cd2d004e"
STRING_BUILDER_SHA = "463d7859579627eff6065316f7c9759fb4648768c80ed29656e988db0a662832"
LIMITS_COMMITMENT = "d97049f65bd9258f7c8ba2f1ec45e7611e26a574eee74823d95442488a39839e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_function(name, text):
    found = re.search(
        r"function _bootstrap" + re.escape(name)
        + r"\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";\s*\}",
        text,
    )
    assert found, name
    return found.group(1)


inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "89928ece8",
    "parentEvidence": "parent-89928ece8",
    "sha256": inputs,
}
parent_pins = json.loads((parent / "pins.json").read_text())
assert parent_pins["bootstrapCount"] == 84
assert parent_pins["engine"]["runtimeSHA256"] == PARENT_RUNTIME_SHA
assert parent_pins["engine"]["runtimeKeccak256"] == PARENT_RUNTIME_KECCAK
assert parent_pins["coordinator"]["runtimeKeccak256"] == PARENT_COORDINATOR_KECCAK
assert parent_pins["engine"]["bytes"] == 392775 and parent_pins["runtimeCap"] == 393216
assert parent_pins["limitsCommitment"] == LIMITS_COMMITMENT
assert len(OLD_DOMAIN) == 19 and len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20

source = (stage / "bootstrap/java/lang/StringBuilder.java").read_text()
EXPECTED_SOURCE = """package java.lang;

/**
 * Bounded Java 8 guest surface: construction, append(String), and toString.
 * Each append owns a fresh exact-length char array.  toString delegates its
 * copy to the ordinary guest String(char[]) constructor.
 */
public final class StringBuilder {
    private char[] value;

    public StringBuilder() {
        value = new char[0];
    }

    public StringBuilder append(String input) {
        char[] next = new char[value.length + input.length()];
        for (int index = 0; index < value.length; index++) {
            next[index] = value[index];
        }
        for (int index = 0; index < input.length(); index++) {
            next[value.length + index] = input.charAt(index);
        }
        value = next;
        return this;
    }

    public String toString() {
        return new String(value);
    }
}
"""
assert source == EXPECTED_SOURCE
pins = json.loads((stage / "bootstrap/pins.json").read_text())
assert pins == {
    "reproduction": "javac -source 8 -target 8 -g:none",
    "StringBuilder": {
        "source": "java/lang/StringBuilder.java",
        "classHex": "java/lang/StringBuilder.class.hex",
        "bytes": 542,
        "sha256": STRING_BUILDER_SHA,
        "nullAppend": "bounded guest NullPointerException before allocation; Java8 null-to-literal conversion is intentionally not exposed",
    },
}

# Compilation is provenance only, never a host execution path.
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="string-builder-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    src = tmp / "java/lang/StringBuilder.java"
    src.parent.mkdir(parents=True)
    src.write_text(source)
    out = tmp / "out"; out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", out, src], check=True)
    image = (out / "java/lang/StringBuilder.class").read_bytes()

assert len(image) == 542 and hashlib.sha256(image).hexdigest() == STRING_BUILDER_SHA
assert image.hex() == (stage / "bootstrap/java/lang/StringBuilder.class.hex").read_text().strip()
# The exact javac image declares Object as its direct superclass, no interfaces,
# one private char[] field, and just the measured constructor/append/toString trio.
assert image[:8] == bytes.fromhex("cafebabe00000034")
assert b"java/lang/AbstractStringBuilder" not in image and b"java/io/Serializable" not in image
for literal in (b"append", b"toString", b"java/lang/String", b"java/lang/Object", b"[C"):
    assert literal in image
# One Class entry and append's return descriptor are the only two occurrences.
assert image.count(b"java/lang/StringBuilder") == 2

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
expected_engine = parent_engine.replace(OLD_DOMAIN, DOMAIN)
assert parent_engine.count(OLD_DOMAIN) == 9
expected_engine = expected_engine.replace("new bytes32[](84)", "new bytes32[](85)")
expected_engine = expected_engine.replace(
    """        h[83] = keccak256(_bootstrapPrintStream());
        return keccak256(abi.encode(DBOOT, h));""",
    """        h[83] = keccak256(_bootstrapPrintStream());
        // StringBuilder appends only after the complete 84-image System.err tail.
        h[84] = keccak256(_bootstrapStringBuilder());
        return keccak256(abi.encode(DBOOT, h));""",
)
expected_engine = expected_engine.replace("uint256 count = inputCount + 78 +", "uint256 count = inputCount + 79 +")
expected_engine = expected_engine.replace(
    """        p.classes[classSlot + 44].data = _bootstrapPrintStream();
        p.classClass = classSlot;""",
    """        p.classes[classSlot + 44].data = _bootstrapPrintStream();
        // Bounded StringBuilder appends after every prior immutable bootstrap.
        p.classes[classSlot + 45].data = _bootstrapStringBuilder();
        p.classClass = classSlot;""",
)
expected_engine = expected_engine.replace(
    """        return _isNamedClass(c, bytes("java/lang/System"))
            || _isNamedClass(c, bytes("java/io/PrintStream"))
            || _isNamedClass(c, bytes("java/lang/IllegalArgumentException"))""",
    """        return _isNamedClass(c, bytes("java/lang/System"))
            || _isNamedClass(c, bytes("java/io/PrintStream"))
            || _isNamedClass(c, bytes("java/lang/StringBuilder"))
            || _isNamedClass(c, bytes("java/lang/IllegalArgumentException"))""",
)
printstream_fn = re.search(r"    /// @dev Java 8 constructor-only guest PrintStream; output APIs are omitted\.\n    function _bootstrapPrintStream\(\) private pure returns \(bytes memory\) \{ return hex\"[0-9a-f]+\"; \}\n\n", expected_engine)
assert printstream_fn
builder_fn = (
    "    /// @dev Bounded Java 8 StringBuilder: ctor, append(String), and copy-producing toString only.\n"
    "    function _bootstrapStringBuilder() private pure returns (bytes memory) { return hex\"" + image.hex() + "\"; }\n\n"
)
expected_engine = expected_engine.replace(printstream_fn.group(0), printstream_fn.group(0) + builder_fn)
assert engine == expected_engine

pattern = r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";"
parent_images = dict(re.findall(pattern, parent_engine))
images = dict(re.findall(pattern, engine))
assert len(parent_images) == 84 and len(images) == 85
assert set(images) == set(parent_images) | {"_bootstrapStringBuilder"}
for name, old in parent_images.items():
    assert images[name] == old, name
assert images["_bootstrapStringBuilder"] == image.hex()
assert engine.count("new bytes32[](85)") == 1
assert engine.count("h[84] = keccak256(_bootstrapStringBuilder());") == 1
assert engine.count("p.classes[classSlot + 45].data = _bootstrapStringBuilder();") == 1
assert engine.count('bytes("java/lang/StringBuilder")') == 1
assert engine.count("uint256 count = inputCount + 79 +") == 1
for fixed in (
    "MAX_RAW_CLASSES = 30;", "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;",
    "MAX_PATH_DEPTH = 16;", "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;",
    "new uint256[](14)", "return 12;", "uint32[11] memory limits",
):
    assert engine.count(fixed) == 1, fixed

coordinator_parent = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
assert coordinator == coordinator_parent.replace(OLD_DOMAIN, DOMAIN).replace(OLD_ENGINE, ENGINE)
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[30]") == 4 and coordinator.count("n > 30") == 1 and "262144" in coordinator

driver_parent = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
assert driver == (driver_parent.replace(OLD_DOMAIN, DOMAIN).replace("0x" + OLD_ENGINE, "0x" + ENGINE)
                  .replace("0x" + OLD_OWNER, "0x" + OWNER))
assert driver.count(DOMAIN) == 5 and driver.count("> 30") == 2
assert PARENT_RUNTIME_SHA in driver and ("0x" + PARENT_RUNTIME_KECCAK) in driver
assert ("0x" + PARENT_COORDINATOR_KECCAK) in driver

diagnostic_parent = (parent / "checkpoint_frames.py").read_text()
diagnostic = (stage / "tools/checkpoint_diagnostic.py").read_text()
assert diagnostic == diagnostic_parent.replace("classes<=114", "classes<=115")
assert diagnostic.count("classes<=115") == 1
assert (stage / "tools/verify_receipts.js").read_bytes() == (parent / "verify_receipts.js").read_bytes()
assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")

print(json.dumps({
    "acceptedParent": "parent-89928ece8", "parentInputsVerified": len(inputs),
    "parentEngineSourceSHA256": PARENT_FILES["artifacts/engine/MCEntryInterpreter.sol"],
    "parentRuntimeSHA256": PARENT_RUNTIME_SHA, "parentRuntimeKeccak256": PARENT_RUNTIME_KECCAK,
    "domain": DOMAIN, "bootstrapImages": 85, "rawLimits": [30, 262144],
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "stringBuilder": {"bytes": len(image), "sha256": STRING_BUILDER_SHA},
    "limitsCommitment": LIMITS_COMMITMENT,
}, indent=2))
