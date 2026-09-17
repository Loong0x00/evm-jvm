#!/usr/bin/env python3
"""Source-only invariants for ordinary Java-8 String.startsWith(String)."""
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
parent = stage.parent / "parent-1fc13ef12"
PARENT_DOMAIN = "MC-PROPERTIES-LOAD-P2"
DOMAIN = "MC-STRING-STARTS-WITH-P1"
PARENT_ENGINE = "4d432d50524f50532d4c4f41442d50322d303030"
ENGINE = "4d432d535452494e472d53544152545357495448"
PARENT_OWNER = "4d432d50524f50532d4c4f41442d4f574e455231"
OWNER = "4d432d535452494e472d5354415254532d4f574e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message):
    raise RuntimeError(message)


def required(text, token, exactly=None):
    n = text.count(token)
    if (exactly is not None and n != exactly) or (exactly is None and n == 0):
        fail("source invariant %r count=%d" % (token, n))


def string_hex(text):
    match = re.search(r'(function _bootstrapString\(\) private pure returns \(bytes memory\) \{\s*return hex")([0-9a-f]+)(";\s*\})', text, re.S)
    if match is None:
        fail("String bootstrap absent")
    return match.group(2)


parent_engine = parent / "artifacts/engine/MCEntryInterpreter.sol"
parent_coordinator = parent / "artifacts/coordinator/MCEntryCoordinator.sol"
parent_driver = parent / "executed-driver.go.txt"
parent_pins_path = parent / "pins.json"
parent_input_path = stage / "parent-input.json"
for path in (parent_engine, parent_coordinator, parent_driver, parent_pins_path, parent_input_path):
    if not path.is_file():
        fail("accepted Properties parent input absent: " + str(path))
parent_input = json.loads(parent_input_path.read_text())
if parent_input["basis"] != "parent-1fc13ef12" or parent_input["parentEvidence"] != "parent-1fc13ef12":
    fail("parent input identity drift")
for name, path in {
    "pins.json": parent_pins_path,
    "artifacts/engine/MCEntryInterpreter.sol": parent_engine,
    "artifacts/coordinator/MCEntryCoordinator.sol": parent_coordinator,
    "executed-driver.go.txt": parent_driver,
}.items():
    if parent_input["sha256"].get(name) != digest(path):
        fail("accepted parent hash drift: " + name)

engine_path = stage / "engine/MCEntryInterpreter.sol"
coord_path = stage / "coordinator/MCEntryCoordinator.sol"
driver_path = stage / "tools/Go.txt"
source_path = stage / "bootstrap/java/lang/String.java"
hex_path = stage / "bootstrap/java/lang/String.class.hex"
for path in (engine_path, coord_path, driver_path, source_path, hex_path):
    if not path.is_file():
        fail("stage input absent: " + str(path))

image_hex = hex_path.read_text().strip()
if not re.fullmatch(r"[0-9a-f]+", image_hex) or len(image_hex) % 2:
    fail("String class hex is not canonical lowercase bytes")
image = bytes.fromhex(image_hex)
if not image.startswith(bytes.fromhex("cafebabe00000034")):
    fail("String image is not Java8 classfile")
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
if not javac.is_file():
    fail("pinned Java8 javac unavailable")
with tempfile.TemporaryDirectory(prefix="string-starts-with-source-", dir=root / "build") as temp:
    classes = Path(temp) / "classes"
    classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, source_path], check=True)
    compiled = (classes / "java/lang/String.class").read_bytes()
if compiled != image:
    fail("String source does not reproduce embedded Java8 image")
source = source_path.read_text()
for token in (
    "public final class String implements java.io.Serializable, Comparable<String>, CharSequence",
    "public int lastIndexOf(String target)",
    "public boolean startsWith(String prefix)",
    "int prefixLength = prefix.length();",
    "if (prefixLength > length()) return false;",
    "charAt(index) != prefix.charAt(index)",
    "public native String[] split(String regex);",
):
    required(source, token, 1)
if "startsWith(String prefix, " in source or " native boolean startsWith" in source or "substring(" in source:
    fail("startsWith profile expanded beyond offset-zero ordinary Java")
if source.index("public int lastIndexOf") > source.index("public boolean startsWith"):
    fail("lastIndexOf must remain before the appended startsWith method")

# This replaces exactly slot26 from the accepted Properties P2 parent. The
# parent Properties image and every other byte (including lastIndexOf) stay in
# the expected source identity, rather than being reconstructed by name.
parent_text = parent_engine.read_text()
old_string = string_hex(parent_text)
if hashlib.sha256(bytes.fromhex(old_string)).hexdigest() != "2fbfe5d57906f5ebd4f2eeaceb209edf8d4a619afb21d1531f7aaea121506033":
    fail("accepted parent String pin drift")
expected_engine = parent_text.replace(PARENT_DOMAIN, DOMAIN).replace(old_string, image_hex)
engine = engine_path.read_text()
if engine != expected_engine:
    fail("engine delta is not exactly domain plus String slot26")
for token in (
    "new bytes32[](86)", "h[26] = keccak256(_bootstrapString());",
    "uint256 private constant MAX_RAW_CLASSES = 32;",
    "uint256 private constant MAX_RAW_BYTES = 262144;",
    "uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;",
    "uint256 private constant MAX_FRAMES = 128;", "function _nativeBinding",
    "return 13;", "function _vfsNativeBinding",
):
    required(engine, token, 1)
if string_hex(engine) != image_hex or len(bytes.fromhex(string_hex(engine))) != len(image):
    fail("String slot26 image drift")
if "startsWith" in engine.replace(image_hex, ""):
    fail("startsWith may enter only through ordinary String bytecode")

# Coordinator may differ only in domain, fixed engine address, and engine hash.
coord = coord_path.read_text()
coord_hash = re.search(r'bytes32 private constant ENGINE_CODEHASH = hex"([0-9a-f]{64})";', coord)
parent_coord = parent_coordinator.read_text()
parent_coord_hash = re.search(r'bytes32 private constant ENGINE_CODEHASH = hex"([0-9a-f]{64})";', parent_coord)
if coord_hash is None or parent_coord_hash is None:
    fail("coordinator engine codehash absent")
expected_coord = (parent_coord.replace(PARENT_DOMAIN, DOMAIN)
                  .replace(PARENT_ENGINE, ENGINE)
                  .replace(parent_coord_hash.group(1), coord_hash.group(1)))
if coord != expected_coord:
    fail("coordinator delta is not domains/address/new engine hash only")
for token in (
    'address private constant ENGINE = address(bytes20(hex"' + ENGINE + '"));',
    'uint32 private constant MAX_SELECTED_RESOURCE_BYTES = 4096;',
    'function _loadSelectedSeed() private view', 'function _readExact(address decoder, uint32 size)',
    'function resourceExists(bytes calldata rawName)', 'finalIndex.staticcall(',
    'abi.encodeWithSignature("lookup(bytes)", rawName)',
):
    required(coord, token, 1)

# The raw-byte driver remains a generated-fixture transport. It is textually
# pinned to the accepted P2 driver except for profile/address/runtime pins.
driver = driver_path.read_text()
new_engine_sha = "674fd77832458387075945d962ea38fe7458bfe134ea91a24ea9ef6714d92779"
new_engine_keccak = "f05ec4279b8ec94cc8dcd7569906ffc248522d204cb9897d2e1ce3242848d659"
parent_driver_text = parent_driver.read_text()
expected_driver = (parent_driver_text.replace(PARENT_DOMAIN, DOMAIN)
                   .replace("b7a1253a8068f3be6609a265d862cb4c55859115d5b155b710dc96d950edad8b", new_engine_sha)
                   .replace("0x788b7b1418d188d06b2b396ca9a11605ca2d8f285f8dd5e24b8006b7095748d3", "0x" + new_engine_keccak)
                   .replace("0x8edf6dc4d76c0004bab972b82280c1dea78b14409b5de4060e8c546a13fb6dc7", "0xde264c857477be68704fb4bbce94d5d051935c9e19bfc535e2d1464cab3b2aea")
                   .replace("392032", "392076")
                   .replace("0x" + PARENT_OWNER, "0x" + OWNER)
                   .replace("0x" + PARENT_ENGINE, "0x" + ENGINE))
if driver != expected_driver:
    fail("driver delta is not fresh String profile pins")
for token in (
    'const format = "' + DOMAIN + '-BOUNDED-1"',
    'var engine = common.HexToAddress("0x' + ENGINE + '")',
    'var owner = common.HexToAddress("0x' + OWNER + '")',
    'func selectedResourceName() []byte', 'MC_ENTRY_SELECTED_RESOURCE',
    'func packageRoot(', 'func resourceTamper(',
):
    required(driver, token, 1)
if "archive/zip" in driver or "zip.NewReader" in driver or "flate." in driver or "gzip." in driver or ".jar" in driver:
    fail("driver may not parse archives or name an original artifact")

inputs = {
    "parent-engine": digest(parent_engine), "parent-coordinator": digest(parent_coordinator),
    "parent-driver": digest(parent_driver), "parent-pins": digest(parent_pins_path),
    "stage-engine": digest(engine_path), "stage-coordinator": digest(coord_path),
    "stage-driver": digest(driver_path), "stage-string-source": digest(source_path),
    "stage-string-class": hashlib.sha256(image).hexdigest(),
}
report = {
    "acceptedParent": "parent-1fc13ef12", "parentInputsVerified": 4,
    "phase": "prebuild" if "--prebuild" in sys.argv else "built", "domain": DOMAIN,
    "bootstrapImages": 86, "replacedBootstrapSlot": 26, "unchangedBootstrapImages": 85,
    "rawLimits": [32, 262144], "diagnosticClassBound": 118, "globalNativeBindings": 13,
    "stringLocalBinding": 10, "exceptionKinds": 14, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
    "stringSHA256": inputs["stage-string-class"], "sourceHashes": inputs,
}
if "--built" in sys.argv:
    at = sys.argv.index("--built")
    pins = json.loads(Path(sys.argv[at + 1]).read_text())
    if pins["domain"] != DOMAIN or pins["bootstrapCount"] != 86 or pins["rawLimits"] != [32, 262144]:
        fail("built pins profile drift")
    if pins["bootstrapSHA256"]["String"] != inputs["stage-string-class"]:
        fail("built pins String image drift")
    if pins["engine"]["runtimeSHA256"] != new_engine_sha or pins["engine"]["runtimeKeccak256"] != new_engine_keccak:
        fail("built engine pin drift")
    if pins["coordinator"]["runtimeKeccak256"] != "de264c857477be68704fb4bbce94d5d051935c9e19bfc535e2d1464cab3b2aea":
        fail("built coordinator pin drift")
    if pins["engine"]["bytes"] > 393216 or pins["globalNativeBindings"] != 13:
        fail("built pins cap/native drift")
print(json.dumps(report, indent=2))
