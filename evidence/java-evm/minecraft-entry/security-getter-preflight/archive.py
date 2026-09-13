#!/usr/bin/env python3
"""Curate reproducible generated-only preflight evidence; never copy LevelDB or binaries."""
from pathlib import Path
import hashlib, json, shutil, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: archive.py BUILD_DIR RUN_DIR")
    build, run = map(lambda x: Path(x).resolve(), sys.argv[1:])
    for value in (build, run):
        if value.parent != ROOT / "build" or not value.name.startswith("java-diff-mc-security-getter-"):
            raise SystemExit("only fresh security-getter build directories may be archived")
    archive = HERE / "candidate-guarded"
    results = HERE / "runs" / "generated-guarded"
    if archive.exists() or results.exists():
        raise SystemExit("refusing to overwrite historical evidence")
    for name in ("pins.json", "bootstrap-build.log", "engine-build.log", "coordinator-build.log",
                 "gofmt.log", "driver-build.log", "driver-vet.log", "executed_generated_driver.go.txt"):
        copy_file(build / name, archive / name)
    for item in sorted(build.glob("*.watchdog.json")):
        copy_file(item, archive / item.name)
    for folder, files in {
        "engine": ("MCEntryInterpreter.sol", "build.js", "MCEntryInterpreter.abi.json", "MCEntryInterpreter.init.hex", "MCEntryInterpreter.runtime.hex", "MCEntryInterpreter.json"),
        "coordinator": ("MCEntryCoordinator.sol", "build.js", "MCEntryCoordinator.abi.json", "MCEntryCoordinator.init.hex", "MCEntryCoordinator.runtime.hex", "MCEntryCoordinator.json"),
        "bootstrap": ("pins.json", "java/lang/System.java", "java/lang/System.class.hex"),
    }.items():
        for name in files:
            copy_file(build / folder / name, archive / folder / name)
    for name in ("summary.json", "canonical.log", "canonical.process.json", "java8-compile.log",
                 "java8-compile.process.json", "java8-getter-oracle.log", "java8-getter-oracle.process.json",
                 "java8-setter-oracle.log", "java8-setter-oracle.process.json", "SecurityGetterProbe.zip",
                 "SecuritySetterRefusal.zip"):
        copy_file(run / name, results / name)
    for item in sorted(run.glob("*.watchdog.json")):
        copy_file(item, results / item.name)
    for label in ("getter-q1", "getter-q7", "getter-q4096", "setter-direct"):
        copy_file(run / label / "durable-head.json", results / label / "durable-head.json")
        for item in sorted((run / label / "checkpoints").glob("*.bin")):
            copy_file(item, results / label / "checkpoints" / item.name)
        for item in sorted((run / "reports" / label).glob("*.json")):
            copy_file(item, results / "reports" / label / item.name)
    entries = []
    for item in sorted(HERE.rglob("*")):
        if item.is_file() and item.name not in ("SHA256SUMS", "archive-files.json"):
            entries.append({"path": str(item.relative_to(HERE)), "bytes": item.stat().st_size,
                            "sha256": hashlib.sha256(item.read_bytes()).hexdigest()})
    (HERE / "archive-files.json").write_text(json.dumps(entries, indent=2) + "\n")
    (HERE / "SHA256SUMS").write_text("".join(x["sha256"] + "  " + x["path"] + "\n" for x in entries))


if __name__ == "__main__":
    main()
