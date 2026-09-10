#!/usr/bin/env python3
"""Rebuild the trusted MC-SC0 Java 8 fixture bytes and manifest."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ["SC0Chars.java", "SC0CopyIntern.java", "SC0Flow.java"]
# id, group, entry class, method, args, expected result, bundle
ROWS = [
    ("chars-empty", "SC0Chars", "SC0Chars", "empty", [], 0, ["SC0Chars.class"]),
    ("chars-ascii-length", "SC0Chars", "SC0Chars", "asciiLength", [], 5, ["SC0Chars.class"]),
    ("chars-nul-units", "SC0Chars", "SC0Chars", "nulUnits", [], 1, ["SC0Chars.class"]),
    ("chars-surrogate-pair", "SC0Chars", "SC0Chars", "surrogatePair", [], 1, ["SC0Chars.class"]),
    ("chars-isolated-high", "SC0Chars", "SC0Chars", "isolatedHigh", [], 55296, ["SC0Chars.class"]),
    ("chars-isolated-low", "SC0Chars", "SC0Chars", "isolatedLow", [], 56320, ["SC0Chars.class"]),
    ("chars-defensive", "SC0Chars", "SC0Chars", "defensive", [], 97099, ["SC0Chars.class"]),
    ("chars-hash-cache", "SC0Chars", "SC0Chars", "hashCache", [], 2112, ["SC0Chars.class"]),
    ("copy-distinct", "SC0CopyIntern", "SC0CopyIntern", "copyDistinct", [], 1, ["SC0CopyIntern.class"]),
    ("copy-hash", "SC0CopyIntern", "SC0CopyIntern", "copyHash", [], 2112, ["SC0CopyIntern.class"]),
    ("copy-category2-caller", "SC0CopyIntern", "SC0CopyIntern", "category2Caller", [], 1, ["SC0CopyIntern.class"]),
    ("copy-literal-intern", "SC0CopyIntern", "SC0CopyIntern", "literalCopyIntern", [], 111, ["SC0CopyIntern.class"]),
    ("copy-constructed-first", "SC0CopyIntern", "SC0CopyIntern", "constructedFirst", [], 111, ["SC0CopyIntern.class"]),
    ("copy-earlier-handle-insert", "SC0CopyIntern", "SC0CopyIntern", "earlierHandleInsert", [], 1, ["SC0CopyIntern.class"]),
    ("copy-hash-collision", "SC0CopyIntern", "SC0CopyIntern", "hashCollision", [], 1, ["SC0CopyIntern.class"]),
    ("copy-interface-dispatch", "SC0CopyIntern", "SC0CopyIntern", "interfaceDispatch", [], 1, ["SC0CopyIntern.class"]),
    ("flow-null-chars", "SC0Flow", "SC0Flow", "nullChars", [], 1, ["SC0Flow.class"]),
    ("flow-null-copy", "SC0Flow", "SC0Flow", "nullCopy", [], 1, ["SC0Flow.class"]),
    ("flow-fail-then-valid", "SC0Flow", "SC0Flow", "failThenValid", [], 12, ["SC0Flow.class"]),
    ("flow-chars-in-clinit", "SC0Flow", "SC0Flow", "charsInClinit", [], 1, ["SC0Flow.class", "SC0Flow$CharsHolder.class"]),
    ("flow-init-failure-then-ncdfe", "SC0Flow", "SC0Flow", "initFailureThenNCDFE", [], 3, ["SC0Flow.class", "SC0Flow$BrokenHolder.class"]),
    ("flow-loop64", "SC0Flow", "SC0Flow", "loop64", [], 64076, ["SC0Flow.class"]),
    ("flow-argument-failure", "SC0Flow", "SC0Flow", "argumentFailure", [], 1, ["SC0Flow.class"]),
    ("flow-throwable-integration", "SC0Flow", "SC0Flow", "throwableIntegration", [], 1, ["SC0Flow.class", "SC0Flow$StringThrowable.class"]),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix="jvmevm-sc0-") as tmp:
        out = pathlib.Path(tmp)
        subprocess.run(["javac", "--release", "8", "-g:none", "-d", str(out)] +
                       [str(ROOT / "src" / source) for source in SOURCES], check=True)
        classes = ROOT / "classes"
        classes.mkdir(exist_ok=True)
        expected = {name for row in ROWS for name in row[6]}
        for stale in classes.glob("*.class"):
            if stale.name not in expected:
                stale.unlink()
        for name in sorted(expected):
            shutil.copyfile(out / name, classes / name)
    source_hashes = {name: sha(ROOT / "src" / name) for name in SOURCES}
    fixtures = []
    for ident, group, entry_class, entry, args, result, bundle in ROWS:
        source = entry_class + ".java"
        fixtures.append({
            "id": ident, "group": group, "source": source,
            "sourceSHA256": source_hashes[source], "entryClass": entry_class,
            "entry": entry, "args": args,
            "outcome": {"lifecycle": "RETURNED", "result": result,
                        "javaKind": 0, "javaClassHex": ""},
            "classes": [{"name": name, "sha256": sha(ROOT / "classes" / name)}
                        for name in bundle],
        })
    manifest = {"schema": 1, "compiler": "javac --release 8 -g:none", "fixtures": fixtures}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
