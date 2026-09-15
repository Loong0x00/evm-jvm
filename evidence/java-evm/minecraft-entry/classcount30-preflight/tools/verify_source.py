#!/usr/bin/env python3
"""Strict mechanical cap29→30 reverse verifier pinned to parent-3ed302a92."""
from pathlib import Path
import hashlib, json, re

here = Path(__file__).resolve().parent
stage = here.parent
parent = stage.parent / "parent-3ed302a92"

parent_files = {
    "artifacts/engine/MCEntryInterpreter.sol": "eced48ba6644e624a60c05889e83db9566cd06905b01addcb234154517e29553",
    "artifacts/coordinator/MCEntryCoordinator.sol": "4fe9909c0285eb95231b3388798bb82c4b2e375e14d7abbe91f70bdd9b525823",
    "executed-driver.go.txt": "574c8157b837642afdd8baa0da2ee0cd6525b1f949036c63e1809274a413e059",
    "checkpoint_frames.py": "38621a2d2788a653393ebc88a8349056443b85aff096673ed55f9bb014ad6328",
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

inputs = {name: digest(parent / name) for name in parent_files}
assert inputs == parent_files
assert json.loads((stage / "parent-input.json").read_text()) == {
    "basis": "3ed302a92", "parentEvidence": "parent-3ed302a92", "sha256": inputs,
}

old_domain = "MC-ENUM-SET-PARENT2"
domain = "MC-CLASSCOUNT30-C30"
old_engine_address = "4d432d454e554d2d5345542d5032000000000001"
engine_address = "4d432d434c415353434f554e5433302d43333001"
old_owner = "4d432d454e554d2d5345542d4f32000000000002"
owner = "4d432d434c415353434f554e5433302d4f333002"
old_engine_sha = "8bdc4b6d2159009fcab50faa861d56bff01eafe25cf9551383f6046ff5d14ae0"
old_engine_keccak = "193fb2fa9fad5417924977b956f06a11c52952c797892c1e2a074c3aa3850c00"
old_coordinator_keccak = "d036eb145986d342d0cc30130ddbffc2e83cf4474aae05fde1ccfa513d8be5e8"
pins = json.loads((stage / "pins.json").read_text())
expected_engine_pin = {
    "bytes": 393205,
    "initSHA256": "05093c0ec00020348f2259b33a19631ef448689ff926a735f36e37722a4b5b2b",
    "runtimeSHA256": "b8d147e622487822f96b8a376ac45c165e8b10606fa0db20de6924e8e76b99b6",
    "runtimeKeccak256": "9cfd566d186f56d8dd994ab452563dbf2a9edac6bad23a99d584519f5e5cbd48",
}
expected_coordinator_pin = {
    "bytes": 4146,
    "initSHA256": "6c8a151bf449b7b8b80ad4f3894f7896ea90333b1edeecd40cdca0acf4a2c7e8",
    "runtimeSHA256": "ca19560b84712c41536ca244ef441f63da8333d2be81124f2ce6b7353f4a704d",
    "runtimeKeccak256": "00422cb4cb9e2d624aa1caf4516f830145bd94a3e16a28ddc22fa4a5503e367b",
}
assert pins["engine"] == expected_engine_pin and pins["coordinator"] == expected_coordinator_pin

engine_parent = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
expected_engine = (engine_parent.replace(old_domain, domain)
    .replace("MAX_RAW_CLASSES = 29", "MAX_RAW_CLASSES = 30")
    .replace("uint32(29), uint32(262144)", "uint32(30), uint32(262144)"))
assert engine == expected_engine
assert len(old_domain) == len(domain) == 19
assert engine.count(domain) == 9
assert engine.count("MAX_RAW_CLASSES = 30") == 1
assert engine.count("uint32(30), uint32(262144)") == 1
for fixed in (
    "MAX_RAW_BYTES = 262144;", "MAX_CHECKPOINT_BYTES = 1048576;",
    "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;",
    "new bytes32[](83)", "new uint256[](14)", "return 12;",
):
    assert engine.count(fixed) == 1, fixed
bootstrap_pattern = r'function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";'
parent_bootstraps = dict(re.findall(bootstrap_pattern, engine_parent))
bootstraps = dict(re.findall(bootstrap_pattern, engine))
assert len(parent_bootstraps) == len(bootstraps) == 83
assert bootstraps == parent_bootstraps
assert "initializationState[enumTarget] == 3" in engine_parent
assert "initializationState[enumTarget] == 3" in engine

coordinator_parent = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coordinator = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
expected_coordinator = (coordinator_parent.replace(old_domain, domain)
    .replace(old_engine_address, engine_address)
    .replace(old_engine_keccak, pins["engine"]["runtimeKeccak256"])
    .replace("[29]", "[30]").replace("n > 29", "n > 30"))
assert coordinator == expected_coordinator
assert coordinator.count(domain) == 3
assert coordinator.count(engine_address) == 1
assert coordinator.count("[30]") == 4
assert coordinator.count("n > 30") == 1
assert "262144" in coordinator

driver_parent = (parent / "executed-driver.go.txt").read_text()
driver = (stage / "tools/Go.txt").read_text()
expected_driver = (driver_parent.replace(old_domain, domain)
    .replace("0x" + old_engine_address, "0x" + engine_address)
    .replace("0x" + old_owner, "0x" + owner)
    .replace("> 29", "> 30")
    .replace(old_engine_sha, pins["engine"]["runtimeSHA256"])
    .replace("0x" + old_engine_keccak, "0x" + pins["engine"]["runtimeKeccak256"])
    .replace("0x" + old_coordinator_keccak, "0x" + pins["coordinator"]["runtimeKeccak256"]))
assert driver == expected_driver
assert driver.count(domain) == 5
assert driver.count("> 30") == 2
assert engine_address in driver and owner in driver
assert str(pins["engine"]["bytes"]) in driver
for key in ("runtimeSHA256", "runtimeKeccak256"):
    assert pins["engine"][key] in driver
assert pins["coordinator"]["runtimeKeccak256"] in driver

diagnostic_parent = (parent / "checkpoint_frames.py").read_text()
diagnostic = (stage / "tools/checkpoint_diagnostic.py").read_text()
assert diagnostic == diagnostic_parent.replace("classes<=112", "classes<=113")
assert diagnostic.count("classes<=113") == 1

assert digest(stage / "engine/build.js") == digest(parent / "artifacts/engine/build.js")
assert digest(stage / "coordinator/build.js") == digest(parent / "artifacts/coordinator/build.js")
assert pins == {
    "basis": "3ed302a92", "parentEvidence": "parent-3ed302a92", "phase": "built",
    "domain": domain, "runtimeCap": 393216, "bootstrapCount": 83,
    "bootstrapSHA256": {"EnumSet": "ab36a2f498e571717f53554bb485b5d84a38616fc376f1af7a0f5a66846ff230"},
    "bootstrapKeccak256": "00e07d84942a8e3eaec0abf3226c2c4f1ac68e70fed62aafc4393cd2fa5414e9",
    "globalNativeBindings": 12, "stringLocalBinding": 10, "exceptionKinds": 14,
    "maxFrames": 128, "externalLocalGas": 1000000000, "reserve": 25000000,
    "rawLimits": [30, 262144], "checkpointCap": 1048576, "headCap": 32768,
    "engine": expected_engine_pin, "coordinator": expected_coordinator_pin,
    "parentAmendment": "reject initializationState==3 as guest NoClassDefFoundError; diagnostic bound112 retained",
    "diagnosticClassBound": 113, "address": "0x" + engine_address, "owner": "0x" + owner,
}
assert pins["engine"]["bytes"] == 393205 and pins["coordinator"]["bytes"] == 4146
assert len(pins["engine"]["runtimeSHA256"]) == len(pins["engine"]["runtimeKeccak256"]) == 64
assert len(pins["coordinator"]["runtimeSHA256"]) == len(pins["coordinator"]["runtimeKeccak256"]) == 64
print(json.dumps({
    "acceptedParent": "parent-3ed302a92", "parentInputsVerified": len(inputs),
    "domain": domain, "bootstrapImages": 83, "globalNativeBindings": 12,
    "stringLocalBinding": 10, "exceptionKinds": 14, "rawClassCount": 30,
    "rawByteCount": 262144, "diagnosticClassBound": 113,
    "address": pins["address"], "engine": pins["engine"], "coordinator": pins["coordinator"],
}, indent=2))
