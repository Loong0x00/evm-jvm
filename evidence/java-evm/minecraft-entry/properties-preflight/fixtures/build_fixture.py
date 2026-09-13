#!/usr/bin/env python3
"""Build the TEST-only guest fixture; no host Java is an execution authority."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine" / "MCEntryInterpreter.sol"
BOOT = ROOT / "bootstrap" / "java" / "util"
HERE = Path(__file__).resolve().parent
JAVA_HOME = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JAVA_HOME / "bin" / "javac"
RT = JAVA_HOME / "jre" / "lib" / "rt.jar"


def main():
    tmpdir = os.environ.get("TMPDIR", "")
    if not tmpdir or not os.path.isabs(tmpdir):
        raise SystemExit("TMPDIR must be an absolute fresh directory")
    if not JAVAC.is_file() or not RT.is_file():
        raise SystemExit("pinned Java 8 toolchain unavailable")
    m = re.search(r'function _bootstrapMap\(\).*?return hex"([0-9a-f]+)";', ENGINE.read_text())
    if not m:
        raise SystemExit("inherited Map image not found")
    with tempfile.TemporaryDirectory(prefix="mc-properties-fixture-", dir=tmpdir) as d:
        d = Path(d)
        api = d / "api"
        bootout = d / "bootout"
        fixtureout = d / "fixtureout"
        (api / "java" / "util").mkdir(parents=True)
        (api / "java" / "util" / "Map.class").write_bytes(bytes.fromhex(m.group(1)))
        api_jar = d / "api.jar"
        bootout.mkdir()
        fixtureout.mkdir()
        subprocess.run(["jar", "cf", str(api_jar), "-C", str(api), "."], check=True)
        sources = [str(BOOT / x) for x in ("Dictionary.java", "Hashtable.java", "Properties.java")]
        subprocess.run([str(JAVAC), "-source", "8", "-target", "8", "-g:none",
                        "-bootclasspath", str(api_jar) + ":" + str(RT), "-d", str(bootout), *sources], check=True)
        subprocess.run([str(JAVAC), "-source", "8", "-target", "8", "-g:none",
                        "-bootclasspath", str(bootout) + ":" + str(api_jar) + ":" + str(RT),
                        "-d", str(fixtureout), str(HERE / "PropertiesProbe.java")], check=True)
        data = (fixtureout / "PropertiesProbe.class").read_bytes()
    (HERE / "PropertiesProbe.class.hex").write_text(data.hex() + "\n")
    (HERE / "pins.json").write_text(json.dumps({
        "javac": str(JAVAC), "release": 8, "name": "PropertiesProbe.class",
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
