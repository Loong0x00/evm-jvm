#!/usr/bin/env python3
"""Rebuild the trusted MC-TL0 Java 8 fixture bytes and manifest."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = [
    "TL0Construction.java", "TL0Identity.java", "TL0Initialization.java",
    "TL0Outcome.java", "TL0ConstructorSelf.java",
]
# id, group, entry class, method, args, lifecycle, result, kind, class bytes, bundle
ROWS = [
    ("construction-exact-exception", "TL0Construction", "TL0Construction", "exactException", [], "RETURNED", 1, 0, "", ["TL0Construction.class"]),
    ("construction-exact-arithmetic", "TL0Construction", "TL0Construction", "exactArithmetic", [], "RETURNED", 1, 0, "", ["TL0Construction.class"]),
    ("construction-custom-fields", "TL0Construction", "TL0Construction", "customFields", [17], "RETURNED", 17, 0, "", ["TL0Construction.class", "TL0Construction$Problem.class"]),
    ("construction-hierarchy-fields", "TL0Construction", "TL0Construction", "hierarchyFields", [], "RETURNED", 37, 0, "", ["TL0Construction.class", "TL0Construction$Problem.class", "TL0Construction$Child.class"]),
    ("construction-distinct", "TL0Construction", "TL0Construction", "distinct", [], "RETURNED", 1, 0, "", ["TL0Construction.class", "TL0Construction$Problem.class"]),
    ("construction-ctor-effects", "TL0Construction", "TL0Construction", "ctorEffects", [], "RETURNED", 11, 0, "", ["TL0Construction.class", "TL0Construction$Problem.class"]),
    ("identity-local-catch", "TL0Identity", "TL0Identity", "localCatch", [], "RETURNED", 1, 0, "", ["TL0Identity.class", "TL0Identity$Problem.class"]),
    ("identity-field-catch", "TL0Identity", "TL0Identity", "fieldCatch", [], "RETURNED", 1, 0, "", ["TL0Identity.class", "TL0Identity$Problem.class"]),
    ("identity-array-catch", "TL0Identity", "TL0Identity", "arrayCatch", [], "RETURNED", 1, 0, "", ["TL0Identity.class", "TL0Identity$Problem.class"]),
    ("identity-call-unwind", "TL0Identity", "TL0Identity", "callUnwind", [], "RETURNED", 1, 0, "", ["TL0Identity.class", "TL0Identity$Problem.class"]),
    ("identity-rethrow", "TL0Identity", "TL0Identity", "rethrow", [], "RETURNED", 1, 0, "", ["TL0Identity.class", "TL0Identity$Problem.class"]),
    ("identity-known-subclass-catch", "TL0Identity", "TL0Identity", "knownSubclassCatch", [], "RETURNED", 1, 0, "", ["TL0Identity.class", "TL0Identity$KnownChild.class"]),
    ("initialization-failing-constructor", "TL0Initialization", "TL0Initialization", "failingConstructor", [], "RETURNED", 7, 0, "", ["TL0Initialization.class", "TL0Initialization$Problem.class", "TL0Initialization$Broken.class"]),
    ("initialization-init-before-new", "TL0Initialization", "TL0Initialization", "initBeforeNew", [], "RETURNED", 3, 0, "", ["TL0Initialization.class", "TL0Initialization$BeforeNew.class"]),
    ("initialization-wraps-non-error", "TL0Initialization", "TL0Initialization", "wrapsNonError", [], "RETURNED", 1, 0, "", ["TL0Initialization.class", "TL0Initialization$Problem.class", "TL0Initialization$WrapInit.class"]),
    ("initialization-propagates-custom-error", "TL0Initialization", "TL0Initialization", "propagatesCustomError", [], "RETURNED", 1, 0, "", ["TL0Initialization.class", "TL0Initialization$CustomError.class", "TL0Initialization$ErrorInit.class"]),
    ("initialization-second-use", "TL0Initialization", "TL0Initialization", "secondUse", [], "RETURNED", 3, 0, "", ["TL0Initialization.class", "TL0Initialization$Problem.class", "TL0Initialization$SecondInit.class"]),
    ("outcome-exact-known", "TL0Outcome", "TL0Outcome", "exactKnown", [], "UNCAUGHT_JAVA", 0, 1, "", ["TL0Outcome.class"]),
    ("outcome-custom", "TL0Outcome", "TL0Outcome", "custom", [], "UNCAUGHT_JAVA", 0, 0, "TL0Outcome$Problem", ["TL0Outcome.class", "TL0Outcome$Problem.class"]),
    ("outcome-subclass-known", "TL0Outcome", "TL0Outcome", "subclassKnown", [], "UNCAUGHT_JAVA", 0, 0, "TL0Outcome$KnownChild", ["TL0Outcome.class", "TL0Outcome$KnownChild.class"]),
    ("constructor-self-direct", "TL0ConstructorSelf", "TL0ConstructorSelf", "direct", [], "RETURNED", 101, 0, "", ["TL0ConstructorSelf.class", "TL0ConstructorSelf$Direct.class"]),
    ("constructor-self-through-call", "TL0ConstructorSelf", "TL0ConstructorSelf", "throughCall", [], "RETURNED", 102, 0, "", ["TL0ConstructorSelf.class", "TL0ConstructorSelf$Through.class"]),
    ("constructor-self-escaped-after-failure", "TL0ConstructorSelf", "TL0ConstructorSelf", "escapedAfterFailure", [], "RETURNED", 103, 0, "", ["TL0ConstructorSelf.class", "TL0ConstructorSelf$Escaped.class"]),
    ("constructor-self-in-class-init", "TL0ConstructorSelf", "TL0ConstructorSelf", "inClassInit", [], "RETURNED", 201, 0, "", ["TL0ConstructorSelf.class", "TL0ConstructorSelf$InitSelf.class", "TL0ConstructorSelf$InitHolder.class"]),
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    with tempfile.TemporaryDirectory(prefix="jvmevm-tl0-") as tmp:
        out = pathlib.Path(tmp)
        subprocess.run(["javac", "--release", "8", "-g:none", "-d", str(out)] + [str(ROOT / "src" / x) for x in SOURCES], check=True)
        classes = ROOT / "classes"
        classes.mkdir(exist_ok=True)
        expected = {name for row in ROWS for name in row[9]}
        for stale in classes.glob("*.class"):
            if stale.name not in expected:
                stale.unlink()
        for name in sorted(expected):
            shutil.copyfile(out / name, classes / name)
    source_hashes = {name: sha(ROOT / "src" / name) for name in SOURCES}
    fixtures = []
    for ident, group, entry_class, entry, args, lifecycle, result, kind, java_class, bundle in ROWS:
        source = entry_class + ".java"
        fixtures.append({
            "id": ident, "group": group, "source": source,
            "sourceSHA256": source_hashes[source], "entryClass": entry_class,
            "entry": entry, "args": args,
            "outcome": {"lifecycle": lifecycle, "result": result,
                        "javaKind": kind, "javaClassHex": java_class.encode().hex()},
            "classes": [{"name": name, "sha256": sha(ROOT / "classes" / name)} for name in bundle],
        })
    manifest = {"schema": 1, "compiler": "javac --release 8 -g:none", "fixtures": fixtures}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

if __name__ == "__main__":
    main()
