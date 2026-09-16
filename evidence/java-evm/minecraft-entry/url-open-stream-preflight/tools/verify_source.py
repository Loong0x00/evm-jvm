#!/usr/bin/env python3
"""Source-only invariants for the generated bounded URL.openStream stage."""
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
parent = stage.parent / "parent-f7e2ad683"
DOMAIN_PARENT = "MC-OBJECT-GET-CLASS-P2"
DOMAIN = "MC-URL-OPEN-STREAM-P1"
ENGINE = "4d432d55524c2d4f50454e53545245414d2d5031"
OWNER = "4d432d55524c2d4f50454e53545245414d2d4f31"


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
for path in (parent_engine, parent_coordinator, parent_driver, parent / "pins.json"):
    if not path.is_file():
        fail("accepted Object.getClass parent input absent: " + str(path))

engine_path = stage / "engine/MCEntryInterpreter.sol"
coord_path = stage / "coordinator/MCEntryCoordinator.sol"
driver_path = stage / "tools/Go.txt"
url_source = stage / "bootstrap/java/net/URL.java"
url_hex_path = stage / "bootstrap/java/net/URL.class.hex"
for path in (engine_path, coord_path, driver_path, url_source, url_hex_path):
    if not path.is_file():
        fail("stage input absent: " + str(path))

url_hex = url_hex_path.read_text().strip()
if not re.fullmatch(r"[0-9a-f]+", url_hex) or len(url_hex) % 2:
    fail("URL class hex is not canonical lowercase bytes")
url_bytes = bytes.fromhex(url_hex)
if not url_bytes.startswith(bytes.fromhex("cafebabe00000034")):
    fail("URL image is not Java8 classfile")

javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
if not javac.is_file():
    fail("pinned Java8 javac unavailable")
with tempfile.TemporaryDirectory(prefix="url-open-stream-source-", dir=root / "build") as temp:
    classes = Path(temp) / "classes"
    classes.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, url_source], check=True)
    compiled = (classes / "java/net/URL.class").read_bytes()
if compiled != url_bytes:
    fail("URL source does not reproduce embedded Java8 image")
source = url_source.read_text()
for token in (
    "public final class URL", "private final String resourceName", "public InputStream openStream() throws IOException",
    "new FileInputStream(new File(\"/ro/\" + resourceName))",
):
    required(source, token, 1)

# The engine differs from the accepted Object parent only in the profile domain
# separation and URL bootstrap slot62. No dispatcher/native/VFS behavior changes.
parent_text = parent_engine.read_text()
old_url = re.search(r'function _bootstrapURL\(\) private pure returns \(bytes memory\) \{ return hex"([0-9a-f]+)"; \}', parent_text)
if old_url is None:
    fail("accepted URL bootstrap absent")
expected_engine = parent_text.replace(DOMAIN_PARENT, DOMAIN)
expected_engine = expected_engine.replace(old_url.group(1), url_hex)
engine = engine_path.read_text()
if engine != expected_engine:
    fail("engine delta is not exactly domains plus bootstrap URL")
required(engine, 'new bytes32[](86)', 1)
required(engine, 'h[62] = keccak256(_bootstrapURL());', 1)
required(engine, 'uint256 private constant MAX_RAW_CLASSES = 32;', 1)
required(engine, 'uint256 private constant MAX_RAW_BYTES = 262144;', 1)
required(engine, 'uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;', 1)
required(engine, 'uint256 private constant MAX_FRAMES = 128;', 1)
required(engine, 'function _nativeBinding', 1)
required(engine, 'return 13;', 1)
required(engine, 'function _vfsNativeBinding', 1)
if 'openStream' in engine.replace(url_hex, ''):
    fail("openStream may only enter through the ordinary URL bootstrap image")

coord = coord_path.read_text()
for token in (
    'address private constant ENGINE = address(bytes20(hex"' + ENGINE + '"));',
    'bytes32 private constant ENGINE_CODEHASH = hex"',
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
if 'new SeedFile[](1)' not in coord or 'new SeedFile[](0)' not in coord:
    fail("optional selected-resource cardinality missing")
if 'resumeMain' not in coord or 'function resumeMain' not in coord:
    fail("resume surface missing")
resume = coord[coord.index('function resumeMain'):coord.index('function _loadAll')]
if '_loadSelectedSeed' in resume:
    fail("resume reloads selected resource instead of checkpointed VFS")

# The raw-byte driver is allowed to create a generated ZIP, but must bind all
# class/resource names from explicit generated-fixture environment metadata and
# supply only opaque archive bytes to AS0. It has no ZIP parser/decompressor.
driver = driver_path.read_text()
for token in (
    'const format = "MC-URL-OPEN-STREAM-P1-BOUNDED-1"',
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
    "parent-engine": digest(parent_engine),
    "parent-coordinator": digest(parent_coordinator),
    "parent-driver": digest(parent_driver),
    "parent-pins": digest(parent / "pins.json"),
    "stage-engine": digest(engine_path),
    "stage-coordinator": digest(coord_path),
    "stage-driver": digest(driver_path),
    "stage-url-source": digest(url_source),
    "stage-url-class": hashlib.sha256(url_bytes).hexdigest(),
}
report = {
    "acceptedParent": "parent-f7e2ad683", "parentInputsVerified": 4,
    "phase": "prebuild" if "--prebuild" in sys.argv else "built",
    "domain": DOMAIN, "bootstrapImages": 86, "replacedBootstrapSlot": 62,
    "unchangedBootstrapImages": 85, "rawLimits": [32, 262144],
    "diagnosticClassBound": 118, "globalNativeBindings": 13,
    "stringLocalBinding": 10, "exceptionKinds": 14, "maxFrames": 128,
    "checkpointCap": 1048576, "headCap": 32768,
    "address": "0x" + ENGINE, "urlSHA256": inputs["stage-url-class"],
    "sourceHashes": inputs,
}
if "--built" in sys.argv:
    at = sys.argv.index("--built")
    pins = json.loads(Path(sys.argv[at + 1]).read_text())
    if pins["domain"] != DOMAIN or pins["bootstrapCount"] != 86 or pins["rawLimits"] != [32, 262144]:
        fail("built pins profile drift")
    if pins["bootstrapSHA256"]["URL"] != inputs["stage-url-class"]:
        fail("built pins URL image drift")
    if pins["engine"]["bytes"] > 393216 or pins["globalNativeBindings"] != 13:
        fail("built pins cap/native drift")
print(json.dumps(report, indent=2))
