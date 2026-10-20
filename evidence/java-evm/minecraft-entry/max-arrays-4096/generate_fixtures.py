#!/usr/bin/env python3
"""Copy retained generated controls and add packed-float and ordinary-array-capacity fixtures.

Only trusted, locally generated Java-8 inputs are compiled here. This script does
not read original Minecraft artifacts or execute any fixture program on the host.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == ROOT / "build"
assert OUT.name.startswith("java-diff-mc-max-arrays-4096-fixtures-")
assert not OUT.exists(), "fixture outputs are append-only"

SOURCE_FIXTURES = ROOT / "evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures"
shutil.copytree(SOURCE_FIXTURES, OUT)
base = json.loads((OUT / "packed-array-oracle.json").read_text())


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


# The pre-existing generated packed-float controls are extended to cover the
# Java-8 oracle's zero-filled tail at a few lengths without changing its prefix.
classes = OUT / "oracle-classes"
classes.mkdir()
oracle = HERE.parent / "packed-float-bulk-u32/tools/RawFloatOracle.java"
subprocess.run(["javac", "--release", "8", "-d", str(classes), str(oracle)],
               cwd=ROOT, check=True)
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
for length in (1024, 1025, 1031):
    label = f"float-tail-{length}"
    zip_path = OUT / f"{label}.zip"
    class_dir = OUT / f"{label}-classes"
    class_dir.mkdir()
    with zipfile.ZipFile(OUT / "packed-array-oracle.zip") as archive, \
            zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as target:
        assert set(archive.namelist()) == set(base["entries"])
        for name in archive.namelist():
            data = archive.read(name)
            needle = b"\x11\x04\x00"
            if length != 1024:
                assert data.count(needle) == 1
                data = data.replace(needle, b"\x11" + length.to_bytes(2, "big"), 1)
            target.writestr(name, data)
            (class_dir / name).write_bytes(data)
    result = subprocess.run(
        ["java", "-cp", str(class_dir) + os.pathsep + str(classes), "RawFloatOracle"],
        cwd=ROOT, env=env, text=True, capture_output=True, check=True,
    )
    values = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert len(values) == length and values[:1024] == base["hostOutput"]
    assert all(value == "00000000" for value in values[1024:])
    with zipfile.ZipFile(zip_path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    row = {
        "entries": base["entries"],
        "bindingCount": base["bindingCount"],
        "bootstrapCount": base["bootstrapCount"],
        "totalClassBytes": sum(map(len, entries.values())),
        "classBytes": {name: len(data) for name, data in entries.items()},
        "classSHA256": {name: sha(data) for name, data in entries.items()},
        "zipSHA256": sha(zip_path.read_bytes()),
        "java8HostOracle": True,
        "tailLength": length,
        "hostOutput": values,
    }
    (OUT / f"{label}.json").write_text(json.dumps(row, indent=2) + "\n")


# The entry contract installs one canonical empty main String[] argument before
# main. Each fixture then allocates target-1 empty primitive arrays, so total
# ordinary arrays reach target; only 4097 should OOM at the 4096 cap.
capacity_source = (
    "package generated;\n"
    "public final class ArrayCapacity{target} {{\n"
    "  public static void main(String[] args) {{\n"
    "    for (int i = 0; i < {allocations}; i++) {{\n"
    "      int[] discarded = new int[0];\n"
    "    }}\n"
    "  }}\n"
    "}}\n"
)
capacity_rows = {}
for target in (2048, 2049, 4096, 4097):
    label = f"array-capacity-{target}"
    class_name = f"ArrayCapacity{target}"
    binary_name = f"generated/{class_name}"
    entry_name = binary_name + ".class"
    # The canonical empty main String[] is one ordinary array; each test class
    # allocates target-1 additional int[] arrays so the exact total reaches target.
    allocations = target - 1
    src_dir = OUT / f"{label}-src/generated"
    cls_dir = OUT / f"{label}-classes"
    src_dir.mkdir(parents=True)
    cls_dir.mkdir()
    java_source = src_dir / f"{class_name}.java"
    java_source.write_text(capacity_source.format(target=target, allocations=allocations))
    subprocess.run(
        ["javac", "--release", "8", "-g:none", "-d", str(cls_dir), str(java_source)],
        cwd=ROOT, check=True,
    )
    class_file = cls_dir / f"{binary_name}.class"
    class_bytes = class_file.read_bytes()
    zip_path = OUT / f"{label}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(entry_name, class_bytes)
    row = {
        "entries": [entry_name],
        "bindingCount": 1,
        "bootstrapCount": base["bootstrapCount"],
        "totalClassBytes": len(class_bytes),
        "classBytes": {entry_name: len(class_bytes)},
        "classSHA256": {entry_name: sha(class_bytes)},
        "zipSHA256": sha(zip_path.read_bytes()),
        "generatedBy": "javac --release 8 -g:none",
        "hostProgramExecution": False,
        "entryClass": binary_name,
        "requestedOrdinaryArrays": target,
        "explicitAllocations": allocations,
        "implicitMainStringArray": 1,
        "expectedOrdinaryArrays": min(target, 4096),
        "expectedLifecycle": 3 if target == 4097 else 2,
        "expectedJavaKind": 7 if target == 4097 else 0,
        "expectedJavaClass": "java/lang/OutOfMemoryError" if target == 4097 else "",
    }
    (OUT / f"{label}.json").write_text(json.dumps(row, indent=2) + "\n")
    capacity_rows[target] = row

print(json.dumps({
    "generatedOnly": True,
    "floatTailLengths": [1024, 1025, 1031],
    "arrayCapacityTargets": sorted(capacity_rows),
    "arrayAllocations": {str(key): row["explicitAllocations"]
                             for key, row in capacity_rows.items()},
    "hostExecution": False,
}, indent=2))
