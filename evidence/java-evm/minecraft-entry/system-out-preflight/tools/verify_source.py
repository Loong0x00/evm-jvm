#!/usr/bin/env python3
"""Strict generated-only System.out source and root verifier.

It reads only the accepted generated parent evidence and this stage's generated
sources.  It never opens an original artifact, JAR, external class/resource,
network input, or world.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
parent = stage.parent / "parent-1004177d2"
root_parent = stage.parent / "string-substring-int-preflight" / "root-commitment.json"
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"

PARENT_SHA256 = {
    "artifacts/engine/MCEntryInterpreter.sol": "2e1eb4688f0a693db18de55b1563b426d5c1db63692ed48216322fc907f212e1",
    "artifacts/coordinator/MCEntryCoordinator.sol": "bd87185a3470de397c5ffe20a7d30973da814e5c106ccd0dc840ed69a98c4c04",
    "canonical-driver.go.txt": "d04d69ae8ada3aeed2455720477a4bc01476c266dc58bbd0d936fe4ef4c83ed0",
    "checkpoint_diagnostic.py": "840b65f1721169bac22dd19fc6e3a330c2b96d70c18cbe06dd985b48ea917230",
    "checkpoint_frames.py": "840b65f1721169bac22dd19fc6e3a330c2b96d70c18cbe06dd985b48ea917230",
    "verify_receipts.js": "e2f3b6eed4379abb0fadfada204eb95b782c4d726d01b7891594dc133a9d98df",
    "artifacts/engine/build.js": "519351b42549fea4dacf5da41f350954f1d916756ab03a40704c160307b9204d",
    "artifacts/coordinator/build.js": "1e9e9fcfdc36ae1e20e6c6458c390fc9bd48218ac0bd2172ce5059f3d47d1f4e",
    "pins.json": "a40bbca66d45dba712c8b054fe99c4b9e9b0c61b398099b19b88709b03b0aed1",
}
SYSTEM_SHA256 = "ad7a74cb7c5fdf1e79a26a7f18034c46f301fb94af6bf4f12648a3ca62f57576"
SYSTEM_KECCAK = "9eb625de17e0334fb7cb100bba9b9c088e9376e94903f7af365e34d52d6f7fad"
PARENT_SYSTEM_KECCAK = "a3102e6ddd5f579d65db36adfc2a8a526ac551c8b53112023726e390a5fe4fbd"
PARENT_ENGINE_KECCAK = "ae06925e64ec66c7bcb4b4ee94564efb95d1a0fb54ca04b30e7498f8a50150cc"
ENGINE_SHA256 = "afb5386cc40432ad6841000610a274b675000c1b2c883f2053b3b7353ba9b77a"
ENGINE_KECCAK = "db74b131f7aea8a589ba3b113141ab1b8964e27e4ae1059d4febfdff037334e4"
COORDINATOR_KECCAK = "028dd666271e4d8a5aa3156792b9ce0cb7d9bfd3965cc4eef04e271e731f60fd"
DBOOT = "7eecaccd2e1b524be7ab89b577ac324552061e68ca6067413058e558fceb1069"
PARENT_SOURCE_ROOT = "9d25c5e2c0f5220840e9a01ecd11dde07d7cf0b522c41ba45ae6b3c24c9014f7"
ROOT = "86dfeffdbb279e8b80834d4905ce6bd639074af4c82d12e6b8a4acf2cdb86542"

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
    public static final PrintStream out;

    private System() {}

    /** Stable LOCAL replay epoch; this is not a host, block, or wall clock. */
    public static long currentTimeMillis() {
        return 0L;
    }

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
        out = new PrintStream();
    }
}
"""

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def literal(text, name):
    found = re.search(r"function _bootstrap" + re.escape(name) + r"\(\) private pure returns \(bytes memory\) \{ return hex\"([0-9a-f]+)\"; \}", text)
    assert found, name
    return found.group(1)

def fields(data):
    """Minimal Class-file field reader, sufficient to pin flags/descriptors."""
    at = 0
    def u1():
        nonlocal at
        value = data[at]; at += 1; return value
    def u2():
        nonlocal at
        value = int.from_bytes(data[at:at + 2], "big"); at += 2; return value
    def u4():
        nonlocal at
        value = int.from_bytes(data[at:at + 4], "big"); at += 4; return value
    assert data[:4] == b"\xca\xfe\xba\xbe"; at = 8
    cp = [None] * u2()
    i = 1
    while i < len(cp):
        tag = u1()
        if tag == 1:
            n = u2(); cp[i] = data[at:at + n].decode(); at += n
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; i += 1
        elif tag in (7, 8, 16, 19, 20): at += 2
        elif tag in (9, 10, 11, 12, 18): at += 4
        elif tag == 15: at += 3
        else: raise AssertionError(("cp-tag", tag))
        i += 1
    u2(); u2(); u2()
    for _ in range(u2()): u2()
    result = []
    for _ in range(u2()):
        flags, name, descriptor = u2(), cp[u2()], cp[u2()]
        result.append((flags, name, descriptor))
        for _ in range(u2()): u2(); at += u4()
    return result

for name, expected in PARENT_SHA256.items():
    assert sha(parent / name) == expected, name
assert sha(root_parent) == "9c3ba3a57998396af77343b3d9eddfa8818ff3bc44abc15e7f921abb280454b1"

pins = json.loads((stage / "build-pins.json").read_text())
assert pins == {
    "phase": "built", "basis": "1004177d2",
    "parentEvidence": "parent-1004177d2/artifacts/{engine,coordinator}/MCEntry*.sol",
    "domain": "MC-SUBSTRING-INT-00003", "bootstrapCount": 94,
    "bootstrapRoot": ROOT,
    "bootstrapSHA256": {"String": "04f9fa3748fae92840942cfa6dbf2cfb0f3845f0320273c33ada18d81a3bd231", "System": SYSTEM_SHA256},
    "globalNativeBindings": 14, "stringLocalBinding": 11, "exceptionKinds": 14,
    "maxFrames": 128, "rawLimits": [51, 328000], "diagnosticClassBound": 145,
    "checkpointCap": 1048576, "reserve": 25000000, "externalLocalGas": 1000000000,
    "runtimeCap": 393216,
    "address": "0x4d432d535542535452494e472d494e542d303035",
    "owner": "0x4d432d535542535452494e472d494e542d303036",
    "engine": {"bytes": 373634, "initSHA256": "aabc0f79ab637ab94e2dc05c1563a945a70b7cdc71923fc3c8e8e7e634713890", "runtimeSHA256": ENGINE_SHA256, "runtimeKeccak256": ENGINE_KECCAK},
    "coordinator": {"bytes": 5394, "initSHA256": "d3ef89a803cc21874f4d33dc8bd90ed10af00d9c49a221d8c8330d7bcc0f3eca", "runtimeSHA256": "2ca5177e425537974be9f78a24f9e7995091a1a712347e689eb1a2c14b204955", "runtimeKeccak256": COORDINATOR_KECCAK},
    "worker": "system-out",
}
assert (stage / "bootstrap/java/lang/System.java").read_text() == EXPECTED_SYSTEM_SOURCE
assert json.loads((stage / "bootstrap/pins.json").read_text()) == {
    "reproduction": "javac -source 8 -target 8 -g:none",
    "System": {"source": "java/lang/System.java", "classHex": "java/lang/System.class.hex", "bytes": 1001, "sha256": SYSTEM_SHA256, "keccak256": SYSTEM_KECCAK},
}
for forbidden in ("setOut", "setErr", "InputStream in", "Console", "File", "stdout", "stderr", "println(", "print("):
    assert forbidden not in EXPECTED_SYSTEM_SOURCE, forbidden

javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
javap = Path("/usr/lib/jvm/java-8-openjdk/bin/javap")
assert javac.is_file() and javap.is_file()
with tempfile.TemporaryDirectory(prefix="system-out-verify-", dir=root / "build") as tmp_name:
    tmp = Path(tmp_name); source = tmp / "src/java/lang/System.java"; stream = tmp / "src/java/io/PrintStream.java"
    source.parent.mkdir(parents=True); stream.parent.mkdir(parents=True)
    source.write_text(EXPECTED_SYSTEM_SOURCE)
    stream.write_text("package java.io; public class PrintStream { public PrintStream() {} }\n")
    output = tmp / "out"; output.mkdir()
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", output, source, stream], check=True)
    system_class = (output / "java/lang/System.class").read_bytes()
    disassembly = subprocess.run([javap, "-bootclasspath", output, "-classpath", output, "-c", "-p", "java.lang.System"], text=True, capture_output=True, check=True).stdout
assert len(system_class) == 1001
assert hashlib.sha256(system_class).hexdigest() == SYSTEM_SHA256
assert system_class.hex() == (stage / "bootstrap/java/lang/System.class.hex").read_text().strip()
assert fields(system_class) == [
    (0x000a, "security", "Ljava/lang/SecurityManager;"),
    (0x000a, "properties", "Ljava/util/Properties;"),
    (0x0019, "err", "Ljava/io/PrintStream;"),
    (0x0019, "out", "Ljava/io/PrintStream;"),
]
assert "public static final java.io.PrintStream err;" in disassembly
assert "public static final java.io.PrintStream out;" in disassembly
clinit = disassembly.split("static {};", 1)[1]
assert clinit.count("new           #13") == 2
assert clinit.index("Field err:Ljava/io/PrintStream;") < clinit.index("Field out:Ljava/io/PrintStream;")

parent_engine = (parent / "artifacts/engine/MCEntryInterpreter.sol").read_text()
engine = (stage / "engine/MCEntryInterpreter.sol").read_text()
parent_system = literal(parent_engine, "System")
assert len(parent_system) // 2 == 967
assert parent_system != system_class.hex()
expected_engine = parent_engine.replace(parent_system, system_class.hex())
assert engine == expected_engine
assert literal(engine, "System") == system_class.hex()
assert "h[44] = keccak256(_bootstrapSystem());" in engine
for fixed in ("MAX_RAW_CLASSES = 51;", "MAX_RAW_BYTES = 328000;", "MAX_CHECKPOINT_BYTES = 1048576;", "MAX_FRAMES = 128;", "COMMIT_RESERVE = 25_000_000;", "new bytes32[](94)", "new uint256[](14)", "return 14;"):
    assert engine.count(fixed) == 1, fixed
assert engine.count("_bootstrapPrintStream") == parent_engine.count("_bootstrapPrintStream")
assert engine.count("DBOOT_PRINT_STREAM") == parent_engine.count("DBOOT_PRINT_STREAM")

parent_coord = (parent / "artifacts/coordinator/MCEntryCoordinator.sol").read_text()
coord = (stage / "coordinator/MCEntryCoordinator.sol").read_text()
assert parent_coord.count(PARENT_ENGINE_KECCAK) == 1
assert coord == parent_coord.replace(PARENT_ENGINE_KECCAK, ENGINE_KECCAK)
source = (stage / "tools/Go.txt").read_text()
parent_source = (parent / "canonical-driver.go.txt").read_text()
expected_source = parent_source.replace("bf34c65ee9fc89a956c3bece3707fe7ae45cf02abaf3942bc2e298c779fc5e58", ENGINE_SHA256).replace(PARENT_ENGINE_KECCAK, ENGINE_KECCAK).replace("2d02eafaccbcb43d0c269eba04e808b81e1442b86dd4b4b3852e825e1903e0d2", COORDINATOR_KECCAK).replace("len(engineRun) != 373596", "len(engineRun) != 373634").replace("len(run) != 373596", "len(run) != 373634")
assert source == expected_source
for local, source_name in (("checkpoint_diagnostic.py", "checkpoint_diagnostic.py"), ("checkpoint_frames.py", "checkpoint_frames.py"), ("verify_receipts.js", "verify_receipts.js"), ("engine/build.js", "artifacts/engine/build.js"), ("coordinator/build.js", "artifacts/coordinator/build.js")):
    assert (stage / "tools" / local).read_bytes() == (parent / source_name).read_bytes() if "/" not in local else True
assert (stage / "engine/build.js").read_bytes() == (parent / "artifacts/engine/build.js").read_bytes()
assert (stage / "coordinator/build.js").read_bytes() == (parent / "artifacts/coordinator/build.js").read_bytes()

commitment = json.loads((stage / "root-commitment.json").read_text())
base = json.loads(root_parent.read_text())
assert commitment["domain"] == pins["domain"] and commitment["dboot"] == DBOOT and commitment["bootstrapRoot"] == ROOT
assert commitment["bootstrapCount"] == 94 and commitment["order"] == base["order"]
assert len(commitment["keccak256"]) == 94 and commitment["unchangedLeavesRuntimeDerived"] is True
assert base["keccak256"][44] == PARENT_SYSTEM_KECCAK
assert all(commitment["keccak256"][i] == base["keccak256"][i] for i in range(94) if i != 44)
assert commitment["keccak256"][44] == SYSTEM_KECCAK
assert commitment["parentSourceDerivedRoot"] == PARENT_SOURCE_ROOT
assert commitment["parentReportedPin"] == json.loads((parent / "pins.json").read_text())["bootstrapRoot"]
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir()
program = """const {keccak256}=require('js-sha3');let x='';process.stdin.on('data',d=>x+=d);process.stdin.on('end',()=>{let p=JSON.parse(x),u=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex'),r=a=>keccak256(Buffer.concat([Buffer.from(p.dboot,'hex'),u(64),u(a.length),...a.map(v=>Buffer.from(v,'hex'))]));process.stdout.write(JSON.stringify([r(p.parent),r(p.current)]));});"""
roots = json.loads(subprocess.run(["node", "-e", program], input=json.dumps({"dboot": DBOOT, "parent": base["keccak256"], "current": commitment["keccak256"]}), text=True, capture_output=True, check=True, env={**os.environ, "NODE_PATH": str(node)}).stdout)
assert roots == [PARENT_SOURCE_ROOT, ROOT]
assert not any(path.suffix in {".jar", ".class", ".zip"} for path in stage.rglob("*"))
print(json.dumps({"basis": pins["basis"], "system": pins["bootstrapSHA256"]["System"], "bootstrapRoot": ROOT, "engine": pins["engine"], "coordinator": pins["coordinator"], "verification": "System-image-only-runtime-derived-root-delta"}, indent=2))
