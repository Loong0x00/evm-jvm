#!/usr/bin/env python3
"""Strict source-only System.err reverse verifier pinned to parent-de60a3245.

This verifier reads only the accepted parent evidence and the generated bootstrap
sources in this stage.  It never opens a Minecraft artifact, resource, or world.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-de60a3245"

PARENT_FILES = {
    "artifacts/engine/MCEntryInterpreter.sol": "0db34cca0265c6cb2250061e23ca3f9bbd8e8cf28aa6e22b6e2de6a7ffa1ef69",
    "artifacts/coordinator/MCEntryCoordinator.sol": "510996189d4f1fef6f24aa184ac950f4a62c757b93e3691c96ed1b7300e27e4b",
    "executed-driver.go.txt": "1a07506544c55d1038437e1b31da0bde378b1d6f971b23758e2196bb0eacfa07",
    "checkpoint_frames.py": "47f86982ed80145982ce8ad017682b8155891c61aa4d4a553d567f7656b2028d",
}
OLD_DOMAIN = "MC-ENUM-SET-PARENT4"
DOMAIN = "MC-SYSTEM-ERR-PRNT1"
OLD_ENGINE = "4d432d454e554d2d5345542d5034000000000001"
ENGINE = "4d432d53595354454d2d4552522d50524e543100"
OLD_OWNER = "4d432d454e554d2d5345542d4f34000000000002"
OWNER = "4d432d53595354454d2d4552522d4f574e523100"
PARENT_ENGINE_KECCAK = "e5baac0ddccaa86a471b2e0e53b63374db401f82ca6fe95643f1a64a21a0cb33"
PARENT_ENGINE_SHA = "3944c4392408f79070728acfa2976fed825ca7c07b8d0d7436fb19277ccf857b"
PARENT_COORDINATOR_KECCAK = "52cdb66227f1a3b7046336959d726059dc45e17d0b553659a7cad0627499c142"
PRINTSTREAM_KECCAK = "d117732b6247b416988a155a58a837ac13689e8e4c9d6e464e1dd6584ab7482d"
LIMITS_KECCAK = "d97049f65bd9258f7c8ba2f1ec45e7611e26a574eee74823d95442488a39839e"
LIMITS = (30, 262144, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576)

# Keccak-256 (legacy Ethereum padding), kept local so the verifier has no node,
# package-cache, or network dependency.
_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
_ROT = (
    (0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56), (27, 20, 39, 8, 14),
)
_MASK64 = (1 << 64) - 1

def _rol64(value, shift):
    shift &= 63
    return ((value << shift) | (value >> ((64 - shift) & 63))) & _MASK64

def _keccak_f(a):
    for rc in _RC:
        c = [a[x] ^ a[x + 5] ^ a[x + 10] ^ a[x + 15] ^ a[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol64(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x + 5 * y] ^= d[x]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol64(a[x + 5 * y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                a[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
        a[0] ^= rc

def keccak256(data):
    rate = 136
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != rate - 1:
        padded.append(0)
    padded.append(0x80)
    a = [0] * 25
    for at in range(0, len(padded), rate):
        block = padded[at:at + rate]
        for lane in range(rate // 8):
            a[lane] ^= int.from_bytes(block[8 * lane:8 * lane + 8], "little")
        _keccak_f(a)
    return b"".join(x.to_bytes(8, "little") for x in a)[:32]

assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"

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

def source_text(path):
    return path.read_text()

inputs = {name: digest(parent / name) for name in PARENT_FILES}
assert inputs == PARENT_FILES
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "de60a3245", "parentEvidence": "parent-de60a3245", "sha256": inputs,
}
assert len(OLD_DOMAIN) == len(DOMAIN) == 19
assert len(bytes.fromhex(ENGINE)) == len(bytes.fromhex(OWNER)) == 20

system_source = source_text(stage / "bootstrap/java/lang/System.java")
printstream_source = source_text(stage / "bootstrap/java/io/PrintStream.java")
EXPECTED_SYSTEM_SOURCE = """package java.lang;

import java.io.PrintStream;
import java.util.Properties;

/**
 * Bounded Java 8 System surface for the local guest launch profile.
 * No host or -D property channel is present.
 */
public final class System {
    private static SecurityManager security;
    private static Properties properties;
    public static final PrintStream err;

    private System() {}

    public static native void arraycopy(
            Object source, int sourcePosition, Object destination,
            int destinationPosition, int length);

    public static SecurityManager getSecurityManager() {
        return security;
    }

    public static String getProperty(String key) {
        if (key.length() == 0) throw new IllegalArgumentException();
        return properties.getProperty(key);
    }

    static {
        properties = new Properties();
        properties.setProperty("java.version", "1.8");
        err = new PrintStream();
    }
}
"""
EXPECTED_PRINTSTREAM_SOURCE = """package java.io;

/** Bounded guest constructor surface only; output APIs are intentionally absent. */
public class PrintStream {
    public PrintStream() {}
}
"""
assert system_source == EXPECTED_SYSTEM_SOURCE
assert printstream_source == EXPECTED_PRINTSTREAM_SOURCE
assert json.loads((stage / "bootstrap/pins.json").read_text()) == {
    "reproduction": "javac -source 8 -target 8 -g:none",
    "System": {
        "source": "java/lang/System.java", "classHex": "java/lang/System.class.hex",
        "bytes": 913, "sha256": "4b0c92d2908cf30aa4df0bd0ee6f737d4fa8f7aff1872be3d882bc729d4e5e6e",
    },
    "PrintStream": {
        "source": "java/io/PrintStream.java", "classHex": "java/io/PrintStream.class.hex",
        "bytes": 134, "sha256": "ab20e0463e529c30c6f6c5668561145ae57f8c9b735a7cc95b5863a0d5db6fa0",
        "keccak256": PRINTSTREAM_KECCAK,
    },
}

# Prove Java-8 provenance and prove that the prior System image is exactly the
# same source without err/PrintStream. This is compilation only, never host run.
old_system_source = """package java.lang;
import java.util.Properties;
public final class System {
  private static SecurityManager security;
  private static Properties properties;
  private System() {}
  public static native void arraycopy(Object src, int srcPos, Object dest, int destPos, int length);
  public static SecurityManager getSecurityManager() { return security; }
  public static String getProperty(String key) {
    if (key.length() == 0) throw new IllegalArgumentException();
    return properties.getProperty(key);
  }
  static { properties = new Properties(); properties.setProperty("java.version", "1.8"); }
}
"""
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
assert javac.is_file()
with tempfile.TemporaryDirectory(prefix="system-err-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name)
    old_src = tmp / "old/java/lang/System.java"
    new_system_src = tmp / "new/java/lang/System.java"
    new_printstream_src = tmp / "new/java/io/PrintStream.java"
    for path, data in ((old_src, old_system_source), (new_system_src, system_source), (new_printstream_src, printstream_source)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    old_out = tmp / "old-out"
    new_out = tmp / "new-out"
    old_out.mkdir()
    new_out.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", old_out, old_src], check=True)
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", new_out, new_system_src, new_printstream_src], check=True)
    old_class = (tmp / "old-out/java/lang/System.class").read_bytes()
    new_system_class = (tmp / "new-out/java/lang/System.class").read_bytes()
    new_printstream_class = (tmp / "new-out/java/io/PrintStream.class").read_bytes()

parent_engine = source_text(parent / "artifacts/engine/MCEntryInterpreter.sol")
parent_system_hex = bootstrap_function("System", parent_engine)
assert old_class.hex() == parent_system_hex
assert hashlib.sha256(old_class).hexdigest() == "fd3898b354bb3e804fc09580d6a7c1d01ea02db4789ca2a876deb3ef9e03ae44"
assert new_system_class.hex() == (stage / "bootstrap/java/lang/System.class.hex").read_text().strip()
assert new_printstream_class.hex() == (stage / "bootstrap/java/io/PrintStream.class.hex").read_text().strip()
assert hashlib.sha256(new_system_class).hexdigest() == "4b0c92d2908cf30aa4df0bd0ee6f737d4fa8f7aff1872be3d882bc729d4e5e6e"
assert hashlib.sha256(new_printstream_class).hexdigest() == "ab20e0463e529c30c6f6c5668561145ae57f8c9b735a7cc95b5863a0d5db6fa0"
assert keccak256(new_printstream_class).hex() == PRINTSTREAM_KECCAK
assert keccak256(b"".join(x.to_bytes(32, "big") for x in LIMITS)).hex() == LIMITS_KECCAK

# The only engine delta is the new domain plus the exact System replacement,
# one append-only PrintStream image/reservation, and the byte-identical fixed-limit
# commitment repair required to remain inside LOCAL384.
expected_engine = parent_engine.replace(OLD_DOMAIN, DOMAIN)
expected_engine = expected_engine.replace(
    'bytes32 private constant DBOOT_ENUMSET = keccak256(hex"',
    "// This fixed-array ABI commitment was previously materialized at runtime.\n"
    "    // The named limit constants below retain every bound; the precomputed value is\n"
    "    // exactly keccak256(abi.encode(uint32[11](...))) for the same ordered tuple.\n"
    '    bytes32 private constant DLIMITS = hex"' + LIMITS_KECCAK + '";\n'
    '    bytes32 private constant DBOOT_PRINTSTREAM = hex"' + PRINTSTREAM_KECCAK + '";\n'
    '    bytes32 private constant DBOOT_ENUMSET = keccak256(hex"',
)
expected_engine = expected_engine.replace(
    """uint32[11] memory limits = [
            uint32(30), uint32(262144), uint32(64), uint32(32), uint32(65536),
            uint32(65536), uint32(16), uint32(64), uint32(256), uint32(4096),
            uint32(1048576)
        ];
        bytes32 limitsHash = keccak256(abi.encode(limits));""",
    """// Byte-identical to the formerly materialized uint32[11] ABI tuple; keeping
        // it constant removes only allocation/encoding code, not a profile check.
        bytes32 limitsHash = DLIMITS;""",
)
expected_engine = expected_engine.replace("new bytes32[](83)", "new bytes32[](84)")
expected_engine = expected_engine.replace("h[82] = DBOOT_ENUMSET;", "h[82] = DBOOT_ENUMSET;\n        h[83] = DBOOT_PRINTSTREAM;")
expected_engine = expected_engine.replace("uint256 count = inputCount + 77 +", "uint256 count = inputCount + 78 +")
expected_engine = expected_engine.replace(
    "p.classes[classSlot + 43].data = _bootstrapEnumSet();",
    "p.classes[classSlot + 43].data = _bootstrapEnumSet();\n        p.classes[classSlot + 44].data = _bootstrapPrintStream();",
)
expected_engine = expected_engine.replace(
    """return _isNamedClass(c, bytes("java/lang/System"))
            || _isNamedClass(c, bytes("java/lang/IllegalArgumentException"))""",
    """return _isNamedClass(c, bytes("java/lang/System"))
            || _isNamedClass(c, bytes("java/io/PrintStream"))
            || _isNamedClass(c, bytes("java/lang/IllegalArgumentException"))""",
)
old_system_fn = re.search(r"function _bootstrapSystem\(\) private pure returns \(bytes memory\) \{ return hex\"[0-9a-f]+\"; \}", expected_engine)
assert old_system_fn
expected_engine = expected_engine.replace(
    old_system_fn.group(0),
    'function _bootstrapSystem() private pure returns (bytes memory) { return hex"' + new_system_class.hex() + '"; }\n\n'
    '    /// @dev Java 8 constructor-only guest PrintStream; output APIs are omitted.\n'
    '    function _bootstrapPrintStream() private pure returns (bytes memory) { return hex"' + new_printstream_class.hex() + '"; }',
)
engine = source_text(stage / "engine/MCEntryInterpreter.sol")
assert engine == expected_engine

bootstrap_pattern = r"function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex\"([0-9a-f]+)\";"
parent_images = dict(re.findall(bootstrap_pattern, parent_engine))
images = dict(re.findall(bootstrap_pattern, engine))
assert len(parent_images) == 83 and len(images) == 84
assert set(images) == set(parent_images) | {"_bootstrapPrintStream"}
for name, image in parent_images.items():
    if name != "_bootstrapSystem":
        assert images[name] == image, name
assert images["_bootstrapSystem"] == new_system_class.hex()
assert images["_bootstrapPrintStream"] == new_printstream_class.hex()
assert engine.count("new bytes32[](84)") == 1
assert engine.count("h[44] = keccak256(_bootstrapSystem());") == 1
assert engine.count("h[82] = DBOOT_ENUMSET;") == 1
assert engine.count("h[83] = DBOOT_PRINTSTREAM;") == 1
assert engine.count("p.classes[classSlot + 44].data = _bootstrapPrintStream();") == 1
assert engine.count('bytes("java/io/PrintStream")') == 1
assert engine.count("uint256 count = inputCount + 78 +") == 1
assert engine.count("MAX_RAW_CLASSES = 30;") == 1
for fixed in (
    "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;",
    "COMMIT_RESERVE = 25_000_000;", "MAX_PATH_COMPONENT = 64;", "MAX_PATH_DEPTH = 16;",
    "MAX_PATH_BYTES = 256;", "MAX_TRANSFER = 4096;", "new uint256[](14)", "return 12;",
):
    assert engine.count(fixed) == 1, fixed
assert "uint32[11] memory limits" not in engine
assert engine.count("DLIMITS") == 2

# The product coordinator and driver retain raw30 arrays/guards. They are source
# templates: build.py replaces only the derived code hashes in its disposable output.
coordinator_parent = source_text(parent / "artifacts/coordinator/MCEntryCoordinator.sol")
coordinator = source_text(stage / "coordinator/MCEntryCoordinator.sol")
assert coordinator == coordinator_parent.replace(OLD_DOMAIN, DOMAIN).replace(OLD_ENGINE, ENGINE)
assert coordinator.count(DOMAIN) == 3 and coordinator.count(ENGINE) == 1
assert coordinator.count("[30]") == 4 and coordinator.count("n > 30") == 1
assert "262144" in coordinator

driver_parent = source_text(parent / "executed-driver.go.txt")
driver = source_text(stage / "tools/Go.txt")
assert driver == (driver_parent.replace(OLD_DOMAIN, DOMAIN)
                 .replace("0x" + OLD_ENGINE, "0x" + ENGINE)
                 .replace("0x" + OLD_OWNER, "0x" + OWNER))
assert driver.count(DOMAIN) == 5 and driver.count("> 30") == 2
assert PARENT_ENGINE_SHA in driver and ("0x" + PARENT_ENGINE_KECCAK) in driver
assert ("0x" + PARENT_COORDINATOR_KECCAK) in driver

diagnostic_parent = (parent / "checkpoint_frames.py").read_text()
diagnostic = (stage / "tools/checkpoint_diagnostic.py").read_text()
assert diagnostic == diagnostic_parent.replace("classes<=113", "classes<=114")
assert diagnostic.count("classes<=114") == 1

assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")
print(json.dumps({
    "acceptedParent": "parent-de60a3245", "parentInputsVerified": len(inputs),
    "domain": DOMAIN, "bootstrapImages": 84, "rawLimits": [30, 262144],
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "checkpointCap": 1048576, "headCap": 32768,
    "system": {"bytes": len(new_system_class), "sha256": hashlib.sha256(new_system_class).hexdigest()},
    "printStream": {"bytes": len(new_printstream_class), "sha256": hashlib.sha256(new_printstream_class).hexdigest()},
    "limitsCommitment": LIMITS_KECCAK,
}, indent=2))
