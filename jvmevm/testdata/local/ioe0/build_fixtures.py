#!/usr/bin/env python3
"""Rebuild the trusted MC-IOE0 Java 8 fixture bytes and exact 24-root manifest."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ["IOE0Messages.java", "IOE0Origins.java", "IOE0Causes.java"]
# id, group, entry class, method, expected result, extra nested classes
ROWS = [
    ("throwableZero", "IOE0Messages", "IOE0Messages", "throwableZero", 1, []),
    ("throwableMessageIdentity", "IOE0Messages", "IOE0Messages", "throwableMessageIdentity", 1, []),
    ("exceptionMessageIdentity", "IOE0Messages", "IOE0Messages", "exceptionMessageIdentity", 1, []),
    ("ioZero", "IOE0Messages", "IOE0Messages", "ioZero", 1, []),
    ("ioLiteral", "IOE0Messages", "IOE0Messages", "ioLiteral", 1, []),
    ("fnfeConstructed", "IOE0Messages", "IOE0Messages", "fnfeConstructed", 1, []),
    ("eofNullVsEmpty", "IOE0Messages", "IOE0Messages", "eofNullVsEmpty", 1, []),
    ("virtualMessageOverride", "IOE0Messages", "IOE0Messages", "virtualMessageOverride", 1,
     ["IOE0Messages$MessageOverride.class"]),
    ("explicitAE", "IOE0Origins", "IOE0Origins", "explicitAE", 1, []),
    ("implicitAECause", "IOE0Origins", "IOE0Origins", "implicitAECause", 1, []),
    ("explicitNPE", "IOE0Origins", "IOE0Origins", "explicitNPE", 1, []),
    ("implicitNPE", "IOE0Origins", "IOE0Origins", "implicitNPE", 1, []),
    ("rethrowIdentity", "IOE0Origins", "IOE0Origins", "rethrowIdentity", 1, []),
    ("ordinaryEIIE", "IOE0Origins", "IOE0Origins", "ordinaryEIIE", 1, []),
    ("wrappedAE", "IOE0Origins", "IOE0Origins", "wrappedAE", 1, ["IOE0Origins$AEHolder.class"]),
    ("wrappedNPE", "IOE0Origins", "IOE0Origins", "wrappedNPE", 1, ["IOE0Origins$NPEHolder.class"]),
    ("eiieNull", "IOE0Causes", "IOE0Causes", "eiieNull", 1, []),
    ("eiieArgumentIdentity", "IOE0Causes", "IOE0Causes", "eiieArgumentIdentity", 1, []),
    ("vmWrapper", "IOE0Causes", "IOE0Causes", "vmWrapper", 1, ["IOE0Causes$WrapperHolder.class"]),
    ("sharedTwoWrappers", "IOE0Causes", "IOE0Causes", "sharedTwoWrappers", 1, []),
    ("customErrorUnwrapped", "IOE0Causes", "IOE0Causes", "customErrorUnwrapped", 1,
     ["IOE0Causes$CustomError.class", "IOE0Causes$ErrorHolder.class"]),
    ("failedClassLater", "IOE0Causes", "IOE0Causes", "failedClassLater", 3,
     ["IOE0Causes$FailedHolder.class"]),
    ("ioSubclassMessage", "IOE0Causes", "IOE0Causes", "ioSubclassMessage", 1,
     ["IOE0Causes$IOChild.class"]),
    ("constructorFailureAfterSuper", "IOE0Causes", "IOE0Causes", "constructorFailureAfterSuper", 1,
     ["IOE0Causes$BrokenIO.class"]),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix="jvmevm-ioe0-") as tmp:
        out = pathlib.Path(tmp)
        subprocess.run(["javac", "--release", "8", "-g:none", "-d", str(out)] +
                       [str(ROOT / "src" / source) for source in SOURCES], check=True)
        classes = ROOT / "classes"
        classes.mkdir(exist_ok=True)
        expected = {row[2] + ".class" for row in ROWS}
        expected.update(name for row in ROWS for name in row[5])
        for stale in classes.glob("*.class"):
            if stale.name not in expected:
                stale.unlink()
        for name in sorted(expected):
            shutil.copyfile(out / name, classes / name)
    source_hashes = {name: sha(ROOT / "src" / name) for name in SOURCES}
    fixtures = []
    for ident, group, entry_class, entry, result, extras in ROWS:
        source = entry_class + ".java"
        bundle = [entry_class + ".class"] + extras
        fixtures.append({
            "id": ident, "group": group, "source": source,
            "sourceSHA256": source_hashes[source], "entryClass": entry_class,
            "entry": entry, "args": [],
            "outcome": {"lifecycle": "RETURNED", "result": result,
                        "javaKind": 0, "javaClassHex": ""},
            "classes": [{"name": name, "sha256": sha(ROOT / "classes" / name)}
                        for name in bundle],
        })
    manifest = {"schema": 1, "compiler": "javac --release 8 -g:none", "fixtures": fixtures}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
