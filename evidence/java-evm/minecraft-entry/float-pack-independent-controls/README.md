# Generated float checkpoint sizing controls (TEST ONLY)

This folder is an independent, offline reference for the measured float-array
checkpoint packing question. It is **not an EVM test, acceptance result, or
Minecraft run**. It reads no original Minecraft JAR/class/resource/world or
guest checkpoint; it performs no class/bytecode/source injection and changes no
runtime, guest, bootstrap, Solidity, or active checkpoint-stage code. The Java
oracle only generates standalone values. The Python model compares candidate
byte counts and exercises its own byte encoders/decoders; it has no EVM or
checkpoint-state authority.

## Reproduce

Requirements: a JDK with `javac --release 8`, `java`, Python 3, and `sha256sum`.
From the repository root (or any directory):

```sh
evidence/java-evm/minecraft-entry/float-pack-independent-controls/run.sh
```

The script compiles `FloatFixtureGenerator.java` to Java 8 classfile version
52, generates a fresh temporary oracle, runs the independent Python verifier,
compares every generated file and report to the pinned copies here, and checks
`SHA256SUMS`. It does not overwrite evidence. The generated float contents are
big-endian `Float.floatToRawIntBits` u32 words, so signed zero and NaN payloads
are retained; the complete expected contents are the `.u32be` oracle files,
not merely a digest or a hand-picked sample. `oracle/oracle.json` pins fixture
lengths and nonzero raw-bit counts. `reference-report.json` contains each full
fixture SHA-256, sizing choice, threshold, control-array contents/hashes, and
refusal results.

The generator and manifest use only Java 8 APIs. This run environment has a
newer host JDK; `--release 8` enforces Java 8 compilation/API targeting, and the
runner verifies classfile major 52. This is a generated host oracle only, not
execution by the EVM guest Java runtime.

## Generated oracle inventory

Every float fixture includes raw patterns for `-0.0` (`80000000`), two distinct
positive quiet-NaN payloads (`7fc00001`, `7fc12345`), a negative quiet-NaN
payload (`ffc54321`), positive and negative infinity (`7f800000`, `ff800000`),
and untouched `+0.0` cells (`00000000`). The remaining nonzero cells are
repeatable finite bit patterns. Nonzero means raw u32 bits are not zero, so
negative zero is deliberately counted as nonzero, matching the raw-cell sizing
model.

| Oracle file | Length | Nonzero raw cells | Old sparse bytes | Packed u32 bytes | Dense u64 bytes | Reference choice |
|---|---:|---:|---:|---:|---:|---|
| `float-16-small.u32be` | 16 | 8 | 100 | 64 | 128 | old sparse (packed below minimum length) |
| `float-1024-sparse.u32be` | 1,024 | 32 | 388 | 4,096 | 8,192 | old sparse |
| `float-1024-dense.u32be` | 1,024 | 400 | 4,804 | 4,096 | 8,192 | packed float u32 |
| `float-65536-sparse.u32be` | 65,536 | 128 | 1,540 | 262,144 | 524,288 | old sparse |
| `float-65536-dense.u32be` | 65,536 | 30,000 | 360,004 | 262,144 | 524,288 | packed float u32 |

Additional non-float controls are an ordered reference array
`["alpha", null, "alpha", "guest", ""]` and an eight-cell raw u64 long
array including zero, signed extrema, high-bit values, and a NaN-shaped integer
pattern. Their exact contents and SHA-256 hashes are in `reference-report.json`;
they are controls, never eligible for float packing.

## Offline sizing and crossover

The reference deliberately uses the frozen preparation's stated size formulas
(not measured Solidity gas):

* old sparse: `4 + 12*n` bytes (u32 count; each pair is u32 index + u64 value);
* proposed packed float: `4*L` bytes;
* dense: `8*L` bytes.

Packed float is eligible only for length `L >= 1024` and selected only when it
is **strictly** smaller than the old sparse record. Otherwise the old choice is
sparse when its record is strictly smaller than dense, and dense on a tie or
win. Solving `4*L < 4 + 12*n` gives:

| Length L | Tie at n | First packed strict win | Bytes at tie | Sparse / packed at first win |
|---:|---:|---:|---:|---:|
| 1,024 | 341 | **342** | 4,096 / 4,096 | 4,108 / 4,096 |
| 65,536 | 21,845 | **21,846** | 262,144 / 262,144 | 262,156 / 262,144 |

The verifier checks the equality point and first strict win for both lengths,
then applies the model to all generated oracle cells. It independently roundtrips
every float fixture through four-byte big-endian words, and positive-tests the
canonical packed decode on both dense fixtures plus an old sparse roundtrip.

Refusal controls cover truncated and overlong packed payloads, wrong array kind,
packed/sparse and unknown flag bits, a too-short array, packed data that does not
strictly win, a u64 source cell with high bits, old sparse count/payload mismatch,
old sparse contents mismatch, and old sparse bytes that are noncanonical after
the packed choice wins. These are Python model tests, **not evidence that any
EVM decoder currently implements or accepts this format**.

## Pinned evidence

`SHA256SUMS` pins the Java and Python sources, runner, readme, generated oracle
files, and report. The report also pins per-fixture, reference-control,
long-control, and manifest SHA-256 values. No official checkpoint bytes are
included. The only Minecraft-related context motivating this test is the
published aggregate observation in the preparation plan; this experiment does
not ingest or reproduce the underlying guest input.
