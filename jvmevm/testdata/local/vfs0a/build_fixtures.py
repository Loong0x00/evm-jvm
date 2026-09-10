#!/usr/bin/env python3
"""Rebuild the trusted MC-VFS0a Java-8 fixture bytes and exact 24-root manifest."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ["VFS0aPaths.java", "VFS0aStreams.java", "VFS0aErrors.java"]
# id, group, entry class, raw (path,data,readOnly) seeds
ROWS = [
    ("existsMissing", "Paths", "VFS0aPaths", []),
    ("seedFile", "Paths", "VFS0aPaths", [(b"seed.bin", b"seed", False)]),
    ("seedDirectory", "Paths", "VFS0aPaths", [(b"seed-dir/leaf", b"x", False)]),
    ("mkdirOnce", "Paths", "VFS0aPaths", []),
    ("mkdirsNested", "Paths", "VFS0aPaths", []),
    ("readonlyMkdir", "Paths", "VFS0aPaths", [(b"locked", b"x", True)]),
    ("lexicalAlias", "Paths", "VFS0aPaths", []),
    ("comparablePaths", "Paths", "VFS0aPaths", []),
    ("readSingleEOF", "Streams", "VFS0aStreams", [(b"single", b"A", False)]),
    ("readBulkSlice", "Streams", "VFS0aStreams", [(b"bulk", b"ABC", False)]),
    ("createRoundtrip", "Streams", "VFS0aStreams", []),
    ("truncate", "Streams", "VFS0aStreams", [(b"truncate", b"old-data", False)]),
    ("append", "Streams", "VFS0aStreams", [(b"append", b"AB", False)]),
    ("twoWriterGap", "Streams", "VFS0aStreams", []),
    ("staleReadCursor", "Streams", "VFS0aStreams", [(b"stale", b"ABCDE", False)]),
    ("closeTwice", "Streams", "VFS0aStreams", [(b"close", b"A", False)]),
    ("nullFileArg", "Errors", "VFS0aErrors", []),
    ("missingInputMessage", "Errors", "VFS0aErrors", []),
    ("missingOutputParentMessage", "Errors", "VFS0aErrors", []),
    ("directoryOpenMessage", "Errors", "VFS0aErrors", [(b"directory/leaf", b"x", False)]),
    ("readOnlyOutputMessage", "Errors", "VFS0aErrors", [(b"readonly", b"x", True)]),
    ("nullArrayBeforeClosed", "Errors", "VFS0aErrors", [(b"precedence", b"x", False)]),
    ("boundsBeforeClosed", "Errors", "VFS0aErrors", []),
    ("zeroLengthClosed", "Errors", "VFS0aErrors", [(b"zero", b"x", False)]),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix="jvmevm-vfs0a-") as tmp:
        out = pathlib.Path(tmp)
        subprocess.run(["javac", "--release", "8", "-g:none", "-d", str(out)] +
                       [str(ROOT / "src" / source) for source in SOURCES], check=True)
        classes = ROOT / "classes"
        classes.mkdir(exist_ok=True)
        expected = {owner + ".class" for _, _, owner, _ in ROWS}
        for stale in classes.glob("*.class"):
            if stale.name not in expected:
                stale.unlink()
        for name in sorted(expected):
            shutil.copyfile(out / name, classes / name)
    source_hashes = {name: digest(ROOT / "src" / name) for name in SOURCES}
    fixtures = []
    for ident, group, owner, seeds in ROWS:
        source = owner + ".java"
        class_name = owner + ".class"
        fixtures.append({
            "id": ident,
            "group": group,
            "source": source,
            "sourceSHA256": source_hashes[source],
            "entryClass": owner,
            "entry": ident,
            "args": [],
            "seeds": [
                {"pathHex": path.hex(), "dataHex": data.hex(), "readOnly": read_only}
                for path, data, read_only in seeds
            ],
            "outcome": {"lifecycle": "RETURNED", "result": 1,
                        "javaKind": 0, "javaClassHex": ""},
            "classes": [{"name": class_name, "sha256": digest(ROOT / "classes" / class_name)}],
        })
    manifest = {"schema": 1, "compiler": "javac --release 8 -g:none", "fixtures": fixtures}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
