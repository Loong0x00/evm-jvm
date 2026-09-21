# Generated `PrintStream` direct-`OutputStream` subtype stage

This generated-only stage implements `JAVA_EVM_MC_PRINT_STREAM_OUTPUT_STREAM_PREPARATION.md` from accepted generated parent evidence `parent-98e55f145`. It changes exactly bootstrap image83, `java/io/PrintStream`.

The canonical guest class now directly extends the retained `java/io/OutputStream`; its constructor invokes `OutputStream.<init>()`. It retains the bounded guest-only `println(String)` reference sink and `print(char)` code-unit sink. Because `OutputStream.write(int)` is abstract, image83 adds only the required concrete bridge: `write(int)` stores `(char) (value & 0xff)` in the existing `print` sink. It provides no byte-array write, flush, close, formatting, encoding, console, file, or host output behavior.

The generated focus assigns `PrintStream` to `OutputStream`, checks `instanceof` in both directions, invokes virtual `OutputStream.write(0x1234)`, and verifies identity plus retained `println`/`print` sinks. Read-only checkpoint inspection proves the canonical `PrintStream` handle, retained line reference, and low-byte sink value `0x34`. A separate no-use root proves both `OutputStream` and `PrintStream` remain uninitialized. Canonical raw `PrintStream` replacement remains rejected without publication.

The focused witness runs q1/q7/direct, each with durable terminal checkpoint reopen. All three agree at 64 Java and 3 internal steps, with machine root `0xf3f64e890e1c8bcff114e9b732bf64aca727510983a0e39c52658c120674b9bf` and opaque payload SHA-256 `cf76ef0762232610ae5fc3188b9af3d658a46708dee62a60a1e6365d961b41df`. Retained generated controls run direct/reopen. The completed gate took 129.924868 seconds, issued 492 commands, and verified 551 canonical receipts, below the fixed 1200-second bound.

The runtime is 373704 bytes, below the unchanged 393216-byte cap. Raw52/329162, diagnostic146, 94 images, native14, String-local11, exception kinds14, frames128, checkpoint1MiB, reserve25M, external LOCAL1B budget, System out/err, toolchain rules, and all other limits remain pinned. `root-commitment.json` records the sole leaf83 replacement: its SHA-256 is `f6b60f173a697b6b9ec39919cc307180feefa5ef35c7aad44e3bfa1366d5d726`, Keccak-256 is `c1ff3f8133bf58b9aa931dd43f2c3a952bd796af365edfc723ff1006c20f12a6`, and the recomputed ordered bootstrap root is `3c341fd7756e7da970305cdb9fbac907d941b873328d5f161fb59ad6645c896b`. OutputStream and every other leaf remain runtime-derived.

## Reproduction

From repository root, using fresh ignored `build/` paths and only local pinned dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/print-stream-output-stream-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-preflight/tools/build.py build/java-diff-mc-print-stream-output-stream-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-print-stream-output-stream-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-print-stream-output-stream-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-preflight/tools/gate.py build/java-diff-mc-print-stream-output-stream-build-repro-LOCAL build/java-diff-mc-print-stream-output-stream-retained-fixtures-repro-LOCAL build/java-diff-mc-print-stream-output-stream-fixtures-repro-LOCAL build/java-diff-mc-print-stream-output-stream-gate-repro-LOCAL
```

Tracked `results/` contains final build pins, fixture manifests, source verification, canonical receipt summary, full gate summary, and timing. `SHA256SUMS` covers every tracked stage file except itself.

No original artifact/JAR/class/resource, unchanged-original replay, network, provider/factory execution, world, EULA, or Done input is read or claimed. Parent replay remains deferred.
