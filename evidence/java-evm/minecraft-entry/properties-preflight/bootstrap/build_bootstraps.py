#!/usr/bin/env python3
"""Rebuild the three owned Java 8 Properties bootstrap images.

The prior Map image is extracted only from this isolated COPY's engine source;
it is not rebuilt or appended.  Compilation has no host execution role.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine" / "MCEntryInterpreter.sol"
SRC = ROOT / "bootstrap" / "java" / "util"
JAVA_HOME = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JAVA_HOME / "bin" / "javac"
RT = JAVA_HOME / "jre" / "lib" / "rt.jar"


def main():
    if not JAVAC.is_file() or not RT.is_file():
        raise SystemExit("pinned Java 8 javac/rt.jar unavailable")
    tmpdir = os.environ.get("TMPDIR", "")
    if not tmpdir or not os.path.isabs(tmpdir):
        raise SystemExit("TMPDIR must be an absolute fresh directory")
    text = ENGINE.read_text()
    m = re.search(r'function _bootstrapMap\(\).*?return hex"([0-9a-f]+)";', text)
    if not m:
        raise SystemExit("could not locate inherited Map image")
    with tempfile.TemporaryDirectory(prefix="mc-properties-bootstrap-", dir=tmpdir) as work:
        work = Path(work)
        api = work / "api"
        out = work / "out"
        (api / "java" / "util").mkdir(parents=True)
        out.mkdir()
        (api / "java" / "util" / "Map.class").write_bytes(bytes.fromhex(m.group(1)))
        api_jar = work / "api.jar"
        subprocess.run(["jar", "cf", str(api_jar), "-C", str(api), "."], check=True)
        sources = [str(SRC / n) for n in ("Dictionary.java", "Hashtable.java", "Properties.java")]
        subprocess.run([
            str(JAVAC), "-source", "8", "-target", "8", "-g:none",
            "-bootclasspath", str(api_jar) + ":" + str(RT), "-d", str(out), *sources,
        ], check=True)
        pins = []
        for name in ("Dictionary", "Hashtable", "Properties"):
            data = (out / "java" / "util" / (name + ".class")).read_bytes()
            target = SRC / (name + ".class.hex")
            target.write_text(data.hex() + "\n")
            pins.append({"name": "java/util/" + name, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
    (ROOT / "bootstrap" / "pins.json").write_text(json.dumps({
        "javac": str(JAVAC), "release": 8, "inheritedMapSHA256": hashlib.sha256(bytes.fromhex(m.group(1))).hexdigest(),
        "images": pins,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
