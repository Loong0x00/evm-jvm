#!/usr/bin/env python3
"""Source-only invariants for bounded guest Properties.load(InputStream)."""
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
parent = stage.parent / "parent-c96c326bc"
DOMAIN_PARENT = "MC-URL-OPEN-STREAM-P2"
DOMAIN = "MC-PROPERTIES-LOAD-P1"
ENGINE_PARENT = "4d432d55524c2d4f50454e53545245414d2d5032"
OWNER_PARENT = "4d432d55524c2d4f50454e53545245414d2d4f32"
ENGINE = "4d432d50524f50532d4c4f41442d50312d303030"
OWNER = "4d432d50524f50532d4c4f41442d4f574e455230"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message):
    raise RuntimeError(message)


def required(text, token, exactly=None):
    n = text.count(token)
    if (exactly is not None and n != exactly) or (exactly is None and n == 0):
        fail("source invariant %r count=%d" % (token, n))


parent_engine = parent / "artifacts/engine/MCEntryInterpreter.sol"
parent_coordinator = parent / "artifacts/coordinator/MCEntryCoordinator.sol"
parent_driver = parent / "executed-driver.go.txt"
parent_pins_path = parent / "pins.json"
for path in (parent_engine, parent_coordinator, parent_driver, parent_pins_path):
    if not path.is_file():
        fail("accepted URL parent input absent: " + str(path))

engine_path = stage / "engine/MCEntryInterpreter.sol"
coord_path = stage / "coordinator/MCEntryCoordinator.sol"
driver_path = stage / "tools/Go.txt"
properties_source = stage / "bootstrap/java/util/Properties.java"
properties_hex_path = stage / "bootstrap/java/util/Properties.class.hex"
for path in (engine_path, coord_path, driver_path, properties_source, properties_hex_path):
    if not path.is_file():
        fail("stage input absent: " + str(path))

properties_hex = properties_hex_path.read_text().strip()
if not re.fullmatch(r"[0-9a-f]+", properties_hex) or len(properties_hex) % 2:
    fail("Properties class hex is not canonical lowercase bytes")
properties_bytes = bytes.fromhex(properties_hex)
if not properties_bytes.startswith(bytes.fromhex("cafebabe00000034")):
    fail("Properties image is not Java8 classfile")

javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
if not javac.is_file():
    fail("pinned Java8 javac unavailable")
with tempfile.TemporaryDirectory(prefix="properties-load-source-", dir=root / "build") as temp:
    classes = Path(temp) / "classes"
    classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, properties_source], check=True)
    compiled = (classes / "java/util/Properties.class").read_bytes()
if compiled != properties_bytes:
    fail("Properties source does not reproduce embedded Java8 image")
source = properties_source.read_text()
for token in (
    "public class Properties extends Hashtable",
    "public void load(InputStream input) throws IOException",
    "new char[4096]", "int next = input.read()",
    "if (next == '\\\\' || length == 4096)",
    "super.put(new String(key), new String(value))",
    "line[at] != '#' && line[at] != '!'",
    "line[at] != '=' && line[at] != ':' && !(line[at] == ' '",
):
    required(source, token, 1)
if source.count("throw new IOException()") != 1 or " native " in source or "\\u" in source.replace("Unicode escapes", ""):
    fail("Properties parser must be ordinary Java and reject, not decode, escapes")

# The engine differs from the accepted URL parent only in the fresh profile
# domain and bootstrap Properties slot47. URL and the selected-resource pipeline
# remain byte-identical to the accepted parent.
parent_text = parent_engine.read_text()
old_properties = re.search(r'function _bootstrapProperties\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}', parent_text)
if old_properties is None:
    fail("accepted Properties bootstrap absent")
expected_engine = parent_text.replace(DOMAIN_PARENT, DOMAIN)
expected_engine = expected_engine.replace(old_properties.group(1), properties_hex)
engine = engine_path.read_text()
if engine != expected_engine:
    fail("engine delta is not exactly domains plus bootstrap Properties")
for token in (
    "new bytes32[](86)", "h[47] = keccak256(_bootstrapProperties());",
    "uint256 private constant MAX_RAW_CLASSES = 32;",
    "uint256 private constant MAX_RAW_BYTES = 262144;",
    "uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;",
    "uint256 private constant MAX_FRAMES = 128;", "function _nativeBinding",
    "return 13;", "function _vfsNativeBinding",
):
    required(engine, token, 1)
if "load(InputStream)" in engine.replace(properties_hex, ""):
    fail("Properties.load may only enter through the ordinary bootstrap image")

coord = coord_path.read_text()
coord_hash = re.search(r'bytes32 private constant ENGINE_CODEHASH = hex"([0-9a-f]{64})";', coord)
if coord_hash is None:
    fail("coordinator engine codehash missing")
parent_coord_text = parent_coordinator.read_text()
parent_engine_hash = re.search(r'bytes32 private constant ENGINE_CODEHASH = hex"([0-9a-f]{64})";', parent_coord_text)
if parent_engine_hash is None:
    fail("parent coordinator engine codehash missing")
expected_coord = (parent_coord_text.replace(DOMAIN_PARENT, DOMAIN)
                  .replace(ENGINE_PARENT, ENGINE).replace(OWNER_PARENT, OWNER)
                  .replace(parent_engine_hash.group(1), coord_hash.group(1)))
if coord != expected_coord:
    fail("coordinator delta is not domains/address/new engine hash only")
for token in (
    'address private constant ENGINE = address(bytes20(hex"' + ENGINE + '"));',
    'uint32 private constant MAX_SELECTED_RESOURCE_BYTES = 4096;',
    'address private seedDecoder;', 'bytes private seedName;', 'bytes32 private seedRoot;', 'uint32 private seedSize;',
    'SeedFile[] memory seeds = _loadSelectedSeed();',
    'SeedFile(abi.encodePacked(bytes("/ro/"), seedName), _readExact(seedDecoder, seedSize), true)',
    'function _loadSelectedSeed() private view', 'function _readExact(address decoder, uint32 size)',
    'function resourceExists(bytes calldata rawName)', 'keccak256(rawName) != keccak256(seedName)',
    'finalIndex.staticcall(', 'abi.encodeWithSignature("lookup(bytes)", rawName)',
    'uint8(assertedSeedDecoder == address(0) ? 0 : 1)',
):
    required(coord, token, 1)
for token in ('DI0_CODEHASH', 'ZI0_CODEHASH', 'AS0_CODEHASH', 'SEED_DOMAIN', 'CLASS_DOMAIN'):
    required(coord, token)
if 'address[] private seed' in coord or 'bytes[] private seed' in coord or 'SeedFile[] private' in coord:
    fail("selected resource must be scalar, not a catalogue")
if coord.count('address assertedSeedDecoder') != 1 or coord.count('bytes memory assertedSeedName') != 1:
    fail("constructor must carry exactly one selected resource")
resume = coord[coord.index('function resumeMain'):coord.index('function _loadAll')]
if '_loadSelectedSeed' in resume:
    fail("resume reloads selected resource instead of checkpointed VFS")

# The raw-byte driver may make a generated ZIP, but it must pass only opaque
# bytes to AS0. It has no ZIP parser/decompressor and leaves resource selection
# scalar and explicit.
driver = driver_path.read_text()
for token in (
    'const format = "MC-PROPERTIES-LOAD-P1-BOUNDED-1"',
    'var engine = common.HexToAddress("0x' + ENGINE + '")',
    'var owner = common.HexToAddress("0x' + OWNER + '")',
    'func selectedResourceName() []byte', 'MC_ENTRY_SELECTED_RESOURCE',
    'strings.Contains(raw, ",")', 'func packageRoot(', 'func resourceTamper(',
    'resource-root-tamper', 'resource-address-tamper',
):
    required(driver, token, 1)
for token in ('seedDomain', 'SeedDecoder', 'SelectedRoot', 'setupResources(e, raw, names, selected, true)'):
    required(driver, token)
if 'archive/zip' in driver or 'zip.NewReader' in driver or 'flate.' in driver or 'gzip.' in driver:
    fail("driver may not parse or decompress ZIP content")
if '.jar' in driver:
    fail("driver may not name an original artifact")

inputs = {
    "parent-engine": digest(parent_engine), "parent-coordinator": digest(parent_coordinator),
    "parent-driver": digest(parent_driver), "parent-pins": digest(parent_pins_path),
    "stage-engine": digest(engine_path), "stage-coordinator": digest(coord_path),
    "stage-driver": digest(driver_path), "stage-properties-source": digest(properties_source),
    "stage-properties-class": hashlib.sha256(properties_bytes).hexdigest(),
}
report = {
    "acceptedParent": "parent-c96c326bc", "parentInputsVerified": 4,
    "phase": "prebuild" if "--prebuild" in sys.argv else "built", "domain": DOMAIN,
    "bootstrapImages": 86, "replacedBootstrapSlot": 47, "unchangedBootstrapImages": 85,
    "rawLimits": [32, 262144], "diagnosticClassBound": 118, "globalNativeBindings": 13,
    "stringLocalBinding": 10, "exceptionKinds": 14, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768, "address": "0x" + ENGINE,
    "propertiesSHA256": inputs["stage-properties-class"], "sourceHashes": inputs,
}
if "--built" in sys.argv:
    at = sys.argv.index("--built")
    pins = json.loads(Path(sys.argv[at + 1]).read_text())
    if pins["domain"] != DOMAIN or pins["bootstrapCount"] != 86 or pins["rawLimits"] != [32, 262144]:
        fail("built pins profile drift")
    if pins["bootstrapSHA256"]["Properties"] != inputs["stage-properties-class"]:
        fail("built pins Properties image drift")
    if pins["engine"]["bytes"] > 393216 or pins["globalNativeBindings"] != 13:
        fail("built pins cap/native drift")
print(json.dumps(report, indent=2))
