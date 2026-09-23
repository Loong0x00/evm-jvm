#!/usr/bin/env python3
"""Build generated Java-8 array controls; no external class/JAR input is read."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
CONTROL_CLASSES = (
    "SparseFloatMain",
    "SparseOneFloatMain",
    "DenseFloatMain",
    "SmallArrayMain",
    "ReferenceArrayMain",
)
# SparseOneFloatMain depends on SparseFloatMain; the five above enumerate every
# class used as a public main, and all five are independent raw bindings.
PAD_CLASS_COUNT = 66
BINDING_COUNT = 71
MAX_BINDING_BYTES = 471_911
MAX_CLASS_BYTES = 262_144
INITIAL_PAD_STRING_BYTES = 7000
PAD_STRING_SEARCH_LIMIT = 16000


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def compile_guest(java8_home, source_dir, classes_dir, padding_bytes):
    if classes_dir.exists():
        shutil.rmtree(classes_dir)
    classes_dir.mkdir(parents=True)
    padding = "x" * padding_bytes
    for pad in range(PAD_CLASS_COUNT):
        # A valid but never-called method carries one inert constant string. This
        # pads each image without creating thousands of guest static fields.
        source = ('public final class Pad%02d {\n' % pad
                  + '  public static int padding() { return "' + padding + '".length(); }\n'
                  + '}\n')
        (source_dir / ("Pad%02d.java" % pad)).write_text(source, encoding="ascii")
    sources = [str(SRC / (name + ".java")) for name in CONTROL_CLASSES]
    sources += [str(source_dir / ("Pad%02d.java" % n)) for n in range(PAD_CLASS_COUNT)]
    run([str(java8_home / "bin" / "javac"), "-g:none", "-encoding", "UTF-8",
         "-d", str(classes_dir), *sources], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    names = list(CONTROL_CLASSES) + ["Pad%02d" % n for n in range(PAD_CLASS_COUNT)]
    sizes = {name: (classes_dir / (name + ".class")).stat().st_size for name in names}
    total = sum(sizes.values())
    return names, sizes, total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="new output directory; must not already exist")
    parser.add_argument("--java8-home", type=Path,
                        default=Path(os.environ.get("JAVA8_HOME", "/usr/lib/jvm/java-8-openjdk")))
    opts = parser.parse_args()
    java8_home = opts.java8_home.resolve()
    javac = java8_home / "bin" / "javac"
    java = java8_home / "bin" / "java"
    if not javac.is_file() or not java.is_file():
        parser.error("Java 8 javac/java not found under " + str(java8_home))
    output = opts.output.resolve()
    if output.exists():
        parser.error("output already exists; choose a fresh directory: " + str(output))
    output.mkdir(parents=True)
    java_version = run([str(java), "-version"], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True).stdout.strip().splitlines()
    javac_version = run([str(javac), "-version"], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="array-controls-") as temp_name:
        temp = Path(temp_name)
        generated_sources = temp / "src"
        generated_sources.mkdir()
        classes = temp / "classes"
        names, sizes, baseline = compile_guest(java8_home, generated_sources, classes, 0)
        _, _, initial_size = compile_guest(java8_home, generated_sources, classes,
                                            INITIAL_PAD_STRING_BYTES)
        slope = (initial_size - baseline) // INITIAL_PAD_STRING_BYTES
        if slope <= 0:
            raise RuntimeError("padding size did not grow monotonically")
        padding_bytes = min(PAD_STRING_SEARCH_LIMIT,
                            max(0, INITIAL_PAD_STRING_BYTES
                                + (MAX_BINDING_BYTES - initial_size) // slope))
        over_budget_total = None
        names, sizes, total = compile_guest(java8_home, generated_sources, classes, padding_bytes)
        while total > MAX_BINDING_BYTES and padding_bytes > 0:
            padding_bytes -= 1
            names, sizes, total = compile_guest(java8_home, generated_sources, classes, padding_bytes)
        while padding_bytes < PAD_STRING_SEARCH_LIMIT:
            next_names, next_sizes, next_total = compile_guest(
                java8_home, generated_sources, classes, padding_bytes + 1)
            if next_total > MAX_BINDING_BYTES:
                over_budget_total = next_total
                # Rebuild the accepted length; never retain the over-budget build.
                names, sizes, total = compile_guest(java8_home, generated_sources,
                                                    classes, padding_bytes)
                break
            padding_bytes += 1
            names, sizes, total = next_names, next_sizes, next_total
        if total > MAX_BINDING_BYTES or len(names) != BINDING_COUNT:
            raise RuntimeError("generated bindings exceed the frozen 71 / 471911 bound")
        if max(sizes.values()) > MAX_CLASS_BYTES:
            raise RuntimeError("one generated class exceeds 262144 bytes")

        # Run each guest entry independently so at most one 65536-element guest
        # array is live per execution. These are host-Java-8 controls, not EVM claims.
        for entry in CONTROL_CLASSES:
            run([str(java), "-cp", str(classes), entry], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        oracle_classes = temp / "oracle"
        oracle_classes.mkdir()
        run([str(javac), "-g:none", "-encoding", "UTF-8", "-cp", str(classes),
             "-d", str(oracle_classes), str(SRC / "ArrayHostOracle.java")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        oracle = run([str(java), "-cp", str(classes) + os.pathsep + str(oracle_classes),
                      "ArrayHostOracle"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True).stdout
        expected_oracle = ('{"sparseOne":1,"sparseSeveral":7,"denseFloatLength":65536,'
                           '"smallArrays":31,"referenceArray":5}\n')
        if oracle != expected_oracle:
            raise RuntimeError("unexpected Java-8 oracle result: " + repr(oracle))

        binding_dir = output / "bindings"
        binding_dir.mkdir()
        image_info = []
        for name in names:
            image = (classes / (name + ".class")).read_bytes()
            (binding_dir / (name + ".class")).write_bytes(image)
            image_info.append({"name": name, "bytes": len(image), "sha256": sha256(image)})
        (output / "oracle-results.txt").write_text(oracle, encoding="ascii")
        source_info = {
            p.name: {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes())}
            for p in sorted(SRC.glob("*.java"))
        }
        manifest = {
            "schema": 1,
            "purpose": "generated Java-8 array stress/control bindings only",
            "toolchain": "Java 8 javac/java from " + str(java8_home),
            "bindingCount": len(image_info),
            "aggregateBindingBytes": total,
            "aggregateByteLimit": MAX_BINDING_BYTES,
            "perClassByteLimit": MAX_CLASS_BYTES,
            "paddingClasses": PAD_CLASS_COUNT,
            "constantStringBytesPerPaddingClass": padding_bytes,
            "nextPaddingAggregateBytes": over_budget_total,
            "sources": source_info,
            "hostOracle": {"source": "src/ArrayHostOracle.java",
                           "sourceSHA256": source_info["ArrayHostOracle.java"]["sha256"],
                           "result": oracle.rstrip("\n")},
            "toolchainVersions": {"java": java_version, "javac": javac_version},
            "bindings": image_info,
            "safety": "No original class, JAR, resource, sibling worktree, or network input is read. No class/ZIP parsing is done by the builder. Generated classes are not guest execution results.",
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                encoding="ascii")
    print(json.dumps({"output": str(output), "bindingCount": BINDING_COUNT,
                      "aggregateBindingBytes": total, "aggregateByteLimit": MAX_BINDING_BYTES,
                      "paddingStringBytesPerClass": padding_bytes, "hostOracle": oracle.rstrip("\n")},

                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
